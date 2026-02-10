"""
Hot-reloading for configuration changes in the scraper framework.

This module provides comprehensive hot-reloading capabilities, including file watching,
configuration change detection, and automatic application of updates.
"""

import os
import asyncio
import json
import yaml
from typing import Dict, Any, List, Optional, Callable, Set, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config_loader import ConfigLoader, ConfigLoadResult
from .config_cache import ConfigCache


class ReloadEventType(Enum):
    """Configuration reload event types."""
    FILE_CHANGED = "file_changed"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    FILE_MOVED = "file_moved"
    DIRECTORY_CHANGED = "directory_changed"


@dataclass
class ReloadEvent:
    """Configuration reload event."""
    event_type: ReloadEventType
    file_path: str
    timestamp: datetime
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    config_path: str = ""
    environment: str = ""
    reload_applied: bool = False
    error: Optional[str] = None


@dataclass
class ReloadResult:
    """Result of configuration reload operation."""
    success: bool
    events: List[ReloadEvent] = field(default_factory=list)
    reloaded_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    reload_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfigFileEventHandler(FileSystemEventHandler):
    """File system event handler for configuration files."""
    
    def __init__(self, hot_reload_manager):
        self.hot_reload_manager = hot_reload_manager
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event)
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event)
    
    def on_moved(self, event):
        """Handle file move events."""
        if not event.is_directory:
            self.hot_reload_manager._handle_file_change(event)


