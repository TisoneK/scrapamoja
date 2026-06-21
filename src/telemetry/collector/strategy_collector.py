"""
Strategy Usage Tracking Collector

Specialized collector for strategy metrics and usage patterns with
effectiveness analysis and performance tracking capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
from statistics import mean, median

from ..models import StrategyMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryCollectionError
from ..configuration.logging import get_logger


@dataclass
class StrategyStats:
    """Statistics for strategy usage."""
    total_usage: int = 0
    successful_usage: int = 0
    failed_usage: int = 0
    success_rate: float = 0.0
    average_execution_time_ms: float = 0.0
    median_execution_time_ms: float = 0.0
    min_execution_time_ms: float = 0.0
    max_execution_time_ms: float = 0.0
    primary_usage_count: int = 0
    secondary_usage_count: int = 0
    switches_triggered: int = 0
    effectiveness_score: float = 0.0
    last_used: Optional[datetime] = None


@dataclass
class StrategyEffectiveness:
    """Effectiveness metrics for a strategy."""
    strategy_name: str
    success_rate: float
    average_confidence: float
    average_execution_time_ms: float
    usage_frequency: float
    reliability_score: float
    performance_score: float
    overall_effectiveness: float


class StrategyCollector:
    """
    Specialized collector for strategy metrics and usage patterns.
    
    Provides comprehensive strategy tracking, effectiveness analysis,
    and performance monitoring for selector operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize strategy collector.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("strategy_collector")
        
        # Strategy configuration
        self.max_samples = config.get("max_strategy_samples", 10000)
        self.effectiveness_window = timedelta(hours=config.get("effectiveness_window_hours", 24))
        
        # Strategy storage
        self._strategy_samples: List[Dict[str, Any]] = []
        self._strategy_stats: Dict[str, StrategyStats] = {}
        self._stats_lock = asyncio.Lock()
        
        # Strategy effectiveness tracking
        self._effectiveness_cache: Dict[str, StrategyEffectiveness] = {}
        self._effectiveness_cache_time: Dict[str, datetime] = {}
        
        # Collection state
        self._enabled = True
        self._collection_count = 0
        self._error_count = 0
    
    async def collect_strategy_metrics(
        self,
        selector_name: str,
        operation_type: str,
        primary_strategy: str,
        secondary_strategies: Optional[List[str]] = None,
        strategy_execution_order: Optional[List[str]] = None,
        strategy_success_by_type: Optional[Dict[str, bool]] = None,
        strategy_timing_by_type: Optional[Dict[str, float]] = None,
        strategy_switches_count: int = 0,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> StrategyMetrics:
        """
        Collect strategy metrics for an operation.
        
        Args:
            selector_name: Name of selector
            operation_type: Type of operation
            primary_strategy: Primary strategy used
            secondary_strategies: List of secondary strategies
            strategy_execution_order: Order of strategy execution
            strategy_success_by_type: Success status by strategy type
            strategy_timing_by_type: Execution timing by strategy type
            strategy_switches_count: Number of strategy switches
            additional_metrics: Additional strategy metrics
            
        Returns:
            StrategyMetrics instance
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            if not self._enabled:
                raise TelemetryCollectionError(
                    "Strategy collector is disabled",
                    error_code="TEL-501"
                )
            
            # Create strategy metrics
            metrics = StrategyMetrics(
                primary_strategy=primary_strategy,
                secondary_strategies=secondary_strategies or [],
                strategy_execution_order=strategy_execution_order or [],
                strategy_success_by_type=strategy_success_by_type or {},
                strategy_timing_by_type=strategy_timing_by_type or {},
                strategy_switches_count=strategy_switches_count
            )
            
            # Store strategy sample
            await self._store_strategy_sample(
                selector_name,
                operation_type,
                metrics,
                additional_metrics
            )
            
            # Update statistics
            await self._update_statistics(selector_name, metrics)
            
            self._collection_count += 1
            
            self.logger.debug(
                "Strategy metrics collected",
                selector_name=selector_name,
                primary_strategy=primary_strategy,
                switches_count=strategy_switches_count
            )
            
            return metrics
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Failed to collect strategy metrics",
                selector_name=selector_name,
                primary_strategy=primary_strategy,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect strategy metrics: {e}",
                error_code="TEL-502"
            )
    
    async def analyze_strategy_effectiveness(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[StrategyEffectiveness]:
        """
        Analyze strategy effectiveness.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            List of strategy effectiveness metrics
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return []
            
            # Group samples by strategy
            strategy_groups = defaultdict(list)
            
            for sample in samples:
                metrics = sample["metrics"]
                primary_strategy = metrics.get("primary_strategy")
                
                if primary_strategy:
                    strategy_groups[primary_strategy].append(sample)
            
            # Calculate effectiveness for each strategy
            effectiveness_list = []
            
            for strategy_name, strategy_samples in strategy_groups.items():
                effectiveness = await self._calculate_strategy_effectiveness(
                    strategy_name,
                    strategy_samples
                )
                
                if effectiveness:
                    effectiveness_list.append(effectiveness)
            
            # Sort by overall effectiveness
            effectiveness_list.sort(key=lambda x: x.overall_effectiveness, reverse=True)
            
            return effectiveness_list
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze strategy effectiveness",
                selector_name=selector_name,
                error=str(e)
            )
            return []
    
    async def get_strategy_usage_patterns(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze strategy usage patterns.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Strategy usage pattern analysis
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Analyze usage patterns
            patterns = {
                "total_operations": len(samples),
                "primary_strategies": defaultdict(int),
                "secondary_strategies": defaultdict(int),
                "strategy_switches": {
                    "total": sum(sample["metrics"].get("strategy_switches_count", 0) for sample in samples),
                    "average": 0,
                    "max": 0,
                    "distribution": defaultdict(int)
                },
                "execution_orders": defaultdict(int),
                "time_of_day_patterns": defaultdict(lambda: defaultdict(int))
            }
            
            # Process samples
            for sample in samples:
                metrics = sample["metrics"]
                
                # Primary strategy usage
                primary = metrics.get("primary_strategy")
                if primary:
                    patterns["primary_strategies"][primary] += 1
                
                # Secondary strategy usage
                secondary = metrics.get("secondary_strategies", [])
                for strategy in secondary:
                    patterns["secondary_strategies"][strategy] += 1
                
                # Strategy switches
                switches = metrics.get("strategy_switches_count", 0)
                patterns["strategy_switches"]["distribution"][switches] += 1
                
                # Execution orders
                execution_order = metrics.get("strategy_execution_order", [])
                if execution_order:
                    order_key = "->".join(execution_order)
                    patterns["execution_orders"][order_key] += 1
                
                # Time of day patterns
                hour = sample["timestamp"].hour
                if primary:
                    patterns["time_of_day_patterns"][hour][primary] += 1
            
            # Calculate averages and percentages
            total_ops = patterns["total_operations"]
            
            # Convert to percentages
            patterns["primary_strategy_percentages"] = {
                strategy: (count / total_ops) * 100
                for strategy, count in patterns["primary_strategies"].items()
            }
            
            patterns["secondary_strategy_percentages"] = {
                strategy: (count / total_ops) * 100
                for strategy, count in patterns["secondary_strategies"].items()
            }
            
            # Strategy switches statistics
            if patterns["strategy_switches"]["total"] > 0:
                patterns["strategy_switches"]["average"] = (
                    patterns["strategy_switches"]["total"] / total_ops
                )
                patterns["strategy_switches"]["max"] = max(patterns["strategy_switches"]["distribution"].keys())
            
            return dict(patterns)
            
        except Exception as e:
            self.logger.error(
                "Failed to get strategy usage patterns",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def detect_strategy_anomalies(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect strategy usage anomalies.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if len(samples) < 10:
                return anomalies  # Not enough data for anomaly detection
            
            # Group by selector for individual analysis
            selector_samples = defaultdict(list)
            for sample in samples:
                sel_name = sample["selector_name"]
                selector_samples[sel_name].append(sample)
            
            # Analyze each selector
            for sel_name, sel_samples in selector_samples.items():
                if len(sel_samples) < 5:
                    continue
                
                # Detect excessive strategy switching
                switches = [
                    sample["metrics"].get("strategy_switches_count", 0)
                    for sample in sel_samples
                ]
                
                avg_switches = mean(switches)
                if avg_switches > 2:  # More than 2 switches on average
                    anomalies.append({
                        "selector_name": sel_name,
                        "anomaly_type": "excessive_strategy_switching",
                        "average_switches": avg_switches,
                        "max_switches": max(switches),
                        "samples_count": len(switches),
                        "severity": "high" if avg_switches > 5 else "medium"
                    })
                
                # Detect strategy failure patterns
                strategy_failures = defaultdict(int)
                strategy_usage = defaultdict(int)
                
                for sample in sel_samples:
                    metrics = sample["metrics"]
                    primary = metrics.get("primary_strategy")
                    success_by_type = metrics.get("strategy_success_by_type", {})
                    
                    if primary:
                        strategy_usage[primary] += 1
                        if not success_by_type.get(primary, True):
                            strategy_failures[primary] += 1
                
                # Check for high failure rates
                for strategy, usage_count in strategy_usage.items():
                    if usage_count >= 5:  # Only analyze strategies with sufficient usage
                        failure_count = strategy_failures[strategy]
                        failure_rate = failure_count / usage_count
                        
                        if failure_rate > 0.5:  # More than 50% failure rate
                            anomalies.append({
                                "selector_name": sel_name,
                                "anomaly_type": "high_strategy_failure_rate",
                                "strategy_name": strategy,
                                "failure_rate": failure_rate,
                                "failure_count": failure_count,
                                "usage_count": usage_count,
                                "severity": "high" if failure_rate > 0.8 else "medium"
                            })
                
                # Detect unusual execution order patterns
                execution_orders = [
                    "->".join(sample["metrics"].get("strategy_execution_order", []))
                    for sample in sel_samples
                    if sample["metrics"].get("strategy_execution_order")
                ]
                
                if len(execution_orders) >= 5:
                    order_counts = defaultdict(int)
                    for order in execution_orders:
                        order_counts[order] += 1
                    
                    # Check if there are too many different execution orders
                    if len(order_counts) > len(execution_orders) * 0.5:  # More than 50% unique orders
                        anomalies.append({
                            "selector_name": sel_name,
                            "anomaly_type": "inconsistent_execution_order",
                            "unique_orders": len(order_counts),
                            "total_orders": len(execution_orders),
                            "order_diversity": len(order_counts) / len(execution_orders),
                            "severity": "medium"
                        })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(
                "Failed to detect strategy anomalies",
                selector_name=selector_name,
                error=str(e)
            )
            return []
    
    async def get_strategy_performance_comparison(
        self,
        strategies: List[str],
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Compare performance between specific strategies.
        
        Args:
            strategies: List of strategy names to compare
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Strategy performance comparison
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Filter samples for specified strategies
            strategy_data = {}
            
            for strategy in strategies:
                strategy_samples = [
                    sample for sample in samples
                    if sample["metrics"].get("primary_strategy") == strategy
                ]
                
                if strategy_samples:
                    strategy_data[strategy] = strategy_samples
            
            if not strategy_data:
                return {}
            
            # Calculate comparison metrics
            comparison = {
                "strategies_compared": list(strategy_data.keys()),
                "total_samples": sum(len(samples) for samples in strategy_data.values()),
                "strategy_metrics": {}
            }
            
            for strategy, strat_samples in strategy_data.items():
                # Extract metrics
                success_count = sum(
                    1 for sample in strat_samples
                    if sample["metrics"].get("strategy_success_by_type", {}).get(strategy, True)
                )
                
                execution_times = [
                    sample["metrics"].get("strategy_timing_by_type", {}).get(strategy, 0)
                    for sample in strat_samples
                    if strategy in sample["metrics"].get("strategy_timing_by_type", {})
                ]
                
                confidence_scores = []
                for sample in strat_samples:
                    # Try to get confidence from additional metrics
                    additional = sample.get("additional_metrics", {})
                    if "confidence_score" in additional:
                        confidence_scores.append(additional["confidence_score"])
                
                # Calculate statistics
                metrics = {
                    "usage_count": len(strat_samples),
                    "success_count": success_count,
                    "success_rate": success_count / len(strat_samples),
                    "average_execution_time_ms": mean(execution_times) if execution_times else 0,
                    "median_execution_time_ms": median(execution_times) if execution_times else 0,
                    "min_execution_time_ms": min(execution_times) if execution_times else 0,
                    "max_execution_time_ms": max(execution_times) if execution_times else 0
                }
                
                if confidence_scores:
                    metrics.update({
                        "average_confidence": mean(confidence_scores),
                        "median_confidence": median(confidence_scores),
                        "min_confidence": min(confidence_scores),
                        "max_confidence": max(confidence_scores)
                    })
                
                comparison["strategy_metrics"][strategy] = metrics
            
            # Calculate rankings
            if len(comparison["strategy_metrics"]) > 1:
                # Rank by success rate
                success_ranking = sorted(
                    comparison["strategy_metrics"].items(),
                    key=lambda x: x[1]["success_rate"],
                    reverse=True
                )
                
                # Rank by execution time (lower is better)
                time_ranking = sorted(
                    comparison["strategy_metrics"].items(),
                    key=lambda x: x[1]["average_execution_time_ms"]
                )
                
                comparison["rankings"] = {
                    "by_success_rate": [(name, idx + 1) for idx, (name, _) in enumerate(success_ranking)],
                    "by_execution_time": [(name, idx + 1) for idx, (name, _) in enumerate(time_ranking)]
                }
            
            return comparison
            
        except Exception as e:
            self.logger.error(
                "Failed to get strategy performance comparison",
                strategies=strategies,
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_strategy_statistics(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive strategy statistics.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for statistics
            
        Returns:
            Strategy statistics
        """
        try:
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name, time_window)
            
            if not samples:
                return {}
            
            # Extract strategy information
            primary_strategies = [
                sample["metrics"].get("primary_strategy")
                for sample in samples
                if sample["metrics"].get("primary_strategy")
            ]
            
            secondary_strategies = []
            for sample in samples:
                secondary = sample["metrics"].get("secondary_strategies", [])
                secondary_strategies.extend(secondary)
            
            strategy_switches = [
                sample["metrics"].get("strategy_switches_count", 0)
                for sample in samples
            ]
            
            # Calculate statistics
            stats = {
                "total_operations": len(samples),
                "unique_primary_strategies": len(set(primary_strategies)),
                "unique_secondary_strategies": len(set(secondary_strategies)),
                "total_strategy_switches": sum(strategy_switches),
                "average_switches_per_operation": mean(strategy_switches) if strategy_switches else 0,
                "max_switches": max(strategy_switches) if strategy_switches else 0
            }
            
            # Primary strategy distribution
            if primary_strategies:
                primary_counts = defaultdict(int)
                for strategy in primary_strategies:
                    primary_counts[strategy] += 1
                
                stats["primary_strategy_distribution"] = dict(primary_counts)
                stats["most_used_primary_strategy"] = max(primary_counts, key=primary_counts.get)
            
            # Secondary strategy distribution
            if secondary_strategies:
                secondary_counts = defaultdict(int)
                for strategy in secondary_strategies:
                    secondary_counts[strategy] += 1
                
                stats["secondary_strategy_distribution"] = dict(secondary_counts)
                stats["most_used_secondary_strategy"] = max(secondary_counts, key=secondary_counts.get)
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get strategy statistics",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics
        """
        return {
            "total_collections": self._collection_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._collection_count),
            "samples_stored": len(self._strategy_samples),
            "selectors_tracked": len(set(s["selector_name"] for s in self._strategy_samples)),
            "strategies_tracked": len(set(
                s["metrics"].get("primary_strategy") 
                for s in self._strategy_samples 
                if s["metrics"].get("primary_strategy")
            )),
            "enabled": self._enabled,
            "max_samples": self.max_samples
        }
    
    async def enable_collection(self) -> None:
        """Enable strategy collection."""
        self._enabled = True
        self.logger.info("Strategy collection enabled")
    
    async def disable_collection(self) -> None:
        """Disable strategy collection."""
        self._enabled = False
        self.logger.info("Strategy collection disabled")
    
    async def clear_samples(self, selector_name: Optional[str] = None) -> int:
        """
        Clear strategy samples.
        
        Args:
            selector_name: Optional selector filter
            
        Returns:
            Number of samples cleared
        """
        async with self._stats_lock:
            if selector_name:
                original_count = len(self._strategy_samples)
                self._strategy_samples = [
                    sample for sample in self._strategy_samples
                    if sample["selector_name"] != selector_name
                ]
                cleared_count = original_count - len(self._strategy_samples)
                
                # Clear selector statistics
                if selector_name in self._strategy_stats:
                    del self._strategy_stats[selector_name]
            else:
                cleared_count = len(self._strategy_samples)
                self._strategy_samples.clear()
                self._strategy_stats.clear()
            
            self.logger.info(
                "Strategy samples cleared",
                selector_name=selector_name or "all",
                cleared_count=cleared_count
            )
            
            return cleared_count
    
    # Private methods
    
    async def _store_strategy_sample(
        self,
        selector_name: str,
        operation_type: str,
        metrics: StrategyMetrics,
        additional_metrics: Optional[Dict[str, Any]]
    ) -> None:
        """Store strategy sample."""
        sample = {
            "selector_name": selector_name,
            "operation_type": operation_type,
            "metrics": metrics.to_dict(),
            "additional_metrics": additional_metrics or {},
            "timestamp": datetime.utcnow()
        }
        
        async with self._stats_lock:
            self._strategy_samples.append(sample)
            
            # Limit sample size
            if len(self._strategy_samples) > self.max_samples:
                self._strategy_samples = self._strategy_samples[-self.max_samples:]
    
    async def _update_statistics(self, selector_name: str, metrics: StrategyMetrics) -> None:
        """Update strategy statistics for selector."""
        async with self._stats_lock:
            # Update primary strategy stats
            primary_strategy = metrics.primary_strategy
            if primary_strategy:
                if primary_strategy not in self._strategy_stats:
                    self._strategy_stats[primary_strategy] = StrategyStats()
                
                stats = self._strategy_stats[primary_strategy]
                stats.total_usage += 1
                stats.last_used = datetime.utcnow()
                
                # Check if primary strategy succeeded
                success = metrics.strategy_success_by_type.get(primary_strategy, True)
                if success:
                    stats.successful_usage += 1
                else:
                    stats.failed_usage += 1
                
                stats.success_rate = stats.successful_usage / stats.total_usage
                
                # Update execution time stats
                timing = metrics.strategy_timing_by_type.get(primary_strategy)
                if timing is not None:
                    await self._update_timing_stats(primary_strategy, timing)
                
                # Update switches count
                stats.switches_triggered += metrics.strategy_switches_count
    
    async def _update_timing_stats(self, strategy_name: str, execution_time_ms: float) -> None:
        """Update timing statistics for strategy."""
        stats = self._strategy_stats[strategy_name]
        
        # Get all execution times for this strategy
        execution_times = [
            sample["metrics"].get("strategy_timing_by_type", {}).get(strategy_name, 0)
            for sample in self._strategy_samples
            if strategy_name in sample["metrics"].get("strategy_timing_by_type", {})
        ]
        
        if execution_times:
            stats.average_execution_time_ms = mean(execution_times)
            stats.median_execution_time_ms = median(execution_times)
            stats.min_execution_time_ms = min(execution_times)
            stats.max_execution_time_ms = max(execution_times)
    
    async def _calculate_strategy_effectiveness(
        self,
        strategy_name: str,
        strategy_samples: List[Dict[str, Any]]
    ) -> Optional[StrategyEffectiveness]:
        """Calculate effectiveness metrics for a strategy."""
        try:
            if not strategy_samples:
                return None
            
            # Extract metrics
            success_count = 0
            execution_times = []
            confidence_scores = []
            
            for sample in strategy_samples:
                metrics = sample["metrics"]
                
                # Success rate
                if metrics.get("strategy_success_by_type", {}).get(strategy_name, True):
                    success_count += 1
                
                # Execution time
                timing = metrics.get("strategy_timing_by_type", {}).get(strategy_name)
                if timing is not None:
                    execution_times.append(timing)
                
                # Confidence score
                additional = sample.get("additional_metrics", {})
                if "confidence_score" in additional:
                    confidence_scores.append(additional["confidence_score"])
            
            # Calculate metrics
            total_usage = len(strategy_samples)
            success_rate = success_count / total_usage
            avg_execution_time = mean(execution_times) if execution_times else 0
            avg_confidence = mean(confidence_scores) if confidence_scores else 0
            
            # Calculate component scores
            reliability_score = success_rate
            performance_score = 1.0 / (1.0 + avg_execution_time / 1000) if avg_execution_time > 0 else 1.0
            
            # Overall effectiveness (weighted average)
            overall_effectiveness = (
                reliability_score * 0.5 +
                avg_confidence * 0.3 +
                performance_score * 0.2
            )
            
            return StrategyEffectiveness(
                strategy_name=strategy_name,
                success_rate=success_rate,
                average_confidence=avg_confidence,
                average_execution_time_ms=avg_execution_time,
                usage_frequency=total_usage,
                reliability_score=reliability_score,
                performance_score=performance_score,
                overall_effectiveness=overall_effectiveness
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate strategy effectiveness",
                strategy_name=strategy_name,
                error=str(e)
            )
            return None
    
    async def _get_filtered_samples(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered strategy samples."""
        samples = self._strategy_samples.copy()
        
        if selector_name:
            samples = [
                sample for sample in samples
                if sample["selector_name"] == selector_name
            ]
        
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            samples = [
                sample for sample in samples
                if sample["timestamp"] >= cutoff_time
            ]
        
        return samples
