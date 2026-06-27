"""
Base extractor interface for Flashscore match data extraction.

Interactive operations use Playwright direct CSS queries because the YAML
selector engine has an internal retry loop that swallows CancelledError,
making asyncio.wait_for timeouts ineffective. Non-interactive reads may
still fall back to the YAML selector engine with 8-second timeout protection.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from playwright.async_api import ElementHandle

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import MatchListing

# Module-level cache shared across all BaseExtractor instances
_yaml_data_cache: Dict[str, Dict[str, Any]] = {}


class BaseExtractor(ABC):
    """Base class for all match extractors — Playwright-direct for interactive ops, YAML fallback for reads."""

    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self._selector_engine = getattr(scraper, 'selector_engine', None)

    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.extractor.{self.__class__.__name__.lower()}")

    # ------------------------------------------------------------------
    # Snapshot capture for debugging
    # ------------------------------------------------------------------

    async def _capture_failure_snapshot(self, reason: str, metadata: dict = None):
        """Capture a snapshot when extraction fails.

        Delegates to the scraper's capture_operation_snapshot so that
        every failure point automatically produces HTML + screenshot
        evidence for post-mortem debugging.
        """
        try:
            full_meta = {'reason': reason, 'extractor': self.__class__.__name__}
            if metadata:
                full_meta.update(metadata)
            await self.scraper.capture_operation_snapshot(
                f"extraction_failure_{reason}", full_meta
            )
        except Exception as e:
            self.logger.error(f"Failed to capture failure snapshot: {e}")

    # ------------------------------------------------------------------
    # YAML-driven selector resolution helpers
    # ------------------------------------------------------------------

    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element via YAML selector engine with 8-second timeout protection.

        Uses a separate asyncio.Task so that we can force-cancel if the
        selector engine enters an infinite retry loop (it catches
        CancelledError internally, making plain asyncio.wait_for ineffective).

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.  Falls
                back to ``self.scraper.page`` when *None*.

        Returns:
            A Playwright ``ElementHandle`` or ``None``.
        """
        import asyncio
        if self._selector_engine:
            try:
                search_target = parent or self.scraper.page
                task = asyncio.create_task(
                    self._selector_engine.find(search_target, selector_name)
                )
                try:
                    return await asyncio.wait_for(task, timeout=8.0)
                except asyncio.TimeoutError:
                    self.logger.debug(f"YAML selector '{selector_name}' timed out after 8s — force cancelling")
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
                    return None
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return None

    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve multiple elements via YAML selector engine with 8-second timeout protection.

        Uses a separate asyncio.Task so that we can force-cancel if the
        selector engine enters an infinite retry loop.

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.

        Returns:
            A list of Playwright ``ElementHandle`` objects (may be empty).
        """
        import asyncio
        if self._selector_engine:
            try:
                search_target = parent or self.scraper.page
                task = asyncio.create_task(
                    self._selector_engine.find_all(search_target, selector_name)
                )
                try:
                    elements = await asyncio.wait_for(task, timeout=8.0)
                    if elements:
                        return elements
                except asyncio.TimeoutError:
                    self.logger.debug(f"YAML selector '{selector_name}' timed out after 8s — force cancelling")
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
                    return []
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return []

    async def _resolve_text(self, selector_name: str, parent=None) -> Optional[str]:
        """Resolve element text content via YAML selector engine.

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.

        Returns:
            Trimmed text content string or ``None``.
        """
        el = await self._resolve_element(selector_name, parent)
        if el:
            try:
                text = await el.text_content()
                return text.strip() if text else None
            except Exception as e:
                self.logger.debug(f"Text extraction for '{selector_name}' failed: {e}")
        return None

    async def _element_matches(self, element: ElementHandle, selector_name: str) -> bool:
        """Check if an element itself matches the CSS selector from a YAML definition.

        Unlike ``_resolve_elements`` which finds *child* elements within a
        parent, this method checks whether *the element itself* has a CSS
        class or matches a selector — e.g. ``event__match--scheduled`` on a
        match row element.

        The primary CSS selector string is loaded from the YAML file that
        carries the given ``selector_name`` as its ``id``.  FlashScore CSS
        hash rotations only require updating the YAML — no Python changes.

        Args:
            element: Playwright element handle to test.
            selector_name: The ``id`` of a YAML selector definition.

        Returns:
            ``True`` if the element matches any CSS strategy in the YAML file.
        """
        try:
            # 1. Try status_class_fragment from YAML metadata (fast path)
            yaml_data = self._load_selector_yaml(selector_name)
            if yaml_data:
                metadata = yaml_data.get('metadata', {})
                fragment = metadata.get('status_class_fragment')
                if fragment:
                    class_name = await element.get_attribute('class')
                    if class_name and fragment in class_name:
                        self.logger.debug(f"Element matches status class fragment '{fragment}' from YAML '{selector_name}'")
                        return True

                # 2. Fallback: use Playwright Element.matches() with each CSS strategy
                for strategy in yaml_data.get('strategies', []):
                    if strategy.get('type') == 'css':
                        css_sel = strategy.get('selector', '')
                        if css_sel:
                            try:
                                # Escape single quotes for safe JS evaluation
                                escaped = css_sel.replace("'", "\\'")
                                matches = await element.evaluate(f"el => el.matches('{escaped}')")
                                if matches:
                                    self.logger.debug(f"Element matches CSS '{css_sel}' from YAML '{selector_name}'")
                                    return True
                            except Exception:
                                continue
        except Exception as e:
            self.logger.debug(f"Element match check for '{selector_name}' failed: {e}")
        return False

    @staticmethod
    def _load_selector_yaml(selector_name: str) -> Optional[Dict[str, Any]]:
        """Load a YAML selector definition by ``id`` with module-level caching.

        Scans ``src/sites/flashscore/selectors/extraction/`` for a YAML
        file whose ``id`` field matches *selector_name*.

        Returns:
            Parsed YAML dictionary or ``None`` if not found.
        """
        global _yaml_data_cache
        if selector_name in _yaml_data_cache:
            return _yaml_data_cache[selector_name]

        import yaml

        selectors_base = Path("src/sites/flashscore/selectors/extraction")
        if not selectors_base.exists():
            return None

        for yaml_file in selectors_base.rglob(f"{selector_name}.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if data and data.get('id') == selector_name:
                    _yaml_data_cache[selector_name] = data
                    return data
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def extract_matches(self, sport_config: dict, limit: Optional[int] = None) -> Dict[str, Any]:
        """Extract matches for this extractor type."""
        pass

    @abstractmethod
    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element has the correct status for this extractor."""
        pass

    # ------------------------------------------------------------------
    # Common extraction methods (YAML-driven)
    # ------------------------------------------------------------------

    async def extract_match_data(self, element: ElementHandle, expected_status: str) -> Optional[MatchListing]:
        """Extract data from a single match element."""
        try:
            # Extract basic match information
            match_id = await self._extract_match_id(element)
            if not match_id:
                self.logger.warning(f"Could not extract match ID from element")
                await self._capture_failure_snapshot('match_id_missing')
                return None

            # Extract team names
            home_team, away_team = await self._extract_teams(element)
            if not home_team or not away_team:
                self.logger.warning(f"Could not extract team names: home={home_team}, away={away_team}")
                await self._capture_failure_snapshot('teams_missing', {'home': home_team, 'away': away_team})
                return None

            # Extract scores
            home_score, away_score = await self._extract_scores(element)
            score = f"{home_score}-{away_score}" if home_score and away_score else None

            # Extract time/stage based on status
            time_info = await self._extract_time_info(element, expected_status)

            # Build match listing
            match_listing = MatchListing(
                match_id=match_id,
                teams={'home': home_team, 'away': away_team},
                time=time_info or '',
                status=expected_status,
                score=score
            )

            self.logger.info(f"Successfully extracted match listing: {home_team} vs {away_team}")
            return match_listing

        except Exception as e:
            self.logger.error(f"Error extracting match data: {e}")
            await self._capture_failure_snapshot('match_data_error', {'error': str(e)})
            return None

    async def _extract_match_id(self, element: ElementHandle) -> Optional[str]:
        """Extract match ID from a match element using Playwright queries."""
        try:
            # Method 1: Find link element and extract mid= from href
            link = await element.query_selector('a[href*="mid="]')
            if link:
                href = await link.get_attribute('href')
                if href:
                    import re
                    mid_match = re.search(r'[?&]mid=([^&]+)', href)
                    if mid_match:
                        return mid_match.group(1)
        except Exception:
            pass

        # Method 2: Extract from aria-describedby attribute
        try:
            link = await element.query_selector('a[aria-describedby]')
            if link:
                aria = await link.get_attribute('aria-describedby')
                if aria:
                    import re
                    id_match = re.search(r'g_\d+_(.+)', aria)
                    if id_match:
                        return id_match.group(1)
        except Exception:
            pass

        # Method 3: Extract from the element's own id attribute
        try:
            el_id = await element.get_attribute('id')
            if el_id:
                return el_id
        except Exception:
            pass

        return None

    async def _extract_teams(self, element: ElementHandle) -> tuple[Optional[str], Optional[str]]:
        """Extract home and away team names using Playwright queries."""
        home_team = None
        away_team = None

        # Extract home team
        try:
            home_el = await element.query_selector('.event__participant--home, .participant__home')
            if home_el:
                text = await home_el.text_content()
                home_team = text.strip() if text else None
        except Exception as e:
            self.logger.debug(f"Home team extraction failed: {e}")

        # Extract away team
        try:
            away_el = await element.query_selector('.event__participant--away, .participant__away')
            if away_el:
                text = await away_el.text_content()
                away_team = text.strip() if text else None
        except Exception as e:
            self.logger.debug(f"Away team extraction failed: {e}")

        return home_team, away_team

    async def _extract_scores(self, element: ElementHandle) -> tuple[Optional[str], Optional[str]]:
        """Extract home and away scores using Playwright queries."""
        try:
            score_els = await element.query_selector_all('.event__score')
            if len(score_els) >= 2:
                home = await score_els[0].text_content()
                away = await score_els[1].text_content()
                return (home.strip() if home else None), (away.strip() if away else None)
        except Exception as e:
            self.logger.debug(f"Score extraction failed: {e}")
        return None, None

    async def _extract_url(self, element: ElementHandle) -> Optional[str]:
        """Extract match URL using Playwright query."""
        try:
            link = await element.query_selector('a[href]')
            if link:
                match_url = await link.get_attribute('href')
                if match_url and not match_url.startswith('http'):
                    match_url = f"https://www.flashscore.com{match_url}"
                return match_url
        except Exception as e:
            self.logger.debug(f"URL extraction failed: {e}")
        return None

    async def _extract_time_info(self, element: ElementHandle, expected_status: str) -> Optional[str]:
        """Extract time information based on match status using Playwright query."""
        if expected_status in ['scheduled', 'finished']:
            try:
                time_el = await element.query_selector('.event__time')
                if time_el:
                    text = await time_el.text_content()
                    return text.strip() if text else None
            except Exception as e:
                self.logger.debug(f"Time extraction failed: {e}")
        return None
