"""
Base extractor interface for Flashscore match data extraction.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle

from src.sites.flashscore.scraper import FlashscoreScraper


class BaseExtractor(ABC):
    """Base class for all match extractors."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
    
    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.extractor.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    async def extract_matches(self, sport_config: dict, limit: Optional[int] = None) -> Dict[str, Any]:
        """Extract matches for this extractor type."""
        pass
    
    @abstractmethod
    async def is_match_status(self, element: ElementHandle) -> bool:
        """Check if a match element has the correct status for this extractor."""
        pass
    
    async def extract_match_data(self, element: ElementHandle, expected_status: str) -> Optional[Dict[str, Any]]:
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
            
            # Extract URL
            match_url = await self._extract_url(element)
            
            # Extract time/stage based on status
            time_info = await self._extract_time_info(element, expected_status)
            
            # Build match data
            match_data = {
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'url': match_url,
                'time': time_info,
                'status': expected_status
            }
            
            self.logger.info(f"Successfully extracted match data: {home_team} vs {away_team}")
            return match_data
            
        except Exception as e:
            self.logger.error(f"Error extracting match data: {e}")
            return None
    
    async def _extract_match_id(self, element: ElementHandle) -> Optional[str]:
        """Extract match ID using two methods: URL parameter (primary) and aria-describedby (fallback)."""
        try:
            # Method 1: Extract from URL parameter ?mid=CSXgyReU (primary)
            link_element = await element.query_selector('.eventRowLink')
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
            link_element = await element.query_selector('.eventRowLink')
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
        """Extract home and away team names."""
        # Extract home team
        try:
            # Try multiple possible selectors for home team
            home_team_element = await element.query_selector('.event__participant--home')
            if not home_team_element:
                home_team_element = await element.query_selector('.participant__home')
            if not home_team_element:
                home_team_element = await element.query_selector('.event__participant.event__participant--home')
            
            if home_team_element:
                self.logger.info("Home team element found")
                home_team = await home_team_element.text_content()
            else:
                self.logger.warning("Home team element not found")
                home_team = None
            if home_team:
                home_team = home_team.strip()
            else:
                self.logger.warning(f"Home team text content empty: {home_team}")
        except Exception as e:
            self.logger.error(f"Error extracting home team: {e}")
            home_team = None
        
        # Extract away team
        try:
            # Try multiple possible selectors for away team
            away_team_element = await element.query_selector('.event__participant--away')
            if not away_team_element:
                away_team_element = await element.query_selector('.participant__away')
            if not away_team_element:
                away_team_element = await element.query_selector('.event__participant.event__participant--away')
            
            if away_team_element:
                self.logger.info("Away team element found")
                away_team = await away_team_element.text_content()
            else:
                self.logger.warning("Away team element not found")
                away_team = None
            if away_team:
                away_team = away_team.strip()
            else:
                self.logger.warning(f"Away team text content empty: {away_team}")
        except Exception as e:
            self.logger.error(f"Error extracting away team: {e}")
            away_team = None
        
        return home_team, away_team
    
    async def _extract_scores(self, element: ElementHandle) -> tuple[Optional[str], Optional[str]]:
        """Extract home and away scores."""
        try:
            score_elements = await element.query_selector_all('.event__score')
            if len(score_elements) >= 2:
                home_score = await score_elements[0].text_content()
                away_score = await score_elements[1].text_content()
                return home_score.strip() if home_score else None, away_score.strip() if away_score else None
        except Exception as e:
            self.logger.error(f"Error extracting scores: {e}")
        
        return None, None
    
    async def _extract_url(self, element: ElementHandle) -> Optional[str]:
        """Extract match URL."""
        try:
            link_element = await element.query_selector('.eventRowLink')
            if link_element:
                match_url = await link_element.get_attribute('href')
                if match_url and not match_url.startswith('http'):
                    match_url = f"https://www.flashscore.com{match_url}"
                return match_url
        except Exception as e:
            self.logger.error(f"Error extracting URL: {e}")
        
        return None
    
    async def _extract_time_info(self, element: ElementHandle, expected_status: str) -> Optional[str]:
        """Extract time information based on match status."""
        from src.selectors.context import DOMContext
        from datetime import datetime
        
        # Create DOM context for element
        dom_context = DOMContext(
            page=element,
            tab_context="match_extraction",
            url=self.scraper.page.url or '',
            timestamp=datetime.utcnow()
        )
        
        if expected_status == 'live':
            # For live matches, try to get current match stage/period
            try:
                stage_result = await self.scraper.selector_engine.resolve("extraction.match_list.match_stage", dom_context)
                if stage_result and stage_result.element_info:
                    stage_text = stage_result.element_info.get('text', '').strip()
                    if stage_text:
                        self.logger.info(f"Extracted match stage: '{stage_text}' for live match")
                        return stage_text
                    else:
                        self.logger.warning(f"Stage selector returned empty text for live match")
                else:
                    self.logger.warning(f"Stage selector failed or returned no element info for live match")
            except Exception as e:
                self.logger.error(f"Error resolving match_stage selector: {e}")
            
            # Fallback to time extraction if stage fails
            try:
                time_result = await self.scraper.selector_engine.resolve("extraction.match_list.match_time", dom_context)
                if time_result and time_result.element_info:
                    time_text = time_result.element_info.get('text', '').strip()
                    if time_text:
                        self.logger.info(f"Using time as fallback for live match: '{time_text}'")
                        return time_text
            except Exception as e:
                self.logger.error(f"Error resolving match_time selector as fallback: {e}")
        
        else:
            # For scheduled and finished matches, get kickoff time
            try:
                time_result = await self.scraper.selector_engine.resolve("extraction.match_list.match_time", dom_context)
                if time_result and time_result.element_info:
                    time_text = time_result.element_info.get('text', '').strip()
                    if time_text:
                        self.logger.info(f"Extracted kickoff time: '{time_text}' for {expected_status} match")
                        return time_text
                    else:
                        self.logger.warning(f"Time selector returned empty text for {expected_status} match")
                else:
                    self.logger.warning(f"Time selector failed or returned no element info for {expected_status} match")
            except Exception as e:
                self.logger.error(f"Error resolving match_time selector: {e}")
        
        return None
