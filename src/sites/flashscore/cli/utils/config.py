"""
CLI configuration utilities.

Handles configuration loading and management.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class CLIConfig:
    """Manages CLI configuration."""
    
    def __init__(self):
        self.config = {}
        self.config_file = None
    
    async def load_from_file(self, file_path: str) -> None:
        """Load configuration from file."""
        self.config_file = Path(file_path)
        
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    self.config = yaml.safe_load(f)
                else:
                    self.config = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")
    
    async def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        import os
        
        # Load common configuration from environment
        self.config = {
            'browser': {
                'headless': os.getenv('FLASHSCORE_HEADLESS', 'true').lower() == 'true',
                'timeout': int(os.getenv('FLASHSCORE_TIMEOUT', '30')),
                'user_agent': os.getenv('FLASHSCORE_USER_AGENT'),
            },
            'output': {
                'format': os.getenv('FLASHSCORE_OUTPUT_FORMAT', 'json'),
                'directory': os.getenv('FLASHSCORE_OUTPUT_DIR', './output'),
            },
            'scraping': {
                'delay': float(os.getenv('FLASHSCORE_DELAY', '1.0')),
                'retries': int(os.getenv('FLASHSCORE_RETRIES', '3')),
                'parallel_limit': int(os.getenv('FLASHSCORE_PARALLEL_LIMIT', '5')),
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def merge(self, other_config: Dict[str, Any]) -> None:
        """Merge another configuration into this one."""
        self._deep_merge(self.config, other_config)
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_to_file(self, file_path: str) -> None:
        """Save configuration to file."""
        save_path = Path(file_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            else:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate browser configuration
        browser_config = self.get('browser', {})
        if 'headless' in browser_config and not isinstance(browser_config['headless'], bool):
            results['errors'].append('browser.headless must be a boolean')
            results['valid'] = False
        
        if 'timeout' in browser_config:
            timeout = browser_config['timeout']
            if not isinstance(timeout, int) or timeout <= 0:
                results['errors'].append('browser.timeout must be a positive integer')
                results['valid'] = False
        
        # Validate output configuration
        output_config = self.get('output', {})
        if 'format' in output_config:
            format_type = output_config['format']
            if format_type not in ['json', 'csv', 'xml']:
                results['errors'].append('output.format must be one of: json, csv, xml')
                results['valid'] = False
        
        # Validate scraping configuration
        scraping_config = self.get('scraping', {})
        if 'delay' in scraping_config:
            delay = scraping_config['delay']
            if not isinstance(delay, (int, float)) or delay < 0:
                results['errors'].append('scraping.delay must be a non-negative number')
                results['valid'] = False
        
        if 'retries' in scraping_config:
            retries = scraping_config['retries']
            if not isinstance(retries, int) or retries < 0:
                results['errors'].append('scraping.retries must be a non-negative integer')
                results['valid'] = False
        
        if 'parallel_limit' in scraping_config:
            limit = scraping_config['parallel_limit']
            if not isinstance(limit, int) or limit <= 0:
                results['errors'].append('scraping.parallel_limit must be a positive integer')
                results['valid'] = False
        
        return results
