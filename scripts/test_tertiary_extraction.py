#!/usr/bin/env python3
"""Quick end-to-end test for basketball match detail tertiary tab extraction.

Uses a known finished basketball match with Stats sub-tab.
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


# Known finished match with Stats sub-tab (Dominican Republic LNB)
TEST_MATCH_URL = "https://www.flashscore.com/match/basketball/gigantes-san-francisco-dx0QQfCo/heroes-de-moca-xfeHvvde/?mid=UN9xlnBb"


async def test_tertiary_extraction():
    """Test the tertiary tab extraction on a finished basketball match."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("=" * 60)
            print("FlashScore basketball tertiary extraction test")
            print("=" * 60)
            
            # Navigate to known finished match
            print(f"\n1. Navigating to known finished match...")
            await page.goto(TEST_MATCH_URL, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Verify we have the Stats sub-tab
            has_stats_tab = await page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button[data-testid="wcl-tab"]');
                    return Array.from(btns).some(b => b.textContent.trim() === 'Stats');
                }
            """)
            print(f"   Stats tab available: {has_stats_tab}")
            if not has_stats_tab:
                print("   ERROR: This match doesn't have a Stats sub-tab!")
                return False
            
            # Create scraper mock
            print("2. Creating extractor...")
            scraper = FlashscoreScraper.__new__(FlashscoreScraper)
            scraper.page = page
            scraper.selector_engine = None
            
            extractor = BasketballMatchDetailExtractor(scraper)
            
            # Create page state
            page_state = PageState(
                match_id="test_match",
                url=page.url,
                tabs_available=[],
                verified=True,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Extract basic info
            print("\n3. Extracting basic info...")
            basic_info = await extractor._extract_basic_info(page_state)
            if basic_info:
                print(f"   Home: {basic_info.home_team}")
                print(f"   Away: {basic_info.away_team}")
                print(f"   Score: {basic_info.current_score}")
                print(f"   Status: {basic_info.status}")
            
            # Test tertiary extraction
            print("\n4. Testing tertiary tab extraction (quarter-by-quarter stats)...")
            start_time = datetime.now(timezone.utc)
            tertiary_data = await extractor._extract_tertiary_tabs(page_state)
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"   Extraction took {duration:.1f}s")
            
            if tertiary_data:
                print(f"\n   Quarter scores: {json.dumps(tertiary_data.quarter_scores, indent=4) if tertiary_data.quarter_scores else 'None'}")
                
                for period_name in ['match', 'q1', 'q2', 'q3', 'q4']:
                    period_data = getattr(tertiary_data, period_name, None)
                    if period_data:
                        sections = len(period_data)
                        total_stats = sum(len(v) for v in period_data.values() if isinstance(v, dict))
                        print(f"   {period_name.upper()} stats: {sections} sections, {total_stats} total stats")
                    else:
                        print(f"   {period_name.upper()} stats: None")
                
                # Show sample match stats
                if tertiary_data.match:
                    print(f"\n   Match stats categories: {list(tertiary_data.match.keys())}")
                    for section, stats in list(tertiary_data.match.items())[:2]:
                        sample = {k: v for k, v in list(stats.items())[:3]}
                        print(f"     {section}: {sample}")
                
                # Show sample Q1 stats
                if tertiary_data.q1:
                    print(f"\n   Q1 stats categories: {list(tertiary_data.q1.keys())}")
                    for section, stats in list(tertiary_data.q1.items())[:2]:
                        sample = {k: v for k, v in list(stats.items())[:3]}
                        print(f"     {section}: {sample}")
            else:
                print("   ERROR: No tertiary data extracted!")
            
            # Summary
            print("\n" + "=" * 60)
            has_quarter_scores = tertiary_data and tertiary_data.quarter_scores is not None
            has_match_stats = tertiary_data and tertiary_data.match is not None
            has_q1_stats = tertiary_data and tertiary_data.q1 is not None
            
            total_periods = sum(1 for field in ['match', 'q1', 'q2', 'q3', 'q4'] 
                              if getattr(tertiary_data, field, None) is not None) if tertiary_data else 0
            
            print(f"RESULTS:")
            print(f"  Quarter scores: {'OK' if has_quarter_scores else 'MISSING'}")
            print(f"  Match stats: {'OK' if has_match_stats else 'MISSING'}")
            print(f"  Q1 stats: {'OK' if has_q1_stats else 'MISSING'}")
            print(f"  Period stats extracted: {total_periods}/5")
            print(f"  Tertiary extraction: {'PASS' if total_periods >= 3 else 'FAIL'}")
            print(f"  Total duration: {duration:.1f}s")
            print("=" * 60)
            
            return total_periods >= 3
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_tertiary_extraction())
    sys.exit(0 if result else 1)
