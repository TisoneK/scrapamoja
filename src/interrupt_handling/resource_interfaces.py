"""
Resource registration interfaces for different types of resources.
"""

import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Callable, Union, TextIO
from contextlib import contextmanager
from abc import ABC, abstractmethod

from .resource_manager import ResourceType, ResourceCleanupTask


class ResourceInterface(ABC):
    """Abstract base class for resource interfaces."""
    
    def __init__(self, resource_id: str, resource_type: ResourceType):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.is_registered = False
        self.metadata: Dict[str, Any] = {}
    
    @abstractmethod
    def get_cleanup_function(self) -> Callable[[], None]:
        """Get the cleanup function for this resource."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of this resource."""
        pass
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata for this resource."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)


class DatabaseResource(ResourceInterface):
    """Interface for database resources."""
    
    def __init__(self, resource_id: str, connection: Any, commit_before_close: bool = True):
        super().__init__(resource_id, ResourceType.DATABASE)
        self.connection = connection
        self.commit_before_close = commit_before_close
        self.connection_type = self._detect_connection_type()
    
    def _detect_connection_type(self) -> str:
        """Detect the type of database connection."""
        if hasattr(self.connection, '__class__'):
            class_name = self.connection.__class__.__name__
            if 'sqlite' in class_name.lower():
                return 'sqlite'
            elif 'postgres' in class_name.lower() or 'psycopg' in class_name.lower():
                return 'postgresql'
            elif 'mysql' in class_name.lower():
                return 'mysql'
            elif 'mongodb' in class_name.lower():
                return 'mongodb'
        return 'unknown'
    
    def get_cleanup_function(self) -> Callable[[], None]:
        """Get cleanup function for database connection."""
        def cleanup():
            try:
                if self.connection:
                    if self.commit_before_close and hasattr(self.connection, 'commit'):
                        self.connection.commit()
                    if hasattr(self.connection, 'close'):
                        self.connection.close()
            except Exception as e:
                # Log error but don't raise
                import logging
                logging.getLogger(__name__).error(f"Error cleaning up database connection {self.resource_id}: {e}")
        
        return cleanup
    
    def get_description(self) -> str:
        """Get description of database resource."""
        return f"Database connection ({self.connection_type}) - {self.resource_id}"


class FileResource(ResourceInterface):
    """Interface for file resources."""
    
    def __init__(self, resource_id: str, file_handle: TextIO, flush_before_close: bool = True):
        super().__init__(resource_id, ResourceType.FILE)
        self.file_handle = file_handle
        self.flush_before_close = flush_before_close
        self.filename = getattr(file_handle, 'name', 'unknown')
        self.mode = getattr(file_handle, 'mode', 'unknown')
    
    def get_cleanup_function(self) -> Callable[[], None]:
        """Get cleanup function for file handle."""
        def cleanup():
            try:
                if self.file_handle and not self.file_handle.closed:
                    if self.flush_before_close and hasattr(self.file_handle, 'flush'):
                        self.file_handle.flush()
                    if hasattr(self.file_handle, 'close'):
                        self.file_handle.close()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error cleaning up file handle {self.resource_id}: {e}")
        
        return cleanup
    
    def get_description(self) -> str:
        """Get description of file resource."""
        return f"File handle ({self.filename}, {self.mode}) - {self.resource_id}"


class NetworkResource(ResourceInterface):
    """Interface for network resources."""
    
    def __init__(self, resource_id: str, connection: Any, close_method: str = 'close'):
        super().__init__(resource_id, ResourceType.NETWORK)
        self.connection = connection
        self.close_method = close_method
        self.connection_type = self._detect_connection_type()
    
    def _detect_connection_type(self) -> str:
        """Detect the type of network connection."""
        if hasattr(self.connection, '__class__'):
            class_name = self.connection.__class__.__name__
            if 'socket' in class_name.lower():
                return 'socket'
            elif 'http' in class_name.lower() or 'request' in class_name.lower():
                return 'http'
            elif 'ftp' in class_name.lower():
                return 'ftp'
            elif 'ssh' in class_name.lower():
                return 'ssh'
        return 'unknown'
    
    def get_cleanup_function(self) -> Callable[[], None]:
        """Get cleanup function for network connection."""
        def cleanup():
            try:
                if self.connection and hasattr(self.connection, self.close_method):
                    close_func = getattr(self.connection, self.close_method)
                    close_func()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error cleaning up network connection {self.resource_id}: {e}")
        
        return cleanup
    
    def get_description(self) -> str:
        """Get description of network resource."""
        return f"Network connection ({self.connection_type}) - {self.resource_id}"


