"""
Base extractor interface for Flashscore match data extraction.

ALL selectors are YAML-driven via the selector engine. Zero hardcoded CSS strings.
Each selector lives in its own YAML file under src/sites/flashscore/selectors/extraction/
with ordered fallback chains: data-testid → obfuscated class → partial class → xpath.

When FlashScore rotates CSS hashes, only the YAML entries need updating.
No Python code changes required.
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
    """Base class for all match extractors — 100% YAML-driven selectors."""

    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self._selector_engine = getattr(scraper, 'selector_engine', None)

    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.extractor.{self.__class__.__name__.lower()}")

    # ------------------------------------------------------------------
    # YAML-driven selector resolution helpers
    # ------------------------------------------------------------------

    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element via YAML selector engine.

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.  Falls
                back to ``self.scraper.page`` when *None*.

        Returns:
            A Playwright ``ElementHandle`` or ``None``.
        """
        if self._selector_engine:
            try:
                search_target = parent or self.scraper.page
                return await self._selector_engine.find(search_target, selector_name)
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return None

    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve multiple elements via YAML selector engine.

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.

        Returns:
            A list of Playwright ``ElementHandle`` objects (may be empty).
        """
        if self._selector_engine:
            try:
                search_target = parent or self.scraper.page
                elements = await self._selector_engine.find_all(search_target, selector_name)
                if elements:
                    return elements
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
                return None

            # Extract team names
            home_team, away_team = await self._extract_teams(element)
            if not home_team or not away_team:
                self.logger.warning(f"Could not extract team names: home={home_team}, away={away_team}")
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
            return None

    async def _extract_match_id(self, element: ElementHandle) -> Optional[str]:
        """Extract match ID using two methods: URL parameter (primary) and aria-describedby (fallback)."""
        try:
            # Method 1: Extract from URL parameter ?mid=CSXgyReU (primary)
            link_element = await self._resolve_element('event_row_link', parent=element)
            if link_element:
                href = await link_element.get_attribute('href')
                if href:
                    import re
                    mid_match = re.search(r'[?&]mid=([^&]+)', href)
                    if mid_match:
                        return mid_match.group(1)
        except:
            pass

        # Method 2: Extract from aria-describedby="g_3_CSXgyReU" (fallback)
        try:
            link_element = await self._resolve_element('event_row_link', parent=element)
            if link_element:
                aria_describedby = await link_element.get_attribute('aria-describedby')
                if aria_describedby:
                    import re
                    id_match = re.search(r'g_\d+_(.+)', aria_describedby)
                    if id_match:
                        return id_match.group(1)
        except:
            pass

        return None

    async def _extract_teams(self, element: ElementHandle) -> tuple[Optional[str], Optional[str]]:
        """Extract home and away team names via YAML selectors."""
        # Extract home team
        try:
            home_team = await self._resolve_text('home_team', parent=element)
            if home_team:
                self.logger.info("Home team element found")
            else:
                self.logger.warning("Home team element not found")
        except Exception as e:
            self.logger.error(f"Error extracting home team: {e}")
            home_team = None

        # Extract away team
        try:
            away_team = await self._resolve_text('away_team', parent=element)
            if away_team:
                self.logger.info("Away team element found")
            else:
                self.logger.warning("Away team element not found")
        except Exception as e:
            self.logger.error(f"Error extracting away team: {e}")
            away_team = None

        return home_team, away_team

    async def _extract_scores(self, element: ElementHandle) -> tuple[Optional[str], Optional[str]]:
        """Extract home and away scores via YAML selectors."""
        try:
            score_elements = await self._resolve_elements('match_scores', parent=element)
            if len(score_elements) >= 2:
                home_score = await score_elements[0].text_content()
                away_score = await score_elements[1].text_content()
                return home_score.strip() if home_score else None, away_score.strip() if away_score else None
        except Exception as e:
            self.logger.error(f"Error extracting scores: {e}")

        return None, None

    async def _extract_url(self, element: ElementHandle) -> Optional[str]:
        """Extract match URL via YAML selector."""
        try:
            link_element = await self._resolve_element('event_row_link', parent=element)
            if link_element:
                match_url = await link_element.get_attribute('href')
                if match_url and not match_url.startswith('http'):
                    match_url = f"https://www.flashscore.com{match_url}"
                return match_url
        except Exception as e:
            self.logger.error(f"Error extracting URL: {e}")

        return None

    async def _extract_time_info(self, element: ElementHandle, expected_status: str) -> Optional[str]:
        """Extract time information based on match status via YAML selector."""
        # For scheduled matches, extract time directly from the match element
        if expected_status in ['scheduled', 'finished']:
            try:
                time_text = await self._resolve_text('match_time', parent=element)
                if time_text:
                    self.logger.info(f"Extracted time: '{time_text}' from element")
                    return time_text
            except Exception as e:
                self.logger.error(f"Error extracting time from element: {e}")

        return None
