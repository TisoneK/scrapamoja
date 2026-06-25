"""
Dynamic route adaptation

Monitor navigation execution and dynamically adapt routes when encountering unexpected page states,
blocked paths, or detection triggers.
Conforms to Constitution Principle II - Stealth-Aware Design.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from .interfaces import IRouteAdaptation
from .models import PathPlan, NavigationContext, NavigationEvent, NavigationOutcome
from .exceptions import NavigationExecutionError
from .integrations.stealth_integration import StealthSystemIntegration
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id


class AdaptationStrategy(Enum):
    """Route adaptation strategies"""
    RETRY_WITH_DELAY = "retry_with_delay"
    ALTERNATIVE_PATH = "alternative_path"
    STEALTH_ENHANCEMENT = "stealth_enhancement"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    GRACEFUL_DEGRADATION = "graceful_degradation"


class RouteAdaptation(IRouteAdaptation):
    """Dynamic route adaptation implementation"""
    
    def __init__(
        self,
        stealth_system_client=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize route adaptation with dependencies"""
        self.logger = get_navigation_logger("route_adaptation")
        self.config = config or {}
        
        # Initialize stealth integration
        self.stealth_integration = StealthSystemIntegration(stealth_system_client)
        
        # Adaptation state
        self._correlation_id: Optional[str] = None
        self._active_plans: Dict[str, PathPlan] = {}
        self._adaptation_history: List[Dict[str, Any]] = []
        
        # Configuration
        self.max_retry_attempts = self.config.get("max_retry_attempts", 3)
        self.retry_delay_base = self.config.get("retry_delay_base", 2.0)
        self.retry_delay_multiplier = self.config.get("retry_delay_multiplier", 1.5)
        self.detection_recovery_threshold = self.config.get("detection_recovery_threshold", 0.7)
        
        # Adaptation strategy weights
        self.strategy_weights = {
            AdaptationStrategy.RETRY_WITH_DELAY: 0.3,
            AdaptationStrategy.ALTERNATIVE_PATH: 0.4,
            AdaptationStrategy.STEALTH_ENHANCEMENT: 0.2,
            AdaptationStrategy.OBSTACLE_AVOIDANCE: 0.1,
            AdaptationStrategy.GRACEFUL_DEGRADATION: 0.0
        }
    
    async def monitor_navigation(
        self,
        path_plan: PathPlan
    ) -> NavigationEvent:
        """Monitor navigation execution"""
        start_time = datetime.utcnow()
        
        # Generate correlation ID for this monitoring session
        self._correlation_id = generate_correlation_id()
        set_correlation_id(self._correlation_id)
        
        self.logger.debug(
            "Starting navigation monitoring",
            plan_id=path_plan.plan_id,
            steps_count=len(path_plan.route_sequence)
        )
        
        try:
            # Register the plan for monitoring
            self._active_plans[path_plan.plan_id] = path_plan
            
            # Start execution monitoring
            event = await self._execute_navigation_step(path_plan, 0)
            
            # Continue monitoring until completion or failure
            while event.outcome == NavigationOutcome.SUCCESS and path_plan.current_step < len(path_plan.route_sequence):
                next_step = path_plan.get_next_step()
                if next_step:
                    event = await self._execute_navigation_step(path_plan, path_plan.current_step + 1)
                else:
                    # No more steps, navigation completed successfully
                    break
            
            # Finalize monitoring
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            event.performance_metrics.duration_seconds = execution_time
            
            self.logger.info(
                "Navigation monitoring completed",
                plan_id=path_plan.plan_id,
                outcome=event.outcome.value,
                execution_time=execution_time,
                steps_completed=path_plan.current_step + 1
            )
            
            return event
            
        except Exception as e:
            self.logger.error(
                f"Navigation monitoring failed: {str(e)}",
                plan_id=path_plan.plan_id,
                correlation_id=self._correlation_id
            )
            
            # Create failure event
            failure_event = NavigationEvent(
                event_id=f"monitor_failure_{self._correlation_id}",
                route_id="unknown",
                context_before="unknown",
                context_after="unknown",
                outcome=NavigationOutcome.FAILURE,
                error_details=str(e)
            )
            
            return failure_event
    
    async def adapt_to_obstacles(
        self,
        current_plan: PathPlan,
        obstacle_type: str
    ) -> Optional[PathPlan]:
        """Adapt route when encountering obstacles"""
        try:
            set_correlation_id(self._correlation_id)
            
            self.logger.adaptation_triggered(
                obstacle_type,
                current_plan.plan_id
            )
            
            # Determine adaptation strategy
            strategy = await self._determine_adaptation_strategy(
                current_plan, obstacle_type
            )
            
            if strategy == AdaptationStrategy.ALTERNATIVE_PATH:
                return await self._generate_alternative_plan(current_plan, obstacle_type)
            elif strategy == Adaptation.RETRY_WITH_DELAY:
                return await self._retry_with_delay(current_plan, obstacle_type)
            elif strategy == Adaptation.STEALTH_ENHANCEMENT:
                return await self._enhance_stealth_measures(current_plan)
            elif strategy == Adaptation.OBSTACLE_AVOIDANCE:
                return await self._avoid_obstacle(current_plan, obstacle_type)
            elif strategy == Adaptation.GRACEFUL_DEGRADATION:
                return await self._graceful_degradation(current_plan)
            else:
                self.logger.warning(
                    f"No adaptation strategy available for obstacle type: {obstacle_type}",
                    obstacle_type=obstacle_type
                )
                return None
                
        except Exception as e:
            self.logger.error(
                f"Route adaptation failed: {str(e)}",
                plan_id=current_plan.plan_id,
                obstacle_type=obstacle_type,
                correlation_id=self._correlation_id
            )
            raise NavigationExecutionError(
                f"Failed to adapt plan {current_plan.plan_id} for obstacle {obstacle_type}: {str(e)}",
                "ADAPTATION_FAILED",
                {
                    "plan_id": current_plan.plan_id,
                    "obstacle_type": obstacle_type,
                    "correlation_id": self._correlation_id
                }
            )
    
    async def handle_detection_triggers(
        self,
        detection_event: NavigationEvent
    ) -> Optional[PathPlan]:
        """Handle anti-bot detection triggers"""
        try:
            set_correlation_id(self._correlation_id)
            
            self.logger.warning(
                "Detection trigger encountered",
                plan_id=detection_event.route_id,
                triggers=detection_event.detection_triggers,
                stealth_score_before=detection_event.stealth_score_before,
                stealth_score_after=detection_event.stealth_score_after
            )
            
            # Record detection event in history
            self._record_adaptation_event({
                "type": "detection_trigger",
                "plan_id": detection_event.route_id,
                "triggers": detection_event.detection_triggers,
                "stealth_before": detection_event.stealth_score_before,
                "stealth_after": detection_event.stealth_score_after,
                "timestamp": detection_event.timestamp.isoformat()
            })
            
            # Determine if recovery is needed
            if detection_event.stealth_score_after > self.detection_recovery_threshold:
                return await self._recover_from_detection(detection_event)
            else:
                # Minor detection, continue with enhanced stealth
                current_plan = self._get_active_plan(detection_event.route_id)
                if current_plan:
                    return await self._enhance_stealth_measures(current_plan)
            
            return None
            
        except Exception as e:
            self.logger.error(
                f"Detection trigger handling failed: {str(e)}",
                event_id=detection_event.event_id,
                correlation_id=self._correlation_id
            )
            raise NavigationExecutionError(
                f"Failed to handle detection trigger for {detection_event.event_id}: {str(e)}",
                "DETECTION_HANDLING_FAILED",
                {
                    "event_id": detection_event.event_id,
                    "correlation_id": self._correlation_id
                }
            )
    
    async def _execute_navigation_step(
        self,
        path_plan: PathPlan,
        step_index: int
    ) -> NavigationEvent:
        """Execute a single navigation step"""
        try:
            step = path_plan.get_current_step()
            if not step:
                return NavigationEvent(
                    event_id=f"step_complete_{self._correlation_id}_{step_index}",
                    route_id=step.route_id,
                    context_before=f"step_{step_index}",
                    context_after=f"step_{step_index + 1}",
                    outcome=NavigationOutcome.SUCCESS
                )
            
            self.logger.debug(
                "Executing navigation step",
                plan_id=path_plan.plan_id,
                step_number=step.step_number,
                route_id=step.route_id,
                action_type=step.action_type,
                target_url=step.target_url
            )
            
            # Simulate step execution (in real implementation, this would use Playwright)
            await asyncio.sleep(step.expected_delay)
            
            # Update plan progress
            path_plan.advance_to_next_step()
            
            # Create success event
            success_event = NavigationEvent(
                event_id=f"step_success_{self._correlation_id}_{step_index}",
                route_id=step.route_id,
                context_before=f"step_{step_index}",
                context_after=f"step_{step_index + 1}",
                outcome=NavigationOutcome.SUCCESS,
                performance_metrics={
                    "duration_seconds": step.expected_delay
                }
            )
            
            return success_event
            
        except Exception as e:
            self.logger.error(
                f"Navigation step execution failed: {str(e)}",
                plan_id=path_plan.plan_id,
                step_index=step_index,
                correlation_id=self._correlation_id
            )
            
            # Create failure event
            failure_event = NavigationEvent(
                event_id=f"step_failure_{self._correlation_id}_{step_index}",
                route_id="unknown",
                context_before=f"step_{step_index}",
                context_after=f"step_{step_index + 1}",
                outcome=NavigationOutcome.FAILURE,
                error_details=str(e)
            )
            
            return failure_event
    
    async def _determine_adaptation_strategy(
        self,
        plan: PathPlan,
        obstacle_type: str
    ) -> AdaptationStrategy:
        """Determine best adaptation strategy for obstacle"""
        
        # Analyze obstacle type and plan state
        obstacle_severity = self._assess_obstacle_severity(obstacle_type)
        plan_progress = plan.get_execution_progress()
        risk_score = plan.total_risk_score
        
        # Calculate strategy scores
        strategy_scores = {}
        
        for strategy in AdaptationStrategy:
            score = self._calculate_strategy_score(
                strategy, obstacle_severity, plan_progress, risk_score
            )
            strategy_scores[strategy] = score
        
        # Select best strategy
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        
        self.logger.debug(
            "Selected adaptation strategy",
            strategy=best_strategy,
            scores=strategy_scores,
            obstacle_type=obstacle_type,
            obstacle_severity=obstacle_severity,
            plan_progress=plan_progress,
            risk_score=risk_score
        )
        
        return best_strategy
    
    def _assess_obstacle_severity(self, obstacle_type: str) -> float:
        """Assess severity of obstacle type"""
        severity_map = {
            "timeout": 0.7,
            "blocked": 0.8,
            "404_error": 0.6,
            "network_error": 0.5,
            "javascript_error": 0.4,
            "element_not_found": 0.3,
            "timeout_error": 0.7,
            "connection_error": 0.6,
            "ssl_error": 0.5
        }
        
        return severity_map.get(obstacle_type.lower(), 0.5)
    
    def _calculate_strategy_score(
        self,
        strategy: AdaptationStrategy,
        obstacle_severity: float,
        plan_progress: float,
        risk_score: float
    ) -> float:
        """Calculate score for adaptation strategy"""
        base_score = self.strategy_weights[strategy]
        
        # Adjust score based on context
        if strategy == AdaptationStrategy.RETRY_WITH_DELAY:
            # Good for low severity, early progress
            if obstacle_severity < 0.5 and plan_progress < 0.3:
                return base_score * 1.2
            elif obstacle_severity > 0.7:
                return base_score * 0.3  # Retry is bad for high severity
        
        elif strategy == AdaptationStrategy.ALTERNATIVE_PATH:
            # Good for high severity or late progress
            if obstacle_severity > 0.6 or plan_progress > 0.7:
                return base_score * 1.3
            elif risk_score > 0.7:
                return base_score * 1.1
        
        elif strategy == AdaptationStrategy.STEALTH_ENHANCEMENT:
            # Good when risk is high
            if risk_score > 0.6:
                return base_score * 1.2
        
        elif strategy == AdaptationStrategy.OBSTACLE_AVOIDANCE:
            # Good for specific known obstacles
            if obstacle_type in ["blocked", "404_error", "connection_error"]:
                return base_score * 1.4
        
        elif strategy == Adaptation.GRACEFUL_DEGRADATION:
            # Last resort for severe issues
            if obstacle_severity > 0.8 or plan_progress > 0.9:
                return base_score * 1.5
        
        return base_score
    
    async def _generate_alternative_path(
        self,
        current_plan: PathPlan,
        obstacle_type: str
    ) -> PathPlan:
        """Generate alternative path for obstacle"""
        try:
            self.logger.info(
                "Generating alternative path",
                original_plan_id=current_plan.plan_id,
                obstacle_type=obstacle_type
            )
            
            # Create new plan with same source and target
            alternative_plan = PathPlan(
                plan_id=f"alt_{self._correlation_id}_{hash(obstacle_type) % 1000}",
                source_context=current_plan.source_context,
                target_destination=current_plan.target_destination
            )
            
            # Get route graph for alternative path finding
            route_graph = await self._get_route_graph()
            
            # Find alternative path avoiding the problematic area
            if obstacle_type in ["blocked", "404_error"]:
                # Try to find path that avoids the blocked route
                alternative_path = await self._find_avoiding_path(
                    route_graph,
                    current_plan.source_context,
                    current_plan.target_destination,
                    blocked_route_id=self._get_current_route_id(current_plan)
                )
            else:
                # Use standard alternative path generation
                alternative_path = await self._generate_standard_alternative(
                    route_graph,
                    current_plan.source_context,
                    current_plan.target_destination
                )
            
            if not alternative_path:
                self.logger.warning(
                    "No alternative path found",
                    source=current_plan.source_context,
                    target=current_plan.target_destination
                )
                return None
            
            # Create route steps from alternative path
            route_steps = await self._create_route_steps_from_path(alternative_path)
            alternative_plan.route_sequence = route_steps
            
            # Calculate metrics
            await self._calculate_path_metrics(alternative_plan)
            
            # Set fallback relationship
            alternative_plan.fallback_plans = [current_plan.plan_id]
            
            # Update metadata
            alternative_plan.plan_metadata.planning_algorithm = f"alternative_for_{obstacle_type}"
            alternative_plan.plan_metadata.obstacle_type = obstacle_type
            
            self.logger.info(
                "Alternative path generated",
                alternative_plan_id=alternative_plan.plan_id,
                steps_count=len(route_steps),
                estimated_duration=alternative_plan.estimated_duration,
                risk_score=alternative_plan.total_risk_score
            )
            
            return alternative_plan
            
        except Exception as e:
            self.logger.error(
                f"Alternative path generation failed: {str(e)}",
                original_plan_id=current_plan.plan_id,
                obstacle_type=obstacle_type
            )
            raise NavigationExecutionError(
                f"Failed to generate alternative path for {current_plan.plan_id}: {str(e)}",
                "ALTERNATIVE_PATH_FAILED",
                {
                    "plan_id": current_plan.plan_id,
                    "obstacle_type": obstacle_type,
                    "correlation_id": self._correlation_id
                }
            )
    
    async def _retry_with_delay(
        self,
        current_plan: PathPlan,
        obstacle_type: str
    ) -> PathPlan:
        """Retry current plan with delay"""
        try:
            self.logger.info(
                "Retrying with delay",
                plan_id=current_plan.plan_id,
                obstacle_type=obstacle_type,
                current_step=current_plan.current_step
            )
            
            # Calculate retry delay
            retry_count = len([
                e for e in self._adaptation_history
                if e.get("plan_id") == current_plan.plan_id and e.get("type") == "retry"
            ])
            
            delay = self.retry_delay_base * (self.retry_delay_multiplier ** retry_count)
            delay = min(delay, 30.0)  # Cap at 30 seconds
            
            self.logger.debug(
                "Applying retry delay",
                plan_id=current_plan.plan_id,
                retry_count=retry_count + 1,
                delay=delay
            )
            
            # Wait before retry
            await asyncio.sleep(delay)
            
            # Reset to current step for retry
            current_plan.current_step = max(0, current_plan.current_step - 1)
            
            # Record retry in history
            self._record_adaptation_event({
                "type": "retry_with_delay",
                "plan_id": current_plan.plan_id,
                "obstacle_type": obstacle_type,
                "retry_count": retry_count + 1,
                "delay": delay,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return current_plan
            
        except Exception as e:
            self.logger.error(
                f"Retry with delay failed: {str(e)}",
                plan_id=current_plan.plan_id,
                obstacle_type=obstacle_type
            )
            raise NavigationExecutionError(
                f"Failed to retry plan {current_plan.plan_id} with delay: {str(e)}",
                "RETRY_DELAY_FAILED",
                {
                    "plan_id": current_plan.plan_id,
                    "obstacle_type": obstacle_type,
                    "correlation_id": self._correlation_id
                }
            )
    
    async def _enhance_stealth_measures(
        self,
        plan: PathPlan
    ) -> PathPlan:
        """Enhance stealth measures for the plan"""
        try:
            self.logger.info(
                "Enhancing stealth measures",
                plan_id=plan.plan_id,
                current_risk=plan.total_risk_score
            )
            
            # Create enhanced plan with stealth improvements
            enhanced_plan = PathPlan(
                plan_id=f"enhanced_{self._correlation_id}",
                source_context=plan.source_context,
                target_destination=plan.target_destination
            )
            
            # Copy existing route sequence
            enhanced_plan.route_sequence = plan.route_sequence.copy()
            
            # Enhance each step with stealth measures
            for step in enhanced_plan.route_sequence:
                step = await self._enhance_step_stealth(step)
            
            # Recalculate metrics with enhanced stealth
            await self._calculate_path_metrics(enhanced_plan)
            
            # Update metadata
            enhanced_plan.plan_metadata.planning_algorithm = "stealth_enhanced"
            
            # Set fallback relationship
            enhanced_plan.fallback_plans = [plan.plan_id]
            
            self.logger.info(
                "Stealth measures enhanced",
                enhanced_plan_id=enhanced_plan.plan_id,
                original_risk=plan.total_risk_score,
                enhanced_risk=enhanced_plan.total_risk_score
            )
            
            return enhanced_plan
            
        except Exception as e:
            self.logger.error(
                f"Stealth enhancement failed: {str(e)}",
                plan_id=plan.plan_id
            )
            raise NavigationExecutionError(
                f"Failed to enhance stealth measures for {plan.plan_id}: {str(e)}",
                "STEALTH_ENHANCEMENT_FAILED",
                {"plan_id": plan.plan_id}
            )
    
    async def _enhance_step_stealth(self, step: RouteStep) -> RouteStep:
        """Enhance stealth measures for a single step"""
        enhanced_step = RouteStep(
            step_number=step.step_number,
            route_id=step.route_id,
            action_type=step.action_type,
            target_url=step.target_url,
            expected_delay=step.expected_delay,
            step_description=step.step_description
        )
        
        # Get stealth timing patterns for this action type
        timing_patterns = await self.stealth_integration.get_timing_patterns(step.action_type)
        
        # Apply stealth timing variations
        base_delay = timing_patterns.get("mean_delay", 1.0)
        variation = timing_patterns.get("std_deviation", 0.3)
        
        # Add random variation to appear more human-like
        import random
        stealth_delay = base_delay + random.uniform(-variation, variation)
        enhanced_step.expected_delay = max(0.1, stealth_delay)
        
        # Add stealth metadata
        enhanced_step.metadata = step.metadata.copy() if step.metadata else {}
        enhanced_step.metadata["stealth_enhanced"] = True
        enhanced_step.metadata["original_delay"] = step.expected_delay
        enhanced_step.metadata["stealth_delay"] = stealth_delay
        
        return enhanced_step
    
    async def _avoid_obstacle(
        self,
        graph,
        source: str,
        target: str,
        blocked_route_id: Optional[str] = None
    ) -> List[str]:
        """Find path that avoids specific obstacle"""
        try:
            # Remove blocked route from graph temporarily
            modified_graph = graph.copy()
            
            if blocked_route_id and modified_graph.has_node(blocked_route_id):
                # Remove the blocked route
                modified_graph.remove_node(blocked_route_id)
            
            # Find alternative path
            try:
                path = nx.dijkstra_path(modified_graph, source, target)
                return path
            except nx.NetworkXNoPath:
                return []
                
        except Exception as e:
            self.logger.error(
                f"Obstacle avoidance failed: {str(e)}",
                source=source,
                target=target,
                blocked_route_id=blocked_route_id
            )
            return []
    
    async def _generate_standard_alternative(
        self,
        graph,
        source: str,
        target: str
    ) -> List[str]:
        """Generate standard alternative path"""
        try:
            # Use different algorithm or parameters
            if graph.number_of_nodes() > 50:
                # For large graphs, try A* with heuristic
                path = nx.astar_path(graph, source, target)
            else:
                # For smaller graphs, try all paths and pick best
                paths = list(nx.all_simple_paths(graph, source, target, cutoff=5))
                if paths:
                    # Choose path with best score
                    weights = await self._calculate_path_weights(graph, paths)
                    best_index = weights.index(min(weights))
                    path = paths[best_index]
                else:
                    path = []
            
            return path
            
        except Exception as e:
            self.logger.error(
                f"Standard alternative generation failed: {str(e)}",
                source=source,
                target=target
            )
            return []
    
    async def _get_current_route_id(self, plan: PathPlan) -> Optional[str]:
        """Get current route ID from plan"""
        if plan.current_step < len(plan.route_sequence):
            return plan.route_sequence[plan.current_step].route_id
        return None
    
    async def _create_route_steps_from_path(self, path: List[str]) -> List[RouteStep]:
        """Create route steps from path"""
        steps = []
        
        for i, (source, target) in enumerate(zip(path[:-1], path[1:]), 1):
            step = RouteStep(
                step_number=i + 1,
                route_id=f"{source}_to_{target}",
                action_type="navigate",
                target_url=target,
                expected_delay=1.0,
                step_description=f"Navigate from {source} to {target}"
            )
            steps.append(step)
        
        return steps
    
    async def _get_route_graph(self) -> Any:
        """Get route graph for planning"""
        # This would integrate with route discovery
        # For now, return a placeholder implementation
        
        # Create a simple test graph
        graph = nx.DiGraph()
        
        # Add some test nodes and edges
        nodes = ["home", "about", "contact", "products", "cart", "checkout"]
        for node in nodes:
            graph.add_node(node)
        
        # Add edges with weights (time + risk)
        edges = [
            ("home", "about", 1.0),
            ("home", "products", 1.2),
            ("home", "contact", 1.1),
            ("products", "cart", 1.5),
            ("cart", "checkout", 1.8),
            ("about", "contact", 1.3)
        ]
        
        for source, target, weight in edges:
            graph.add_edge(source, target, weight)
        
        return graph
    
    async def _calculate_path_metrics(self, plan: PathPlan) -> None:
        """Calculate path metrics"""
        if not plan.route_sequence:
            plan.estimated_duration = 0.0
            plan.total_risk_score = 0.0
            return
        
        # Calculate estimated duration
        total_duration = sum(step.expected_delay for step in plan.route_sequence)
        plan.estimated_duration = total_duration
        
        # Calculate total risk score
        total_risk = 0.0
        for step in plan.route_sequence:
            step_risk = await self._evaluate_step_risk(step)
            total_risk += step_risk
        
        plan.total_risk_score = total_risk / len(plan.route_sequence)
    
    async def _evaluate_step_risk(self, step: RouteStep) -> float:
        """Evaluate risk for individual step"""
        # Get timing patterns for this interaction type
        timing_patterns = await self.stealth_integration.get_timing_patterns(step.action_type)
        
        # Base risk assessment
        base_risk = 0.1
        
        # Adjust risk based on step characteristics
        if step.action_type == "form_submit":
            base_risk += 0.2
        elif step.action_type == "javascript_execution":
            base_risk += 0.3
        elif step.action_type == "navigate":
            base_risk += 0.1
        
        # Adjust based on timing
        if step.expected_delay < timing_patterns.get("min_delay", 0.5):
            base_risk += 0.2  # Too fast is suspicious
        
        # Ensure risk is within bounds
        return min(1.0, max(0.0, base_risk))
    
    def _get_active_plan(self, plan_id: str) -> Optional[PathPlan]:
        """Get active plan by ID"""
        return self._active_plans.get(plan_id)
    
    def _record_adaptation_event(self, event_data: Dict[str, Any]) -> None:
        """Record adaptation event in history"""
        event_data["correlation_id"] = self._correlation_id
        self._adaptation_history.append(event_data)
        
        # Keep history manageable
        if len(self._adaptation_history) > 1000:
            self._adaptation_history = self._adaptation_history[-500:]
    
    async def _recover_from_detection(
        self,
        detection_event: NavigationEvent
    ) -> Optional[PathPlan]:
        """Recover from detection trigger"""
        try:
            self.logger.warning(
                "Recovering from detection trigger",
                event_id=detection_event.event_id,
                stealth_score_before=detection_event.stealth_score_before,
                stealth_score_after=detection_event.stealth_score_after
            )
            
            # Get current plan
            current_plan = self._get_active_plan(detection_event.route_id)
            if not current_plan:
                return None
            
            # Implement recovery strategy
            recovery_plan = await self._create_recovery_plan(current_plan, detection_event)
            
            if recovery_plan:
                self.logger.info(
                    "Recovery plan created",
                    recovery_plan_id=recovery_plan.plan_id,
                    original_plan_id=current_plan.plan_id
                )
                
                # Replace current plan with recovery plan
                self._active_plans[recovery_plan.plan_id] = recovery_plan
                return recovery_plan
            
            return None
            
        except Exception as e:
            self.logger.error(
                f"Detection recovery failed: {str(e)}",
                event_id=detection_event.event_id
            )
            return None
    
    async def _create_recovery_plan(
        self,
        original_plan: PathPlan,
        detection_event: NavigationEvent
    ) -> PathPlan:
        """Create recovery plan after detection"""
        recovery_plan = PathPlan(
            plan_id=f"recovery_{self._correlation_id}_{hash(detection_event.event_id) % 1000}",
            source_context=original_plan.source_context,
            target_destination=original_plan.target_destination
        )
        
        # Copy remaining steps after current step
        current_step = original_plan.current_step
        remaining_steps = original_plan.get_remaining_steps()
        
        # Add remaining steps with enhanced stealth measures
        for i, step in enumerate(remaining_steps, current_step + 1):
            enhanced_step = await self._enhance_step_stealth(step)
            recovery_plan.route_sequence.append(enhanced_step)
        
        # Calculate metrics
        await self._calculate_path_metrics(recovery_plan)
        
        # Update metadata
        recovery_plan.plan_metadata.planning_algorithm = "detection_recovery"
        recovery_plan.plan_metadata.detection_event_id = detection_event.event_id
        
        return recovery_plan
    
    async def _graceful_degradation(
        self,
        plan: PathPlan
    ) -> PathPlan:
        """Gracefully degrade navigation when all else fails"""
        try:
            self.logger.warning(
                "Graceful degradation initiated",
                plan_id=plan.plan_id,
                current_step=plan.current_step,
                total_steps=len(plan.route_sequence)
            )
            
            # Create degraded plan with minimal functionality
            degraded_plan = PathPlan(
                plan_id=f"degraded_{self._correlation_id}_{plan.plan_id}",
                source_context=plan.source_context,
                target_destination=plan.target_destination
            )
            
            # Keep only the first step or create simple fallback
            if plan.route_sequence:
                first_step = plan.route_sequence[0]
                degraded_plan.route_sequence = [first_step]
                degraded_plan.estimated_duration = first_step.expected_delay * 2.0  # Double delay for safety
            else:
                # Create minimal fallback step
                fallback_step = RouteStep(
                    step_number=1,
                    route_id="fallback_navigation",
                    action_type="navigate",
                    target_url=plan.target_destination,
                    expected_delay=5.0,
                    step_description="Fallback navigation"
                )
                degraded_plan.route_sequence = [fallback_step]
            
            # Calculate metrics
            await self._calculate_path_metrics(degraded_plan)
            
            # Update metadata
            degraded_plan.plan_metadata.planning_algorithm = "graceful_degradation"
            degraded_plan.plan_metadata.degradation_reason = "all_else_failed"
            
            self.logger.warning(
                "Graceful degradation completed",
                degraded_plan_id=degraded_plan.plan_id,
                remaining_steps=len(degraded_plan.route_sequence)
            )
            
            return degraded_plan
            
        except Exception as e:
            self.logger.error(
                f"Graceful degradation failed: {str(e)}",
                plan_id=plan.plan_id
            )
            raise NavigationExecutionError(
                f"Failed to gracefully degrade plan {plan.plan_id}: {str(e)}",
                "GRACEFUL_DEGRADATION_FAILED",
                {"plan_id": plan.plan_id}
            )
