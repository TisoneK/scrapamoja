"""
Integration test fixtures for route optimization

Test scenarios for Navigation & Routing Intelligence route optimization and learning functionality.
"""

from typing import Dict, List, Any, Optional
from src.navigation.models import PathPlan, RouteStep, NavigationEvent, NavigationOutcome
from src.navigation.route_optimizer import RouteOptimizationEngine


class RouteOptimizationTestScenarios:
    """Test scenarios for route optimization"""
    
    @staticmethod
    def get_high_performance_route_scenario() -> Dict[str, Any]:
        """High performance route scenario"""
        return {
            "name": "high_performance_route",
            "route_id": "route_high_perf",
            "success_rate": 0.95,
            "average_time": 1.2,
            "detection_rate": 0.02,
            "expected_optimization": False,
            "expected_recommendations": 0
        }
    
    @staticmethod
    def get_low_performance_route_scenario() -> Dict[str, Any]:
        """Low performance route scenario"""
        return {
            "name": "low_performance_route",
            "route_id": "route_low_perf",
            "success_rate": 0.45,
            "average_time": 8.5,
            "detection_rate": 0.25,
            "expected_optimization": True,
            "expected_recommendations": 3
        }
    
    @staticmethod
    def get_timing_optimization_scenario() -> Dict[str, Any]:
        """Timing optimization scenario"""
        return {
            "name": "timing_optimization",
            "plan_id": "plan_timing_test",
            "steps": [
                {
                    "step_number": 1,
                    "action_type": "navigate",
                    "target_url": "https://example.com/page1",
                    "expected_delay": 2.0
                },
                {
                    "step_number": 2,
                    "action_type": "click",
                    "target_url": "https://example.com/page2",
                    "expected_delay": 1.5
                }
            ],
            "historical_data": [
                {
                    "step_type": "navigate",
                    "target_url": "https://example.com/page1",
                    "duration": 1.2,
                    "success": True
                },
                {
                    "step_type": "click",
                    "target_url": "https://example.com/page2",
                    "duration": 0.8,
                    "success": True
                }
            ],
            "expected_optimization": True,
            "expected_duration_reduction": 0.5
        }
    
    @staticmethod
    def get_learning_scenario() -> Dict[str, Any]:
        """Learning from outcomes scenario"""
        return {
            "name": "learning_scenario",
            "navigation_events": [
                {
                    "event_id": "learn_001",
                    "route_id": "route_learn",
                    "outcome": "success",
                    "duration": 1.0,
                    "stealth_score": 0.8
                },
                {
                    "event_id": "learn_002",
                    "route_id": "route_learn",
                    "outcome": "success",
                    "duration": 1.2,
                    "stealth_score": 0.7
                },
                {
                    "event_id": "learn_003",
                    "route_id": "route_learn",
                    "outcome": "failure",
                    "duration": 0.5,
                    "error_code": "TIMEOUT_ERROR"
                }
            ],
            "expected_patterns_identified": 1,
            "expected_timing_adjustments": 3,
            "expected_recommendations": 1
        }
    
    @staticmethod
    def get_route_selection_scenario() -> Dict[str, Any]:
        """Route selection optimization scenario"""
        return {
            "name": "route_selection",
            "candidate_routes": [
                {
                    "plan_id": "candidate_1",
                    "total_risk_score": 0.2,
                    "estimated_duration": 2.0,
                    "steps_count": 2
                },
                {
                    "plan_id": "candidate_2",
                    "total_risk_score": 0.4,
                    "estimated_duration": 1.5,
                    "steps_count": 3
                },
                {
                    "plan_id": "candidate_3",
                    "total_risk_score": 0.1,
                    "estimated_duration": 3.0,
                    "steps_count": 1
                }
            ],
            "expected_selected_route": "candidate_1",  # Best balance of risk and time
            "expected_selection_score": 0.7
        }


