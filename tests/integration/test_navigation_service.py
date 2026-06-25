"""
Integration tests for navigation service

Test scenarios for complete navigation service integration including all components.
"""

import asyncio
from typing import Dict, List, Any, Optional
from src.navigation.navigation_service import NavigationService
from src.navigation.models import NavigationContext, NavigationEvent, NavigationOutcome


class NavigationServiceTestScenarios:
    """Test scenarios for navigation service integration"""
    
    @staticmethod
    def get_simple_navigation_scenario() -> Dict[str, Any]:
        """Simple navigation scenario"""
        return {
            "name": "simple_navigation",
            "session_id": "test_session_001",
            "source_context": "https://example.com",
            "target_destination": "https://example.com/about",
            "options": {
                "enable_optimization": True,
                "enable_adaptation": True,
                "enable_learning": True
            },
            "expected_success": True,
            "expected_steps": 1
        }
    
    @staticmethod
    def get_complex_navigation_scenario() -> Dict[str, Any]:
        """Complex multi-step navigation scenario"""
        return {
            "name": "complex_navigation",
            "session_id": "test_session_002",
            "source_context": "https://shop.example.com",
            "target_destination": "https://shop.example.com/checkout",
            "options": {
                "enable_optimization": True,
                "enable_adaptation": True,
                "enable_learning": True
            },
            "expected_success": True,
            "expected_min_steps": 2
        }
    
    @staticmethod
    def get_adaptation_scenario() -> Dict[str, Any]:
        """Navigation with adaptation scenario"""
        return {
            "name": "navigation_with_adaptation",
            "session_id": "test_session_003",
            "source_context": "https://example.com",
            "target_destination": "https://example.com/protected",
            "options": {
                "enable_optimization": True,
                "enable_adaptation": True,
                "enable_learning": True
            },
            "simulate_failure": True,
            "expected_adaptation": True,
            "expected_success": True
        }
    
    @staticmethod
    def get_context_persistence_scenario() -> Dict[str, Any]:
        """Context persistence across navigations scenario"""
        return {
            "name": "context_persistence",
            "session_id": "test_session_004",
            "navigations": [
                {
                    "source": "https://example.com",
                    "target": "https://example.com/products"
                },
                {
                    "source": "https://example.com/products",
                    "target": "https://example.com/cart"
                },
                {
                    "source": "https://example.com/cart",
                    "target": "https://example.com/checkout"
                }
            ],
            "expected_context_continuity": True,
            "expected_pages_visited": 4
        }
    
    @staticmethod
    def get_service_statistics_scenario() -> Dict[str, Any]:
        """Service statistics collection scenario"""
        return {
            "name": "service_statistics",
            "session_count": 5,
            "navigations_per_session": 3,
            "success_rate": 0.8,
            "expected_statistics": {
                "total_navigations": 15,
                "successful_navigations": 12,
                "failed_navigations": 3,
                "active_sessions": 5
            }
        }


