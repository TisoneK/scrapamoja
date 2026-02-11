"""
Scrape command for Flashscore data extraction.
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional

from src.browser.manager import BrowserManager
from src.sites.flashscore.scraper import FlashscoreScraper


# Sport configurations
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


class ScrapeCommand:
    """Command for scraping Flashscore data."""
    
    help_text = "Scrape Flashscore data for specified sport and status"
    
    def __init__(self):
        self.browser_manager = BrowserManager()
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add command-specific arguments."""
        parser.add_argument(
            'sport',
            choices=list(sports.keys()),
            help='Sport to scrape'
        )
        parser.add_argument(
            'status',
            choices=['live', 'finished', 'scheduled'],
            help='Match status to scrape'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of matches to scrape'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path (default: stdout)'
        )
        parser.add_argument(
            '--no-headless',
            action='store_true',
            help='Run browser in non-headless mode (show window)'
        )
    
    async def execute(self, args: argparse.Namespace) -> int:
        """Run the scrape command."""
        session = None
        try:
            # Create browser configuration based on --no-headless flag
            from src.browser.config import BrowserConfiguration
            browser_config = BrowserConfiguration(headless=not args.no_headless)
            
            # Create browser session with proper configuration
            session = await self.browser_manager.create_session(configuration=browser_config)
            
            # Create a page in the session
            page = await session.create_page()
            
            # Create selector engine
            from src.selectors.engine import SelectorEngine
            selector_engine = SelectorEngine()
            
            # Create scraper
            scraper = FlashscoreScraper(page, selector_engine)
            
            # Initialize selector engine
            await scraper.initialize_selectors()
            
            # Navigate to Flashscore
            await scraper.navigate()
            
            # Scrape data using orchestrator
            result = await self._scrape_data(scraper, args)
            
            # Output results
            if args.output:
                await self._write_to_file(json.dumps(result, indent=2), args.output)
                print(f"Results saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
            
            return 0
            
        except Exception as e:
            print(f"Scraping failed: {e}", file=__import__('sys').stderr)
            return 1
        
        finally:
            # Cleanup
            if session:
                try:
                    await self.browser_manager.close_session(session.session_id)
                except Exception as e:
                    print(f"Warning: Error during session cleanup: {e}", file=__import__('sys').stderr)
            
            # Additional cleanup for asyncio resources
            try:
                import asyncio
                # Give asyncio a chance to clean up pending tasks
                await asyncio.sleep(0.1)
            except Exception:
                pass
    
    async def _scrape_data(self, scraper: FlashscoreScraper, args: argparse.Namespace) -> dict:
        """Scrape data based on arguments using the orchestrator."""
        from src.sites.flashscore.orchestrator import FlashscoreOrchestrator
        
        # Create orchestrator with scraper
        orchestrator = FlashscoreOrchestrator(scraper)
        
        # Use orchestrator to scrape data
        result = await orchestrator.scrape_data(args)
        
        return result
    
    async def _write_to_file(self, content: str, file_path: str):
        """Write content to file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
