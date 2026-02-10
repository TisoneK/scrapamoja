"""
Memory Monitor

Specialized monitoring for memory resources with leak detection,
garbage collection, and automatic cleanup capabilities.
"""

import gc
import psutil
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque

from ..models.resource import Resource, ResourceMetrics, ResourceStatus, ResourceType
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_resource_event


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a specific point in time."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_memory: int = 0
    available_memory: int = 0
    used_memory: int = 0
    memory_percent: float = 0.0
    process_memory: int = 0
    process_percent: float = 0.0
    gc_stats: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_memory": self.total_memory,
            "available_memory": self.available_memory,
            "used_memory": self.used_memory,
            "memory_percent": self.memory_percent,
            "process_memory": self.process_memory,
            "process_percent": self.process_percent,
            "gc_stats": self.gc_stats
        }


@dataclass
class MemoryLeakInfo:
    """Information about a potential memory leak."""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    leak_rate: float = 0.0  # MB per hour
    confidence: float = 0.0  # 0.0 to 1.0
    affected_objects: List[str] = field(default_factory=list)
    memory_growth: List[Tuple[datetime, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "detected_at": self.detected_at.isoformat(),
            "leak_rate": self.leak_rate,
            "confidence": self.confidence,
            "affected_objects": self.affected_objects,
            "memory_growth": [(t.isoformat(), v) for t, v in self.memory_growth]
        }


class MemoryMonitor:
    """Monitors memory usage and detects leaks with automatic cleanup."""
    
    def __init__(self, monitoring_interval: int = 30):
        """
        Initialize memory monitor.
        
        Args:
            monitoring_interval: Monitoring interval in seconds
        """
        self.monitoring_interval = monitoring_interval
        self.logger = get_logger("memory_monitor")
        
        # Memory history
        self.memory_history: deque = deque(maxlen=1000)
        self.process_memory_history: deque = deque(maxlen=1000)
        
        # Leak detection
        self.leak_detection_enabled = True
        self.leak_threshold_mb_per_hour = 100.0
        self.leak_confidence_threshold = 0.7
        self.detected_leaks: List[MemoryLeakInfo] = []
        
        # Automatic cleanup
        self.auto_gc_enabled = True
        self.gc_threshold_percent = 85.0
        self.gc_cooldown_minutes = 5
        self.last_gc_time: Optional[datetime] = None
        
        # Process handle
        self.process = psutil.Process()
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_monitoring(self) -> None:
        """Start memory monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info(
            "Memory monitoring started",
            event_type="memory_monitoring_started",
            correlation_id=get_correlation_id(),
            context={
                "monitoring_interval": self.monitoring_interval,
                "leak_detection_enabled": self.leak_detection_enabled,
                "auto_gc_enabled": self.auto_gc_enabled
            },
            component="memory_monitor"
        )
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(
            "Memory monitoring stopped",
            event_type="memory_monitoring_stopped",
            correlation_id=get_correlation_id(),
            component="memory_monitor"
        )
    
    async def get_memory_snapshot(self) -> MemorySnapshot:
        """
        Get current memory snapshot.
        
        Returns:
            MemorySnapshot with current memory information
        """
        try:
            # System memory
            memory = psutil.virtual_memory()
            
            # Process memory
            process_memory = self.process.memory_info()
            process_percent = self.process.memory_percent()
            
            # GC stats
            gc_stats = {
                "counts": gc.get_count(),
                "thresholds": gc.get_threshold()
            }
            
            snapshot = MemorySnapshot(
                total_memory=memory.total,
                available_memory=memory.available,
                used_memory=memory.used,
                memory_percent=memory.percent,
                process_memory=process_memory.rss,
                process_percent=process_percent,
                gc_stats=gc_stats
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error(
                f"Failed to get memory snapshot: {str(e)}",
                event_type="memory_snapshot_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="memory_monitor"
            )
            return MemorySnapshot()
    
    async def get_memory_metrics(self) -> ResourceMetrics:
        """
        Get memory metrics for resource management.
        
        Returns:
            ResourceMetrics with current memory information
        """
        snapshot = await self.get_memory_snapshot()
        
        # Calculate trend from history
        trend = "stable"
        rate_of_change = 0.0
        
        if len(self.memory_history) >= 2:
            recent = list(self.memory_history)[-10:]  # Last 10 snapshots
            if len(recent) >= 2:
                first_percent = recent[0].memory_percent
                latest_percent = recent[-1].memory_percent
                
                if latest_percent > first_percent + 5:
                    trend = "increasing"
                elif latest_percent < first_percent - 5:
                    trend = "decreasing"
                
                # Calculate rate of change
                time_diff = (recent[-1].timestamp - recent[0].timestamp).total_seconds() / 3600  # hours
                if time_diff > 0:
                    rate_of_change = (latest_percent - first_percent) / time_diff
        
        return ResourceMetrics(
            current_value=snapshot.memory_percent,
            peak_value=max(s.memory_percent for s in self.memory_history) if self.memory_history else snapshot.memory_percent,
            average_value=sum(s.memory_percent for s in self.memory_history) / len(self.memory_history) if self.memory_history else snapshot.memory_percent,
            minimum_value=0.0,
            maximum_value=100.0,
            unit="percent",
            timestamp=snapshot.timestamp,
            samples_count=len(self.memory_history),
            trend=trend,
            rate_of_change=rate_of_change
        )
    
    async def force_garbage_collection(self) -> Dict[str, Any]:
        """
        Force garbage collection.
        
        Returns:
            GC results
        """
        try:
            # Get GC stats before
            before_stats = gc.get_stats()
            before_counts = gc.get_count()
            
            # Perform garbage collection
            collected = gc.collect()
            
            # Get GC stats after
            after_stats = gc.get_stats()
            after_counts = gc.get_count()
            
            # Get memory after GC
            after_snapshot = await self.get_memory_snapshot()
            
            self.last_gc_time = datetime.utcnow()
            
            results = {
                "collected_objects": collected,
                "before_counts": before_counts,
                "after_counts": after_counts,
                "before_stats": before_stats,
                "after_stats": after_stats,
                "memory_before": self.memory_history[-1].memory_percent if self.memory_history else 0,
                "memory_after": after_snapshot.memory_percent,
                "memory_freed_mb": (self.memory_history[-1].used_memory - after_snapshot.used_memory) / (1024 * 1024) if self.memory_history else 0,
                "timestamp": self.last_gc_time.isoformat()
            }
            
            # Publish event
            await publish_resource_event(
                action="garbage_collected",
                resource_id="system_memory",
                resource_type=ResourceType.MEMORY.value,
                context=results,
                component="memory_monitor"
            )
            
            self.logger.info(
                f"Garbage collection completed: {collected} objects collected",
                event_type="garbage_collection_completed",
                correlation_id=get_correlation_id(),
                context=results,
                component="memory_monitor"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                f"Failed to perform garbage collection: {str(e)}",
                event_type="garbage_collection_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="memory_monitor"
            )
            return {"error": str(e)}
    
    async def detect_memory_leaks(self) -> List[MemoryLeakInfo]:
        """
        Detect memory leaks based on historical data.
        
        Returns:
            List of detected memory leaks
        """
        if not self.leak_detection_enabled or len(self.memory_history) < 10:
            return []
        
        detected_leaks = []
        
        try:
            # Analyze system memory growth
            system_leak = await self._analyze_memory_growth(list(self.memory_history))
            if system_leak:
                detected_leaks.append(system_leak)
            
            # Analyze process memory growth
            process_leak = await self._analyze_process_memory_growth(list(self.process_memory_history))
            if process_leak:
                detected_leaks.append(process_leak)
            
            # Update detected leaks list
            self.detected_leaks.extend(detected_leaks)
            
            # Keep only recent leaks (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.detected_leaks = [
                leak for leak in self.detected_leaks
                if leak.detected_at >= cutoff_time
            ]
            
            return detected_leaks
            
        except Exception as e:
            self.logger.error(
                f"Failed to detect memory leaks: {str(e)}",
                event_type="memory_leak_detection_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="memory_monitor"
            )
            return []
    
    async def get_memory_history(
        self,
        hours: int = 1,
        include_process: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get memory history for specified time period.
        
        Args:
            hours: Number of hours of history to return
            include_process: Whether to include process memory history
            
        Returns:
            Dictionary with memory history
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        system_history = [
            snapshot.to_dict() for snapshot in self.memory_history
            if snapshot.timestamp >= cutoff_time
        ]
        
        result = {
            "system_memory": system_history
        }
        
        if include_process:
            process_history = [
                snapshot.to_dict() for snapshot in self.process_memory_history
                if snapshot.timestamp >= cutoff_time
            ]
            result["process_memory"] = process_history
        
        return result
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics.
        
        Returns:
            Memory statistics
        """
        current_snapshot = await self.get_memory_snapshot()
        
        # Calculate statistics from history
        if self.memory_history:
            memory_percentages = [s.memory_percent for s in self.memory_history]
            process_percentages = [s.process_percent for s in self.process_memory_history]
            
            system_stats = {
                "current": current_snapshot.memory_percent,
                "min": min(memory_percentages),
                "max": max(memory_percentages),
                "average": sum(memory_percentages) / len(memory_percentages),
                "trend": self._calculate_trend(memory_percentages),
                "samples": len(memory_percentages)
            }
            
            process_stats = {
                "current": current_snapshot.process_percent,
                "min": min(process_percentages),
                "max": max(process_percentages),
                "average": sum(process_percentages) / len(process_percentages),
                "trend": self._calculate_trend(process_percentages),
                "samples": len(process_percentages)
            }
        else:
            system_stats = {
                "current": current_snapshot.memory_percent,
                "min": current_snapshot.memory_percent,
                "max": current_snapshot.memory_percent,
                "average": current_snapshot.memory_percent,
                "trend": "stable",
                "samples": 1
            }
            
            process_stats = {
                "current": current_snapshot.process_percent,
                "min": current_snapshot.process_percent,
                "max": current_snapshot.process_percent,
                "average": current_snapshot.process_percent,
                "trend": "stable",
                "samples": 1
            }
        
        return {
            "system_memory": system_stats,
            "process_memory": process_stats,
            "gc_stats": current_snapshot.gc_stats,
            "leak_detection": {
                "enabled": self.leak_detection_enabled,
                "detected_leaks": len(self.detected_leaks),
                "leak_threshold_mb_per_hour": self.leak_threshold_mb_per_hour
            },
            "auto_gc": {
                "enabled": self.auto_gc_enabled,
                "threshold_percent": self.gc_threshold_percent,
                "last_gc": self.last_gc_time.isoformat() if self.last_gc_time else None
            },
            "monitoring": {
                "running": self._running,
                "interval": self.monitoring_interval,
                "history_samples": len(self.memory_history)
            }
        }
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Get current memory snapshot
                snapshot = await self.get_memory_snapshot()
                
                # Store in history
                self.memory_history.append(snapshot)
                self.process_memory_history.append(snapshot)
                
                # Check for automatic garbage collection
                if self.auto_gc_enabled and await self._should_trigger_gc(snapshot):
                    await self.force_garbage_collection()
                
                # Detect memory leaks
                if self.leak_detection_enabled:
                    await self.detect_memory_leaks()
                
                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in memory monitoring loop: {str(e)}",
                    event_type="memory_monitoring_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="memory_monitor"
                )
                await asyncio.sleep(self.monitoring_interval)
    
    async def _should_trigger_gc(self, snapshot: MemorySnapshot) -> bool:
        """Check if garbage collection should be triggered."""
        if not self.auto_gc_enabled:
            return False
        
        # Check memory threshold
        if snapshot.memory_percent >= self.gc_threshold_percent:
            # Check cooldown
            if self.last_gc_time:
                time_since_gc = (datetime.utcnow() - self.last_gc_time).total_seconds() / 60
                if time_since_gc >= self.gc_cooldown_minutes:
                    return True
            else:
                return True
        
        return False
    
    async def _analyze_memory_growth(self, history: List[MemorySnapshot]) -> Optional[MemoryLeakInfo]:
        """Analyze system memory growth for leaks."""
        if len(history) < 10:
            return None
        
        try:
            # Calculate growth rate
            time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 3600  # hours
            memory_growth = history[-1].used_memory - history[0].used_memory
            growth_rate_mb_per_hour = memory_growth / (1024 * 1024) / time_span
            
            # Check if growth rate exceeds threshold
            if growth_rate_mb_per_hour > self.leak_threshold_mb_per_hour:
                # Calculate confidence based on consistency
                confidence = self._calculate_leak_confidence(history)
                
                if confidence >= self.leak_confidence_threshold:
                    return MemoryLeakInfo(
                        leak_rate=growth_rate_mb_per_hour,
                        confidence=confidence,
                        memory_growth=[(s.timestamp, s.memory_percent) for s in history[-10:]]
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(
                f"Error analyzing memory growth: {str(e)}",
                event_type="memory_growth_analysis_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="memory_monitor"
            )
            return None
    
    async def _analyze_process_memory_growth(self, history: List[MemorySnapshot]) -> Optional[MemoryLeakInfo]:
        """Analyze process memory growth for leaks."""
        if len(history) < 10:
            return None
        
        try:
            # Calculate growth rate
            time_span = (history[-1].timestamp - history[0].timestamp).total_seconds() / 3600  # hours
            memory_growth = history[-1].process_memory - history[0].process_memory
            growth_rate_mb_per_hour = memory_growth / (1024 * 1024) / time_span
            
            # Check if growth rate exceeds threshold
            if growth_rate_mb_per_hour > self.leak_threshold_mb_per_hour:
                # Calculate confidence based on consistency
                confidence = self._calculate_leak_confidence(history)
                
                if confidence >= self.leak_confidence_threshold:
                    return MemoryLeakInfo(
                        leak_rate=growth_rate_mb_per_hour,
                        confidence=confidence,
                        memory_growth=[(s.timestamp, s.process_percent) for s in history[-10:]]
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(
                f"Error analyzing process memory growth: {str(e)}",
                event_type="process_memory_growth_analysis_error",
                correlation_id=get_correlation_id(),
                context={"error": str(e)},
                component="memory_monitor"
            )
            return None
    
    def _calculate_leak_confidence(self, history: List[MemorySnapshot]) -> float:
        """Calculate confidence level for leak detection."""
        if len(history) < 5:
            return 0.0
        
        try:
            # Calculate correlation between time and memory usage
            timestamps = [(s.timestamp - history[0].timestamp).total_seconds() for s in history]
            memory_values = [s.memory_percent for s in history]
            
            # Simple linear correlation calculation
            n = len(timestamps)
            sum_x = sum(timestamps)
            sum_y = sum(memory_values)
            sum_xy = sum(x * y for x, y in zip(timestamps, memory_values))
            sum_x2 = sum(x * x for x in timestamps)
            sum_y2 = sum(y * y for y in memory_values)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
            
            if denominator == 0:
                return 0.0
            
            correlation = abs(numerator / denominator)
            
            # Convert correlation to confidence (0.0 to 1.0)
            confidence = min(1.0, correlation)
            
            return confidence
            
        except Exception:
            return 0.0
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from a list of values."""
        if len(values) < 2:
            return "stable"
        
        # Simple trend calculation
        recent_values = values[-5:]  # Last 5 values
        if len(recent_values) < 2:
            return "stable"
        
        first_avg = sum(recent_values[:2]) / 2
        last_avg = sum(recent_values[-2:]) / 2
        
        if last_avg > first_avg + 3:
            return "increasing"
        elif last_avg < first_avg - 3:
            return "decreasing"
        else:
            return "stable"


# Global memory monitor instance
_memory_monitor = MemoryMonitor()


def get_memory_monitor() -> MemoryMonitor:
    """Get the global memory monitor instance."""
    return _memory_monitor


async def start_memory_monitoring() -> None:
    """Start memory monitoring using the global monitor."""
    await _memory_monitor.start_monitoring()


async def get_memory_metrics() -> ResourceMetrics:
    """Get memory metrics using the global monitor."""
    return await _memory_monitor.get_memory_metrics()


async def force_garbage_collection() -> Dict[str, Any]:
    """Force garbage collection using the global monitor."""
    return await _memory_monitor.force_garbage_collection()
