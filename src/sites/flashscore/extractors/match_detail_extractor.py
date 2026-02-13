"""
Match detail extractor for Flashscore match pages.

Handles extraction of detailed match data from individual match pages
including primary and tertiary tab data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.models import StructuredMatch, PageState, ExtractionMetadata
from datetime import datetime
import asyncio


class MatchDetailExtractor(ABC):
    """Base class for match detail extraction from individual match pages."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.logger = self._get_logger()
        self.page = scraper.page
    
    def _get_logger(self):
        """Get logger instance."""
        from src.observability.logger import get_logger
        return get_logger(f"flashscore.match_detail_extractor.{self.__class__.__name__.lower()}")
    
    async def extract(self, page_state: PageState, timeout: int = 10000) -> Optional[StructuredMatch]:
        """
        Extract complete match data from match detail page.
        
        Args:
            page_state: Current page state with match information
            timeout: Maximum time to wait for extraction in milliseconds
            
        Returns:
            StructuredMatch object with all extracted data, or None if extraction fails
        """
        start_time = datetime.utcnow()
        retry_count = 0
        
        try:
            # Validate page structure before extraction
            if not await self._validate_page_structure(page_state):
                self.logger.warning(f"Page structure validation failed for match {page_state.match_id}")
                return None
            
            # Extract basic match information
            basic_info = await self._extract_basic_info(page_state)
            if not basic_info:
                self.logger.error(f"Failed to extract basic info for match {page_state.match_id}")
                return None
            
            # Extract data from available tabs
            extracted_tabs = []
            failed_tabs = []
            
            summary_data = await self._extract_summary_tab(page_state)
            if summary_data:
                extracted_tabs.append('summary')
            else:
                failed_tabs.append('summary')
            
            h2h_data = await self._extract_h2h_tab(page_state)
            if h2h_data:
                extracted_tabs.append('h2h')
            else:
                failed_tabs.append('h2h')
            
            odds_data = await self._extract_odds_tab(page_state)
            if odds_data:
                extracted_tabs.append('odds')
            else:
                failed_tabs.append('odds')
            
            stats_data = await self._extract_stats_tab(page_state)
            if stats_data:
                extracted_tabs.append('stats')
            else:
                failed_tabs.append('stats')
            
            # Extract tertiary tabs
            tertiary_data = await self._extract_tertiary_tabs(page_state)
            if tertiary_data and (tertiary_data.inc_ot or tertiary_data.ft or tertiary_data.q1):
                extracted_tabs.append('tertiary')
            else:
                failed_tabs.append('tertiary')
            
            # Calculate completeness score
            total_expected_tabs = len(['summary', 'h2h', 'odds', 'stats', 'tertiary'])
            completeness_score = len(extracted_tabs) / total_expected_tabs
            
            # Create extraction metadata
            extraction_duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            extraction_metadata = ExtractionMetadata(
                tabs_extracted=extracted_tabs,
                failed_tabs=failed_tabs,
                extraction_duration_ms=extraction_duration,
                retry_count=retry_count
            )
            
            # Create structured match
            structured_match = StructuredMatch(
                match_id=page_state.match_id,
                metadata=self._create_match_metadata(page_state, completeness_score),
                basic_info=basic_info,
                summary_tab=summary_data,
                h2h_tab=h2h_data,
                odds_tab=odds_data,
                stats_tab=stats_data,
                tertiary_tabs=tertiary_data,
                extraction_metadata=extraction_metadata
            )
            
            # Log performance metrics
            self.logger.info(f"Match {page_state.match_id} extraction completed in {extraction_duration}ms "
                           f"({completeness_score:.1%} completeness, {len(extracted_tabs)}/{total_expected_tabs} tabs)")
            
            return structured_match
            
        except Exception as e:
            self.logger.error(f"Error extracting match data for {page_state.match_id}: {e}")
            return None
    
    async def _validate_page_structure(self, page_state: PageState) -> bool:
        """Validate that the match detail page has the expected structure."""
        try:
            if not page_state.verified:
                return False
            
            # Check for match-specific content
            match_content = await self.page.query_selector('.matchDetail, .matchHeader, .event')
            if not match_content:
                self.logger.warning("No match-specific content found on page")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating page structure: {e}")
            return False
    
    async def _extract_basic_info(self, page_state: PageState) -> Optional[Any]:
        """Extract basic match information from the page."""
        try:
            # This would be implemented by concrete extractors
            # For now, return a placeholder
            from src.sites.flashscore.models import BasicMatchInfo
            return BasicMatchInfo(
                home_team="Unknown",
                away_team="Unknown", 
                current_score=None,
                match_time="Unknown",
                status="Unknown"
            )
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {e}")
            return None
    
    @abstractmethod
    async def _extract_summary_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from SUMMARY tab."""
        pass
    
    @abstractmethod
    async def _extract_h2h_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from H2H tab."""
        pass
    
    @abstractmethod
    async def _extract_odds_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from ODDS tab."""
        pass
    
    @abstractmethod
    async def _extract_stats_tab(self, page_state: PageState) -> Optional[Any]:
        """Extract data from STATS tab."""
        pass
    
    @abstractmethod
    async def _extract_tertiary_tabs(self, page_state: PageState) -> Optional[Any]:
        """Extract data from tertiary tabs."""
        pass
    
    def _create_match_metadata(self, page_state: PageState, completeness_score: float) -> Any:
        """Create match metadata object."""
        from src.sites.flashscore.models import MatchMetadata
        return MatchMetadata(
            extraction_time=datetime.utcnow(),
            source_url=page_state.url,
            sport="basketball",
            completeness_score=completeness_score
        )
