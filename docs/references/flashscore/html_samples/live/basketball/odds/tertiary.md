# Live Basketball - Odds Tab - Tertiary Tabs

**Secondary Tab:** *(Specify which secondary tab you're documenting: e.g., Home/Away, 1X2, Over/Under)*
**Source URL:** *(Add URL here)*
**Date Collected:** *(Add date here)*
**Country:** *(Add country here)*
**League:** *(Add league here)*
**Match:** *(Add match teams here)*

---

## HTML

```html
<!-- Paste tertiary tabs HTML under each Odds secondary tab here -->
<!-- These are sub-tabs within each odds market type during live match -->
<!-- Copy separate HTML blocks for each secondary tab's tertiary structure -->
```

---

## Tertiary Structure by Secondary Tab

### Home/Away > Tertiary
*(Document any sub-tabs within Home/Away market)*

### 1X2 > Tertiary
*(Document any sub-tabs within 1X2 market)*

### Over/Under > Tertiary
*(Document any sub-tabs within Over/Under market)*

### Asian handicap > Tertiary
*(Document any sub-tabs within Asian handicap market)*

### Double chance > Tertiary
*(Document any sub-tabs within Double chance market)*

### Half Time/Full Time > Tertiary
*(Document any sub-tabs within Half Time/Full Time market)*

### Odd/Even > Tertiary
*(Document any sub-tabs within Odd/Even market)*

---

## Notes

### General
- Tertiary tabs appear under secondary tabs
- Each secondary betting market has its own unique tertiary options

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="active"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="tertiary"]`
- **Tab Links:** `a[title]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Active Tab:** `a[aria-current="page"]` or `button[data-selected="true"]`

### Match State Differences
- **Live:** Odds update in real-time; some time period options may not be available
- **Scheduled:** All tertiary options typically available
- **Finished:** Only full match and completed periods available
