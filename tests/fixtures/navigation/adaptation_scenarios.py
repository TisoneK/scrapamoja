"""
Integration test fixtures for route adaptation

Test scenarios for Navigation & Routing Intelligence route adaptation functionality.
"""

from typing import Dict, List, Any, Optional
from src.navigation.models import PathPlan, RouteStep, NavigationEvent, NavigationOutcome
from src.navigation.route_adaptation import AdaptationStrategy


class RouteAdaptationTestScenarios:
    """Test scenarios for route adaptation"""
    
    @staticmethod
    def get_timeout_obstacle_scenario() -> Dict[str, Any]:
        """Timeout obstacle scenario"""
        return {
            "name": "timeout_obstacle",
            "plan_id": "test_plan_timeout",
            "obstacle_type": "timeout",
            "expected_strategy": AdaptationStrategy.RETRY_WITH_DELAY,
            "expected_delay": 2.0,
            "max_retries": 3
        }
    
    @staticmethod
    def get_blocked_route_scenario() -> Dict[str, Any]:
        """Blocked route obstacle scenario"""
        return {
            "name": "blocked_route",
            "plan_id": "test_plan_blocked",
            "obstacle_type": "blocked",
            "expected_strategy": AdaptationStrategy.ALTERNATIVE_PATH,
            "expected_alternative_steps": 2,
            "risk_tolerance": 0.3
        }
    
    @staticmethod
    def get_detection_trigger_scenario() -> Dict[str, Any]:
        """Detection trigger scenario"""
        return {
            "name": "detection_trigger",
            "plan_id": "test_plan_detection",
            "detection_triggers": ["suspicious_timing", "unusual_pattern"],
            "stealth_score_before": 0.2,
            "stealth_score_after": 0.8,
            "expected_recovery": True,
            "recovery_threshold": 0.7
        }
    
    @staticmethod
    def get_network_error_scenario() -> Dict[str, Any]:
        """Network error obstacle scenario"""
        return {
            "name": "network_error",
            "plan_id": "test_plan_network",
            "obstacle_type": "network_error",
            "expected_strategy": AdaptationStrategy.OBSTACLE_AVOIDANCE,
            "expected_avoidance": True
        }
    
    @staticmethod
    def get_graceful_degradation_scenario() -> Dict[str, Any]:
        """Graceful degradation scenario"""
        return {
            "name": "graceful_degradation",
            "plan_id": "test_plan_degrade",
            "obstacle_type": "critical_failure",
            "expected_strategy": AdaptationStrategy.GRACEFUL_DEGRADATION,
            "expected_minimal_steps": 1
        }
    
    @staticmethod
    def get_stealth_enhancement_scenario() -> Dict[str, Any]:
        """Stealth enhancement scenario"""
        return {
            "name": "stealth_enhancement",
            "plan_id": "test_plan_stealth",
            "obstacle_type": "high_risk",
            "expected_strategy": AdaptationStrategy.STEALTH_ENHANCEMENT,
            "original_risk": 0.7,
            "expected_enhanced_risk": 0.4
        }


class MockPathPlans:
    """Mock path plans for testing"""
    
    @staticmethod
    def get_simple_plan(plan_id: str = "test_plan") -> PathPlan:
        """Get simple path plan"""
        steps = [
            RouteStep(
                step_number=1,
                route_id="home_to_about",
                action_type="navigate",
                target_url="about",
                expected_delay=1.0,
                step_description="Navigate from home to about"
            )
        ]
        
        return PathPlan(
            plan_id=plan_id,
            source_context="home",
            target_destination="about",
            route_sequence=steps,
            total_risk_score=0.2,
            estimated_duration=1.0
        )
    
    @staticmethod
    def get_complex_plan(plan_id: str = "test_plan_complex") -> PathPlan:
        """Get complex path plan"""
        steps = [
            RouteStep(
                step_number=1,
                route_id="home_to_products",
                action_type="navigate",
                target_url="products",
                expected_delay=1.0,
                step_description="Navigate from home to products"
            ),
            RouteStep(
                step_number=2,
                route_id="products_to_cart",
                action_type="navigate",
                target_url="cart",
                expected_delay=1.5,
                step_description="Navigate from products to cart"
            ),
            RouteStep(
                step_number=3,
                route_id="cart_to_checkout",
                action_type="form_submit",
                target_url="checkout",
                expected_delay=2.0,
                step_description="Submit checkout form"
            )
        ]
        
        return PathPlan(
            plan_id=plan_id,
            source_context="home",
            target_destination="checkout",
            route_sequence=steps,
            total_risk_score=0.4,
            estimated_duration=4.5
        )
    
    @staticmethod
    def get_high_risk_plan(plan_id: str = "test_plan_risk") -> PathPlan:
        """Get high-risk path plan"""
        steps = [
            RouteStep(
                step_number=1,
                route_id="home_to_admin",
                action_type="javascript_execution",
                target_url="admin",
                expected_delay=0.5,
                step_description="Execute JavaScript to access admin"
            ),
            RouteStep(
                step_number=2,
                route_id="admin_to_settings",
                action_type="form_submit",
                target_url="settings",
                expected_delay=1.0,
                step_description="Submit admin form"
            )
        ]
        
        return PathPlan(
            plan_id=plan_id,
            source_context="home",
            target_destination="settings",
            route_sequence=steps,
            total_risk_score=0.8,
            estimated_duration=1.5
        )


