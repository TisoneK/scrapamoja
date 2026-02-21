# Live Basketball - H2H Tab - Secondary Tabs

**Source URL:** https://www.flashscore.com/match/basketball/hana-bank-women-s-basketball-team-23WBYlF8/s-birds-6aq77K10/h2h/overall/?mid=pz9bb7F8
**Date Collected:** 2026-02-20
**Country:** South Korea
**League:** WKBL Women
**Match:** Hana Bank W vs S-Birds W

## HTML

```html
<div class="filterOver filterOver--indent"><div data-testid="wcl-tabs" data-type="secondary" class="wcl-tabs_LqJs2 wcl-tabsSecondary_Q2jLn" role="tablist"><a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_0_h2h" title="Overall" class="active" href="/match/basketball/hana-bank-women-s-basketball-team-23WBYlF8/s-birds-6aq77K10/h2h/overall/?mid=pz9bb7F8" data-discover="true" aria-current="page"><button data-testid="wcl-tab" data-selected="true" class="wcl-tab_GS7ig wcl-tabSelected_rHdTM" role="tab">Overall</button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_1_h2h" title="Hana Bank - Home" class="" href="/match/basketball/hana-bank-women-s-basketball-team-23WBYlF8/s-birds-6aq77K10/h2h/home/?mid=pz9bb7F8" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">Hana Bank - Home</button></a><a data-analytics-element="SCN_TAB" data-analytics-alias="head-2-head_2_h2h" title="S-Birds - Away" class="" href="/match/basketball/hana-bank-women-s-basketball-team-23WBYlF8/s-birds-6aq77K10/h2h/away/?mid=pz9bb7F8" data-discover="true"><button data-testid="wcl-tab" data-selected="false" class="wcl-tab_GS7ig" role="tab">S-Birds - Away</button></a></div></div>
```

## Expected Secondary Tabs

| Tab | Description | URL Pattern |
|-----|-------------|-------------|
| Overall | Default H2H view showing all matches | /h2h/overall/ |
| Hana Bank - Home | Head-to-head stats when Hana Bank is home team | /h2h/home/ |
| S-Birds - Away | Head-to-head stats when S-Birds is away team | /h2h/away/ |

## Notes
- H2H during live shows current match in context
- Secondary tabs filter H2H data by home/away team perspective
- Each tab shows historical matches between the two teams
- Selector: `data-testid="wcl-tabs" data-type="secondary"`
