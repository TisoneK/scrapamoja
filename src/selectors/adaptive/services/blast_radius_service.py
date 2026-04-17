"""
Blast Radius Service for calculating impact of selector failures.

This service provides:
- Blast radius calculation for failed selectors
- Severity assessment based on confidence scores
- Cascading effects detection from selector dependencies
- Affected records counting

Story: 6.3 - Blast Radius Calculation
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type
import logging

from pydantic import BaseModel, Field

from src.selectors.adaptive.services.confidence_query_service import (
    get_confidence_query_service,
    ConfidenceQueryService,
)
from src.selectors.adaptive.services.health_status_service import (
    get_health_status_service,
    HealthStatusService,
    HealthStatus,
)
from src.selectors.adaptive.db.repositories.failure_event_repository import (
    FailureEventRepository,
)
from src.selectors.yaml_loader import get_yaml_loader, YAMLSelectorLoader
from src.observability.logger import get_logger

logger = logging.getLogger(__name__)


class BlastRadiusSeverity(str, Enum):
    """Severity levels for blast radius assessment."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class FieldType(str, Enum):
    """Type of data field affected by selector failure."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    AUXILIARY = "auxiliary"


class DependencyType(str, Enum):
    """Type of dependency between selectors."""
    SHARES_DATA = "shares_data"
    DEPENDS_ON = "depends_on"
    RELATED = "related"


@dataclass
class AffectedFieldData:
    """Data for an affected field."""
    field_name: str
    field_type: FieldType
    confidence_impact: float


@dataclass
class CascadingSelectorData:
    """Data for a cascading selector."""
    selector_id: str
    dependency_type: DependencyType
    potential_impact: str


class BlastRadiusConfig(BaseModel):
    """Configuration for blast radius calculation."""
    critical_confidence_threshold: float = Field(default=0.5, description="Score < 0.5 = critical")
    major_confidence_threshold: float = Field(default=0.8, description="Score 0.5-0.79 = major")
    # Score >= 0.8 = minor (or healthy - no blast radius)
    critical_fields: List[str] = Field(
        default=["home_team", "away_team", "score", "match_time"],
        description="List of fields considered primary/critical"
    )


@dataclass
class BlastRadiusResult:
    """Result of blast radius calculation for a single selector."""
    failed_selector: str
    affected_fields: List[AffectedFieldData]
    affected_records: int
    severity: BlastRadiusSeverity
    recommended_actions: List[str]
    cascading_selectors: List[CascadingSelectorData]
    timestamp: datetime
    confidence_score: float
    message: Optional[str] = None


class BlastRadiusService:
    """
    Service for calculating blast radius of selector failures.
    
    Features:
    - AC1: Failure Impact Identification
    - AC2: Severity Assessment
    - AC3: Cascading Effects Detection
    - AC4: Blast Radius Query Response
    - AC5: Real-Time Updates (via WebSocket integration)
    """

    # Primary/secondary field classification
    PRIMARY_FIELDS = {"home_team", "away_team", "score", "match_time", "date", "league"}
    SECONDARY_FIELDS = {"odds", "weather", "venue", "referee", "attendance"}
    AUXILIARY_FIELDS = {"highlights", "statistics", "player_stats", "coach_info"}

    def __init__(
        self,
        confidence_service: Optional[ConfidenceQueryService] = None,
        health_service: Optional[HealthStatusService] = None,
        failure_repository: Optional[FailureEventRepository] = None,
        yaml_loader: Optional[YAMLSelectorLoader] = None,
        config: Optional[BlastRadiusConfig] = None,
    ):
        """
        Initialize the blast radius service.
        
        Args:
            confidence_service: Service for querying confidence scores
            health_service: Service for health status
            failure_repository: Repository for failure events
            yaml_loader: Loader for YAML selector configs
            config: Configuration for blast radius thresholds
        """
        self.confidence_service = confidence_service or get_confidence_query_service()
        self.health_service = health_service or get_health_status_service()
        self.failure_repository = failure_repository or FailureEventRepository()
        self.yaml_loader = yaml_loader or get_yaml_loader()
        self.config = config or BlastRadiusConfig()
        
        # Cache for selector dependencies
        self._dependency_cache: Dict[str, List[CascadingSelectorData]] = {}

    def calculate_severity(
        self, 
        confidence_score: float, 
        is_primary_field: bool = False
    ) -> BlastRadiusSeverity:
        """
        Calculate severity based on confidence score and field type.
        
        Args:
            confidence_score: The confidence score (0.0 to 1.0)
            is_primary_field: Whether the affected field is primary
            
        Returns:
            BlastRadiusSeverity: critical, major, or minor
        """
        # Critical: confidence_score < 0.5 AND affects primary data fields
        if confidence_score < self.config.critical_confidence_threshold:
            if is_primary_field:
                return BlastRadiusSeverity.CRITICAL
            # Still critical if very low confidence regardless of field
            return BlastRadiusSeverity.CRITICAL
        
        # Major: confidence_score 0.5-0.79 OR affects secondary data fields
        if confidence_score < self.config.major_confidence_threshold:
            return BlastRadiusSeverity.MAJOR
        
        # Minor: confidence_score >= 0.8 OR affects optional/auxiliary data
        return BlastRadiusSeverity.MINOR

    def get_field_type(self, field_name: str) -> FieldType:
        """
        Determine the type of field based on field name.
        
        Args:
            field_name: Name of the field
            
        Returns:
            FieldType: primary, secondary, or auxiliary
        """
        if field_name in self.PRIMARY_FIELDS:
            return FieldType.PRIMARY
        elif field_name in self.SECONDARY_FIELDS:
            return FieldType.SECONDARY
        else:
            return FieldType.AUXILIARY

    def get_affected_fields(self, selector_id: str) -> List[AffectedFieldData]:
        """
        Get affected fields for a selector.
        
        Args:
            selector_id: The selector ID
            
        Returns:
            List of affected fields with their types
        """
        affected_fields = []
        
        # Try to get fields from YAML selector configuration
        try:
            cached = self.yaml_loader._selector_cache
            for file_path, selector in cached.items():
                if selector.id == selector_id:
                    # Check for extracted_fields in metadata or hints
                    if hasattr(selector, 'metadata') and selector.metadata:
                        fields = selector.metadata.get('extracted_fields', [])
                        for field in fields:
                            field_type = self.get_field_type(field)
                            affected_fields.append(AffectedFieldData(
                                field_name=field,
                                field_type=field_type,
                                confidence_impact=1.0 if field_type == FieldType.PRIMARY else 0.7
                            ))
                    break
        except Exception as e:
            logger.warning(
                "Failed to get fields from YAML",
                selector_id=selector_id,
                error=str(e)
            )
        
        # If no fields found, use selector_id as field name with default type
        if not affected_fields:
            # Infer field name from selector_id (e.g., "home_team" -> "home_team")
            field_type = self.get_field_type(selector_id)
            affected_fields.append(AffectedFieldData(
                field_name=selector_id,
                field_type=field_type,
                confidence_impact=1.0 if field_type == FieldType.PRIMARY else 0.7
            ))
        
        return affected_fields

    def count_affected_records(self, selector_id: str) -> int:
        """
        Count the number of records affected by a selector failure.
        
        Args:
            selector_id: The selector ID
            
        Returns:
            Number of affected records
        """
        try:
            # Get failure events for this selector
            events = self.failure_repository.get_by_selector(selector_id, limit=1000)
            return len(events)
        except Exception as e:
            logger.warning(
                "Failed to count affected records",
                selector_id=selector_id,
                error=str(e)
            )
            return 0

    def get_cascading_selectors(self, selector_id: str) -> List[CascadingSelectorData]:
        """
        Get selectors that may be affected by cascading failures.
        
        Args:
            selector_id: The failed selector ID
            
        Returns:
            List of potentially cascading selectors
        """
        if selector_id in self._dependency_cache:
            return self._dependency_cache[selector_id]
        
        cascading = []
        
        try:
            # Get dependency information from YAML hints
            cached = self.yaml_loader._selector_cache
            
            # Find all selectors that depend on or share data with this selector
            for file_path, selector in cached.items():
                if not hasattr(selector, 'hints') or not selector.hints:
                    continue
                
                hints = selector.hints
                
                # Check for depends_on relationships
                depends_on = getattr(hints, 'depends_on', []) or []
                if selector_id in depends_on:
                    cascading.append(CascadingSelectorData(
                        selector_id=selector.id,
                        dependency_type=DependencyType.DEPENDS_ON,
                        potential_impact=f"Selector '{selector.id}' depends on '{selector_id}'"
                    ))
                
                # Check for alternatives (shared data)
                alternatives = getattr(hints, 'alternatives', []) or []
                if selector_id in alternatives:
                    cascading.append(CascadingSelectorData(
                        selector_id=selector.id,
                        dependency_type=DependencyType.SHARES_DATA,
                        potential_impact=f"Selector '{selector.id}' shares data context with '{selector_id}'"
                    ))
                
                # Check for related_selectors
                related = getattr(hints, 'related_selectors', []) or []
                if selector_id in related:
                    cascading.append(CascadingSelectorData(
                        selector_id=selector.id,
                        dependency_type=DependencyType.RELATED,
                        potential_impact=f"Selector '{selector.id}' is related to '{selector_id}'"
                    ))
                    
        except Exception as e:
            logger.warning(
                "Failed to get cascading selectors",
                selector_id=selector_id,
                error=str(e)
            )
        
        self._dependency_cache[selector_id] = cascading
        return cascading

    def get_recommended_actions(
        self,
        severity: BlastRadiusSeverity,
        alternatives: List[str]
    ) -> List[str]:
        """
        Generate recommended actions based on severity and alternatives.
        
        Args:
            severity: The blast radius severity
            alternatives: List of alternative selectors
            
        Returns:
            List of recommended action strings
        """
        if severity == BlastRadiusSeverity.CRITICAL:
            actions = [
                "URGENT: Selector requires immediate attention",
                f"Consider using alternative selectors: {', '.join(alternatives)}" if alternatives else "No alternatives available",
                "Review selector configuration in YAML"
            ]
        elif severity == BlastRadiusSeverity.MAJOR:
            actions = [
                "Selector showing degraded performance",
                "Monitor closely and plan selector update",
                f"Alternatives available: {', '.join(alternatives)}" if alternatives else "None"
            ]
        else:  # MINOR
            actions = [
                "Selector performing adequately",
                "Minor impact - no immediate action required"
            ]
        
        return actions

    def calculate_blast_radius(
        self,
        selector_id: str,
        include_cascading: bool = True,
        include_recommended_actions: bool = True,
    ) -> BlastRadiusResult:
        """
        Calculate blast radius for a single selector.
        
        Args:
            selector_id: The selector ID to calculate blast radius for
            include_cascading: Whether to include cascading selectors
            include_recommended_actions: Whether to include recommended actions
            
        Returns:
            BlastRadiusResult with blast radius calculation
        """
        logger.info("Calculating blast radius", selector_id=selector_id)
        
        # Get confidence score
        try:
            confidence_result = self.confidence_service.query_single(selector_id)
            confidence_score = confidence_result.confidence_score
        except Exception as e:
            logger.warning(
                "Failed to get confidence score, using default",
                selector_id=selector_id,
                error=str(e)
            )
            confidence_score = self.config.critical_confidence_threshold
        
        # Get affected fields
        affected_fields = self.get_affected_fields(selector_id)
        
        # Check if any field is primary
        is_primary_field = any(
            f.field_type == FieldType.PRIMARY for f in affected_fields
        )
        
        # Calculate severity
        severity = self.calculate_severity(confidence_score, is_primary_field)
        
        # Count affected records
        affected_records = self.count_affected_records(selector_id)
        
        # Get cascading selectors
        cascading_selectors = []
        if include_cascading:
            cascading_selectors = self.get_cascading_selectors(selector_id)
        
        # Get recommended actions
        recommended_actions = []
        if include_recommended_actions:
            alternatives = self.health_service.get_alternatives_from_yaml(selector_id)
            recommended_actions = self.get_recommended_actions(severity, alternatives)
        
        # Generate message
        message = None
        if severity == BlastRadiusSeverity.CRITICAL:
            message = f"CRITICAL: {affected_records} records affected by selector failure"
        elif severity == BlastRadiusSeverity.MAJOR:
            message = f"MAJOR: {affected_records} records affected, degraded performance detected"
        else:
            message = f"MINOR: {affected_records} records affected, acceptable performance"
        
        return BlastRadiusResult(
            failed_selector=selector_id,
            affected_fields=affected_fields,
            affected_records=affected_records,
            severity=severity,
            recommended_actions=recommended_actions,
            cascading_selectors=cascading_selectors,
            timestamp=datetime.now(timezone.utc),
            confidence_score=confidence_score,
            message=message,
        )

    def calculate_batch_blast_radius(
        self,
        selector_ids: List[str],
        include_cascading: bool = True,
        include_recommended_actions: bool = True,
    ) -> Dict[str, BlastRadiusResult]:
        """
        Calculate blast radius for multiple selectors.
        
        Args:
            selector_ids: List of selector IDs
            include_cascading: Whether to include cascading selectors
            include_recommended_actions: Whether to include recommended actions
            
        Returns:
            Dictionary of blast radius results keyed by selector_id
        """
        logger.info("Calculating batch blast radius", count=len(selector_ids))
        
        results = {}
        for selector_id in selector_ids:
            try:
                result = self.calculate_blast_radius(
                    selector_id=selector_id,
                    include_cascading=include_cascading,
                    include_recommended_actions=include_recommended_actions,
                )
                results[selector_id] = result
            except Exception as e:
                logger.warning(
                    "Failed to calculate blast radius for selector",
                    selector_id=selector_id,
                    error=str(e)
                )
        
        return results

    def get_blast_radius_summary(
        self,
        selector_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Get summary of blast radius for multiple selectors.
        
        Args:
            selector_ids: List of selector IDs
            
        Returns:
            Dictionary with summary statistics
        """
        results = self.calculate_batch_blast_radius(selector_ids)
        
        total_affected_records = 0
        critical_count = 0
        major_count = 0
        minor_count = 0
        
        for result in results.values():
            total_affected_records += result.affected_records
            if result.severity == BlastRadiusSeverity.CRITICAL:
                critical_count += 1
            elif result.severity == BlastRadiusSeverity.MAJOR:
                major_count += 1
            else:
                minor_count += 1
        
        return {
            "total_affected_records": total_affected_records,
            "critical_count": critical_count,
            "major_count": major_count,
            "minor_count": minor_count,
            "selectors_analyzed": len(results),
        }

    def clear_cache(self) -> None:
        """Clear the dependency cache."""
        self._dependency_cache.clear()
        logger.info("Blast radius cache cleared")


# Global service instance
_blast_radius_service: Optional[BlastRadiusService] = None


def get_blast_radius_service() -> BlastRadiusService:
    """
    Get the global blast radius service instance.
    
    Returns:
        The global BlastRadiusService instance
    """
    global _blast_radius_service
    if _blast_radius_service is None:
        _blast_radius_service = BlastRadiusService()
    return _blast_radius_service
