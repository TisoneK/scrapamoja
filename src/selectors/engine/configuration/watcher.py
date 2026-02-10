"""
File system monitoring for configuration hot-reloading.

This module provides file system monitoring capabilities to detect
YAML configuration changes and trigger hot-reload operations.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Set, Optional, Dict, List
from datetime import datetime
import logging

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("watchdog not available - file monitoring disabled")


class IConfigurationWatcher(ABC):
    """Interface for monitoring configuration file changes."""
    
    @abstractmethod
    async def start_watching(self, root_path: Path) -> None:
        """Start monitoring configuration files for changes."""
        pass
    
    @abstractmethod
    async def stop_watching(self) -> None:
        """Stop monitoring configuration files."""
        pass
    
    @abstractmethod
    def set_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for file change events."""
        pass
    
    @abstractmethod
    def get_watched_files(self) -> Set[str]:
        """Get set of currently watched files."""
        pass


class ConfigurationFileEventHandler(FileSystemEventHandler):
    """Event handler for configuration file changes."""
    
    def __init__(self, callback: Callable[[str, str], None], file_patterns: List[str]):
        """Initialize the event handler."""
        super().__init__()
        self.callback = callback
        self.file_patterns = file_patterns
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, "modified")
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, "created")
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, "deleted")
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, "moved")
            if hasattr(event, 'dest_path'):
                self._handle_file_change(event.dest_path, "moved")
    
    def _handle_file_change(self, file_path: str, event_type: str) -> None:
        """Handle a file change event."""
        # Check if file matches our patterns
        file_path_obj = Path(file_path)
        
        for pattern in self.file_patterns:
            if file_path_obj.match(pattern):
                try:
                    self.callback(file_path, event_type)
                except Exception as e:
                    self.logger.error(f"Error in change callback for {file_path}: {e}")
                break


class ConfigurationRollbackManager:
    """Manager for handling configuration rollbacks during hot reload."""
    
    def __init__(self):
        """Initialize the rollback manager."""
        self._config_snapshots: Dict[str, 'SelectorConfiguration'] = {}
        self._rollback_history: List[Dict[str, any]] = []
        self.logger = logging.getLogger(__name__)
    
    def create_snapshot(self, file_path: str, config: 'SelectorConfiguration') -> None:
        """Create a snapshot of the current configuration for rollback."""
        self._config_snapshots[file_path] = config
        self.logger.debug(f"Created configuration snapshot for {file_path}")
    
    def rollback_configuration(self, file_path: str) -> Optional['SelectorConfiguration']:
        """Rollback to the previous configuration snapshot."""
        if file_path in self._config_snapshots:
            snapshot = self._config_snapshots[file_path]
            self._rollback_history.append({
                "file_path": file_path,
                "timestamp": datetime.now().isoformat(),
                "reason": "validation_failed"
            })
            self.logger.info(f"Rolled back configuration for {file_path}")
            return snapshot
        else:
            self.logger.warning(f"No snapshot available for rollback: {file_path}")
            return None
    
    def clear_snapshot(self, file_path: str) -> None:
        """Clear the snapshot for a file after successful reload."""
        if file_path in self._config_snapshots:
            del self._config_snapshots[file_path]
            self.logger.debug(f"Cleared configuration snapshot for {file_path}")
    
    def get_rollback_history(self) -> List[Dict[str, any]]:
        """Get the rollback history."""
        return self._rollback_history.copy()
    
    def clear_all_snapshots(self) -> None:
        """Clear all configuration snapshots."""
        self._config_snapshots.clear()
        self.logger.debug("Cleared all configuration snapshots")


