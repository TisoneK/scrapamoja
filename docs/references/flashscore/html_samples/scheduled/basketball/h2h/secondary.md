# Scheduled Basketball - H2H Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/?mid=xM2EzBO7
**Date Collected:** 2026-02-21
**Country:** Austria
**League:** Superliga - Losers stage - Round 2
**Match:** St. Polten vs Furstenfeld

## HTML

```html
<div class="filterOver filterOver--indent"><div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist"><a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_0_h2h" title="Overall" class="active" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/h2h/overall/?mid=xM2EzBO7" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_1_h2h" title="St. Polten - Home" class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/h2h/home/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">St. Polten - Home</button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_2_h2h" title="Furstenfeld - Away" class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/h2h/away/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Furstenfeld - Away</button></a></div></div>
```

## Expected Secondary Tabs

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall H2H statistics | /h2h/overall/ |
| St. Polten - Home | St. Polten home games | /h2h/home/ |
| Furstenfeld - Away | Furstenfeld away games | /h2h/away/ |

---

## Notes

### General
- Pre-match H2H shows historical data
- Useful for pre-match analysis
- H2H tabs filter by venue (Home team home games, Away team away games)

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="active"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Active Tab:** `a[aria-current="page"]` or `button[data-selected="true"]`

### Match State Differences
- **Live:** H2H updates with recent head-to-head history
- **Scheduled:** Shows complete historical H2H data
- **Finished:** Shows final H2H statistics after match completion
