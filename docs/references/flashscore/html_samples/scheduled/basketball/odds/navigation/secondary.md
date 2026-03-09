# Scheduled Basketball - Odds Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/cleveland-state-xC0O4mib/wright-state-zRE4XnDt/odds/home-away/ft-including-ot/?mid=nVL9t0uB
**Date Collected:** 2026-02-15
**Country:** USA
**League:** NCAA
**Match:** Cleveland State vs Wright State

---

## Summary

This HTML sample captures the **secondary navigation tabs** under the Odds primary tab for a scheduled basketball match on Flashscore. These tabs allow users to navigate between different betting markets.

### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| Home/Away | `moneyline` | `/match/basketball/.../odds/home-away/?mid=nVL9t0uB` | Yes |
| 1X2 | `1x2` | `/match/basketball/.../odds/1x2-odds/?mid=nVL9t0uB` | No |
| Over/Under | `under-over` | `/match/basketball/.../odds/over-under/?mid=nVL9t0uB` | No |
| Asian handicap | `asian-handicap` | `/match/basketball/.../odds/asian-handicap/?mid=nVL9t0uB` | No |
| Odd/Even | `oddeven` | `/match/basketball/.../odds/odd-even/?mid=nVL9t0uB` | No |

---

## HTML

```html
<div class="filterOver filterOver--indent">
  <div data-testid="wcl-tabs" 
       data-type="secondary" 
       class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" 
       role="tablist">
    
    <!-- Home/Away Secondary Tab (Active) -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="moneyline" 
       title="Home/Away" 
       class="active" 
       href="/match/basketball/cleveland-state-xC0O4mib/wright-state-zRE4XnDt/odds/home-away/?mid=nVL9t0uB" 
       data-discover="true" 
       aria-current="page">
      <button data-testid="wcl-tab" 
              data-selected="true" 
              class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" 
              role="tab">Home/Away </button>
    </a>
    
    <!-- 1X2 Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="1x2" 
       title="1X2" 
       class="" 
       href="/match/basketball/cleveland-state-xC0O4mib/wright-state-zRE4XnDt/odds/1x2-odds/?mid=nVL9t0uB" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">1X2 </button>
    </a>
    
    <!-- Over/Under Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="under-over" 
       title="Over/Under" 
       class="" 
       href="/match/basketball/cleveland-state-xC0O4mib/wright-state-zRE4XnDt/odds/over-under/?mid=nVL9t0uB" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Over/Under </button>
    </a>
    
    <!-- Asian handicap Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="asian-handicap" 
       title="Asian handicap" 
       class="" 
       href="/match/basketball/cleveland-state-xC0O4mib/wright-state-zRE4XnDt/odds/asian-handicap/?mid=nVL9t0uB" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Asian handicap </button>
    </a>
    
    <!-- Odd/Even Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="oddeven" 
       title="Odd/Even" 
       class="" 
       href="/match/basketball/cleveland-state-xC0O4mib/wright-state-zRE4XnDt/odds/odd-even/?mid=nVL9t0uB" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Odd/Even </button>
    </a>
    
  </div>
</div>
```

---

## Notes

### General
- Secondary tabs appear under the Odds primary tab
- These allow navigation between different betting market types
- All markets are available for scheduled matches

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

### Available Betting Markets
| Tab | data-analytics-alias | Purpose |
|-----|---------------------|---------|
| Home/Away | `moneyline` | Bet on which team wins (moneyline) |
| 1X2 | `1x2` | Traditional 1X2 betting (Home win / Draw / Away win) |
| Over/Under | `under-over` | Bet on whether total points will be over or under a line |
| Asian handicap | `asian-handicap` | Asian handicap betting lines |
| Odd/Even | `oddeven` | Bet on whether total points will be odd or even |

### Match State Differences
- **Scheduled:** All betting markets typically available with pre-match odds
- **Live:** Odds update in real-time; some markets may be suspended during play
- **Finished:** Odds markets may be limited or unavailable as match is complete
