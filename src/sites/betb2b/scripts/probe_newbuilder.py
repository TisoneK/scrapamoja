"""Live probe: old-builder vs new-builder GetGameZip (ADR-19 wire validation).

Fixture tests prove the parser; this proves the *wire contract*. It runs the
browser-free discovery chain (GetSportsZip → GetChampZip → GetGameZip, ADR-15)
through the operator proxy and compares, for one real event:

  A. old-builder  ``GetGameZip?id=<I>&isSubGames=true&grMode=4``
  B. new-builder  ``…&isNewBuilder=true&GroupEvents=true&marketType=1`` with ``id=<I>``
  C. new-builder  same params with ``id=<CI>``   (the SPA addresses events by CI)

and reports, per variant: HTTP status, body size, whether the payload carries
``MEC[]`` (real category names), ``SG[].TG`` (real sub-game names), ``GE[]``
(grouped market layout), plus the parsed market-name quality (how many
``G=<n>`` fallbacks survive after extraction).

Usage (operator proxy env vars, no secrets in CLI args — the URL may carry
creds directly, as ``http://user:pass@bore.pub:<port>``)::

    export BETB2B_PROXY_URL=http://TisoneK:Taalib01@bore.pub:12382
    export BETB2B_PROXY_COUNTRY=KE BETB2B_PROXY_ID=kenya
    python -m src.sites.betb2b.scripts.probe_newbuilder --skin linebet --sport basketball
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.sites.betb2b.extraction.rules import BetB2BExtractionRules


def _repo_root() -> Path:
    # …/src/sites/betb2b/scripts/probe_newbuilder.py → repo root is parents[4]
    return Path(__file__).resolve().parents[4]


async def main() -> int:
    sys.path.insert(0, str(_repo_root()))

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skin", default="linebet")
    parser.add_argument("--sport-id", type=int, default=3,
                        help="SI sport id for league discovery (3 = basketball)")
    parser.add_argument("--event-id", default=None,
                        help="Skip discovery and probe this event id directly")
    parser.add_argument("--out", default=None,
                        help="Output directory (default: output/probe_newbuilder)")
    args = parser.parse_args()

    from src.network.proxy import build_proxy_manager, verify_proxy
    from src.sites.betb2b.client import BetB2BFeedClient
    from src.sites.betb2b.config import BetB2BSkinConfig
    from src.sites.betb2b.harvest import extract_leagues_from_sports

    out_dir = Path(args.out) if args.out else Path("output/probe_newbuilder")
    out_dir.mkdir(parents=True, exist_ok=True)

    skin = BetB2BSkinConfig.from_yaml(
        str(_repo_root() / "src/sites/betb2b/skins" / f"{args.skin}.yaml")
    )
    print(f"skin={skin.name} domain={skin.domain} "
          f"partner={skin.partner} gr={skin.gr} country={skin.country}", flush=True)

    # ---- proxy from env (optional but expected here) ----------------------
    import os
    proxy_url = os.environ.get("BETB2B_PROXY_URL")
    pm = ep = None
    if proxy_url:
        pm = build_proxy_manager({
            "endpoints": [{
                "id": os.environ.get("BETB2B_PROXY_ID", "operator"),
                "url": proxy_url,
                "country": os.environ.get("BETB2B_PROXY_COUNTRY", "KE"),
                "source": "ngrok",
            }],
            "routing": [{"pattern": f"*.{skin.domain}", "target": os.environ.get("BETB2B_PROXY_ID", "operator")}],
        })
        ep = pm.get(os.environ.get("BETB2B_PROXY_ID", "operator")) or pm.acquire(site=skin.domain)
        print(f"proxy: {ep!r}", flush=True)
        check = await verify_proxy(ep, timeout=30.0, with_geo=True)
        print(f"egress: {check}", flush=True)
        if not check.ok:
            print(f"PROXY UNREACHABLE: {check.error}", flush=True)
            return 1
    else:
        print("no BETB2B_PROXY_URL — running DIRECT", flush=True)

    # ADR-15 direct mode: GetSportsZip / GetChampZip / GetGameZip are un-gated,
    # so no browser bootstrap or cookies are needed — pure httpx through the proxy.
    # The session manager must still be a REAL instance: `fetch()` calls
    # `record_auth_failure()`/`clear()` on it unconditionally (even in direct
    # mode), but its constructor launches no browser — only `get_session()`
    # does, which direct mode never calls.
    from src.sites.betb2b.session import BetB2BSessionManager

    session_manager = BetB2BSessionManager(skin=skin, proxy=ep, settle_seconds=8.0)
    client = BetB2BFeedClient(
        skin, session_manager=session_manager,
        proxy=ep, direct=True, timeout=30.0, rate_limit_per_minute=10,
    )
    await client.start()

    try:
        # ---- discover an event id (unless given) --------------------------
        event_id = args.event_id
        ci_from_feed: Optional[str] = None
        if not event_id:
            print("\n[discovery] GetSportsZip → top league → GetChampZip …", flush=True)
            sports = await client.fetch_sports(root="line")
            print(f"  sports status={sports.status} bytes={sports.body_bytes}", flush=True)
            leagues = extract_leagues_from_sports(sports.decoded, sport_id=args.sport_id)
            if not leagues:
                print("  no leagues with games found — aborting", flush=True)
                return 1
            league_id, gc, lname = leagues[0]
            print(f"  league: {lname} (id={league_id}, games={gc})", flush=True)

            champ = await client.fetch_champ(str(league_id), root="line")
            print(f"  champ status={champ.status} bytes={champ.body_bytes}", flush=True)
            games = _games_from_champ(champ.decoded)
            if not games:
                print("  no games in GetChampZip payload — aborting", flush=True)
                (out_dir / "champ_raw.json").write_text(
                    json.dumps(champ.decoded, indent=2, default=str), encoding="utf-8")
                return 1
            first = games[0]
            event_id = str(first.get("I") or first.get("CI") or "")
            ci_from_feed = str(first["CI"]) if first.get("CI") else None
            print(f"  first game: {first.get('O1') or first.get('O1E')} vs "
                  f"{first.get('O2') or first.get('O2E')} I={event_id} CI={ci_from_feed}", flush=True)
            if not event_id:
                print("  no I/CI on first game — aborting", flush=True)
                return 1

        # ---- probe the three variants -------------------------------------
        report: Dict[str, Any] = {"skin": skin.name, "event_id": event_id}
        variants = {
            "A_old_id_I": {},
            "B_new_id_I": {},
            "C_new_id_CI": {},
        }

        # A: old builder, id=I
        cap_a = await client.fetch_game(event_id, root="line", new_builder=False)
        variants["A_old_id_I"] = await _analyze(skin, cap_a, out_dir, "A_old_id_I")
        print(_fmt("A old-builder id=I", variants["A_old_id_I"]), flush=True)

        # B: new builder, id=I
        cap_b = await client.fetch_game(event_id, root="line", new_builder=True)
        variants["B_new_id_I"] = await _analyze(skin, cap_b, out_dir, "B_new_id_I")
        print(_fmt("B new-builder id=I", variants["B_new_id_I"]), flush=True)

        # C: new builder, id=CI (the SPA's addressing)
        ci = ci_from_feed
        if not ci and cap_b.decoded:
            ci = _find_ci(cap_b.decoded)
        if ci:
            cap_c = await client.fetch_game(event_id, root="line", new_builder=True,
                                            extra_params={"id": ci})
            variants["C_new_id_CI"] = await _analyze(skin, cap_c, out_dir, "C_new_id_CI")
            print(_fmt("C new-builder id=CI", variants["C_new_id_CI"]), flush=True)
        else:
            variants["C_new_id_CI"] = {"status": 0, "note": "no CI found to probe"}
            print("C new-builder id=CI: no CI value available — skipped", flush=True)

        report["variants"] = variants
        report_path = out_dir / "report.json"
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"\nreport: {report_path}", flush=True)
        return 0
    finally:
        await client.close()


def _games_from_champ(decoded: Any) -> List[Dict[str, Any]]:
    """Pull the game list out of a GetChampZip payload (Value.G[])."""
    if not isinstance(decoded, dict):
        return []
    value = decoded.get("Value")
    if isinstance(value, dict):
        for key in ("G", "Games"):
            g = value.get(key)
            if isinstance(g, list):
                return [x for x in g if isinstance(x, dict)]
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("G"), list):
                return [x for x in item["G"] if isinstance(x, dict)]
    return []


def _find_ci(decoded: Any) -> Optional[str]:
    """Recursively find the first 'CI' value in the payload."""
    if isinstance(decoded, dict):
        if "CI" in decoded:
            return str(decoded["CI"])
        for v in decoded.values():
            found = _find_ci(v)
            if found:
                return found
    elif isinstance(decoded, list):
        for v in decoded:
            found = _find_ci(v)
            if found:
                return found
    return None


async def _analyze(
    skin: BetB2BSkinConfig, cap: Any, out_dir: Path, tag: str,
) -> Dict[str, Any]:
    """Digest one capture: presence flags + parsed market-name quality."""
    decoded = cap.decoded if cap.decoded else {}
    value = decoded.get("Value") if isinstance(decoded, dict) else None

    # Presence flags on the raw payload.
    has_mec = _contains_key(decoded, "MEC")
    has_sg = _contains_key(decoded, "SG")
    has_ge = _contains_key(decoded, "GE")
    has_tg = _contains_key(decoded, "TG")
    mec_names = _collect_mec_names(decoded)
    sg_tg_names = _collect_tg_names(decoded)

    # Parsed market-name quality.
    parsed = BetB2BExtractionRules(skin).extract_from_captured(cap) if cap.decoded else []
    market_count = sum(len(e.markets or []) for e in parsed)
    fallback_count = sum(
        1 for e in parsed for m in (e.markets or [])
        if str(m.name).startswith("G=")
    )
    # market_categories entries are {MT, EC, name} dicts — unwrap the names.
    categories = sorted(
        {c.get("name") or str(c) for e in parsed for c in (e.market_categories or [])}
    )
    sub_game_count = sum(len(e.sub_games or []) for e in parsed)
    sample_markets = []
    for e in parsed:
        for m in (e.markets or [])[:12]:
            sample_markets.append(m.name)
        if len(sample_markets) >= 12:
            break

    entry = {
        "status": cap.status,
        "body_bytes": cap.body_bytes,
        "has_MEC": has_mec, "has_SG": has_sg, "has_GE": has_ge, "has_TG": has_tg,
        "mec_names": mec_names[:12],
        "sg_tg_names": sg_tg_names[:12],
        "parsed_events": len(parsed),
        "parsed_markets": market_count,
        "G_fallback_markets": fallback_count,
        "market_categories": categories[:12],
        "sub_games": sub_game_count,
        "sample_market_names": sample_markets,
    }
    # Keep the raw body for offline inspection (this is diagnostic scratch).
    (out_dir / f"{tag}_raw.json").write_text(
        json.dumps(decoded, indent=2, default=str), encoding="utf-8")
    return entry


def _contains_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(v, key) for v in obj)
    return False


def _collect_mec_names(decoded: Any) -> List[str]:
    """Collect MEC[].N (category names) from a payload."""
    out: List[str] = []
    if isinstance(decoded, dict):
        # MEC entries are {MT, EC(count), N} dicts.
        n = decoded.get("N")
        if isinstance(n, str) and n and "MT" in decoded:
            out.append(n)
        for v in decoded.values():
            out.extend(_collect_mec_names(v))
    elif isinstance(decoded, list):
        for v in decoded:
            out.extend(_collect_mec_names(v))
    return out


def _collect_tg_names(decoded: Any) -> List[str]:
    """Collect SG[].TG (sub-game names)."""
    out: List[str] = []
    if isinstance(decoded, dict):
        if isinstance(decoded.get("TG"), str):
            out.append(decoded["TG"])
        for v in decoded.values():
            out.extend(_collect_tg_names(v))
    elif isinstance(decoded, list):
        for v in decoded:
            out.extend(_collect_tg_names(v))
    return out


def _fmt(tag: str, entry: Dict[str, Any]) -> str:
    return (
        f"\n[{tag}] status={entry.get('status')} bytes={entry.get('body_bytes')} "
        f"MEC={entry.get('has_MEC')} SG={entry.get('has_SG')} GE={entry.get('has_GE')} "
        f"markets={entry.get('parsed_markets')} G-fallback={entry.get('G_fallback_markets')} "
        f"categories={entry.get('market_categories')} sub_games={entry.get('sub_games')}"
    )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
