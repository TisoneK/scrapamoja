"""Match detail page extractor for BetB2B skins.

Navigates to a **specific match page** (e.g.
``/en/line/basketball/352015844-oklahoma-city-thunder-brooklyn-nets``)
and extracts ALL visible UI data: scoreboard, period scores, statistics,
market groups, H2H sections, and any other rendered data.

This is complementary to the dashboard-level extractors in
:mod:`~src.sites.betb2b.extraction.dom` — they extract from the list view,
this extracts from the individual match detail view.

Usage::

    from playwright.async_api import async_playwright
    from src.sites.betb2b.extraction.match_detail import extract_match_page

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://linebet.com/en/line/basketball/...")
        data = await extract_match_page(page)
        print(data["scoreboard"])
        print(data["period_scores"])
        print(data["market_groups"])
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class ScoreboardData:
    """Data visible in the match scoreboard header."""

    home_team: str = ""
    away_team: str = ""
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    competition: str = ""
    sport: str = ""
    status: str = ""  # e.g. "live", "finished", "not_started"
    minute: Optional[int] = None
    period: Optional[str] = None
    start_time: Optional[str] = None
    event_id: str = ""
    venue: Optional[str] = None


@dataclass
class PeriodScore:
    """Score for one period (quarter, half, set, etc.)."""

    period_name: str  # e.g. "1st Quarter", "2nd Half"
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    period_type: Optional[int] = None  # raw BetB2B period type value


@dataclass
class MatchStatistic:
    """One row from the match statistics table."""

    label: str          # e.g. "Ball Possession", "Shots on Goal"
    home_value: str = ""
    away_value: str = ""


@dataclass
class MarketGroupData:
    """One market group as rendered on the match page."""

    group_name: str                           # e.g. "Match Result", "Totals"
    selections: List[Dict[str, Any]] = field(default_factory=list)
    # Each selection: {"name": "1", "price": 1.85, "suspended": False, ...}


@dataclass
class MatchPageData:
    """All extracted data from a match detail page."""

    url: str = ""
    scoreboard: Dict[str, Any] = field(default_factory=dict)
    period_scores: List[Dict[str, Any]] = field(default_factory=list)
    statistics: List[Dict[str, Any]] = field(default_factory=list)
    market_groups: List[Dict[str, Any]] = field(default_factory=list)
    h2h_sections: List[Dict[str, Any]] = field(default_factory=list)
    summary_info: Dict[str, Any] = field(default_factory=dict)
    raw_html_size: int = 0
    extraction_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# The JS script that walks the match page
# ---------------------------------------------------------------------------
_MATCH_PAGE_SCRIPT = """
() => {
  const txt = el => el && el.textContent ? el.textContent.trim() : "";
  const num = s => { const m = (s||"").replace(',', '.').match(/-?\\d+(?:\\.\\d+)?/); return m ? parseFloat(m[0]) : null; };

  const result = {};

  // ── 1. Scoreboard ──────────────────────────────────────────────
  result.scoreboard = {};

  // Team names — scope to scoreboard-intro__team to avoid duplicates
  const teamEls = document.querySelectorAll('.scoreboard-intro__team .scoreboard-team-name__text');
  if (teamEls.length >= 2) {
    result.scoreboard.home_team = txt(teamEls[0]);
    result.scoreboard.away_team = txt(teamEls[1]);
  } else if (teamEls.length === 1) {
    result.scoreboard.home_team = txt(teamEls[0]);
  }

  // Scores — BetB2B: home = bare .scoreboard-scores__score, away = .scoreboard-scores__score--team-2
  const sHome = document.querySelector('.scoreboard-scores__score:not(.scoreboard-scores__score--team-2):not(.scoreboard-scores__colon)');
  const sAway = document.querySelector('.scoreboard-scores__score--team-2');
  if (sHome) result.scoreboard.home_score = num(txt(sHome));
  if (sAway) result.scoreboard.away_score = num(txt(sAway));
  // Fallback: .scoreboard-header__col children
  if (!result.scoreboard.home_score && !result.scoreboard.away_score) {
    const cols = document.querySelectorAll('.scoreboard-header__col');
    if (cols.length >= 2) {
      result.scoreboard.home_score = num(txt(cols[0]));
      result.scoreboard.away_score = num(txt(cols[1]));
    }
  }

  // Competition — from scoreboard-header or scoreboard-section area
  const compEl = document.querySelector('.scoreboard-header__label, .scoreboard-header__competition, .scoreboard-section-block__title');
  if (compEl) result.scoreboard.competition = txt(compEl);

  // Status — .scoreboard-status + .ui-game-timer
  const statusEl = document.querySelector('.scoreboard-status');
  if (statusEl) result.scoreboard.status = txt(statusEl);
  // Timer for live minute
  const timerEl = document.querySelector('.ui-game-timer__label');
  if (timerEl) {
    const t = txt(timerEl);
    if (t) { result.scoreboard.minute = num(t); if (!result.scoreboard.status) result.scoreboard.status = t; }
  }
  // Fallback: time in status element
  if (result.scoreboard.status && !result.scoreboard.minute) {
    const mm = result.scoreboard.status.match(/(\\d+)\\s*['']/);
    if (mm) result.scoreboard.minute = parseInt(mm[1]);
  }

  // Event ID from URL — match LAST number-hyphen segment (not competition id)
  const href = window.location.href;
  const evtMatch = href.match(/\\/(\\d{5,})-[^\\/]+$/);
  if (evtMatch) result.scoreboard.event_id = evtMatch[1];

  // ── 2. Period scores ──────────────────────────────────────────
  // BetB2B period table: --team-0 = home scores, --team-1 = away scores.
  // TH captions = period names (first is empty corner cell), skip index 0.
  result.period_scores = [];
  (function() {
    const homeScores = document.querySelectorAll('.scoreboard-periods-table-cell__caption--team-0');
    const awayScores = document.querySelectorAll('.scoreboard-periods-table-cell__caption--team-1');
    const thCaptions = document.querySelectorAll('.scoreboard-periods-table-cell--th .scoreboard-periods-table-cell__caption');
    const names = [];
    thCaptions.forEach(function(el) {
      var t = txt(el);
      if (t) names.push(t);
    });
    var len = Math.min(names.length, homeScores.length, awayScores.length);
    for (var i = 0; i < len; i++) {
      result.period_scores.push({
        period_name: names[i],
        home_score: num(txt(homeScores[i])),
        away_score: num(txt(awayScores[i]))
      });
    }
  })();
  // Fallback: try capturing individual period cells if above fails
  if (result.period_scores.length === 0) {
    document.querySelectorAll('.scoreboard-periods-table [class*=row], .scoreboard-periods-inning').forEach(function(row) {
      var cells = row.querySelectorAll('[class*=cell], [class*=score]');
      var homeVal = cells[0] ? num(txt(cells[0])) : null;
      var awayVal = cells[1] ? num(txt(cells[1])) : null;
      if (homeVal !== null || awayVal !== null) {
        result.period_scores.push({ period_name: '', home_score: homeVal, away_score: awayVal });
      }
    });
  }

  // ── 3. Statistics (div-based) ─────────────────────────────────
  result.statistics = [];
  // BetB2B uses .scoreboard-stats-table-view-row (5 stats)
  document.querySelectorAll('.scoreboard-stats-table-view-row, .scoreboard-stats__row').forEach(function(row) {
    var label = txt(row.querySelector('.scoreboard-stats-table-view-row__name, .scoreboard-stats-table-view-name__label, [class*=name]'));
    var values = row.querySelectorAll('.scoreboard-stats-table-view-row__value, .scoreboard-stats-value');
    if (label && values.length >= 1) {
      result.statistics.push({
        label: label,
        home_value: txt(values[0]),
        away_value: values.length >= 2 ? txt(values[1]) : ''
      });
    }
  });

  // ── 4. Market groups ─────────────────────────────────────────
  // NOTE: BetB2B match pages LAZY-LOAD markets via SPA.
  // The `.market-grid` container is empty placeholder until the
  // Vue component fetches odds and renders them. This JS runs at
  // page-ready and will NOT see rendered markets unless we wait.
  // Market data is reliably available from GetGameZip API endpoint.
  result.market_groups = [];

  // ── 5. H2H sections ──────────────────────────────────────────
  // NOTE: H2H is triggered by hover on team names/statistic button.
  // The SPA fetches the H2H data from statisticfeed API and renders
  // it in a popup/panel. This JS runs at page-ready and will NOT
  // see the popup. H2H data is available from statisticfeed API.
  result.h2h_sections = [];

  // ── 6. Summary info ──────────────────────────────────────────
  result.summary_info = {};
  const summaryEl = document.querySelector('.scoreboard-content-layout__header, [class*=venue], [class*=details]');
  if (summaryEl) result.summary_info.raw = txt(summaryEl).substring(0, 1000);

  return result;
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def extract_match_page(page: Any) -> MatchPageData:
    """Extract all visible data from a match detail page.

    Args:
        page: a Playwright Page already navigated to a match detail URL
            (e.g. ``/en/line/basketball/352015844-...``).

    Returns:
        A :class:`MatchPageData` with whatever the browser rendered.
        Best-effort — never raises; errors are recorded in
        ``extraction_errors``.
    """
    data = MatchPageData(url=page.url)
    try:
        raw = await page.evaluate(_MATCH_PAGE_SCRIPT)
    except Exception as exc:
        logger.warning("Match page script evaluate failed: %s", exc)
        data.extraction_errors.append(f"evaluate failed: {exc}")
        return data

    try:
        data.raw_html_size = len(await page.content())
    except Exception:
        pass

    # Map raw JS result onto dataclass fields.
    if isinstance(raw, dict):
        sb = raw.get("scoreboard") or {}
        data.scoreboard = {
            k: sb.get(k) for k in [
                "home_team", "away_team", "home_score", "away_score",
                "competition", "sport", "status", "minute",
                "period", "start_time", "event_id", "venue",
            ]
        }

        data.period_scores = [
            {k: p.get(k) for k in ("period_name", "home_score", "away_score", "period_type")}
            for p in (raw.get("period_scores") or [])
        ]

        data.statistics = [
            {k: s.get(k) for k in ("label", "home_value", "away_value")}
            for s in (raw.get("statistics") or [])
        ]

        data.market_groups = raw.get("market_groups") or []
        data.h2h_sections = raw.get("h2h_sections") or []
        data.summary_info = raw.get("summary_info") or {}

    # Log basic stats.
    logger.info(
        "Match page extracted: url=%s scoreboard=%s periods=%d stats=%d "
        "market_groups=%d h2h=%d html=%db",
        data.url,
        data.scoreboard.get("home_team", "?") + " vs " + data.scoreboard.get("away_team", "?"),
        len(data.period_scores),
        len(data.statistics),
        len(data.market_groups),
        len(data.h2h_sections),
        data.raw_html_size,
    )

    return data


async def capture_match_page_context(
    page: Any,
    *,
    screenshot_path: Optional[str] = None,
    html_path: Optional[str] = None,
    wait_for_hover_seconds: int = 0,
) -> Dict[str, Any]:
    """Full-context capture: UI data + API responses + screenshot + HTML.

    Similar to :func:`extract_match_page` but also registers a Playwright
    response listener to capture ALL API responses the page triggers, and
    optionally hovers team names to trigger H2H popups.

    Args:
        page: a Playwright Page — will be navigated to the match URL.
        screenshot_path: optional path to save a full-page screenshot.
        html_path: optional path to save the rendered HTML.
        wait_for_hover_seconds: if >0, hover each team name and wait this
            many seconds for H2H popups to appear.

    Returns:
        dict with keys: ``ui_data``, ``api_responses``, ``screenshot``,
        ``html_size``.
    """
    all_responses: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    async def on_response(response):
        u = response.url
        # Only capture from the same domain (data endpoints)
        if not u.startswith(page.url.split("/")[0]):
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
        all_responses.append({
            "url": u,
            "status": response.status,
            "method": response.request.method,
            "body": body[:60000],  # cap at 60KB
        })

    page.on("response", lambda r: asyncio.create_task(on_response(r)))

    # Navigate to the match page
    await page.goto(page.url, wait_until="load", timeout=60000)

    # Wait for SPA hydration
    await asyncio.sleep(8)

    # Extract UI data
    ui_data = await extract_match_page(page)

    # Hover team names if requested
    if wait_for_hover_seconds > 0:
        team_names = list({
            ui_data.scoreboard.get("home_team", ""),
            ui_data.scoreboard.get("away_team", ""),
        })
        team_names = [t for t in team_names if t]
        for name in team_names:
            try:
                el = await page.query_selector(f':has-text("{name}")')
                if el:
                    await el.hover(timeout=5000, force=True)
                    await asyncio.sleep(wait_for_hover_seconds)
            except Exception:
                pass

    # Screenshot
    if screenshot_path:
        try:
            await page.screenshot(path=screenshot_path, full_page=True)
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)

    # HTML
    html_size = 0
    if html_path:
        try:
            html = await page.content()
            html_size = len(html)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as exc:
            logger.warning("HTML save failed: %s", exc)

    return {
        "ui_data": ui_data.to_dict(),
        "api_responses": all_responses,
        "screenshot_path": screenshot_path,
        "html_size": html_size or ui_data.raw_html_size,
    }
