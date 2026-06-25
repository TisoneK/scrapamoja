# Finished Basketball - Match Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/?mid=QVFOnTYi
**Date Collected:** 2026-02-15
**Country:** France
**League:** LNB - Round 20
**Match:** Paris vs Saint Quentin

---

## Summary

This HTML sample captures the **secondary navigation tabs** under the Match primary tab for a finished basketball match on Flashscore. The match is in a "finished" state (completed), which affects the available secondary tabs.

### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| Summary | `match-summary` | `/match/basketball/.../?mid=QVFOnTYi` | Yes |
| Player stats | `player-statistics` | `/match/basketball/.../summary/player-stats/?mid=QVFOnTYi` | No |
| Stats | `match-statistics` | `/match/basketball/.../summary/stats/?mid=QVFOnTYi` | No |
| Lineups | `lineups` | `/match/basketball/.../summary/lineups/?mid=QVFOnTYi` | No |
| Match History | `match-history` | `/match/basketball/.../summary/point-by-point/?mid=QVFOnTYi` | No |

---

## HTML

```html
<div class="filterOver filterOver--indent">
  <div data-testid="wcl-tabs" 
       data-type="secondary" 
       class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" 
       role="tablist">
    
    <!-- Summary Secondary Tab (Active) -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-summary" 
       aria-current="page" 
       class="selected" 
       href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/?mid=QVFOnTYi" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="true" 
              class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" 
              role="tab">Summary</button>
    </a>
    
    <!-- Player stats Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="player-statistics" 
       class="" 
       href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/summary/player-stats/?mid=QVFOnTYi" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Player stats</button>
    </a>
    
    <!-- Stats Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-statistics" 
       class="" 
       href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/summary/stats/?mid=QVFOnTYi" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Stats</button>
    </a>
    
    <!-- Lineups Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="lineups" 
       class="" 
       href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/summary/lineups/?mid=QVFOnTYi" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Lineups</button>
    </a>
    
    <!-- Match History Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-history" 
       class="" 
       href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/summary/point-by-point/?mid=QVFOnTYi" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Match History</button>
    </a>
    
  </div>
</div>

---

## Notes
### General
- Secondary tabs appear under the primary Match tab
- For finished matches, tabs focus on final statistics and match analysis
- All tabs are available with complete post-match data

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active secondary tab
- `class="selected"` on the `<a>` element indicates the active secondary tab
- `data-selected="true"` on the `<button>` element indicates the active secondary tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active secondary tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Secondary Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Secondary Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Active Secondary Tab:** `a[aria-current="page"]` or `button[data-selected="true"]`

### Available Secondary Tabs for Finished Matches
| Tab | data-analytics-alias | Purpose |
|-----|---------------------|---------|
| Summary | `match-summary` | Final score, match summary, key statistics |
| Player stats | `player-statistics` | Individual player performance statistics |
| Stats | `match-statistics` | Team and match statistical breakdowns |
| Lineups | `lineups` | Final team lineups and substitutions |
| Match History | `match-history` | Point-by-point progression, key moments |

### Match State Differences
- **Scheduled:** Only Summary and Match History tabs available
- **Live:** Limited tabs (Summary, Lineups, Match History) with real-time data
- **Finished:** Full complement of tabs with complete post-match statistics