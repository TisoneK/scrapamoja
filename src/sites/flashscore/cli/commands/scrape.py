"""
Scrape command for Flashscore data extraction.
"""
import argparse
import asyncio
import json
import sys
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
        """Run scrape command with interrupt handling support."""
        session = None
        
        try:
            # Initialize browser manager
            from src.browser.manager import BrowserManager
            browser_manager = BrowserManager()
            
            # Initialize scraper with interrupt handling
            from src.browser.config import BrowserConfiguration
            browser_config = BrowserConfiguration(headless=not args.no_headless)
            
            session = await browser_manager.create_session(browser_config)
            
            # Initialize selector engine
            from src.selectors import get_selector_engine
            selector_engine = get_selector_engine()
            
            scraper = FlashscoreScraper(
                page=await session.create_page(),
                selector_engine=selector_engine
            )
            
            # Initialize selectors asynchronously
            await scraper.initialize_selectors()
            
            # Initialize orchestrator
            from src.sites.flashscore.orchestrator import FlashscoreOrchestrator
            orchestrator = FlashscoreOrchestrator(scraper)
            
            # Scrape data using interrupt-aware scraper
            result = await scraper.scrape_with_interrupt_handling(
                orchestrator.scrape_data, args
            )
            
            # Output results
            if args.output:
                await self._write_to_file(json.dumps(result, indent=2), args.output)
                print(f"Results saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
            
            return 0
            
        except Exception as e:
            print(f"Scraping failed: {e}", file=sys.stderr)
            return 1
        
        finally:
            # Cleanup
            if session:
                try:
                    await browser_manager.close_session(session.session_id)
                except Exception as e:
                    print(f"Warning: Error during session cleanup: {e}", file=sys.stderr)
            
            # Additional cleanup for asyncio resources
            try:
                import asyncio
                import warnings
                
                # Suppress asyncio ResourceWarning during cleanup
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", ResourceWarning)
                    
                    # Wait for all pending tasks to complete (excluding Connection.run)
                    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
                    # Filter out Connection.run task which should keep running
                    filtered_tasks = [task for task in tasks if 'Connection.run' not in str(task.get_coro())]
                    if filtered_tasks:
                        await asyncio.gather(*filtered_tasks, return_exceptions=True)
                    
                    # Force cleanup of event loop
                    loop = asyncio.get_event_loop()
                    if loop and not loop.is_closed():
                        # Run a final iteration to process any remaining callbacks
                        await asyncio.sleep(0)
                        
                        # Close the event loop properly
                        loop.close()
                        
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
