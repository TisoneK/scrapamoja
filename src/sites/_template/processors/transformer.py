"""
Data transformer template for the modular site scraper template.

This module provides data transformation functionality with configurable
rules for converting, mapping, and enriching scraped data.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import re
import json
from urllib.parse import urlparse, parse_qs

from src.sites.base.base_processor import BaseProcessor
from src.sites.base.component_interface import ComponentResult


class DataTransformer(BaseProcessor):
    """Data transformer with configurable transformation rules."""
    
    def __init__(
        self,
        component_id: str = "data_transformer",
        name: str = "Data Transformer",
        version: str = "1.0.0",
        description: str = "Transforms and enriches scraped data with configurable rules"
    ):
        """
        Initialize data transformer.
        
        Args:
            component_id: Unique identifier for the processor
            name: Human-readable name for the processor
            version: Processor version
            description: Processor description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            processor_type="TRANSFORMER"
        )
        
        # Transformation configuration
        self._enable_field_mapping: bool = True
        self._enable_value_mapping: bool = True
        self._enable_data_enrichment: bool = True
        self._enable_conditional_transforms: bool = True
        self._enable_calculated_fields: bool = True
        self._enable_data_aggregation: bool = True
        
        # Transformation rules
        self._field_mappings: Dict[str, str] = {}
        self._value_mappings: Dict[str, Dict[str, Any]] = {}
        self._conditional_transforms: Dict[str, List[Dict[str, Any]]] = {}
        self._calculated_fields: Dict[str, Dict[str, Any]] = {}
        self._custom_transformers: Dict[str, Callable] = {}
        
        # Data enrichment sources
        self._enrichment_sources: Dict[str, Any] = {}
    
    async def execute(self, data: Any, **kwargs) -> ComponentResult:
        """
        Execute data transformation.
        
        Args:
            data: Data to transform
            **kwargs: Additional transformation parameters
            
        Returns:
            Transformation result
        """
        try:
            start_time = datetime.utcnow()
            
            # Handle different data types
            if isinstance(data, list):
                transformed_data = await self._transform_list(data)
            elif isinstance(data, dict):
                transformed_data = await self._transform_dict(data)
            else:
                transformed_data = await self._transform_value(data)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=True,
                data={
                    'output_data': transformed_data,
                    'input_type': type(data).__name__,
                    'output_type': type(transformed_data).__name__,
                    'transformations_applied': self._get_applied_transformations(),
                    'execution_time_ms': execution_time
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Transformation failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _transform_list(self, data_list: List[Any]) -> List[Any]:
        """Transform a list of data items."""
        transformed_list = []
        
        for item in data_list:
            if isinstance(item, dict):
                transformed_item = await self._transform_dict(item)
            elif isinstance(item, list):
                transformed_item = await self._transform_list(item)
            else:
                transformed_item = await self._transform_value(item)
            
            transformed_list.append(transformed_item)
        
        return transformed_list
    
    async def _transform_dict(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a dictionary of data."""
        transformed_dict = {}
        
        # Apply field mappings
        if self._enable_field_mapping:
            for old_field, new_field in self._field_mappings.items():
                if old_field in data_dict:
                    transformed_dict[new_field] = data_dict[old_field]
        
        # Transform remaining fields
        for key, value in data_dict.items():
            # Skip if field was already mapped
            if self._enable_field_mapping and key in self._field_mappings:
                continue
            
            # Apply value mappings
            if self._enable_value_mapping and key in self._value_mappings:
                transformed_value = await self._apply_value_mapping(key, value)
            else:
                transformed_value = await self._transform_value(value)
            
            # Apply conditional transforms
            if self._enable_conditional_transforms and key in self._conditional_transforms:
                transformed_value = await self._apply_conditional_transforms(key, transformed_value)
            
            transformed_dict[key] = transformed_value
        
        # Add calculated fields
        if self._enable_calculated_fields:
            for field_name, field_config in self._calculated_fields.items():
                calculated_value = await self._calculate_field(field_name, field_config, transformed_dict)
                if calculated_value is not None:
                    transformed_dict[field_name] = calculated_value
        
        # Apply data enrichment
        if self._enable_data_enrichment:
            transformed_dict = await self._enrich_data(transformed_dict)
        
        return transformed_dict
    
    async def _transform_value(self, value: Any) -> Any:
        """Transform a single value."""
        if value is None:
            return None
        
        if isinstance(value, str):
            return await self._transform_string(value)
        elif isinstance(value, (int, float)):
            return await self._transform_number(value)
        elif isinstance(value, list):
            return await self._transform_list(value)
        elif isinstance(value, dict):
            return await self._transform_dict(value)
        else:
            return value
    
    async def _transform_string(self, text: str) -> str:
        """Transform a string value."""
        if not isinstance(text, str):
            return str(text)
        
        transformed = text
        
        # Apply custom string transformers
        for name, transformer in self._custom_transformers.items():
            if name.startswith('string_'):
                try:
                    transformed = transformer(transformed)
                except Exception as e:
                    self._log_operation("_transform_string", f"Custom transformer {name} failed: {str(e)}", "error")
        
        return transformed
    
    async def _transform_number(self, number: Union[int, float]) -> Union[int, float]:
        """Transform a numeric value."""
        transformed = number
        
        # Apply custom number transformers
        for name, transformer in self._custom_transformers.items():
            if name.startswith('number_'):
                try:
                    transformed = transformer(transformed)
                except Exception as e:
                    self._log_operation("_transform_number", f"Custom transformer {name} failed: {str(e)}", "error")
        
        return transformed
    
    async def _apply_value_mapping(self, field_name: str, value: Any) -> Any:
        """Apply value mapping rules to a field."""
        if field_name not in self._value_mappings:
            return value
        
        mapping_rules = self._value_mappings[field_name]
        
        # Direct value mapping
        if str(value) in mapping_rules:
            return mapping_rules[str(value)]
        
        # Pattern-based mapping
        for pattern, mapped_value in mapping_rules.items():
            if isinstance(pattern, str) and pattern.startswith('regex:'):
                regex_pattern = pattern[6:]  # Remove 'regex:' prefix
                if re.match(regex_pattern, str(value)):
                    return mapped_value
        
        return value
    
    async def _apply_conditional_transforms(self, field_name: str, value: Any) -> Any:
        """Apply conditional transformation rules to a field."""
        if field_name not in self._conditional_transforms:
            return value
        
        transforms = self._conditional_transforms[field_name]
        transformed_value = value
        
        for transform in transforms:
            condition = transform.get('condition')
            action = transform.get('action')
            
            if await self._evaluate_condition(condition, transformed_value):
                transformed_value = await self._apply_action(action, transformed_value)
        
        return transformed_value
    
    async def _evaluate_condition(self, condition: Dict[str, Any], value: Any) -> bool:
        """Evaluate a transformation condition."""
        condition_type = condition.get('type')
        
        if condition_type == 'equals':
            return value == condition.get('value')
        elif condition_type == 'contains':
            return str(condition.get('value')) in str(value)
        elif condition_type == 'regex':
            return bool(re.match(condition.get('pattern'), str(value)))
        elif condition_type == 'greater_than':
            return float(value) > float(condition.get('value'))
        elif condition_type == 'less_than':
            return float(value) < float(condition.get('value'))
        elif condition_type == 'in_list':
            return value in condition.get('values', [])
        elif condition_type == 'custom':
            custom_evaluator = condition.get('evaluator')
            if custom_evaluator and callable(custom_evaluator):
                return custom_evaluator(value)
        
        return False
    
    async def _apply_action(self, action: Dict[str, Any], value: Any) -> Any:
        """Apply a transformation action."""
        action_type = action.get('type')
        
        if action_type == 'set_value':
            return action.get('value')
        elif action_type == 'prepend':
            return f"{action.get('prefix')}{value}"
        elif action_type == 'append':
            return f"{value}{action.get('suffix')}"
        elif action_type == 'replace':
            old_value = action.get('old')
            new_value = action.get('new')
            return str(value).replace(old_value, new_value)
        elif action_type == 'regex_replace':
            pattern = action.get('pattern')
            replacement = action.get('replacement')
            return re.sub(pattern, replacement, str(value))
        elif action_type == 'uppercase':
            return str(value).upper()
        elif action_type == 'lowercase':
            return str(value).lower()
        elif action_type == 'title_case':
            return str(value).title()
        elif action_type == 'multiply':
            return float(value) * float(action.get('multiplier', 1))
        elif action_type == 'add':
            return float(value) + float(action.get('addend', 0))
        elif action_type == 'custom':
            custom_transformer = action.get('transformer')
            if custom_transformer and callable(custom_transformer):
                return custom_transformer(value)
        
        return value
    
    async def _calculate_field(self, field_name: str, field_config: Dict[str, Any], data: Dict[str, Any]) -> Any:
        """Calculate a derived field."""
        calculation_type = field_config.get('type')
        
        if calculation_type == 'concatenate':
            fields = field_config.get('fields', [])
            separator = field_config.get('separator', ' ')
            values = [str(data.get(field, '')) for field in fields]
            return separator.join(values)
        
        elif calculation_type == 'sum':
            fields = field_config.get('fields', [])
            return sum(float(data.get(field, 0)) for field in fields)
        
        elif calculation_type == 'average':
            fields = field_config.get('fields', [])
            values = [float(data.get(field, 0)) for field in fields]
            return sum(values) / len(values) if values else 0
        
        elif calculation_type == 'count':
            fields = field_config.get('fields', [])
            count = 0
            for field in fields:
                value = data.get(field)
                if isinstance(value, list):
                    count += len(value)
                elif value:
                    count += 1
            return count
        
        elif calculation_type == 'extract':
            source_field = field_config.get('source_field')
            pattern = field_config.get('pattern')
            group = field_config.get('group', 0)
            
            source_value = str(data.get(source_field, ''))
            match = re.search(pattern, source_value)
            return match.group(group) if match else None
        
        elif calculation_type == 'parse_url':
            source_field = field_config.get('source_field')
            component = field_config.get('component')  # scheme, netloc, path, query, fragment
            
            url = str(data.get(source_field, ''))
            try:
                parsed = urlparse(url)
                return getattr(parsed, component, None)
            except:
                return None
        
        elif calculation_type == 'parse_query':
            source_field = field_config.get('source_field')
            param_name = field_config.get('param')
            
            url = str(data.get(source_field, ''))
            try:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                values = query_params.get(param_name, [])
                return values[0] if values else None
            except:
                return None
        
        elif calculation_type == 'custom':
            custom_calculator = field_config.get('calculator')
            if custom_calculator and callable(custom_calculator):
                return custom_calculator(data)
        
        return None
    
    async def _enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich data with additional information."""
        enriched_data = data.copy()
        
        # Add timestamp if not present
        if 'timestamp' not in enriched_data:
            enriched_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Add data hash for integrity checking
        if 'data_hash' not in enriched_data:
            import hashlib
            data_str = json.dumps(data, sort_keys=True)
            enriched_data['data_hash'] = hashlib.md5(data_str.encode()).hexdigest()
        
        # Apply custom enrichment
        for source_name, enricher in self._enrichment_sources.items():
            try:
                if callable(enricher):
                    enrichment = enricher(enriched_data)
                    if isinstance(enrichment, dict):
                        enriched_data.update(enrichment)
            except Exception as e:
                self._log_operation("_enrich_data", f"Enrichment source {source_name} failed: {str(e)}", "error")
        
        return enriched_data
    
    def _get_applied_transformations(self) -> List[str]:
        """Get list of applied transformations."""
        transformations = []
        
        if self._enable_field_mapping:
            transformations.append("field_mapping")
        if self._enable_value_mapping:
            transformations.append("value_mapping")
        if self._enable_data_enrichment:
            transformations.append("data_enrichment")
        if self._enable_conditional_transforms:
            transformations.append("conditional_transforms")
        if self._enable_calculated_fields:
            transformations.append("calculated_fields")
        if self._enable_data_aggregation:
            transformations.append("data_aggregation")
        
        transformations.extend(self._custom_transformers.keys())
        
        return transformations
    
    def configure_transformation(
        self,
        enable_field_mapping: Optional[bool] = None,
        enable_value_mapping: Optional[bool] = None,
        enable_data_enrichment: Optional[bool] = None,
        enable_conditional_transforms: Optional[bool] = None,
        enable_calculated_fields: Optional[bool] = None,
        enable_data_aggregation: Optional[bool] = None
    ) -> None:
        """
        Configure transformation settings.
        
        Args:
            enable_field_mapping: Enable field mapping
            enable_value_mapping: Enable value mapping
            enable_data_enrichment: Enable data enrichment
            enable_conditional_transforms: Enable conditional transforms
            enable_calculated_fields: Enable calculated fields
            enable_data_aggregation: Enable data aggregation
        """
        if enable_field_mapping is not None:
            self._enable_field_mapping = enable_field_mapping
        if enable_value_mapping is not None:
            self._enable_value_mapping = enable_value_mapping
        if enable_data_enrichment is not None:
            self._enable_data_enrichment = enable_data_enrichment
        if enable_conditional_transforms is not None:
            self._enable_conditional_transforms = enable_conditional_transforms
        if enable_calculated_fields is not None:
            self._enable_calculated_fields = enable_calculated_fields
        if enable_data_aggregation is not None:
            self._enable_data_aggregation = enable_data_aggregation
    
    def add_field_mapping(self, old_field: str, new_field: str) -> None:
        """
        Add a field mapping rule.
        
        Args:
            old_field: Original field name
            new_field: New field name
        """
        self._field_mappings[old_field] = new_field
    
    def add_value_mapping(self, field_name: str, mappings: Dict[str, Any]) -> None:
        """
        Add value mapping rules for a field.
        
        Args:
            field_name: Name of the field
            mappings: Dictionary of value mappings
        """
        self._value_mappings[field_name] = mappings
    
    def add_conditional_transform(self, field_name: str, condition: Dict[str, Any], action: Dict[str, Any]) -> None:
        """
        Add a conditional transformation rule.
        
        Args:
            field_name: Name of the field
            condition: Condition dictionary
            action: Action dictionary
        """
        if field_name not in self._conditional_transforms:
            self._conditional_transforms[field_name] = []
        
        self._conditional_transforms[field_name].append({
            'condition': condition,
            'action': action
        })
    
    def add_calculated_field(self, field_name: str, field_config: Dict[str, Any]) -> None:
        """
        Add a calculated field.
        
        Args:
            field_name: Name of the calculated field
            field_config: Field configuration
        """
        self._calculated_fields[field_name] = field_config
    
    def add_custom_transformer(self, name: str, transformer: Callable) -> None:
        """
        Add a custom transformer function.
        
        Args:
            name: Name of the transformer
            transformer: Transformer function
        """
        self._custom_transformers[name] = transformer
    
    def add_enrichment_source(self, source_name: str, enricher: Callable) -> None:
        """
        Add a data enrichment source.
        
        Args:
            source_name: Name of the enrichment source
            enricher: Enrichment function
        """
        self._enrichment_sources[source_name] = enricher
    
    def remove_field_mapping(self, old_field: str) -> None:
        """Remove a field mapping rule."""
        if old_field in self._field_mappings:
            del self._field_mappings[old_field]
    
    def remove_value_mapping(self, field_name: str) -> None:
        """Remove value mapping rules for a field."""
        if field_name in self._value_mappings:
            del self._value_mappings[field_name]
    
    def get_transformation_configuration(self) -> Dict[str, Any]:
        """Get current transformation configuration."""
        return {
            'enable_field_mapping': self._enable_field_mapping,
            'enable_value_mapping': self._enable_value_mapping,
            'enable_data_enrichment': self._enable_data_enrichment,
            'enable_conditional_transforms': self._enable_conditional_transforms,
            'enable_calculated_fields': self._enable_calculated_fields,
            'enable_data_aggregation': self._enable_data_aggregation,
            'field_mappings': self._field_mappings,
            'value_mappings': self._value_mappings,
            'conditional_transforms': self._conditional_transforms,
            'calculated_fields': self._calculated_fields,
            'custom_transformers': list(self._custom_transformers.keys()),
            'enrichment_sources': list(self._enrichment_sources.keys()),
            **self.get_configuration()
        }
