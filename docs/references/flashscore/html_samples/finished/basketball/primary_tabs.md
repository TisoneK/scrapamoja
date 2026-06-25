# Finished Basketball Match - Primary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/detroit-titans-Y7s9JydR/youngstown-state-6eUTT4C5/?mid=8pAIvvAN
**Date Collected:** 2026-02-15
**Country:** USA
**League:** NCAA
**Match:** Detroit vs Youngstown State

---

## Summary

This HTML sample captures the **primary navigation tabs** for a finished basketball match on Flashscore. The match is in a "finished" state (completed), which affects the available secondary tabs.

### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| Summary | `match-summary` | `/match/basketball/.../?mid=8pAIvvAN` | Yes |
| Odds | `odds-comparison` | `/match/basketball/.../odds/?mid=8pAIvvAN` | No |
| H2H | `h2h` | `/match/basketball/.../h2h/?mid=8pAIvvAN` | No |
| Standings | `stats-detail` | `/match/basketball/.../standings/?mid=8pAIvvAN` | No |

---

## HTML

```html
<div class="detailOver">
  <div data-testid="wcl-tabs" 
       data-type="primary" 
       class="wcl-tabs_LqJs2 wcl-tabsPrimary_Zzfe6" 
       role="tablist">
    
    <!-- Summary Tab (Active) -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-summary" 
       aria-current="page" 
       class="selected" 
       href="/match/basketball/detroit-titans-Y7s9JydR/youngstown-state-6eUTT4C5/?mid=8pAIvvAN" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="true" 
              class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" 
              role="tab">Summary</button>
    </a>
    
    <!-- Odds Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="odds-comparison" 
       class="" 
       href="/match/basketball/detroit-titans-Y7s9JydR/youngstown-state-6eUTT4C5/odds/?mid=8pAIvvAN" 
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
       href="/match/basketball/detroit-titans-Y7s9JydR/youngstown-state-6eUTT4C5/h2h/?mid=8pAIvvAN" 
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
       href="/match/basketball/detroit-titans-Y7s9JydR/youngstown-state-6eUTT4C5/standings/?mid=8pAIvvAN" 
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
- Primary tabs are the top-level navigation (Summary, Odds, H2H, Standings)
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
- **Scheduled:** Summary tab shows match preview info; limited secondary tabs
- **Live:** Summary tab shows live score and real-time updates; additional secondary tabs available (Player Stats, Match Stats, Lineups)
- **Finished:** Summary tab shows final score and match statistics