class ConfigurationWatcher(IConfigurationWatcher):
    """Implementation for monitoring configuration file changes."""
    
    def __init__(self):
        """Initialize the configuration watcher."""
        self.is_watching = False
        self.observer: Optional[Observer] = None
        self.change_callback: Optional[Callable[[str, str], None]] = None
        self.watched_files: Set[str] = set()
        self.root_path: Optional[Path] = None
        self.logger = logging.getLogger(__name__)
        self._correlation_counter = 0
        self.rollback_manager = ConfigurationRollbackManager()
        
        # File patterns to watch
        self.file_patterns = ["*.yaml", "*.yml"]
        
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("File system monitoring not available - install watchdog package")
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"config_watcher_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def start_watching(self, root_path: Path) -> None:
        """Start monitoring configuration files for changes."""
        if not WATCHDOG_AVAILABLE:
            raise RuntimeError("File system monitoring not available - install watchdog package")
        
        if self.is_watching:
            self.logger.warning("Already watching for configuration changes")
            return
        
        if not root_path.exists():
            raise ValueError(f"Root path does not exist: {root_path}")
        
        self.root_path = root_path
        
        try:
            # Create observer
            self.observer = Observer()
            
            # Create event handler
            event_handler = ConfigurationFileEventHandler(
                self._on_file_change,
                self.file_patterns
            )
            
            # Start watching
            self.observer.schedule(event_handler, str(root_path), recursive=True)
            self.observer.start()
            
            self.is_watching = True
            
            # Scan for existing files
            await self._scan_existing_files(root_path)
            
            self.logger.info(f"Started watching configuration files in {root_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to start file watching: {e}")
            await self.stop_watching()
            raise
    
    async def stop_watching(self) -> None:
        """Stop monitoring configuration files."""
        if not self.is_watching:
            return
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5.0)
                self.observer = None
            
            self.is_watching = False
            self.watched_files.clear()
            
            self.logger.info("Stopped watching configuration files")
            
        except Exception as e:
            self.logger.error(f"Error stopping file watcher: {e}")
    
    def set_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for file change events."""
        self.change_callback = callback
    
    def get_watched_files(self) -> Set[str]:
        """Get set of currently watched files."""
        return self.watched_files.copy()
    
    def is_file_watched(self, file_path: str) -> bool:
        """Check if a specific file is being watched."""
        return file_path in self.watched_files
    
    def get_watch_status(self) -> Dict[str, any]:
        """Get current watch status."""
        return {
            "is_watching": self.is_watching,
            "root_path": str(self.root_path) if self.root_path else None,
            "watched_files_count": len(self.watched_files),
            "file_patterns": self.file_patterns,
            "watchdog_available": WATCHDOG_AVAILABLE
        }
    
    async def _scan_existing_files(self, root_path: Path) -> None:
        """Scan for existing configuration files."""
        self.watched_files.clear()
        
        for pattern in self.file_patterns:
            for file_path in root_path.rglob(pattern):
                if file_path.is_file():
                    self.watched_files.add(str(file_path))
        
        self.logger.info(f"Found {len(self.watched_files)} existing configuration files")
    
    def _on_file_change(self, file_path: str, event_type: str) -> None:
        """Handle a file change event."""
        correlation_id = self._generate_correlation_id()
        
        try:
            # Update watched files set
            if event_type in ["created", "modified"]:
                self.watched_files.add(file_path)
            elif event_type == "deleted":
                self.watched_files.discard(file_path)
            
            # Log the change
            self.logger.debug(f"File {event_type}: {file_path} (correlation: {correlation_id})")
            
            # Call the change callback if set
            if self.change_callback:
                try:
                    self.change_callback(file_path, event_type)
                except Exception as e:
                    self.logger.error(f"Error in change callback: {e}")
            
        except Exception as e:
            self.logger.error(f"Error handling file change {file_path}: {e}")
    
    async def add_watch_pattern(self, pattern: str) -> None:
        """Add a file pattern to watch."""
        if pattern not in self.file_patterns:
            self.file_patterns.append(pattern)
            
            # Rescan if currently watching
            if self.is_watching and self.root_path:
                await self._scan_existing_files(self.root_path)
    
    async def remove_watch_pattern(self, pattern: str) -> None:
        """Remove a file pattern from watching."""
        if pattern in self.file_patterns:
            self.file_patterns.remove(pattern)
            
            # Rescan if currently watching
            if self.is_watching and self.root_path:
                await self._scan_existing_files(self.root_path)
    
    def get_file_change_history(self) -> List[Dict[str, str]]:
        """Get recent file change history (placeholder implementation)."""
        # This would typically maintain a history of changes
        # For now, return empty list
        return []
    
    async def validate_watch_configuration(self) -> Dict[str, any]:
        """Validate the watch configuration."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not WATCHDOG_AVAILABLE:
            validation_result["valid"] = False
            validation_result["errors"].append("watchdog package not available")
        
        if not self.root_path:
            validation_result["valid"] = False
            validation_result["errors"].append("No root path set")
        elif not self.root_path.exists():
            validation_result["valid"] = False
            validation_result["errors"].append(f"Root path does not exist: {self.root_path}")
        
        if not self.file_patterns:
            validation_result["warnings"].append("No file patterns configured")
        
        if not self.change_callback:
            validation_result["warnings"].append("No change callback set")
        
        return validation_result
    
    async def get_performance_metrics(self) -> Dict[str, any]:
        """Get performance metrics for the file watcher."""
        return {
            "watched_files_count": len(self.watched_files),
            "is_watching": self.is_watching,
            "callback_set": self.change_callback is not None,
            "file_patterns_count": len(self.file_patterns),
            "watchdog_available": WATCHDOG_AVAILABLE,
            "uptime_seconds": datetime.now().timestamp() if self.is_watching else 0
        }


