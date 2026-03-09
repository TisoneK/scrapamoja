"""
Health Status Service for calculating and managing selector health status.

This module provides:
- Health status calculation from confidence scores
- Last failure timestamp retrieval
- Alternative selector lookup from YAML hints
- Recommended actions based on health status

Story: 6.2 - Selector Health Status Display
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
import asyncio

from pydantic import BaseModel, Field

from src.selectors.adaptive.services.confidence_query_service import (
    get_confidence_query_service,
    ConfidenceQueryService,
)
from src.selectors.adaptive.db.repositories.failure_event_repository import (
    FailureEventRepository,
)
from src.selectors.yaml_loader import get_yaml_loader, YAMLSelectorLoader
from src.selectors.websocket.integration import get_notification_service
from src.observability.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status enum for selectors."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class HealthStatusConfig(BaseModel):
    """Configuration for health status thresholds."""
    healthy_threshold: float = Field(default=0.8, description="Score >= 0.8 = healthy")
    degraded_threshold: float = Field(default=0.5, description="Score 0.5-0.79 = degraded")
    failed_threshold: float = Field(default=0.5, description="Score < 0.5 = failed")


@dataclass
class SelectorHealthInfo:
    """Health information for a single selector."""
    selector_id: str
    status: HealthStatus
    confidence_score: float
    last_failure: Optional[datetime]
    recommended_action: str
    alternatives: List[str]


@dataclass
class HealthDashboardData:
    """Dashboard data with selectors grouped by health status."""
    healthy: List[SelectorHealthInfo]
    degraded: List[SelectorHealthInfo]
    failed: List[SelectorHealthInfo]
    total: int
    last_updated: datetime


class HealthStatusService:
    """
    Service for calculating selector health status.
    
    Provides methods to:
    - Calculate health status from confidence scores
    - Get all selectors grouped by health status
    - Get single selector health
    - Look up alternative selectors from YAML hints
    - Generate recommended actions
    - Send real-time health status updates via WebSocket
    """

    # Track last known health status for change detection
    _last_health_status: Dict[str, 'HealthStatus'] = {}

    def __init__(
        self,
        confidence_service: Optional[ConfidenceQueryService] = None,
        failure_repository: Optional[FailureEventRepository] = None,
        yaml_loader: Optional[YAMLSelectorLoader] = None,
        config: Optional[HealthStatusConfig] = None,
    ):
        """
        Initialize the health status service.
        
        Args:
            confidence_service: Service for querying confidence scores
            failure_repository: Repository for failure events
            yaml_loader: Loader for YAML selector configs
            config: Configuration for health thresholds
        """
        self.confidence_service = confidence_service or get_confidence_query_service()
        self.failure_repository = failure_repository or FailureEventRepository()
        self.yaml_loader = yaml_loader or get_yaml_loader()
        self.config = config or HealthStatusConfig()
        
        # Cache for alternative selectors
        self._alternatives_cache: Dict[str, List[str]] = {}

    def calculate_status(self, confidence_score: float) -> HealthStatus:
        """
        Calculate health status from confidence score.
        
        Args:
            confidence_score: The confidence score (0.0 to 1.0)
            
        Returns:
            HealthStatus: healthy, degraded, or failed
        """
        if confidence_score >= self.config.healthy_threshold:
            return HealthStatus.HEALTHY
        elif confidence_score >= self.config.degraded_threshold:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.FAILED

    def get_last_failure(self, selector_id: str) -> Optional[datetime]:
        """
        Get the last failure timestamp for a selector.
        
        Args:
            selector_id: The selector ID to query
            
        Returns:
            Timestamp of last failure, or None if no failures
        """
        try:
            events = self.failure_repository.get_by_selector(selector_id, limit=1)
            if events:
                return events[0].timestamp
        except Exception as e:
            logger.warning(
                "Failed to get last failure",
                selector_id=selector_id,
                error=str(e)
            )
        return None

    def get_alternatives_from_yaml(self, selector_id: str) -> List[str]:
        """
        Get alternative selectors from YAML hints.
        
        Args:
            selector_id: The selector ID to find alternatives for
            
        Returns:
            List of alternative selector IDs
        """
        if selector_id in self._alternatives_cache:
            return self._alternatives_cache[selector_id]
        
        alternatives = []
        
        try:
            # Try to find selector in cached selectors
            cached = self.yaml_loader._selector_cache
            for file_path, selector in cached.items():
                if selector.id == selector_id:
                    # Check for alternatives in hints
                    if hasattr(selector, 'hints') and selector.hints:
                        alternatives = getattr(selector.hints, 'alternatives', []) or []
                    break
        except Exception as e:
            logger.warning(
                "Failed to get alternatives from YAML",
                selector_id=selector_id,
                error=str(e)
            )
        
        self._alternatives_cache[selector_id] = alternatives
        return alternatives

    def get_recommended_action(
        self,
        status: HealthStatus,
        alternatives: List[str]
    ) -> str:
        """
        Generate recommended action based on health status.
        
        Args:
            status: Current health status
            alternatives: List of alternative selectors
            
        Returns:
            Recommended action string
        """
        if status == HealthStatus.HEALTHY:
            return "Selector is performing well"
        
        alternatives_text = ""
        if alternatives:
            alternatives_text = f" Alternatives available: {', '.join(alternatives)}"
        
        if status == HealthStatus.DEGRADED:
            return f"Consider reviewing selector - moderate failure rate{alternatives_text}"
        else:  # FAILED
            return f"Selector requires immediate attention - high failure rate{alternatives_text}"

    def get_selector_health(self, selector_id: str) -> SelectorHealthInfo:
        """
        Get health information for a single selector.
        
        Args:
            selector_id: The selector ID to query
            
        Returns:
            SelectorHealthInfo with health details
        """
        logger.info("Getting health for selector", selector_id=selector_id)
        
        # Get confidence score
        confidence_result = self.confidence_service.query_single(selector_id)
        confidence_score = confidence_result.confidence_score
        
        # Calculate health status
        status = self.calculate_status(confidence_score)
        
        # Get last failure timestamp
        last_failure = self.get_last_failure(selector_id)
        
        # Get alternatives
        alternatives = self.get_alternatives_from_yaml(selector_id)
        
        # Generate recommended action
        recommended_action = self.get_recommended_action(status, alternatives)
        
        return SelectorHealthInfo(
            selector_id=selector_id,
            status=status,
            confidence_score=confidence_score,
            last_failure=last_failure,
            recommended_action=recommended_action,
            alternatives=alternatives,
        )

    def get_dashboard(self) -> HealthDashboardData:
        """
        Get health dashboard with all selectors grouped by status.
        
        Returns:
            HealthDashboardData with selectors grouped by health status
        """
        logger.info("Building health dashboard")
        
        # Get all unique selectors from both failure repository AND yaml loader
        unique_selectors = set()
        
        # Get selectors from failure repository
        try:
            failure_selectors = self.failure_repository.get_unique_selectors()
            unique_selectors.update(failure_selectors)
        except Exception as e:
            logger.warning("Failed to get unique selectors from failure repository", error=str(e))
        
        # Get selectors from YAML loader cache (for selectors with no failures)
        try:
            yaml_selectors = list(self.yaml_loader._selector_cache.values())
            unique_selectors.update([s.id for s in yaml_selectors])
        except Exception as e:
            logger.warning("Failed to get selectors from yaml loader", error=str(e))
        
        # If no selectors, return empty dashboard
        if not unique_selectors:
            return HealthDashboardData(
                healthy=[],
                degraded=[],
                failed=[],
                total=0,
                last_updated=datetime.now(timezone.utc),
            )
        
        # Get health for each selector
        healthy = []
        degraded = []
        failed = []
        
        for selector_id in unique_selectors:
            try:
                health_info = self.get_selector_health(selector_id)
                
                # Check if status changed and notify via WebSocket (non-blocking)
                self._notify_status_change_sync(selector_id, health_info.status)
                
                if health_info.status == HealthStatus.HEALTHY:
                    healthy.append(health_info)
                elif health_info.status == HealthStatus.DEGRADED:
                    degraded.append(health_info)
                else:
                    failed.append(health_info)
            except Exception as e:
                logger.warning(
                    "Failed to get health for selector",
                    selector_id=selector_id,
                    error=str(e)
                )
        
        total = len(healthy) + len(degraded) + len(failed)
        
        return HealthDashboardData(
            healthy=healthy,
            degraded=degraded,
            failed=failed,
            total=total,
            last_updated=datetime.now(timezone.utc),
        )
    
    def _notify_status_change_sync(self, selector_id: str, new_status: HealthStatus) -> None:
        """
        Notify WebSocket subscribers of health status change (sync version).
        
        Args:
            selector_id: The selector ID
            new_status: The new health status
        """
        old_status = self._last_health_status.get(selector_id)
        
        # Only notify if status actually changed
        if old_status != new_status:
            self._last_health_status[selector_id] = new_status
            
            # Get confidence score for notification
            confidence_score = 0.0
            try:
                result = self.confidence_service.query_single(selector_id)
                confidence_score = result.confidence_score
            except Exception:
                pass
            
            # Schedule async WebSocket notification (fire and forget)
            try:
                asyncio.create_task(self._send_websocket_notification(
                    selector_id=selector_id,
                    old_status=old_status,
                    new_status=new_status,
                    confidence_score=confidence_score,
                ))
            except Exception as e:
                logger.warning(
                    "Failed to schedule health status notification",
                    selector_id=selector_id,
                    error=str(e)
                )
    
    async def _send_websocket_notification(
        self,
        selector_id: str,
        old_status: Optional[HealthStatus],
        new_status: HealthStatus,
        confidence_score: float,
    ) -> None:
        """
        Send WebSocket notification asynchronously.
        
        Args:
            selector_id: The selector ID
            old_status: Previous health status
            new_status: New health status
            confidence_score: Current confidence score
        """
        try:
            notification_service = get_notification_service()
            if notification_service.is_enabled and notification_service._client:
                # Use the existing WebSocket client's send_health_status_update method
                await notification_service._client.send_health_status_update(
                    selector_id=selector_id,
                    old_status=old_status.value if old_status else "unknown",
                    new_status=new_status.value,
                    confidence_score=confidence_score,
                )
        except Exception as e:
            logger.warning(
                "Failed to send health status notification",
                selector_id=selector_id,
                error=str(e)
            )

    def clear_cache(self) -> None:
        """Clear the alternatives cache."""
        self._alternatives_cache.clear()
        logger.info("Health status cache cleared")


# Global service instance
_health_status_service: Optional[HealthStatusService] = None


def get_health_status_service() -> HealthStatusService:
    """
    Get the global health status service instance.
    
    Returns:
        The global HealthStatusService instance
    """
    global _health_status_service
    if _health_status_service is None:
        _health_status_service = HealthStatusService()
    return _health_status_service
