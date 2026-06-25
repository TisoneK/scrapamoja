"""
Configuration management for the Stealth & Anti-Detection System.

Provides default configurations and configuration loading from files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .models import (
    StealthConfig,
    BrowserFingerprint,
    BehaviorIntensity,
    FingerprintConsistencyLevel,
    ProxyRotationStrategy,
)


# Default production configuration
DEFAULT_CONFIG = StealthConfig(
    enabled=True,
    fingerprint=None,  # Auto-generate
    fingerprint_consistency_level=FingerprintConsistencyLevel.MODERATE,
    proxy_enabled=True,
    proxy_rotation_strategy=ProxyRotationStrategy.PER_MATCH,
    proxy_cooldown_seconds=600,
    proxy_provider="bright_data",
    behavior_enabled=True,
    behavior_intensity=BehaviorIntensity.MODERATE,
    click_hesitation_ms_range=(100, 500),
    scroll_variation=0.3,
    micro_delay_ms_range=(10, 100),
    consent_enabled=True,
    consent_aggressive=False,
    consent_timeout_seconds=5,
    anti_detection_enabled=True,
    mask_webdriver_property=True,
    mask_playwright_indicators=True,
    mask_process_property=True,
    graceful_degradation=True,
    logging_level="info",
)

# Development configuration (no real proxy)
DEVELOPMENT_CONFIG = StealthConfig(
    enabled=True,
    proxy_enabled=False,  # No proxy in development
    proxy_provider="mock",
    behavior_enabled=True,
    behavior_intensity=BehaviorIntensity.MODERATE,
    consent_enabled=True,
    anti_detection_enabled=True,
    graceful_degradation=True,
    logging_level="debug",
)

# Conservative configuration (high-risk targets)
CONSERVATIVE_CONFIG = StealthConfig(
    enabled=True,
    fingerprint_consistency_level=FingerprintConsistencyLevel.STRICT,
    proxy_enabled=True,
    proxy_rotation_strategy=ProxyRotationStrategy.PER_MATCH,
    proxy_cooldown_seconds=1200,  # Longer cooldown
    behavior_enabled=True,
    behavior_intensity=BehaviorIntensity.CONSERVATIVE,
    click_hesitation_ms_range=(200, 800),  # Longer hesitation
    scroll_variation=0.5,  # More variation
    consent_enabled=True,
    consent_aggressive=False,
    anti_detection_enabled=True,
    graceful_degradation=True,
    logging_level="info",
)

# Aggressive configuration (low-risk targets)
AGGRESSIVE_CONFIG = StealthConfig(
    enabled=True,
    proxy_enabled=False,  # Skip proxy overhead
    behavior_enabled=True,
    behavior_intensity=BehaviorIntensity.AGGRESSIVE,
    click_hesitation_ms_range=(50, 200),  # Shorter hesitation
    scroll_variation=0.1,  # Less variation
    consent_enabled=True,
    consent_aggressive=True,  # Aggressive consent acceptance
    anti_detection_enabled=False,  # Skip masking
    graceful_degradation=True,
)


def load_config_from_file(config_file: Path) -> StealthConfig:
    """
    Load stealth configuration from YAML file.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        StealthConfig instance
        
    Raises:
        FileNotFoundError: If config file not found
        ValueError: If configuration is invalid
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    
    if not data or "stealth" not in data:
        raise ValueError(f"Invalid config file: missing 'stealth' section")
    
    return _build_config_from_dict(data["stealth"])


def _build_config_from_dict(config_dict: Dict[str, Any]) -> StealthConfig:
    """
    Build StealthConfig from dictionary.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        StealthConfig instance
    """
    # Extract top-level config
    config = StealthConfig()
    
    # Update from dictionary
    if "enabled" in config_dict:
        config.enabled = config_dict["enabled"]
    
    if "logging_level" in config_dict:
        config.logging_level = config_dict["logging_level"]
    
    # Fingerprint section
    if "fingerprint" in config_dict:
        fingerprint_cfg = config_dict["fingerprint"]
        config.fingerprint_consistency_level = FingerprintConsistencyLevel(
            fingerprint_cfg.get("consistency_level", "moderate")
        )
    
    # Proxy section
    if "proxy" in config_dict:
        proxy_cfg = config_dict["proxy"]
        config.proxy_enabled = proxy_cfg.get("enabled", True)
        config.proxy_rotation_strategy = ProxyRotationStrategy(
            proxy_cfg.get("rotation_strategy", "per_match")
        )
        config.proxy_cooldown_seconds = proxy_cfg.get("cooldown_seconds", 600)
        config.proxy_provider = proxy_cfg.get("provider", "bright_data")
        config.proxy_provider_config = proxy_cfg.get("provider_config", {})
    
    # Behavior section
    if "behavior" in config_dict:
        behavior_cfg = config_dict["behavior"]
        config.behavior_enabled = behavior_cfg.get("enabled", True)
        config.behavior_intensity = BehaviorIntensity(
            behavior_cfg.get("intensity", "moderate")
        )
        if "click_hesitation_range" in behavior_cfg:
            config.click_hesitation_ms_range = tuple(behavior_cfg["click_hesitation_range"])
        config.scroll_variation = behavior_cfg.get("scroll_variation", 0.3)
        if "micro_delay_range" in behavior_cfg:
            config.micro_delay_ms_range = tuple(behavior_cfg["micro_delay_range"])
    
    # Consent section
    if "consent" in config_dict:
        consent_cfg = config_dict["consent"]
        config.consent_enabled = consent_cfg.get("enabled", True)
        config.consent_aggressive = consent_cfg.get("aggressive", False)
        config.consent_timeout_seconds = consent_cfg.get("timeout_seconds", 5)
    
    # Anti-detection section
    if "anti_detection" in config_dict:
        anti_cfg = config_dict["anti_detection"]
        config.anti_detection_enabled = anti_cfg.get("enabled", True)
        config.mask_webdriver_property = anti_cfg.get("mask_webdriver", True)
        config.mask_playwright_indicators = anti_cfg.get("mask_playwright", True)
        config.mask_process_property = anti_cfg.get("mask_process", True)
    
    # Resilience section
    if "graceful_degradation" in config_dict:
        config.graceful_degradation = config_dict["graceful_degradation"]
    
    return config


def get_config_by_name(name: str) -> StealthConfig:
    """
    Get predefined configuration by name.
    
    Args:
        name: Configuration name ('default', 'development', 'conservative', 'aggressive')
        
    Returns:
        StealthConfig instance
        
    Raises:
        ValueError: If configuration name not recognized
    """
    configs = {
        "default": DEFAULT_CONFIG,
        "development": DEVELOPMENT_CONFIG,
        "conservative": CONSERVATIVE_CONFIG,
        "aggressive": AGGRESSIVE_CONFIG,
    }
    
    if name not in configs:
        raise ValueError(f"Unknown config: {name}. Available: {list(configs.keys())}")
    
    return configs[name]
