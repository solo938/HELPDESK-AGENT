import sqlite3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Type, Union, Tuple

# Database-specific retry decorator
db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    retry=retry_if_exception_type(sqlite3.OperationalError),
    reraise=True  # After 3 attempts, raise original exception (not tenacity wrapper)
)

# Generic retry for any exception (for API calls, network issues)
def generic_retry(max_attempts: int = 3, max_wait: int = 4):
    """Factory for generic retry decorator with custom settings."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, max=max_wait),
        reraise=True
    )

# HTTP/network specific retry
http_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception_type((
        ConnectionError,
        TimeoutError,
        ConnectionRefusedError
    )),
    reraise=True
)

# Example usage in services/license_db.py:
"""
from helpdesk_agent.reliability.retry import db_retry

@db_retry
def get_license_status(username: str, software_name: str) -> str:
    # Database query that might fail with OperationalError
    ...
"""