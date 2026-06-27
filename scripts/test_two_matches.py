#!/usr/bin/env python3
"""Fast multi-match test — just 2 matches, one finished, one scheduled."""
import asyncio
import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from playwright.async_api import async_playwright
from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.basketball_match_detail_extractor import BasketballMatchDetailExtractor
from src.sites.flashscore.models import PageState
from datetime import datetime, timezone


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        )
        page = await ctx.new_page()
        
        # Step 1: Get 1 finished + 1 scheduled match URL from listing
        print("Finding matches...")
        await page.goto("https://www.flashscore.com/basketball/?type=finished", wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(3000)
        
        finished_url = await page.evaluate("""
            () => {
                const row = document.querySelector('[class*="event__match"] a[href*="/match/"]');
                return row ? row.getAttribute('href') : null;
            }
        """)
        
        await page.goto("https://www.flashscore.com/basketball/?type=scheduled", wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(3000)
        
        scheduled_url = await page.evaluate("""
            () => {
                const row = document.querySelector('[class*="event__match"] a[href*="/match/"]');
                return row ? row.getAttribute('href') : null;
            }
        """)
        
        print(f"Finished URL: {finished_url}")
        print(f"Scheduled URL: {scheduled_url}")
        
        # Step 2: Test each match
        test_urls = []
        if finished_url:
            full = f"https://www.flashscore.com{finished_url}" if finished_url.startswith('/') else finished_url
            test_urls.append(('finished', full))
        if scheduled_url:
            full = f"https://www.flashscore.com{scheduled_url}" if scheduled_url.startswith('/') else scheduled_url
            test_urls.append(('scheduled', full))
        
        for status, url in test_urls:
            t0 = time.time()
            print(f"\n{'='*50}")
            print(f"Testing {status}: {url[:70]}")
            print(f"{'='*50}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(3000)
            
            scraper = FlashscoreScraper.__new__(FlashscoreScraper)
            scraper.page = page
            scraper.selector_engine = None
            
            extractor = BasketballMatchDetailExtractor(scraper)
            page_state = PageState(
                match_id=f"test_{status}",
                url=page.url,
                tabs_available=[],
                verified=True,
                timestamp=datetime.now(timezone.utc)
            )
            
            result = await extractor.extract(page_state)
            duration = time.time() - t0
            
            if result:
                print(f"  Completeness: {result.metadata.completeness_score:.0%}")
                print(f"  Tabs: {result.extraction_metadata.tabs_extracted}")
                print(f"  Failed: {result.extraction_metadata.failed_tabs}")
                print(f"  Duration: {duration:.1f}s")
                print(f"  Home: {result.basic_info.home_team}")
                print(f"  Away: {result.basic_info.away_team}")
                print(f"  Score: {result.basic_info.current_score}")
                print(f"  Competition: {result.basic_info.competition}")
                
                if result.summary_tab:
                    print(f"  Summary keys: {list(result.summary_tab.overview.keys())}")
                    print(f"  Quarter scores in summary: {'quarter_scores' in result.summary_tab.overview}")
                
                if result.h2h_tab:
                    print(f"  H2H: {len(result.h2h_tab.previous_matches)} matches")
                    print(f"  Win/Loss: {result.h2h_tab.win_loss_record}")
                
                if result.odds_tab:
                    print(f"  Odds: {len(result.odds_tab.betting_odds)} bookmakers")
                    for name, vals in list(result.odds_tab.betting_odds.items())[:3]:
                        print(f"    {name}: {vals}")
                
                if result.stats_tab:
                    sections = result.stats_tab.detailed_statistics
                    print(f"  Stats: {len(sections)} sections")
                    for sec, items in sections.items():
                        print(f"    {sec}: {len(items)} stats")
                
                if result.tertiary_tabs:
                    qs = result.tertiary_tabs.quarter_scores
                    periods = sum(1 for f in ['match','q1','q2','q3','q4']
                                   if getattr(result.tertiary_tabs, f, None))
                    print(f"  Tertiary: quarter_scores={bool(qs)}, period_stats={periods}/5")
                    if qs:
                        print(f"    Home Q1-Q4: {qs.get('home', {})}")
                        print(f"    Away Q1-Q4: {qs.get('away', {})}")
                
                if result.extraction_metadata.failed_tabs:
                    print(f"  ⚠️ Failed tabs: {result.extraction_metadata.failed_tabs}")
            else:
                print(f"  ❌ Extraction returned None ({duration:.1f}s)")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
