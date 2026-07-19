"""Cross-skin H2H endpoint validation via hybrid bootstrap.

For each BetB2B skin, this script:

  1. Launches a headless Playwright browser
  2. Navigates to a scheduled NBA Summer League match page on that skin's domain
  3. Waits for SPA hydration (20s) so session cookies get set
  4. Harvests the browser cookies
  5. Calls the H2H endpoint via httpx with those cookies + real betting headers
  6. Validates the JSON response (teams[], gameShorts[])

This mirrors the actual hybrid extraction mode (ADR-3/ADR-4) used by the
BetB2B scraper — not raw direct httpx.

Usage:
    # All skins
    python -m src.sites.betb2b.scripts.validate_h2h_cross_skin

    # Specific skins only
    python -m src.sites.betb2b.scripts.validate_h2h_cross_skin --skins linebet,melbet

    # Non-headless for debugging
    python -m src.sites.betb2b.scripts.validate_h2h_cross_skin --visible
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from ._common import ensure_repo_on_path, output_dir

ensure_repo_on_path()

from src.sites.betb2b.config import BetB2BSkinConfig

# The game ID from our linebet NBA Summer League discovery.
# All BetB2B skins share the same backend, so this ID works across domains.
KNOWN_GAME_ID = "737455106"

# The event URL slug from discovery — universal across BetB2B backend
KNOWN_EVENT_SLUG = "/en/line/basketball/75093-nba-summer-league/352015844-oklahoma-city-thunder-brooklyn-nets"

# Real betting headers matching what __BETTING_APP__ sends
BETTING_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "is-srv": "false",
    "x-app-n": "__BETTING_APP__",
    "x-svc-source": "__BETTING_APP__",
    "x-requested-with": "XMLHttpRequest",
    "x-mobile-project-id": "0",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def load_all_skins() -> Dict[str, BetB2BSkinConfig]:
    """Load all BetB2B skin configs from the YAML directory."""
    skins_dir = Path(__file__).resolve().parents[1] / "skins"
    skins: Dict[str, BetB2BSkinConfig] = {}
    for yaml_file in sorted(skins_dir.glob("*.yaml")):
        name = yaml_file.stem
        try:
            config = BetB2BSkinConfig.from_yaml(str(yaml_file))
            skins[name] = config
        except Exception as e:
            print(f"  [SKIP] {name}: failed to load config: {e}")
    return skins


def build_h2h_url(skin: BetB2BSkinConfig, game_id: str = KNOWN_GAME_ID) -> str:
    """Build the H2H endpoint URL with the skin's specific params."""
    return (
        f"{skin.base_url}/service-api/statisticfeed/api/v1/Game/h2h"
        f"?id={game_id}"
        f"&lng={skin.language}"
        f"&ref={skin.partner}"
        f"&fcountry={skin.country}"
        f"&gr={skin.gr}"
    )


def build_match_url(skin: BetB2BSkinConfig) -> str:
    """Build the scheduled match page URL on the skin's domain."""
    return f"{skin.base_url}{KNOWN_EVENT_SLUG}"


