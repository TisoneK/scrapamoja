"""
Base interfaces for the Site Template Integration Framework.

This module defines the core interfaces that all template components must implement,
ensuring consistency and enabling polymorphic usage across different site templates.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path


class ISiteTemplate(ABC):
    """Base interface for site scraper templates."""
    
    @abstractmethod
    async def initialize(self, page: Any, selector_engine: Any) -> bool:
        """
        Initialize the template with framework components.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        Execute scraping using template configuration.
        
        Args:
            **kwargs: Scraping parameters
            
        Returns:
            Dict[str, Any]: Scraped data
        """
        pass
    
    @abstractmethod
    def get_template_info(self) -> Dict[str, Any]:
        """
        Get template metadata and capabilities.
        
        Returns:
            Dict[str, Any]: Template information
        """
        pass


class IIntegrationBridge(ABC):
    """Interface for connecting site components with framework infrastructure."""
    
    @abstractmethod
    async def initialize_complete_integration(self) -> bool:
        """
        Initialize complete framework integration.
        
        Returns:
            bool: True if integration successful
        """
        pass
    
    @abstractmethod
    async def load_selectors(self) -> bool:
        """
        Load YAML selectors into existing selector engine.
        
        Returns:
            bool: True if selectors loaded successfully
        """
        pass
    
    @abstractmethod
    async def setup_extraction_rules(self) -> bool:
        """
        Setup extraction rules using existing extractor module.
        
        Returns:
            bool: True if rules setup successful
        """
        pass
    
    @abstractmethod
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get current integration status and health.
        
        Returns:
            Dict[str, Any]: Integration status information
        """
        pass


class ISelectorLoader(ABC):
    """Interface for loading YAML selectors into existing selector engine."""
    
    @abstractmethod
    async def load_site_selectors(self, site_name: str) -> bool:
        """
        Load selectors for a specific site.
        
        Args:
            site_name: Name of the site to load selectors for
            
        Returns:
            bool: True if selectors loaded successfully
        """
        pass
    
    @abstractmethod
    async def register_selector(self, selector_name: str, selector_config: Dict[str, Any]) -> bool:
        """
        Register a single selector with the selector engine.
        
        Args:
            selector_name: Name of the selector
            selector_config: Selector configuration from YAML
            
        Returns:
            bool: True if registration successful
        """
        pass
    
    @abstractmethod
    def get_loaded_selectors(self) -> List[str]:
        """
        Get list of loaded selector names.
        
        Returns:
            List[str]: List of selector names
        """
        pass
    
    @abstractmethod
    async def validate_selector_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate selector configuration.
        
        Args:
            config: Selector configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        pass


class ITemplateRegistry(ABC):
    """Combined interface for template registry operations."""
    pass