class ConfigHotReloadManager:
    """Configuration hot-reloading manager."""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None, 
                 config_cache: Optional[ConfigCache] = None):
        """Initialize hot-reload manager."""
        self.config_loader = config_loader or ConfigLoader()
        self.config_cache = config_cache or ConfigCache()
        
        self._watchers: Dict[str, Observer] = {}
        self._watched_paths: Set[str] = set()
        self._file_patterns: Set[str] = {
            '*.json', '*.yaml', '*.yml', '.env*', 'config.*', 'settings.*'
        }
        
        self._reload_callbacks: List[Callable[[ReloadResult], None]] = []
        self._reload_history: List[ReloadResult] = []
        self._performance_stats = {
            'total_reloads': 0,
            'total_events': 0,
            'total_time_ms': 0.0,
            'average_time_ms': 0.0,
            'last_reload_time': None
        }
        
        self._is_running = False
        self._lock = threading.Lock()
        
        # Configuration for hot-reloading
        self._debounce_time_ms = 1000  # Debounce time to avoid multiple reloads
        self._max_file_size = 10 * 1024 * 1024  # 10MB max file size
        self._ignore_patterns = {
            '*.tmp', '*.swp', '*.bak', '*~', '.DS_Store', 'Thumbs.db'
        }
        
        # Built-in file patterns to watch
        self._config_file_patterns = [
            'config.{env}.json',
            'config.{env}.yaml',
            'config.{env}.yml',
            'settings.{env}.json',
            'settings.{env}.yaml',
            'settings.{env}.yml',
            '.env.{env}',
            'feature_flags.json',
            'config.json',
            'config.yaml',
            'config.yml',
            'settings.json',
            'settings.yaml',
            'settings.yml'
        ]
    
    def start_watching(self, paths: List[str], recursive: bool = True) -> bool:
        """
        Start watching configuration files for changes.
        
        Args:
            paths: List of paths to watch
            recursive: Whether to watch recursively
            
        Returns:
            True if watching started successfully
        """
        try:
            if self._is_running:
                return True
            
            with self._lock:
                self._is_running = True
                
                # Create observers for each path
                for path in paths:
                    path_obj = Path(path)
                    if not path_obj.exists():
                        print(f"Warning: Path does not exist: {path}")
                        continue
                    
                    if path_obj.is_dir():
                        observer = Observer()
                        event_handler = ConfigFileEventHandler(self)
                        observer.schedule(event_handler, path_obj, recursive=recursive)
                        observer.start()
                        self._watchers[str(path_obj)] = observer
                        self._watched_paths.add(str(path_obj))
                    else:
                        # Watch parent directory for file changes
                        parent_path = path_obj.parent
                        if parent_path.exists():
                            observer = Observer()
                            event_handler = ConfigFileEventHandler(self)
                            observer.schedule(event_handler, parent_path, recursive=False)
                            observer.start()
                            self._watchers[str(parent_path)] = observer
                            self._watched_paths.add(str(parent_path))
            
            print(f"Started watching {len(self._watchers)} paths for configuration changes")
            return True
            
        except Exception as e:
            print(f"Error starting file watching: {str(e)}")
            return False
    
    def stop_watching(self) -> bool:
        """Stop watching configuration files."""
        try:
            with self._lock:
                if not self._is_running:
                    return True
                
                self._is_running = False
                
                # Stop all observers
                for observer in self._watchers.values():
                    observer.stop()
                    observer.join()
                
                self._watchers.clear()
                self._watched_paths.clear()
            
            print("Stopped watching configuration files")
            return True
            
        except Exception as e:
            print(f"Error stopping file watching: {str(e)}")
            return False
    
    def is_watching(self) -> bool:
        """Check if hot-reloading is active."""
        return self._is_running
    
    def add_watch_path(self, path: str, recursive: bool = True) -> bool:
        """Add a path to watch."""
        try:
            if self._is_running:
                # Stop current watching and restart
                self.stop_watching()
            
            path_obj = Path(path)
            if not path_obj.exists():
                return False
            
            # Add to watched paths
            self._watched_paths.add(str(path_obj))
            
            # Restart watching if currently running
            if self._is_running:
                return self.start_watching(list(self._watched_paths), recursive)
            
            return True
            
        except Exception as e:
            print(f"Error adding watch path {path}: {str(e)}")
            return False
    
    def remove_watch_path(self, path: str) -> bool:
        """Remove a path from watching."""
        try:
            path_obj = Path(path)
            path_str = str(path_obj)
            
            if path_str in self._watched_paths:
                self._watched_paths.remove(path_str)
                
                # Restart watching if currently running
                if self._is_running:
                    self.stop_watching()
                    return self.start_watching(list(self._watched_paths))
            
            return True
            
        except Exception as e:
            print(f"Error removing watch path {path}: {str(e)}")
            return False
    
    def add_reload_callback(self, callback: Callable[[ReloadResult], None]) -> None:
        """Add a callback for reload events."""
        self._reload_callbacks.append(callback)
    
    def remove_reload_callback(self, callback: Callable[[ReloadResult], None]) -> bool:
        """Remove a reload callback."""
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)
            return True
        return False
    
    def _handle_file_change(self, event) -> None:
        """Handle file system change event."""
        try:
            file_path = Path(event.src_path)
            
            # Skip if file is too large
            if file_path.stat().st_size > self._max_file_size:
                return
            
            # Skip if file matches ignore patterns
            if self._should_ignore_file(file_path):
                return
            
            # Check if it's a configuration file
            if not self._is_config_file(file_path):
                return
            
            # Determine event type
            if event.event_type.name == 'modified':
                event_type = ReloadEventType.FILE_CHANGED
            elif event.event_type.name == 'created':
                event_type = ReloadEventType.FILE_CREATED
            elif event.event_type.name == 'deleted':
                event_type = ReloadEventType.FILE_DELETED
            elif event_type.name == 'moved':
                event_type = ReloadEventType.FILE_MOVED
            else:
                return
            
            # Create reload event
            reload_event = ReloadEvent(
                event_type=event_type,
                file_path=str(file_path),
                timestamp=datetime.utcnow()
            )
            
            # Debounce rapid changes
            asyncio.create_task(self._debounced_reload(reload_event))
            
        except Exception as e:
            print(f"Error handling file change event: {str(e)}")
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        file_name = file_path.name
        
        # Check ignore patterns
        for pattern in self._ignore_patterns:
            if file_name.startswith(pattern.replace('*', '')):
                return True
        
        # Check if it's a hidden file
        if file_name.startswith('.'):
            return True
        
        # Check file extension
        if file_path.suffix in ['.tmp', '.swp', '.bak', '~']:
            return True
        
        return False
    
    def _is_config_file(self, file_path: Path) -> bool:
        """Check if file is a configuration file."""
        file_name = file_path.name.lower()
        
        # Check built-in patterns
        for pattern in self._config_file_patterns:
            if pattern.replace('{env}', '') in file_name:
                return True
        
        # Check custom patterns
        for pattern in self._file_patterns:
            if pattern.replace('{env}', '') in file_name:
                return True
        
        return False
    
    async def _debounced_reload(self, event: ReloadEvent) -> None:
        """Debounced reload to handle rapid file changes."""
        try:
            # Wait debounce time
            await asyncio.sleep(self._debounce_time_ms / 1000.0)
            
            # Perform reload
            reload_result = await self._perform_reload(event)
            
            # Notify callbacks
            for callback in self._reload_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(reload_result)
                    else:
                        callback(reload_result)
                except Exception as e:
                    print(f"Error in reload callback: {str(e)}")
            
        except Exception as e:
            print(f"Error in debounced reload: {str(e)}")
    
    async def _perform_reload(self, event: ReloadEvent) -> ReloadResult:
        """Perform the actual configuration reload."""
        start_time = time.time()
        
        try:
            reload_result = ReloadResult(
                success=True,
                events=[event]
            )
            
            # Determine environment from file path
            environment = self._extract_environment_from_path(event.file_path)
            
            # Load new configuration
            config_load_result = self.config_loader.reload_config(
                environment=environment,
                config_path=event.file_path
            )
            
            if config_load_result.success:
                reload_result.reloaded_configs[environment] = config_load_result.config
                reload_result.success = True
                
                # Update cache
                if self.config_cache:
                    self.config_cache.set(environment, config_load_result.config)
                
                # Apply configuration changes
                await self._apply_configuration_changes(
                    environment, 
                    config_load_result.config, 
                    event
                )
            else:
                reload_result.errors.extend(config_load_result.errors)
                reload_result.success = False
            
            # Calculate reload time
            end_time = time.time()
            reload_result.reload_time_ms = (end_time - start_time) * 1000
            
            # Update stats
            self._update_performance_stats(reload_result)
            
            # Store in history
            self._reload_history.append(reload_result)
            
            return reload_result
            
        except Exception as e:
            end_time = time.time()
            reload_time_ms = (end_time - start_time) * 1000
            
            return ReloadResult(
                success=False,
                events=[event],
                errors=[f"Reload failed: {str(e)}"],
                reload_time_ms=reload_time_ms
            )
    
    def _extract_environment_from_path(self, file_path: str) -> str:
        """Extract environment from file path."""
        path_obj = Path(file_path)
        file_name = path_obj.name.lower()
        
        # Check environment patterns in filename
        env_patterns = {
            'development': ['dev', 'development'],
            'testing': ['test', 'testing'],
            'staging': ['staging', 'stage'],
            'production': ['prod', 'production'],
            'local': ['local']
        }
        
        for env, patterns in env_patterns.items():
            for pattern in patterns:
                if pattern in file_name:
                    return env
        
        return "unknown"
    
    async def _apply_configuration_changes(self, environment: str, 
                                         new_config: Dict[str, Any], 
                                         event: ReloadEvent) -> None:
        """Apply configuration changes to the system."""
        try:
            # This would implement the actual application of configuration changes
            # For now, it's a placeholder
            print(f"Applying configuration changes for {environment}")
            print(f"Changed file: {event.file_path}")
            
            # Notify other parts of the system about configuration changes
            # This could involve updating in-memory configurations,
            # notifying components, triggering reinitialization, etc.
            
        except Exception as e:
            print(f"Error applying configuration changes: {str(e)}")
    
    def reload_config(self, environment: Optional[str] = None,
                     config_path: Optional[str] = None) -> ReloadResult:
        """Manually trigger configuration reload."""
        start_time = time.time()
        
        try:
            # Create a mock event for manual reload
            event = ReloadEvent(
                event_type=ReloadEventType.FILE_CHANGED,
                file_path=config_path or "manual_reload",
                timestamp=datetime.utcnow()
            )
            
            # Perform reload
            reload_result = asyncio.run(self._perform_reload(event))
            
            # Notify callbacks
            for callback in self._reload_callbacks:
                try:
                    if asyncio.is_coroutinefunction(callback):
                        asyncio.run(callback(reload_result))
                    else:
                        callback(reload_result)
                except Exception as e:
                    print(f"Error in reload callback: {str(e)}")
            
            return reload_result
            
        except Exception as e:
            end_time = time.time()
            reload_time_ms = (end_time - start_time) * 1000
            
            return ReloadResult(
                success=False,
                errors=[f"Manual reload failed: {str(e)}"],
                reload_time_ms=reload_time_ms
            )
    
    def _update_performance_stats(self, result: ReloadResult) -> None:
        """Update performance statistics."""
        self._performance_stats['total_reloads'] += 1
        self._performance_stats['total_events'] += len(result.events)
        self._performance_stats['total_time_ms'] += result.reload_time_ms
        self._performance_stats['average_time_ms'] = (
            self._performance_stats['total_time_ms'] / 
            self._performance_stats['total_reloads']
        )
        self._performance_stats['last_reload_time'] = datetime.utcnow()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self._performance_stats.copy()
        
        # Add watcher info
        stats['is_watching'] = self._is_running
        stats['watched_paths'] = list(self._watched_paths)
        stats['watcher_count'] = len(self._watchers)
        stats['callback_count'] = len(self._reload_callbacks)
        
        return stats
    
    def get_reload_history(self, limit: Optional[int] = None) -> List[ReloadResult]:
        """Get reload history."""
        if limit:
            return self._reload_history[-limit:]
        return self._reload_history.copy()
    
    def clear_history(self) -> None:
        """Clear reload history."""
        self._reload_history.clear()
    
    def set_debounce_time(self, debounce_time_ms: int) -> None:
        """Set debounce time for file changes."""
        self._debounce_ms = debounce_time_ms
    
    def set_max_file_size(self, max_size_bytes: int) -> None:
        """Set maximum file size to watch."""
        self._max_file_size = max_size_bytes
    
    def add_ignore_pattern(self, pattern: str) -> None:
        """Add file pattern to ignore."""
        self._ignore_patterns.add(pattern)
    
    def remove_ignore_pattern(self, pattern: str) -> bool:
        """Remove file pattern from ignore list."""
        if pattern in self._ignore_patterns:
            self._ignore_patterns.remove(pattern)
            return True
        return False
    
    def add_file_pattern(self, pattern: str) -> None:
        """Add file pattern to watch."""
        self._file_patterns.add(pattern)
    
    def remove_file_pattern(self, pattern: str) -> bool:
        """Remove file pattern from watch list."""
        if pattern in self._file_patterns:
            self._file_patterns.remove(pattern)
            return True
        return False
    
    def get_watched_paths(self) -> List[str]:
        """Get list of watched paths."""
        return list(self._watched_paths)
    
    def get_ignore_patterns(self) -> List[str]:
        """Get list of ignore patterns."""
        return list(self._ignore_patterns)
    
    def get_file_patterns(self) -> List[str]:
        """Get list of file patterns."""
        return list(self._file_patterns)
    
    def export_config(self) -> Dict[str, Any]:
        """Export hot-reload configuration."""
        return {
            'debounce_time_ms': self._debounce_time_ms,
            'max_file_size': self._max_file_size,
            'ignore_patterns': list(self._import_patterns),
            'file_patterns': list(self._file_patterns),
            'config_file_patterns': self._config_file_patterns,
            'is_watching': self._is_running,
            'watched_paths': list(self._watched_paths),
            'callback_count': len(self._reload_callbacks),
            'performance_stats': self.get_performance_stats()
        }
    
    def import_config(self, config: Dict[str, Any]) -> None:
        """Import hot-reload configuration."""
        self._debounce_time_ms = config.get('debounce_time_ms', self._debounce_ms)
        self._max_file_size = config.get('max_file_size', self._max_file_size)
        self._ignore_patterns = set(config.get('ignore_patterns', []))
        self._file_patterns = set(config.get('file_patterns', []))
        
        # Restart watching if currently running
        if self._is_running:
            self.stop_watching()
            if 'watched_paths' in config:
                self.start_watching(config['watched_paths'])


