"""
Production resilience testing for Navigation & Routing Intelligence

Tests retry/recovery validation, error handling, and system resilience
under various failure scenarios and production conditions.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch

from navigation import (
    NavigationService, RouteDiscovery, PathPlanning, RouteAdaptation,
    ContextManager, RouteOptimizationEngine
)
from navigation.exceptions import (
    NavigationError, RouteDiscoveryError, PathPlanningError,
    RouteAdaptationError, ContextManagementError
)
from navigation.checkpoint_manager import NavigationCheckpointManager
from navigation.error_context import ErrorContextCollector
from navigation.health_checker import NavigationHealthChecker


class TestProductionResilience:
    """Production resilience test suite"""
    
    @pytest.fixture
    async def navigation_service(self):
        """Create navigation service for testing"""
        # Mock dependencies
        selector_engine = Mock()
        stealth_system = Mock()
        
        service = NavigationService(selector_engine, stealth_system)
        await service.initialize()
        yield service
        await service.cleanup()
    
    @pytest.mark.asyncio
    async def test_route_discovery_retry_mechanism(self, navigation_service):
        """Test route discovery retry mechanism"""
        # Mock selector engine to fail initially, then succeed
        call_count = 0
        
        async def mock_discover(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RouteDiscoveryError("Temporary failure", "TEMPORARY_ERROR")
            return Mock()  # Success on third attempt
        
        navigation_service.route_discovery.discover_routes = mock_discover
        
        # Test retry mechanism
        result = await navigation_service.discover_routes_with_retry(
            "https://example.com",
            max_retries=3,
            retry_delay=0.1
        )
        
        assert result is not None
        assert call_count == 3  # Should have retried 2 times + 1 success
    
    @pytest.mark.asyncio
    async def test_path_planning_fallback_mechanism(self, navigation_service):
        """Test path planning fallback mechanism"""
        # Mock path planning to fail with primary strategy
        primary_failed = False
        
        async def mock_plan_path(*args, **kwargs):
            nonlocal primary_failed
            if not primary_failed:
                primary_failed = True
                raise PathPlanningError("Primary strategy failed", "PRIMARY_FAILED")
            return Mock()  # Success with fallback
        
        navigation_service.path_planning.plan_path = mock_plan_path
        
        # Test fallback mechanism
        result = await navigation_service.plan_path_with_fallback(
            source="https://example.com/home",
            target="https://example.com/dashboard",
            fallback_strategies=["alternative", "conservative"]
        )
        
        assert result is not None
        assert primary_failed  # Primary should have failed
    
    @pytest.mark.asyncio
    async def test_route_adaptation_recovery(self, navigation_service):
        """Test route adaptation recovery mechanisms"""
        # Mock adaptation scenarios
        adaptation_scenarios = [
            {"type": "element_not_found", "should_recover": True},
            {"type": "timeout", "should_recover": True},
            {"type": "blocked", "should_recover": True},
            {"type": "critical_failure", "should_recover": False}
        ]
        
        for scenario in adaptation_scenarios:
            # Mock adaptation to handle scenario
            async def mock_adapt(*args, **kwargs):
                if scenario["type"] == "critical_failure":
                    raise RouteAdaptationError("Critical failure", "CRITICAL_FAILURE")
                return Mock()  # Successful adaptation
            
            navigation_service.route_adaptation.adapt_to_obstacle = mock_adapt
            
            try:
                result = await navigation_service.adapt_to_obstacle_with_recovery(
                    Mock(),  # original_route
                    scenario["type"],
                    Mock()  # context
                )
                
                if scenario["should_recover"]:
                    assert result is not None
                else:
                    assert False, "Should have failed for critical failure"
                    
            except RouteAdaptationError:
                if not scenario["should_recover"]:
                    assert True  # Expected failure
                else:
                    assert False, "Should have recovered"
    
    @pytest.mark.asyncio
    async def test_context_management_persistence(self, navigation_service):
        """Test context management persistence and recovery"""
        # Create context
        context = await navigation_service.context_manager.create_context(
            session_id="test_session",
            start_url="https://example.com"
        )
        
        # Add navigation data
        await navigation_service.context_manager.update_context(
            context.context_id,
            current_page="https://example.com/dashboard",
            navigation_data={"action": "login"}
        )
        
        # Simulate context loss and recovery
        recovered_context = await navigation_service.context_manager.get_context(
            context.context_id
        )
        
        assert recovered_context is not None
        assert recovered_context.session_id == "test_session"
        assert recovered_context.current_page == "https://example.com/dashboard"
        assert "login" in str(recovered_context.session_data)
    
    @pytest.mark.asyncio
    async def test_checkpoint_and_resume(self, navigation_service):
        """Test checkpoint and resume functionality"""
        checkpoint_manager = NavigationCheckpointManager()
        
        # Create checkpoint during operation
        checkpoint_id = checkpoint_manager.create_checkpoint(
            operation_type="route_discovery",
            correlation_id="test_corr_123",
            session_id="test_session_456",
            current_step=5,
            total_steps=20,
            completed_routes=["route_1", "route_2"],
            failed_routes=[],
            pending_routes=["route_3", "route_4"]
        )
        
        # Verify checkpoint created
        assert checkpoint_id is not None
        
        # Load checkpoint
        checkpoint = checkpoint_manager.load_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.current_step == 5
        assert checkpoint.total_steps == 20
        assert len(checkpoint.completed_routes) == 2
        assert len(checkpoint.pending_routes) == 2
        
        # Test resume capability
        assert checkpoint.operation_type == "route_discovery"
        assert checkpoint.correlation_id == "test_corr_123"
    
    @pytest.mark.asyncio
    async def test_error_context_collection(self, navigation_service):
        """Test error context collection for debugging"""
        error_collector = ErrorContextCollector()
        
        # Register component for context collection
        error_collector.register_component("test_component", navigation_service)
        
        # Simulate error and collect context
        test_error = Exception("Test error for context collection")
        
        error_context = error_collector.collect_error_context(
            error=test_error,
            component_name="test_component",
            correlation_id="test_corr_789",
            session_id="test_session_123"
        )
        
        # Verify error context collected
        assert error_context is not None
        assert error_context.error_type == "Exception"
        assert error_context.error_message == "Test error for context collection"
        assert error_context.component_name == "test_component"
        assert error_context.correlation_id == "test_corr_789"
        
        # Verify system context collected
        assert error_context.system_context is not None
        assert error_context.system_context.python_version is not None
        
        # Verify recovery suggestions provided
        assert len(error_context.recovery_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring_under_load(self, navigation_service):
        """Test health monitoring under system load"""
        health_checker = NavigationHealthChecker()
        
        # Simulate system under load
        with patch('psutil.cpu_percent', return_value=85.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 75.0
                mock_memory.return_value.available = 8 * 1024**3  # 8GB
                mock_memory.return_value.used = 8 * 1024**3  # 8GB
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 60.0
                    mock_disk.return_value.free = 100 * 1024**3  # 100GB
                    mock_disk.return_value.used = 150 * 1024**3  # 150GB
                    mock_disk.return_value.total = 250 * 1024**3  # 250GB
                    
                    # Check system health
                    health_status = await health_checker.check_system_health()
                    
                    # Verify health status
                    assert health_status.overall_status in ["healthy", "warning"]
                    assert len(health_status.component_results) >= 3  # CPU, memory, disk
                    
                    # Check individual components
                    cpu_result = next(r for r in health_status.component_results 
                                    if r.component_name == "system_resources")
                    assert cpu_result.status in ["healthy", "warning"]
                    
                    memory_result = next(r for r in health_status.component_results 
                                       if r.component_name == "memory_usage")
                    assert memory_result.status in ["healthy", "warning"]
    
    @pytest.mark.asyncio
    async def test_concurrent_operation_resilience(self, navigation_service):
        """Test resilience under concurrent operations"""
        # Mock successful operations
        navigation_service.route_discovery.discover_routes = AsyncMock(
            return_value=Mock()
        )
        navigation_service.path_planning.plan_path = AsyncMock(
            return_value=Mock()
        )
        
        # Run multiple concurrent operations
        tasks = []
        for i in range(10):
            # Route discovery tasks
            task1 = asyncio.create_task(
                navigation_service.discover_routes(f"https://example.com/page{i}")
            )
            tasks.append(task1)
            
            # Path planning tasks
            task2 = asyncio.create_task(
                navigation_service.plan_path(
                    f"https://example.com/page{i}",
                    f"https://example.com/target{i}"
                )
            )
            tasks.append(task2)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Operations failed: {exceptions}"
        assert len(results) == 20  # 10 discovery + 10 planning tasks
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, navigation_service):
        """Test handling under memory pressure"""
        # Simulate memory pressure
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 95.0  # High memory usage
            mock_memory.return_value.available = 1 * 1024**3  # 1GB available
            
            # Test memory optimization trigger
            from navigation.memory_optimization import MemoryOptimizedRouteGraph
            
            graph = MemoryOptimizedRouteGraph(max_memory_mb=100)
            
            # Add routes to trigger memory pressure
            for i in range(1000):
                graph.add_node(f"node_{i}")
                graph.add_edge(f"node_{i}", f"node_{i+1}")
            
            # Check memory optimization
            stats = graph.get_memory_stats()
            assert stats.memory_usage_mb > 0
            
            # Trigger optimization
            graph.optimize_memory()
            
            # Verify optimization occurred
            optimized_stats = graph.get_memory_stats()
            assert optimized_stats.memory_usage_mb <= stats.memory_usage_mb * 1.1  # Allow small increase
    
    @pytest.mark.asyncio
    async def test_network_failure_recovery(self, navigation_service):
        """Test recovery from network failures"""
        # Mock network failure scenarios
        failure_scenarios = [
            {"type": "timeout", "recoverable": True},
            {"type": "connection_refused", "recoverable": True},
            {"type": "dns_failure", "recoverable": False},
            {"type": "ssl_error", "recoverable": True}
        ]
        
        for scenario in failure_scenarios:
            # Mock network failure
            if scenario["type"] == "timeout":
                navigation_service.route_discovery.discover_routes = AsyncMock(
                    side_effect=asyncio.TimeoutError("Network timeout")
                )
            elif scenario["type"] == "connection_refused":
                navigation_service.route_discovery.discover_routes = AsyncMock(
                    side_effect=ConnectionError("Connection refused")
                )
            elif scenario["type"] == "dns_failure":
                navigation_service.route_discovery.discover_routes = AsyncMock(
                    side_effect=Exception("DNS resolution failed")
                )
            elif scenario["type"] == "ssl_error":
                navigation_service.route_discovery.discover_routes = AsyncMock(
                    side_effect=Exception("SSL handshake failed")
                )
            
            # Test recovery
            try:
                result = await navigation_service.discover_routes_with_retry(
                    "https://example.com",
                    max_retries=3,
                    retry_delay=0.1
                )
                
                if scenario["recoverable"]:
                    assert result is not None
                else:
                    assert False, "Should have failed for unrecoverable error"
                    
            except Exception as e:
                if not scenario["recoverable"]:
                    assert True  # Expected failure
                else:
                    assert False, f"Should have recovered from {scenario['type']}"
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, navigation_service):
        """Test graceful shutdown under load"""
        # Start some operations
        operations = []
        for i in range(5):
            task = asyncio.create_task(
                navigation_service.discover_routes(f"https://example.com/page{i}")
            )
            operations.append(task)
        
        # Wait a bit for operations to start
        await asyncio.sleep(0.1)
        
        # Test graceful shutdown
        await navigation_service.graceful_shutdown(timeout=5.0)
        
        # Verify all operations completed or cancelled gracefully
        results = await asyncio.gather(*operations, return_exceptions=True)
        
        # Should have some results or cancellations, but no crashes
        assert len(results) == 5
    
    @pytest.mark.asyncio
    async def test_data_corruption_recovery(self, navigation_service):
        """Test recovery from data corruption"""
        # Mock corrupted data scenario
        corrupted_context_data = {
            "context_id": "corrupted_context",
            "session_id": "test_session",
            "invalid_field": "corrupted_data",
            "navigation_history": ["invalid_url", None, 123]  # Invalid data
        }
        
        # Test context manager handling of corrupted data
        try:
            context = await navigation_service.context_manager.create_context(
                session_id="test_session",
                start_url="https://example.com"
            )
            
            # Try to update with corrupted data
            await navigation_service.context_manager.update_context(
                context.context_id,
                **corrupted_context_data
            )
            
            # Should handle corruption gracefully
            recovered_context = await navigation_service.context_manager.get_context(
                context.context_id
            )
            
            assert recovered_context is not None
            assert recovered_context.session_id == "test_session"
            
        except Exception as e:
            # Should handle corruption gracefully
            assert "corruption" in str(e).lower() or "invalid" in str(e).lower()


# Performance resilience tests
class TestPerformanceResilience:
    """Performance resilience test suite"""
    
    @pytest.mark.asyncio
    async def test_high_volume_operations(self):
        """Test system under high volume operations"""
        # Create navigation service
        selector_engine = Mock()
        stealth_system = Mock()
        service = NavigationService(selector_engine, stealth_system)
        
        # Mock high-performance operations
        service.route_discovery.discover_routes = AsyncMock(return_value=Mock())
        service.path_planning.plan_path = AsyncMock(return_value=Mock())
        
        # Execute high volume operations
        start_time = datetime.utcnow()
        
        tasks = []
        for i in range(100):
            task = asyncio.create_task(
                service.discover_routes(f"https://example.com/page{i}")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Verify performance under load
        assert len(results) == 100
        assert duration < 30.0  # Should complete within 30 seconds
        assert all(r is not None for r in results)
        
        await service.cleanup()
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test memory leak prevention"""
        from navigation.memory_optimization import MemoryOptimizedRouteGraph
        
        # Create and destroy multiple graphs
        for iteration in range(10):
            graph = MemoryOptimizedRouteGraph(max_memory_mb=50)
            
            # Add significant data
            for i in range(100):
                graph.add_node(f"node_{iteration}_{i}")
                graph.add_edge(f"node_{iteration}_{i}", f"node_{iteration}_{i+1}")
            
            # Check memory usage
            stats = graph.get_memory_stats()
            assert stats.memory_usage_mb < 100  # Should not exceed limit
            
            # Clear graph
            graph.clear_cache()
            
        # Final check - memory should be reasonable
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        # Should not have grown excessively
        assert memory_mb < 500  # Reasonable limit for test


