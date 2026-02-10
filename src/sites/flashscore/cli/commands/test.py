"""
Test command implementation.

Tests navigation and selector functionality.
"""

import asyncio
import argparse
from typing import Dict, Any

from ...scraper import FlashscoreScraper
from ...selector_config import sports, match_status_detection
from ..utils.output import OutputFormatter


class TestCommand:
    """Command for testing scraper functionality."""
    
    help_text = "Test scraper functionality"
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add command-specific arguments."""
        parser.add_argument(
            'test_type',
            choices=['navigation', 'selectors', 'extraction'],
            help='Type of test to run'
        )
        
        parser.add_argument(
            '--sport',
            choices=list(sports.keys()),
            default='basketball',
            help='Sport to test (default: basketball)'
        )
        
        parser.add_argument(
            '--status',
            choices=['live', 'finished', 'scheduled'],
            default='live',
            help='Match status to test (default: live)'
        )
        
        parser.add_argument(
            '--headless',
            action='store_true',
            default=True,
            help='Run browser in headless mode'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Test timeout in seconds (default: 30)'
        )
    
    async def execute(self, args: argparse.Namespace) -> int:
        """Execute test command."""
        try:
            if args.test_type == 'navigation':
                return await self._test_navigation(args)
            elif args.test_type == 'selectors':
                return await self._test_selectors(args)
            elif args.test_type == 'extraction':
                return await self._test_extraction(args)
            else:
                print(f"Unknown test type: {args.test_type}")
                return 1
                
        except Exception as e:
            print(f"Test failed: {e}", file=__import__('sys').stderr)
            return 1
    
    async def _test_navigation(self, args: argparse.Namespace) -> int:
        """Test navigation functionality."""
        print(f"Testing navigation for {args.sport} {args.status} matches...")
        
        # Initialize scraper
        scraper = FlashscoreScraper(None, None)  # Will be initialized properly
        
        # Test navigation flow
        test_results = {
            'test_type': 'navigation',
            'sport': args.sport,
            'status': args.status,
            'results': []
        }
        
        try:
            # Navigate to home
            await scraper.navigate()
            test_results['results'].append({
                'test': 'navigate_home',
                'status': 'success',
                'message': 'Successfully navigated to home page'
            })
            
            # Navigate to sport
            sport_config = sports[args.sport]
            await scraper.flow.navigate_to_sport(sport_config['path_segment'])
            test_results['results'].append({
                'test': f'navigate_sport_{args.sport}',
                'status': 'success',
                'message': f'Successfully navigated to {sport_config["name"]}'
            })
            
            # Navigate to match status
            if args.status == 'live':
                await scraper.flow.navigate_to_live_games(sport_config['path_segment'])
                test_results['results'].append({
                    'test': 'navigate_live_games',
                    'status': 'success',
                    'message': 'Successfully navigated to live games'
                })
            elif args.status == 'finished':
                await scraper.flow.navigate_to_finished_games(sport_config['path_segment'])
                test_results['results'].append({
                    'test': 'navigate_finished_games',
                    'status': 'success',
                    'message': 'Successfully navigated to finished games'
                })
            elif args.status == 'scheduled':
                await scraper.flow.navigate_to_scheduled_games(sport_config['path_segment'])
                test_results['results'].append({
                    'test': 'navigate_scheduled_games',
                    'status': 'success',
                    'message': 'Successfully navigated to scheduled games'
                })
            
        except Exception as e:
            test_results['results'].append({
                'test': 'navigation_error',
                'status': 'error',
                'message': str(e)
            })
        
        # Output results
        formatter = OutputFormatter()
        output = formatter.format(test_results, 'json')
        print(output)
        
        # Return success if no errors
        has_errors = any(
            result.get('status') == 'error' 
            for result in test_results['results']
        )
        return 1 if has_errors else 0
    
    async def _test_selectors(self, args: argparse.Namespace) -> int:
        """Test selector functionality."""
        print(f"Testing selectors for {args.sport} {args.status} matches...")
        
        test_results = {
            'test_type': 'selectors',
            'sport': args.sport,
            'status': args.status,
            'results': []
        }
        
        try:
            # Initialize context manager
            selectors_root = Path(__file__).parent.parent.parent / 'selectors'
            context_manager = get_context_manager(selectors_root)
            
            # Set context
            await context_manager.set_context(
                primary_context=f"{args.sport}_{args.status}",
                dom_state="loaded"
            )
            
            test_results['results'].append({
                'test': 'context_set',
                'status': 'success',
                'message': f'Successfully set context: {args.sport}_{args.status}'
            })
            
            # Test selector loading
            context_loader = get_context_based_loader(selectors_root)
            selectors = await context_loader.load_selectors_for_context(
                f"{args.sport}_{args.status}"
            )
            
            if selectors:
                test_results['results'].append({
                    'test': 'selector_load',
                    'status': 'success',
                    'message': f'Loaded {len(selectors)} selectors'
                })
            else:
                test_results['results'].append({
                    'test': 'selector_load',
                    'status': 'error',
                    'message': 'No selectors loaded'
                })
        
        except Exception as e:
            test_results['results'].append({
                'test': 'selector_error',
                'status': 'error',
                'message': str(e)
            })
        
        # Output results
        formatter = OutputFormatter()
        output = formatter.format(test_results, 'json')
        print(output)
        
        has_errors = any(
            result.get('status') == 'error' 
            for result in test_results['results']
        )
        return 1 if has_errors else 0
    
    async def _test_extraction(self, args: argparse.Namespace) -> int:
        """Test data extraction."""
        print(f"Testing extraction for {args.sport} {args.status} matches...")
        
        test_results = {
            'test_type': 'extraction',
            'sport': args.sport,
            'status': args.status,
            'results': []
        }
        
        try:
            # This would require actual browser automation
            # For now, just test the extraction configuration
            sport_config = sports[args.sport]
            extraction_types = sport_config.get('extraction_types', {})
            
            if extraction_types:
                test_results['results'].append({
                    'test': 'extraction_config',
                    'status': 'success',
                    'message': f'Found extraction types: {list(extraction_types.keys())}'
                })
            else:
                test_results['results'].append({
                    'test': 'extraction_config',
                    'status': 'warning',
                    'message': 'No extraction types configured'
                })
        
        except Exception as e:
            test_results['results'].append({
                'test': 'extraction_error',
                'status': 'error',
                'message': str(e)
            })
        
        # Output results
        formatter = OutputFormatter()
        output = formatter.format(test_results, 'json')
        print(output)
        
        has_errors = any(
            result.get('status') == 'error' 
            for result in test_results['results']
        )
        return 1 if has_errors else 0
