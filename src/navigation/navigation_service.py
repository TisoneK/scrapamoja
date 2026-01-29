"""
Navigation service integration

Main service coordinating all navigation components including route discovery, 
path planning, route adaptation, context management, and optimization.
Conforms to Constitution Principle III - Deep Modularity.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .interfaces import INavigationService
from .models import (
    NavigationContext, PathPlan, NavigationEvent, NavigationOutcome,
    NavigationRoute, RouteGraph, NavigationContext as ContextModel
)
from .exceptions import NavigationServiceError
from .logging_config import get_navigation_logger, set_correlation_id, generate_correlation_id
from .schema_validation import navigation_validator

# Import all navigation components
from .route_discovery import RouteDiscovery
from .path_planning import PathPlanning
from .route_adaptation import RouteAdaptation
from .context_manager import ContextManager
from .route_optimizer import RouteOptimizationEngine


class NavigationService(INavigationService):
    """Main navigation service coordinating all components"""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        storage_path: Optional[str] = None
    ):
        """Initialize navigation service with all components"""
        self.logger = get_navigation_logger("navigation_service")
        self.config = config or {}
        self.storage_path = Path(storage_path or "data/navigation")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize all components
        self._route_discovery = None
        self._path_planning = None
        self._route_adaptation = None
        self._context_manager = None
        self._route_optimizer = None
        
        # Service state
        self._initialized = False
        self._active_sessions: Dict[str, str] = {}  # session_id -> context_id mapping
        self._service_stats = {
            "total_navigations": 0,
            "successful_navigations": 0,
            "failed_navigations": 0,
            "adaptations_performed": 0,
            "optimizations_applied": 0
        }
        
        self.logger.info(
            "Navigation service initialized",
            storage_path=str(self.storage_path)
        )
    
    async def initialize(self) -> None:
        """Initialize all navigation components"""
        try:
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
            
            self.logger.info("Initializing navigation service components")
            
            # Initialize route discovery
            self._route_discovery = RouteDiscovery(
                config=self.config.get("route_discovery", {}),
                storage_path=str(self.storage_path / "discovery")
            )
            await self._route_discovery.initialize()
            
            # Initialize path planning
            self._path_planning = PathPlanning(
                config=self.config.get("path_planning", {}),
                storage_path=str(self.storage_path / "planning")
            )
            await self._path_planning.initialize()
            
            # Initialize route adaptation
            self._route_adaptation = RouteAdaptation(
                config=self.config.get("route_adaptation", {}),
                storage_path=str(self.storage_path / "adaptation")
            )
            await self._route_adaptation.initialize()
            
            # Initialize context manager
            self._context_manager = ContextManager(
                config=self.config.get("context_manager", {}),
                storage_path=str(self.storage_path / "contexts")
            )
            
            # Initialize route optimizer
            self._route_optimizer = RouteOptimizationEngine(
                config=self.config.get("route_optimizer", {}),
                storage_path=str(self.storage_path / "optimization")
            )
            
            self._initialized = True
            
            self.logger.info(
                "Navigation service initialization completed",
                components_initialized=5
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to initialize navigation service: {str(e)}"
            )
            raise NavigationServiceError(
                f"Navigation service initialization failed: {str(e)}",
                "SERVICE_INITIALIZATION_FAILED"
            )
    
    async def navigate(
        self,
        session_id: str,
        source_context: str,
        target_destination: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute complete navigation from source to destination"""
        try:
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
            
            self.logger.info(
                "Starting navigation",
                session_id=session_id,
                source_context=source_context,
                target_destination=target_destination
            )
            
            if not self._initialized:
                await self.initialize()
            
            options = options or {}
            
            # Get or create navigation context
            context = await self._get_or_create_context(session_id, source_context)
            
            # Discover available routes
            routes = await self._route_discovery.discover_routes(
                context.current_page.url,
                target_destination,
                context
            )
            
            if not routes:
                raise NavigationServiceError(
                    f"No routes found from {source_context} to {target_destination}",
                    "NO_ROUTES_FOUND"
                )
            
            # Plan optimal path
            plan = await self._path_planning.plan_path(
                routes,
                context,
                options
            )
            
            # Optimize plan if enabled
            if options.get("enable_optimization", True):
                plan = await self._route_optimizer.optimize_route_timing(plan)
            
            # Execute navigation with adaptation
            navigation_result = await self._execute_navigation_plan(
                context,
                plan,
                options
            )
            
            # Update context
            await self._context_manager.update_context(
                context.context_id,
                navigation_result["final_event"]
            )
            
            # Learn from outcomes
            if options.get("enable_learning", True):
                await self._route_optimizer.learn_from_outcomes(
                    navigation_result["events"]
                )
            
            # Update statistics
            self._update_service_statistics(navigation_result)
            
            self.logger.info(
                "Navigation completed successfully",
                session_id=session_id,
                plan_id=plan.plan_id,
                success=navigation_result["success"]
            )
            
            return navigation_result
            
        except Exception as e:
            self.logger.error(
                f"Navigation failed: {str(e)}",
                session_id=session_id,
                source_context=source_context,
                target_destination=target_destination
            )
            
            self._service_stats["failed_navigations"] += 1
            
            raise NavigationServiceError(
                f"Navigation failed: {str(e)}",
                "NAVIGATION_FAILED",
                {
                    "session_id": session_id,
                    "source_context": source_context,
                    "target_destination": target_destination
                }
            )
    
    async def get_navigation_context(
        self,
        session_id: str
    ) -> Optional[NavigationContext]:
        """Get navigation context for session"""
        try:
            if not self._initialized:
                await self.initialize()
            
            return await self._context_manager.get_context_by_session(session_id)
            
        except Exception as e:
            self.logger.error(
                f"Failed to get navigation context: {str(e)}",
                session_id=session_id
            )
            return None
    
    async def update_navigation_context(
        self,
        session_id: str,
        context_updates: Dict[str, Any]
    ) -> NavigationContext:
        """Update navigation context"""
        try:
            if not self._initialized:
                await self.initialize()
            
            context = await self._context_manager.get_context_by_session(session_id)
            if not context:
                raise NavigationServiceError(
                    f"No context found for session {session_id}",
                    "CONTEXT_NOT_FOUND"
                )
            
            # Apply context updates
            for key, value in context_updates.items():
                if key == "session_data":
                    context.session_data.update(value)
                elif key == "authentication_state":
                    context.update_authentication(value)
            
            return context
            
        except Exception as e:
            self.logger.error(
                f"Failed to update navigation context: {str(e)}",
                session_id=session_id
            )
            raise NavigationServiceError(
                f"Context update failed: {str(e)}",
                "CONTEXT_UPDATE_FAILED"
            )
    
    async def get_navigation_history(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[NavigationEvent]:
        """Get navigation history for session"""
        try:
            if not self._initialized:
                await self.initialize()
            
            context = await self._context_manager.get_context_by_session(session_id)
            if not context:
                return []
            
            return await self._context_manager.get_context_history(
                context.context_id,
                limit
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to get navigation history: {str(e)}",
                session_id=session_id
            )
            return []
    
    async def cleanup_session(
        self,
        session_id: str
    ) -> bool:
        """Clean up navigation session"""
        try:
            if not self._initialized:
                return True
            
            self.logger.info(
                "Cleaning up navigation session",
                session_id=session_id
            )
            
            # Clean up context
            context = await self._context_manager.get_context_by_session(session_id)
            if context:
                await self._context_manager.cleanup_context(context.context_id)
            
            # Remove from active sessions
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
            
            self.logger.info(
                "Navigation session cleaned up successfully",
                session_id=session_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup session: {str(e)}",
                session_id=session_id
            )
            return False
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        try:
            if not self._initialized:
                return {"initialized": False}
            
            # Get component statistics
            discovery_stats = await self._route_discovery.get_discovery_statistics()
            planning_stats = self._path_planning.get_planning_statistics()
            adaptation_stats = self._route_adaptation.get_adaptation_statistics()
            context_stats = await self._context_manager.get_context_statistics()
            optimization_stats = await self._route_optimizer.get_learning_statistics()
            
            # Calculate overall statistics
            total_success_rate = (
                self._service_stats["successful_navigations"] / 
                max(self._service_stats["total_navigations"], 1)
            )
            
            return {
                "initialized": True,
                "active_sessions": len(self._active_sessions),
                "service_statistics": self._service_stats,
                "success_rate": total_success_rate,
                "component_statistics": {
                    "route_discovery": discovery_stats,
                    "path_planning": planning_stats,
                    "route_adaptation": adaptation_stats,
                    "context_management": context_stats,
                    "route_optimization": optimization_stats
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to get service statistics: {str(e)}"
            )
            return {"initialized": False, "error": str(e)}
    
    async def shutdown(self) -> None:
        """Shutdown navigation service and all components"""
        try:
            self.logger.info("Shutting down navigation service")
            
            # Shutdown all components
            if self._route_discovery:
                await self._route_discovery.shutdown()
            
            if self._path_planning:
                self._path_planning.shutdown()
            
            if self._route_adaptation:
                await self._route_adaptation.shutdown()
            
            if self._route_optimizer:
                # Route optimizer doesn't have explicit shutdown
                pass
            
            # Clean up all active sessions
            for session_id in list(self._active_sessions.keys()):
                await self.cleanup_session(session_id)
            
            self._initialized = False
            
            self.logger.info("Navigation service shutdown completed")
            
        except Exception as e:
            self.logger.error(
                f"Error during service shutdown: {str(e)}"
            )
    
    # Private helper methods
    
    async def _get_or_create_context(
        self,
        session_id: str,
        source_context: str
    ) -> NavigationContext:
        """Get existing context or create new one"""
        context = await self._context_manager.get_context_by_session(session_id)
        
        if not context:
            # Create new context
            context = await self._context_manager.create_context(
                session_id,
                source_context
            )
            self._active_sessions[session_id] = context.context_id
        
        return context
    
    async def _execute_navigation_plan(
        self,
        context: NavigationContext,
        plan: PathPlan,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute navigation plan with adaptation"""
        events = []
        current_step = 0
        
        try:
            for step in plan.route_sequence:
                current_step += 1
                
                # Execute step
                event = await self._execute_navigation_step(
                    context,
                    step,
                    current_step,
                    options
                )
                
                events.append(event)
                
                # Check if navigation failed
                if not event.is_successful():
                    # Attempt adaptation
                    if options.get("enable_adaptation", True):
                        adaptation_result = await self._route_adaptation.adapt_to_obstacle(
                            plan,
                            event,
                            context
                        )
                        
                        if adaptation_result["adapted"]:
                            # Use adapted plan
                            plan = adaptation_result["adapted_plan"]
                            events.extend(adaptation_result["adaptation_events"])
                            continue
                    else:
                        # No adaptation, break
                        break
            
            # Determine final success
            final_event = events[-1] if events else None
            success = final_event.is_successful() if final_event else False
            
            return {
                "success": success,
                "plan_id": plan.plan_id,
                "events": events,
                "final_event": final_event,
                "steps_completed": len(events),
                "total_steps": len(plan.route_sequence)
            }
            
        except Exception as e:
            self.logger.error(
                f"Error executing navigation plan: {str(e)}",
                plan_id=plan.plan_id,
                current_step=current_step
            )
            
            # Create failure event
            failure_event = NavigationEvent(
                event_id=f"nav_error_{plan.plan_id}_{current_step}",
                route_id=plan.route_sequence[current_step - 1].route_id if current_step > 0 else "unknown",
                context_before=context.current_page.url,
                context_after=context.current_page.url,
                outcome=NavigationOutcome.FAILURE,
                error_details=str(e),
                error_code="EXECUTION_ERROR"
            )
            
            return {
                "success": False,
                "plan_id": plan.plan_id,
                "events": events + [failure_event],
                "final_event": failure_event,
                "steps_completed": len(events),
                "total_steps": len(plan.route_sequence)
            }
    
    async def _execute_navigation_step(
        self,
        context: NavigationContext,
        step: RouteStep,
        step_number: int,
        options: Dict[str, Any]
    ) -> NavigationEvent:
        """Execute individual navigation step"""
        try:
            # Simulate navigation step execution
            # In real implementation, this would use browser automation
            
            await asyncio.sleep(step.expected_delay)
            
            # Create success event
            event = NavigationEvent(
                event_id=f"nav_step_{step.route_id}_{step_number}",
                route_id=step.route_id,
                context_before=context.current_page.url,
                context_after=step.target_url,
                outcome=NavigationOutcome.SUCCESS,
                page_url_after=step.target_url,
                performance_metrics={
                    "duration_seconds": step.expected_delay,
                    "cpu_usage_percent": 10.0,
                    "memory_usage_mb": 50.0,
                    "dom_changes_count": 5
                },
                stealth_score_before=0.7,
                stealth_score_after=0.8
            )
            
            return event
            
        except Exception as e:
            # Create failure event
            event = NavigationEvent(
                event_id=f"nav_step_{step.route_id}_{step_number}",
                route_id=step.route_id,
                context_before=context.current_page.url,
                context_after=context.current_page.url,
                outcome=NavigationOutcome.FAILURE,
                error_details=str(e),
                error_code="STEP_EXECUTION_ERROR",
                performance_metrics={
                    "duration_seconds": 0.1,
                    "cpu_usage_percent": 5.0,
                    "memory_usage_mb": 45.0
                }
            )
            
            return event
    
    def _update_service_statistics(self, navigation_result: Dict[str, Any]) -> None:
        """Update service statistics"""
        self._service_stats["total_navigations"] += 1
        
        if navigation_result["success"]:
            self._service_stats["successful_navigations"] += 1
        else:
            self._service_stats["failed_navigations"] += 1
        
        # Count adaptations and optimizations
        for event in navigation_result["events"]:
            if event.metadata and event.metadata.get("adaptation_applied"):
                self._service_stats["adaptations_performed"] += 1
            
            if event.metadata and event.metadata.get("optimization_applied"):
                self._service_stats["optimizations_applied"] += 1
