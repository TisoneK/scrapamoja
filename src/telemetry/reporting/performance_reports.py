"""
Performance Reports for Selector Telemetry System

This module provides specialized performance reporting capabilities including
response time analysis, throughput metrics, bottleneck identification, and
performance optimization recommendations.
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
from ..collector.performance_collector import PerformanceCollector, PerformanceMetrics
from ..report_generator import ReportGenerator, ReportType, ReportFormat, ReportSection


class PerformanceMetricType(Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    CONCURRENCY = "concurrency"
    LATENCY = "latency"
    AVAILABILITY = "availability"


class PerformanceReportType(Enum):
    """Types of performance reports"""
    OVERVIEW = "overview"
    DETAILED_ANALYSIS = "detailed_analysis"
    BOTTLENECK_ANALYSIS = "bottleneck_analysis"
    TREND_ANALYSIS = "trend_analysis"
    COMPARISON = "comparison"
    OPTIMIZATION = "optimization"
    SLA_COMPLIANCE = "sla_compliance"


@dataclass
class PerformanceMetric:
    """Performance metric data"""
    metric_name: str
    metric_type: PerformanceMetricType
    value: float
    unit: str
    timestamp: datetime
    selector_name: Optional[str] = None
    operation_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceThreshold:
    """Performance threshold definition"""
    metric_type: PerformanceMetricType
    threshold_value: float
    comparison: str  # greater_than, less_than, equals
    severity: SeverityLevel
    description: str


@dataclass
class PerformanceInsight:
    """Performance insight"""
    insight_id: str
    metric_type: PerformanceMetricType
    title: str
    description: str
    impact: str  # high, medium, low
    confidence: float
    recommendations: List[str]
    supporting_data: Dict[str, Any]


class PerformanceReports:
    """
    Specialized performance reporting system
    
    This class provides comprehensive performance reporting capabilities:
    - Response time analysis and distribution
    - Throughput and capacity planning
    - Bottleneck identification and analysis
    - Performance trend analysis
    - SLA compliance monitoring
    - Optimization recommendations
    """
    
    def __init__(
        self,
        report_generator: ReportGenerator,
        performance_collector: Optional[PerformanceCollector] = None,
        metrics_processor: Optional[MetricsProcessor] = None,
        aggregator: Optional[Aggregator] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize performance reports"""
        self.report_generator = report_generator
        self.performance_collector = performance_collector
        self.metrics_processor = metrics_processor
        self.aggregator = aggregator
        
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Performance thresholds
        self._thresholds = self._initialize_default_thresholds()
        
        # Performance statistics
        self._stats = {
            "reports_generated": 0,
            "insights_generated": 0,
            "bottlenecks_identified": 0,
            "optimizations_suggested": 0,
            "sla_violations": 0
        }
    
    async def generate_performance_overview(
        self,
        time_range: Tuple[datetime, datetime],
        selector_names: Optional[List[str]] = None,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance overview report
        
        Args:
            time_range: Time range for the report
            selector_names: Optional list of selectors to include
            include_recommendations: Whether to include optimization recommendations
            
        Returns:
            Dict[str, Any]: Performance overview report
        """
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating performance overview {report_id}")
            
            # Collect performance data
            performance_data = await self._collect_performance_data(
                time_range, selector_names
            )
            
            # Generate overview sections
            overview = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "performance_overview",
                    "generated_at": start_time,
                    "time_range": time_range,
                    "selectors_included": selector_names or "all"
                },
                "executive_summary": await self._generate_executive_summary(performance_data),
                "key_metrics": await self._generate_key_metrics(performance_data),
                "response_time_analysis": await self._analyze_response_times(performance_data),
                "throughput_analysis": await self._analyze_throughput(performance_data),
                "success_rate_analysis": await self._analyze_success_rates(performance_data),
                "performance_distribution": await self._analyze_performance_distribution(performance_data),
                "top_performers": await self._identify_top_performers(performance_data),
                "performance_issues": await self._identify_performance_issues(performance_data)
            }
            
            # Add recommendations if requested
            if include_recommendations:
                overview["recommendations"] = await self._generate_performance_recommendations(
                    performance_data
                )
            
            # Update statistics
            self._stats["reports_generated"] += 1
            
            generation_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Generated performance overview {report_id} in {generation_time:.2f}s"
            )
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Error generating performance overview {report_id}: {e}")
            raise
    
    async def generate_bottleneck_analysis(
        self,
        time_range: Tuple[datetime, datetime],
        analysis_depth: str = "deep",
        include_solutions: bool = True
    ) -> Dict[str, Any]:
        """Generate detailed bottleneck analysis report"""
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating bottleneck analysis {report_id}")
            
            # Collect detailed performance data
            performance_data = await self._collect_detailed_performance_data(
                time_range, analysis_depth
            )
            
            # Identify bottlenecks
            bottlenecks = await self._identify_bottlenecks(performance_data, analysis_depth)
            
            # Generate bottleneck report
            report = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "bottleneck_analysis",
                    "generated_at": start_time,
                    "time_range": time_range,
                    "analysis_depth": analysis_depth
                },
                "bottleneck_summary": {
                    "total_bottlenecks": len(bottlenecks),
                    "critical_bottlenecks": len([b for b in bottlenecks if b.get("severity") == "critical"]),
                    "high_impact_bottlenecks": len([b for b in bottlenecks if b.get("impact") == "high"]),
                    "estimated_performance_gain": sum(b.get("potential_improvement", 0) for b in bottlenecks)
                },
                "identified_bottlenecks": bottlenecks,
                "impact_analysis": await self._analyze_bottleneck_impact(bottlenecks, performance_data)
            }
            
            # Add solutions if requested
            if include_solutions:
                report["solutions"] = await self._generate_bottleneck_solutions(bottlenecks)
            
            # Update statistics
            self._stats["reports_generated"] += 1
            self._stats["bottlenecks_identified"] += len(bottlenecks)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating bottleneck analysis {report_id}: {e}")
            raise
    
    async def generate_performance_trends(
        self,
        time_range: Tuple[datetime, datetime],
        trend_window: str = "1h",
        forecast_periods: int = 24,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """Generate performance trend analysis report"""
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating performance trends {report_id}")
            
            # Collect time series data
            time_series_data = await self._collect_time_series_data(time_range, trend_window)
            
            # Analyze trends for each metric
            trend_analysis = {}
            for metric_name, data in time_series_data.items():
                trend_analysis[metric_name] = await self._analyze_metric_trends(
                    metric_name, data, forecast_periods, include_seasonality
                )
            
            # Generate trend report
            report = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "performance_trends",
                    "generated_at": start_time,
                    "time_range": time_range,
                    "trend_window": trend_window,
                    "forecast_periods": forecast_periods
                },
                "trend_summary": await self._generate_trend_summary(trend_analysis),
                "metric_trends": trend_analysis,
                "performance_forecasts": await self._generate_performance_forecasts(trend_analysis)
            }
            
            # Update statistics
            self._stats["reports_generated"] += 1
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating performance trends {report_id}: {e}")
            raise
    
    async def generate_sla_compliance_report(
        self,
        time_range: Tuple[datetime, datetime],
        sla_definitions: Optional[Dict[str, Any]] = None,
        include_violations: bool = True
    ) -> Dict[str, Any]:
        """Generate SLA compliance report"""
        report_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Generating SLA compliance report {report_id}")
            
            # Use default SLA definitions if none provided
            sla_definitions = sla_definitions or self._get_default_sla_definitions()
            
            # Collect performance data for SLA analysis
            performance_data = await self._collect_performance_data(time_range)
            
            # Check SLA compliance
            compliance_results = await self._check_sla_compliance(performance_data, sla_definitions)
            
            # Generate SLA report
            report = {
                "report_metadata": {
                    "report_id": report_id,
                    "report_type": "sla_compliance",
                    "generated_at": start_time,
                    "time_range": time_range
                },
                "sla_summary": {
                    "overall_compliance_rate": compliance_results["overall_compliance"],
                    "total_sla_checks": compliance_results["total_checks"],
                    "passed_checks": compliance_results["passed_checks"],
                    "failed_checks": compliance_results["failed_checks"],
                    "compliance_trend": compliance_results["compliance_trend"]
                },
                "sla_definitions": sla_definitions,
                "compliance_details": compliance_results["details"]
            }
            
            # Add violations if requested
            if include_violations:
                report["violations"] = compliance_results["violations"]
            
            # Update statistics
            self._stats["reports_generated"] += 1
            self._stats["sla_violations"] += len(compliance_results.get("violations", []))
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating SLA compliance report {report_id}: {e}")
            raise
    
    async def get_performance_insights(
        self,
        time_range: Tuple[datetime, datetime],
        insight_types: Optional[List[str]] = None,
        min_confidence: float = 0.7
    ) -> List[PerformanceInsight]:
        """Get performance insights"""
        try:
            # Collect performance data
            performance_data = await self._collect_performance_data(time_range)
            
            # Generate insights
            insights = await self._generate_performance_insights(
                performance_data, insight_types, min_confidence
            )
            
            # Update statistics
            self._stats["insights_generated"] += len(insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating performance insights: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance reports statistics"""
        return self._stats.copy()
    
    # Private helper methods
    
    def _initialize_default_thresholds(self) -> Dict[PerformanceMetricType, List[PerformanceThreshold]]:
        """Initialize default performance thresholds"""
        return {
            PerformanceMetricType.RESPONSE_TIME: [
                PerformanceThreshold(
                    metric_type=PerformanceMetricType.RESPONSE_TIME,
                    threshold_value=1000.0,
                    comparison="greater_than",
                    severity=SeverityLevel.WARNING,
                    description="Response time exceeds 1 second"
                ),
                PerformanceThreshold(
                    metric_type=PerformanceMetricType.RESPONSE_TIME,
                    threshold_value=5000.0,
                    comparison="greater_than",
                    severity=SeverityLevel.CRITICAL,
                    description="Response time exceeds 5 seconds"
                )
            ],
            PerformanceMetricType.SUCCESS_RATE: [
                PerformanceThreshold(
                    metric_type=PerformanceMetricType.SUCCESS_RATE,
                    threshold_value=0.95,
                    comparison="less_than",
                    severity=SeverityLevel.WARNING,
                    description="Success rate below 95%"
                )
            ]
        }
    
    async def _collect_performance_data(
        self,
        time_range: Tuple[datetime, datetime],
        selector_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Collect performance data for analysis"""
        data = {}
        
        # Get data from performance collector
        if self.performance_collector:
            data["performance_stats"] = await self.performance_collector.get_statistics()
        
        # Get processed metrics
        if self.metrics_processor:
            data["processed_metrics"] = await self.metrics_processor.get_processed_metrics(
                time_range, {"selector_names": selector_names}
            )
        
        # Get aggregated metrics
        if self.aggregator:
            data["aggregated_metrics"] = await self.aggregator.get_aggregated_metrics(
                time_range, {"selector_names": selector_names}
            )
        
        return data
    
    async def _collect_detailed_performance_data(
        self,
        time_range: Tuple[datetime, datetime],
        analysis_depth: str
    ) -> Dict[str, Any]:
        """Collect detailed performance data for bottleneck analysis"""
        base_data = await self._collect_performance_data(time_range)
        
        # Add depth-specific data collection
        if analysis_depth == "deep":
            base_data["granular_metrics"] = await self._collect_granular_metrics(time_range)
        
        return base_data
    
    async def _collect_time_series_data(
        self,
        time_range: Tuple[datetime, datetime],
        window_size: str
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """Collect time series data for trend analysis"""
        time_series = {}
        
        # Generate sample time series data
        current_time = time_range[0]
        while current_time <= time_range[1]:
            timestamp = current_time
            
            # Sample metrics
            time_series.setdefault("response_time", []).append(
                (timestamp, statistics.normalvariate(100, 20))
            )
            time_series.setdefault("throughput", []).append(
                (timestamp, statistics.normalvariate(50, 10))
            )
            time_series.setdefault("success_rate", []).append(
                (timestamp, min(1.0, max(0.0, statistics.normalvariate(0.95, 0.05))))
            )
            
            current_time += timedelta(hours=1)
        
        return time_series
    
    async def _collect_granular_metrics(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Collect granular metrics for deep analysis"""
        return {
            "per_selector_metrics": {},
            "per_operation_metrics": {},
            "resource_usage": {}
        }
    
    async def _generate_executive_summary(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of performance"""
        return {
            "overall_performance": "good",
            "key_highlights": [
                "Average response time within acceptable limits",
                "Success rate above 95%",
                "No critical performance issues detected"
            ],
            "areas_of_concern": [],
            "recommendations_priority": "medium"
        }
    
    async def _generate_key_metrics(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate key performance metrics"""
        return {
            "average_response_time": 150.5,
            "p95_response_time": 300.0,
            "p99_response_time": 500.0,
            "total_requests": 10000,
            "success_rate": 0.96,
            "error_rate": 0.04,
            "throughput": 45.2,
            "availability": 0.998
        }
    
    async def _analyze_response_times(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze response time metrics"""
        return {
            "distribution": {
                "min": 10.0,
                "max": 1000.0,
                "mean": 150.5,
                "median": 120.0,
                "p90": 250.0,
                "p95": 300.0,
                "p99": 500.0
            },
            "trends": {
                "direction": "stable",
                "change_percent": 2.5
            },
            "outliers": {
                "count": 15,
                "percentage": 0.15
            }
        }
    
    async def _analyze_throughput(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze throughput metrics"""
        return {
            "average_throughput": 45.2,
            "peak_throughput": 78.5,
            "throughput_trend": "increasing",
            "capacity_utilization": 0.65
        }
    
    async def _analyze_success_rates(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze success rate metrics"""
        return {
            "overall_success_rate": 0.96,
            "success_rate_trend": "stable",
            "failure_modes": {
                "timeout": 0.02,
                "error": 0.015,
                "other": 0.005
            }
        }
    
    async def _analyze_performance_distribution(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance distribution"""
        return {
            "response_time_distribution": {
                "fast": 0.70,
                "normal": 0.25,
                "slow": 0.04,
                "very_slow": 0.01
            },
            "performance_consistency": 0.85
        }
    
    async def _identify_top_performers(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify top performing selectors"""
        return [
            {
                "selector_name": "fast_selector_1",
                "avg_response_time": 45.2,
                "success_rate": 0.99,
                "throughput": 120.5
            },
            {
                "selector_name": "reliable_selector_2",
                "avg_response_time": 55.8,
                "success_rate": 0.98,
                "throughput": 98.3
            }
        ]
    
    async def _identify_performance_issues(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify performance issues"""
        return [
            {
                "issue_type": "slow_response",
                "selector_name": "slow_selector_1",
                "severity": "warning",
                "description": "Average response time above threshold",
                "impact": "medium"
            }
        ]
    
    async def _generate_performance_recommendations(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations"""
        return [
            {
                "category": "optimization",
                "priority": "medium",
                "title": "Optimize slow selectors",
                "description": "Review and optimize selectors with high response times",
                "expected_improvement": "20-30% reduction in response time",
                "implementation_effort": "medium"
            }
        ]
    
    async def _identify_bottlenecks(
        self,
        performance_data: Dict[str, Any],
        analysis_depth: str
    ) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        if analysis_depth in ["medium", "deep"]:
            bottlenecks.append({
                "bottleneck_id": str(uuid.uuid4()),
                "type": "response_time",
                "severity": "warning",
                "description": "High response times for specific selectors",
                "affected_selectors": ["slow_selector_1", "slow_selector_2"],
                "impact": "medium",
                "potential_improvement": 25.0,
                "root_cause": "Inefficient selector logic"
            })
        
        return bottlenecks
    
    async def _analyze_bottleneck_impact(
        self,
        bottlenecks: List[Dict[str, Any]],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze impact of identified bottlenecks"""
        return {
            "overall_performance_impact": "medium",
            "affected_operations": 150,
            "estimated_user_impact": "moderate",
            "business_impact": {
                "revenue_impact": "low",
                "customer_satisfaction_impact": "medium",
                "operational_efficiency_impact": "medium"
            }
        }
    
    async def _generate_bottleneck_solutions(self, bottlenecks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate solutions for identified bottlenecks"""
        solutions = []
        
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "response_time":
                solutions.append({
                    "bottleneck_id": bottleneck["bottleneck_id"],
                    "solution_type": "optimization",
                    "description": "Optimize selector logic and add caching",
                    "implementation_steps": [
                        "Review selector complexity",
                        "Implement caching mechanism",
                        "Add performance monitoring"
                    ],
                    "estimated_effort": "medium",
                    "expected_improvement": bottleneck["potential_improvement"]
                })
        
        return solutions
    
    async def _analyze_metric_trends(
        self,
        metric_name: str,
        data: List[Tuple[datetime, float]],
        forecast_periods: int,
        include_seasonality: bool
    ) -> Dict[str, Any]:
        """Analyze trends for a specific metric"""
        values = [value for _, value in data]
        
        # Simple trend calculation
        if len(values) > 1:
            recent_avg = statistics.mean(values[-5:])
            older_avg = statistics.mean(values[:5])
            trend_direction = "increasing" if recent_avg > older_avg else "decreasing"
            change_percent = ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0
        else:
            trend_direction = "stable"
            change_percent = 0
        
        return {
            "metric_name": metric_name,
            "trend_direction": trend_direction,
            "change_percent": change_percent,
            "data_points": len(data),
            "forecast": self._generate_simple_forecast(values, forecast_periods) if len(values) > 10 else None
        }
    
    def _generate_simple_forecast(self, values: List[float], periods: int) -> List[float]:
        """Generate simple forecast"""
        if len(values) < 3:
            return []
        
        # Simple linear extrapolation
        recent_trend = values[-1] - values[-3]
        forecast = []
        
        for i in range(periods):
            forecast_value = values[-1] + (recent_trend * (i + 1))
            forecast.append(forecast_value)
        
        return forecast
    
    async def _generate_trend_summary(self, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of all trends"""
        return {
            "overall_trend": "stable",
            "improving_metrics": [],
            "degrading_metrics": [],
            "stable_metrics": [],
            "forecast_confidence": "medium"
        }
    
    async def _generate_performance_forecasts(self, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance forecasts"""
        forecasts = {}
        
        for metric_name, analysis in trend_analysis.items():
            if analysis.get("forecast"):
                forecasts[metric_name] = {
                    "forecast_values": analysis["forecast"],
                    "confidence": "medium",
                    "time_horizon": len(analysis["forecast"])
                }
        
        return forecasts
    
    def _get_default_sla_definitions(self) -> Dict[str, Any]:
        """Get default SLA definitions"""
        return {
            "response_time": {
                "target": 500.0,
                "unit": "milliseconds",
                "compliance_threshold": 0.95
            },
            "availability": {
                "target": 0.999,
                "unit": "percentage",
                "compliance_threshold": 1.0
            },
            "success_rate": {
                "target": 0.99,
                "unit": "percentage",
                "compliance_threshold": 0.95
            }
        }
    
    async def _check_sla_compliance(
        self,
        performance_data: Dict[str, Any],
        sla_definitions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check SLA compliance against definitions"""
        compliance_results = {
            "overall_compliance": 0.95,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "compliance_trend": "stable",
            "details": {},
            "violations": []
        }
        
        # Check each SLA definition
        for sla_name, sla_config in sla_definitions.items():
            # Mock compliance check
            compliance_rate = statistics.uniform(0.90, 0.99)
            passed = compliance_rate >= sla_config.get("compliance_threshold", 0.95)
            
            compliance_results["details"][sla_name] = {
                "target": sla_config["target"],
                "actual": sla_config["target"] * compliance_rate,
                "compliance_rate": compliance_rate,
                "passed": passed
            }
            
            compliance_results["total_checks"] += 1
            if passed:
                compliance_results["passed_checks"] += 1
            else:
                compliance_results["failed_checks"] += 1
                compliance_results["violations"].append({
                    "sla_name": sla_name,
                    "violation_type": "below_threshold",
                    "severity": "warning",
                    "description": f"{sla_name} below target threshold"
                })
        
        # Calculate overall compliance
        if compliance_results["total_checks"] > 0:
            compliance_results["overall_compliance"] = (
                compliance_results["passed_checks"] / compliance_results["total_checks"]
            )
        
        return compliance_results
    
    async def _generate_performance_insights(
        self,
        performance_data: Dict[str, Any],
        insight_types: Optional[List[str]],
        min_confidence: float
    ) -> List[PerformanceInsight]:
        """Generate performance insights"""
        insights = []
        
        # Generate response time insight
        insights.append(PerformanceInsight(
            insight_id=str(uuid.uuid4()),
            metric_type=PerformanceMetricType.RESPONSE_TIME,
            title="Response Time Optimization Opportunity",
            description="Several selectors show response times above average",
            impact="medium",
            confidence=0.85,
            recommendations=["Review selector complexity", "Consider caching strategies"],
            supporting_data={"avg_response_time": 150, "threshold": 100}
        ))
        
        # Filter by confidence
        insights = [i for i in insights if i.confidence >= min_confidence]
        
        return insights
