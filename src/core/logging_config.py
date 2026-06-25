import logging
import sys
from typing import Optional
from pythonjsonlogger import jsonlogger


class _FlushingStreamHandler(logging.StreamHandler):
    """
    StreamHandler that flushes after every emit().
    
    Standard StreamHandler does NOT flush after each log record. When stderr
    is piped (e.g. `2>&1 | head`), Python uses full buffering, causing all
    logs to appear at once when the program exits instead of streaming in
    real-time. This handler forces a flush after every record.
    """

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


class JsonLoggingConfigurator:
    """
    Centralized logging configuration.
    Ensures single JSON logger across entire application.
    
    Usage:
        JsonLoggingConfigurator.setup(verbose=True)
        logger = logging.getLogger('module.name')
        logger.info('event_name', extra={'field': 'value'})
    """

    @staticmethod
    def setup(verbose: bool = False) -> None:
        level = logging.DEBUG if verbose else logging.INFO

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Remove ALL existing handlers to prevent duplication
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        handler = _FlushingStreamHandler(sys.stderr)
        handler.setLevel(level)

        formatter = jsonlogger.JsonFormatter(
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )

        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        # Silence noisy third-party internals
        logging.getLogger("asyncio").setLevel(logging.ERROR)
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        # Ensure propagation works everywhere
        root_logger.propagate = False
