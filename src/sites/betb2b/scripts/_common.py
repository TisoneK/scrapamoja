"""Shared helpers for the betb2b debug scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    """Return the scrapamoja repo root."""
    return Path(__file__).resolve().parents[4]


def ensure_repo_on_path() -> None:
    """Make ``src.*`` imports work when the script is run directly."""
    root = repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def output_dir(subdir: str = "betb2b_output") -> Path:
    """Return the output directory, creating it if needed."""
    sandbox_download = Path("/home/z/my-project/download")
    if sandbox_download.parent.exists():
        out = sandbox_download / subdir
    else:
        out = Path.cwd() / subdir
    out.mkdir(parents=True, exist_ok=True)
    return out
