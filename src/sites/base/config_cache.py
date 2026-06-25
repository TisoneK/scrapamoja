"""
Configuration caching mechanism for the scraper framework.

This module provides comprehensive configuration caching capabilities, including
memory caching, cache invalidation, and performance optimization.
"""

import json
import time
import threading
from typing import Dict, Any, Optional, List, Union, Callable, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import pickle


class CacheStrategy(Enum):
    """Cache strategy enumeration."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """Configuration cache entry."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[timedelta] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return datetime.utcnow() - self.created_at > self.ttl
    
    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    total_size_bytes: int = 0
    entry_count: int = 0
    avg_access_time_ms: float = 0.0
    last_cleanup: Optional[datetime] = None
    
    def update_hit_rate(self) -> None:
        """Update hit rate statistics."""
        if self.total_requests > 0:
            self.hit_rate = self.hits / self.total_requests
            self.miss_rate = self.misses / self.total_requests


class ConfigCache:
    """Configuration cache with multiple strategies and performance optimization."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100,
                 default_ttl: Optional[timedelta] = None,
                 strategy: CacheStrategy = CacheStrategy.LRU):
        """Initialize configuration cache."""
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.strategy = strategy
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU/FIFO
        self._lock = threading.RLock()
        
        self._stats = CacheStats()
        self._cleanup_interval = timedelta(minutes=5)
        self._last_cleanup = datetime.utcnow()
        
        # Cache event callbacks
        self._hit_callbacks: List[Callable[[str, Any], None]] = []
        self._miss_callbacks: List[Callable[[str], None]] = []
        self._eviction_callbacks: List[Callable[[str, Any], None]] = []
        
        # Serialization settings
        self._use_pickle = False
        self._compress_large_entries = True
        self._compression_threshold = 1024  # bytes
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        start_time = time.time()
        
        with self._lock:
            self._stats.total_requests += 1
            
            if key in self._cache:
                entry = self._cache[key]
                
                # Check if expired
                if entry.is_expired():
                    self._remove_entry(key)
                    self._stats.misses += 1
                    self._stats.update_hit_rate()
                    return default
                
                # Update access information
                entry.touch()
                
                # Update access order for LRU
                if self.strategy == CacheStrategy.LRU:
                    self._update_access_order(key)
                
                # Update statistics
                self._stats.hits += 1
                self._stats.update_hit_rate()
                
                # Call hit callbacks
                for callback in self._hit_callbacks:
                    try:
                        callback(key, entry.value)
                    except Exception as e:
                        print(f"Cache hit callback error: {str(e)}")
                
                # Update access time
                access_time_ms = (time.time() - start_time) * 1000
                self._update_avg_access_time(access_time_ms)
                
                return entry.value
            else:
                self._stats.misses += 1
                self._stats.update_hit_rate()
                
                # Call miss callbacks
                for callback in self._miss_callbacks:
                    try:
                        callback(key)
                    except Exception as e:
                        print(f"Cache miss callback error: {str(e)}")
                
                # Update access time
                access_time_ms = (time.time() - start_time) * 1000
                self._update_avg_access_time(access_time_ms)
                
                return default
    
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live
            metadata: Additional metadata
            
        Returns:
            True if set successfully
        """
        try:
            with self._lock:
                # Calculate entry size
                size_bytes = self._calculate_size(value)
                
                # Check memory limits
                if not self._check_memory_limits(size_bytes):
                    self._evict_entries(size_bytes)
                
                # Check size limits
                if len(self._cache) >= self.max_size:
                    self._evict_one_entry()
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow(),
                    ttl=ttl or self.default_ttl,
                    size_bytes=size_bytes,
                    metadata=metadata or {}
                )
                
                # Add to cache
                self._cache[key] = entry
                
                # Update access order
                self._update_access_order(key)
                
                # Update statistics
                self._stats.sets += 1
                self._stats.entry_count = len(self._cache)
                self._stats.total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())
                
                # Periodic cleanup
                self._maybe_cleanup()
                
                return True
                
        except Exception as e:
            print(f"Cache set error: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._remove_entry(key)
                self._stats.deletes += 1
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats.entry_count = 0
            self._stats.total_size_bytes = 0
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                return not entry.is_expired()
            return False
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern."""
        with self._lock:
            keys = list(self._cache.keys())
            
            if pattern:
                import re
                try:
                    regex = re.compile(pattern)
                    keys = [key for key in keys if regex.match(key)]
                except re.error:
                    # Simple substring match if regex fails
                    keys = [key for key in keys if pattern in key]
            
            return keys
    
    def get_size(self) -> int:
        """Get current cache size in bytes."""
        with self._lock:
            return sum(entry.size_bytes for entry in self._cache.values())
    
    def get_count(self) -> int:
        """Get current cache entry count."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            stats = CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                sets=self._stats.sets,
                deletes=self._stats.deletes,
                evictions=self._stats.evictions,
                total_requests=self._stats.total_requests,
                hit_rate=self._stats.hit_rate,
                miss_rate=self._stats.miss_rate,
                total_size_bytes=self._stats.total_size_bytes,
                entry_count=self._stats.entry_count,
                avg_access_time_ms=self._stats.avg_access_time_ms,
                last_cleanup=self._stats.last_cleanup
            )
            stats.update_hit_rate()
            return stats
    
    def cleanup(self) -> int:
        """Clean up expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
            
            self._last_cleanup = datetime.utcnow()
            return len(expired_keys)
    
    def _remove_entry(self, key: str) -> None:
        """Remove an entry from the cache."""
        if key in self._cache:
            entry = self._cache[key]
            
            # Call eviction callbacks
            for callback in self._eviction_callbacks:
                try:
                    callback(key, entry.value)
                except Exception as e:
                    print(f"Cache eviction callback error: {str(e)}")
            
            del self._cache[key]
            
            # Remove from access order
            if key in self._access_order:
                self._access_order.remove(key)
            
            # Update statistics
            self._stats.entry_count = len(self._cache)
            self._stats.total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())
    
    def _update_access_order(self, key: str) -> None:
        """Update access order for LRU strategy."""
        if self.strategy == CacheStrategy.LRU:
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
        elif self.strategy == CacheStrategy.FIFO:
            if key not in self._access_order:
                self._access_order.append(key)
    
    def _evict_entries(self, required_size: int) -> None:
        """Evict entries to make room for new data."""
        while not self._check_memory_limits(required_size) and self._cache:
            self._evict_one_entry()
    
    def _evict_one_entry(self) -> None:
        """Evict one entry based on strategy."""
        if not self._cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # Evict least recently used
            if self._access_order:
                key_to_evict = self._access_order[0]
            else:
                key_to_evict = min(self._cache.keys(), 
                                 key=lambda k: self._cache[k].last_accessed)
        
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            key_to_evict = min(self._cache.keys(), 
                             key=lambda k: self._cache[k].access_count)
        
        elif self.strategy == CacheStrategy.FIFO:
            # Evict first in
            if self._access_order:
                key_to_evict = self._access_order[0]
            else:
                key_to_evict = min(self._cache.keys(), 
                                 key=lambda k: self._cache[k].created_at)
        
        elif self.strategy == CacheStrategy.TTL:
            # Evict expired entries first, then oldest
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            if expired_keys:
                key_to_evict = expired_keys[0]
            else:
                key_to_evict = min(self._cache.keys(), 
                                 key=lambda k: self._cache[k].created_at)
        
        else:
            # Default to LRU
            key_to_evict = min(self._cache.keys(), 
                             key=lambda k: self._cache[k].last_accessed)
        
        if key_to_evict in self._cache:
            self._remove_entry(key_to_evict)
            self._stats.evictions += 1
    
    def _check_memory_limits(self, additional_size: int) -> bool:
        """Check if adding additional size would exceed memory limits."""
        current_size = sum(entry.size_bytes for entry in self._cache.values())
        return (current_size + additional_size) <= self.max_memory_bytes
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate the size of a value in bytes."""
        try:
            if self._use_pickle:
                data = pickle.dumps(value)
            else:
                data = json.dumps(value, default=str).encode('utf-8')
            
            return len(data)
        except Exception:
            # Fallback to string representation
            return len(str(value).encode('utf-8'))
    
    def _maybe_cleanup(self) -> None:
        """Perform cleanup if needed."""
        if datetime.utcnow() - self._last_cleanup > self._cleanup_interval:
            self.cleanup()
    
    def _update_avg_access_time(self, access_time_ms: float) -> None:
        """Update average access time."""
        if self._stats.total_requests > 0:
            total_time = self._stats.avg_access_time_ms * (self._stats.total_requests - 1)
            self._stats.avg_access_time_ms = (total_time + access_time_ms) / self._stats.total_requests
    
    def add_hit_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Add a cache hit callback."""
        self._hit_callbacks.append(callback)
    
    def add_miss_callback(self, callback: Callable[[str], None]) -> None:
        """Add a cache miss callback."""
        self._miss_callbacks.append(callback)
    
    def add_eviction_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Add a cache eviction callback."""
        self._eviction_callbacks.append(callback)
    
    def remove_hit_callback(self, callback: Callable[[str, Any], None]) -> bool:
        """Remove a cache hit callback."""
        if callback in self._hit_callbacks:
            self._hit_callbacks.remove(callback)
            return True
        return False
    
    def remove_miss_callback(self, callback: Callable[[str], None]) -> bool:
        """Remove a cache miss callback."""
        if callback in self._miss_callbacks:
            self._miss_callbacks.remove(callback)
            return True
        return False
    
    def remove_eviction_callback(self, callback: Callable[[str, Any], None]) -> bool:
        """Remove a cache eviction callback."""
        if callback in self._eviction_callbacks:
            self._eviction_callbacks.remove(callback)
            return True
        return False
    
    def set_strategy(self, strategy: CacheStrategy) -> None:
        """Set cache strategy."""
        self.strategy = strategy
        self._access_order.clear()
        
        # Rebuild access order for LRU/FIFO
        if strategy in [CacheStrategy.LRU, CacheStrategy.FIFO]:
            for key in self._cache.keys():
                self._access_order.append(key)
    
    def set_max_size(self, max_size: int) -> None:
        """Set maximum cache size."""
        self.max_size = max_size
        
        # Evict entries if necessary
        while len(self._cache) > max_size:
            self._evict_one_entry()
    
    def set_max_memory(self, max_memory_mb: int) -> None:
        """Set maximum memory usage in MB."""
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Evict entries if necessary
        current_size = sum(entry.size_bytes for entry in self._cache.values())
        while current_size > self.max_memory_bytes and self._cache:
            self._evict_one_entry()
            current_size = sum(entry.size_bytes for entry in self._cache.values())
    
    def set_default_ttl(self, ttl: Optional[timedelta]) -> None:
        """Set default TTL for cache entries."""
        self.default_ttl = ttl
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache entry."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            return {
                'key': entry.key,
                'size_bytes': entry.size_bytes,
                'created_at': entry.created_at.isoformat(),
                'last_accessed': entry.last_accessed.isoformat(),
                'access_count': entry.access_count,
                'ttl': entry.ttl.total_seconds() if entry.ttl else None,
                'is_expired': entry.is_expired(),
                'metadata': entry.metadata
            }
    
    def get_all_entries_info(self) -> List[Dict[str, Any]]:
        """Get information about all cache entries."""
        with self._lock:
            return [self.get_entry_info(key) for key in self._cache.keys()]
    
    def export_cache(self) -> Dict[str, Any]:
        """Export cache data."""
        with self._lock:
            return {
                'entries': {
                    key: {
                        'value': entry.value,
                        'created_at': entry.created_at.isoformat(),
                        'last_accessed': entry.last_accessed.isoformat(),
                        'access_count': entry.access_count,
                        'ttl': entry.ttl.total_seconds() if entry.ttl else None,
                        'metadata': entry.metadata
                    }
                    for key, entry in self._cache.items()
                },
                'stats': self.get_stats().__dict__,
                'config': {
                    'max_size': self.max_size,
                    'max_memory_bytes': self.max_memory_bytes,
                    'default_ttl': self.default_ttl.total_seconds() if self.default_ttl else None,
                    'strategy': self.strategy.value
                }
            }
    
    def import_cache(self, cache_data: Dict[str, Any]) -> None:
        """Import cache data."""
        with self._lock:
            # Clear existing cache
            self.clear()
            
            # Import entries
            for key, entry_data in cache_data.get('entries', {}).items():
                ttl = None
                if entry_data.get('ttl'):
                    ttl = timedelta(seconds=entry_data['ttl'])
                
                self.set(
                    key=key,
                    value=entry_data['value'],
                    ttl=ttl,
                    metadata=entry_data.get('metadata', {})
                )
    
    def warm_up(self, data: Dict[str, Any], ttl: Optional[timedelta] = None) -> None:
        """Warm up cache with initial data."""
        for key, value in data.items():
            self.set(key, value, ttl)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        keys_to_remove = []
        
        with self._lock:
            for key in self._cache.keys():
                import re
                try:
                    if re.match(pattern, key):
                        keys_to_remove.append(key)
                except re.error:
                    # Simple substring match if regex fails
                    if pattern in key:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.delete(key)
        
        return len(keys_to_remove)
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information."""
        with self._lock:
            entry_sizes = [entry.size_bytes for entry in self._cache.values()]
            
            return {
                'total_bytes': sum(entry_sizes),
                'total_mb': sum(entry_sizes) / (1024 * 1024),
                'max_bytes': self.max_memory_bytes,
                'max_mb': self.max_memory_bytes / (1024 * 1024),
                'usage_percentage': (sum(entry_sizes) / self.max_memory_bytes) * 100,
                'entry_count': len(entry_sizes),
                'average_entry_size': sum(entry_sizes) / len(entry_sizes) if entry_sizes else 0,
                'min_entry_size': min(entry_sizes) if entry_sizes else 0,
                'max_entry_size': max(entry_sizes) if entry_sizes else 0
            }


# Global cache instance
_config_cache = ConfigCache()


# Convenience functions
def get(key: str, default: Any = None) -> Any:
    """Get value from global cache."""
    return _config_cache.get(key, default)


def set(key: str, value: Any, ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Set value in global cache."""
    return _config_cache.set(key, value, ttl, metadata)


def delete(key: str) -> bool:
    """Delete value from global cache."""
    return _config_cache.delete(key)


def clear() -> None:
    """Clear global cache."""
    _config_cache.clear()


def exists(key: str) -> bool:
    """Check if key exists in global cache."""
    return _config_cache.exists(key)


def get_stats() -> CacheStats:
    """Get global cache statistics."""
    return _config_cache.get_stats()


def cleanup() -> int:
    """Clean up expired entries in global cache."""
    return _config_cache.cleanup()


def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage information."""
    return _config_cache.get_memory_usage()


def warm_up(data: Dict[str, Any], ttl: Optional[timedelta] = None) -> None:
    """Warm up global cache with data."""
    _config_cache.warm_up(data, ttl)


def invalidate_pattern(pattern: str) -> int:
    """Invalidate entries matching pattern."""
    return _config_cache.invalidate_pattern(pattern)
