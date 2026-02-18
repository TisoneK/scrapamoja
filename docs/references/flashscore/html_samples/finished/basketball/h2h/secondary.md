# Finished Basketball - H2H Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/?mid=QVFOnTYi
**Date Collected:** 2026-02-16
**Country:** France
**League:** LNB - Round 20
**Match:** Saint Quentin vs Paris

## HTML

```html
<div class="filterOver filterOver--indent">
  <div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist">
    <a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_0_h2h" title="Overall" class="active" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/h2h/overall/?mid=QVFOnTYi" data-discover="true" aria-current="page">
      <button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_1_h2h" title="Saint Quentin - Home" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/h2h/home/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Saint Quentin - Home</button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_2_h2h" title="Paris - Away" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/h2h/away/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Paris - Away</button>
    </a>
  </div>
</div>
```

## Secondary Tabs

| Tab | URL Pattern | Description |
|-----|-------------|-------------|
| Overall | `/h2h/overall/` | All head-to-head matches between teams |
| Saint Quentin - Home | `/h2h/home/` | Home team's (Saint Quentin) home matches |
| Paris - Away | `/h2h/away/` | Away team's (Paris) away matches |

## Selector Reference

- **Container:** `div.filterOver.filterOver--indent`
- **Tabs Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Button:** `button[data-testid="wcl-tab"]`
- **Selected Tab:** `button[data-selected="true"]`
- **Tab Link:** `a[data-analytics-element="SCN_TAB"]`

## URL Structure

```
/match/basketball/{home-team-slug}-{home-id}/{away-team-slug}-{away-id}/h2h/{filter}/?mid={match-id}
```

**Filters:**
- `overall` - Combined H2H record
- `home` - Home team's home games
- `away` - Away team's away games

## Notes

- H2H shows head-to-head history between teams
- Tab labels are dynamically generated with team names (e.g., "Saint Quentin - Home")
- The active tab has `class="active"` on the anchor and `data-selected="true"` on the button
- Analytics attributes: `data-analytics-element="SCN_TAB"` and `data-analytics-alias="head-2-head_{n}_h2h"`
