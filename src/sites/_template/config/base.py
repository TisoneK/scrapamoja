"""
Base configuration template for the modular site scraper template.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class BaseConfig:
    """Base configuration class with common scraper settings."""
    
    # Site configuration
    site_id: str = "template"
    site_name: str = "Template Site"
    base_url: str = "https://example.com"
    
    # Scraper configuration
    timeout_ms: int = 30000
    retry_attempts: int = 3
    retry_delay_ms: int = 1000
    max_concurrent_requests: int = 5
    
    # Browser configuration
    headless: bool = True
    browser_type: str = "chromium"
    viewport_width: int = 1920
    viewport_height: int = 1080
    
    # Rate limiting
    requests_per_minute: int = 60
    delay_between_requests_ms: int = 1000
    
    # Data collection
    max_results: int = 100
    enable_screenshots: bool = False
    enable_html_capture: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/scraper.log"
    
    # Feature flags
    enable_stealth_mode: bool = True
    enable_circuit_breaker: bool = True
    
    # Output configuration
    output_format: str = "json"
    output_file_path: str = "output/results.json"
    
    # Environment settings
    environment: str = "base"
    debug_mode: bool = False
    
    def __post_init__(self):
        """Initialize configuration after creation."""
        self.custom_headers = {}
        self.proxy_settings = None
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.site_id:
            errors.append("site_id is required")
        
        if not self.base_url:
            errors.append("base_url is required")
        
        if self.timeout_ms <= 0:
            errors.append("timeout_ms must be positive")
        
        if self.retry_attempts < 0:
            errors.append("retry_attempts must be non-negative")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'site_id': self.site_id,
            'site_name': self.site_name,
            'base_url': self.base_url,
            'timeout_ms': self.timeout_ms,
            'retry_attempts': self.retry_attempts,
            'retry_delay_ms': self.retry_delay_ms,
            'max_concurrent_requests': self.max_concurrent_requests,
            'headless': self.headless,
            'browser_type': self.browser_type,
            'viewport_width': self.viewport_width,
            'viewport_height': self.viewport_height,
            'requests_per_minute': self.requests_per_minute,
            'delay_between_requests_ms': self.delay_between_requests_ms,
            'max_results': self.max_results,
            'enable_screenshots': self.enable_screenshots,
            'enable_html_capture': self.enable_html_capture,
            'log_level': self.log_level,
            'log_to_file': self.log_to_file,
            'log_file_path': self.log_file_path,
            'enable_stealth_mode': self.enable_stealth_mode,
            'enable_circuit_breaker': self.enable_circuit_breaker,
            'output_format': self.output_format,
            'output_file_path': self.output_file_path,
            'environment': self.environment,
            'debug_mode': self.debug_mode
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
    def merge_with(self, other_config: 'BaseConfig') -> 'BaseConfig':
        """Merge this configuration with another."""
        merged_dict = self.to_dict()
        other_dict = other_config.to_dict()
        
        # Merge dictionaries, with other_config taking precedence
        for key, value in other_dict.items():
            if value is not None:
                merged_dict[key] = value
        
        return BaseConfig.from_dict(merged_dict)
