# app/logger.py
import logging
import sys
import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog once at application startup.
    Call this in main.py before anything else.
    """
    # 1. Configure the standard library logging to feed into structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # 2. Configure structlog's processing pipeline
    structlog.configure(
        processors=[
            # Add log level to every event
            structlog.stdlib.add_log_level,
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="iso"),
            # If there's an exception, render it nicely
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            # Final render: JSON in production, colored in dev
            structlog.processors.JSONRenderer(),
        ],
        # Use standard library logging under the hood
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "tip"):
    """
    Return a structlog logger bound to a given name/module.
    Usage: logger = get_logger(__name__)
    """
    return structlog.get_logger(name)