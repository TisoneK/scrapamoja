# Finished Basketball - Standings Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/?mid=QVFOnTYi
**Date Collected:** 2026-02-16
**Country:** France
**League:** LNB - Round 20
**Match:** Saint Quentin vs Paris

## HTML

```html
<div class="filterOver filterOver--table">
  <div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist">
    <a data-analytics-element="SCN_TAB" data-analytics-alias="stats-detail_table" class="active" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/standings/?mid=QVFOnTYi" data-discover="true" aria-current="page">
      <button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Standings</button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="stats-detail_form" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/form/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Form</button>
    </a>
  </div>
</div>
```

## Secondary Tabs

| Tab | URL Pattern | Analytics Alias | Description |
|-----|-------------|-----------------|-------------|
| Standings | `/standings/standings/` | `stats-detail_table` | League table with team rankings |
| Form | `/standings/form/` | `stats-detail_form` | Team form guide (recent results) |

## Selector Reference

- **Container:** `div.filterOver.filterOver--table`
- **Tabs Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Button:** `button[data-testid="wcl-tab"]`
- **Selected Tab:** `button[data-selected="true"]`
- **Tab Link:** `a[data-analytics-element="SCN_TAB"]`

## URL Structure

```
/match/basketball/{home-team-slug}-{home-id}/{away-team-slug}-{away-id}/standings/{view-type}/?mid={match-id}
```

**View Types:**
- `standings` - League table
- `form` - Team form guide

## Notes

- Standings availability depends on league type
- Tournament/bracket matches may not have standings
- The Standings tab shows the league table with team rankings
- The Form tab shows recent match results for each team
- Container uses `filterOver--table` class instead of `filterOver--indent`
