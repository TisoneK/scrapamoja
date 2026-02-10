"""
Standard pattern flows registry.

This module handles registration and discovery of flows for the standard pattern.
Flows in this directory handle specialized operations that are too complex
for the basic flow.py file.
"""

from .search_flow import SearchFlow
from .pagination_flow import PaginationFlow
from .extraction_flow import ExtractionFlow

# Registry of available flows
AVAILABLE_FLOWS = {
    'search': SearchFlow,
    'pagination': PaginationFlow,
    'extraction': ExtractionFlow,
}

def get_flow(flow_name: str):
    """Get a flow class by name."""
    return AVAILABLE_FLOWS.get(flow_name)

def list_available_flows():
    """List all available flow names."""
    return list(AVAILABLE_FLOWS.keys())
