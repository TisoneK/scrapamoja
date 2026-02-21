# Scheduled Basketball - Match Tab - Tertiary Tabs

**Secondary Tab:** Match (all secondary tabs)
**Source URL:** https://www.flashscore.com/match/basketball/derthona-tortona-0OZBANVT/sassari-CQMh2ve4/?mid=Q1pAmBdc
**Date Collected:** 2026-02-15
**Country:** Italy
**League:** Lega A - Round 20
**Match:** Sassari vs Tortona

---

## Notes

### Tertiary Tabs
⚠️ **No tertiary tabs exist under this secondary tab.**

The Match secondary tabs (Summary, Match History) do not have tertiary sub-tabs for navigation. These tabs contain content (preview, history) rather than further navigation options. Verified on 2026-02-15.

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
- **Scheduled:** Only Summary and Match History tabs - no tertiary navigation
- **Live:** Additional tabs (Lineups, Statistics) - no tertiary navigation
- **Finished:** Full set of tabs - no tertiary navigation
