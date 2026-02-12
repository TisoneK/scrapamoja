"""
Scheduled match extractor for Flashscore.
"""
from typing import Dict, Any, Optional
from playwright.async_api import ElementHandle

from .base_extractor import BaseExtractor


class ScheduledMatchExtractor(BaseExtractor):
    """Extractor for scheduled matches."""
    
    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element is actually scheduled using multiple reliable indicators."""
        try:
            # Method 1: Check for explicit scheduled CSS class (most reliable)
            class_name = await element.get_attribute('class')
            if class_name and 'event__match--scheduled' in class_name:
                self.logger.debug("Scheduled match detected via CSS class")
                return True
            
            # Method 2: Check for scheduled score state indicators
            scheduled_scores = await element.query_selector_all('.event__score[data-state="pre-match"]')
            if scheduled_scores:
                self.logger.debug(f"Scheduled match detected via {len(scheduled_scores)} pre-match score elements")
                return True
            
            # Method 3: Check for scheduled score CSS classes
            scheduled_score_classes = await element.query_selector_all('.wcl-isPreMatch_FgNtO')
            if scheduled_score_classes:
                self.logger.debug(f"Scheduled match detected via {len(scheduled_score_classes)} pre-match score CSS classes")
                return True
            
            # Method 4: Check for time elements (scheduled matches have time, not stage)
            try:
                time_element = await element.query_selector('.event__time')
                if time_element:
                    time_text = await time_element.text_content()
                    if time_text and time_text.strip() and ':' in time_text:
                        self.logger.debug(f"Scheduled match detected via time text: {time_text}")
                        return True
            except Exception as e:
                self.logger.debug(f"Time check failed: {e}")
            
            # Method 5: Check for dash scores (scheduled matches have "-" scores)
            try:
                score_elements = await element.query_selector_all('.event__score')
                if len(score_elements) >= 2:
                    home_score = await score_elements[0].text_content()
                    away_score = await score_elements[1].text_content()
                    if home_score == '-' and away_score == '-':
                        # Additional check: verify these are actually pre-match scores
                        score_state = await score_elements[0].get_attribute('data-state')
                        if score_state == 'pre-match':
                            self.logger.debug("Scheduled match detected via dash scores")
                            return True
            except Exception as e:
                self.logger.debug(f"Score check failed: {e}")
            
            # Method 6: Exclude if it has live or finished indicators
            # If it has live or finished indicators, it's not scheduled
            live_indicators = await element.query_selector_all('.event__score[data-state="live"]')
            finished_indicators = await element.query_selector_all('.event__score[data-state="final"]')
            if live_indicators or finished_indicators:
                self.logger.debug("Match has live or finished indicators - not scheduled")
                return False
            
            # Method 7: Default to scheduled if no live/finished indicators and has time
            # This is a fallback for edge cases
            stage_element = await element.query_selector('.event__stage--block')
            if not stage_element:
                time_element = await element.query_selector('.event__time')
                if time_element:
                    self.logger.debug("No stage element but has time - assuming scheduled")
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
                logger.info(f"Reached limit of {limit} scheduled match{'s' if limit > 1 else ''}")
                break
            
            # Elements are already scheduled (from scheduled_indicators), no need to check status
            match_data = await self.extract_match_data(element, 'scheduled')
            if match_data:
                matches.append(match_data)
                logger.info(f"Added scheduled match: {match_data.get('home_team', 'Unknown')} vs {match_data.get('away_team', 'Unknown')}")
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
        """Wait for real content to load (not skeleton placeholders)."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.scheduled")
        
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
        """Get scheduled match elements using direct CSS selector (what actually works)."""
        from src.observability.logger import get_logger
        logger = get_logger("flashscore.extractor.scheduled")
        
        # Use the working CSS selector first (what we know works)
        try:
            scheduled_elements = await self.scraper.page.query_selector_all('.event__match--scheduled')
            if scheduled_elements:
                logger.info(f"Found {len(scheduled_elements)} scheduled match elements with direct CSS selector (primary method)")
                return scheduled_elements
            else:
                logger.warning("No scheduled matches found with direct CSS selector")
        except Exception as e:
            logger.error(f"Error with direct CSS selector: {e}")
        
        # Only try semantic selector as fallback if direct CSS fails
        try:
            from src.selectors.context import DOMContext
            from datetime import datetime
            
            # Create DOM context
            context = DOMContext(
                page=self.scraper.page,
                tab_context="scheduled",
                url=self.scraper.page.url,
                timestamp=datetime.utcnow()
            )
            
            # Check if selector engine exists and is properly initialized
            if not hasattr(self.scraper, 'selector_engine') or self.scraper.selector_engine is None:
                logger.warning("Selector engine not available")
                return []
            
            # Use semantic selector as fallback
            result = await self.scraper.selector_engine.resolve('extraction.match_list.basketball.scheduled_indicators', context)
            if result and result.element_info:
                # Check if elements are stored in metadata (for multi-element results)
                if hasattr(result.element_info, 'metadata') and result.element_info.metadata.get('all_elements'):
                    elements = result.element_info.metadata.get('all_elements')
                    logger.info(f"Found {len(elements)} scheduled match elements via semantic selector (fallback)")
                    return elements
                # Fallback to old way for single element results
                elif hasattr(result.element_info, 'element') and result.element_info.element:
                    elements = [result.element_info.element]
                    logger.info(f"Found {len(elements)} scheduled match elements via semantic selector (single element fallback)")
                    return elements
                else:
                    logger.warning("Semantic selector returned success but no elements")
            else:
                logger.warning("Semantic selector failed to resolve")
        except Exception as e:
            logger.error(f"Error using semantic selector: {e}")
        
        return []
