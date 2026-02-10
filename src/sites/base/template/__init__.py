"""
Site Template Integration Framework

This module provides a standardized template framework for creating site scrapers
that leverage existing Scorewise framework components.

The template framework enables rapid development of site scrapers by providing:
- Standardized directory structure and base classes
- Integration bridge pattern for framework component connections
- YAML selector loading and management
- Site registry for template discovery and management
- Validation framework for quality assurance
"""

from .site_template import ISiteTemplate
from .integration_bridge import IIntegrationBridge
from .selector_loader import ISelectorLoader
from .site_registry import ITemplateRegistry, ITemplateDiscovery, ITemplateLoader
from .validation import IValidationFramework

__version__ = "1.0.0"
__all__ = [
    "ISiteTemplate",
    "IIntegrationBridge", 
    "ISelectorLoader",
    "ITemplateRegistry",
    "ITemplateDiscovery",
    "ITemplateLoader",
    "IValidationFramework",
]
