from functools import wraps
from typing import Optional, Callable
from helpdesk_agent.schemas.tool_outputs import ToolResult
from helpdesk_agent.services.user_db import user_has_permission
from helpdesk_agent.reliability.circuit_breaker import circuit_breaker
from helpdesk_agent.observability.metrics import TOOL_CALL_COUNTER, TOOL_CALL_LATENCY


class StepLimitExceeded(Exception):
    pass


def safe_execute(required_permission: Optional[str] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(username: str, tool_input) -> ToolResult:
            tool_name = func.__name__

            if circuit_breaker.is_open(tool_name):
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    error="Tool temporarily unavailable due to repeated failures"
                )

            if required_permission is not None:
                if not user_has_permission(username, required_permission):
                    circuit_breaker.record_failure(tool_name)
                    TOOL_CALL_COUNTER.labels(tool_name=tool_name, success="false").inc()
                    return ToolResult(
                        success=False,
                        tool_name=tool_name,
                        error=f"Permission denied: '{required_permission}' required"
                    )

            try:
                with TOOL_CALL_LATENCY.labels(tool_name=tool_name).time():
                    data = func(tool_input)
                circuit_breaker.record_success(tool_name)
                TOOL_CALL_COUNTER.labels(tool_name=tool_name, success="true").inc()
                return ToolResult(success=True, tool_name=tool_name, data=data)
            except Exception as e:
                circuit_breaker.record_failure(tool_name)
                TOOL_CALL_COUNTER.labels(tool_name=tool_name, success="false").inc()
                return ToolResult(success=False, tool_name=tool_name, error=str(e))

        return wrapper
    return decorator