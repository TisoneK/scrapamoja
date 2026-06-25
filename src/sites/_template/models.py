"""
Data models for template site scraper.

Optional: Define site-specific data models and structures here.
Remove this file if not needed for your scraper.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class SearchResult:
    """Model for a single search result."""
    title: str
    url: str
    description: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SearchResults:
    """Model for search results collection."""
    query: str
    results: List[SearchResult]
    total_count: int
    page_number: int = 1
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SiteMetadata:
    """Model for site metadata information."""
    site_id: str
    site_name: str
    base_url: str
    version: str
    maintainer: str
    description: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# Utility functions for model creation
def create_search_result(title: str, url: str, description: str) -> SearchResult:
    """Create a search result model."""
    return SearchResult(title=title, url=url, description=description)


def create_search_results(query: str, results_data: List[dict]) -> SearchResults:
    """Create a search results collection from raw data."""
    search_results = []
    
    for item in results_data:
        result = create_search_result(
            title=item.get('title', ''),
            url=item.get('url', ''),
            description=item.get('description', '')
        )
        search_results.append(result)
    
    return SearchResults(
        query=query,
        results=search_results,
        total_count=len(search_results)
    )
