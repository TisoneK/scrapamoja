"""
Performance optimization utilities for template framework.

This module provides performance optimization features including caching,
lazy loading, and resource management for template operations.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
from functools import wraps, lru_cache
import weakref
import threading
import hashlib
import json

logger = logging.getLogger(__name__)


class PerformanceCache:
    """
    Performance cache for template framework operations.
    
    This class provides intelligent caching for template operations
    with configurable TTL, size limits, and cache invalidation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize performance cache.
        
        Args:
            config: Cache configuration
        """
        self.config = config or {}
        
        # Cache configuration
        self.cache_config = {
            "max_size": self.config.get("max_size", 1000),
            "default_ttl": self.config.get("default_ttl", 300),  # 5 minutes
            "cleanup_interval": self.config.get("cleanup_interval", 60),  # 1 minute
            "enable_stats": self.config.get("enable_stats", True),
            "enable_compression": self.config.get("enable_compression", False)
        }
        
        # Cache storage
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "total_requests": 0
        }
        
        # Cache metadata
        self.cache_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Cleanup timer
        self.cleanup_timer = None
        self._start_cleanup_timer()
        
        logger.info(f"PerformanceCache initialized with max_size={self.cache_config['max_size']}")
    
    def _start_cleanup_timer(self) -> None:
        """Start the cleanup timer."""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
        
        self.cleanup_timer = threading.Timer(
            self.cache_config["cleanup_interval"],
            self._cleanup_expired_entries
        )
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()
    
    def _cleanup_expired_entries(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, metadata in self.cache_metadata.items():
                ttl = metadata.get("ttl", self.cache_config["default_ttl"])
                created_at = metadata.get("created_at", current_time)
                
                if current_time - created_at > timedelta(seconds=ttl):
                    expired_keys.append(key)
            
            # Remove expired entries
            for key in expired_keys:
                if key in self.cache:
                    del self.cache[key]
                if key in self.cache_metadata:
                    del self.cache_metadata[key]
                self.cache_stats["evictions"] += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found
        """
        self.cache_stats["total_requests"] += 1
        
        if key not in self.cache:
            self.cache_stats["misses"] += 1
            return None
        
        # Check if entry is expired
        current_time = datetime.now()
        metadata = self.cache_metadata.get(key, {})
        ttl = metadata.get("ttl", self.cache_config["default_ttl"])
        created_at = metadata.get("created_at", current_time)
        
        if current_time - created_at > timedelta(seconds=ttl):
            # Entry expired
            del self.cache[key]
            del self.cache_metadata[key]
            self.cache_stats["misses"] += 1
            return None
        
        # Update access time
        self.cache_metadata[key]["accessed_at"] = current_time
        self.cache_stats["hits"] += 1
        
        return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        current_time = datetime.now()
        
        # Check cache size limit
        if len(self.cache) >= self.cache_config["max_size"]:
            self._evict_lru()
        
        # Store value and metadata
        self.cache[key] = value
        self.cache_metadata[key] = {
            "created_at": current_time,
            "accessed_at": current_time,
            "ttl": ttl or self.cache_config["default_ttl"],
            "size": self._get_size(value)
        }
        
        self.cache_stats["sets"] += 1
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        try:
            # Find LRU entry
            lru_key = None
            lru_time = datetime.now()
            
            for key, metadata in self.cache_metadata.items():
                accessed_at = metadata.get("accessed_at", datetime.now())
                if accessed_at < lru_time:
                    lru_time = accessed_at
                    lru_key = key
            
            if lru_key:
                del self.cache[lru_key]
                del self.cache_metadata[lru_key]
                self.cache_stats["evictions"] += 1
                logger.debug(f"Evicted LRU cache entry: {lru_key}")
            
        except Exception as e:
            logger.error(f"Error during LRU eviction: {e}")
    
    def _get_size(self, value: Any) -> int:
        """Get approximate size of value."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, dict):
                return len(json.dumps(value).encode('utf-8'))
            elif isinstance(value, list):
                return len(str(value).encode('utf-8'))
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 0
    
    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if entry was deleted
        """
        deleted = False
        
        if key in self.cache:
            del self.cache[key]
            deleted = True
        
        if key in self.cache_metadata:
            del self.cache_metadata[key]
            deleted = True
        
        return deleted
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.cache_metadata.clear()
        self.cache_stats["evictions"] += len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        stats = self.cache_stats.copy()
        
        # Calculate hit rate
        total_requests = stats["total_requests"]
        if total_requests > 0:
            stats["hit_rate"] = stats["hits"] / total_requests
        else:
            stats["hit_rate"] = 0.0
        
        stats["cache_size"] = len(self.cache)
        stats["max_size"] = self.cache_config["max_size"]
        
        return stats
    
    def cleanup(self) -> None:
        """Cleanup cache resources."""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
            self.cleanup_timer = None
        
        self.clear()
        logger.info("PerformanceCache cleaned up")


