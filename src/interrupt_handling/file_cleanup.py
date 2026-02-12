"""
File-specific cleanup utilities for interrupt handling.
"""

import os
import tempfile
import threading
import time
import logging
from typing import Any, Dict, List, Optional, Callable, TextIO, BinaryIO
from contextlib import contextmanager

from .resource_interfaces import FileResource, ResourceRegistry


class FileCleanupManager:
    """Specialized manager for file cleanup operations."""
    
    def __init__(self, resource_registry: ResourceRegistry):
        self.resource_registry = resource_registry
        self.logger = logging.getLogger(__name__)
        self._cleanup_stats = {
            'total_cleanups': 0,
            'successful_cleanups': 0,
            'failed_cleanups': 0,
            'forced_cleanups': 0
        }
        self._lock = threading.Lock()
        self._temp_files: Dict[str, str] = {}  # resource_id -> temp_file_path
    
    def register_file_handle(self, resource_id: str, file_handle: Union[TextIO, BinaryIO], 
                           flush_before_close: bool = True, timeout: float = 5.0) -> bool:
        """Register a file handle for cleanup."""
        try:
            # Check if file handle is valid
            if not self._is_file_handle_valid(file_handle):
                self.logger.warning(f"File handle {resource_id} is not valid")
                return False
            
            # Register with resource registry
            success = self.resource_registry.register_file(
                resource_id=resource_id,
                file_handle=file_handle,
                flush_before_close=flush_before_close,
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered file handle: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('file_type', self._get_file_type(file_handle))
                    interface.set_metadata('registered_at', time.time())
                    interface.set_metadata('mode', getattr(file_handle, 'mode', 'unknown'))
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering file handle {resource_id}: {e}")
            return False
    
    def register_temp_file(self, resource_id: str, temp_file_path: str, 
                         cleanup_on_exit: bool = True) -> bool:
        """Register a temporary file for cleanup."""
        try:
            # Verify temp file exists
            if not os.path.exists(temp_file_path):
                self.logger.warning(f"Temporary file {temp_file_path} does not exist")
                return False
            
            # Store temp file reference
            self._temp_files[resource_id] = temp_file_path
            
            # Create cleanup function
            def cleanup_temp_file():
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        self.logger.debug(f"Removed temporary file: {temp_file_path}")
                except Exception as e:
                    self.logger.error(f"Error removing temporary file {temp_file_path}: {e}")
            
            # Register as custom resource
            success = self.resource_registry.register_custom(
                resource_id=resource_id,
                cleanup_func=cleanup_temp_file,
                description=f"Temporary file cleanup - {temp_file_path}"
            )
            
            if success:
                self.logger.debug(f"Registered temporary file: {resource_id} -> {temp_file_path}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering temporary file {resource_id}: {e}")
            return False
    
    def _is_file_handle_valid(self, file_handle: Union[TextIO, BinaryIO]) -> bool:
        """Check if file handle is valid and open."""
        try:
            return (hasattr(file_handle, 'closed') and 
                   not file_handle.closed and
                   hasattr(file_handle, 'close'))
        except Exception:
            return False
    
    def _get_file_type(self, file_handle: Union[TextIO, BinaryIO]) -> str:
        """Determine file type from handle."""
        if hasattr(file_handle, 'mode'):
            mode = file_handle.mode
            if 'b' in mode:
                return 'binary'
            elif 't' in mode or mode is None:
                return 'text'
        
        # Try to determine from class name
        class_name = file_handle.__class__.__name__.lower()
        if 'buffered' in class_name:
            return 'buffered'
        elif 'text' in class_name:
            return 'text'
        elif 'binary' in class_name:
            return 'binary'
        
        return 'unknown'
    
    def cleanup_file_handle(self, resource_id: str) -> bool:
        """Clean up a specific file handle."""
        try:
            interface = self.resource_registry.get_interface(resource_id)
            if not interface or not isinstance(interface, FileResource):
                self.logger.warning(f"File resource {resource_id} not found")
                return False
            
            self.logger.debug(f"Cleaning up file handle: {resource_id}")
            
            # Execute cleanup
            cleanup_func = interface.get_cleanup_function()
            cleanup_func()
            
            # Update statistics
            with self._lock:
                self._cleanup_stats['total_cleanups'] += 1
                self._cleanup_stats['successful_cleanups'] += 1
            
            self.logger.debug(f"Successfully cleaned up file handle: {resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up file handle {resource_id}: {e}")
            
            # Update statistics
            with self._lock:
                self._cleanup_stats['total_cleanups'] += 1
                self._cleanup_stats['failed_cleanups'] += 1
            
            return False
    
    def cleanup_all_files(self) -> Dict[str, bool]:
        """Clean up all registered file handles."""
        results = {}
        file_resources = {}
        
        # Find all file resources
        for resource_id, interface in self.resource_registry.get_registered_resources().items():
            if isinstance(interface, FileResource):
                file_resources[resource_id] = interface
        
        self.logger.info(f"Cleaning up {len(file_resources)} file handles")
        
        # Clean up each file handle
        for resource_id in file_resources:
            results[resource_id] = self.cleanup_file_handle(resource_id)
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(f"File cleanup completed: {successful_count}/{len(results)} successful")
        
        return results
    
    def force_cleanup_file(self, resource_id: str, timeout: float = 3.0) -> bool:
        """Force cleanup of a file handle with timeout."""
        import threading
        
        interface = self.resource_registry.get_interface(resource_id)
        if not interface or not isinstance(interface, FileResource):
            return False
        
        cleanup_result = {'success': False, 'error': None}
        
        def cleanup_thread():
            try:
                cleanup_func = interface.get_cleanup_function()
                cleanup_func()
                cleanup_result['success'] = True
            except Exception as e:
                cleanup_result['error'] = e
        
        thread = threading.Thread(target=cleanup_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            self.logger.error(f"Force cleanup timeout for file {resource_id}")
            with self._lock:
                self._cleanup_stats['forced_cleanups'] += 1
            return False
        
        if cleanup_result['success']:
            self.logger.debug(f"Force cleanup successful for file {resource_id}")
            return True
        else:
            self.logger.error(f"Force cleanup failed for file {resource_id}: {cleanup_result['error']}")
            return False
    
    def create_atomic_file_writer(self, file_path: str) -> 'AtomicFileWriter':
        """Create an atomic file writer for safe data preservation."""
        return AtomicFileWriter(file_path, self)
    
    def get_file_status(self) -> Dict[str, Any]:
        """Get status of all registered file handles."""
        file_resources = {}
        
        for resource_id, interface in self.resource_registry.get_registered_resources().items():
            if isinstance(interface, FileResource):
                file_resources[resource_id] = {
                    'file_type': interface.get_metadata('file_type', 'unknown'),
                    'mode': interface.get_metadata('mode', 'unknown'),
                    'registered_at': interface.get_metadata('registered_at'),
                    'description': interface.get_description()
                }
        
        with self._lock:
            stats = self._cleanup_stats.copy()
        
        return {
            'file_count': len(file_resources),
            'files': file_resources,
            'temp_files': self._temp_files.copy(),
            'cleanup_stats': stats
        }
    
    @contextmanager
    def managed_file_handle(self, resource_id: str, file_path: str, mode: str = 'r', 
                          flush_before_close: bool = True, timeout: float = 5.0):
        """Context manager for file handle management."""
        file_handle = None
        try:
            file_handle = open(file_path, mode)
            self.register_file_handle(resource_id, file_handle, flush_before_close, timeout)
            yield file_handle
        finally:
            if file_handle:
                self.cleanup_file_handle(resource_id)
    
    @contextmanager
    def managed_temp_file(self, resource_id: str, mode: str = 'w+', suffix: str = '', prefix: str = 'tmp'):
        """Context manager for temporary file management."""
        temp_file = None
        temp_path = None
        try:
            temp_file = tempfile.NamedTemporaryFile(mode=mode, suffix=suffix, prefix=prefix, delete=False)
            temp_path = temp_file.name
            self.register_temp_file(resource_id, temp_path)
            yield temp_file
        finally:
            if temp_file:
                try:
                    temp_file.close()
                except:
                    pass
            if temp_path and resource_id in self._temp_files:
                self.cleanup_file_handle(resource_id)


class AtomicFileWriter:
    """Atomic file writer for safe data preservation."""
    
    def __init__(self, file_path: str, cleanup_manager: FileCleanupManager):
        self.file_path = file_path
        self.cleanup_manager = cleanup_manager
        self.temp_path = None
        self.temp_file = None
        self.logger = logging.getLogger(__name__)
        self._resource_id = f"atomic_writer_{int(time.time())}"
    
    def __enter__(self):
        """Enter context and create temporary file."""
        try:
            # Create temporary file in same directory as target
            dir_name = os.path.dirname(self.file_path) or '.'
            self.temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                dir=dir_name,
                delete=False,
                prefix='.tmp_',
                suffix=os.path.basename(self.file_path)
            )
            self.temp_path = self.temp_file.name
            
            # Register temp file for cleanup
            self.cleanup_manager.register_temp_file(self._resource_id, self.temp_path)
            
            self.logger.debug(f"Created atomic file writer: {self.file_path} -> {self.temp_path}")
            return self.temp_file
            
        except Exception as e:
            self.logger.error(f"Error creating atomic file writer: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and atomically move file to target location."""
        try:
            # Close temp file
            if self.temp_file:
                self.temp_file.close()
            
            # If no exception occurred, move temp file to target location
            if exc_type is None:
                try:
                    # Ensure target directory exists
                    os.makedirs(os.path.dirname(self.file_path) or '.', exist_ok=True)
                    
                    # Atomic rename/move
                    os.replace(self.temp_path, self.file_path)
                    self.logger.debug(f"Atomically moved file: {self.temp_path} -> {self.file_path}")
                    
                except Exception as e:
                    self.logger.error(f"Error moving temp file to target: {e}")
                    raise
            else:
                self.logger.warning(f"Exception occurred, not moving temp file: {exc_val}")
            
        finally:
            # Cleanup temp file registration
            self.cleanup_manager.unregister_resource(self._resource_id)
            
            # Remove temp file if it still exists
            if self.temp_path and os.path.exists(self.temp_path):
                try:
                    os.remove(self.temp_path)
                    self.logger.debug(f"Cleaned up temp file: {self.temp_path}")
                except Exception as e:
                    self.logger.error(f"Error removing temp file: {e}")
    
    def write(self, data: str):
        """Write data to the temporary file."""
        if self.temp_file:
            self.temp_file.write(data)
    
    def flush(self):
        """Flush the temporary file."""
        if self.temp_file:
            self.temp_file.flush()
