"""
Resource manager for coordinating cleanup during interrupts.
"""

import threading
import logging
import time
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

from .config import InterruptConfig


class ResourceType(Enum):
    """Types of resources that can be managed."""
    DATABASE = "database"
    FILE = "file"
    NETWORK = "network"
    CUSTOM = "custom"


@dataclass
class ResourceCleanupTask:
    """A cleanup task for a specific resource."""
    resource_id: str
    resource_type: ResourceType
    cleanup_func: Callable[[], None]
    timeout: float = 10.0
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceManager:
    """Manages resource registration and cleanup during interrupts."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Resource registration
        self._resources: Dict[str, ResourceCleanupTask] = {}
        self._registration_lock = threading.RLock()
        
        # Cleanup state
        self._cleanup_in_progress = False
        self._cleanup_results: Dict[str, bool] = {}
        
        # Statistics
        self._registration_count = 0
        self._cleanup_count = 0
    
    def register_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        cleanup_func: Callable[[], None],
        timeout: Optional[float] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a resource for cleanup.
        
        Args:
            resource_id: Unique identifier for the resource
            resource_type: Type of resource
            cleanup_func: Function to call for cleanup
            timeout: Timeout for cleanup (uses config default if None)
            description: Human-readable description
            metadata: Additional metadata
            
        Returns:
            True if registration successful, False if resource already exists
        """
        with self._registration_lock:
            if resource_id in self._resources:
                self.logger.warning(f"Resource {resource_id} already registered")
                return False
            
            if timeout is None:
                # Use type-specific timeout from config
                timeout = self.config.cleanup_timeout
            
            task = ResourceCleanupTask(
                resource_id=resource_id,
                resource_type=resource_type,
                cleanup_func=cleanup_func,
                timeout=timeout,
                description=description,
                metadata=metadata or {}
            )
            
            self._resources[resource_id] = task
            self._registration_count += 1
            
            self.logger.debug(f"Registered resource {resource_id} of type {resource_type.value}")
            return True
    
    def unregister_resource(self, resource_id: str) -> bool:
        """
        Unregister a resource.
        
        Args:
            resource_id: ID of resource to unregister
            
        Returns:
            True if unregistration successful, False if resource not found
        """
        with self._registration_lock:
            if resource_id not in self._resources:
                self.logger.warning(f"Resource {resource_id} not found for unregistration")
                return False
            
            del self._resources[resource_id]
            self.logger.debug(f"Unregistered resource {resource_id}")
            return True
    
    def cleanup_all(self) -> Dict[str, bool]:
        """
        Clean up all registered resources.
        
        Returns:
            Dictionary mapping resource IDs to cleanup success status
        """
        with self._registration_lock:
            if self._cleanup_in_progress:
                self.logger.warning("Cleanup already in progress")
                return self._cleanup_results
            
            self._cleanup_in_progress = True
            self._cleanup_results = {}
            
            self.logger.info(f"Starting cleanup of {len(self._resources)} resources")
            
            try:
                # Sort resources by priority
                sorted_resources = self._get_resources_by_priority()
                
                for resource in sorted_resources:
                    success = self._cleanup_resource(resource)
                    self._cleanup_results[resource.resource_id] = success
                    
                    if success:
                        self._cleanup_count += 1
                
                self.logger.info(f"Cleanup completed: {self._cleanup_count}/{len(sorted_resources)} successful")
                
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
            finally:
                self._cleanup_in_progress = False
            
            return self._cleanup_results.copy()
    
    def cleanup_resource(self, resource_id: str) -> bool:
        """
        Clean up a specific resource.
        
        Args:
            resource_id: ID of resource to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        with self._registration_lock:
            if resource_id not in self._resources:
                self.logger.warning(f"Resource {resource_id} not found for cleanup")
                return False
            
            resource = self._resources[resource_id]
            return self._cleanup_resource(resource)
    
    def _cleanup_resource(self, resource: ResourceCleanupTask) -> bool:
        """
        Clean up a single resource with timeout.
        
        Args:
            resource: Resource cleanup task
            
        Returns:
            True if cleanup successful, False otherwise
        """
        self.logger.debug(f"Cleaning up resource {resource.resource_id} ({resource.resource_type.value})")
        
        try:
            # Execute cleanup with timeout
            cleanup_thread = threading.Thread(
                target=resource.cleanup_func,
                name=f"cleanup-{resource.resource_id}",
                daemon=True
            )
            cleanup_thread.start()
            cleanup_thread.join(timeout=resource.timeout)
            
            if cleanup_thread.is_alive():
                self.logger.error(f"Cleanup timeout for resource {resource.resource_id}")
                return False
            
            self.logger.debug(f"Successfully cleaned up resource {resource.resource_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up resource {resource.resource_id}: {e}")
            return False
    
    def _get_resources_by_priority(self) -> List[ResourceCleanupTask]:
        """
        Get resources sorted by cleanup priority.
        
        Returns:
            List of resources sorted by priority (lower number = higher priority)
        """
        resources = list(self._resources.values())
        
        def get_priority(resource: ResourceCleanupTask) -> int:
            return self.config.cleanup_priorities.get(
                resource.resource_type.value, 
                999  # High priority number for unknown types
            )
        
        return sorted(resources, key=get_priority)
    
    def get_registered_resources(self) -> Dict[str, ResourceCleanupTask]:
        """Get a copy of all registered resources."""
        with self._registration_lock:
            return self._resources.copy()
    
    def get_resource_count(self) -> int:
        """Get the number of registered resources."""
        with self._registration_lock:
            return len(self._resources)
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get cleanup status and statistics."""
        with self._registration_lock:
            return {
                'registered_resources': len(self._resources),
                'cleanup_in_progress': self._cleanup_in_progress,
                'total_registrations': self._registration_count,
                'total_cleanups': self._cleanup_count,
                'last_cleanup_results': self._cleanup_results.copy()
            }
    
    @contextmanager
    def managed_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        cleanup_func: Callable[[], None],
        timeout: Optional[float] = None,
        description: str = ""
    ):
        """
        Context manager for automatic resource registration and cleanup.
        
        Args:
            resource_id: Unique identifier for the resource
            resource_type: Type of resource
            cleanup_func: Function to call for cleanup
            timeout: Timeout for cleanup
            description: Human-readable description
        """
        # Register resource
        self.register_resource(
            resource_id=resource_id,
            resource_type=resource_type,
            cleanup_func=cleanup_func,
            timeout=timeout,
            description=description
        )
        
        try:
            yield
        finally:
            # Unregister resource
            self.unregister_resource(resource_id)
