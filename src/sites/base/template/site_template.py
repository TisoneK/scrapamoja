"""
Base template classes for the Site Template Integration Framework.

This module provides concrete implementations of the core template interfaces,
serving as foundation classes that site-specific templates can extend.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .interfaces import ISiteTemplate, TemplateInfo
from ..site_scraper import BaseSiteScraper


logger = logging.getLogger(__name__)


class BaseSiteTemplate(ISiteTemplate):
    """
    Base implementation of ISiteTemplate that provides common functionality
    for all site scraper templates.
    """
    
    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        framework_version: str,
        site_domain: str,
        supported_domains: Optional[List[str]] = None,
        configuration_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base template.
        
        Args:
            name: Unique template identifier
            version: Template version following semantic versioning
            description: Human-readable description
            author: Template author/organization
            framework_version: Required framework version compatibility
            site_domain: Primary domain the template targets
            supported_domains: Additional domains supported by template
            configuration_schema: JSON schema for template-specific configuration
        """
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.framework_version = framework_version
        self.site_domain = site_domain
        self.supported_domains = supported_domains or []
        self.configuration_schema = configuration_schema or {}
        
        # Runtime state
        self.page = None
        self.selector_engine = None
        self.initialized = False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Template capabilities and dependencies
        self.capabilities = [
            "repository_search",
            "repository_details", 
            "user_profile",
            "issue_tracking",
            "pull_request_tracking",
            "screenshot_capture",
            "html_capture",
            "resource_monitoring"
        ]
        self.dependencies: List[str] = []
        
        # Integration components
        self.integration_bridge = None
        self.extraction_rules = None
        self.browser_lifecycle = None
        
        logger.info(f"BaseSiteTemplate initialized: {name} v{version}")
    
    async def initialize(self, page: Any, selector_engine: Any) -> bool:
        """
        Initialize the template with framework components.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
            
        Returns:
            bool: True if initialization successful
        """
        try:
            self.page = page
            self.selector_engine = selector_engine
            
            # Validate framework compatibility
            if not await self._validate_framework_compatibility():
                logger.error(f"Framework compatibility check failed for {self.name}")
                return False
            
            # Initialize integration components
            if not await self._initialize_integration_components():
                logger.error(f"Integration components initialization failed for {self.name}")
                return False
            
            # Setup template-specific initialization
            if not await self._setup_template_specific():
                logger.error(f"Template-specific setup failed for {self.name}")
                return False
            
            self.initialized = True
            self.updated_at = datetime.now()
            
            logger.info(f"Template {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize template {self.name}: {e}")
            return False
    
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """
        Execute scraping using template configuration.
        
        Args:
            **kwargs: Scraping parameters
            
        Returns:
            Dict[str, Any]: Scraped data
        """
        if not self.initialized:
            raise RuntimeError(f"Template {self.name} not initialized. Call initialize() first.")
        
        try:
            logger.info(f"Starting scrape for template {self.name} with params: {kwargs}")
            
            # Pre-scrape validation
            if not await self._validate_scrape_params(**kwargs):
                raise ValueError("Invalid scrape parameters")
            
            # Execute template-specific scraping logic
            results = await self._execute_scrape_logic(**kwargs)
            
            # Post-scrape processing
            processed_results = await self._process_scrape_results(results)
            
            logger.info(f"Scrape completed for template {self.name}")
            return processed_results
            
        except Exception as e:
            logger.error(f"Scrape failed for template {self.name}: {e}")
            raise
    
    async def capture_screenshot(
        self,
        filename: Optional[str] = None,
        full_page: bool = True,
        quality: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Capture a screenshot of the current page.
        
        Args:
            filename: Optional filename for the screenshot
            full_page: Whether to capture the full page
            quality: Image quality (for JPEG)
            format_type: Image format (png, jpeg)
            
        Returns:
            Optional[str]: Path to the captured screenshot
        """
        if not self.browser_lifecycle:
            logger.error("Browser lifecycle integration not available")
            return None
        
        return await self.browser_lifecycle.capture_screenshot(
            filename=filename,
            full_page=full_page,
            quality=quality,
            format_type=format_type
        )
    
    async def capture_html(
        self,
        filename: Optional[str] = None,
        clean: Optional[bool] = None,
        element: Optional[Any] = None
    ) -> Optional[str]:
        """
        Capture HTML content of the current page or element.
        
        Args:
            filename: Optional filename for the HTML file
            clean: Whether to clean the HTML
            element: Optional element to capture HTML from
            
        Returns:
            Optional[str]: Path to the captured HTML file
        """
        if not self.browser_lifecycle:
            logger.error("Browser lifecycle integration not available")
            return None
        
        return await self.browser_lifecycle.capture_html(
            filename=filename,
            clean=clean,
            element=element
        )
    
    def get_browser_session_info(self) -> Dict[str, Any]:
        """
        Get browser session information.
        
        Returns:
            Dict[str, Any]: Browser session information
        """
        if not self.browser_lifecycle:
            return {"error": "Browser lifecycle integration not available"}
        
        return self.browser_lifecycle.get_browser_session_info()
    
    def get_lifecycle_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get browser lifecycle events.
        
        Args:
            event_type: Optional event type filter
            limit: Maximum number of events to return
            
        Returns:
            List[Dict[str, Any]]: Lifecycle events
        """
        if not self.browser_lifecycle:
            return []
        
        return self.browser_lifecycle.get_lifecycle_events(event_type=event_type, limit=limit)
    
    def get_feature_status(self) -> Dict[str, bool]:
        """
        Get status of available browser features.
        
        Returns:
            Dict[str, bool]: Feature availability status
        """
        if not self.browser_lifecycle:
            return {"error": "Browser lifecycle integration not available"}
        
        return self.browser_lifecycle.get_feature_status()
    
    def update_browser_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update browser lifecycle configuration.
        
        Args:
            new_config: New configuration values
        """
        if self.browser_lifecycle:
            self.browser_lifecycle.update_config(new_config)
        else:
            logger.warning("Browser lifecycle integration not available")
    
    def get_browser_config(self) -> Dict[str, Any]:
        """
        Get current browser lifecycle configuration.
        
        Returns:
            Dict[str, Any]: Current configuration
        """
        if not self.browser_lifecycle:
            return {"error": "Browser lifecycle integration not available"}
        
        return self.browser_lifecycle.get_config()
    
    def get_template_info(self) -> Dict[str, Any]:
        """
        Get template metadata and capabilities.
        
        Returns:
            Dict[str, Any]: Template information
        """
        info = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "configuration_schema": self.configuration_schema,
            "initialized": self.initialized,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        
        # Add browser lifecycle information if available
        if self.browser_lifecycle:
            info["browser_features"] = self.browser_lifecycle.get_feature_status()
            info["browser_session"] = self.browser_lifecycle.get_browser_session_info()
        
        return info
    
    def _validate_framework_compatibility(self) -> bool:
        """
        Validate framework version compatibility.
        
        Returns:
            bool: True if compatible
        """
        # This would typically check against actual framework version
        # For now, assume compatibility
        return True
    
    async def _setup_integration_components(self) -> bool:
        """
        Setup integration components for the template.
        
        Returns:
            bool: True if setup successful
        """
        try:
            # Initialize integration bridge
            self.integration_bridge = FullIntegrationBridge(
                template_name=self.name,
                page=self.page,
                selector_engine=self.selector_engine
            )
            
            # Initialize browser lifecycle integration
            from .browser_lifecycle import BrowserLifecycleIntegration
            self.browser_lifecycle = BrowserLifecycleIntegration(self.integration_bridge)
            
            # Initialize browser lifecycle
            if not await self.browser_lifecycle.initialize_browser_integration():
                logger.warning("Browser lifecycle integration failed")
            
            # Initialize integration bridge
            if not await self.integration_bridge.initialize():
                logger.error("Integration bridge initialization failed")
                return False
            
            logger.info("Integration components setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup integration components: {e}")
            return False
    
    async def _setup_template_specific(self) -> bool:
        """
        Setup template-specific configuration and validation.
        
        Returns:
            bool: True if successful
        """
        # Override in subclasses for template-specific setup
        return True
    
    async def _validate_scrape_params(self, **kwargs) -> bool:
        """
        Validate scraping parameters.
        
        Args:
            **kwargs: Scrape parameters
            
        Returns:
            bool: True if valid
        """
        # Override in subclasses for parameter validation
        return True
    
    async def _execute_scrape_logic(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the core scraping logic.
        
        Args:
            **kwargs: Scrape parameters
            
        Returns:
            Dict[str, Any]: Raw scrape results
        """
        # Override in subclasses with specific scraping logic
        raise NotImplementedError("Subclasses must implement _execute_scrape_logic")
    
    async def _process_scrape_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and format scrape results.
        
        Args:
            results: Raw scrape results
            
        Returns:
            Dict[str, Any]: Processed results
        """
        # Add metadata to results
        processed = {
            "template_name": self.name,
            "template_version": self.version,
            "scraped_at": datetime.now().isoformat(),
            "data": results
        }
        
        return processed


class ConfigurableSiteTemplate(BaseSiteTemplate):
    """
    Enhanced base template that supports configuration-based customization.
    """
    
    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        framework_version: str,
        site_domain: str,
        configuration: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize configurable template.
        
        Args:
            configuration: Template configuration dictionary
            **kwargs: Additional arguments passed to BaseSiteTemplate
        """
        super().__init__(name, version, description, author, framework_version, site_domain, **kwargs)
        
        self.configuration = configuration or {}
        self._apply_configuration()
    
    def _apply_configuration(self) -> None:
        """Apply configuration to template properties."""
        # Apply supported domains from configuration
        if "supported_domains" in self.configuration:
            self.supported_domains = self.configuration["supported_domains"]
        
        # Apply capabilities from configuration
        if "capabilities" in self.configuration:
            self.capabilities = self.configuration["capabilities"]
        
        # Apply dependencies from configuration
        if "dependencies" in self.configuration:
            self.dependencies = self.configuration["dependencies"]
    
    def get_configuration_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Any: Configuration value
        """
        return self.configuration.get(key, default)
    
    def update_configuration(self, new_config: Dict[str, Any]) -> None:
        """
        Update template configuration.
        
        Args:
            new_config: New configuration values
        """
        self.configuration.update(new_config)
        self._apply_configuration()
        self.updated_at = datetime.now()


class TemplateFactory:
    """
    Factory class for creating template instances.
    """
    
    @staticmethod
    def create_template(
        template_class: type,
        name: str,
        version: str,
        description: str,
        author: str,
        framework_version: str,
        site_domain: str,
        **kwargs
    ) -> ISiteTemplate:
        """
        Create a template instance.
        
        Args:
            template_class: Template class to instantiate
            name: Template name
            version: Template version
            description: Template description
            author: Template author
            framework_version: Framework version
            site_domain: Target site domain
            **kwargs: Additional arguments
            
        Returns:
            ISiteTemplate: Template instance
        """
        return template_class(
            name=name,
            version=version,
            description=description,
            author=author,
            framework_version=framework_version,
            site_domain=site_domain,
            **kwargs
        )
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> ISiteTemplate:
        """
        Create a template from configuration dictionary.
        
        Args:
            config: Template configuration
            
        Returns:
            ISiteTemplate: Template instance
        """
        template_class = ConfigurableSiteTemplate
        
        return TemplateFactory.create_template(
            template_class=template_class,
            **config
        )