async def bootstrap_and_test_skin(
    skin: BetB2BSkinConfig,
    headless: bool = True,
) -> Dict[str, Any]:
    """Full hybrid bootstrap for one skin: browser -> cookies -> httpx -> H2H."""
    from playwright.async_api import async_playwright

    match_url = build_match_url(skin)
    h2h_url = build_h2h_url(skin)

    result: Dict[str, Any] = {
        "skin": skin.name,
        "domain": skin.domain,
        "params": {"ref": skin.partner, "gr": skin.gr, "fcountry": skin.country},
        "match_url": match_url,
        "h2h_url": h2h_url,
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1536, "height": 864},
            locale="en-US",
        )
        page = await context.new_page()

        all_api_responses: List[Dict] = []

        async def on_response(response):
            u = response.url
            if skin.domain not in u:
                return
            if re.search(r'\.(js|css|png|svg|ico|woff2?|gif|webp|ttf|eot|jpg|jpeg)(\?|$)', u):
                return
            try:
                raw = await response.body()
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                return
            all_api_responses.append({
                "url": u, "status": response.status, "body_length": len(body),
            })

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        # --- Bootstrap ---
        start = time.monotonic()
        try:
            print(f"    Navigating to {match_url}", flush=True)
            await page.goto(match_url, wait_until="load", timeout=90000)
            await asyncio.sleep(25)
        except Exception as e:
            result["bootstrap_error"] = str(e)[:200]

        # --- Harvest cookies ---
        cookies = await context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        # --- Check page state ---
        try:
            result["final_url"] = page.url
            result["page_title"] = await page.title()
            result["has_betting_app"] = await page.evaluate(
                '() => document.querySelector("#__BETTING_APP__")?.innerText?.length > 50'
            )
        except Exception as e:
            result["page_eval_error"] = str(e)[:100]

        result["bootstrap_elapsed_s"] = round(time.monotonic() - start, 2)
        result["harvested_cookies"] = len(cookie_dict)
        result["api_responses_count"] = len(all_api_responses)

        await browser.close()

    # --- Phase 2: httpx with harvested cookies ---
    if not cookie_dict:
        result["httpx"] = {
            "error": "No cookies harvested — cannot make authenticated request",
        }
        return result

    # Patch origin/referer headers per skin
    headers = dict(BETTING_HEADERS)
    headers["origin"] = skin.base_url
    headers["referer"] = f"{skin.base_url}/"

    h2h_start = time.monotonic()
    try:
        async with httpx.AsyncClient(verify=False, follow_redirects=False) as client:
            resp = await client.get(
                h2h_url, headers=headers, cookies=cookie_dict, timeout=30,
            )
        h2h_elapsed = round(time.monotonic() - h2h_start, 2)
        body = resp.text

        httpx_result: Dict[str, Any] = {
            "status": resp.status_code,
            "elapsed_s": h2h_elapsed,
            "body_length": len(body),
        }

        # Redirect = unauthenticated
        if resp.status_code in (301, 302, 307, 308):
            httpx_result["redirect"] = resp.headers.get("location", "")[:150]
            result["httpx"] = httpx_result
            return result

        # HTML response = blocked / redirected to landing page
        body_stripped = body.strip()
        if body_stripped.startswith("<!DOCTYPE") or body_stripped.startswith("<html"):
            httpx_result["error"] = "Got HTML page instead of JSON"
            httpx_result["html_preview"] = body[:300]
            result["httpx"] = httpx_result
            return result

        # Parse JSON
        data = json.loads(body)
        teams = data.get("teams", [])
        games = data.get("gameShorts", [])
        httpx_result["teams_count"] = len(teams)
        httpx_result["games_count"] = len(games)
        httpx_result["sport_id"] = data.get("sportId")
        httpx_result["has_valid_data"] = len(teams) > 0 and len(games) > 0
        httpx_result["team_names"] = [t.get("title", "?") for t in teams[:4]]
        if games:
            httpx_result["sample_game"] = {
                "dateStart": games[0].get("dateStart"),
                "score": f"{games[0].get('score1','?')}-{games[0].get('score2','?')}",
                "periods": len(games[0].get("periods", [])),
            }

        result["httpx"] = httpx_result

    except json.JSONDecodeError as e:
        result["httpx"] = {
            "error": f"JSON decode error: {e}",
            "body_preview": body[:300],  # type: ignore[possibly-undefined]
            "status": resp.status_code,  # type: ignore[possibly-undefined]
            "elapsed_s": round(time.monotonic() - h2h_start, 2),
        }
    except Exception as e:
        result["httpx"] = {
            "error": str(e)[:200],
            "elapsed_s": round(time.monotonic() - h2h_start, 2),
        }

    return result