class MockPathPlans:
    """Mock path plans for optimization testing"""
    
    @staticmethod
    def get_fast_plan(plan_id: str = "fast_plan") -> PathPlan:
        """Get fast path plan"""
        steps = [
            RouteStep(
                step_number=1,
                route_id="direct_route",
                action_type="navigate",
                target_url="https://example.com/target",
                expected_delay=1.0,
                step_description="Direct navigation to target"
            )
        ]
        
        return PathPlan(
            plan_id=plan_id,
            source_context="source",
            target_destination="target",
            route_sequence=steps,
            total_risk_score=0.3,
            estimated_duration=1.0
        )
    
    @staticmethod
    def get_slow_plan(plan_id: str = "slow_plan") -> PathPlan:
        """Get slow path plan"""
        steps = [
            RouteStep(
                step_number=1,
                route_id="indirect_route_1",
                action_type="navigate",
                target_url="https://example.com/intermediate1",
                expected_delay=3.0,
                step_description="Navigate to intermediate page 1"
            ),
            RouteStep(
                step_number=2,
                route_id="indirect_route_2",
                action_type="navigate",
                target_url="https://example.com/intermediate2",
                expected_delay=2.5,
                step_description="Navigate to intermediate page 2"
            ),
            RouteStep(
                step_number=3,
                route_id="final_route",
                action_type="navigate",
                target_url="https://example.com/target",
                expected_delay=2.0,
                step_description="Navigate to target"
            )
        ]
        
        return PathPlan(
            plan_id=plan_id,
            source_context="source",
            target_destination="target",
            route_sequence=steps,
            total_risk_score=0.1,
            estimated_duration=7.5
        )
    
    @staticmethod
    def get_risky_plan(plan_id: str = "risky_plan") -> PathPlan:
        """Get risky path plan"""
        steps = [
            RouteStep(
                step_number=1,
                route_id="javascript_route",
                action_type="javascript_execution",
                target_url="https://example.com/target",
                expected_delay=0.5,
                step_description="Execute JavaScript to reach target"
            )
        ]
        
        return PathPlan(
            plan_id=plan_id,
            source_context="source",
            target_destination="target",
            route_sequence=steps,
            total_risk_score=0.8,
            estimated_duration=0.5
        )


class MockNavigationEvents:
    """Mock navigation events for optimization testing"""
    
    @staticmethod
    def create_performance_events(
        route_id: str,
        count: int,
        success_rate: float = 0.8,
        avg_duration: float = 2.0
    ) -> List[NavigationEvent]:
        """Create performance navigation events"""
        events = []
        success_count = int(count * success_rate)
        
        for i in range(count):
            is_success = i < success_count
            
            if is_success:
                event = NavigationEvent(
                    event_id=f"perf_{route_id}_{i}",
                    route_id=route_id,
                    context_before="step_before",
                    context_after="step_after",
                    outcome=NavigationOutcome.SUCCESS,
                    page_url_after=f"https://example.com/page_{i}",
                    performance_metrics={
                        "duration_seconds": avg_duration + (i * 0.1),
                        "cpu_usage_percent": 10.0,
                        "memory_usage_mb": 50.0
                    },
                    stealth_score_before=0.7,
                    stealth_score_after=0.8
                )
            else:
                event = NavigationEvent(
                    event_id=f"perf_{route_id}_{i}",
                    route_id=route_id,
                    context_before="step_before",
                    context_after="step_before",
                    outcome=NavigationOutcome.FAILURE,
                    error_details="Element not found",
                    error_code="ELEMENT_NOT_FOUND",
                    performance_metrics={
                        "duration_seconds": 0.5,
                        "cpu_usage_percent": 5.0,
                        "memory_usage_mb": 45.0
                    }
                )
            
            events.append(event)
        
        return events
    
    @staticmethod
    def create_timing_events(
        route_id: str,
        durations: List[float],
        success_rates: List[bool]
    ) -> List[NavigationEvent]:
        """Create timing-focused navigation events"""
        events = []
        
        for i, (duration, success) in enumerate(zip(durations, success_rates)):
            outcome = NavigationOutcome.SUCCESS if success else NavigationOutcome.FAILURE
            
            event = NavigationEvent(
                event_id=f"time_{route_id}_{i}",
                route_id=route_id,
                context_before="step_before",
                context_after="step_after" if success else "step_before",
                outcome=outcome,
                performance_metrics={
                    "duration_seconds": duration,
                    "cpu_usage_percent": 10.0,
                    "memory_usage_mb": 50.0
                }
            )
            
            events.append(event)
        
        return events
    
    @staticmethod
    def create_detection_events(
        route_id: str,
        detection_count: int,
        total_count: int
    ) -> List[NavigationEvent]:
        """Create detection-focused navigation events"""
        events = []
        
        for i in range(total_count):
            is_detected = i < detection_count
            
            if is_detected:
                event = NavigationEvent(
                    event_id=f"det_{route_id}_{i}",
                    route_id=route_id,
                    context_before="step_before",
                    context_after="step_before",
                    outcome=NavigationOutcome.DETECTED,
                    detection_triggers=["suspicious_timing", "bot_detected"],
                    stealth_score_before=0.6,
                    stealth_score_after=0.9,
                    performance_metrics={
                        "duration_seconds": 1.0,
                        "cpu_usage_percent": 15.0,
                        "memory_usage_mb": 60.0
                    }
                )
            else:
                event = NavigationEvent(
                    event_id=f"det_{route_id}_{i}",
                    route_id=route_id,
                    context_before="step_before",
                    context_after="step_after",
                    outcome=NavigationOutcome.SUCCESS,
                    stealth_score_before=0.7,
                    stealth_score_after=0.8,
                    performance_metrics={
                        "duration_seconds": 1.5,
                        "cpu_usage_percent": 10.0,
                        "memory_usage_mb": 50.0
                    }
                )
            
            events.append(event)
        
        return events


