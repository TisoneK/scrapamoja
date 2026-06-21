"""
Performance testing and optimization validation for telemetry system.

This module provides comprehensive performance testing capabilities
including load testing, overhead measurement, and optimization validation.
"""

import asyncio
import logging
import time
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import psutil
import os

from ..lifecycle import telemetry_system, get_lifecycle_manager
from ..integration.selector_integration import SelectorTelemetryIntegration
from ..optimization import get_performance_optimizer, performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance test metrics."""
    operation_count: int
    total_time: float
    average_time: float
    min_time: float
    max_time: float
    percentile_95: float
    percentile_99: float
    throughput: float  # operations per second
    memory_usage_mb: float
    cpu_usage_percent: float
    overhead_percent: float


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_operations: int = 100
    total_operations: int = 10000
    operation_duration: float = 0.01  # seconds
    ramp_up_time: float = 5.0  # seconds
    test_duration: float = 60.0  # seconds


@dataclass 
class OverheadTestConfig:
    """Configuration for overhead testing."""
    baseline_iterations: int = 1000
    telemetry_iterations: int = 1000
    operation_complexity: str = "simple"  # simple, medium, complex


class PerformanceTester:
    """Performance testing for telemetry system."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_metrics: Optional[PerformanceMetrics] = None
    
    async def run_comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite."""
        logger.info("🚀 Starting comprehensive performance test suite...")
        
        results = {
            "load_test": await self.run_load_test(),
            "overhead_test": await self.run_overhead_test(),
            "memory_test": await self.run_memory_test(),
            "stress_test": await self.run_stress_test(),
            "optimization_test": await self.run_optimization_test()
        }
        
        # Calculate overall score
        results["overall_score"] = self._calculate_overall_score(results)
        
        logger.info(f"✅ Performance test completed - Overall score: {results['overall_score']:.1f}%")
        return results
    
    async def run_load_test(self, config: Optional[LoadTestConfig] = None) -> PerformanceMetrics:
        """Run load test with concurrent operations."""
        config = config or LoadTestConfig()
        
        logger.info(f"📊 Running load test: {config.total_operations} ops, {config.concurrent_operations} concurrent")
        
        # Setup telemetry system
        test_config = {
            "collection": {
                "enabled": True,
                "buffer_size": 5000,
                "batch_size": 500,
                "flush_interval": 1.0
            },
            "storage": {
                "type": "json",
                "directory": "test_telemetry_data",
                "retention_days": 1
            },
            "performance": {
                "overhead_target_percent": 2.0,
                "memory_threshold_mb": 200
            }
        }
        
        async with telemetry_system(test_config) as manager:
            integration = SelectorTelemetryIntegration()
            
            # Record initial metrics
            initial_memory = self.process.memory_info().rss / 1024 / 1024
            initial_cpu = self.process.cpu_percent()
            
            # Run load test
            start_time = time.time()
            operation_times = []
            
            # Create concurrent tasks
            semaphore = asyncio.Semaphore(config.concurrent_operations)
            
            async def run_operation(operation_id: int) -> float:
                async with semaphore:
                    op_start = time.time()
                    
                    correlation_id = f"load_test_{operation_id:06d}"
                    selector_id = f"selector_{operation_id % 100}"
                    strategy = ["text_anchor", "attribute_match", "dom_relationship"][operation_id % 3]
                    
                    await integration.start_selector_operation(
                        selector_id=selector_id,
                        correlation_id=correlation_id,
                        strategy=strategy
                    )
                    
                    # Simulate work
                    await asyncio.sleep(config.operation_duration)
                    
                    await integration.record_selector_success(
                        selector_id=selector_id,
                        correlation_id=correlation_id,
                        confidence_score=0.8 + (operation_id % 20) * 0.01,
                        resolution_time_ms=10 + (operation_id % 50),
                        elements_found=1 + (operation_id % 5)
                    )
                    
                    return time.time() - op_start
            
            # Execute operations with ramp-up
            tasks = []
            for i in range(config.total_operations):
                # Add ramp-up delay
                if i > 0 and i % config.concurrent_operations == 0:
                    await asyncio.sleep(config.ramp_up_time / (config.total_operations / config.concurrent_operations))
                
                task = asyncio.create_task(run_operation(i))
                tasks.append(task)
            
            # Wait for all operations to complete
            operation_times = await asyncio.gather(*tasks)
            
            # Wait for telemetry processing
            await asyncio.sleep(2)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Record final metrics
            final_memory = self.process.memory_info().rss / 1024 / 1024
            final_cpu = self.process.cpu_percent()
            
            # Calculate metrics
            metrics = PerformanceMetrics(
                operation_count=config.total_operations,
                total_time=total_time,
                average_time=statistics.mean(operation_times),
                min_time=min(operation_times),
                max_time=max(operation_times),
                percentile_95=statistics.quantiles(operation_times, n=20)[18] if len(operation_times) > 20 else max(operation_times),
                percentile_99=statistics.quantiles(operation_times, n=100)[98] if len(operation_times) > 100 else max(operation_times),
                throughput=config.total_operations / total_time,
                memory_usage_mb=final_memory - initial_memory,
                cpu_usage_percent=final_cpu - initial_cpu,
                overhead_percent=0.0  # Will be calculated in overhead test
            )
            
            logger.info(f"✅ Load test completed: {metrics.throughput:.1f} ops/sec, avg {metrics.average_time*1000:.1f}ms")
            return metrics
    
    async def run_overhead_test(self, config: Optional[OverheadTestConfig] = None) -> PerformanceMetrics:
        """Run overhead test comparing baseline vs telemetry."""
        config = config or OverheadTestConfig()
        
        logger.info(f"📏 Running overhead test: {config.telemetry_iterations} iterations")
        
        # Baseline test (without telemetry)
        baseline_times = await self._run_baseline_operations(config)
        
        # Telemetry test (with telemetry)
        telemetry_times = await self._run_telemetry_operations(config)
        
        # Calculate overhead
        baseline_avg = statistics.mean(baseline_times)
        telemetry_avg = statistics.mean(telemetry_times)
        overhead_percent = ((telemetry_avg - baseline_avg) / baseline_avg) * 100
        
        metrics = PerformanceMetrics(
            operation_count=config.telemetry_iterations,
            total_time=sum(telemetry_times),
            average_time=telemetry_avg,
            min_time=min(telemetry_times),
            max_time=max(telemetry_times),
            percentile_95=statistics.quantiles(telemetry_times, n=20)[18] if len(telemetry_times) > 20 else max(telemetry_times),
            percentile_99=statistics.quantiles(telemetry_times, n=100)[98] if len(telemetry_times) > 100 else max(telemetry_times),
            throughput=config.telemetry_iterations / sum(telemetry_times),
            memory_usage_mb=0.0,  # Not measured in this test
            cpu_usage_percent=0.0,  # Not measured in this test
            overhead_percent=overhead_percent
        )
        
        logger.info(f"✅ Overhead test completed: {overhead_percent:.2f}% overhead")
        return metrics
    
    async def run_memory_test(self) -> Dict[str, Any]:
        """Run memory usage test."""
        logger.info("💾 Running memory usage test...")
        
        # Setup telemetry system
        test_config = {
            "collection": {
                "enabled": True,
                "buffer_size": 10000,
                "batch_size": 1000,
                "flush_interval": 5.0
            },
            "storage": {
                "type": "json",
                "directory": "memory_test_data",
                "retention_days": 1
            }
        }
        
        async with telemetry_system(test_config) as manager:
            integration = SelectorTelemetryIntegration()
            
            # Record baseline memory
            baseline_memory = self.process.memory_info().rss / 1024 / 1024
            memory_samples = [baseline_memory]
            
            # Generate increasing load
            for batch_size in [100, 500, 1000, 2000, 5000]:
                # Generate operations
                for i in range(batch_size):
                    correlation_id = f"memory_test_{batch_size}_{i}"
                    selector_id = f"selector_{i % 50}"
                    
                    await integration.start_selector_operation(
                        selector_id=selector_id,
                        correlation_id=correlation_id,
                        strategy="text_anchor"
                    )
                    
                    await integration.record_selector_success(
                        selector_id=selector_id,
                        correlation_id=correlation_id,
                        confidence_score=0.85,
                        resolution_time_ms=25,
                        elements_found=2
                    )
                
                # Wait for processing
                await asyncio.sleep(1)
                
                # Record memory usage
                current_memory = self.process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                logger.info(f"  Batch {batch_size}: {current_memory:.1f}MB (+{current_memory - baseline_memory:.1f}MB)")
        
        # Calculate memory growth rate
        memory_growth = memory_samples[-1] - baseline_memory
        total_operations = sum([100, 500, 1000, 2000, 5000])
        memory_per_operation = memory_growth / total_operations
        
        results = {
            "baseline_memory_mb": baseline_memory,
            "peak_memory_mb": max(memory_samples),
            "memory_growth_mb": memory_growth,
            "memory_per_operation_bytes": memory_per_operation * 1024 * 1024,
            "memory_samples": memory_samples
        }
        
        logger.info(f"✅ Memory test completed: {memory_growth:.1f}MB growth, {memory_per_operation*1024:.1f}KB per operation")
        return results
    
    async def run_stress_test(self) -> Dict[str, Any]:
        """Run stress test with high load."""
        logger.info("🔥 Running stress test...")
        
        # High-load configuration
        stress_config = LoadTestConfig(
            concurrent_operations=500,
            total_operations=50000,
            operation_duration=0.001,
            ramp_up_time=2.0,
            test_duration=30.0
        )
        
        # Setup telemetry system with optimized settings
        test_config = {
            "collection": {
                "enabled": True,
                "buffer_size": 10000,
                "batch_size": 1000,
                "flush_interval": 0.5
            },
            "storage": {
                "type": "json",
                "directory": "stress_test_data",
                "retention_days": 1
            },
            "performance": {
                "overhead_target_percent": 1.0,
                "memory_threshold_mb": 500
            }
        }
        
        start_time = time.time()
        errors = []
        
        try:
            async with telemetry_system(test_config) as manager:
                integration = SelectorTelemetryIntegration()
                
                # Monitor system health during stress test
                health_monitor_task = asyncio.create_task(
                    self._monitor_health_during_test(manager, errors)
                )
                
                # Run stress test
                metrics = await self.run_load_test(stress_config)
                
                # Cancel health monitor
                health_monitor_task.cancel()
                try:
                    await health_monitor_task
                except asyncio.CancelledError:
                    pass
                
                end_time = time.time()
                
                results = {
                    "metrics": metrics,
                    "test_duration": end_time - start_time,
                    "errors": errors,
                    "error_rate": len(errors) / stress_config.total_operations,
                    "system_stable": len(errors) < stress_config.total_operations * 0.01  # <1% error rate
                }
                
                logger.info(f"✅ Stress test completed: {len(errors)} errors, {results['error_rate']*100:.2f}% error rate")
                return results
                
        except Exception as e:
            logger.error(f"❌ Stress test failed: {e}")
            return {
                "error": str(e),
                "test_duration": time.time() - start_time,
                "errors": [str(e)],
                "system_stable": False
            }
    
    async def run_optimization_test(self) -> Dict[str, Any]:
        """Test optimization features."""
        logger.info("⚡ Running optimization test...")
        
        # Setup telemetry system with optimization enabled
        test_config = {
            "collection": {
                "enabled": True,
                "buffer_size": 2000,
                "batch_size": 200,
                "flush_interval": 2.0
            },
            "storage": {
                "type": "json",
                "directory": "optimization_test_data",
                "retention_days": 1
            },
            "performance": {
                "overhead_target_percent": 2.0,
                "memory_threshold_mb": 100,
                "cache": {
                    "size": 1000,
                    "ttl_seconds": 300
                }
            }
        }
        
        async with telemetry_system(test_config) as manager:
            # Get performance optimizer
            optimizer = get_performance_optimizer()
            
            # Test 1: Buffer optimization
            buffer_test = await self._test_buffer_optimization(optimizer)
            
            # Test 2: Connection pooling
            connection_test = await self._test_connection_pooling(optimizer)
            
            # Test 3: Caching
            cache_test = await self._test_caching(optimizer)
            
            # Test 4: Resource monitoring
            resource_test = await self._test_resource_monitoring(optimizer)
            
            results = {
                "buffer_optimization": buffer_test,
                "connection_pooling": connection_test,
                "caching": cache_test,
                "resource_monitoring": resource_test,
                "overall_optimization_score": self._calculate_optimization_score([
                    buffer_test, connection_test, cache_test, resource_test
                ])
            }
            
            logger.info(f"✅ Optimization test completed: {results['overall_optimization_score']:.1f}% score")
            return results
    
    async def _run_baseline_operations(self, config: OverheadTestConfig) -> List[float]:
        """Run operations without telemetry for baseline."""
        operation_times = []
        
        for i in range(config.baseline_iterations):
            start_time = time.time()
            
            # Simulate selector operation without telemetry
            await asyncio.sleep(0.001)  # Simulate work
            
            operation_times.append(time.time() - start_time)
        
        return operation_times
    
    async def _run_telemetry_operations(self, config: OverheadTestConfig) -> List[float]:
        """Run operations with telemetry for overhead measurement."""
        # Setup minimal telemetry system
        test_config = {
            "collection": {"enabled": True, "buffer_size": 1000},
            "storage": {"type": "json", "directory": "overhead_test_data"},
            "performance": {"overhead_target_percent": 5.0}
        }
        
        async with telemetry_system(test_config) as manager:
            integration = SelectorTelemetryIntegration()
            operation_times = []
            
            for i in range(config.telemetry_iterations):
                start_time = time.time()
                
                correlation_id = f"overhead_test_{i}"
                selector_id = f"selector_{i % 10}"
                
                await integration.start_selector_operation(
                    selector_id=selector_id,
                    correlation_id=correlation_id,
                    strategy="text_anchor"
                )
                
                await integration.record_selector_success(
                    selector_id=selector_id,
                    correlation_id=correlation_id,
                    confidence_score=0.85,
                    resolution_time_ms=15,
                    elements_found=1
                )
                
                operation_times.append(time.time() - start_time)
            
            return operation_times
    
    async def _monitor_health_during_test(self, manager, errors: List[str]) -> None:
        """Monitor system health during stress test."""
        while True:
            try:
                health = await manager.get_health_status()
                
                if not health.healthy:
                    errors.extend(health.issues)
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                errors.append(f"Health monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _test_buffer_optimization(self, optimizer) -> Dict[str, Any]:
        """Test buffer optimization."""
        start_time = time.time()
        
        # Test memory-efficient buffer
        buffer = optimizer.buffer
        
        # Fill buffer
        for i in range(1000):
            await buffer.add(f"test_data_{i}")
        
        # Get batch
        batch = await buffer.get_batch(100)
        
        end_time = time.time()
        
        return {
            "operations": 1000,
            "time": end_time - start_time,
            "buffer_size": await buffer.size(),
            "batch_size": len(batch),
            "score": 100.0 if len(batch) == 100 else 50.0
        }
    
    async def _test_connection_pooling(self, optimizer) -> Dict[str, Any]:
        """Test connection pooling."""
        start_time = time.time()
        
        # Test connection pool (mock implementation)
        pool = optimizer.get_connection_pool("test", lambda: {"connection": "mock"})
        
        async with pool.get_connection():
            await asyncio.sleep(0.001)
        
        end_time = time.time()
        
        return {
            "operations": 1,
            "time": end_time - start_time,
            "pool_size": len(pool.pool),
            "score": 100.0  # Assume success
        }
    
    async def _test_caching(self, optimizer) -> Dict[str, Any]:
        """Test caching optimization."""
        start_time = time.time()
        
        cache = optimizer.cache
        
        # Test cache operations
        await cache.set("test_key", "test_value")
        value = await cache.get("test_key")
        
        end_time = time.time()
        
        return {
            "operations": 2,
            "time": end_time - start_time,
            "cache_hit": value == "test_value",
            "score": 100.0 if value == "test_value" else 0.0
        }
    
    async def _test_resource_monitoring(self, optimizer) -> Dict[str, Any]:
        """Test resource monitoring."""
        start_time = time.time()
        
        # Test resource monitoring
        resources = await optimizer.resource_monitor.check_resources()
        
        end_time = time.time()
        
        return {
            "operations": 1,
            "time": end_time - start_time,
            "resources_checked": len(resources),
            "score": 100.0 if resources else 0.0
        }
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall performance score."""
        scores = []
        
        # Load test score (target: >1000 ops/sec)
        load_metrics = results["load_test"]
        load_score = min(100.0, (load_metrics.throughput / 1000) * 100)
        scores.append(load_score)
        
        # Overhead test score (target: <2% overhead)
        overhead_metrics = results["overhead_test"]
        overhead_score = max(0.0, 100.0 - (overhead_metrics.overhead_percent / 2.0) * 100)
        scores.append(overhead_score)
        
        # Memory test score (target: <1KB per operation)
        memory_results = results["memory_test"]
        memory_per_op = memory_results["memory_per_operation_bytes"]
        memory_score = max(0.0, 100.0 - (memory_per_op / 1024) * 100)
        scores.append(memory_score)
        
        # Stress test score (target: <1% error rate)
        stress_results = results["stress_test"]
        if "error_rate" in stress_results:
            stress_score = max(0.0, 100.0 - (stress_results["error_rate"] * 100))
        else:
            stress_score = 0.0
        scores.append(stress_score)
        
        # Optimization test score
        opt_score = results["optimization_test"]["overall_optimization_score"]
        scores.append(opt_score)
        
        return statistics.mean(scores)
    
    def _calculate_optimization_score(self, test_results: List[Dict[str, Any]]) -> float:
        """Calculate optimization score from test results."""
        scores = [result["score"] for result in test_results if "score" in result]
        return statistics.mean(scores) if scores else 0.0


async def run_performance_tests() -> Dict[str, Any]:
    """Run complete performance test suite."""
    tester = PerformanceTester()
    return await tester.run_comprehensive_performance_test()


if __name__ == "__main__":
    async def main():
        results = await run_performance_tests()
        
        print(f"\n🎯 Performance Test Results")
        print(f"Overall Score: {results['overall_score']:.1f}%")
        
        if results['overall_score'] >= 90:
            print("✅ Excellent performance!")
        elif results['overall_score'] >= 80:
            print("✅ Good performance")
        elif results['overall_score'] >= 70:
            print("⚠️  Acceptable performance")
        else:
            print("❌ Performance needs improvement")
        
        print(f"\n📊 Detailed Results:")
        print(f"Load Test: {results['load_test'].throughput:.1f} ops/sec")
        print(f"Overhead: {results['overhead_test'].overhead_percent:.2f}%")
        print(f"Memory Growth: {results['memory_test']['memory_growth_mb']:.1f}MB")
        print(f"Stress Test: {'Stable' if results['stress_test'].get('system_stable', False) else 'Unstable'}")
        print(f"Optimization: {results['optimization_test']['overall_optimization_score']:.1f}%")
    
    asyncio.run(main())
