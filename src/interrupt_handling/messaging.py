"""
User messaging system for interrupt handling feedback.
"""

import logging
import sys
import time
import threading
import os
from typing import Optional, TextIO, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field

from .config import InterruptConfig
from .handler import InterruptContext


class MessageType(Enum):
    """Types of interrupt messages."""
    ACKNOWLEDGMENT = "acknowledgment"
    PROGRESS = "progress"
    COMPLETION = "completion"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InterruptMessage:
    """A message to display to the user."""
    message_type: MessageType
    text: str
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age(self) -> float:
        """Get age of message in seconds."""
        return time.time() - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message_type': self.message_type.value,
            'text': self.text,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'age': self.age,
            'metadata': self.metadata
        }


class MessageFormatter:
    """Formats interrupt messages for display."""
    
    def __init__(self, use_colors: bool = True, use_icons: bool = True, verbosity_level: int = 1):
        self.use_colors = use_colors
        self.use_icons = use_icons
        self.verbosity_level = verbosity_level  # 0=minimal, 1=normal, 2=verbose
        self.logger = logging.getLogger(__name__)
        
        # Color codes (ANSI)
        self.colors = {
            'reset': '\033[0m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'bold': '\033[1m'
        }
        
        # Icons
        self.icons = {
            'interrupt': '🛑',
            'progress': '🔄',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'cleanup': '🧹',
            'save': '💾',
            'network': '🌐',
            'database': '🗄️',
            'file': '📄'
        }
    
    def set_verbosity_level(self, level: int):
        """Set the verbosity level (0=minimal, 1=normal, 2=verbose)."""
        self.verbosity_level = max(0, min(2, level))
    
    def should_show_message(self, message_type: MessageType, priority: MessagePriority) -> bool:
        """Determine if a message should be shown based on verbosity."""
        if self.verbosity_level == 0:  # Minimal
            # Only show high priority and critical messages
            return priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]
        elif self.verbosity_level == 1:  # Normal
            # Show all except low priority
            return priority != MessagePriority.LOW
        else:  # Verbose
            # Show all messages
            return True
    
    def format_message(self, message: InterruptMessage) -> str:
        """Format a message for display."""
        # Check if message should be shown based on verbosity
        if not self.should_show_message(message.message_type, message.priority):
            return ""  # Return empty string for filtered messages
        
        # Start with icon if enabled
        prefix = ""
        if self.use_icons:
            icon = self._get_icon_for_type(message.message_type)
            prefix = f"{icon} "
        
        # Add color if enabled
        color = ""
        if self.use_colors:
            color = self._get_color_for_priority(message.priority)
            prefix = f"{color}{prefix}"
            suffix = self.colors['reset']
        else:
            suffix = ""
        
        # Format timestamp if recent
        time_str = ""
        if message.age < 5.0:  # Show timestamp for recent messages
            time_str = f"[{time.strftime('%H:%M:%S', time.localtime(message.timestamp))}] "
        
        # Add verbosity-specific details
        details_str = ""
        if self.verbosity_level == 2:  # Verbose mode
            # Add metadata details
            if message.metadata:
                metadata_parts = [f"{k}={v}" for k, v in message.metadata.items()]
                details_str = f" [{', '.join(metadata_parts)}]"
        
        # Combine all parts
        formatted = f"{prefix}{time_str}{message.text}{details_str}{suffix}"
        
        return formatted
    
    def _get_icon_for_type(self, message_type: MessageType) -> str:
        """Get icon for message type."""
        icon_map = {
            MessageType.ACKNOWLEDGMENT: self.icons['interrupt'],
            MessageType.PROGRESS: self.icons['progress'],
            MessageType.COMPLETION: self.icons['success'],
            MessageType.ERROR: self.icons['error'],
            MessageType.WARNING: self.icons['warning'],
            MessageType.INFO: self.icons['info']
        }
        return icon_map.get(message_type, '')
    
    def _get_color_for_priority(self, priority: MessagePriority) -> str:
        """Get color for message priority."""
        color_map = {
            MessagePriority.LOW: self.colors['white'],
            MessagePriority.NORMAL: self.colors['cyan'],
            MessagePriority.HIGH: self.colors['yellow'],
            MessagePriority.CRITICAL: self.colors['red']
        }
        return color_map.get(priority, self.colors['white'])
    
    def format_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Format a progress bar."""
        if total == 0:
            return "[" + " " * width + "]"
        
        filled = int((current / total) * width)
        bar = "█" * filled + "░" * (width - filled)
        percentage = (current / total) * 100
        
        if self.use_colors:
            bar = f"{self.colors['green']}{bar}{self.colors['reset']}"
        
        return f"[{bar}] {current}/{total} ({percentage:.1f}%)"
    
    def format_resource_status(self, resource_type: str, success: bool, count: int = 1) -> str:
        """Format resource cleanup status."""
        if self.use_icons:
            icon = self.icons.get(resource_type.lower(), '')
            status_icon = self.icons['success'] if success else self.icons['error']
            return f"{status_icon} {icon} resources ({count})"
        else:
            status = "CLEANED" if success else "FAILED"
            return f"{resource_type.upper()} {status} ({count})"


class InterruptMessageHandler:
    """Handles interrupt messages and user communication."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Output streams
        self.stdout: TextIO = sys.stdout
        self.stderr: TextIO = sys.stderr
        
        # Message formatter with verbosity level
        verbosity_level = 0 if not config.verbose_feedback else 1
        if hasattr(config, 'feedback_verbosity_level'):
            verbosity_level = config.feedback_verbosity_level
        
        self.formatter = MessageFormatter(
            use_colors=self._should_use_colors(),
            use_icons=self._should_use_icons(),
            verbosity_level=verbosity_level
        )
        
        # Message state
        self._messages: List[InterruptMessage] = []
        self._lock = threading.Lock()
        self._last_progress_time = 0.0
        self._progress_rate_limit = 0.5  # Minimum seconds between progress updates
    
    def set_verbosity_level(self, level: int):
        """Set the verbosity level for message display."""
        self.formatter.set_verbosity_level(level)
        self.logger.debug(f"Set verbosity level to {level}")
    
    def get_verbosity_level(self) -> int:
        """Get the current verbosity level."""
        return self.formatter.verbosity_level
    
    def _should_use_colors(self) -> bool:
        """Determine if colors should be used."""
        # Check if output is a TTY
        if hasattr(sys.stdout, 'isatty') and not sys.stdout.isatty():
            return False
        
        # Check environment variables
        if os.environ.get('NO_COLOR', '').lower() in ('1', 'true', 'yes'):
            return False
        
        # Check config
        return self.config.verbose_feedback
    
    def _should_use_icons(self) -> bool:
        """Determine if icons should be used."""
        # Check if terminal supports Unicode
        if not self._supports_unicode():
            return False
        
        # Check environment variables
        if os.environ.get('NO_ICONS', '').lower() in ('1', 'true', 'yes'):
            return False
        
        return True
    
    def _supports_unicode(self) -> bool:
        """Check if terminal supports Unicode."""
        try:
            encoding = sys.stdout.encoding or 'ascii'
            return 'utf' in encoding.lower()
        except:
            return False
    
    def acknowledge_interrupt(self, context: InterruptContext):
        """Send interrupt acknowledgment message."""
        message = InterruptMessage(
            message_type=MessageType.ACKNOWLEDGMENT,
            text=f"Interrupt received ({context.signal_name}) - Initiating graceful shutdown",
            priority=MessagePriority.HIGH,
            metadata={
                'signal_number': context.signal_number,
                'signal_name': context.signal_name,
                'thread_id': context.thread_id
            }
        )
        
        self._send_message(message)
    
    def report_progress(self, step: str, current: int, total: int, 
                     resource_type: Optional[str] = None, details: Optional[str] = None):
        """Report progress during cleanup."""
        # Rate limit progress updates
        current_time = time.time()
        if current_time - self._last_progress_time < self._progress_rate_limit:
            return
        
        self._last_progress_time = current_time
        
        # Create progress text
        if resource_type:
            progress_text = f"Cleaning up {resource_type}: {self.formatter.format_progress_bar(current, total)}"
        else:
            progress_text = f"Progress: {self.formatter.format_progress_bar(current, total)}"
        
        # Add details if provided
        if details:
            progress_text += f" - {details}"
        
        message = InterruptMessage(
            message_type=MessageType.PROGRESS,
            text=progress_text,
            priority=MessagePriority.NORMAL,
            metadata={
                'step': step,
                'current': current,
                'total': total,
                'percentage': (current / total) * 100 if total > 0 else 0,
                'resource_type': resource_type,
                'details': details
            }
        )
        
        self._send_message(message, overwrite=True)
    
    def report_resource_cleanup(self, resource_type: str, success: bool, count: int = 1):
        """Report resource cleanup status."""
        status_text = self.formatter.format_resource_status(resource_type, success, count)
        
        message = InterruptMessage(
            message_type=MessageType.INFO if success else MessageType.WARNING,
            text=status_text,
            priority=MessagePriority.NORMAL,
            metadata={
                'resource_type': resource_type,
                'success': success,
                'count': count
            }
        )
        
        self._send_message(message)
    
    def report_checkpoint_status(self, success: bool, checkpoint_path: Optional[str] = None):
        """Report checkpoint creation status."""
        if success:
            text = "Checkpoint created successfully"
            if checkpoint_path:
                text += f": {checkpoint_path}"
        else:
            text = "Checkpoint creation failed"
        
        message = InterruptMessage(
            message_type=MessageType.INFO if success else MessageType.ERROR,
            text=text,
            priority=MessagePriority.NORMAL,
            metadata={
                'success': success,
                'checkpoint_path': checkpoint_path
            }
        )
        
        self._send_message(message)
    
    def report_shutdown_complete(self):
        """Report shutdown completion."""
        message = InterruptMessage(
            message_type=MessageType.COMPLETION,
            text="Graceful shutdown completed successfully",
            priority=MessagePriority.HIGH
        )
        
        self._send_message(message)
    
    def report_shutdown_error(self, error: Exception):
        """Report shutdown error."""
        message = InterruptMessage(
            message_type=MessageType.ERROR,
            text=f"Shutdown error: {error}",
            priority=MessagePriority.CRITICAL,
            metadata={
                'error_type': type(error).__name__,
                'error_message': str(error)
            }
        )
        
        self._send_message(message)
    
    def report_cleanup_error(self, resource_type: str, error: Exception, count: int = 1):
        """Report cleanup error with detailed information."""
        error_text = f"Cleanup failed for {resource_type} ({count}): {error}"
        
        message = InterruptMessage(
            message_type=MessageType.ERROR,
            text=error_text,
            priority=MessagePriority.HIGH,
            metadata={
                'resource_type': resource_type,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'count': count
            }
        )
        
        self._send_message(message)
    
    def send_custom_message(self, text: str, message_type: MessageType = MessageType.INFO,
                         priority: MessagePriority = MessagePriority.NORMAL,
                         metadata: Optional[Dict[str, Any]] = None):
        """Send a custom message."""
        message = InterruptMessage(
            message_type=message_type,
            text=text,
            priority=priority,
            metadata=metadata or {}
        )
        
        self._send_message(message)
    
    def _send_message(self, message: InterruptMessage, overwrite: bool = False):
        """Send a message to the user."""
        with self._lock:
            # Store message
            self._messages.append(message)
            
            # Limit message history
            if len(self._messages) > 100:
                self._messages = self._messages[-50:]
            
            # Format and display message
            formatted_message = self.formatter.format_message(message)
            
            # Choose output stream
            output_stream = self.stderr if message.priority in [MessagePriority.HIGH, MessagePriority.CRITICAL] else self.stdout
            
            try:
                if overwrite:
                    # Use carriage return for progress updates
                    output_stream.write(f"\r{formatted_message}")
                    output_stream.flush()
                else:
                    # Regular message with newline
                    output_stream.write(f"{formatted_message}\n")
                    output_stream.flush()
                    
            except BrokenPipeError:
                # Handle broken pipe (e.g., output redirected to closed file)
                pass
            except Exception as e:
                self.logger.error(f"Error sending message: {e}")
    
    def get_message_history(self, limit: Optional[int] = None) -> List[InterruptMessage]:
        """Get message history."""
        with self._lock:
            messages = self._messages.copy()
        
        if limit:
            return messages[-limit:]
        
        return messages
    
    def clear_messages(self):
        """Clear message history."""
        with self._lock:
            self._messages.clear()
    
    def set_output_streams(self, stdout: TextIO, stderr: TextIO):
        """Set custom output streams."""
        self.stdout = stdout
        self.stderr = stderr
    
    def get_messaging_status(self) -> Dict[str, Any]:
        """Get messaging system status."""
        with self._lock:
            message_count = len(self._messages)
            recent_messages = [msg for msg in self._messages if msg.age < 60.0]
        
        return {
            'total_messages': message_count,
            'recent_messages': len(recent_messages),
            'uses_colors': self.formatter.use_colors,
            'uses_icons': self.formatter.use_icons,
            'verbosity_level': self.formatter.verbosity_level,
            'progress_rate_limit': self._progress_rate_limit,
            'last_progress_time': self._last_progress_time
        }


# Global message handler instance
_message_handler = None


def get_message_handler(config: InterruptConfig) -> InterruptMessageHandler:
    """Get the global message handler instance."""
    global _message_handler
    if _message_handler is None:
        _message_handler = InterruptMessageHandler(config)
    return _message_handler
