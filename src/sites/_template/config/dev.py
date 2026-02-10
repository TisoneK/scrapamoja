"""
Development configuration template for the modular site scraper template.

This module provides development-specific configuration with
debugging features and relaxed settings.
"""

from .base import BaseConfig


class DevConfig(BaseConfig):
    """Development configuration with debugging features."""
    
    def __init__(self):
        """Initialize development configuration."""
        super().__init__()
        
        # Override base settings for development
        self.environment = "dev"
        self.debug_mode = True
        self.headless = False  # Show browser for debugging
        self.timeout_ms = 60000  # Longer timeout for debugging
        self.retry_attempts = 5  # More retries for unstable dev
        self.log_level = "DEBUG"
        self.enable_screenshots = True  # Enable screenshots for debugging
        self.enable_html_capture = True
        
        # Development-specific settings
        self.requests_per_minute = 120  # Higher rate limit for testing
        self.delay_between_requests_ms = 500  # Faster for testing
        self.max_results = 20  # Smaller dataset for testing
        
        # Browser settings for development
        self.viewport_width = 1366
        self.viewport_height = 768
        self.browser_type = "chromium"
        
        # Output settings for development
        self.output_file_path = "output/dev_results.json"
        self.log_file_path = "logs/dev_scraper.log"
        
        # Development feature flags
        self.enable_stealth_mode = False  # Disable stealth for easier debugging
        self.enable_circuit_breaker = False  # Disable circuit breaker for testing
        self.enable_performance_monitoring = True
        self.enable_structured_logging = True
        
        # Development headers
        self.custom_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
