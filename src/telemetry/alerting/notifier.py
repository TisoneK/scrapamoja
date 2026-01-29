"""
Alert Notification System

Comprehensive alert notification system with multiple channels,
templates, and delivery tracking capabilities.
"""

import asyncio
import json
import smtplib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import aiohttp
import requests

from ..interfaces import Alert, AlertSeverity
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    SMS = "sms"
    CONSOLE = "console"
    LOG = "log"


class NotificationStatus(Enum):
    """Notification status types."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class NotificationConfig:
    """Configuration for notification channel."""
    channel_id: str
    name: str
    channel_type: NotificationChannel
    enabled: bool = True
    severity_filter: List[AlertSeverity] = field(default_factory=lambda: [AlertSeverity.ERROR, AlertSeverity.CRITICAL])
    rate_limit_per_hour: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: int = 60
    template_id: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationTemplate:
    """Template for alert notifications."""
    template_id: str
    name: str
    description: str
    channel_type: NotificationChannel
    subject_template: str
    body_template: str
    variables: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationResult:
    """Result of notification delivery."""
    notification_id: str
    channel_id: str
    alert_id: str
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    delivery_time_ms: Optional[float] = None
    response_data: Optional[Dict[str, Any]] = None


@dataclass
class NotificationStatistics:
    """Statistics for notification system."""
    total_notifications: int = 0
    notifications_by_channel: Dict[str, int] = field(default_factory=dict)
    notifications_by_status: Dict[str, int] = field(default_factory=dict)
    notifications_by_severity: Dict[str, int] = field(default_factory=dict)
    average_delivery_time_ms: float = 0.0
    success_rate: float = 0.0
    most_active_channel: str = ""
    last_notification: Optional[datetime] = None
    rate_limited_notifications: int = 0


class AlertNotifier:
    """
    Comprehensive alert notification system.
    
    Provides multi-channel alert notifications with templates,
    rate limiting, and delivery tracking.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize alert notifier.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("alert_notifier")
        
        # Notifier configuration
        self.enabled = config.get("notification_enabled", True)
        self.default_retry_attempts = config.get("notification_retry_attempts", 3)
        self.default_rate_limit = config.get("notification_rate_limit_per_hour", 10)
        
        # Storage
        self._notification_configs: Dict[str, NotificationConfig] = {}
        self._notification_templates: Dict[str, NotificationTemplate] = {}
        self._notification_history: List[NotificationResult] = []
        self._rate_limiters: Dict[str, List[datetime]] = defaultdict(list)
        self._notifier_lock = asyncio.Lock()
        
        # Statistics
        self._statistics = NotificationStatistics()
        
        # HTTP session for webhooks
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # Initialize default configurations and templates
        self._initialize_default_configs()
        self._initialize_default_templates()
    
    async def send_notification(
        self,
        alert: Alert,
        channel_ids: Optional[List[str]] = None,
        custom_template: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """
        Send alert notification through configured channels.
        
        Args:
            alert: Alert to send notification for
            channel_ids: Optional list of channel IDs to use
            custom_template: Optional custom template ID
            context: Additional context for template variables
            
        Returns:
            List of notification results
            
        Raises:
            TelemetryAlertingError: If sending fails
        """
        if not self.enabled:
            return []
        
        try:
            results = []
            
            async with self._notifier_lock:
                # Determine channels to use
                if channel_ids:
                    channels = [
                        config for config_id, config in self._notification_configs.items()
                        if config_id in channel_ids and config.enabled
                    ]
                else:
                    # Use all enabled channels that match severity
                    channels = [
                        config for config in self._notification_configs.values()
                        if config.enabled and alert.severity in config.severity_filter
                    ]
                
                # Send notifications
                for channel_config in channels:
                    # Check rate limiting
                    if await self._is_rate_limited(channel_config.channel_id):
                        results.append(NotificationResult(
                            notification_id=f"rate_limited_{alert.alert_id}_{channel_config.channel_id}_{int(datetime.utcnow().timestamp())}",
                            channel_id=channel_config.channel_id,
                            alert_id=alert.alert_id,
                            status=NotificationStatus.CANCELLED,
                            error_message="Rate limited"
                        ))
                        self._statistics.rate_limited_notifications += 1
                        continue
                    
                    # Send notification
                    result = await self._send_to_channel(
                        channel_config,
                        alert,
                        custom_template,
                        context
                    )
                    
                    results.append(result)
                    self._notification_history.append(result)
                    self._update_statistics(result)
                
                # Limit history size
                if len(self._notification_history) > 10000:
                    self._notification_history = self._notification_history[-10000:]
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to send notification",
                alert_id=alert.alert_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to send notification: {e}",
                error_code="TEL-812"
            )
    
    async def send_to_channel(
        self,
        channel_id: str,
        alert: Alert,
        custom_template: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[NotificationResult]:
        """
        Send notification to specific channel.
        
        Args:
            channel_id: Channel ID to send to
            alert: Alert to send notification for
            custom_template: Optional custom template ID
            context: Additional context for template variables
            
        Returns:
            Notification result or None if channel not found
        """
        try:
            async with self._notifier_lock:
                if channel_id not in self._notification_configs:
                    return None
                
                channel_config = self._notification_configs[channel_id]
                
                if not channel_config.enabled:
                    return None
                
                # Check rate limiting
                if await self._is_rate_limited(channel_id):
                    return NotificationResult(
                        notification_id=f"rate_limited_{alert.alert_id}_{channel_id}_{int(datetime.utcnow().timestamp())}",
                        channel_id=channel_id,
                        alert_id=alert.alert_id,
                        status=NotificationStatus.CANCELLED,
                        error_message="Rate limited"
                    )
                
                # Send notification
                result = await self._send_to_channel(
                    channel_config,
                    alert,
                    custom_template,
                    context
                )
                
                self._notification_history.append(result)
                self._update_statistics(result)
                
                return result
                
        except Exception as e:
            self.logger.error(
                "Failed to send to channel",
                channel_id=channel_id,
                alert_id=alert.alert_id,
                error=str(e)
            )
            return None
    
    async def add_notification_config(self, config: NotificationConfig) -> bool:
        """
        Add a notification configuration.
        
        Args:
            config: Notification configuration to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._notifier_lock:
                self._notification_configs[config.channel_id] = config
            
            self.logger.info(
                "Notification config added",
                channel_id=config.channel_id,
                channel_type=config.channel_type.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add notification config",
                channel_id=config.channel_id,
                error=str(e)
            )
            return False
    
    async def remove_notification_config(self, channel_id: str) -> bool:
        """
        Remove a notification configuration.
        
        Args:
            channel_id: Channel ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._notifier_lock:
                if channel_id in self._notification_configs:
                    del self._notification_configs[channel_id]
                    
                    # Clean up rate limiter
                    if channel_id in self._rate_limiters:
                        del self._rate_limiters[channel_id]
                    
                    self.logger.info(
                        "Notification config removed",
                        channel_id=channel_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove notification config",
                channel_id=channel_id,
                error=str(e)
            )
            return False
    
    async def add_notification_template(self, template: NotificationTemplate) -> bool:
        """
        Add a notification template.
        
        Args:
            template: Template to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._notifier_lock:
                self._notification_templates[template.template_id] = template
            
            self.logger.info(
                "Notification template added",
                template_id=template.template_id,
                channel_type=template.channel_type.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add notification template",
                template_id=template.template_id,
                error=str(e)
            )
            return False
    
    async def get_notification_statistics(self) -> Dict[str, Any]:
        """
        Get notification system statistics.
        
        Returns:
            Notification statistics
        """
        try:
            async with self._notifier_lock:
                return {
                    "total_notifications": self._statistics.total_notifications,
                    "notifications_by_channel": dict(self._statistics.notifications_by_channel),
                    "notifications_by_status": dict(self._statistics.notifications_by_status),
                    "notifications_by_severity": dict(self._statistics.notifications_by_severity),
                    "average_delivery_time_ms": self._statistics.average_delivery_time_ms,
                    "success_rate": self._statistics.success_rate,
                    "most_active_channel": self._statistics.most_active_channel,
                    "last_notification": self._statistics.last_notification,
                    "rate_limited_notifications": self._statistics.rate_limited_notifications,
                    "active_channels": len([c for c in self._notification_configs.values() if c.enabled]),
                    "total_channels": len(self._notification_configs),
                    "total_templates": len(self._notification_templates)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get notification statistics",
                error=str(e)
            )
            return {}
    
    async def get_notification_history(
        self,
        channel_id: Optional[str] = None,
        status: Optional[NotificationStatus] = None,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[NotificationResult]:
        """
        Get notification history with filtering.
        
        Args:
            channel_id: Optional channel ID filter
            status: Optional status filter
            limit: Optional limit on number of results
            time_window: Optional time window for results
            
        Returns:
            List of notification results
        """
        try:
            async with self._notifier_lock:
                results = self._notification_history.copy()
                
                # Apply filters
                if channel_id:
                    results = [r for r in results if r.channel_id == channel_id]
                
                if status:
                    results = [r for r in results if r.status == status]
                
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    results = [r for r in results if r.sent_at and r.sent_at >= cutoff_time]
                
                # Sort by sent time (newest first)
                results.sort(key=lambda x: x.sent_at or datetime.min, reverse=True)
                
                # Apply limit
                if limit:
                    results = results[:limit]
                
                return results
                
        except Exception as e:
            self.logger.error(
                "Failed to get notification history",
                error=str(e)
            )
            return []
    
    async def get_all_configs(self) -> List[NotificationConfig]:
        """
        Get all notification configurations.
        
        Returns:
            List of all configurations
        """
        try:
            async with self._notifier_lock:
                return list(self._notification_configs.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all configs",
                error=str(e)
            )
            return []
    
    async def get_all_templates(self) -> List[NotificationTemplate]:
        """
        Get all notification templates.
        
        Returns:
            List of all templates
        """
        try:
            async with self._notifier_lock:
                return list(self._notification_templates.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all templates",
                error=str(e)
            )
            return []
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._http_session:
            await self._http_session.close()
    
    # Private methods
    
    def _initialize_default_configs(self) -> None:
        """Initialize default notification configurations."""
        default_configs = [
            NotificationConfig(
                channel_id="console",
                name="Console Notifications",
                channel_type=NotificationChannel.CONSOLE,
                severity_filter=[AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL],
                rate_limit_per_hour=1000  # No limit for console
            ),
            NotificationConfig(
                channel_id="log",
                name="Log Notifications",
                channel_type=NotificationChannel.LOG,
                severity_filter=[AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL],
                rate_limit_per_hour=1000  # No limit for logging
            )
        ]
        
        for config in default_configs:
            self._notification_configs[config.channel_id] = config
    
    def _initialize_default_templates(self) -> None:
        """Initialize default notification templates."""
        default_templates = [
            NotificationTemplate(
                template_id="console_default",
                name="Default Console Template",
                description="Default template for console notifications",
                channel_type=NotificationChannel.CONSOLE,
                subject_template="Alert: {title}",
                body_template="[{severity}] {title}\n{message}\nTimestamp: {timestamp}\nSelector: {selector_name}"
            ),
            NotificationTemplate(
                template_id="log_default",
                name="Default Log Template",
                description="Default template for log notifications",
                channel_type=NotificationChannel.LOG,
                subject_template="Alert: {title}",
                body_template="Alert {alert_id} - {severity} - {title}: {message} (Selector: {selector_name}, Timestamp: {timestamp})"
            ),
            NotificationTemplate(
                template_id="email_default",
                name="Default Email Template",
                description="Default template for email notifications",
                channel_type=NotificationChannel.EMAIL,
                subject_template="[{severity}] {title}",
                body_template="Alert Details:\n\nTitle: {title}\nSeverity: {severity}\nMessage: {message}\nTimestamp: {timestamp}\nSelector: {selector_name}\nAlert ID: {alert_id}\n\nContext:\n{context}"
            )
        ]
        
        for template in default_templates:
            self._notification_templates[template.template_id] = template
    
    async def _send_to_channel(
        self,
        channel_config: NotificationConfig,
        alert: Alert,
        custom_template: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> NotificationResult:
        """Send notification to specific channel."""
        start_time = datetime.utcnow()
        notification_id = f"{alert.alert_id}_{channel_config.channel_id}_{int(start_time.timestamp())}"
        
        try:
            # Get template
            template_id = custom_template or channel_config.template_id
            template = self._notification_templates.get(template_id)
            
            if not template:
                # Use default template for channel type
                default_template_id = f"{channel_config.channel_type.value}_default"
                template = self._notification_templates.get(default_template_id)
            
            # Prepare template variables
            template_vars = self._prepare_template_variables(alert, context)
            
            # Render template
            subject = self._render_template(template.subject_template, template_vars) if template else f"Alert: {alert.title}"
            body = self._render_template(template.body_template, template_vars) if template else alert.message
            
            # Send based on channel type
            if channel_config.channel_type == NotificationChannel.CONSOLE:
                await self._send_console_notification(subject, body)
            elif channel_config.channel_type == NotificationChannel.LOG:
                await self._send_log_notification(subject, body)
            elif channel_config.channel_type == NotificationChannel.EMAIL:
                await self._send_email_notification(channel_config, subject, body)
            elif channel_config.channel_type == NotificationChannel.WEBHOOK:
                await self._send_webhook_notification(channel_config, alert, subject, body)
            elif channel_config.channel_type == NotificationChannel.SLACK:
                await self._send_slack_notification(channel_config, alert, subject, body)
            else:
                raise TelemetryAlertingError(
                    f"Unsupported channel type: {channel_config.channel_type.value}",
                    error_code="TEL-813"
                )
            
            delivery_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return NotificationResult(
                notification_id=notification_id,
                channel_id=channel_config.channel_id,
                alert_id=alert.alert_id,
                status=NotificationStatus.SENT,
                sent_at=datetime.utcnow(),
                delivery_time_ms=delivery_time
            )
            
        except Exception as e:
            return NotificationResult(
                notification_id=notification_id,
                channel_id=channel_config.channel_id,
                alert_id=alert.alert_id,
                status=NotificationStatus.FAILED,
                error_message=str(e),
                retry_count=0
            )
    
    async def _send_console_notification(self, subject: str, body: str) -> None:
        """Send console notification."""
        print(f"\n{'='*60}")
        print(f"ALERT NOTIFICATION")
        print(f"{'='*60}")
        print(f"Subject: {subject}")
        print(f"Message: {body}")
        print(f"{'='*60}\n")
    
    async def _send_log_notification(self, subject: str, body: str) -> None:
        """Send log notification."""
        self.logger.warning(f"ALERT: {subject} - {body}")
    
    async def _send_email_notification(self, config: NotificationConfig, subject: str, body: str) -> None:
        """Send email notification."""
        email_config = config.config
        
        smtp_server = email_config.get("smtp_server", "localhost")
        smtp_port = email_config.get("smtp_port", 587)
        username = email_config.get("username")
        password = email_config.get("password")
        from_email = email_config.get("from_email", "alerts@scorewise.local")
        to_emails = email_config.get("to_emails", [])
        
        if not to_emails:
            raise TelemetryAlertingError("No recipients configured for email notification", error_code="TEL-814")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        if username and password:
            server.starttls()
            server.login(username, password)
        
        server.send_message(msg)
        server.quit()
    
    async def _send_webhook_notification(self, config: NotificationConfig, alert: Alert, subject: str, body: str) -> None:
        """Send webhook notification."""
        webhook_config = config.config
        
        url = webhook_config.get("url")
        if not url:
            raise TelemetryAlertingError("No URL configured for webhook notification", error_code="TEL-815")
        
        method = webhook_config.get("method", "POST")
        headers = webhook_config.get("headers", {})
        auth = webhook_config.get("auth")
        
        # Prepare payload
        payload = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "timestamp": alert.timestamp.isoformat(),
            "subject": subject,
            "body": body,
            "selector_name": alert.selector_name,
            "correlation_id": alert.correlation_id,
            "tags": alert.tags,
            "context": alert.context
        }
        
        # Add custom fields
        custom_fields = webhook_config.get("custom_fields", {})
        payload.update(custom_fields)
        
        # Send request
        if not self._http_session:
            self._http_session = aiohttp.ClientSession()
        
        async with self._http_session.request(
            method=method,
            url=url,
            json=payload,
            headers=headers,
            auth=auth
        ) as response:
            response.raise_for_status()
    
    async def _send_slack_notification(self, config: NotificationConfig, alert: Alert, subject: str, body: str) -> None:
        """Send Slack notification."""
        slack_config = config.config
        
        webhook_url = slack_config.get("webhook_url")
        if not webhook_url:
            raise TelemetryAlertingError("No webhook URL configured for Slack notification", error_code="TEL-816")
        
        # Prepare Slack payload
        color = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "danger",
            AlertSeverity.CRITICAL: "danger"
        }.get(alert.severity, "warning")
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": subject,
                    "text": body,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value,
                            "short": True
                        },
                        {
                            "title": "Selector",
                            "value": alert.selector_name or "Unknown",
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ],
                    "footer": f"Alert ID: {alert.alert_id}",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        # Send request
        if not self._http_session:
            self._http_session = aiohttp.ClientSession()
        
        async with self._http_session.post(webhook_url, json=payload) as response:
            response.raise_for_status()
    
    def _prepare_template_variables(self, alert: Alert, context: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Prepare template variables."""
        variables = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "timestamp": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "selector_name": alert.selector_name or "Unknown",
            "correlation_id": alert.correlation_id or "Unknown",
            "metric_name": alert.metric_name or "Unknown",
            "current_value": str(getattr(alert, 'current_value', 'N/A')),
            "threshold_value": str(getattr(alert, 'threshold_value', 'N/A')),
            "tags": ', '.join(alert.tags) if alert.tags else "",
            "context": json.dumps(alert.context, indent=2) if alert.context else "{}"
        }
        
        # Add custom context
        if context:
            for key, value in context.items():
                variables[f"context_{key}"] = str(value)
        
        return variables
    
    def _render_template(self, template: str, variables: Dict[str, str]) -> str:
        """Render template with variables."""
        try:
            return template.format(**variables)
        except KeyError as e:
            self.logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            self.logger.error(f"Template rendering error: {e}")
            return template
    
    async def _is_rate_limited(self, channel_id: str) -> bool:
        """Check if channel is rate limited."""
        if channel_id not in self._notification_configs:
            return False
        
        config = self._notification_configs[channel_id]
        rate_limit = config.rate_limit_per_hour
        
        if rate_limit <= 0:
            return False
        
        # Clean old entries (older than 1 hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self._rate_limiters[channel_id] = [
            timestamp for timestamp in self._rate_limiters[channel_id]
            if timestamp >= cutoff_time
        ]
        
        # Check rate limit
        return len(self._rate_limiters[channel_id]) >= rate_limit
    
    def _update_statistics(self, result: NotificationResult) -> None:
        """Update notification statistics."""
        self._statistics.total_notifications += 1
        
        if result.sent_at:
            self._statistics.last_notification = result.sent_at
        
        # Update by channel
        if result.channel_id not in self._statistics.notifications_by_channel:
            self._statistics.notifications_by_channel[result.channel_id] = 0
        self._statistics.notifications_by_channel[result.channel_id] += 1
        
        # Update by status
        status_name = result.status.value
        if status_name not in self._statistics.notifications_by_status:
            self._statistics.notifications_by_status[status_name] = 0
        self._statistics.notifications_by_status[status_name] += 1
        
        # Update delivery time
        if result.delivery_time_ms is not None:
            total_notifications = self._statistics.total_notifications
            current_avg = self._statistics.average_delivery_time_ms
            new_avg = ((current_avg * (total_notifications - 1)) + result.delivery_time_ms) / total_notifications
            self._statistics.average_delivery_time_ms = new_avg
        
        # Update success rate
        sent_count = self._statistics.notifications_by_status.get("sent", 0)
        total_notifications = self._statistics.total_notifications
        if total_notifications > 0:
            self._statistics.success_rate = sent_count / total_notifications
        
        # Update most active channel
        if self._statistics.notifications_by_channel:
            self._statistics.most_active_channel = max(
                self._statistics.notifications_by_channel,
                key=self._statistics.notifications_by_channel.get
            )
        
        # Add to rate limiter if sent
        if result.status == NotificationStatus.SENT and result.sent_at:
            self._rate_limiters[result.channel_id].append(result.sent_at)
