"""Linebet snapshot package — normalizes captured API responses for diffing.

Public API:

    from src.sites.linebet.snapshots.normalize import (
        normalize_captured_response,
        normalize_capture_list,
    )
    from src.sites.linebet.snapshots.diff import diff_snapshots

CLI:

    # Normalize a raw capture file into a stable snapshot
    python -m src.sites.linebet.snapshots.normalize <input.json> <output.json>

    # Diff two normalized snapshots to detect API drift
    python -m src.sites.linebet.snapshots.diff <old.json> <new.json>
"""

from .normalize import normalize_captured_response, normalize_capture_list
from .diff import diff_snapshots

__all__ = [
    "normalize_captured_response",
    "normalize_capture_list",
    "diff_snapshots",
]
