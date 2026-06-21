"""
Performance optimization utilities and strategies for telemetry components.

This module provides performance optimization strategies including:
- Memory-efficient data structures
- Batch processing optimizations
- Connection pooling
- Caching strategies
- Resource cleanup
"""

import asyncio
import gc
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union
import weakref

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization monitoring."""
    operation_count: int = 0
    total_time: float = 0.0
    memory_usage: int = 0
    cache_hit_rate: float = 0.0
    batch_efficiency: float = 0.0
    
    @property
    def average_time(self) -> float:
        """Calculate average operation time."""
        return self.total_time / max(self.operation_count, 1)


class MemoryEfficientBuffer:
    """Memory-efficient circular buffer for telemetry data."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
    
    async def add(self, item: Any) -> None:
        """Add item to buffer with memory management."""
        async with self._lock:
            self.buffer.append(item)
            
            # Trigger garbage collection if buffer is full
            if len(self.buffer) == self.max_size:
                gc.collect()
    
    async def get_batch(self, batch_size: int = 100) -> List[Any]:
        """Get batch of items for processing."""
        async with self._lock:
            batch = []
            for _ in range(min(batch_size, len(self.buffer))):
                if self.buffer:
                    batch.append(self.buffer.popleft())
            return batch
    
    async def size(self) -> int:
        """Get current buffer size."""
        async with self._lock:
            return len(self.buffer)


class ConnectionPool:
    """Generic connection pool for telemetry components."""
    
    def __init__(self, create_connection, max_connections: int = 10):
        self.create_connection = create_connection
        self.max_connections = max_connections
        self.pool: deque = deque(maxlen=max_connections)
        self.active_connections: Set = set()
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        connection = None
        try:
            async with self._lock:
                if self.pool:
                    connection = self.pool.popleft()
                else:
                    connection = await self.create_connection()
                
                self.active_connections.add(connection)
            
            yield connection
            
        finally:
            if connection:
                async with self._lock:
                    self.active_connections.discard(connection)
                    if len(self.pool) < self.max_connections:
                        self.pool.append(connection)
    
    async def close_all(self) -> None:
        """Close all connections in pool."""
        async with self._lock:
            # Close pooled connections
            while self.pool:
                conn = self.pool.popleft()
                if hasattr(conn, 'close'):
                    await conn.close()
            
            # Close active connections
            for conn in list(self.active_connections):
                if hasattr(conn, 'close'):
                    await conn.close()
            
            self.active_connections.clear()


class LRUCache:
    """Thread-safe LRU cache with automatic cleanup."""
    
    def __init__(self, max_size: int = 1000, ttl: float = 300.0):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        async with self._lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            
            # Check TTL
            if time.time() - item['timestamp'] > self.ttl:
                del self.cache[key]
                self.access_order.remove(key)
                return None
            
            # Update access order
            self.access_order.remove(key)
            self.access_order.append(key)
            
            return item['value']
    
    async def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        async with self._lock:
            current_time = time.time()
            
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]
            
            # Update or add item
            if key in self.cache:
                self.access_order.remove(key)
            
            self.cache[key] = {
                'value': value,
                'timestamp': current_time
            }
            self.access_order.append(key)
    
    async def clear_expired(self) -> int:
        """Clear expired items."""
        async with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, item in self.cache.items():
                if current_time - item['timestamp'] > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                self.access_order.remove(key)
            
            return len(expired_keys)
    
    async def size(self) -> int:
        """Get cache size."""
        async with self._lock:
            return len(self.cache)


