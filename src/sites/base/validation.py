"""
Validation utilities for site scrapers.

Provides validation result structure and validation methods
for scraper implementations and configurations.
"""

import yaml
import jsonschema
from pathlib import Path
from typing import List, Dict, Any


class InterfaceValidator:
    """Validator for interface compliance."""
    
    @staticmethod
    def validate_scraper_interface(scraper_class) -> ValidationResult:
        """Validate that scraper class implements required interface."""
        result = ValidationResult()
        
        # Check class inheritance
        if not hasattr(scraper_class, '__bases__'):
            result.add_error("Scraper class has no base classes")
            return result
        
        from .site_scraper import BaseSiteScraper
        if not issubclass(scraper_class, BaseSiteScraper):
            result.add_error("Scraper class must inherit from BaseSiteScraper")
        
        # Check required class attributes
        required_attrs = ['site_id', 'site_name', 'base_url']
        for attr in required_attrs:
            if not hasattr(scraper_class, attr):
                result.add_error(f"Missing required class attribute: {attr}")
            elif getattr(scraper_class, attr) is None:
                result.add_error(f"Required class attribute '{attr}' cannot be None")
            elif attr in ['site_id', 'site_name', 'base_url'] and not isinstance(getattr(scraper_class, attr), str):
                result.add_error(f"Class attribute '{attr}' must be a string")
        
        # Check required methods
        required_methods = ['navigate', 'scrape', 'normalize']
        for method in required_methods:
            if not hasattr(scraper_class, method):
                result.add_error(f"Missing required method: {method}")
            elif not callable(getattr(scraper_class, method)):
                result.add_error(f"Attribute '{method}' is not callable")
            else:
                # Validate method signatures
                method_obj = getattr(scraper_class, method)
                InterfaceValidator._validate_method_signature(method_obj, method, result)
        
        return result
    
    @staticmethod
    def _validate_method_signature(method_obj, method_name: str, result: ValidationResult):
        """Validate method signature for required methods."""
        import inspect
        
        try:
            sig = inspect.signature(method_obj)
            
            if method_name == 'navigate':
                # navigate() should take only self
                params = list(sig.parameters.keys())
                if len(params) > 1:
                    result.add_warning(f"navigate() method should take no parameters besides self")
            
            elif method_name == 'scrape':
                # scrape() should take self and **kwargs
                params = list(sig.parameters.keys())
                if len(params) < 1:
                    result.add_error(f"scrape() method must accept **kwargs")
                elif len(params) > 2:
                    result.add_warning(f"scrape() method should only take **kwargs beyond self")
            
            elif method_name == 'normalize':
                # normalize() should take self and raw_data
                params = list(sig.parameters.keys())
                if len(params) != 2:
                    result.add_error(f"normalize() method must take exactly one parameter (raw_data)")
                elif 'raw_data' not in params:
                    result.add_error(f"normalize() method must have 'raw_data' parameter")
        
        except Exception as e:
            result.add_warning(f"Could not validate {method_name}() method signature: {str(e)}")


class ValidationResult:
    """Validation result for scraper implementation."""
    
    def __init__(self):
        self.valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.missing_files: List[str] = []
        self.invalid_selectors: List[str] = []
    
    def add_error(self, message: str) -> None:
        """Add a critical validation error."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a non-critical validation warning."""
        self.warnings.append(message)
    
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid


