"""
Centralized interrupt handler for coordinating safe shutdown.
"""

import signal
import threading
import logging
import time
from typing import Callable, List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from .config import InterruptConfig
from .resource_manager import ResourceManager
from .feedback import FeedbackProvider


class InterruptState(Enum):
    """States of interrupt handling."""
    NORMAL = "normal"
    INTERRUPTED = "interrupted"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_COMPLETE = "shutdown_complete"


@dataclass
class InterruptContext:
    """Context information about an interrupt event."""
    signal_number: int
    signal_name: str
    timestamp: float
    thread_id: int
    additional_info: Dict[str, Any] = None


class InterruptHandler:
    """Centralized interrupt handler for safe scraping operations."""
    
    def __init__(self, config: Optional[InterruptConfig] = None):
        self.config = config or InterruptConfig()
        self.state = InterruptState.NORMAL
        self.interrupt_context: Optional[InterruptContext] = None
        self.logger = logging.getLogger(__name__)
        self._should_exit = False
        
        # Components
        self.resource_manager = ResourceManager(self.config)
        self.feedback_provider = FeedbackProvider(self.config)
        
        # Callbacks
        self.interrupt_callbacks: List[Callable[[InterruptContext], None]] = []
        
        # Threading
        self._shutdown_lock = threading.RLock()
        self._original_handlers: Dict[int, Callable] = {}
        
        # Setup logging
        self._setup_logging()
        
        # Register signal handlers if enabled
        if self.config.enable_interrupt_handling:
            self._register_signal_handlers()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
    
    def _register_signal_handlers(self):
        """Register signal handlers for interrupt signals."""
        signals_to_handle = [signal.SIGINT, signal.SIGTERM]
        
        # Add Windows-specific signals if available
        if hasattr(signal, 'SIGBREAK'):
            signals_to_handle.append(signal.SIGBREAK)
        
        for sig in signals_to_handle:
            try:
                # Store original handler
                self._original_handlers[sig] = signal.signal(sig, self._signal_handler)
                self.logger.debug(f"Registered handler for signal {sig}")
            except (OSError, ValueError) as e:
                self.logger.warning(f"Could not register handler for signal {sig}: {e}")
    
    def _signal_handler(self, signum: int, frame):
        """Handle incoming interrupt signals."""
        with self._shutdown_lock:
            if self.state != InterruptState.NORMAL:
                # Already handling interrupt, ignore additional signals
                self.logger.debug(f"Ignoring additional signal {signum}, already in {self.state}")
                return
            
            # Create interrupt context
            signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
            self.interrupt_context = InterruptContext(
                signal_number=signum,
                signal_name=signal_name,
                timestamp=time.time(),
                thread_id=threading.get_ident()
            )
            
            # Update state
            self.state = InterruptState.INTERRUPTED
            
            self.logger.info(f"Received interrupt signal {signal_name} ({signum})")
            
            # Provide immediate feedback
            self.feedback_provider.acknowledge_interrupt(self.interrupt_context)
            
            # Start shutdown process in separate thread to avoid signal handling constraints
            shutdown_thread = threading.Thread(
                target=self._perform_shutdown,
                name="interrupt-shutdown",
                daemon=True
            )
            shutdown_thread.start()
    
    def _perform_shutdown(self):
        """Perform the actual shutdown process."""
        with self._shutdown_lock:
            try:
                self.state = InterruptState.SHUTTING_DOWN
                self.logger.info("Starting graceful shutdown")
                
                # Execute interrupt callbacks
                self._execute_interrupt_callbacks()
                
                # Perform resource cleanup
                self.resource_manager.cleanup_all()
                
                # Create checkpoint if enabled
                if self.config.enable_checkpoints:
                    self._create_checkpoint()
                
                self.state = InterruptState.SHUTDOWN_COMPLETE
                self.logger.info("Graceful shutdown completed")
                
                # Provide completion feedback
                self.feedback_provider.shutdown_complete()
                
                # Set flag for main thread to exit instead of raising SystemExit in daemon thread
                self._should_exit = True
                
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")
                self.feedback_provider.shutdown_error(e)
            finally:
                # Restore original signal handlers
                self._restore_signal_handlers()
    
    def _execute_interrupt_callbacks(self):
        """Execute all registered interrupt callbacks."""
        if not self.interrupt_callbacks:
            return
        
        self.logger.debug(f"Executing {len(self.interrupt_callbacks)} interrupt callbacks")
        
        for callback in self.interrupt_callbacks:
            try:
                callback(self.interrupt_context)
            except Exception as e:
                self.logger.error(f"Error in interrupt callback: {e}")
    
    def _create_checkpoint(self):
        """Create a checkpoint of current state."""
        # This will be implemented in the data preservation phase
        self.logger.debug("Checkpoint creation requested")
    
    def _restore_signal_handlers(self):
        """Restore original signal handlers."""
        import threading
        main_thread = threading.main_thread()
        current_thread = threading.current_thread()
        
        for sig, handler in self._original_handlers.items():
            try:
                # Only restore signal handlers in the main thread
                if current_thread is main_thread:
                    signal.signal(sig, handler)
                    self.logger.debug(f"Restored handler for signal {sig}")
                else:
                    self.logger.debug(f"Skipping signal restoration for {sig} - not in main thread")
            except (OSError, ValueError) as e:
                self.logger.warning(f"Could not restore handler for signal {sig}: {e}")
    
    def register_interrupt_callback(self, callback: Callable[[InterruptContext], None]):
        """Register a callback to be called when interrupt occurs."""
        self.interrupt_callbacks.append(callback)
        self.logger.debug(f"Registered interrupt callback: {callback.__name__}")
    
    def unregister_interrupt_callback(self, callback: Callable[[InterruptContext], None]):
        """Unregister an interrupt callback."""
        try:
            self.interrupt_callbacks.remove(callback)
            self.logger.debug(f"Unregistered interrupt callback: {callback.__name__}")
        except ValueError:
            self.logger.warning(f"Callback not found for unregistration: {callback.__name__}")
    
    def is_interrupted(self) -> bool:
        """Check if interrupt has been received."""
        return self.state != InterruptState.NORMAL
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self.state in [InterruptState.SHUTTING_DOWN, InterruptState.SHUTDOWN_COMPLETE]
    
    def get_state(self) -> InterruptState:
        """Get current interrupt state."""
        return self.state
    
    def should_exit(self) -> bool:
        """Check if the program should exit after interrupt handling."""
        return self._should_exit
    
    def force_shutdown(self):
        """Force immediate shutdown without graceful cleanup."""
        self.logger.warning("Force shutdown requested")
        self.state = InterruptState.SHUTDOWN_COMPLETE
        self._restore_signal_handlers()
    
    def cleanup(self):
        """Cleanup handler resources."""
        self._restore_signal_handlers()
        self.resource_manager.cleanup_all()
