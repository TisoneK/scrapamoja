"""
Main selector engine implementation for Selector Engine.

Implements the core ISelectorEngine interface with multi-strategy resolution, confidence scoring,
context-aware scoping, and integration with all strategy patterns as specified in the API contracts.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.models.selector_models import (
    SemanticSelector, SelectorResult, StrategyPattern, ValidationRule,
    ConfidenceMetrics, SnapshotType, DOMSnapshot
)
from src.selectors.context import DOMContext
from src.selectors.strategies.base import StrategyFactory
from src.selectors.confidence.thresholds import get_threshold_manager
from src.selectors.validation import get_validation_engine
from src.selectors.quality.control import get_quality_control_manager
from src.selectors.interfaces import ISelectorEngine
from src.observability.logger import get_logger, CorrelationContext
from src.observability.events import publish_selector_resolved, publish_selector_failed
from src.observability.metrics import get_performance_monitor
from src.storage.adapter import get_storage_adapter
from src.utils.exceptions import (
    SelectorNotFoundError, ResolutionTimeoutError, ConfidenceThresholdError,
    StrategyExecutionError, ValidationError, ConfigurationError
)
from src.config.settings import get_config


@dataclass
class ResolutionAttempt:
    """Information about a single resolution attempt."""
    strategy_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[SelectorResult] = None
    error: Optional[Exception] = None


class SelectorEngine(ISelectorEngine):
    """Main selector engine implementing multi-strategy resolution."""
    
    def __init__(self):
        self._logger = get_logger("selector_engine")
        self._threshold_manager = get_threshold_manager()
        self._validation_engine = get_validation_engine()
        self._quality_control_manager = get_quality_control_manager()
        self._performance_monitor = get_performance_monitor()
        self._storage_adapter = get_storage_adapter()
        self._strategy_factory = StrategyFactory()
        
        # Strategy registry
        self._strategies: Dict[str, IStrategyPattern] = {}
        self._selector_registry: Dict[str, SemanticSelector] = {}
        
        # Performance tracking
        self._resolution_attempts: List[ResolutionAttempt] = []
        self._current_resolution_id: Optional[str] = None
        
        # Configuration
        self._config = get_config()
        
        # Initialize common strategies
        self._initialize_common_strategies()
        
        self._logger.info("SelectorEngine initialized")
    
    async def resolve(self, selector_name: str, context: DOMContext) -> StrategyResult:
        """
        Resolve a semantic selector to DOM element.
        
        Args:
            selector_name: Name of the semantic selector
            context: DOM context for resolution
            
        Returns:
            SelectorResult with resolution outcome
        """
        # Set correlation context
        CorrelationContext.set_selector_name(selector_name)
        correlation_id = CorrelationContext.get_correlation_id()
        if not correlation_id:
            CorrelationContext.set_correlation_id(f"resolve_{selector_name}_{datetime.utcnow().timestamp()}")
        
        try:
            # Get selector definition
            selector = self.get_selector(selector_name)
            if not selector:
                raise SelectorNotFoundError(selector_name)
            
            try:
                # Validate selector
                issues = await self.validate_selector(selector)
                if issues:
                    raise ValidationError(f"Selector validation failed: {issues}")
            except Exception as e:
                # Handle validation errors
                raise ValidationError(f"Selector validation failed: {e}")
            
            # Create resolution attempt
            attempt = ResolutionAttempt(
                strategy_id="unknown",
                start_time=datetime.utcnow(),
                end_time=None,
                result=None,
                error=None
            )
            
            self._current_resolution_id = f"{selector_name}_{attempt.start_time.timestamp()}"
            self._resolution_attempts.append(attempt)
            
            # Attempt resolution with strategies
            result = await self._resolve_with_strategies(selector, context, attempt)
            
            # Complete attempt
            attempt.end_time = datetime.utcnow()
            attempt.result = result
            self._current_resolution_id = None
            
            # Update metrics
            await self._performance_monitor.record_resolution(result)
            
            # Quality control evaluation
            if result.success:
                try:
                    # Determine quality gate based on environment
                    gate_name = self._determine_quality_gate(context)
                    
                    # Create a mock selector for quality evaluation
                    quality_selector = SemanticSelector(
                        name=selector_name,
                        description=f"Quality evaluation for {selector_name}",
                        context="quality_check",
                        strategies=selector.strategies,
                        validation_rules=selector.validation_rules,
                        confidence_threshold=selector.confidence_threshold
                    )
                    
                    # Evaluate quality
                    quality_result = await self._quality_control_manager.evaluate_quality(
                        quality_selector, context, gate_name
                    )
                    
                    # Log quality result
                    self._logger.info(
                        "quality_evaluation_completed",
                        selector_name=selector_name,
                        gate_name=gate_name,
                        quality_passed=quality_result.passed,
                        confidence_score=quality_result.confidence_score,
                        violations=len(quality_result.violations)
                    )
                    
                    # Add quality metadata to result
                    if hasattr(result, 'metadata'):
                        result.metadata['quality_passed'] = quality_result.passed
                        result.metadata['quality_confidence'] = quality_result.confidence_score
                        result.metadata['quality_violations'] = len(quality_result.violations)
                        result.metadata['quality_gate'] = gate_name
                    
                except Exception as e:
                    # Log quality evaluation error but don't fail the resolution
                    self._logger.warning(
                        "quality_evaluation_failed",
                        selector_name=selector_name,
                        error=str(e)
                    )
            
            # Publish events
            if result.success:
                await publish_selector_resolved(
                    selector_name=selector_name,
                    strategy=result.strategy_used,
                    confidence=result.confidence_score,
                    resolution_time=result.resolution_time,
                    correlation_id=correlation_id
                )
            else:
                await publish_selector_failed(
                    selector_name=selector_name,
                    strategy=result.strategy_used,
                    failure_reason=result.failure_reason,
                    resolution_time=result.resolution_time,
                    correlation_id=correlation_id
                )
            
            # Log completion
            self._log_resolution_completion(selector_name, result)
            
            return result
            
        except Exception as e:
            # Handle known exceptions appropriately
            if isinstance(e, (SelectorNotFoundError, ResolutionTimeoutError, 
                              ConfidenceThresholdError)):
                # Re-raise known exceptions
                raise
            else:
                # Wrap unknown exceptions
                raise StrategyExecutionError(
                    "unknown", selector_name, f"Resolution failed: {e}"
                )
    
    async def resolve_batch(self, selector_names: List[str], context: DOMContext) -> List[SelectorResult]:
        """
        Resolve multiple selectors in parallel.
        
        Args:
            selector_names: List of selector names
            context: DOM context for resolution
            
        Returns:
            List of selector results
        """
        # Set correlation context
        correlation_id = CorrelationContext.get_correlation_id()
        if not correlation_id:
            CorrelationContext.set_correlation_id(f"batch_{datetime.utcnow().timestamp()}")
        
        try:
            # Validate all selectors first
            for selector_name in selector_names:
                selector = self.get_selector(selector_name)
                if not selector:
                    raise SelectorNotFoundError(selector_name)
                
                validation_issues = await self.validate_selector(selector)
                if validation_issues:
                    raise ValidationError(f"Selector '{selector_name}' validation failed: {validation_issues}")
            
            # Resolve selectors in parallel
            tasks = []
            for selector_name in selector_names:
                task = asyncio.create_task(
                    self.resolve(selector_name, context)
                )
                tasks.append(task)
            
            # Wait for all resolutions to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            final_results = []
            for i, result in results:
                if isinstance(result, Exception):
                    # Create failure result for exceptions
                    selector_name = selector_names[i]
                    error = result
                    failure_result = SelectorResult(
                        selector_name=selector_name,
                        strategy_used="none",
                        element_info=None,
                        confidence_score=0.0,
                        resolution_time=0.0,
                        validation_results=[],
                        success=False,
                        timestamp=datetime.utcnow(),
                        failure_reason=str(error)
                    )
                    final_results.append(failure_result)
                else:
                    final_results.append(result)
            
            # Update batch metrics
            await self._performance_monitor.record_batch_performance(
                len(selector_names), 
                sum(r.resolution_time for r in final_results),
                sum(1 for r in final_results if r.success) / len(final_results)
            )
            
            return final_results
            
        except Exception as e:
            self._logger.error(
                "batch_resolution_failed",
                selector_names=selector_names,
                error=str(e)
            )
            # Create failure results for all selectors
            return [
                SelectorResult(
                    selector_name=name,
                    strategy_used="none",
                    element_info=None,
                    confidence_score=0.0,
                    resolution_time=0.0,
                    validation_results=[],
                    success=False,
                    timestamp=datetime.utcnow(),
                    failure_reason=f"Batch resolution failed: {e}"
                )
                for name in selector_names
            ]
    
    def get_selector(self, name: str) -> Optional[SemanticSelector]:
        """Get selector definition by name."""
        return self._selector_registry.get(name)
    
    def list_selectors(self, context: Optional[str] = None) -> List[str]:
        """List available selectors, optionally filtered by context."""
        if context:
            return [
                name for name, selector in self._selector_registry.items()
                if selector.context == context
            ]
        else:
            return list(self._selector_registry.keys())
    
    async def validate_selector(self, selector: SemanticSelector) -> List[str]:
        """Validate selector definition, return list of issues."""
        issues = []
        
        # Basic validation
        if not selector.name.strip():
            issues.append("Selector name cannot be empty")
        
        # Validate strategies
        if len(selector.strategies) < 3:
            issues.append("Selector must have at least 3 strategies")
        
        # Validate strategy priorities
        priorities = [s.priority for s in selector.strategies]
        if len(priorities) != len(set(priorities)):
            issues.append("Strategy priorities must be unique")
        
        # Validate confidence threshold
        if not (0.0 <= selector.confidence_threshold <= 1.0):
            issues.append("Confidence threshold must be between 0.0 and 1.0")
        
        # Validate validation rules
        for rule in selector.validation_rules:
            if not rule.weight or rule.weight < 0.0 or rule.weight > 1.0:
                issues.append(f"Validation rule weight must be between 0.0 and 1.0")
        
        # Validate context
        if not selector.context.strip():
            issues.append("Context cannot be empty")
        
        return issues
    
    def get_confidence_metrics(self, selector_name: str) -> ConfidenceMetrics:
        """Get performance metrics for selector."""
        # Get metrics from performance monitor
        return self._performance_monitor.get_metrics(selector_name)
    
    async def register_selector(self, selector: SemanticSelector) -> bool:
        """Register a new selector definition."""
        try:
            # Validate selector
            issues = await self.validate_selector(selector)
            if issues:
                self._logger.warning(
                    "selector_registration_failed",
                    selector_name=selector.name,
                    issues=issues
                )
                return False
            
            # Register selector
            self._selector_registry[selector.name] = selector
            
            # Register strategies
            for strategy in selector.strategies:
                strategy_instance = self._strategy_factory.create_strategy({
                    "type": strategy.type.value,
                    "id": strategy.id,
                    "priority": strategy.priority,
                    **strategy.config
                })
                self._strategies[strategy.id] = strategy_instance
            
            self._logger.info(
                "selector_registered",
                selector_name=selector.name,
                strategies=len(selector.strategies),
                context=selector.context
            )
            
            return True
            
        except Exception as e:
            self._logger.error(
                "selector_registration_error",
                selector_name=selector.name,
                error=str(e)
            )
            return False
    
    def unregister_selector(self, name: str) -> bool:
        """Unregister selector definition."""
        if name in self._selector_registry:
            del self._selector_registry[name]
            
            # Remove associated strategies
            strategies_to_remove = [
                strategy_id for strategy_id, strategy in self._strategies.items()
                if strategy_id.startswith(f"{name}.")
            ]
            
            for strategy_id in strategies_to_remove:
                del self._strategies[strategy_id]
            
            self._logger.info(
                "selector_unregistered",
                selector_name=name
            )
            
            return True
        
        return False
    
    async def _resolve_with_strategies(self, selector: SemanticSelector, 
                                   context: DOMContext, 
                                   attempt: ResolutionAttempt) -> SelectorResult:
        """Resolve selector using multiple strategies."""
        strategies = selector.get_strategies_by_priority()
        
        for strategy in strategies:
            strategy_instance = self._strategies.get(strategy.id)
            if not strategy_instance:
                self._logger.warning(
                    "strategy_not_found",
                    strategy_id=strategy.id
                )
                continue
            
            attempt.strategy_id = strategy.id
            attempt.start_time = datetime.utcnow()
            
            try:
                # Attempt resolution with this strategy
                result = await strategy_instance.attempt_resolution(selector, context)
                
                # Check if result meets confidence threshold
                if result.success and result.confidence_score >= selector.confidence_threshold:
                    attempt.end_time = datetime.utcnow()
                    attempt.result = result
                    attempt.error = None
                    break
                elif result.success:
                    # Low confidence, continue to next strategy
                    self._logger.debug(
                        "low_confidence_skip",
                        selector_name=selector.name,
                        strategy_id=strategy.id,
                        confidence=result.confidence_score,
                        threshold=selector.confidence_threshold
                    )
                    continue
                else:
                    # Failed resolution, continue to next strategy
                    self._logger.debug(
                        "strategy_failed",
                        selector_name=selector.name,
                        strategy_id=strategy_id,
                        failure_reason=result.failure_reason
                    )
                    continue
                    
            except Exception as e:
                attempt.error = e
                self._logger.error(
                    "strategy_execution_error",
                    selector_name=selector.name,
                    strategy_id=strategy_id,
                    error=str(e)
                )
                continue
        
        # If all strategies failed, create failure result with snapshot
        if not attempt.result:
            attempt.end_time = datetime.utcnow()
            attempt.error = Exception("All strategies failed")
            
            # Capture DOM snapshot for failure analysis
            try:
                snapshot_id = await self._capture_failure_snapshot(selector, context)
                attempt.failure_reason = f"All {len(strategies)} strategies failed"
            except Exception as e:
                self._logger.warning(
                    "snapshot_capture_failed",
                    selector_name=selector.name,
                    error=str(e)
                )
                snapshot_id = None
            
            result = SelectorResult(
                selector_name=selector.name,
                strategy_used="none",
                element_info=None,
                confidence_score=0.0,
                resolution_time=(attempt.end_time - attempt.start_time).total_seconds() * 1000,
                validation_results=[],
                success=False,
                timestamp=datetime.utcnow(),
                failure_reason=attempt.failure_reason,
                snapshot_id=snapshot_id
            )
        
        attempt.end_time = datetime.utcnow()
        attempt.result = result
        attempt.error = None
        
        return result
    
    async def _capture_failure_snapshot(self, selector: SemanticSelector, context: DOMContext) -> Optional[str]:
        """Capture DOM snapshot for failure analysis."""
        try:
            # Create snapshot metadata
            viewport_size = await context.get_viewport_size()
            user_agent = await context.get_user_agent()
            
            metadata = SnapshotMetadata(
                page_url=context.url,
                tab_context=context.tab_context,
                viewport_size=viewport_size,
                user_agent=user_agent,
                resolution_attempt=len(self._resolution_attempts),
                failure_reason="All strategies failed",
                performance_metrics={
                    "total_time": 0.0,
                    "strategies_tried": len(selector.strategies),
                    "success_rate": 0.0
                }
            )
            
            # Capture DOM content
            dom_content = await context.get_page_content()
            
            # Create snapshot
            snapshot = DOMSnapshot(
                id=f"failure_{selector.name}_{datetime.utcnow().timestamp()}",
                selector_name=selector.name,
                snapshot_type=SnapshotType.FAILURE,
                dom_content=dom_content,
                metadata=metadata,
                file_path=f"data/snapshots/{snapshot.id}.json",
                created_at=datetime.utcnow(),
                file_size=len(dom_content.encode('utf-8'))
            )
            
            # Store snapshot
            snapshot_id = await self._storage_adapter.store_snapshot(snapshot)
            
            self._logger.info(
                "failure_snapshot_captured",
                selector_name=selector.name,
                snapshot_id=snapshot_id,
                file_size=snapshot.file_size
            )
            
            return snapshot_id
            
        except Exception as e:
            self._logger.error(
                "failure_snapshot_capture_failed",
                selector_name=selector.name,
                error=str(e)
            )
            return None
    
    def _log_resolution_completion(self, selector_name: str, result: SelectorResult) -> None:
        """Log resolution completion details."""
        if result.success:
            self._logger.info(
                "resolution_completed",
                selector_name=selector_name,
                strategy=result.strategy_used,
                confidence=result.confidence_score,
                resolution_time=result.resolution_time,
                validation_count=len(result.validation_results),
                element_text=result.element_info.text_content[:50] if result.element_info else "N/A"
            )
        else:
            self._logger.warning(
                "resolution_failed",
                selector_name=selector_name,
                strategy=result.strategy_used,
                failure_reason=result.failure_reason,
                resolution_time=result.resolution_time
            )
    
    def _determine_quality_gate(self, context: DOMContext) -> str:
        """Determine quality gate based on context."""
        # Default to development if no context information is available
        if not context or not hasattr(context, 'environment'):
            return "development"
        
        # Get environment from context
        environment = getattr(context, 'environment', 'development')
        
        # Map environment to quality gate
        gate_mapping = {
            'production': 'production',
            'prod': 'production',
            'staging': 'staging',
            'stage': 'staging',
            'development': 'development',
            'dev': 'development',
            'testing': 'testing',
            'test': 'testing',
            'research': 'development'  # Use development gate for research
        }
        
        return gate_mapping.get(environment.lower(), 'development')
    
    def _initialize_common_strategies(self) -> None:
        """Initialize common strategy patterns."""
        # Register strategy factory
        common_strategies = [
            {"type": "text_anchor", "id": "default_text_anchor", "priority": 1},
            {"type": "attribute_match", "id": "default_attribute_match", "priority": 2},
            {"type": "dom_relationship", "id": "default_dom_relationship", "priority": 3},
            {"type": "role_based", "id": "default_role_based", "priority": 4}
        ]
        
        for strategy_config in common_strategies:
            try:
                strategy_instance = self._strategy_factory.create_strategy(strategy_config)
                self._strategies[strategy_config["id"]] = strategy_instance
                self._logger.debug(
                    "common_strategy_registered",
                    strategy_id=strategy_config["id"],
                    strategy_type=strategy_config["type"],
                    priority=strategy_config["priority"]
                )
            except Exception as e:
                self._logger.error(
                    "common_strategy_registration_failed",
                    strategy_config=strategy_config,
                    error=str(e)
                )
    
    def _get_strategy(self, strategy_id: str) -> Optional[ISelectorPattern]:
        """Get strategy by ID."""
        return self._strategies.get(strategy_id)
    
    def filter_results_by_confidence(self, results: List[SelectorResult], 
                                   context: Optional[DOMContext] = None,
                                   gate_name: Optional[str] = None) -> List[SelectorResult]:
        """
        Filter results based on confidence thresholds and quality gates.
        
        Args:
            results: List of selector results to filter
            context: Optional DOM context for determining quality gate
            gate_name: Optional quality gate name (overrides context-based determination)
            
        Returns:
            Filtered list of results that pass confidence and quality checks
        """
        if not results:
            return []
        
        # Determine quality gate
        if gate_name:
            quality_gate = gate_name
        elif context:
            quality_gate = self._determine_quality_gate(context)
        else:
            quality_gate = "development"  # Default gate
        
        # Get threshold for the quality gate
        threshold = self._threshold_manager.get_threshold(quality_gate)
        
        filtered_results = []
        rejected_results = []
        
        for result in results:
            # Check if result has confidence score
            if not hasattr(result, 'confidence_score'):
                self._logger.warning(
                    "result_missing_confidence",
                    selector_name=getattr(result, 'selector_name', 'unknown'),
                    result_type=type(result).__name__
                )
                continue
            
            # Filter by confidence threshold
            if result.confidence_score >= threshold:
                # Check quality if metadata is available
                quality_passed = True
                if hasattr(result, 'metadata') and 'quality_passed' in result.metadata:
                    quality_passed = result.metadata['quality_passed']
                
                if quality_passed:
                    filtered_results.append(result)
                else:
                    rejected_results.append({
                        'result': result,
                        'reason': 'quality_gate_failed',
                        'gate': quality_gate,
                        'confidence': result.confidence_score,
                        'threshold': threshold
                    })
            else:
                rejected_results.append({
                    'result': result,
                    'reason': 'confidence_threshold_failed',
                    'gate': quality_gate,
                    'confidence': result.confidence_score,
                    'threshold': threshold
                })
        
        # Log filtering results
        self._logger.info(
            "confidence_filtering_completed",
            total_results=len(results),
            passed=len(filtered_results),
            rejected=len(rejected_results),
            gate_name=quality_gate,
            threshold=threshold
        )
        
        # Log rejected results details
        for rejection in rejected_results:
            self._logger.debug(
                "result_rejected",
                selector_name=getattr(rejection['result'], 'selector_name', 'unknown'),
                reason=rejection['reason'],
                confidence=rejection['confidence'],
                threshold=rejection['threshold'],
                gate=rejection['gate']
            )
        
        return filtered_results
    
    def get_confidence_statistics(self, results: List[SelectorResult]) -> Dict[str, Any]:
        """
        Get confidence statistics for a list of results.
        
        Args:
            results: List of selector results
            
        Returns:
            Dictionary with confidence statistics
        """
        if not results:
            return {
                'total_results': 0,
                'average_confidence': 0.0,
                'min_confidence': 0.0,
                'max_confidence': 0.0,
                'confidence_distribution': {},
                'quality_passed_rate': 0.0
            }
        
        # Extract confidence scores
        confidence_scores = []
        quality_passed_count = 0
        
        for result in results:
            if hasattr(result, 'confidence_score'):
                confidence_scores.append(result.confidence_score)
                
                # Check quality passed if metadata is available
                if hasattr(result, 'metadata') and 'quality_passed' in result.metadata:
                    if result.metadata['quality_passed']:
                        quality_passed_count += 1
        
        if not confidence_scores:
            return {
                'total_results': len(results),
                'average_confidence': 0.0,
                'min_confidence': 0.0,
                'max_confidence': 0.0,
                'confidence_distribution': {},
                'quality_passed_rate': 0.0
            }
        
        # Calculate statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)
        
        # Calculate confidence distribution
        distribution = {
            'perfect': sum(1 for score in confidence_scores if score >= 0.95),
            'high': sum(1 for score in confidence_scores if 0.85 <= score < 0.95),
            'medium': sum(1 for score in confidence_scores if 0.70 <= score < 0.85),
            'low': sum(1 for score in confidence_scores if 0.50 <= score < 0.70),
            'failed': sum(1 for score in confidence_scores if score < 0.50)
        }
        
        # Calculate quality passed rate
        quality_passed_rate = quality_passed_count / len(results) if results else 0.0
        
        return {
            'total_results': len(results),
            'average_confidence': avg_confidence,
            'min_confidence': min_confidence,
            'max_confidence': max_confidence,
            'confidence_distribution': distribution,
            'quality_passed_rate': quality_passed_rate
        }


# Global selector engine instance
selector_engine = SelectorEngine()


def get_selector_engine() -> SelectorEngine:
    """Get global selector engine instance."""
    return selector_engine
