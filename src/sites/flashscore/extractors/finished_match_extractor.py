"""
Finished match extractor for Flashscore.
"""
from typing import Dict, Any, Optional
from playwright.async_api import ElementHandle

from .base_extractor import BaseExtractor


class FinishedMatchExtractor(BaseExtractor):
    """Extractor for finished matches."""
    
    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element is actually finished using multiple reliable indicators."""
        try:
            # Method 1: Check for finished score state indicators (most reliable)
            finished_scores = await element.query_selector_all('.event__score[data-state="final"]')
            if finished_scores:
                self.logger.debug(f"Finished match detected via {len(finished_scores)} final score elements")
                return True
            
            # Method 2: Check for finished score CSS classes
            finished_score_classes = await element.query_selector_all('.wcl-isFinal_7U4ca')
            if finished_score_classes:
                self.logger.debug(f"Finished match detected via {len(finished_score_classes)} final score CSS classes")
                return True
            
            # Method 3: Check for explicit finished CSS class
            class_name = await element.get_attribute('class')
            if class_name and 'event__match--finished' in class_name:
                self.logger.debug("Finished match detected via CSS class")
                return True
            
            # Method 4: Check for finished stage text
            try:
                stage_element = await element.query_selector('.event__stage--block')
                if stage_element:
                    stage_text = await stage_element.text_content()
                    if stage_text and ('finished' in stage_text.lower() or 'after' in stage_text.lower() or 'ft' in stage_text.lower()):
                        self.logger.debug(f"Finished match detected via stage text: {stage_text}")
                        return True
            except Exception as e:
                self.logger.debug(f"Stage check failed: {e}")
            
            # Method 5: Check for actual finished scores (not "-" and not live)
            try:
                score_elements = await element.query_selector_all('.event__score')
                if len(score_elements) >= 2:
                    home_score = await score_elements[0].text_content()
                    away_score = await score_elements[1].text_content()
                    if home_score and away_score and home_score != '-' and away_score != '-':
                        # Additional check: verify these are actually finished scores
                        score_state = await score_elements[0].get_attribute('data-state')
                        if score_state == 'final':
                            self.logger.debug(f"Finished match detected via actual final scores: {home_score}-{away_score}")
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
                logger.info(f"Reached limit of {limit} finished match{'s' if limit > 1 else ''}")
                break
            
            # Elements are already finished (from finished_indicators), no need to check status
            match_data = await self.extract_match_data(element, 'finished')
            if match_data:
                matches.append(match_data)
                logger.info(f"Added finished match: {match_data.get('home_team', 'Unknown')} vs {match_data.get('away_team', 'Unknown')}")
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
        """Wait for real content to load (not skeleton placeholders)."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")
        
        max_attempts = 20
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Check if we have real content (not just skeleton placeholders)
                real_content = await self.scraper.page.query_selector('.event__match:not([class*="skeleton"])')
                if real_content:
                    logger.info(f"Real content detected on attempt {attempt + 1}")
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
        """Get finished match elements using finished indicators directly."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.finished")
        
        # Use finished_indicators selector to find only finished matches
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
                    logger.info(f"Found {len(elements)} finished match elements via finished_indicators selector")
                    return elements
                else:
                    logger.warning("Finished indicators selector returned success but no elements")
            else:
                logger.warning("Finished indicators selector failed to resolve")
        except Exception as e:
            logger.error(f"Error using finished indicators selector: {e}")
        
        # Fallback to direct CSS query for finished matches
        try:
            finished_elements = await self.scraper.page.query_selector_all('.event__score[data-state="final"]')
            # Get the parent match elements
            match_elements = []
            for score_elem in finished_elements:
                match_elem = await score_elem.evaluate('element => element.closest(".event__match")')
                if match_elem:
                    match_elements.append(match_elem)
            
            if match_elements:
                logger.info(f"Found {len(match_elements)} finished match elements with fallback selector")
                return match_elements
            else:
                logger.warning("No finished matches found with fallback selector")
        except Exception as e:
            logger.error(f"Error with fallback finished selector: {e}")
        
        return []