async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Cross-skin H2H validation via hybrid bootstrap"
    )
    parser.add_argument(
        "--skins", type=str, default=None,
        help="Comma-separated skin names to test (default: all)",
    )
    parser.add_argument(
        "--visible", action="store_true",
        help="Run browser headful for debugging",
    )
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    skins = load_all_skins()
    if args.skins:
        filter_list = [s.strip() for s in args.skins.split(",")]
        skins = {k: v for k, v in skins.items() if k in filter_list}

    print(f"\n{'='*60}", flush=True)
    print(f"Cross-skin H2H Validation (hybrid bootstrap)", flush=True)
    print(f"Skins: {len(skins)}  |  Game ID: {KNOWN_GAME_ID}", flush=True)
    print(f"{'='*60}", flush=True)

    out_dir = Path(args.output) if args.output else output_dir("betb2b_h2h_cross_skin")

    results: List[Dict[str, Any]] = []

    for name, skin in skins.items():
        print(f"\n--- {name} ({skin.domain}) ---", flush=True)
        r = await bootstrap_and_test_skin(skin, headless=not args.visible)

        h = r.get("httpx", {}) or {}
        if h.get("has_valid_data"):
            print(f"  ✅ H2H: {h['status']} - {h.get('games_count','?')} games, "
                  f"{h.get('teams_count','?')} teams in {h.get('elapsed_s','?')}s",
                  flush=True)
            print(f"     Teams: {', '.join(h.get('team_names', []))}", flush=True)
            if h.get("sample_game"):
                sg = h["sample_game"]
                print(f"     Sample: score {sg['score']}, {sg['periods']} periods",
                      flush=True)
        elif h.get("error"):
            print(f"  ❌ {h['error']}", flush=True)
        elif h.get("status") == 200:
            print(f"  ⚠️  200 but no data ({h.get('teams_count','?')} teams, "
                  f"{h.get('games_count','?')} games)", flush=True)
        elif h.get("status"):
            loc = h.get("redirect", "")[:80]
            print(f"  ❌ HTTP {h['status']} - {loc}", flush=True)
        else:
            print(f"  💥 No httpx result", flush=True)

        print(f"     Cookies: {r.get('harvested_cookies', 0)} | "
              f"Bootstrap: {r.get('bootstrap_elapsed_s','?')}s | "
              f"API: {r.get('api_responses_count', 0)}", flush=True)

        results.append(r)

    # --- Summary ---
    print(f"\n{'='*60}", flush=True)
    print("SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"{'Skin':<15} {'Domain':<22} {'Status':<10} {'Games':<8} {'Teams':<8} "
          f"{'Cookies':<8}", flush=True)
    print(f"{'─'*15} {'─'*22} {'─'*10} {'─'*8} {'─'*8} {'─'*8}", flush=True)

    for r in results:
        h = r.get("httpx", {}) or {}
        if h.get("has_valid_data"):
            status = f"✅ {h['status']}"
            games = str(h["games_count"])
            teams = str(h["teams_count"])
        elif h.get("error") or h.get("status") in (301, 302, 307, 308):
            status = f"❌ {h.get('status','ERR')}"
            games = teams = "—"
        else:
            status = "💥 FAIL"
            games = teams = "—"

        print(f"{r['skin']:<15} {r['domain']:<22} {status:<10} {games:<8} {teams:<8} "
              f"{r.get('harvested_cookies', 0):<8}", flush=True)

    print(f"{'─'*15} {'─'*22} {'─'*10} {'─'*8} {'─'*8} {'─'*8}", flush=True)

    # Save
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "game_id": KNOWN_GAME_ID,
        "skin_count": len(results),
        "working": sum(1 for r in results if r.get("httpx", {}).get("has_valid_data")),
        "results": results,
    }
    (out_dir / "h2h_cross_skin_results.json").write_text(
        json.dumps(output, indent=2, default=str, ensure_ascii=False), encoding="utf-8",
    )
    print(f"\nFull results: {out_dir / 'h2h_cross_skin_results.json'}", flush=True)

    working = output["working"]
    print(f"\nCONCLUSION: {working}/{len(results)} skins have working H2H "
          f"via hybrid bootstrap", flush=True)
    if working < len(results):
        failed = [r["skin"] for r in results
                  if not r.get("httpx", {}).get("has_valid_data")]
        print(f"Failed: {', '.join(failed)}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
