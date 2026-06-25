"""
Validators module for the modular site scraper template.

This module contains validation components that handle
configuration validation, data validation, and business rule validation.
"""

from .config_validator import ConfigValidator
from .data_validator import DataValidator

__all__ = [
    'ConfigValidator',
    'DataValidator'
]

# Version information
__version__ = "1.0.0"
__author__ = "Modular Scraper Template"

# Validator registry for easy access
VALIDATOR_REGISTRY = {
    'config': ConfigValidator,
    'data': DataValidator
}

def get_validator(validator_type: str):
    """
    Get validator class by type.
    
    Args:
        validator_type: Type of validator ('config', 'data')
        
    Returns:
        Validator class
        
    Raises:
        ValueError: If validator type is not found
    """
    if validator_type not in VALIDATOR_REGISTRY:
        raise ValueError(f"Unknown validator type: {validator_type}. Available types: {list(VALIDATOR_REGISTRY.keys())}")
    
    return VALIDATOR_REGISTRY[validator_type]

def list_available_validators():
    """List all available validator types."""
    return list(VALIDATOR_REGISTRY.keys())

# Validation pipeline for chaining multiple validators
class ValidationPipeline:
    """Pipeline for chaining multiple validators."""
    
    def __init__(self):
        """Initialize validation pipeline."""
        self.validators = []
        self.stop_on_first_error = False
    
    def add_validator(self, validator, name: str = None):
        """
        Add a validator to the pipeline.
        
        Args:
            validator: Validator instance
            name: Optional name for the validator
        """
        self.validators.append({
            'validator': validator,
            'name': name or validator.__class__.__name__
        })
    
    async def validate(self, data, **kwargs):
        """
        Validate data through all validators in the pipeline.
        
        Args:
            data: Data to validate
            **kwargs: Additional validation parameters
            
        Returns:
            Validation results
        """
        results = []
        overall_success = True
        
        for step in self.validators:
            validator = step['validator']
            name = step['name']
            
            try:
                if hasattr(validator, 'execute'):
                    import asyncio
                    if asyncio.iscoroutinefunction(validator.execute):
                        result = await validator.execute(data, **kwargs)
                    else:
                        result = validator.execute(data, **kwargs)
                else:
                    result = validator.validate(data, **kwargs)
                
                results.append({
                    'validator': name,
                    'success': result.success if hasattr(result, 'success') else result.get('success', True),
                    'result': result
                })
                
                if not results[-1]['success'] and self.stop_on_first_error:
                    break
                    
            except Exception as e:
                results.append({
                    'validator': name,
                    'success': False,
                    'error': str(e)
                })
                
                if self.stop_on_first_error:
                    break
        
        overall_success = all(result['success'] for result in results)
        
        return {
            'overall_success': overall_success,
            'validator_results': results,
            'total_validators': len(self.validators)
        }
    
    def clear(self):
        """Clear all validators from the pipeline."""
        self.validators.clear()
    
    def get_validator_names(self):
        """Get names of all validators in the pipeline."""
        return [step['name'] for step in self.validators]
