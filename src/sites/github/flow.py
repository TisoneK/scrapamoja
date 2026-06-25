"""
GitHub flow implementation for navigation and interaction patterns.

This module implements the flow logic for GitHub-specific navigation,
following the BaseFlow pattern from the existing framework.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote, urljoin

from src.sites.base.flow import BaseFlow


logger = logging.getLogger(__name__)


class GitHubFlow(BaseFlow):
    """
    GitHub-specific flow implementation for navigation and interaction.
    
    This class provides standardized navigation patterns for GitHub,
    including search, repository browsing, user profiles, and issue tracking.
    """
    
    def __init__(self, page: Any, selector_engine: Any):
        """
        Initialize GitHub flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
        """
        super().__init__(page, selector_engine)
        
        # GitHub-specific configuration
        self.base_url = "https://github.com"
        self.search_url = "https://github.com/search"
        
        # Navigation state
        self.current_url = None
        self.navigation_history: List[str] = []
        
        # Flow capabilities
        self.capabilities = [
            "search_navigation",
            "repository_navigation", 
            "user_navigation",
            "issue_navigation",
            "pagination_handling"
        ]
        
        logger.info("GitHubFlow initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the GitHub flow.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Navigate to GitHub homepage
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Check if we're on GitHub
            current_url = self.page.url
            if "github.com" not in current_url:
                logger.error(f"Not redirected to GitHub. Current URL: {current_url}")
                return False
            
            self.current_url = current_url
            self.navigation_history.append(current_url)
            
            logger.info("GitHub flow initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize GitHub flow: {e}")
            return False
    
    async def navigate_to_search(self, query: str, search_type: str = "repositories") -> bool:
        """
        Navigate to GitHub search with specific query.
        
        Args:
            query: Search query
            search_type: Type of search (repositories, users, issues, etc.)
            
        Returns:
            bool: True if navigation successful
        """
        try:
            logger.info(f"Navigating to GitHub search for: {query}")
            
            # Construct search URL
            encoded_query = quote(query)
            search_url = f"{self.search_url}?q={encoded_query}&type={search_type}"
            
            # Navigate to search page
            await self.page.goto(search_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for search results to load
            await self.page.wait_for_selector('[data-testid="results-list"]', timeout=10000)
            
            # Update navigation state
            self.current_url = self.page.url
            self.navigation_history.append(self.current_url)
            
            logger.info(f"Successfully navigated to search for: {query}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to search for '{query}': {e}")
            return False
    
    async def navigate_to_repository(self, identifier: str) -> bool:
        """
        Navigate to a specific repository.
        
        Args:
            identifier: Repository identifier (owner/repo format)
            
        Returns:
            bool: True if navigation successful
        """
        try:
            logger.info(f"Navigating to repository: {identifier}")
            
            # Construct repository URL
            repo_url = f"{self.base_url}/{identifier}"
            
            # Navigate to repository page
            await self.page.goto(repo_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for repository content to load
            await self.page.wait_for_selector('main', timeout=10000)
            
            # Check if we successfully loaded the repository
            current_url = self.page.url
            if "github.com" not in current_url or identifier not in current_url:
                logger.error(f"Failed to load repository page. Current URL: {current_url}")
                return False
            
            # Update navigation state
            self.current_url = current_url
            self.navigation_history.append(self.current_url)
            
            logger.info(f"Successfully navigated to repository: {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to repository '{identifier}': {e}")
            return False
    
    async def navigate_to_user(self, identifier: str) -> bool:
        """
        Navigate to a user profile.
        
        Args:
            identifier: User identifier (username)
            
        Returns:
            bool: True if navigation successful
        """
        try:
            logger.info(f"Navigating to user profile: {identifier}")
            
            # Construct user profile URL
            user_url = f"{self.base_url}/{identifier}"
            
            # Navigate to user profile
            await self.page.goto(user_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for profile content to load
            await self.page.wait_for_selector('main', timeout=10000)
            
            # Check if we successfully loaded the user profile
            current_url = self.page.url
            if "github.com" not in current_url or identifier not in current_url:
                logger.error(f"Failed to load user profile. Current URL: {current_url}")
                return False
            
            # Update navigation state
            self.current_url = current_url
            self.navigation_history.append(self.current_url)
            
            logger.info(f"Successfully navigated to user profile: {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to user profile '{identifier}': {e}")
            return False
    
    async def navigate_to_repository_issues(self, identifier: str, state: str = "open") -> bool:
        """
        Navigate to repository issues page.
        
        Args:
            identifier: Repository identifier (owner/repo format)
            state: Issue state (open, closed, all)
            
        Returns:
            bool: True if navigation successful
        """
        try:
            logger.info(f"Navigating to issues for repository: {identifier} (state: {state})")
            
            # Construct issues URL
            issues_url = f"{self.base_url}/{identifier}/issues?q=is:{state}"
            
            # Navigate to issues page
            await self.page.goto(issues_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for issues list to load
            await self.page.wait_for_selector('[data-testid="issue-list"]', timeout=10000)
            
            # Check if we successfully loaded the issues page
            current_url = self.page.url
            if "github.com" not in current_url or identifier not in current_url or "issues" not in current_url:
                logger.error(f"Failed to load issues page. Current URL: {current_url}")
                return False
            
            # Update navigation state
            self.current_url = current_url
            self.navigation_history.append(self.current_url)
            
            logger.info(f"Successfully navigated to issues for repository: {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to issues for repository '{identifier}': {e}")
            return False
    
    async def handle_pagination(self, direction: str = "next", max_pages: int = 10) -> bool:
        """
        Handle pagination on GitHub pages.
        
        Args:
            direction: Pagination direction ("next", "previous", "first", "last")
            max_pages: Maximum number of pages to navigate
            
        Returns:
            bool: True if pagination successful
        """
        try:
            logger.info(f"Handling pagination: {direction}")
            
            # Check current page count
            if len(self.navigation_history) >= max_pages:
                logger.warning(f"Maximum page limit ({max_pages}) reached")
                return False
            
            # Find pagination controls
            pagination_selectors = [
                'nav[aria-label="Pagination"]',
                '.paginate-container',
                '[data-testid="pagination"]'
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
                logger.warning("No pagination controls found")
                return False
            
            # Find the appropriate pagination link
            if direction == "next":
                link_selector = 'a[rel="next"], .next_page'
            elif direction == "previous":
                link_selector = 'a[rel="prev"], .previous_page'
            elif direction == "first":
                link_selector = 'a[rel="start"], .first_page'
            elif direction == "last":
                link_selector = 'a[rel="end"], .last_page'
            else:
                logger.error(f"Invalid pagination direction: {direction}")
                return False
            
            # Click the pagination link
            pagination_link = await pagination_element.query_selector(link_selector)
            if not pagination_link:
                logger.warning(f"No pagination link found for direction: {direction}")
                return False
            
            # Get the href and navigate
            href = await pagination_link.get_attribute('href')
            if not href:
                # Try clicking the link directly
                await pagination_link.click()
                await self.page.wait_for_load_state('networkidle')
            else:
                await self.page.goto(href)
                await self.page.wait_for_load_state('networkidle')
            
            # Update navigation state
            self.current_url = self.page.url
            self.navigation_history.append(self.current_url)
            
            logger.info(f"Successfully handled pagination: {direction}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle pagination '{direction}': {e}")
            return False
    
    async def wait_for_content_load(self, timeout: int = 10000) -> bool:
        """
        Wait for GitHub content to load completely.
        
        Args:
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            bool: True if content loaded successfully
        """
        try:
            # Wait for main content to be visible
            await self.page.wait_for_selector('main', timeout=timeout)
            
            # Wait for any loading indicators to disappear
            loading_selectors = [
                '.loading-spinner',
                '[data-testid="loading"]',
                '.is-loading'
            ]
            
            for selector in loading_selectors:
                try:
                    await self.page.wait_for_selector(selector, state='hidden', timeout=2000)
                except:
                    continue  # Loading element might not exist
            
            # Additional wait for dynamic content
            await asyncio.sleep(1)
            
            logger.debug("GitHub content loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to wait for content load: {e}")
            return False
    
    async def scroll_to_bottom(self, scroll_pause_time: float = 1.0) -> bool:
        """
        Scroll to the bottom of the page to load dynamic content.
        
        Args:
            scroll_pause_time: Time to pause between scrolls
            
        Returns:
            bool: True if scroll completed successfully
        """
        try:
            logger.debug("Scrolling to bottom of page")
            
            # Get initial page height
            last_height = await self.page.evaluate("document.body.scrollHeight")
            
            while True:
                # Scroll to bottom
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # Wait for new content to load
                await asyncio.sleep(scroll_pause_time)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = await self.page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break  # No more content to load
                
                last_height = new_height
            
            logger.debug("Successfully scrolled to bottom of page")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scroll to bottom: {e}")
            return False
    
    async def get_navigation_state(self) -> Dict[str, Any]:
        """
        Get current navigation state.
        
        Returns:
            Dict[str, Any]: Navigation state information
        """
        return {
            "current_url": self.current_url,
            "navigation_history": self.navigation_history.copy(),
            "history_length": len(self.navigation_history),
            "capabilities": self.capabilities.copy()
        }
    
    async def go_back(self) -> bool:
        """
        Navigate back to the previous page.
        
        Returns:
            bool: True if navigation back successful
        """
        try:
            if len(self.navigation_history) < 2:
                logger.warning("No previous page to go back to")
                return False
            
            # Remove current URL from history
            self.navigation_history.pop()
            
            # Get previous URL
            previous_url = self.navigation_history[-1]
            
            # Navigate back
            await self.page.goto(previous_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Update current URL
            self.current_url = previous_url
            
            logger.info(f"Successfully navigated back to: {previous_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate back: {e}")
            return False
    
    async def refresh_page(self) -> bool:
        """
        Refresh the current page.
        
        Returns:
            bool: True if refresh successful
        """
        try:
            logger.info("Refreshing current page")
            
            await self.page.reload()
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for content to reload
            await self.wait_for_content_load()
            
            logger.info("Page refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh page: {e}")
            return False
