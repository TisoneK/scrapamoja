"""
Alert Thresholds Configuration

Configuration management for alert thresholds with validation,
persistence, and dynamic adjustment capabilities.
"""

import json
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio

from ..alerting.threshold_monitor import ThresholdConfig, ThresholdType, ComparisonOperator
from ..interfaces import AlertSeverity, AlertType
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryConfigurationError
from ..configuration.logging import get_logger


@dataclass
class ThresholdTemplate:
    """Template for creating threshold configurations."""
    template_id: str
    name: str
    description: str
    metric_name: str
    threshold_type: ThresholdType
    comparison: ComparisonOperator
    default_threshold: float
    severity: AlertSeverity
    tags: List[str]
    validation_rules: Dict[str, Any]
    recommended_cooldown_minutes: int
    recommended_evaluation_window_minutes: int
    recommended_min_samples: int


@dataclass
class ThresholdProfile:
    """Profile containing related thresholds for a specific use case."""
    profile_id: str
    name: str
    description: str
    use_case: str
    thresholds: List[str]  # Threshold IDs
    enabled: bool
    created_at: datetime
    last_updated: datetime


class AlertThresholdsConfiguration:
    """
    Configuration management for alert thresholds.
    
    Provides comprehensive threshold configuration with validation,
    persistence, and dynamic adjustment capabilities.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize alert thresholds configuration.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("alert_thresholds")
        
        # Configuration paths
        self.config_dir = Path(config.get_storage_path()) / "alerting"
        self.thresholds_file = self.config_dir / "thresholds.json"
        self.profiles_file = self.config_dir / "profiles.json"
        self.templates_file = self.config_dir / "templates.json"
        
        # Configuration storage
        self._thresholds: Dict[str, ThresholdConfig] = {}
        self._profiles: Dict[str, ThresholdProfile] = {}
        self._templates: Dict[str, ThresholdTemplate] = {}
        self._config_lock = asyncio.Lock()
        
        # Ensure configuration directory exists
        self._ensure_config_directory()
        
        # Load configurations
        asyncio.create_task(self._load_configurations())
        
        # Initialize default templates
        self._initialize_default_templates()
    
    async def add_threshold(self, threshold: ThresholdConfig) -> bool:
        """
        Add a threshold configuration.
        
        Args:
            threshold: Threshold configuration to add
            
        Returns:
            True if successfully added
        """
        try:
            # Validate threshold
            validation_errors = await self._validate_threshold(threshold)
            if validation_errors:
                raise TelemetryConfigurationError(
                    f"Threshold validation failed: {'; '.join(validation_errors)}",
                    error_code="TEL-901"
                )
            
            async with self._config_lock:
                self._thresholds[threshold.threshold_id] = threshold
            
            # Save configuration
            await self._save_thresholds()
            
            self.logger.info(
                "Threshold added to configuration",
                threshold_id=threshold.threshold_id,
                name=threshold.name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add threshold to configuration",
                threshold_id=threshold.threshold_id,
                error=str(e)
            )
            return False
    
    async def remove_threshold(self, threshold_id: str) -> bool:
        """
        Remove a threshold configuration.
        
        Args:
            threshold_id: Threshold ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._config_lock:
                if threshold_id in self._thresholds:
                    del self._thresholds[threshold_id]
                    
                    # Save configuration
                    await self._save_thresholds()
                    
                    self.logger.info(
                        "Threshold removed from configuration",
                        threshold_id=threshold_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove threshold from configuration",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def update_threshold(self, threshold_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a threshold configuration.
        
        Args:
            threshold_id: Threshold ID to update
            updates: Updates to apply
            
        Returns:
            True if successfully updated
        """
        try:
            async with self._config_lock:
                if threshold_id not in self._thresholds:
                    return False
                
                threshold = self._thresholds[threshold_id]
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(threshold, key):
                        setattr(threshold, key, value)
                
                # Validate updated threshold
                validation_errors = await self._validate_threshold(threshold)
                if validation_errors:
                    raise TelemetryConfigurationError(
                        f"Updated threshold validation failed: {'; '.join(validation_errors)}",
                        error_code="TEL-902"
                    )
                
                # Save configuration
                await self._save_thresholds()
                
                self.logger.info(
                    "Threshold updated in configuration",
                    threshold_id=threshold_id,
                    updates=updates
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to update threshold in configuration",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def get_threshold(self, threshold_id: str) -> Optional[ThresholdConfig]:
        """
        Get a threshold configuration.
        
        Args:
            threshold_id: Threshold ID
            
        Returns:
            Threshold configuration or None if not found
        """
        try:
            async with self._config_lock:
                return self._thresholds.get(threshold_id)
                
        except Exception as e:
            self.logger.error(
                "Failed to get threshold from configuration",
                threshold_id=threshold_id,
                error=str(e)
            )
            return None
    
    async def get_all_thresholds(self) -> List[ThresholdConfig]:
        """
        Get all threshold configurations.
        
        Returns:
            List of all threshold configurations
        """
        try:
            async with self._config_lock:
                return list(self._thresholds.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all thresholds from configuration",
                error=str(e)
            )
            return []
    
    async def get_thresholds_by_metric(self, metric_name: str) -> List[ThresholdConfig]:
        """
        Get thresholds for a specific metric.
        
        Args:
            metric_name: Metric name
            
        Returns:
            List of threshold configurations for the metric
        """
        try:
            async with self._config_lock:
                return [
                    threshold for threshold in self._thresholds.values()
                    if threshold.metric_name == metric_name
                ]
                
        except Exception as e:
            self.logger.error(
                "Failed to get thresholds by metric",
                metric_name=metric_name,
                error=str(e)
            )
            return []
    
    async def get_thresholds_by_severity(self, severity: AlertSeverity) -> List[ThresholdConfig]:
        """
        Get thresholds by severity level.
        
        Args:
            severity: Alert severity
            
        Returns:
            List of threshold configurations with specified severity
        """
        try:
            async with self._config_lock:
                return [
                    threshold for threshold in self._thresholds.values()
                    if threshold.severity == severity
                ]
                
        except Exception as e:
            self.logger.error(
                "Failed to get thresholds by severity",
                severity=severity.value,
                error=str(e)
            )
            return []
    
    async def create_threshold_from_template(
        self,
        template_id: str,
        threshold_id: str,
        threshold_value: float,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[ThresholdConfig]:
        """
        Create a threshold from a template.
        
        Args:
            template_id: Template ID
            threshold_id: New threshold ID
            threshold_value: Threshold value
            overrides: Optional configuration overrides
            
        Returns:
            Created threshold configuration or None if template not found
        """
        try:
            async with self._config_lock:
                if template_id not in self._templates:
                    return None
                
                template = self._templates[template_id]
                
                # Create threshold from template
                threshold = ThresholdConfig(
                    threshold_id=threshold_id,
                    name=template.name,
                    description=template.description,
                    metric_name=template.metric_name,
                    threshold_type=template.threshold_type,
                    comparison=template.comparison,
                    threshold_value=threshold_value,
                    severity=template.severity,
                    tags=template.tags.copy(),
                    cooldown_minutes=template.recommended_cooldown_minutes,
                    evaluation_window_minutes=template.recommended_evaluation_window_minutes,
                    min_samples=template.recommended_min_samples
                )
                
                # Apply overrides
                if overrides:
                    for key, value in overrides.items():
                        if hasattr(threshold, key):
                            setattr(threshold, key, value)
                
                # Validate threshold
                validation_errors = await self._validate_threshold(threshold)
                if validation_errors:
                    raise TelemetryConfigurationError(
                        f"Created threshold validation failed: {'; '.join(validation_errors)}",
                        error_code="TEL-903"
                    )
                
                # Add threshold
                self._thresholds[threshold_id] = threshold
                
                # Save configuration
                await self._save_thresholds()
                
                self.logger.info(
                    "Threshold created from template",
                    template_id=template_id,
                    threshold_id=threshold_id,
                    threshold_value=threshold_value
                )
                
                return threshold
                
        except Exception as e:
            self.logger.error(
                "Failed to create threshold from template",
                template_id=template_id,
                error=str(e)
            )
            return None
    
    async def add_template(self, template: ThresholdTemplate) -> bool:
        """
        Add a threshold template.
        
        Args:
            template: Template to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._config_lock:
                self._templates[template.template_id] = template
                
            # Save templates
            await self._save_templates()
            
            self.logger.info(
                "Template added",
                template_id=template.template_id,
                name=template.name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add template",
                template_id=template.template_id,
                error=str(e)
            )
            return False
    
    async def get_template(self, template_id: str) -> Optional[ThresholdTemplate]:
        """
        Get a threshold template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template or None if not found
        """
        try:
            async with self._config_lock:
                return self._templates.get(template_id)
                
        except Exception as e:
            self.logger.error(
                "Failed to get template",
                template_id=template_id,
                error=str(e)
            )
            return None
    
    async def get_all_templates(self) -> List[ThresholdTemplate]:
        """
        Get all threshold templates.
        
        Returns:
            List of all templates
        """
        try:
            async with self._config_lock:
                return list(self._templates.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all templates",
                error=str(e)
            )
            return []
    
    async def create_profile(
        self,
        profile_id: str,
        name: str,
        description: str,
        use_case: str,
        threshold_ids: List[str]
    ) -> bool:
        """
        Create a threshold profile.
        
        Args:
            profile_id: Profile ID
            name: Profile name
            description: Profile description
            use_case: Use case description
            threshold_ids: List of threshold IDs to include
            
        Returns:
            True if successfully created
        """
        try:
            # Validate threshold IDs
            async with self._config_lock:
                for threshold_id in threshold_ids:
                    if threshold_id not in self._thresholds:
                        raise TelemetryConfigurationError(
                            f"Threshold not found: {threshold_id}",
                            error_code="TEL-904"
                        )
                
                profile = ThresholdProfile(
                    profile_id=profile_id,
                    name=name,
                    description=description,
                    use_case=use_case,
                    thresholds=threshold_ids,
                    enabled=True,
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                
                self._profiles[profile_id] = profile
                
                # Save profiles
                await self._save_profiles()
                
                self.logger.info(
                    "Profile created",
                    profile_id=profile_id,
                    name=name,
                    threshold_count=len(threshold_ids)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to create profile",
                profile_id=profile_id,
                error=str(e)
            )
            return False
    
    async def get_profile(self, profile_id: str) -> Optional[ThresholdProfile]:
        """
        Get a threshold profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Profile or None if not found
        """
        try:
            async with self._config_lock:
                return self._profiles.get(profile_id)
                
        except Exception as e:
            self.logger.error(
                "Failed to get profile",
                profile_id=profile_id,
                error=str(e)
            )
            return None
    
    async def get_all_profiles(self) -> List[ThresholdProfile]:
        """
        Get all threshold profiles.
        
        Returns:
            List of all profiles
        """
        try:
            async with self._config_lock:
                return list(self._profiles.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all profiles",
                error=str(e)
            )
            return []
    
    async def enable_profile(self, profile_id: str) -> bool:
        """
        Enable a profile and its thresholds.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            True if successfully enabled
        """
        try:
            async with self._config_lock:
                if profile_id not in self._profiles:
                    return False
                
                profile = self._profiles[profile_id]
                profile.enabled = True
                profile.last_updated = datetime.utcnow()
                
                # Enable all thresholds in profile
                for threshold_id in profile.thresholds:
                    if threshold_id in self._thresholds:
                        self._thresholds[threshold_id].enabled = True
                
                # Save configurations
                await self._save_profiles()
                await self._save_thresholds()
                
                self.logger.info(
                    "Profile enabled",
                    profile_id=profile_id,
                    threshold_count=len(profile.thresholds)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to enable profile",
                profile_id=profile_id,
                error=str(e)
            )
            return False
    
    async def disable_profile(self, profile_id: str) -> bool:
        """
        Disable a profile and its thresholds.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            True if successfully disabled
        """
        try:
            async with self._config_lock:
                if profile_id not in self._profiles:
                    return False
                
                profile = self._profiles[profile_id]
                profile.enabled = False
                profile.last_updated = datetime.utcnow()
                
                # Disable all thresholds in profile
                for threshold_id in profile.thresholds:
                    if threshold_id in self._thresholds:
                        self._thresholds[threshold_id].enabled = False
                
                # Save configurations
                await self._save_profiles()
                await self._save_thresholds()
                
                self.logger.info(
                    "Profile disabled",
                    profile_id=profile_id,
                    threshold_count=len(profile.thresholds)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to disable profile",
                profile_id=profile_id,
                error=str(e)
            )
            return False
    
    async def export_configuration(self, include_profiles: bool = True) -> Dict[str, Any]:
        """
        Export configuration to dictionary.
        
        Args:
            include_profiles: Whether to include profiles
            
        Returns:
            Configuration dictionary
        """
        try:
            async with self._config_lock:
                export_data = {
                    "thresholds": {
                        threshold_id: asdict(threshold)
                        for threshold_id, threshold in self._thresholds.items()
                    },
                    "templates": {
                        template_id: asdict(template)
                        for template_id, template in self._templates.items()
                    },
                    "exported_at": datetime.utcnow().isoformat(),
                    "version": "1.0"
                }
                
                if include_profiles:
                    export_data["profiles"] = {
                        profile_id: asdict(profile)
                        for profile_id, profile in self._profiles.items()
                    }
                
                return export_data
                
        except Exception as e:
            self.logger.error(
                "Failed to export configuration",
                error=str(e)
            )
            return {}
    
    async def import_configuration(self, config_data: Dict[str, Any]) -> bool:
        """
        Import configuration from dictionary.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            True if successfully imported
        """
        try:
            async with self._config_lock:
                # Import thresholds
                if "thresholds" in config_data:
                    for threshold_id, threshold_data in config_data["thresholds"].items():
                        threshold = ThresholdConfig(**threshold_data)
                        
                        # Validate threshold
                        validation_errors = await self._validate_threshold(threshold)
                        if validation_errors:
                            self.logger.warning(
                                "Skipping invalid threshold during import",
                                threshold_id=threshold_id,
                                errors=validation_errors
                            )
                            continue
                        
                        self._thresholds[threshold_id] = threshold
                
                # Import templates
                if "templates" in config_data:
                    for template_id, template_data in config_data["templates"].items():
                        template = ThresholdTemplate(**template_data)
                        self._templates[template_id] = template
                
                # Import profiles
                if "profiles" in config_data:
                    for profile_id, profile_data in config_data["profiles"].items():
                        profile = ThresholdProfile(**profile_data)
                        self._profiles[profile_id] = profile
                
                # Save configurations
                await self._save_thresholds()
                await self._save_templates()
                await self._save_profiles()
                
                self.logger.info(
                    "Configuration imported successfully",
                    thresholds_count=len(self._thresholds),
                    templates_count=len(self._templates),
                    profiles_count=len(self._profiles)
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to import configuration",
                error=str(e)
            )
            return False
    
    # Private methods
    
    def _ensure_config_directory(self) -> None:
        """Ensure configuration directory exists."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(
                "Failed to create configuration directory",
                path=str(self.config_dir),
                error=str(e)
            )
    
    async def _load_configurations(self) -> None:
        """Load configurations from files."""
        try:
            # Load thresholds
            if self.thresholds_file.exists():
                with open(self.thresholds_file, 'r') as f:
                    data = json.load(f)
                    
                    for threshold_id, threshold_data in data.items():
                        threshold = ThresholdConfig(**threshold_data)
                        self._thresholds[threshold_id] = threshold
            
            # Load profiles
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r') as f:
                    data = json.load(f)
                    
                    for profile_id, profile_data in data.items():
                        profile = ThresholdProfile(**profile_data)
                        self._profiles[profile_id] = profile
            
            # Load templates
            if self.templates_file.exists():
                with open(self.templates_file, 'r') as f:
                    data = json.load(f)
                    
                    for template_id, template_data in data.items():
                        template = ThresholdTemplate(**template_data)
                        self._templates[template_id] = template
            
            self.logger.info(
                "Configurations loaded",
                thresholds_count=len(self._thresholds),
                profiles_count=len(self._profiles),
                templates_count=len(self._templates)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to load configurations",
                error=str(e)
            )
    
    async def _save_thresholds(self) -> None:
        """Save thresholds to file."""
        try:
            data = {
                threshold_id: asdict(threshold)
                for threshold_id, threshold in self._thresholds.items()
            }
            
            with open(self.thresholds_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(
                "Failed to save thresholds",
                error=str(e)
            )
    
    async def _save_profiles(self) -> None:
        """Save profiles to file."""
        try:
            data = {
                profile_id: asdict(profile)
                for profile_id, profile in self._profiles.items()
            }
            
            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(
                "Failed to save profiles",
                error=str(e)
            )
    
    async def _save_templates(self) -> None:
        """Save templates to file."""
        try:
            data = {
                template_id: asdict(template)
                for template_id, template in self._templates.items()
            }
            
            with open(self.templates_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(
                "Failed to save templates",
                error=str(e)
            )
    
    async def _validate_threshold(self, threshold: ThresholdConfig) -> List[str]:
        """Validate a threshold configuration."""
        errors = []
        
        # Validate required fields
        if not threshold.threshold_id or not threshold.threshold_id.strip():
            errors.append("Threshold ID is required")
        
        if not threshold.name or not threshold.name.strip():
            errors.append("Threshold name is required")
        
        if not threshold.metric_name or not threshold.metric_name.strip():
            errors.append("Metric name is required")
        
        # Validate threshold value
        if threshold.threshold_value is None or not isinstance(threshold.threshold_value, (int, float)):
            errors.append("Threshold value must be a number")
        
        # Validate cooldown
        if threshold.cooldown_minutes < 0:
            errors.append("Cooldown minutes must be non-negative")
        
        # Validate evaluation window
        if threshold.evaluation_window_minutes < 1:
            errors.append("Evaluation window minutes must be at least 1")
        
        # Validate min samples
        if threshold.min_samples < 1:
            errors.append("Min samples must be at least 1")
        
        # Validate metric name format
        if not self._is_valid_metric_name(threshold.metric_name):
            errors.append(f"Invalid metric name format: {threshold.metric_name}")
        
        return errors
    
    def _is_valid_metric_name(self, metric_name: str) -> bool:
        """Validate metric name format."""
        import re
        
        # Allow alphanumeric characters, underscores, and dots
        pattern = r'^[a-zA-Z][a-zA-Z0-9_.]*$'
        return bool(re.match(pattern, metric_name))
    
    def _initialize_default_templates(self) -> None:
        """Initialize default threshold templates."""
        default_templates = [
            ThresholdTemplate(
                template_id="performance_time",
                name="Performance Time",
                description="Template for performance-related time thresholds",
                metric_name="resolution_time_ms",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.GREATER_THAN,
                default_threshold=5000.0,
                severity=AlertSeverity.WARNING,
                tags=["performance", "timing"],
                validation_rules={
                    "min_value": 0,
                    "max_value": 300000  # 5 minutes
                },
                recommended_cooldown_minutes=5,
                recommended_evaluation_window_minutes=10,
                recommended_min_samples=3
            ),
            ThresholdTemplate(
                template_id="quality_confidence",
                name="Quality Confidence",
                description="Template for quality-related confidence thresholds",
                metric_name="confidence_score",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.LESS_THAN,
                default_threshold=0.5,
                severity=AlertSeverity.WARNING,
                tags=["quality", "confidence"],
                validation_rules={
                    "min_value": 0.0,
                    "max_value": 1.0
                },
                recommended_cooldown_minutes=10,
                recommended_evaluation_window_minutes=15,
                recommended_min_samples=5
            ),
            ThresholdTemplate(
                template_id="error_rate",
                name="Error Rate",
                description="Template for error rate thresholds",
                metric_name="error_rate",
                threshold_type=ThresholdType.DYNAMIC,
                comparison=ComparisonOperator.GREATER_THAN,
                default_threshold=0.1,
                severity=AlertSeverity.ERROR,
                tags=["error", "rate"],
                validation_rules={
                    "min_value": 0.0,
                    "max_value": 1.0
                },
                recommended_cooldown_minutes=15,
                recommended_evaluation_window_minutes=30,
                recommended_min_samples=10
            ),
            ThresholdTemplate(
                template_id="strategy_switches",
                name="Strategy Switches",
                description="Template for strategy switching thresholds",
                metric_name="strategy_switches_count",
                threshold_type=ThresholdType.STATIC,
                comparison=ComparisonOperator.GREATER_THAN,
                default_threshold=3.0,
                severity=AlertSeverity.WARNING,
                tags=["strategy", "switches"],
                validation_rules={
                    "min_value": 0,
                    "max_value": 10
                },
                recommended_cooldown_minutes=5,
                recommended_evaluation_window_minutes=10,
                recommended_min_samples=3
            )
        ]
        
        for template in default_templates:
            self._templates[template.template_id] = template