# Fallback implementation when watchdog is not available
class FallbackConfigurationWatcher(IConfigurationWatcher):
    """Fallback implementation that polls for file changes."""
    
    def __init__(self, poll_interval: float = 1.0):
        """Initialize the fallback watcher."""
        self.poll_interval = poll_interval
        self.is_watching = False
        self.change_callback: Optional[Callable[[str, str], None]] = None
        self.watched_files: Dict[str, float] = {}
        self.root_path: Optional[Path] = None
        self.logger = logging.getLogger(__name__)
        self._poll_task: Optional[asyncio.Task] = None
        self._correlation_counter = 0
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"fallback_watcher_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def start_watching(self, root_path: Path) -> None:
        """Start monitoring configuration files for changes."""
        if self.is_watching:
            self.logger.warning("Already watching for configuration changes")
            return
        
        if not root_path.exists():
            raise ValueError(f"Root path does not exist: {root_path}")
        
        self.root_path = root_path
        
        # Scan for existing files
        await self._scan_existing_files(root_path)
        
        # Start polling task
        self._poll_task = asyncio.create_task(self._poll_for_changes())
        self.is_watching = True
        
        self.logger.info(f"Started fallback file watching in {root_path}")
    
    async def stop_watching(self) -> None:
        """Stop monitoring configuration files."""
        if not self.is_watching:
            return
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        
        self.is_watching = False
        self.watched_files.clear()
        
        self.logger.info("Stopped fallback file watching")
    
    def set_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for file change events."""
        self.change_callback = callback
    
    def get_watched_files(self) -> Set[str]:
        """Get set of currently watched files."""
        return set(self.watched_files.keys())
    
    async def _scan_existing_files(self, root_path: Path) -> None:
        """Scan for existing configuration files."""
        self.watched_files.clear()
        
        for pattern in ["*.yaml", "*.yml"]:
            for file_path in root_path.rglob(pattern):
                if file_path.is_file():
                    self.watched_files[str(file_path)] = file_path.stat().st_mtime
        
        self.logger.info(f"Found {len(self.watched_files)} existing configuration files")
    
    async def _poll_for_changes(self) -> None:
        """Poll for file changes."""
        while self.is_watching:
            try:
                await self._check_file_changes()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in file polling: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _check_file_changes(self) -> None:
        """Check for file changes."""
        if not self.root_path:
            return
        
        current_files = {}
        
        for pattern in ["*.yaml", "*.yml"]:
            for file_path in self.root_path.rglob(pattern):
                if file_path.is_file():
                    file_path_str = str(file_path)
                    current_mtime = file_path.stat().st_mtime
                    
                    if file_path_str in self.watched_files:
                        old_mtime = self.watched_files[file_path_str]
                        if current_mtime > old_mtime:
                            await self._handle_file_change(file_path_str, "modified")
                    else:
                        await self._handle_file_change(file_path_str, "created")
                    
                    current_files[file_path_str] = current_mtime
        
        # Check for deleted files
        for file_path_str in list(self.watched_files.keys()):
            if file_path_str not in current_files:
                await self._handle_file_change(file_path_str, "deleted")
        
        self.watched_files = current_files
    
    async def _handle_file_change(self, file_path: str, event_type: str) -> None:
        """Handle a file change event."""
        correlation_id = self._generate_correlation_id()
        
        try:
            self.logger.debug(f"File {event_type}: {file_path} (correlation: {correlation_id})")
            
            if self.change_callback:
                self.change_callback(file_path, event_type)
                
        except Exception as e:
            self.logger.error(f"Error handling file change {file_path}: {e}")


def create_configuration_watcher() -> IConfigurationWatcher:
    """Create appropriate configuration watcher based on available dependencies."""
    if WATCHDOG_AVAILABLE:
        return ConfigurationWatcher()
    else:
        logging.warning("Using fallback file watcher - install watchdog for better performance")
        return FallbackConfigurationWatcher()
