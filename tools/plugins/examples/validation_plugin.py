"""
Example validation plugin for the plugin system.

This plugin demonstrates how to create a validation plugin that can be
automatically integrated into the scraping pipeline to validate extracted data.
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sites.base.plugin_interface import (
    BasePlugin, PluginContext, PluginResult, PluginMetadata, 
    PluginType, HookType, register_plugin
)


class ValidationPlugin(BasePlugin):
    """Example validation plugin for data validation."""
    
    def __init__(self):
        """Initialize validation plugin."""
        super().__init__()
        
        # Validation rules
        self._validation_rules = {
            'email': {
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'required': False,
                'message': 'Invalid email format'
            },
            'phone': {
                'pattern': r'^\+?1?-?\.?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})$',
                'required': False,
                'message': 'Invalid phone number format'
            },
            'url': {
                'pattern': r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$',
                'required': False,
                'message': 'Invalid URL format'
            },
            'date': {
                'pattern': r'^\d{4}-\d{2}-\d{2}$',
                'required': False,
                'message': 'Invalid date format (YYYY-MM-DD)'
            },
            'numeric': {
                'pattern': r'^-?\d+\.?\d*$',
                'required': False,
                'message': 'Invalid numeric format'
            }
        }
        
        # Validation statistics
        self._stats = {
            'validations_performed': 0,
            'validations_passed': 0,
            'validations_failed': 0,
            'fields_validated': {},
            'common_errors': {}
        }
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id="validation_plugin",
            name="Data Validation Plugin",
            version="1.0.0",
            description="Validates extracted data against configurable rules",
            author="Scorewise Team",
            plugin_type=PluginType.VALIDATION,
            dependencies=[],
            permissions=["data_access"],
            hooks=[
                HookType.AFTER_EXTRACT,
                HookType.BEFORE_EXTRACT,
                HookType.VALIDATION_FAILED
            ],
            configuration_schema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable validation"
                    },
                    "strict_mode": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable strict validation mode"
                    },
                    "custom_rules": {
                        "type": "object",
                        "description": "Custom validation rules"
                    },
                    "field_mappings": {
                        "type": "object",
                        "description": "Field name to validation type mappings"
                    }
                }
            },
            tags=["validation", "data-quality", "example"]
        )
    
    async def _on_initialize(self, context: PluginContext) -> bool:
        """Initialize the validation plugin."""
        try:
            # Load configuration
            config = context.configuration
            
            # Set default configuration
            self._enabled = config.get('enabled', True)
            self._strict_mode = config.get('strict_mode', False)
            self._custom_rules = config.get('custom_rules', {})
            self._field_mappings = config.get('field_mappings', {})
            
            # Merge custom rules
            self._validation_rules.update(self._custom_rules)
            
            self._logger.info(f"Validation plugin initialized - Enabled: {self._enabled}, Strict: {self._strict_mode}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize validation plugin: {str(e)}")
            return False
    
    async def _on_execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        """Execute the validation plugin."""
        if not self._enabled:
            return PluginResult(
                success=True,
                plugin_id=self.metadata.id,
                hook_type=hook_type,
                data={"skipped": True, "reason": "validation_disabled"}
            )
        
        try:
            if hook_type == HookType.AFTER_EXTRACT:
                return await self._validate_extracted_data(context, **kwargs)
            elif hook_type == HookType.BEFORE_EXTRACT:
                return await self._validate_extraction_context(context, **kwargs)
            else:
                return PluginResult(
                    success=True,
                    plugin_id=self.metadata.id,
                    hook_type=hook_type,
                    data={"skipped": True, "reason": "unsupported_hook"}
                )
                
        except Exception as e:
            self._logger.error(f"Validation plugin execution failed: {str(e)}")
            return PluginResult(
                success=False,
                plugin_id=self.metadata.id,
                hook_type=hook_type,
                errors=[str(e)]
            )
    
    async def _validate_extracted_data(self, context: PluginContext, **kwargs) -> PluginResult:
        """Validate extracted data."""
        extracted_data = kwargs.get('extracted_data', {})
        if not extracted_data:
            return PluginResult(
                success=True,
                plugin_id=self.metadata.id,
                hook_type=HookType.AFTER_EXTRACT,
                data={"skipped": True, "reason": "no_data_to_validate"}
            )
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'field_results': {},
            'statistics': {}
        }
        
        # Validate each field
        for field_name, field_value in extracted_data.items():
            field_result = await self._validate_field(field_name, field_value)
            validation_results['field_results'][field_name] = field_result
            
            if not field_result['valid']:
                validation_results['valid'] = False
                validation_results['errors'].extend(field_result['errors'])
            
            validation_results['warnings'].extend(field_result['warnings'])
        
        # Update statistics
        self._update_statistics(validation_results)
        
        # Add statistics to result
        validation_results['statistics'] = self._get_statistics()
        
        # Log validation results
        if not validation_results['valid']:
            self._logger.warning(f"Validation failed for {len(validation_results['errors'])} fields")
        
        return PluginResult(
            success=validation_results['valid'],
            plugin_id=self.metadata.id,
            hook_type=HookType.AFTER_EXTRACT,
            data=validation_results
        )
    
    async def _validate_extraction_context(self, context: PluginContext, **kwargs) -> PluginResult:
        """Validate extraction context before extraction."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate context
        if not context.framework_context:
            validation_results['valid'] = False
            validation_results['errors'].append("Missing framework context")
        
        # Validate extraction parameters
        extraction_params = kwargs.get('extraction_params', {})
        if not extraction_params:
            validation_results['warnings'].append("No extraction parameters provided")
        
        return PluginResult(
            success=validation_results['valid'],
            plugin_id=self.metadata.id,
            hook_type=HookType.BEFORE_EXTRACT,
            data=validation_results
        )
    
    async def _validate_field(self, field_name: str, field_value: Any) -> Dict[str, Any]:
        """Validate a single field."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'validation_type': None,
            'original_value': field_value,
            'normalized_value': None
        }
        
        if field_value is None or field_value == '':
            # Check if field is required
            if self._is_field_required(field_name):
                result['valid'] = False
                result['errors'].append(f"Required field '{field_name}' is empty")
            return result
        
        # Determine validation type
        validation_type = self._get_validation_type(field_name)
        result['validation_type'] = validation_type
        
        if not validation_type:
            # No validation rule for this field
            result['warnings'].append(f"No validation rule for field '{field_name}'")
            return result
        
        # Get validation rule
        rule = self._validation_rules.get(validation_type)
        if not rule:
            result['warnings'].append(f"Validation rule not found for type '{validation_type}'")
            return result
        
        # Perform validation
        try:
            # Convert to string for regex matching
            str_value = str(field_value).strip()
            
            # Apply regex pattern
            if rule['pattern']:
                pattern = re.compile(rule['pattern'])
                if not pattern.match(str_value):
                    result['valid'] = False
                    result['errors'].append(f"Field '{field_name}': {rule['message']}")
            
            # Normalize value if valid
            if result['valid']:
                result['normalized_value'] = self._normalize_value(str_value, validation_type)
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Validation error for field '{field_name}': {str(e)}")
        
        # Update field statistics
        self._update_field_statistics(field_name, result['valid'])
        
        return result
    
    def _is_field_required(self, field_name: str) -> bool:
        """Check if a field is required."""
        # In strict mode, more fields are required
        if self._strict_mode:
            required_fields = ['title', 'url', 'content']
            return field_name.lower() in required_fields
        
        return False
    
    def _get_validation_type(self, field_name: str) -> Optional[str]:
        """Get validation type for a field."""
        # Check field mappings first
        if field_name in self._field_mappings:
            return self._field_mappings[field_name]
        
        # Infer from field name
        field_lower = field_name.lower()
        
        if 'email' in field_lower:
            return 'email'
        elif 'phone' in field_lower or 'tel' in field_lower:
            return 'phone'
        elif 'url' in field_lower or 'link' in field_lower:
            return 'url'
        elif 'date' in field_lower:
            return 'date'
        elif field_lower in ['price', 'cost', 'amount', 'quantity', 'count', 'number']:
            return 'numeric'
        
        return None
    
    def _normalize_value(self, value: str, validation_type: str) -> str:
        """Normalize a value based on its validation type."""
        if validation_type == 'email':
            return value.lower().strip()
        elif validation_type == 'phone':
            # Remove all non-digit characters except +
            return re.sub(r'[^\d+]', '', value)
        elif validation_type == 'url':
            # Ensure URL has protocol
            if not value.startswith(('http://', 'https://')):
                return f'https://{value}'
            return value
        elif validation_type == 'numeric':
            # Remove formatting
            return re.sub(r'[^\d.-]', '', value)
        
        return value.strip()
    
    def _update_statistics(self, validation_results: Dict[str, Any]) -> None:
        """Update validation statistics."""
        self._stats['validations_performed'] += 1
        
        if validation_results['valid']:
            self._stats['validations_passed'] += 1
        else:
            self._stats['validations_failed'] += 1
        
        # Track common errors
        for error in validation_results['errors']:
            error_type = error.split(':')[0] if ':' in error else error
            self._stats['common_errors'][error_type] = self._stats['common_errors'].get(error_type, 0) + 1
    
    def _update_field_statistics(self, field_name: str, is_valid: bool) -> None:
        """Update field-specific statistics."""
        if field_name not in self._stats['fields_validated']:
            self._stats['fields_validated'][field_name] = {
                'total': 0,
                'valid': 0,
                'invalid': 0
            }
        
        self._stats['fields_validated'][field_name]['total'] += 1
        
        if is_valid:
            self._stats['fields_validated'][field_name]['valid'] += 1
        else:
            self._stats['fields_validated'][field_name]['invalid'] += 1
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        stats = self._stats.copy()
        
        # Calculate success rate
        if stats['validations_performed'] > 0:
            stats['success_rate'] = stats['validations_passed'] / stats['validations_performed']
        else:
            stats['success_rate'] = 0.0
        
        # Calculate field success rates
        for field_name, field_stats in stats['fields_validated'].items():
            if field_stats['total'] > 0:
                field_stats['success_rate'] = field_stats['valid'] / field_stats['total']
            else:
                field_stats['success_rate'] = 0.0
        
        return stats
    
    async def _on_validate_configuration(self, configuration: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        # Check configuration structure
        if not isinstance(configuration, dict):
            return False
        
        # Validate custom rules if provided
        custom_rules = configuration.get('custom_rules', {})
        if custom_rules:
            for rule_name, rule_config in custom_rules.items():
                if not isinstance(rule_config, dict):
                    return False
                
                if 'pattern' not in rule_config:
                    return False
                
                # Test regex pattern
                try:
                    re.compile(rule_config['pattern'])
                except re.error:
                    return False
        
        return True
    
    async def _register_hooks(self) -> None:
        """Register plugin hooks."""
        self.add_hook(HookType.AFTER_EXTRACT, self._execute)
        self.add_hook(HookType.BEFORE_EXTRACT, self._execute)
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get plugin telemetry data."""
        telemetry = super().get_telemetry()
        
        # Add validation-specific telemetry
        telemetry.update({
            'validation_statistics': self._get_statistics(),
            'validation_rules_count': len(self._validation_rules),
            'custom_rules_count': len(self._custom_rules),
            'field_mappings_count': len(self._field_mappings),
            'strict_mode_enabled': self._strict_mode,
            'plugin_enabled': self._enabled
        })
        
        return telemetry


