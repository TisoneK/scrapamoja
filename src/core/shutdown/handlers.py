"""
Platform-specific signal handlers for graceful shutdown.

Provides signal detection and handler registration for different platforms
(Windows vs Unix) to initiate graceful shutdown process.
"""

import signal
import sys
import asyncio
from typing import Callable, Optional

from .state import ShutdownState


class SignalHandler:
    """Manages platform-specific signal handling for graceful shutdown."""
    
    def __init__(self, shutdown_callback: Callable[[], None]):
        self._shutdown_callback = shutdown_callback
        self._original_handlers = {}
        self._logger = None
    
    def set_logger(self, logger) -> None:
        """Set logger for signal handler operations."""
        self._logger = logger
    
    def register_signal_handlers(self) -> None:
        """Register appropriate signal handlers based on platform."""
        # Always register SIGINT (Ctrl+C)
        self._register_handler(signal.SIGINT, "SIGINT")
        
        # Platform-specific signals
        if sys.platform.startswith('win'):
            # Windows: Use SIGBREAK for termination
            if hasattr(signal, 'SIGBREAK'):
                self._register_handler(signal.SIGBREAK, "SIGBREAK")
        else:
            # Unix: Use SIGTERM for termination
            self._register_handler(signal.SIGTERM, "SIGTERM")
        
        if self._logger:
            registered_signals = list(self._original_handlers.keys())
            self._logger.info(f"Registered signal handlers", signals=registered_signals)
    
    def _register_handler(self, signum: int, name: str) -> None:
        """Register a signal handler and store the original."""
        try:
            # Store original handler for restoration
            self._original_handlers[signum] = signal.signal(signum, self._create_handler(name))
        except (OSError, ValueError) as e:
            if self._logger:
                self._logger.warning(f"Failed to register signal handler", signal=name, error=str(e))
    
    def _create_handler(self, signal_name: str) -> Callable:
        """Create a signal handler function."""
        def handler(signum: int, frame) -> None:
            if self._logger:
                self._logger.info(f"Received signal", signal=signal_name, signum=signum)
            
            # Initiate shutdown asynchronously
            try:
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(self._async_shutdown())
                else:
                    # If no event loop, call directly
                    self._shutdown_callback()
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Error in signal handler", signal=signal_name, error=str(e))
                # Fallback: call directly
                self._shutdown_callback()
        
        return handler
    
    async def _async_shutdown(self) -> None:
        """Handle shutdown asynchronously."""
        try:
            if asyncio.iscoroutinefunction(self._shutdown_callback):
                await self._shutdown_callback()
            else:
                self._shutdown_callback()
        except Exception as e:
            if self._logger:
                self._logger.error(f"Error during async shutdown", error=str(e))
    
    def restore_original_handlers(self) -> None:
        """Restore original signal handlers."""
        for signum, original_handler in self._original_handlers.items():
            try:
                signal.signal(signum, original_handler)
            except (OSError, ValueError) as e:
                if self._logger:
                    self._logger.warning(f"Failed to restore signal handler", signum=signum, error=str(e))
        
        self._original_handlers.clear()
        
        if self._logger:
            self._logger.info("Restored original signal handlers")
    
    def get_supported_signals(self) -> list:
        """Get list of supported signals for current platform."""
        signals = [signal.SIGINT]
        
        if sys.platform.startswith('win'):
            if hasattr(signal, 'SIGBREAK'):
                signals.append(signal.SIGBREAK)
        else:
            signals.append(signal.SIGTERM)
        
        return signals
