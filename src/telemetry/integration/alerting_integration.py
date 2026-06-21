"""
Alerting Integration with Data Collection

Integration layer connecting telemetry data collection with
alerting system for real-time monitoring and alerting.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from ..interfaces import ITelemetryIntegration, Alert, AlertSeverity
from ..models import TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryIntegrationError
from ..configuration.logging import get_logger

# Import alerting components
from ..alerting.alert_engine import AlertEngine
from ..alerting.threshold_monitor import ThresholdMonitor
from ..alerting.performance_evaluator import PerformanceEvaluator
from ..alerting.quality_monitor import QualityMonitor
from ..alerting.anomaly_detector import AnomalyDetector
from ..alerting.severity_classifier import SeverityClassifier
from ..alerting.notifier import AlertNotifier
from ..alerting.management import AlertManager
from ..alerting.logging import AlertLogger


@dataclass
class AlertingIntegrationConfig:
    """Configuration for alerting integration."""
    enable_real_time_alerting: bool = True
    enable_threshold_monitoring: bool = True
    enable_performance_evaluation: bool = True
    enable_quality_monitoring: bool = True
    enable_anomaly_detection: bool = True
    enable_severity_classification: bool = True
    enable_notifications: bool = True
    enable_lifecycle_management: bool = True
    batch_processing_enabled: bool = True
    batch_size: int = 10
    batch_timeout_seconds: int = 30


class AlertingIntegration(ISelectorTelemetryIntegration):
    """
    Integration layer connecting telemetry data collection with alerting.
    
    Provides seamless integration between telemetry collection and
    alerting system for real-time monitoring and alerting.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize alerting integration.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("alerting_integration")
        
        # Integration configuration
        self.enabled = config.get("alerting_integration_enabled", True)
        self.integration_config = AlertingIntegrationConfig(
            enable_real_time_alerting=config.get("enable_real_time_alerting", True),
            enable_threshold_monitoring=config.get("enable_threshold_monitoring", True),
            enable_performance_evaluation=config.get("enable_performance_evaluation", True),
            enable_quality_monitoring=config.get("enable_quality_monitoring", True),
            enable_anomaly_detection=config.get("enable_anomaly_detection", True),
            enable_severity_classification=config.get("enable_severity_classification", True),
            enable_notifications=config.get("enable_notifications", True),
            enable_lifecycle_management=config.get("enable_lifecycle_management", True),
            batch_processing_enabled=config.get("alert_batch_processing_enabled", True),
            batch_size=config.get("alert_batch_size", 10),
            batch_timeout_seconds=config.get("alert_batch_timeout_seconds", 30)
        )
        
        # Alerting components
        self.alert_engine = AlertEngine(config)
        self.threshold_monitor = ThresholdMonitor(config)
        self.performance_evaluator = PerformanceEvaluator(config)
        self.quality_monitor = QualityMonitor(config)
        self.anomaly_detector = AnomalyDetector(config)
        self.severity_classifier = SeverityClassifier(config)
        self.alert_notifier = AlertNotifier(config)
        self.alert_manager = AlertManager(config)
        self.alert_logger = AlertLogger(config, "integration")
        
        # Integration state
        self._real_time_enabled = self.integration_config.enable_real_time_alerting
        self._batch_queue: List[TelemetryEvent] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._integration_stats = {
            "events_processed": 0,
            "alerts_generated": 0,
            "notifications_sent": 0,
            "errors_encountered": 0,
            "start_time": datetime.utcnow()
        }
        
        # Callbacks
        self._alert_callbacks: List[Callable] = []
        
        # Start background tasks
        if self.enabled:
            self._start_background_tasks()
    
    async def initialize_integration(self, config: Dict[str, Any]) -> bool:
        """
        Initialize alerting integration.
        
        Args:
            config: Integration configuration
            
        Returns:
            True if successfully initialized
        """
        try:
            # Update configuration
            self.enabled = config.get("enabled", True)
            
            # Update integration config
            for key, value in config.items():
                if hasattr(self.integration_config, key):
                    setattr(self.integration_config, key, value)
            
            # Validate components
            if not all([
                self.alert_engine,
                self.threshold_monitor,
                self.performance_evaluator,
                self.quality_monitor,
                self.anomaly_detector,
                self.severity_classifier,
                self.alert_notifier,
                self.alert_manager
            ]):
                raise TelemetryIntegrationError(
                    "Not all alerting components are available",
                    error_code="TEL-901"
                )
            
            # Test alert engine availability
            if hasattr(self.alert_engine, 'is_alerting_enabled'):
                alerting_enabled = await self.alert_engine.is_alerting_enabled()
                if not alerting_enabled:
                    self.logger.warning("Alert engine is disabled")
            
            self.alert_logger.info(
                "Alerting integration initialized",
                enabled=self.enabled,
                real_time_enabled=self._real_time_enabled,
                batch_processing=self.integration_config.batch_processing_enabled
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize alerting integration",
                error=str(e)
            )
            raise TelemetryIntegrationError(
                f"Failed to initialize alerting integration: {e}",
                error_code="TEL-902",
                integration_point="initialization"
            )
    
    async def shutdown_integration(self) -> bool:
        """
        Shutdown alerting integration.
        
        Returns:
            True if successfully shutdown
        """
        try:
            # Disable integration
            self.enabled = False
            self._real_time_enabled = False
            
            # Stop background tasks
            self._shutdown_event.set()
            
            if self._batch_task:
                self._batch_task.cancel()
                try:
                    await self._batch_task
                except asyncio.CancelledError:
                    pass
                self._batch_task = None
            
            # Cleanup components
            await self.alert_manager.cleanup()
            await self.alert_notifier.cleanup()
            
            self.alert_logger.info(
                "Alerting integration shutdown",
                total_events_processed=self._integration_stats["events_processed"],
                total_alerts_generated=self._integration_stats["alerts_generated"],
                total_notifications_sent=self._integration_stats["notifications_sent"]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to shutdown alerting integration",
                error=str(e)
            )
            return False
    
    async def process_telemetry_event(self, event: TelemetryEvent) -> List[Alert]:
        """
        Process telemetry event through alerting pipeline.
        
        Args:
            event: TelemetryEvent to process
            
        Returns:
            List of generated alerts
            
        Raises:
            TelemetryIntegrationError: If processing fails
        """
        if not self.enabled:
            return []
        
        try:
            start_time = datetime.utcnow()
            self._integration_stats["events_processed"] += 1
            
            # Add to batch queue if batch processing is enabled
            if self.integration_config.batch_processing_enabled:
                async with self._batch_lock:
                    self._batch_queue.append(event)
                    
                    # Process batch if queue is full or timeout reached
                    if len(self._batch_queue) >= self.integration_config.batch_size:
                        await self._process_batch()
                return []
            
            # Real-time processing
            if self._real_time_enabled:
                alerts = await self._process_event_realtime(event)
            else:
                alerts = []
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._integration_stats["alerts_generated"] += len(alerts)
            
            # Execute callbacks
            for alert in alerts:
                await self._execute_alert_callbacks(alert)
            
            self.alert_logger.debug(
                "Telemetry event processed",
                event_id=event.event_id,
                alerts_count=len(alerts),
                processing_time_ms=processing_time
            )
            
            return alerts
            
        except Exception as e:
            self._integration_stats["errors_encountered"] += 1
            self.logger.error(
                "Failed to process telemetry event",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryIntegrationError(
                f"Failed to process telemetry event: {e}",
                error_code="TEL-903",
                integration_point="event_processing"
            )
    
    async def process_events_batch(self, events: List[TelemetryEvent]) -> List[Alert]:
        """
        Process multiple telemetry events in batch.
        
        Args:
            events: List of TelemetryEvents to process
            
        Returns:
            List of generated alerts
        """
        if not self.enabled or not events:
            return []
        
        try:
            start_time = datetime.utcnow()
            all_alerts = []
            
            # Process each event
            for event in events:
                if self._real_time_enabled:
                    alerts = await self._process_event_realtime(event)
                    all_alerts.extend(alerts)
                else:
                    # Add to batch queue for later processing
                    async with self._batch_lock:
                        self._batch_queue.extend(events)
            
            # Process batch if queue is large enough
            if len(self._batch_queue) >= self.integration_config.batch_size:
                batch_alerts = await self._process_batch()
                all_alerts.extend(batch_alerts)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._integration_stats["events_processed"] += len(events)
            self._integration_stats["alerts_generated"] += len(all_alerts)
            
            self.alert_logger.info(
                "Telemetry events batch processed",
                events_count=len(events),
                alerts_count=len(all_alerts),
                processing_time_ms=processing_time
            )
            
            return all_alerts
            
        except Exception as e:
            self._integration_stats["errors_encountered"] += 1
            self.logger.error(
                "Failed to process events batch",
                events_count=len(events),
                error=str(e)
            )
            raise TelemetryIntegrationError(
                f"Failed to process events batch: {e}",
                error_code="TEL-904",
                integration_point="batch_processing"
            )
    
    async def evaluate_thresholds(
        self,
        metrics: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Evaluate thresholds for metrics.
        
        Args:
            metrics: Dictionary of metric values
            context: Additional context
            
        Returns:
            List of threshold alerts
        """
        try:
            if not self.enabled or not self.integration_config.enable_threshold_monitoring:
                return []
            
            alerts = []
            
            # Evaluate thresholds using threshold monitor
            threshold_evaluations = await self.threshold_monitor.evaluate_all_thresholds(metrics, context)
            
            # Convert evaluations to alerts
            for evaluation in threshold_evaluations:
                if evaluation.triggered:
                    alert = Alert(
                        alert_id=f"threshold_{evaluation.threshold_id}_{int(datetime.utcnow().timestamp())}",
                        alert_type=AlertType.THRESHOLD,
                        severity=evaluation.severity,
                        title=f"Threshold Exceeded: {evaluation.metric_name}",
                        message=f"{evaluation.metric_name} value {evaluation.current_value} exceeds threshold {evaluation.threshold_value}",
                        metric_name=evaluation.metric_name,
                        current_value=evaluation.current_value,
                        threshold_value=evaluation.threshold_value,
                        comparison=evaluation.comparison.value,
                        context=evaluation.context,
                        timestamp=datetime.utcnow(),
                        tags=["threshold", evaluation.metric_name]
                    )
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate thresholds",
                error=str(e)
            )
            return []
    
    async def detect_anomalies(
        self,
        metrics: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Detect anomalies in metrics.
        
        Args:
            metrics: Dictionary of metric values
            context: Additional context
            
        Returns:
            List of anomaly alerts
        """
        try:
            if not self.enabled or not self.integration_config.enable_anomaly_detection:
                return []
            
            alerts = []
            
            # Detect anomalies using anomaly detector
            anomaly_results = []
            
            for metric_name, value in metrics.items():
                anomaly = await self.anomaly_detector.detect_anomaly(
                    metric_name,
                    value,
                    context
                )
                if anomaly:
                    anomaly_results.append(anomaly)
            
            # Convert anomaly results to alerts
            for anomaly in anomaly_results:
                alert = Alert(
                    alert_id=f"anomaly_{anomaly.config_id}_{int(datetime.utcnow().timestamp())}",
                    alert_type=AlertType.ANOMALY,
                    severity=anomaly.severity,
                    title=f"Anomaly Detected: {anomaly.metric_name}",
                    message=f"Anomaly detected in {anomaly.metric_name}: {anomaly.explanation}",
                    metric_name=anomaly.metric_name,
                    current_value=anomaly.value,
                    context=anomaly.context,
                    timestamp=datetime.utcnow(),
                    tags=["anomaly", anomaly.metric_name, anomaly.algorithm.value]
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(
                "Failed to detect anomalies",
                error=str(e)
            )
            return []
    
    async def classify_alert_severity(
        self,
        alert: Alert,
        event: Optional[TelemetryEvent] = None
    ) -> Alert:
        """
        Classify alert severity.
        
        Args:
            alert: Alert to classify
            event: Optional telemetry event for context
            
        Returns:
            Alert with classified severity
        """
        try:
            if not self.enabled or not self.integration_config.enable_severity_classification:
                return alert
            
            # Classify severity
            classification = await self.severity_classifier.classify_alert_severity(alert, event)
            
            # Update alert severity
            alert.severity = classification.classified_severity
            
            # Add classification context
            if not alert.context:
                alert.context = {}
            
            alert.context.update({
                "classification_method": classification.classification_method.value,
                "classification_confidence": classification.confidence,
                "classification_reasoning": classification.reasoning,
                "applied_rules": classification.applied_rules,
                "factors": {factor.value: value for factor, value in classification.factors.items()}
            })
            
            self.alert_logger.debug(
                "Alert severity classified",
                alert_id=alert.alert_id,
                original_severity="unknown",
                classified_severity=alert.severity.value,
                confidence=classification.confidence
            )
            
            return alert
            
        except Exception as e:
            self.logger.error(
                "Failed to classify alert severity",
                alert_id=alert.alert_id,
                error=str(e)
            )
            return alert
    
    async def send_notifications(
        self,
        alerts: List[Alert],
        channel_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Send notifications for alerts.
        
        Args:
            alerts: List of alerts to notify
            channel_ids: Optional list of channel IDs
            
        Returns:
            List of notification results
        """
        try:
            if not self.enabled or not self.integration_config.enable_notifications:
                return []
            
            results = []
            
            # Send notifications for each alert
            for alert in alerts:
                notification_results = await self.alert_notifier.send_notification(
                    alert,
                    channel_ids
                )
                results.extend([
                    {
                        "alert_id": result.notification_id,
                        "channel_id": result.channel_id,
                        "status": result.status.value,
                        "sent_at": result.sent_at.isoformat() if result.sent_at else None,
                        "error_message": result.error_message
                    }
                    for result in notification_results
                ])
                
                # Update statistics
                success_count = sum(1 for r in notification_results if r.status.value == "sent")
                self._integration_stats["notifications_sent"] += success_count
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to send notifications",
                alerts_count=len(alerts),
                error=str(e)
            )
            return []
    
    async def get_integration_statistics(self) -> Dict[str, Any]:
        """
        Get integration statistics.
        
        Returns:
            Integration statistics
        """
        try:
            runtime = datetime.utcnow() - self._integration_stats["start_time"]
            
            base_stats = {
                "enabled": self.enabled,
                "real_time_enabled": self._real_time_enabled,
                "batch_processing_enabled": self.integration_config.batch_processing_enabled,
                "events_processed": self._integration_stats["events_processed"],
                "alerts_generated": self._integration_stats["alerts_generated"],
                "notifications_sent": self._integration_stats["notifications_sent"],
                "errors_encountered": self._integration_stats["errors_encountered"],
                "runtime_seconds": runtime.total_seconds(),
                "batch_queue_size": len(self._batch_queue),
                "config": {
                    "enable_real_time_alerting": self.integration_config.enable_real_time_alerting,
                    "enable_threshold_monitoring": self.integration_config.enable_threshold_monitoring,
                    "enable_performance_evaluation": self.integration_config.enable_performance_evaluation,
                    "enable_quality_monitoring": self.integration_config.enable_quality_monitoring,
                    "enable_anomaly_detection": self.integration_config.enable_anomaly_detection,
                    "enable_severity_classification": self.integration_config.enable_severity_classification,
                    "enable_notifications": self.integration_config.enable_notifications,
                    "enable_lifecycle_management": self.integration_config.enable_lifecycle_management,
                    "batch_processing_enabled": self.integration_config.batch_processing_enabled,
                    "batch_size": self.integration_config.batch_size,
                    "batch_timeout_seconds": self.integration_config.batch_timeout_seconds
                }
            }
            
            # Add component statistics
            if hasattr(self.alert_engine, 'get_alert_statistics'):
                base_stats["alert_engine"] = await self.alert_engine.get_alert_statistics()
            
            if hasattr(self.threshold_monitor, 'get_threshold_statistics'):
                base_stats["threshold_monitor"] = await self.threshold_monitor.get_threshold_statistics()
            
            if hasattr(self.performance_evaluator, 'get_performance_statistics'):
                base_stats["performance_evaluator"] = await self.performance_evaluator.get_performance_statistics()
            
            if hasattr(self.quality_monitor, 'get_quality_statistics'):
                base_stats["quality_monitor"] = await self.quality_monitor.get_quality_statistics()
            
            if hasattr(self.anomaly_detector, 'get_anomaly_statistics'):
                base_stats["anomaly_detector"] = await self.anomaly_detector.get_anomaly_statistics()
            
            if hasattr(self.severity_classifier, 'get_classification_statistics'):
                base_stats["severity_classifier"] = await self.severity_classifier.get_classification_statistics()
            
            if hasattr(self.alert_notifier, 'get_notification_statistics'):
                base_stats["alert_notifier"] = await self.alert_notifier.get_notification_statistics()
            
            if hasattr(self.alert_manager, 'get_management_statistics'):
                base_stats["alert_manager"] = await self.alert_manager.get_management_statistics()
            
            return base_stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get integration statistics",
                error=str(e)
            )
            return {}
    
    async def is_integration_enabled(self) -> bool:
        """
        Check if integration is enabled.
        
        Returns:
            True if integration is enabled
        """
        return self.enabled
    
    async def enable_integration(self) -> None:
        """Enable integration."""
        self.enabled = True
        self._real_time_enabled = self.integration_config.enable_real_time_alerting
        
        # Start background tasks if needed
        if not self._batch_task or self._batch_task.done():
            self._start_background_tasks()
        
        self.alert_logger.info("Alerting integration enabled")
    
    async def disable_integration(self) -> None:
        """Disable integration."""
        self.enabled = False
        self._real_time_enabled = False
        
        # Stop background tasks
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None
        
        self.alert_logger.info("Alerting integration disabled")
    
    def add_alert_callback(self, callback: Callable) -> None:
        """
        Add callback for alert generation.
        
        Args:
            callback: Callback function
        """
        self._alert_callbacks.append(callback)
    
    # Private methods
    
    def _start_background_tasks(self) -> None:
        """Start background tasks."""
        if self.integration_config.batch_processing_enabled:
            self._batch_task = asyncio.create_task(self._batch_processing_loop())
    
    async def _batch_processing_loop(self) -> None:
        """Background loop for batch processing."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for batch timeout or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.integration_config.batch_timeout_seconds
                )
                
                if self._shutdown_event.is_set():
                    break
                
                # Process batch
                await self._process_batch()
                
            except asyncio.TimeoutError:
                # Timeout - continue with next iteration
                continue
            except Exception as e:
                self.logger.error(
                    "Batch processing loop error",
                    error=str(e)
                )
                await asyncio.sleep(5.0)  # Brief pause before retrying
    
    async def _process_event_realtime(self, event: TelemetryEvent) -> List[Alert]:
        """Process event in real-time."""
        alerts = []
        
        try:
            # Generate alerts from alert engine
            engine_alerts = await self.alert_engine.evaluate_event(event)
            alerts.extend(engine_alerts)
            
            # Generate threshold alerts
            if self.integration_config.enable_threshold_monitoring:
                # Extract metrics from event
                metrics = self._extract_metrics(event)
                threshold_alerts = await self.evaluate_thresholds(metrics, {
                    "selector_name": event.selector_name,
                    "correlation_id": event.correlation_id,
                    "timestamp": event.timestamp
                })
                alerts.extend(threshold_alerts)
            
            # Generate anomaly alerts
            if self.integration_config.enable_anomaly_detection:
                metrics = self._extract_metrics(event)
                anomaly_alerts = await self.detect_anomalies(metrics, {
                    "selector_name": event.selector_name,
                    "correlation_id": event.correlation_id,
                    "timestamp": event.timestamp
                })
                alerts.extend(anomaly_alerts)
            
            # Classify severity
            if self.integration_config.enable_severity_classification:
                for alert in alerts:
                    alert = await self.classify_alert_severity(alert, event)
            
            # Send notifications
            if self.integration_config.enable_notifications and alerts:
                notification_results = await self.send_notifications(alerts)
                
                # Update statistics
                success_count = sum(1 for r in notification_results if r["status"] == "sent")
                self._integration_stats["notifications_sent"] += success_count
            
            # Manage alert lifecycle
            if self.integration_config.enable_lifecycle_management:
                for alert in alerts:
                    # Auto-acknowledge critical alerts if configured
                    if alert.severity in [AlertSeverity.CRITICAL]:
                        await self.alert_manager.acknowledge_alert(
                            alert.alert_id,
                            "system",
                            f"Auto-acknowledged critical alert: {alert.title}"
                        )
            
            return alerts
            
        except Exception as e:
            self.logger.error(
                "Failed to process event in real-time",
                event_id=event.event_id,
                error=str(e)
            )
            return []
    
    async def _process_batch(self) -> List[Alert]:
        """Process batch of events."""
        try:
            async with self._batch_lock:
                if not self._batch_queue:
                    return []
                
                events = self._batch_queue.copy()
                self._batch_queue.clear()
            
            alerts = []
            
            # Process each event in batch
            for event in events:
                event_alerts = await self.process_telemetry_event(event)
                alerts.extend(event_alerts)
            
            return alerts
            
        except Exception as e:
            self.logger.error(
                "Failed to process batch",
                error=str(e)
            )
            return []
    
    def _extract_metrics(self, event: TelemetryEvent) -> Dict[str, float]:
        """Extract metrics from telemetry event."""
        metrics = {}
        
        # Performance metrics
        if event.performance_metrics:
            perf = event.performance_metrics
            metrics["resolution_time_ms"] = perf.resolution_time_ms
            metrics["strategy_execution_time_ms"] = perf.strategy_execution_time_ms
            metrics["total_duration_ms"] = perf.total_duration_ms
            metrics["memory_usage_mb"] = perf.memory_usage_mb or 0.0
            metrics["cpu_usage_percent"] = perf.cpu_usage_percent or 0.0
            metrics["network_requests_count"] = perf.network_requests_count or 0
            metrics["dom_operations_count"] = perf.dom_operations_count or 0
        
        # Quality metrics
        if event.quality_metrics:
            quality = event.quality_metrics
            metrics["confidence_score"] = quality.confidence_score or 0.0
            metrics["success_rate"] = 1.0 if quality.success else 0.0
            metrics["elements_found"] = float(quality.elements_found) if quality.elements_found is not None else 0.0
            metrics["strategy_success_rate"] = quality.strategy_success_rate or 0.0
        
        # Strategy metrics
        if event.strategy_metrics:
            strategy = event.strategy_metrics
            metrics["strategy_switches_count"] = float(strategy.strategy_switches_count)
        
        return metrics
    
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
