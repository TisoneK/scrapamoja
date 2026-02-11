#!/usr/bin/env python3
"""
Scorewise CLI main entry point.

Provides unified command-line interface for all scraping operations.
"""

import asyncio
import sys
import importlib


# Site registry - maps site names to their CLI class paths
SITE_CLIS = {
    'flashscore': ('src.sites.flashscore.cli.main', 'FlashscoreCLI'),
    'wikipedia': ('src.sites.wikipedia.cli.main', 'WikipediaCLI'),
}


async def cli():
    """Main CLI entry point."""
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
    
    # Import the site's CLI module and class
    module_path, class_name = SITE_CLIS[site_name]
    module = importlib.import_module(module_path)
    site_cli_class = getattr(module, class_name)
    site_cli = site_cli_class()
    
    # Create parser and parse remaining args
    parser = site_cli.create_parser()
    args = parser.parse_args(sys.argv[2:])
    
    return await site_cli.run(args)


if __name__ == "__main__":
    asyncio.run(cli())
