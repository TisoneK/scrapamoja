#!/usr/bin/env python3
"""Data quality diagnostic — dumps all extracted data for visual inspection."""
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


def safe_dump(obj, max_depth=5):
    """Recursively convert dataclass objects to dicts for JSON serialization."""
    if max_depth <= 0:
        return str(obj)
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: safe_dump(v, max_depth - 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [safe_dump(v, max_depth - 1) for v in obj]
    if hasattr(obj, '__dataclass_fields__'):
        return {k: safe_dump(getattr(obj, k), max_depth - 1) for k in obj.__dataclass_fields__}
    return str(obj)


async def test_data_quality():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("Navigating to match...")
            await page.goto(TEST_MATCH_URL, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
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
            
            result = await extractor.extract(page_state)
            
            if not result:
                print("ERROR: Extraction returned None!")
                return
            
            data = safe_dump(result)
            
            # Print each section with formatting
            print("\n" + "=" * 80)
            print("BASIC INFO")
            print("=" * 80)
            bi = data.get('basic_info', {})
            for k, v in bi.items():
                print(f"  {k}: {v}")
            
            print("\n" + "=" * 80)
            print("SUMMARY TAB")
            print("=" * 80)
            summary = data.get('summary_tab', {})
            overview = summary.get('overview', {})
            print(f"  Overview ({len(overview)} keys):")
            for k, v in overview.items():
                print(f"    {k}: {v}")
            print(f"  Team statistics ({len(summary.get('team_statistics', {}))} keys)")
            print(f"  Match events: {len(summary.get('match_events', []))} events")
            for evt in summary.get('match_events', [])[:5]:
                print(f"    - {evt}")
            
            print("\n" + "=" * 80)
            print("H2H TAB")
            print("=" * 80)
            h2h = data.get('h2h_tab', {})
            prev = h2h.get('previous_matches', [])
            print(f"  Previous matches: {len(prev)}")
            if prev:
                print("  First 3 matches:")
                for m in prev[:3]:
                    print(f"    {m.get('home_team', '?')} {m.get('home_score', '?')} - {m.get('away_score', '?')} {m.get('away_team', '?')} ({m.get('date', 'no date')})")
            print(f"  Win/Loss: {h2h.get('win_loss_record', {})}")
            
            print("\n" + "=" * 80)
            print("ODDS TAB")
            print("=" * 80)
            odds = data.get('odds_tab', {})
            betting = odds.get('betting_odds', {})
            print(f"  Bookmakers: {len(betting)}")
            for name, vals in list(betting.items())[:5]:
                print(f"    {name}: {vals}")
            
            print("\n" + "=" * 80)
            print("STATS TAB")
            print("=" * 80)
            stats = data.get('stats_tab', {})
            det = stats.get('detailed_statistics', {})
            print(f"  Sections: {len(det)}")
            for section, stat_items in det.items():
                print(f"    [{section}] ({len(stat_items)} stats)")
                for stat_name, vals in list(stat_items.items())[:3]:
                    print(f"      {stat_name}: home={vals.get('home')}, away={vals.get('away')}")
                if len(stat_items) > 3:
                    print(f"      ... and {len(stat_items) - 3} more")
            
            print("\n" + "=" * 80)
            print("TERTIARY TAB (Quarter-by-Quarter)")
            print("=" * 80)
            tertiary = data.get('tertiary_tabs', {})
            qs = tertiary.get('quarter_scores', {})
            if qs:
                print(f"  Quarter Scores:")
                home = qs.get('home', {})
                away = qs.get('away', {})
                print(f"    Home: {home}")
                print(f"    Away: {away}")
            else:
                print("  Quarter Scores: NONE")
            
            for period_key, label in [('match', 'Full Match'), ('q1', '1st Quarter'), ('q2', '2nd Quarter'), ('q3', '3rd Quarter'), ('q4', '4th Quarter')]:
                period = tertiary.get(period_key)
                if period:
                    print(f"\n  [{label}] ({len(period)} sections)")
                    for section, stat_items in period.items():
                        print(f"    {section}: {len(stat_items)} stats")
                else:
                    print(f"\n  [{label}]: NONE")
            
            # Save full JSON for detailed inspection
            output_path = "/home/z/my-project/repos/scrapamoja/output/extraction_dump.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"\n\nFull data dump saved to: {output_path}")
            
            # Quality checks
            print("\n" + "=" * 80)
            print("QUALITY CHECKS")
            print("=" * 80)
            issues = []
            
            # Check 1: Summary tab should have more than just date/status
            if len(overview) <= 2:
                issues.append(f"Summary overview sparse: only {list(overview.keys())}")
            
            # Check 2: Team names should not contain form strings
            home = bi.get('home_team', '')
            away = bi.get('away_team', '')
            import re
            if re.search(r'[WLD]\d+', home):
                issues.append(f"Home team has form string: '{home}'")
            if re.search(r'[WLD]\d+', away):
                issues.append(f"Away team has form string: '{away}'")
            
            # Check 3: H2H scores should be numeric
            for m in prev:
                hs = m.get('home_score', '')
                as_ = m.get('away_score', '')
                if hs and not re.match(r'^\d+', str(hs)):
                    issues.append(f"H2H home_score not numeric: '{hs}' in {m}")
                if as_ and not re.match(r'^\d+', str(as_)):
                    issues.append(f"H2H away_score not numeric: '{as_}' in {m}")
            
            # Check 4: Quarter scores should have Q1-Q4
            if qs:
                for side in ['home', 'away']:
                    for q in ['Q1', 'Q2', 'Q3', 'Q4']:
                        if q not in qs.get(side, {}):
                            issues.append(f"Missing {side} {q} in quarter_scores")
                    if 'total' not in qs.get(side, {}):
                        issues.append(f"Missing {side} total in quarter_scores")
            
            # Check 5: All 5 period stats should be present
            for key in ['match', 'q1', 'q2', 'q3', 'q4']:
                if not tertiary.get(key):
                    issues.append(f"Missing tertiary period: {key}")
            
            if issues:
                print(f"  Found {len(issues)} issues:")
                for i, issue in enumerate(issues, 1):
                    print(f"    {i}. {issue}")
            else:
                print("  All quality checks passed!")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_data_quality())
