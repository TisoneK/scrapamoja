"""
GitHub search flow implementation.

This module implements the search flow for GitHub, including query input,
result navigation, and result extraction.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from ..flow import GitHubFlow


logger = logging.getLogger(__name__)


class GitHubSearchFlow(GitHubFlow):
    """
    GitHub search flow implementation.
    
    This class handles the complete search flow on GitHub,
    from query input to result extraction and pagination.
    """
    
    def __init__(self, page: Any, selector_engine: Any):
        """
        Initialize GitHub search flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
        """
        super().__init__(page, selector_engine)
        
        # Search-specific configuration
        self.search_types = ["repositories", "users", "issues", "commits", "code"]
        self.sort_options = ["stars", "forks", "updated", "created"]
        self.order_options = ["desc", "asc"]
        
        # Search state
        self.current_query = ""
        self.current_search_type = "repositories"
        self.current_sort = "stars"
        self.current_order = "desc"
        self.current_page = 1
        
        logger.info("GitHubSearchFlow initialized")
    
    async def perform_search(
        self,
        query: str,
        search_type: str = "repositories",
        sort: str = "stars",
        order: str = "desc",
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Perform a complete search operation.
        
        Args:
            query: Search query
            search_type: Type of search (repositories, users, issues, etc.)
            sort: Sort order (stars, forks, updated, created)
            order: Sort direction (desc, asc)
            page: Page number
            
        Returns:
            Dict[str, Any]: Search results
        """
        try:
            logger.info(f"Performing GitHub search: {query} (type: {search_type}, sort: {sort}, order: {order}, page: {page})")
            
            # Update search state
            self.current_query = query
            self.current_search_type = search_type
            self.current_sort = sort
            self.current_order = order
            self.current_page = page
            
            # Navigate to search
            success = await self.navigate_to_search(query, search_type)
            if not success:
                return {
                    "success": False,
                    "error": "Failed to navigate to search",
                    "query": query,
                    "search_type": search_type
                }
            
            # Apply sort and order if needed
            if sort != "stars" or order != "desc":
                await self.apply_search_sort(sort, order)
            
            # Navigate to specific page if needed
            if page > 1:
                await self.navigate_to_search_page(page)
            
            # Wait for results to load
            await self.wait_for_content_load()
            
            # Extract search results
            results = await self.extract_search_results()
            
            # Add search metadata
            results.update({
                "query": query,
                "search_type": search_type,
                "sort": sort,
                "order": order,
                "page": page,
                "success": True
            })
            
            logger.info(f"Search completed: {len(results.get('results', []))} results found")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform search: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "search_type": search_type
            }
    
    async def apply_search_sort(self, sort: str, order: str) -> bool:
        """
        Apply sort order to search results.
        
        Args:
            sort: Sort field
            order: Sort order
            
        Returns:
            bool: True if sort applied successfully
        """
        try:
            logger.debug(f"Applying search sort: {sort} {order}")
            
            # Look for sort dropdown
            sort_selectors = [
                "select[name='sort']",
                "#sort-options",
                "[data-testid='sort-dropdown']"
            ]
            
            sort_element = None
            for selector in sort_selectors:
                try:
                    sort_element = await self.page.query_selector(selector)
                    if sort_element:
                        break
                except:
                    continue
            
            if not sort_element:
                logger.warning("Sort dropdown not found, using URL parameters")
                return await self.apply_sort_via_url(sort, order)
            
            # Click sort dropdown
            await sort_element.click()
            await self.page.wait_for_timeout(500)
            
            # Select sort option
            sort_option_selector = f"option[value='{sort}']"
            sort_option = await sort_element.query_selector(sort_option_selector)
            
            if sort_option:
                await sort_option.click()
                await self.page.wait_for_timeout(500)
            
            # Apply order if needed
            if order == "asc":
                await self.apply_search_order(order)
            
            # Wait for results to reload
            await self.wait_for_content_load()
            
            logger.debug(f"Search sort applied: {sort} {order}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply search sort: {e}")
            return False
    
    async def apply_sort_via_url(self, sort: str, order: str) -> bool:
        """
        Apply sort via URL parameters.
        
        Args:
            sort: Sort field
            order: Sort order
            
        Returns:
            bool: True if sort applied successfully
        """
        try:
            current_url = self.page.url
            
            # Add sort parameters to URL
            if "?" in current_url:
                new_url = f"{current_url}&sort={sort}&order={order}"
            else:
                new_url = f"{current_url}?sort={sort}&order={order}"
            
            await self.page.goto(new_url)
            await self.wait_for_content_load()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply sort via URL: {e}")
            return False
    
    async def apply_search_order(self, order: str) -> bool:
        """
        Apply search order (asc/desc).
        
        Args:
            order: Sort order
            
        Returns:
            bool: True if order applied successfully
        """
        try:
            # Look for order toggle
            order_selectors = [
                "a[href*='order=asc']",
                "a[href*='order=desc']",
                "[data-testid='order-toggle']"
            ]
            
            for selector in order_selectors:
                try:
                    order_element = await self.page.query_selector(selector)
                    if order_element and order in await order_element.get_attribute('href'):
                        await order_element.click()
                        await self.page.wait_for_timeout(500)
                        break
                except:
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply search order: {e}")
            return False
    
    async def navigate_to_search_page(self, page: int) -> bool:
        """
        Navigate to a specific search results page.
        
        Args:
            page: Page number
            
        Returns:
            bool: True if navigation successful
        """
        try:
            if page <= 1:
                return True  # Already on first page
            
            # Look for pagination controls
            pagination_selectors = [
                "nav[aria-label='Pagination']",
                ".paginate-container",
                "[data-testid='pagination']"
            ]
            
            pagination_element = None
            for selector in pagination_selectors:
                try:
                    pagination_element = await self.page.query_selector(selector)
                    if pagination_element:
                        break
                except:
                    continue
            
            if not pagination_element:
                logger.warning("Pagination controls not found")
                return False
            
            # Try to navigate directly to page
            current_url = self.page.url
            if "&p=" in current_url:
                new_url = current_url.replace(f"&p={self.current_page}", f"&p={page}")
            elif "?p=" in current_url:
                new_url = current_url.replace(f"?p={self.current_page}", f"?p={page}")
            else:
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}p={page}"
            
            await self.page.goto(new_url)
            await self.wait_for_content_load()
            
            self.current_page = page
            logger.debug(f"Navigated to search page: {page}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to search page {page}: {e}")
            return False
    
    async def extract_search_results(self) -> Dict[str, Any]:
        """
        Extract search results from the current page.
        
        Returns:
            Dict[str, Any]: Extracted search results
        """
        try:
            logger.debug("Extracting search results")
            
            # Get search results container
            results_container = await self.page.query_selector('[data-testid="results-list"]')
            if not results_container:
                results_container = await self.page.query_selector('.repo-list')
            
            if not results_container:
                return {
                    "results": [],
                    "total_results": 0,
                    "page": self.current_page,
                    "per_page": 0
                }
            
            # Extract result items
            result_items = await results_container.query_selector_all('> div')
            
            results = []
            for i, item in enumerate(result_items):
                try:
                    # Use selector engine to extract data from each item
                    item_data = await self.selector_engine.find_all(item, "repository_list_item")
                    
                    if item_data:
                        # Extract structured data using extraction rules
                        from ..extraction.rules import GitHubExtractionRules
                        extraction_rules = GitHubExtractionRules()
                        
                        extracted_data = await extraction_rules.extract_repository_data(item)
                        if extracted_data and "error" not in extracted_data:
                            results.append(extracted_data)
                            
                except Exception as e:
                    logger.warning(f"Failed to extract result item {i}: {e}")
                    continue
            
            # Get total results count
            total_results = await self.get_total_results_count()
            
            # Get per page count
            per_page = len(results)
            
            return {
                "results": results,
                "total_results": total_results,
                "page": self.current_page,
                "per_page": per_page,
                "has_next": await self.has_next_page(),
                "has_previous": self.current_page > 1
            }
            
        except Exception as e:
            logger.error(f"Failed to extract search results: {e}")
            return {
                "results": [],
                "total_results": 0,
                "page": self.current_page,
                "per_page": 0,
                "error": str(e)
            }
    
    async def get_total_results_count(self) -> int:
        """
        Get total number of search results.
        
        Returns:
            int: Total results count
        """
        try:
            # Look for results count
            count_selectors = [
                "[data-testid='results-count']",
                ".codesearch-results",
                "h3 strong"
            ]
            
            for selector in count_selectors:
                try:
                    count_element = await self.page.query_selector(selector)
                    if count_element:
                        count_text = await count_element.text_content()
                        if count_text:
                            # Extract number from text
                            import re
                            match = re.search(r'(\d+[,\d]*)', count_text)
                            if match:
                                return int(match.group(1).replace(',', ''))
                except:
                    continue
            
            return 0
            
        except Exception as e:
            logger.debug(f"Failed to get total results count: {e}")
            return 0
    
    async def has_next_page(self) -> bool:
        """
        Check if there is a next page of results.
        
        Returns:
            bool: True if next page exists
        """
        try:
            # Look for next page link
            next_selectors = [
                "a[rel='next']",
                ".next_page",
                "[data-testid='next-page']"
            ]
            
            for selector in next_selectors:
                try:
                    next_element = await self.page.query_selector(selector)
                    if next_element:
                        href = await next_element.get_attribute('href')
                        if href:
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Failed to check for next page: {e}")
            return False
    
    async def get_search_suggestions(self, query: str) -> List[str]:
        """
        Get search suggestions for a query.
        
        Args:
            query: Search query
            
        Returns:
            List[str]: Search suggestions
        """
        try:
            logger.debug(f"Getting search suggestions for: {query}")
            
            # Type in search input to trigger suggestions
            search_input = await self.page.query_selector("input[name='q']")
            if not search_input:
                return []
            
            await search_input.clear()
            await search_input.type(query)
            await self.page.wait_for_timeout(1000)
            
            # Look for suggestions
            suggestion_selectors = [
                ".search-suggestions",
                "[data-testid='search-suggestions']",
                ".typeahead-suggestions"
            ]
            
            suggestions = []
            for selector in suggestion_selectors:
                try:
                    suggestion_elements = await self.page.query_selector_all(f"{selector} li, {selector} a")
                    for element in suggestion_elements:
                        text = await element.text_content()
                        if text and text.strip():
                            suggestions.append(text.strip())
                except:
                    continue
            
            # Clear search input
            await search_input.clear()
            
            logger.debug(f"Found {len(suggestions)} search suggestions")
            return suggestions[:10]  # Limit to 10 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    async def get_search_filters(self) -> Dict[str, List[str]]:
        """
        Get available search filters.
        
        Returns:
            Dict[str, List[str]]: Available filters
        """
        try:
            logger.debug("Getting search filters")
            
            filters = {
                "languages": [],
                "topics": [],
                "sort": self.sort_options,
                "order": self.order_options
            }
            
            # Look for language filters
            language_selectors = [
                "select[name='language']",
                "[data-testid='language-filter']"
            ]
            
            for selector in language_selectors:
                try:
                    language_element = await self.page.query_selector(selector)
                    if language_element:
                        options = await language_element.query_selector_all('option')
                        for option in options:
                            value = await option.get_attribute('value')
                            if value and value != "":
                                filters["languages"].append(value)
                        break
                except:
                    continue
            
            # Look for topic filters
            topic_selectors = [
                "select[name='topic']",
                "[data-testid='topic-filter']"
            ]
            
            for selector in topic_selectors:
                try:
                    topic_element = await self.page.query_selector(selector)
                    if topic_element:
                        options = await topic_element.query_selector_all('option')
                        for option in options:
                            value = await option.get_attribute('value')
                            if value and value != "":
                                filters["topics"].append(value)
                        break
                except:
                    continue
            
            logger.debug(f"Found search filters: {list(filters.keys())}")
            return filters
            
        except Exception as e:
            logger.error(f"Failed to get search filters: {e}")
            return {
                "languages": [],
                "topics": [],
                "sort": self.sort_options,
                "order": self.order_options
            }
    
    def get_search_state(self) -> Dict[str, Any]:
        """
        Get current search state.
        
        Returns:
            Dict[str, Any]: Current search state
        """
        return {
            "current_query": self.current_query,
            "current_search_type": self.current_search_type,
            "current_sort": self.current_sort,
            "current_order": self.current_order,
            "current_page": self.current_page,
            "available_search_types": self.search_types,
            "available_sort_options": self.sort_options,
            "available_order_options": self.order_options
        }
