"""
Standard pattern template.

This pattern combines basic navigation in flow.py with specialized
flows in the flows/ subfolder for complex operations.
"""

from .flow import StandardFlow
from .flows import AVAILABLE_FLOWS

__all__ = ['StandardFlow', 'AVAILABLE_FLOWS']