# Integration resilience tests
class TestIntegrationResilience:
    """Integration resilience test suite"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_resilience(self):
        """Test end-to-end navigation resilience"""
        # Create complete navigation system
        selector_engine = Mock()
        stealth_system = Mock()
        service = NavigationService(selector_engine, stealth_system)
        
        # Mock complete workflow
        service.route_discovery.discover_routes = AsyncMock(return_value=Mock())
        service.path_planning.plan_path = AsyncMock(return_value=Mock())
        service.route_adaptation.adapt_to_obstacle = AsyncMock(return_value=Mock())
        
        # Test complete navigation workflow with failures
        try:
            # Initialize navigation
            context = await service.initialize_navigation(
                session_id="test_session",
                start_url="https://example.com"
            )
            
            # Discover routes
            routes = await service.discover_routes("https://example.com")
            
            # Plan path
            path_plan = await service.plan_path(
                source="https://example.com",
                target="https://example.com/target"
            )
            
            # Execute navigation
            result = await service.execute_navigation(path_plan)
            
            # Verify complete workflow
            assert context is not None
            assert routes is not None
            assert path_plan is not None
            assert result is not None
            
        except Exception as e:
            # Should handle failures gracefully
            assert "resilience" in str(e).lower() or "recovery" in str(e).lower()
        
        finally:
            await service.cleanup()


if __name__ == "__main__":
    # Run resilience tests
    pytest.main([__file__, "-v", "--tb=short"])
