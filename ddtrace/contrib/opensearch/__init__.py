"""
The Opensearch integration will trace Opensearch queries.

Enabling
~~~~~~~~

The Opensearch integration is enabled automatically when using
:ref:`ddtrace-run<ddtracerun>` or :func:`patch_all()<ddtrace.patch_all>`.

Or use :func:`patch()<ddtrace.patch>` to manually enable the integration::

    from ddtrace import patch
    from opensearch import Opensearch

    patch(opensearch=True)
    # This will report spans with the default instrumentation
    es = Opensearch(port=Opensearch['port'])
    # Example of instrumented query
    es.indices.create(index='books', ignore=400)

    # Use a pin to specify metadata related to this client
    es = Opensearch(port=Opensearch['port'])
    Pin.override(es.transport, service='opensearch-videos')
    es.indices.create(index='videos', ignore=400)



Configuration
~~~~~~~~~~~~~

.. py:data:: ddtrace.config.opensearch['service']

   The service name reported for your opensearch app.


Example::

    from ddtrace import config

    # Override service name
    config.opensearch['service'] = 'custom-service-name'
"""
from .patch import patch


__all__ = ["patch"]
