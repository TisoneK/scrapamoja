"""Validate the Linebet scraper against the live site.

Runs ``action="raw_capture"`` then ``action="list_all"`` against
linebet.com, persists captured JSON, runs the extractor, and writes a
summary. Designed for operator use from a residential IP — from the
sandbox, the WAF block is detected and reported clearly.

Run as:
    python -m src.sites.linebet.scripts.validate_live
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ._common import ensure_repo_on_path, output_dir

ensure_repo_on_path()

from playwright.async_api import async_playwright  # noqa: E402
from src.selectors.engine import SelectorEngine  # noqa: E402
from src.sites.linebet import LinebetScraper  # noqa: E402
from src.sites.linebet.extraction.rules import LinebetExtractionRules  # noqa: E402


async def main() -> int:
    out_dir = output_dir("linebet_validate")
    summary_path = out_dir / "summary.json"
    captured_dir = out_dir / "captured"
    captured_dir.mkdir(parents=True, exist_ok=True)

    summary: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1536, "height": 864},
            locale="en-US",
            timezone_id="Europe/London",
        )
        page = await context.new_page()

        engine = SelectorEngine()
        scraper = LinebetScraper(page, engine)
        await scraper.initialize(page, engine)
        summary["steps"].append({"step": "initialize", "ok": True})

        # Pre-flight: detect WAF block (HTTP 203 + redirect to /en/block).
        print("[1/3] Pre-flight: navigating to linebet.com/en ...", flush=True)
        try:
            pre_resp = await page.goto(
                "https://linebet.com/en",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            pre_status = pre_resp.status if pre_resp else 0
            pre_url = page.url
            if pre_status == 203 or pre_url.endswith("/block"):
                block_msg = (
                    f"Linebet WAF block detected — status={pre_status}, "
                    f"redirected to {pre_url}. The sandbox / datacenter IP "
                    "is blocked. Run from a residential IP, or use the HAR "
                    "export + replay path (see scripts/har_export.py + "
                    "scripts/har_replay.py)."
                )
                print(f"    {block_msg}", flush=True)
                summary["steps"].append({
                    "step": "preflight", "ok": False, "blocked": True,
                    "error": block_msg, "status": pre_status, "url": pre_url,
                })
                summary["waf_block_detected"] = True
                await browser.close()
                summary["finished_at"] = datetime.now(timezone.utc).isoformat()
                summary_path.write_text(json.dumps(summary, indent=2))
                print(f"\nSummary: {summary_path}", flush=True)
                return 0
            await page.goto("about:blank")
        except Exception as exc:
            summary["steps"].append({
                "step": "preflight", "ok": False, "error": str(exc),
            })
            print(f"    preflight FAILED: {exc}", flush=True)
            await browser.close()
            summary_path.write_text(json.dumps(summary, indent=2))
            return 1

        # Step 2: raw_capture
        print("[2/3] Running raw_capture ...", flush=True)
        try:
            raw_result = await scraper.scrape(
                action="raw_capture",
                settle_seconds=15.0,
                scroll_count=4,
                timeout_seconds=90.0,
            )
            summary["steps"].append({
                "step": "raw_capture",
                "ok": raw_result.get("error") is None,
                "error": raw_result.get("error"),
                "url": raw_result.get("url"),
                "captured_response_count": raw_result.get("captured_response_count", 0),
                "scrape_duration_seconds": raw_result.get("scrape_duration_seconds"),
            })
            captured = raw_result.get("captured_responses", [])
            print(f"    Captured {len(captured)} responses", flush=True)
        except Exception as exc:
            summary["steps"].append({"step": "raw_capture", "ok": False, "error": str(exc)})
            print(f"    raw_capture FAILED: {exc}", flush=True)
            await browser.close()
            summary_path.write_text(json.dumps(summary, indent=2))
            return 1

        # Step 3: list_all + extraction
        print("[3/3] Running list_all with extraction ...", flush=True)
        try:
            extracted_result = await scraper.scrape(
                action="list_all",
                settle_seconds=15.0,
                scroll_count=4,
                timeout_seconds=120.0,
            )
            summary["steps"].append({
                "step": "list_all_extract",
                "ok": extracted_result.get("error") is None,
                "error": extracted_result.get("error"),
                "event_count": extracted_result.get("event_count", 0),
                "captured_response_count": extracted_result.get("captured_response_count", 0),
                "scrape_duration_seconds": extracted_result.get("scrape_duration_seconds"),
            })
            events = extracted_result.get("events", [])
            print(f"    Extracted {len(events)} events", flush=True)
            (out_dir / "events.json").write_text(json.dumps(events, indent=2, default=str))
            (out_dir / "captures.json").write_text(
                json.dumps(extracted_result.get("captured_responses", []), indent=2, default=str)
            )
        except Exception as exc:
            summary["steps"].append({
                "step": "list_all_extract", "ok": False, "error": str(exc),
            })
            print(f"    list_all FAILED: {exc}", flush=True)

        await browser.close()

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
