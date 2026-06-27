"""
Basketball match detail extractor implementing primary tab extraction.

Extends the base MatchDetailExtractor with basketball-specific implementations
for primary tabs: SUMMARY, H2H, ODDS, STATS.

Interactive operations (tab clicks, navigation, active tab detection) use
Playwright direct CSS queries because the YAML selector engine has an
internal retry loop that swallows CancelledError, making asyncio.wait_for
timeouts ineffective. Non-interactive reads fall back to the YAML selector
engine with 8-second timeout protection.
"""

import asyncio
from typing import Dict, Any, Optional, List
from playwright.async_api import ElementHandle, Page

from src.sites.flashscore.scraper import FlashscoreScraper
from src.sites.flashscore.extractors.match_detail_extractor import MatchDetailExtractor
from src.sites.flashscore.extractors.primary_tab_extractor import PrimaryTabExtractor
from src.sites.flashscore.models import (
    PageState, SummaryData, H2HData, OddsData, StatsData, 
    BasicMatchInfo, TertiaryData
)
from datetime import datetime


class BasketballMatchDetailExtractor(MatchDetailExtractor):
    """Basketball-specific match detail extractor — Playwright-direct for interactive ops, YAML fallback for reads."""
    
    def __init__(self, scraper: FlashscoreScraper):
        super().__init__(scraper)
        self.primary_extractor = BasketballPrimaryTabExtractor(scraper)
    
    # YAML selector engine methods inherited from SelectorEngineMixin via MatchDetailExtractor
    # (_resolve_element, _resolve_elements, _resolve_text)
    
    async def _extract_basic_info(self, page_state: PageState) -> Optional[BasicMatchInfo]:
        """Extract basic match info — Playwright direct only.
        
        YAML selector engine NOT used because its internal retry loop
        catches CancelledError, making timeouts ineffective.
        """
        try:
            home_team = "Unknown"
            away_team = "Unknown"
            current_score = None
            match_time = "Unknown"
            status = "Unknown"
            competition = None
            
            # Playwright direct queries — reliable, no infinite loops
            
            # Home team
            for sel in ['.event__participant--home', '.participant__home',
                        '.duelParticipant__home .participant__playerName',
                        '[data-testid="home-team"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = self._clean_team_name((await el.text_content()).strip())
                        if text:
                            home_team = text
                            break
                except Exception:
                    continue
            
            # Away team
            for sel in ['.event__participant--away', '.participant__away',
                        '.duelParticipant__away .participant__playerName',
                        '[data-testid="away-team"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = self._clean_team_name((await el.text_content()).strip())
                        if text:
                            away_team = text
                            break
                except Exception:
                    continue
            
            # Scores
            for sel in ['.event__score', '.detailScore__matchDetail']:
                try:
                    score_els = await self.page.query_selector_all(sel)
                    if len(score_els) >= 2:
                        home = (await score_els[0].text_content()).strip()
                        away = (await score_els[1].text_content()).strip()
                        current_score = f"{home}-{away}"
                        break
                except Exception:
                    continue
            
            # Match time
            for sel in ['.duelParticipant__startTime', '.event__time',
                        '[data-testid="match-time"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            match_time = text
                            break
                except Exception:
                    continue
            
            # Status
            for sel in ['.detailScore__status', '[data-testid="match-status"]',
                        '.event__status']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            status = text
                            break
                except Exception:
                    continue
            
            # Competition / league name
            for sel in ['.tournamentHeader__content', '.event__tournament',
                        '[data-testid="tournament-name"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            competition = text
                            break
                except Exception:
                    continue
            
            # JavaScript fallback for any missing fields
            try:
                js_result = await self.page.evaluate("""
                    () => {
                        const data = {};
                        // Try to find team names from the page
                        const participants = document.querySelectorAll('[class*="participant"], [class*="team"]');
                        participants.forEach(p => {
                            const text = p.textContent.trim();
                            if (text && text.length < 50 && text.length > 1) {
                                const cls = p.className || '';
                                if (cls.includes('home') && !data.home_team) data.home_team = text;
                                if (cls.includes('away') && !data.away_team) data.away_team = text;
                            }
                        });
                        // Try tournament header
                        const tournament = document.querySelector('[class*="tournament"], [class*="header"]');
                        if (tournament && tournament.textContent.trim().length < 100) {
                            data.competition = tournament.textContent.trim();
                        }
                        return data;
                    }
                """)
                if js_result:
                    if home_team == "Unknown" and js_result.get('home_team'):
                        home_team = js_result['home_team']
                    if away_team == "Unknown" and js_result.get('away_team'):
                        away_team = js_result['away_team']
                    if not competition and js_result.get('competition'):
                        competition = js_result['competition']
            except Exception:
                pass
            
            return BasicMatchInfo(
                home_team=home_team,
                away_team=away_team,
                current_score=current_score,
                match_time=match_time,
                status=status,
                competition=competition,
                league=competition,
            )
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {e}")
            return None
    
    async def _extract_summary_tab(self, page_state: PageState) -> Optional[SummaryData]:
        """Extract data from SUMMARY tab."""
        try:
            summary_data = await self.primary_extractor.extract_tab_data('summary')
            if not summary_data:
                return None
            return SummaryData(
                overview=summary_data.get('overview', {}),
                team_statistics=summary_data.get('team_statistics', {}),
                match_events=summary_data.get('match_events', [])
            )
        except Exception as e:
            self.logger.error(f"Error extracting SUMMARY tab: {e}")
            return None
    
    async def _extract_h2h_tab(self, page_state: PageState) -> Optional[H2HData]:
        """Extract data from H2H tab."""
        try:
            h2h_data = await self.primary_extractor.extract_tab_data('h2h')
            if not h2h_data:
                return None
            return H2HData(
                previous_matches=h2h_data.get('previous_matches', []),
                historical_statistics=h2h_data.get('historical_statistics', {}),
                win_loss_record=h2h_data.get('win_loss_record', {})
            )
        except Exception as e:
            self.logger.error(f"Error extracting H2H tab: {e}")
            return None
    
    async def _extract_odds_tab(self, page_state: PageState) -> Optional[OddsData]:
        """Extract data from ODDS tab."""
        try:
            odds_data = await self.primary_extractor.extract_tab_data('odds')
            if not odds_data:
                return None
            return OddsData(
                betting_odds=odds_data.get('betting_odds', {}),
                odds_history=odds_data.get('odds_history', []),
                bookmaker_data=odds_data.get('bookmaker_data', {})
            )
        except Exception as e:
            self.logger.error(f"Error extracting ODDS tab: {e}")
            return None
    
    async def _extract_stats_tab(self, page_state: PageState) -> Optional[StatsData]:
        """Extract data from STATS tab."""
        try:
            stats_data = await self.primary_extractor.extract_tab_data('stats')
            if not stats_data:
                return None
            return StatsData(
                detailed_statistics=stats_data.get('detailed_statistics', {}),
                player_performance=stats_data.get('player_performance', []),
                team_performance=stats_data.get('team_performance', {})
            )
        except Exception as e:
            self.logger.error(f"Error extracting STATS tab: {e}")
            return None
    
    async def _extract_tertiary_tabs(self, page_state: PageState) -> Optional[TertiaryData]:
        """Extract data from tertiary tabs (quarter-by-quarter stats)."""
        try:
            ft_stats = None
            q1_stats = None
            inc_ot_stats = None
            
            if await self.primary_extractor.navigate_to_tab('stats'):
                await self.page.wait_for_timeout(2000)
                ft_stats = await self._extract_stats_rows()
                q1_stats = await self._extract_period_stats('1st Quarter')
                await self._click_period_filter('Match')
                await self.page.wait_for_timeout(1000)
                inc_ot_stats = ft_stats
            
            return TertiaryData(inc_ot=inc_ot_stats, ft=ft_stats, q1=q1_stats)
        except Exception as e:
            self.logger.error(f"Error extracting tertiary tabs: {e}")
            return TertiaryData(inc_ot=None, ft=None, q1=None)
    
    async def _extract_stats_rows(self) -> Optional[Dict[str, Any]]:
        """Extract stats from currently visible content — Playwright direct only.
        
        YAML selector engine NOT used (CancelledError-swallowing infinite loop).
        """
        try:
            statistics = {}
            current_section = "General"
            
            # Playwright direct — find stat rows and headers
            stat_rows = []
            stat_headers = []
            for sel in ['.stat__row', '[class*="statRow"]', '[class*="stats__row"]', '[data-testid="stat-row"]']:
                try:
                    found = await self.page.query_selector_all(sel)
                    stat_rows.extend(found)
                except Exception:
                    continue
            for sel in ['.stat__header', '[class*="sectionHeader"]', '[class*="statHeader"]', '[data-testid="stat-header"]']:
                try:
                    found = await self.page.query_selector_all(sel)
                    stat_headers.extend(found)
                except Exception:
                    continue
            
            if stat_rows or stat_headers:
                all_elements = stat_rows + stat_headers
                for element in all_elements:
                    try:
                        cls = await element.get_attribute('class') or ''
                        if 'header' in cls.lower() or 'section' in cls.lower():
                            text = (await element.text_content()).strip()
                            if text:
                                current_section = text
                                if current_section not in statistics:
                                    statistics[current_section] = {}
                            continue
                        
                        cells = await element.query_selector_all('span, div, td')
                        if len(cells) >= 3:
                            texts = [(await c.text_content()).strip() for c in cells]
                            texts = [t for t in texts if t]
                            if len(texts) >= 3:
                                home_val = texts[0]
                                name = texts[len(texts) // 2]
                                away_val = texts[-1]
                                if current_section not in statistics:
                                    statistics[current_section] = {}
                                statistics[current_section][name] = {'home': home_val, 'away': away_val}
                    except Exception:
                        continue
            
            # JavaScript fallback — extract stats using DOM traversal
            if not statistics:
                try:
                    js_stats = await self.page.evaluate("""
                        () => {
                            const stats = {};
                            let section = 'General';
                            // Look for stat comparison rows
                            const rows = document.querySelectorAll('[class*="stat"], [class*="comparison"]');
                            rows.forEach(row => {
                                const cls = row.className || '';
                                if (cls.includes('header') || cls.includes('section')) {
                                    section = row.textContent.trim();
                                    if (!(section in stats)) stats[section] = {};
                                    return;
                                }
                                const cells = row.querySelectorAll('span, div, td');
                                const texts = Array.from(cells).map(c => c.textContent.trim()).filter(t => t);
                                if (texts.length >= 3) {
                                    stats[section][texts[Math.floor(texts.length/2)]] = {
                                        home: texts[0], away: texts[texts.length-1]
                                    };
                                }
                            });
                            return Object.keys(stats).length > 0 ? stats : null;
                        }
                    """)
                    if js_stats:
                        statistics = js_stats
                except Exception:
                    pass
            
            return statistics if statistics else None
        except Exception as e:
            self.logger.error(f"Error extracting stats rows: {e}")
            return None
    
    async def _extract_period_stats(self, period_name: str) -> Optional[Dict[str, Any]]:
        """Click a period filter and extract stats for that period."""
        try:
            if await self._click_period_filter(period_name):
                await self.page.wait_for_timeout(2000)
                return await self._extract_stats_rows()
            return None
        except Exception as e:
            self.logger.error(f"Error extracting period stats for {period_name}: {e}")
            return None
    
    async def _click_period_filter(self, period_name: str) -> bool:
        """Click a period filter tab — Playwright direct + JavaScript only.
        
        YAML selector engine NOT used (CancelledError-swallowing infinite loop).
        """
        # Strategy 1: Playwright direct — find all tab-like buttons
        for sel in ['button[data-testid="wcl-tab"]', 'button[class*="tab"]', '[role="tab"]']:
            try:
                buttons = await self.page.query_selector_all(sel)
                for btn in buttons:
                    text = (await btn.text_content()).strip()
                    if text == period_name:
                        await btn.click()
                        await self.page.wait_for_timeout(1500)
                        self.logger.info(f"Clicked period filter: {period_name}")
                        return True
            except Exception:
                continue
        
        # Strategy 2: JavaScript text search
        try:
            safe_name = period_name.replace("'", "\\'")
            clicked = await self.page.evaluate(f"""
                () => {{
                    const buttons = document.querySelectorAll('button, [role="tab"]');
                    for (const btn of buttons) {{
                        if (btn.textContent.trim() === '{safe_name}') {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if clicked:
                await self.page.wait_for_timeout(1500)
                self.logger.info(f"Clicked period filter via JS: {period_name}")
                return True
        except Exception:
            pass
        
        self.logger.debug(f"Period filter not found: {period_name}")
        return False


class BasketballPrimaryTabExtractor(PrimaryTabExtractor):
    """Basketball-specific primary tab extractor.
    
    Interactive DOM operations (tab clicks, navigation) use Playwright direct
    CSS queries. Non-interactive reads may fall back to the YAML selector engine
    with 8-second timeout protection.
    """
    
    def __init__(self, scraper: FlashscoreScraper):
        super().__init__(scraper)
        # _selector_engine is set by PrimaryTabExtractor parent
    
    # ─────────────────────────────────────────────────────────
    # SUMMARY TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_summary_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from SUMMARY tab — Playwright direct first, YAML engine fallback."""
        try:
            overview = {}
            team_statistics = {}
            match_events = []
            
            # ── Playwright direct queries (fast, reliable) ──
            
            # Competition name
            for sel in ['.tournamentHeader__content', '[data-testid="tournament-name"]', '.event__tournament']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text and len(text) < 100:
                            overview['competition'] = text
                            break
                except Exception:
                    continue
            
            # Match start time
            for sel in ['.duelParticipant__startTime', '.event__time', '[data-testid="match-time"]']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            overview['date'] = text
                            break
                except Exception:
                    continue
            
            # Match status
            for sel in ['.detailScore__status', '[data-testid="match-status"]', '.event__status']:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        text = (await el.text_content()).strip()
                        if text:
                            overview['status'] = text
                            break
                except Exception:
                    continue
            
            # Quarter scores — look for score cells in the summary table
            try:
                # FlashScore summary often shows quarter-by-quarter scores in a specific table
                score_sections = await self.page.query_selector_all('.detailScore__matchDetail, .matchInfo, [data-testid="score-breakdown"]')
                for section in score_sections:
                    text = (await section.text_content()).strip()
                    if text and ('Q1' in text or 'Quarter' in text or '1st' in text):
                        # Parse quarter scores from text
                        match_events.append({'type': 'quarter_scores_text', 'content': text})
                        break
            except Exception:
                pass
            
            return {
                'overview': overview,
                'team_statistics': team_statistics,
                'match_events': match_events
            }
        except Exception as e:
            self.logger.error(f"Error extracting SUMMARY data: {e}")
            return None
    
    # ─────────────────────────────────────────────────────────
    # H2H TAB
    # ─────────────────────────────────────────────────────────
    
    @staticmethod
    def _clean_team_name(raw: str) -> str:
        """Clean a team name by removing form strings, extra whitespace, and common FlashScore artifacts.
        
        FlashScore sometimes appends form indicators (W1, L2, D3 etc.),
        ranking numbers, or child-element text that shouldn't be part of
        the team name.
        """
        if not raw:
            return raw
        import re
        # Remove trailing form strings like "W1", "L2", "D3", "W 1", "L 2"
        cleaned = re.sub(r'\s+[WLD]\s*\d+\s*$', '', raw)
        # Remove trailing parenthetical form like "(W1)"
        cleaned = re.sub(r'\s*\([WLD]\d+\)\s*$', '', cleaned)
        # Remove leading/trailing whitespace and newlines
        cleaned = ' '.join(cleaned.split())
        # Truncate if suspiciously long (likely picked up container text)
        if len(cleaned) > 60:
            cleaned = cleaned[:60].rsplit(' ', 1)[0]
        return cleaned

    @staticmethod
    def _is_valid_score(text: str) -> bool:
        """Check if a string looks like a valid sports score (digits, possibly with OT suffix)."""
        if not text:
            return False
        import re
        # Scores are digits, optionally followed by OT indicator like " (OT)" or "aet"
        return bool(re.match(r'^\d+(?:\s*\(.*\))?$', text.strip()))

    async def _extract_h2h_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from H2H tab — Playwright direct first, YAML engine fallback."""
        try:
            previous_matches = []
            historical_statistics = {}
            win_loss_record = {}
            
            # ── Playwright direct queries ──
            # H2H tab shows previous matches between the two teams.
            # FlashScore uses rows inside a container for each H2H match.
            try:
                # Look for H2H match rows using common FlashScore classes
                h2h_containers = await self.page.query_selector_all(
                    '.h2h__row, .h2h-match, [data-testid="h2h-match"]'
                )
                if not h2h_containers:
                    # Try broader selectors for the H2H content area
                    h2h_section = await self.page.query_selector('.h2h, [data-testid="h2h-content"]')
                    if h2h_section:
                        h2h_containers = await h2h_section.query_selector_all('a, .row')
                
                for row in h2h_containers:
                    match_data = {}
                    try:
                        # Try to extract basic match info from each row
                        text = (await row.text_content()).strip()
                        if not text or len(text) < 5:
                            continue
                        
                        # Get the link href if it's an anchor
                        href = await row.get_attribute('href')
                        if href:
                            match_data['match_url'] = href
                        
                        # Date — use [data-testid="wcl-stageTime"] (confirmed on live site)
                        # Also try .h2hH2h__date as fallback
                        date_el = await row.query_selector(
                            '[data-testid="wcl-stageTime"], .h2hH2h__date, .h2h__date'
                        )
                        if date_el:
                            t = (await date_el.text_content()).strip()
                            if t:
                                match_data['date'] = t
                        
                        # Home/Away participants — use specific H2H participant selectors
                        # Live site uses .h2h__homeParticipant and .h2h__awayParticipant
                        home_el = await row.query_selector(
                            '.h2h__homeParticipant, .event__participant--home, .participant__home'
                        )
                        away_el = await row.query_selector(
                            '.h2h__awayParticipant, .event__participant--away, .participant__away'
                        )
                        if home_el:
                            t = self._clean_team_name((await home_el.text_content()).strip())
                            if t:
                                match_data['home_team'] = t
                        if away_el:
                            t = self._clean_team_name((await away_el.text_content()).strip())
                            if t:
                                match_data['away_team'] = t
                        
                        # Scores — use [class*="tableScore"] spans (confirmed on live site)
                        # .event__score does NOT exist in H2H rows
                        score_els = await row.query_selector_all('span[class*="tableScore"]')
                        # Filter out empty score spans
                        valid_scores = []
                        for s_el in score_els:
                            s_text = (await s_el.text_content()).strip()
                            if s_text and self._is_valid_score(s_text):
                                valid_scores.append(s_text)
                        
                        if len(valid_scores) >= 2:
                            match_data['home_score'] = valid_scores[0]
                            match_data['away_score'] = valid_scores[1]
                        else:
                            # Fallback: try .h2h__result element which has combined score like "10691"
                            result_el = await row.query_selector('.h2h__result')
                            if result_el:
                                result_text = (await result_el.text_content()).strip()
                                if result_text and len(result_text) >= 4:
                                    # Split combined score: "10691" → "106", "91"
                                    # Try to find a reasonable split point
                                    import re
                                    # Try 3-digit + 2-digit or 2-digit + 2-digit or 3-digit + 3-digit
                                    for split_at in [3, 2, 4]:
                                        if len(result_text) > split_at:
                                            h = result_text[:split_at]
                                            a = result_text[split_at:]
                                            if h.isdigit() and a.isdigit() and int(h) < 300 and int(a) < 300:
                                                match_data['home_score'] = h
                                                match_data['away_score'] = a
                                                break
                        
                        if 'home_team' in match_data or 'away_team' in match_data:
                            previous_matches.append(match_data)
                    except Exception:
                        continue
                    
            except Exception as e:
                self.logger.debug(f"Playwright direct H2H extraction failed: {e}")
            
            self.logger.info(f"Extracted {len(previous_matches)} H2H matches")
            
            # Calculate win/loss record from actual scores
            if previous_matches:
                home_wins = 0
                away_wins = 0
                draws = 0
                for m in previous_matches:
                    hs = m.get('home_score')
                    as_ = m.get('away_score')
                    if hs and as_:
                        try:
                            # Extract leading digits only (ignore OT suffixes)
                            import re
                            h = int(re.match(r'(\d+)', hs).group(1))
                            a = int(re.match(r'(\d+)', as_).group(1))
                            if h > a:
                                home_wins += 1
                            elif a > h:
                                away_wins += 1
                            else:
                                draws += 1
                        except (ValueError, AttributeError):
                            pass
                win_loss_record = {
                    'home_wins': home_wins,
                    'away_wins': away_wins,
                    'draws': draws,
                    'total': len(previous_matches)
                }
            
            return {
                'previous_matches': previous_matches,
                'historical_statistics': historical_statistics,
                'win_loss_record': win_loss_record
            }
        except Exception as e:
            self.logger.error(f"Error extracting H2H data: {e}")
            return None
    
    # ─────────────────────────────────────────────────────────
    # ODDS TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_odds_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from ODDS tab — Playwright direct first, YAML engine fallback."""
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            # ── Playwright direct queries ──
            try:
                # FlashScore odds tables use rows with bookmaker data
                odds_rows = await self.page.query_selector_all(
                    '.oddsRow, [class*="odds__row"], [class*="oddsRow"], [data-testid="odds-row"]'
                )
                if not odds_rows:
                    # Try the main odds container and find rows inside
                    odds_table = await self.page.query_selector(
                        '.oddsTable, [class*="odds__table"], [class*="oddsComparison"], [data-testid="odds-table"]'
                    )
                    if odds_table:
                        odds_rows = await odds_table.query_selector_all('tr, [class*="row"]')
                
                self.logger.info(f"Found {len(odds_rows)} odds rows via Playwright direct")
                
                for row in odds_rows:
                    try:
                        # Try to get bookmaker name
                        bookmaker_name = ""
                        name_el = await row.query_selector(
                            'a[title], [class*="bookmaker"] a, [class*="logo"] img'
                        )
                        if name_el:
                            bookmaker_name = await name_el.get_attribute('title') or ""
                            if not bookmaker_name:
                                bookmaker_name = await name_el.get_attribute('alt') or ""
                            if not bookmaker_name:
                                bookmaker_name = (await name_el.text_content()).strip()
                        
                        if not bookmaker_name:
                            continue
                        
                        # Extract odds cells
                        cells = await row.query_selector_all(
                            'td[class*="odds"], [class*="oddsCell"], [class*="cell"]'
                        )
                        odds_values = []
                        for cell in cells:
                            text = (await cell.text_content()).strip()
                            if text:
                                odds_values.append(text)
                        
                        if odds_values:
                            odds_entry = {'market_type': 'moneyline'}
                            if len(odds_values) >= 2:
                                odds_entry['home'] = odds_values[0]
                                odds_entry['away'] = odds_values[-1]
                            if len(odds_values) >= 3:
                                odds_entry['draw'] = odds_values[1]
                            betting_odds[bookmaker_name] = odds_entry
                            bookmaker_data[bookmaker_name] = {'market_type': 'moneyline'}
                    except Exception:
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Playwright direct odds extraction failed: {e}")
            
            self.logger.info(f"Extracted odds for {len(betting_odds)} bookmakers")
            
            return {
                'betting_odds': betting_odds,
                'odds_history': odds_history,
                'bookmaker_data': bookmaker_data
            }
        except Exception as e:
            self.logger.error(f"Error extracting ODDS data: {e}")
            return None
    
    # ─────────────────────────────────────────────────────────
    # STATS TAB
    # ─────────────────────────────────────────────────────────
    
    async def _extract_stats_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from STATS tab — Playwright direct first, YAML engine fallback."""
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}
            current_category = "General"
            
            # ── Playwright direct queries ──
            # FlashScore stats tab has stat rows with category, home value, away value
            try:
                stat_rows = await self.page.query_selector_all(
                    '.stat__row, [class*="statRow"], [class*="stats__row"], [data-testid="stat-row"]'
                )
                stat_headers = await self.page.query_selector_all(
                    '.stat__header, [class*="sectionHeader"], [class*="statHeader"], [data-testid="stat-header"]'
                )
                
                if stat_rows or stat_headers:
                    self.logger.info(f"Found {len(stat_rows)} stat rows, {len(stat_headers)} headers via Playwright")
                    
                    all_elements = stat_rows + stat_headers
                    for element in all_elements:
                        try:
                            cls = await element.get_attribute('class') or ''
                            
                            # Section header?
                            if 'header' in cls.lower() or 'section' in cls.lower():
                                text = (await element.text_content()).strip()
                                if text:
                                    current_category = text
                                    if current_category not in detailed_statistics:
                                        detailed_statistics[current_category] = {}
                                continue
                            
                            # Stat row — try to extract category name, home value, away value
                            # FlashScore stats rows typically have: home_val | category | away_val
                            cells = await element.query_selector_all('span, div, td')
                            if len(cells) >= 3:
                                texts = []
                                for cell in cells:
                                    t = (await cell.text_content()).strip()
                                    if t:
                                        texts.append(t)
                                
                                if len(texts) >= 3:
                                    # Pattern: home_val, category_name, away_val
                                    home_val = texts[0]
                                    name = texts[len(texts) // 2]  # Middle element is usually the category
                                    away_val = texts[-1]
                                    if current_category not in detailed_statistics:
                                        detailed_statistics[current_category] = {}
                                    detailed_statistics[current_category][name] = {
                                        'home': home_val,
                                        'away': away_val
                                    }
                        except Exception:
                            continue
            except Exception as e:
                self.logger.debug(f"Playwright direct stats extraction failed: {e}")
            
            self.logger.info(f"Extracted stats in {len(detailed_statistics)} categories")
            
            return {
                'detailed_statistics': detailed_statistics,
                'player_performance': player_performance,
                'team_performance': team_performance
            }
        except Exception as e:
            self.logger.error(f"Error extracting STATS data: {e}")
            return None
