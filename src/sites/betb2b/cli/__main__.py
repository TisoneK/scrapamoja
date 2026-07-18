"""CLI entry point for the betb2b family scraper."""

from __future__ import annotations

import asyncio
import sys

from .main import BetB2BCLI


def main() -> int:
    return asyncio.run(BetB2BCLI().run())


if __name__ == "__main__":
    sys.exit(main())
