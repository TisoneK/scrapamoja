# Live Basketball Match - Primary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/imortal-jeG09eEq/portimonense-OddWoQk3/?mid=Q7DBkfOj
**Date Collected:** 2026-02-15
**Country:** Portugal
**League:** Proliga - Winners stage - Round 4
**Match:** Imortal B vs Portimonense

---

## Summary

This HTML sample captures the **primary navigation tabs** for a live basketball match on Flashscore. The match is in a "live" state (currently in progress), which affects the available secondary tabs.

### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| Match | `match-summary` | `/match/basketball/.../?mid=Q7DBkfOj` | Yes |
| Odds | `odds-comparison` | `/match/basketball/.../odds/?mid=Q7DBkfOj` | No |
| H2H | `h2h` | `/match/basketball/.../h2h/?mid=Q7DBkfOj` | No |
| Standings | `stats-detail` | `/match/basketball/.../standings/?mid=Q7DBkfOj` | No |

---

## HTML

```html
<div class="detailOver">
  <div data-testid="wcl-tabs" 
       data-type="primary" 
       class="wcl-tabs_LqJs2 wcl-tabsPrimary_Zzfe6" 
       role="tablist">
    
    <!-- Match Tab (Active) -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-summary" 
       aria-current="page" 
       class="selected" 
       href="/match/basketball/imortal-jeG09eEq/portimonense-OddWoQk3/?mid=Q7DBkfOj" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="true" 
              class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" 
              role="tab">Match</button>
    </a>
    
    <!-- Odds Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="odds-comparison" 
       class="" 
       href="/match/basketball/imortal-jeG09eEq/portimonense-OddWoQk3/odds/?mid=Q7DBkfOj" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Odds</button>
    </a>
    
    <!-- H2H Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="h2h" 
       class="" 
       href="/match/basketball/imortal-jeG09eEq/portimonense-OddWoQk3/h2h/?mid=Q7DBkfOj" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">H2H</button>
    </a>
    
    <!-- Standings Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="stats-detail" 
       class="" 
       href="/match/basketball/imortal-jeG09eEq/portimonense-OddWoQk3/standings/?mid=Q7DBkfOj" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Standings</button>
    </a>
    
  </div>
</div>
```

---

## Notes

### General
- Primary tabs are the top-level navigation (Match, Odds, H2H, Standings)
- These appear on all match pages regardless of state (scheduled/live/finished)

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="selected"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="primary"]`
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Active Tab:** `a[aria-current="page"]` or `button[data-selected="true"]`

### Match State Differences
- **Scheduled:** Match tab shows match preview info; limited secondary tabs
- **Live:** Match tab shows live score and real-time updates; additional secondary tabs available (Player Stats, Match Stats, Lineups)
- **Finished:** Match tab shows final score and match statistics
