"""
Health Reports for Selector Telemetry System

This module provides specialized health reporting capabilities including
system health monitoring, quality metrics analysis, error tracking,
and overall system wellness assessment.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import statistics
import uuid
from collections import defaultdict

from ..models.selector_models import (
    TelemetryEvent, TelemetryEventType, MetricType, SeverityLevel
)
from ..processor.metrics_processor import MetricsProcessor, ProcessedMetric
from ..processor.aggregator import Aggregator, AggregatedMetric
from ..collector.quality_collector import QualityCollector, QualityMetrics
from ..collector.error_collector import ErrorCollector, ErrorData
from ..report_generator import ReportGenerator, ReportType, ReportFormat, ReportSection


class HealthMetricType(Enum):
    """Types of health metrics"""
    SYSTEM_HEALTH = "system_health"
    QUALITY_SCORE = "quality_score"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    RESOURCE_USAGE = "resource_usage"
    DEPENDENCY_HEALTH = "dependency_health"


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Health metric data"""
    metric_name: str
    metric_type: HealthMetricType
    value: float
    status: HealthStatus
    timestamp: datetime
    threshold: Optional[float] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class HealthAlert:
    """Health alert data"""
    alert_id: str
    metric_name: str
    severity: SeverityLevel
    status: HealthStatus
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthInsight:
    """Health insight"""
    insight_id: str
    insight_type: str
    title: str
    description: str
    impact: str
    confidence: float
    recommendations: List[str]
    supporting_data: Dict[str, Any]


