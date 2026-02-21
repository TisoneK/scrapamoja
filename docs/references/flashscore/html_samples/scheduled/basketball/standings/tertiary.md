# Scheduled Basketball - Standings Tab - Tertiary Tabs

**Secondary Tab:** Standings (all secondary tabs)
**Source URL:** https://www.flashscore.com/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/?mid=xM2EzBO7
**Date Collected:** 2026-02-21
**Country:** Austria
**League:** Superliga - Losers stage - Round 2
**Match:** St. Polten vs Furstenfeld

## HTML

### Standings Tertiary Tabs
```html
<div class="subFilterOver"><div data-testid="wcl-tabs" data-type="tertiary" class="wcl-tabs_LqJs2 wcl-tabsTertiary_wjP-c" role="tablist"><a class="active" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/standings/overall/?mid=xM2EzBO7" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/standings/home/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Home</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/standings/away/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Away</button></a></div></div>
```

### Form Tertiary Tabs
```html
<div class="subFilterOver"><div data-testid="wcl-tabs" data-type="tertiary" class="wcl-tabs_LqJs2 wcl-tabsTertiary_wjP-c" role="tablist"><a class="active" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/overall/?mid=xM2EzBO7" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/home/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Home</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/away/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Away</button></a></div></div>
```

### Form > Overall Filter Tabs (4th Level)
```html
<div class="subFilterOver"><div data-testid="wcl-tabs" data-type="tertiary" class="wcl-tabs_LqJs2 wcl-tabsTertiary_wjP-c" role="tablist"><a class="active" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/overall/5/?mid=xM2EzBO7" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">5</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/overall/10/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">10</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/overall/15/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">15</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/overall/20/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">20</button></a><a class="" href="/match/basketball/furstenfeld-0fZ1Ela2/st-polten-nFXVDSTE/standings/form/overall/25/?mid=xM2EzBO7" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">25</button></a></div></div>
```

---

## Tertiary Structure by Secondary Tab

### Standings > Tertiary

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall league standings | /standings/standings/overall/ |
| Home | Home standings only | /standings/standings/home/ |
| Away | Away standings only | /standings/standings/away/ |

### Form > Tertiary

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Overall team form | /standings/form/overall/ |
| Home | Home team form | /standings/form/home/ |
| Away | Away team form | /standings/form/away/ |

### Form > Overall > Filter Tabs (4th Level)

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| 5 | Show top 5 teams | /standings/form/overall/5/ |
| 10 | Show top 10 teams | /standings/form/overall/10/ |
| 15 | Show top 15 teams | /standings/form/overall/15/ |
| 20 | Show top 20 teams | /standings/form/overall/20/ |
| 25 | Show top 25 teams | /standings/form/overall/25/ |

---

## Notes

### General
- Pre-match standings show current table
- Both Standings and Form secondary tabs have tertiary structure (Overall, Home, Away)
- Form tab has additional filter sub-tabs to limit displayed teams (5, 10, 15, 20, 25)
- The filter numbers indicate how many teams to show in the form table

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
- **Live:** Standings update in real-time during match
- **Scheduled:** Shows complete league standings
- **Finished:** Shows final standings after match completion
