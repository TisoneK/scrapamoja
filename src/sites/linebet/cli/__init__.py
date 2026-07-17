"""Linebet CLI package.

Usage:
    python -m src.main linebet scrape --action list_prematch
    python -m src.main linebet scrape --action list_live --settle 20
    python -m src.main linebet scrape --action raw_capture --output captures.json
    python -m src.main linebet replay --input captures.json
    python -m src.main linebet info
"""

from .main import LinebetCLI

__all__ = ["LinebetCLI"]
