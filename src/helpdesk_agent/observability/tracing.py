from opentelemetry import trace
from functools import wraps

tracer = trace.get_tracer("helpdesk_agent")


def traced(name: str):
    """
    Decorator that wraps a function in an OpenTelemetry span.
    Note: no exporter is configured. Spans are created but not sent anywhere
    until an OTel collector (e.g., Jaeger, Prometheus via OTel) is wired up
    in deploy/. This provides the instrumentation hooks now so that adding
    an exporter later requires no code changes to agent/tool functions.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator