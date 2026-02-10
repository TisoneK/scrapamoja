"""
LRU Cache implementation for selector contexts.

This module provides a Least Recently Used cache for selector contexts
with intelligent eviction policies and performance monitoring.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Hashable
from dataclasses import dataclass, field
from collections import OrderedDict
import threading
import weakref

from ..models.selector_models import SemanticSelector


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the LRU cache."""
    key: str
    value: Any
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0
    ttl_seconds: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    current_size: int = 0
    max_size: int = 0
    total_memory_bytes: int = 0
    average_access_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        if self.total_requests == 0:
            return 0.0
        return self.misses / self.total_requests
    
    @property
    def eviction_rate(self) -> float:
        """Calculate cache eviction rate."""
        if self.total_requests == 0:
            return 0.0
        return self.evictions / self.total_requests


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache for selector contexts.
    """
    
    def __init__(
        self,
        max_size: int = 100,
        default_ttl_seconds: Optional[float] = 300,  # 5 minutes
        max_memory_mb: Optional[float] = 50.0  # 50MB default
        cleanup_interval_seconds: float = 60  # 1 minute
    ):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries to cache
            default_ttl_seconds: Default TTL for entries in seconds
            max_memory_mb: Maximum memory usage in MB
            cleanup_interval_seconds: Interval for cleanup operations
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.cleanup_interval_seconds = cleanup_interval_seconds
        
        # Cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = CacheStats(max_size=max_size)
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"LRUCache initialized: max_size={max_size}, ttl={default_ttl_seconds}s, max_memory={max_memory_mb}MB")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found/expired
        """
        start_time = time.time()
        
        with self._lock:
            self.stats.total_requests += 1
            
            # Check if key exists
            if key not in self._cache:
                self.stats.misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check if entry is expired
            if entry.is_expired:
                # Remove expired entry
                del self._cache[key]
                self.stats.evictions += 1
                self.stats.misses += 1
                logger.debug(f"Cache entry expired and removed: {key}")
                return None
            
            # Move to end (most recently used)
            del self._cache[key]
            self._cache[key] = entry
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = start_time
            self.stats.hits += 1
            
            access_time_ms = (time.time() - start_time) * 1000
            self._update_average_access_time(access_time_ms)
            
            logger.debug(f"Cache hit: {key} (access_count: {entry.access_count})")
            
            return entry.value
    
    async def put(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
        size_bytes: Optional[int] = None
    ) -> bool:
        """
        Put a value into the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL for this entry (uses default if None)
            size_bytes: Size of value in bytes (calculated if None)
            
        Returns:
            bool: True if value was cached, False if evicted
        """
        with self._lock:
            # Calculate size if not provided
            if size_bytes is None:
                size_bytes = self._calculate_size(value)
            
            # Check memory constraints
            current_memory = self._get_current_memory_bytes()
            if current_memory + size_bytes > self.max_memory_bytes:
                # Need to evict entries to make space
                await self._evict_for_space(size_bytes)
            
            # Check size constraints
            while len(self._cache) >= self.max_size:
                await self._evict_lru()
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl_seconds or self.default_ttl_seconds,
                size_bytes=size_bytes
            )
            
            # Store in cache
            self._cache[key] = entry
            self.stats.current_size = len(self._cache)
            self.stats.total_memory_bytes = self._get_current_memory_bytes()
            
            logger.debug(f"Cache put: {key} (size: {size_bytes} bytes, ttl: {entry.ttl_seconds}s)")
            
            return True
    
    async def remove(self, key: str) -> bool:
        """
        Remove a value from the cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            bool: True if key was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.current_size = len(self._cache)
                self.stats.total_memory_bytes = self._get_current_memory_bytes()
                logger.debug(f"Cache remove: {key}")
                return True
            else:
                logger.debug(f"Cache remove failed: {key} not found")
                return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            pattern: Pattern to match keys (clears all if None)
            
        Returns:
            int: Number of entries removed
        """
        with self._lock:
            if pattern is None:
                # Clear all
                removed_count = len(self._cache)
                self._cache.clear()
            else:
                # Clear matching entries
                import re
                regex_pattern = re.compile(pattern, re.IGNORECASE)
                matching_keys = [
                    key for key in self._cache.keys()
                    if regex_pattern.search(key)
                ]
                
                for key in matching_keys:
                    del self._cache[key]
                
                removed_count = len(matching_keys)
            
            self.stats.current_size = len(self._cache)
            self.stats.total_memory_bytes = self._get_current_memory_bytes()
            
            logger.info(f"Cache clear: pattern='{pattern}', removed={removed_count} entries")
            
            return removed_count
    
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from the cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict[str, Any]: Dictionary of found values
        """
        result = {}
        
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        
        return result
    
    def _calculate_size(self, value: Any) -> int:
        """
        Calculate the size of a value in bytes.
        
        Args:
            value: Value to size
            
        Returns:
            int: Size in bytes
        """
        if isinstance(value, SemanticSelector):
            # Rough estimation for SemanticSelector objects
            return len(str(value)) * 2  # Assume 2 bytes per character
        elif isinstance(value, (list, dict)):
            return len(str(value)) * 2
        elif isinstance(value, str):
            return len(value.encode('utf-8'))
        else:
            return len(str(value).encode('utf-8'))
    
    def _get_current_memory_bytes(self) -> int:
        """Calculate current memory usage in bytes."""
        return sum(entry.size_bytes for entry in self._cache.values())
    
    async def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if not self._cache:
            return
        
        # Get the LRU key (first in OrderedDict)
        lru_key = next(iter(self._cache))
        lru_entry = self._cache[lru_key]
        
        del self._cache[lru_key]
        self.stats.evictions += 1
        self.stats.current_size = len(self._cache)
        self.stats.total_memory_bytes = self._get_current_memory_bytes()
        
        logger.debug(f"LRU eviction: {lru_key} (age: {lru_entry.age_seconds:.1f}s)")
    
    async def _evict_for_space(self, required_bytes: int) -> None:
        """
        Evict entries to free up space for required bytes.
        
        Args:
            required_bytes: Bytes of space needed
        """
        freed_bytes = 0
        
        # Sort entries by creation time (oldest first)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda item: item[1].created_at
        )
        
        for key, entry in sorted_entries:
            del self._cache[key]
            freed_bytes += entry.size_bytes
            self.stats.evictions += 1
            
            if freed_bytes >= required_bytes:
                break
        
        self.stats.current_size = len(self._cache)
        self.stats.total_memory_bytes = self._get_current_memory_bytes()
        
        logger.debug(f"Space eviction: freed {freed_bytes} bytes, evicted {len(sorted_entries)} entries")
    
    def _update_average_access_time(self, access_time_ms: float) -> None:
        """Update running average of access times."""
        if self.stats.total_requests == 1:
            self.stats.average_access_time_ms = access_time_ms
        else:
            # Exponential moving average with alpha = 0.1
            alpha = 0.1
            self.stats.average_access_time_ms = (
                alpha * access_time_ms +
                (1 - alpha) * self.stats.average_access_time_ms
            )
    
    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cache cleanup task started")
    
    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Cache cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                await self._cleanup_expired_entries()
                await self._cleanup_memory_pressure()
                
            except asyncio.CancelledError:
                logger.debug("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(self.cleanup_interval_seconds)
    
    async def _cleanup_expired_entries(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if (entry.ttl_seconds and 
                    (current_time - entry.created_at) > entry.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self.stats.evictions += len(expired_keys)
            
            if expired_keys:
                self.stats.current_size = len(self._cache)
                self.stats.total_memory_bytes = self._get_current_memory_bytes()
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    async def _cleanup_memory_pressure(self) -> None:
        """Clean up entries if under memory pressure."""
        current_memory = self._get_current_memory_bytes()
        
        # If using more than 80% of max memory, start cleaning
        if current_memory > (self.max_memory_bytes * 0.8):
            # Target 60% memory usage
            target_memory = self.max_memory_bytes * 0.6
            bytes_to_free = current_memory - target_memory
            
            await self._evict_for_space(bytes_to_free)
            logger.debug(f"Memory pressure cleanup: freed {bytes_to_free} bytes")
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                total_requests=self.stats.total_requests,
                current_size=self.stats.current_size,
                max_size=self.stats.max_size,
                total_memory_bytes=self.stats.total_memory_bytes,
                average_access_time_ms=self.stats.average_access_time_ms
            )
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        stats = self.get_stats()
        
        with self._lock:
            # Get cache entries sorted by access frequency
            entries_by_access = sorted(
                self._cache.items(),
                key=lambda item: item[1].access_count,
                reverse=True
            )
            
            # Get cache entries sorted by age
            entries_by_age = sorted(
                self._cache.items(),
                key=lambda item: item[1].created_at,
                reverse=True
            )
            
            return {
                "statistics": {
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "hit_rate": stats.hit_rate,
                    "miss_rate": stats.miss_rate,
                    "evictions": stats.evictions,
                    "total_requests": stats.total_requests,
                    "current_size": stats.current_size,
                    "max_size": stats.max_size,
                    "memory_usage_mb": stats.total_memory_bytes / (1024 * 1024),
                    "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                    "average_access_time_ms": stats.average_access_time_ms
                },
                "top_entries": [
                    {
                        "key": key,
                        "access_count": entry.access_count,
                        "age_seconds": entry.age_seconds,
                        "size_bytes": entry.size_bytes,
                        "last_accessed": entry.last_accessed,
                        "is_expired": entry.is_expired
                    }
                    for key, entry in entries_by_access[:10]  # Top 10
                ],
                "oldest_entries": [
                    {
                        "key": key,
                        "age_seconds": entry.age_seconds,
                        "size_bytes": entry.size_bytes,
                        "created_at": entry.created_at
                    }
                    for key, entry in entries_by_age[:10]  # Oldest 10
                ],
                "configuration": {
                    "max_size": self.max_size,
                    "default_ttl_seconds": self.default_ttl_seconds,
                    "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                    "cleanup_interval_seconds": self.cleanup_interval_seconds,
                    "cleanup_task_running": self._running
                }
            }
        }


class ContextualLRUCache:
    """
    LRU cache specifically designed for selector contexts with context-aware features.
    """
    
    def __init__(
        self,
        max_size: int = 100,
        context_ttl_multiplier: float = 2.0,  # Context entries get 2x TTL
        max_memory_mb: Optional[float] = 50.0
    ):
        """
        Initialize contextual LRU cache.
        
        Args:
            max_size: Maximum number of entries
            context_ttl_multiplier: Multiplier for context-based TTL
            max_memory_mb: Maximum memory usage in MB
        """
        self.base_cache = LRUCache(
            max_size=max_size,
            max_memory_mb=max_memory_mb
        )
        self.context_ttl_multiplier = context_ttl_multiplier
        
        logger.info(f"ContextualLRUCache initialized with context TTL multiplier: {context_ttl_multiplier}")
    
    async def get_context_selectors(
        self,
        context_path: str,
        dom_state: Optional[str] = None
    ) -> List[Any]:
        """
        Get selectors for a specific context with enhanced TTL.
        
        Args:
            context_path: Context path (e.g., "extraction/match_stats")
            dom_state: DOM state for context-aware TTL
            
        Returns:
            List[Any]: Cached selectors for the context
        """
        # Create context-specific key
        cache_key = f"context:{context_path}"
        if dom_state:
            cache_key += f":{dom_state}"
        
        entry = await self.base_cache.get(cache_key)
        
        if entry is not None:
            return entry.value if isinstance(entry.value, list) else [entry.value]
        
        return []
    
    async def put_context_selectors(
        self,
        context_path: str,
        selectors: List[Any],
        dom_state: Optional[str] = None,
        ttl_seconds: Optional[float] = None
    ) -> None:
        """
        Put selectors for a specific context with enhanced TTL.
        
        Args:
            context_path: Context path
            selectors: Selectors to cache
            dom_state: DOM state for context-aware TTL
            ttl_seconds: Custom TTL (uses calculated if None)
        """
        # Create context-specific key
        cache_key = f"context:{context_path}"
        if dom_state:
            cache_key += f":{dom_state}"
        
        # Calculate TTL based on context and DOM state
        if ttl_seconds is None:
            base_ttl = self.base_cache.default_ttl_seconds
            
            # Context entries get longer TTL
            if '/' in context_path:  # Hierarchical context
                ttl_multiplier = self.context_ttl_multiplier
            else:
                ttl_multiplier = 1.0
            
            # DOM state affects TTL
            if dom_state in ['live', 'scheduled', 'finished']:
                # Dynamic content gets shorter TTL
                ttl_multiplier *= 0.5
            
            ttl_seconds = base_ttl * ttl_multiplier
        
        await self.base_cache.put(cache_key, selectors, ttl_seconds=ttl_seconds)
    
    async def invalidate_context(self, context_path: str, dom_state: Optional[str] = None) -> int:
        """
        Invalidate all entries for a specific context.
        
        Args:
            context_path: Context path to invalidate
            dom_state: DOM state to invalidate
            
        Returns:
            int: Number of entries invalidated
        """
        # Create pattern for context matching
        pattern = f"context:{context_path}"
        if dom_state:
            pattern += f":{dom_state}"
        
        pattern += r":.*"  # Match any DOM state variant
        
        return await self.base_cache.clear(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics with context-specific insights."""
        base_stats = self.base_cache.get_stats()
        
        # Analyze context usage
        context_entries = 0
        total_entries = 0
        
        with self.base_cache._lock:
            for key in self.base_cache._cache.keys():
                if key.startswith("context:"):
                    context_entries += 1
                total_entries += 1
        
        return {
            **base_stats.__dict__,
            "context_usage": {
                "context_entries": context_entries,
                "context_ratio": context_entries / max(total_entries, 1),
                "total_entries": total_entries
            }
        }


# Global cache instances
_context_caches: Dict[str, ContextualLRUCache] = {}
_cache_lock = threading.Lock()


def get_context_cache(cache_id: str, **kwargs) -> ContextualLRUCache:
    """
    Get or create a contextual LRU cache instance.
    
    Args:
        cache_id: Unique identifier for the cache
        **kwargs: Arguments to pass to ContextualLRUCache
        
    Returns:
        ContextualLRUCache: Cache instance
    """
    global _context_caches, _cache_lock
    
    with _cache_lock:
        if cache_id not in _context_caches:
            _context_caches[cache_id] = ContextualLRUCache(**kwargs)
            logger.info(f"Created new context cache: {cache_id}")
        
        return _context_caches[cache_id]


def cleanup_all_caches() -> None:
    """Clean up all cache instances."""
    global _context_caches, _cache_lock
    
    with _cache_lock:
        for cache_id, cache in _context_caches.items():
            try:
                asyncio.create_task(cache.base_cache.stop_cleanup_task())
                logger.info(f"Stopped cleanup task for cache: {cache_id}")
            except Exception as e:
                logger.error(f"Error stopping cache cleanup for {cache_id}: {e}")
        
        _context_caches.clear()
        logger.info("All context caches cleaned up")