class IRegistryManager(ITemplateRegistry):
    """Primary interface for site template registry management."""
    
    @abstractmethod
    async def initialize_registry(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the registry with configuration.
        
        Args:
            config: Registry configuration
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def scan_and_register(self, scan_paths: List[str]) -> Dict[str, Any]:
        """
        Scan paths and automatically register discovered templates.
        
        Args:
            scan_paths: List of paths to scan for templates
            
        Returns:
            Dict[str, Any]: Scan results with registered templates
        """
        pass
    
    @abstractmethod
    async def get_registry_status(self) -> Dict[str, Any]:
        """
        Get current registry status and health.
        
        Returns:
            Dict[str, Any]: Registry status information
        """
        pass
    
    @abstractmethod
    async def refresh_registry(self) -> Dict[str, Any]:
        """
        Refresh registry by rescanning all discovery paths.
        
        Returns:
            Dict[str, Any]: Refresh results
        """
        pass


class ITemplateDiscovery(ITemplateRegistry):
    """Interface for discovering templates in filesystem and other sources."""
    
    @abstractmethod
    async def discover_templates_in_path(self, path: str) -> List[Dict[str, Any]]:
        """
        Discover templates in a specific path.
        
        Args:
            path: Filesystem path to search
            
        Returns:
            List[Dict[str, Any]]: List of discovered template metadata
        """
        pass
    
    @abstractmethod
    async def validate_template_structure(self, template_path: str) -> bool:
        """
        Validate template directory structure.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            bool: True if structure is valid
        """
        pass
    
    @abstractmethod
    async def extract_template_metadata(self, template_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from template directory.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if invalid
        """
        pass
    
    @abstractmethod
    async def watch_for_changes(self, paths: List[str]) -> None:
        """
        Watch paths for template changes and updates.
        
        Args:
            paths: List of paths to watch
        """
        pass


class ITemplateStorage(ITemplateRegistry):
    """Interface for template storage and retrieval."""
    
    @abstractmethod
    async def register_template(self, template_metadata: Dict[str, Any]) -> bool:
        """
        Register a template in the registry.
        
        Args:
            template_metadata: Template metadata to register
            
        Returns:
            bool: True if registration successful
        """
        pass
    
    @abstractmethod
    async def unregister_template(self, template_name: str) -> bool:
        """
        Unregister a template from the registry.
        
        Args:
            template_name: Name of template to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        pass
    
    @abstractmethod
    async def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get template metadata by name.
        
        Args:
            template_name: Name of template
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if not found
        """
        pass
    
    @abstractmethod
    async def list_templates(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List all registered templates with optional filters.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[Dict[str, Any]]: List of template metadata
        """
        pass


class ITemplateLoader(ITemplateRegistry):
    """Interface for loading and instantiating templates."""
    
    @abstractmethod
    async def load_template(self, template_name: str, page: Any, selector_engine: Any) -> Optional[Any]:
        """
        Load and instantiate a template.
        
        Args:
            template_name: Name of template to load
            page: Playwright page instance
            selector_engine: Selector engine instance
            
        Returns:
            Optional[Any]: Loaded template instance or None if failed
        """
        pass
    
    @abstractmethod
    async def validate_template_dependencies(self, template_name: str) -> Dict[str, Any]:
        """
        Validate template dependencies.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Dict[str, Any]: Dependency validation results
        """
        pass
    
    @abstractmethod
    async def get_template_instance_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about template instance requirements.
        
        Args:
            template_name: Name of template
            
        Returns:
            Optional[Dict[str, Any]]: Template instance information
        """
        pass


class IValidationFramework(ABC):
    """Interface for validating templates and framework compliance."""
    
    @abstractmethod
    async def validate_template(self, template_path: str) -> Dict[str, Any]:
        """
        Validate a complete template.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Validation results
        """
        pass
    
    @abstractmethod
    async def validate_selectors(self, selector_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate YAML selector configurations.
        
        Args:
            selector_configs: List of selector configurations
            
        Returns:
            Dict[str, Any]: Validation results
        """
        pass
    
    @abstractmethod
    async def validate_extraction_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate extraction rule configurations.
        
        Args:
            rules: List of extraction rules
            
        Returns:
            Dict[str, Any]: Validation results
        """
        pass
    
    @abstractmethod
    async def check_framework_compliance(self, template_path: str) -> Dict[str, Any]:
        """
        Check template compliance with framework constitution.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Compliance check results
        """
        pass


# Data Transfer Objects
class TemplateInfo:
    """Template metadata and capabilities."""
    
    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        created_at: datetime,
        updated_at: datetime,
        framework_version: str,
        site_domain: str,
        supported_domains: List[str],
        configuration_schema: Dict[str, Any],
        capabilities: List[str],
        dependencies: List[str]
    ):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.created_at = created_at
        self.updated_at = updated_at
        self.framework_version = framework_version
        self.site_domain = site_domain
        self.supported_domains = supported_domains
        self.configuration_schema = configuration_schema
        self.capabilities = capabilities
        self.dependencies = dependencies


class ValidationResult:
    """Validation result for templates and components."""
    
    def __init__(
        self,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        compliance_score: float,
        validation_details: Dict[str, Any]
    ):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.compliance_score = compliance_score
        self.validation_details = validation_details


class IntegrationStatus:
    """Status of framework integration."""
    
    def __init__(
        self,
        is_integrated: bool,
        selector_count: int,
        extraction_rule_count: int,
        bridge_status: str,
        last_updated: datetime,
        health_metrics: Dict[str, Any],
        error_details: Optional[Dict[str, Any]] = None
    ):
        self.is_integrated = is_integrated
        self.selector_count = selector_count
        self.extraction_rule_count = extraction_rule_count
        self.bridge_status = bridge_status
        self.last_updated = last_updated
        self.health_metrics = health_metrics
        self.error_details = error_details
