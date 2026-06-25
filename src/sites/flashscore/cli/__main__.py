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
    return await cli.run(sys.argv[1:])


if __name__ == "__main__":
    # Suppress the RuntimeWarning by ensuring clean module execution
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(main())
