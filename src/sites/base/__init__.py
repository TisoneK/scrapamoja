"""
Base contracts and utilities for site scrapers.

Provides abstract base classes and validation utilities that all
site scrapers must implement and follow.
"""

from .site_scraper import BaseSiteScraper
from .flow import BaseFlow
from .validation import ValidationResult, FileValidator, ConfigurationValidator, InterfaceValidator
from .error_formatter import ErrorFormatter, ValidationReport
from .contract_validator import ContractValidator, validate_and_create_scraper, monitor_compliance

__all__ = [
    "BaseSiteScraper", 
    "BaseFlow", 
    "ValidationResult",
    "FileValidator",
    "ConfigurationValidator", 
    "InterfaceValidator",
    "ErrorFormatter",
    "ValidationReport",
    "ContractValidator",
    "validate_and_create_scraper",
    "monitor_compliance"
]
