# Live Basketball - Standings Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/asker-6JCGbW0h/gimle-rRSydUpB/standings/standings/overall/?mid=McJt1SX9
**Date Collected:** 2026-02-21
**Country:** Norway
**League:** BLNO
**Match:** Asker vs Gimle

## HTML

```html
<div class="filterOver filterOver--table"><div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist"><a data-analytics-element="SCN_TAB" data-analytics-alias="stats-detail_table" class="active" href="/match/basketball/asker-6JCGbW0h/gimle-rRSydUpB/standings/standings/?mid=McJt1SX9" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Standings</button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="stats-detail_form" class="" href="/match/basketball/asker-6JCGbW0h/gimle-rRSydUpB/standings/form/?mid=McJt1SX9" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Form</button></a></div></div>
```

## Expected Secondary Tabs

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Standings | League standings table | /standings/standings/ |
| Form | Team form comparison | /standings/form/ |

---

## Tertiary Tabs by Secondary Tab

### Standings > Tertiary

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall standings | /standings/standings/overall/ |
| Home | Home standings | /standings/standings/home/ |
| Away | Away standings | /standings/standings/away/ |

### Form > Tertiary

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall form | /standings/form/overall/ |
| Home | Home form | /standings/form/home/ |
| Away | Away form | /standings/form/away/ |

---

## Notes

### General
- Live standings may update in real-time during match
- Availability depends on league type

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="active"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Tertiary Container:** `div[data-testid="wcl-tabs"][data-type="tertiary"]`

### Match State Differences
- **Live:** Standings update in real-time during match
- **Scheduled:** Shows complete league standings
- **Finished:** Shows final standings after match completion