class CustomResource(ResourceInterface):
    """Interface for custom resources with user-defined cleanup."""
    
    def __init__(self, resource_id: str, cleanup_func: Callable[[], None], description: str = ""):
        super().__init__(resource_id, ResourceType.CUSTOM)
        self._cleanup_func = cleanup_func
        self._description = description or f"Custom resource - {resource_id}"
    
    def get_cleanup_function(self) -> Callable[[], None]:
        """Get cleanup function for custom resource."""
        def cleanup():
            try:
                self._cleanup_func()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error cleaning up custom resource {self.resource_id}: {e}")
        
        return cleanup
    
    def get_description(self) -> str:
        """Get description of custom resource."""
        return self._description


class ResourceRegistry:
    """Registry for managing different types of resources."""
    
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager
        self.logger = logging.getLogger(__name__)
        self._registered_interfaces: Dict[str, ResourceInterface] = {}
        self._lock = threading.Lock()
    
    def register_database(self, resource_id: str, connection: Any, commit_before_close: bool = True, timeout: Optional[float] = None) -> bool:
        """Register a database connection."""
        interface = DatabaseResource(resource_id, connection, commit_before_close)
        return self._register_interface(interface, timeout)
    
    def register_file(self, resource_id: str, file_handle: TextIO, flush_before_close: bool = True, timeout: Optional[float] = None) -> bool:
        """Register a file handle."""
        interface = FileResource(resource_id, file_handle, flush_before_close)
        return self._register_interface(interface, timeout)
    
    def register_network(self, resource_id: str, connection: Any, close_method: str = 'close', timeout: Optional[float] = None) -> bool:
        """Register a network connection."""
        interface = NetworkResource(resource_id, connection, close_method)
        return self._register_interface(interface, timeout)
    
    def register_custom(self, resource_id: str, cleanup_func: Callable[[], None], description: str = "", timeout: Optional[float] = None) -> bool:
        """Register a custom resource."""
        interface = CustomResource(resource_id, cleanup_func, description)
        return self._register_interface(interface, timeout)
    
    def _register_interface(self, interface: ResourceInterface, timeout: Optional[float] = None) -> bool:
        """Register a resource interface with the resource manager."""
        with self._lock:
            if interface.resource_id in self._registered_interfaces:
                self.logger.warning(f"Resource {interface.resource_id} already registered")
                return False
            
            success = self.resource_manager.register_resource(
                resource_id=interface.resource_id,
                resource_type=interface.resource_type,
                cleanup_func=interface.get_cleanup_function(),
                timeout=timeout,
                description=interface.get_description(),
                metadata=interface.metadata
            )
            
            if success:
                self._registered_interfaces[interface.resource_id] = interface
                interface.is_registered = True
                self.logger.debug(f"Registered {interface.resource_type.value} resource: {interface.resource_id}")
            
            return success
    
    def unregister_resource(self, resource_id: str) -> bool:
        """Unregister a resource."""
        with self._lock:
            if resource_id in self._registered_interfaces:
                del self._registered_interfaces[resource_id]
            
            return self.resource_manager.unregister_resource(resource_id)
    
    def get_interface(self, resource_id: str) -> Optional[ResourceInterface]:
        """Get a registered resource interface."""
        with self._lock:
            return self._registered_interfaces.get(resource_id)
    
    def get_registered_resources(self) -> Dict[str, ResourceInterface]:
        """Get all registered resource interfaces."""
        with self._lock:
            return self._registered_interfaces.copy()
    
    @contextmanager
    def managed_database(self, resource_id: str, connection: Any, commit_before_close: bool = True, timeout: Optional[float] = None):
        """Context manager for database resource management."""
        try:
            self.register_database(resource_id, connection, commit_before_close, timeout)
            yield connection
        finally:
            self.unregister_resource(resource_id)
    
    @contextmanager
    def managed_file(self, resource_id: str, file_handle: TextIO, flush_before_close: bool = True, timeout: Optional[float] = None):
        """Context manager for file resource management."""
        try:
            self.register_file(resource_id, file_handle, flush_before_close, timeout)
            yield file_handle
        finally:
            self.unregister_resource(resource_id)
    
    @contextmanager
    def managed_network(self, resource_id: str, connection: Any, close_method: str = 'close', timeout: Optional[float] = None):
        """Context manager for network resource management."""
        try:
            self.register_network(resource_id, connection, close_method, timeout)
            yield connection
        finally:
            self.unregister_resource(resource_id)
    
    @contextmanager
    def managed_custom(self, resource_id: str, cleanup_func: Callable[[], None], description: str = "", timeout: Optional[float] = None):
        """Context manager for custom resource management."""
        try:
            self.register_custom(resource_id, cleanup_func, description, timeout)
            yield
        finally:
            self.unregister_resource(resource_id)
