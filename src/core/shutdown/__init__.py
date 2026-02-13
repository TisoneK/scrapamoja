"""
Graceful shutdown coordination module.

Provides centralized shutdown management with priority-based cleanup,
timeout protection, and platform-specific signal handling.

Main exports:
- ShutdownCoordinator: Main class for managing shutdown lifecycle
- ShutdownState: Enum for shutdown states
- ShutdownError, TimeoutError: Exception classes
"""

from .coordinator import ShutdownCoordinator
from .state import ShutdownState
from .exceptions import ShutdownError, TimeoutError

__all__ = [
    "ShutdownCoordinator",
    "ShutdownState", 
    "ShutdownError",
    "TimeoutError",
]
