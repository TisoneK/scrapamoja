"""
Flow implementation for quotes template.

This module provides navigation flows for quotes.toscrape.com.
Flows handle navigation and interaction only — extraction lives in the
scraper, selectors live in selectors/*.yaml.
"""

import logging
from typing import Dict, Any

from src.sites.base.flow import BaseFlow
from src.sites.quotes.config import SITE_CONFIG

logger = logging.getLogger(__name__)


class MainFlow(BaseFlow):
    """
    Main navigation flow for quotes.toscrape.com.
    """

    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.flow_name = "main_flow"
        self.description = "Main navigation flow for quotes"

    async def navigate_to_start(self) -> bool:
        """
        Navigate to the first page of quotes.

        Returns:
            bool: True if navigation succeeded
        """
        try:
            base_url = SITE_CONFIG["base_url"]
            logger.info(f"Navigating to {base_url}")
            await self.page.goto(base_url, wait_until="domcontentloaded")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to start page: {e}")
            return False

    async def goto_next_page(self) -> bool:
        """
        Follow the pagination link to the next page of quotes.

        Returns:
            bool: True if a next page existed and was navigated to
        """
        try:
            next_link = await self.selector_engine.find(self.page, "next_page_link")
            if not next_link:
                logger.info("No next page link found — last page reached")
                return False

            href = await next_link.get_attribute("href")
            if not href:
                return False

            async with self.page.expect_navigation(wait_until="domcontentloaded"):
                await next_link.click()
            logger.info(f"Navigated to next page: {href}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to next page: {e}")
            return False

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the main flow: navigate to the start page.

        Returns:
            Dict[str, Any]: Flow execution results
        """
        success = await self.navigate_to_start()
        return {
            "flow": self.flow_name,
            "success": success,
            "url": self.page.url if success else None,
        }
