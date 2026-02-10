"""
Wikipedia YAML selector integration using existing selector engine.

This module provides simple integration to load Wikipedia YAML selectors
into the existing selector engine without breaking it.
"""

import asyncio
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class WikipediaSelectorIntegration:
    """Simple integration for Wikipedia YAML selectors using existing engine infrastructure."""
    
    def __init__(self, selector_engine):
        """Initialize the Wikipedia selector integration."""
        self.selector_engine = selector_engine
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.selectors_directory = Path(__file__).parent / "selectors"
        self._initialized = False
    
    async def initialize_wikipedia_selectors(self) -> bool:
        """Initialize Wikipedia YAML selectors using simple approach."""
        try:
            self.logger.info("Initializing Wikipedia YAML selectors using simple approach...")
            
            # Check if selectors directory exists
            if not self.selectors_directory.exists():
                self.logger.error(f"Selectors directory not found: {self.selectors_directory}")
                return False
            
            # Find all YAML selector files
            selector_files = list(self.selectors_directory.glob("*.yaml"))
            if not selector_files:
                self.logger.warning(f"No YAML selector files found in {self.selectors_directory}")
                return False
            
            self.logger.info(f"Found {len(selector_files)} YAML selector files")
            
            # Load each selector file and register with engine
            loaded_count = 0
            for selector_file in selector_files:
                try:
                    # Load YAML file
                    with open(selector_file, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f)
                    
                    if not yaml_data:
                        self.logger.warning(f"Empty YAML file: {selector_file}")
                        continue
                    
                    # Create a simple selector object
                    selector_name = selector_file.stem
                    selector_data = {
                        "name": selector_name,
                        "description": yaml_data.get("description", f"Wikipedia selector: {selector_name}"),
                        "selector_type": yaml_data.get("selector_type", "css"),
                        "pattern": yaml_data.get("strategies", [{}])[0].get("selector", ""),
                        "strategies": yaml_data.get("strategies", []),
                        "confidence_threshold": yaml_data.get("confidence_threshold", 0.8)
                    }
                    
                    # Register with selector engine (using existing API)
                    if hasattr(self.selector_engine, 'register_selector'):
                        # Try to register using existing method
                        success = await self._register_with_engine(selector_name, selector_data)
                        if success:
                            loaded_count += 1
                            self.logger.info(f"✅ Registered Wikipedia selector: {selector_name}")
                        else:
                            self.logger.error(f"❌ Failed to register selector: {selector_name}")
                    else:
                        self.logger.warning(f"Selector engine doesn't have register_selector method")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing {selector_file}: {str(e)}")
                    continue
            
            self._initialized = loaded_count > 0
            
            # Log results
            available_selectors = self.selector_engine.list_selectors() if hasattr(self.selector_engine, 'list_selectors') else []
            wikipedia_selectors = [s for s in available_selectors if any(
                s.startswith(prefix) for prefix in [
                    'article_title', 'article_content', 'result_title', 
                    'result_description', 'result_url', 'search_input', 
                    'search_results'
                ]
            )]
            
            self.logger.info(f"✅ Wikipedia selectors initialized: {loaded_count} loaded")
            self.logger.info(f"🔍 Available Wikipedia selectors: {wikipedia_selectors}")
            
            return self._initialized
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Wikipedia selectors: {str(e)}")
            return False
    
    async def _register_with_engine(self, name: str, data: Dict[str, Any]) -> bool:
        """Register selector with the existing engine."""
        try:
            # Try different registration methods that might exist
            if hasattr(self.selector_engine, 'register_selector'):
                # Try with a simple selector object
                from src.models.selector_models import SemanticSelector, StrategyPattern, ValidationRule
                
                strategies = []
                for i, strategy_data in enumerate(data.get("strategies", [])):
                    strategy = StrategyPattern(
                        id=f"{name}_strategy_{i}",
                        type=strategy_data.get("type", "css"),
                        priority=i + 1,  # Ensure unique priorities
                        config=strategy_data
                    )
                    strategies.append(strategy)
                
                selector = SemanticSelector(
                    name=name,
                    description=data.get("description", ""),
                    context="wikipedia_extraction",
                    strategies=strategies,
                    validation_rules=[]
                )
                
                result = await self.selector_engine.register_selector(selector)
                return result
            
            elif hasattr(self.selector_engine, 'add_selector'):
                # Try alternative method
                return self.selector_engine.add_selector(name, data)
            
            else:
                self.logger.warning(f"No registration method available in selector engine")
                return False
                
        except Exception as e:
            self.logger.error(f"Error registering selector {name}: {str(e)}")
            return False
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status and statistics."""
        try:
            status = {
                "initialized": self._initialized,
                "selectors_directory": str(self.selectors_directory)
            }
            
            # Engine statistics
            if self.selector_engine:
                try:
                    if hasattr(self.selector_engine, 'get_statistics'):
                        engine_stats = self.selector_engine.get_statistics()
                        status.update({
                            "total_engine_selectors": engine_stats.get("total_selectors", 0),
                            "engine_selectors": engine_stats.get("registered_selectors", [])
                        })
                    elif hasattr(self.selector_engine, 'list_selectors'):
                        available_selectors = self.selector_engine.list_selectors()
                        status.update({
                            "total_engine_selectors": len(available_selectors),
                            "engine_selectors": available_selectors
                        })
                except Exception as e:
                    status["engine_stats_error"] = str(e)
            
            return status
            
        except Exception as e:
            return {
                "error": str(e),
                "initialized": False
            }
    
    async def reload_selectors(self) -> bool:
        """Reload Wikipedia selectors."""
        try:
            self._initialized = False
            return await self.initialize_wikipedia_selectors()
        except Exception as e:
            self.logger.error(f"Failed to reload selectors: {str(e)}")
            return False


# Convenience functions for backward compatibility
async def initialize_wikipedia_selectors(selector_engine) -> bool:
    """Initialize Wikipedia selectors for the given selector engine."""
    integration = WikipediaSelectorIntegration(selector_engine)
    return await integration.initialize_wikipedia_selectors()


def get_wikipedia_selector_integration(selector_engine) -> WikipediaSelectorIntegration:
    """Get Wikipedia selector integration instance."""
    return WikipediaSelectorIntegration(selector_engine)
