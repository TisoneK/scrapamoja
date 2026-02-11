"""
Flashscore orchestrator that manages extractors and coordinates scraping operations.
"""
from typing import Dict, Any, Optional
import argparse

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.live_match_extractor import LiveMatchExtractor
from src.sites.flashscore.extractors.finished_match_extractor import FinishedMatchExtractor
from src.sites.flashscore.extractors.scheduled_match_extractor import ScheduledMatchExtractor


class FlashscoreOrchestrator:
    """Orchestrator for Flashscore scraping operations."""
    
    def __init__(self, scraper: FlashscoreScraper):
        self.scraper = scraper
        self.extractors = {
            'live': LiveMatchExtractor(scraper),
            'finished': FinishedMatchExtractor(scraper),
            'scheduled': ScheduledMatchExtractor(scraper)
        }
    
    async def scrape_data(self, args: argparse.Namespace) -> dict:
        """Scrape data based on arguments using appropriate extractor."""
        sport_config = self._get_sport_config(args.sport)
        
        # Get the appropriate extractor
        extractor = self.extractors.get(args.status)
        if not extractor:
            raise ValueError(f"Unknown status: {args.status}")
        
        # Extract matches using the dedicated extractor
        result = await extractor.extract_matches(sport_config, args.limit)
        
        return result
    
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
