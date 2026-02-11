"""
Template scraper with modular architecture.

Copy and modify this file to create your site scraper.
This template demonstrates the new modular component system with flows,
processors, validators, and dependency injection.
"""

from typing import Dict, Any, Optional
from src.sites.base.site_scraper import ModularSiteScraper
from src.sites.base.configuration_manager import Environment
from src.sites.base.component_manager import ComponentManager
from src.sites.base.configuration_manager import ConfigurationManager
from src.sites.base.di_container import DIContainer
from src.sites.base.base_flow import BaseFlow
from src.sites.base.base_processor import BaseProcessor
from src.sites.base.base_validator import BaseValidator

# Import modular components (will be created in subsequent tasks)
# from .flows.search_flow import SearchFlow
# from .flows.login_flow import LoginFlow
# from .processors.data_processor import DataProcessor
# from .validators.data_validator import DataValidator


class TemplateScraper(ModularSiteScraper):
    """Template scraper with modular component support."""
    
    # Site configuration (can be moved to config files)
    site_id = "template"
    site_name = "Template Site"
    base_url = "https://example.com"
    
    def __init__(
        self,
        page,
        selector_engine,
        component_manager: Optional[ComponentManager] = None,
        config_manager: Optional[ConfigurationManager] = None,
        di_container: Optional[DIContainer] = None,
        environment: Environment = Environment.DEV
    ):
        """
        Initialize enhanced template scraper.
        
        Args:
            page: Playwright page object
            selector_engine: Selector engine instance
            component_manager: Component manager for modular components
            config_manager: Configuration manager for multi-environment configs
            di_container: Dependency injection container
            environment: Target environment
        """
        # Initialize with modular support
        super().__init__(
            page=page,
            selector_engine=selector_engine,
            component_manager=component_manager,
            config_manager=config_manager,
            di_container=di_container,
            environment=environment
        )
    
    async def setup_components(self) -> None:
        """
        Setup modular components.
        This method should be called after initialization to register flows, processors, and validators.
        """
        try:
            # Register flows (will be implemented in subsequent tasks)
            # await self.register_flow(SearchFlow("search_flow", "Search Flow", "1.0.0", "Handles search navigation"))
            # await self.register_flow(LoginFlow("login_flow", "Login Flow", "1.0.0", "Handles user authentication"))
            
            # Register processors (will be implemented in subsequent tasks)
            # await self.register_processor(DataProcessor("data_processor", "Data Processor", "1.0.0", "Processes scraped data"))
            
            # Register validators (will be implemented in subsequent tasks)
            # await self.register_validator(DataValidator("data_validator", "Data Validator", "1.0.0", "Validates scraped data"))
            
            print("Modular components setup completed")
            
        except Exception as e:
            print(f"Failed to setup components: {str(e)}")
    
    async def navigate(self) -> None:
        """Navigate to initial state for scraping."""
        try:
            # Use configuration if available
            base_url = await self.get_config("base_url") or self.base_url
            
            # Navigate to base URL
            await self.page.goto(base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Execute navigation flow if available
            if 'navigation_flow' in self._flows:
                await self.execute_flow('navigation_flow')
            
            print(f"Navigation completed to {base_url}")
            
        except Exception as e:
            print(f"Navigation failed: {str(e)}")
            raise
    
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """Perform scraping using modular components."""
        try:
            # Get configuration
            config = await self.get_config()
            
            # Extract parameters
            query = kwargs.get('query', '')
            max_results = kwargs.get('max_results', config.get('max_results', 10))
            
            # Execute search flow if available and query provided
            if query and 'search_flow' in self._flows:
                search_result = await self.execute_flow('search_flow', query=query, max_results=max_results)
                if not search_result.success:
                    return {
                        'error': 'Search flow failed',
                        'details': search_result.errors
                    }
            
            # Extract data using selector engine
            results = await self.selector_engine.extract_all(self.page, "search_results")
            
            # Limit results if specified
            if max_results and results:
                results = results[:max_results]
            
            return {
                "query": query,
                "results": results,
                "total_count": len(results) if results else 0,
                "max_results": max_results,
                "scraped_at": await self._get_current_timestamp()
            }
            
        except Exception as e:
            print(f"Scraping failed: {str(e)}")
            return {
                'error': str(e),
                'query': kwargs.get('query', ''),
                'results': [],
                'total_count': 0
            }
    
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw scraped data into structured output."""
        try:
            from datetime import datetime
            
            # Get site configuration
            site_config = {
                'site_id': self.site_id,
                'site_name': self.site_name,
                'base_url': self.base_url
            }
            
            # Process results through processors if available
            processed_results = raw_data.get('results', [])
            if 'data_processor' in self._processors:
                process_result = self._processors['data_processor'].process(processed_results)
                if process_result.success:
                    processed_results = process_result.data.get('output_data', processed_results)
            
            # Validate data if validators are available
            validation_results = {}
            if 'data_validator' in self._validators:
                validation_result = self._validators['data_validator'].validate(processed_results)
                validation_results['data_validation'] = validation_result
            
            return {
                "site": site_config,
                "timestamp": datetime.utcnow().isoformat(),
                "query": raw_data.get("query", ""),
                "results": processed_results,
                "total_count": len(processed_results) if processed_results else 0,
                "max_results": raw_data.get("max_results", 0),
                "validation_results": validation_results,
                "environment": self.environment.value,
                "flow_state": self._flow_state.__dict__ if self._flow_state else None
            }
            
        except Exception as e:
            print(f"Normalization failed: {str(e)}")
            return {
                "site": {
                    'site_id': self.site_id,
                    'site_name': self.site_name,
                    'base_url': self.base_url
                },
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "query": raw_data.get("query", ""),
                "results": [],
                "total_count": 0
            }
    
    async def scrape_with_modular_components(self, **kwargs) -> Dict[str, Any]:
        """
        Execute modular scraping using registered components.
        This method demonstrates the full capability of the modular architecture.
        """
        try:
            # Setup components if not already done
            if not self._flows and not self._processors and not self._validators:
                await self.setup_components()
            
            # Use the enhanced scraping method from the base class
            return await super().scrape_with_components(**kwargs)
            
        except Exception as e:
            print(f"Modular scraping failed: {str(e)}")
            return {
                'error': str(e),
                'stats': self._execution_stats
            }
    
    async def _get_current_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get template information for debugging."""
        return {
            "template_version": "2.0.0",
            "architecture": "modular",
            "components": {
                "flows": list(self._flows.keys()),
                "processors": list(self._processors.keys()),
                "validators": list(self._validators.keys())
            },
            "environment": self.environment.value,
            "site_info": self.get_site_info(),
            "state": self.validate_state()
        }


# Legacy compatibility class for existing code
class TemplateScraperLegacy(TemplateScraper):
    """Legacy template scraper for backward compatibility."""
    
    def __init__(self, page, selector_engine):
        """Initialize legacy template scraper without modular components."""
        super().__init__(
            page=page,
            selector_engine=selector_engine,
            component_manager=None,
            config_manager=None,
            di_container=None,
            environment=Environment.DEV
        )


# Factory function for easy instantiation
def create_template_scraper(
    page,
    selector_engine,
    use_modular: bool = True,
    environment: Environment = Environment.DEV,
    **kwargs
) -> TemplateScraper:
    """
    Factory function to create template scraper.
    
    Args:
        page: Playwright page object
        selector_engine: Selector engine instance
        use_modular: Whether to use modular components
        environment: Target environment
        **kwargs: Additional arguments
        
    Returns:
        Template scraper instance
    """
    if use_modular:
        # Create modular components
        component_manager = ComponentManager()
        config_manager = ConfigurationManager()
        di_container = DIContainer()
        
        return TemplateScraper(
            page=page,
            selector_engine=selector_engine,
            component_manager=component_manager,
            config_manager=config_manager,
            di_container=di_container,
            environment=environment
        )
    else:
        # Use legacy version
        return TemplateScraperLegacy(page, selector_engine)


# Example usage
if __name__ == "__main__":
    """
    Example usage of the enhanced template scraper.
    
    This demonstrates how to use the new modular architecture.
    """
    # This would be used in your actual scraping code:
    # 
    # from playwright.async_api import async_playwright
    # 
    # async def main():
    #     async with async_playwright() as p:
    #         browser = await p.chromium.launch()
    #         page = await browser.new_page()
    #         
    #         # Create enhanced template scraper
    #         scraper = create_template_scraper(
    #             page=page,
    #             selector_engine=your_selector_engine,
    #             use_modular=True,
    #             environment=Environment.PROD
    #         )
    #         
    #         # Setup components
    #         await scraper.setup_components()
    #         
    #         # Navigate and scrape
    #         await scraper.navigate()
    #         results = await scraper.scrape_with_modular_components(query="example")
    #         
    #         print(results)
    #         
    #         await scraper.cleanup()
    #         await browser.close()
    # 
    # asyncio.run(main())
    pass
