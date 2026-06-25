"""
Report Generator for Selector Telemetry System

This module provides comprehensive report generation capabilities for the telemetry system,
including performance reports, usage analysis, health reports, trend analysis, and
optimization recommendations.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import uuid
from pathlib import Path

from ..models.selector_models import (
    TelemetryEvent, TelemetryEventType, MetricType, SeverityLevel
)
from ..processor.metrics_processor import MetricsProcessor, ProcessedMetric
from ..processor.aggregator import Aggregator, AggregatedMetric
from ..collector.performance_collector import PerformanceCollector, PerformanceMetrics
from ..collector.quality_collector import QualityCollector, QualityMetrics
from ..collector.strategy_collector import StrategyCollector, StrategyMetrics
from ..collector.error_collector import ErrorCollector, ErrorData
from ..collector.context_collector import ContextCollector, ContextData


class ReportType(Enum):
    """Types of reports that can be generated"""
    PERFORMANCE = "performance"
    USAGE = "usage"
    HEALTH = "health"
    TRENDS = "trends"
    RECOMMENDATIONS = "recommendations"
    DATA_QUALITY = "data_quality"
    SUMMARY = "summary"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Supported report formats"""
    JSON = "json"
    HTML = "html"
    CSV = "csv"
    MARKDOWN = "markdown"
    PDF = "pdf"


@dataclass
class ReportSection:
    """Represents a section in a report"""
    title: str
    content: Any
    metadata: Dict[str, Any]
    order: int = 0


@dataclass
class ReportMetadata:
    """Metadata for generated reports"""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    generated_by: str
    time_range: Tuple[datetime, datetime]
    data_sources: List[str]
    filters: Dict[str, Any]
    format: ReportFormat
    version: str = "1.0"


@dataclass
class GeneratedReport:
    """Represents a generated report"""
    metadata: ReportMetadata
    sections: List[ReportSection]
    summary: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None