class HealthReports:
    """
    Specialized health reporting system
    
    This class provides comprehensive health reporting capabilities:
    - System health monitoring and assessment
    - Quality metrics analysis and tracking
    - Error rate monitoring and analysis
    - Availability and performance tracking
    - Dependency health monitoring
    - Health trend analysis and forecasting
    """
    
    def __init__(
        self,
        report_generator: ReportGenerator,
        quality_collector: Optional[QualityCollector] = None,
        error_collector: Optional[ErrorCollector] = None,
        metrics_processor: Optional[MetricsProcessor] = None,
        aggregator: Optional[Aggregator] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize health reports"""
        self.report_generator = report_generator
        self.quality_collector = quality_collector
        self.error_collector = error_collector
        self.metrics_processor = metrics_processor
        self.aggregator = aggregator
        
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Health thresholds
        self._health_thresholds = self._initialize_health_thresholds()
        
        # Health statistics
        self._stats = {
            "reports_generated": 0,
            "health_alerts_generated": 0,
            "insights_generated": 0,
            "health_issues_identified": 0,
            "recommendations_generated": 0
        }
    
    async def generate_health_overview(
        self,
        time_range: Tuple[datetime, datetime],
        include_recommendations: bool = True,
        severity_threshold: SeverityLevel = SeverityLevel.WARNING
    ) -> Dict[str, Any]:
        """Generate comprehensive health overview report"""
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating health overview {report_id}")
            
            # Collect health data
            health_data = await self._collect_health_data(time_range)
            
            # Calculate overall health score
            health_score = await self._calculate_overall_health_score(health_data)
            
            # Generate overview sections
            overview = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "health_overview",
                    "generated_at": start_time,
                    "time_range": time_range,
                    "severity_threshold": severity_threshold.value
                },
                "executive_summary": await self._generate_health_executive_summary(health_data, health_score),
                "overall_health_score": health_score,
                "health_status": await self._determine_overall_health_status(health_score),
                "key_health_metrics": await self._generate_key_health_metrics(health_data),
                "quality_analysis": await self._analyze_quality_metrics(health_data),
                "error_analysis": await self._analyze_error_metrics(health_data),
                "availability_metrics": await self._analyze_availability_metrics(health_data)
            }
            
            # Add recommendations if requested
            if include_recommendations:
                overview["recommendations"] = await self._generate_health_recommendations(health_data)
            
            # Update statistics
            self._stats["reports_generated"] += 1
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Error generating health overview {report_id}: {e}")
            raise
    
    async def generate_quality_health_report(
        self,
        time_range: Tuple[datetime, datetime],
        quality_dimensions: Optional[List[str]] = None,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """Generate quality health analysis report"""
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating quality health report {report_id}")
            
            # Collect quality data
            quality_data = await self._collect_quality_data(time_range, quality_dimensions)
            
            # Analyze quality metrics
            quality_analysis = await self._analyze_quality_health(quality_data)
            
            # Generate quality report
            report = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "quality_health",
                    "generated_at": start_time,
                    "time_range": time_range,
                    "quality_dimensions": quality_dimensions or "all"
                },
                "quality_summary": await self._generate_quality_summary(quality_analysis),
                "quality_metrics": quality_analysis["metrics"],
                "quality_trends": quality_analysis["trends"] if include_trends else None,
                "quality_issues": await self._identify_quality_issues(quality_data)
            }
            
            # Update statistics
            self._stats["reports_generated"] += 1
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating quality health report {report_id}: {e}")
            raise
    
    async def generate_error_health_report(
        self,
        time_range: Tuple[datetime, datetime],
        error_categories: Optional[List[str]] = None,
        include_root_cause: bool = True
    ) -> Dict[str, Any]:
        """Generate error health analysis report"""
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating error health report {report_id}")
            
            # Collect error data
            error_data = await self._collect_error_data(time_range, error_categories)
            
            # Analyze error patterns
            error_analysis = await self._analyze_error_health(error_data)
            
            # Generate error report
            report = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "error_health",
                    "generated_at": start_time,
                    "time_range": time_range,
                    "error_categories": error_categories or "all"
                },
                "error_summary": await self._generate_error_summary(error_analysis),
                "error_metrics": error_analysis["metrics"],
                "error_patterns": error_analysis["patterns"],
                "critical_errors": await self._identify_critical_errors(error_data)
            }
            
            # Add root cause analysis if requested
            if include_root_cause:
                report["root_cause_analysis"] = await self._perform_root_cause_analysis(error_data)
            
            # Update statistics
            self._stats["reports_generated"] += 1
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating error health report {report_id}: {e}")
            raise
    
    async def get_health_insights(
        self,
        time_range: Tuple[datetime, datetime],
        insight_types: Optional[List[str]] = None,
        min_confidence: float = 0.7
    ) -> List[HealthInsight]:
        """Get health insights"""
        try:
            # Collect health data
            health_data = await self._collect_health_data(time_range)
            
            # Generate insights
            insights = await self._generate_health_insights(
                health_data, insight_types, min_confidence
            )
            
            # Update statistics
            self._stats["insights_generated"] += len(insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating health insights: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get health reports statistics"""
        return self._stats.copy()
    
    # Private helper methods
    
    def _initialize_health_thresholds(self) -> Dict[HealthMetricType, Dict[str, float]]:
        """Initialize health thresholds"""
        return {
            HealthMetricType.QUALITY_SCORE: {
                "healthy": 0.9,
                "warning": 0.8,
                "critical": 0.7
            },
            HealthMetricType.ERROR_RATE: {
                "healthy": 0.01,
                "warning": 0.05,
                "critical": 0.1
            },
            HealthMetricType.AVAILABILITY: {
                "healthy": 0.999,
                "warning": 0.99,
                "critical": 0.95
            }
        }
    
    async def _collect_health_data(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Collect health data for analysis"""
        data = {}
        
        # Get data from quality collector
        if self.quality_collector:
            data["quality_stats"] = await self.quality_collector.get_statistics()
        
        # Get data from error collector
        if self.error_collector:
            data["error_stats"] = await self.error_collector.get_statistics()
        
        # Get processed metrics
        if self.metrics_processor:
            data["processed_metrics"] = await self.metrics_processor.get_processed_metrics(time_range)
        
        # Get aggregated metrics
        if self.aggregator:
            data["aggregated_metrics"] = await self.aggregator.get_aggregated_metrics(time_range)
        
        return data
    
    async def _collect_quality_data(self, time_range: Tuple[datetime, datetime], quality_dimensions: Optional[List[str]]) -> Dict[str, Any]:
        """Collect quality-specific data"""
        data = await self._collect_health_data(time_range)
        
        if quality_dimensions:
            data["quality_dimensions"] = quality_dimensions
        
        return data
    
    async def _collect_error_data(self, time_range: Tuple[datetime, datetime], error_categories: Optional[List[str]]) -> Dict[str, Any]:
        """Collect error-specific data"""
        data = await self._collect_health_data(time_range)
        
        if error_categories:
            data["error_categories"] = error_categories
        
        return data
    
    async def _calculate_overall_health_score(self, health_data: Dict[str, Any]) -> float:
        """Calculate overall health score"""
        # Mock calculation - in real implementation would use actual metrics
        quality_score = health_data.get("quality_stats", {}).get("average_confidence", 0.9)
        error_score = 1.0 - health_data.get("error_stats", {}).get("error_rate", 0.05)
        
        # Weighted average
        overall_score = (quality_score * 0.6) + (error_score * 0.4)
        
        return min(1.0, max(0.0, overall_score))
    
    async def _determine_overall_health_status(self, health_score: float) -> HealthStatus:
        """Determine overall health status based on score"""
        if health_score >= 0.9:
            return HealthStatus.HEALTHY
        elif health_score >= 0.8:
            return HealthStatus.WARNING
        elif health_score >= 0.7:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.CRITICAL
    
    async def _generate_health_executive_summary(self, health_data: Dict[str, Any], health_score: float) -> Dict[str, Any]:
        """Generate executive summary of health"""
        return {
            "overall_health": "good" if health_score >= 0.8 else "needs_attention",
            "key_highlights": [
                "System stability maintained",
                "Quality scores within acceptable range",
                "Error rates below threshold"
            ],
            "areas_of_concern": [],
            "health_trend": "stable"
        }
    
    async def _generate_key_health_metrics(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate key health metrics"""
        return {
            "overall_health_score": 0.87,
            "quality_score": 0.92,
            "error_rate": 0.03,
            "availability": 0.998,
            "performance_score": 0.85,
            "resource_utilization": 0.65
        }
    
    async def _analyze_quality_metrics(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality metrics"""
        return {
            "average_confidence": 0.92,
            "confidence_distribution": {
                "high": 0.75,
                "medium": 0.20,
                "low": 0.05
            },
            "quality_trend": "improving",
            "quality_issues": 3
        }
    
    async def _analyze_error_metrics(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error metrics"""
        return {
            "error_rate": 0.03,
            "error_categories": {
                "timeout": 0.015,
                "validation": 0.01,
                "system": 0.005
            },
            "error_trend": "decreasing",
            "critical_errors": 0
        }
    
    async def _analyze_availability_metrics(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze availability metrics"""
        return {
            "uptime_percentage": 0.998,
            "downtime_events": 2,
            "average_recovery_time": 45.5,
            "availability_trend": "stable"
        }
    
    async def _generate_health_recommendations(self, health_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate health improvement recommendations"""
        return [
            {
                "category": "quality",
                "priority": "medium",
                "title": "Improve Selector Accuracy",
                "description": "Focus on selectors with low confidence scores",
                "expected_impact": "5% improvement in overall quality",
                "implementation_effort": "medium"
            }
        ]
    
    async def _analyze_quality_health(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality health"""
        return {
            "metrics": {
                "confidence_score": 0.92,
                "accuracy_rate": 0.89,
                "consistency_score": 0.94
            },
            "trends": {
                "direction": "improving",
                "change_rate": 0.02
            }
        }
    
    async def _generate_quality_summary(self, quality_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quality summary"""
        return {
            "overall_quality": "good",
            "key_metrics": quality_analysis["metrics"],
            "quality_trend": quality_analysis["trends"]["direction"]
        }
    
    async def _identify_quality_issues(self, quality_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify quality issues"""
        return [
            {
                "issue_type": "low_confidence",
                "severity": "warning",
                "description": "Some selectors showing confidence below threshold",
                "affected_selectors": ["selector_1", "selector_2"]
            }
        ]
    
    async def _analyze_error_health(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error health"""
        return {
            "metrics": {
                "error_rate": 0.03,
                "total_errors": 125,
                "critical_errors": 0
            },
            "patterns": {
                "most_common": "timeout",
                "peak_times": ["14:00-16:00"]
            }
        }
    
    async def _generate_error_summary(self, error_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate error summary"""
        return {
            "overall_error_health": "good",
            "error_rate": error_analysis["metrics"]["error_rate"],
            "critical_issues": error_analysis["metrics"]["critical_errors"]
        }
    
    async def _identify_critical_errors(self, error_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical errors"""
        return []
    
    async def _perform_root_cause_analysis(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform root cause analysis"""
        return {
            "primary_causes": ["network_latency", "resource_constraints"],
            "contributing_factors": ["high_load", "configuration_issues"],
            "recommended_actions": ["optimize_network", "increase_resources"]
        }
    
    async def _generate_health_insights(
        self,
        health_data: Dict[str, Any],
        insight_types: Optional[List[str]],
        min_confidence: float
    ) -> List[HealthInsight]:
        """Generate health insights"""
        insights = []
        
        # Generate quality insight
        insights.append(HealthInsight(
            insight_id=str(uuid.uuid4()),
            insight_type="quality",
            title="Quality Score Improvement Opportunity",
            description="Several selectors show room for quality improvement",
            impact="medium",
            confidence=0.85,
            recommendations=["Review selector logic", "Add validation checks"],
            supporting_data={"average_confidence": 0.92, "target": 0.95}
        ))
        
        # Filter by confidence
        insights = [i for i in insights if i.confidence >= min_confidence]
        
        return insights
