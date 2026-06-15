import time
from helpdesk_agent.config.settings import settings


class CircuitBreaker:
    def __init__(self, threshold: int = 3, reset_timeout: int = 60):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failures: dict[str, int] = {}
        self.opened_at: dict[str, float] = {}

    def record_failure(self, tool_name: str) -> None:
        self.failures[tool_name] = self.failures.get(tool_name, 0) + 1
        if self.failures[tool_name] >= self.threshold:
            self.opened_at[tool_name] = time.time()

    def record_success(self, tool_name: str) -> None:
        self.failures[tool_name] = 0
        self.opened_at.pop(tool_name, None)

    def is_open(self, tool_name: str) -> bool:
        opened = self.opened_at.get(tool_name)
        if opened is None:
            return False
        if time.time() - opened >= self.reset_timeout:
            # cooldown elapsed, allow a retry attempt
            self.opened_at.pop(tool_name, None)
            self.failures[tool_name] = 0
            return False
        return True


circuit_breaker = CircuitBreaker(threshold=settings.circuit_breaker_threshold)