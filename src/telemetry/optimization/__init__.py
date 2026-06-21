"""
Telemetry optimization module for performance improvements.

This module provides optimization strategies and utilities for telemetry components.
"""

from .performance_optimizer import (
    PerformanceOptimizer,
    MemoryEfficientBuffer,
    ConnectionPool,
    LRUCache,
    BatchProcessor,
    ResourceMonitor,
    get_performance_optimizer,
    performance_monitor,
)

__all__ = [
    'PerformanceOptimizer',
    'MemoryEfficientBuffer', 
    'ConnectionPool',
    'LRUCache',
    'BatchProcessor',
    'ResourceMonitor',
    'get_performance_optimizer',
    'performance_monitor',
]
