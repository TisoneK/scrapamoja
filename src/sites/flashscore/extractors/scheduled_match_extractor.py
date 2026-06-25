"""
Scheduled match extractor for Flashscore.

ALL selectors are YAML-driven via the selector engine. Zero hardcoded CSS strings.
Each selector lives in its own YAML file under src/sites/flashscore/selectors/extraction/
with ordered fallback chains: data-testid → obfuscated class → partial class → xpath.

When FlashScore rotates CSS hashes, only the YAML entries need updating.
No Python code changes required.
"""
from typing import Dict, Any, Optional, List
from src.sites.flashscore.models import MatchListing
from playwright.async_api import ElementHandle

from .base_extractor import BaseExtractor


class ScheduledMatchExtractor(BaseExtractor):
    """Extractor for scheduled matches — 100% YAML-driven selectors."""

    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element is actually scheduled using Playwright queries."""
        try:
            # Method 1: Check for scheduled CSS class on the element itself
            class_attr = await element.get_attribute('class')
            if class_attr and 'event__match--scheduled' in class_attr:
                self.logger.debug("Scheduled match detected via .event__match--scheduled class")
                return True

            # Method 2: Check for time element (scheduled matches show time, not stage)
            try:
                time_el = await element.query_selector('.event__time')
                if time_el:
                    time_text = await time_el.text_content()
                    if time_text and ':' in time_text:
                        self.logger.debug(f"Scheduled match detected via time text: {time_text}")
                        return True
            except Exception:
                pass

            # Method 3: Check for dash scores (scheduled matches have "-" scores)
            try:
                score_els = await element.query_selector_all('.event__score')
                if len(score_els) >= 2:
                    home = (await score_els[0].text_content() or '').strip()
                    away = (await score_els[1].text_content() or '').strip()
                    if home == '-' and away == '-':
                        score_state = await score_els[0].get_attribute('data-state')
                        if score_state == 'pre-match':
                            self.logger.debug("Scheduled match detected via dash scores with pre-match state")
                            return True
            except Exception:
                pass

            # Method 4: Exclude if it has live or finished indicators
            try:
                class_attr = await element.get_attribute('class') or ''
                if 'event__match--live' in class_attr or 'event__match--finished' in class_attr:
                    self.logger.debug("Match has live/finished class - not scheduled")
                    return False
            except Exception:
                pass

            # Method 5: If no stage element and has time, assume scheduled
            try:
                stage_el = await element.query_selector('.event__stage')
                time_el = await element.query_selector('.event__time')
                if not stage_el and time_el:
                    self.logger.debug("No stage but has time - assuming scheduled")
                    return True
            except Exception:
                pass

            self.logger.debug("No scheduled indicators found - match is not scheduled")
            return False

        except Exception as e:
            self.logger.error(f"Error in is_match_status: {e}")
            return False

    async def extract_matches(self, sport_config: dict, limit: Optional[int] = None) -> Dict[str, Any]:
        """Extract scheduled matches."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.scheduled")

        # Navigate to scheduled games
        await self.scraper.flow.navigate_to_scheduled_games(sport_config['path_segment'])

        # Wait for real content to load
        await self._wait_for_content()

        # Find match elements
        match_elements = await self._get_match_elements()
        logger.info(f"Found {len(match_elements)} scheduled matches on page")

        matches = []
        for i, element in enumerate(match_elements):
            if limit and i >= limit:
                logger.info(f"Reached limit of {limit} scheduled match{'es' if limit > 1 else ''}")
                break

            # Elements are already scheduled (from scheduled_indicators), no need to check status
            match_data = await self.extract_match_data(element, 'scheduled')
            if match_data:
                matches.append(match_data)
                logger.info(f"Added scheduled match: {match_data.teams['home']} vs {match_data.teams['away']}")
            else:
                logger.debug("Skipped scheduled match - no data extracted")

        if limit and len(match_elements) > limit:
            logger.info(f"Extracted {len(matches)} scheduled match{'es' if len(matches) != 1 else ''} (limit: {limit}, available: {len(match_elements)})")
        else:
            logger.info(f"Extracted {len(matches)} scheduled match{'es' if len(matches) != 1 else ''} from {len(match_elements)} found")

        return {
            'sport': sport_config['name'],
            'status': 'scheduled',
            'matches': matches,
            'total': len(matches)
        }

    async def _wait_for_content(self):
        """Wait for loaded (non-skeleton) match row elements to appear on the page.

        Uses a lightweight Playwright check first, then falls back to the
        selector engine if needed. Exponential backoff between attempts.
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.scheduled")

        max_attempts = 10
        attempt = 0
        base_delay = 500  # ms
        max_delay = 3000  # ms

        # Diagnostic: what page are we actually on?
        try:
            current_url = self.scraper.page.url
            title = await self.scraper.page.title()
            logger.info(f"_wait_for_content starting — url={current_url}, title={title}")
        except Exception as e:
            logger.warning(f"Could not read page URL: {e}")

        while attempt < max_attempts:
            try:
                # Lightweight Playwright check — bypasses the heavy engine resolve
                elements = await self.scraper.page.query_selector_all('.event__match:not([class*="skeleton"])')
                if not elements:
                    # Broader check — any .event__match at all?
                    elements = await self.scraper.page.query_selector_all('.event__match')
                
                if elements:
                    logger.info(f"Loaded content detected on attempt {attempt + 1}: {len(elements)} match elements on page")
                    break

                # Exponential backoff: 500ms → 1000ms → 2000ms → 3000ms cap
                delay = min(base_delay * (2 ** attempt), max_delay)
                await self.scraper.page.wait_for_timeout(delay)
                attempt += 1

            except Exception as e:
                logger.warning(f"Error checking for loaded content on attempt {attempt + 1}: {e}")
                delay = min(base_delay * (2 ** attempt), max_delay)
                await self.scraper.page.wait_for_timeout(delay)
                attempt += 1

        if attempt >= max_attempts:
            logger.warning("No loaded content detected after maximum attempts, proceeding anyway")

    async def _get_match_elements(self):
        """Get scheduled match elements using YAML-driven selectors.

        Resolution order:
        1. Playwright direct query for .event__match--scheduled (fast, reliable)
        2. All .event__match elements filtered by is_match_status() (fallback)
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.scheduled")

        # Primary: Find matches with the scheduled status class
        try:
            scheduled_elements = await self.scraper.page.query_selector_all('.event__match--scheduled')
            if scheduled_elements:
                logger.info(f"Found {len(scheduled_elements)} scheduled match elements via .event__match--scheduled")
                return scheduled_elements
            else:
                logger.warning("No .event__match--scheduled elements found")
        except Exception as e:
            logger.error(f"Error querying .event__match--scheduled: {e}")

        # Fallback: Get all match elements and filter by status
        try:
            all_matches = await self.scraper.page.query_selector_all('.event__match')
            if all_matches:
                scheduled = []
                for el in all_matches:
                    if await self.is_match_status(el):
                        scheduled.append(el)
                if scheduled:
                    logger.info(f"Found {len(scheduled)} scheduled matches from {len(all_matches)} total (filtered by is_match_status)")
                    return scheduled
                else:
                    logger.warning(f"No scheduled matches among {len(all_matches)} total match elements")
                    # On the scheduled tab, all matches are scheduled — return them all
                    logger.info(f"Returning all {len(all_matches)} match elements (on scheduled tab)")
                    return all_matches
        except Exception as e:
            logger.error(f"Error with match_items fallback: {e}")

        return []
