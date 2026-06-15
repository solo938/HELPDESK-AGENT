import logging
import sys
from helpdesk_agent.guardrails.pii_scrubber import scrub_pii
from helpdesk_agent.config.settings import settings


class PIIScrubFilter(logging.Filter):
    """
    Custom logging filter that scrubs PII from all log messages automatically.
    
    This ensures sensitive data (emails, phone numbers, SSNs) never reaches log files,
    without requiring each log call to manually call scrub_pii().
    """
    def filter(self, record):
        # Scrub the log message before it's emitted
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = scrub_pii(record.msg)
        return True


def setup_logging():
    """
    Configure root logger with PII scrubbing filter.
    
    Call this once at application startup (e.g., in api/main.py).
    """
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add PII scrubbing filter to the handler
    console_handler.addFilter(PIIScrubFilter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info("Logging configured with PII scrubbing")