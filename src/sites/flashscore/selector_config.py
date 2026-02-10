"""
Flashscore selector configuration.

Loads and provides access to selector configuration from YAML file.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List


def load_config() -> Dict[str, Any]:
    """Load selector configuration from YAML file."""
    config_path = Path(__file__).parent / "selectors" / "selector_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# Load configuration once at import time
_config = load_config()

# Export commonly used configuration sections
sports: Dict[str, Any] = _config.get('sports', {})
match_status_detection: Dict[str, Any] = _config.get('match_status_detection', {})
navigation_hierarchy: Dict[str, Any] = _config.get('navigation_hierarchy', {})
extraction_types: Dict[str, Any] = _config.get('extraction_types', {})
selector_loading: Dict[str, Any] = _config.get('selector_loading', {})
error_handling: Dict[str, Any] = _config.get('error_handling', {})

# Export full config for advanced usage
selector_config = _config
config = _config
