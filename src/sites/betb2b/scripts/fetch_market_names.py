"""Regenerate the BetB2B/1xbet market-group name table (ADR-19).

The 1xbet-family SPA names market groups client-side via
``name = groupNames[GS]`` where ``GS`` is the feed's *groupShortId*. That
``groupNames`` table is the union of the per-template "bet-model" files the
CDN serves at::

    https://v3.traincdn.com/genfiles/cms/betstemplates/bets_model_short_en_<N>.json

for ``N`` in ``0..77`` (gzip-compressed JSON). Each file is
``{templateId: {G: {"N": groupName, "GN": {GS: name, ...}, "M": {...}}}}``.
The ``GN`` sub-map is keyed by **GS** — and across all 78 templates the GS
space is globally unique (verified: 0 name conflicts, ~5.4k entries). So the
union of every ``GN`` is a static, authoritative ``GS -> market-group name``
lookup that resolves *every* group the feed can carry — including the exotic
groups that previously fell back to ``G=<n>``.

This script fetches the files (globally reachable — no proxy needed), builds
the union, and writes ``data/market_group_names_en.json``. Re-run it to refresh
the table when the operator adds new markets.

Usage::

    python -m src.sites.betb2b.scripts.fetch_market_names
    python -m src.sites.betb2b.scripts.fetch_market_names --lng en
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Dict

from ._common import ensure_repo_on_path, repo_root

ensure_repo_on_path()

CDN_BASE = "https://v3.traincdn.com/genfiles/cms/betstemplates"
NUM_TEMPLATES = 78  # bets_model_short_<lng>_0 .. _77


def _decode(raw: bytes) -> dict:
    try:
        raw = gzip.decompress(raw)
    except (OSError, EOFError):
        pass  # already plain JSON
    return json.loads(raw)


def build_table(lng: str = "en") -> Dict[str, str]:
    """Fetch all templates and return the ``{GS: name}`` union (string keys)."""
    import httpx

    gs_name: Dict[int, str] = {}
    conflicts = 0
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for n in range(NUM_TEMPLATES):
            url = f"{CDN_BASE}/bets_model_short_{lng}_{n}.json"
            resp = client.get(url)
            if resp.status_code != 200:
                print(f"  WARN {resp.status_code} {url}", file=sys.stderr)
                continue
            obj = _decode(resp.content)
            # top level: {templateId: {G: entry}} — a single template per file
            for tpl in obj.values():
                if not isinstance(tpl, dict):
                    continue
                for entry in tpl.values():
                    if not isinstance(entry, dict):
                        continue
                    for gs, name in (entry.get("GN") or {}).items():
                        try:
                            gs_i = int(gs)
                        except (TypeError, ValueError):
                            continue
                        if not isinstance(name, str) or not name.strip():
                            continue
                        if gs_i in gs_name and gs_name[gs_i] != name:
                            conflicts += 1
                        gs_name[gs_i] = name.strip()
    if conflicts:
        print(f"  NOTE: {conflicts} GS name conflicts (last-wins)", file=sys.stderr)
    return {str(k): gs_name[k] for k in sorted(gs_name)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lng", default="en")
    ap.add_argument(
        "--out",
        default=str(repo_root() / "src/sites/betb2b/data/market_group_names_en.json"),
    )
    args = ap.parse_args()

    print(f"Fetching {NUM_TEMPLATES} bet-model templates ({args.lng}) from CDN...")
    table = build_table(args.lng)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {len(table)} GS -> name entries to {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
