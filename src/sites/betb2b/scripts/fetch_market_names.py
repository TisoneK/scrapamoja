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


def build_tables(lng: str = "en") -> "tuple[Dict[str, str], Dict[str, str]]":
    """Fetch all templates once; return two unions with string keys:

    * ``by_gs`` — ``{GS: name}`` from every entry's ``GN`` sub-map (keyed by the
      feed's *groupShortId*). The precise key ``lookup_market`` uses.
    * ``by_g`` — ``{G: name}`` from every entry's top-level ``N`` (keyed by the
      feed's *group id*). Coarser (one name per group), but the only key the
      store persists on ``markets.raw_g`` — used by the name backfill.

    Both spaces are globally unique across the 78 templates (0 conflicts).
    """
    import httpx

    gs_name: Dict[int, str] = {}
    g_name: Dict[int, str] = {}
    gs_conflicts = g_conflicts = 0
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
                for g, entry in tpl.items():
                    if not isinstance(entry, dict):
                        continue
                    n_name = entry.get("N")
                    try:
                        g_i = int(g)
                    except (TypeError, ValueError):
                        g_i = None
                    if g_i is not None and isinstance(n_name, str) and n_name.strip():
                        if g_i in g_name and g_name[g_i] != n_name.strip():
                            g_conflicts += 1
                        g_name[g_i] = n_name.strip()
                    for gs, name in (entry.get("GN") or {}).items():
                        try:
                            gs_i = int(gs)
                        except (TypeError, ValueError):
                            continue
                        if not isinstance(name, str) or not name.strip():
                            continue
                        if gs_i in gs_name and gs_name[gs_i] != name:
                            gs_conflicts += 1
                        gs_name[gs_i] = name.strip()
    if gs_conflicts or g_conflicts:
        print(f"  NOTE: {gs_conflicts} GS + {g_conflicts} G name conflicts (last-wins)",
              file=sys.stderr)
    return (
        {str(k): gs_name[k] for k in sorted(gs_name)},
        {str(k): g_name[k] for k in sorted(g_name)},
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lng", default="en")
    ap.add_argument("--data-dir", default=str(repo_root() / "src/sites/betb2b/data"))
    args = ap.parse_args()

    print(f"Fetching {NUM_TEMPLATES} bet-model templates ({args.lng}) from CDN...")
    by_gs, by_g = build_tables(args.lng)
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    gs_out = data_dir / f"market_group_names_{args.lng}.json"
    gs_out.write_text(json.dumps(by_gs, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {len(by_gs)} GS -> name entries to {gs_out} ({gs_out.stat().st_size} bytes)")

    g_out = data_dir / f"market_group_names_by_g_{args.lng}.json"
    g_out.write_text(json.dumps(by_g, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {len(by_g)} G -> name entries to {g_out} ({g_out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