# Global hot-reload manager instance
_config_hot_reload_manager = ConfigHotReloadManager()


# Convenience functions
def start_watching(paths: List[str], recursive: bool = True) -> bool:
    """Start watching configuration files."""
    return _config_hot_reload_manager.start_watching(paths, recursive)


def stop_watching() -> bool:
    """Stop watching configuration files."""
    return _config_hot_reload_manager.stop_watching()


def is_watching() -> bool:
    """Check if hot-reloading is active."""
    return _config_hot_reload_manager.is_watching()


def add_watch_path(path: str, recursive: bool = True) -> bool:
    """Add a path to watch."""
    return _config_hot_reload_manager.add_watch_path(path, recursive)


def remove_watch_path(path: str) -> bool:
    """Remove a path from watching."""
    return _config_hot_reload_manager.remove_watch_path(path)


def add_reload_callback(callback: Callable[[ReloadResult], None]) -> None:
    """Add a reload callback."""
    _config_hot_reload_manager.add_reload_callback(callback)


def reload_config(environment: Optional[str] = None,
                 config_path: Optional[str] = None) -> ReloadResult:
    """Manually trigger configuration reload."""
    return _config_hot_reload_manager.reload_config(environment, config_path)


def get_performance_stats() -> Dict[str, Any]:
    """Get hot-reload performance statistics."""
    return _config_hot_reload_manager.get_performance_stats()


def get_reload_history(limit: Optional[int] = None) -> List[ReloadResult]:
    """Get reload history."""
    return _config_hot_reload_manager.get_reload_history(limit)


def clear_history() -> None:
    """Clear reload history."""
    _config_hot_reload_manager.clear_history()
