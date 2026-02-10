"""
Production configuration template for the modular site scraper template.

This module provides production-specific configuration with
optimized settings and enhanced security.
"""

from .base import BaseConfig


class ProdConfig(BaseConfig):
    """Production configuration with optimized settings."""
    
    def __init__(self):
        """Initialize production configuration."""
        super().__init__()
        
        # Override base settings for production
        self.environment = "prod"
        self.debug_mode = False
        self.headless = True  # Run headless in production
        self.timeout_ms = 30000  # Standard timeout
        self.retry_attempts = 3  # Standard retry count
        self.log_level = "WARNING"  # Reduced logging in production
        self.enable_screenshots = False  # Disable screenshots to save space
        self.enable_html_capture = False  # Disable HTML capture in production
        
        # Production-specific settings
        self.requests_per_minute = 30  # Conservative rate limiting
        self.delay_between_requests_ms = 2000  # Slower to be respectful
        self.max_results = 1000  # Larger dataset for production
        
        # Browser settings for production
        self.viewport_width = 1920
        self.viewport_height = 1080
        self.browser_type = "chromium"
        
        # Output settings for production
        self.output_file_path = "output/prod_results.json"
        self.log_file_path = "logs/prod_scraper.log"
        self.enable_compression = True  # Compress output files
        
        # Production feature flags
        self.enable_stealth_mode = True  # Enable stealth for production
        self.enable_circuit_breaker = True  # Enable circuit breaker
        self.enable_performance_monitoring = True
        self.enable_structured_logging = True
        
        # Production headers
        self.custom_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        # Production performance settings
        self.memory_limit_mb = 512  # Lower memory limit
        self.cpu_limit_percent = 70.0  # Lower CPU limit
        self.max_concurrent_requests = 3  # Fewer concurrent requests
        
        # Production security settings
        self.enable_request_headers = True
        self.proxy_settings = None  # Configure proxy if needed
