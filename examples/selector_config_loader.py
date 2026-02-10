"""
Selector Configuration Loader
Utility for loading selector configurations from YAML files.
"""

import yaml
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SelectorStrategy:
    """Individual selector strategy configuration"""
    type: str
    selector: str
    priority: int
    expected_attributes: Optional[Dict[str, str]] = None
    search_context: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SelectorConfiguration:
    """Complete selector configuration for an element"""
    element_purpose: str
    strategies: list[SelectorStrategy]
    confidence_threshold: float = 0.7
    timeout_per_strategy_ms: int = 1500
    enable_fallback: bool = True


class SelectorConfigLoader:
    """Loads and manages selector configurations from YAML files"""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing YAML config files
        """
        if config_dir is None:
            # Default to the examples directory where the YAML file is located
            self.config_dir = os.path.dirname(__file__)
        else:
            self.config_dir = config_dir
        self._cache: Dict[str, SelectorConfiguration] = {}
    
    def load_config(self, config_name: str, config_file: str = None) -> SelectorConfiguration:
        """
        Load a selector configuration from YAML file.
        
        Args:
            config_name: Name of the configuration section
            config_file: Path to YAML file (optional, defaults to wikipedia_selectors.yaml)
            
        Returns:
            SelectorConfiguration object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            KeyError: If config_name not found in file
            yaml.YAMLError: If YAML parsing fails
        """
        cache_key = f"{config_file}:{config_name}"
        
        # Return cached configuration if available
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Determine config file path
        if config_file is None:
            config_file = os.path.join(self.config_dir, "wikipedia_selectors.yaml")
        
        # Load and parse YAML
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Selector config file not found: {config_file}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML config file {config_file}: {e}")
        
        # Extract configuration section
        if config_name not in yaml_data:
            raise KeyError(f"Configuration '{config_name}' not found in {config_file}")
        
        config_data = yaml_data[config_name]
        
        # Parse strategies
        strategies = []
        for strategy_data in config_data.get('strategies', []):
            strategy = SelectorStrategy(
                type=strategy_data['type'],
                selector=strategy_data['selector'],
                priority=strategy_data['priority'],
                expected_attributes=strategy_data.get('expected_attributes'),
                search_context=strategy_data.get('search_context'),
                description=strategy_data.get('description')
            )
            strategies.append(strategy)
        
        # Create configuration object
        config = SelectorConfiguration(
            element_purpose=config_data['element_purpose'],
            strategies=strategies,
            confidence_threshold=config_data.get('confidence_threshold', 0.7),
            timeout_per_strategy_ms=config_data.get('timeout_per_strategy_ms', 1500),
            enable_fallback=config_data.get('enable_fallback', True)
        )
        
        # Cache and return
        self._cache[cache_key] = config
        return config
    
    def list_available_configs(self, config_file: str = None) -> list[str]:
        """
        List all available configuration names in a YAML file.
        
        Args:
            config_file: Path to YAML file (optional)
            
        Returns:
            List of configuration names
        """
        if config_file is None:
            config_file = os.path.join(self.config_dir, "wikipedia_selectors.yaml")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            return list(yaml_data.keys()) if yaml_data else []
        except (FileNotFoundError, yaml.YAMLError):
            return []
    
    def validate_config(self, config: SelectorConfiguration) -> list[str]:
        """
        Validate a selector configuration.
        
        Args:
            config: SelectorConfiguration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check basic required fields
        if not config.element_purpose:
            errors.append("element_purpose is required")
        
        if not config.strategies:
            errors.append("At least one strategy is required")
        
        # Validate strategies
        for i, strategy in enumerate(config.strategies):
            if not strategy.type:
                errors.append(f"Strategy {i}: type is required")
            
            if not strategy.selector:
                errors.append(f"Strategy {i}: selector is required")
            
            if strategy.priority < 1:
                errors.append(f"Strategy {i}: priority must be >= 1")
            
            # Validate strategy type
            valid_types = ['css', 'xpath', 'text']
            if strategy.type not in valid_types:
                errors.append(f"Strategy {i}: type must be one of {valid_types}")
            
            # Validate text strategy specific requirements
            if strategy.type == 'text' and not strategy.search_context:
                errors.append(f"Strategy {i}: text strategy requires search_context")
        
        # Validate thresholds
        if not 0 <= config.confidence_threshold <= 1:
            errors.append("confidence_threshold must be between 0 and 1")
        
        if config.timeout_per_strategy_ms <= 0:
            errors.append("timeout_per_strategy_ms must be positive")
        
        return errors
    
    def clear_cache(self):
        """Clear the configuration cache"""
        self._cache.clear()


# Global loader instance
_loader = SelectorConfigLoader()


def get_selector_config(config_name: str, config_file: str = None) -> SelectorConfiguration:
    """
    Convenience function to get a selector configuration.
    
    Args:
        config_name: Name of the configuration
        config_file: Path to YAML file (optional)
        
    Returns:
        SelectorConfiguration object
    """
    return _loader.load_config(config_name, config_file)


def list_selector_configs(config_file: str = None) -> list[str]:
    """
    Convenience function to list available configurations.
    
    Args:
        config_file: Path to YAML file (optional)
        
    Returns:
        List of configuration names
    """
    return _loader.list_available_configs(config_file)