class OptimizationTestHelpers:
    """Helpers for testing route optimization"""
    
    @staticmethod
    def validate_performance_analysis(
        analysis: Dict[str, Any],
        expected_success_rate: float,
        expected_avg_time: float,
        tolerance: float = 0.1
    ) -> bool:
        """Validate performance analysis results"""
        success_rate_match = abs(analysis["success_rate"] - expected_success_rate) <= tolerance
        avg_time_match = abs(analysis["average_time"] - expected_avg_time) <= tolerance
        
        return (
            analysis["route_id"] and
            success_rate_match and
            avg_time_match and
            analysis["total_events"] > 0 and
            isinstance(analysis["recommendations"], list)
        )
    
    @staticmethod
    def validate_timing_optimization(
        original_plan: PathPlan,
        optimized_plan: PathPlan,
        expected_reduction: float
    ) -> bool:
        """Validate timing optimization results"""
        duration_reduction = original_plan.estimated_duration - optimized_plan.estimated_duration
        
        return (
            optimized_plan.plan_id != original_plan.plan_id and
            optimized_plan.plan_metadata.get("timing_optimized") and
            duration_reduction >= expected_reduction and
            len(optimized_plan.route_sequence) == len(original_plan.route_sequence)
        )
    
    @staticmethod
    def validate_learning_results(
        learning_results: Dict[str, Any],
        expected_patterns: int,
        expected_adjustments: int
    ) -> bool:
        """Validate learning results"""
        return (
            learning_results["patterns_identified"] >= expected_patterns and
            learning_results["timing_adjustments"] >= expected_adjustments and
            learning_results["learning_timestamp"] and
            learning_results["risk_assessments"] >= 0
        )
    
    @staticmethod
    def validate_optimization_recommendations(
        recommendations: List[Dict[str, Any]],
        min_count: int = 1
    ) -> bool:
        """Validate optimization recommendations"""
        if len(recommendations) < min_count:
            return False
        
        for rec in recommendations:
            if not all(key in rec for key in ["type", "message", "suggested_action"]):
                return False
        
        return True
    
    @staticmethod
    def validate_route_selection(
        selected_route: PathPlan,
        expected_route_id: str,
        min_score: float = 0.5
    ) -> bool:
        """Validate route selection results"""
        return (
            selected_route.plan_id == expected_route_id and
            selected_route.plan_metadata.get("selection_score", 0) >= min_score and
            selected_route.plan_metadata.get("candidates_evaluated", 0) > 0
        )
    
    @staticmethod
    def calculate_optimization_effectiveness(
        original_performance: Dict[str, Any],
        optimized_performance: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate optimization effectiveness metrics"""
        success_rate_improvement = (
            optimized_performance["success_rate"] - original_performance["success_rate"]
        )
        
        time_improvement = (
            original_performance["average_time"] - optimized_performance["average_time"]
        ) / original_performance["average_time"] if original_performance["average_time"] > 0 else 0
        
        detection_improvement = (
            original_performance["detection_rate"] - optimized_performance["detection_rate"]
        )
        
        return {
            "success_rate_improvement": success_rate_improvement,
            "time_improvement_percent": time_improvement,
            "detection_reduction": detection_improvement,
            "overall_effectiveness": (success_rate_improvement + time_improvement + detection_improvement) / 3
        }
    
    @staticmethod
    def simulate_learning_progression(
        optimizer: RouteOptimizationEngine,
        route_id: str,
        event_batches: List[List[NavigationEvent]]
    ) -> List[Dict[str, Any]]:
        """Simulate learning progression over multiple batches"""
        progression = []
        
        for i, batch in enumerate(event_batches):
            learning_results = optimizer.learn_from_outcomes(batch)
            stats = optimizer.get_learning_statistics()
            
            progression.append({
                "batch_number": i + 1,
                "events_count": len(batch),
                "learning_results": learning_results,
                "learning_stats": stats
            })
        
        return progression


class OptimizationTestUtils:
    """Utilities for optimization testing"""
    
    @staticmethod
    def create_test_optimizer(
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> RouteOptimizationEngine:
        """Create test route optimizer"""
        if config is None:
            config = {
                "learning_enabled": True,
                "performance_window_size": 50,
                "min_samples_for_optimization": 3,
                "optimization_threshold": 0.1,
                "max_alternative_routes": 3
            }
        
        return RouteOptimizationEngine(storage_path=storage_path, config=config)
    
    @staticmethod
    def generate_performance_scenarios() -> List[Dict[str, Any]]:
        """Generate various performance scenarios"""
        return [
            {
                "name": "excellent_performance",
                "success_rate": 0.95,
                "average_time": 1.0,
                "detection_rate": 0.01
            },
            {
                "name": "good_performance",
                "success_rate": 0.85,
                "average_time": 2.0,
                "detection_rate": 0.05
            },
            {
                "name": "moderate_performance",
                "success_rate": 0.70,
                "average_time": 4.0,
                "detection_rate": 0.10
            },
            {
                "name": "poor_performance",
                "success_rate": 0.50,
                "average_time": 6.0,
                "detection_rate": 0.20
            },
            {
                "name": "terrible_performance",
                "success_rate": 0.25,
                "average_time": 10.0,
                "detection_rate": 0.40
            }
        ]
    
    @staticmethod
    def create_timing_dataset(
        base_time: float,
        variation: float,
        count: int
    ) -> List[float]:
        """Create timing dataset with variation"""
        import random
        
        timings = []
        for i in range(count):
            timing = base_time + (random.random() - 0.5) * variation
            timings.append(max(0.1, timing))  # Ensure minimum time
        
        return timings
    
    @staticmethod
    def simulate_optimization_cycle(
        optimizer: RouteOptimizationEngine,
        routes: List[PathPlan],
        event_batches: List[List[NavigationEvent]]
    ) -> Dict[str, Any]:
        """Simulate complete optimization cycle"""
        cycle_results = {
            "initial_analysis": {},
            "learning_progression": [],
            "optimization_recommendations": [],
            "final_performance": {}
        }
        
        # Initial analysis
        for route in routes:
            analysis = optimizer.analyze_route_performance(route.plan_id, [])
            cycle_results["initial_analysis"][route.plan_id] = analysis
        
        # Learning progression
        for i, batch in enumerate(event_batches):
            learning_results = optimizer.learn_from_outcomes(batch)
            cycle_results["learning_progression"].append({
                "batch": i + 1,
                "results": learning_results
            })
        
        # Get recommendations
        recommendations = optimizer.get_optimization_recommendations()
        cycle_results["optimization_recommendations"] = recommendations
        
        # Final analysis
        for route in routes:
            analysis = optimizer.analyze_route_performance(route.plan_id, [])
            cycle_results["final_performance"][route.plan_id] = analysis
        
        return cycle_results
    
    @staticmethod
    def validate_learning_convergence(
        progression_data: List[Dict[str, Any]],
        convergence_threshold: float = 0.05
    ) -> bool:
        """Validate learning convergence over time"""
        if len(progression_data) < 3:
            return False
        
        # Check if learning effectiveness stabilizes
        effectiveness_scores = [
            data["learning_stats"].get("learning_effectiveness", 0)
            for data in progression_data
        ]
        
        # Calculate variance in last few batches
        recent_scores = effectiveness_scores[-3:]
        variance = max(recent_scores) - min(recent_scores)
        
        return variance <= convergence_threshold
    
    @staticmethod
    def measure_optimization_overhead(
        optimizer: RouteOptimizationEngine,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Measure optimization overhead"""
        import time
        
        start_time = time.time()
        
        for operation in operations:
            op_type = operation["type"]
            
            if op_type == "analyze":
                optimizer.analyze_route_performance(
                    operation["route_id"],
                    operation.get("events", [])
                )
            elif op_type == "optimize":
                optimizer.optimize_route_timing(operation["plan"])
            elif op_type == "learn":
                optimizer.learn_from_outcomes(operation.get("events", []))
            elif op_type == "recommend":
                optimizer.get_optimization_recommendations()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return {
            "total_overhead_time": total_time,
            "operations_per_second": len(operations) / total_time,
            "average_operation_time": total_time / len(operations)
        }
    
    @staticmethod
    def create_optimization_benchmark(
        route_count: int,
        events_per_route: int,
        optimization_cycles: int
    ) -> Dict[str, Any]:
        """Create optimization benchmark scenario"""
        return {
            "route_count": route_count,
            "events_per_route": events_per_route,
            "optimization_cycles": optimization_cycles,
            "expected_total_events": route_count * events_per_route,
            "expected_learning_iterations": optimization_cycles,
            "benchmark_duration_estimate": (route_count * events_per_route * optimization_cycles) / 100  # Rough estimate
        }
