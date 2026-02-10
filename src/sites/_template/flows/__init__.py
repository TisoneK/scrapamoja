"""
Flows module for the modular site scraper template.

This module contains navigation flow components that handle different
aspects of site interaction such as search, login, pagination, etc.
"""

from .base_flow import BaseTemplateFlow
from .search_flow import SearchFlow
from .login_flow import LoginFlow
from .pagination_flow import PaginationFlow

__all__ = [
    'BaseTemplateFlow',
    'SearchFlow', 
    'LoginFlow',
    'PaginationFlow'
]

# Version information
__version__ = "1.0.0"
__author__ = "Modular Scraper Template"

# Flow registry for easy access
FLOW_REGISTRY = {
    'base': BaseTemplateFlow,
    'search': SearchFlow,
    'login': LoginFlow,
    'pagination': PaginationFlow
}

def get_flow(flow_type: str):
    """
    Get flow class by type.
    
    Args:
        flow_type: Type of flow ('base', 'search', 'login', 'pagination')
        
    Returns:
        Flow class
        
    Raises:
        ValueError: If flow type is not found
    """
    if flow_type not in FLOW_REGISTRY:
        raise ValueError(f"Unknown flow type: {flow_type}. Available types: {list(FLOW_REGISTRY.keys())}")
    
    return FLOW_REGISTRY[flow_type]

def list_available_flows():
    """List all available flow types."""
    return list(FLOW_REGISTRY.keys())
