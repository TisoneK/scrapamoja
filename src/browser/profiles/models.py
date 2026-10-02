"""Persistent browser profile metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ProfileMeta:
    """Stored next to the profile's user-data dir as ``profile.json``.

    ``identity`` holds optional Playwright context overrides (``user_agent``,
    ``viewport``, ``locale``, ``timezone_id``). Left empty, the browser keeps
    its own real values — the most consistent identity there is.
    """
    name: str
    created_at: float
    last_used_at: float = 0.0
    uses: int = 0
    notes: str = ""
    identity: Dict[str, Any] = field(default_factory=dict)
