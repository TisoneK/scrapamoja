"""Snapshot diff tool — compare two normalized snapshots and report drift.

Used to detect Linebet API schema changes between captures. Run it
after a fresh capture (from a residential IP) to see what changed vs.
the committed snapshot:

    python -m src.sites.linebet.snapshots.diff <old.json> <new.json>

Exit code:
  0 — no drift
  1 — drift detected (printed to stdout)
  2 — error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


def _endpoint_key(ep: Dict[str, Any]) -> str:
    """Stable identity key for an endpoint."""
    return f"{ep['method']} {ep['path']}?{json.dumps(ep.get('query', {}), sort_keys=True)}"


def diff_snapshots(
    old: Dict[str, Any], new: Dict[str, Any]
) -> Dict[str, Any]:
    """Diff two normalized snapshot bundles.

    Returns a dict with:
      * ``added`` — endpoints in NEW but not OLD
      * ``removed`` — endpoints in OLD but not NEW
      * ``changed`` — endpoints in both but with different body hashes
        (each entry has ``old_sha`` and ``new_sha``)
      * ``stable_count`` — how many endpoints are unchanged
    """
    old_eps = {_endpoint_key(e): e for e in old.get("endpoints", [])}
    new_eps = {_endpoint_key(e): e for e in new.get("endpoints", [])}

    added: List[str] = sorted(set(new_eps) - set(old_eps))
    removed: List[str] = sorted(set(old_eps) - set(new_eps))
    changed: List[Dict[str, Any]] = []
    stable_count = 0

    for key in sorted(set(old_eps) & set(new_eps)):
        old_sha = old_eps[key].get("body_sha256", "")
        new_sha = new_eps[key].get("body_sha256", "")
        if old_sha != new_sha:
            changed.append({
                "endpoint": key,
                "old_sha": old_sha,
                "new_sha": new_sha,
                "old_body_bytes": old_eps[key].get("body_bytes", 0),
                "new_body_bytes": new_eps[key].get("body_bytes", 0),
            })
        else:
            stable_count += 1

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "stable_count": stable_count,
        "old_total": len(old_eps),
        "new_total": len(new_eps),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python -m src.sites.linebet.snapshots.diff <old.json> <new.json>")
        return 2

    old_path, new_path = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (old_path, new_path):
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            return 2

    old = json.loads(old_path.read_text())
    new = json.loads(new_path.read_text())
    diff = diff_snapshots(old, new)

    print(f"Old snapshot: {diff['old_total']} endpoints")
    print(f"New snapshot: {diff['new_total']} endpoints")
    print(f"Stable:       {diff['stable_count']}")
    print(f"Added:        {len(diff['added'])}")
    print(f"Removed:      {len(diff['removed'])}")
    print(f"Changed:      {len(diff['changed'])}")

    if diff["added"]:
        print("\n--- ADDED ---")
        for e in diff["added"]:
            print(f"  + {e}")
    if diff["removed"]:
        print("\n--- REMOVED ---")
        for e in diff["removed"]:
            print(f"  - {e}")
    if diff["changed"]:
        print("\n--- CHANGED (body hash differs) ---")
        for c in diff["changed"]:
            print(f"  ~ {c['endpoint']}")
            print(f"      {c['old_sha']} ({c['old_body_bytes']}B) -> "
                  f"{c['new_sha']} ({c['new_body_bytes']}B)")

    drift = bool(diff["added"] or diff["removed"] or diff["changed"])
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
