"""
Primary tab extractor for Flashscore match detail pages.

Handles extraction from primary tabs: SUMMARY, H2H, ODDS, STATS.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import PageState, SummaryData, H2HData, OddsData, StatsData
from datetime import datetime


class PrimaryTabExtractor(ABC):
    """Base class for primary tab extraction from match detail pages."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self.page = scraper.page
    
    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.primary_tab_extractor.{self.__class__.__name__.lower()}")
    
    async def navigate_to_tab(self, tab_name: str) -> bool:
        """
        Navigate to a specific primary tab.
        
        Args:
            tab_name: Name of the tab to navigate to (summary, h2h, odds, stats)
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Try multiple selector patterns for tab navigation
            tab_selectors = [
                f'.tab__title[data-tab-name="{tab_name}"]',
                f'.tab__title[href*="#/{tab_name}"]',
                f'.tabs__detail .tab[href*="{tab_name}"]',
                f'[data-tab="{tab_name}"]'
            ]
            
            for selector in tab_selectors:
                tab_element = await self.page.query_selector(selector)
                if tab_element:
                    await tab_element.click()
                    await self.page.wait_for_timeout(1000)
                    
                    # Verify tab is active
                    is_active = await self._verify_tab_active(tab_name)
                    if is_active:
                        self.logger.info(f"Successfully navigated to {tab_name} tab")
                        return True
                    else:
                        self.logger.warning(f"Tab clicked but not active: {tab_name}")
                        continue
            
            self.logger.warning(f"Could not find or navigate to {tab_name} tab")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to {tab_name} tab: {e}")
            return False
    
    async def _verify_tab_active(self, tab_name: str) -> bool:
        """Verify that the specified tab is currently active."""
        try:
            active_selectors = [
                f'.tab__title[data-tab-name="{tab_name}"].active',
                f'.tab__title[data-tab-name="{tab_name}"].selected',
                f'.tab__title[href*="#/{tab_name}"].active',
                f'[data-tab="{tab_name}"].active'
            ]
            
            for selector in active_selectors:
                active_element = await self.page.query_selector(selector)
                if active_element:
                    return True
            
            # Fallback: check if tab content is visible
            content_selectors = [
                f'.tab__content[data-tab="{tab_name}"]',
                f'.{tab_name}__content',
                f'[data-content="{tab_name}"]'
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
            self.logger.error(f"Error verifying tab active status for {tab_name}: {e}")
            return False
    
    async def wait_for_tab_content(self, tab_name: str, timeout: int = 5000) -> bool:
        """
        Wait for tab content to load.
        
        Args:
            tab_name: Name of the tab
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if content loaded, False otherwise
        """
        try:
            content_selectors = [
                f'.tab__content[data-tab="{tab_name}"]',
                f'.{tab_name}__content',
                f'[data-content="{tab_name}"]'
            ]
            
            for selector in content_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=timeout)
                    return True
                except:
                    continue
            
            self.logger.warning(f"Tab content did not load for {tab_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for {tab_name} tab content: {e}")
            return False
    
    async def extract_tab_data(self, tab_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from a specific tab with efficient switching.
        
        Args:
            tab_name: Name of tab to extract data from
            
        Returns:
            Extracted data dictionary or None if extraction fails
        """
        try:
            # Check if we're already on the correct tab to avoid unnecessary navigation
            current_tab = await self._get_current_active_tab()
            if current_tab == tab_name:
                self.logger.info(f"Already on {tab_name} tab, skipping navigation")
                return await self._extract_current_tab_data(tab_name)
            
            # Navigate to tab
            if not await self.navigate_to_tab(tab_name):
                return None
            
            # Wait for content to load
            if not await self.wait_for_tab_content(tab_name):
                return None
            
            # Extract data based on tab type
            return await self._extract_current_tab_data(tab_name)
                
        except Exception as e:
            self.logger.error(f"Error extracting data from {tab_name} tab: {e}")
            return None
    
    async def _get_current_active_tab(self) -> Optional[str]:
        """Get the currently active tab name."""
        try:
            # Check for active tab indicators
            active_selectors = [
                '.tab__title.active',
                '.tab__title.selected',
                '.tab__title[data-active="true"]'
            ]
            
            for selector in active_selectors:
                active_element = await self.page.query_selector(selector)
                if active_element:
                    tab_name = await active_element.get_attribute('data-tab-name')
                    if tab_name:
                        return tab_name
                    
                    # Fallback: get text content
                    tab_text = await active_element.text_content()
                    if tab_text:
                        return tab_text.strip().lower()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting current active tab: {e}")
            return None
    
    async def _extract_current_tab_data(self, tab_name: str) -> Optional[Dict[str, Any]]:
        """Extract data from the currently active tab without navigation."""
        try:
            # Extract data based on tab type (same logic as before but without navigation)
            if tab_name == 'summary':
                return await self._extract_summary_data()
            elif tab_name == 'h2h':
                return await self._extract_h2h_data()
            elif tab_name == 'odds':
                return await self._extract_odds_data()
            elif tab_name == 'stats':
                return await self._extract_stats_data()
            else:
                self.logger.warning(f"Unknown tab type: {tab_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting current tab data for {tab_name}: {e}")
            return None
    
    @abstractmethod
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab."""
        pass
    
    @abstractmethod
    async def _extract_h2h_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from H2H tab."""
        pass
    
    @abstractmethod
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab."""
        pass
    
    @abstractmethod
    async def _extract_stats_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from STATS tab."""
        pass
    
    async def validate_tab_data(self, tab_name: str, data: Dict[str, Any]) -> bool:
        """
        Validate extracted tab data structure.
        
        Args:
            tab_name: Name of the tab
            data: Extracted data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if not data or not isinstance(data, dict):
                return False
            
            # Basic validation for each tab type
            if tab_name == 'summary':
                required_fields = ['overview', 'teams']
                return all(field in data for field in required_fields)
            elif tab_name == 'h2h':
                required_fields = ['previous_matches']
                return all(field in data for field in required_fields)
            elif tab_name == 'odds':
                required_fields = ['betting_odds']
                return all(field in data for field in required_fields)
            elif tab_name == 'stats':
                required_fields = ['statistics']
                return all(field in data for field in required_fields)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating {tab_name} tab data: {e}")
            return False
