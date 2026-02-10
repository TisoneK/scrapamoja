"""
Component caching optimization system.

This module provides intelligent caching for components to improve performance
by reducing redundant computations, storing frequently used results, and
managing cache lifecycle efficiently.
"""

import asyncio
import time
import json
import hashlib
import threading
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
import weakref
import pickle
import os

from .component_interface import IComponent, ComponentContext, ComponentResult


class CacheStrategy(Enum):
    """Cache strategy enumeration."""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    FIFO = "fifo"                  # First In, First Out
    TTL = "ttl"                    # Time To Live
    ADAPTIVE = "adaptive"           # Adaptive based on usage patterns


class CacheLevel(Enum):
    """Cache level enumeration."""
    MEMORY = "memory"               # In-memory cache
    DISK = "disk"                   # Disk-based cache
    DISTRIBUTED = "distributed"     # Distributed cache (future)
    HYBRID = "hybrid"               # Combination of memory and disk


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds
    
    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Cache statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    average_access_time_ms: float = 0.0
    last_cleanup: Optional[datetime] = None
    
    def update_hit_rate(self):
        """Update hit rate calculation."""
        if self.total_requests > 0:
            self.hit_rate = self.cache_hits / self.total_requests


class MemoryCache:
    """In-memory cache implementation."""
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.strategy = strategy
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            start_time = time.time()
            
            self._stats.total_requests += 1
            
            if key in self._cache:
                entry = self._cache[key]
                
                # Check expiration
                if entry.is_expired():
                    del self._cache[key]
                    self._stats.cache_misses += 1
                    self._stats.update_hit_rate()
                    return None
                
                # Update access based on strategy
                if self.strategy == CacheStrategy.LRU:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                elif self.strategy == CacheStrategy.LFU:
                    # Access count is updated in entry.touch()
                    pass
                
                entry.touch()
                self._stats.cache_hits += 1
                self._stats.update_hit_rate()
                
                # Update access time
                access_time_ms = (time.time() - start_time) * 1000
                self._stats.average_access_time_ms = (
                    (self._stats.average_access_time_ms * (self._stats.total_requests - 1) + access_time_ms) /
                    self._stats.total_requests
                )
                
                return entry.value
            else:
                self._stats.cache_misses += 1
                self._stats.update_hit_rate()
                return None
    
    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Put value into cache."""
        with self._lock:
            try:
                # Calculate size
                size_bytes = len(pickle.dumps(value))
                
                # Create entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    size_bytes=size_bytes,
                    ttl_seconds=ttl_seconds,
                    metadata=metadata or {}
                )
                
                # Check if eviction is needed
                if key not in self._cache and len(self._cache) >= self.max_size:
                    self._evict()
                
                # Add or update entry
                self._cache[key] = entry
                
                # Update statistics
                self._stats.entry_count = len(self._cache)
                self._stats.size_bytes = sum(entry.size_bytes for entry in self._cache.values())
                
                return True
                
            except Exception:
                return False
    
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._stats.entry_count = len(self._cache)
                self._stats.size_bytes -= entry.size_bytes
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._stats.entry_count = 0
            self._stats.size_bytes = 0
    
    def _evict(self):
        """Evict entries based on strategy."""
        if not self._cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            key, entry = self._cache.popitem(last=False)
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            min_access_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            entry = self._cache.pop(min_access_key)
        elif self.strategy == CacheStrategy.FIFO:
            # Remove first in (oldest)
            key, entry = self._cache.popitem(last=False)
        else:
            # Default to LRU
            key, entry = self._cache.popitem(last=False)
        
        self._stats.evictions += 1
        self._stats.size_bytes -= entry.size_bytes
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache statistics."""
        with self._lock:
            stats = CacheStatistics(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                evictions=self._stats.evictions,
                size_bytes=self._stats.size_bytes,
                entry_count=len(self._cache),
                hit_rate=self._stats.hit_rate,
                average_access_time_ms=self._stats.average_access_time_ms,
                last_cleanup=self._stats.last_cleanup
            )
            stats.update_hit_rate()
            return stats
    
    def get_keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache entry."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                return {
                    "key": entry.key,
                    "size_bytes": entry.size_bytes,
                    "created_at": entry.created_at.isoformat(),
                    "last_accessed": entry.last_accessed.isoformat(),
                    "access_count": entry.access_count,
                    "ttl_seconds": entry.ttl_seconds,
                    "is_expired": entry.is_expired(),
                    "metadata": entry.metadata
                }
            return None


