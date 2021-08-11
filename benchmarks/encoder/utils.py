import random
import string

from ddtrace.internal.encoding import Encoder
from ddtrace.span import Span


try:
    # the introduction of the buffered encoder changed the internal api
    # see https://github.com/DataDog/dd-trace-py/pull/2422
    from ddtrace.internal._encoding import BufferedEncoder  # noqa: F401

    def init_encoder(max_size=8 << 20, max_item_size=8 << 20):
        return Encoder(max_size, max_item_size)


except ImportError:

    def init_encoder():
        return Encoder()


def _rands(size=6, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def _random_values(k, size):
    return list(set([_rands(size=size) for _ in range(k)]))


def gen_traces(config):
    traces = []

    # choose from a set of randomly generated span attributes
    span_names = _random_values(256, 16)
    resources = _random_values(256, 16)
    services = _random_values(16, 16)
    tag_keys = _random_values(config.ntags, 16)
    metric_keys = _random_values(config.nmetrics, 16)

    for _ in range(config.ntraces):
        trace = []
        for i in range(0, config.nspans):
            # first span is root so has no parent otherwise parent is root span
            parent_id = trace[0].span_id if i > 0 else None
            span_name = random.choice(span_names)
            resource = random.choice(resources)
            service = random.choice(services)
            with Span(None, span_name, resource=resource, service=service, parent_id=parent_id) as span:
                if config.ntags > 0:
                    span.set_tags(dict(zip(tag_keys, [_rands(size=config.ltags) for _ in range(config.ntags)])))
                if config.nmetrics > 0:
                    span.set_metrics(
                        dict(
                            zip(
                                metric_keys,
                                [random.randint(0, 2 ** 16) for _ in range(config.nmetrics)],
                            )
                        )
                    )
                trace.append(span)
        traces.append(trace)
    return traces