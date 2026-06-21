"""
GitHub scraper configuration.

This module contains configuration settings for the GitHub scraper,
including site-specific settings, rate limiting, and feature flags.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


# GitHub Site Configuration
SITE_DOMAIN = "github.com"
SUPPORTED_DOMAINS = ["github.com", "api.github.com", "gist.github.com"]

# Template Configuration
TEMPLATE_NAME = "github"
TEMPLATE_VERSION = "1.0.0"
TEMPLATE_DESCRIPTION = "GitHub repository and user data scraper"
TEMPLATE_AUTHOR = "Scorewise Team"
FRAMEWORK_VERSION = "1.0.0"

# GitHub-Specific Settings
GITHUB_BASE_URL = "https://github.com"
GITHUB_API_URL = "https://api.github.com"
GITHUB_SEARCH_URL = "https://github.com/search"

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS_PER_HOUR = 60  # GitHub unauthenticated rate limit
RATE_LIMIT_REQUESTS_PER_MINUTE = 10  # Conservative limit
RATE_LIMIT_WAIT_TIME = 60  # Seconds to wait when rate limited

# Request Configuration
REQUEST_TIMEOUT = 30000  # 30 seconds in milliseconds
PAGE_LOAD_TIMEOUT = 10000  # 10 seconds
ELEMENT_WAIT_TIMEOUT = 5000  # 5 seconds

# Pagination Configuration
DEFAULT_PAGE_SIZE = 20
MAX_PAGES_PER_SEARCH = 10
MAX_ISSUES_PER_REPOSITORY = 100

# Search Configuration
DEFAULT_SEARCH_TYPE = "repositories"
SEARCH_TYPES = ["repositories", "users", "issues", "commits", "code"]
SEARCH_SORT_OPTIONS = ["stars", "forks", "updated", "created"]
SEARCH_ORDER_OPTIONS = ["desc", "asc"]

# Data Extraction Configuration
EXTRACTION_ENABLED = True
EXTRACTION_RETRY_COUNT = 3
EXTRACTION_RETRY_DELAY = 1.0  # Seconds

# Selector Configuration
SELECTOR_CONFIDENCE_THRESHOLD = 0.7
SELECTOR_VALIDATION_ENABLED = True
SELECTOR_CACHE_ENABLED = True

# Feature Flags
ENABLE_USER_SCRAPING = True
ENABLE_ISSUE_SCRAPING = True
ENABLE_REPOSITORY_SCRAPING = True
ENABLE_SEARCH_SCRAPING = True
ENABLE_PAGINATION = True
ENABLE_STEALTH_MODE = True

# Stealth Configuration
STEALTH_ENABLED = True
STEALTH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
STEALTH_VIEWPORT = {"width": 1920, "height": 1080}
STEALTH_LOCALE = "en-US"
STEALTH_TIMEZONE = "America/New_York"

# Browser Configuration
BROWSER_HEADLESS = False  # Set to True for production
BROWSER_SLOWMO = 100  # Milliseconds
BROWSER_IGNORE_HTTPS_ERRORS = True

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_STRUCTURED = True
LOG_PERFORMANCE_METRICS = True

# Cache Configuration
CACHE_ENABLED = True
CACHE_TTL = 3600  # 1 hour in seconds
CACHE_MAX_SIZE = 1000

# Error Handling Configuration
ERROR_RETRY_ENABLED = True
ERROR_RETRY_COUNT = 3
ERROR_RETRY_BACKOFF_FACTOR = 2.0
ERROR_RETRY_MAX_DELAY = 60.0

# Monitoring Configuration
MONITORING_ENABLED = True
MONITORING_METRICS_INTERVAL = 60  # Seconds
MONITORING_PERFORMANCE_TRACKING = True

# Output Configuration
OUTPUT_FORMAT = "json"
OUTPUT_INCLUDE_METADATA = True
OUTPUT_INCLUDE_TIMESTAMPS = True
OUTPUT_INCLUDE_PERFORMANCE_METRICS = False

# Validation Configuration
VALIDATION_ENABLED = True
VALIDATION_STRICT_MODE = False
VALIDATION_SCHEMA_VERSION = "1.0"

# Security Configuration
SECURITY_VALIDATE_SSL = True
SECURITY_BLOCK_TRACKERS = True
SECURITY_BLOCK_ADS = True

# Development Configuration
DEBUG_MODE = False
DEBUG_SAVE_SCREENSHOTS = False
DEBUG_SAVE_HTML = False
DEBUG_LOG_SELECTOR_RESOLUTION = False


def get_github_config() -> Dict[str, Any]:
    """
    Get complete GitHub configuration.
    
    Returns:
        Dict[str, Any]: Complete configuration dictionary
    """
    return {
        # Site Information
        "site": {
            "domain": SITE_DOMAIN,
            "supported_domains": SUPPORTED_DOMAINS,
            "base_url": GITHUB_BASE_URL,
            "api_url": GITHUB_API_URL,
            "search_url": GITHUB_SEARCH_URL
        },
        
        # Template Information
        "template": {
            "name": TEMPLATE_NAME,
            "version": TEMPLATE_VERSION,
            "description": TEMPLATE_DESCRIPTION,
            "author": TEMPLATE_AUTHOR,
            "framework_version": FRAMEWORK_VERSION
        },
        
        # Rate Limiting
        "rate_limit": {
            "enabled": RATE_LIMIT_ENABLED,
            "requests_per_hour": RATE_LIMIT_REQUESTS_PER_HOUR,
            "requests_per_minute": RATE_LIMIT_REQUESTS_PER_MINUTE,
            "wait_time": RATE_LIMIT_WAIT_TIME
        },
        
        # Request Settings
        "request": {
            "timeout": REQUEST_TIMEOUT,
            "page_load_timeout": PAGE_LOAD_TIMEOUT,
            "element_wait_timeout": ELEMENT_WAIT_TIMEOUT
        },
        
        # Pagination
        "pagination": {
            "default_page_size": DEFAULT_PAGE_SIZE,
            "max_pages_per_search": MAX_PAGES_PER_SEARCH,
            "max_issues_per_repository": MAX_ISSUES_PER_REPOSITORY
        },
        
        # Search Configuration
        "search": {
            "default_type": DEFAULT_SEARCH_TYPE,
            "types": SEARCH_TYPES,
            "sort_options": SEARCH_SORT_OPTIONS,
            "order_options": SEARCH_ORDER_OPTIONS
        },
        
        # Data Extraction
        "extraction": {
            "enabled": EXTRACTION_ENABLED,
            "retry_count": EXTRACTION_RETRY_COUNT,
            "retry_delay": EXTRACTION_RETRY_DELAY
        },
        
        # Selectors
        "selectors": {
            "confidence_threshold": SELECTOR_CONFIDENCE_THRESHOLD,
            "validation_enabled": SELECTOR_VALIDATION_ENABLED,
            "cache_enabled": SELECTOR_CACHE_ENABLED
        },
        
        # Feature Flags
        "features": {
            "user_scraping": ENABLE_USER_SCRAPING,
            "issue_scraping": ENABLE_ISSUE_SCRAPING,
            "repository_scraping": ENABLE_REPOSITORY_SCRAPING,
            "search_scraping": ENABLE_SEARCH_SCRAPING,
            "pagination": ENABLE_PAGINATION,
            "stealth_mode": ENABLE_STEALTH_MODE
        },
        
        # Stealth Settings
        "stealth": {
            "enabled": STEALTH_ENABLED,
            "user_agent": STEALTH_USER_AGENT,
            "viewport": STEALTH_VIEWPORT,
            "locale": STEALTH_LOCALE,
            "timezone": STEALTH_TIMEZONE
        },
        
        # Browser Settings
        "browser": {
            "headless": BROWSER_HEADLESS,
            "slowmo": BROWSER_SLOWMO,
            "ignore_https_errors": BROWSER_IGNORE_HTTPS_ERRORS
        },
        
        # Logging
        "logging": {
            "level": LOG_LEVEL,
            "structured": LOG_STRUCTURED,
            "performance_metrics": LOG_PERFORMANCE_METRICS
        },
        
        # Cache
        "cache": {
            "enabled": CACHE_ENABLED,
            "ttl": CACHE_TTL,
            "max_size": CACHE_MAX_SIZE
        },
        
        # Error Handling
        "error_handling": {
            "retry_enabled": ERROR_RETRY_ENABLED,
            "retry_count": ERROR_RETRY_COUNT,
            "retry_backoff_factor": ERROR_RETRY_BACKOFF_FACTOR,
            "retry_max_delay": ERROR_RETRY_MAX_DELAY
        },
        
        # Monitoring
        "monitoring": {
            "enabled": MONITORING_ENABLED,
            "metrics_interval": MONITORING_METRICS_INTERVAL,
            "performance_tracking": MONITORING_PERFORMANCE_TRACKING
        },
        
        # Output
        "output": {
            "format": OUTPUT_FORMAT,
            "include_metadata": OUTPUT_INCLUDE_METADATA,
            "include_timestamps": OUTPUT_INCLUDE_TIMESTAMPS,
            "include_performance_metrics": OUTPUT_INCLUDE_PERFORMANCE_METRICS
        },
        
        # Validation
        "validation": {
            "enabled": VALIDATION_ENABLED,
            "strict_mode": VALIDATION_STRICT_MODE,
            "schema_version": VALIDATION_SCHEMA_VERSION
        },
        
        # Security
        "security": {
            "validate_ssl": SECURITY_VALIDATE_SSL,
            "block_trackers": SECURITY_BLOCK_TRACKERS,
            "block_ads": SECURITY_BLOCK_ADS
        },
        
        # Development
        "development": {
            "debug_mode": DEBUG_MODE,
            "save_screenshots": DEBUG_SAVE_SCREENSHOTS,
            "save_html": DEBUG_SAVE_HTML,
            "log_selector_resolution": DEBUG_LOG_SELECTOR_RESOLUTION
        }
    }


def get_rate_limit_config() -> Dict[str, Any]:
    """
    Get rate limiting configuration.
    
    Returns:
        Dict[str, Any]: Rate limiting configuration
    """
    return {
        "enabled": RATE_LIMIT_ENABLED,
        "requests_per_hour": RATE_LIMIT_REQUESTS_PER_HOUR,
        "requests_per_minute": RATE_LIMIT_REQUESTS_PER_MINUTE,
        "wait_time": RATE_LIMIT_WAIT_TIME
    }


def get_stealth_config() -> Dict[str, Any]:
    """
    Get stealth configuration.
    
    Returns:
        Dict[str, Any]: Stealth configuration
    """
    return {
        "enabled": STEALTH_ENABLED,
        "user_agent": STEALTH_USER_AGENT,
        "viewport": STEALTH_VIEWPORT,
        "locale": STEALTH_LOCALE,
        "timezone": STEALTH_TIMEZONE
    }


def get_browser_config() -> Dict[str, Any]:
    """
    Get browser configuration.
    
    Returns:
        Dict[str, Any]: Browser configuration
    """
    return {
        "headless": BROWSER_HEADLESS,
        "slowmo": BROWSER_SLOWMO,
        "ignore_https_errors": BROWSER_IGNORE_HTTPS_ERRORS
    }


def is_feature_enabled(feature: str) -> bool:
    """
    Check if a feature is enabled.
    
    Args:
        feature: Feature name
        
    Returns:
        bool: True if feature is enabled
    """
    feature_flags = {
        "user_scraping": ENABLE_USER_SCRAPING,
        "issue_scraping": ENABLE_ISSUE_SCRAPING,
        "repository_scraping": ENABLE_REPOSITORY_SCRAPING,
        "search_scraping": ENABLE_SEARCH_SCRAPING,
        "pagination": ENABLE_PAGINATION,
        "stealth_mode": ENABLE_STEALTH_MODE
    }
    
    return feature_flags.get(feature, False)


def update_config(key: str, value: Any) -> None:
    """
    Update configuration value.
    
    Args:
        key: Configuration key (dot notation supported)
        value: New value
    """
    # This would typically update a configuration store
    # For now, this is a placeholder for future implementation
    pass


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get configuration value.
    
    Args:
        key: Configuration key (dot notation supported)
        default: Default value if key not found
        
    Returns:
        Any: Configuration value
    """
    config = get_github_config()
    
    # Navigate through nested keys using dot notation
    keys = key.split('.')
    current = config
    
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    
    return current


