"""
Extraction caching mechanism for Wikipedia articles.

This module provides caching functionality to improve extraction performance
by storing and retrieving previously extracted data.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json


@dataclass
class CacheEntry:
    """Cache entry for extracted data."""
    
    key: str
    data: Dict[str, Any]
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: int = 3600
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def update_access(self) -> None:
        """Update access information."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1


class ExtractionCache:
    """Extraction cache for Wikipedia articles."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """Initialize extraction cache."""
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache."""
        if key not in self.cache:
            self.miss_count += 1
            return None
        
        entry = self.cache[key]
        
        # Check if entry is expired
        if entry.is_expired():
            del self.cache[key]
            self.miss_count += 1
            return None
        
        # Update access information
        entry.update_access()
        self.hit_count += 1
        
        return entry.data.copy()
    
    def put(self, key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """Put data into cache."""
        # Check if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Create cache entry
        ttl = ttl_seconds or self.default_ttl
        entry = CacheEntry(
            key=key,
            data=data.copy(),
            created_at=datetime.utcnow(),
            accessed_at=datetime.utcnow(),
            ttl_seconds=ttl
        )
        
        self.cache[key] = entry
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        expired_keys = []
        for key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_cache_key(self, url: str, extraction_type: str, **kwargs) -> str:
        """Generate cache key for extraction request."""
        # Create a deterministic key based on URL and extraction parameters
        key_data = {
            'url': url,
            'extraction_type': extraction_type,
            **kwargs
        }
        
        # Sort keys for consistency
        key_str = json.dumps(key_data, sort_keys=True)
        
        # Generate hash
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'eviction_count': self.eviction_count,
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        if not self.cache:
            return {
                'entries': [],
                'oldest_entry': None,
                'newest_entry': None,
                'most_accessed': None
            }
        
        entries = []
        oldest_entry = None
        newest_entry = None
        most_accessed = None
        
        for key, entry in self.cache.items():
            entry_info = {
                'key': key,
                'created_at': entry.created_at.isoformat(),
                'accessed_at': entry.accessed_at.isoformat(),
                'access_count': entry.access_count,
                'ttl_seconds': entry.ttl_seconds,
                'is_expired': entry.is_expired()
            }
            entries.append(entry_info)
            
            # Track oldest and newest entries
            if oldest_entry is None or entry.created_at < oldest_entry['created_at']:
                oldest_entry = entry_info
            
            if newest_entry is None or entry.created_at > newest_entry['created_at']:
                newest_entry = entry_info
            
            # Track most accessed entry
            if most_accessed is None or entry.access_count > most_accessed['access_count']:
                most_accessed = entry_info
        
        return {
            'entries': entries,
            'oldest_entry': oldest_entry,
            'newest_entry': newest_entry,
            'most_accessed': most_accessed
        }
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Find LRU entry
        lru_key = None
        lru_time = datetime.utcnow()
        
        for key, entry in self.cache.items():
            if entry.accessed_at < lru_time:
                lru_time = entry.accessed_at
                lru_key = key
        
        if lru_key:
            del self.cache[lru_key]
            self.eviction_count += 1
    
    def _evict_lfu(self) -> None:
        """Evict least frequently used entry."""
        if not self.cache:
            return
        
        # Find LFU entry
        lfu_key = None
        lfu_count = float('inf')
        
        for key, entry in self.cache.items():
            if entry.access_count < lfu_count:
                lfu_count = entry.access_count
                lfu_key = key
        
        if lfu_key:
            del self.cache[lfu_key]
            self.eviction_count += 1
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance."""
        # Remove expired entries
        expired_count = self.cleanup_expired()
        
        # If still over capacity, evict LRU entries
        evicted_count = 0
        while len(self.cache) > self.max_size * 0.9:  # Leave 10% headroom
            self._evict_lru()
            evicted_count += 1
        
        return {
            'expired_removed': expired_count,
            'evicted_for_space': evicted_count,
            'final_size': len(self.cache)
        }


class CacheManager:
    """Manager for multiple cache instances."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.caches: Dict[str, ExtractionCache] = {}
    
    def get_cache(self, name: str, **kwargs) -> ExtractionCache:
        """Get or create cache instance."""
        if name not in self.caches:
            self.caches[name] = ExtractionCache(**kwargs)
        return self.caches[name]
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        stats = {}
        for name, cache in self.caches.items():
            stats[name] = cache.get_cache_stats()
        return stats
    
    def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self.caches.values():
            cache.clear()
    
    def optimize_all(self) -> Dict[str, Any]:
        """Optimize all caches."""
        results = {}
        for name, cache in self.caches.items():
            results[name] = cache.optimize_cache()
        return results


# Global cache manager instance
cache_manager = CacheManager()
