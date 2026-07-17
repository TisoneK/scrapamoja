"""Shared helpers for the Linebet debug scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    """Return the scrapamoja repo root.

    Computed from this file's location:
    <repo>/src/sites/linebet/scripts/_common.py
    -> .parent = scripts/
    -> .parent.parent = linebet/
    -> .parent.parent.parent = sites/
    -> .parent.parent.parent.parent = src/
    -> .parent.parent.parent.parent.parent = repo root
    """
    return Path(__file__).resolve().parents[4]


def ensure_repo_on_path() -> None:
    """Make ``src.*`` imports work when the script is run directly.

    Run as ``python -m src.sites.linebet.scripts.foo`` this is a no-op
    (Python already has the repo root on sys.path). Run as
    ``python src/sites/linebet/scripts/foo.py`` this adds the repo root.
    """
    root = repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def output_dir(subdir: str = "linebet_output") -> Path:
    """Return the output directory, creating it if needed.

    Prefers ``/home/z/my-project/download/<subdir>`` (the sandbox's
    persistent download dir) if that parent exists; otherwise uses
    ``./<subdir>`` next to wherever the script is run from.
    """
    sandbox_download = Path("/home/z/my-project/download")
    if sandbox_download.parent.exists():
        out = sandbox_download / subdir
    else:
        out = Path.cwd() / subdir
    out.mkdir(parents=True, exist_ok=True)
    return out
