"""
Configuration validation for telemetry system.

This module provides comprehensive validation for all telemetry configuration
parameters with detailed error reporting and default value handling.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

from ..exceptions import TelemetryConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrected_values: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, field: str, message: str) -> None:
        """Add validation error."""
        self.errors.append(f"{field}: {message}")
        self.is_valid = False
    
    def add_warning(self, field: str, message: str) -> None:
        """Add validation warning."""
        self.warnings.append(f"{field}: {message}")
    
    def add_correction(self, field: str, old_value: Any, new_value: Any) -> None:
        """Add corrected value."""
        self.corrected_values[field] = {
            'old_value': old_value,
            'new_value': new_value
        }


class ConfigurationValidator:
    """Validates telemetry system configuration."""
    
    def __init__(self):
        self.validation_rules = self._get_validation_rules()
    
    def validate_telemetry_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate complete telemetry configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate main sections
        self._validate_collection_config(config.get('collection', {}), result)
        self._validate_storage_config(config.get('storage', {}), result)
        self._validate_alerting_config(config.get('alerting', {}), result)
        self._validate_reporting_config(config.get('reporting', {}), result)
        self._validate_performance_config(config.get('performance', {}), result)
        
        # Validate global settings
        self._validate_global_config(config, result)
        
        return result
    
    def _validate_collection_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate data collection configuration."""
        # Buffer size
        buffer_size = config.get('buffer_size', 1000)
        if not isinstance(buffer_size, int) or buffer_size < 1:
            result.add_error('collection.buffer_size', f'Invalid buffer size: {buffer_size}')
        elif buffer_size > 100000:
            result.add_warning('collection.buffer_size', f'Large buffer size may impact memory: {buffer_size}')
        
        # Batch size
        batch_size = config.get('batch_size', 100)
        if not isinstance(batch_size, int) or batch_size < 1:
            result.add_error('collection.batch_size', f'Invalid batch size: {batch_size}')
        elif batch_size > 10000:
            result.add_warning('collection.batch_size', f'Large batch size may impact performance: {batch_size}')
        
        # Flush interval
        flush_interval = config.get('flush_interval', 1.0)
        if not isinstance(flush_interval, (int, float)) or flush_interval <= 0:
            result.add_error('collection.flush_interval', f'Invalid flush interval: {flush_interval}')
        elif flush_interval > 60:
            result.add_warning('collection.flush_interval', f'Long flush interval may delay data: {flush_interval}s')
        
        # Collection enabled
        enabled = config.get('enabled', True)
        if not isinstance(enabled, bool):
            result.add_correction('collection.enabled', enabled, True)
            config['enabled'] = True
    
    def _validate_storage_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate storage configuration."""
        if not config:
            result.add_error('storage', 'Storage configuration is required')
            return
        
        storage_type = config.get('type', 'json')
        valid_types = ['json', 'influxdb']
        if storage_type not in valid_types:
            result.add_error('storage.type', f'Invalid storage type: {storage_type}')
        
        # JSON storage validation
        if storage_type == 'json':
            self._validate_json_storage_config(config, result)
        
        # InfluxDB storage validation
        elif storage_type == 'influxdb':
            self._validate_influxdb_storage_config(config, result)
        
        # Retention settings
        retention_days = config.get('retention_days', 30)
        if not isinstance(retention_days, int) or retention_days < 1:
            result.add_error('storage.retention_days', f'Invalid retention days: {retention_days}')
        elif retention_days > 365:
            result.add_warning('storage.retention_days', f'Long retention may use significant storage: {retention_days} days')
    
    def _validate_json_storage_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate JSON storage configuration."""
        # Directory path
        directory = config.get('directory', 'telemetry_data')
        if not isinstance(directory, str):
            result.add_error('storage.directory', f'Invalid directory: {directory}')
        else:
            # Check if path is valid
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                result.add_error('storage.directory', f'Cannot create directory: {e}')
        
        # File rotation
        rotation = config.get('file_rotation', {})
        if rotation:
            max_file_size = rotation.get('max_file_size_mb', 100)
            if not isinstance(max_file_size, int) or max_file_size < 1:
                result.add_error('storage.file_rotation.max_file_size_mb', f'Invalid max file size: {max_file_size}')
            
            max_files = rotation.get('max_files', 10)
            if not isinstance(max_files, int) or max_files < 1:
                result.add_error('storage.file_rotation.max_files', f'Invalid max files: {max_files}')
    
    def _validate_influxdb_storage_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate InfluxDB storage configuration."""
        required_fields = ['url', 'token', 'org', 'bucket']
        for field in required_fields:
            if field not in config:
                result.add_error(f'storage.{field}', f'Required field missing: {field}')
            elif not isinstance(config[field], str) or not config[field].strip():
                result.add_error(f'storage.{field}', f'Invalid {field}: {config[field]}')
        
        # Batch settings
        batch_size = config.get('batch_size', 100)
        if not isinstance(batch_size, int) or batch_size < 1:
            result.add_error('storage.batch_size', f'Invalid batch size: {batch_size}')
        
        flush_interval = config.get('flush_interval', 1.0)
        if not isinstance(flush_interval, (int, float)) or flush_interval <= 0:
            result.add_error('storage.flush_interval', f'Invalid flush interval: {flush_interval}')
    
    def _validate_alerting_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate alerting configuration."""
        # Alerting enabled
        enabled = config.get('enabled', True)
        if not isinstance(enabled, bool):
            result.add_correction('alerting.enabled', enabled, True)
            config['enabled'] = True
        
        if not enabled:
            return  # Skip validation if disabled
        
        # Thresholds
        thresholds = config.get('thresholds', {})
        self._validate_performance_thresholds(thresholds.get('performance', {}), result)
        self._validate_quality_thresholds(thresholds.get('quality', {}), result)
        self._validate_health_thresholds(thresholds.get('health', {}), result)
        
        # Notification settings
        notifications = config.get('notifications', {})
        self._validate_notification_config(notifications, result)
    
    def _validate_performance_thresholds(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate performance alert thresholds."""
        # Resolution time threshold
        resolution_time = config.get('resolution_time_ms', 5000)
        if not isinstance(resolution_time, (int, float)) or resolution_time <= 0:
            result.add_error('alerting.thresholds.performance.resolution_time_ms', f'Invalid threshold: {resolution_time}')
        
        # Memory usage threshold
        memory_usage = config.get('memory_usage_mb', 100)
        if not isinstance(memory_usage, (int, float)) or memory_usage <= 0:
            result.add_error('alerting.thresholds.performance.memory_usage_mb', f'Invalid threshold: {memory_usage}')
        
        # Error rate threshold
        error_rate = config.get('error_rate_percent', 5.0)
        if not isinstance(error_rate, (int, float)) or not (0 <= error_rate <= 100):
            result.add_error('alerting.thresholds.performance.error_rate_percent', f'Invalid threshold: {error_rate}')
    
    def _validate_quality_thresholds(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate quality alert thresholds."""
        # Confidence score threshold
        confidence_score = config.get('confidence_score', 0.7)
        if not isinstance(confidence_score, (int, float)) or not (0 <= confidence_score <= 1):
            result.add_error('alerting.thresholds.quality.confidence_score', f'Invalid threshold: {confidence_score}')
        
        # Quality decline threshold
        quality_decline = config.get('decline_percent', 20.0)
        if not isinstance(quality_decline, (int, float)) or not (0 <= quality_decline <= 100):
            result.add_error('alerting.thresholds.quality.decline_percent', f'Invalid threshold: {quality_decline}')
    
    def _validate_health_thresholds(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate health alert thresholds."""
        # Anomaly detection threshold
        anomaly_threshold = config.get('anomaly_threshold', 2.0)
        if not isinstance(anomaly_threshold, (int, float)) or anomaly_threshold <= 0:
            result.add_error('alerting.thresholds.health.anomaly_threshold', f'Invalid threshold: {anomaly_threshold}')
        
        # Timeout frequency threshold
        timeout_frequency = config.get('timeout_frequency_percent', 10.0)
        if not isinstance(timeout_frequency, (int, float)) or not (0 <= timeout_frequency <= 100):
            result.add_error('alerting.thresholds.health.timeout_frequency_percent', f'Invalid threshold: {timeout_frequency}')
    
    def _validate_notification_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate notification configuration."""
        # Notification channels
        channels = config.get('channels', [])
        if not isinstance(channels, list):
            result.add_error('alerting.notifications.channels', f'Invalid channels: {channels}')
        else:
            valid_channels = ['log', 'email', 'webhook', 'slack']
            for channel in channels:
                if channel not in valid_channels:
                    result.add_warning('alerting.notifications.channels', f'Unknown channel: {channel}')
        
        # Rate limiting
        rate_limit = config.get('rate_limit', {})
        if rate_limit:
            max_per_hour = rate_limit.get('max_per_hour', 10)
            if not isinstance(max_per_hour, int) or max_per_hour < 1:
                result.add_error('alerting.notifications.rate_limit.max_per_hour', f'Invalid rate limit: {max_per_hour}')
    
    def _validate_reporting_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate reporting configuration."""
        # Reporting enabled
        enabled = config.get('enabled', True)
        if not isinstance(enabled, bool):
            result.add_correction('reporting.enabled', enabled, True)
            config['enabled'] = True
        
        if not enabled:
            return  # Skip validation if disabled
        
        # Report types
        report_types = config.get('types', ['performance', 'usage', 'health'])
        if not isinstance(report_types, list):
            result.add_error('reporting.types', f'Invalid report types: {report_types}')
        else:
            valid_types = ['performance', 'usage', 'health', 'trends', 'recommendations']
            for report_type in report_types:
                if report_type not in valid_types:
                    result.add_warning('reporting.types', f'Unknown report type: {report_type}')
        
        # Scheduling
        schedule = config.get('schedule', {})
        if schedule:
            frequency = schedule.get('frequency', 'daily')
            valid_frequencies = ['hourly', 'daily', 'weekly', 'monthly']
            if frequency not in valid_frequencies:
                result.add_error('reporting.schedule.frequency', f'Invalid frequency: {frequency}')
            
            # Time of day (for daily/weekly)
            time_of_day = schedule.get('time_of_day', '00:00')
            if isinstance(time_of_day, str):
                try:
                    hour, minute = map(int, time_of_day.split(':'))
                    if not (0 <= hour < 24 and 0 <= minute < 60):
                        result.add_error('reporting.schedule.time_of_day', f'Invalid time: {time_of_day}')
                except ValueError:
                    result.add_error('reporting.schedule.time_of_day', f'Invalid time format: {time_of_day}')
    
    def _validate_performance_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate performance configuration."""
        # Performance overhead target
        overhead_target = config.get('overhead_target_percent', 2.0)
        if not isinstance(overhead_target, (int, float)) or not (0 < overhead_target <= 10):
            result.add_error('performance.overhead_target_percent', f'Invalid overhead target: {overhead_target}')
        
        # Memory threshold
        memory_threshold = config.get('memory_threshold_mb', 100)
        if not isinstance(memory_threshold, (int, float)) or memory_threshold <= 0:
            result.add_error('performance.memory_threshold_mb', f'Invalid memory threshold: {memory_threshold}')
        
        # Cache settings
        cache = config.get('cache', {})
        if cache:
            cache_size = cache.get('size', 1000)
            if not isinstance(cache_size, int) or cache_size < 1:
                result.add_error('performance.cache.size', f'Invalid cache size: {cache_size}')
            
            ttl = cache.get('ttl_seconds', 300)
            if not isinstance(ttl, (int, float)) or ttl <= 0:
                result.add_error('performance.cache.ttl_seconds', f'Invalid cache TTL: {ttl}')
    
    def _validate_global_config(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate global configuration settings."""
        # Logging level
        log_level = config.get('log_level', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level not in valid_levels:
            result.add_error('log_level', f'Invalid log level: {log_level}')
        
        # Correlation ID length
        correlation_id_length = config.get('correlation_id_length', 8)
        if not isinstance(correlation_id_length, int) or not (4 <= correlation_id_length <= 32):
            result.add_error('correlation_id_length', f'Invalid correlation ID length: {correlation_id_length}')
        
        # Component timeouts
        timeouts = config.get('timeouts', {})
        if timeouts:
            for component, timeout in timeouts.items():
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    result.add_error(f'timeouts.{component}', f'Invalid timeout: {timeout}')
    
    def _get_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get validation rules for configuration fields."""
        return {
            'collection': {
                'buffer_size': {'type': int, 'min': 1, 'max': 100000},
                'batch_size': {'type': int, 'min': 1, 'max': 10000},
                'flush_interval': {'type': (int, float), 'min': 0.1, 'max': 60},
                'enabled': {'type': bool},
            },
            'storage': {
                'type': {'type': str, 'choices': ['json', 'influxdb']},
                'retention_days': {'type': int, 'min': 1, 'max': 365},
            },
            'alerting': {
                'enabled': {'type': bool},
            },
            'reporting': {
                'enabled': {'type': bool},
            },
            'performance': {
                'overhead_target_percent': {'type': (int, float), 'min': 0.1, 'max': 10},
                'memory_threshold_mb': {'type': (int, float), 'min': 10},
            },
        }


def validate_configuration(config: Dict[str, Any]) -> ValidationResult:
    """Validate telemetry configuration."""
    validator = ConfigurationValidator()
    return validator.validate_telemetry_config(config)


def apply_corrections(config: Dict[str, Any], result: ValidationResult) -> Dict[str, Any]:
    """Apply automatic corrections to configuration."""
    corrected_config = config.copy()
    
    for field, correction in result.corrected_values.items():
        keys = field.split('.')
        current = corrected_config
        
        # Navigate to the field
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Apply correction
        current[keys[-1]] = correction['new_value']
        
        logger.info(f"Applied correction to {field}: {correction['old_value']} -> {correction['new_value']}")
    
    return corrected_config
