"""
Network-specific cleanup utilities for interrupt handling.
"""

import socket
import threading
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager

from .resource_interfaces import NetworkResource, ResourceRegistry


class NetworkCleanupManager:
    """Specialized manager for network cleanup operations."""
    
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
    
    def register_socket(self, resource_id: str, sock: socket.socket, timeout: float = 5.0) -> bool:
        """Register a socket for cleanup."""
        try:
            # Check if socket is valid
            if not self._is_socket_valid(sock):
                self.logger.warning(f"Socket {resource_id} is not valid")
                return False
            
            # Register with resource registry
            success = self.resource_registry.register_network(
                resource_id=resource_id,
                connection=sock,
                close_method='close',
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered socket: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('connection_type', 'socket')
                    interface.set_metadata('socket_family', str(sock.family))
                    interface.set_metadata('socket_type', str(sock.type))
                    interface.set_metadata('registered_at', time.time())
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering socket {resource_id}: {e}")
            return False
    
    def register_http_connection(self, resource_id: str, connection: Any, 
                               close_method: str = 'close', timeout: float = 5.0) -> bool:
        """Register an HTTP connection for cleanup."""
        try:
            # Check if connection is valid
            if not self._is_connection_valid(connection):
                self.logger.warning(f"HTTP connection {resource_id} is not valid")
                return False
            
            # Register with resource registry
            success = self.resource_registry.register_network(
                resource_id=resource_id,
                connection=connection,
                close_method=close_method,
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered HTTP connection: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('connection_type', 'http')
                    interface.set_metadata('close_method', close_method)
                    interface.set_metadata('registered_at', time.time())
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering HTTP connection {resource_id}: {e}")
            return False
    
    def register_generic_connection(self, resource_id: str, connection: Any, 
                                 close_method: str = 'close', timeout: float = 5.0) -> bool:
        """Register a generic network connection for cleanup."""
        try:
            # Check if connection is valid
            if not self._is_connection_valid(connection):
                self.logger.warning(f"Network connection {resource_id} is not valid")
                return False
            
            # Register with resource registry
            success = self.resource_registry.register_network(
                resource_id=resource_id,
                connection=connection,
                close_method=close_method,
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered generic network connection: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('connection_type', 'generic')
                    interface.set_metadata('close_method', close_method)
                    interface.set_metadata('registered_at', time.time())
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering generic network connection {resource_id}: {e}")
            return False
    
    def _is_socket_valid(self, sock: socket.socket) -> bool:
        """Check if socket is valid and connected."""
        try:
            return (sock is not None and 
                   hasattr(sock, 'close') and
                   not getattr(sock, '_closed', False))
        except Exception:
            return False
    
    def _is_connection_valid(self, connection: Any) -> bool:
        """Check if network connection is valid."""
        try:
            # Check for common connection attributes
            if hasattr(connection, 'close'):
                return True
            elif hasattr(connection, 'shutdown'):
                return True
            elif hasattr(connection, 'disconnect'):
                return True
            else:
                return False
        except Exception:
            return False
    
    def cleanup_network_connection(self, resource_id: str) -> bool:
        """Clean up a specific network connection."""
        try:
            interface = self.resource_registry.get_interface(resource_id)
            if not interface or not isinstance(interface, NetworkResource):
                self.logger.warning(f"Network resource {resource_id} not found")
                return False
            
            self.logger.debug(f"Cleaning up network connection: {resource_id}")
            
            # Execute cleanup
            cleanup_func = interface.get_cleanup_function()
            cleanup_func()
            
            # Update statistics
            with self._lock:
                self._cleanup_stats['total_cleanups'] += 1
                self._cleanup_stats['successful_cleanups'] += 1
            
            self.logger.debug(f"Successfully cleaned up network connection: {resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up network connection {resource_id}: {e}")
            
            # Update statistics
            with self._lock:
                self._cleanup_stats['total_cleanups'] += 1
                self._cleanup_stats['failed_cleanups'] += 1
            
            return False
    
    def cleanup_all_network_connections(self) -> Dict[str, bool]:
        """Clean up all registered network connections."""
        results = {}
        network_resources = {}
        
        # Find all network resources
        for resource_id, interface in self.resource_registry.get_registered_resources().items():
            if isinstance(interface, NetworkResource):
                network_resources[resource_id] = interface
        
        self.logger.info(f"Cleaning up {len(network_resources)} network connections")
        
        # Clean up each network connection
        for resource_id in network_resources:
            results[resource_id] = self.cleanup_network_connection(resource_id)
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Network cleanup completed: {successful_count}/{len(results)} successful")
        
        return results
    
    def force_cleanup_network(self, resource_id: str, timeout: float = 3.0) -> bool:
        """Force cleanup of a network connection with timeout."""
        import threading
        
        interface = self.resource_registry.get_interface(resource_id)
        if not interface or not isinstance(interface, NetworkResource):
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
            self.logger.error(f"Force cleanup timeout for network {resource_id}")
            with self._lock:
                self._cleanup_stats['timeout_cleanups'] += 1
            return False
        
        if cleanup_result['success']:
            self.logger.debug(f"Force cleanup successful for network {resource_id}")
            return True
        else:
            self.logger.error(f"Force cleanup failed for network {resource_id}: {cleanup_result['error']}")
            return False
    
    def create_graceful_socket_shutdown(self, resource_id: str, sock: socket.socket) -> Callable[[], None]:
        """Create a graceful socket shutdown function."""
        def graceful_shutdown():
            try:
                # Try graceful shutdown first
                if hasattr(sock, 'shutdown'):
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        # Socket might already be closed
                        pass
                
                # Then close the socket
                if hasattr(sock, 'close'):
                    sock.close()
                
                self.logger.debug(f"Gracefully shutdown socket: {resource_id}")
                
            except Exception as e:
                self.logger.error(f"Error in graceful socket shutdown {resource_id}: {e}")
        
        return graceful_shutdown
    
    def register_graceful_socket(self, resource_id: str, sock: socket.socket, timeout: float = 5.0) -> bool:
        """Register a socket with graceful shutdown."""
        try:
            if not self._is_socket_valid(sock):
                return False
            
            # Create graceful shutdown function
            cleanup_func = self.create_graceful_socket_shutdown(resource_id, sock)
            
            # Register with resource registry
            success = self.resource_registry.register_resource(
                resource_id=resource_id,
                resource_type=ResourceType.NETWORK,
                cleanup_func=cleanup_func,
                timeout=timeout,
                description=f"Graceful socket shutdown - {resource_id}"
            )
            
            if success:
                self.logger.debug(f"Registered graceful socket: {resource_id}")
                # Add metadata
                interface = self.resource_registry.get_interface(resource_id)
                if interface:
                    interface.set_metadata('connection_type', 'socket_graceful')
                    interface.set_metadata('socket_family', str(sock.family))
                    interface.set_metadata('socket_type', str(sock.type))
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering graceful socket {resource_id}: {e}")
            return False
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get status of all registered network connections."""
        network_resources = {}
        
        for resource_id, interface in self.resource_registry.get_registered_resources().items():
            if isinstance(interface, NetworkResource):
                network_resources[resource_id] = {
                    'connection_type': interface.get_metadata('connection_type', 'unknown'),
                    'close_method': interface.get_metadata('close_method', 'close'),
                    'registered_at': interface.get_metadata('registered_at'),
                    'description': interface.get_description()
                }
        
        with self._lock:
            stats = self._cleanup_stats.copy()
        
        return {
            'connection_count': len(network_resources),
            'connections': network_resources,
            'cleanup_stats': stats
        }
    
    @contextmanager
    def managed_socket(self, resource_id: str, family: int = socket.AF_INET, 
                     socktype: int = socket.SOCK_STREAM, timeout: float = 5.0):
        """Context manager for socket management."""
        sock = None
        try:
            sock = socket.socket(family, socktype)
            self.register_socket(resource_id, sock, timeout)
            yield sock
        finally:
            if sock:
                self.cleanup_network_connection(resource_id)
    
    @contextmanager
    def managed_connection(self, resource_id: str, connection: Any, 
                         close_method: str = 'close', timeout: float = 5.0):
        """Context manager for generic network connection management."""
        try:
            self.register_generic_connection(resource_id, connection, close_method, timeout)
            yield connection
        finally:
            self.cleanup_network_connection(resource_id)
    
    def create_connection_pool_cleanup(self, pool_id: str, connection_pool: Any) -> Callable[[], None]:
        """Create cleanup function for connection pools."""
        def cleanup_pool():
            try:
                # Try different pool cleanup methods
                if hasattr(connection_pool, 'close_all'):
                    connection_pool.close_all()
                elif hasattr(connection_pool, 'close'):
                    connection_pool.close()
                elif hasattr(connection_pool, 'shutdown'):
                    connection_pool.shutdown()
                elif hasattr(connection_pool, 'disconnect_all'):
                    connection_pool.disconnect_all()
                else:
                    self.logger.warning(f"No known cleanup method for pool {pool_id}")
                
                self.logger.debug(f"Cleaned up connection pool: {pool_id}")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up connection pool {pool_id}: {e}")
        
        return cleanup_pool
    
    def register_connection_pool(self, pool_id: str, connection_pool: Any, timeout: float = 10.0) -> bool:
        """Register a connection pool for cleanup."""
        try:
            cleanup_func = self.create_connection_pool_cleanup(pool_id, connection_pool)
            
            success = self.resource_registry.register_custom(
                resource_id=pool_id,
                cleanup_func=cleanup_func,
                description=f"Connection pool cleanup - {pool_id}",
                timeout=timeout
            )
            
            if success:
                self.logger.debug(f"Registered connection pool: {pool_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error registering connection pool {pool_id}: {e}")
            return False
