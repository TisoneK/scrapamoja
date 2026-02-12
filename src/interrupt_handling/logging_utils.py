"""
Signal-safe logging utilities for interrupt handling.
"""

import logging
import sys
import os
import threading
from typing import Optional, TextIO
from contextlib import contextmanager


class SignalSafeLogger:
    """Logger that is safe to use during signal handling."""
    
    def __init__(self, name: str = __name__, fallback_stream: Optional[TextIO] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.fallback_stream = fallback_stream or sys.stderr
        self._lock = threading.Lock()
        
        # Pre-format common messages to avoid formatting during signal handling
        self._preformatted = {
            'interrupt_received': "🛑 Interrupt signal received",
            'shutdown_started': "🔄 Starting graceful shutdown",
            'shutdown_complete': "✅ Graceful shutdown completed",
            'cleanup_error': "❌ Cleanup error occurred",
            'timeout_error': "⏰ Cleanup timeout occurred"
        }
    
    def signal_safe_log(self, level: int, message: str, exc_info: bool = False):
        """
        Log a message in a signal-safe manner.
        
        This method avoids operations that might be unsafe during signal handling,
        such as complex string formatting or I/O operations that might block.
        """
        try:
            # Try normal logging first
            if self.logger.isEnabledFor(level):
                self.logger.log(level, message, exc_info=exc_info)
        except Exception:
            # Fallback to direct stream write if normal logging fails
            try:
                with self._lock:
                    level_name = logging.getLevelName(level)
                    timestamp = os.times()[4]  # Process time
                    fallback_msg = f"[{timestamp:.2f}] {level_name}: {message}\n"
                    self.fallback_stream.write(fallback_msg)
                    self.fallback_stream.flush()
            except Exception:
                # Last resort - silent failure
                pass
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.signal_safe_log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.signal_safe_log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.signal_safe_log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.signal_safe_log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.signal_safe_log(logging.CRITICAL, message, **kwargs)
    
    def preformatted(self, key: str, level: int = logging.INFO):
        """Log a pre-formatted message."""
        if key in self._preformatted:
            self.signal_safe_log(level, self._preformatted[key])
        else:
            self.signal_safe_log(level, f"Unknown preformatted key: {key}")
    
    def exception(self, message: str, exc_info: bool = True):
        """Log exception with traceback."""
        self.signal_safe_log(logging.ERROR, message, exc_info=exc_info)


class InterruptAwareLogHandler(logging.Handler):
    """Log handler that is aware of interrupt handling state."""
    
    def __init__(self, stream: Optional[TextIO] = None):
        super().__init__()
        self.stream = stream or sys.stderr
        self._interrupt_mode = False
        self._lock = threading.Lock()
    
    def set_interrupt_mode(self, enabled: bool):
        """Enable or disable interrupt mode."""
        with self._lock:
            self._interrupt_mode = enabled
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record with interrupt-safe handling."""
        try:
            msg = self.format(record)
            
            with self._lock:
                if self._interrupt_mode:
                    # In interrupt mode, use simpler formatting
                    timestamp = os.times()[4]
                    simple_msg = f"[{timestamp:.1f}] {record.levelname}: {msg}\n"
                    self.stream.write(simple_msg)
                else:
                    # Normal logging
                    self.stream.write(f"{record.levelname}: {msg}\n")
                
                self.stream.flush()
                
        except Exception:
            # Silent failure to avoid recursion during signal handling
            pass


@contextmanager
def interrupt_safe_logging(logger_name: str = __name__):
    """
    Context manager for signal-safe logging.
    
    This sets up a temporary signal-safe logging configuration
    that avoids operations that might be unsafe during signal handling.
    """
    # Get the logger
    logger = logging.getLogger(logger_name)
    
    # Store original handlers
    original_handlers = logger.handlers.copy()
    original_level = logger.level
    
    # Create interrupt-safe handler
    safe_handler = InterruptAwareLogHandler()
    safe_handler.set_interrupt_mode(True)
    
    try:
        # Configure for interrupt-safe operation
        logger.handlers.clear()
        logger.addHandler(safe_handler)
        logger.setLevel(logging.INFO)  # Conservative level during interrupts
        
        yield SignalSafeLogger(logger_name)
        
    finally:
        # Restore original configuration
        logger.handlers.clear()
        for handler in original_handlers:
            logger.addHandler(handler)
        logger.setLevel(original_level)


def setup_interrupt_safe_logging():
    """
    Setup global interrupt-safe logging configuration.
    
    This should be called during application initialization to ensure
    that logging is safe during interrupt handling.
    """
    # Create a global interrupt-safe handler
    safe_handler = InterruptAwareLogHandler()
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(safe_handler)
    
    # Store reference for later access
    if not hasattr(root_logger, '_interrupt_safe_handler'):
        root_logger._interrupt_safe_handler = safe_handler


def enable_interrupt_mode():
    """Enable interrupt mode for all interrupt-safe handlers."""
    root_logger = logging.getLogger()
    if hasattr(root_logger, '_interrupt_safe_handler'):
        root_logger._interrupt_safe_handler.set_interrupt_mode(True)


def disable_interrupt_mode():
    """Disable interrupt mode for all interrupt-safe handlers."""
    root_logger = logging.getLogger()
    if hasattr(root_logger, '_interrupt_safe_handler'):
        root_logger._interrupt_safe_handler.set_interrupt_mode(False)
