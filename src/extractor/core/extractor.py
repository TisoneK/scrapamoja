"""
Main Extractor class and configuration system.

This module contains the primary Extractor class that orchestrates
the extraction process, along with configuration and context classes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .rules import (
    ExtractionRule,
    ExtractionResult,
    ExtractionType,
    DataType,
    TransformationType,
)
from ..exceptions import ExtractionError, ValidationError


class ExtractorConfig(BaseModel):
    """Configuration for the Extractor."""
    
    # Performance settings
    max_extraction_time_ms: float = Field(100.0, description="Maximum time per extraction")
    batch_size: int = Field(100, description="Batch size for batch processing")
    enable_caching: bool = Field(True, description="Enable pattern caching")
    
    # Error handling
    strict_mode: bool = Field(False, description="Raise exceptions on errors")
    log_failures: bool = Field(True, description="Log extraction failures")
    max_errors_per_batch: int = Field(10, description="Max errors before stopping batch")
    
    # Validation
    enable_validation: bool = Field(True, description="Enable result validation")
    auto_fix_errors: bool = Field(False, description="Attempt to auto-fix validation errors")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    include_performance_metrics: bool = Field(True, description="Include timing in logs")
    
    # Memory management
    max_memory_mb: int = Field(100, description="Maximum memory usage in MB")
    gc_threshold: int = Field(1000, description="GC trigger threshold")


class ExtractionContext(BaseModel):
    """Context information for extraction operations."""
    
    # Identification
    extraction_id: str = Field(..., description="Unique extraction identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier")
    
    # Source information
    source_url: Optional[str] = Field(None, description="Source URL")
    source_type: str = Field("unknown", description="Source type (html, json, etc.)")
    
    # Metadata
    user_agent: Optional[str] = Field(None, description="User agent string")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    
    # Custom context
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="Custom context data")


class ExtractorStatistics(BaseModel):
    """Extractor performance and usage statistics."""
    
    # Usage metrics
    total_extractions: int = Field(0, description="Total extractions performed")
    successful_extractions: int = Field(0, description="Successful extractions")
    failed_extractions: int = Field(0, description="Failed extractions")
    
    # Performance metrics
    average_extraction_time_ms: float = Field(0.0, description="Average extraction time")
    min_extraction_time_ms: float = Field(0.0, description="Minimum extraction time")
    max_extraction_time_ms: float = Field(0.0, description="Maximum extraction time")
    
    # Cache metrics
    cache_hits: int = Field(0, description="Cache hits")
    cache_misses: int = Field(0, description="Cache misses")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate")
    
    # Memory metrics
    current_memory_mb: float = Field(0.0, description="Current memory usage")
    peak_memory_mb: float = Field(0.0, description="Peak memory usage")
    
    # Error metrics
    error_counts: Dict[str, int] = Field(default_factory=dict, description="Error counts by type")
    warning_counts: Dict[str, int] = Field(default_factory=dict, description="Warning counts by type")
    
    # Timestamps
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Start time")
    last_extraction_time: Optional[datetime] = Field(None, description="Last extraction time")


class Extractor:
    """Main extractor class for structured data extraction."""
    
    def __init__(self, config: Optional[ExtractorConfig] = None):
        """Initialize extractor with optional configuration."""
        self.config = config or ExtractorConfig()
        self._statistics = ExtractorStatistics()
        self._pattern_cache: Dict[str, Any] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured logging for the extractor."""
        # This will be implemented in the logging utilities
        pass
    
    def extract(
        self,
        element: Union[Any, Dict[str, Any], str],
        rules: Union[ExtractionRule, List[ExtractionRule], Dict[str, Any]],
        context: Optional[ExtractionContext] = None,
    ) -> Union[ExtractionResult, Dict[str, ExtractionResult]]:
        """Extract data from element using provided rules."""
        from ..types.text import TextExtractor
        from ..types.attribute import AttributeExtractor
        from ..types.numeric import NumericExtractor
        from ..types.date import DateExtractor
        from ..types.list import ListExtractor
        from .transformers import TransformationEngine
        from .validators import ValidationEngine
        
        # Initialize engines
        text_extractor = TextExtractor()
        attribute_extractor = AttributeExtractor()
        numeric_extractor = NumericExtractor()
        date_extractor = DateExtractor()
        list_extractor = ListExtractor()
        transformation_engine = TransformationEngine()
        validation_engine = ValidationEngine()
        
        # Convert rules to list format
        if isinstance(rules, dict):
            # Convert dict rules to ExtractionRule objects
            rule_list = []
            for field_path, rule_data in rules.items():
                if isinstance(rule_data, ExtractionRule):
                    rule_list.append(rule_data)
                else:
                    # Convert dict to ExtractionRule
                    rule_list.append(ExtractionRule(**rule_data))
        elif isinstance(rules, ExtractionRule):
            rule_list = [rules]
        else:
            rule_list = rules
        
        # Extract for each rule
        results = {}
        
        for rule in rule_list:
            try:
                # Validate rule first
                validation_result = validation_engine.validate_rule(rule)
                if not validation_result.is_valid:
                    if self.config.strict_mode:
                        raise ValidationError(
                            f"Rule validation failed: {validation_result.errors}",
                            rule_name=rule.name
                        )
                    else:
                        # Log validation errors and continue
                        for error in validation_result.errors:
                            self._log_error(f"Rule validation error: {error.error_message}", rule.name)
                
                # Choose extractor based on extraction type
                if rule.extraction_type == ExtractionType.TEXT:
                    result = text_extractor.extract(element, rule, context.__dict__ if context else None)
                elif rule.extraction_type == ExtractionType.ATTRIBUTE:
                    result = attribute_extractor.extract(element, rule, context.__dict__ if context else None)
                elif rule.extraction_type == ExtractionType.REGEX:
                    # Use text extractor with regex pattern
                    result = text_extractor.extract(element, rule, context.__dict__ if context else None)
                elif rule.extraction_type == ExtractionType.LIST:
                    result = list_extractor.extract(element, rule, context.__dict__ if context else None)
                elif rule.extraction_type == ExtractionType.NESTED:
                    # Use text extractor for nested extraction (simplified for now)
                    result = text_extractor.extract(element, rule, context.__dict__ if context else None)
                else:
                    # For now, use text extractor as fallback
                    result = ExtractionResult(
                        value=None,
                        success=False,
                        rule_name=rule.name,
                        extraction_type=rule.extraction_type,
                        target_type=rule.target_type,
                        extraction_time_ms=0.0,
                        errors=[f"Extraction type {rule.extraction_type} not yet implemented"]
                    )
                
                # Handle multi-value extraction
                if result.success and hasattr(rule, 'extract_all') and rule.extract_all:
                    # For multi-value extraction, ensure result is a list
                    if not isinstance(result.value, list):
                        # Convert single value to list
                        result.value = [result.value]
                
                # Apply additional transformations if needed
                if result.success and rule.transformations:
                    from .transformers import TransformationType
                    if isinstance(result.value, list):
                        # Apply transformations to each item in list
                        transformed_list = []
                        for item in result.value:
                            transformed_item = transformation_engine.apply_transformations(
                                item,
                                rule.transformations
                            )
                            transformed_list.append(transformed_item)
                        result.value = transformed_list
                    else:
                        # Apply transformation to single value
                        transformed_value = transformation_engine.apply_transformations(
                            result.value,
                            rule.transformations
                        )
                        result.value = transformed_value
                    
                    # Re-validate after transformation
                    validation_result = validation_engine.validate_result(result, rule)
                    result.validation_passed = validation_result.is_valid
                    result.validation_errors = [error.error_message for error in validation_result.errors]
                
                results[rule.field_path] = result
                
                # Update statistics
                self._update_statistics(
                    success=result.success,
                    extraction_time_ms=result.extraction_time_ms,
                    error_type=None if result.success else "extraction_failed"
                )
                
                # Log if configured
                if self.config.log_failures and not result.success:
                    self._log_error(f"Extraction failed for rule {rule.name}: {result.errors}", rule.name)
                
            except Exception as e:
                # Handle unexpected errors
                error_result = ExtractionResult(
                    value=rule.default_value,
                    success=False,
                    rule_name=rule.name,
                    extraction_type=rule.extraction_type,
                    target_type=rule.target_type,
                    extraction_time_ms=0.0,
                    errors=[str(e)],
                    used_default=True
                )
                
                results[rule.field_path] = error_result
                
                self._update_statistics(
                    success=False,
                    extraction_time_ms=0.0,
                    error_type="unexpected_error"
                )
                
                if self.config.strict_mode:
                    raise
        
        # Return single result if only one rule, otherwise return dict
        if len(results) == 1:
            return list(results.values())[0]
        else:
            return results
    
    def extract_batch(
        self,
        elements: List[Union[Any, Dict[str, Any], str]],
        rules: Union[ExtractionRule, List[ExtractionRule], Dict[str, Any]],
        context: Optional[ExtractionContext] = None,
    ) -> List[Dict[str, ExtractionResult]]:
        """Extract data from multiple elements efficiently."""
        # Placeholder implementation - will be completed in user stories
        raise NotImplementedError("Extract batch method will be implemented in User Story 1")
    
    def validate_rules(
        self,
        rules: Union[ExtractionRule, List[ExtractionRule], Dict[str, Any]],
    ) -> ValidationResult:
        """Validate extraction rules before use."""
        # Placeholder implementation - will be completed in user stories
        raise NotImplementedError("Validate rules method will be implemented in User Story 1")
    
    def get_statistics(self) -> ExtractorStatistics:
        """Get extraction performance and usage statistics."""
        return self._statistics
    
    def _update_statistics(
        self,
        success: bool,
        extraction_time_ms: float,
        error_type: Optional[str] = None,
    ):
        """Update internal statistics."""
        self._statistics.total_extractions += 1
        self._statistics.last_extraction_time = datetime.utcnow()
        
        if success:
            self._statistics.successful_extractions += 1
        else:
            self._statistics.failed_extractions += 1
            if error_type:
                self._statistics.error_counts[error_type] = (
                    self._statistics.error_counts.get(error_type, 0) + 1
                )
        
        # Update timing statistics
        if self._statistics.total_extractions == 1:
            self._statistics.min_extraction_time_ms = extraction_time_ms
            self._statistics.max_extraction_time_ms = extraction_time_ms
            self._statistics.average_extraction_time_ms = extraction_time_ms
        else:
            self._statistics.min_extraction_time_ms = min(
                self._statistics.min_extraction_time_ms, extraction_time_ms
            )
            self._statistics.max_extraction_time_ms = max(
                self._statistics.max_extraction_time_ms, extraction_time_ms
            )
            
            # Update running average
            total_time = (
                self._statistics.average_extraction_time_ms * (self._statistics.total_extractions - 1)
                + extraction_time_ms
            )
            self._statistics.average_extraction_time_ms = total_time / self._statistics.total_extractions
    
    def _log_error(self, message: str, rule_name: Optional[str] = None):
        """Log an error message."""
        if self.config.log_failures:
            # Use Python's logging module since structured logging setup is optional
            import logging
            logger = logging.getLogger("extractor")
            if rule_name:
                logger.error(f"[{rule_name}] {message}")
            else:
                logger.error(message)
