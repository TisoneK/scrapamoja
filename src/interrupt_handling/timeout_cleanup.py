"""
Timeout-based cleanup utilities for forced termination.
"""

import threading
import time
import logging
import signal
import os
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager
from enum import Enum

from .resource_manager import ResourceType


class CleanupTimeoutStrategy(Enum):
    """Strategies for handling cleanup timeouts."""
    IGNORE = "ignore"           # Continue with other cleanups
    FORCE_TERMINATE = "force"   # Force terminate the resource
    ESCALATE = "escalate"       # Escalate to more aggressive methods


class TimeoutCleanupManager:
    """Manages timeout-based cleanup operations."""
    
    def __init__(self, default_timeout: float = 10.0):
        self.default_timeout = default_timeout
        self.logger = logging.getLogger(__name__)
        self._cleanup_stats = {
            'total_timeouts': 0,
            'forced_terminations': 0,
            'escalations': 0,
            'successful_forced_cleanups': 0
        }
        self._lock = threading.Lock()
        self._active_cleanups: Dict[str, threading.Thread] = {}
    
    def cleanup_with_timeout(self, resource_id: str, cleanup_func: Callable[[], None], 
                           timeout: Optional[float] = None, 
                           strategy: CleanupTimeoutStrategy = CleanupTimeoutStrategy.FORCE_TERMINATE) -> bool:
        """
        Execute cleanup function with timeout protection.
        
        Args:
            resource_id: Identifier for the resource
            cleanup_func: Cleanup function to execute
            timeout: Timeout in seconds (uses default if None)
            strategy: Strategy for handling timeouts
            
        Returns:
            True if cleanup successful, False otherwise
        """
        if timeout is None:
            timeout = self.default_timeout
        
        cleanup_result = {'success': False, 'error': None, 'timed_out': False}
        
        def cleanup_thread():
            try:
                cleanup_func()
                cleanup_result['success'] = True
            except Exception as e:
                cleanup_result['error'] = e
        
        # Start cleanup thread
        thread = threading.Thread(
            target=cleanup_thread,
            name=f"cleanup-{resource_id}",
            daemon=True
        )
        
        with self._lock:
            self._active_cleanups[resource_id] = thread
        
        thread.start()
        thread.join(timeout=timeout)
        
        with self._lock:
            if resource_id in self._active_cleanups:
                del self._active_cleanups[resource_id]
        
        if thread.is_alive():
            # Cleanup timed out
            cleanup_result['timed_out'] = True
            self.logger.warning(f"Cleanup timeout for resource {resource_id} after {timeout}s")
            
            with self._lock:
                self._cleanup_stats['total_timeouts'] += 1
            
            # Handle timeout based on strategy
            return self._handle_timeout(resource_id, strategy, timeout)
        
        if cleanup_result['success']:
            self.logger.debug(f"Cleanup successful for resource {resource_id}")
            return True
        else:
            self.logger.error(f"Cleanup failed for resource {resource_id}: {cleanup_result['error']}")
            return False
    
    def _handle_timeout(self, resource_id: str, strategy: CleanupTimeoutStrategy, timeout: float) -> bool:
        """Handle cleanup timeout based on strategy."""
        if strategy == CleanupTimeoutStrategy.IGNORE:
            self.logger.info(f"Ignoring timeout for resource {resource_id}")
            return False
        
        elif strategy == CleanupTimeoutStrategy.FORCE_TERMINATE:
            return self._force_terminate_resource(resource_id, timeout)
        
        elif strategy == CleanupTimeoutStrategy.ESCALATE:
            return self._escalate_cleanup(resource_id, timeout)
        
        else:
            self.logger.error(f"Unknown timeout strategy: {strategy}")
            return False
    
    def _force_terminate_resource(self, resource_id: str, timeout: float) -> bool:
        """Force terminate a resource using aggressive methods."""
        self.logger.info(f"Attempting force termination for resource {resource_id}")
        
        try:
            # Try to find and terminate the cleanup thread
            # Note: Python doesn't provide direct thread termination, so we use other methods
            
            # Method 1: Try to interrupt the thread if it's waiting on I/O
            # This is platform-specific and may not always work
            
            # Method 2: Use signal to interrupt (Unix-like systems only)
            if hasattr(os, 'kill'):
                try:
                    # Send interrupt signal to current process group
                    # This may interrupt the cleanup thread
                    os.kill(os.getpid(), signal.SIGUSR1)
                    time.sleep(0.1)  # Give it time to process
                except (OSError, PermissionError):
                    pass
            
            # Method 3: Log the issue and mark as forced termination
            with self._lock:
                self._cleanup_stats['forced_terminations'] += 1
            
            self.logger.warning(f"Force termination attempted for resource {resource_id}")
            return False  # Force termination is not guaranteed to succeed
            
        except Exception as e:
            self.logger.error(f"Error during force termination of {resource_id}: {e}")
            return False
    
    def _escalate_cleanup(self, resource_id: str, timeout: float) -> bool:
        """Escalate cleanup using more aggressive methods."""
        self.logger.info(f"Escalating cleanup for resource {resource_id}")
        
        try:
            # Try multiple escalation strategies
            
            # Strategy 1: Wait a bit longer
            time.sleep(min(timeout, 5.0))
            
            # Strategy 2: Try to find and interrupt the thread
            with self._lock:
                if resource_id in self._active_cleanups:
                    thread = self._active_cleanups[resource_id]
                    if thread.is_alive():
                        self.logger.debug(f"Thread for {resource_id} still alive after escalation")
            
            # Strategy 3: Log escalation
            with self._lock:
                self._cleanup_stats['escalations'] += 1
            
            self.logger.warning(f"Cleanup escalation completed for resource {resource_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error during cleanup escalation of {resource_id}: {e}")
            return False
    
    def batch_cleanup_with_timeout(self, cleanup_tasks: List[Dict[str, Any]], 
                                 overall_timeout: Optional[float] = None) -> Dict[str, bool]:
        """
        Execute multiple cleanup tasks with timeout protection.
        
        Args:
            cleanup_tasks: List of cleanup task dictionaries with keys:
                          - resource_id: str
                          - cleanup_func: Callable[[], None]
                          - timeout: Optional[float]
                          - strategy: Optional[CleanupTimeoutStrategy]
            overall_timeout: Overall timeout for all cleanups
            
        Returns:
            Dictionary mapping resource IDs to cleanup success status
        """
        if overall_timeout is None:
            overall_timeout = self.default_timeout * 2  # Allow more time for batch
        
        results = {}
        start_time = time.time()
        
        self.logger.info(f"Starting batch cleanup of {len(cleanup_tasks)} resources")
        
        # Execute cleanups concurrently with individual timeouts
        cleanup_threads = {}
        
        for task in cleanup_tasks:
            resource_id = task['resource_id']
            cleanup_func = task['cleanup_func']
            timeout = task.get('timeout', self.default_timeout)
            strategy = task.get('strategy', CleanupTimeoutStrategy.FORCE_TERMINATE)
            
            # Create thread for this cleanup
            result_container = {'success': False}
            
            def cleanup_wrapper():
                result_container['success'] = self.cleanup_with_timeout(
                    resource_id, cleanup_func, timeout, strategy
                )
            
            thread = threading.Thread(
                target=cleanup_wrapper,
                name=f"batch-cleanup-{resource_id}",
                daemon=True
            )
            
            cleanup_threads[resource_id] = (thread, result_container)
            thread.start()
        
        # Wait for all cleanups or overall timeout
        for resource_id, (thread, result_container) in cleanup_threads.items():
            remaining_time = overall_timeout - (time.time() - start_time)
            
            if remaining_time <= 0:
                self.logger.warning(f"Overall timeout reached, stopping batch cleanup")
                break
            
            thread.join(timeout=min(remaining_time, self.default_timeout))
            
            if thread.is_alive():
                self.logger.warning(f"Batch cleanup timeout for resource {resource_id}")
                results[resource_id] = False
            else:
                results[resource_id] = result_container['success']
        
        # Count successful cleanups
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Batch cleanup completed: {successful_count}/{len(results)} successful")
        
        return results
    
    def create_timeout_aware_cleanup(self, resource_id: str, cleanup_func: Callable[[], None], 
                                   timeout: float, strategy: CleanupTimeoutStrategy = CleanupTimeoutStrategy.FORCE_TERMINATE) -> Callable[[], None]:
        """Create a timeout-aware cleanup function."""
        def timeout_aware_cleanup():
            return self.cleanup_with_timeout(resource_id, cleanup_func, timeout, strategy)
        
        return timeout_aware_cleanup
    
    def get_active_cleanups(self) -> List[str]:
        """Get list of currently active cleanup operations."""
        with self._lock:
            return list(self._active_cleanups.keys())
    
    def cancel_cleanup(self, resource_id: str) -> bool:
        """Attempt to cancel a cleanup operation."""
        with self._lock:
            if resource_id in self._active_cleanups:
                thread = self._active_cleanups[resource_id]
                # Note: Python doesn't provide direct thread cancellation
                # This is a placeholder for future implementation
                self.logger.warning(f"Cleanup cancellation requested for {resource_id} (not implemented)")
                return False
            return False
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get cleanup timeout statistics."""
        with self._lock:
            return {
                'active_cleanups': len(self._active_cleanups),
                'active_cleanup_ids': list(self._active_cleanups.keys()),
                'stats': self._cleanup_stats.copy()
            }
    
    @contextmanager
    def timeout_context(self, resource_id: str, timeout: Optional[float] = None):
        """Context manager for timeout-aware operations."""
        if timeout is None:
            timeout = self.default_timeout
        
        start_time = time.time()
        
        try:
            yield timeout
        finally:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                self.logger.warning(f"Operation {resource_id} exceeded timeout: {elapsed:.2f}s > {timeout}s")
    
    def set_default_timeout(self, timeout: float):
        """Set the default timeout for cleanup operations."""
        self.default_timeout = max(timeout, 1.0)  # Minimum 1 second
        self.logger.debug(f"Default timeout set to {self.default_timeout}s")
    
    def reset_statistics(self):
        """Reset cleanup statistics."""
        with self._lock:
            self._cleanup_stats = {
                'total_timeouts': 0,
                'forced_terminations': 0,
                'escalations': 0,
                'successful_forced_cleanups': 0
            }
        self.logger.debug("Cleanup statistics reset")


class ForcedTerminationHandler:
    """Handles forced termination of resources."""
    
    def __init__(self, timeout_manager: TimeoutCleanupManager):
        self.timeout_manager = timeout_manager
        self.logger = logging.getLogger(__name__)
        self._termination_methods = {
            ResourceType.DATABASE: self._terminate_database,
            ResourceType.FILE: self._terminate_file,
            ResourceType.NETWORK: self._terminate_network,
            ResourceType.CUSTOM: self._terminate_custom
        }
    
    def force_terminate_resource(self, resource_type: ResourceType, resource_id: str, resource: Any) -> bool:
        """Force terminate a specific resource."""
        termination_method = self._termination_methods.get(resource_type)
        
        if termination_method:
            return termination_method(resource_id, resource)
        else:
            self.logger.warning(f"No termination method for resource type: {resource_type}")
            return False
    
    def _terminate_database(self, resource_id: str, connection: Any) -> bool:
        """Force terminate a database connection."""
        try:
            # Try different termination methods
            if hasattr(connection, 'close'):
                connection.close()
            elif hasattr(connection, 'disconnect'):
                connection.disconnect()
            elif hasattr(connection, 'shutdown'):
                connection.shutdown()
            
            self.logger.debug(f"Force terminated database connection: {resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error force terminating database {resource_id}: {e}")
            return False
    
    def _terminate_file(self, resource_id: str, file_handle: Any) -> bool:
        """Force terminate a file handle."""
        try:
            if hasattr(file_handle, 'close'):
                file_handle.close()
            
            self.logger.debug(f"Force terminated file handle: {resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error force terminating file {resource_id}: {e}")
            return False
    
    def _terminate_network(self, resource_id: str, connection: Any) -> bool:
        """Force terminate a network connection."""
        try:
            # Try graceful shutdown first
            if hasattr(connection, 'shutdown'):
                try:
                    connection.shutdown()
                except:
                    pass
            
            # Then force close
            if hasattr(connection, 'close'):
                connection.close()
            elif hasattr(connection, 'disconnect'):
                connection.disconnect()
            
            self.logger.debug(f"Force terminated network connection: {resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error force terminating network {resource_id}: {e}")
            return False
    
    def _terminate_custom(self, resource_id: str, resource: Any) -> bool:
        """Force terminate a custom resource."""
        try:
            # Try common termination methods
            for method_name in ['close', 'shutdown', 'stop', 'terminate', 'disconnect']:
                if hasattr(resource, method_name):
                    method = getattr(resource, method_name)
                    try:
                        method()
                        self.logger.debug(f"Force terminated custom resource {resource_id} using {method_name}")
                        return True
                    except:
                        continue
            
            self.logger.warning(f"No termination method found for custom resource: {resource_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error force terminating custom resource {resource_id}: {e}")
            return False
