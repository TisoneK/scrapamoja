"""
Database-specific cleanup utilities for interrupt handling.
"""

import sqlite3
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager

from .resource_interfaces import DatabaseResource, ResourceRegistry


class DatabaseCleanupManager:
    """Specialized manager for database cleanup operations."""
    
    def __init__(self, resource_registry: ResourceRegistry):
        self.resource_registry = resource_registry
        self.logger = logging.getLogger(__name__)
        self._cleanup_stats = {
            'total_cleanups': 0,
            'successful_cleanups': 0,
            'failed_cleanups': 0,
            'timeout_cleanups': 0
        }
        self._lock = threading.Lock()
    
    def register_sqlite_connection(self, resource_id: str, connection: sqlite3.Connection, 
                                  commit_before_close: bool = True, timeout: float = 10.0) -> bool:
        """Register a SQLite connection for cleanup."""
        try:
            # Test connection health
            if not self._is_sqlite_connection_healthy(connection):
                self.logger.warning(f"SQLite connection {resource_id} appears unhealthy")
                return False
            
            # Register with resource registry
            success = self.resource_registry.register_database(
                resource_id=resource_id,
                connection=connection,
                commit_before_close=commit_before_close,
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered SQLite connection: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('connection_type', 'sqlite')
                    interface.set_metadata('registered_at', time.time())
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering SQLite connection {resource_id}: {e}")
            return False
    
    def register_generic_database(self, resource_id: str, connection: Any, 
                                 commit_before_close: bool = True, timeout: float = 10.0) -> bool:
        """Register a generic database connection for cleanup."""
        try:
            # Test basic connection health
            if not self._is_generic_connection_healthy(connection):
                self.logger.warning(f"Database connection {resource_id} appears unhealthy")
                return False
            
            # Register with resource registry
            success = self.resource_registry.register_database(
                resource_id=resource_id,
                connection=connection,
                commit_before_close=commit_before_close,
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered generic database connection: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('connection_type', 'generic')
                    interface.set_metadata('registered_at', time.time())
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering database connection {resource_id}: {e}")
            return False
    
    def _is_sqlite_connection_healthy(self, connection: sqlite3.Connection) -> bool:
        """Check if SQLite connection is healthy."""
        try:
            # Simple health check - try to execute a simple query
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception as e:
            self.logger.debug(f"SQLite health check failed: {e}")
            return False
    
    def _is_generic_connection_healthy(self, connection: Any) -> bool:
        """Check if generic database connection is healthy."""
        try:
            # Try common health check methods
            if hasattr(connection, 'ping'):
                return connection.ping()
            elif hasattr(connection, 'is_connected'):
                return connection.is_connected()
            elif hasattr(connection, 'connection') and hasattr(connection.connection, 'is_connected'):
                return connection.connection.is_connected()
            else:
                # If no health check method available, assume healthy
                return True
        except Exception as e:
            self.logger.debug(f"Generic database health check failed: {e}")
            return False
    
    def cleanup_database_connection(self, resource_id: str) -> bool:
        """Clean up a specific database connection."""
        try:
            interface = self.resource_registry.get_interface(resource_id)
            if not interface or not isinstance(interface, DatabaseResource):
                self.logger.warning(f"Database resource {resource_id} not found")
                return False
            
            self.logger.debug(f"Cleaning up database connection: {resource_id}")
            
            # Execute cleanup
            cleanup_func = interface.get_cleanup_function()
            cleanup_func()
            
            # Update statistics
            with self._lock:
                self._cleanup_stats['total_cleanups'] += 1
                self._cleanup_stats['successful_cleanups'] += 1
            
            self.logger.debug(f"Successfully cleaned up database connection: {resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up database connection {resource_id}: {e}")
            
            # Update statistics
            with self._lock:
                self._cleanup_stats['total_cleanups'] += 1
                self._cleanup_stats['failed_cleanups'] += 1
            
            return False
    
    def cleanup_all_databases(self) -> Dict[str, bool]:
        """Clean up all registered database connections."""
        results = {}
        database_resources = {}
        
        # Find all database resources
        for resource_id, interface in self.resource_registry.get_registered_resources().items():
            if isinstance(interface, DatabaseResource):
                database_resources[resource_id] = interface
        
        self.logger.info(f"Cleaning up {len(database_resources)} database connections")
        
        # Clean up each database connection
        for resource_id in database_resources:
            results[resource_id] = self.cleanup_database_connection(resource_id)
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Database cleanup completed: {successful_count}/{len(results)} successful")
        
        return results
    
    def force_cleanup_database(self, resource_id: str, timeout: float = 5.0) -> bool:
        """Force cleanup of a database connection with timeout."""
        import threading
        
        interface = self.resource_registry.get_interface(resource_id)
        if not interface or not isinstance(interface, DatabaseResource):
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
            self.logger.error(f"Force cleanup timeout for database {resource_id}")
            with self._lock:
                self._cleanup_stats['timeout_cleanups'] += 1
            return False
        
        if cleanup_result['success']:
            self.logger.debug(f"Force cleanup successful for database {resource_id}")
            return True
        else:
            self.logger.error(f"Force cleanup failed for database {resource_id}: {cleanup_result['error']}")
            return False
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get status of all registered database connections."""
        database_resources = {}
        
        for resource_id, interface in self.resource_registry.get_registered_resources().items():
            if isinstance(interface, DatabaseResource):
                database_resources[resource_id] = {
                    'connection_type': interface.get_metadata('connection_type', 'unknown'),
                    'registered_at': interface.get_metadata('registered_at'),
                    'description': interface.get_description()
                }
        
        with self._lock:
            stats = self._cleanup_stats.copy()
        
        return {
            'database_count': len(database_resources),
            'databases': database_resources,
            'cleanup_stats': stats
        }
    
    @contextmanager
    def managed_sqlite_connection(self, resource_id: str, database_path: str, 
                               commit_before_close: bool = True, timeout: float = 10.0):
        """Context manager for SQLite connection management."""
        connection = None
        try:
            connection = sqlite3.connect(database_path)
            self.register_sqlite_connection(resource_id, connection, commit_before_close, timeout)
            yield connection
        finally:
            if connection:
                self.cleanup_database_connection(resource_id)
    
    @contextmanager
    def managed_database_connection(self, resource_id: str, connection: Any,
                                 commit_before_close: bool = True, timeout: float = 10.0):
        """Context manager for generic database connection management."""
        try:
            self.register_generic_database(resource_id, connection, commit_before_close, timeout)
            yield connection
        finally:
            self.cleanup_database_connection(resource_id)
    
    def create_transactional_cleanup(self, resource_id: str, connection: Any) -> Callable[[], None]:
        """Create a cleanup function that handles transactions properly."""
        def cleanup():
            try:
                # Check if we're in a transaction
                if hasattr(connection, 'in_transaction') and connection.in_transaction:
                    # Rollback the transaction to maintain data consistency
                    if hasattr(connection, 'rollback'):
                        connection.rollback()
                        self.logger.debug(f"Rolled back transaction for {resource_id}")
                elif hasattr(connection, 'commit'):
                    # Commit any pending changes
                    connection.commit()
                    self.logger.debug(f"Committed changes for {resource_id}")
                
                # Close the connection
                if hasattr(connection, 'close'):
                    connection.close()
                    self.logger.debug(f"Closed connection for {resource_id}")
                    
            except Exception as e:
                self.logger.error(f"Error in transactional cleanup for {resource_id}: {e}")
        
        return cleanup
    
    def register_transactional_database(self, resource_id: str, connection: Any, timeout: float = 10.0) -> bool:
        """Register a database connection with transactional cleanup."""
        try:
            cleanup_func = self.create_transactional_cleanup(resource_id, connection)
            
            success = self.resource_manager.register_resource(
                resource_id=resource_id,
                resource_type=ResourceType.DATABASE,
                cleanup_func=cleanup_func,
                timeout=timeout,
                description=f"Transactional database connection - {resource_id}"
            )
            
            if success:
                self.logger.debug(f"Registered transactional database: {resource_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering transactional database {resource_id}: {e}")
            return False
