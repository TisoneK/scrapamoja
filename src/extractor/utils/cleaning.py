"""
String cleaning utilities for the extractor module.

This module provides functions for cleaning, normalizing, and transforming
text data during the extraction process.
"""

import html
import re
import unicodedata
from typing import Any, List, Optional, Union


class StringCleaner:
    """Utility class for string cleaning and normalization."""
    
    @staticmethod
    def trim(text: str) -> str:
        """Remove leading and trailing whitespace."""
        return text.strip()
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """Normalize whitespace by replacing multiple spaces with single space."""
        # Replace multiple whitespace characters with single space
        text = re.sub(r'\s+', ' ', text)
        # Trim leading/trailing whitespace
        return text.strip()
    
    @staticmethod
    def remove_all_whitespace(text: str) -> str:
        """Remove all whitespace characters."""
        return re.sub(r'\s+', '', text)
    
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize Unicode text and remove diacritics."""
        # Normalize to NFKD form
        normalized = unicodedata.normalize('NFKD', text)
        # Remove diacritics
        return ''.join(
            char for char in normalized
            if not unicodedata.combining(char)
        )
    
    @staticmethod
    def lowercase(text: str) -> str:
        """Convert text to lowercase."""
        return text.lower()
    
    @staticmethod
    def uppercase(text: str) -> str:
        """Convert text to uppercase."""
        return text.upper()
    
    @staticmethod
    def title_case(text: str) -> str:
        """Convert text to title case."""
        return text.title()
    
    @staticmethod
    def unescape_html(text: str) -> str:
        """Unescape HTML entities."""
        return html.unescape(text)
    
    @staticmethod
    def remove_html_tags(text: str) -> str:
        """Remove HTML tags from text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up any remaining HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        return text
    
    @staticmethod
    def clean_html_text(text: str) -> str:
        """Clean text extracted from HTML content."""
        # Unescape HTML entities
        text = StringCleaner.unescape_html(text)
        # Remove HTML tags
        text = StringCleaner.remove_html_tags(text)
        # Clean whitespace
        text = StringCleaner.clean_whitespace(text)
        return text
    
    @staticmethod
    def remove_special_chars(text: str, keep_spaces: bool = True) -> str:
        """Remove special characters, keeping only alphanumeric and optionally spaces."""
        if keep_spaces:
            return re.sub(r'[^a-zA-Z0-9\s]', '', text)
        else:
            return re.sub(r'[^a-zA-Z0-9]', '', text)
    
    @staticmethod
    def keep_only_chars(text: str, chars: str) -> str:
        """Keep only specified characters in text."""
        pattern = f'[^{re.escape(chars)}]'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def extract_digits(text: str) -> str:
        """Extract only digits from text."""
        return re.sub(r'\D', '', text)
    
    @staticmethod
    def extract_letters(text: str) -> str:
        """Extract only letters from text."""
        return re.sub(r'[^a-zA-Z]', '', text)
    
    @staticmethod
    def extract_alphanumeric(text: str) -> str:
        """Extract only alphanumeric characters from text."""
        return re.sub(r'[^a-zA-Z0-9]', '', text)
    
    @staticmethod
    def remove_numbers(text: str) -> str:
        """Remove all numbers from text."""
        return re.sub(r'\d+', '', text)
    
    @staticmethod
    def remove_punctuation(text: str) -> str:
        """Remove punctuation from text."""
        return re.sub(r'[^\w\s]', '', text)
    
    @staticmethod
    def clean_currency(text: str) -> str:
        """Clean currency symbols and formatting."""
        # Remove currency symbols
        text = re.sub(r'[$€£¥₹₽₩]', '', text)
        # Remove commas in numbers
        text = re.sub(r',(?=\d)', '', text)
        # Clean whitespace
        return StringCleaner.clean_whitespace(text)
    
    @staticmethod
    def clean_phone_number(text: str) -> str:
        """Clean phone number by keeping only digits and common separators."""
        # Keep digits, plus, minus, parentheses, and spaces
        return re.sub(r'[^\d\+\-\(\)\s]', '', text)
    
    @staticmethod
    def clean_email(text: str) -> str:
        """Clean email address by removing surrounding whitespace and converting to lowercase."""
        return StringCleaner.lowercase(StringCleaner.trim(text))
    
    @staticmethod
    def clean_url(text: str) -> str:
        """Clean URL by removing surrounding whitespace."""
        return StringCleaner.trim(text)
    
    @staticmethod
    def remove_extra_spaces(text: str) -> str:
        """Remove extra spaces between words."""
        # Replace multiple spaces with single space
        return re.sub(r' {2,}', ' ', text)
    
    @staticmethod
    def fix_encoding_issues(text: str) -> str:
        """Fix common encoding issues."""
        # Fix common encoding problems
        fixes = [
            (r'â€™', "'"),  # Apostrophe
            (r'â€œ', '"'),  # Opening quote
            (r'â€', '"'),   # Closing quote
            (r'â€¦', '...'), # Ellipsis
            (r'â€"', '-'),   # Dash
            (r'Â', ''),     # Non-breaking space
        ]
        
        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def standardize_line_breaks(text: str) -> str:
        """Standardize line breaks to Unix format."""
        # Convert Windows line breaks to Unix
        text = re.sub(r'\r\n', '\n', text)
        # Convert old Mac line breaks to Unix
        text = re.sub(r'\r', '\n', text)
        return text
    
    @staticmethod
    def remove_empty_lines(text: str) -> str:
        """Remove empty lines from text."""
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        return '\n'.join(non_empty_lines)
    
    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        """Truncate text to maximum length with suffix."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def pad_left(text: str, width: int, fill_char: str = ' ') -> str:
        """Pad text on the left to specified width."""
        return text.ljust(width, fill_char)
    
    @staticmethod
    def pad_right(text: str, width: int, fill_char: str = ' ') -> str:
        """Pad text on the right to specified width."""
        return text.rjust(width, fill_char)
    
    @staticmethod
    def clean_list_items(items: List[str]) -> List[str]:
        """Clean a list of string items."""
        return [StringCleaner.clean_whitespace(str(item).strip()) for item in items if item]
    
    @staticmethod
    def split_and_clean(text: str, delimiter: str = ',') -> List[str]:
        """Split text by delimiter and clean each part."""
        items = text.split(delimiter)
        return StringCleaner.clean_list_items(items)
    
    @staticmethod
    def join_and_clean(items: List[Any], delimiter: str = ', ') -> str:
        """Join items into string and clean the result."""
        string_items = [str(item) for item in items if item is not None]
        return delimiter.join(string_items)


# Common cleaning transformations
class CleaningTransformations:
    """Predefined cleaning transformations."""
    
    @staticmethod
    def basic_text_cleaning(text: str) -> str:
        """Apply basic text cleaning transformations."""
        text = StringCleaner.trim(text)
        text = StringCleaner.clean_whitespace(text)
        text = StringCleaner.fix_encoding_issues(text)
        return text
    
    @staticmethod
    def html_text_cleaning(text: str) -> str:
        """Apply HTML-specific text cleaning."""
        text = StringCleaner.clean_html_text(text)
        text = StringCleaner.basic_text_cleaning(text)
        return text
    
    @staticmethod
    def numeric_cleaning(text: str) -> str:
        """Apply numeric-specific cleaning."""
        text = StringCleaner.clean_currency(text)
        text = StringCleaner.trim(text)
        return text
    
    @staticmethod
    def email_cleaning(text: str) -> str:
        """Apply email-specific cleaning."""
        text = StringCleaner.clean_email(text)
        return text
    
    @staticmethod
    def phone_cleaning(text: str) -> str:
        """Apply phone number-specific cleaning."""
        text = StringCleaner.clean_phone_number(text)
        text = StringCleaner.trim(text)
        return text
    
    @staticmethod
    def url_cleaning(text: str) -> str:
        """Apply URL-specific cleaning."""
        text = StringCleaner.clean_url(text)
        return text
