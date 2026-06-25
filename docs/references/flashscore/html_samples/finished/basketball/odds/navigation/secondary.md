# Finished Basketball - Odds Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/?mid=QVFOnTYi
**Date Collected:** 2026-02-16
**Country:** France
**League:** LNB - Round 20
**Match:** Saint Quentin vs Paris

---

## HTML

```html
<div class="filterOver filterOver--indent">
  <div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist">
    <a data-analytics-element="SCN_TAB" data-analytics-alias="moneyline" title="Home/Away" class="active" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/odds/home-away/?mid=QVFOnTYi" data-discover="true" aria-current="page">
      <button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Home/Away </button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="1x2" title="1X2" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/odds/1x2-odds/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">1X2 </button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="under-over" title="Over/Under" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/odds/over-under/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Over/Under </button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="asian-handicap" title="Asian handicap" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/odds/asian-handicap/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Asian handicap </button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="ht-ft" title="Half Time/Full Time" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/odds/ht-ft/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Half Time/Full Time </button>
    </a>
    <a data-analytics-element="SCN_TAB" data-analytics-alias="oddeven" title="Odd/Even" class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/odds/odd-even/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Odd/Even </button>
    </a>
  </div>
</div>
```

---

## Secondary Tabs

| Tab | URL Pattern | Analytics Alias | Description |
|-----|-------------|-----------------|-------------|
| Home/Away | `/odds/home-away/` | `moneyline` | Moneyline betting (which team wins) |
| 1X2 | `/odds/1x2-odds/` | `1x2` | Traditional 1X2 betting (Home/Draw/Away) |
| Over/Under | `/odds/over-under/` | `under-over` | Total points over/under betting |
| Asian handicap | `/odds/asian-handicap/` | `asian-handicap` | Asian handicap betting lines |
| Half Time/Full Time | `/odds/ht-ft/` | `ht-ft` | Half time / full time result betting |
| Odd/Even | `/odds/odd-even/` | `oddeven` | Odd or even total points betting |

---

## Selector Reference

- **Container:** `div.filterOver.filterOver--indent`
- **Tabs Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Button:** `button[data-testid="wcl-tab"]`
- **Selected Tab:** `button[data-selected="true"]`
- **Tab Link:** `a[data-analytics-element="SCN_TAB"]`

---

## URL Structure

```
/match/basketball/{home-team-slug}-{home-id}/{away-team-slug}-{away-id}/odds/{market-type}/?mid={match-id}
```

**Market Types:**
- `home-away` - Home/Away (moneyline)
- `1x2-odds` - 1X2
- `over-under` - Over/Under
- `asian-handicap` - Asian handicap
- `ht-ft` - Half Time/Full Time
- `odd-even` - Odd/Even

---

## Notes

### General
- Secondary tabs appear under the Odds primary tab
- These allow navigation between different betting market types
- For finished matches, odds shown are archived/closing odds

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="active"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Match State Differences
- **Finished:** Shows archived/closing odds for all markets
- **Scheduled:** All betting markets typically available with current odds
- **Live:** Odds update in real-time; some markets may be suspended
