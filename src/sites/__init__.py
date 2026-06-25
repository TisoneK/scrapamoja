"""
Site Scraper Framework

A template-driven system for creating and managing website scrapers.
Provides base contracts, registry system, and validation guardrails.
"""

from .registry import ScraperRegistry

__version__ = "1.0.0"
__all__ = ["ScraperRegistry"]
