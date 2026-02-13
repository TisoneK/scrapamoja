"""
Tertiary tab extractor for Flashscore match detail pages.

Handles extraction from tertiary statistical filters: Inc OT, FT, Q1.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import PageState, TertiaryData
from datetime import datetime


class TertiaryTabExtractor(ABC):
    """Base class for tertiary tab extraction from match detail pages."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self.page = scraper.page
    
    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.tertiary_tab_extractor.{self.__class__.__name__.lower()}")
    
    async def navigate_to_filter(self, filter_name: str) -> bool:
        """
        Navigate to a specific statistical filter.
        
        Args:
            filter_name: Name of filter to navigate to (inc_ot, ft, q1)
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Try multiple selector patterns for filter navigation
            filter_selectors = [
                f'.statsFilter[data-filter="{filter_name}"]',
                f'.filter__item[data-name="{filter_name}"]',
                f'.stats__filter[href*="{filter_name}"]',
                f'[data-stats-filter="{filter_name}"]'
            ]
            
            for selector in filter_selectors:
                filter_element = await self.page.query_selector(selector)
                if filter_element:
                    await filter_element.click()
                    await self.page.wait_for_timeout(1000)
                    
                    # Verify filter is active
                    is_active = await self._verify_filter_active(filter_name)
                    if is_active:
                        self.logger.info(f"Successfully navigated to {filter_name} filter")
                        return True
                    else:
                        self.logger.warning(f"Filter clicked but not active: {filter_name}")
                        continue
            
            self.logger.warning(f"Could not find or navigate to {filter_name} filter")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to {filter_name} filter: {e}")
            return False
    
    async def _verify_filter_active(self, filter_name: str) -> bool:
        """Verify that specified filter is currently active."""
        try:
            active_selectors = [
                f'.statsFilter[data-filter="{filter_name}"].active',
                f'.filter__item[data-name="{filter_name}"].selected',
                f'.stats__filter[href*="{filter_name}"].active',
                f'[data-stats-filter="{filter_name}"].active'
            ]
            
            for selector in active_selectors:
                active_element = await self.page.query_selector(selector)
                if active_element:
                    return True
            
            # Fallback: check if filter content is visible
            content_selectors = [
                f'.statsContent[data-filter="{filter_name}"]',
                f'.{filter_name}__content',
                f'[data-content="{filter_name}"]'
            ]
            
            for selector in content_selectors:
                content_element = await self.page.query_selector(selector)
                if content_element:
                    # Check if element is visible
                    is_visible = await content_element.is_visible()
                    if is_visible:
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying filter active status for {filter_name}: {e}")
            return False
    
    async def wait_for_filter_content(self, filter_name: str, timeout: int = 3000) -> bool:
        """
        Wait for filter content to load.
        
        Args:
            filter_name: Name of filter
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if content loaded, False otherwise
        """
        try:
            content_selectors = [
                f'.statsContent[data-filter="{filter_name}"]',
                f'.{filter_name}__content',
                f'[data-content="{filter_name}"]'
            ]
            
            for selector in content_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=timeout)
                    return True
                except:
                    continue
            
            self.logger.warning(f"Filter content did not load for {filter_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for {filter_name} filter content: {e}")
            return False
    
    async def extract_filter_data(self, filter_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from a specific statistical filter.
        
        Args:
            filter_name: Name of filter to extract data from
            
        Returns:
            Extracted data dictionary or None if extraction fails
        """
        try:
            # Navigate to filter
            if not await self.navigate_to_filter(filter_name):
                return None
            
            # Wait for content to load
            if not await self.wait_for_filter_content(filter_name):
                return None
            
            # Extract data based on filter type
            if filter_name == 'inc_ot':
                return await self._extract_inc_ot_data()
            elif filter_name == 'ft':
                return await self._extract_ft_data()
            elif filter_name == 'q1':
                return await self._extract_q1_data()
            else:
                self.logger.warning(f"Unknown filter type: {filter_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting data from {filter_name} filter: {e}")
            return None
    
    @abstractmethod
    async def _extract_inc_ot_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from Inc OT (Including Overtime) filter."""
        pass
    
    @abstractmethod
    async def _extract_ft_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from FT (Full Time) filter."""
        pass
    
    @abstractmethod
    async def _extract_q1_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from Q1 (First Quarter) filter."""
        pass
    
    async def validate_filter_data(self, filter_name: str, data: Dict[str, Any]) -> bool:
        """
        Validate extracted filter data structure.
        
        Args:
            filter_name: Name of filter
            data: Extracted data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if not data or not isinstance(data, dict):
                return False
            
            # Basic validation for each filter type
            if filter_name == 'inc_ot':
                required_fields = ['overtime_stats', 'including_ot_totals']
                return all(field in data for field in required_fields)
            elif filter_name == 'ft':
                required_fields = ['full_time_stats', 'match_totals']
                return all(field in data for field in required_fields)
            elif filter_name == 'q1':
                required_fields = ['first_quarter_stats', 'q1_breakdown']
                return all(field in data for field in required_fields)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating {filter_name} filter data: {e}")
            return False
    
    async def extract_all_tertiary_data(self, page_state: PageState) -> Optional[TertiaryData]:
        """
        Extract data from all available tertiary filters.
        
        Args:
            page_state: Current page state with match information
            
        Returns:
            TertiaryData object with all extracted data, or None if extraction fails
        """
        try:
            # Check which tertiary filters are available
            available_filters = await self._detect_available_filters()
            
            inc_ot_data = None
            ft_data = None
            q1_data = None
            
            # Extract data from available filters
            if 'inc_ot' in available_filters:
                inc_ot_data = await self.extract_filter_data('inc_ot')
                if inc_ot_data and not self.validate_filter_data('inc_ot', inc_ot_data):
                    inc_ot_data = None
                    self.logger.warning("Inc OT data validation failed")
            
            if 'ft' in available_filters:
                ft_data = await self.extract_filter_data('ft')
                if ft_data and not self.validate_filter_data('ft', ft_data):
                    ft_data = None
                    self.logger.warning("FT data validation failed")
            
            if 'q1' in available_filters:
                q1_data = await self.extract_filter_data('q1')
                if q1_data and not self.validate_filter_data('q1', q1_data):
                    q1_data = None
                    self.logger.warning("Q1 data validation failed")
            
            return TertiaryData(
                inc_ot=inc_ot_data,
                ft=ft_data,
                q1=q1_data
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting all tertiary data: {e}")
            return None
    
    async def _detect_available_filters(self) -> List[str]:
        """Detect which tertiary filters are available on the current page."""
        try:
            available_filters = []
            
            # Check for filter container
            filter_container = await self.page.query_selector('.statsFilters, .filterContainer')
            if not filter_container:
                return available_filters
            
            # Check for each filter type
            filter_checks = [
                ('inc_ot', [
                    '.statsFilter[data-filter="inc_ot"]',
                    '.filter__item[data-name="inc_ot"]',
                    '[data-stats-filter="inc_ot"]'
                ]),
                ('ft', [
                    '.statsFilter[data-filter="ft"]',
                    '.filter__item[data-name="ft"]',
                    '[data-stats-filter="ft"]'
                ]),
                ('q1', [
                    '.statsFilter[data-filter="q1"]',
                    '.filter__item[data-name="q1"]',
                    '[data-stats-filter="q1"]'
                ])
            ]
            
            for filter_name, selectors in filter_checks:
                for selector in selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        available_filters.append(filter_name)
                        break
            
            self.logger.info(f"Available tertiary filters: {available_filters}")
            return available_filters
            
        except Exception as e:
            self.logger.error(f"Error detecting available filters: {e}")
            return []
