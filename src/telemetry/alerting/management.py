"""
Alert Acknowledgment and Resolution Management

Comprehensive alert lifecycle management with acknowledgment,
resolution tracking, and automated escalation capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

from ..interfaces import Alert, AlertSeverity
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class AlertStatus(Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class ResolutionMethod(Enum):
    """Resolution method types."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SYSTEM_RESTART = "system_restart"
    CONFIG_CHANGE = "config_change"
    DEPLOYMENT_FIX = "deployment_fix"
    TEMPORARY_WORKAROUND = "temporary_workaround"
    FALSE_POSITIVE = "false_positive"


class EscalationLevel(Enum):
    """Escalation level enumeration."""
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    CRITICAL = "critical"


@dataclass
class Acknowledgment:
    """Alert acknowledgment information."""
    acknowledgment_id: str
    alert_id: str
    acknowledged_by: str
    acknowledged_at: datetime
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None


@dataclass
class Resolution:
    """Alert resolution information."""
    resolution_id: str
    alert_id: str
    resolved_by: str
    resolved_at: datetime
    method: ResolutionMethod
    notes: Optional[str] = None
    root_cause: Optional[str] = None
    prevention_measures: Optional[List[str]] = None
    resolution_time_minutes: Optional[float] = None


@dataclass
class EscalationRule:
    """Alert escalation rule."""
    rule_id: str
    name: str
    description: str
    severity_filter: List[AlertSeverity]
    time_threshold_minutes: int
    escalation_level: EscalationLevel
    escalation_targets: List[str]
    auto_escalate: bool = True
    notification_template: Optional[str] = None
    enabled: bool = True


@dataclass
class AlertLifecycle:
    """Complete alert lifecycle information."""
    alert_id: str
    created_at: datetime
    status: AlertStatus
    severity: AlertSeverity
    acknowledgments: List[Acknowledgment] = field(default_factory=list)
    resolutions: List[Resolution] = field(default_factory=list)
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    status_changes: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ManagementStatistics:
    """Alert management statistics."""
    total_alerts: int = 0
    alerts_by_status: Dict[str, int] = field(default_factory=dict)
    alerts_by_severity: Dict[str, int] = field(default_factory=dict)
    average_resolution_time_minutes: float = 0.0
    average_acknowledgment_time_minutes: float = 0.0
    resolution_rate: float = 0.0
    acknowledgment_rate: float = 0.0
    escalations_triggered: int = 0
    most_common_resolution_method: str = ""
    last_action: Optional[datetime] = None


