"""
GitHub pagination flow implementation.

This module implements pagination handling for GitHub pages,
including repository lists, issue lists, and search results.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs


logger = logging.getLogger(__name__)


class GitHubPaginationFlow:
    """
    GitHub pagination flow implementation.
    
    This class handles pagination across GitHub pages, including
    navigation, page detection, and result collection.
    """
    
    def __init__(self, page: Any, selector_engine: Any):
        """
        Initialize GitHub pagination flow.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
        """
        self.page = page
        self.selector_engine = selector_engine
        
        # Pagination state
        self.current_page = 1
        self.total_pages = 0
        self.total_items = 0
        self.items_per_page = 20
        
        # Pagination configuration
        self.max_pages = 50
        self.wait_timeout = 10000  # 10 seconds
        
        logger.info("GitHubPaginationFlow initialized")
    
    async def get_pagination_info(self) -> Dict[str, Any]:
        """
        Get pagination information for the current page.
        
        Returns:
            Dict[str, Any]: Pagination information
        """
        try:
            logger.debug("Getting pagination information")
            
            pagination_info = {
                "current_page": self.current_page,
                "total_pages": 0,
                "total_items": 0,
                "items_per_page": self.items_per_page,
                "has_next": False,
                "has_previous": False,
                "next_url": None,
                "previous_url": None,
                "first_url": None,
                "last_url": None
            }
            
            # Look for pagination container
            pagination_container = await self._find_pagination_container()
            if not pagination_container:
                logger.debug("No pagination container found")
                return pagination_info
            
            # Extract pagination information
            await self._extract_pagination_numbers(pagination_container, pagination_info)
            await self._extract_pagination_urls(pagination_container, pagination_info)
            
            # Calculate derived values
            pagination_info["has_next"] = pagination_info["current_page"] < pagination_info["total_pages"]
            pagination_info["has_previous"] = pagination_info["current_page"] > 1
            
            logger.debug(f"Pagination info: {pagination_info}")
            return pagination_info
            
        except Exception as e:
            logger.error(f"Failed to get pagination information: {e}")
            return {
                "current_page": self.current_page,
                "total_pages": 0,
                "total_items": 0,
                "items_per_page": self.items_per_page,
                "has_next": False,
                "has_previous": False,
                "error": str(e)
            }
    
    async def _find_pagination_container(self) -> Optional[Any]:
        """
        Find the pagination container element.
        
        Returns:
            Optional[Any]: Pagination container element
        """
        pagination_selectors = [
            "nav[aria-label='Pagination']",
            ".paginate-container",
            "[data-testid='pagination']",
            ".pagination",
            ".js-pagination-container"
        ]
        
        for selector in pagination_selectors:
            try:
                container = await self.page.query_selector(selector)
                if container:
                    return container
            except:
                continue
        
        return None
    
    async def _extract_pagination_numbers(self, container: Any, info: Dict[str, Any]) -> None:
        """
        Extract pagination numbers from container.
        
        Args:
            container: Pagination container element
            info: Pagination info dictionary to update
        """
        try:
            # Look for current page number
            current_selectors = [
                ".current",
                "[aria-current='page']",
                ".selected",
                "span[itemprop='name codeRepository']"
            ]
            
            for selector in current_selectors:
                try:
                    current_element = await container.query_selector(selector)
                    if current_element:
                        current_text = await current_element.text_content()
                        if current_text and current_text.strip().isdigit():
                            info["current_page"] = int(current_text.strip())
                            break
                except:
                    continue
            
            # Look for total pages
            total_selectors = [
                "a[href*='page=100']",
                "a[href*='?page=100']",
                ".last_page"
            ]
            
            for selector in total_selectors:
                try:
                    total_element = await container.query_selector(selector)
                    if total_element:
                        href = await total_element.get_attribute('href')
                        if href:
                            # Extract page number from URL
                            import re
                            match = re.search(r'[?&]page=(\d+)', href)
                            if match:
                                info["total_pages"] = int(match.group(1))
                                break
                except:
                    continue
            
            # Alternative: look for page count text
            if info["total_pages"] == 0:
                page_text_selectors = [
                    ".pagination-info",
                    "[data-testid='pagination-info']",
                    ".js-paging-info"
                ]
                
                for selector in page_text_selectors:
                    try:
                        text_element = await self.page.query_selector(selector)
                        if text_element:
                            text = await text_element.text_content()
                            if text:
                                # Extract from text like "1-20 of 1,234"
                                import re
                                match = re.search(r'of\s*([\d,]+)', text)
                                if match:
                                    total_items = int(match.group(1).replace(',', ''))
                                    info["total_items"] = total_items
                                    
                                    # Estimate total pages
                                    if info["items_per_page"] > 0:
                                        info["total_pages"] = (total_items + info["items_per_page"] - 1) // info["items_per_page"]
                                    break
                    except:
                        continue
            
        except Exception as e:
            logger.debug(f"Failed to extract pagination numbers: {e}")
    
    async def _extract_pagination_urls(self, container: Any, info: Dict[str, Any]) -> None:
        """
        Extract pagination URLs from container.
        
        Args:
            container: Pagination container element
            info: Pagination info dictionary to update
        """
        try:
            # Get all pagination links
            links = await container.query_selector_all('a')
            
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    
                    text = await link.text_content()
                    if not text:
                        continue
                    
                    text = text.strip().lower()
                    
                    # Identify link type
                    if text in ["next", "›", "→"]:
                        info["next_url"] = href
                    elif text in ["previous", "prev", "‹", "←"]:
                        info["previous_url"] = href
                    elif text == "first":
                        info["first_url"] = href
                    elif text == "last":
                        info["last_url"] = href
                    elif text.isdigit():
                        page_num = int(text)
                        if page_num == 1:
                            info["first_url"] = href
                        elif page_num > info["total_pages"]:
                            info["total_pages"] = page_num
                            info["last_url"] = href
                            
                except:
                    continue
            
        except Exception as e:
            logger.debug(f"Failed to extract pagination URLs: {e}")
    
    async def navigate_to_page(self, page_number: int) -> bool:
        """
        Navigate to a specific page number.
        
        Args:
            page_number: Page number to navigate to
            
        Returns:
            bool: True if navigation successful
        """
        try:
            if page_number < 1:
                logger.error(f"Invalid page number: {page_number}")
                return False
            
            if page_number > self.max_pages:
                logger.error(f"Page number {page_number} exceeds maximum {self.max_pages}")
                return False
            
            logger.info(f"Navigating to page {page_number}")
            
            # Get current pagination info
            pagination_info = await self.get_pagination_info()
            
            # Try different navigation methods
            success = False
            
            # Method 1: Use direct URL construction
            if not success:
                success = await self._navigate_via_url(page_number)
            
            # Method 2: Use pagination controls
            if not success:
                success = await self._navigate_via_controls(page_number)
            
            # Method 3: Use search for page link
            if not success:
                success = await self._navigate_via_link_search(page_number)
            
            if success:
                self.current_page = page_number
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)  # Wait for content to stabilize
                
                logger.info(f"Successfully navigated to page {page_number}")
                return True
            else:
                logger.error(f"Failed to navigate to page {page_number}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to page {page_number}: {e}")
            return False
    
    async def _navigate_via_url(self, page_number: int) -> bool:
        """
        Navigate to page via URL construction.
        
        Args:
            page_number: Page number
            
        Returns:
            bool: True if navigation successful
        """
        try:
            current_url = self.page.url
            
            # Parse current URL
            parsed = urlparse(current_url)
            query_params = parse_qs(parsed.query)
            
            # Update page parameter
            query_params['p'] = [str(page_number)]
            
            # Reconstruct URL
            from urllib.parse import urlencode
            new_query = urlencode(query_params, doseq=True)
            
            if parsed.query:
                new_url = current_url.replace(parsed.query, new_query)
            else:
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}{new_query}"
            
            await self.page.goto(new_url)
            await self.page.wait_for_load_state('networkidle')
            
            return True
            
        except Exception as e:
            logger.debug(f"Failed to navigate via URL: {e}")
            return False
    
    async def _navigate_via_controls(self, page_number: int) -> bool:
        """
        Navigate to page using pagination controls.
        
        Args:
            page_number: Page number
            
        Returns:
            bool: True if navigation successful
        """
        try:
            pagination_container = await self._find_pagination_container()
            if not pagination_container:
                return False
            
            # Look for page link
            page_link = await pagination_container.query_selector(f"a[href*='page={page_number}'], a[href*='?page={page_number}']")
            
            if page_link:
                await page_link.click()
                await self.page.wait_for_load_state('networkidle')
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Failed to navigate via controls: {e}")
            return False
    
    async def _navigate_via_link_search(self, page_number: int) -> bool:
        """
        Navigate to page by searching for page link.
        
        Args:
            page_number: Page number
            
        Returns:
            bool: True if navigation successful
        """
        try:
            # Look for any link containing the page number
            page_links = await self.page.query_selector_all(f"a[href*='{page_number}']")
            
            for link in page_links:
                try:
                    href = await link.get_attribute('href')
                    if href and ('page=' in href or '?page=' in href):
                        await link.click()
                        await self.page.wait_for_load_state('networkidle')
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Failed to navigate via link search: {e}")
            return False
    
    async def navigate_next(self) -> bool:
        """
        Navigate to the next page.
        
        Returns:
            bool: True if navigation successful
        """
        pagination_info = await self.get_pagination_info()
        
        if not pagination_info["has_next"]:
            logger.warning("No next page available")
            return False
        
        return await self.navigate_to_page(self.current_page + 1)
    
    async def navigate_previous(self) -> bool:
        """
        Navigate to the previous page.
        
        Returns:
            bool: True if navigation successful
        """
        pagination_info = await self.get_pagination_info()
        
        if not pagination_info["has_previous"]:
            logger.warning("No previous page available")
            return False
        
        return await self.navigate_to_page(self.current_page - 1)
    
    async def navigate_first(self) -> bool:
        """
        Navigate to the first page.
        
        Returns:
            bool: True if navigation successful
        """
        return await self.navigate_to_page(1)
    
    async def navigate_last(self) -> bool:
        """
        Navigate to the last page.
        
        Returns:
            bool: True if navigation successful
        """
        pagination_info = await self.get_pagination_info()
        
        if pagination_info["total_pages"] == 0:
            logger.warning("Total pages unknown, cannot navigate to last page")
            return False
        
        return await self.navigate_to_page(pagination_info["total_pages"])
    
    async def collect_all_pages(
        self,
        max_pages: Optional[int] = None,
        extractor_func: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect data from all pages.
        
        Args:
            max_pages: Maximum number of pages to collect
            extractor_func: Function to extract data from each page
            
        Returns:
            List[Dict[str, Any]]: Data from all pages
        """
        try:
            logger.info("Starting to collect data from all pages")
            
            if max_pages is None:
                max_pages = self.max_pages
            
            all_data = []
            current_page = self.current_page
            
            # Navigate to first page
            await self.navigate_first()
            
            while True:
                # Extract data from current page
                if extractor_func:
                    page_data = await extractor_func()
                else:
                    page_data = await self._extract_page_items()
                
                if page_data:
                    all_data.extend(page_data)
                
                # Check if we should continue
                pagination_info = await self.get_pagination_info()
                
                if not pagination_info["has_next"]:
                    logger.info("Reached last page")
                    break
                
                if current_page >= max_pages:
                    logger.info(f"Reached maximum page limit: {max_pages}")
                    break
                
                # Navigate to next page
                if not await self.navigate_next():
                    logger.error("Failed to navigate to next page")
                    break
                
                current_page += 1
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
            
            logger.info(f"Collected data from {len(all_data)} items across {current_page} pages")
            return all_data
            
        except Exception as e:
            logger.error(f"Failed to collect all pages: {e}")
            return []
    
    async def _extract_page_items(self) -> List[Dict[str, Any]]:
        """
        Extract items from the current page.
        
        Returns:
            List[Dict[str, Any]]: Extracted items
        """
        try:
            # Look for item containers
            item_selectors = [
                "[data-testid='results-list'] > div",
                ".repo-list-item",
                ".js-issue-row",
                "tr.js-navigation-item"
            ]
            
            items = []
            for selector in item_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for element in elements:
                            # Extract basic item data
                            item_data = await self._extract_item_data(element)
                            if item_data:
                                items.append(item_data)
                        break
                except:
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to extract page items: {e}")
            return []
    
    async def _extract_item_data(self, element: Any) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single item element.
        
        Args:
            element: Item element
            
        Returns:
            Optional[Dict[str, Any]]: Item data
        """
        try:
            # Extract basic information
            text = await element.text_content()
            href = await element.get_attribute('href')
            
            return {
                "text": text.strip() if text else "",
                "url": href or "",
                "page": self.current_page
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract item data: {e}")
            return None
    
    def reset_pagination_state(self) -> None:
        """Reset pagination state to defaults."""
        self.current_page = 1
        self.total_pages = 0
        self.total_items = 0
        self.items_per_page = 20
        
        logger.info("Pagination state reset")
    
    def get_pagination_state(self) -> Dict[str, Any]:
        """
        Get current pagination state.
        
        Returns:
            Dict[str, Any]: Pagination state
        """
        return {
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "total_items": self.total_items,
            "items_per_page": self.items_per_page,
            "max_pages": self.max_pages
        }
