"""
Template validation logic for the modular site scraper template.

This module provides comprehensive validation functionality to ensure
template integrity, configuration correctness, and component compatibility.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
import asyncio
import importlib
import inspect
from datetime import datetime

from src.sites.base.component_interface import BaseComponent, BaseProcessor, BaseValidator, BaseFlow


class TemplateValidator:
    """Comprehensive template validation system."""
    
    def __init__(self, template_path: str = None):
        """
        Initialize template validator.
        
        Args:
            template_path: Path to the template directory
        """
        self.template_path = Path(template_path) if template_path else Path(__file__).parent
        self.validation_results = {}
        self.errors = []
        self.warnings = []
        
        # Required files and directories
        self.required_files = {
            'scraper.py',
            'README.md'
        }
        
        self.required_directories = {
            'flows',
            'config',
            'processors',
            'validators',
            'components'
        }
        
        # Required modules in each directory
        self.required_modules = {
            'flows': ['__init__.py', 'base_flow.py'],
            'config': ['__init__.py', 'base.py'],
            'processors': ['__init__.py', 'normalizer.py', 'validator.py', 'transformer.py'],
            'validators': ['__init__.py', 'config_validator.py', 'data_validator.py'],
            'components': ['__init__.py', 'oauth_auth.py', 'rate_limiter.py', 'stealth_handler.py']
        }
    
    async def validate_template(self) -> Dict[str, Any]:
        """
        Perform comprehensive template validation.
        
        Returns:
            Validation results with errors, warnings, and recommendations
        """
        try:
            start_time = datetime.utcnow()
            
            # Reset validation state
            self.validation_results = {}
            self.errors = []
            self.warnings = []
            
            # Perform validation checks
            await self._validate_directory_structure()
            await self._validate_required_files()
            await self._validate_module_imports()
            await self._validate_class_definitions()
            await self._validate_configuration()
            await self._validate_component_compatibility()
            await self._validate_async_patterns()
            await self._validate_documentation()
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Compile results
            self.validation_results = {
                'valid': len(self.errors) == 0,
                'errors': self.errors,
                'warnings': self.warnings,
                'execution_time_ms': execution_time,
                'validation_timestamp': start_time.isoformat(),
                'template_path': str(self.template_path),
                'summary': {
                    'total_errors': len(self.errors),
                    'total_warnings': len(self.warnings),
                    'critical_issues': len([e for e in self.errors if e.get('severity') == 'critical'])
                }
            }
            
            return self.validation_results
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [{'type': 'validation_error', 'message': f'Template validation failed: {str(e)}', 'severity': 'critical'}],
                'warnings': [],
                'execution_time_ms': 0,
                'validation_timestamp': datetime.utcnow().isoformat(),
                'template_path': str(self.template_path)
            }
    
    async def _validate_directory_structure(self) -> None:
        """Validate required directory structure."""
        try:
            # Check template directory exists
            if not self.template_path.exists():
                self.errors.append({
                    'type': 'directory_missing',
                    'message': f'Template directory does not exist: {self.template_path}',
                    'severity': 'critical',
                    'path': str(self.template_path)
                })
                return
            
            # Check required directories
            for directory in self.required_directories:
                dir_path = self.template_path / directory
                if not dir_path.exists():
                    self.errors.append({
                        'type': 'directory_missing',
                        'message': f'Required directory missing: {directory}',
                        'severity': 'critical',
                        'path': str(dir_path)
                    })
                elif not dir_path.is_dir():
                    self.errors.append({
                        'type': 'invalid_directory',
                        'message': f'Path exists but is not a directory: {directory}',
                        'severity': 'critical',
                        'path': str(dir_path)
                    })
            
        except Exception as e:
            self.errors.append({
                'type': 'directory_validation_error',
                'message': f'Directory structure validation failed: {str(e)}',
                'severity': 'critical'
            })
    
    async def _validate_required_files(self) -> None:
        """Validate required files exist."""
        try:
            # Check required files in root
            for file_name in self.required_files:
                file_path = self.template_path / file_name
                if not file_path.exists():
                    self.errors.append({
                        'type': 'file_missing',
                        'message': f'Required file missing: {file_name}',
                        'severity': 'critical',
                        'path': str(file_path)
                    })
                elif not file_path.is_file():
                    self.errors.append({
                        'type': 'invalid_file',
                        'message': f'Path exists but is not a file: {file_name}',
                        'severity': 'critical',
                        'path': str(file_path)
                    })
            
            # Check required modules in directories
            for directory, modules in self.required_modules.items():
                dir_path = self.template_path / directory
                if dir_path.exists():
                    for module in modules:
                        module_path = dir_path / module
                        if not module_path.exists():
                            self.errors.append({
                                'type': 'module_missing',
                                'message': f'Required module missing: {directory}/{module}',
                                'severity': 'critical',
                                'path': str(module_path)
                            })
            
        except Exception as e:
            self.errors.append({
                'type': 'file_validation_error',
                'message': f'Required files validation failed: {str(e)}',
                'severity': 'critical'
            })
    
    async def _validate_module_imports(self) -> None:
        """Validate that all modules can be imported."""
        try:
            # Test importing key modules
            import_tests = [
                ('scraper', 'src.sites._template.scraper'),
                ('flows', 'src.sites._template.flows'),
                ('config', 'src.sites._template.config'),
                ('processors', 'src.sites._template.processors'),
                ('validators', 'src.sites._template.validators'),
                ('components', 'src.sites._template.components')
            ]
            
            for name, module_path in import_tests:
                try:
                    importlib.import_module(module_path)
                except ImportError as e:
                    self.errors.append({
                        'type': 'import_error',
                        'message': f'Failed to import {name}: {str(e)}',
                        'severity': 'critical',
                        'module': module_path
                    })
                except Exception as e:
                    self.errors.append({
                        'type': 'import_error',
                        'message': f'Error importing {name}: {str(e)}',
                        'severity': 'error',
                        'module': module_path
                    })
            
        except Exception as e:
            self.errors.append({
                'type': 'import_validation_error',
                'message': f'Module import validation failed: {str(e)}',
                'severity': 'critical'
            })
    
    async def _validate_class_definitions(self) -> None:
        """Validate required class definitions and inheritance."""
        try:
            # Check key classes
            class_tests = [
                ('TemplateScraper', 'src.sites._template.scraper', 'EnhancedSiteScraper'),
                ('BaseTemplateFlow', 'src.sites._template.flows.base_flow', 'BaseFlow'),
                ('SearchFlow', 'src.sites._template.flows.search_flow', 'BaseTemplateFlow'),
                ('LoginFlow', 'src.sites._template.flows.login_flow', 'BaseTemplateFlow'),
                ('PaginationFlow', 'src.sites._template.flows.pagination_flow', 'BaseTemplateFlow'),
                ('BaseConfig', 'src.sites._template.config.base', None),
                ('DevConfig', 'src.sites._template.config.dev', 'BaseConfig'),
                ('ProdConfig', 'src.sites._template.config.prod', 'BaseConfig'),
                ('DataNormalizer', 'src.sites._template.processors.normalizer', 'BaseProcessor'),
                ('DataValidator', 'src.sites._template.processors.validator', 'BaseProcessor'),
                ('DataTransformer', 'src.sites._template.processors.transformer', 'BaseProcessor'),
                ('ConfigValidator', 'src.sites._template.validators.config_validator', 'BaseValidator'),
                ('DataValidator', 'src.sites._template.validators.data_validator', 'BaseValidator'),
                ('OAuthAuthComponent', 'src.sites._template.components.oauth_auth', 'BaseComponent'),
                ('RateLimiterComponent', 'src.sites._template.components.rate_limiter', 'BaseComponent'),
                ('StealthHandlerComponent', 'src.sites._template.components.stealth_handler', 'BaseComponent')
            ]
            
            for class_name, module_path, expected_base in class_tests:
                try:
                    module = importlib.import_module(module_path)
                    if not hasattr(module, class_name):
                        self.errors.append({
                            'type': 'class_missing',
                            'message': f'Class {class_name} not found in {module_path}',
                            'severity': 'critical',
                            'module': module_path,
                            'class': class_name
                        })
                        continue
                    
                    cls = getattr(module, class_name)
                    
                    # Check inheritance if expected base is specified
                    if expected_base:
                        if not inspect.isclass(cls):
                            self.errors.append({
                                'type': 'invalid_class',
                                'message': f'{class_name} is not a class',
                                'severity': 'critical',
                                'module': module_path,
                                'class': class_name
                            })
                            continue
                        
                        # Check if it inherits from expected base
                        base_module_path = module_path.rsplit('.', 1)[0]
                        base_module = importlib.import_module(base_module_path)
                        if hasattr(base_module, expected_base):
                            base_class = getattr(base_module, expected_base)
                            if not issubclass(cls, base_class):
                                self.errors.append({
                                    'type': 'invalid_inheritance',
                                    'message': f'{class_name} does not inherit from {expected_base}',
                                    'severity': 'critical',
                                    'module': module_path,
                                    'class': class_name,
                                    'expected_base': expected_base
                                })
                    
                    # Check for required methods
                    await self._validate_class_methods(cls, class_name, module_path)
                    
                except ImportError as e:
                    self.errors.append({
                        'type': 'import_error',
                        'message': f'Failed to import {module_path} for class validation: {str(e)}',
                        'severity': 'critical',
                        'module': module_path
                    })
                except Exception as e:
                    self.errors.append({
                        'type': 'class_validation_error',
                        'message': f'Error validating class {class_name}: {str(e)}',
                        'severity': 'error',
                        'module': module_path,
                        'class': class_name
                    })
            
        except Exception as e:
            self.errors.append({
                'type': 'class_definition_validation_error',
                'message': f'Class definition validation failed: {str(e)}',
                'severity': 'critical'
            })
    
    async def _validate_class_methods(self, cls: type, class_name: str, module_path: str) -> None:
        """Validate required methods for classes."""
        try:
            # Define required methods by class type
            required_methods = {
                'TemplateScraper': ['setup_components', 'scrape_with_modular_components'],
                'BaseTemplateFlow': ['navigate_to', 'wait_for_element', 'retry_operation'],
                'SearchFlow': ['perform_search', 'extract_search_results'],
                'LoginFlow': ['perform_login', 'perform_logout'],
                'PaginationFlow': ['detect_pagination', 'navigate_to_next_page'],
                'DataNormalizer': ['process'],
                'DataValidator': ['process'],
                'DataTransformer': ['process'],
                'ConfigValidator': ['validate'],
                'DataValidator': ['validate'],
                'OAuthAuthComponent': ['execute', 'initialize'],
                'RateLimiterComponent': ['execute', 'initialize'],
                'StealthHandlerComponent': ['execute', 'initialize']
            }
            
            if class_name in required_methods:
                for method_name in required_methods[class_name]:
                    if not hasattr(cls, method_name):
                        self.errors.append({
                            'type': 'method_missing',
                            'message': f'Required method {method_name} missing from {class_name}',
                            'severity': 'critical',
                            'module': module_path,
                            'class': class_name,
                            'method': method_name
                        })
                    else:
                        method = getattr(cls, method_name)
                        if not callable(method):
                            self.errors.append({
                                'type': 'invalid_method',
                                'message': f'Method {method_name} in {class_name} is not callable',
                                'severity': 'critical',
                                'module': module_path,
                                'class': class_name,
                                'method': method_name
                            })
            
        except Exception as e:
            self.errors.append({
                'type': 'method_validation_error',
                'message': f'Method validation failed for {class_name}: {str(e)}',
                'severity': 'error',
                'module': module_path,
                'class': class_name
            })
    
    async def _validate_configuration(self) -> None:
        """Validate configuration files and settings."""
        try:
            # Check configuration classes
            config_tests = [
                ('BaseConfig', 'src.sites._template.config.base'),
                ('DevConfig', 'src.sites._template.config.dev'),
                ('ProdConfig', 'src.sites._template.config.prod'),
                ('FeatureFlags', 'src.sites._template.config.feature_flags')
            ]
            
            for class_name, module_path in config_tests:
                try:
                    module = importlib.import_module(module_path)
                    if not hasattr(module, class_name):
                        continue
                    
                    cls = getattr(module, class_name)
                    
                    # Check if it's a dataclass for config classes
                    if class_name in ['BaseConfig', 'DevConfig', 'ProdConfig']:
                        if not hasattr(cls, '__dataclass_fields__'):
                            self.warnings.append({
                                'type': 'config_not_dataclass',
                                'message': f'Configuration class {class_name} is not a dataclass',
                                'severity': 'warning',
                                'module': module_path,
                                'class': class_name
                            })
                    
                    # Check for required configuration attributes
                    if class_name == 'BaseConfig':
                        required_attrs = ['site_id', 'site_name', 'base_url', 'environment']
                        instance = cls() if hasattr(cls, '__init__') and not inspect.isabstract(cls) else None
                        if instance:
                            for attr in required_attrs:
                                if not hasattr(instance, attr):
                                    self.errors.append({
                                        'type': 'config_attribute_missing',
                                        'message': f'Required configuration attribute {attr} missing from {class_name}',
                                        'severity': 'critical',
                                        'module': module_path,
                                        'class': class_name,
                                        'attribute': attr
                                    })
                    
                except Exception as e:
                    self.errors.append({
                        'type': 'config_validation_error',
                        'message': f'Error validating configuration {class_name}: {str(e)}',
                        'severity': 'error',
                        'module': module_path,
                        'class': class_name
                    })
            
        except Exception as e:
            self.errors.append({
                'type': 'configuration_validation_error',
                'message': f'Configuration validation failed: {str(e)}',
                'severity': 'critical'
            })
    
    async def _validate_component_compatibility(self) -> None:
        """Validate component compatibility and integration."""
        try:
            # Test component registry
            try:
                from src.sites._template.components import COMPONENT_REGISTRY
                if not isinstance(COMPONENT_REGISTRY, dict):
                    self.errors.append({
                        'type': 'invalid_component_registry',
                        'message': 'Component registry is not a dictionary',
                        'severity': 'critical',
                        'module': 'src.sites._template.components'
                    })
                
                expected_components = ['oauth_auth', 'rate_limiter', 'stealth_handler']
                for component in expected_components:
                    if component not in COMPONENT_REGISTRY:
                        self.errors.append({
                            'type': 'component_missing_from_registry',
                            'message': f'Component {component} missing from registry',
                            'severity': 'critical',
                            'component': component
                        })
                
            except ImportError as e:
                self.errors.append({
                    'type': 'component_registry_import_error',
                    'message': f'Failed to import component registry: {str(e)}',
                    'severity': 'critical'
                })
            
            # Test flow registry
            try:
                from src.sites._template.flows import FLOW_REGISTRY
                if not isinstance(FLOW_REGISTRY, dict):
                    self.errors.append({
                        'type': 'invalid_flow_registry',
                        'message': 'Flow registry is not a dictionary',
                        'severity': 'critical',
                        'module': 'src.sites._template.flows'
                    })
                
            except ImportError as e:
                self.errors.append({
                    'type': 'flow_registry_import_error',
                    'message': f'Failed to import flow registry: {str(e)}',
                    'severity': 'critical'
                })
            
        except Exception as e:
            self.errors.append({
                'type': 'component_compatibility_validation_error',
                'message': f'Component compatibility validation failed: {str(e)}',
                'severity': 'critical'
            })
    
    async def _validate_async_patterns(self) -> None:
        """Validate async/await patterns are used correctly."""
        try:
            # Check key async methods
            async_method_tests = [
                ('TemplateScraper', 'src.sites._template.scraper', ['setup_components', 'scrape_with_modular_components']),
                ('BaseTemplateFlow', 'src.sites._template.flows.base_flow', ['navigate_to', 'wait_for_element']),
                ('DataNormalizer', 'src.sites._template.processors.normalizer', ['process']),
                ('OAuthAuthComponent', 'src.sites._template.components.oauth_auth', ['execute', 'initialize'])
            ]
            
            for class_name, module_path, method_names in async_method_tests:
                try:
                    module = importlib.import_module(module_path)
                    if not hasattr(module, class_name):
                        continue
                    
                    cls = getattr(module, class_name)
                    
                    for method_name in method_names:
                        if hasattr(cls, method_name):
                            method = getattr(cls, method_name)
                            if not inspect.iscoroutinefunction(method):
                                self.warnings.append({
                                    'type': 'method_not_async',
                                    'message': f'Method {method_name} in {class_name} should be async',
                                    'severity': 'warning',
                                    'module': module_path,
                                    'class': class_name,
                                    'method': method_name
                                })
                
                except Exception as e:
                    self.warnings.append({
                        'type': 'async_pattern_validation_error',
                        'message': f'Error validating async patterns for {class_name}: {str(e)}',
                        'severity': 'warning',
                        'module': module_path,
                        'class': class_name
                    })
            
        except Exception as e:
            self.errors.append({
                'type': 'async_patterns_validation_error',
                'message': f'Async patterns validation failed: {str(e)}',
                'severity': 'error'
            })
    
    async def _validate_documentation(self) -> None:
        """Validate documentation completeness."""
        try:
            # Check README exists and has content
            readme_path = self.template_path / 'README.md'
            if readme_path.exists():
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                
                if len(readme_content) < 1000:
                    self.warnings.append({
                        'type': 'incomplete_documentation',
                        'message': 'README.md appears to be incomplete or too short',
                        'severity': 'warning',
                        'path': str(readme_path)
                    })
                
                # Check for key sections
                required_sections = ['Features', 'Getting Started', 'Usage', 'Configuration']
                for section in required_sections:
                    if section.lower() not in readme_content.lower():
                        self.warnings.append({
                            'type': 'missing_documentation_section',
                            'message': f'README.md missing section: {section}',
                            'severity': 'warning',
                            'path': str(readme_path),
                            'section': section
                        })
            
            # Check docstrings in key modules
            docstring_tests = [
                ('src.sites._template.scraper', 'TemplateScraper'),
                ('src.sites._template.flows.base_flow', 'BaseTemplateFlow'),
                ('src.sites._template.components.oauth_auth', 'OAuthAuthComponent')
            ]
            
            for module_path, class_name in docstring_tests:
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, class_name):
                        cls = getattr(module, class_name)
                        if not cls.__doc__ or len(cls.__doc__.strip()) < 50:
                            self.warnings.append({
                                'type': 'missing_class_docstring',
                                'message': f'Class {class_name} has insufficient documentation',
                                'severity': 'info',
                                'module': module_path,
                                'class': class_name
                            })
                
                except Exception:
                    pass  # Ignore docstring validation errors
            
        except Exception as e:
            self.warnings.append({
                'type': 'documentation_validation_error',
                'message': f'Documentation validation failed: {str(e)}',
                'severity': 'warning'
            })
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results."""
        if not self.validation_results:
            return {'status': 'not_validated'}
        
        return {
            'status': 'valid' if self.validation_results['valid'] else 'invalid',
            'total_errors': self.validation_results['summary']['total_errors'],
            'total_warnings': self.validation_results['summary']['total_warnings'],
            'critical_issues': self.validation_results['summary']['critical_issues'],
            'execution_time_ms': self.validation_results['execution_time_ms'],
            'validation_timestamp': self.validation_results['validation_timestamp']
        }
    
    def get_error_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize errors by type."""
        if not self.errors:
            return {}
        
        categories = {}
        for error in self.errors:
            error_type = error.get('type', 'unknown')
            if error_type not in categories:
                categories[error_type] = []
            categories[error_type].append(error)
        
        return categories
    
    def get_recommendations(self) -> List[str]:
        """Get recommendations based on validation results."""
        recommendations = []
        
        if self.errors:
            recommendations.append("Fix all critical errors before using the template")
        
        if self.warnings:
            recommendations.append("Review and address warnings for better template quality")
        
        error_categories = self.get_error_categories()
        if 'missing_class_docstring' in error_categories:
            recommendations.append("Add comprehensive docstrings to all classes")
        
        if 'method_not_async' in error_categories:
            recommendations.append("Convert appropriate methods to async/await pattern")
        
        if 'incomplete_documentation' in error_categories:
            recommendations.append("Enhance documentation with more detailed examples")
        
        return recommendations


async def validate_template(template_path: str = None) -> Dict[str, Any]:
    """
    Validate a template directory.
    
    Args:
        template_path: Path to the template directory
        
    Returns:
        Validation results
    """
    validator = TemplateValidator(template_path)
    return await validator.validate_template()


async def quick_validate(template_path: str = None) -> bool:
    """
    Quick validation check - returns True/False.
    
    Args:
        template_path: Path to the template directory
        
    Returns:
        True if template is valid, False otherwise
    """
    results = await validate_template(template_path)
    return results.get('valid', False)
