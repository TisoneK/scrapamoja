"""Probe linebet.com with multiple browser profiles to find one that works.

Tries default Chromium, Chrome 124 (Linux + Windows UA), and Firefox.
For each profile, captures the first ~30 responses so we can study the
real API endpoints + request headers.

Output: ``<out>/probe_summary.json`` + per-profile capture files.

Run as:
    python -m src.sites.linebet.scripts.probe_profiles
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List

from ._common import output_dir

from playwright.async_api import async_playwright


PROFILES: List[Dict[str, Any]] = [
    {
        "name": "default_chromium",
        "user_agent": None,
        "extra_http_headers": {},
        "locale": "en-US",
        "timezone": "America/New_York",
    },
    {
        "name": "chrome_124_linux",
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "extra_http_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        "locale": "en-US",
        "timezone": "America/New_York",
    },
    {
        "name": "chrome_124_win10",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "extra_http_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        "locale": "en-US",
        "timezone": "America/New_York",
    },
]


async def try_profile(pw, profile: Dict[str, Any]) -> Dict[str, Any]:
    name = profile["name"]
    result: Dict[str, Any] = {"profile": name, "captured": []}

    browser = await pw.chromium.launch(headless=True)
    try:
        kwargs: Dict[str, Any] = {
            "viewport": {"width": 1536, "height": 864},
            "locale": profile["locale"],
            "timezone_id": profile["timezone"],
        }
        if profile["user_agent"]:
            kwargs["user_agent"] = profile["user_agent"]
        if profile["extra_http_headers"]:
            kwargs["extra_http_headers"] = profile["extra_http_headers"]

        ctx = await browser.new_context(**kwargs)
        page = await ctx.new_page()

        captured: List[Dict[str, Any]] = []

        async def on_response(response):
            try:
                req = response.request
                captured.append({
                    "url": response.url,
                    "status": response.status,
                    "method": req.method,
                    "request_headers": dict(req.headers),
                    "response_headers": dict(response.headers),
                })
            except Exception:
                pass

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        try:
            resp = await page.goto(
                "https://linebet.com/en",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            result["status"] = resp.status if resp else None
            result["final_url"] = page.url
            result["title"] = await page.title()
            await asyncio.sleep(8)
            result["captured"] = captured
            result["blocked"] = (
                (resp.status == 203 if resp else False)
                or page.url.endswith("/block")
            )
        except Exception as exc:
            result["error"] = f"navigation failed: {exc}"
            result["captured"] = captured

        await ctx.close()
    finally:
        await browser.close()

    return result


async def main() -> int:
    out_dir = output_dir("linebet_probe")
    summary: List[Dict[str, Any]] = []

    async with async_playwright() as pw:
        for profile in PROFILES:
            print(f"\n=== Trying profile: {profile['name']} ===", flush=True)
            result = await try_profile(pw, profile)
            n_cap = len(result.get("captured", []))
            blocked = result.get("blocked", False)
            print(f"  status={result.get('status')} blocked={blocked} captured={n_cap}", flush=True)

            cap_path = out_dir / f"captures_{profile['name']}.json"
            cap_path.write_text(json.dumps(result.get("captured", []), indent=2, default=str))
            print(f"  saved captures to {cap_path}", flush=True)

            trimmed = {k: v for k, v in result.items() if k != "captured"}
            trimmed["captured_count"] = n_cap
            trimmed["captures_file"] = str(cap_path)
            summary.append(trimmed)

    summary_path = out_dir / "probe_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nSummary: {summary_path}", flush=True)
    for s in summary:
        print(f"  {s['profile']:25s} blocked={s.get('blocked', '?'):>5}  captured={s.get('captured_count', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
