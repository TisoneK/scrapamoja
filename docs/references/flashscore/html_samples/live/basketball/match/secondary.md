# Live Basketball - Match Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/melilla-Ac45vn4k/obradoiro-cab-YRPggwMM/?mid=4Gywf4Ji
**Date Collected:** 2026-02-15
**Country:** Spain
**League:** Primera FEB - Round 21
**Match:** Melilla vs Obradoiro CAB

---

## Summary

This HTML sample captures the **secondary navigation tabs** under the Match primary tab for a live basketball match on Flashscore. The match is in a "live" state (currently in progress), which affects the available secondary tabs.

### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| Summary | `match-summary` | `/match/basketball/.../?mid=4Gywf4Ji` | Yes |
| Lineups | `lineups` | `/match/basketball/.../summary/lineups/?mid=4Gywf4Ji` | No |
| Match History | `match-history` | `/match/basketball/.../summary/point-by-point/?mid=4Gywf4Ji` | No |

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
       href="/match/basketball/melilla-Ac45vn4k/obradoiro-cab-YRPggwMM/?mid=4Gywf4Ji" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="true" 
              class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" 
              role="tab">Summary</button>
    </a>
    
    <!-- Lineups Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="lineups" 
       class="" 
       href="/match/basketball/melilla-Ac45vn4k/obradoiro-cab-YRPggwMM/summary/lineups/?mid=4Gywf4Ji" 
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
       href="/match/basketball/melilla-Ac45vn4k/obradoiro-cab-YRPggwMM/summary/point-by-point/?mid=4Gywf4Ji" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="false" 
              class="wcl-tab_GS7ig" 
              role="tab">Match History</button>
    </a>
    
  </div>
</div>
```

---

## Notes

### General
- Secondary tabs appear under the primary Match tab
- For live matches, tabs focus on real-time data and match progress
- Available tabs may vary based on match importance and data availability

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

### Available Secondary Tabs for Live Matches
| Tab | data-analytics-alias | Purpose |
|-----|---------------------|---------|
| Summary | `match-summary` | Live score, current game state, play-by-play |
| Lineups | `lineups` | Team lineups and player information |
| Match History | `match-history` | Point-by-point progression, key moments |

### Match State Differences
- **Scheduled:** Only Summary and Match History tabs available
- **Live:** Additional tabs appear (Lineups, real-time statistics)
- **Finished:** Full complement of tabs including final statistics and analysis