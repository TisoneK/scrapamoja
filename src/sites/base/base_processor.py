"""
Base processor class for data transformation in the modular site scraper template system.

This module provides the base class that all processor components must inherit from,
ensuring consistent data processing patterns and enabling proper lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

from .component_interface import BaseComponent, ComponentContext, ComponentResult


@dataclass
class ProcessingRule:
    """Rule for data transformation."""
    rule_id: str
    name: str
    input_type: str
    output_type: str
    transformation: str
    parameters: Dict[str, Any]
    required: bool = True
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class TransformationResult:
    """Result object for data transformation."""
    success: bool
    input_data: Any
    output_data: Any
    transformations_applied: List[str]
    errors: List[str]
    warnings: List[str]
    processing_time_ms: float
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.transformations_applied is None:
            self.transformations_applied = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationResult:
    """Result object for data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validation_time_ms: float
    schema_version: str
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseProcessor(BaseComponent):
    """Base class for all processor components in the modular template system."""
    
    def __init__(
        self,
        component_id: str,
        name: str,
        version: str,
        description: str,
        processor_type: str,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        transformation_rules: Optional[List[ProcessingRule]] = None
    ):
        """
        Initialize the base processor.
        
        Args:
            component_id: Unique identifier for the processor
            name: Human-readable name for the processor
            version: Processor version following semantic versioning
            description: Processor description
            processor_type: Type of processor (NORMALIZER, VALIDATOR, TRANSFORMER)
            input_schema: Schema for input data validation
            output_schema: Schema for output data validation
            transformation_rules: List of transformation rules
        """
        super().__init__(component_id, name, version, description)
        self.processor_type = processor_type
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
        self.transformation_rules = transformation_rules or []
        self._processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'average_processing_time_ms': 0.0
        }
    
    @property
    def processor_type(self) -> str:
        """Get processor type."""
        return self._processor_type
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get input schema."""
        return self._input_schema
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Get output schema."""
        return self._output_schema
    
    @property
    def transformation_rules(self) -> List[ProcessingRule]:
        """Get transformation rules."""
        return self._transformation_rules
    
    @property
    def processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self._processing_stats
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize the processor with given context.
        
        Args:
            context: Component execution context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._context = context
            
            # Validate transformation rules
            for rule in self.transformation_rules:
                if not await self._validate_transformation_rule(rule):
                    self._log_operation("initialize", f"Invalid transformation rule: {rule.rule_id}", "error")
                    return False
            
            self._log_operation("initialize", f"Processor {self.component_id} initialized successfully")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Failed to initialize processor: {str(e)}", "error")
            return False
    
    @abstractmethod
    async def process(self, data: Any) -> TransformationResult:
        """
        Process data according to processor type.
        
        Args:
            data: Input data to process
            
        Returns:
            Transformation result
        """
        pass
    
    async def validate_input(self, data: Any) -> ValidationResult:
        """
        Validate input data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Validation result
        """
        try:
            start_time = datetime.utcnow()
            errors = []
            warnings = []
            
            # Basic validation
            if data is None:
                errors.append("Input data is None")
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    validation_time_ms=0.0,
                    schema_version="1.0.0"
                )
            
            # Schema validation (if schema is defined)
            if self.input_schema:
                schema_errors = await self._validate_against_schema(data, self.input_schema)
                errors.extend(schema_errors)
            
            end_time = datetime.utcnow()
            validation_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_time_ms=validation_time,
                schema_version="1.0.0"
            )
            
        except Exception as e:
            self._log_operation("validate_input", f"Input validation failed: {str(e)}", "error")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                validation_time_ms=0.0,
                schema_version="1.0.0"
            )
    
    async def validate_output(self, data: Any) -> ValidationResult:
        """
        Validate output data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Validation result
        """
        try:
            start_time = datetime.utcnow()
            errors = []
            warnings = []
            
            # Basic validation
            if data is None:
                errors.append("Output data is None")
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    validation_time_ms=0.0,
                    schema_version="1.0.0"
                )
            
            # Schema validation (if schema is defined)
            if self.output_schema:
                schema_errors = await self._validate_against_schema(data, self.output_schema)
                errors.extend(schema_errors)
            
            end_time = datetime.utcnow()
            validation_time = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_time_ms=validation_time,
                schema_version="1.0.0"
            )
            
        except Exception as e:
            self._log_operation("validate_output", f"Output validation failed: {str(e)}", "error")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                validation_time_ms=0.0,
                schema_version="1.0.0"
            )
    
    async def apply_transformation_rules(self, data: Any) -> TransformationResult:
        """
        Apply all transformation rules to data.
        
        Args:
            data: Data to transform
            
        Returns:
            Transformation result
        """
        try:
            start_time = datetime.utcnow()
            transformed_data = data
            transformations_applied = []
            errors = []
            warnings = []
            
            for rule in self.transformation_rules:
                try:
                    transformed_data = await self._apply_single_rule(transformed_data, rule)
                    transformations_applied.append(rule.rule_id)
                except Exception as e:
                    error_msg = f"Rule {rule.rule_id} failed: {str(e)}"
                    errors.append(error_msg)
                    if rule.required:
                        # If required rule fails, stop processing
                        break
                    else:
                        warnings.append(f"Optional rule {rule.rule_id} failed: {str(e)}")
                        continue
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            return TransformationResult(
                success=len(errors) == 0,
                input_data=data,
                output_data=transformed_data,
                transformations_applied=transformations_applied,
                errors=errors,
                warnings=warnings,
                processing_time_ms=processing_time,
                metadata={
                    'processor_id': self.component_id,
                    'processor_type': self.processor_type,
                    'rules_count': len(self.transformation_rules),
                    'rules_applied': len(transformations_applied)
                }
            )
            
        except Exception as e:
            self._log_operation("apply_transformation_rules", f"Transformation failed: {str(e)}", "error")
            return TransformationResult(
                success=False,
                input_data=data,
                output_data=data,
                transformations_applied=[],
                errors=[f"Transformation error: {str(e)}"],
                warnings=[],
                processing_time_ms=0.0,
                metadata={'processor_id': self.component_id}
            )
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute the processor's main functionality.
        
        Args:
            **kwargs: Processor-specific arguments (should include 'data')
            
        Returns:
            Component execution result
        """
        try:
            data = kwargs.get('data')
            if data is None:
                raise ValueError("No data provided for processing")
            
            # Validate input
            input_validation = await self.validate_input(data)
            if not input_validation.is_valid:
                return self._create_result(
                    success=False,
                    data={'validation_errors': input_validation.errors},
                    errors=input_validation.errors
                )
            
            # Process data
            processing_result = await self.process(data)
            
            # Validate output
            output_validation = await self.validate_output(processing_result.output_data)
            if not output_validation.is_valid:
                return self._create_result(
                    success=False,
                    data={
                        'processing_result': processing_result.__dict__,
                        'validation_errors': output_validation.errors
                    },
                    errors=output_validation.errors
                )
            
            # Update statistics
            self._update_processing_stats(processing_result.success, processing_result.processing_time_ms)
            
            return self._create_result(
                success=processing_result.success,
                data={
                    'transformation_result': processing_result.__dict__,
                    'input_validation': input_validation.__dict__,
                    'output_validation': output_validation.__dict__
                },
                errors=processing_result.errors,
                warnings=processing_result.warnings,
                execution_time_ms=processing_result.processing_time_ms
            )
            
        except Exception as e:
            self._log_operation("execute", f"Processor execution failed: {str(e)}", "error")
            return self._create_result(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def validate(self, **kwargs) -> bool:
        """
        Validate processor configuration and dependencies.
        
        Args:
            **kwargs: Validation parameters
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Validate transformation rules
            for rule in self.transformation_rules:
                if not await self._validate_transformation_rule(rule):
                    return False
            
            # Validate schemas (if present)
            if self.input_schema and not await self._validate_schema_definition(self.input_schema):
                return False
            
            if self.output_schema and not await self._validate_schema_definition(self.output_schema):
                return False
            
            self._log_operation("validate", "Processor validation passed")
            return True
            
        except Exception as e:
            self._log_operation("validate", f"Processor validation failed: {str(e)}", "error")
            return False
    
    async def cleanup(self) -> None:
        """Clean up processor resources."""
        try:
            self._log_operation("cleanup", f"Cleaning up processor {self.component_id}")
            
            # Reset statistics
            self._processing_stats = {
                'total_processed': 0,
                'successful_processed': 0,
                'failed_processed': 0,
                'average_processing_time_ms': 0.0
            }
            
            # Clear references
            self._context = None
            
        except Exception as e:
            self._log_operation("cleanup", f"Cleanup failed: {str(e)}", "error")
    
    async def _validate_transformation_rule(self, rule: ProcessingRule) -> bool:
        """Validate a single transformation rule."""
        try:
            # Basic validation
            if not rule.rule_id or not rule.name:
                return False
            
            if not rule.transformation:
                return False
            
            # Type validation
            valid_types = ['string', 'number', 'boolean', 'array', 'object']
            if rule.input_type not in valid_types or rule.output_type not in valid_types:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _validate_against_schema(self, data: Any, schema: Dict[str, Any]) -> List[str]:
        """Validate data against schema (basic implementation)."""
        errors = []
        
        # This is a basic implementation - in a real system, use jsonschema or similar
        if 'type' in schema:
            expected_type = schema['type']
            if expected_type == 'string' and not isinstance(data, str):
                errors.append(f"Expected string, got {type(data).__name__}")
            elif expected_type == 'number' and not isinstance(data, (int, float)):
                errors.append(f"Expected number, got {type(data).__name__}")
            elif expected_type == 'boolean' and not isinstance(data, bool):
                errors.append(f"Expected boolean, got {type(data).__name__}")
            elif expected_type == 'array' and not isinstance(data, list):
                errors.append(f"Expected array, got {type(data).__name__}")
            elif expected_type == 'object' and not isinstance(data, dict):
                errors.append(f"Expected object, got {type(data).__name__}")
        
        return errors
    
    async def _validate_schema_definition(self, schema: Dict[str, Any]) -> bool:
        """Validate schema definition."""
        try:
            # Basic validation
            if not isinstance(schema, dict):
                return False
            
            if 'type' not in schema:
                return False
            
            valid_types = ['string', 'number', 'boolean', 'array', 'object']
            if schema['type'] not in valid_types:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _apply_single_rule(self, data: Any, rule: ProcessingRule) -> Any:
        """Apply a single transformation rule."""
        # This is a basic implementation - specific processors should override
        transformation = rule.transformation.lower()
        
        if transformation == 'uppercase' and isinstance(data, str):
            return data.upper()
        elif transformation == 'lowercase' and isinstance(data, str):
            return data.lower()
        elif transformation == 'trim' and isinstance(data, str):
            return data.strip()
        elif transformation == 'to_number' and isinstance(data, str):
            try:
                return float(data)
            except ValueError:
                return data
        else:
            # Return data unchanged if transformation not recognized
            return data
    
    def _update_processing_stats(self, success: bool, processing_time_ms: float):
        """Update processing statistics."""
        self._processing_stats['total_processed'] += 1
        
        if success:
            self._processing_stats['successful_processed'] += 1
        else:
            self._processing_stats['failed_processed'] += 1
        
        # Update average processing time
        total = self._processing_stats['total_processed']
        current_avg = self._processing_stats['average_processing_time_ms']
        self._processing_stats['average_processing_time_ms'] = (
            (current_avg * (total - 1) + processing_time_ms) / total
        )


class ProcessorError(Exception):
    """Exception raised when processor operations fail."""
    pass


class ValidationError(ProcessorError):
    """Exception raised when data validation fails."""
    pass


class TransformationError(ProcessorError):
    """Exception raised when data transformation fails."""
    pass
