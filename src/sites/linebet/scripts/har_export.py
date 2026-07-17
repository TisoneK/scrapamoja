"""HAR exporter — record a browser session and dump it as a HAR file.

This is the **production** solution to Linebet's WAF block. The sandbox
/ datacenter IPs are blocked, but a residential IP is not. So the
workflow is:

  1. Operator (with a residential IP) runs this script. It launches a
     REAL Playwright browser, navigates through linebet.com, and exports
     the full network trace as a HAR file.
  2. Operator ships the HAR file to the developer (or commits it to the
     repo under src/sites/linebet/snapshots/raw/).
  3. Developer runs ``python -m src.sites.linebet.scripts.har_replay
     <input.har>`` to extract events from the HAR — no live browser
     needed.

Run as:
    python -m src.sites.linebet.scripts.har_export --output my_session.har

Options:
    --output PATH       Where to write the HAR file (default: linebet.har)
    --url URL           Entry URL (default: https://linebet.com/en)
    --live              Also visit /en/live after the home page
    --scroll N          Number of times to scroll the fixtures list
    --settle SECONDS    How long to wait after each navigation
    --headed            Show the browser window (useful if a CAPTCHA
                        needs to be solved manually)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from ._common import output_dir

from playwright.async_api import async_playwright


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, default=Path("linebet.har"),
                        help="Where to write the HAR file")
    parser.add_argument("--url", default="https://linebet.com/en",
                        help="Entry URL (default: https://linebet.com/en)")
    parser.add_argument("--live", action="store_true",
                        help="Also visit /en/live after the home page")
    parser.add_argument("--scroll", type=int, default=5,
                        help="Number of times to scroll the fixtures list (default: 5)")
    parser.add_argument("--settle", type=float, default=15.0,
                        help="Seconds to wait after each navigation (default: 15)")
    parser.add_argument("--headed", action="store_true",
                        help="Show the browser window (useful for manual CAPTCHA solving)")
    args = parser.parse_args()

    if not args.output.is_absolute():
        args.output = output_dir("linebet_har") / args.output

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1536, "height": 864},
            locale="en-US",
            timezone_id="Europe/London",
            record_har_path=str(args.output),
            record_har_content="embed",  # include response bodies in the HAR
        )
        page = await context.new_page()

        try:
            print(f"Navigating to {args.url} ...", flush=True)
            resp = await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            if resp and resp.status == 203:
                print(
                    f"WARNING: WAF block (status=203). The HAR will only "
                    "contain the technical-pages API calls. To capture the "
                    "actual sports data, run this script from a residential "
                    "IP (or use --headed and solve the CAPTCHA if shown).",
                    flush=True,
                )

            # Scroll to trigger lazy-loaded fixtures
            for i in range(args.scroll):
                await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                await asyncio.sleep(1.5)
                print(f"  scrolled {i+1}/{args.scroll}", flush=True)

            print(f"Waiting {args.settle}s for API calls to settle...", flush=True)
            await asyncio.sleep(args.settle)

            if args.live:
                live_url = "https://linebet.com/en/live"
                print(f"Navigating to {live_url} ...", flush=True)
                await page.goto(live_url, wait_until="domcontentloaded", timeout=60000)
                for i in range(args.scroll):
                    await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                    await asyncio.sleep(1.5)
                await asyncio.sleep(args.settle)

        finally:
            await context.close()  # this flushes the HAR to disk
            await browser.close()

    size = args.output.stat().st_size
    print(f"\nHAR written: {args.output} ({size:,} bytes)", flush=True)
    print(f"Replay with: python -m src.sites.linebet.scripts.har_replay "
          f"{args.output} <output.json>", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
