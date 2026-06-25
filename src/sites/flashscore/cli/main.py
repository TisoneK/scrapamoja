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
        # Create parent parser for common arguments
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument(
            '--config',
            type=str,
            help='Path to configuration file'
        )
        parent_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        parent_parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress output except errors'
        )
        
        parser = argparse.ArgumentParser(
            prog='flashscore-cli',
            description='Flashscore scraper CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            parents=[parent_parser],
            epilog="""
Examples:
  %(prog)s scrape basketball live --output json
  %(prog)s validate selectors --sport basketball
  %(prog)s test navigation --status live
            """
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
                help=cmd_class.help_text,
                parents=[parent_parser]
            )
            cmd_class.add_arguments(cmd_parser)
        
        return parser
    
    async def run(self, args: argparse.Namespace, interrupt_handler=None, shutdown_coordinator=None) -> int:
        """Run CLI with given arguments."""
        try:
            # Load configuration
            if args.config:
                await self.config.load_from_file(args.config)
            
            # Set logging level
            self._setup_logging(args.verbose, args.quiet)
            
            # Initialize interrupt handling for this CLI
            if interrupt_handler is not None:
                # Use the provided interrupt handler
                cli_interrupt_handler = interrupt_handler
            else:
                # Create new interrupt handler
                from src.interrupt_handling.compatibility import create_compatible_handler
                from src.interrupt_handling.config import InterruptConfig
                
                interrupt_config = InterruptConfig.from_env()
                cli_interrupt_handler = create_compatible_handler(interrupt_config)
            
            # Store interrupt handler in commands for access
            for command in self.commands.values():
                if hasattr(command, 'set_interrupt_handler'):
                    command.set_interrupt_handler(cli_interrupt_handler)
                if hasattr(command, 'set_shutdown_coordinator') and shutdown_coordinator is not None:
                    command.set_shutdown_coordinator(shutdown_coordinator)
            
            # Execute command
            if args.command in self.commands:
                return await self.commands[args.command].execute(args)
            else:
                print(f"Unknown command: {args.command}", file=sys.stderr)
                return 1
                
        except KeyboardInterrupt:
            # Let interrupt handling system manage the interruption
            print("\nOperation interrupted - cleaning up...", file=sys.stderr)
            return 1
        except SystemExit as e:
            # Handle graceful shutdown exit from interrupt handler
            return e.code if e.code is not None else 0
        except Exception as e:
            # Enhanced error handling with interrupt context
            print(f"Error: {e}", file=sys.stderr)
            
            # Check if this might be interrupt-related
            if "interrupt" in str(e).lower() or "signal" in str(e).lower():
                print("This may be related to interrupt handling. Check configuration.", file=sys.stderr)
            
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
        finally:
            # Ensure cleanup happens even if interrupt handling fails
            try:
                # Additional cleanup if needed
                pass
            except Exception:
                pass
    
    def _setup_logging(self, verbose: bool, quiet: bool):
        """Setup logging based on verbosity."""
        from src.observability.logger import setup_logging
        
        if quiet:
            level = "ERROR"
        elif verbose:
            level = "DEBUG"
        else:
            level = "INFO"
            
        # Use the structured logging setup
        setup_logging(log_level=level)


async def main():
    """Main CLI entry point."""
    # Setup logging first before anything else
    import sys
    from src.observability.logger import setup_logging
    setup_logging(log_level="INFO")  # Default level, will be overridden by CLI args
    
    cli = FlashscoreCLI()
    parser = cli.create_parser()
    args = parser.parse_args()
    
    # Run CLI and exit with appropriate code
    exit_code = await cli.run(args)
    return exit_code


if __name__ == '__main__':
    asyncio.run(main())
