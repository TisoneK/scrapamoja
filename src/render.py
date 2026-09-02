"""General-purpose stealth page renderer — one URL in, rendered text out.

Scrapamoja's site CLIs are sport-specific; this is the *general* entry point so
other tools (e.g. LocalMind's web acquisition) can reuse Scrapamoja's stealth
browser for ANY heavy-JS / skeleton / anti-bot site, not just configured ones.

    python -m src.render <url> [--wait 2.5] [--timeout 30] [--json]

It navigates with a real (stealth) Chromium, waits for client-side hydration,
best-effort dismisses consent dialogs, and prints the rendered text. With
--json it emits {url,title,text,status,method} on stdout so a caller can parse
it deterministically; the process prints NOTHING else to stdout (logs → stderr).

Primary path uses Scrapamoja's BrowserManager/session (its full stealth setup);
if that API is unavailable it falls back to raw Playwright with a minimal
webdriver mask, so the renderer always works.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional


def _err(*a: object) -> None:
    print(*a, file=sys.stderr, flush=True)


async def _extract(page, wait: float) -> tuple[str, str]:
    """Wait for hydration, best-effort accept consent, return (title, text)."""
    # Let client-side rendering settle beyond initial load.
    try:
        await page.wait_for_load_state("networkidle", timeout=int(wait * 1000) + 8000)
    except Exception:
        pass
    if wait > 0:
        await asyncio.sleep(wait)
    # Best-effort consent dismissal (Scrapamoja's handler if importable).
    try:
        from src.stealth.consent_handler import ConsentHandler  # type: ignore
        await ConsentHandler().detect_and_accept(page)
        await asyncio.sleep(0.3)
    except Exception:
        pass
    title = ""
    try:
        title = (await page.title()) or ""
    except Exception:
        pass
    text = ""
    try:
        text = await page.evaluate("document.body ? document.body.innerText : ''")
    except Exception:
        pass
    return title, (text or "").strip()


async def _render_via_manager(url: str, wait: float, timeout: float) -> Optional[dict]:
    """Primary: Scrapamoja BrowserManager + stealth session."""
    try:
        from src.browser.manager import BrowserManager
        from src.browser.config import BrowserConfiguration
    except Exception as e:
        _err(f"[render] manager import failed ({e}); using fallback")
        return None
    mgr = BrowserManager(site_id="render")
    try:
        await mgr.initialize()
        session = await mgr.create_session(BrowserConfiguration(headless=True))
        page = await session.create_page()
        try:
            from src.stealth.anti_detection import AntiDetection  # type: ignore
            await AntiDetection().apply_masks(page.context)
        except Exception:
            pass
        await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
        title, text = await _extract(page, wait)
        return {"url": url, "title": title, "text": text,
                "status": "ok" if text else "empty", "method": "scrapamoja_stealth"}
    except Exception as e:
        _err(f"[render] manager path failed: {e}")
        return None
    finally:
        try:
            await mgr.close_all_sessions()
            await mgr.shutdown()
        except Exception:
            pass


async def _render_via_playwright(url: str, wait: float, timeout: float) -> dict:
    """Fallback: raw Playwright with a minimal stealth init script."""
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    try:
        ctx = await browser.new_context(
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
            viewport={"width": 1366, "height": 900},
            locale="en-US",
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
        title, text = await _extract(page, wait)
        return {"url": url, "title": title, "text": text,
                "status": "ok" if text else "empty", "method": "playwright_fallback"}
    finally:
        try:
            await browser.close()
            await pw.stop()
        except Exception:
            pass


async def render(url: str, wait: float, timeout: float) -> dict:
    result = await _render_via_manager(url, wait, timeout)
    if result is None or result.get("status") == "empty":
        _err("[render] falling back to raw Playwright")
        try:
            result = await _render_via_playwright(url, wait, timeout)
        except Exception as e:
            return {"url": url, "title": "", "text": "", "status": "error",
                    "method": "none", "error": str(e)}
    return result


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="render", description="Stealth-render a URL to text.")
    ap.add_argument("url")
    ap.add_argument("--wait", type=float, default=2.0, help="extra hydration wait (s)")
    ap.add_argument("--timeout", type=float, default=30.0, help="navigation timeout (s)")
    ap.add_argument("--json", action="store_true", help="emit JSON on stdout")
    args = ap.parse_args(argv)
    result = asyncio.run(render(args.url, args.wait, args.timeout))
    if args.json:
        # Scrapamoja's structlog writes to stdout, so a bare print of the JSON
        # would be mixed with log lines. Emit on a unique sentinel line the
        # caller greps for — robust against any log noise on the stream.
        print(_JSON_SENTINEL + json.dumps(result, ensure_ascii=False))
    else:
        print(result.get("text", ""))
    return 0 if result.get("status") == "ok" else 2


# Callers extract the JSON as the substring after this marker on its line.
_JSON_SENTINEL = "@@RENDER_JSON@@ "


if __name__ == "__main__":
    sys.exit(main())