class ReportGenerator:
    """
    Advanced report generator for telemetry data
    
    This class provides comprehensive report generation capabilities including:
    - Multiple report types and formats
    - Configurable time ranges and filters
    - Automated data processing and aggregation
    - Template-based report generation
    - Export and distribution capabilities
    """
    
    def __init__(
        self,
        metrics_processor: Optional[MetricsProcessor] = None,
        aggregator: Optional[Aggregator] = None,
        performance_collector: Optional[PerformanceCollector] = None,
        quality_collector: Optional[QualityCollector] = None,
        strategy_collector: Optional[StrategyCollector] = None,
        error_collector: Optional[ErrorCollector] = None,
        context_collector: Optional[ContextCollector] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the report generator"""
        self.metrics_processor = metrics_processor
        self.aggregator = aggregator
        self.performance_collector = performance_collector
        self.quality_collector = quality_collector
        self.strategy_collector = strategy_collector
        self.error_collector = error_collector
        self.context_collector = context_collector
        
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Report generation statistics
        self._stats = {
            "reports_generated": 0,
            "reports_by_type": {},
            "reports_by_format": {},
            "generation_times": [],
            "errors": 0
        }
        
        # Template storage
        self._templates = {}
        self._load_default_templates()
        
        # Background processing
        self._processing_lock = asyncio.Lock()
        self._background_tasks = set()
    
    async def generate_report(
        self,
        report_type: ReportType,
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]] = None,
        format: ReportFormat = ReportFormat.JSON,
        custom_template: Optional[str] = None,
        include_raw_data: bool = False
    ) -> GeneratedReport:
        """
        Generate a comprehensive report
        
        Args:
            report_type: Type of report to generate
            time_range: Time range for the report (start, end)
            filters: Optional filters to apply
            format: Output format for the report
            custom_template: Optional custom template
            include_raw_data: Whether to include raw data in the report
            
        Returns:
            GeneratedReport: The generated report
        """
        start_time = datetime.now()
        report_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Generating {report_type.value} report {report_id}")
            
            # Validate inputs
            if time_range[0] >= time_range[1]:
                raise ValueError("Invalid time range: start must be before end")
            
            # Collect and process data
            processed_data = await self._collect_and_process_data(
                report_type, time_range, filters
            )
            
            # Generate sections based on report type
            sections = await self._generate_sections(
                report_type, processed_data, time_range, filters
            )
            
            # Generate summary
            summary = await self._generate_summary(
                report_type, processed_data, sections
            )
            
            # Create metadata
            metadata = ReportMetadata(
                report_id=report_id,
                report_type=report_type,
                generated_at=start_time,
                generated_by="ReportGenerator",
                time_range=time_range,
                data_sources=self._get_data_sources(report_type),
                filters=filters or {},
                format=format
            )
            
            # Create report
            report = GeneratedReport(
                metadata=metadata,
                sections=sections,
                summary=summary,
                raw_data=processed_data if include_raw_data else None
            )
            
            # Apply formatting
            formatted_report = await self._format_report(report, format, custom_template)
            
            # Update statistics
            generation_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(report_type, format, generation_time)
            
            self.logger.info(
                f"Generated {report_type.value} report {report_id} in {generation_time:.2f}s"
            )
            
            return formatted_report
            
        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Error generating report {report_id}: {e}")
            raise
    
    async def generate_performance_report(
        self,
        time_range: Tuple[datetime, datetime],
        selector_names: Optional[List[str]] = None,
        operation_types: Optional[List[str]] = None,
        include_trends: bool = True,
        include_anomalies: bool = True
    ) -> GeneratedReport:
        """Generate a comprehensive performance report"""
        filters = {}
        if selector_names:
            filters["selector_names"] = selector_names
        if operation_types:
            filters["operation_types"] = operation_types
        filters["include_trends"] = include_trends
        filters["include_anomalies"] = include_anomalies
        
        return await self.generate_report(
            ReportType.PERFORMANCE,
            time_range,
            filters,
            ReportFormat.JSON
        )
    
    async def generate_usage_report(
        self,
        time_range: Tuple[datetime, datetime],
        group_by: str = "selector",
        include_effectiveness: bool = True,
        include_patterns: bool = True
    ) -> GeneratedReport:
        """Generate a usage analysis report"""
        filters = {
            "group_by": group_by,
            "include_effectiveness": include_effectiveness,
            "include_patterns": include_patterns
        }
        
        return await self.generate_report(
            ReportType.USAGE,
            time_range,
            filters,
            ReportFormat.JSON
        )
    
    async def generate_health_report(
        self,
        time_range: Tuple[datetime, datetime],
        include_recommendations: bool = True,
        severity_threshold: SeverityLevel = SeverityLevel.WARNING
    ) -> GeneratedReport:
        """Generate a system health report"""
        filters = {
            "include_recommendations": include_recommendations,
            "severity_threshold": severity_threshold.value
        }
        
        return await self.generate_report(
            ReportType.HEALTH,
            time_range,
            filters,
            ReportFormat.JSON
        )
    
    async def generate_trend_report(
        self,
        time_range: Tuple[datetime, datetime],
        metrics: List[str],
        trend_window: str = "7d",
        include_forecasts: bool = True
    ) -> GeneratedReport:
        """Generate a trend analysis report"""
        filters = {
            "metrics": metrics,
            "trend_window": trend_window,
            "include_forecasts": include_forecasts
        }
        
        return await self.generate_report(
            ReportType.TRENDS,
            time_range,
            filters,
            ReportFormat.JSON
        )
    
    async def generate_recommendations_report(
        self,
        time_range: Tuple[datetime, datetime],
        categories: List[str] = None,
        priority_threshold: str = "medium"
    ) -> GeneratedReport:
        """Generate optimization recommendations report"""
        filters = {
            "categories": categories or ["performance", "quality", "strategy"],
            "priority_threshold": priority_threshold
        }
        
        return await self.generate_report(
            ReportType.RECOMMENDATIONS,
            time_range,
            filters,
            ReportFormat.JSON
        )
    
    async def export_report(
        self,
        report: GeneratedReport,
        output_path: Union[str, Path],
        format: Optional[ReportFormat] = None
    ) -> str:
        """Export a report to a file"""
        output_format = format or report.metadata.format
        output_path = Path(output_path)
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Format based on type
        if output_format == ReportFormat.JSON:
            content = await self._export_to_json(report)
            output_path = output_path.with_suffix('.json')
        elif output_format == ReportFormat.HTML:
            content = await self._export_to_html(report)
            output_path = output_path.with_suffix('.html')
        elif output_format == ReportFormat.CSV:
            content = await self._export_to_csv(report)
            output_path = output_path.with_suffix('.csv')
        elif output_format == ReportFormat.MARKDOWN:
            content = await self._export_to_markdown(report)
            output_path = output_path.with_suffix('.md')
        else:
            raise ValueError(f"Unsupported export format: {output_format}")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"Exported report to {output_path}")
        return str(output_path)
    
    async def _collect_and_process_data(
        self,
        report_type: ReportType,
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Collect and process data for the report"""
        data = {}
        
        # Collect data based on report type
        if report_type in [ReportType.PERFORMANCE, ReportType.SUMMARY]:
            if self.performance_collector:
                data["performance"] = await self.performance_collector.get_statistics()
        
        if report_type in [ReportType.USAGE, ReportType.SUMMARY]:
            if self.strategy_collector:
                data["strategy"] = await self.strategy_collector.get_statistics()
        
        if report_type in [ReportType.HEALTH, ReportType.SUMMARY]:
            if self.quality_collector:
                data["quality"] = await self.quality_collector.get_statistics()
            if self.error_collector:
                data["errors"] = await self.error_collector.get_statistics()
        
        if report_type in [ReportType.TRENDS, ReportType.SUMMARY]:
            if self.metrics_processor:
                data["metrics"] = await self.metrics_processor.get_processed_metrics(
                    time_range, filters
                )
        
        if self.aggregator:
            data["aggregated"] = await self.aggregator.get_aggregated_metrics(
                time_range, filters
            )
        
        return data
    
    async def _generate_sections(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate report sections based on type"""
        sections = []
        
        if report_type == ReportType.PERFORMANCE:
            sections.extend(await self._generate_performance_sections(data, time_range, filters))
        elif report_type == ReportType.USAGE:
            sections.extend(await self._generate_usage_sections(data, time_range, filters))
        elif report_type == ReportType.HEALTH:
            sections.extend(await self._generate_health_sections(data, time_range, filters))
        elif report_type == ReportType.TRENDS:
            sections.extend(await self._generate_trend_sections(data, time_range, filters))
        elif report_type == ReportType.RECOMMENDATIONS:
            sections.extend(await self._generate_recommendations_sections(data, time_range, filters))
        elif report_type == ReportType.SUMMARY:
            sections.extend(await self._generate_summary_sections(data, time_range, filters))
        
        return sections
    
    async def _generate_performance_sections(
        self,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate performance report sections"""
        sections = []
        
        # Performance Overview
        if "performance" in data:
            sections.append(ReportSection(
                title="Performance Overview",
                content=data["performance"],
                metadata={"section_type": "overview"},
                order=1
            ))
        
        # Timing Analysis
        if "aggregated" in data:
            timing_data = self._extract_timing_data(data["aggregated"])
            sections.append(ReportSection(
                title="Timing Analysis",
                content=timing_data,
                metadata={"section_type": "timing"},
                order=2
            ))
        
        return sections
    
    async def _generate_usage_sections(
        self,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate usage report sections"""
        sections = []
        
        if "strategy" in data:
            sections.append(ReportSection(
                title="Usage Overview",
                content=data["strategy"],
                metadata={"section_type": "overview"},
                order=1
            ))
        
        return sections
    
    async def _generate_health_sections(
        self,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate health report sections"""
        sections = []
        
        health_overview = await self._generate_health_overview(data)
        sections.append(ReportSection(
            title="System Health Overview",
            content=health_overview,
            metadata={"section_type": "overview"},
            order=1
        ))
        
        return sections
    
    async def _generate_trend_sections(
        self,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate trend analysis sections"""
        sections = []
        
        trend_overview = await self._generate_trend_overview(data, filters)
        sections.append(ReportSection(
            title="Trend Overview",
            content=trend_overview,
            metadata={"section_type": "overview"},
            order=1
        ))
        
        return sections
    
    async def _generate_recommendations_sections(
        self,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate recommendations sections"""
        sections = []
        
        overview = await self._generate_recommendations_overview(data, filters)
        sections.append(ReportSection(
            title="Recommendations Overview",
            content=overview,
            metadata={"section_type": "overview"},
            order=1
        ))
        
        return sections
    
    async def _generate_summary_sections(
        self,
        data: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        filters: Optional[Dict[str, Any]]
    ) -> List[ReportSection]:
        """Generate summary report sections"""
        sections = []
        
        executive_summary = await self._generate_executive_summary(data)
        sections.append(ReportSection(
            title="Executive Summary",
            content=executive_summary,
            metadata={"section_type": "executive_summary"},
            order=1
        ))
        
        return sections
    
    async def _generate_summary(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        sections: List[ReportSection]
    ) -> Dict[str, Any]:
        """Generate a summary for the report"""
        summary = {
            "report_type": report_type.value,
            "sections_count": len(sections),
            "data_points": self._count_data_points(data),
            "generated_at": datetime.now().isoformat(),
            "key_insights": []
        }
        
        return summary
    
    async def _format_report(
        self,
        report: GeneratedReport,
        format: ReportFormat,
        custom_template: Optional[str] = None
    ) -> GeneratedReport:
        """Format the report according to the specified format"""
        if format == ReportFormat.JSON:
            return report
        elif format == ReportFormat.HTML:
            return await self._format_as_html(report, custom_template)
        elif format == ReportFormat.CSV:
            return await self._format_as_csv(report)
        elif format == ReportFormat.MARKDOWN:
            return await self._format_as_markdown(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def _format_as_html(
        self,
        report: GeneratedReport,
        custom_template: Optional[str] = None
    ) -> GeneratedReport:
        """Format report as HTML"""
        template = custom_template or self._templates.get("html", self._get_default_html_template())
        
        # Convert sections to HTML
        html_sections = []
        for section in report.sections:
            html_content = self._convert_section_to_html(section)
            html_sections.append(f"""
                <div class="report-section" data-order="{section.order}">
                    <h2>{section.title}</h2>
                    <div class="section-content">
                        {html_content}
                    </div>
                </div>
            """)
        
        # Build complete HTML
        html_content = template.format(
            title=f"{report.metadata.report_type.value.title()} Report",
            report_id=report.metadata.report_id,
            generated_at=report.metadata.generated_at.isoformat(),
            sections="".join(html_sections),
            summary=json.dumps(report.summary, indent=2)
        )
        
        # Create new report with HTML content
        html_report = GeneratedReport(
            metadata=report.metadata,
            sections=[ReportSection(
                title="HTML Report",
                content=html_content,
                metadata={"format": "html"},
                order=0
            )],
            summary=report.summary,
            raw_data=report.raw_data
        )
        
        return html_report
    
    async def _format_as_csv(self, report: GeneratedReport) -> GeneratedReport:
        """Format report as CSV"""
        csv_lines = ["Section,Title,Content,Metadata"]
        
        for section in report.sections:
            content_str = json.dumps(section.content) if isinstance(section.content, (dict, list)) else str(section.content)
            metadata_str = json.dumps(section.metadata)
            csv_lines.append(f'"{section.order}","{section.title}","{content_str}","{metadata_str}"')
        
        csv_content = "\n".join(csv_lines)
        
        csv_report = GeneratedReport(
            metadata=report.metadata,
            sections=[ReportSection(
                title="CSV Report",
                content=csv_content,
                metadata={"format": "csv"},
                order=0
            )],
            summary=report.summary,
            raw_data=report.raw_data
        )
        
        return csv_report
    
    async def _format_as_markdown(self, report: GeneratedReport) -> GeneratedReport:
        """Format report as Markdown"""
        md_lines = [
            f"# {report.metadata.report_type.value.title()} Report",
            "",
            f"**Report ID:** {report.metadata.report_id}",
            f"**Generated:** {report.metadata.generated_at}",
            f"**Time Range:** {report.metadata.time_range[0]} - {report.metadata.time_range[1]}",
            ""
        ]
        
        for section in sorted(report.sections, key=lambda s: s.order):
            md_lines.append(f"## {section.title}")
            md_lines.append("")
            
            if isinstance(section.content, dict):
                for key, value in section.content.items():
                    md_lines.append(f"**{key}:** {value}")
            elif isinstance(section.content, list):
                for item in section.content:
                    md_lines.append(f"- {item}")
            else:
                md_lines.append(str(section.content))
            
            md_lines.append("")
        
        md_content = "\n".join(md_lines)
        
        md_report = GeneratedReport(
            metadata=report.metadata,
            sections=[ReportSection(
                title="Markdown Report",
                content=md_content,
                metadata={"format": "markdown"},
                order=0
            )],
            summary=report.summary,
            raw_data=report.raw_data
        )
        
        return md_report
    
    def _get_data_sources(self, report_type: ReportType) -> List[str]:
        """Get list of data sources for a report type"""
        sources = []
        
        if self.performance_collector:
            sources.append("performance_collector")
        if self.quality_collector:
            sources.append("quality_collector")
        if self.strategy_collector:
            sources.append("strategy_collector")
        if self.error_collector:
            sources.append("error_collector")
        if self.context_collector:
            sources.append("context_collector")
        if self.metrics_processor:
            sources.append("metrics_processor")
        if self.aggregator:
            sources.append("aggregator")
        
        return sources
    
    def _update_stats(
        self,
        report_type: ReportType,
        format: ReportFormat,
        generation_time: float
    ) -> None:
        """Update generation statistics"""
        self._stats["reports_generated"] += 1
        self._stats["generation_times"].append(generation_time)
        
        type_key = report_type.value
        self._stats["reports_by_type"][type_key] = self._stats["reports_by_type"].get(type_key, 0) + 1
        
        format_key = format.value
        self._stats["reports_by_format"][format_key] = self._stats["reports_by_format"].get(format_key, 0) + 1
    
    def _count_data_points(self, data: Dict[str, Any]) -> int:
        """Count total data points in the data"""
        count = 0
        for key, value in data.items():
            if isinstance(value, list):
                count += len(value)
            elif isinstance(value, dict):
                count += len(value)
            else:
                count += 1
        return count
    
    def _load_default_templates(self) -> None:
        """Load default report templates"""
        self._templates["html"] = self._get_default_html_template()
        self._templates["markdown"] = self._get_default_markdown_template()
    
    def _get_default_html_template(self) -> str:
        """Get default HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .report-section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        .section-content {{ margin-top: 10px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p><strong>Report ID:</strong> {report_id}</p>
        <p><strong>Generated:</strong> {generated_at}</p>
    </div>
    {sections}
    <div class="summary">
        <h2>Summary</h2>
        <pre>{summary}</pre>
    </div>
</body>
</html>
        """
    
    def _get_default_markdown_template(self) -> str:
        """Get default Markdown template"""
        return """
# {title}

**Report ID:** {report_id}  
**Generated:** {generated_at}

{sections}

## Summary

{summary}
        """
    
    def _convert_section_to_html(self, section: ReportSection) -> str:
        """Convert a section to HTML"""
        if isinstance(section.content, dict):
            html = "<table>"
            for key, value in section.content.items():
                html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
            html += "</table>"
        elif isinstance(section.content, list):
            html = "<ul>"
            for item in section.content:
                html += f"<li>{item}</li>"
            html += "</ul>"
        else:
            html = f"<p>{section.content}</p>"
        
        return html
    
    # Helper methods for generating specific section content
    def _extract_timing_data(self, aggregated_data: List[AggregatedMetric]) -> Dict[str, Any]:
        """Extract timing data from aggregated metrics"""
        timing_metrics = [m for m in aggregated_data if 'timing' in m.metric_name.lower()]
        
        return {
            "average_response_time": statistics.mean([m.value for m in timing_metrics]) if timing_metrics else 0,
            "total_requests": len(timing_metrics),
            "timing_distribution": {
                "min": min([m.value for m in timing_metrics]) if timing_metrics else 0,
                "max": max([m.value for m in timing_metrics]) if timing_metrics else 0,
                "median": statistics.median([m.value for m in timing_metrics]) if timing_metrics else 0
            }
        }
    
    async def _generate_health_overview(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate health overview"""
        health_score = 85  # Placeholder calculation
        
        return {
            "overall_health_score": health_score,
            "status": "healthy" if health_score > 80 else "warning" if health_score > 60 else "critical",
            "key_indicators": {
                "error_rate": data.get("errors", {}).get("error_rate", 0),
                "quality_score": data.get("quality", {}).get("average_confidence", 0),
                "performance_score": data.get("performance", {}).get("average_response_time", 0)
            }
        }
    
    async def _generate_trend_overview(self, data: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trend overview"""
        return {
            "trend_period": filters.get("trend_window", "7d") if filters else "7d",
            "overall_trend": "stable",
            "significant_changes": []
        }
    
    async def _generate_recommendations_overview(self, data: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate recommendations overview"""
        return {
            "total_recommendations": 5,
            "priority_distribution": {"high": 1, "medium": 3, "low": 1},
            "categories": ["performance", "quality", "strategy"]
        }
    
    async def _generate_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        return {
            "overall_status": "operational",
            "key_metrics": {
                "total_operations": data.get("performance", {}).get("total_operations", 0),
                "success_rate": data.get("quality", {}).get("success_rate", 0),
                "average_response_time": data.get("performance", {}).get("average_response_time", 0)
            },
            "highlights": ["System performing within expected parameters"],
            "concerns": []
        }
    
    async def _export_to_json(self, report: GeneratedReport) -> str:
        """Export report to JSON"""
        return json.dumps(asdict(report), indent=2, default=str)
    
    async def _export_to_html(self, report: GeneratedReport) -> str:
        """Export report to HTML"""
        if report.sections and report.sections[0].metadata.get("format") == "html":
            return report.sections[0].content
        return await self._format_as_html(report).sections[0].content
    
    async def _export_to_csv(self, report: GeneratedReport) -> str:
        """Export report to CSV"""
        if report.sections and report.sections[0].metadata.get("format") == "csv":
            return report.sections[0].content
        return await self._format_as_csv(report).sections[0].content
    
    async def _export_to_markdown(self, report: GeneratedReport) -> str:
        """Export report to Markdown"""
        if report.sections and report.sections[0].metadata.get("format") == "markdown":
            return report.sections[0].content
        return await self._format_as_markdown(report).sections[0].content
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get report generation statistics"""
        stats = self._stats.copy()
        
        if stats["generation_times"]:
            stats["average_generation_time"] = statistics.mean(stats["generation_times"])
            stats["min_generation_time"] = min(stats["generation_times"])
            stats["max_generation_time"] = max(stats["generation_times"])
        
        return stats
    
    async def start_background_processing(self) -> None:
        """Start background report processing"""
        async def process_loop():
            while True:
                try:
                    # Background processing logic here
                    await asyncio.sleep(60)  # Process every minute
                except Exception as e:
                    self.logger.error(f"Background processing error: {e}")
                    await asyncio.sleep(5)
        
        task = asyncio.create_task(process_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def stop_background_processing(self) -> None:
        """Stop background report processing"""
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
