"""
Integration utilities for YAML selector loading.

This module provides utilities to integrate YAML selector loading
with the existing selector engine infrastructure.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .engine import SelectorEngine
from .engine.configuration.loader import ConfigurationLoader
from .engine.configuration.discovery import ConfigurationDiscovery
from .models.selector_config import SemanticSelector
from ..sites.wikipedia.selector_loader import WikipediaSelectorLoader

logger = logging.getLogger(__name__)


class YAMLSelectorIntegrator:
    """Integrates YAML selector loading with the selector engine."""
    
    def __init__(self, selector_engine: SelectorEngine):
        """Initialize the integrator."""
        self.selector_engine = selector_engine
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._wikipedia_loader: Optional[WikipediaSelectorLoader] = None
    
    async def initialize_yaml_selectors(self, site_name: str = "wikipedia") -> bool:
        """Initialize YAML selectors for a specific site."""
        try:
            self.logger.info(f"Initializing YAML selectors for site: {site_name}")
            
            if site_name.lower() == "wikipedia":
                return await self._initialize_wikipedia_selectors()
            else:
                self.logger.warning(f"Unsupported site for YAML loading: {site_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize YAML selectors for {site_name}: {str(e)}")
            return False
    
    async def _initialize_wikipedia_selectors(self) -> bool:
        """Initialize Wikipedia-specific YAML selectors."""
        try:
            # Create Wikipedia selector loader
            self._wikipedia_loader = WikipediaSelectorLoader(self.selector_engine)
            
            # Load Wikipedia selectors
            success = await self._wikipedia_loader.load_wikipedia_selectors()
            
            if success:
                self.logger.info("Wikipedia YAML selectors successfully initialized")
                
                # Log available selectors
                available_selectors = self.selector_engine.list_selectors()
                wikipedia_selectors = [s for s in available_selectors if any(
                    s.startswith(prefix) for prefix in [
                        'article_title', 'article_content', 'result_title', 
                        'result_description', 'result_url', 'search_input', 
                        'search_results'
                    ]
                )]
                
                self.logger.info(f"Wikipedia selectors available: {wikipedia_selectors}")
                return True
            else:
                self.logger.error("Failed to load Wikipedia YAML selectors")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing Wikipedia selectors: {str(e)}")
            return False
    
    def get_wikipedia_loader(self) -> Optional[WikipediaSelectorLoader]:
        """Get the Wikipedia selector loader instance."""
        return self._wikipedia_loader
    
    async def reload_selectors(self, site_name: str = "wikipedia") -> bool:
        """Reload YAML selectors for a specific site."""
        try:
            self.logger.info(f"Reloading YAML selectors for site: {site_name}")
            
            if site_name.lower() == "wikipedia" and self._wikipedia_loader:
                return self._wikipedia_loader.reload_selectors()
            else:
                return await self.initialize_yaml_selectors(site_name)
                
        except Exception as e:
            self.logger.error(f"Failed to reload selectors for {site_name}: {str(e)}")
            return False
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status and statistics."""
        try:
            engine_stats = self.selector_engine.get_statistics()
            total_selectors = engine_stats.get("total_selectors", 0)
            available_selectors = engine_stats.get("registered_selectors", [])
            
            wikipedia_selectors = [s for s in available_selectors if any(
                s.startswith(prefix) for prefix in [
                    'article_title', 'article_content', 'result_title', 
                    'result_description', 'result_url', 'search_input', 
                    'search_results'
                ]
            )]
            
            status = {
                "total_engine_selectors": total_selectors,
                "wikipedia_selectors_count": len(wikipedia_selectors),
                "wikipedia_selectors": wikipedia_selectors,
                "wikipedia_loader_active": self._wikipedia_loader is not None,
                "integration_complete": len(wikipedia_selectors) > 0
            }
            
            if self._wikipedia_loader:
                loader_stats = self._wikipedia_loader.get_statistics()
                status.update({
                    "loaded_selectors": loader_stats["loaded_selectors"],
                    "selector_names": loader_stats["selector_names"]
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get integration status: {str(e)}")
            return {
                "error": str(e),
                "integration_complete": False
            }


# Global integrator instance
_integrator: Optional[YAMLSelectorIntegrator] = None


def get_yaml_integrator(selector_engine: SelectorEngine) -> YAMLSelectorIntegrator:
    """Get global YAML integrator instance."""
    global _integrator
    if _integrator is None:
        _integrator = YAMLSelectorIntegrator(selector_engine)
    return _integrator


async def initialize_yaml_selectors(selector_engine: SelectorEngine, site_name: str = "wikipedia") -> bool:
    """Initialize YAML selectors using the global integrator."""
    integrator = get_yaml_integrator(selector_engine)
    return await integrator.initialize_yaml_selectors(site_name)


def get_integration_status(selector_engine: SelectorEngine) -> Dict[str, Any]:
    """Get integration status using the global integrator."""
    integrator = get_yaml_integrator(selector_engine)
    return integrator.get_integration_status()
