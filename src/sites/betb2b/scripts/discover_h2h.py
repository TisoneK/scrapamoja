"""Discover H2H — navigate to a specific scheduled match and hover team names.

For scheduled (pre-match) matches from major leagues, H2H data appears as
a hover tooltip over team names labeled "Recent Games" or "Previous meetings".
This script navigates directly to a specific match URL, captures all API
responses, and looks for H2H data triggered by hovering team names.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

from ._common import ensure_repo_on_path, output_dir

ensure_repo_on_path()


# NBA Summer League — Oklahoma City Thunder vs Brooklyn Nets
DEFAULT_MATCH_URL = (
    "https://linebet.com/en/line/basketball/75093-nba-summer-league/"
    "352015844-oklahoma-city-thunder-brooklyn-nets"
)


async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--skin", default="linebet")
    parser.add_argument("--wait", type=int, default=20,
                        help="Seconds to wait for SPA hydration (default 20)")
    parser.add_argument("--match-url", default=DEFAULT_MATCH_URL,
                        help="Specific match page URL to visit")
    args = parser.parse_args()

    out = output_dir("betb2b_h2h_discovery")
    print(f"Output dir: {out}", flush=True)
    print(f"Match URL: {args.match_url}", flush=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            viewport={"width": 1536, "height": 864},
            locale="en-US",
        )
        page = await context.new_page()

        # Capture ALL responses on linebet.com + v3.traincdn.com
        all_responses: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        async def on_response(response):
            u = response.url
            # Only capture from linebet.com (or CDN data endpoints)
            if "linebet.com" not in u and "traincdn.com" not in u:
                return
            if re.search(r'\.(js|css|png|svg|ico|woff2?|gif|webp|ttf|eot|jpg|jpeg)(\?|$)', u):
                return
            try:
                raw = await response.body()
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                body = "<error>"
            rid = f"{u}:{len(body)}"
            if rid in seen:
                return
            seen.add(rid)
            entry = {"url": u, "status": response.status,
                     "method": response.request.method,
                     "body_length": len(body),
                     "body": body[:60000]}
            all_responses.append(entry)
            # Print interesting ones immediately
            if any(p in u for p in ("/service-api/", "/champs-api/", "statistic",
                                     "getgame", "livedata", "express",
                                     "h2h", "meeting", "history", "recent")):
                print(f"  [★ API] {response.status} {u[:150]} ({len(body)}b)", flush=True)
            elif "/linebet.com/" in u and not re.search(r'\.(js|css|png|svg|ico)(\?|$)', u):
                print(f"  [resp] {response.status} {u[:130]} ({len(body)}b)", flush=True)

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        # ----- Navigate directly to match page -----
        print(f"\n--- Navigate to scheduled match page ---", flush=True)
        await page.goto(args.match_url, wait_until="load", timeout=90000)
        print(f"  URL: {page.url}", flush=True)

        # Wait for SPA hydration
        print(f"  Waiting {args.wait}s for SPA hydration...", flush=True)
        await asyncio.sleep(args.wait)

        # Save HTML and screenshot BEFORE hover
        html = await page.content()
        (out / "match_page_full.html").write_text(html, encoding="utf-8")
        await page.screenshot(path=str(out / "01_match_page.png"), full_page=True)
        print(f"  Page HTML: {len(html)}b", flush=True)

        # Check if betting app loaded
        has_betting = await page.evaluate(
            '() => document.querySelector("#__BETTING_APP__")?.innerText?.length > 50'
        )
        print(f"  Betting app loaded: {has_betting}", flush=True)

        # Count all non-static responses so far
        init_resp_count = len(all_responses)
        print(f"  Responses captured before hover: {init_resp_count}", flush=True)

        # ----- 1) Check for visible H2H / Recent Games sections -----
        print(f"\n--- Scanning for H2H content in visible DOM ---", flush=True)
        h2h_sections = await page.evaluate("""() => {
            const found = [];
            const keywords = ['recent games', 'previous meetings', 'h2h',
                'head to head', 'last matches', 'past meetings', 'form',
                'team history', 'match history', 'versus', 'vs history',
                'meeting history', 'head2head'];
            // Search all visible elements
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (!el.offsetParent && el.tagName !== 'SCRIPT') continue;
                const text = (el.innerText || '').trim();
                if (!text || text.length < 3) continue;
                const lower = text.toLowerCase();
                for (const kw of keywords) {
                    if (lower.includes(kw) && text.length < 200) {
                        if (!found.find(f => f.text === text)) {
                            const r = el.getBoundingClientRect();
                            found.push({
                                tag: el.tagName,
                                cls: (el.className || '').substring(0, 100),
                                text: text.replace(/\\s+/g, ' ').substring(0, 250),
                                rect: {t: r.top, l: r.left, w: r.width, h: r.height},
                                visible: el.offsetParent !== null
                            });
                        }
                    }
                }
            }
            return found;
        }""")
        print(f"  H2H sections found in DOM: {len(h2h_sections)}", flush=True)
        for s in h2h_sections:
            vis = "VISIBLE" if s['visible'] else "HIDDEN"
            print(f"    [{vis}] {s['tag']}.{s['cls']}: {s['text'][:200]}", flush=True)

        # ----- 2) Find team-name elements for hover -----
        team_info = await page.evaluate("""() => {
            const result = [];
            const selectors = [
                '.scoreboard-team-name',
                '.scoreboard-team-name__text',
                '.dashboard-game-block__team',
                '[class*=team-name]',
                '[class*=teamName]'
            ];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const text = el.innerText?.trim() || '';
                    if (text && text.length < 50 && text.length > 0) {
                        if (!result.find(r => r.text === text)) {
                            result.push({text, selector: sel, tag: el.tagName,
                                cls: (el.className || '').substring(0, 80)});
                        }
                    }
                });
            }
            return result;
        }""")
        print(f"\n  Team elements found: {len(team_info)}", flush=True)
        for t in team_info:
            print(f"    '{t['text']}' ({t['selector']})", flush=True)

        # ----- 3) Hover over team names -----
        team_names = list(dict.fromkeys(t['text'] for t in team_info if t['text']))
        print(f"\n--- Hovering {len(team_names)} team names ---", flush=True)

        for i, name in enumerate(team_names):
            print(f"\n  [{i}] Hover: '{name}'", flush=True)

            # Strategy A: Playwright .hover() on matching elements
            for sel in [
                f':has-text("{name}")',
                f'.scoreboard-team-name:has-text("{name}")',
                f'.scoreboard-team-name__text:has-text("{name}")',
                f'[class*="team"]:has-text("{name}")',
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        print(f"    -> Playwright hover on '{sel}'", flush=True)
                        await el.hover(timeout=5000, force=True)
                        await asyncio.sleep(3)
                        break
                except Exception as e:
                    print(f"    -> hover failed on {sel}: {e}", flush=True)

            # Strategy B: JS dispatch mouse events
            count = await page.evaluate("""(name) => {
                const matches = [];
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.innerText?.trim() === name ||
                        el.textContent?.trim() === name) {
                        matches.push(el);
                    }
                }
                matches.forEach(el => {
                    el.scrollIntoView({block: 'center'});
                    const rect = el.getBoundingClientRect();
                    const cx = rect.left + rect.width/2;
                    const cy = rect.top + rect.height/2;
                    ['mouseenter','mouseover','mousemove','pointerenter',
                     'pointerover','pointermove'].forEach(type => {
                        el.dispatchEvent(new MouseEvent(type, {
                            bubbles: true, cancelable: true,
                            clientX: cx, clientY: cy
                        }));
                    });
                });
                return matches.length;
            }""", name)
            print(f"    -> JS mouse events dispatched to {count} elements", flush=True)
            await asyncio.sleep(4)

        # ----- 4) Take screenshot after hover -----
        await page.screenshot(path=str(out / "02_after_hover.png"), full_page=True)

        # ----- 5) Check for popups / tooltips that appeared -----
        print(f"\n--- Scanning for popups/tooltips after hover ---", flush=True)
        popup = await page.evaluate("""() => {
            const found = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (!el.offsetParent) continue;  // only visible elements
                const r = el.getBoundingClientRect();
                if (r.width < 80 || r.height < 30) continue;
                const text = el.innerText?.trim() || '';
                if (text.length < 5) continue;
                const lower = text.toLowerCase();
                // Look for H2H-related keywords
                const keywords = ['recent', 'previous', 'meeting', 'h2h', 'history',
                    'head to head', 'last match', 'past', 'versus', 'form', 'win',
                    'draw', 'loss', 'wins', 'losses', 'played'];
                const matchCount = keywords.filter(k => lower.includes(k)).length;
                if (matchCount >= 2 || lower.includes('recent games') ||
                    lower.includes('previous meetings') || lower.includes('h2h')) {
                    found.push({
                        tag: el.tagName,
                        cls: (el.className || '').substring(0, 100),
                        text: text.replace(/\\s+/g, ' ').substring(0, 400),
                        rect: {t: r.top, l: r.left, w: r.width, h: r.height},
                        matchCount
                    });
                }
            }
            return found;
        }""")
        print(f"  H2H popups detected: {len(popup)}", flush=True)
        for p in popup:
            print(f"    [{p['matchCount']} kw matches] {p['tag']}.{p['cls']}", flush=True)
            print(f"    Text: {p['text']}", flush=True)

        # ----- 6) Also check for mouseover-triggered iframes or shadow DOM -----
        print(f"\n--- Checking for iframes / shadow DOM ---", flush=True)
        iframes = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('iframe')).map(f => ({
                src: f.src || '(blank)',
                id: f.id,
                cls: (f.className || '').substring(0, 80),
                w: f.offsetWidth,
                h: f.offsetHeight,
                visible: f.offsetParent !== null
            }));
        }""")
        print(f"  Iframes found: {len(iframes)}", flush=True)
        for f in iframes:
            print(f"    {f['src'][:120]} ({f['w']}x{f['h']}, visible={f['visible']})", flush=True)

        # ----- 7) Summarize new responses -----
        new_responses = all_responses[init_resp_count:]
        print(f"\n{'='*60}", flush=True)
        print(f"Total responses: {len(all_responses)}", flush=True)
        print(f"Responses before hover: {init_resp_count}", flush=True)
        print(f"New responses after hover: {len(new_responses)}", flush=True)

        print(f"\nAll service-api / data endpoints:", flush=True)
        for r in all_responses:
            u = r["url"]
            is_new = all_responses.index(r) >= init_resp_count
            marker = " [NEW-after-hover]" if is_new else ""
            if any(p in u for p in ("/service-api/", "/champs-api/", "statistic",
                                     "getgame", "h2h", "meeting", "history",
                                     "recent", "express", "livedata")):
                print(f"  {r['status']} {u[:150]} ({r['body_length']}b){marker}", flush=True)

        # ----- 8) Save output -----
        output = {
            "match_url": args.match_url,
            "final_url": page.url,
            "betting_app_loaded": has_betting,
            "h2h_sections_in_dom": h2h_sections,
            "team_elements": team_info,
            "popups_after_hover": popup,
            "iframes": iframes,
            "responses_before_hover": init_resp_count,
            "responses": [{
                "url": r["url"], "status": r["status"],
                "body_length": r["body_length"],
                "body": r.get("body", "")[:30000],
            } for r in all_responses],
        }
        json_str = json.dumps(output, indent=2, default=str, ensure_ascii=False)
        (out / "h2h_discovery.json").write_text(json_str, encoding="utf-8")
        print(f"\nSaved: {out / 'h2h_discovery.json'}", flush=True)

        await browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
