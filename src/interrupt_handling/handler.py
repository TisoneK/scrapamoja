"""
Centralized interrupt handler for coordinating safe shutdown.
"""

import signal
import threading
import logging
import time
import sys
import asyncio
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
    
    def _log_diagnostics(self, context: str):
        """Log diagnostic information about threads and async tasks."""
        self.logger.info(f"=== DIAGNOSTIC: {context} ===")
        
        # Log active threads
        active_threads = threading.enumerate()
        self.logger.info(f"Active threads ({len(active_threads)}):")
        for thread in active_threads:
            self.logger.info(f"  - {thread.name} (ID: {thread.ident}, Daemon: {thread.daemon})")
        
        # Log async tasks if event loop exists
        try:
            if asyncio.get_event_loop().is_running():
                tasks = asyncio.all_tasks()
                self.logger.info(f"Pending async tasks ({len(tasks)}):")
                for task in tasks:
                    self.logger.info(f"  - {task.get_name()} (Done: {task.done()})")
            else:
                self.logger.info("No active event loop")
        except Exception as e:
            self.logger.info(f"Could not check async tasks: {e}")
        
        self.logger.info("=== END DIAGNOSTIC ===")

    def _close_event_loops(self):
        """Close all running event loops properly with timeout."""
        try:
            self.logger.info("Starting event loop closure")
            
            # Since we're in the interrupt thread, we need to find the main thread's event loop
            try:
                # Try to get the main thread's event loop
                import threading
                main_thread = threading.main_thread()
                
                # Check if we can access the main thread's event loop
                try:
                    # This will work if we're in the same process and the loop is accessible
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self.logger.info(f"Found accessible event loop: {loop}")
                        
                        # Get all tasks in the loop
                        tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
                        if tasks:
                            self.logger.info(f"Cancelling {len(tasks)} pending tasks")
                            for task in tasks:
                                task.cancel()
                                
                            # Wait for tasks to complete with timeout
                            try:
                                # Use asyncio.wait_for for timeout
                                async def wait_for_tasks():
                                    return await asyncio.gather(*tasks, return_exceptions=True)
                                
                                # 5 second timeout for task cancellation
                                loop.run_until_complete(
                                    asyncio.wait_for(wait_for_tasks(), timeout=5.0)
                                )
                                self.logger.info("All tasks cancelled successfully")
                            except asyncio.TimeoutError:
                                self.logger.warning("Timeout while cancelling tasks - forcing continuation")
                            except Exception as e:
                                self.logger.warning(f"Error while cancelling tasks: {e}")
                        else:
                            self.logger.info("No pending tasks to cancel")
                    else:
                        self.logger.info("Event loop found but not running")
                        
                except RuntimeError:
                    self.logger.info("No accessible event loop found - may be in main thread")
                    
            except Exception as e:
                self.logger.warning(f"Error accessing event loop: {e}")
            
            # Since we can't directly close the main thread's event loop from this thread,
            # we'll add explicit process exit to force termination
            self.logger.info("Event loop closure completed - will use explicit process exit")
                
        except Exception as e:
            self.logger.error(f"Error in event loop closure: {e}")
        
        # Additional force cleanup - try to get current loop and stop it
        try:
            import asyncio
            current_loop = asyncio.get_running_loop()
            if current_loop and not current_loop.is_closed():
                self.logger.info("Force stopping current event loop")
                current_loop.stop()
        except Exception as e:
            self.logger.debug(f"Could not stop current loop: {e}")

    def _perform_shutdown(self):
        """Perform the actual shutdown process."""
        with self._shutdown_lock:
            try:
                self.state = InterruptState.SHUTTING_DOWN
                self.logger.info("Starting graceful shutdown")
                
                # Log diagnostics at shutdown start
                self._log_diagnostics("SHUTDOWN_START")
                
                # Execute interrupt callbacks
                self._execute_interrupt_callbacks()
                
                # Perform resource cleanup
                self.resource_manager.cleanup_all()
                
                # Create checkpoint if enabled
                if self.config.enable_checkpoints:
                    self._create_checkpoint()
                
                self.state = InterruptState.SHUTDOWN_COMPLETE
                self.logger.info("Graceful shutdown completed")
                
                # Log diagnostics after cleanup
                self._log_diagnostics("POST_CLEANUP")
                
                # Close event loops properly
                self._close_event_loops()
                
                # Provide completion feedback
                self.feedback_provider.shutdown_complete()
                
                # Set flag for main thread to exit instead of raising SystemExit in daemon thread
                self._should_exit = True
                
                # Add explicit process exit after a short delay to ensure cleanup completes
                import threading
                import time
                
                def delayed_exit():
                    time.sleep(1.0)  # Give 1 second for any final cleanup
                    self.logger.info("Executing explicit process exit")
                    sys.exit(0)
                
                exit_thread = threading.Thread(target=delayed_exit, daemon=True)
                exit_thread.start()
                
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
