"""
Basketball match detail extractor implementing primary tab extraction.

Extends the base MatchDetailExtractor with basketball-specific implementations
for primary tabs: SUMMARY, H2H, ODDS, STATS.

Interactive operations (tab clicks, navigation, active tab detection) use
Playwright direct CSS queries because the YAML selector engine is inherently
slow (12-40s per resolve across 4+ strategies) and its ``except Exception``
handlers swallowed CancelledError on Python 3.8, making asyncio.wait_for
timeouts ineffective.  On Python 3.12+, CancelledError is BaseException and
propagates through those handlers, but the engine's strategy iteration is
still too slow for interactive use (tab clicks need <3s response).  Direct
Playwright queries resolve in <1s and bypass the engine entirely.

Non-interactive reads (where 8s latency is acceptable) may fall back to the
YAML selector engine with the SelectorEngineMixin's timeout-protected
_resolve_element / _resolve_elements helpers.
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
        # Pre-extracted data — populated at the start of extract() before any tab navigation
        self._quarter_scores: Optional[Dict[str, Any]] = None
    
    # YAML selector engine methods inherited from SelectorEngineMixin via MatchDetailExtractor
    # (_resolve_element, _resolve_elements, _resolve_text)
    
    async def extract(self, page_state: PageState, timeout: int = 10000) -> Optional[Any]:
        """Override extract() to pre-extract quarter scores BEFORE any tab navigation.

        Quarter scores (smh__part elements) are only reliably present in the
        match header on the initial page load.  After navigating to other
        primary tabs (H2H, Odds, etc.) the smh container may be re-rendered
        or hidden, making Q1-Q4 values unavailable.  Extracting them first
        ensures both the summary and tertiary tabs can use the same data.
        """
        # Extract quarter scores while we're still on the default match detail view
        self._quarter_scores = await self._extract_quarter_scores()
        if self._quarter_scores:
            self.logger.info(f"Pre-extracted quarter scores: {self._quarter_scores}")
        else:
            self.logger.warning("Quarter scores not found on initial page load")
        
        # Delegate to the parent extract() pipeline
        return await super().extract(page_state, timeout)
    
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
            
            # Home team — .duelParticipant__home works on match detail page
            for sel in ['.duelParticipant__home', '.event__participant--home',
                        '.participant__home',
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
            
            # Away team — .duelParticipant__away works on match detail page
            for sel in ['.duelParticipant__away', '.event__participant--away',
                        '.participant__away',
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
            
            # Scores — FlashScore match detail page uses .detailScore__wrapper
            # which contains <span>106</span><span class="detailScore__divider">-</span><span>91</span>
            # The .detailScore__matchInfo also has "106-91Finished" text
            try:
                score_wrapper = await self.page.query_selector('.detailScore__wrapper')
                if score_wrapper:
                    score_spans = await score_wrapper.query_selector_all('span:not([class*="divider"])')
                    valid_scores = []
                    for sp in score_spans:
                        txt = (await sp.text_content()).strip()
                        if txt and txt.isdigit():
                            valid_scores.append(txt)
                    if len(valid_scores) >= 2:
                        current_score = f"{valid_scores[0]}-{valid_scores[1]}"
            except Exception:
                pass
            
            # Fallback: .detailScore__matchInfo contains "106-91Finished"
            if not current_score:
                try:
                    match_info_el = await self.page.query_selector('.detailScore__matchInfo')
                    if match_info_el:
                        info_text = (await match_info_el.text_content()).strip()
                        import re
                        score_match = re.match(r'(\d+)-(\d+)', info_text)
                        if score_match:
                            current_score = f"{score_match.group(1)}-{score_match.group(2)}"
                except Exception:
                    pass
            
            # Fallback: .event__score for listing-style pages
            if not current_score:
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
            
            # Competition / league name — FlashScore uses breadcrumb navigation
            # on match detail pages: Basketball > Australia > NBL1 North
            try:
                breadcrumbs = await self.page.query_selector_all('[class*="breadcrumbItem"]')
                if breadcrumbs:
                    # Last breadcrumb is usually the competition name
                    for bc in reversed(breadcrumbs):
                        text = (await bc.text_content()).strip()
                        if text and len(text) > 2 and len(text) < 60:
                            competition = text
                            break
            except Exception:
                pass
            
            # Fallback: traditional selectors
            if not competition:
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
                        const participants = document.querySelectorAll('[class*="duelParticipant"], [class*="participant__"], [class*="team"]');
                        participants.forEach(p => {
                            const text = p.textContent.trim();
                            if (text && text.length < 50 && text.length > 1) {
                                const cls = p.className || '';
                                if (cls.includes('home') && !data.home_team) data.home_team = text;
                                if (cls.includes('away') && !data.away_team) data.away_team = text;
                            }
                        });
                        // Try breadcrumb for competition
                        const crumbs = document.querySelectorAll('[class*="breadcrumbItem"]');
                        if (crumbs.length > 0) {
                            const last = crumbs[crumbs.length - 1];
                            const text = last.textContent.trim();
                            if (text && text.length < 60) data.competition = text;
                        }
                        // Fallback: tournament header
                        if (!data.competition) {
                            const tournament = document.querySelector('[class*="tournament"], [class*="header"]');
                            if (tournament && tournament.textContent.trim().length < 100) {
                                data.competition = tournament.textContent.trim();
                            }
                        }
                        // Score from detailScore__matchInfo
                        const scoreInfo = document.querySelector('.detailScore__matchInfo');
                        if (scoreInfo) {
                            const m = scoreInfo.textContent.match(/(\\d+)-(\\d+)/);
                            if (m) data.score = m[1] + '-' + m[2];
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
                    if not current_score and js_result.get('score'):
                        current_score = js_result['score']
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
            # Use 'match-stats' which maps to display text "Stats" on basketball pages
            stats_data = await self.primary_extractor.extract_tab_data('match-stats')
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
        """Extract data from tertiary tabs (quarter-by-quarter stats).

        FlashScore basketball layout (confirmed via live inspection):
          Primary tabs: Match, Odds, H2H, Draw, Summary, Player Stats, Stats, ...
          Under Summary → Stats sub-tab, tertiary period filters appear:
            Match | 1st Quarter | 2nd Quarter | 3rd Quarter | 4th Quarter

        Strategy:
          1. Use pre-extracted quarter scores from self._quarter_scores
             (populated at the start of extract() before any tab navigation).
          2. Navigate to the Stats sub-tab.
          3. For each period filter (Match, 1st-4th Quarter), click it and
             extract the stat comparison rows using data-testid="wcl-statistics".
        """
        try:
            match_stats = None
            q1_stats = None
            q2_stats = None
            q3_stats = None
            q4_stats = None

            # Step 1: Use pre-extracted quarter scores (populated by extract() override)
            quarter_scores = self._quarter_scores

            # Step 2: Navigate to the Stats sub-tab
            # Use 'match-stats' which maps to display text "Stats" (not 'stats' which maps to "Standings")
            if not await self.primary_extractor.navigate_to_tab('match-stats'):
                self.logger.warning("Could not navigate to Stats tab; skipping tertiary extraction")
                # Return quarter scores even if stats extraction fails
                return TertiaryData(quarter_scores=quarter_scores)

            await self.page.wait_for_timeout(2000)

            # Step 3: Detect available period filters
            available_periods = await self._detect_period_filters()
            self.logger.info(f"Available period filters: {available_periods}")

            # Step 4: Extract stats for each period
            # Always start with "Match" (full game) — it may already be active
            if 'match' in available_periods or not available_periods:
                match_stats = await self._extract_period_stats('Match')
            else:
                # If "Match" is not found as a filter, just extract whatever is showing
                match_stats = await self._extract_stats_rows()

            if '1st quarter' in available_periods:
                q1_stats = await self._extract_period_stats('1st Quarter')
            if '2nd quarter' in available_periods:
                q2_stats = await self._extract_period_stats('2nd Quarter')
            if '3rd quarter' in available_periods:
                q3_stats = await self._extract_period_stats('3rd Quarter')
            if '4th quarter' in available_periods:
                q4_stats = await self._extract_period_stats('4th Quarter')

            return TertiaryData(
                match=match_stats,
                q1=q1_stats,
                q2=q2_stats,
                q3=q3_stats,
                q4=q4_stats,
                quarter_scores=quarter_scores,
                inc_ot=match_stats,   # backward compat
                ft=match_stats,       # backward compat
            )
        except Exception as e:
            self.logger.error(f"Error extracting tertiary tabs: {e}")
            return TertiaryData()

    async def _extract_quarter_scores(self) -> Optional[Dict[str, Any]]:
        """Extract quarter-by-quarter scores from the match header.

        FlashScore renders quarter scores in the duel participant header using
        smh__part elements inside .smh__template container:
          - smh__part smh__score smh__home smh__part--current  → home total
          - smh__part smh__home smh__part--1  → home Q1 score
          - smh__part smh__home smh__part--2  → home Q2 score
          ... (same pattern for smh__away)
        Each smh__part may contain a <sup> child (empty for finished matches).

        IMPORTANT: Must run BEFORE any tab navigation, as the smh container
        may disappear from the DOM after switching tabs.  Also, scroll to the
        top of the page first to ensure the header is loaded and visible.
        """
        try:
            # Scroll to top so the match header (with smh elements) is in view
            await self.page.evaluate('window.scrollTo(0, 0)')
            await self.page.wait_for_timeout(500)

            # Wait for the smh container to appear
            try:
                await self.page.wait_for_selector(
                    '[class*="smh__template"]', timeout=5000
                )
            except Exception:
                self.logger.debug("smh__template container not found; trying without wait")

            scores = await self.page.evaluate("""
                () => {
                    const result = { home: {}, away: {} };

                    // Home quarter scores: smh__part smh__home smh__part--N
                    // Use direct child text of smh__part, ignoring <sup> elements
                    const homeParts = document.querySelectorAll(
                        '[class*="smh__home"][class*="smh__part--"]'
                    );
                    homeParts.forEach(el => {
                        const cls = el.className || '';
                        const m = cls.match(/smh__part--(\\d+)/);
                        if (m) {
                            const qNum = parseInt(m[1]);
                            // Get direct text node, skip <sup> children
                            let val = '';
                            for (const node of el.childNodes) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    val += node.textContent.trim();
                                }
                            }
                            // Fallback: use full textContent if direct text is empty
                            if (!val) val = el.textContent.trim();
                            // Only keep the numeric part
                            const numMatch = val.match(/^(\\d+)/);
                            if (numMatch) result.home['Q' + qNum] = numMatch[1];
                        }
                    });

                    // Away quarter scores: smh__part smh__away smh__part--N
                    const awayParts = document.querySelectorAll(
                        '[class*="smh__away"][class*="smh__part--"]'
                    );
                    awayParts.forEach(el => {
                        const cls = el.className || '';
                        const m = cls.match(/smh__part--(\\d+)/);
                        if (m) {
                            const qNum = parseInt(m[1]);
                            let val = '';
                            for (const node of el.childNodes) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    val += node.textContent.trim();
                                }
                            }
                            if (!val) val = el.textContent.trim();
                            const numMatch = val.match(/^(\\d+)/);
                            if (numMatch) result.away['Q' + qNum] = numMatch[1];
                        }
                    });

                    // Total scores from smh__part--current (has smh__score class)
                    const homeTotal = document.querySelector(
                        '[class*="smh__score"][class*="smh__home"]'
                    );
                    const awayTotal = document.querySelector(
                        '[class*="smh__score"][class*="smh__away"]'
                    );
                    if (homeTotal) {
                        const v = homeTotal.textContent.trim();
                        const m = v.match(/^(\\d+)/);
                        if (m) result.home['total'] = m[1];
                    }
                    if (awayTotal) {
                        const v = awayTotal.textContent.trim();
                        const m = v.match(/^(\\d+)/);
                        if (m) result.away['total'] = m[1];
                    }

                    // Fallback: extract total from detailScore__wrapper
                    if (!result.home.total || !result.away.total) {
                        const wrapper = document.querySelector('.detailScore__wrapper');
                        if (wrapper) {
                            const spans = wrapper.querySelectorAll('span:not([class*="divider"])');
                            const nums = Array.from(spans)
                                .map(s => s.textContent.trim())
                                .filter(t => /^\\d+$/.test(t));
                            if (nums.length >= 2) {
                                if (!result.home.total) result.home.total = nums[0];
                                if (!result.away.total) result.away.total = nums[1];
                            }
                        }
                    }

                    const hasData = Object.keys(result.home).length > 0
                                 || Object.keys(result.away).length > 0;
                    return hasData ? result : null;
                }
            """)
            if scores:
                self.logger.info(f"Extracted quarter scores: {scores}")
            else:
                self.logger.warning("Quarter scores not found in DOM — smh elements may not be present")
            return scores
        except Exception as e:
            self.logger.debug(f"Error extracting quarter scores: {e}")
            return None

    async def _detect_period_filters(self) -> List[str]:
        """Detect which period filter tabs are available under the Stats sub-tab.

        Period filters are tertiary tabs rendered as button[data-testid="wcl-tab"]
        inside a container with data-type="tertiary".
        """
        try:
            filters = await self.page.evaluate("""
                () => {
                    const tertiary = document.querySelector('[data-type="tertiary"]');
                    if (!tertiary) return [];
                    const btns = tertiary.querySelectorAll('button[data-testid="wcl-tab"]');
                    return Array.from(btns).map(b => b.textContent.trim().toLowerCase());
                }
            """)
            return filters if filters else []
        except Exception as e:
            self.logger.debug(f"Error detecting period filters: {e}")
            return []
    
    async def _extract_stats_rows(self) -> Optional[Dict[str, Any]]:
        """Extract stats from currently visible content — Playwright direct only.

        FlashScore stats layout (confirmed via live inspection):
          - Section headers: .stat__header (e.g. "Scoring", "Rebounds", "Other")
          - Stat rows: [data-testid="wcl-statistics"]
            Each row contains:
              [data-testid="wcl-statistics-value"] (home)  →  first match
              [data-testid="wcl-statistics-category"]      →  stat name
              [data-testid="wcl-statistics-value"] (away)  →  second match
        """
        try:
            # Strategy 1: JavaScript extraction using data-testid selectors (fastest, most reliable)
            statistics = await self.page.evaluate("""
                () => {
                    const stats = {};
                    let currentSection = 'General';

                    // Get section headers
                    const headers = document.querySelectorAll('.stat__header');
                    // Get stat rows
                    const rows = document.querySelectorAll('[data-testid="wcl-statistics"]');

                    if (rows.length === 0) return null;

                    // Build a map from element position to section header
                    // Headers and rows are siblings in DOM order
                    const allElements = document.querySelectorAll('.stat__header, [data-testid="wcl-statistics"]');
                    allElements.forEach(el => {
                        if (el.classList.contains('stat__header') || el.className.includes('sectionHeader')) {
                            const text = el.textContent.trim();
                            if (text) {
                                currentSection = text;
                                if (!(currentSection in stats)) stats[currentSection] = {};
                            }
                            return;
                        }

                        // It's a stat row
                        const category = el.querySelector('[data-testid="wcl-statistics-category"]');
                        const values = el.querySelectorAll('[data-testid="wcl-statistics-value"]');
                        if (category && values.length >= 2) {
                            const catName = category.textContent.trim();
                            const homeVal = values[0].textContent.trim();
                            const awayVal = values[1].textContent.trim();
                            if (catName) {
                                if (!(currentSection in stats)) stats[currentSection] = {};
                                stats[currentSection][catName] = { home: homeVal, away: awayVal };
                            }
                        }
                    });

                    return Object.keys(stats).length > 0 ? stats : null;
                }
            """)

            if statistics:
                self.logger.info(f"Extracted stats in {len(statistics)} sections via data-testid")
                return statistics

            # Strategy 2: Fallback — Playwright direct with older CSS class patterns
            statistics = {}
            current_section = "General"

            stat_rows = []
            stat_headers = []
            for sel in ['.stat__row', '[class*="statRow"]', '[class*="stats__row"]']:
                try:
                    found = await self.page.query_selector_all(sel)
                    stat_rows.extend(found)
                except Exception:
                    continue
            for sel in ['.stat__header', '[class*="sectionHeader"]', '[class*="statHeader"]']:
                try:
                    found = await self.page.query_selector_all(sel)
                    stat_headers.extend(found)
                except Exception:
                    continue

            if stat_rows or stat_headers:
                all_elements = stat_headers + stat_rows
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
        """Click a period filter tab inside the tertiary tabs container.

        Period filters live inside [data-type="tertiary"] and are rendered as
        button[data-testid="wcl-tab"].  We must scope our search to the tertiary
        container so we don't accidentally click a primary tab with the same text.

        Playwright direct + JavaScript only — YAML selector engine NOT used.
        """
        # Strategy 1: JavaScript — click the button inside the tertiary container
        try:
            safe_name = period_name.replace("'", "\\'")
            clicked = await self.page.evaluate(f"""
                () => {{
                    const tertiary = document.querySelector('[data-type="tertiary"]');
                    if (!tertiary) return false;
                    const btns = tertiary.querySelectorAll('button[data-testid="wcl-tab"]');
                    for (const btn of btns) {{
                        if (btn.textContent.trim() === '{safe_name}') {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if clicked:
                await self.page.wait_for_timeout(2000)
                self.logger.info(f"Clicked period filter via JS: {period_name}")
                return True
        except Exception:
            pass

        # Strategy 2: Playwright direct — find the tertiary container then its buttons
        try:
            tertiary_container = await self.page.query_selector('[data-type="tertiary"]')
            if tertiary_container:
                buttons = await tertiary_container.query_selector_all('button[data-testid="wcl-tab"]')
                for btn in buttons:
                    text = (await btn.text_content()).strip()
                    if text == period_name:
                        await btn.click()
                        await self.page.wait_for_timeout(2000)
                        self.logger.info(f"Clicked period filter: {period_name}")
                        return True
        except Exception:
            pass

        # Strategy 3: Broader fallback — try all tab buttons (less precise)
        try:
            buttons = await self.page.query_selector_all('button[data-testid="wcl-tab"]')
            for btn in buttons:
                text = (await btn.text_content()).strip()
                if text == period_name:
                    await btn.click()
                    await self.page.wait_for_timeout(2000)
                    self.logger.info(f"Clicked period filter (broad search): {period_name}")
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
        """Extract data from SUMMARY tab — Playwright direct with JavaScript enrichment.

        The Summary sub-tab (default under Match primary tab) contains:
          - Match overview: competition, date, status, venue, series info
          - Score breakdown with quarter-by-quarter scores
          - Key match events (incidents, highlights)
          - Stats preview (top stats)
          - Player Stats - Top 3

        Live-site verified selectors:
          - Breadcrumbs: .detail__breadcrumbs or [class*="breadcrumbItem"]
          - Venue: inside [class*="wclDetailSection"] with "Venue:" prefix
          - Series info: .infoBox__info inside .infoBox__wrapper
          - Winner: .duelParticipant--winner class on team name
        """
        try:
            overview = {}
            team_statistics = {}
            match_events = []

            # ── JavaScript extraction — single round-trip, comprehensive ──
            summary_data = await self.page.evaluate("""
                () => {
                    const data = { overview: {}, match_events: [] };

                    // Competition from breadcrumbs — deduplicate adjacent identical entries
                    const crumbs = document.querySelectorAll('[class*="breadcrumbItem"]');
                    if (crumbs.length > 0) {
                        const texts = Array.from(crumbs).map(c => c.textContent.trim()).filter(t => t);
                        // Deduplicate: remove consecutive duplicates (FlashScore renders each
                        // breadcrumb twice — once as icon, once as text link)
                        const deduped = texts.filter((t, i) => i === 0 || t !== texts[i - 1]);
                        if (deduped.length > 0) data.overview.competition = deduped[deduped.length - 1];
                        if (deduped.length > 1) data.overview.breadcrumb_path = deduped.join(' > ');
                    }
                    // Fallback: tournament header
                    if (!data.overview.competition) {
                        const tHeader = document.querySelector('.tournamentHeader__content');
                        if (tHeader) data.overview.competition = tHeader.textContent.trim();
                    }

                    // Match start time
                    const timeEl = document.querySelector('.duelParticipant__startTime');
                    if (timeEl) data.overview.date = timeEl.textContent.trim();

                    // Match status
                    const statusEl = document.querySelector('.detailScore__status');
                    if (statusEl) data.overview.status = statusEl.textContent.trim();

                    // Winner detection — .duelParticipant--winner is on the parent container
                    const winnerContainer = document.querySelector('.duelParticipant--winner');
                    if (winnerContainer) {
                        // The container's textContent is just the team name (e.g. "Gigantes San Francisco")
                        // But first try the specific participant name link
                        const nameLink = winnerContainer.querySelector('[class*="participantName"] a, a[class*="participantName"]');
                        if (nameLink && nameLink.textContent.trim()) {
                            data.overview.winner = nameLink.textContent.trim();
                        } else {
                            // Fallback: use the container's direct text (excludes icon SVGs)
                            const text = winnerContainer.textContent.trim();
                            if (text && text.length < 80) {
                                data.overview.winner = text;
                            }
                        }
                    }

                    // Venue — search for elements containing "Venue:" using XPath (efficient)
                    const venueResult = document.evaluate(
                        '//*[contains(text(), "Venue:")]|//*[starts-with(text(), "Venue:")]',
                        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    if (venueResult.singleNodeValue) {
                        const text = venueResult.singleNodeValue.textContent.trim();
                        if (text.startsWith('Venue:')) {
                            data.overview.venue = text.substring(6).trim();
                        }
                    }
                    // Fallback: search inside detail/summary widgets
                    if (!data.overview.venue) {
                        const widgets = document.querySelectorAll(
                            '[class*="wclDetailSection"], [class*="summaryWidget"], [class*="detailSection"]'
                        );
                        for (const w of widgets) {
                            const text = w.textContent.trim();
                            const idx = text.indexOf('Venue:');
                            if (idx >= 0) {
                                const after = text.substring(idx + 6).trim();
                                // Take first line only
                                const nlIdx = after.indexOf('\\n');
                                data.overview.venue = nlIdx >= 0 ? after.substring(0, nlIdx).trim() : after;
                                break;
                            }
                        }
                    }

                    // Referee — similar XPath approach
                    const refResult = document.evaluate(
                        '//*[starts-with(text(), "Referee:") or starts-with(text(), "Referees:")]',
                        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    if (refResult.singleNodeValue) {
                        const text = refResult.singleNodeValue.textContent.trim();
                        const colonIdx = text.indexOf(':');
                        if (colonIdx >= 0) {
                            data.overview.referee = text.substring(colonIdx + 1).trim();
                        }
                    }

                    // Series / leg info from infoBox
                    const infoBox = document.querySelector('.infoBox__info');
                    if (infoBox) {
                        const text = infoBox.textContent.trim();
                        if (text) data.overview.series_info = text;
                    }

                    // Score breakdown — extract from smh__part elements
                    const smhContainer = document.querySelector('[class*="smh__template"]');
                    if (smhContainer) {
                        const homeQ = {}, awayQ = {};
                        smhContainer.querySelectorAll('[class*="smh__home"][class*="smh__part--"]').forEach(el => {
                            const m = el.className.match(/smh__part--(\\d+)/);
                            if (m) {
                                const val = el.textContent.trim().replace(/\\D/g, '');
                                if (val) homeQ['Q' + m[1]] = val;
                            }
                        });
                        smhContainer.querySelectorAll('[class*="smh__away"][class*="smh__part--"]').forEach(el => {
                            const m = el.className.match(/smh__part--(\\d+)/);
                            if (m) {
                                const val = el.textContent.trim().replace(/\\D/g, '');
                                if (val) awayQ['Q' + m[1]] = val;
                            }
                        });
                        // Total scores
                        const homeScore = smhContainer.querySelector('[class*="smh__score"][class*="smh__home"]');
                        const awayScore = smhContainer.querySelector('[class*="smh__score"][class*="smh__away"]');
                        if (homeScore) homeQ['total'] = homeScore.textContent.trim();
                        if (awayScore) awayQ['total'] = awayScore.textContent.trim();

                        if (Object.keys(homeQ).length > 0 || Object.keys(awayQ).length > 0) {
                            data.overview.quarter_scores = { home: homeQ, away: awayQ };
                        }
                    }

                    // Key match events (incidents like technical fouls, ejections, etc.)
                    const incidentEls = document.querySelectorAll(
                        '[class*="incident"], [class*="moment"], [class*="eventRow"]'
                    );
                    incidentEls.forEach(el => {
                        const text = el.textContent.trim();
                        if (text && text.length > 3 && text.length < 200) {
                            data.match_events.push({ type: 'incident', content: text });
                        }
                    });

                    // Stats preview rows (if visible on Summary tab)
                    const statPreviewRows = document.querySelectorAll(
                        '[data-testid="wcl-statistics"]'
                    );
                    statPreviewRows.forEach(row => {
                        const cat = row.querySelector('[data-testid="wcl-statistics-category"]');
                        const vals = row.querySelectorAll('[data-testid="wcl-statistics-value"]');
                        if (cat && vals.length >= 2) {
                            const catName = cat.textContent.trim();
                            if (!data.stats_preview) data.stats_preview = {};
                            data.stats_preview[catName] = {
                                home: vals[0].textContent.trim(),
                                away: vals[1].textContent.trim()
                            };
                        }
                    });

                    return data;
                }
            """)

            if summary_data:
                overview = summary_data.get('overview', {})
                match_events = summary_data.get('match_events', [])
                if summary_data.get('stats_preview'):
                    team_statistics = summary_data['stats_preview']

            # ── Playwright direct fallbacks for any missing fields ──

            # Competition fallback
            if 'competition' not in overview:
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

            # Date fallback
            if 'date' not in overview:
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

            # Status fallback
            if 'status' not in overview:
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

            self.logger.info(f"Summary overview: {list(overview.keys())} ({len(match_events)} events)")
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
        """Extract data from ODDS tab — uses live-site-verified selectors.
        
        FlashScore odds layout (confirmed via live inspection):
        - .oddsTab__tableWrapper contains the odds table
        - .ui-table__row for each bookmaker row
        - a[title] for bookmaker name (e.g. title="1xBet")
        - a.oddsCell__odd for odds values (e.g. text "1.28", "3.35")
        """
        try:
            betting_odds = {}
            odds_history = []
            bookmaker_data = {}
            
            # ── Playwright direct queries using live-site selectors ──
            try:
                # Primary: .ui-table__row inside oddsTab__tableWrapper
                odds_rows = await self.page.query_selector_all('.ui-table__row')
                
                if not odds_rows:
                    # Fallback: try old selectors
                    odds_rows = await self.page.query_selector_all(
                        '.oddsRow, [class*="odds__row"], [class*="oddsRow"]'
                    )
                
                self.logger.info(f"Found {len(odds_rows)} odds rows via Playwright direct")
                
                for row in odds_rows:
                    try:
                        # Get bookmaker name from a[title] (FlashScore uses title attr on logo links)
                        bookmaker_name = ""
                        name_el = await row.query_selector('a[title]')
                        if name_el:
                            bookmaker_name = await name_el.get_attribute('title') or ""
                        if not bookmaker_name:
                            name_el = await row.query_selector('img[alt]')
                            if name_el:
                                bookmaker_name = await name_el.get_attribute('alt') or ""
                        
                        if not bookmaker_name:
                            continue
                        
                        # Extract odds values from a.oddsCell__odd links
                        odds_cells = await row.query_selector_all('a.oddsCell__odd')
                        odds_values = []
                        for cell in odds_cells:
                            text = (await cell.text_content()).strip()
                            if text:
                                odds_values.append(text)
                        
                        # Fallback: try generic odds cell selectors
                        if not odds_values:
                            cells = await row.query_selector_all(
                                'td[class*="odds"], [class*="oddsCell"], [class*="cell"]'
                            )
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
            
            # JavaScript fallback — extract odds via DOM traversal
            if not betting_odds:
                try:
                    js_odds = await self.page.evaluate("""
                        () => {
                            const odds = {};
                            const rows = document.querySelectorAll('.ui-table__row');
                            rows.forEach(row => {
                                const nameEl = row.querySelector('a[title]');
                                if (!nameEl) return;
                                const name = nameEl.getAttribute('title');
                                const cells = row.querySelectorAll('a.oddsCell__odd');
                                const vals = Array.from(cells).map(c => c.textContent.trim()).filter(t => t);
                                if (name && vals.length >= 2) {
                                    odds[name] = {home: vals[0], away: vals[vals.length-1], market_type: 'moneyline'};
                                }
                            });
                            return Object.keys(odds).length > 0 ? odds : null;
                        }
                    """)
                    if js_odds:
                        betting_odds = js_odds
                        for name in js_odds:
                            bookmaker_data[name] = {'market_type': 'moneyline'}
                except Exception:
                    pass
            
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
        """Extract data from STATS tab — Playwright direct first, YAML engine fallback.

        FlashScore stats layout (confirmed via live inspection):
          - Section headers: .stat__header (e.g. "Scoring", "Rebounds", "Other")
          - Stat rows: [data-testid="wcl-statistics"]
            Each row contains:
              [data-testid="wcl-statistics-value"] (home)  →  first match
              [data-testid="wcl-statistics-category"]      →  stat name
              [data-testid="wcl-statistics-value"] (away)  →  second match
        """
        try:
            detailed_statistics = {}
            player_performance = []
            team_performance = {}

            # Strategy 1: JavaScript extraction using data-testid selectors (most reliable)
            try:
                js_stats = await self.page.evaluate("""
                    () => {
                        const stats = {};
                        let currentSection = 'General';
                        const allElements = document.querySelectorAll(
                            '.stat__header, [data-testid="wcl-statistics"]'
                        );
                        allElements.forEach(el => {
                            if (el.classList.contains('stat__header') || el.className.includes('sectionHeader')) {
                                const text = el.textContent.trim();
                                if (text) {
                                    currentSection = text;
                                    if (!(currentSection in stats)) stats[currentSection] = {};
                                }
                                return;
                            }
                            const category = el.querySelector('[data-testid="wcl-statistics-category"]');
                            const values = el.querySelectorAll('[data-testid="wcl-statistics-value"]');
                            if (category && values.length >= 2) {
                                const catName = category.textContent.trim();
                                const homeVal = values[0].textContent.trim();
                                const awayVal = values[1].textContent.trim();
                                if (catName) {
                                    if (!(currentSection in stats)) stats[currentSection] = {};
                                    stats[currentSection][catName] = { home: homeVal, away: awayVal };
                                }
                            }
                        });
                        return Object.keys(stats).length > 0 ? stats : null;
                    }
                """)
                if js_stats:
                    detailed_statistics = js_stats
                    self.logger.info(f"Extracted stats in {len(detailed_statistics)} sections via data-testid")
            except Exception as e:
                self.logger.debug(f"data-testid stats extraction failed: {e}")

            # Strategy 2: Fallback — Playwright direct with CSS class patterns
            if not detailed_statistics:
                current_category = "General"
                try:
                    stat_rows = await self.page.query_selector_all(
                        '.stat__row, [class*="statRow"], [class*="stats__row"]'
                    )
                    stat_headers = await self.page.query_selector_all(
                        '.stat__header, [class*="sectionHeader"], [class*="statHeader"]'
                    )

                    if stat_rows or stat_headers:
                        self.logger.info(f"Found {len(stat_rows)} stat rows, {len(stat_headers)} headers via CSS fallback")

                        all_elements = stat_headers + stat_rows
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

                                # Stat row
                                cells = await element.query_selector_all('span, div, td')
                                if len(cells) >= 3:
                                    texts = []
                                    for cell in cells:
                                        t = (await cell.text_content()).strip()
                                        if t:
                                            texts.append(t)

                                    if len(texts) >= 3:
                                        home_val = texts[0]
                                        name = texts[len(texts) // 2]
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
                    self.logger.debug(f"CSS fallback stats extraction failed: {e}")

            # Strategy 3: If no stat comparison found, try extracting standings table
            if not detailed_statistics:
                try:
                    standings_rows = await self.page.query_selector_all(
                        '.tabContent__stats-detail .ui-table__row'
                    )
                    if standings_rows:
                        self.logger.info(f"Found {len(standings_rows)} standings rows")
                        standings_data = []
                        for row in standings_rows:
                            text = (await row.text_content()).strip()
                            if text:
                                import re
                                match = re.match(r'(\d+)\.\s*(.+)', text)
                                if match:
                                    pos = int(match.group(1))
                                    remainder = match.group(2)
                                    form_match = re.search(r'([WLD]+)$', remainder)
                                    form = form_match.group(1) if form_match else ''
                                    if form:
                                        remainder = remainder[:-len(form)]
                                    pct_match = re.search(r'([\d.]+)\??$', remainder)
                                    win_pct = pct_match.group(1) if pct_match else ''
                                    if pct_match:
                                        remainder = remainder[:pct_match.start()]
                                    pts_match = re.search(r'(\d+:\d+)$', remainder)
                                    points_ratio = pts_match.group(1) if pts_match else ''
                                    if pts_match:
                                        remainder = remainder[:pts_match.start()]
                                    nums = re.findall(r'\d+', remainder)
                                    team_part = re.sub(r'\d+$', '', remainder).strip()

                                    entry = {
                                        'position': pos,
                                        'team': team_part,
                                        'played': int(nums[0]) if len(nums) > 0 else 0,
                                        'wins': int(nums[1]) if len(nums) > 1 else 0,
                                        'losses': int(nums[2]) if len(nums) > 2 else 0,
                                        'draws_or_other': int(nums[3]) if len(nums) > 3 else 0,
                                        'points_ratio': points_ratio,
                                        'win_pct': win_pct,
                                        'form': form,
                                    }
                                    standings_data.append(entry)

                        if standings_data:
                            detailed_statistics['standings'] = {
                                entry['team']: entry for entry in standings_data
                            }
                            team_performance = standings_data
                            self.logger.info(f"Extracted {len(standings_data)} standings entries")
                except Exception as e:
                    self.logger.debug(f"Standings table extraction failed: {e}")

            self.logger.info(f"Extracted stats in {len(detailed_statistics)} categories")

            return {
                'detailed_statistics': detailed_statistics,
                'player_performance': player_performance,
                'team_performance': team_performance
            }
        except Exception as e:
            self.logger.error(f"Error extracting STATS data: {e}")
            return None
