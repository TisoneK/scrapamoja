#!/usr/bin/env python3
"""
Scorewise CLI main entry point.

Provides unified command-line interface for all scraping operations.
"""

import asyncio
import sys
import importlib
import signal
import logging

# Import logging configuration first
from src.core.logging_config import JsonLoggingConfigurator

# Import interrupt handling
from src.interrupt_handling.compatibility import create_compatible_handler
from src.interrupt_handling.config import InterruptConfig


# Site registry - maps site names to their CLI class paths
SITE_CLIS = {
    'flashscore': ('src.sites.flashscore.cli.main', 'FlashscoreCLI'),
    'wikipedia': ('src.sites.wikipedia.cli.main', 'WikipediaCLI'),
}


async def cli():
    """Main CLI entry point with interrupt handling support."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <site> <command> ...")
        print(f"Available sites: {', '.join(SITE_CLIS.keys())}")
        print("Example: python -m src.main flashscore scrape basketball scheduled --limit 1")
        return 1
    
    site_name = sys.argv[1]
    
    if site_name not in SITE_CLIS:
        print(f"Unknown site: {site_name}")
        print(f"Available sites: {', '.join(SITE_CLIS.keys())}")
        return 1
    
    # Check for verbose flag before importing site CLI
    verbose = '--verbose' in sys.argv
    
    # Initialize logging with verbose flag
    JsonLoggingConfigurator.setup(verbose=verbose)
    
    # Initialize interrupt handling
    config = InterruptConfig.from_env()
    interrupt_handler = create_compatible_handler(config)
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        print(f"\nReceived interrupt signal {signum}. Gracefully shutting down...")
        # Let the interrupt handler take care of cleanup
        if hasattr(interrupt_handler, 'handle_interrupt'):
            interrupt_handler.handle_interrupt(signum)
    
    # Register signal handlers
    if config.enable_interrupt_handling:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    try:
        # Import the site's CLI module and class
        module_path, class_name = SITE_CLIS[site_name]
        module = importlib.import_module(module_path)
        site_cli_class = getattr(module, class_name)
        site_cli = site_cli_class()
        
        # Create parser and parse remaining args
        parser = site_cli.create_parser()
        args = parser.parse_args(sys.argv[2:])
        
        # Run the site CLI with interrupt handling
        result = await site_cli.run(args)
        
        # Check if interrupt handler signaled exit
        if hasattr(interrupt_handler, 'should_exit') and interrupt_handler.should_exit():
            return 0
        
        return result
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if config.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    asyncio.run(cli())