# Register the plugin
register_plugin(ValidationPlugin())


# Convenience function for creating validation plugin instances
def create_validation_plugin(config: Optional[Dict[str, Any]] = None) -> ValidationPlugin:
    """Create a validation plugin instance with optional configuration."""
    plugin = ValidationPlugin()
    
    if config:
        # Update plugin configuration
        plugin._config.update(config)
    
    return plugin


# Example usage function
async def example_usage():
    """Example usage of the validation plugin."""
    # Create plugin instance
    plugin = create_validation_plugin({
        'enabled': True,
        'strict_mode': False,
        'field_mappings': {
            'user_email': 'email',
            'contact_phone': 'phone',
            'website_url': 'url'
        }
    })
    
    # Create mock context
    from src.sites.base.plugin_interface import PluginContext
    context = PluginContext(
        plugin_id="validation_plugin",
        plugin_metadata=plugin.metadata,
        framework_context=None,
        configuration=plugin._config
    )
    
    # Initialize plugin
    success = await plugin.initialize(context)
    print(f"Plugin initialized: {success}")
    
    # Test validation
    test_data = {
        'title': 'Test Article',
        'user_email': 'invalid-email',
        'contact_phone': '123-456-7890',
        'website_url': 'example.com',
        'description': 'This is a test article'
    }
    
    result = await plugin.execute(context, HookType.AFTER_EXTRACT, extracted_data=test_data)
    
    print(f"Validation result: {result.success}")
    print(f"Validation data: {result.data}")
    
    # Get telemetry
    telemetry = plugin.get_telemetry()
    print(f"Telemetry: {telemetry['validation_statistics']}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
