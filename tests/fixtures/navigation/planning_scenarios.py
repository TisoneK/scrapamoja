"""
Integration test fixtures for path planning

Test scenarios for Navigation & Routing Intelligence path planning functionality.
"""

from typing import Dict, List, Any, Tuple
from src.navigation.models import PathPlan, RouteStep, NavigationContext


class PathPlanningTestScenarios:
    """Test scenarios for path planning"""
    
    @staticmethod
    def get_simple_path_scenario() -> Dict[str, Any]:
        """Simple path planning scenario"""
        return {
            "name": "simple_path",
            "source": "home",
            "target": "about",
            "expected_steps": [
                {
                    "step_number": 1,
                    "route_id": "home_to_about",
                    "action_type": "navigate",
                    "target_url": "about",
                    "expected_delay": 1.0
                }
            ],
            "expected_duration": 1.0,
            "expected_risk_score": 0.2,
            "risk_tolerance": 0.3
        }
    
    @staticmethod
    def get_complex_path_scenario() -> Dict[str, Any]:
        """Complex multi-step path planning scenario"""
        return {
            "name": "complex_path",
            "source": "home",
            "target": "checkout",
            "expected_steps": [
                {
                    "step_number": 1,
                    "route_id": "home_to_products",
                    "action_type": "navigate",
                    "target_url": "products",
                    "expected_delay": 1.0
                },
                {
                    "step_number": 2,
                    "route_id": "products_to_cart",
                    "action_type": "navigate",
                    "target_url": "cart",
                    "expected_delay": 1.5
                },
                {
                    "step_number": 3,
                    "route_id": "cart_to_checkout",
                    "action_type": "navigate",
                    "target_url": "checkout",
                    "expected_delay": 2.0
                }
            ],
            "expected_duration": 4.5,
            "expected_risk_score": 0.4,
            "risk_tolerance": 0.3
        }
    
    @staticmethod
    def get_high_risk_path_scenario() -> Dict[str, Any]:
        """High-risk path planning scenario"""
        return {
            "name": "high_risk_path",
            "source": "home",
            "target": "admin",
            "expected_steps": [
                {
                    "step_number": 1,
                    "route_id": "home_to_login",
                    "action_type": "form_submit",
                    "target_url": "login",
                    "expected_delay": 2.0
                },
                {
                    "step_number": 2,
                    "route_id": "login_to_admin",
                    "action_type": "javascript_execution",
                    "target_url": "admin",
                    "expected_delay": 1.5
                }
            ],
            "expected_duration": 3.5,
            "expected_risk_score": 0.7,
            "risk_tolerance": 0.3
        }
    
    @staticmethod
    def get_no_path_scenario() -> Dict[str, Any]:
        """No path available scenario"""
        return {
            "name": "no_path",
            "source": "home",
            "target": "inaccessible",
            "expected_error": "NO_PATH_FOUND",
            "risk_tolerance": 0.3
        }
    
    @staticmethod
    def get_alternative_paths_scenario() -> Dict[str, Any]:
        """Multiple alternative paths scenario"""
        return {
            "name": "alternative_paths",
            "source": "home",
            "target": "products",
            "primary_path": {
                "steps": [
                    {"step_number": 1, "route_id": "home_to_products_direct", "action_type": "navigate"}
                ],
                "duration": 1.0,
                "risk_score": 0.3
            },
            "alternatives": [
                {
                    "strategy": "minimize_risk",
                    "steps": [
                        {"step_number": 1, "route_id": "home_to_about", "action_type": "navigate"},
                        {"step_number": 2, "route_id": "about_to_products", "action_type": "navigate"}
                    ],
                    "duration": 2.0,
                    "risk_score": 0.2
                },
                {
                    "strategy": "minimize_time",
                    "steps": [
                        {"step_number": 1, "route_id": "home_to_products_fast", "action_type": "navigate"}
                    ],
                    "duration": 0.8,
                    "risk_score": 0.4
                }
            ],
            "max_alternatives": 2
        }


