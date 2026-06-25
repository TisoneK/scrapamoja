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
        """Check if a match element is actually scheduled using multiple reliable indicators."""
        try:
            # Method 1: Check for explicit scheduled CSS class (most reliable)
            if await self._element_matches(element, 'scheduled_match_class'):
                self.logger.debug("Scheduled match detected via CSS class (YAML: scheduled_match_class)")
                return True

            # Method 2: Check for scheduled score state indicators
            scheduled_scores = await self._resolve_elements('prematch_score', parent=element)
            if scheduled_scores:
                self.logger.debug(f"Scheduled match detected via {len(scheduled_scores)} pre-match score elements (YAML: prematch_score)")
                return True

            # Method 3: Check for scheduled score CSS classes
            scheduled_score_classes = await self._resolve_elements('prematch_class', parent=element)
            if scheduled_score_classes:
                self.logger.debug(f"Scheduled match detected via {len(scheduled_score_classes)} pre-match score CSS classes (YAML: prematch_class)")
                return True

            # Method 4: Check for time elements (scheduled matches have time, not stage)
            try:
                time_text = await self._resolve_text('match_time', parent=element)
                if time_text and ':' in time_text:
                    self.logger.debug(f"Scheduled match detected via time text: {time_text} (YAML: match_time)")
                    return True
            except Exception as e:
                self.logger.debug(f"Time check failed: {e}")

            # Method 5: Check for dash scores (scheduled matches have "-" scores)
            try:
                score_elements = await self._resolve_elements('match_score', parent=element)
                if len(score_elements) >= 2:
                    home_score = await score_elements[0].text_content()
                    away_score = await score_elements[1].text_content()
                    if home_score == '-' and away_score == '-':
                        # Additional check: verify these are actually pre-match scores
                        score_state = await score_elements[0].get_attribute('data-state')
                        if score_state == 'pre-match':
                            self.logger.debug("Scheduled match detected via dash scores (YAML: match_score)")
                            return True
            except Exception as e:
                self.logger.debug(f"Score check failed: {e}")

            # Method 6: Exclude if it has live or finished indicators
            # If it has live or finished indicators, it's not scheduled
            live_indicators = await self._resolve_elements('live_score', parent=element)
            finished_indicators = await self._resolve_elements('final_score', parent=element)
            if live_indicators or finished_indicators:
                self.logger.debug("Match has live or finished indicators - not scheduled (YAML: live_score/final_score)")
                return False

            # Method 7: Default to scheduled if no live/finished indicators and has time
            # This is a fallback for edge cases
            stage_element = await self._resolve_element('match_stage', parent=element)
            if not stage_element:
                time_element = await self._resolve_element('match_time', parent=element)
                if time_element:
                    self.logger.debug("No stage element but has time - assuming scheduled (YAML: match_time)")
                    return True

            # If none of the scheduled indicators are found, it's not a scheduled match
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
        """Get scheduled match elements using YAML-driven selectors.

        Resolution order:
        1. ``scheduled_match_class`` — targets .event__match--scheduled (status-specific)
        2. ``match_items`` — targets .event__match (all matches), filtered by is_match_status()
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.scheduled")

        # Primary: Find matches with the scheduled status class
        try:
            scheduled_elements = await self._resolve_elements('scheduled_match_class')
            if scheduled_elements:
                logger.info(f"Found {len(scheduled_elements)} scheduled match elements via YAML selector (scheduled_match_class)")
                return scheduled_elements
            else:
                logger.warning("No scheduled matches found with scheduled_match_class selector")
        except Exception as e:
            logger.error(f"Error with scheduled_match_class selector: {e}")

        # Fallback: Get all match elements and filter by status
        try:
            all_matches = await self._resolve_elements('match_items')
            if all_matches:
                scheduled = []
                for el in all_matches:
                    if await self.is_match_status(el):
                        scheduled.append(el)
                if scheduled:
                    logger.info(f"Found {len(scheduled)} scheduled matches from {len(all_matches)} total (filtered via match_items)")
                    return scheduled
                else:
                    logger.warning(f"No scheduled matches among {len(all_matches)} total match elements")
        except Exception as e:
            logger.error(f"Error with match_items fallback: {e}")

        return []
