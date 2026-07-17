"""Linebet snapshot package — fixtures + thin re-exports of the framework API.

The normalizer + diff logic lives in the framework now
(:mod:`src.core.snapshot.normalize` + :mod:`src.core.snapshot.diff`).
This package just re-exports them so existing linebet code that did
``from src.sites.linebet.snapshots.normalize import ...`` keeps working,
and provides a home for the committed linebet fixtures under
``raw/`` and ``normalized/``.
"""

# Re-export the framework API for backward compatibility with any
# existing linebet code that imported from here.
from src.core.snapshot.normalize import (  # noqa: F401
    normalize_captured_response,
    normalize_capture_list,
    NormalizerConfig,
)
from src.core.snapshot.diff import diff_snapshots  # noqa: F401

__all__ = [
    "normalize_captured_response",
    "normalize_capture_list",
    "NormalizerConfig",
    "diff_snapshots",
]
