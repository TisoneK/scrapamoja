# Finished Basketball - Standings Tab - Tertiary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/?mid=QVFOnTYi
**Date Collected:** 2026-02-16
**Country:** France
**League:** LNB - Round 20
**Match:** Saint Quentin vs Paris

---

## HTML Samples by Secondary Tab

### Standings (League Table) > Tertiary

```html
<div class="subFilterOver">
  <div data-testid="wcl-tabs" data-type="tertiary" class="wcl-tabs_LqJs2 wcl-tabsTertiary_wjP-c" role="tablist">
    <a class="active" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/standings/overall/?mid=QVFOnTYi" data-discover="true" aria-current="page">
      <button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button>
    </a>
    <a class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/standings/home/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Home</button>
    </a>
    <a class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/standings/away/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Away</button>
    </a>
  </div>
</div>
```

| Tab | URL Pattern | Description |
|-----|-------------|-------------|
| Overall | `/standings/standings/overall/` | Combined home and away standings |
| Home | `/standings/standings/home/` | Home-only standings |
| Away | `/standings/standings/away/` | Away-only standings |

---

### Form > Tertiary

```html
<div class="subFilterOver">
  <div data-testid="wcl-tabs" data-type="tertiary" class="wcl-tabs_LqJs2 wcl-tabsTertiary_wjP-c" role="tablist">
    <a class="active" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/form/overall/?mid=QVFOnTYi" data-discover="true" aria-current="page">
      <button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button>
    </a>
    <a class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/form/home/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Home</button>
    </a>
    <a class="" href="/match/basketball/paris-CdCP6AWf/saint-quentin-hESgWNT6/standings/form/away/?mid=QVFOnTYi" data-discover="true">
      <button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Away</button>
    </a>
  </div>
</div>
```

| Tab | URL Pattern | Description |
|-----|-------------|-------------|
| Overall | `/standings/form/overall/` | Combined home and away form |
| Home | `/standings/form/home/` | Home-only form |
| Away | `/standings/form/away/` | Away-only form |

---

## Tertiary Tab Summary

| Secondary Tab | Tertiary Tabs Available |
|---------------|------------------------|
| Standings (League Table) | Overall, Home, Away |
| Form | Overall, Home, Away |

---

## Selector Reference

- **Container:** `div.subFilterOver`
- **Tabs Container:** `div[data-testid="wcl-tabs"][data-type="tertiary"]`
- **Tab Button:** `button[data-testid="wcl-tab"]`
- **Selected Tab:** `button[data-selected="true"]`
- **Active Link:** `a[aria-current="page"]`

---

## URL Structure

```
/match/basketball/{home-team-slug}-{home-id}/{away-team-slug}-{away-id}/standings/{view-type}/{filter}/?mid={match-id}
```

**View Types:**
- `standings` - League table
- `form` - Team form guide

**Filters:**
- `overall` - Combined home and away
- `home` - Home-only
- `away` - Away-only

---

## Notes

- Both Standings and Form views have the same tertiary structure (Overall, Home, Away)
- The Overall tab shows combined statistics
- Home tab shows statistics for home games only
- Away tab shows statistics for away games only
- Container uses `subFilterOver` class (without `--indent` modifier)
