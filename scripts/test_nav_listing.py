#!/usr/bin/env python3
"""Quick capability test — navigation + match listing only (fast)."""
import asyncio
import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from playwright.async_api import async_playwright


async def test_navigation_and_listing():
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # ── 1. Homepage ──
        t0 = time.time()
        try:
            await page.goto("https://www.flashscore.com/", wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(2000)
            # Dismiss cookies
            try:
                btn = await page.query_selector('[id*="onetrust-accept"], button:has-text("Accept")')
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass
            results['homepage'] = {'ok': True, 'time': f'{time.time()-t0:.1f}s', 'title': (await page.title())[:50]}
            print(f"✅ Homepage: {time.time()-t0:.1f}s — {results['homepage']['title']}")
        except Exception as e:
            results['homepage'] = {'ok': False, 'error': str(e)[:100]}
            print(f"❌ Homepage: {e}")
        
        # ── 2. Basketball page ──
        t0 = time.time()
        try:
            await page.goto("https://www.flashscore.com/basketball/", wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(3000)
            
            match_count = await page.evaluate("""
                () => document.querySelectorAll('[class*="event__match"]').length
            """)
            results['basketball_page'] = {'ok': match_count > 0, 'time': f'{time.time()-t0:.1f}s', 'matches': match_count}
            print(f"{'✅' if match_count else '❌'} Basketball page: {match_count} matches ({time.time()-t0:.1f}s)")
        except Exception as e:
            results['basketball_page'] = {'ok': False, 'error': str(e)[:100]}
            print(f"❌ Basketball page: {e}")
        
        # ── 3. Finished matches ──
        t0 = time.time()
        finished = []
        try:
            await page.goto("https://www.flashscore.com/basketball/?type=finished", wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(3000)
            
            finished = await page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('[class*="event__match"]');
                    return Array.from(rows).slice(0, 15).map(row => {
                        const home = row.querySelector('[class*="event__participant--home"]');
                        const away = row.querySelector('[class*="event__participant--away"]');
                        const link = row.querySelector('a[href*="/match/"]');
                        const scores = row.querySelectorAll('[class*="event__score"]');
                        return {
                            home: home ? home.textContent.trim().substring(0, 30) : '',
                            away: away ? away.textContent.trim().substring(0, 30) : '',
                            score: scores.length >= 2 ? scores[0].textContent.trim() + '-' + scores[1].textContent.trim() : '',
                            href: link ? link.getAttribute('href') : '',
                        };
                    }).filter(m => m.home || m.away);
                }
            """)
            results['finished_listing'] = {'ok': len(finished) > 0, 'count': len(finished), 'time': f'{time.time()-t0:.1f}s'}
            print(f"{'✅' if finished else '❌'} Finished: {len(finished)} matches ({time.time()-t0:.1f}s)")
            for m in finished[:5]:
                print(f"   {m['home']} {m['score']} {m['away']}")
        except Exception as e:
            results['finished_listing'] = {'ok': False, 'error': str(e)[:100]}
            print(f"❌ Finished listing: {e}")
        
        # ── 4. Scheduled matches ──
        t0 = time.time()
        scheduled = []
        try:
            await page.goto("https://www.flashscore.com/basketball/?type=scheduled", wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(3000)
            
            scheduled = await page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('[class*="event__match"]');
                    return Array.from(rows).slice(0, 15).map(row => {
                        const home = row.querySelector('[class*="event__participant--home"]');
                        const away = row.querySelector('[class*="event__participant--away"]');
                        const time = row.querySelector('[class*="event__time"]');
                        const link = row.querySelector('a[href*="/match/"]');
                        return {
                            home: home ? home.textContent.trim().substring(0, 30) : '',
                            away: away ? away.textContent.trim().substring(0, 30) : '',
                            time: time ? time.textContent.trim() : '',
                            href: link ? link.getAttribute('href') : '',
                        };
                    }).filter(m => m.home || m.away);
                }
            """)
            results['scheduled_listing'] = {'ok': len(scheduled) > 0, 'count': len(scheduled), 'time': f'{time.time()-t0:.1f}s'}
            print(f"{'✅' if scheduled else '❌'} Scheduled: {len(scheduled)} matches ({time.time()-t0:.1f}s)")
            for m in scheduled[:5]:
                print(f"   {m['time']} {m['home']} vs {m['away']}")
        except Exception as e:
            results['scheduled_listing'] = {'ok': False, 'error': str(e)[:100]}
            print(f"❌ Scheduled listing: {e}")
        
        # ── 5. Extract match URLs for next test ──
        match_urls = []
        for m in finished[:3]:
            if m.get('href'):
                url = f"https://www.flashscore.com{m['href']}" if m['href'].startswith('/') else m['href']
                match_urls.append(('finished', url, f"{m['home']} vs {m['away']}"))
        for m in scheduled[:2]:
            if m.get('href'):
                url = f"https://www.flashscore.com{m['href']}" if m['href'].startswith('/') else m['href']
                match_urls.append(('scheduled', url, f"{m['home']} vs {m['away']}"))
        
        results['match_urls'] = match_urls
        print(f"\n📋 Collected {len(match_urls)} match URLs for detail extraction testing")
        
        await browser.close()
    
    # Save results
    output_path = "/home/z/my-project/repos/scrapamoja/output/capability_nav.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return results


if __name__ == "__main__":
    asyncio.run(test_navigation_and_listing())
