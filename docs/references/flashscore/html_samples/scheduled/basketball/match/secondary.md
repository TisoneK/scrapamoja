# Scheduled Basketball Match - Match Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/derthona-tortona-0OZBANVT/sassari-CQMh2ve4/?mid=Q1pAmBdc  
**Date Collected:** 2026-02-15  
**Country:** Italy  
**League:** Lega A - Round 20  
**Match:** Sassari vs Tortona  

---

## Summary

This HTML sample captures the **secondary navigation tabs** under the Match primary tab for a scheduled basketball match on Flashscore. The match is in a "scheduled" state, which limits the available secondary tabs to preview-focused content.

---

## HTML

```html
<div class="detailOver">
  <div data-testid="wcl-tabs" 
       data-type="secondary" 
       class="wcl-tabs_LqJs2 wcl-tabsSecondary_Zzfe6" 
       role="tablist">
    
    <!-- Summary Secondary Tab (Active) -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-summary" 
       aria-current="page" 
       class="selected" 
       href="/match/basketball/derthona-tortona-0OZBANVT/sassari-CQMh2ve4/?mid=Q1pAmBdc" 
       data-discover="true">
      <button data-testid="wcl-tab" 
              data-selected="true" 
              class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" 
              role="tab">Summary</button>
    </a>
    
    <!-- Match History Secondary Tab -->
    <a data-analytics-element="SCN_TAB" 
       data-analytics-alias="match-history" 
       class="" 
       href="/match/basketball/derthona-tortona-0OZBANVT/sassari-CQMh2ve4/match-history/?mid=Q1pAmBdc" 
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
- For scheduled matches, only preview-related tabs are available
- No live statistics or real-time data tabs are present

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

### Available Secondary Tabs for Scheduled Matches
| Tab | data-analytics-alias | Purpose |
|-----|---------------------|---------|
| Summary | `match-summary` | Match preview and basic information |
| Match History | `match-history` | Head-to-head historical data |

### Match State Differences
- **Scheduled:** Only Summary and Match History tabs available
- **Live:** Additional tabs appear (Live Score, Statistics, Lineups)
- **Finished:** Full complement of tabs including final statistics