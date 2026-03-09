# Scheduled Basketball - Standings Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/?mid=xM2EzBO7
**Date Collected:** 2026-02-21
**Country:** Austria
**League:** Superliga - Losers stage - Round 2
**Match:** St. Polten vs Furstenfeld

## HTML

```html
<div class="filterOver filterOver--table"><div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist"><a data-analytics-element="SCN_TAB" data-analytics-alias="stats-detail_table" class="active" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/standings/?mid=xM2EzBO7" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Standings</button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="stats-detail_form" class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Form</button></a></div></div>
```

## Expected Secondary Tabs

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Standings | League standings table | /standings/standings/ |
| Form | Team form comparison | /standings/form/ |

---

## Tertiary Tabs by Secondary Tab

### Standings > Tertiary

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall standings | /standings/standings/overall/ |
| Home | Home standings | /standings/standings/home/ |
| Away | Away standings | /standings/standings/away/ |

### Form > Tertiary

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall form | /standings/form/overall/ |
| Home | Home form | /standings/form/home/ |
| Away | Away form | /standings/form/away/ |

### Form > Overall > Filter Tabs (4th Level)

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| 5 | Show top 5 teams | /standings/form/overall/5/ |
| 10 | Show top 10 teams | /standings/form/overall/10/ |
| 15 | Show top 15 teams | /standings/form/overall/15/ |
| 20 | Show top 20 teams | /standings/form/overall/20/ |
| 25 | Show top 25 teams | /standings/form/overall/25/ |

---

## Notes

### General
- Pre-match standings show current table
- Availability depends on league type
- Form tab has filter sub-tabs to limit displayed teams (5, 10, 15, 20, 25)

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="active"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Tertiary Container:** `div[data-testid="wcl-tabs"][data-type="tertiary"]`

### Match State Differences
- **Live:** Standings update in real-time during match
- **Scheduled:** Shows complete league standings
- **Finished:** Shows final standings after match completion
