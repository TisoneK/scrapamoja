"""End-to-end live validation of the betb2b family scraper.

Runs the full hybrid pipeline against a real BetB2B skin through the
operator's proxy:

  1. Verify proxy egress country.
  2. Bootstrap a Playwright session through the proxy.
  3. Harvest cookies via the framework's SessionHarvester.
  4. Poll the LiveFeed + LineFeed endpoints via httpx.
  5. Extract events with the BetB2BExtractionRules.
  6. Persist a summary + the raw captures for offline replay.

Designed for operator use from anywhere — the proxy is the only
network requirement. From the sandbox WITHOUT the proxy env vars,
this script will fail at step 1 with a clear message (no surprise
"WAF block" output).

Usage::

    # Operator sets these env vars (no secrets in CLI args):
    export BETB2B_PROXY_URL=http://bore.pub:1074
    export BETB2B_PROXY_USER=TisoneK
    export BETB2B_PROXY_PASS=Taalib01
    export BETB2B_PROXY_COUNTRY=KE
    export BETB2B_PROXY_ID=kenya

    python -m src.sites.betb2b.scripts.validate_live --skin linebet
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _output_dir(subdir: str = "betb2b_validate") -> Path:
    sandbox_download = Path("/home/z/my-project/download")
    if sandbox_download.parent.exists():
        out = sandbox_download / subdir
    else:
        out = Path.cwd() / subdir
    out.mkdir(parents=True, exist_ok=True)
    return out


async def main() -> int:
    # Lazy imports so `--help` works without the full dep chain.
    sys.path.insert(0, str(_repo_root()))

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skin", default="linebet", help="Skin name (default: linebet)")
    parser.add_argument("--settle", type=float, default=12.0,
                        help="Bootstrap SPA settle seconds (default: 12)")
    parser.add_argument("--count", type=int, default=50,
                        help="`count=` query param (default: 50)")
    parser.add_argument("--sport-id", type=int, default=None,
                        help="Filter by sport SI id")
    parser.add_argument("--skip-live", action="store_true",
                        help="Skip LiveFeed (prematch-only test)")
    parser.add_argument("--skip-line", action="store_true",
                        help="Skip LineFeed (live-only test)")
    parser.add_argument("--out", default=None, help="Output directory (default: sandbox download)")
    args = parser.parse_args()

    from src.network.proxy import build_proxy_manager, verify_proxy
    from src.sites.betb2b import BetB2BScraper
    from src.sites.betb2b.cli.main import _load_skin

    out_dir = Path(args.out) if args.out else _output_dir(f"betb2b_validate_{args.skin}")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    captured_dir = out_dir / "captured"
    captured_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "skin": args.skin,
        "steps": [],
    }

    # ----- Step 1: load skin -----
    print(f"[1/6] Loading skin={args.skin} ...", flush=True)
    try:
        skin = _load_skin(args.skin)
        print(f"    domain={skin.domain} partner={skin.partner} gr={skin.gr} geo={skin.geo}", flush=True)
        summary["skin_config"] = skin.to_dict()
    except Exception as exc:  # noqa: BLE001
        summary["steps"].append({"step": "load_skin", "ok": False, "error": str(exc)})
        print(f"    FAILED: {exc}", flush=True)
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        return 1

    # ----- Step 2: build proxy from env -----
    print("[2/6] Building proxy manager from env ...", flush=True)
    proxy_url = os.environ.get("BETB2B_PROXY_URL")
    if not proxy_url:
        msg = (
            "BETB2B_PROXY_URL is not set. The betb2b scraper needs an "
            "allowed-country proxy to bootstrap a session. Set:\n"
            "  export BETB2B_PROXY_URL=http://bore.pub:1074\n"
            "  export BETB2B_PROXY_USER=TisoneK\n"
            "  export BETB2B_PROXY_PASS=Taalib01\n"
            "  export BETB2B_PROXY_COUNTRY=KE\n"
            "  export BETB2B_PROXY_ID=kenya"
        )
        print(f"    FAILED: {msg}", flush=True)
        summary["steps"].append({"step": "build_proxy", "ok": False, "error": msg})
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        return 1

    user = os.environ.get("BETB2B_PROXY_USER", "")
    pw = os.environ.get("BETB2B_PROXY_PASS", "")
    if user and pw and "@" not in proxy_url:
        from urllib.parse import urlparse, urlunparse

        p = urlparse(proxy_url)
        netloc = f"{user}:{pw}@{p.hostname}"
        if p.port:
            netloc += f":{p.port}"
        proxy_url = urlunparse(p._replace(netloc=netloc))

    endpoint_id = os.environ.get("BETB2B_PROXY_ID", "kenya")
    country = os.environ.get("BETB2B_PROXY_COUNTRY", "KE")

    pm = build_proxy_manager({
        "endpoints": [
            {"id": endpoint_id, "url": proxy_url,
             "country": country, "source": "ngrok"},
        ],
        "routing": [
            {"pattern": f"*.{skin.domain}", "target": endpoint_id},
        ],
    })
    ep = pm.get(endpoint_id) or pm.acquire(site=skin.domain)
    print(f"    proxy endpoint: {ep!r}", flush=True)
    summary["steps"].append({"step": "build_proxy", "ok": True, "endpoint": repr(ep)})

    # ----- Step 3: verify proxy egress country -----
    print(f"[3/6] Verifying proxy egress country (expected: {skin.allowed_countries}) ...", flush=True)
    try:
        check = await verify_proxy(ep, timeout=30.0, with_geo=True)
        print(f"    {check}", flush=True)
        summary["steps"].append({
            "step": "verify_proxy", "ok": check.ok,
            "egress_ip": check.egress_ip,
            "country_code": check.country_code,
            "latency_ms": check.latency_ms,
            "error": check.error,
        })
        if not check.ok:
            print(f"    FAILED: proxy unreachable — {check.error}", flush=True)
            summary_path.write_text(json.dumps(summary, indent=2, default=str))
            return 1
        if check.country_code and check.country_code not in skin.allowed_countries:
            print(
                f"    WARNING: proxy country={check.country_code} not in "
                f"allowed={skin.allowed_countries} — bootstrap will likely fail.",
                flush=True,
            )
    except Exception as exc:  # noqa: BLE001
        summary["steps"].append({"step": "verify_proxy", "ok": False, "error": str(exc)})
        print(f"    FAILED: {exc}", flush=True)
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        return 1

    # ----- Step 4 + 5: scrape (bootstrap + poll + extract) -----
    actions_to_run = []
    if not args.skip_live:
        actions_to_run.append("list_live")
    if not args.skip_line:
        actions_to_run.append("list_prematch")

    all_events = []
    all_captures = []

    async with BetB2BScraper(
        skin,
        proxy_manager=pm,
        proxy_endpoint_id=endpoint_id,
        rate_limit_per_minute=20,
        settle_seconds=args.settle,
    ) as scraper:
        for i, action in enumerate(actions_to_run, start=4):
            print(f"[{i}/6] Running scrape action={action} ...", flush=True)
            try:
                result = await scraper.scrape(
                    action=action,
                    sport_id=args.sport_id,
                    count=args.count,
                    timeout_seconds=120.0,
                )
                ok = result.get("error") is None
                ev_count = result.get("event_count", 0)
                cap_count = result.get("captured_response_count", 0)
                print(f"    ok={ok} events={ev_count} captures={cap_count} "
                      f"session_harvested={result.get('session_harvested')}",
                      flush=True)
                summary["steps"].append({
                    "step": action, "ok": ok,
                    "error": result.get("error"),
                    "event_count": ev_count,
                    "captured_response_count": cap_count,
                    "scrape_duration_seconds": result.get("scrape_duration_seconds"),
                    "session_harvested": result.get("session_harvested"),
                })
                if not ok:
                    continue

                events = result.get("events", [])
                captures = result.get("captured_responses", [])
                all_events.extend(events)
                all_captures.extend(captures)

                # Persist per-action captures for offline replay.
                (captured_dir / f"{action}_captures.json").write_text(
                    json.dumps(captures, indent=2, default=str)
                )
                (captured_dir / f"{action}_events.json").write_text(
                    json.dumps(events, indent=2, default=str)
                )
            except Exception as exc:  # noqa: BLE001
                summary["steps"].append({"step": action, "ok": False, "error": str(exc)})
                print(f"    FAILED: {exc}", flush=True)

    # ----- Step 6: write summary -----
    print(f"[6/6] Writing summary to {summary_path} ...", flush=True)
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary["total_events"] = len(all_events)
    summary["total_captures"] = len(all_captures)
    summary["events_preview"] = all_events[:5]
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    # Print a small summary to stdout.
    print(
        f"\nDONE: {len(all_events)} events, {len(all_captures)} captures "
        f"from skin={args.skin}.",
        flush=True,
    )
    print(f"Summary: {summary_path}", flush=True)
    if all_events:
        # Sample first event for sanity.
        sample = all_events[0]
        print(
            f"Sample event: {sample.get('home')} vs {sample.get('away')} "
            f"({sample.get('sport')}, {sample.get('competition')}) "
            f"markets={len(sample.get('markets', []))}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
