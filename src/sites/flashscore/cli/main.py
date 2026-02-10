#!/usr/bin/env python3
"""
Flashscore CLI main entry point.

Provides command-line interface for Flashscore scraping operations.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional, List
import json

from ..scraper import FlashscoreScraper
from ..config import SITE_CONFIG
from ..selector_config import sports, match_status_detection
from .commands.scrape import ScrapeCommand
from .commands.validate import ValidateCommand
from .commands.test import TestCommand
from .utils.output import OutputFormatter
from .utils.config import CLIConfig


class FlashscoreCLI:
    """Main CLI class for Flashscore scraper."""
    
    def __init__(self):
        self.config = CLIConfig()
        self.output_formatter = OutputFormatter()
        
        # Initialize commands
        self.commands = {
            'scrape': ScrapeCommand(),
            'validate': ValidateCommand(),
            'test': TestCommand()
        }
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog='flashscore-cli',
            description='Flashscore scraper CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s scrape basketball live --output json
  %(prog)s validate selectors --sport basketball
  %(prog)s test navigation --status live
            """
        )
        
        # Global arguments
        parser.add_argument(
            '--config',
            type=str,
            help='Path to configuration file'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress output except errors'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands',
            required=True
        )
        
        # Add command parsers
        for cmd_name, cmd_class in self.commands.items():
            cmd_parser = subparsers.add_parser(
                cmd_name,
                help=cmd_class.help_text
            )
            cmd_class.add_arguments(cmd_parser)
        
        return parser
    
    async def run(self, args: argparse.Namespace) -> int:
        """Run CLI with given arguments."""
        try:
            # Load configuration
            if args.config:
                await self.config.load_from_file(args.config)
            
            # Set logging level
            self._setup_logging(args.verbose, args.quiet)
            
            # Execute command
            if args.command in self.commands:
                return await self.commands[args.command].execute(args)
            else:
                print(f"Unknown command: {args.command}", file=sys.stderr)
                return 1
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def _setup_logging(self, verbose: bool, quiet: bool):
        """Setup logging based on verbosity."""
        import logging
        
        if quiet:
            level = logging.ERROR
        elif verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO
            
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


async def main():
    """Main CLI entry point."""
    cli = FlashscoreCLI()
    parser = cli.create_parser()
    args = parser.parse_args()
    
    # Run CLI and exit with appropriate code
    exit_code = await cli.run(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())
