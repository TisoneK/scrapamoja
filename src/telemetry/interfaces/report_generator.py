"""
Report Generator Interface

Abstract interface for generating analytical reports from telemetry data
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..models import TelemetryEvent


class ReportType(Enum):
    """Report types."""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    USAGE = "usage"
    HEALTH = "health"
    TRENDS = "trends"
    SUMMARY = "summary"


class ReportFormat(Enum):
    """Report output formats."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"


class Report:
    """Report data structure."""
    
    def __init__(
        self,
        report_id: str,
        report_type: ReportType,
        title: str,
        generated_at: datetime,
        time_range: Dict[str, datetime],
        data: Dict[str, Any],
        format: ReportFormat = ReportFormat.JSON
    ):
        self.report_id = report_id
        self.report_type = report_type
        self.title = title
        self.generated_at = generated_at
        self.time_range = time_range
        self.data = data
        self.format = format


class IReportGenerator(ABC):
    """
    Interface for generating analytical reports from telemetry data.
    
    This interface defines the contract for report generation,
    including performance reports, quality reports, and analytics.
    """
    
    @abstractmethod
    async def generate_performance_report(
        self,
        start_time: datetime,
        end_time: datetime,
        selector_names: Optional[List[str]] = None,
        include_charts: bool = False
    ) -> Report:
        """
        Generate a performance report.
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            selector_names: Optional list of selectors to include
            include_charts: Whether to include chart data
            
        Returns:
            Generated performance report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def generate_quality_report(
        self,
        start_time: datetime,
        end_time: datetime,
        selector_names: Optional[List[str]] = None,
        include_trends: bool = False
    ) -> Report:
        """
        Generate a quality report.
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            selector_names: Optional list of selectors to include
            include_trends: Whether to include trend analysis
            
        Returns:
            Generated quality report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def generate_usage_report(
        self,
        start_time: datetime,
        end_time: datetime,
        group_by: str = "selector"
    ) -> Report:
        """
        Generate a usage report.
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            group_by: Grouping dimension (selector, operation_type, strategy)
            
        Returns:
            Generated usage report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def generate_health_report(
        self,
        start_time: datetime,
        end_time: datetime,
        include_alerts: bool = True
    ) -> Report:
        """
        Generate a health report.
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            include_alerts: Whether to include alert information
            
        Returns:
            Generated health report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def generate_trends_report(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: List[str],
        time_window: str = "1h"
    ) -> Report:
        """
        Generate a trends report.
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            metrics: List of metrics to analyze
            time_window: Time window for trend analysis
            
        Returns:
            Generated trends report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def generate_summary_report(
        self,
        start_time: datetime,
        end_time: datetime,
        include_recommendations: bool = True
    ) -> Report:
        """
        Generate a summary report.
        
        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            include_recommendations: Whether to include optimization recommendations
            
        Returns:
            Generated summary report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def generate_custom_report(
        self,
        report_config: Dict[str, Any]
    ) -> Report:
        """
        Generate a custom report based on configuration.
        
        Args:
            report_config: Report configuration including metrics, filters, etc.
            
        Returns:
            Generated custom report
            
        Raises:
            TelemetryReportingError: If report generation fails
        """
        pass
    
    @abstractmethod
    async def get_report(self, report_id: str) -> Optional[Report]:
        """
        Retrieve a previously generated report.
        
        Args:
            report_id: Unique report identifier
            
        Returns:
            Report if found, None otherwise
            
        Raises:
            TelemetryReportingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List available reports.
        
        Args:
            report_type: Optional report type filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Optional limit on number of reports
            
        Returns:
            List of report metadata
            
        Raises:
            TelemetryReportingError: If listing fails
        """
        pass
    
    @abstractmethod
    async def delete_report(self, report_id: str) -> bool:
        """
        Delete a report.
        
        Args:
            report_id: Unique report identifier
            
        Returns:
            True if successfully deleted, False otherwise
            
        Raises:
            TelemetryReportingError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def export_report(
        self,
        report_id: str,
        format: ReportFormat,
        output_path: Optional[str] = None
    ) -> str:
        """
        Export a report in specified format.
        
        Args:
            report_id: Unique report identifier
            format: Export format
            output_path: Optional output file path
            
        Returns:
            Path to exported file or data string
            
        Raises:
            TelemetryReportingError: If export fails
        """
        pass
    
    @abstractmethod
    async def schedule_report(
        self,
        report_config: Dict[str, Any],
        schedule: str,
        recipients: List[str]
    ) -> str:
        """
        Schedule a recurring report.
        
        Args:
            report_config: Report configuration
            schedule: Cron-like schedule string
            recipients: List of recipient email addresses
            
        Returns:
            Schedule ID
            
        Raises:
            TelemetryReportingError: If scheduling fails
        """
        pass
    
    @abstractmethod
    async def get_scheduled_reports(self) -> List[Dict[str, Any]]:
        """
        Get list of scheduled reports.
        
        Returns:
            List of scheduled report configurations
            
        Raises:
            TelemetryReportingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def cancel_scheduled_report(self, schedule_id: str) -> bool:
        """
        Cancel a scheduled report.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            True if successfully cancelled, False otherwise
            
        Raises:
            TelemetryReportingError: If cancellation fails
        """
        pass
    
    @abstractmethod
    async def get_report_statistics(self) -> Dict[str, Any]:
        """
        Get report generation statistics.
        
        Returns:
            Report statistics including counts by type, generation times, etc.
        """
        pass
    
    @abstractmethod
    async def is_reporting_enabled(self) -> bool:
        """
        Check if reporting is enabled.
        
        Returns:
            True if reporting is enabled
        """
        pass
    
    @abstractmethod
    async def enable_reporting(self) -> None:
        """
        Enable reporting.
        """
        pass
    
    @abstractmethod
    async def disable_reporting(self) -> None:
        """
        Disable reporting.
        """
        pass
    
    @abstractmethod
    async def get_report_generator_health(self) -> Dict[str, Any]:
        """
        Get report generator health status.
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def configure_report_generator(self, config: Dict[str, Any]) -> None:
        """
        Configure report generator settings.
        
        Args:
            config: Report generator configuration
        """
        pass
    
    @abstractmethod
    async def validate_report_config(self, report_config: Dict[str, Any]) -> List[str]:
        """
        Validate report configuration.
        
        Args:
            report_config: Report configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
