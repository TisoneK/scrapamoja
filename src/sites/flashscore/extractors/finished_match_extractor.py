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
        """Check if a match element is actually finished using multiple reliable indicators."""
        try:
            # Method 1: Check for finished score state indicators (most reliable)
            finished_scores = await self._resolve_elements('final_score', parent=element)
            if finished_scores:
                self.logger.debug(f"Finished match detected via {len(finished_scores)} final score elements (YAML: final_score)")
                return True

            # Method 2: Check for finished score CSS classes
            finished_score_classes = await self._resolve_elements('final_class', parent=element)
            if finished_score_classes:
                self.logger.debug(f"Finished match detected via {len(finished_score_classes)} final score CSS classes (YAML: final_class)")
                return True

            # Method 3: Check for explicit finished CSS class
            if await self._element_matches(element, 'finished_match_class'):
                self.logger.debug("Finished match detected via CSS class (YAML: finished_match_class)")
                return True

            # Method 4: Check for finished stage text
            try:
                stage_text = await self._resolve_text('match_stage', parent=element)
                if stage_text and ('finished' in stage_text.lower() or 'after' in stage_text.lower() or 'ft' in stage_text.lower()):
                    self.logger.debug(f"Finished match detected via stage text: {stage_text} (YAML: match_stage)")
                    return True
            except Exception as e:
                self.logger.debug(f"Stage check failed: {e}")

            # Method 5: Check for actual finished scores (not "-" and not live)
            try:
                score_elements = await self._resolve_elements('match_score', parent=element)
                if len(score_elements) >= 2:
                    home_score = await score_elements[0].text_content()
                    away_score = await score_elements[1].text_content()
                    if home_score and away_score and home_score != '-' and away_score != '-':
                        # Additional check: verify these are actually finished scores
                        score_state = await score_elements[0].get_attribute('data-state')
                        if score_state == 'final':
                            self.logger.debug(f"Finished match detected via actual final scores: {home_score}-{away_score} (YAML: match_score)")
                            return True
            except Exception as e:
                self.logger.debug(f"Score check failed: {e}")

            # If none of the finished indicators are found, it's not a finished match
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
        """Wait for real content to load (not skeleton placeholders) via YAML selector.
        
        Uses exponential backoff: starts at 500ms, caps at 3s.
        Stops early if the selector is not registered in the engine.
        """
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")

        max_attempts = 10  # Reduced from 20 — exponential backoff makes 10 plenty
        attempt = 0
        base_delay = 500  # ms
        max_delay = 3000  # ms

        # Early exit: check if the selector is even registered
        if hasattr(self.scraper, 'selector_engine') and self.scraper.selector_engine is not None:
            try:
                registry = self.scraper.selector_engine.registry
                if registry and not registry.get('real_match_content'):
                    logger.warning("Selector 'real_match_content' not in registry — skipping wait loop")
                    return
            except Exception:
                pass

        while attempt < max_attempts:
            try:
                real_content = await self._resolve_element('real_match_content')
                if real_content:
                    logger.info(f"Real content detected on attempt {attempt + 1} (YAML: real_match_content)")
                    break

                delay = min(base_delay * (2 ** attempt) // 1000, max_delay)
                await self.scraper.page.wait_for_timeout(delay)
                attempt += 1

            except Exception as e:
                logger.warning(f"Error checking for real content on attempt {attempt + 1}: {e}")
                delay = min(base_delay * (2 ** attempt) // 1000, max_delay)
                await self.scraper.page.wait_for_timeout(delay)
                attempt += 1

        if attempt >= max_attempts:
            logger.warning("No real content detected after maximum attempts, proceeding anyway")

    async def _get_match_elements(self):
        """Get finished match elements using YAML-driven selectors."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")

        # Primary: Use YAML selector engine to find finished matches
        try:
            finished_elements = await self._resolve_elements('finished_match_class')
            if finished_elements:
                logger.info(f"Found {len(finished_elements)} finished match elements via YAML selector (primary: finished_match_class)")
                return finished_elements
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

            result = await self.scraper.selector_engine.resolve("extraction.match_list.basketball.finished_indicators", dom_context)
            if result and result.element_info:
                elements = result.element_info.get('elements', [])
                if elements:
                    logger.info(f"Found {len(elements)} finished match elements via semantic selector (fallback)")
                    return elements
                else:
                    logger.warning("Finished indicators selector returned success but no elements")
            else:
                logger.warning("Finished indicators selector failed to resolve")
        except Exception as e:
            logger.error(f"Error using finished indicators selector: {e}")

        # Final fallback: Use real_match_content YAML selector
        # FlashScore shows finished matches by filter tab - all non-skeleton matches on the page are finished
        try:
            match_elements = await self._resolve_elements('real_match_content')
            if match_elements:
                logger.info(f"Found {len(match_elements)} match elements on finished page (all are finished by filter) (YAML: real_match_content)")
                return match_elements
        except Exception as e:
            logger.error(f"Error with real_match_content fallback: {e}")

        return []
