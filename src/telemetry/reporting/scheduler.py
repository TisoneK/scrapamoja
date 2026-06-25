"""
Report Scheduling for Selector Telemetry System

This module provides automated report scheduling capabilities including
cron-based scheduling, report distribution, and schedule management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path
import json

from ..models.selector_models import SeverityLevel
from .report_generator import ReportGenerator, ReportType, ReportFormat
from .logging import TelemetryReportingLogger, get_telemetry_logger


class ScheduleStatus(Enum):
    """Schedule status types"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleFrequency(Enum):
    """Schedule frequency types"""
    ONCE = "once"
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


@dataclass
class ScheduleConfig:
    """Report schedule configuration"""
    schedule_id: str
    name: str
    report_type: ReportType
    frequency: ScheduleFrequency
    cron_expression: Optional[str] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    filters: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    format: ReportFormat = ReportFormat.JSON
    recipients: Optional[List[str]] = None
    enabled: bool = True
    created_at: datetime = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    status: ScheduleStatus = ScheduleStatus.ACTIVE


@dataclass
class ScheduleExecution:
    """Schedule execution record"""
    execution_id: str
    schedule_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    report_id: Optional[str] = None


class ReportScheduler:
    """
    Automated report scheduling system
    
    This class provides comprehensive scheduling capabilities:
    - Cron-based scheduling
    - Report generation automation
    - Schedule management and monitoring
    - Execution history tracking
    - Error handling and retry logic
    - Report distribution
    """
    
    def __init__(
        self,
        report_generator: ReportGenerator,
        logger: Optional[TelemetryReportingLogger] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the report scheduler"""
        self.report_generator = report_generator
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Schedule storage
        self._schedules = {}
        self._executions = {}
        self._schedule_lock = asyncio.Lock()
        
        # Background task management
        self._scheduler_task = None
        self._running = False
        
        # Statistics
        self._stats = {
            "total_schedules": 0,
            "active_schedules": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0
        }
    
    async def start(self) -> None:
        """Start the report scheduler"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        self.logger.info("Report scheduler started")
    
    async def stop(self) -> None:
        """Stop the report scheduler"""
        if not self._running:
            return
        
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Report scheduler stopped")
    
    async def create_schedule(
        self,
        name: str,
        report_type: ReportType,
        frequency: ScheduleFrequency,
        cron_expression: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        filters: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        format: ReportFormat = ReportFormat.JSON,
        recipients: Optional[List[str]] = None,
        enabled: bool = True
    ) -> str:
        """
        Create a new report schedule
        
        Args:
            name: Schedule name
            report_type: Type of report to generate
            frequency: Schedule frequency
            cron_expression: Cron expression (required if frequency is CRON)
            time_range: Time range for report data
            filters: Report filters
            output_path: Output path for generated reports
            format: Report format
            recipients: Email recipients for report distribution
            enabled: Whether schedule is initially enabled
            
        Returns:
            str: Schedule ID
        """
        schedule_id = str(uuid.uuid4())
        
        # Validate cron expression if needed
        if frequency == ScheduleFrequency.CRON and not cron_expression:
            raise ValueError("Cron expression is required when frequency is CRON")
        
        # Calculate next run time
        next_run = self._calculate_next_run(frequency, cron_expression, datetime.now())
        
        # Create schedule
        schedule = ScheduleConfig(
            schedule_id=schedule_id,
            name=name,
            report_type=report_type,
            frequency=frequency,
            cron_expression=cron_expression,
            time_range=time_range,
            filters=filters,
            output_path=output_path,
            format=format,
            recipients=recipients,
            enabled=enabled,
            created_at=datetime.now(),
            next_run=next_run
        )
        
        async with self._schedule_lock:
            self._schedules[schedule_id] = schedule
            
            # Update statistics
            self._stats["total_schedules"] += 1
            if enabled:
                self._stats["active_schedules"] += 1
        
        self.logger.info(
            f"Created schedule {schedule_id}: {name}",
            schedule_id=schedule_id,
            report_type=report_type.value,
            frequency=frequency.value
        )
        
        return schedule_id
    
    async def update_schedule(
        self,
        schedule_id: str,
        **updates
    ) -> bool:
        """Update an existing schedule"""
        async with self._schedule_lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return False
            
            # Update schedule fields
            for key, value in updates.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            
            # Recalculate next run if frequency or cron changed
            if "frequency" in updates or "cron_expression" in updates:
                schedule.next_run = self._calculate_next_run(
                    schedule.frequency, schedule.cron_expression, datetime.now()
                )
            
            self.logger.info(f"Updated schedule {schedule_id}")
            return True
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule"""
        async with self._schedule_lock:
            if schedule_id not in self._schedules:
                return False
            
            schedule = self._schedules[schedule_id]
            
            # Update statistics
            if schedule.enabled:
                self._stats["active_schedules"] -= 1
            
            del self._schedules[schedule_id]
            self._stats["total_schedules"] -= 1
        
        self.logger.info(f"Deleted schedule {schedule_id}")
        return True
    
    async def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule"""
        return await self.update_schedule(schedule_id, enabled=True)
    
    async def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule"""
        return await self.update_schedule(schedule_id, enabled=False)
    
    async def run_schedule_now(self, schedule_id: str) -> str:
        """Run a schedule immediately"""
        async with self._schedule_lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                raise ValueError(f"Schedule {schedule_id} not found")
        
        execution_id = await self._execute_schedule(schedule)
        return execution_id
    
    async def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Get schedule configuration"""
        async with self._schedule_lock:
            return self._schedules.get(schedule_id)
    
    async def get_all_schedules(self) -> List[ScheduleConfig]:
        """Get all schedules"""
        async with self._schedule_lock:
            return list(self._schedules.values())
    
    async def get_schedule_executions(
        self,
        schedule_id: str,
        limit: int = 50
    ) -> List[ScheduleExecution]:
        """Get execution history for a schedule"""
        executions = [
            exec for exec in self._executions.values()
            if exec.schedule_id == schedule_id
        ]
        
        # Sort by started_at descending
        executions.sort(key=lambda x: x.started_at, reverse=True)
        
        return executions[:limit]
    
    async def get_execution(self, execution_id: str) -> Optional[ScheduleExecution]:
        """Get execution details"""
        return self._executions.get(execution_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return self._stats.copy()
    
    # Private methods
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_and_run_schedules()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _check_and_run_schedules(self) -> None:
        """Check for schedules that need to run"""
        now = datetime.now()
        schedules_to_run = []
        
        async with self._schedule_lock:
            for schedule in self._schedules.values():
                if (schedule.enabled and 
                    schedule.next_run and 
                    schedule.next_run <= now and
                    schedule.status == ScheduleStatus.ACTIVE):
                    schedules_to_run.append(schedule)
        
        # Run schedules outside of lock to avoid blocking
        for schedule in schedules_to_run:
            try:
                await self._execute_schedule(schedule)
                
                # Update next run time
                next_run = self._calculate_next_run(
                    schedule.frequency, schedule.cron_expression, now
                )
                await self.update_schedule(schedule_id=schedule.schedule_id, next_run=next_run)
                
            except Exception as e:
                self.logger.error(f"Error executing schedule {schedule.schedule_id}: {e}")
    
    async def _execute_schedule(self, schedule: ScheduleConfig) -> str:
        """Execute a schedule and generate report"""
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Create execution record
        execution = ScheduleExecution(
            execution_id=execution_id,
            schedule_id=schedule.schedule_id,
            started_at=start_time
        )
        
        self._executions[execution_id] = execution
        
        try:
            self.logger.info(
                f"Executing schedule {schedule.schedule_id}: {schedule.name}",
                execution_id=execution_id,
                schedule_id=schedule.schedule_id
            )
            
            # Generate time range if not provided
            time_range = schedule.time_range
            if not time_range:
                end_time = datetime.now()
                start_time_range = end_time - timedelta(days=1)  # Default to last 24 hours
                time_range = (start_time_range, end_time)
            
            # Generate report
            report = await self.report_generator.generate_report(
                report_type=schedule.report_type,
                time_range=time_range,
                filters=schedule.filters,
                format=schedule.format
            )
            
            # Export report if output path specified
            output_path = None
            if schedule.output_path:
                output_path = await self.report_generator.export_report(
                    report, schedule.output_path, schedule.format
                )
            
            # Update execution record
            execution.completed_at = datetime.now()
            execution.duration_ms = (execution.completed_at - execution.started_at).total_seconds() * 1000
            execution.success = True
            execution.output_path = output_path
            execution.report_id = report.metadata.report_id
            
            # Update schedule
            await self.update_schedule(
                schedule_id=schedule.schedule_id,
                last_run=execution.started_at,
                run_count=schedule.run_count + 1
            )
            
            # Update statistics
            self._stats["total_executions"] += 1
            self._stats["successful_executions"] += 1
            
            self.logger.info(
                f"Schedule execution completed: {schedule.name}",
                execution_id=execution_id,
                duration_ms=execution.duration_ms,
                output_path=output_path
            )
            
            # Distribute report if recipients specified
            if schedule.recipients:
                await self._distribute_report(report, schedule.recipients)
            
            return execution_id
            
        except Exception as e:
            # Update execution record with error
            execution.completed_at = datetime.now()
            execution.duration_ms = (execution.completed_at - execution.started_at).total_seconds() * 1000
            execution.success = False
            execution.error_message = str(e)
            
            # Update statistics
            self._stats["total_executions"] += 1
            self._stats["failed_executions"] += 1
            
            self.logger.error(
                f"Schedule execution failed: {schedule.name}",
                execution_id=execution_id,
                error=str(e)
            )
            
            raise
    
    async def _distribute_report(self, report, recipients: List[str]) -> None:
        """Distribute report to recipients"""
        # Mock distribution - in real implementation would send emails, notifications, etc.
        self.logger.info(
            f"Distributing report {report.metadata.report_id} to {len(recipients)} recipients",
            report_id=report.metadata.report_id,
            recipients=recipients
        )
    
    def _calculate_next_run(
        self,
        frequency: ScheduleFrequency,
        cron_expression: Optional[str],
        from_time: datetime
    ) -> Optional[datetime]:
        """Calculate next run time for a schedule"""
        if frequency == ScheduleFrequency.ONCE:
            return None  # One-time schedules don't have next run
        
        elif frequency == ScheduleFrequency.MINUTELY:
            return from_time + timedelta(minutes=1)
        
        elif frequency == ScheduleFrequency.HOURLY:
            return from_time + timedelta(hours=1)
        
        elif frequency == ScheduleFrequency.DAILY:
            return from_time + timedelta(days=1)
        
        elif frequency == ScheduleFrequency.WEEKLY:
            return from_time + timedelta(weeks=1)
        
        elif frequency == ScheduleFrequency.MONTHLY:
            return from_time + timedelta(days=30)
        
        elif frequency == ScheduleFrequency.CRON:
            # Mock cron parsing - in real implementation would use a cron library
            return from_time + timedelta(hours=1)
        
        return None
