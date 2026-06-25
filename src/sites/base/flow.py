"""
Base flow abstract class.

Defines the contract for navigation-only logic in site scrapers.
Flow classes should handle page navigation and interactions only,
without data extraction or normalization.
"""

from abc import ABC
from playwright.async_api import Page


class BaseFlow(ABC):
    """Abstract base class for navigation-only logic."""
    
    def __init__(self, page: Page, selector_engine):
        """Initialize flow with page and selector engine."""
        self.page = page
        self.selector_engine = selector_engine
