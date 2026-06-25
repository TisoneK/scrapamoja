"""
Structured logging configuration for site scraper framework.

Provides centralized logging setup with correlation IDs,
structured JSON output, and appropriate log levels.
"""

import structlog
import logging
import sys
from typing import Any, Dict

# Guard to prevent multiple basicConfig calls
_logging_configured = False


def setup_logger(name: str = "sites") -> structlog.stdlib.BoundLogger:
    """Setup structured logger for site scraper operations."""
    global _logging_configured

    # Configure structlog (idempotent — structlog.configure is safe to call multiple times)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging only once — send to stderr so stdout stays clean for JSON output
    if not _logging_configured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.basicConfig(
            format="%(message)s",
            handlers=[handler],
            level=logging.INFO,
        )
        _logging_configured = True

    return structlog.get_logger(name)


def get_logger(site_id: str = None, correlation_id: str = None) -> structlog.stdlib.BoundLogger:
    """Get logger with optional site and correlation context."""
    logger = setup_logger()

    context: Dict[str, Any] = {}
    if site_id:
        context["site_id"] = site_id
    if correlation_id:
        context["correlation_id"] = correlation_id

    return logger.bind(**context) if context else logger