class BatchProcessor:
    """Optimized batch processor with adaptive sizing."""
    
    def __init__(self, 
                 min_batch_size: int = 10,
                 max_batch_size: int = 1000,
                 target_latency: float = 0.1):
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_latency = target_latency
        self.current_batch_size = min_batch_size
        self.processing_times = deque(maxlen=10)
        self._lock = asyncio.Lock()
    
    async def get_optimal_batch_size(self) -> int:
        """Get optimal batch size based on performance."""
        async with self._lock:
            if len(self.processing_times) < 3:
                return self.current_batch_size
            
            avg_time = sum(self.processing_times) / len(self.processing_times)
            
            # Adjust batch size based on performance
            if avg_time > self.target_latency:
                # Too slow, reduce batch size
                self.current_batch_size = max(
                    self.min_batch_size,
                    int(self.current_batch_size * 0.8)
                )
            elif avg_time < self.target_latency * 0.5:
                # Very fast, increase batch size
                self.current_batch_size = min(
                    self.max_batch_size,
                    int(self.current_batch_size * 1.2)
                )
            
            return self.current_batch_size
    
    async def record_processing_time(self, duration: float) -> None:
        """Record processing time for optimization."""
        async with self._lock:
            self.processing_times.append(duration)


class ResourceMonitor:
    """Monitor and optimize resource usage."""
    
    def __init__(self, memory_threshold_mb: int = 100):
        self.memory_threshold_mb = memory_threshold_mb
        self.optimization_callbacks: List[callable] = []
    
    def add_optimization_callback(self, callback: callable) -> None:
        """Add callback for resource optimization."""
        self.optimization_callbacks.append(callback)
    
    async def check_resources(self) -> Dict[str, Any]:
        """Check current resource usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        return {
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'memory_threshold_exceeded': memory_mb > self.memory_threshold_mb
        }
    
    async def optimize_if_needed(self) -> None:
        """Run optimization if resources are high."""
        resources = await self.check_resources()
        
        if resources['memory_threshold_exceeded']:
            logger.warning(f"Memory threshold exceeded: {resources['memory_mb']:.1f}MB")
            
            # Run optimization callbacks
            for callback in self.optimization_callbacks:
                try:
                    await callback()
                except Exception as e:
                    logger.error(f"Optimization callback failed: {e}")
            
            # Force garbage collection
            gc.collect()


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        self.buffer = MemoryEfficientBuffer()
        self.cache = LRUCache()
        self.batch_processor = BatchProcessor()
        self.resource_monitor = ResourceMonitor()
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.metrics = PerformanceMetrics()
        self._running = False
    
    async def start(self) -> None:
        """Start performance optimization services."""
        self._running = True
        
        # Add optimization callbacks
        self.resource_monitor.add_optimization_callback(self.cache.clear_expired)
        self.resource_monitor.add_optimization_callback(self._cleanup_expired_pools)
        
        # Start background optimization task
        asyncio.create_task(self._optimization_loop())
        
        logger.info("Performance optimizer started")
    
    async def stop(self) -> None:
        """Stop performance optimization services."""
        self._running = False
        
        # Close all connection pools
        for pool in self.connection_pools.values():
            await pool.close_all()
        
        logger.info("Performance optimizer stopped")
    
    def get_connection_pool(self, name: str, create_connection) -> ConnectionPool:
        """Get or create connection pool."""
        if name not in self.connection_pools:
            self.connection_pools[name] = ConnectionPool(create_connection)
        return self.connection_pools[name]
    
    async def record_operation(self, operation: str, duration: float) -> None:
        """Record operation metrics."""
        self.metrics.operation_count += 1
        self.metrics.total_time += duration
        
        await self.batch_processor.record_processing_time(duration)
    
    async def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        # Update memory usage
        import psutil
        import os
        process = psutil.Process(os.getpid())
        self.metrics.memory_usage = process.memory_info().rss
        
        # Update cache hit rate
        cache_size = await self.cache.size()
        self.metrics.cache_hit_rate = min(1.0, cache_size / 1000)  # Normalized
        
        return self.metrics
    
    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        while self._running:
            try:
                await self.resource_monitor.optimize_if_needed()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _cleanup_expired_pools(self) -> None:
        """Clean up expired connection pools."""
        # Implementation for pool cleanup
        pass


# Global performance optimizer instance
_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


@asynccontextmanager
async def performance_monitor(operation_name: str):
    """Context manager for performance monitoring."""
    start_time = time.time()
    optimizer = get_performance_optimizer()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        await optimizer.record_operation(operation_name, duration)
        
        if duration > 1.0:  # Log slow operations
            logger.warning(f"Slow operation: {operation_name} took {duration:.3f}s")
