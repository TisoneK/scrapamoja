#!/usr/bin/env python3
"""
Flashscore CLI __main__ entry point.

This module allows running the CLI with: python -m src.sites.flashscore.cli
"""

import asyncio
import sys


async def main():
    """Main entry point for the CLI."""
    from .main import FlashscoreCLI
    cli = FlashscoreCLI()
    # run() expects a parsed argparse.Namespace, not the raw argv list —
    # build the parser and parse first (mirrors src/main.py's dispatcher).
    parser = cli.create_parser()
    args = parser.parse_args(sys.argv[1:])
    return await cli.run(args)


if __name__ == "__main__":
    # Suppress the RuntimeWarning by ensuring clean module execution
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(main())