class LazyLoader:
    """
    Lazy loader for template components.
    
    This class provides lazy loading of template components
    with dependency injection and initialization tracking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize lazy loader.
        
        Args:
            config: Loader configuration
        """
        self.config = config or {}
        
        # Loader configuration
        self.loader_config = {
            "enable_caching": self.config.get("enable_caching", True),
            "cache_ttl": self.config.get("cache_ttl", 300),
            "preload_components": self.config.get("preload_components", []),
            "dependency_injection": self.config.get("dependency_injection", True)
        }
        
        # Component storage
        self.components: Dict[str, Any] = {}
        self.component_factories: Dict[str, Callable] = {}
        self.component_dependencies: Dict[str, List[str]] = {}
        self.initialized_components: set = set()
        
        # Performance tracking
        self.load_times: Dict[str, float] = {}
        self.load_counts: Dict[str, int] = {}
        
        # Cache for loaded components
        self.cache = PerformanceCache(self.loader_config) if self.loader_config["enable_caching"] else None
        
        logger.info("LazyLoader initialized")
    
    def register_factory(self, name: str, factory: Callable, dependencies: Optional[List[str]] = None) -> None:
        """
        Register a component factory.
        
        Args:
            name: Component name
            factory: Factory function
            dependencies: Component dependencies
        """
        self.component_factories[name] = factory
        self.component_dependencies[name] = dependencies or []
        
        logger.debug(f"Registered factory for component: {name}")
    
    async def get_component(self, name: str) -> Any:
        """
        Get component, loading if necessary.
        
        Args:
            name: Component name
            
        Returns:
            Any: Component instance
        """
        # Check cache first
        if self.cache:
            cached_component = self.cache.get(f"component:{name}")
            if cached_component is not None:
                self.load_counts[name] = self.load_counts.get(name, 0) + 1
                return cached_component
        
        # Check if already loaded
        if name in self.components:
            self.load_counts[name] = self.load_counts.get(name, 0) + 1
            return self.components[name]
        
        # Load component
        start_time = time.time()
        
        try:
            # Check dependencies first
            if name in self.component_dependencies:
                dependencies = self.component_dependencies[name]
                for dep_name in dependencies:
                    await self.get_component(dep_name)
            
            # Load component
            if name not in self.component_factories:
                raise ValueError(f"No factory registered for component: {name}")
            
            factory = self.component_factories[name]
            
            # Handle different factory types
            if asyncio.iscoroutinefunction(factory):
                component = await factory()
            else:
                component = factory()
            
            # Store component
            self.components[name] = component
            self.initialized_components.add(name)
            
            # Cache component if enabled
            if self.cache:
                self.cache.set(f"component:{name}", component, self.loader_config["cache_ttl"])
            
            # Track performance
            load_time = time.time() - start_time
            self.load_times[name] = load_time
            self.load_counts[name] = self.load_counts.get(name, 0) + 1
            
            logger.debug(f"Loaded component: {name} (took {load_time:.3f}s)")
            
            return component
            
        except Exception as e:
            logger.error(f"Failed to load component {name}: {e}")
            raise
    
    def is_loaded(self, name: str) -> bool:
        """
        Check if component is loaded.
        
        Args:
            name: Component name
            
        Returns:
            bool: True if loaded
        """
        return name in self.components
    
    def is_initialized(self, name: str) -> bool:
        """
        Check if component is initialized.
        
        Args:
            name: Component name
            
        Returns:
            bool: True if initialized
        """
        return name in self.initialized_components
    
    def unload_component(self, name: str) -> bool:
        """
        Unload a component.
        
        Args:
            name: Component name
            
        Returns:
            bool: True if unloaded
        """
        unloaded = False
        
        if name in self.components:
            # Check if component has cleanup method
            component = self.components[name]
            if hasattr(component, 'cleanup'):
                try:
                    if asyncio.iscoroutinefunction(component.cleanup):
                        asyncio.create_task(component.cleanup())
                    else:
                        component.cleanup()
                except Exception as e:
                    logger.warning(f"Error during component cleanup: {e}")
            
            del self.components[name]
            self.initialized_components.discard(name)
            unloaded = True
        
        # Remove from cache
        if self.cache:
            self.cache.delete(f"component:{name}")
        
        # Remove load tracking
        if name in self.load_times:
            del self.load_times[name]
        if name in self.load_counts:
            del self.load_counts[name]
        
        return unloaded
    
    def get_load_stats(self) -> Dict[str, Any]:
        """
        Get component loading statistics.
        
        Returns:
            Dict[str, Any]: Loading statistics
        """
        stats = {
            "loaded_components": len(self.components),
            "initialized_components": len(self.initialized_components),
            "registered_factories": len(self.component_factories),
            "component_dependencies": self.component_dependencies.copy()
        }
        
        # Add load times
        if self.load_times:
            stats["load_times"] = self.load_times.copy()
            stats["average_load_time"] = sum(self.load_times.values()) / len(self.load_times)
        
        # Add load counts
        if self.load_counts:
            stats["load_counts"] = self.load_counts.copy()
            stats["total_loads"] = sum(self.load_counts.values())
        
        # Add cache stats
        if self.cache:
            cache_stats = self.cache.get_stats()
            stats["cache_stats"] = cache_stats
        
        return stats
    
    def preload_components(self, component_names: List[str]) -> None:
        """
        Preload specified components.
        
        Args:
            component_names: List of component names to preload
        """
        async def _preload():
            for name in component_names:
                try:
                    await self.get_component(name)
                    logger.debug(f"Preloaded component: {name}")
                except Exception as e:
                    logger.error(f"Failed to preload component {name}: {e}")
        
        # Create background task for preloading
        asyncio.create_task(_preload())
        
        logger.info(f"Preloading {len(component_names)} components")


