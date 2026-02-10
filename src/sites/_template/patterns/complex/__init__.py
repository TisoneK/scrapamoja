"""
Complex pattern template.

This pattern provides the most sophisticated flow organization with
domain-specific subfolders for navigation, extraction, filtering, and authentication.
"""

from .flows import DOMAIN_FLOWS, get_flow, list_domains, list_domain_flows, list_all_flows

__all__ = [
    'DOMAIN_FLOWS',
    'get_flow',
    'list_domains', 
    'list_domain_flows',
    'list_all_flows'
]