class FileValidator:
    """Validator for file existence and structure."""
    
    @staticmethod
    def validate_required_files(scraper_dir: Path) -> ValidationResult:
        """Validate that required scraper files exist."""
        result = ValidationResult()
        
        # Check required files
        required_files = ['config.py', 'flow.py', 'scraper.py']
        for file_name in required_files:
            file_path = scraper_dir / file_name
            if not file_path.exists():
                result.add_error(f"Missing required file: {file_name}")
                result.missing_files.append(str(file_path))
            elif not file_path.is_file():
                result.add_error(f"Path exists but is not a file: {file_name}")
                result.missing_files.append(str(file_path))
        
        # Check selectors directory exists
        selectors_dir = scraper_dir / 'selectors'
        if not selectors_dir.exists():
            result.add_error("Missing required directory: selectors/")
            result.missing_files.append(str(selectors_dir))
        elif not selectors_dir.is_dir():
            result.add_error("Path exists but is not a directory: selectors/")
            result.missing_files.append(str(selectors_dir))
        else:
            # Check if selectors directory has at least one YAML file
            yaml_files = list(selectors_dir.glob('*.yaml'))
            if not yaml_files:
                result.add_warning("No selector files found in selectors/ directory")
            else:
                # Validate each YAML file
                for yaml_file in yaml_files:
                    yaml_result = FileValidator.validate_yaml_file(yaml_file)
                    if not yaml_result.is_valid():
                        result.errors.extend(yaml_result.errors)
                        result.invalid_selectors.append(str(yaml_file))
                    result.warnings.extend(yaml_result.warnings)
        
        return result
    
    @staticmethod
    def validate_yaml_file(yaml_path: Path) -> ValidationResult:
        """Validate YAML selector file structure and content."""
        result = ValidationResult()
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file is empty
            if not content.strip():
                result.add_error(f"YAML file is empty: {yaml_path.name}")
                return result
            
            # Parse YAML
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                result.add_error(f"Invalid YAML syntax in {yaml_path.name}: {str(e)}")
                return result
            
            # Validate structure against schema
            schema = FileValidator._get_selector_schema()
            try:
                jsonschema.validate(data, schema)
            except jsonschema.ValidationError as e:
                result.add_error(f"Schema validation failed in {yaml_path.name}: {e.message}")
                return result
            
            # Validate confidence threshold
            if 'confidence_threshold' in data:
                threshold = data['confidence_threshold']
                if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
                    result.add_error(f"Invalid confidence_threshold in {yaml_path.name}: must be between 0.0 and 1.0")
            
            # Validate strategies
            if 'strategies' in data:
                strategies = data['strategies']
                if not isinstance(strategies, list) or len(strategies) == 0:
                    result.add_error(f"Strategies must be a non-empty list in {yaml_path.name}")
                else:
                    valid_types = ['css', 'xpath', 'text', 'attribute', 'role']
                    for i, strategy in enumerate(strategies):
                        if not isinstance(strategy, dict):
                            result.add_error(f"Strategy {i} must be a dictionary in {yaml_path.name}")
                            continue
                        
                        if 'type' not in strategy:
                            result.add_error(f"Strategy {i} missing 'type' field in {yaml_path.name}")
                        elif strategy['type'] not in valid_types:
                            result.add_error(f"Invalid strategy type '{strategy['type']}' in {yaml_path.name}")
                        
                        if 'selector' not in strategy:
                            result.add_error(f"Strategy {i} missing 'selector' field in {yaml_path.name}")
                        elif not isinstance(strategy['selector'], str) or not strategy['selector'].strip():
                            result.add_error(f"Strategy {i} has invalid selector in {yaml_path.name}")
                        
                        # Validate weight if present
                        if 'weight' in strategy:
                            weight = strategy['weight']
                            if not isinstance(weight, (int, float)) or not (0.0 <= weight <= 1.0):
                                result.add_error(f"Strategy {i} has invalid weight in {yaml_path.name}")
            
        except Exception as e:
            result.add_error(f"Unexpected error validating {yaml_path.name}: {str(e)}")
        
        return result
    
    @staticmethod
    def _get_selector_schema() -> Dict[str, Any]:
        """Get JSON schema for selector validation."""
        return {
            "type": "object",
            "required": ["description", "confidence_threshold", "strategies"],
            "properties": {
                "description": {
                    "type": "string",
                    "minLength": 1
                },
                "confidence_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "timeout": {
                    "type": "number",
                    "minimum": 0
                },
                "retry_count": {
                    "type": "integer",
                    "minimum": 0
                },
                "strategies": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["type", "selector"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["css", "xpath", "text", "attribute", "role"]
                            },
                            "selector": {
                                "type": "string",
                                "minLength": 1
                            },
                            "weight": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0
                            }
                        }
                    }
                }
            }
        }


class ConfigurationValidator:
    """Validator for site configuration."""
    
    @staticmethod
    def validate_site_config(config: Dict[str, Any]) -> ValidationResult:
        """Validate site configuration structure and values."""
        result = ValidationResult()
        
        # Check required fields
        required_fields = ['id', 'name', 'base_url', 'version', 'maintainer']
        for field in required_fields:
            if field not in config:
                result.add_error(f"Missing required configuration field: {field}")
            elif config[field] is None:
                result.add_error(f"Configuration field '{field}' cannot be None")
            elif isinstance(config[field], str) and not config[field].strip():
                result.add_error(f"Configuration field '{field}' cannot be empty")
        
        # Validate field formats and types
        if 'id' in config:
            if not isinstance(config['id'], str):
                result.add_error("Site ID must be a string")
            else:
                import re
                if not re.match(r'^[a-z0-9_]+$', config['id']):
                    result.add_error("Site ID must contain only lowercase letters, numbers, and underscores")
        
        if 'name' in config and isinstance(config['name'], str):
            if len(config['name'].strip()) == 0:
                result.add_error("Site name cannot be empty")
        
        if 'base_url' in config and isinstance(config['base_url'], str):
            if not (config['base_url'].startswith('http://') or config['base_url'].startswith('https://')):
                result.add_error("Base URL must start with http:// or https://")
        
        if 'version' in config and isinstance(config['version'], str):
            import re
            if not re.match(r'^\d+\.\d+\.\d+$', config['version']):
                result.add_error("Version must follow semantic versioning (e.g., 1.0.0)")
        
        if 'maintainer' in config and isinstance(config['maintainer'], str):
            if len(config['maintainer'].strip()) == 0:
                result.add_error("Maintainer cannot be empty")
        
        # Validate optional fields
        if 'description' in config and config['description'] is not None:
            if not isinstance(config['description'], str):
                result.add_error("Description must be a string")
        
        if 'tags' in config and config['tags'] is not None:
            if not isinstance(config['tags'], list):
                result.add_error("Tags must be a list")
            else:
                for tag in config['tags']:
                    if not isinstance(tag, str):
                        result.add_error("All tags must be strings")
        
        return result