class AlertManager:
    """
    Comprehensive alert lifecycle management system.
    
    Provides alert acknowledgment, resolution tracking, escalation,
    and automated lifecycle management.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize alert manager.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("alert_manager")
        
        # Manager configuration
        self.enabled = config.get("alert_management_enabled", True)
        self.auto_acknowledge_timeout = config.get("auto_acknowledge_timeout_minutes", 60)
        self.auto_escalation_enabled = config.get("auto_escalation_enabled", True)
        
        # Storage
        self._alert_lifecycles: Dict[str, AlertLifecycle] = {}
        self._escalation_rules: Dict[str, EscalationRule] = {}
        self._management_lock = asyncio.Lock()
        
        # Callbacks
        self._acknowledgment_callbacks: List[Callable] = []
        self._resolution_callbacks: List[Callable] = []
        self._escalation_callbacks: List[Callable] = []
        
        # Statistics
        self._statistics = ManagementStatistics()
        
        # Background tasks
        self._escalation_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Initialize default escalation rules
        self._initialize_default_escalation_rules()
        
        # Start background tasks
        if self.enabled:
            self._start_background_tasks()
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
        notes: Optional[str] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: Who is acknowledging
            notes: Optional acknowledgment notes
            assigned_to: Optional assignment
            priority: Optional priority level
            due_date: Optional due date
            
        Returns:
            True if successfully acknowledged
        """
        try:
            async with self._management_lock:
                if alert_id not in self._alert_lifecycles:
                    return False
                
                lifecycle = self._alert_lifecycles[alert_id]
                
                # Create acknowledgment
                acknowledgment = Acknowledgment(
                    acknowledgment_id=f"ack_{alert_id}_{int(datetime.utcnow().timestamp())}",
                    alert_id=alert_id,
                    acknowledged_by=acknowledged_by,
                    acknowledged_at=datetime.utcnow(),
                    notes=notes,
                    assigned_to=assigned_to,
                    priority=priority,
                    due_date=due_date
                )
                
                # Update lifecycle
                lifecycle.acknowledgments.append(acknowledgment)
                lifecycle.status = AlertStatus.ACKNOWLEDGED
                lifecycle.last_updated = datetime.utcnow()
                
                # Record status change
                lifecycle.status_changes.append({
                    "from_status": AlertStatus.ACTIVE.value,
                    "to_status": AlertStatus.ACKNOWLEDGED.value,
                    "timestamp": datetime.utcnow(),
                    "changed_by": acknowledged_by,
                    "reason": "Manual acknowledgment"
                })
                
                # Update statistics
                self._update_acknowledgment_statistics(lifecycle)
                
                # Execute callbacks
                await self._execute_acknowledgment_callbacks(acknowledgment)
                
                self.logger.info(
                    "Alert acknowledged",
                    alert_id=alert_id,
                    acknowledged_by=acknowledged_by,
                    assigned_to=assigned_to
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to acknowledge alert",
                alert_id=alert_id,
                error=str(e)
            )
            return False
    
    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        method: ResolutionMethod,
        notes: Optional[str] = None,
        root_cause: Optional[str] = None,
        prevention_measures: Optional[List[str]] = None
    ) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID to resolve
            resolved_by: Who is resolving
            method: Resolution method
            notes: Optional resolution notes
            root_cause: Optional root cause analysis
            prevention_measures: Optional prevention measures
            
        Returns:
            True if successfully resolved
        """
        try:
            async with self._management_lock:
                if alert_id not in self._alert_lifecycles:
                    return False
                
                lifecycle = self._alert_lifecycles[alert_id]
                
                # Calculate resolution time
                resolution_time = None
                if lifecycle.acknowledgments:
                    last_acknowledgment = max(lifecycle.acknowledgments, key=lambda x: x.acknowledged_at)
                    resolution_time = (datetime.utcnow() - last_acknowledgment.acknowledged_at).total_seconds() / 60
                else:
                    resolution_time = (datetime.utcnow() - lifecycle.created_at).total_seconds() / 60
                
                # Create resolution
                resolution = Resolution(
                    resolution_id=f"res_{alert_id}_{int(datetime.utcnow().timestamp())}",
                    alert_id=alert_id,
                    resolved_by=resolved_by,
                    resolved_at=datetime.utcnow(),
                    method=method,
                    notes=notes,
                    root_cause=root_cause,
                    prevention_measures=prevention_measures,
                    resolution_time_minutes=resolution_time
                )
                
                # Update lifecycle
                lifecycle.resolutions.append(resolution)
                lifecycle.status = AlertStatus.RESOLVED
                lifecycle.last_updated = datetime.utcnow()
                
                # Record status change
                from_status = lifecycle.status_changes[-1]["to_status"] if lifecycle.status_changes else AlertStatus.ACTIVE.value
                lifecycle.status_changes.append({
                    "from_status": from_status,
                    "to_status": AlertStatus.RESOLVED.value,
                    "timestamp": datetime.utcnow(),
                    "changed_by": resolved_by,
                    "reason": f"Resolution via {method.value}"
                })
                
                # Update statistics
                self._update_resolution_statistics(lifecycle)
                
                # Execute callbacks
                await self._execute_resolution_callbacks(resolution)
                
                self.logger.info(
                    "Alert resolved",
                    alert_id=alert_id,
                    resolved_by=resolved_by,
                    method=method.value,
                    resolution_time_minutes=resolution_time
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to resolve alert",
                alert_id=alert_id,
                error=str(e)
            )
            return False
    
    async def escalate_alert(
        self,
        alert_id: str,
        escalation_level: EscalationLevel,
        escalated_by: str,
        targets: List[str],
        reason: Optional[str] = None
    ) -> bool:
        """
        Escalate an alert.
        
        Args:
            alert_id: Alert ID to escalate
            escalation_level: Escalation level
            escalated_by: Who is escalating
            targets: Escalation targets
            reason: Optional escalation reason
            
        Returns:
            True if successfully escalated
        """
        try:
            async with self._management_lock:
                if alert_id not in self._alert_lifecycles:
                    return False
                
                lifecycle = self._alert_lifecycles[alert_id]
                
                # Record escalation
                escalation = {
                    "escalation_id": f"esc_{alert_id}_{int(datetime.utcnow().timestamp())}",
                    "escalation_level": escalation_level.value,
                    "escalated_by": escalated_by,
                    "escalated_at": datetime.utcnow(),
                    "targets": targets,
                    "reason": reason or f"Manual escalation to {escalation_level.value}"
                }
                
                lifecycle.escalations.append(escalation)
                lifecycle.status = AlertStatus.ESCALATED
                lifecycle.last_updated = datetime.utcnow()
                
                # Record status change
                from_status = lifecycle.status_changes[-1]["to_status"] if lifecycle.status_changes else AlertStatus.ACTIVE.value
                lifecycle.status_changes.append({
                    "from_status": from_status,
                    "to_status": AlertStatus.ESCALATED.value,
                    "timestamp": datetime.utcnow(),
                    "changed_by": escalated_by,
                    "reason": reason
                })
                
                # Update statistics
                self._statistics.escalations_triggered += 1
                
                # Execute callbacks
                await self._execute_escalation_callbacks(escalation)
                
                self.logger.warning(
                    "Alert escalated",
                    alert_id=alert_id,
                    escalation_level=escalation_level.value,
                    escalated_by=escalated_by,
                    targets=targets
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to escalate alert",
                alert_id=alert_id,
                error=str(e)
            )
            return False
    
    async def get_alert_lifecycle(self, alert_id: str) -> Optional[AlertLifecycle]:
        """
        Get complete lifecycle for an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Alert lifecycle or None if not found
        """
        try:
            async with self._management_lock:
                return self._alert_lifecycles.get(alert_id)
                
        except Exception as e:
            self.logger.error(
                "Failed to get alert lifecycle",
                alert_id=alert_id,
                error=str(e)
            )
            return None
    
    async def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        assigned_to: Optional[str] = None,
        overdue_only: bool = False
    ) -> List[AlertLifecycle]:
        """
        Get active alerts with filtering.
        
        Args:
            severity: Optional severity filter
            assigned_to: Optional assignment filter
            overdue_only: Filter for overdue alerts only
            
        Returns:
            List of active alert lifecycles
        """
        try:
            async with self._management_lock:
                active_alerts = []
                
                for lifecycle in self._alert_lifecycles.values():
                    if lifecycle.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS, AlertStatus.ESCALATED]:
                        # Apply filters
                        if severity and lifecycle.severity != severity:
                            continue
                        
                        if assigned_to:
                            assigned = False
                            for ack in lifecycle.acknowledgments:
                                if ack.assigned_to == assigned_to:
                                    assigned = True
                                    break
                            if not assigned:
                                continue
                        
                        if overdue_only:
                            overdue = False
                            for ack in lifecycle.acknowledgments:
                                if ack.due_date and datetime.utcnow() > ack.due_date:
                                    overdue = True
                                    break
                            if not overdue:
                                continue
                        
                        active_alerts.append(lifecycle)
                
                # Sort by last updated (newest first)
                active_alerts.sort(key=lambda x: x.last_updated, reverse=True)
                
                return active_alerts
                
        except Exception as e:
            self.logger.error(
                "Failed to get active alerts",
                error=str(e)
            )
            return []
    
    async def get_management_statistics(self) -> Dict[str, Any]:
        """
        Get alert management statistics.
        
        Returns:
            Management statistics
        """
        try:
            async with self._management_lock:
                return {
                    "total_alerts": self._statistics.total_alerts,
                    "alerts_by_status": dict(self._statistics.alerts_by_status),
                    "alerts_by_severity": dict(self._statistics.alerts_by_severity),
                    "average_resolution_time_minutes": self._statistics.average_resolution_time_minutes,
                    "average_acknowledgment_time_minutes": self._statistics.average_acknowledgment_time_minutes,
                    "resolution_rate": self._statistics.resolution_rate,
                    "acknowledgment_rate": self._statistics.acknowledgment_rate,
                    "escalations_triggered": self._statistics.escalations_triggered,
                    "most_common_resolution_method": self._statistics.most_common_resolution_method,
                    "last_action": self._statistics.last_action,
                    "active_alerts": len([
                        lifecycle for lifecycle in self._alert_lifecycles.values()
                        if lifecycle.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS, AlertStatus.ESCALATED]
                    ]),
                    "escalation_rules": len(self._escalation_rules),
                    "enabled_escalation_rules": len([r for r in self._escalation_rules.values() if r.enabled])
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get management statistics",
                error=str(e)
            )
            return {}
    
    async def add_escalation_rule(self, rule: EscalationRule) -> bool:
        """
        Add an escalation rule.
        
        Args:
            rule: Escalation rule to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._management_lock:
                self._escalation_rules[rule.rule_id] = rule
            
            self.logger.info(
                "Escalation rule added",
                rule_id=rule.rule_id,
                escalation_level=rule.escalation_level.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add escalation rule",
                rule_id=rule.rule_id,
                error=str(e)
            )
            return False
    
    async def remove_escalation_rule(self, rule_id: str) -> bool:
        """
        Remove an escalation rule.
        
        Args:
            rule_id: Rule ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._management_lock:
                if rule_id in self._escalation_rules:
                    del self._escalation_rules[rule_id]
                    
                    self.logger.info(
                        "Escalation rule removed",
                        rule_id=rule_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove escalation rule",
                rule_id=rule_id,
                error=str(e)
            )
            return False
    
    def add_acknowledgment_callback(self, callback: Callable) -> None:
        """
        Add callback for alert acknowledgments.
        
        Args:
            callback: Callback function
        """
        self._acknowledgment_callbacks.append(callback)
    
    def add_resolution_callback(self, callback: Callable) -> None:
        """
        Add callback for alert resolutions.
        
        Args:
            callback: Callback function
        """
        self._resolution_callbacks.append(callback)
    
    def add_escalation_callback(self, callback: Callable) -> None:
        """
        Add callback for alert escalations.
        
        Args:
            callback: Callback function
        """
        self._escalation_callbacks.append(callback)
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._shutdown_event.set()
        
        if self._escalation_task:
            self._escalation_task.cancel()
            try:
                await self._escalation_task
            except asyncio.CancelledError:
                pass
    
    # Private methods
    
    def _initialize_default_escalation_rules(self) -> None:
        """Initialize default escalation rules."""
        default_rules = [
            EscalationRule(
                rule_id="critical_5min",
                name="Critical Alert 5 Minute Escalation",
                description="Escalate critical alerts after 5 minutes",
                severity_filter=[AlertSeverity.CRITICAL],
                time_threshold_minutes=5,
                escalation_level=EscalationLevel.LEVEL_1,
                escalation_targets=["team_lead", "on_call_engineer"],
                auto_escalate=True
            ),
            EscalationRule(
                rule_id="error_15min",
                name="Error Alert 15 Minute Escalation",
                description="Escalate error alerts after 15 minutes",
                severity_filter=[AlertSeverity.ERROR],
                time_threshold_minutes=15,
                escalation_level=EscalationLevel.LEVEL_1,
                escalation_targets=["team_lead"],
                auto_escalate=True
            ),
            EscalationRule(
                rule_id="warning_30min",
                name="Warning Alert 30 Minute Escalation",
                description="Escalate warning alerts after 30 minutes",
                severity_filter=[AlertSeverity.WARNING],
                time_threshold_minutes=30,
                escalation_level=EscalationLevel.LEVEL_1,
                escalation_targets=["team_member"],
                auto_escalate=True
            ),
            EscalationRule(
                rule_id="critical_15min_level2",
                name="Critical Alert 15 Minute Level 2 Escalation",
                description="Escalate critical alerts to level 2 after 15 minutes",
                severity_filter=[AlertSeverity.CRITICAL],
                time_threshold_minutes=15,
                escalation_level=EscalationLevel.LEVEL_2,
                escalation_targets=["manager", "director"],
                auto_escalate=True
            )
        ]
        
        for rule in default_rules:
            self._escalation_rules[rule.rule_id] = rule
    
    def _start_background_tasks(self) -> None:
        """Start background tasks for automatic processing."""
        if self.auto_escalation_enabled:
            self._escalation_task = asyncio.create_task(self._escalation_monitoring_loop())
    
    async def _escalation_monitoring_loop(self) -> None:
        """Background loop for automatic escalation monitoring."""
        while not self._shutdown_event.is_set():
            try:
                # Check for escalations every minute
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=60.0
                )
                
                if self._shutdown_event.is_set():
                    break
                
                await self._check_automatic_escalations()
                
            except asyncio.TimeoutError:
                # Timeout - continue with next iteration
                continue
            except Exception as e:
                self.logger.error(
                    "Escalation monitoring loop error",
                    error=str(e)
                )
                await asyncio.sleep(10.0)  # Brief pause before retrying
    
    async def _check_automatic_escalations(self) -> None:
        """Check for automatic escalations."""
        try:
            async with self._management_lock:
                current_time = datetime.utcnow()
                
                for lifecycle in self._alert_lifecycles.values():
                    # Skip resolved alerts
                    if lifecycle.status == AlertStatus.RESOLVED:
                        continue
                    
                    # Check each escalation rule
                    for rule in self._escalation_rules.values():
                        if not rule.enabled:
                            continue
                        
                        # Check severity filter
                        if lifecycle.severity not in rule.severity_filter:
                            continue
                        
                        # Check if already escalated to this level or higher
                        current_level = self._get_current_escalation_level(lifecycle)
                        if self._is_higher_or_equal_level(current_level, rule.escalation_level):
                            continue
                        
                        # Check time threshold
                        alert_age = (current_time - lifecycle.created_at).total_seconds() / 60
                        
                        if alert_age >= rule.time_threshold_minutes:
                            # Auto-escalate
                            await self.escalate_alert(
                                lifecycle.alert_id,
                                rule.escalation_level,
                                "system",
                                rule.escalation_targets,
                                f"Automatic escalation after {rule.time_threshold_minutes} minutes"
                            )
                
        except Exception as e:
            self.logger.error(
                "Failed to check automatic escalations",
                error=str(e)
            )
    
    def _get_current_escalation_level(self, lifecycle: AlertLifecycle) -> Optional[EscalationLevel]:
        """Get current escalation level for alert."""
        if not lifecycle.escalations:
            return None
        
        latest_escalation = max(lifecycle.escalations, key=lambda x: x["escalated_at"])
        return EscalationLevel(latest_escalation["escalation_level"])
    
    def _is_higher_or_equal_level(self, current: Optional[EscalationLevel], target: EscalationLevel) -> bool:
        """Check if current level is higher or equal to target."""
        if current is None:
            return False
        
        level_order = {
            EscalationLevel.LEVEL_1: 1,
            EscalationLevel.LEVEL_2: 2,
            EscalationLevel.LEVEL_3: 3,
            EscalationLevel.CRITICAL: 4
        }
        
        return level_order.get(current, 0) >= level_order.get(target, 0)
    
    def _update_acknowledgment_statistics(self, lifecycle: AlertLifecycle) -> None:
        """Update acknowledgment statistics."""
        if lifecycle.acknowledgments:
            total_alerts = self._statistics.total_alerts
            acknowledged_alerts = len([
                l for l in self._alert_lifecycles.values()
                if l.acknowledgments
            ])
            
            if total_alerts > 0:
                self._statistics.acknowledgment_rate = acknowledged_alerts / total_alerts
            
            # Update average acknowledgment time
            total_ack_time = 0
            ack_count = 0
            
            for l in self._alert_lifecycles.values():
                if l.acknowledgments:
                    first_ack = min(l.acknowledgments, key=lambda x: x.acknowledged_at)
                    ack_time = (first_ack.acknowledged_at - l.created_at).total_seconds() / 60
                    total_ack_time += ack_time
                    ack_count += 1
            
            if ack_count > 0:
                self._statistics.average_acknowledgment_time_minutes = total_ack_time / ack_count
    
    def _update_resolution_statistics(self, lifecycle: AlertLifecycle) -> None:
        """Update resolution statistics."""
        if lifecycle.resolutions:
            total_alerts = self._statistics.total_alerts
            resolved_alerts = len([
                l for l in self._alert_lifecycles.values()
                if l.resolutions
            ])
            
            if total_alerts > 0:
                self._statistics.resolution_rate = resolved_alerts / total_alerts
            
            # Update average resolution time
            total_res_time = 0
            res_count = 0
            
            for l in self._alert_lifecycles.values():
                if l.resolutions:
                    for resolution in l.resolutions:
                        if resolution.resolution_time_minutes:
                            total_res_time += resolution.resolution_time_minutes
                            res_count += 1
            
            if res_count > 0:
                self._statistics.average_resolution_time_minutes = total_res_time / res_count
            
            # Update most common resolution method
            method_counts = defaultdict(int)
            for l in self._alert_lifecycles.values():
                for resolution in l.resolutions:
                    method_counts[resolution.method.value] += 1
            
            if method_counts:
                self._statistics.most_common_resolution_method = max(
                    method_counts,
                    key=method_counts.get
                )
    
    async def _execute_acknowledgment_callbacks(self, acknowledgment: Acknowledgment) -> None:
        """Execute acknowledgment callbacks."""
        for callback in self._acknowledgment_callbacks:
            try:
                await callback(acknowledgment)
            except Exception as e:
                self.logger.error(
                    "Acknowledgment callback failed",
                    acknowledgment_id=acknowledgment.acknowledgment_id,
                    error=str(e)
                )
    
    async def _execute_resolution_callbacks(self, resolution: Resolution) -> None:
        """Execute resolution callbacks."""
        for callback in self._resolution_callbacks:
            try:
                await callback(resolution)
            except Exception as e:
                self.logger.error(
                    "Resolution callback failed",
                    resolution_id=resolution.resolution_id,
                    error=str(e)
                )
    
    async def _execute_escalation_callbacks(self, escalation: Dict[str, Any]) -> None:
        """Execute escalation callbacks."""
        for callback in self._escalation_callbacks:
            try:
                await callback(escalation)
            except Exception as e:
                self.logger.error(
                    "Escalation callback failed",
                    escalation_id=escalation["escalation_id"],
                    error=str(e)
                )