# Configuration validation
def validate_config() -> List[str]:
    """
    Validate configuration settings.
    
    Returns:
        List[str]: List of validation errors
    """
    errors = []
    
    # Validate required settings
    if not SITE_DOMAIN:
        errors.append("SITE_DOMAIN is required")
    
    if not GITHUB_BASE_URL:
        errors.append("GITHUB_BASE_URL is required")
    
    # Validate numeric settings
    if RATE_LIMIT_REQUESTS_PER_HOUR <= 0:
        errors.append("RATE_LIMIT_REQUESTS_PER_HOUR must be positive")
    
    if REQUEST_TIMEOUT <= 0:
        errors.append("REQUEST_TIMEOUT must be positive")
    
    if SELECTOR_CONFIDENCE_THRESHOLD < 0 or SELECTOR_CONFIDENCE_THRESHOLD > 1:
        errors.append("SELECTOR_CONFIDENCE_THRESHOLD must be between 0 and 1")
    
    # Validate list settings
    if not SEARCH_TYPES:
        errors.append("SEARCH_TYPES cannot be empty")
    
    return errors


# Runtime configuration (can be modified during execution)
runtime_config = {
    "current_user_agent": STEALTH_USER_AGENT,
    "current_viewport": STEALTH_VIEWPORT.copy(),
    "current_locale": STEALTH_LOCALE,
    "rate_limit_reset_time": None,
    "requests_made_current_hour": 0,
    "last_request_time": None
}


def get_runtime_config() -> Dict[str, Any]:
    """
    Get runtime configuration.
    
    Returns:
        Dict[str, Any]: Runtime configuration
    """
    return runtime_config.copy()


def update_runtime_config(key: str, value: Any) -> None:
    """
    Update runtime configuration.
    
    Args:
        key: Configuration key
        value: New value
    """
    runtime_config[key] = value


def reset_runtime_config() -> None:
    """Reset runtime configuration to defaults."""
    global runtime_config
    runtime_config = {
        "current_user_agent": STEALTH_USER_AGENT,
        "current_viewport": STEALTH_VIEWPORT.copy(),
        "current_locale": STEALTH_LOCALE,
        "rate_limit_reset_time": None,
        "requests_made_current_hour": 0,
        "last_request_time": None
    }
