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


def require_page_access(skin: str | None = None) -> None:
    """Exit (code 2) before a script opens a browser page on a machine that must not load the
    site's pages (country-blocked connection, no proxy). A proxy is detected from the same
    ``BETB2B_PROXY_URL`` the scripts read."""
    import os
    from src.security import egress
    try:
        egress.check_page_load(skin or "betb2b", via_proxy=bool(os.environ.get("BETB2B_PROXY_URL")),
                               what="script browser run")
    except egress.PageLoadsRefused as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
