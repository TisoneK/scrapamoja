"""
Updated Flashscore scraper with new snapshot integration.

This module demonstrates how to integrate the new context-aware snapshot system
into an existing site scraper with minimal code changes.
"""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.scheduled_match_extractor import ScheduledMatchExtractor
from src.sites.flashscore.extractors.live_match_extractor import LiveMatchExtractor
from src.sites.flashscore.extractors.finished_match_extractor import FinishedMatchExtractor
from src.sites.flashscore.extractors.basketball_match_detail_extractor import BasketballMatchDetailExtractor
from src.sites.flashscore.flow import FlashscoreFlow
from src.sites.flashscore.models import StructuredMatch, NavigationState, PageState, MatchListing
from src.interrupt_handling.integration import InterruptAwareScraper

# Import new snapshot integration
from src.sites.site_snapshot_integration import ScraperSnapshotMixin, create_flashscore_snapshot_manager
from src.core.snapshot.config_presets import CaptureEnvironment


class UpdatedFlashscoreScraper(ScraperSnapshotMixin, FlashscoreScraper):
    """
    Updated Flashscore scraper with integrated snapshot functionality.
    
    This class extends the original FlashscoreScraper with snapshot capabilities
    using the ScraperSnapshotMixin for minimal code changes.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize snapshot functionality
        self.initialize_snapshots("flashscore", CaptureEnvironment.PRODUCTION)
        
        # Create extractors with snapshot support
        self.extractors = {
            'live': LiveMatchExtractor(self),
            'finished': FinishedMatchExtractor(self),
            'scheduled': ScheduledMatchExtractor(self)
        }
        self.flow = FlashscoreFlow(self.page, self.selector_engine)
        self.match_detail_extractor = BasketballMatchDetailExtractor(self)
    
    async def navigate_to_basketball(self) -> bool:
        """Navigate to basketball section with snapshot capture."""
        try:
            # Capture before navigation
            await self.capture_page_snapshot(self.page, "before_basketball_navigation")
            
            # Original navigation logic
            success = await super().navigate_to_basketball()
            
            if success:
                # Capture successful navigation
                await self.capture_page_snapshot(self.page, "successful_basketball_navigation")
            else:
                # Capture navigation failure
                await self.handle_failure(self.page, "navigation_failure", "Failed to navigate to basketball")
            
            return success
            
        except Exception as e:
            # Automatic failure snapshot
            await self.handle_failure(self.page, "navigation_error", str(e))
            raise
    
    async def extract_live_matches(self) -> List[StructuredMatch]:
        """Extract live matches with snapshot capture."""
        try:
            # Capture before extraction
            await self.capture_page_snapshot(self.page, "before_live_matches_extraction")
            
            # Extract matches
            matches = await self.extractors['live'].extract(self.page)
            
            # Capture successful extraction
            await self.capture_page_snapshot(
                self.page, 
                "successful_live_extraction", 
                matches_count=len(matches)
            )
            
            return matches
            
        except Exception as e:
            # Capture extraction failure
            await self.handle_failure(self.page, "live_extraction_error", str(e))
            raise
    
    async def extract_scheduled_matches(self) -> List[StructuredMatch]:
        """Extract scheduled matches with snapshot capture."""
        try:
            await self.capture_page_snapshot(self.page, "before_scheduled_matches_extraction")
            
            matches = await self.extractors['scheduled'].extract(self.page)
            
            await self.capture_page_snapshot(
                self.page,
                "successful_scheduled_extraction", 
                matches_count=len(matches)
            )
            
            return matches
            
        except Exception as e:
            await self.handle_failure(self.page, "scheduled_extraction_error", str(e))
            raise
    
    async def extract_finished_matches(self) -> List[StructuredMatch]:
        """Extract finished matches with snapshot capture."""
        try:
            await self.capture_page_snapshot(self.page, "before_finished_matches_extraction")
            
            matches = await self.extractors['finished'].extract(self.page)
            
            await self.capture_page_snapshot(
                self.page,
                "successful_finished_extraction",
                matches_count=len(matches)
            )
            
            return matches
            
        except Exception as e:
            await self.handle_failure(self.page, "finished_extraction_error", str(e))
            raise
    
    async def extract_match_details(self, match_url: str) -> Optional[StructuredMatch]:
        """Extract match details with snapshot capture."""
        try:
            # Capture before navigation to match details
            await self.capture_page_snapshot(
                self.page, 
                "before_match_details_navigation", 
                match_url=match_url
            )
            
            # Navigate to match details
            success = await self.navigate_to_match(match_url)
            
            if not success:
                await self.handle_failure(
                    self.page, 
                    "match_navigation_failure", 
                    f"Failed to navigate to match: {match_url}"
                )
                return None
            
            # Capture match page
            await self.capture_page_snapshot(
                self.page,
                "match_page_loaded",
                match_url=match_url
            )
            
            # Extract details
            match_details = await self.match_detail_extractor.extract(self.page)
            
            if match_details:
                await self.capture_page_snapshot(
                    self.page,
                    "successful_match_details_extraction",
                    match_url=match_url,
                    has_details=True
                )
            else:
                await self.handle_failure(
                    self.page,
                    "match_details_extraction_failed",
                    f"No details extracted for match: {match_url}"
                )
            
            return match_details
            
        except Exception as e:
            await self.handle_failure(
                self.page,
                "match_details_extraction_error",
                str(e),
                match_url=match_url
            )
            raise


class UpdatedFlashscoreOrchestrator:
    """
    Updated orchestrator with snapshot integration.
    
    This orchestrator uses the updated scraper with built-in snapshot capabilities.
    """
    
    def __init__(self, scraper: UpdatedFlashscoreScraper):
        self.scraper = scraper
        self.snapshot_manager = create_flashscore_snapshot_manager()
        
        # Extractors are already created in the updated scraper
        self.extractors = scraper.extractors
        self.flow = scraper.flow
        self.match_detail_extractor = scraper.match_detail_extractor
        
        # Ensure scraper has interrupt handling capabilities
        if not isinstance(scraper, InterruptAwareScraper):
            raise TypeError("Scraper must inherit from InterruptAwareScraper for interrupt handling support")
    
    async def execute_basketball_workflow(self, limit: Optional[int] = None) -> List[StructuredMatch]:
        """
        Execute the complete basketball workflow with integrated snapshot capture.
        
        This method demonstrates the workflow with automatic snapshot capture
        at key points and failure handling.
        """
        try:
            # Capture workflow start
            await self.snapshot_manager.capture_scraping_snapshot(
                self.scraper.page,
                function_name="basketball_workflow_start",
                limit=limit
            )
            
            # Navigate to basketball section
            navigation_success = await self.scraper.navigate_to_basketball()
            
            if not navigation_success:
                await self.snapshot_manager.capture_failure_snapshot(
                    self.scraper.page,
                    "workflow_navigation_failure",
                    "Failed to navigate to basketball section"
                )
                return []
            
            # Extract all match types
            live_matches = await self.scraper.extract_live_matches()
            scheduled_matches = await self.scraper.extract_scheduled_matches()
            finished_matches = await self.scraper.extract_finished_matches()
            
            all_matches = live_matches + scheduled_matches + finished_matches
            
            # Apply limit if specified
            if limit and len(all_matches) > limit:
                all_matches = all_matches[:limit]
            
            # Extract details for a sample of matches
            detailed_matches = []
            for i, match in enumerate(all_matches[:min(5, len(all_matches))]):  # Limit to 5 for demo
                if match.url:
                    details = await self.scraper.extract_match_details(match.url)
                    if details:
                        detailed_matches.append(details)
            
            # Capture workflow completion
            await self.snapshot_manager.capture_scraping_snapshot(
                self.scraper.page,
                function_name="basketball_workflow_complete",
                total_matches=len(all_matches),
                detailed_matches=len(detailed_matches)
            )
            
            return all_matches
            
        except Exception as e:
            # Capture workflow failure
            await self.snapshot_manager.capture_failure_snapshot(
                self.scraper.page,
                "basketball_workflow_error",
                str(e),
                limit=limit
            )
            raise


# Example usage function
async def run_updated_flashscore_workflow():
    """Example of running the updated Flashscore workflow with snapshots."""
    
    # Create updated scraper with snapshot integration
    scraper = UpdatedFlashscoreScraper()
    
    # Create orchestrator
    orchestrator = UpdatedFlashscoreOrchestrator(scraper)
    
    # Execute workflow with automatic snapshot capture
    matches = await orchestrator.execute_basketball_workflow(limit=10)
    
    print(f"Extracted {len(matches)} matches with automatic snapshot capture")
    return matches


# Migration helper for existing scrapers
def migrate_existing_scraper(existing_scraper_class) -> type:
    """
    Helper function to migrate an existing scraper class to use snapshots.
    
    This function creates a new class that inherits from both the existing
    scraper and the ScraperSnapshotMixin.
    """
    
    class MigratedScraper(ScraperSnapshotMixin, existing_scraper_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Initialize snapshots with site name from class name
            site_name = existing_scraper_class.__name__.lower().replace('scraper', '')
            self.initialize_snapshots(site_name, CaptureEnvironment.PRODUCTION)
    
    return MigratedScraper
