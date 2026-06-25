"""
Data normalizer template for the modular site scraper template.

This module provides data normalization functionality with configurable
rules for cleaning, standardizing, and formatting scraped data.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import re
import html
from urllib.parse import urlparse

from src.sites.base.base_processor import BaseProcessor
from src.sites.base.component_interface import ComponentResult


class DataNormalizer(BaseProcessor):
    """Data normalizer with configurable normalization rules."""
    
    def __init__(
        self,
        component_id: str = "data_normalizer",
        name: str = "Data Normalizer",
        version: str = "1.0.0",
        description: str = "Normalizes and cleans scraped data with configurable rules"
    ):
        """
        Initialize data normalizer.
        
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
            processor_type="NORMALIZER"
        )
        
        # Normalization configuration
        self._enable_html_decode: bool = True
        self._enable_whitespace_normalization: bool = True
        self._enable_case_normalization: bool = False
        self._case_target: str = "lower"  # lower, upper, title
        self._enable_url_normalization: bool = True
        self._enable_date_normalization: bool = True
        self._enable_number_normalization: bool = True
        self._enable_email_normalization: bool = True
        self._enable_phone_normalization: bool = True
        self._custom_normalizers: Dict[str, Callable] = {}
        
        # Normalization rules
        self._field_rules: Dict[str, Dict[str, Any]] = {}
        self._global_rules: Dict[str, Any] = {}
    
    async def execute(self, data: Any, **kwargs) -> ComponentResult:
        """
        Execute data normalization.
        
        Args:
            data: Data to normalize
            **kwargs: Additional normalization parameters
            
        Returns:
            Normalization result
        """
        try:
            start_time = datetime.utcnow()
            
            # Handle different data types
            if isinstance(data, list):
                normalized_data = await self._normalize_list(data)
            elif isinstance(data, dict):
                normalized_data = await self._normalize_dict(data)
            else:
                normalized_data = await self._normalize_value(data)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=True,
                data={
                    'output_data': normalized_data,
                    'input_type': type(data).__name__,
                    'output_type': type(normalized_data).__name__,
                    'normalization_rules_applied': self._get_applied_rules(),
                    'execution_time_ms': execution_time
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Normalization failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _normalize_list(self, data_list: List[Any]) -> List[Any]:
        """Normalize a list of data items."""
        normalized_list = []
        
        for item in data_list:
            if isinstance(item, dict):
                normalized_item = await self._normalize_dict(item)
            elif isinstance(item, list):
                normalized_item = await self._normalize_list(item)
            else:
                normalized_item = await self._normalize_value(item)
            
            normalized_list.append(normalized_item)
        
        return normalized_list
    
    async def _normalize_dict(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a dictionary of data."""
        normalized_dict = {}
        
        for key, value in data_dict.items():
            # Check for field-specific rules
            field_rules = self._field_rules.get(key, {})
            
            # Apply field-specific normalization
            if field_rules:
                normalized_value = await self._apply_field_rules(key, value, field_rules)
            else:
                # Apply global normalization rules
                normalized_value = await self._normalize_value(value)
            
            normalized_dict[key] = normalized_value
        
        return normalized_dict
    
    async def _normalize_value(self, value: Any) -> Any:
        """Normalize a single value."""
        if value is None:
            return None
        
        if isinstance(value, str):
            return await self._normalize_string(value)
        elif isinstance(value, (int, float)):
            return await self._normalize_number(value)
        elif isinstance(value, list):
            return await self._normalize_list(value)
        elif isinstance(value, dict):
            return await self._normalize_dict(value)
        else:
            return value
    
    async def _normalize_string(self, text: str) -> str:
        """Normalize a string value."""
        if not isinstance(text, str):
            return str(text)
        
        normalized = text
        
        # HTML decode
        if self._enable_html_decode:
            normalized = html.unescape(normalized)
        
        # Whitespace normalization
        if self._enable_whitespace_normalization:
            # Remove extra whitespace and normalize line breaks
            normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        # Case normalization
        if self._enable_case_normalization:
            if self._case_target == "lower":
                normalized = normalized.lower()
            elif self._case_target == "upper":
                normalized = normalized.upper()
            elif self._case_target == "title":
                normalized = normalized.title()
        
        # URL normalization
        if self._enable_url_normalization:
            normalized = self._normalize_urls_in_text(normalized)
        
        # Email normalization
        if self._enable_email_normalization:
            normalized = self._normalize_emails_in_text(normalized)
        
        # Phone normalization
        if self._enable_phone_normalization:
            normalized = self._normalize_phones_in_text(normalized)
        
        # Apply custom normalizers
        for name, normalizer in self._custom_normalizers.items():
            try:
                normalized = normalizer(normalized)
            except Exception as e:
                self._log_operation("_normalize_string", f"Custom normalizer {name} failed: {str(e)}", "error")
        
        return normalized
    
    async def _normalize_number(self, number: Union[int, float]) -> Union[int, float]:
        """Normalize a numeric value."""
        if not self._enable_number_normalization:
            return number
        
        # Handle special cases
        if isinstance(number, float):
            # Remove floating point precision issues
            if number.is_integer():
                return int(number)
        
        return number
    
    def _normalize_urls_in_text(self, text: str) -> str:
        """Normalize URLs in text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        def normalize_url(match):
            url = match.group(0)
            try:
                parsed = urlparse(url)
                # Normalize scheme and netloc
                scheme = parsed.scheme.lower()
                netloc = parsed.netloc.lower()
                # Reconstruct URL
                normalized = f"{scheme}://{netloc}"
                if parsed.path:
                    normalized += parsed.path
                if parsed.query:
                    normalized += f"?{parsed.query}"
                if parsed.fragment:
                    normalized += f"#{parsed.fragment}"
                return normalized
            except:
                return url
        
        return re.sub(url_pattern, normalize_url, text)
    
    def _normalize_emails_in_text(self, text: str) -> str:
        """Normalize email addresses in text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        def normalize_email(match):
            email = match.group(0)
            return email.lower()
        
        return re.sub(email_pattern, normalize_email, text)
    
    def _normalize_phones_in_text(self, text: str) -> str:
        """Normalize phone numbers in text."""
        # Remove common phone number formatting
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        
        def normalize_phone(match):
            country_code = match.group(1) or ""
            area_code = match.group(2)
            prefix = match.group(3)
            line_number = match.group(4)
            
            # Normalize to standard format
            if country_code:
                return f"+1-{area_code}-{prefix}-{line_number}"
            else:
                return f"{area_code}-{prefix}-{line_number}"
        
        return re.sub(phone_pattern, normalize_phone, text)
    
    async def _apply_field_rules(self, field_name: str, value: Any, rules: Dict[str, Any]) -> Any:
        """Apply field-specific normalization rules."""
        normalized_value = value
        
        # Apply type conversion
        if 'type' in rules:
            target_type = rules['type']
            try:
                if target_type == 'int':
                    normalized_value = int(float(str(normalized_value))) if normalized_value else 0
                elif target_type == 'float':
                    normalized_value = float(normalized_value) if normalized_value else 0.0
                elif target_type == 'str':
                    normalized_value = str(normalized_value)
                elif target_type == 'bool':
                    normalized_value = bool(normalized_value)
            except (ValueError, TypeError):
                self._log_operation("_apply_field_rules", f"Type conversion failed for {field_name}", "warning")
        
        # Apply string-specific rules
        if isinstance(normalized_value, str):
            # Apply regex transformations
            if 'regex_transformations' in rules:
                for pattern, replacement in rules['regex_transformations'].items():
                    normalized_value = re.sub(pattern, replacement, normalized_value)
            
            # Apply validation and default values
            if 'default' in rules and not normalized_value.strip():
                normalized_value = rules['default']
            
            # Apply length limits
            if 'max_length' in rules:
                normalized_value = normalized_value[:rules['max_length']]
            
            if 'min_length' in rules and len(normalized_value) < rules['min_length']:
                # Pad or handle minimum length requirement
                pass
        
        # Apply value constraints
        if 'allowed_values' in rules:
            if normalized_value not in rules['allowed_values']:
                default_value = rules.get('default', rules['allowed_values'][0])
                normalized_value = default_value
        
        # Apply range constraints for numbers
        if isinstance(normalized_value, (int, float)):
            if 'min_value' in rules and normalized_value < rules['min_value']:
                normalized_value = rules['min_value']
            if 'max_value' in rules and normalized_value > rules['max_value']:
                normalized_value = rules['max_value']
        
        return normalized_value
    
    def _get_applied_rules(self) -> List[str]:
        """Get list of applied normalization rules."""
        rules = []
        
        if self._enable_html_decode:
            rules.append("html_decode")
        if self._enable_whitespace_normalization:
            rules.append("whitespace_normalization")
        if self._enable_case_normalization:
            rules.append(f"case_normalization_{self._case_target}")
        if self._enable_url_normalization:
            rules.append("url_normalization")
        if self._enable_date_normalization:
            rules.append("date_normalization")
        if self._enable_number_normalization:
            rules.append("number_normalization")
        if self._enable_email_normalization:
            rules.append("email_normalization")
        if self._enable_phone_normalization:
            rules.append("phone_normalization")
        
        rules.extend(self._custom_normalizers.keys())
        
        return rules
    
    def configure_normalization(
        self,
        enable_html_decode: Optional[bool] = None,
        enable_whitespace_normalization: Optional[bool] = None,
        enable_case_normalization: Optional[bool] = None,
        case_target: Optional[str] = None,
        enable_url_normalization: Optional[bool] = None,
        enable_date_normalization: Optional[bool] = None,
        enable_number_normalization: Optional[bool] = None,
        enable_email_normalization: Optional[bool] = None,
        enable_phone_normalization: Optional[bool] = None
    ) -> None:
        """
        Configure normalization settings.
        
        Args:
            enable_html_decode: Enable HTML entity decoding
            enable_whitespace_normalization: Enable whitespace normalization
            enable_case_normalization: Enable case normalization
            case_target: Target case (lower, upper, title)
            enable_url_normalization: Enable URL normalization
            enable_date_normalization: Enable date normalization
            enable_number_normalization: Enable number normalization
            enable_email_normalization: Enable email normalization
            enable_phone_normalization: Enable phone normalization
        """
        if enable_html_decode is not None:
            self._enable_html_decode = enable_html_decode
        if enable_whitespace_normalization is not None:
            self._enable_whitespace_normalization = enable_whitespace_normalization
        if enable_case_normalization is not None:
            self._enable_case_normalization = enable_case_normalization
        if case_target is not None:
            self._case_target = case_target
        if enable_url_normalization is not None:
            self._enable_url_normalization = enable_url_normalization
        if enable_date_normalization is not None:
            self._enable_date_normalization = enable_date_normalization
        if enable_number_normalization is not None:
            self._enable_number_normalization = enable_number_normalization
        if enable_email_normalization is not None:
            self._enable_email_normalization = enable_email_normalization
        if enable_phone_normalization is not None:
            self._enable_phone_normalization = enable_phone_normalization
    
    def add_field_rule(self, field_name: str, rules: Dict[str, Any]) -> None:
        """
        Add normalization rules for a specific field.
        
        Args:
            field_name: Name of the field
            rules: Normalization rules for the field
        """
        self._field_rules[field_name] = rules
    
    def add_custom_normalizer(self, name: str, normalizer: Callable) -> None:
        """
        Add a custom normalizer function.
        
        Args:
            name: Name of the normalizer
            normalizer: Normalizer function
        """
        self._custom_normalizers[name] = normalizer
    
    def remove_field_rule(self, field_name: str) -> None:
        """Remove normalization rules for a field."""
        if field_name in self._field_rules:
            del self._field_rules[field_name]
    
    def remove_custom_normalizer(self, name: str) -> None:
        """Remove a custom normalizer."""
        if name in self._custom_normalizers:
            del self._custom_normalizers[name]
    
    def get_normalization_configuration(self) -> Dict[str, Any]:
        """Get current normalization configuration."""
        return {
            'enable_html_decode': self._enable_html_decode,
            'enable_whitespace_normalization': self._enable_whitespace_normalization,
            'enable_case_normalization': self._enable_case_normalization,
            'case_target': self._case_target,
            'enable_url_normalization': self._enable_url_normalization,
            'enable_date_normalization': self._enable_date_normalization,
            'enable_number_normalization': self._enable_number_normalization,
            'enable_email_normalization': self._enable_email_normalization,
            'enable_phone_normalization': self._enable_phone_normalization,
            'field_rules': self._field_rules,
            'custom_normalizers': list(self._custom_normalizers.keys()),
            **self.get_configuration()
        }
