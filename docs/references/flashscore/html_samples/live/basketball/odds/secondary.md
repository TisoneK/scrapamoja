# Live Basketball - Odds Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/brest-Q34q9qkP/grodno-MXrXQwaf/?mid=CYA83OHP
**Date Collected:** 2026-02-21
**Country:** Belarus
**League:** Premier League
**Match:** Brest vs Grodno

---

## HTML

```html
<div class="filterOver filterOver--indent"><div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist"><a data-analytics-element="SCN_TAB" data-analytics-alias="moneyline" title="Home/Away" class="active" href="/match/basketball/pyrinto-bXU0sWvk/tapiolan-honka-KYTU1b54/odds/home-away/?mid=rVQBxJdS" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Home/Away </button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="1x2" title="1X2" class="" href="/match/basketball/pyrinto-bXU0sWvk/tapiolan-honka-KYTU1b54/odds/1x2-odds/?mid=rVQBxJdS" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">1X2 </button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="under-over" title="Over/Under" class="" href="/match/basketball/pyrinto-bXU0sWvk/tapiolan-honka-KYTU1b54/odds/over-under/?mid=rVQBxJdS" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Over/Under </button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="asian-handicap" title="Asian handicap" class="" href="/match/basketball/pyrinto-bXU0sWvk/tapiolan-honka-KYTU1b54/odds/asian-handicap/?mid=rVQBxJdS" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Asian handicap </button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="oddeven" title="Odd/Even" class="" href="/match/basketball/pyrinto-bXU0sWvk/tapiolan-honka-KYTU1b54/odds/odd-even/?mid=rVQBxJdS" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Odd/Even </button></a></div></div>
```

---

## Tertiary Tabs by Secondary Tab

### 1. Home/Away

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| FT including OT | Full Time including Overtime | /odds/home-away/ft-including-ot/ |

### 2. 1X2

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Full Time | Full time result | /odds/1x2-odds/full-time/ |
| 1st Half | First half result | /odds/1x2-odds/1st-half/ |
| 1st Qrt | First quarter result | /odds/1x2-odds/1st-qrt/ |

### 3. Over/Under

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| FT including OT | Full Time including Overtime (24 markets) | /odds/over-under/ft-including-ot/ |
| 1st Half | First half (9 markets) | /odds/over-under/1st-half/ |
| 1st Qrt | First quarter (8 markets) | /odds/over-under/1st-qrt/ |

### 4. Asian handicap

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| FT including OT | Full Time including Overtime (13 markets) | /odds/asian-handicap/ft-including-ot/ |
| 1st Half | First half (14 markets) | /odds/asian-handicap/1st-half/ |
| 1st Qrt | First quarter (8 markets) | /odds/asian-handicap/1st-qrt/ |

### 5. Odd/Even

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| FT including OT | Full Time including Overtime | /odds/odd-even/ft-including-ot/ |
| 1st Half | First half | /odds/odd-even/1st-half/ |
| 1st Qrt | First quarter | /odds/odd-even/1st-qrt/ |

---

## Notes

### General
- Secondary tabs appear under the Odds primary tab
- These allow navigation between different betting market types

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

### Betting Markets
- **Home/Away (moneyline):** Bet on which team wins
- **1X2:** Traditional 1X2 betting (Home win / Draw / Away win)
- **Over/Under:** Bet on whether total points will be over or under a line
- **Asian handicap:** Asian handicap betting lines
- **Double chance:** Bet on two of three possible outcomes
- **Half Time/Full Time:** Bet on both half time and full time result
- **Odd/Even:** Bet on whether total points will be odd or even

### Match State Differences
- **Live:** Odds update in real-time; some markets may be suspended
- **Scheduled:** All betting markets typically available
- **Finished:** Odds markets may be limited or unavailable