class MockNavigationEvents:
    """Mock navigation events for testing"""
    
    @staticmethod
    def get_success_event(event_id: str = "test_success") -> NavigationEvent:
        """Get successful navigation event"""
        return NavigationEvent(
            event_id=event_id,
            route_id="test_route",
            context_before="step_1",
            context_after="step_2",
            outcome=NavigationOutcome.SUCCESS,
            performance_metrics={
                "duration_seconds": 1.0,
                "cpu_usage_percent": 10.0,
                "memory_usage_mb": 50.0
            }
        )
    
    @staticmethod
    def get_failure_event(event_id: str = "test_failure") -> NavigationEvent:
        """Get failed navigation event"""
        return NavigationEvent(
            event_id=event_id,
            route_id="test_route",
            context_before="step_1",
            context_after="step_1",
            outcome=NavigationOutcome.FAILURE,
            error_details="Element not found",
            error_code="ELEMENT_NOT_FOUND",
            performance_metrics={
                "duration_seconds": 0.5,
                "cpu_usage_percent": 5.0,
                "memory_usage_mb": 45.0
            }
        )
    
    @staticmethod
    def get_timeout_event(event_id: str = "test_timeout") -> NavigationEvent:
        """Get timeout navigation event"""
        return NavigationEvent(
            event_id=event_id,
            route_id="test_route",
            context_before="step_1",
            context_after="step_1",
            outcome=NavigationOutcome.TIMEOUT,
            error_details="Navigation timed out after 30 seconds",
            error_code="TIMEOUT_ERROR",
            performance_metrics={
                "duration_seconds": 30.0,
                "cpu_usage_percent": 15.0,
                "memory_usage_mb": 60.0
            }
        )
    
    @staticmethod
    def get_detection_event(event_id: str = "test_detection") -> NavigationEvent:
        """Get detection trigger event"""
        return NavigationEvent(
            event_id=event_id,
            route_id="test_route",
            context_before="step_1",
            context_after="step_1",
            outcome=NavigationOutcome.DETECTED,
            detection_triggers=["suspicious_timing", "unusual_pattern", "bot_detected"],
            stealth_score_before=0.2,
            stealth_score_after=0.8,
            performance_metrics={
                "duration_seconds": 2.0,
                "cpu_usage_percent": 20.0,
                "memory_usage_mb": 70.0
            }
        )


