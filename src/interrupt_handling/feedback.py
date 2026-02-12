"""
User feedback system for interrupt handling.
"""

import logging
import sys
import time
import threading
from typing import Optional, TextIO, TYPE_CHECKING
from enum import Enum

from .config import InterruptConfig

if TYPE_CHECKING:
    from .handler import InterruptContext


class FeedbackLevel(Enum):
    """Levels of feedback verbosity."""
    MINIMAL = "minimal"
    NORMAL = "normal"
    VERBOSE = "verbose"


class FeedbackProvider:
    """Provides user feedback during interrupt processing."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Feedback state
        self._feedback_lock = threading.Lock()
        self._last_feedback_time = 0
        self._feedback_count = 0
        
        # Output streams
        self._stdout: TextIO = sys.stdout
        self._stderr: TextIO = sys.stderr
        
        # Determine feedback level
        self._feedback_level = self._determine_feedback_level()
    
    def _determine_feedback_level(self) -> FeedbackLevel:
        """Determine the appropriate feedback level."""
        if self.config.verbose_feedback:
            return FeedbackLevel.VERBOSE
        
        if self.config.log_level in ['DEBUG']:
            return FeedbackLevel.VERBOSE
        
        return FeedbackLevel.NORMAL
    
    def acknowledge_interrupt(self, context: 'InterruptContext'):
        """Provide immediate acknowledgment of interrupt."""
        with self._feedback_lock:
            if self._feedback_level == FeedbackLevel.MINIMAL:
                return
            
            message = f"\n🛑 Interrupt received ({context.signal_name})"
            
            if self._feedback_level == FeedbackLevel.VERBOSE:
                message += f" at {time.strftime('%H:%M:%S', time.localtime(context.timestamp))}"
            
            self._print_message(message, stream=self._stderr)
            self._feedback_count += 1
    
    def shutdown_progress(self, step: str, current: int, total: int, details: str = ""):
        """Provide progress feedback during shutdown."""
        with self._feedback_lock:
            if self._feedback_level == FeedbackLevel.MINIMAL:
                return
            
            # Rate limit progress updates
            current_time = time.time()
            if current_time - self._last_feedback_time < 0.5 and current < total:
                return
            
            self._last_feedback_time = current_time
            
            if self.config.show_progress_bar and self._feedback_level != FeedbackLevel.MINIMAL:
                # Simple progress bar
                progress_width = 20
                filled = int((current / total) * progress_width)
                bar = "█" * filled + "░" * (progress_width - filled)
                message = f"\r🔄 Shutting down: [{bar}] {current}/{total} {step}"
            else:
                message = f"🔄 {step} ({current}/{total})"
            
            if details and self._feedback_level == FeedbackLevel.VERBOSE:
                message += f" - {details}"
            
            self._print_message(message, end="\r" if current < total else "\n")
            self._feedback_count += 1
    
    def shutdown_complete(self):
        """Provide completion feedback."""
        with self._feedback_lock:
            if self._feedback_level == FeedbackLevel.MINIMAL:
                return
            
            message = "✅ Graceful shutdown completed"
            
            if self._feedback_level == FeedbackLevel.VERBOSE:
                message += f" ({self._feedback_count} feedback messages)"
            
            self._print_message(message)
            self._feedback_count += 1
    
    def shutdown_error(self, error: Exception):
        """Provide error feedback."""
        with self._feedback_lock:
            message = f"❌ Shutdown error: {error}"
            
            if self._feedback_level == FeedbackLevel.VERBOSE:
                message += f" (type: {type(error).__name__})"
            
            self._print_message(message, stream=self._stderr)
            self._feedback_count += 1
    
    def resource_cleanup_status(self, resource_type: str, success: bool, count: int = 1):
        """Provide resource cleanup status feedback."""
        with self._feedback_lock:
            if self._feedback_level == FeedbackLevel.MINIMAL:
                return
            
            status_icon = "✅" if success else "❌"
            message = f"{status_icon} {resource_type} resources ({count})"
            
            if self._feedback_level == FeedbackLevel.VERBOSE:
                message += f" cleaned up" if success else " cleanup failed"
            
            self._print_message(message)
            self._feedback_count += 1
    
    def checkpoint_status(self, success: bool, checkpoint_path: Optional[str] = None):
        """Provide checkpoint creation status feedback."""
        with self._feedback_lock:
            if self._feedback_level == FeedbackLevel.MINIMAL:
                return
            
            if success:
                message = "💾 Checkpoint created"
                if checkpoint_path and self._feedback_level == FeedbackLevel.VERBOSE:
                    message += f": {checkpoint_path}"
            else:
                message = "⚠️  Checkpoint creation failed"
            
            self._print_message(message)
            self._feedback_count += 1
    
    def callback_execution_status(self, callback_name: str, success: bool, error: Optional[Exception] = None):
        """Provide callback execution status feedback."""
        with self._feedback_lock:
            if self._feedback_level == FeedbackLevel.MINIMAL:
                return
            
            status_icon = "✅" if success else "❌"
            message = f"{status_icon} Callback: {callback_name}"
            
            if not success and error and self._feedback_level == FeedbackLevel.VERBOSE:
                message += f" - {error}"
            
            self._print_message(message)
            self._feedback_count += 1
    
    def _print_message(self, message: str, end: str = "\n", stream: Optional[TextIO] = None):
        """Print a message with appropriate stream and formatting."""
        output_stream = stream or self._stdout
        
        try:
            # Ensure we're not interfering with other output
            if end == "\r":
                output_stream.write(message + end)
                output_stream.flush()
            else:
                # Add newline if message doesn't end with one
                if not message.endswith('\n'):
                    message += '\n'
                output_stream.write(message)
                output_stream.flush()
        except (BrokenPipeError, OSError):
            # Handle cases where output stream is closed
            pass
    
    def set_output_streams(self, stdout: TextIO, stderr: TextIO):
        """Set custom output streams for testing or redirection."""
        self._stdout = stdout
        self._stderr = stderr
    
    def get_feedback_statistics(self) -> dict:
        """Get feedback statistics."""
        with self._feedback_lock:
            return {
                'feedback_level': self._feedback_level.value,
                'feedback_count': self._feedback_count,
                'last_feedback_time': self._last_feedback_time,
                'show_progress_bar': self.config.show_progress_bar,
                'verbose_feedback': self.config.verbose_feedback
            }
