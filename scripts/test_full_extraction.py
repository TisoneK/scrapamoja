#!/usr/bin/env python3
"""Full end-to-end test for basketball match detail extraction.

Tests all tabs including the new tertiary extraction.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from playwright.async_api import async_playwright
from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.basketball_match_detail_extractor import BasketballMatchDetailExtractor
from src.sites.flashscore.models import PageState
from datetime import datetime, timezone


TEST_MATCH_URL = "https://www.flashscore.com/match/basketball/gigantes-san-francisco-dx0QQfCo/heroes-de-moca-xfeHvvde/?mid=UN9xlnBb"


async def test_full_extraction():
    """Test full extraction on a finished basketball match."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("=" * 60)
            print("Full FlashScore basketball match extraction test")
            print("=" * 60)
            
            print(f"\n1. Navigating to match...")
            await page.goto(TEST_MATCH_URL, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Create extractor
            scraper = FlashscoreScraper.__new__(FlashscoreScraper)
            scraper.page = page
            scraper.selector_engine = None
            
            extractor = BasketballMatchDetailExtractor(scraper)
            
            page_state = PageState(
                match_id="test_match",
                url=page.url,
                tabs_available=[],
                verified=True,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Run full extraction
            print("2. Running full extraction pipeline...")
            start_time = datetime.now(timezone.utc)
            result = await extractor.extract(page_state)
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"   Full extraction took {duration:.1f}s")
            
            if result:
                print(f"\n3. Extraction Results:")
                print(f"   Match ID: {result.match_id}")
                print(f"   Completeness: {result.metadata.completeness_score:.1%}")
                print(f"   Tabs extracted: {result.extraction_metadata.tabs_extracted}")
                print(f"   Tabs failed: {result.extraction_metadata.failed_tabs}")
                print(f"   Duration: {result.extraction_metadata.extraction_duration_ms}ms")
                
                # Basic info
                if result.basic_info:
                    print(f"\n   Basic Info:")
                    print(f"     Home: {result.basic_info.home_team}")
                    print(f"     Away: {result.basic_info.away_team}")
                    print(f"     Score: {result.basic_info.current_score}")
                    print(f"     Status: {result.basic_info.status}")
                
                # Summary
                if result.summary_tab:
                    print(f"\n   Summary tab: OK")
                    print(f"     Overview keys: {list(result.summary_tab.overview.keys())}")
                
                # H2H
                if result.h2h_tab:
                    print(f"\n   H2H tab: OK")
                    print(f"     Previous matches: {len(result.h2h_tab.previous_matches)}")
                    if result.h2h_tab.win_loss_record:
                        print(f"     Win/Loss: {result.h2h_tab.win_loss_record}")
                
                # Odds
                if result.odds_tab:
                    print(f"\n   Odds tab: OK")
                    print(f"     Bookmakers: {len(result.odds_tab.betting_odds)}")
                
                # Stats
                if result.stats_tab:
                    print(f"\n   Stats tab: OK")
                    sections = len(result.stats_tab.detailed_statistics)
                    print(f"     Sections: {sections}")
                else:
                    print(f"\n   Stats tab: MISSING")
                
                # Tertiary
                if result.tertiary_tabs:
                    print(f"\n   Tertiary tab: OK")
                    if result.tertiary_tabs.quarter_scores:
                        print(f"     Quarter scores: {json.dumps(result.tertiary_tabs.quarter_scores)}")
                    periods = sum(1 for f in ['match', 'q1', 'q2', 'q3', 'q4'] 
                                 if getattr(result.tertiary_tabs, f, None))
                    print(f"     Period stats: {periods}/5")
                else:
                    print(f"\n   Tertiary tab: MISSING")
                
                # Overall
                print(f"\n" + "=" * 60)
                total_tabs = len(result.extraction_metadata.tabs_extracted)
                passed = total_tabs >= 4 and result.tertiary_tabs and (
                    result.tertiary_tabs.match is not None or 
                    result.tertiary_tabs.q1 is not None
                )
                print(f"OVERALL: {'PASS' if passed else 'FAIL'}")
                print(f"  Tabs: {total_tabs}/5 extracted")
                print(f"  Completeness: {result.metadata.completeness_score:.1%}")
                print(f"  Duration: {duration:.1f}s")
                print("=" * 60)
                
                return passed
            else:
                print("   ERROR: Full extraction returned None!")
                return False
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_full_extraction())
    sys.exit(0 if result else 1)