class AdaptationTestHelpers:
    """Helpers for testing route adaptation"""
    
    @staticmethod
    def validate_adaptation_strategy(
        strategy: AdaptationStrategy,
        expected_strategy: AdaptationStrategy
    ) -> bool:
        """Validate adaptation strategy"""
        return strategy == expected_strategy
    
    @staticmethod
    def validate_alternative_plan(
        original_plan: PathPlan,
        alternative_plan: PathPlan,
        expected_steps: Optional[int] = None
    ) -> bool:
        """Validate alternative plan"""
        if not alternative_plan:
            return False
        
        # Check source and target are preserved
        if (alternative_plan.source_context != original_plan.source_context or
            alternative_plan.target_destination != original_plan.target_destination):
            return False
        
        # Check expected step count
        if expected_steps is not None:
            if len(alternative_plan.route_sequence) != expected_steps:
                return False
        
        # Check plan is different from original
        if alternative_plan.plan_id == original_plan.plan_id:
            return False
        
        return True
    
    @staticmethod
    def validate_stealth_enhancement(
        original_plan: PathPlan,
        enhanced_plan: PathPlan,
        expected_risk_reduction: float = 0.1
    ) -> bool:
        """Validate stealth enhancement"""
        if not enhanced_plan:
            return False
        
        # Check risk is reduced
        risk_reduction = original_plan.total_risk_score - enhanced_plan.total_risk_score
        if risk_reduction < expected_risk_reduction:
            return False
        
        # Check steps are enhanced
        for step in enhanced_plan.route_sequence:
            if not step.metadata or not step.metadata.get("stealth_enhanced"):
                return False
        
        return True
    
    @staticmethod
    def validate_retry_with_delay(
        original_plan: PathPlan,
        retry_plan: PathPlan,
        expected_delay: float
    ) -> bool:
        """Validate retry with delay"""
        if not retry_plan:
            return False
        
        # Check plan is the same (retry uses same plan)
        if retry_plan.plan_id != original_plan.plan_id:
            return False
        
        # Check current step is reset
        if retry_plan.current_step >= original_plan.current_step:
            return False
        
        return True
    
    @staticmethod
    def validate_graceful_degradation(
        original_plan: PathPlan,
        degraded_plan: PathPlan,
        expected_max_steps: int = 2
    ) -> bool:
        """Validate graceful degradation"""
        if not degraded_plan:
            return False
        
        # Check plan has minimal steps
        if len(degraded_plan.route_sequence) > expected_max_steps:
            return False
        
        # Check degradation metadata
        if not degraded_plan.plan_metadata.get("degradation_reason"):
            return False
        
        # Check algorithm is set correctly
        if degraded_plan.plan_metadata.planning_algorithm != "graceful_degradation":
            return False
        
        return True
    
    @staticmethod
    def validate_detection_recovery(
        original_plan: PathPlan,
        recovery_plan: PathPlan,
        detection_event: NavigationEvent
    ) -> bool:
        """Validate detection recovery"""
        if not recovery_plan:
            return False
        
        # Check recovery metadata
        if recovery_plan.plan_metadata.planning_algorithm != "detection_recovery":
            return False
        
        if recovery_plan.plan_metadata.detection_event_id != detection_event.event_id:
            return False
        
        # Check stealth measures are enhanced
        for step in recovery_plan.route_sequence:
            if not step.metadata or not step.metadata.get("stealth_enhanced"):
                return False
        
        return True
    
    @staticmethod
    def calculate_adaptation_success_rate(
        adaptation_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate adaptation success rate"""
        if not adaptation_results:
            return 0.0
        
        successful_adaptations = sum(
            1 for result in adaptation_results
            if result.get("success", False)
        )
        
        return successful_adaptations / len(adaptation_results)
    
    @staticmethod
    def measure_adaptation_performance(
        adaptation_events: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Measure adaptation performance metrics"""
        if not adaptation_events:
            return {
                "average_adaptation_time": 0.0,
                "max_adaptation_time": 0.0,
                "min_adaptation_time": 0.0,
                "total_adaptations": 0
            }
        
        adaptation_times = [
            event.get("adaptation_time", 0.0)
            for event in adaptation_events
        ]
        
        return {
            "average_adaptation_time": sum(adaptation_times) / len(adaptation_times),
            "max_adaptation_time": max(adaptation_times),
            "min_adaptation_time": min(adaptation_times),
            "total_adaptations": len(adaptation_events)
        }


class AdaptationTestUtils:
    """Utilities for adaptation testing"""
    
    @staticmethod
    def create_mock_obstacle(
        obstacle_type: str,
        severity: float = 0.5,
        recoverable: bool = True
    ) -> Dict[str, Any]:
        """Create mock obstacle"""
        return {
            "type": obstacle_type,
            "severity": severity,
            "recoverable": recoverable,
            "timestamp": "2025-01-27T10:00:00Z",
            "context": {
                "url": "https://example.com",
                "step_number": 1,
                "total_steps": 3
            }
        }
    
    @staticmethod
    def create_mock_detection_triggers(
        trigger_types: List[str],
        stealth_score_before: float = 0.2,
        stealth_score_after: float = 0.8
    ) -> Dict[str, Any]:
        """Create mock detection triggers"""
        return {
            "triggers": trigger_types,
            "stealth_score_before": stealth_score_before,
            "stealth_score_after": stealth_score_after,
            "detection_confidence": 0.9,
            "timestamp": "2025-01-27T10:00:00Z"
        }
    
    @staticmethod
    def simulate_adaptation_delay(
        base_delay: float,
        retry_count: int,
        multiplier: float = 1.5
    ) -> float:
        """Simulate adaptation delay calculation"""
        return base_delay * (multiplier ** retry_count)
    
    @staticmethod
    def calculate_strategy_effectiveness(
        strategy_results: Dict[AdaptationStrategy, List[bool]]
    ) -> Dict[AdaptationStrategy, float]:
        """Calculate effectiveness of adaptation strategies"""
        effectiveness = {}
        
        for strategy, results in strategy_results.items():
            if results:
                success_rate = sum(results) / len(results)
                effectiveness[strategy] = success_rate
            else:
                effectiveness[strategy] = 0.0
        
        return effectiveness
    
    @staticmethod
    def create_adaptation_history_entry(
        strategy: AdaptationStrategy,
        obstacle_type: str,
        success: bool,
        duration: float
    ) -> Dict[str, Any]:
        """Create adaptation history entry"""
        return {
            "strategy": strategy.value,
            "obstacle_type": obstacle_type,
            "success": success,
            "duration": duration,
            "timestamp": "2025-01-27T10:00:00Z",
            "correlation_id": "test_correlation_id"
        }
