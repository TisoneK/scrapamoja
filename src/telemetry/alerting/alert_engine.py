"""
Alert Engine

Core alerting engine for real-time monitoring, threshold evaluation,
and alert generation with severity classification and notification.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

from ..interfaces import IAlertEngine, Alert, AlertSeverity, AlertType
from ..models import TelemetryEvent, PerformanceMetrics, QualityMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class AlertStatus(Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: str  # Expression language condition
    threshold: Dict[str, Any]
    enabled: bool = True
    cooldown_minutes: int = 5
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class AlertStatistics:
    """Alert engine statistics."""
    total_alerts: int = 0
    alerts_by_type: Dict[str, int] = field(default_factory=dict)
    alerts_by_severity: Dict[str, int] = field(default_factory=dict)
    alerts_by_status: Dict[str, int] = field(default_factory=dict)
    average_resolution_time_minutes: float = 0.0
    false_positive_rate: float = 0.0
    most_common_alert_type: str = ""
    most_common_severity: str = ""
    last_alert: Optional[datetime] = None


class AlertEngine(IAlertEngine):
    """
    Core alerting engine for real-time monitoring and alert generation.
    
    Provides comprehensive alerting with threshold evaluation,
    severity classification, and notification management.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize alert engine.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("alert_engine")
        
        # Alert configuration
        self.enabled = config.get("alerting_enabled", True)
        self.max_alerts = config.get("max_alerts", 10000)
        self.default_cooldown_minutes = config.get("alert_cooldown_minutes", 5)
        
        # Alert storage
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alerts_lock = asyncio.Lock()
        
        # Alert callbacks
        self._alert_callbacks: List[Callable] = []
        self._resolution_callbacks: List[Callable] = []
        
        # Statistics
        self._statistics = AlertStatistics()
        
        # Initialize default rules
        self._initialize_default_rules()
    
    async def evaluate_event(self, event: TelemetryEvent) -> List[Alert]:
        """
        Evaluate a telemetry event for alert conditions.
        
        Args:
            event: TelemetryEvent to evaluate
            
        Returns:
            List of generated alerts
            
        Raises:
            TelemetryAlertingError: If evaluation fails
        """
        if not self.enabled:
            return []
        
        try:
            generated_alerts = []
            
            async with self._alerts_lock:
                # Evaluate against all enabled rules
                for rule in self._alert_rules.values():
                    if not rule.enabled:
                        continue
                    
                    # Check cooldown
                    if self._is_in_cooldown(rule):
                        continue
                    
                    # Evaluate rule condition
                    if await self._evaluate_rule(rule, event):
                        alert = await self._create_alert(rule, event)
                        
                        # Add to active alerts
                        self._active_alerts[alert.alert_id] = alert
                        self._alert_history.append(alert)
                        
                        # Update rule statistics
                        rule.last_triggered = datetime.utcnow()
                        rule.trigger_count += 1
                        
                        # Update engine statistics
                        self._update_statistics(alert)
                        
                        generated_alerts.append(alert)
                        
                        # Execute callbacks
                        await self._execute_alert_callbacks(alert)
                        
                        self.logger.info(
                            "Alert generated",
                            alert_id=alert.alert_id,
                            rule_name=rule.name,
                            severity=alert.severity.value,
                            selector_name=event.selector_name
                        )
            
            # Limit history size
            await self._limit_alert_history()
            
            return generated_alerts
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate event for alerts",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to evaluate event: {e}",
                error_code="TEL-801"
            )
    
    async def evaluate_threshold(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        comparison: str = "greater_than",
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Alert]:
        """
        Evaluate a threshold condition and generate alert if needed.
        
        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            threshold_value: Threshold value
            comparison: Comparison type (greater_than, less_than, equals)
            context: Additional context for the alert
            
        Returns:
            Generated alert or None if threshold not exceeded
            
        Raises:
            TelemetryAlertingError: If evaluation fails
        """
        try:
            if not self.enabled:
                return None
            
            # Check threshold condition
            triggered = False
            
            if comparison == "greater_than":
                triggered = current_value > threshold_value
            elif comparison == "less_than":
                triggered = current_value < threshold_value
            elif comparison == "equals":
                triggered = abs(current_value - threshold_value) < 0.001
            elif comparison == "greater_equal":
                triggered = current_value >= threshold_value
            elif comparison == "less_equal":
                triggered = current_value <= threshold_value
            else:
                self.logger.warning(f"Unknown comparison type: {comparison}")
                return None
            
            if not triggered:
                return None
            
            # Determine severity based on how much threshold is exceeded
            severity = self._determine_threshold_severity(
                metric_name, current_value, threshold_value, comparison
            )
            
            # Create alert
            alert_id = f"threshold_{metric_name}_{int(datetime.utcnow().timestamp())}"
            
            alert = Alert(
                alert_id=alert_id,
                alert_type=AlertType.THRESHOLD,
                severity=severity,
                title=f"Threshold Exceeded: {metric_name}",
                message=f"{metric_name} value {current_value} exceeds threshold {threshold_value}",
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                comparison=comparison,
                context=context or {},
                timestamp=datetime.utcnow(),
                status=AlertStatus.ACTIVE
            )
            
            # Add to storage
            async with self._alerts_lock:
                self._active_alerts[alert_id] = alert
                self._alert_history.append(alert)
                self._update_statistics(alert)
            
            # Execute callbacks
            await self._execute_alert_callbacks(alert)
            
            self.logger.warning(
                "Threshold alert generated",
                alert_id=alert_id,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                severity=severity.value
            )
            
            return alert
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate threshold",
                metric_name=metric_name,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to evaluate threshold: {e}",
                error_code="TEL-802"
            )
    
    async def create_manual_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        alert_type: AlertType = AlertType.MANUAL,
        context: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Create a manual alert.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            alert_type: Type of alert
            context: Additional context
            
        Returns:
            Created alert
            
        Raises:
            TelemetryAlertingError: If creation fails
        """
        try:
            alert_id = f"manual_{int(datetime.utcnow().timestamp())}"
            
            alert = Alert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                context=context or {},
                timestamp=datetime.utcnow(),
                status=AlertStatus.ACTIVE
            )
            
            async with self._alerts_lock:
                self._active_alerts[alert_id] = alert
                self._alert_history.append(alert)
                self._update_statistics(alert)
            
            await self._execute_alert_callbacks(alert)
            
            self.logger.info(
                "Manual alert created",
                alert_id=alert_id,
                title=title,
                severity=severity.value
            )
            
            return alert
            
        except Exception as e:
            self.logger.error(
                "Failed to create manual alert",
                title=title,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to create manual alert: {e}",
                error_code="TEL-803"
            )
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: Optional[str] = None) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: Who acknowledged the alert
            notes: Optional acknowledgment notes
            
        Returns:
            True if successfully acknowledged
            
        Raises:
            TelemetryAlertingError: If acknowledgment fails
        """
        try:
            async with self._alerts_lock:
                if alert_id not in self._active_alerts:
                    return False
                
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                alert.acknowledgment_notes = notes
            
            self.logger.info(
                "Alert acknowledged",
                alert_id=alert_id,
                acknowledged_by=acknowledged_by
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to acknowledge alert",
                alert_id=alert_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to acknowledge alert: {e}",
                error_code="TEL-804"
            )
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: Optional[str] = None) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID
            resolved_by: Who resolved the alert
            resolution_notes: Optional resolution notes
            
        Returns:
            True if successfully resolved
            
        Raises:
            TelemetryAlertingError: If resolution fails
        """
        try:
            async with self._alerts_lock:
                alert = None
                
                # Check active alerts first
                if alert_id in self._active_alerts:
                    alert = self._active_alerts.pop(alert_id)
                else:
                    # Check if alert exists in history
                    for hist_alert in reversed(self._alert_history):
                        if hist_alert.alert_id == alert_id:
                            alert = hist_alert
                            break
                
                if not alert:
                    return False
                
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = resolved_by
                alert.resolution_notes = resolution_notes
                
                # Calculate resolution time
                if alert.acknowledged_at:
                    resolution_time = alert.resolved_at - alert.acknowledged_at
                    alert.resolution_time_minutes = resolution_time.total_seconds() / 60
                else:
                    resolution_time = alert.resolved_at - alert.timestamp
                    alert.resolution_time_minutes = resolution_time.total_seconds() / 60
                
                # Update statistics
                self._update_resolution_statistics(alert)
            
            # Execute resolution callbacks
            await self._execute_resolution_callbacks(alert)
            
            self.logger.info(
                "Alert resolved",
                alert_id=alert_id,
                resolved_by=resolved_by,
                resolution_time_minutes=getattr(alert, 'resolution_time_minutes', 0)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to resolve alert",
                alert_id=alert_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to resolve alert: {e}",
                error_code="TEL-805"
            )
    
    async def suppress_alert(self, alert_id: str, duration_minutes: int, reason: Optional[str] = None) -> bool:
        """
        Suppress an alert for a duration.
        
        Args:
            alert_id: Alert ID
            duration_minutes: Duration to suppress in minutes
            reason: Optional reason for suppression
            
        Returns:
            True if successfully suppressed
            
        Raises:
            TelemetryAlertingError: If suppression fails
        """
        try:
            async with self._alerts_lock:
                if alert_id not in self._active_alerts:
                    return False
                
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.SUPPRESSED
                alert.suppressed_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
                alert.suppression_reason = reason
            
            self.logger.info(
                "Alert suppressed",
                alert_id=alert_id,
                duration_minutes=duration_minutes,
                reason=reason
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to suppress alert",
                alert_id=alert_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to suppress alert: {e}",
                error_code="TEL-806"
            )
    
    async def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        limit: Optional[int] = None
    ) -> List[Alert]:
        """
        Get active alerts with optional filtering.
        
        Args:
            severity: Optional severity filter
            alert_type: Optional alert type filter
            limit: Optional limit on number of alerts
            
        Returns:
            List of active alerts
        """
        try:
            async with self._alerts_lock:
                alerts = list(self._active_alerts.values())
                
                # Apply filters
                if severity:
                    alerts = [alert for alert in alerts if alert.severity == severity]
                
                if alert_type:
                    alerts = [alert for alert in alerts if alert.alert_type == alert_type]
                
                # Sort by timestamp (newest first)
                alerts.sort(key=lambda x: x.timestamp, reverse=True)
                
                # Apply limit
                if limit:
                    alerts = alerts[:limit]
                
                return alerts
                
        except Exception as e:
            self.logger.error(
                "Failed to get active alerts",
                error=str(e)
            )
            return []
    
    async def get_alert_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        status: Optional[AlertStatus] = None,
        limit: Optional[int] = None
    ) -> List[Alert]:
        """
        Get alert history with filtering.
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            severity: Optional severity filter
            alert_type: Optional alert type filter
            status: Optional status filter
            limit: Optional limit on number of alerts
            
        Returns:
            List of alerts from history
        """
        try:
            async with self._alerts_lock:
                alerts = self._alert_history.copy()
                
                # Apply time filters
                if start_time:
                    alerts = [alert for alert in alerts if alert.timestamp >= start_time]
                
                if end_time:
                    alerts = [alert for alert in alerts if alert.timestamp <= end_time]
                
                # Apply other filters
                if severity:
                    alerts = [alert for alert in alerts if alert.severity == severity]
                
                if alert_type:
                    alerts = [alert for alert in alerts if alert.alert_type == alert_type]
                
                if status:
                    alerts = [alert for alert in alerts if alert.status == status]
                
                # Sort by timestamp (newest first)
                alerts.sort(key=lambda x: x.timestamp, reverse=True)
                
                # Apply limit
                if limit:
                    alerts = alerts[:limit]
                
                return alerts
                
        except Exception as e:
            self.logger.error(
                "Failed to get alert history",
                error=str(e)
            )
            return []
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alert engine statistics.
        
        Returns:
            Alert statistics
        """
        try:
            async with self._alerts_lock:
                stats = {
                    "total_alerts": self._statistics.total_alerts,
                    "active_alerts": len(self._active_alerts),
                    "alerts_by_type": dict(self._statistics.alerts_by_type),
                    "alerts_by_severity": dict(self._statistics.alerts_by_severity),
                    "alerts_by_status": dict(self._statistics.alerts_by_status),
                    "average_resolution_time_minutes": self._statistics.average_resolution_time_minutes,
                    "false_positive_rate": self._statistics.false_positive_rate,
                    "most_common_alert_type": self._statistics.most_common_alert_type,
                    "most_common_severity": self._statistics.most_common_severity,
                    "last_alert": self._statistics.last_alert,
                    "enabled_rules": len([r for r in self._alert_rules.values() if r.enabled]),
                    "total_rules": len(self._alert_rules)
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(
                "Failed to get alert statistics",
                error=str(e)
            )
            return {}
    
    async def is_alerting_enabled(self) -> bool:
        """
        Check if alerting is enabled.
        
        Returns:
            True if alerting is enabled
        """
        return self.enabled
    
    async def enable_alerting(self) -> None:
        """Enable alerting."""
        self.enabled = True
        self.logger.info("Alerting enabled")
    
    async def disable_alerting(self) -> None:
        """Disable alerting."""
        self.enabled = False
        self.logger.info("Alerting disabled")
    
    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """
        Add an alert rule.
        
        Args:
            rule: Alert rule to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._alerts_lock:
                self._alert_rules[rule.rule_id] = rule
            
            self.logger.info(
                "Alert rule added",
                rule_id=rule.rule_id,
                rule_name=rule.name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add alert rule",
                rule_id=rule.rule_id,
                error=str(e)
            )
            return False
    
    async def remove_alert_rule(self, rule_id: str) -> bool:
        """
        Remove an alert rule.
        
        Args:
            rule_id: Rule ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._alerts_lock:
                if rule_id in self._alert_rules:
                    del self._alert_rules[rule_id]
                    
                    self.logger.info(
                        "Alert rule removed",
                        rule_id=rule_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove alert rule",
                rule_id=rule_id,
                error=str(e)
            )
            return False
    
    async def get_alert_rules(self) -> List[AlertRule]:
        """
        Get all alert rules.
        
        Returns:
            List of alert rules
        """
        try:
            async with self._alerts_lock:
                return list(self._alert_rules.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get alert rules",
                error=str(e)
            )
            return []
    
    def add_alert_callback(self, callback: Callable) -> None:
        """
        Add callback for alert generation.
        
        Args:
            callback: Callback function
        """
        self._alert_callbacks.append(callback)
    
    def add_resolution_callback(self, callback: Callable) -> None:
        """
        Add callback for alert resolution.
        
        Args:
            callback: Callback function
        """
        self._resolution_callbacks.append(callback)
    
    # Private methods
    
    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules."""
        default_rules = [
            AlertRule(
                rule_id="high_resolution_time",
                name="High Resolution Time",
                description="Alert when selector resolution time exceeds threshold",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.WARNING,
                condition="performance_metrics.resolution_time_ms > threshold",
                threshold={"resolution_time_ms": 5000},
                tags=["performance", "resolution"]
            ),
            AlertRule(
                rule_id="low_confidence_score",
                name="Low Confidence Score",
                description="Alert when confidence score falls below threshold",
                alert_type=AlertType.QUALITY,
                severity=AlertSeverity.WARNING,
                condition="quality_metrics.confidence_score < threshold",
                threshold={"confidence_score": 0.5},
                tags=["quality", "confidence"]
            ),
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                description="Alert when error rate exceeds threshold",
                alert_type=AlertType.ERROR,
                severity=AlertSeverity.ERROR,
                condition="error_rate > threshold",
                threshold={"error_rate": 0.1},
                tags=["error", "rate"]
            ),
            AlertRule(
                rule_id="strategy_switches",
                name="Excessive Strategy Switches",
                description="Alert when strategy switches exceed threshold",
                alert_type=AlertType.STRATEGY,
                severity=AlertSeverity.WARNING,
                condition="strategy_metrics.strategy_switches_count > threshold",
                threshold={"strategy_switches_count": 3},
                tags=["strategy", "switches"]
            )
        ]
        
        for rule in default_rules:
            self._alert_rules[rule.rule_id] = rule
    
    async def _evaluate_rule(self, rule: AlertRule, event: TelemetryEvent) -> bool:
        """Evaluate a rule against an event."""
        try:
            # Simple rule evaluation - this could be extended with a proper expression language
            if rule.alert_type == AlertType.PERFORMANCE and event.performance_metrics:
                if "resolution_time_ms" in rule.threshold:
                    return event.performance_metrics.resolution_time_ms > rule.threshold["resolution_time_ms"]
            
            elif rule.alert_type == AlertType.QUALITY and event.quality_metrics:
                if "confidence_score" in rule.threshold:
                    return event.quality_metrics.confidence_score < rule.threshold["confidence_score"]
            
            elif rule.alert_type == AlertType.STRATEGY and event.strategy_metrics:
                if "strategy_switches_count" in rule.threshold:
                    return event.strategy_metrics.strategy_switches_count > rule.threshold["strategy_switches_count"]
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate rule",
                rule_id=rule.rule_id,
                error=str(e)
            )
            return False
    
    async def _create_alert(self, rule: AlertRule, event: TelemetryEvent) -> Alert:
        """Create an alert from a triggered rule."""
        alert_id = f"{rule.rule_id}_{event.event_id}_{int(datetime.utcnow().timestamp())}"
        
        return Alert(
            alert_id=alert_id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=f"Alert: {rule.name}",
            message=f"Rule '{rule.name}' triggered for selector '{event.selector_name}'",
            selector_name=event.selector_name,
            correlation_id=event.correlation_id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            context={
                "event_id": event.event_id,
                "operation_type": event.operation_type,
                "timestamp": event.timestamp.isoformat()
            },
            tags=rule.tags,
            timestamp=datetime.utcnow(),
            status=AlertStatus.ACTIVE
        )
    
    def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """Check if rule is in cooldown period."""
        if not rule.last_triggered:
            return False
        
        cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
        return datetime.utcnow() < cooldown_end
    
    def _determine_threshold_severity(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        comparison: str
    ) -> AlertSeverity:
        """Determine alert severity based on threshold exceedance."""
        # Calculate how much the threshold is exceeded
        if comparison in ["greater_than", "greater_equal"]:
            exceed_ratio = current_value / threshold_value if threshold_value > 0 else 1
        elif comparison in ["less_than", "less_equal"]:
            exceed_ratio = threshold_value / current_value if current_value > 0 else 1
        else:
            exceed_ratio = 1
        
        # Determine severity based on exceedance
        if exceed_ratio > 3:
            return AlertSeverity.CRITICAL
        elif exceed_ratio > 2:
            return AlertSeverity.ERROR
        elif exceed_ratio > 1.5:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def _update_statistics(self, alert: Alert) -> None:
        """Update alert statistics."""
        self._statistics.total_alerts += 1
        self._statistics.last_alert = alert.timestamp
        
        # Update type statistics
        type_name = alert.alert_type.value
        if type_name not in self._statistics.alerts_by_type:
            self._statistics.alerts_by_type[type_name] = 0
        self._statistics.alerts_by_type[type_name] += 1
        
        # Update severity statistics
        severity_name = alert.severity.value
        if severity_name not in self._statistics.alerts_by_severity:
            self._statistics.alerts_by_severity[severity_name] = 0
        self._statistics.alerts_by_severity[severity_name] += 1
        
        # Update status statistics
        status_name = alert.status.value
        if status_name not in self._statistics.alerts_by_status:
            self._statistics.alerts_by_status[status_name] = 0
        self._statistics.alerts_by_status[status_name] += 1
        
        # Update most common
        if self._statistics.alerts_by_type:
            self._statistics.most_common_alert_type = max(
                self._statistics.alerts_by_type,
                key=self._statistics.alerts_by_type.get
            )
        
        if self._statistics.alerts_by_severity:
            self._statistics.most_common_severity = max(
                self._statistics.alerts_by_severity,
                key=self._statistics.alerts_by_severity.get
            )
    
    def _update_resolution_statistics(self, alert: Alert) -> None:
        """Update resolution statistics."""
        if hasattr(alert, 'resolution_time_minutes'):
            total_resolved = len([
                a for a in self._alert_history
                if hasattr(a, 'resolution_time_minutes')
            ])
            
            if total_resolved > 0:
                current_avg = self._statistics.average_resolution_time_minutes
                new_avg = ((current_avg * (total_resolved - 1)) + alert.resolution_time_minutes) / total_resolved
                self._statistics.average_resolution_time_minutes = new_avg
    
    async def _limit_alert_history(self) -> None:
        """Limit alert history size."""
        if len(self._alert_history) > self.max_alerts:
            self._alert_history = self._alert_history[-self.max_alerts:]
    
    async def _execute_alert_callbacks(self, alert: Alert) -> None:
        """Execute alert generation callbacks."""
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(
                    "Alert callback failed",
                    alert_id=alert.alert_id,
                    error=str(e)
                )
    
    async def _execute_resolution_callbacks(self, alert: Alert) -> None:
        """Execute alert resolution callbacks."""
        for callback in self._resolution_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(
                    "Resolution callback failed",
                    alert_id=alert.alert_id,
                    error=str(e)
                )
