"""
Platform-specific utilities for interrupt handling.
"""

import sys
import os
import signal
import logging
from typing import List, Dict, Optional, Callable
from enum import Enum


class Platform(Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class PlatformSignalHandler:
    """Platform-specific signal handling utilities."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform = self._detect_platform()
        self._original_handlers: Dict[int, Callable] = {}
    
    def _detect_platform(self) -> Platform:
        """Detect the current platform."""
        system = sys.platform.lower()
        
        if system == "win32" or system == "cygwin":
            return Platform.WINDOWS
        elif system.startswith("linux"):
            return Platform.LINUX
        elif system.startswith("darwin"):
            return Platform.MACOS
        else:
            return Platform.UNKNOWN
    
    def get_available_signals(self) -> List[int]:
        """Get list of available interrupt signals for current platform."""
        if self.platform == Platform.WINDOWS:
            # Windows has limited signal support
            available = [signal.SIGINT]
            if hasattr(signal, 'SIGBREAK'):
                available.append(signal.SIGBREAK)
            # SIGTERM is available but may not work as expected
            if hasattr(signal, 'SIGTERM'):
                available.append(signal.SIGTERM)
        else:
            # Unix-like systems have full signal support
            available = [signal.SIGINT, signal.SIGTERM]
            if hasattr(signal, 'SIGHUP'):
                available.append(signal.SIGHUP)
            if hasattr(signal, 'SIGQUIT'):
                available.append(signal.SIGQUIT)
        
        return available
    
    def register_signal_handler(self, signum: int, handler: Callable) -> bool:
        """
        Register a signal handler with platform-specific considerations.
        
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Store original handler
            self._original_handlers[signum] = signal.signal(signum, handler)
            self.logger.debug(f"Registered handler for signal {signum} on {self.platform.value}")
            return True
        except (OSError, ValueError) as e:
            self.logger.warning(f"Could not register handler for signal {signum} on {self.platform.value}: {e}")
            return False
    
    def restore_signal_handlers(self):
        """Restore all original signal handlers."""
        for signum, handler in self._original_handlers.items():
            try:
                signal.signal(signum, handler)
                self.logger.debug(f"Restored handler for signal {signum} on {self.platform.value}")
            except (OSError, ValueError) as e:
                self.logger.warning(f"Could not restore handler for signal {signum} on {self.platform.value}: {e}")
        
        self._original_handlers.clear()
    
    def setup_windows_console_handling(self, handler: Callable) -> bool:
        """
        Setup Windows-specific console event handling.
        
        This provides better interrupt handling on Windows console applications.
        """
        if self.platform != Platform.WINDOWS:
            return True  # Not applicable on other platforms
        
        try:
            import ctypes
            from ctypes import wintypes
            
            # Define Windows API types and functions
            kernel32 = ctypes.windll.kernel32
            
            # Define callback type
            CONSOLE_CTRL_HANDLER = ctypes.CFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
            
            # Console control event types
            CTRL_C_EVENT = 0
            CTRL_BREAK_EVENT = 1
            CTRL_CLOSE_EVENT = 2
            CTRL_LOGOFF_EVENT = 5
            CTRL_SHUTDOWN_EVENT = 6
            
            # Store reference to prevent garbage collection
            if not hasattr(self, '_windows_handler_ref'):
                self._windows_handler_ref = None
            
            def windows_handler(ctrl_type):
                """Windows console control handler."""
                try:
                    # Map Windows events to signals
                    if ctrl_type in [CTRL_C_EVENT, CTRL_BREAK_EVENT]:
                        handler(signal.SIGINT, None)
                        return True
                    elif ctrl_type in [CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT]:
                        handler(signal.SIGTERM, None)
                        return True
                except Exception as e:
                    self.logger.error(f"Error in Windows console handler: {e}")
                
                return False  # Let default handler run
            
            # Create and register handler
            handler_func = CONSOLE_CTRL_HANDLER(windows_handler)
            self._windows_handler_ref = handler_func
            
            result = kernel32.SetConsoleCtrlHandler(handler_func, 1)
            if result:
                self.logger.debug("Windows console control handler registered")
                return True
            else:
                self.logger.warning("Failed to register Windows console control handler")
                return False
                
        except ImportError:
            self.logger.warning("ctypes not available, Windows console handling disabled")
            return False
        except Exception as e:
            self.logger.error(f"Error setting up Windows console handling: {e}")
            return False
    
    def cleanup_windows_console_handling(self):
        """Cleanup Windows console event handling."""
        if self.platform != Platform.WINDOWS:
            return
        
        try:
            import ctypes
            
            if hasattr(self, '_windows_handler_ref') and self._windows_handler_ref:
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleCtrlHandler(self._windows_handler_ref, 0)
                self._windows_handler_ref = None
                self.logger.debug("Windows console control handler unregistered")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up Windows console handling: {e}")
    
    def get_platform_recommendations(self) -> Dict[str, str]:
        """Get platform-specific recommendations."""
        recommendations = {}
        
        if self.platform == Platform.WINDOWS:
            recommendations.update({
                'signal_limitations': "Windows has limited signal support, prefer console events",
                'recommended_signals': "SIGINT, SIGBREAK (Ctrl+Break)",
                'fallback_mechanism': "Use atexit handlers and try/except blocks",
                'console_handling': "Enable Windows console event handling for better responsiveness"
            })
        elif self.platform == Platform.LINUX:
            recommendations.update({
                'signal_support': "Full signal support available",
                'recommended_signals': "SIGINT, SIGTERM, SIGHUP",
                'additional_signals': "SIGQUIT for forceful termination",
                'process_groups': "Consider process group handling for child processes"
            })
        elif self.platform == Platform.MACOS:
            recommendations.update({
                'signal_support': "Unix-like signal support",
                'recommended_signals': "SIGINT, SIGTERM",
                'app_nap': "Be aware of App Nap affecting background processes",
                'grand_central': "Consider Grand Central Dispatch for async operations"
            })
        else:
            recommendations.update({
                'compatibility': "Unknown platform, using basic signal handling",
                'testing': "Thorough testing recommended",
                'fallbacks': "Implement multiple fallback mechanisms"
            })
        
        return recommendations
    
    def is_signal_supported(self, signum: int) -> bool:
        """Check if a specific signal is supported on the current platform."""
        available_signals = self.get_available_signals()
        return signum in available_signals
    
    def get_signal_name(self, signum: int) -> str:
        """Get human-readable name for a signal number."""
        if hasattr(signal, 'Signals'):
            # Python 3.5+ has Signals enum
            try:
                return signal.Signals(signum).name
            except ValueError:
                pass
        
        # Fallback to common signal names
        signal_names = {
            signal.SIGINT: "SIGINT",
            signal.SIGTERM: "SIGTERM",
        }
        
        if hasattr(signal, 'SIGBREAK') and signum == signal.SIGBREAK:
            return "SIGBREAK"
        if hasattr(signal, 'SIGHUP') and signum == signal.SIGHUP:
            return "SIGHUP"
        if hasattr(signal, 'SIGQUIT') and signum == signal.SIGQUIT:
            return "SIGQUIT"
        
        return signal_names.get(signum, f"Signal({signum})")
    
    def setup_platform_specific_logging(self):
        """Setup platform-specific logging configuration."""
        if self.platform == Platform.WINDOWS:
            # Windows-specific logging considerations
            logging.getLogger().addHandler(logging.StreamHandler())
            self.logger.debug("Windows-specific logging configured")
        elif self.platform == Platform.LINUX:
            # Linux-specific logging considerations
            self.logger.debug("Linux-specific logging configured")
        elif self.platform == Platform.MACOS:
            # macOS-specific logging considerations
            self.logger.debug("macOS-specific logging configured")


# Global platform handler instance
_platform_handler = None


def get_platform_handler() -> PlatformSignalHandler:
    """Get the global platform handler instance."""
    global _platform_handler
    if _platform_handler is None:
        _platform_handler = PlatformSignalHandler()
    return _platform_handler


def get_current_platform() -> Platform:
    """Get the current platform."""
    return get_platform_handler().platform
