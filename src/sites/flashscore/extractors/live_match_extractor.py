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
        """Check if a match element is actually live using multiple reliable indicators."""
        try:
            # Method 1: Check for explicit live CSS class (most reliable)
            if await self._element_matches(element, 'live_match_class'):
                self.logger.debug("Live match detected via CSS class (YAML: live_match_class)")
                return True

            # Method 2: Check for live score state indicators
            try:
                live_scores = await self._resolve_elements('live_score', parent=element)
                if live_scores:
                    self.logger.debug(f"Live match detected via {len(live_scores)} live score elements (YAML: live_score)")
                    return True
            except Exception as e:
                self.logger.debug(f"Live score check failed: {e}")

            # Method 3: Check for live score CSS classes
            try:
                live_score_classes = await self._resolve_elements('live_class', parent=element)
                if live_score_classes:
                    self.logger.debug(f"Live match detected via {len(live_score_classes)} live score CSS classes (YAML: live_class)")
                    return True
            except Exception as e:
                self.logger.debug(f"Live score class check failed: {e}")

            # Method 4: Check for actual live scores (not "-" placeholders)
            try:
                score_elements = await self._resolve_elements('match_score', parent=element)
                if len(score_elements) >= 2:
                    home_score = await score_elements[0].text_content()
                    away_score = await score_elements[1].text_content()
                    if home_score and away_score and home_score != '-' and away_score != '-':
                        # Additional check: verify these are actually live scores, not finished scores
                        score_state = await score_elements[0].get_attribute('data-state')
                        if score_state == 'live':
                            self.logger.debug(f"Live match detected via actual live scores: {home_score}-{away_score} (YAML: match_score)")
                            return True
            except Exception as e:
                self.logger.debug(f"Score check failed: {e}")

            # Method 5: Check for live time indicators (quarter/period info)
            try:
                stage_text = await self._resolve_text('match_stage', parent=element)
                if stage_text and ('quarter' in stage_text.lower() or 'min' in stage_text.lower() or 'half' in stage_text.lower()):
                    self.logger.debug(f"Live match detected via stage text: {stage_text} (YAML: match_stage)")
                    return True
            except Exception as e:
                self.logger.debug(f"Stage check failed: {e}")

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
        """Wait for real content to load (not skeleton placeholders) via YAML selector."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")

        max_attempts = 20
        attempt = 0

        while attempt < max_attempts:
            try:
                # Check if we have real content (not just skeleton placeholders)
                real_content = await self._resolve_element('real_match_content')
                if real_content:
                    logger.info(f"Real content detected on attempt {attempt + 1} (YAML: real_match_content)")
                    break

                # Wait a bit and try again
                await self.scraper.page.wait_for_timeout(500)
                attempt += 1

            except Exception as e:
                logger.warning(f"Error checking for real content on attempt {attempt + 1}: {e}")
                await self.scraper.page.wait_for_timeout(500)
                attempt += 1

        if attempt >= max_attempts:
            logger.warning("No real content detected after maximum attempts, proceeding anyway")

    async def _get_match_elements(self):
        """Get live match elements using YAML-driven selectors."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")

        # Primary: Use YAML selector engine to find live matches
        try:
            live_elements = await self._resolve_elements('live_match_class')
            if live_elements:
                logger.info(f"Found {len(live_elements)} live match elements via YAML selector (primary: live_match_class)")
                return live_elements
        except Exception as e:
            logger.error(f"Error with YAML selector: {e}")

        # Fallback: Use semantic selector path via selector engine resolve()
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime

            dom_context = DOMContext(
                page=self.scraper.page,
                tab_context="match_extraction",
                url=self.scraper.page.url,
                timestamp=datetime.utcnow()
            )

            result = await self.scraper.selector_engine.resolve("extraction.match_list.basketball.live_indicators", dom_context)
            if result and result.element_info:
                elements = result.element_info.get('elements', [])
                if elements:
                    logger.info(f"Found {len(elements)} live match elements via semantic selector (fallback)")
                    return elements
                else:
                    logger.warning("Live indicators selector returned success but no elements")
            else:
                logger.warning("Live indicators selector failed to resolve")
        except Exception as e:
            logger.error(f"Error using live indicators selector: {e}")

        # Final fallback: Use real_match_content YAML selector for the finished page filter
        try:
            match_elements = await self._resolve_elements('real_match_content')
            if match_elements:
                logger.info(f"Found {len(match_elements)} match elements via real_match_content (last resort fallback)")
                return match_elements
        except Exception as e:
            logger.error(f"Error with real_match_content fallback: {e}")

        return []
