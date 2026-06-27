"""
Match detail extractor for Flashscore match pages.

Handles extraction of detailed match data from individual match pages
including primary and tertiary tab data.

Interactive operations (tab clicks, navigation, page validation) use
Playwright direct CSS queries. Non-interactive reads may fall back
to the YAML selector engine with 8-second timeout protection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import StructuredMatch, PageState, ExtractionMetadata
from src.sites.flashscore.extractors.selector_mixin import SelectorEngineMixin
from datetime import datetime
import asyncio


class MatchDetailExtractor(SelectorEngineMixin, ABC):
    """Base class for match detail extraction — Playwright-direct for interactive ops, YAML fallback for reads."""

    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self.page = scraper.page
        self._selector_engine = getattr(scraper, 'selector_engine', None)

    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.match_detail_extractor.{self.__class__.__name__.lower()}")

    # ------------------------------------------------------------------
    # YAML-driven selector resolution helpers
    # ------------------------------------------------------------------

    # YAML selector engine methods are provided by SelectorEngineMixin
    # (_resolve_element, _resolve_elements, _resolve_text)

    async def _element_matches(self, element: ElementHandle, selector_name: str) -> bool:
        """Check if an element itself matches the CSS selector from a YAML definition.

        Unlike ``_resolve_elements`` which finds *child* elements within a
        parent, this method checks whether *the element itself* has a CSS
        class or matches a selector. Uses YAML metadata status_class_fragment
        or falls back to Playwright Element.matches().
        """
        try:
            from src.sites.flashscore.extractors.base_extractor import BaseExtractor
            yaml_data = BaseExtractor._load_selector_yaml(selector_name)
            if yaml_data:
                # 1. Try status_class_fragment from YAML metadata (fast path)
                metadata = yaml_data.get('metadata', {})
                fragment = metadata.get('status_class_fragment')
                if fragment:
                    class_name = await element.get_attribute('class')
                    if class_name and fragment in class_name:
                        return True

                # 2. Fallback: use Playwright Element.matches() with each CSS strategy
                for strategy in yaml_data.get('strategies', []):
                    if strategy.get('type') == 'css':
                        css_sel = strategy.get('selector', '')
                        if css_sel:
                            try:
                                escaped = css_sel.replace("'", "\\'")
                                matches = await element.evaluate(f"el => el.matches('{escaped}')")
                                if matches:
                                    return True
                            except Exception:
                                continue
        except Exception as e:
            self.logger.debug(f"Element match check for '{selector_name}' failed: {e}")
        return False

    # ------------------------------------------------------------------
    # Core extraction pipeline
    # ------------------------------------------------------------------

    async def extract(self, page_state: PageState, timeout: int = 10000) -> Optional[StructuredMatch]:
        """
        Extract complete match data from match detail page.

        Args:
            page_state: Current page state with match information
            timeout: Maximum time to wait for extraction in milliseconds

        Returns:
            StructuredMatch object with all extracted data, or None if extraction fails
        """
        start_time = datetime.utcnow()
        retry_count = 0

        try:
            # Validate page structure before extraction
            if not await self._validate_page_structure(page_state):
                self.logger.warning(f"Page structure validation failed for match {page_state.match_id}")
                return None

            # Extract basic match information
            basic_info = await self._extract_basic_info(page_state)
            if not basic_info:
                self.logger.error(f"Failed to extract basic info for match {page_state.match_id}")
                return None

            # Extract data from available tabs
            extracted_tabs = []
            failed_tabs = []

            summary_data = await self._extract_summary_tab(page_state)
            if summary_data:
                extracted_tabs.append('summary')
            else:
                failed_tabs.append('summary')

            h2h_data = await self._extract_h2h_tab(page_state)
            if h2h_data:
                extracted_tabs.append('h2h')
            else:
                failed_tabs.append('h2h')

            odds_data = await self._extract_odds_tab(page_state)
            if odds_data:
                extracted_tabs.append('odds')
            else:
                failed_tabs.append('odds')

            stats_data = await self._extract_stats_tab(page_state)
            if stats_data:
                extracted_tabs.append('stats')
            else:
                failed_tabs.append('stats')

            # Extract tertiary tabs
            tertiary_data = await self._extract_tertiary_tabs(page_state)
            if tertiary_data and (tertiary_data.inc_ot or tertiary_data.ft or tertiary_data.q1):
                extracted_tabs.append('tertiary')
            else:
                failed_tabs.append('tertiary')

            # Calculate completeness score
            total_expected_tabs = len(['summary', 'h2h', 'odds', 'stats', 'tertiary'])
            completeness_score = len(extracted_tabs) / total_expected_tabs

            # Create extraction metadata
            extraction_duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            extraction_metadata = ExtractionMetadata(
                tabs_extracted=extracted_tabs,
                failed_tabs=failed_tabs,
                extraction_duration_ms=extraction_duration,
                retry_count=retry_count
            )

            # Create structured match
            structured_match = StructuredMatch(
                match_id=page_state.match_id,
                metadata=self._create_match_metadata(page_state, completeness_score),
                basic_info=basic_info,
                summary_tab=summary_data,
                h2h_tab=h2h_data,
                odds_tab=odds_data,
                stats_tab=stats_data,
                tertiary_tabs=tertiary_data,
                extraction_metadata=extraction_metadata
            )

            # Log performance metrics
            self.logger.info(f"Match {page_state.match_id} extraction completed in {extraction_duration}ms "
                           f"({completeness_score:.1%} completeness, {len(extracted_tabs)}/{total_expected_tabs} tabs)")

            return structured_match

        except Exception as e:
            self.logger.error(f"Error extracting match data for {page_state.match_id}: {e}")
            return None

    async def _validate_page_structure(self, page_state: PageState) -> bool:
        """Validate that the match detail page has the expected structure.
        
        Uses Playwright direct queries first (fast, reliable), then falls back
        to YAML selector engine.
        """
        try:
            if not page_state or not hasattr(page_state, 'verified') or not page_state.verified:
                return False

            # Strategy 1: Playwright direct — check for match-specific elements
            # that are always present on a FlashScore match detail page
            direct_selectors = [
                '[data-testid="match-status"]',
                '.detailScore__status',
                '.duelParticipant__startTime',
                '.tournamentHeader__content',
            ]
            for selector in direct_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        self.logger.debug(f"Match detail page validated via Playwright selector: {selector}")
                        return True
                except Exception:
                    continue

            # Strategy 2: YAML selector engine (fallback)
            match_content = await self._resolve_element('match_detail_validation')
            if match_content:
                self.logger.debug("Match detail page validated via YAML selector")
                return True

            # Strategy 3: URL-based check — if URL contains /match/ and has mid= param,
            # we're probably on a match detail page even if no elements loaded yet
            current_url = self.page.url
            if '/match/' in current_url and 'mid=' in current_url:
                self.logger.debug("Match detail page validated via URL pattern")
                return True

            self.logger.warning("No match-specific content found on page")
            return False

        except Exception as e:
            self.logger.error(f"Error validating page structure: {e}")
            return False

    async def _extract_basic_info(self, page_state: PageState) -> Optional[Any]:
        """Extract basic match information from the page.
        
        Uses Playwright direct queries first, then falls back to YAML selector engine.
        """
        try:
            from src.sites.flashscore.models import BasicMatchInfo
            
            # Try Playwright direct queries for team names and score
            home_team = "Unknown"
            away_team = "Unknown"
            current_score = None
            match_time = "Unknown"
            status = "Unknown"
            competition = None
            
            # Home team — try direct CSS selectors used on FlashScore
            for sel in ['.event__participant--home', '.participant__home', '[data-testid="home-team"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            home_team = text
                            break
                except Exception:
                    continue
            
            # Away team
            for sel in ['.event__participant--away', '.participant__away', '[data-testid="away-team"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            away_team = text
                            break
                except Exception:
                    continue
            
            # Score
            try:
                score_els = await self.page.query_selector_all('.event__score')
                if len(score_els) >= 2:
                    home = (await score_els[0].text_content()).strip()
                    away = (await score_els[1].text_content()).strip()
                    current_score = f"{home}-{away}"
            except Exception:
                pass
            
            # Match time
            for sel in ['.duelParticipant__startTime', '.event__time', '[data-testid="match-time"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            match_time = text
                            break
                except Exception:
                    continue
            
            # Status
            for sel in ['.detailScore__status', '[data-testid="match-status"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            status = text
                            break
                except Exception:
                    continue
            
            # Competition
            for sel in ['.tournamentHeader__content', '[data-testid="tournament-name"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            competition = text
                            break
                except Exception:
                    continue
            
            return BasicMatchInfo(
                home_team=home_team,
                away_team=away_team,
                current_score=current_score,
                match_time=match_time,
                status=status,
                competition=competition,
                league=competition,
            )
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {e}")
            return None

    @abstractmethod
    async def _extract_summary_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from SUMMARY tab."""
        pass

    @abstractmethod
    async def _extract_h2h_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from H2H tab."""
        pass

    @abstractmethod
    async def _extract_odds_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from ODDS tab."""
        pass

    @abstractmethod
    async def _extract_stats_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from STATS tab."""
        pass

    @abstractmethod
    async def _extract_tertiary_tabs(self, page_state: PageState) -> Optional[Any]:
        """Extract data from tertiary tabs."""
        pass

    def _create_match_metadata(self, page_state: PageState, completeness_score: float) -> Any:
        """Create match metadata object."""
        from src.sites.flashscore.models import MatchMetadata
        return MatchMetadata(
            extraction_time=datetime.utcnow(),
            source_url=page_state.url,
            sport="basketball",
            completeness_score=completeness_score
        )
