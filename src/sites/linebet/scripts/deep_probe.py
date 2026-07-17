"""Deep probe — try alternative Linebet URLs to discover sports data endpoints.

The WAF blocks /en -> /en/block, but maybe alternative entry points
(/en/prematch, /en/live, /m/en, sport-specific URLs) won't be blocked,
or will at least fire additional API calls before the block kicks in.

Output: ``<out>/deep_probe_summary.json`` + per-URL capture files.

Run as:
    python -m src.sites.linebet.scripts.deep_probe
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List

from ._common import output_dir

from playwright.async_api import async_playwright


ENTRY_POINTS = [
    "https://linebet.com/en/prematch",
    "https://linebet.com/en/live",
    "https://m.linebet.com/en",
    "https://linebet.com/en/sport/1",
    "https://linebet.com/en/sport/football",
]


async def probe_entry(pw, url: str) -> Dict[str, Any]:
    captured: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {"entry": url, "captured": []}

    browser = await pw.chromium.launch(headless=True)
    try:
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1536, "height": 864},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = await ctx.new_page()

        async def on_response(response):
            u = response.url
            if "linebet.com" not in u:
                return
            if not any(p in u for p in ("/bff-api/", "/fatman-api/", "/analytics-module-api/")):
                return
            try:
                req = response.request
                body: str = ""
                try:
                    raw = await response.body()
                    body = raw.decode("utf-8", errors="replace")[:3000]
                except Exception:
                    body = ""
                captured.append({
                    "url": u, "status": response.status, "method": req.method,
                    "body": body,
                })
            except Exception:
                pass

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            result["status"] = resp.status if resp else None
            result["final_url"] = page.url
            result["title"] = await page.title()
            await asyncio.sleep(10)
            result["captured"] = captured
            result["blocked"] = (
                (resp.status == 203 if resp else False)
                or page.url.endswith("/block")
            )
        except Exception as exc:
            result["error"] = str(exc)
            result["captured"] = captured

        await ctx.close()
    finally:
        await browser.close()

    return result


async def main() -> int:
    out_dir = output_dir("linebet_probe")
    summary: List[Dict[str, Any]] = []

    async with async_playwright() as pw:
        for url in ENTRY_POINTS:
            print(f"\n=== Probing {url} ===", flush=True)
            r = await probe_entry(pw, url)
            n = len(r.get("captured", []))
            print(f"  status={r.get('status')} blocked={r.get('blocked')} captured={n}", flush=True)

            safe_name = url.replace("/", "_").replace(":", "")[-60:]
            cap_path = out_dir / f"deep_{safe_name}.json"
            cap_path.write_text(json.dumps(r.get("captured", []), indent=2, default=str))

            paths = set()
            for c in r.get("captured", []):
                u = c["url"]
                if "/bff-api/" in u:
                    paths.add("/bff-api/" + u.split("/bff-api/")[1].split("?")[0])
                elif "/fatman-api/" in u:
                    paths.add("/fatman-api/...")
                elif "/analytics-module-api/" in u:
                    paths.add("/analytics-module-api/" + u.split("/analytics-module-api/")[1].split("?")[0])
            if paths:
                print(f"  unique endpoint paths:", flush=True)
                for p in sorted(paths):
                    print(f"    {p}", flush=True)

            trimmed = {k: v for k, v in r.items() if k != "captured"}
            trimmed["captured_count"] = n
            trimmed["unique_paths"] = sorted(paths)
            summary.append(trimmed)

    summary_path = out_dir / "deep_probe_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nSummary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
