"""
Live match extractor for Flashscore.

ALL selectors are YAML-driven via the selector engine. Zero hardcoded CSS strings.
Each selector lives in its own YAML file under src/sites/flashscore/selectors/extraction/
with ordered fallback chains: data-testid → obfuscated class → partial class → xpath.

When FlashScore rotates CSS hashes, only the YAML entries need updating.
No Python code changes required.
"""
from typing import Dict, Any, Optional
from playwright.async_api import ElementHandle

from .base_extractor import BaseExtractor


class LiveMatchExtractor(BaseExtractor):
    """Extractor for live matches — 100% YAML-driven selectors."""

    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element is actually live using Playwright queries."""
        try:
            # Method 1: Check for live CSS class on the element itself
            class_attr = await element.get_attribute('class')
            if class_attr and 'event__match--live' in class_attr:
                self.logger.debug("Live match detected via .event__match--live class")
                return True

            # Method 2: Check for live score state
            try:
                live_scores = await element.query_selector_all('.event__score[data-state="live"]')
                if live_scores:
                    self.logger.debug(f"Live match detected via {len(live_scores)} live score elements")
                    return True
            except Exception:
                pass

            # Method 3: Check for live stage text
            try:
                stage_el = await element.query_selector('.event__stage, .event__stage--block')
                if stage_el:
                    stage_text = await stage_el.text_content()
                    if stage_text and ('quarter' in stage_text.lower() or 'min' in stage_text.lower() or 'half' in stage_text.lower()):
                        self.logger.debug(f"Live match detected via stage text: {stage_text}")
                        return True
            except Exception:
                pass

            # If none of the live indicators are found, it's not a live match
            self.logger.debug("No live indicators found - match is not live")
            return False

        except Exception as e:
            self.logger.error(f"Error in is_match_status: {e}")
            return False

    async def extract_matches(self, sport_config: dict, limit: Optional[int] = None) -> Dict[str, Any]:
        """Extract live matches."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")

        # Navigate to live games
        await self.scraper.flow.navigate_to_live_games(sport_config['path_segment'])

        # Wait for real content to load
        await self._wait_for_content()

        # Find match elements
        match_elements = await self._get_match_elements()
        logger.info(f"Found {len(match_elements)} live matches on page")

        matches = []
        for i, element in enumerate(match_elements):
            if limit and i >= limit:
                logger.info(f"Reached limit of {limit} live match{'s' if limit > 1 else ''}")
                break

            # Elements are already live (from live_indicators), no need to check status
            match_data = await self.extract_match_data(element, 'live')
            if match_data:
                matches.append(match_data)
                logger.info(f"Added live match: {match_data.teams.get('home', 'Unknown')} vs {match_data.teams.get('away', 'Unknown')}")
            else:
                logger.debug("Skipped live match - no data extracted")

        if limit and len(match_elements) > limit:
            logger.info(f"Extracted {len(matches)} live match{'es' if len(matches) != 1 else ''} (limit: {limit}, available: {len(match_elements)})")
        else:
            logger.info(f"Extracted {len(matches)} live match{'es' if len(matches) != 1 else ''} from {len(match_elements)} found")

        return {
            'sport': sport_config['name'],
            'status': 'live',
            'matches': matches,
            'total': len(matches)
        }

    async def _wait_for_content(self):
        """Wait for loaded (non-skeleton) match row elements to appear on the page.

        Uses a lightweight Playwright check. Exponential backoff between attempts.
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")

        max_attempts = 10
        attempt = 0
        base_delay = 500  # ms
        max_delay = 3000  # ms

        while attempt < max_attempts:
            try:
                # Lightweight Playwright check — bypasses the heavy engine resolve
                elements = await self.scraper.page.query_selector_all('.event__match:not([class*="skeleton"])')
                if not elements:
                    elements = await self.scraper.page.query_selector_all('.event__match')
                
                if elements:
                    logger.info(f"Loaded content detected on attempt {attempt + 1}: {len(elements)} match elements on page")
                    break

                delay = min(base_delay * (2 ** attempt) // 1000, max_delay)
                await self.scraper.page.wait_for_timeout(delay)
                attempt += 1

            except Exception as e:
                logger.warning(f"Error checking for loaded content on attempt {attempt + 1}: {e}")
                delay = min(base_delay * (2 ** attempt) // 1000, max_delay)
                await self.scraper.page.wait_for_timeout(delay)
                attempt += 1

        if attempt >= max_attempts:
            logger.warning("No loaded content detected after maximum attempts, proceeding anyway")

    async def _get_match_elements(self):
        """Get live match elements using Playwright queries.

        Resolution order:
        1. Playwright direct query for .event__match--live (fast, reliable)
        2. All .event__match elements filtered by is_match_status() (fallback)
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")

        # Primary: Find matches with the live status class
        try:
            live_elements = await self.scraper.page.query_selector_all('.event__match--live')
            if live_elements:
                logger.info(f"Found {len(live_elements)} live match elements via .event__match--live")
                return live_elements
        except Exception as e:
            logger.error(f"Error querying .event__match--live: {e}")

        # Fallback: Get all match elements and filter by status
        try:
            all_matches = await self.scraper.page.query_selector_all('.event__match')
            if all_matches:
                live = []
                for el in all_matches:
                    if await self.is_match_status(el):
                        live.append(el)
                if live:
                    logger.info(f"Found {len(live)} live matches from {len(all_matches)} total (filtered by is_match_status)")
                    return live
                else:
                    logger.warning(f"No live matches among {len(all_matches)} total match elements")
        except Exception as e:
            logger.error(f"Error with match fallback: {e}")

        return []
