# Live Basketball - Match Tab - Tertiary Tabs

**Secondary Tab:** Match (all secondary tabs)
**Source URL:** https://www.flashscore.com/match/basketball/melilla-Ac45vn4k/obradoiro-cab-YRPggwMM/?mid=4Gywf4Ji
**Date Collected:** 2026-02-15
**Country:** Spain
**League:** Primera FEB - Round 21
**Match:** Melilla vs Obradoiro CAB

---

## Notes

### Tertiary Tabs
⚠️ **No tertiary tabs exist under this secondary tab.**

The Match secondary tabs (Summary, Lineups, Match History) do not have tertiary sub-tabs for navigation. These tabs contain content (score, lineups, history) rather than further navigation options. Verified on 2026-02-15.

The navigation structure ends at the secondary level for this tab.

---

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="selected"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]` (tertiary container not present)
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`

### Match State Differences
- **Live:** Shows Summary, Lineups, Match History - no tertiary navigation
- **Scheduled:** Limited tabs available
- **Finished:** Full set of tabs with final statistics
