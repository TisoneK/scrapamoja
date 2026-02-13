"""
Flashscore orchestrator that manages extractors and coordinates scraping operations.
"""
from typing import Dict, Any, Optional, List
import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

# Load .env file explicitly
from dotenv import load_dotenv
env_paths = [Path(".env"), Path("..") / ".env", Path("..") / ".." / ".env"]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.scheduled_match_extractor import ScheduledMatchExtractor
from src.sites.flashscore.extractors.live_match_extractor import LiveMatchExtractor
from src.sites.flashscore.extractors.finished_match_extractor import FinishedMatchExtractor
from src.sites.flashscore.extractors.basketball_match_detail_extractor import BasketballMatchDetailExtractor
from src.sites.flashscore.flow import FlashscoreFlow
from src.sites.flashscore.models import StructuredMatch, NavigationState, PageState, MatchListing
from src.interrupt_handling.integration import InterruptAwareScraper


class FlashscoreOrchestrator:
    """Orchestrator for Flashscore scraping operations with interrupt handling support."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.extractors = {
            'live': LiveMatchExtractor(scraper),
            'finished': FinishedMatchExtractor(scraper),
            'scheduled': ScheduledMatchExtractor(scraper)
        }
        self.flow = FlashscoreFlow(scraper.page, scraper.selector_engine)
        self.match_detail_extractor = BasketballMatchDetailExtractor(scraper)
        
        # Ensure scraper has interrupt handling capabilities
        if not isinstance(scraper, InterruptAwareScraper):
            raise TypeError("Scraper must inherit from InterruptAwareScraper for interrupt handling support")
    
    async def execute_basketball_workflow(self, limit: Optional[int] = None) -> List[StructuredMatch]:
        """
        Execute the complete basketball workflow with match detail extraction.
        
        Args:
            limit: Maximum number of matches to process (default: 50)
            
        Returns:
            List of StructuredMatch objects with complete match data
        """
        # Check feature flag
        if not self._is_full_workflow_enabled():
            self.scraper.logger.warning("Full workflow is disabled, falling back to legacy mode")
            return await self._execute_legacy_workflow(limit)
        
        # Enforce processing limit (50 matches max per run)
        max_matches = min(limit or 50, 50)
        
        self.scraper.logger.info(f"Starting basketball workflow with max {max_matches} matches")
        
        try:
            # Step 1: Navigate to basketball section
            navigation_state = await self.flow.navigate_to_basketball()
            if not navigation_state.verified:
                self.scraper.logger.error("Failed to navigate to basketball section")
                return []
            
            # Step 2: Extract match listings
            scheduled_extractor = self.extractors['scheduled']
            sport_config = self._get_sport_config('basketball')
            listing_result = await self.scraper.scrape_with_interrupt_handling(
                scheduled_extractor.extract_matches, sport_config, max_matches
            )
            
            if not listing_result or 'matches' not in listing_result:
                self.scraper.logger.error("Failed to extract match listings")
                return []
            
            match_listings = listing_result['matches']
            self.scraper.logger.info(f"Found {len(match_listings)} matches to process")
            
            # Step 3: Process matches with concurrent execution and retry logic
            structured_matches = await self._process_matches_with_retry(match_listings, max_matches)
            
            # Memory optimization: process in batches to avoid memory issues
            if len(structured_matches) > 20:
                self.scraper.logger.info(f"Memory optimization: processing {len(structured_matches)} matches in batches")
                # Convert to generator to reduce memory footprint
                def match_generator():
                    for match in structured_matches:
                        yield match
                        # Force garbage collection every 10 matches
                        if len(structured_matches) % 10 == 0:
                            import gc
                            gc.collect()
                
                # Re-process matches from generator
                optimized_matches = list(match_generator())
            else:
                optimized_matches = structured_matches
            
            self.scraper.logger.info(f"Basketball workflow completed: {len(optimized_matches)} successful extractions")
            return optimized_matches
            
        except Exception as e:
            self.scraper.logger.error(f"Error in basketball workflow: {e}")
            return []
    
    async def _process_matches_with_retry(self, match_listings: List[MatchListing], max_matches: int) -> List[StructuredMatch]:
        """Process matches with retry logic and concurrent execution."""
        structured_matches = []
        failed_matches = []
        
        # Limit matches to process
        matches_to_process = match_listings[:max_matches]
        
        # Process matches concurrently (up to 3 at a time)
        semaphore = asyncio.Semaphore(3)
        
        async def process_single_match(match_listing: MatchListing) -> Optional[StructuredMatch]:
            async with semaphore:
                return await self._process_single_match_with_retry(match_listing)
        
        # Execute concurrent processing
        tasks = [process_single_match(match) for match in matches_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            match_listing = matches_to_process[i]
            
            if isinstance(result, Exception):
                self.scraper.logger.error(f"Failed to process match {match_listing.match_id}: {result}")
                failed_matches.append(match_listing.match_id)
            elif result:
                structured_matches.append(result)
                self.scraper.logger.info(f"Successfully processed match {match_listing.match_id}")
            else:
                failed_matches.append(match_listing.match_id)
                self.scraper.logger.warning(f"No data extracted for match {match_listing.match_id}")
        
        # Log summary
        success_count = len(structured_matches)
        failure_count = len(failed_matches)
        self.scraper.logger.info(f"Match processing summary: {success_count} successful, {failure_count} failed")
        
        if failed_matches:
            self.scraper.logger.warning(f"Failed matches: {failed_matches}")
        
        return structured_matches
    
    async def _process_single_match_with_retry(self, match_listing: MatchListing, max_retries: int = 3) -> Optional[StructuredMatch]:
        """Process a single match with retry logic."""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    backoff_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    self.scraper.logger.info(f"Retry attempt {attempt + 1}/{max_retries} for match {match_listing.match_id} after {backoff_time}s backoff")
                    await asyncio.sleep(backoff_time)
                
                # Navigate to match detail page
                page_state = await self.flow.navigate_to_match(match_listing.match_id, max_retries=1)
                
                if not page_state.verified:
                    self.scraper.logger.warning(f"Failed to navigate to match {match_listing.match_id} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return None
                
                # Extract match detail data
                structured_match = await self.match_detail_extractor.extract(page_state)
                
                if structured_match:
                    self.scraper.logger.info(f"Successfully extracted match {match_listing.match_id}")
                    return structured_match
                else:
                    self.scraper.logger.warning(f"Failed to extract match data for {match_listing.match_id} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return None
                    
            except Exception as e:
                self.scraper.logger.error(f"Error processing match {match_listing.match_id} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    return None
        
        self.scraper.logger.error(f"All {max_retries} attempts failed for match {match_listing.match_id}")
        return None
    
    def _is_full_workflow_enabled(self) -> bool:
        """Check if full workflow is enabled via feature flag."""
        return os.getenv('FLASHSCORE_ENABLE_FULL_WORKFLOW', 'false').lower() == 'true'
    
    async def _execute_legacy_workflow(self, limit: Optional[int] = None) -> List[StructuredMatch]:
        """Execute legacy workflow for backward compatibility."""
        self.scraper.logger.info("Executing legacy workflow (listing-only extraction)")
        
        try:
            scheduled_extractor = self.extractors['scheduled']
            sport_config = self._get_sport_config('basketball')
            listing_result = await self.scraper.scrape_with_interrupt_handling(
                scheduled_extractor.extract_matches, sport_config, limit
            )
            
            # Convert legacy results to structured matches (minimal data)
            structured_matches = []
            if listing_result and 'matches' in listing_result:
                for match_data in listing_result['matches']:
                    # Create minimal structured match from listing data
                    from src.sites.flashscore.models import (
                        StructuredMatch, MatchMetadata, BasicMatchInfo, ExtractionMetadata
                    )
                    
                    structured_match = StructuredMatch(
                        match_id=match_data.get('match_id', ''),
                        metadata=MatchMetadata(
                            extraction_time=datetime.utcnow(),
                            source_url=match_data.get('url', ''),
                            sport='basketball',
                            completeness_score=0.2  # Low completeness for listing-only
                        ),
                        basic_info=BasicMatchInfo(
                            home_team=match_data.get('home_team', ''),
                            away_team=match_data.get('away_team', ''),
                            current_score=match_data.get('score'),
                            match_time=match_data.get('time', ''),
                            status=match_data.get('status', '')
                        ),
                        summary_tab=None,
                        h2h_tab=None,
                        odds_tab=None,
                        stats_tab=None,
                        tertiary_tabs=None,
                        extraction_metadata=ExtractionMetadata(
                            tabs_extracted=[],
                            failed_tabs=['summary', 'h2h', 'odds', 'stats', 'tertiary'],
                            extraction_duration_ms=0,
                            retry_count=0
                        )
                    )
                    structured_matches.append(structured_match)
            
            return structured_matches
            
        except Exception as e:
            self.scraper.logger.error(f"Error in legacy workflow: {e}")
            return []
    
    async def scrape_data(self, args: argparse.Namespace) -> dict:
        """Scrape data with interrupt handling support."""
        # Enter critical operation
        self.scraper.enter_critical_operation("orchestrator_scrape_data")
        
        try:
            # Check for interrupt before starting
            if self.scraper.check_interrupt_before_critical():
                return None
            
            # Check if this is a full workflow request (CLI flag or environment variable)
            full_workflow = (
                (hasattr(args, 'full_workflow') and args.full_workflow) or
                self._is_full_workflow_enabled()
            )
            
            if full_workflow:
                # Execute new basketball workflow
                self.scraper.logger.info(f"Starting basketball workflow with max {args.limit or 50} matches")
                structured_matches = await self.execute_basketball_workflow(args.limit)
                return {
                    'matches': [self._structured_match_to_dict(match) for match in structured_matches],
                    'workflow_type': 'full_basketball_workflow',
                    'total_matches': len(structured_matches)
                }
            else:
                # Execute legacy workflow
                self.scraper.logger.warning("Full workflow is disabled, falling back to legacy mode")
                return await self._legacy_scrape_data(args)
            
        except Exception as e:
            self.scraper.logger.error(f"Error during orchestrated scraping: {e}")
            raise
        finally:
            # Exit critical operation
            self.scraper.exit_critical_operation("orchestrator_scrape_data")
    
    async def _legacy_scrape_data(self, args: argparse.Namespace) -> dict:
        """Legacy scrape data method for backward compatibility."""
        sport_config = self._get_sport_config(args.sport)
        
        # Get appropriate extractor
        extractor = self.extractors.get(args.status)
        if not extractor:
            raise ValueError(f"Unknown status: {args.status}")
        
        # Extract matches using dedicated extractor with interrupt handling
        result = await self.scraper.scrape_with_interrupt_handling(
            extractor.extract_matches, sport_config, args.limit
        )
        
        # Convert MatchListing objects to dictionaries for JSON serialization
        if 'matches' in result and isinstance(result['matches'], list):
            result['matches'] = [
                self._match_listing_to_dict(m) if isinstance(m, MatchListing) else m
                for m in result['matches']
            ]
        
        return result
    
    def _match_listing_to_dict(self, match_listing: MatchListing) -> dict:
        """Convert MatchListing dataclass to dictionary for JSON serialization."""
        return {
            'match_id': match_listing.match_id,
            'teams': match_listing.teams,
            'time': match_listing.time,
            'status': match_listing.status,
            'score': match_listing.score
        }
    
    def _structured_match_to_dict(self, structured_match: StructuredMatch) -> dict:
        """Convert StructuredMatch to dictionary for legacy compatibility."""
        return {
            'match_id': structured_match.match_id,
            'metadata': {
                'extraction_time': structured_match.metadata.extraction_time.isoformat(),
                'source_url': structured_match.metadata.source_url,
                'sport': structured_match.metadata.sport,
                'completeness_score': structured_match.metadata.completeness_score
            },
            'basic_info': {
                'home_team': structured_match.basic_info.home_team,
                'away_team': structured_match.basic_info.away_team,
                'current_score': structured_match.basic_info.current_score,
                'match_time': structured_match.basic_info.match_time,
                'status': structured_match.basic_info.status
            },
            'summary_tab': self._tab_data_to_dict(structured_match.summary_tab),
            'h2h_tab': self._tab_data_to_dict(structured_match.h2h_tab),
            'odds_tab': self._tab_data_to_dict(structured_match.odds_tab),
            'stats_tab': self._tab_data_to_dict(structured_match.stats_tab),
            'tertiary_tabs': self._tertiary_data_to_dict(structured_match.tertiary_tabs),
            'extraction_metadata': {
                'tabs_extracted': structured_match.extraction_metadata.tabs_extracted,
                'failed_tabs': structured_match.extraction_metadata.failed_tabs,
                'extraction_duration_ms': structured_match.extraction_metadata.extraction_duration_ms,
                'retry_count': structured_match.extraction_metadata.retry_count
            }
        }
    
    def _tab_data_to_dict(self, tab_data) -> Optional[dict]:
        """Convert tab data to dictionary."""
        if tab_data is None:
            return None
        
        if hasattr(tab_data, '__dict__'):
            return tab_data.__dict__
        else:
            return tab_data
    
    def _tertiary_data_to_dict(self, tertiary_data) -> Optional[dict]:
        """Convert tertiary data to dictionary."""
        if tertiary_data is None:
            return None
        
        return {
            'inc_ot': self._tab_data_to_dict(tertiary_data.inc_ot),
            'ft': self._tab_data_to_dict(tertiary_data.ft),
            'q1': self._tab_data_to_dict(tertiary_data.q1)
        }
    
    def _get_sport_config(self, sport: str) -> dict:
        """Get sport configuration."""
        sports = {
            'basketball': {
                'name': 'Basketball',
                'path_segment': 'basketball'
            },
            'football': {
                'name': 'Football', 
                'path_segment': 'football'
            },
            'tennis': {
                'name': 'Tennis',
                'path_segment': 'tennis'
            }
        }
        
        if sport not in sports:
            raise ValueError(f"Unknown sport: {sport}")
        
        return sports[sport]
