"""
Components module for the modular site scraper template.

This module contains reusable components that provide common functionality
like authentication, rate limiting, stealth handling, and more.
"""

from .oauth_auth import OAuthAuthComponent
from .rate_limiter import RateLimiterComponent
from .stealth_handler import StealthHandlerComponent

__all__ = [
    'OAuthAuthComponent',
    'RateLimiterComponent',
    'StealthHandlerComponent'
]

# Version information
__version__ = "1.0.0"
__author__ = "Modular Scraper Template"

# Component registry for easy access
COMPONENT_REGISTRY = {
    'oauth_auth': OAuthAuthComponent,
    'rate_limiter': RateLimiterComponent,
    'stealth_handler': StealthHandlerComponent
}

def get_component(component_type: str):
    """
    Get component class by type.
    
    Args:
        component_type: Type of component ('oauth_auth', 'rate_limiter', 'stealth_handler')
        
    Returns:
        Component class
        
    Raises:
        ValueError: If component type is not found
    """
    if component_type not in COMPONENT_REGISTRY:
        raise ValueError(f"Unknown component type: {component_type}. Available types: {list(COMPONENT_REGISTRY.keys())}")
    
    return COMPONENT_REGISTRY[component_type]

def list_available_components():
    """List all available component types."""
    return list(COMPONENT_REGISTRY.keys())

# Component manager for managing multiple components
class ComponentManager:
    """Manager for handling multiple components."""
    
    def __init__(self):
        """Initialize component manager."""
        self.components = {}
        self.component_configs = {}
    
    def add_component(self, component_type: str, component_instance, config: dict = None):
        """
        Add a component to the manager.
        
        Args:
            component_type: Type of component
            component_instance: Component instance
            config: Component configuration
        """
        self.components[component_type] = component_instance
        self.component_configs[component_type] = config or {}
    
    def get_component(self, component_type: str):
        """
        Get a component instance.
        
        Args:
            component_type: Type of component
            
        Returns:
            Component instance or None
        """
        return self.components.get(component_type)
    
    def remove_component(self, component_type: str):
        """
        Remove a component from the manager.
        
        Args:
            component_type: Type of component to remove
        """
        if component_type in self.components:
            del self.components[component_type]
        if component_type in self.component_configs:
            del self.component_configs[component_type]
    
    def list_components(self):
        """List all managed components."""
        return list(self.components.keys())
    
    async def initialize_all(self):
        """Initialize all managed components."""
        for component_type, component in self.components.items():
            try:
                if hasattr(component, 'initialize'):
                    await component.initialize(self.component_configs[component_type])
            except Exception as e:
                print(f"Failed to initialize component {component_type}: {str(e)}")
    
    async def cleanup_all(self):
        """Cleanup all managed components."""
        for component_type, component in self.components.items():
            try:
                if hasattr(component, 'cleanup'):
                    await component.cleanup()
            except Exception as e:
                print(f"Failed to cleanup component {component_type}: {str(e)}")
    
    def get_component_status(self):
        """Get status of all components."""
        status = {}
        for component_type, component in self.components.items():
            try:
                if hasattr(component, 'get_status'):
                    status[component_type] = component.get_status()
                else:
                    status[component_type] = {'status': 'active', 'type': component_type}
            except Exception as e:
                status[component_type] = {'status': 'error', 'error': str(e)}
        return status
