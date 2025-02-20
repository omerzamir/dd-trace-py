from importlib import import_module

from ddtrace import config
from ddtrace.contrib.trace_utils import ext_service
from ddtrace.vendor.wrapt import wrap_function_wrapper as _w

from ...constants import ANALYTICS_SAMPLE_RATE_KEY
from ...constants import SPAN_MEASURED_KEY
from ...ext import SpanTypes
from ...ext import opensearch as metadata
from ...ext import http
from ...internal.compat import urlencode
from ...internal.utils.wrappers import unwrap as _u
from ...pin import Pin
from .quantize import quantize


config._add(
    "opensearch",
    {
        "_default_service": "opensearch",
    },
)


def _es_modules():
    module_names = (
        "opensearch-py",
        "opensearchpy",
    )
    for module_name in module_names:
        try:
            yield import_module(module_name)
        except ImportError:
            pass


# NB: We are patching the default opensearch.transport module
def patch():
    for opensearch in _es_modules():
        _patch(opensearch)


def _patch(opensearch):
    if getattr(opensearch, "_datadog_patch", False):
        return
    setattr(opensearch, "_datadog_patch", True)
    _w(opensearch.transport, "Transport.perform_request", _get_perform_request(opensearch))
    Pin().onto(opensearch.transport.Transport)


def unpatch():
    for opensearch in _es_modules():
        _unpatch(opensearch)


def _unpatch(opensearch):
    if getattr(opensearch, "_datadog_patch", False):
        setattr(opensearch, "_datadog_patch", False)
        _u(opensearch.transport.Transport, "perform_request")


def _get_perform_request(opensearch):
    def _perform_request(func, instance, args, kwargs):
        pin = Pin.get_from(instance)
        if not pin or not pin.enabled():
            return func(*args, **kwargs)

        with pin.tracer.trace(
            "opensearch.query", service=ext_service(pin, config.opensearch), span_type=SpanTypes.OPENSEARCH
        ) as span:
            span.set_tag(SPAN_MEASURED_KEY)

            # Don't instrument if the trace is not sampled
            if not span.sampled:
                return func(*args, **kwargs)

            method, url = args
            params = kwargs.get("params") or {}
            encoded_params = urlencode(params)
            body = kwargs.get("body")

            span.set_tag(metadata.METHOD, method)
            span.set_tag(metadata.URL, url)
            span.set_tag(metadata.PARAMS, encoded_params)
            if config.opensearch.trace_query_string:
                span.set_tag(http.QUERY_STRING, encoded_params)

            if method in ["GET", "POST"]:
                span.set_tag(metadata.BODY, instance.serializer.dumps(body))
            status = None

            # set analytics sample rate
            span.set_tag(ANALYTICS_SAMPLE_RATE_KEY, config.opensearch.get_analytics_sample_rate())

            span = quantize(span)

            try:
                result = func(*args, **kwargs)
            except opensearch.exceptions.TransportError as e:
                span.set_tag(http.STATUS_CODE, getattr(e, "status_code", 500))
                span.error = 1
                raise

            try:
                # Optional metadata extraction with soft fail.
                if isinstance(result, tuple) and len(result) == 2:
                    # opensearch<2.4; it returns both the status and the body
                    status, data = result
                else:
                    # opensearch>=2.4; internal change for ``Transport.perform_request``
                    # that just returns the body
                    data = result

                took = data.get("took")
                if took:
                    span.set_metric(metadata.TOOK, int(took))
            except Exception:
                pass

            if status:
                span.set_tag(http.STATUS_CODE, status)

            return result

    return _perform_request