class MockNavigationService:
    """Mock navigation service for testing"""
    
    @staticmethod
    def create_test_service(
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> NavigationService:
        """Create test navigation service"""
        if config is None:
            config = {
                "route_discovery": {
                    "max_discovery_time": 30,
                    "max_routes_per_page": 10
                },
                "path_planning": {
                    "max_planning_time": 10,
                    "optimization_enabled": True
                },
                "route_adaptation": {
                    "max_adaptation_attempts": 3,
                    "adaptation_timeout": 15
                },
                "context_manager": {
                    "max_context_age_hours": 24,
                    "auto_save_enabled": True
                },
                "route_optimizer": {
                    "learning_enabled": True,
                    "min_samples_for_optimization": 3
                }
            }
        
        return NavigationService(config=config, storage_path=storage_path)
    
    @staticmethod
    async def simulate_navigation_session(
        service: NavigationService,
        session_id: str,
        navigations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Simulate complete navigation session"""
        results = []
        
        for nav in navigations:
            try:
                result = await service.navigate(
                    session_id=session_id,
                    source_context=nav["source"],
                    target_destination=nav["target"],
                    options=nav.get("options", {})
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "source": nav["source"],
                    "target": nav["target"]
                })
        
        return results


class NavigationServiceTestHelpers:
    """Helpers for testing navigation service"""
    
    @staticmethod
    async def validate_navigation_result(
        result: Dict[str, Any],
        expected_success: bool,
        expected_min_steps: int = 1
    ) -> bool:
        """Validate navigation result"""
        return (
            result.get("success") == expected_success and
            result.get("steps_completed", 0) >= expected_min_steps and
            result.get("total_steps", 0) >= expected_min_steps and
            len(result.get("events", [])) > 0 and
            result.get("final_event") is not None
        )
    
    @staticmethod
    async def validate_context_continuity(
        service: NavigationService,
        session_id: str,
        expected_pages_visited: int
    ) -> bool:
        """Validate context continuity across navigations"""
        context = await service.get_navigation_context(session_id)
        
        if not context:
            return False
        
        return (
            context.session_id == session_id and
            context.pages_visited == expected_pages_visited and
            len(context.navigation_history) > 0
        )
    
    @staticmethod
    async def validate_service_statistics(
        service: NavigationService,
        expected_stats: Dict[str, Any]
    ) -> bool:
        """Validate service statistics"""
        stats = await service.get_service_statistics()
        
        if not stats.get("initialized"):
            return False
        
        service_stats = stats.get("service_statistics", {})
        
        for key, expected_value in expected_stats.items():
            if service_stats.get(key) != expected_value:
                return False
        
        return True
    
    @staticmethod
    async def validate_adaptation_functionality(
        result: Dict[str, Any],
        expected_adaptation: bool
    ) -> bool:
        """Validate adaptation functionality"""
        if not expected_adaptation:
            return True
        
        # Check if any events have adaptation metadata
        for event in result.get("events", []):
            if (event.metadata and 
                event.metadata.get("adaptation_applied")):
                return True
        
        return False
    
    @staticmethod
    async def validate_component_integration(
        service: NavigationService
    ) -> bool:
        """Validate all components are properly integrated"""
        stats = await service.get_service_statistics()
        
        if not stats.get("initialized"):
            return False
        
        component_stats = stats.get("component_statistics", {})
        
        required_components = [
            "route_discovery",
            "path_planning", 
            "route_adaptation",
            "context_management",
            "route_optimization"
        ]
        
        for component in required_components:
            if component not in component_stats:
                return False
        
        return True
    
    @staticmethod
    def calculate_navigation_efficiency(
        results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate navigation efficiency metrics"""
        if not results:
            return {
                "success_rate": 0.0,
                "average_steps": 0.0,
                "efficiency_score": 0.0
            }
        
        successful_results = [r for r in results if r.get("success", False)]
        success_rate = len(successful_results) / len(results)
        
        total_steps = sum(r.get("steps_completed", 0) for r in results)
        average_steps = total_steps / len(results)
        
        # Efficiency score: success rate / average steps
        efficiency_score = success_rate / max(average_steps, 1.0)
        
        return {
            "success_rate": success_rate,
            "average_steps": average_steps,
            "efficiency_score": efficiency_score
        }
    
    @staticmethod
    async def measure_service_performance(
        service: NavigationService,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Measure service performance"""
        import time
        
        start_time = time.time()
        
        for operation in operations:
            op_type = operation["type"]
            
            if op_type == "navigate":
                await service.navigate(
                    session_id=operation["session_id"],
                    source_context=operation["source"],
                    target_destination=operation["target"],
                    options=operation.get("options", {})
                )
            elif op_type == "get_context":
                await service.get_navigation_context(operation["session_id"])
            elif op_type == "get_history":
                await service.get_navigation_history(operation["session_id"])
            elif op_type == "get_stats":
                await service.get_service_statistics()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return {
            "total_time": total_time,
            "operations_per_second": len(operations) / total_time,
            "average_operation_time": total_time / len(operations)
        }


class NavigationServiceTestUtils:
    """Utilities for navigation service testing"""
    
    @staticmethod
    async def run_complete_test_suite(
        service: NavigationService
    ) -> Dict[str, Any]:
        """Run complete test suite for navigation service"""
        test_results = {
            "initialization_test": False,
            "simple_navigation_test": False,
            "complex_navigation_test": False,
            "adaptation_test": False,
            "context_persistence_test": False,
            "statistics_test": False,
            "integration_test": False,
            "overall_success": False
        }
        
        try:
            # Test initialization
            await service.initialize()
            test_results["initialization_test"] = True
            
            # Test simple navigation
            simple_result = await service.navigate(
                session_id="test_simple",
                source_context="https://example.com",
                target_destination="https://example.com/about"
            )
            test_results["simple_navigation_test"] = simple_result.get("success", False)
            
            # Test complex navigation
            complex_result = await service.navigate(
                session_id="test_complex",
                source_context="https://shop.example.com",
                target_destination="https://shop.example.com/checkout"
            )
            test_results["complex_navigation_test"] = complex_result.get("success", False)
            
            # Test context persistence
            await service.navigate(
                session_id="test_persistence",
                source_context="https://example.com",
                target_destination="https://example.com/products"
            )
            await service.navigate(
                session_id="test_persistence",
                source_context="https://example.com/products",
                target_destination="https://example.com/cart"
            )
            context = await service.get_navigation_context("test_persistence")
            test_results["context_persistence_test"] = context is not None and context.pages_visited >= 3
            
            # Test statistics
            stats = await service.get_service_statistics()
            test_results["statistics_test"] = stats.get("initialized", False)
            
            # Test integration
            test_results["integration_test"] = await NavigationServiceTestHelpers.validate_component_integration(service)
            
            # Calculate overall success
            passed_tests = sum(1 for result in test_results.values() if result)
            test_results["overall_success"] = passed_tests >= 6  # At least 6/7 tests pass
            
        except Exception as e:
            print(f"Test suite error: {e}")
        
        return test_results
    
    @staticmethod
    async def simulate_load_test(
        service: NavigationService,
        concurrent_sessions: int = 10,
        navigations_per_session: int = 5
    ) -> Dict[str, Any]:
        """Simulate load test for navigation service"""
        import time
        
        start_time = time.time()
        tasks = []
        
        for session_id in range(concurrent_sessions):
            session_tasks = []
            
            for nav_id in range(navigations_per_session):
                task = service.navigate(
                    session_id=f"load_test_session_{session_id}",
                    source_context=f"https://example.com/page_{nav_id}",
                    target_destination=f"https://example.com/page_{nav_id + 1}"
                )
                session_tasks.append(task)
            
            tasks.append(asyncio.gather(*session_tasks, return_exceptions=True))
        
        # Run all sessions concurrently
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        total_navigations = concurrent_sessions * navigations_per_session
        successful_navigations = 0
        
        for session_results in all_results:
            if isinstance(session_results, list):
                for result in session_results:
                    if isinstance(result, dict) and result.get("success"):
                        successful_navigations += 1
        
        return {
            "concurrent_sessions": concurrent_sessions,
            "navigations_per_session": navigations_per_session,
            "total_navigations": total_navigations,
            "successful_navigations": successful_navigations,
            "success_rate": successful_navigations / total_navigations,
            "total_time": total_time,
            "navigations_per_second": total_navigations / total_time
        }
    
    @staticmethod
    def create_test_scenarios() -> List[Dict[str, Any]]:
        """Create comprehensive test scenarios"""
        return [
            NavigationServiceTestScenarios.get_simple_navigation_scenario(),
            NavigationServiceTestScenarios.get_complex_navigation_scenario(),
            NavigationServiceTestScenarios.get_adaptation_scenario(),
            NavigationServiceTestScenarios.get_context_persistence_scenario(),
            NavigationServiceTestScenarios.get_service_statistics_scenario()
        ]
    
    @staticmethod
    async def validate_service_lifecycle(
        service: NavigationService
    ) -> bool:
        """Validate complete service lifecycle"""
        try:
            # Initialize
            await service.initialize()
            
            # Perform operations
            await service.navigate(
                session_id="lifecycle_test",
                source_context="https://example.com",
                target_destination="https://example.com/about"
            )
            
            # Get statistics
            stats = await service.get_service_statistics()
            
            # Cleanup
            await service.cleanup_session("lifecycle_test")
            
            # Shutdown
            await service.shutdown()
            
            return stats.get("initialized", False)
            
        except Exception as e:
            print(f"Lifecycle test error: {e}")
            return False
    
    @staticmethod
    def generate_performance_benchmark(
        session_count: int,
        navigation_complexity: str = "simple"
    ) -> Dict[str, Any]:
        """Generate performance benchmark parameters"""
        complexity_factors = {
            "simple": {"steps_per_navigation": 1, "expected_time": 2.0},
            "moderate": {"steps_per_navigation": 3, "expected_time": 5.0},
            "complex": {"steps_per_navigation": 5, "expected_time": 10.0}
        }
        
        factor = complexity_factors.get(navigation_complexity, complexity_factors["simple"])
        
        return {
            "session_count": session_count,
            "navigation_complexity": navigation_complexity,
            "steps_per_navigation": factor["steps_per_navigation"],
            "expected_time_per_navigation": factor["expected_time"],
            "total_expected_time": session_count * factor["expected_time"],
            "target_throughput": session_count / factor["expected_time"]
        }
