"""
Route optimization and learning

Learn from navigation outcomes to optimize future routing decisions, building knowledge 
about successful paths, timing patterns, and detection avoidance techniques.
Conforms to Constitution Principle III - Deep Modularity.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict, deque
import statistics

from .interfaces import IRouteOptimizer
from .models import PathPlan, RouteStep, NavigationEvent, NavigationOutcome, RouteOptimizer
from .exceptions import OptimizationError
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id
from .schema_validation import navigation_validator


class RouteOptimizationEngine(IRouteOptimizer):
    """Route optimization and learning implementation"""
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize optimization engine with storage and configuration"""
        self.logger = get_navigation_logger("route_optimizer")
        self.config = config or {}
        
        # Storage configuration
        self.storage_path = Path(storage_path or "data/navigation/optimization")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Learning data storage
        self._route_performance: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._timing_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._detection_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._success_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Optimization configuration
        self.learning_enabled = self.config.get("learning_enabled", True)
        self.performance_window_size = self.config.get("performance_window_size", 50)
        self.min_samples_for_optimization = self.config.get("min_samples_for_optimization", 5)
        self.optimization_threshold = self.config.get("optimization_threshold", 0.1)
        self.max_alternative_routes = self.config.get("max_alternative_routes", 3)
        
        # Learning state
        self._learning_active = False
        self._last_optimization = datetime.utcnow()
        self._optimization_interval_hours = self.config.get("optimization_interval_hours", 1)
        
        self.logger.info(
            "Route optimization engine initialized",
            storage_path=str(self.storage_path),
            learning_enabled=self.learning_enabled,
            performance_window_size=self.performance_window_size
        )
    
    async def analyze_route_performance(
        self,
        route_id: str,
        navigation_events: List[NavigationEvent]
    ) -> Dict[str, Any]:
        """Analyze performance of a specific route"""
        try:
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
            
            self.logger.info(
                "Analyzing route performance",
                route_id=route_id,
                events_count=len(navigation_events)
            )
            
            if not navigation_events:
                return {
                    "route_id": route_id,
                    "success_rate": 0.0,
                    "average_time": 0.0,
                    "total_events": 0,
                    "recommendations": []
                }
            
            # Calculate performance metrics
            successful_events = [e for e in navigation_events if e.is_successful()]
            failed_events = [e for e in navigation_events if not e.is_successful()]
            
            success_rate = len(successful_events) / len(navigation_events)
            
            # Calculate timing metrics
            successful_times = [
                e.performance_metrics.duration_seconds
                for e in successful_events
                if e.performance_metrics
            ]
            
            average_time = statistics.mean(successful_times) if successful_times else 0.0
            median_time = statistics.median(successful_times) if successful_times else 0.0
            
            # Calculate risk metrics
            detection_events = [e for e in navigation_events if e.outcome == NavigationOutcome.DETECTED]
            detection_rate = len(detection_events) / len(navigation_events)
            
            # Analyze failure patterns
            failure_patterns = self._analyze_failure_patterns(failed_events)
            
            # Generate recommendations
            recommendations = self._generate_performance_recommendations(
                route_id, success_rate, average_time, detection_rate, failure_patterns
            )
            
            performance_analysis = {
                "route_id": route_id,
                "total_events": len(navigation_events),
                "successful_events": len(successful_events),
                "failed_events": len(failed_events),
                "success_rate": success_rate,
                "average_time": average_time,
                "median_time": median_time,
                "detection_rate": detection_rate,
                "failure_patterns": failure_patterns,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            # Store performance data for learning
            if self.learning_enabled:
                await self._store_performance_data(route_id, performance_analysis)
            
            self.logger.info(
                "Route performance analysis completed",
                route_id=route_id,
                success_rate=success_rate,
                average_time=average_time
            )
            
            return performance_analysis
            
        except Exception as e:
            self.logger.error(
                f"Failed to analyze route performance: {str(e)}",
                route_id=route_id,
                events_count=len(navigation_events)
            )
            raise OptimizationError(
                f"Failed to analyze performance for route {route_id}: {str(e)}",
                "PERFORMANCE_ANALYSIS_FAILED",
                {
                    "route_id": route_id,
                    "events_count": len(navigation_events)
                }
            )
    
    async def optimize_route_timing(
        self,
        plan: PathPlan,
        historical_data: Optional[List[Dict[str, Any]]] = None
    ) -> PathPlan:
        """Optimize timing for route steps based on historical data"""
        try:
            set_correlation_id(plan.correlation_id)
            
            self.logger.info(
                "Optimizing route timing",
                plan_id=plan.plan_id,
                steps_count=len(plan.route_sequence)
            )
            
            if not historical_data:
                historical_data = await self._get_historical_timing_data(plan)
            
            optimized_steps = []
            
            for i, step in enumerate(plan.route_sequence):
                # Get historical timing data for this step type
                step_type = step.action_type
                target_url = step.target_url
                
                timing_data = [
                    data for data in historical_data
                    if data.get("step_type") == step_type and 
                       data.get("target_url", "").endswith(target_url.split('/')[-1])
                ]
                
                if timing_data and len(timing_data) >= self.min_samples_for_optimization:
                    # Calculate optimal timing
                    successful_times = [
                        data["duration"] for data in timing_data
                        if data.get("success", False)
                    ]
                    
                    if successful_times:
                        # Use median with safety margin for optimal timing
                        optimal_time = statistics.median(successful_times) * 1.1  # 10% safety margin
                        
                        # Add human-like variation
                        variation = optimal_time * 0.2  # 20% variation
                        optimized_time = optimal_time + (hash(target_url) % int(variation * 1000)) / 1000
                        
                        # Create optimized step
                        optimized_step = RouteStep(
                            step_number=step.step_number,
                            route_id=step.route_id,
                            action_type=step.action_type,
                            target_url=step.target_url,
                            expected_delay=optimized_time,
                            step_description=step.step_description,
                            metadata=step.metadata.copy() if step.metadata else {}
                        )
                        
                        optimized_step.metadata["timing_optimized"] = True
                        optimized_step.metadata["original_delay"] = step.expected_delay
                        optimized_step.metadata["optimization_timestamp"] = datetime.utcnow().isoformat()
                        
                        optimized_steps.append(optimized_step)
                        
                        self.logger.debug(
                            "Step timing optimized",
                            step_number=step.step_number,
                            original_time=step.expected_delay,
                            optimized_time=optimized_time
                        )
                    else:
                        optimized_steps.append(step)
                else:
                    optimized_steps.append(step)
            
            # Create optimized plan
            optimized_plan = PathPlan(
                plan_id=f"{plan.plan_id}_optimized",
                source_context=plan.source_context,
                target_destination=plan.target_destination,
                route_sequence=optimized_steps,
                total_risk_score=plan.total_risk_score,
                estimated_duration=sum(step.expected_delay for step in optimized_steps),
                correlation_id=plan.correlation_id
            )
            
            # Copy metadata
            if plan.plan_metadata:
                optimized_plan.plan_metadata = plan.plan_metadata.copy()
                optimized_plan.plan_metadata.timing_optimized = True
                optimized_plan.plan_metadata.optimization_timestamp = datetime.utcnow().isoformat()
            
            self.logger.info(
                "Route timing optimization completed",
                plan_id=plan.plan_id,
                optimized_plan_id=optimized_plan.plan_id,
                original_duration=plan.estimated_duration,
                optimized_duration=optimized_plan.estimated_duration
            )
            
            return optimized_plan
            
        except Exception as e:
            self.logger.error(
                f"Failed to optimize route timing: {str(e)}",
                plan_id=plan.plan_id
            )
            raise OptimizationError(
                f"Failed to optimize timing for plan {plan.plan_id}: {str(e)}",
                "TIMING_OPTIMIZATION_FAILED",
                {"plan_id": plan.plan_id}
            )
    
    async def learn_from_outcomes(
        self,
        navigation_events: List[NavigationEvent]
    ) -> Dict[str, Any]:
        """Learn from navigation outcomes to improve future routing"""
        try:
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
            
            self.logger.info(
                "Learning from navigation outcomes",
                events_count=len(navigation_events)
            )
            
            learning_results = {
                "patterns_identified": 0,
                "timing_adjustments": 0,
                "risk_assessments": 0,
                "recommendations_generated": 0,
                "learning_timestamp": datetime.utcnow().isoformat()
            }
            
            # Group events by route for pattern analysis
            route_events = defaultdict(list)
            for event in navigation_events:
                route_events[event.route_id].append(event)
            
            for route_id, events in route_events.items():
                # Learn timing patterns
                timing_adjustments = await self._learn_timing_patterns(route_id, events)
                learning_results["timing_adjustments"] += timing_adjustments
                
                # Learn success patterns
                success_patterns = await self._learn_success_patterns(route_id, events)
                learning_results["patterns_identified"] += len(success_patterns)
                
                # Learn risk patterns
                risk_assessments = await self._learn_risk_patterns(route_id, events)
                learning_results["risk_assessments"] += risk_assessments
                
                # Generate recommendations
                recommendations = await self._generate_learning_recommendations(route_id, events)
                learning_results["recommendations_generated"] += len(recommendations)
            
            # Update learning state
            if self.learning_enabled:
                await self._update_learning_state(learning_results)
            
            self.logger.info(
                "Learning from outcomes completed",
                learning_results=learning_results
            )
            
            return learning_results
            
        except Exception as e:
            self.logger.error(
                f"Failed to learn from outcomes: {str(e)}",
                events_count=len(navigation_events)
            )
            raise OptimizationError(
                f"Failed to learn from navigation outcomes: {str(e)}",
                "LEARNING_FAILED",
                {"events_count": len(navigation_events)}
            )
    
    async def get_optimization_recommendations(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on learned patterns"""
        try:
            self.logger.info(
                "Generating optimization recommendations",
                context_provided=context is not None
            )
            
            recommendations = []
            
            # Analyze route performance patterns
            for route_id, performance_data in self._route_performance.items():
                if len(performance_data) >= self.min_samples_for_optimization:
                    route_recommendations = self._analyze_route_recommendations(route_id, performance_data)
                    recommendations.extend(route_recommendations)
            
            # Analyze timing patterns
            timing_recommendations = self._analyze_timing_recommendations()
            recommendations.extend(timing_recommendations)
            
            # Analyze detection patterns
            detection_recommendations = self._analyze_detection_recommendations()
            recommendations.extend(detection_recommendations)
            
            # Sort recommendations by priority and impact
            recommendations.sort(key=lambda x: (x.get("priority", 0), x.get("impact", 0)), reverse=True)
            
            # Filter by context if provided
            if context:
                recommendations = self._filter_recommendations_by_context(recommendations, context)
            
            self.logger.info(
                "Optimization recommendations generated",
                recommendations_count=len(recommendations)
            )
            
            return recommendations[:50]  # Limit to top 50 recommendations
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate optimization recommendations: {str(e)}"
            )
            raise OptimizationError(
                f"Failed to generate recommendations: {str(e)}",
                "RECOMMENDATION_GENERATION_FAILED"
            )
    
    async def optimize_route_selection(
        self,
        candidate_routes: List[PathPlan],
        context: Optional[Dict[str, Any]] = None
    ) -> PathPlan:
        """Select and optimize the best route from candidates"""
        try:
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
            
            self.logger.info(
                "Optimizing route selection",
                candidates_count=len(candidate_routes)
            )
            
            if not candidate_routes:
                raise OptimizationError(
                    "No candidate routes provided",
                    "NO_CANDIDATE_ROUTES"
                )
            
            # Score each candidate route
            scored_routes = []
            for route in candidate_routes:
                score = await self._score_route(route, context)
                scored_routes.append((route, score))
            
            # Sort by score (highest first)
            scored_routes.sort(key=lambda x: x[1], reverse=True)
            
            # Select best route
            best_route, best_score = scored_routes[0]
            
            # Apply timing optimization to selected route
            optimized_route = await self.optimize_route_timing(best_route)
            
            # Add optimization metadata
            if not optimized_route.plan_metadata:
                optimized_route.plan_metadata = {}
            
            optimized_route.plan_metadata["selection_score"] = best_score
            optimized_route.plan_metadata["candidates_evaluated"] = len(candidate_routes)
            optimized_route.plan_metadata["selection_timestamp"] = datetime.utcnow().isoformat()
            
            self.logger.info(
                "Route selection optimized",
                selected_route_id=optimized_route.plan_id,
                selection_score=best_score,
                candidates_evaluated=len(candidate_routes)
            )
            
            return optimized_route
            
        except Exception as e:
            self.logger.error(
                f"Failed to optimize route selection: {str(e)}",
                candidates_count=len(candidate_routes)
            )
            raise OptimizationError(
                f"Failed to optimize route selection: {str(e)}",
                "ROUTE_SELECTION_FAILED",
                {"candidates_count": len(candidate_routes)}
            )
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning and optimization statistics"""
        try:
            total_routes = len(self._route_performance)
            total_timing_patterns = sum(len(patterns) for patterns in self._timing_patterns.values())
            total_detection_patterns = len(self._detection_patterns)
            total_success_patterns = len(self._success_patterns)
            
            # Calculate learning effectiveness
            learning_effectiveness = 0.0
            if total_routes > 0:
                routes_with_sufficient_data = sum(
                    1 for data in self._route_performance.values()
                    if len(data) >= self.min_samples_for_optimization
                )
                learning_effectiveness = routes_with_sufficient_data / total_routes
            
            return {
                "learning_enabled": self.learning_enabled,
                "learning_active": self._learning_active,
                "total_routes_analyzed": total_routes,
                "total_timing_patterns": total_timing_patterns,
                "total_detection_patterns": total_detection_patterns,
                "total_success_patterns": total_success_patterns,
                "learning_effectiveness": learning_effectiveness,
                "last_optimization": self._last_optimization.isoformat(),
                "optimization_interval_hours": self._optimization_interval_hours,
                "min_samples_for_optimization": self.min_samples_for_optimization
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to get learning statistics: {str(e)}"
            )
            return {}
    
    # Private helper methods
    
    def _analyze_failure_patterns(self, failed_events: List[NavigationEvent]) -> List[Dict[str, Any]]:
        """Analyze patterns in failed navigation events"""
        patterns = []
        
        # Group by error type
        error_groups = defaultdict(list)
        for event in failed_events:
            error_key = event.error_code or "unknown_error"
            error_groups[error_key].append(event)
        
        for error_type, events in error_groups.items():
            if len(events) >= 3:  # Pattern threshold
                pattern = {
                    "error_type": error_type,
                    "frequency": len(events),
                    "recent_occurrences": len([e for e in events if self._is_recent_event(e)]),
                    "common_contexts": self._find_common_contexts(events)
                }
                patterns.append(pattern)
        
        return patterns
    
    def _generate_performance_recommendations(
        self,
        route_id: str,
        success_rate: float,
        average_time: float,
        detection_rate: float,
        failure_patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Success rate recommendations
        if success_rate < 0.7:
            recommendations.append(f"Low success rate ({success_rate:.2f}) - consider alternative routes")
        elif success_rate < 0.9:
            recommendations.append(f"Moderate success rate ({success_rate:.2f}) - optimize timing and stealth")
        
        # Timing recommendations
        if average_time > 5.0:
            recommendations.append(f"High average time ({average_time:.2f}s) - optimize step delays")
        
        # Detection recommendations
        if detection_rate > 0.1:
            recommendations.append(f"High detection rate ({detection_rate:.2f}) - enhance stealth measures")
        
        # Failure pattern recommendations
        for pattern in failure_patterns:
            if pattern["frequency"] >= 5:
                recommendations.append(f"Frequent {pattern['error_type']} errors - investigate root cause")
        
        return recommendations
    
    async def _store_performance_data(self, route_id: str, performance_data: Dict[str, Any]) -> None:
        """Store performance data for learning"""
        try:
            self._route_performance[route_id].append(performance_data)
            
            # Limit data size
            if len(self._route_performance[route_id]) > self.performance_window_size:
                self._route_performance[route_id] = self._route_performance[route_id][-self.performance_window_size:]
            
            # Save to storage
            await self._save_performance_data_to_storage(route_id, performance_data)
            
        except Exception as e:
            self.logger.warning(
                f"Failed to store performance data: {str(e)}",
                route_id=route_id
            )
    
    async def _get_historical_timing_data(self, plan: PathPlan) -> List[Dict[str, Any]]:
        """Get historical timing data for plan optimization"""
        timing_data = []
        
        for step in plan.route_sequence:
            step_key = f"{step.action_type}_{step.target_url}"
            
            if step_key in self._timing_patterns:
                for timing_record in self._timing_patterns[step_key]:
                    timing_data.append({
                        "step_type": step.action_type,
                        "target_url": step.target_url,
                        "duration": timing_record["duration"],
                        "success": timing_record["success"],
                        "timestamp": timing_record["timestamp"]
                    })
        
        return timing_data
    
    async def _learn_timing_patterns(self, route_id: str, events: List[NavigationEvent]) -> int:
        """Learn timing patterns from navigation events"""
        adjustments = 0
        
        for event in events:
            if event.performance_metrics:
                step_key = f"{event.route_id}_{event.context_after}"
                
                timing_record = {
                    "duration": event.performance_metrics.duration_seconds,
                    "success": event.is_successful(),
                    "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.utcnow().isoformat()
                }
                
                self._timing_patterns[step_key].append(timing_record)
                adjustments += 1
        
        return adjustments
    
    async def _learn_success_patterns(self, route_id: str, events: List[NavigationEvent]) -> List[Dict[str, Any]]:
        """Learn success patterns from navigation events"""
        patterns = []
        
        successful_events = [e for e in events if e.is_successful()]
        
        if len(successful_events) >= self.min_samples_for_optimization:
            # Analyze common factors in successful events
            common_factors = self._analyze_success_factors(successful_events)
            
            pattern = {
                "route_id": route_id,
                "success_count": len(successful_events),
                "common_factors": common_factors,
                "learned_at": datetime.utcnow().isoformat()
            }
            
            self._success_patterns[route_id].append(pattern)
            patterns.append(pattern)
        
        return patterns
    
    async def _learn_risk_patterns(self, route_id: str, events: List[NavigationEvent]) -> int:
        """Learn risk patterns from navigation events"""
        risk_assessments = 0
        
        for event in events:
            if event.stealth_score_after is not None:
                risk_record = {
                    "route_id": route_id,
                    "stealth_score": event.stealth_score_after,
                    "success": event.is_successful(),
                    "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.utcnow().isoformat()
                }
                
                self._detection_patterns[route_id].append(risk_record)
                risk_assessments += 1
        
        return risk_assessments
    
    async def _generate_learning_recommendations(self, route_id: str, events: List[NavigationEvent]) -> List[str]:
        """Generate learning-based recommendations"""
        recommendations = []
        
        # Analyze event patterns
        if events:
            success_rate = sum(1 for e in events if e.is_successful()) / len(events)
            
            if success_rate < 0.5:
                recommendations.append(f"Route {route_id} has low success rate - consider replacement")
            elif success_rate < 0.8:
                recommendations.append(f"Route {route_id} needs optimization - review timing and stealth")
        
        return recommendations
    
    def _is_recent_event(self, event: NavigationEvent, hours: int = 24) -> bool:
        """Check if event is recent"""
        if not event.timestamp:
            return False
        
        return datetime.utcnow() - event.timestamp < timedelta(hours=hours)
    
    def _find_common_contexts(self, events: List[NavigationEvent]) -> List[str]:
        """Find common contexts in events"""
        contexts = [e.context_before for e in events if e.context_before]
        context_counts = defaultdict(int)
        
        for context in contexts:
            context_counts[context] += 1
        
        # Return contexts that appear in at least 50% of events
        threshold = len(events) * 0.5
        return [context for context, count in context_counts.items() if count >= threshold]
    
    async def _score_route(self, route: PathPlan, context: Optional[Dict[str, Any]]) -> float:
        """Score a route for selection"""
        score = 0.0
        
        # Base score from risk assessment (lower risk = higher score)
        risk_score = 1.0 - route.total_risk_score
        score += risk_score * 0.4
        
        # Duration score (shorter = higher score)
        duration_score = 1.0 / (1.0 + route.estimated_duration / 10.0)
        score += duration_score * 0.3
        
        # Historical performance score
        performance_score = await self._get_route_performance_score(route)
        score += performance_score * 0.3
        
        return min(score, 1.0)
    
    async def _get_route_performance_score(self, route: PathPlan) -> float:
        """Get historical performance score for route"""
        # Check if we have performance data for similar routes
        similar_routes = [
            route_id for route_id in self._route_performance.keys()
            if any(step.route_id in route_id for step in route.route_sequence)
        ]
        
        if not similar_routes:
            return 0.5  # Neutral score for unknown routes
        
        # Calculate average success rate for similar routes
        success_rates = []
        for route_id in similar_routes:
            performance_data = self._route_performance[route_id]
            if performance_data:
                latest_performance = performance_data[-1]
                success_rates.append(latest_performance.get("success_rate", 0.5))
        
        return statistics.mean(success_rates) if success_rates else 0.5
    
    async def _save_performance_data_to_storage(self, route_id: str, data: Dict[str, Any]) -> None:
        """Save performance data to storage"""
        try:
            performance_file = self.storage_path / "performance" / f"{route_id}.json"
            performance_file.parent.mkdir(exist_ok=True)
            
            # Load existing data
            existing_data = []
            if performance_file.exists():
                with open(performance_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # Add new data
            existing_data.append(data)
            
            # Limit data size
            if len(existing_data) > self.performance_window_size:
                existing_data = existing_data[-self.performance_window_size:]
            
            # Save to file
            with open(performance_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.warning(
                f"Failed to save performance data to storage: {str(e)}",
                route_id=route_id
            )
    
    async def _update_learning_state(self, learning_results: Dict[str, Any]) -> None:
        """Update learning state"""
        self._last_optimization = datetime.utcnow()
        self._learning_active = True
        
        # Save learning state to storage
        try:
            state_file = self.storage_path / "learning_state.json"
            state_data = {
                "last_optimization": self._last_optimization.isoformat(),
                "learning_active": self._learning_active,
                "latest_results": learning_results
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.warning(
                f"Failed to save learning state: {str(e)}"
            )
    
    def _analyze_route_recommendations(self, route_id: str, performance_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze recommendations for specific route"""
        recommendations = []
        
        if len(performance_data) >= self.min_samples_for_optimization:
            latest_data = performance_data[-1]
            
            # Success rate recommendations
            if latest_data["success_rate"] < 0.7:
                recommendations.append({
                    "type": "success_rate",
                    "priority": 1,
                    "impact": 0.8,
                    "route_id": route_id,
                    "message": f"Low success rate ({latest_data['success_rate']:.2f}) - consider route replacement",
                    "suggested_action": "replace_route"
                })
            
            # Timing recommendations
            if latest_data["average_time"] > 5.0:
                recommendations.append({
                    "type": "timing",
                    "priority": 2,
                    "impact": 0.6,
                    "route_id": route_id,
                    "message": f"High average time ({latest_data['average_time']:.2f}s) - optimize delays",
                    "suggested_action": "optimize_timing"
                })
        
        return recommendations
    
    def _analyze_timing_recommendations(self) -> List[Dict[str, Any]]:
        """Analyze timing optimization recommendations"""
        recommendations = []
        
        for step_key, timing_patterns in self._timing_patterns.items():
            if len(timing_patterns) >= self.min_samples_for_optimization:
                successful_times = [
                    pattern["duration"] for pattern in timing_patterns
                    if pattern["success"]
                ]
                
                if successful_times:
                    avg_time = statistics.mean(successful_times)
                    
                    if avg_time > 3.0:
                        recommendations.append({
                            "type": "timing_optimization",
                            "priority": 2,
                            "impact": 0.5,
                            "step_key": step_key,
                            "message": f"High average time ({avg_time:.2f}s) for {step_key}",
                            "suggested_action": "adjust_delays"
                        })
        
        return recommendations
    
    def _analyze_detection_recommendations(self) -> List[Dict[str, Any]]:
        """Analyze detection avoidance recommendations"""
        recommendations = []
        
        for route_id, detection_patterns in self._detection_patterns.items():
            if len(detection_patterns) >= self.min_samples_for_optimization:
                avg_stealth_score = statistics.mean([
                    pattern["stealth_score"] for pattern in detection_patterns
                ])
                
                if avg_stealth_score < 0.5:
                    recommendations.append({
                        "type": "stealth_enhancement",
                        "priority": 1,
                        "impact": 0.9,
                        "route_id": route_id,
                        "message": f"Low stealth score ({avg_stealth_score:.2f}) for {route_id}",
                        "suggested_action": "enhance_stealth"
                    })
        
        return recommendations
    
    def _filter_recommendations_by_context(
        self,
        recommendations: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter recommendations by context"""
        filtered = []
        
        for rec in recommendations:
            # Filter by priority if specified
            if "min_priority" in context:
                if rec.get("priority", 0) < context["min_priority"]:
                    continue
            
            # Filter by type if specified
            if "types" in context:
                if rec.get("type") not in context["types"]:
                    continue
            
            filtered.append(rec)
        
        return filtered
    
    def _analyze_success_factors(self, successful_events: List[NavigationEvent]) -> Dict[str, Any]:
        """Analyze common factors in successful events"""
        factors = {
            "common_time_ranges": [],
            "common_delays": [],
            "common_stealth_scores": []
        }
        
        # Analyze timing patterns
        if successful_events:
            times = [
                e.performance_metrics.duration_seconds
                for e in successful_events
                if e.performance_metrics
            ]
            
            if times:
                factors["common_time_ranges"] = [
                    statistics.mean(times),
                    statistics.median(times)
                ]
        
        return factors
