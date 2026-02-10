"""
Configuration module for the modular site scraper template.

This module contains configuration classes for different environments
and feature flags management.
"""

from .base import BaseConfig
from .dev import DevConfig
from .prod import ProdConfig
from .feature_flags import FeatureFlags

__all__ = [
    'BaseConfig',
    'DevConfig', 
    'ProdConfig',
    'FeatureFlags'
]

# Version information
__version__ = "1.0.0"
__author__ = "Modular Scraper Template"

# Configuration registry for easy access
CONFIG_REGISTRY = {
    'base': BaseConfig,
    'dev': DevConfig,
    'prod': ProdConfig
}

def get_config(config_type: str):
    """
    Get configuration class by type.
    
    Args:
        config_type: Type of configuration ('base', 'dev', 'prod')
        
    Returns:
        Configuration class
        
    Raises:
        ValueError: If config type is not found
    """
    if config_type not in CONFIG_REGISTRY:
        raise ValueError(f"Unknown config type: {config_type}. Available types: {list(CONFIG_REGISTRY.keys())}")
    
    return CONFIG_REGISTRY[config_type]

def list_available_configs():
    """List all available configuration types."""
    return list(CONFIG_REGISTRY.keys())

# Environment detection
def detect_environment() -> str:
    """
    Detect the current environment.
    
    Returns:
        Environment name ('dev', 'staging', 'prod')
    """
    import os
    
    # Check environment variable
    env = os.getenv('SCRAPER_ENV', '').lower()
    if env in ['dev', 'development', 'local']:
        return 'dev'
    elif env in ['prod', 'production']:
        return 'prod'
    elif env in ['staging', 'test']:
        return 'staging'
    
    # Default to development
    return 'dev'

def get_config_for_environment(environment: str = None):
    """
    Get configuration for a specific environment.
    
    Args:
        environment: Environment name (auto-detected if None)
        
    Returns:
        Configuration instance
    """
    if environment is None:
        environment = detect_environment()
    
    config_class = get_config(environment)
    return config_class()
