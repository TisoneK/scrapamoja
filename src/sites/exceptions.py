"""
Exception hierarchy for site scraper framework.

Provides specific exception types for different error scenarios
in scraper operations, validation, registry management, and contract violations.
"""


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class NavigationError(ScraperError):
    """Navigation-related errors."""
    pass


class ScrapingError(ScraperError):
    """Data extraction errors."""
    pass


class NormalizationError(ScraperError):
    """Data transformation errors."""
    pass


class ValidationError(ScraperError):
    """Validation errors."""
    pass


class RegistryError(ScraperError):
    """Registry-related errors."""
    pass


class ConfigurationError(ScraperError):
    """Configuration-related errors."""
    pass


class ContractViolationError(ScraperError):
    """Contract compliance errors."""
    pass


class MethodSignatureError(ValidationError):
    """Method signature validation errors."""
    pass


class ClassAttributeError(ValidationError):
    """Class attribute validation errors."""
    pass


class InstantiationError(ContractViolationError):
    """Scraper instantiation errors."""
    pass