class DiskCache:
    """Disk-based cache implementation."""
    
    def __init__(self, cache_dir: str = "component_cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        self._stats = CacheStatistics()
        
        # Load existing cache index
        self._index_file = self.cache_dir / "cache_index.json"
        self._index = self._load_index()
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from disk."""
        try:
            if self._index_file.exists():
                with open(self._index_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_index(self):
        """Save cache index to disk."""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f)
        except Exception:
            pass
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        # Use hash of key as filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        with self._lock:
            start_time = time.time()
            
            self._stats.total_requests += 1
            
            if key not in self._index:
                self._stats.cache_misses += 1
                self._stats.update_hit_rate()
                return None
            
            entry_info = self._index[key]
            cache_file = self._get_cache_file(key)
            
            if not cache_file.exists():
                # Remove from index
                del self._index[key]
                self._save_index()
                self._stats.cache_misses += 1
                self._stats.update_hit_rate()
                return None
            
            # Check expiration
            created_at = datetime.fromisoformat(entry_info['created_at'])
            ttl = entry_info.get('ttl_seconds')
            if ttl and (datetime.utcnow() - created_at).total_seconds() > ttl:
                # Remove expired entry
                cache_file.unlink(missing_ok=True)
                del self._index[key]
                self._save_index()
                self._stats.cache_misses += 1
                self._stats.update_hit_rate()
                return None
            
            try:
                with open(cache_file, 'rb') as f:
                    value = pickle.load(f)
                
                # Update access info
                self._index[key]['last_accessed'] = datetime.utcnow().isoformat()
                self._index[key]['access_count'] = self._index[key].get('access_count', 0) + 1
                self._save_index()
                
                self._stats.cache_hits += 1
                self._stats.update_hit_rate()
                
                # Update access time
                access_time_ms = (time.time() - start_time) * 1000
                self._stats.average_access_time_ms = (
                    (self._stats.average_access_time_ms * (self._stats.total_requests - 1) + access_time_ms) /
                    self._stats.total_requests
                )
                
                return value
                
            except Exception:
                # Remove corrupted entry
                cache_file.unlink(missing_ok=True)
                del self._index[key]
                self._save_index()
                self._stats.cache_misses += 1
                self._stats.update_hit_rate()
                return None
    
    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Put value into disk cache."""
        with self._lock:
            try:
                cache_file = self._get_cache_file(key)
                
                # Save value
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
                
                # Update index
                file_size = cache_file.stat().st_size
                
                self._index[key] = {
                    'created_at': datetime.utcnow().isoformat(),
                    'last_accessed': datetime.utcnow().isoformat(),
                    'access_count': 0,
                    'size_bytes': file_size,
                    'ttl_seconds': ttl_seconds,
                    'metadata': metadata or {}
                }
                
                # Check if cleanup is needed
                if self._get_total_size() > self.max_size_bytes:
                    self._cleanup()
                
                self._save_index()
                
                # Update statistics
                self._stats.entry_count = len(self._index)
                self._stats.size_bytes = self._get_total_size()
                
                return True
                
            except Exception:
                return False
    
    def remove(self, key: str) -> bool:
        """Remove entry from disk cache."""
        with self._lock:
            if key in self._index:
                cache_file = self._get_cache_file(key)
                cache_file.unlink(missing_ok=True)
                
                del self._index[key]
                self._save_index()
                
                self._stats.entry_count = len(self._index)
                self._stats.size_bytes = self._get_total_size()
                
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            # Remove all cache files
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
            
            # Clear index
            self._index.clear()
            self._save_index()
            
            self._stats.entry_count = 0
            self._stats.size_bytes = 0
    
    def _get_total_size(self) -> int:
        """Get total size of cache."""
        return sum(entry.get('size_bytes', 0) for entry in self._index.values())
    
    def _cleanup(self):
        """Cleanup old entries based on LRU."""
        if not self._index:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1]['last_accessed']
        )
        
        # Remove oldest entries until under limit
        while self._get_total_size() > self.max_size_bytes and sorted_entries:
            key, entry_info = sorted_entries.pop(0)
            cache_file = self._get_cache_file(key)
            cache_file.unlink(missing_ok=True)
            del self._index[key]
            self._stats.evictions += 1
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache statistics."""
        with self._lock:
            stats = CacheStatistics(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                evictions=self._stats.evictions,
                size_bytes=self._get_total_size(),
                entry_count=len(self._index),
                hit_rate=self._stats.hit_rate,
                average_access_time_ms=self._stats.average_access_time_ms,
                last_cleanup=self._stats.last_cleanup
            )
            stats.update_hit_rate()
            return stats


class ComponentCache:
    """Component cache manager."""
    
    def __init__(self, memory_cache_size: int = 1000, disk_cache_size_mb: int = 100,
                 cache_level: CacheLevel = CacheLevel.HYBRID):
        """Initialize component cache."""
        self.cache_level = cache_level
        
        # Initialize caches based on level
        if cache_level == CacheLevel.MEMORY:
            self.memory_cache = MemoryCache(memory_cache_size)
            self.disk_cache = None
        elif cache_level == CacheLevel.DISK:
            self.memory_cache = None
            self.disk_cache = DiskCache(max_size_mb=disk_cache_size_mb)
        else:  # HYBRID
            self.memory_cache = MemoryCache(memory_cache_size)
            self.disk_cache = DiskCache(max_size_mb=disk_cache_size_mb)
        
        # Cache configuration
        self._default_ttl = 3600  # 1 hour
        self._component_cache_config = {}
        
        # Statistics
        self._global_stats = {
            'total_requests': 0,
            'memory_hits': 0,
            'disk_hits': 0,
            'total_misses': 0,
            'cache_level': cache_level.value
        }
    
    def configure_component_cache(self, component_id: str, ttl_seconds: Optional[float] = None,
                                enabled: bool = True, cache_strategy: Optional[str] = None):
        """Configure caching for a specific component."""
        self._component_cache_config[component_id] = {
            'ttl_seconds': ttl_seconds or self._default_ttl,
            'enabled': enabled,
            'cache_strategy': cache_strategy
        }
    
    def get_cache_key(self, component_id: str, context: ComponentContext, **kwargs) -> str:
        """Generate cache key for component execution."""
        # Create a deterministic key based on component ID, context, and parameters
        key_data = {
            'component_id': component_id,
            'data': context.data,
            'metadata': context.metadata,
            'kwargs': {k: v for k, v in kwargs.items() if not callable(v)}
        }
        
        # Convert to JSON and hash
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()
        
        return f"{component_id}:{key_hash}"
    
    async def get(self, component_id: str, context: ComponentContext, **kwargs) -> Optional[ComponentResult]:
        """Get cached result for component."""
        # Check if caching is enabled for this component
        config = self._component_cache_config.get(component_id, {})
        if not config.get('enabled', True):
            return None
        
        cache_key = self.get_cache_key(component_id, context, **kwargs)
        
        self._global_stats['total_requests'] += 1
        
        # Try memory cache first
        if self.memory_cache:
            result = self.memory_cache.get(cache_key)
            if result is not None:
                self._global_stats['memory_hits'] += 1
                return result
        
        # Try disk cache
        if self.disk_cache:
            result = self.disk_cache.get(cache_key)
            if result is not None:
                self._global_stats['disk_hits'] += 1
                
                # Promote to memory cache if available
                if self.memory_cache:
                    ttl = config.get('ttl_seconds', self._default_ttl)
                    self.memory_cache.put(cache_key, result, ttl_seconds=ttl)
                
                return result
        
        self._global_stats['total_misses'] += 1
        return None
    
    async def put(self, component_id: str, context: ComponentContext, result: ComponentResult,
                 **kwargs) -> bool:
        """Put result into cache."""
        # Check if caching is enabled for this component
        config = self._component_cache_config.get(component_id, {})
        if not config.get('enabled', True):
            return False
        
        # Don't cache failed results unless configured
        if not result.success and not config.get('cache_failures', False):
            return False
        
        cache_key = self.get_cache_key(component_id, context, **kwargs)
        ttl = config.get('ttl_seconds', self._default_ttl)
        
        # Prepare metadata
        metadata = {
            'component_id': component_id,
            'execution_time_ms': result.execution_time_ms,
            'success': result.success,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        success = True
        
        # Put in memory cache
        if self.memory_cache:
            success &= self.memory_cache.put(cache_key, result, ttl_seconds=ttl, metadata=metadata)
        
        # Put in disk cache
        if self.disk_cache:
            success &= self.disk_cache.put(cache_key, result, ttl_seconds=ttl, metadata=metadata)
        
        return success
    
    def invalidate(self, component_id: Optional[str] = None, pattern: Optional[str] = None):
        """Invalidate cache entries."""
        if component_id:
            # Invalidate all entries for specific component
            if self.memory_cache:
                keys = self.memory_cache.get_keys()
                for key in keys:
                    if key.startswith(f"{component_id}:"):
                        self.memory_cache.remove(key)
            
            if self.disk_cache:
                # This would require iterating through disk cache entries
                # For now, we'll clear the entire disk cache for simplicity
                self.disk_cache.clear()
        
        elif pattern:
            # Invalidate entries matching pattern
            if self.memory_cache:
                keys = self.memory_cache.get_keys()
                for key in keys:
                    if pattern in key:
                        self.memory_cache.remove(key)
            
            if self.disk_cache:
                self.disk_cache.clear()
        
        else:
            # Clear all caches
            if self.memory_cache:
                self.memory_cache.clear()
            if self.disk_cache:
                self.disk_cache.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = self._global_stats.copy()
        
        # Calculate hit rate
        if stats['total_requests'] > 0:
            stats['hit_rate'] = (stats['memory_hits'] + stats['disk_hits']) / stats['total_requests']
        else:
            stats['hit_rate'] = 0.0
        
        # Add memory cache stats
        if self.memory_cache:
            memory_stats = self.memory_cache.get_statistics()
            stats['memory_cache'] = {
                'entry_count': memory_stats.entry_count,
                'size_bytes': memory_stats.size_bytes,
                'hit_rate': memory_stats.hit_rate,
                'evictions': memory_stats.evictions
            }
        
        # Add disk cache stats
        if self.disk_cache:
            disk_stats = self.disk_cache.get_statistics()
            stats['disk_cache'] = {
                'entry_count': disk_stats.entry_count,
                'size_bytes': disk_stats.size_bytes,
                'hit_rate': disk_stats.hit_rate,
                'evictions': disk_stats.evictions
            }
        
        # Add component configuration
        stats['component_config'] = self._component_cache_config
        
        return stats
    
    def cleanup(self):
        """Perform cache cleanup."""
        if self.memory_cache:
            # Memory cache cleanup is automatic
            pass
        
        if self.disk_cache:
            self.disk_cache._cleanup()
    
    def export_cache_data(self, format: str = "json") -> str:
        """Export cache data for analysis."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "cache_level": self.cache_level.value,
            "statistics": self.get_statistics(),
            "component_config": self._component_cache_config
        }
        
        # Add memory cache entries
        if self.memory_cache:
            data["memory_entries"] = {}
            for key in self.memory_cache.get_keys():
                entry_info = self.memory_cache.get_entry_info(key)
                if entry_info:
                    data["memory_entries"][key] = entry_info
        
        # Add disk cache entries
        if self.disk_cache:
            data["disk_entries"] = self._disk_cache._index
        
        if format.lower() == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            return str(data)