class ResourceManager:
    """
    Resource manager for template framework operations.
    
    This class provides resource management including memory monitoring,
    cleanup scheduling, and resource optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize resource manager.
        
        Args:
            config: Resource manager configuration
        """
        self.config = config or {}
        
        # Resource configuration
        self.resource_config = {
            "memory_threshold": self.config.get("memory_threshold", 0.8),  # 80%
            "cpu_threshold": self.config.get("cpu_threshold", 0.8),  # 80%
            "cleanup_interval": self.config.get("cleanup_interval", 300),  # 5 minutes
            "max_memory_mb": self.config.get("max_memory_mb", 1024),  # 1GB
            "enable_monitoring": self.config.get("enable_monitoring", True),
            "auto_cleanup": self.config.get("auto_cleanup", True)
        }
        
        # Resource tracking
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.resource_limits: Dict[str, Any] = {}
        
        # Monitoring
        self.monitoring_active = False
        self.cleanup_timer = None
        
        # Performance metrics
        self.metrics = {
            "memory_usage": [],
            "cpu_usage": [],
            "cleanup_operations": 0,
            "resource_allocations": 0,
            "resource_deallocations": 0
        }
        
        logger.info("ResourceManager initialized")
    
    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if not self.resource_config["enable_monitoring"]:
            logger.info("Resource monitoring disabled")
            return
        
        self.monitoring_active = True
        self._start_cleanup_timer()
        
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.monitoring_active = False
        
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
            self.cleanup_timer = None
        
        logger.info("Resource monitoring stopped")
    
    def _start_cleanup_timer(self) -> None:
        """Start cleanup timer."""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
        
        self.cleanup_timer = threading.Timer(
            self.resource_config["cleanup_interval"],
            lambda: asyncio.create_task(self._perform_cleanup())
        )
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()
    
    async def _perform_cleanup(self) -> None:
        """Perform resource cleanup."""
        try:
            if not self.resource_config["auto_cleanup"]:
                return
            
            # Check memory usage
            memory_usage = self._get_memory_usage()
            if memory_usage > self.resource_config["memory_threshold"]:
                logger.warning(f"High memory usage detected: {memory_usage:.2%}")
                await self._cleanup_memory()
            
            # Check CPU usage
            cpu_usage = self._get_cpu_usage()
            if cpu_usage > self.resource_config["cpu_threshold"]:
                logger.warning(f"High CPU usage detected: {cpu_usage:.2%}")
                await self._cleanup_cpu()
            
            self.metrics["cleanup_operations"] += 1
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage as percentage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent
        except ImportError:
            logger.debug("psutil not available for memory monitoring")
            return 0.0
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage as percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            logger.debug("psutil not available for CPU monitoring")
            return 0.0
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 0.0
    
    async def _cleanup_memory(self) -> None:
        """Perform memory cleanup."""
        try:
            import gc
            
            # Force garbage collection
            collected = gc.collect()
            
            logger.debug(f"Garbage collection collected {collected} objects")
            
            # Clear caches if available
            if hasattr(self, 'cache'):
                self.cache.clear()
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    async def _cleanup_cpu(self) -> None:
        """Perform CPU cleanup."""
        try:
            # Reduce CPU-intensive operations
            # This would be implemented based on specific needs
            pass
        except Exception as e:
            logger.error(f"Error during CPU cleanup: {e}")
    
    def register_resource(self, name: str, resource: Any, limits: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a resource for monitoring.
        
        Args:
            name: Resource name
            resource: Resource instance
            limits: Resource limits
        """
        self.resources[name] = {
            "resource": resource,
            "limits": limits or {},
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
            "access_count": 0
        }
        
        if limits:
            self.resource_limits[name] = limits
        
        self.metrics["resource_allocations"] += 1
        
        logger.debug(f"Registered resource: {name}")
    
    def unregister_resource(self, name: str) -> bool:
        """
        Unregister a resource.
        
        Args:
            name: Resource name
            
        Returns:
            bool: True if unregistered
        """
        unregistered = False
        
        if name in self.resources:
            del self.resources[name]
            if name in self.resource_limits:
                del self.resource_limits[name]
            
            self.metrics["resource_deallocations"] += 1
            unregistered = True
        
        return unregistered
    
    def get_resource(self, name: str) -> Optional[Any]:
        """
        Get a registered resource.
        
        Args:
            name: Resource name
            
        Returns:
            Optional[Any]: Resource instance or None if not found
        """
        if name not in self.resources:
            return None
        
        resource_info = self.resources[name]
        resource_info["last_accessed"] = datetime.now()
        resource_info["access_count"] += 1
        
        return resource_info["resource"]
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get resource management statistics.
        
        Returns:
            Dict[str, Any]: Resource statistics
        """
        stats = {
            "registered_resources": len(self.resources),
            "resource_limits": self.resource_limits.copy(),
            "monitoring_active": self.monitoring_active,
            "auto_cleanup": self.resource_config["auto_cleanup"],
            "metrics": self.metrics.copy()
        }
        
        # Add current resource usage
        stats["current_memory_usage"] = self._get_memory_usage()
        stats["current_cpu_usage"] = self._get_cpu_usage()
        
        return stats


def performance_monitor(ttl: int = 300):
    """
    Performance monitoring decorator.
    
    Args:
        ttl: Time to live in seconds for caching
    """
    cache = PerformanceCache()
    
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    execution_time = time.time() - start_time
                    
                    # Log performance if slow
                    if execution_time > 1.0:  # 1 second threshold
                        logger.warning(
                            f"Slow operation detected: {func.__name__} took {execution_time:.3f}s"
                        )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(
                        f"Error in {func.__name__} after {execution_time:.3f}s: {e}"
                    )
                    raise
            
            return wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    execution_time = time.time() - start_time
                    
                    # Log performance if slow
                    if execution_time > 1.0:  # 1 second threshold
                        logger.warning(
                            f"Slow operation detected: {func.__name__} took {execution_time:.3f}s"
                        )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(
                        f"Error in {func.__name__} after {execution_time:.3f}s: {e}"
                    )
                    raise
            
            return wrapper
    
    return decorator


def cached_result(ttl: int = 300):
    """
    Cached result decorator.
    
    Args:
        ttl: Time to live in seconds
    """
    cache = _global_cache
    
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # Try to get from cache
                cached_result = cache.get(key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                cache.set(key, result, ttl)
                
                return result
            
            return wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # Try to get from cache
                cached_result = cache.get(key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                cache.set(key, result, ttl)
                
                return result
            
            return wrapper
    
    return decorator


# Global performance cache instance
_global_cache = PerformanceCache()
_global_lazy_loader = LazyLoader()
_global_resource_manager = ResourceManager()


def get_global_cache() -> PerformanceCache:
    """Get global performance cache instance."""
    return _global_cache


def get_global_lazy_loader() -> LazyLoader:
    """Get global lazy loader instance."""
    return _global_lazy_loader


def get_global_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    return _global_resource_manager
