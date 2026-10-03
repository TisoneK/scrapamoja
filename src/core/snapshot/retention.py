"""Snapshot retention: bundles age out and total size is capped, without anyone remembering to.

``SnapshotStorage.cleanup_old_bundles`` existed but nothing ever called it, it only looks at age,
and it leaves the empty date/site directories behind. :func:`sweep` is synchronous (callable from
any code, async or not), never raises, and:

1. deletes bundles (directories holding a ``metadata.json``) older than ``days``;
2. if what is left still exceeds ``max_mb``, deletes the oldest bundles until it fits;
3. prunes directories that became empty.

It runs automatically once per process (first snapshot capture of any kind) and on demand:

    python -m src.core.snapshot.retention [--base data/snapshots] [--days 14] [--max-mb 500] [--dry-run]

Defaults: ``SNAPSHOT_CLEANUP_OLD_BUNDLES_DAYS`` (else 14), ``SNAPSHOT_MAX_MB`` (else 500).
"""

from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DAYS = 14
DEFAULT_MAX_MB = 500
_done: set = set()


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def sweep(base_path: str = "data/snapshots", days: Optional[float] = None,
          max_mb: Optional[float] = None, dry_run: bool = False,
          now: Optional[float] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"deleted": 0, "freed_bytes": 0, "kept": 0, "kept_bytes": 0,
                           "by_reason": {"age": 0, "size": 0}, "dry_run": dry_run}
    try:
        base = Path(base_path)
        if not base.is_dir():
            return out
        days = float(os.environ.get("SNAPSHOT_CLEANUP_OLD_BUNDLES_DAYS", DEFAULT_DAYS)) if days is None else days
        max_mb = float(os.environ.get("SNAPSHOT_MAX_MB", DEFAULT_MAX_MB)) if max_mb is None else max_mb
        now = time.time() if now is None else now

        bundles: List[Tuple[float, Path, int]] = []
        for meta in base.rglob("metadata.json"):
            d = meta.parent
            try:
                bundles.append((meta.stat().st_mtime, d, _dir_size(d)))
            except OSError:
                continue
        bundles.sort(key=lambda b: b[0])                       # oldest first

        def drop(bundle: Tuple[float, Path, int], reason: str) -> None:
            if not dry_run:
                shutil.rmtree(bundle[1], ignore_errors=True)
            out["deleted"] += 1
            out["freed_bytes"] += bundle[2]
            out["by_reason"][reason] += 1

        keep: List[Tuple[float, Path, int]] = []
        for b in bundles:
            (drop(b, "age") if now - b[0] > days * 86400 else keep.append(b))
        total = sum(b[2] for b in keep)
        while keep and total > max_mb * 1024 * 1024:
            oldest = keep.pop(0)
            drop(oldest, "size")
            total -= oldest[2]
        out["kept"], out["kept_bytes"] = len(keep), total

        if not dry_run:                                        # prune directories left empty
            for d, _dirs, _files in os.walk(base, topdown=False):
                p = Path(d)
                if p != base and not any(p.iterdir()):
                    p.rmdir()
    except Exception:  # noqa: BLE001 -- cleanup must never break a scrape
        pass
    return out


def sweep_once(base_path: str = "data/snapshots") -> None:
    """The automatic hook: sweep each base path at most once per process."""
    key = str(Path(base_path).resolve())
    if key not in _done:
        _done.add(key)
        sweep(base_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Delete old / excess snapshot bundles.")
    ap.add_argument("--base", default="data/snapshots")
    ap.add_argument("--days", type=float)
    ap.add_argument("--max-mb", type=float)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    r = sweep(a.base, a.days, a.max_mb, a.dry_run)
    verb = "would delete" if a.dry_run else "deleted"
    print(f"{verb} {r['deleted']} bundle(s) ({r['freed_bytes'] / 1e6:.1f} MB; "
          f"{r['by_reason']['age']} by age, {r['by_reason']['size']} by size); "
          f"kept {r['kept']} ({r['kept_bytes'] / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
