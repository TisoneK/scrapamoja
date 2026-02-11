"""
Live match extractor for Flashscore.
"""
from typing import Dict, Any, Optional
from playwright.async_api import ElementHandle

from .base_extractor import BaseExtractor


class LiveMatchExtractor(BaseExtractor):
    """Extractor for live matches."""
    
    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element is actually live using multiple reliable indicators."""
        try:
            # Method 1: Check for explicit live CSS class (most reliable)
            class_name = await element.get_attribute('class')
            if class_name and 'event__match--live' in class_name:
                self.logger.debug("Live match detected via CSS class")
                return True
            
            # Method 2: Check for live score state indicators
            try:
                live_scores = await element.query_selector_all('.event__score[data-state="live"]')
                if live_scores:
                    self.logger.debug(f"Live match detected via {len(live_scores)} live score elements")
                    return True
            except Exception as e:
                self.logger.debug(f"Live score check failed: {e}")
            
            # Method 3: Check for live score CSS classes
            try:
                live_score_classes = await element.query_selector_all('.wcl-isLive_VTsUE')
                if live_score_classes:
                    self.logger.debug(f"Live match detected via {len(live_score_classes)} live score CSS classes")
                    return True
            except Exception as e:
                self.logger.debug(f"Live score class check failed: {e}")
            
            # Method 4: Check for actual live scores (not "-" placeholders)
            try:
                score_elements = await element.query_selector_all('.event__score')
                if len(score_elements) >= 2:
                    home_score = await score_elements[0].text_content()
                    away_score = await score_elements[1].text_content()
                    if home_score and away_score and home_score != '-' and away_score != '-':
                        # Additional check: verify these are actually live scores, not finished scores
                        score_state = await score_elements[0].get_attribute('data-state')
                        if score_state == 'live':
                            self.logger.debug(f"Live match detected via actual live scores: {home_score}-{away_score}")
                            return True
            except Exception as e:
                self.logger.debug(f"Score check failed: {e}")
            
            # Method 5: Check for live time indicators (quarter/period info)
            try:
                stage_element = await element.query_selector('.event__stage--block')
                if stage_element:
                    stage_text = await stage_element.text_content()
                    if stage_text and ('quarter' in stage_text.lower() or 'min' in stage_text.lower() or 'half' in stage_text.lower()):
                        self.logger.debug(f"Live match detected via stage text: {stage_text}")
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
                logger.info(f"Added live match: {match_data.get('home_team', 'Unknown')} vs {match_data.get('away_team', 'Unknown')}")
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
        """Wait for real content to load (not skeleton placeholders)."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")
        
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
        """Get live match elements using live indicators directly."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.live")
        
        # Use live_indicators selector to find only live matches
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
                    logger.info(f"Found {len(elements)} live match elements via live_indicators selector")
                    return elements
                else:
                    logger.warning("Live indicators selector returned success but no elements")
            else:
                logger.warning("Live indicators selector failed to resolve")
        except Exception as e:
            logger.error(f"Error using live indicators selector: {e}")
        
        # Fallback to direct CSS query for live matches
        try:
            live_elements = await self.scraper.page.query_selector_all('.event__match--live')
            if live_elements:
                logger.info(f"Found {len(live_elements)} live match elements with fallback CSS selector")
                return live_elements
            else:
                logger.warning("No live matches found with fallback selector")
        except Exception as e:
            logger.error(f"Error with fallback live selector: {e}")
        
        return []