# Global component cache instance
_component_cache = ComponentCache()


# Convenience functions
def configure_component_cache(component_id: str, ttl_seconds: Optional[float] = None,
                            enabled: bool = True, cache_strategy: Optional[str] = None):
    """Configure caching for a specific component."""
    _component_cache.configure_component_cache(component_id, ttl_seconds, enabled, cache_strategy)


async def get_cached_result(component_id: str, context: ComponentContext, **kwargs) -> Optional[ComponentResult]:
    """Get cached result for component."""
    return await _component_cache.get(component_id, context, **kwargs)


async def cache_result(component_id: str, context: ComponentContext, result: ComponentResult, **kwargs) -> bool:
    """Put result into cache."""
    return await _component_cache.put(component_id, context, result, **kwargs)


def invalidate_cache(component_id: Optional[str] = None, pattern: Optional[str] = None):
    """Invalidate cache entries."""
    _component_cache.invalidate(component_id, pattern)


def get_cache_statistics() -> Dict[str, Any]:
    """Get cache statistics."""
    return _component_cache.get_statistics()


def cleanup_cache():
    """Perform cache cleanup."""
    _component_cache.cleanup()


def get_component_cache() -> ComponentCache:
    """Get the global component cache."""
    return _component_cache


# Decorator for automatic caching
def cached_component(ttl_seconds: Optional[float] = None, enabled: bool = True,
                    cache_strategy: Optional[str] = None):
    """Decorator to automatically cache component results."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(self, context: ComponentContext, **kwargs):
                component_id = getattr(self, 'component_id', func.__name__)
                
                # Try to get from cache
                cached_result = await get_cached_result(component_id, context, **kwargs)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = await func(self, context, **kwargs)
                
                # Cache the result
                await cache_result(component_id, context, result, **kwargs)
                
                return result
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(self, context: ComponentContext, **kwargs):
                component_id = getattr(self, 'component_id', func.__name__)
                
                # For sync functions, we'd need to run in async context
                # For now, just execute without caching
                return func(self, context, **kwargs)
            
            return sync_wrapper
    
    return decorator
