"""
Validate command implementation.

Validates selectors and configuration.
"""

import asyncio
from pathlib import Path
import argparse
from typing import List, Dict, Any

from ...selector_config import selector_config, sports, navigation_hierarchy
from ..utils.output import OutputFormatter


class ValidateCommand:
    """Command for validating selectors and configuration."""
    
    help_text = "Validate selectors and configuration"
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add command-specific arguments."""
        parser.add_argument(
            '--selectors',
            action='store_true',
            help='Validate selector files'
        )
        
        parser.add_argument(
            '--config',
            action='store_true',
            help='Validate configuration files'
        )
        
        parser.add_argument(
            '--sport',
            choices=list(sports.keys()),
            help='Validate specific sport selectors'
        )
        
        parser.add_argument(
            '--status',
            choices=['live', 'finished', 'scheduled'],
            help='Validate specific match status selectors'
        )
        
        parser.add_argument(
            '--html-structure',
            action='store_true',
            help='Validate HTML structure references'
        )
    
    async def execute(self, args: argparse.Namespace) -> int:
        """Execute validate command."""
        try:
            validation_results = {}
            
            if args.config or not args.selectors:
                validation_results['config'] = await self._validate_config()
            
            if args.selectors:
                validation_results['selectors'] = await self._validate_selectors(args)
            
            if args.html_structure:
                validation_results['html_structure'] = await self._validate_html_structure()
            
            # Output results
            formatter = OutputFormatter()
            output = formatter.format(validation_results, 'json')
            print(output)
            
            # Return appropriate exit code
            has_errors = any(
                result.get('status') == 'error' 
                for result in validation_results.values()
            )
            return 1 if has_errors else 0
            
        except Exception as e:
            print(f"Validation failed: {e}", file=__import__('sys').stderr)
            return 1
    
    async def _validate_config(self) -> dict:
        """Validate configuration files."""
        results = {
            'status': 'success',
            'checks': []
        }
        
        try:
            # Check selector config
            if 'sports' not in selector_config:
                results['checks'].append({
                    'check': 'selector_config_structure',
                    'status': 'error',
                    'message': 'Missing sports configuration'
                })
                results['status'] = 'error'
            else:
                results['checks'].append({
                    'check': 'selector_config_structure',
                    'status': 'success',
                    'message': 'Configuration structure is valid'
                })
            
            # Check sport configurations
            for sport_name, sport_config in sports.items():
                if not sport_config.get('name'):
                    results['checks'].append({
                        'check': f'sport_config_{sport_name}',
                        'status': 'error',
                        'message': f'Missing name for sport {sport_name}'
                    })
                    results['status'] = 'error'
                else:
                    results['checks'].append({
                        'check': f'sport_config_{sport_name}',
                        'status': 'success',
                        'message': f'Sport {sport_name} config is valid'
                    })
        
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
        
        return results
    
    async def _validate_selectors(self, args: argparse.Namespace) -> dict:
        """Validate selector files."""
        results = {
            'status': 'success',
            'checks': []
        }
        
        try:
            selectors_root = Path(__file__).parent.parent.parent / 'selectors'
            
            # Validate specific sport/status combination
            if args.sport and args.status:
                sport_path = selectors_root / 'navigation' / 'primary_tabs' / args.status / args.sport
                if not sport_path.exists():
                    results['checks'].append({
                        'check': f'selectors_{args.sport}_{args.status}',
                        'status': 'error',
                        'message': f'Missing selectors for {args.sport} {args.status}'
                    })
                    results['status'] = 'error'
                else:
                    # Check for required selector files
                    required_tabs = navigation_hierarchy['primary_tabs'][args.status]
                    for tab in required_tabs:
                        selector_file = sport_path / f'{tab}_tab.yaml'
                        if not selector_file.exists():
                            results['checks'].append({
                                'check': f'selector_file_{tab}',
                                'status': 'error',
                                'message': f'Missing selector: {selector_file}'
                            })
                            results['status'] = 'error'
                        else:
                            results['checks'].append({
                                'check': f'selector_file_{tab}',
                                'status': 'success',
                                'message': f'Selector exists: {tab}'
                            })
            
            # Validate all selectors if no specific sport/status
            else:
                for status in ['live', 'finished', 'scheduled']:
                    for sport in sports.keys():
                        sport_path = selectors_root / 'navigation' / 'primary_tabs' / status / sport
                        if sport_path.exists():
                            selector_files = list(sport_path.glob('*.yaml'))
                            results['checks'].append({
                                'check': f'selectors_{sport}_{status}',
                                'status': 'success',
                                'message': f'Found {len(selector_files)} selectors for {sport} {status}'
                            })
        
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
        
        return results
    
    async def _validate_html_structure(self) -> dict:
        """Validate HTML structure references."""
        results = {
            'status': 'success',
            'checks': []
        }
        
        try:
            html_root = Path(__file__).parent.parent.parent / 'html_structure'
            required_files = [
                'match_page_live.html',
                'match_page_finished.html',
                'match_page_scheduled.html'
            ]
            
            for html_file in required_files:
                file_path = html_root / html_file
                if file_path.exists():
                    results['checks'].append({
                        'check': f'html_file_{html_file}',
                        'status': 'success',
                        'message': f'HTML file exists: {html_file}'
                    })
                else:
                    results['checks'].append({
                        'check': f'html_file_{html_file}',
                        'status': 'error',
                        'message': f'Missing HTML file: {html_file}'
                    })
                    results['status'] = 'error'
        
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
        
        return results
