"""
Template patterns for different complexity levels.

This package contains four architectural patterns for site templates:
- Simple: Single flow.py file for basic sites
- Standard: flow.py + flows/ for moderate complexity
- Complex: Domain-separated flows for sophisticated sites
- Legacy: Backward compatibility with existing template
"""

from .simple import SimpleFlow
from .standard import StandardFlow, AVAILABLE_FLOWS
from .complex import DOMAIN_FLOWS, get_flow, list_domains, list_domain_flows, list_all_flows

# Pattern registry
PATTERNS = {
    'simple': {
        'name': 'Simple Pattern',
        'description': 'Single flow.py file for basic sites',
        'flow_class': SimpleFlow,
        'suitable_for': ['Static sites', 'Simple navigation', 'Basic extraction']
    },
    'standard': {
        'name': 'Standard Pattern', 
        'description': 'flow.py + flows/ for moderate complexity',
        'flow_class': StandardFlow,
        'suitable_for': ['Dynamic sites', 'Moderate complexity', 'Mixed operations']
    },
    'complex': {
        'name': 'Complex Pattern',
        'description': 'Domain-separated flows for sophisticated sites',
        'flow_registry': DOMAIN_FLOWS,
        'suitable_for': ['SPAs', 'Complex navigation', 'Multi-domain operations']
    }
}

def get_pattern(pattern_name: str):
    """Get pattern configuration by name."""
    return PATTERNS.get(pattern_name)

def list_patterns():
    """List all available patterns."""
    return list(PATTERNS.keys())

def get_pattern_info(pattern_name: str):
    """Get detailed information about a pattern."""
    pattern = PATTERNS.get(pattern_name)
    if pattern:
        return {
            'name': pattern['name'],
            'description': pattern['description'],
            'suitable_for': pattern['suitable_for']
        }
    return None

__all__ = [
    'SimpleFlow',
    'StandardFlow', 
    'AVAILABLE_FLOWS',
    'DOMAIN_FLOWS',
    'get_flow',
    'list_domains',
    'list_domain_flows', 
    'list_all_flows',
    'PATTERNS',
    'get_pattern',
    'list_patterns',
    'get_pattern_info'
]
