# Live Basketball - Odds Tab - Secondary Tabs

**Source URL:** *(Add URL here)*
**Date Collected:** *(Add date here)*
**Country:** *(Add country here)*
**League:** *(Add league here)*
**Match:** *(Add match teams here)*

---

## HTML

```html
<!-- Paste secondary tabs HTML under Odds primary tab here -->
<!-- Navigate to Odds tab and look for sub-tabs during live match -->
<!-- Common sub-tabs: 1X2, Over/Under, Handicap, Asian Handicap, etc. -->
```

---

## Expected Secondary Tabs

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| *(To be documented)* | | |

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