class MockRouteGraphs:
    """Mock route graphs for testing"""
    
    @staticmethod
    def get_simple_graph() -> Dict[str, Any]:
        """Simple graph for basic path planning"""
        return {
            "nodes": ["home", "about", "contact", "products"],
            "edges": [
                {"from": "home", "to": "about", "weight": 1.0},
                {"from": "home", "to": "contact", "weight": 1.1},
                {"from": "home", "to": "products", "weight": 1.2},
                {"from": "about", "to": "contact", "weight": 1.3},
                {"from": "products", "to": "contact", "weight": 1.4}
            ]
        }
    
    @staticmethod
    def get_ecommerce_graph() -> Dict[str, Any]:
        """E-commerce graph for complex path planning"""
        return {
            "nodes": ["home", "products", "electronics", "clothing", "cart", "checkout", "account", "help"],
            "edges": [
                {"from": "home", "to": "products", "weight": 1.0},
                {"from": "home", "to": "account", "weight": 1.1},
                {"from": "home", "to": "help", "weight": 0.8},
                {"from": "products", "to": "electronics", "weight": 1.2},
                {"from": "products", "to": "clothing", "weight": 1.1},
                {"from": "products", "to": "cart", "weight": 1.5},
                {"from": "electronics", "to": "cart", "weight": 1.3},
                {"from": "clothing", "to": "cart", "weight": 1.4},
                {"from": "cart", "to": "checkout", "weight": 1.8},
                {"from": "account", "to": "cart", "weight": 1.6},
                {"from": "help", "to": "home", "weight": 0.9}
            ]
        }
    
    @staticmethod
    def get_disconnected_graph() -> Dict[str, Any]:
        """Graph with disconnected components"""
        return {
            "nodes": ["home", "about", "isolated", "products"],
            "edges": [
                {"from": "home", "to": "about", "weight": 1.0},
                {"from": "home", "to": "products", "weight": 1.2}
                # Note: "isolated" node has no connections
            ]
        }


class ExpectedPathPlans:
    """Expected path plans for validation"""
    
    @staticmethod
    def get_simple_plan() -> Dict[str, Any]:
        """Expected simple path plan"""
        return {
            "plan_id": "test_plan_simple",
            "source_context": "home",
            "target_destination": "about",
            "route_sequence": [
                {
                    "step_number": 1,
                    "route_id": "home_to_about",
                    "action_type": "navigate",
                    "target_url": "about",
                    "expected_delay": 1.0
                }
            ],
            "total_risk_score": 0.2,
            "estimated_duration": 1.0,
            "status": "planned"
        }
    
    @staticmethod
    def get_complex_plan() -> Dict[str, Any]:
        """Expected complex path plan"""
        return {
            "plan_id": "test_plan_complex",
            "source_context": "home",
            "target_destination": "checkout",
            "route_sequence": [
                {
                    "step_number": 1,
                    "route_id": "home_to_products",
                    "action_type": "navigate",
                    "target_url": "products",
                    "expected_delay": 1.0
                },
                {
                    "step_number": 2,
                    "route_id": "products_to_cart",
                    "action_type": "navigate",
                    "target_url": "cart",
                    "expected_delay": 1.5
                },
                {
                    "step_number": 3,
                    "route_id": "cart_to_checkout",
                    "action_type": "navigate",
                    "target_url": "checkout",
                    "expected_delay": 2.0
                }
            ],
            "total_risk_score": 0.4,
            "estimated_duration": 4.5,
            "status": "planned"
        }


