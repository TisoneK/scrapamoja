"""Capture real Linebet API response bodies.

Even when the WAF blocks the SPA's main app, the technical-pages app
still fires several real Linebet API calls (/bff-api/, /fatman-api/)
whose responses we can study. This script captures the full response
bodies for those endpoints so the extractor can be tuned against real
JSON, not guessed.

Output: ``<out>/real_api_bodies.json``

Run as:
    python -m src.sites.linebet.scripts.capture_real_bodies
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List

from ._common import output_dir

from playwright.async_api import async_playwright


async def main() -> int:
    out_dir = output_dir("linebet_probe")
    captured: List[Dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1536, "height": 864},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Chromium";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Linux"',
            },
        )
        page = await ctx.new_page()

        async def on_response(response):
            url = response.url
            if not any(p in url for p in ("/bff-api/", "/fatman-api/", "/analytics-module-api/", "/genfiles/")):
                return
            if "/genfiles/" in url and ".json" not in url:
                return
            try:
                req = response.request
                body: str = ""
                try:
                    raw = await response.body()
                    body = raw.decode("utf-8", errors="replace")[:5000]
                except Exception:
                    body = "<body capture failed>"

                captured.append({
                    "url": url,
                    "status": response.status,
                    "method": req.method,
                    "request_headers": dict(req.headers),
                    "response_headers": dict(response.headers),
                    "body": body,
                })
                print(f"  [{response.status}] {req.method} {url[:90]}", flush=True)
            except Exception as exc:
                print(f"  capture error for {url}: {exc}", flush=True)

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        try:
            await page.goto("https://linebet.com/en", wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            print(f"  navigation: {exc}", flush=True)

        print("  waiting 12s for API calls to settle...", flush=True)
        await asyncio.sleep(12)
        await browser.close()

    out_path = out_dir / "real_api_bodies.json"
    out_path.write_text(json.dumps(captured, indent=2, default=str))
    print(f"\nCaptured {len(captured)} API responses with bodies", flush=True)
    print(f"Written to: {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
