"""
Processors module for the modular site scraper template.

This module contains data processing components that handle
data transformation, normalization, and validation.
"""

from .normalizer import DataNormalizer
from .validator import DataValidator
from .transformer import DataTransformer

__all__ = [
    'DataNormalizer',
    'DataValidator', 
    'DataTransformer'
]

# Version information
__version__ = "1.0.0"
__author__ = "Modular Scraper Template"

# Processor registry for easy access
PROCESSOR_REGISTRY = {
    'normalizer': DataNormalizer,
    'validator': DataValidator,
    'transformer': DataTransformer
}

def get_processor(processor_type: str):
    """
    Get processor class by type.
    
    Args:
        processor_type: Type of processor ('normalizer', 'validator', 'transformer')
        
    Returns:
        Processor class
        
    Raises:
        ValueError: If processor type is not found
    """
    if processor_type not in PROCESSOR_REGISTRY:
        raise ValueError(f"Unknown processor type: {processor_type}. Available types: {list(PROCESSOR_REGISTRY.keys())}")
    
    return PROCESSOR_REGISTRY[processor_type]

def list_available_processors():
    """List all available processor types."""
    return list(PROCESSOR_REGISTRY.keys())

# Processor pipeline for chaining multiple processors
class ProcessorPipeline:
    """Pipeline for chaining multiple data processors."""
    
    def __init__(self):
        """Initialize processor pipeline."""
        self.processors = []
    
    def add_processor(self, processor, name: str = None):
        """
        Add a processor to the pipeline.
        
        Args:
            processor: Processor instance
            name: Optional name for the processor
        """
        self.processors.append({
            'processor': processor,
            'name': name or processor.__class__.__name__
        })
    
    async def process(self, data):
        """
        Process data through all processors in the pipeline.
        
        Args:
            data: Data to process
            
        Returns:
            Processed data
        """
        result = data
        
        for step in self.processors:
            processor = step['processor']
            name = step['name']
            
            try:
                if hasattr(processor, 'execute'):
                    if hasattr(processor.execute, '__call__'):
                        import asyncio
                        if asyncio.iscoroutinefunction(processor.execute):
                            result = await processor.execute(data=data)
                        else:
                            result = processor.execute(data=data)
                        
                        # Extract processed data from result
                        if hasattr(result, 'data') and result.data:
                            result = result.data.get('output_data', result.data)
                    else:
                        result = processor.process(data)
                else:
                    result = processor.process(data)
                    
            except Exception as e:
                print(f"Processor {name} failed: {str(e)}")
                # Continue with original data if processor fails
                continue
        
        return result
    
    def clear(self):
        """Clear all processors from the pipeline."""
        self.processors.clear()
    
    def get_processor_names(self):
        """Get names of all processors in the pipeline."""
        return [step['name'] for step in self.processors]