class PathPlanningValidationHelpers:
    """Helpers for validating path planning results"""
    
    @staticmethod
    def validate_plan_structure(plan: PathPlan) -> bool:
        """Validate basic path plan structure"""
        return (
            plan.plan_id is not None and
            plan.source_context is not None and
            plan.target_destination is not None and
            isinstance(plan.route_sequence, list)
        )
    
    @staticmethod
    def validate_route_sequence(plan: PathPlan) -> bool:
        """Validate route sequence structure"""
        if not plan.route_sequence:
            return True
        
        for i, step in enumerate(plan.route_sequence):
            if step.step_number != i + 1:
                return False
            if not step.route_id or not step.action_type:
                return False
        
        return True
    
    @staticmethod
    def validate_path_metrics(plan: PathPlan) -> bool:
        """Validate path metrics are reasonable"""
        if not plan.route_sequence:
            return plan.estimated_duration == 0.0 and plan.total_risk_score == 0.0
        
        # Check duration is reasonable
        if plan.estimated_duration < 0:
            return False
        
        # Check risk score is within bounds
        if not (0.0 <= plan.total_risk_score <= 1.0):
            return False
        
        return True
    
    @staticmethod
    def validate_path_exists(graph, source: str, target: str) -> bool:
        """Validate that path exists in graph"""
        try:
            import networkx as nx
            return nx.has_path(graph, source, target)
        except:
            return False
    
    @staticmethod
    def validate_path_optimization(
        plan: PathPlan,
        max_duration: float = 10.0,
        max_risk: float = 0.8
    ) -> bool:
        """Validate path meets optimization criteria"""
        return (
            plan.estimated_duration <= max_duration and
            plan.total_risk_score <= max_risk
        )
    
    @staticmethod
    def validate_alternative_paths(
        primary_plan: PathPlan,
        alternatives: list,
        min_alternatives: int = 1
    ) -> bool:
        """Validate alternative paths are different from primary"""
        if len(alternatives) < min_alternatives:
            return False
        
        primary_steps = {(step.route_id, step.action_type) for step in primary_plan.route_sequence}
        
        for alt_plan in alternatives:
            alt_steps = {(step.route_id, step.action_type) for step in alt_plan.route_sequence}
            if alt_steps == primary_steps:
                return False  # Alternative is identical to primary
        
        return True
    
    @staticmethod
    def validate_risk_tolerance(
        plan: PathPlan,
        risk_tolerance: float
    ) -> bool:
        """Validate plan meets risk tolerance"""
        return plan.total_risk_score <= risk_tolerance
    
    @staticmethod
    def validate_timing_constraints(plan: PathPlan) -> bool:
        """Validate timing constraints are reasonable"""
        for step in plan.route_sequence:
            if step.expected_delay < 0 or step.expected_delay > 10.0:
                return False
        return True
    
    @staticmethod
    def calculate_path_efficiency(plan: PathPlan) -> float:
        """Calculate path efficiency score"""
        if not plan.route_sequence:
            return 1.0
        
        # Efficiency based on path length and risk
        length_factor = 1.0 / len(plan.route_sequence)
        risk_factor = 1.0 - plan.total_risk_score
        time_factor = 1.0 / (1.0 + plan.estimated_duration)
        
        return (length_factor + risk_factor + time_factor) / 3.0


class PathPlanningTestUtils:
    """Utilities for path planning tests"""
    
    @staticmethod
    def create_mock_plan(
        plan_id: str,
        source: str,
        target: str,
        steps: List[Tuple[str, str, str, float]] = None
    ) -> PathPlan:
        """Create mock path plan for testing"""
        plan = PathPlan(
            plan_id=plan_id,
            source_context=source,
            target_destination=target
        )
        
        if steps:
            route_steps = []
            for i, (route_id, action_type, target_url, delay) in enumerate(steps, 1):
                step = RouteStep(
                    step_number=i,
                    route_id=route_id,
                    action_type=action_type,
                    target_url=target_url,
                    expected_delay=delay
                )
                route_steps.append(step)
            plan.route_sequence = route_steps
        
        return plan
    
    @staticmethod
    def create_mock_context(context_id: str, url: str) -> NavigationContext:
        """Create mock navigation context"""
        from src.navigation.models import PageState
        
        page_state = PageState(url=url, title=f"Page {url}")
        
        return NavigationContext(
            context_id=context_id,
            session_id=f"session_{context_id}",
            current_page=page_state
        )
    
    @staticmethod
    def compare_plans(plan1: PathPlan, plan2: PathPlan) -> Dict[str, Any]:
        """Compare two path plans"""
        comparison = {
            "same_id": plan1.plan_id == plan2.plan_id,
            "same_source": plan1.source_context == plan2.source_context,
            "same_target": plan1.target_destination == plan2.target_destination,
            "same_step_count": len(plan1.route_sequence) == len(plan2.route_sequence),
            "duration_diff": plan1.estimated_duration - plan2.estimated_duration,
            "risk_diff": plan1.total_risk_score - plan2.total_risk_score
        }
        
        # Compare route sequences
        steps1 = [(step.route_id, step.action_type) for step in plan1.route_sequence]
        steps2 = [(step.route_id, step.action_type) for step in plan2.route_sequence]
        comparison["same_steps"] = steps1 == steps2
        
        return comparison
