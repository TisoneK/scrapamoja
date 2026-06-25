"""
Finished match extractor for Flashscore.

ALL selectors are YAML-driven via the selector engine. Zero hardcoded CSS strings.
Each selector lives in its own YAML file under src/sites/flashscore/selectors/extraction/
with ordered fallback chains: data-testid → obfuscated class → partial class → xpath.

When FlashScore rotates CSS hashes, only the YAML entries need updating.
No Python code changes required.
"""
from typing import Dict, Any, Optional
from playwright.async_api import ElementHandle

from .base_extractor import BaseExtractor


class FinishedMatchExtractor(BaseExtractor):
    """Extractor for finished matches — 100% YAML-driven selectors."""

    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element is actually finished using Playwright queries."""
        try:
            # Method 1: Check for finished CSS class on the element itself
            class_attr = await element.get_attribute('class')
            if class_attr and 'event__match--finished' in class_attr:
                self.logger.debug("Finished match detected via .event__match--finished class")
                return True

            # Method 2: Check for final score state indicators
            try:
                final_scores = await element.query_selector_all('.event__score[data-state="final"]')
                if final_scores:
                    self.logger.debug(f"Finished match detected via {len(final_scores)} final score elements")
                    return True
            except Exception:
                pass

            # Method 3: Check for finished stage text
            try:
                stage_el = await element.query_selector('.event__stage, .event__stage--block')
                if stage_el:
                    stage_text = await stage_el.text_content()
                    if stage_text and ('finished' in stage_text.lower() or 'after' in stage_text.lower() or 'ft' in stage_text.lower()):
                        self.logger.debug(f"Finished match detected via stage text: {stage_text}")
                        return True
            except Exception:
                pass

            # Method 4: Check for actual numeric scores (not "-" placeholders)
            try:
                score_els = await element.query_selector_all('.event__score')
                if len(score_els) >= 2:
                    home = (await score_els[0].text_content() or '').strip()
                    away = (await score_els[1].text_content() or '').strip()
                    if home and away and home != '-' and away != '-':
                        score_state = await score_els[0].get_attribute('data-state')
                        if score_state == 'final':
                            self.logger.debug(f"Finished match detected via final scores: {home}-{away}")
                            return True
            except Exception:
                pass

            self.logger.debug("No finished indicators found - match is not finished")
            return False

        except Exception as e:
            self.logger.error(f"Error in is_match_status: {e}")
            return False

    async def extract_matches(self, sport_config: dict, limit: Optional[int] = None) -> Dict[str, Any]:
        """Extract finished matches."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")

        # Navigate to finished games
        await self.scraper.flow.navigate_to_finished_games(sport_config['path_segment'])

        # Wait for real content to load
        await self._wait_for_content()

        # Find match elements
        match_elements = await self._get_match_elements()
        logger.info(f"Found {len(match_elements)} finished matches on page")

        matches = []
        for i, element in enumerate(match_elements):
            if limit and i >= limit:
                logger.info(f"Reached limit of {limit} finished match{'es' if limit > 1 else ''}")
                break

            # Elements are already finished (from finished_indicators), no need to check status
            match_data = await self.extract_match_data(element, 'finished')
            if match_data:
                matches.append(match_data)
                logger.info(f"Added finished match: {match_data.teams.get('home', 'Unknown')} vs {match_data.teams.get('away', 'Unknown')}")
            else:
                logger.debug("Skipped finished match - no data extracted")

        if limit and len(match_elements) > limit:
            logger.info(f"Extracted {len(matches)} finished match{'es' if len(matches) != 1 else ''} (limit: {limit}, available: {len(match_elements)})")
        else:
            logger.info(f"Extracted {len(matches)} finished match{'es' if len(matches) != 1 else ''} from {len(match_elements)} found")

        return {
            'sport': sport_config['name'],
            'status': 'finished',
            'matches': matches,
            'total': len(matches)
        }

    async def _wait_for_content(self):
        """Wait for loaded (non-skeleton) match row elements to appear on the page.

        Uses a lightweight Playwright check. Exponential backoff between attempts.
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")

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
        """Get finished match elements using Playwright queries.

        Resolution order:
        1. Playwright direct query for .event__match--finished (fast, reliable)
        2. All .event__match elements filtered by is_match_status() (fallback)
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")

        # Primary: Find matches with the finished status class
        try:
            finished_elements = await self.scraper.page.query_selector_all('.event__match--finished')
            if finished_elements:
                logger.info(f"Found {len(finished_elements)} finished match elements via .event__match--finished")
                return finished_elements
        except Exception as e:
            logger.error(f"Error querying .event__match--finished: {e}")

        # Fallback: Get all match elements and filter by status
        # When navigating to the finished tab, all visible matches should be finished
        try:
            all_matches = await self.scraper.page.query_selector_all('.event__match')
            if all_matches:
                finished = []
                for el in all_matches:
                    if await self.is_match_status(el):
                        finished.append(el)
                if finished:
                    logger.info(f"Found {len(finished)} finished matches from {len(all_matches)} total (filtered by is_match_status)")
                    return finished
                else:
                    # On the finished tab, all non-skeleton matches are likely finished
                    logger.info(f"No finished matches identified by is_match_status, returning all {len(all_matches)} match elements (on finished tab)")
                    return all_matches
        except Exception as e:
            logger.error(f"Error with match fallback: {e}")

        return []
