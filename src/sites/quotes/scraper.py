"""
quotes Site Template

This module provides the main scraper implementation for quotes.toscrape.com.
Generated with `template create`, then implemented against the Site Template
Integration Framework: selectors live in selectors/*.yaml and are resolved
through the framework selector engine — no hardcoded selectors here.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from src.sites.base.template import BaseSiteTemplate
from src.sites.base.template.selector_loader import FileSystemSelectorLoader
from src.sites.quotes.flow import MainFlow

logger = logging.getLogger(__name__)


class QuotesScraper(BaseSiteTemplate):
    """
    Main scraper for quotes.toscrape.com.

    Actions:
        scrape_quotes(max_pages=1): scrape quote text/author/tags across pages.
    """

    def __init__(self, page, selector_engine):
        """
        Initialize quotes scraper.

        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
        """
        super().__init__(
            name="quotes",
            version="1.0.0",
            description="Quotes to Scrape — template framework proof-of-life",
            author="Tisone Kironget",
            framework_version="1.0.0",
            site_domain="quotes.toscrape.com"
        )

        self.capabilities = [
            "quote_extraction",
            "pagination",
        ]
        self.supported_domains = ["quotes.toscrape.com"]
        self.dependencies = ["selector_engine"]

        self.selector_loader = None
        self.flow = None

        # initialize(page, selector_engine) wires these in
        self.page = page
        self.selector_engine = selector_engine

        logger.info(f"QuotesScraper initialized for {self.site_domain}")

    async def _setup_template_specific(self) -> bool:
        """Load this template's YAML selectors into the engine and build flows."""
        self.selector_loader = FileSystemSelectorLoader(
            template_name=self.name,
            selector_engine=self.selector_engine,
            selectors_directory=Path(__file__).parent / "selectors",
        )
        if not await self.selector_loader.load_site_selectors(self.name):
            logger.error("Failed to load quotes selectors")
            return False

        self.flow = MainFlow(self.page, self.selector_engine)
        return True

    async def _validate_scrape_params(self, action: str = "scrape_quotes", **kwargs) -> bool:
        if action != "scrape_quotes":
            logger.error(f"Unknown action: {action}")
            return False
        max_pages = kwargs.get("max_pages", 1)
        return isinstance(max_pages, int) and max_pages >= 1

    async def _execute_scrape_logic(self, action: str = "scrape_quotes", **kwargs) -> Dict[str, Any]:
        """
        Execute scraping logic for quotes.

        Args:
            action: Action to perform
            **kwargs: Additional parameters (max_pages)

        Returns:
            Dict[str, Any]: Scrape results
        """
        if action == "scrape_quotes":
            return await self._scrape_quotes(**kwargs)
        raise ValueError(f"Unknown action: {action}")

    async def _scrape_quotes(self, max_pages: int = 1, **kwargs) -> Dict[str, Any]:
        """
        Scrape quotes (text, author, tags) across up to max_pages pages.
        """
        if not await self.flow.navigate_to_start():
            raise RuntimeError("Failed to navigate to quotes start page")

        quotes: List[Dict[str, Any]] = []
        pages_scraped = 0

        while True:
            page_quotes = await self._extract_quotes_on_page()
            quotes.extend(page_quotes)
            pages_scraped += 1
            logger.info(f"Extracted {len(page_quotes)} quotes from page {pages_scraped}")

            if pages_scraped >= max_pages:
                break
            if not await self.flow.goto_next_page():
                break

        return {
            "action": "scrape_quotes",
            "url": self.page.url,
            "pages_scraped": pages_scraped,
            "quote_count": len(quotes),
            "quotes": quotes,
        }

    async def _extract_quotes_on_page(self) -> List[Dict[str, Any]]:
        """Extract all quote blocks on the current page via the selector engine."""
        quotes = []
        blocks = await self.selector_engine.find_all(self.page, "quote_block")

        for block in blocks:
            text_els = await self.selector_engine.find_all(block, "quote_text")
            author_els = await self.selector_engine.find_all(block, "quote_author")
            tag_els = await self.selector_engine.find_all(block, "quote_tag")

            text = await text_els[0].text_content() if text_els else None
            author = await author_els[0].text_content() if author_els else None
            tags = [
                (await tag_el.text_content() or "").strip()
                for tag_el in tag_els
            ]

            quotes.append({
                "text": text.strip() if text else None,
                "author": author.strip() if author else None,
                "tags": tags,
            })

        return quotes
