# Flashscore HTML Samples Directory

This directory contains HTML samples for Flashscore tab navigation, organized by match state, primary tab, and tab level.

## Directory Structure

```
html_samples/
|-- README.md                           # This file
|
|-- scheduled/                          # Scheduled matches (not started)
|   |-- basketball/
|       |-- primary_tabs.md             # Primary tabs HTML
|       |-- match/
|       |   |-- navigation/
|       |   |   |-- secondary.md         # Summary, Match History
|       |   |   |-- tertiary.md
|       |   |-- content/
|       |       |-- summary/
|       |       |-- match-history/
|       |-- odds/
|       |   |-- navigation/
|       |   |   |-- secondary.md         # Home/Away, 1X2, Over/Under, Asian handicap, Odd/Even
|       |   |   |-- tertiary.md
|       |   |-- content/
|       |       |-- home-away/
|       |       |-- 1x2/
|       |       |-- over-under/
|       |       |-- asian-handicap/
|       |       |-- odd-even/
|       |-- h2h/
|       |   |-- navigation/
|       |   |   |-- secondary.md         # Overall, Home, Away
|       |   |   |-- tertiary.md
|       |   |-- content/
|       |       |-- overall/
|       |       |-- home/
|       |       |-- away/
|       |-- standings/
|           |-- navigation/
|           |   |-- secondary.md         # Standings, Form
|           |   |-- tertiary.md
|           |-- content/
|               |-- standings/
|               |-- form/
|
|-- live/                               # Live matches (in progress)
|   |-- basketball/
|       |-- primary_tabs.md
|       |-- match/
|       |   |-- navigation/
|       |   |   |-- secondary.md         # Summary, Lineups, Match History
|       |   |   |-- tertiary.md
|       |   |-- content/
|       |       |-- summary/
|       |       |-- lineups/
|       |       |-- match-history/
|       |-- odds/
|       |   |-- navigation/
|       |   |   |-- secondary.md         # Home/Away
|       |   |   |-- tertiary.md
|       |   |-- content/
|       |       |-- home-away/
|       |-- h2h/
|       |   |-- navigation/
|       |   |   |-- secondary.md         # Overall
|       |   |   |-- tertiary.md
|       |   |-- content/
|       |       |-- overall/
|       |-- standings/
|           |-- navigation/
|           |   |-- secondary.md         # Standings
|           |   |-- tertiary.md
|           |-- content/
|               |-- standings/
|
|-- finished/                           # Finished matches (completed)
    |-- basketball/
        |-- primary_tabs.md
        |-- match/
        |   |-- navigation/
        |   |   |-- secondary.md         # Summary, Player stats, Stats, Lineups, Match History
        |   |   |-- tertiary.md
        |   |-- content/
        |       |-- summary/
        |       |-- player-stats/
        |       |-- stats/
        |       |-- lineups/
        |       |-- match-history/
        |-- odds/
        |   |-- navigation/
        |   |   |-- secondary.md         # Home/Away, 1X2, Over/Under, Asian handicap, HT/FT, Odd/Even
        |   |   |-- tertiary.md
        |   |-- content/
        |       |-- home-away/
        |       |-- 1x2/
        |       |-- over-under/
        |       |-- asian-handicap/
        |       |-- half-time-full-time/
        |       |-- odd-even/
        |-- h2h/
        |   |-- navigation/
        |   |   |-- secondary.md         # Overall, Home, Away
        |   |   |-- tertiary.md
        |   |-- content/
        |       |-- overall/
        |       |-- home/
        |       |-- away/
        |-- standings/
            |-- navigation/
            |   |-- secondary.md         # Standings, Form
            |   |-- tertiary.md
            |-- content/
                |-- standings/
                |-- form/
```

## Tab Hierarchy

### Level 1: Primary Tabs
| Tab | data-analytics-alias | URL Pattern |
|-----|---------------------|-------------|
| Match | `match-summary` | `/match/basketball/{teams}/?mid={id}` |
| Odds | `odds-comparison` | `/match/basketball/{teams}/odds/?mid={id}` |
| H2H | `h2h` | `/match/basketball/{teams}/h2h/?mid={id}` |
| Standings | `stats-detail` | `/match/basketball/{teams}/standings/?mid={id}` |

### Level 2: Secondary Tabs (varies by primary tab and match state)

#### Match Tab Secondary
| Match State | Available Secondary Tabs |
|-------------|-------------------------|
| Scheduled | Summary, Match History |
| Live | Summary, Player stats, Stats, Lineups, Match History |
| Finished | Summary, Match History |

#### Other Primary Tabs
| Primary Tab | Secondary Tabs (to be documented) |
|-------------|----------------------------------|
| Odds | *(paste HTML in odds/secondary.md)* |
| H2H | *(paste HTML in h2h/secondary.md)* |
| Standings | *(paste HTML in standings/secondary.md)* |

### Level 3: Tertiary Tabs
Sub-tabs under each secondary tab. Document in `tertiary.md` files.

---

## How to Create a New Template

When creating templates for new sports or new tab combinations, follow this structure:

### Template Sections

Each template file should contain these sections:

#### 1. Header Metadata
```markdown
**Source URL:** *(Add URL here)*
**Date Collected:** *(Add date here)*
**Country:** *(Add country here)*
**League:** *(Add league here)*
**Match:** *(Add match teams here)*
```

#### 2. Summary Section
Brief description of what this HTML sample captures.

```markdown
## Summary

This HTML sample captures the **[primary/secondary] navigation tabs** under the [parent tab] for a [match state] [sport] match on Flashscore.
```

#### 3. Tab Structure Table (for populated files)
```markdown
### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| *(Tab name)* | *(analytics alias)* | *(URL pattern)* | Yes/No |
```

#### 4. HTML Section
```markdown
## HTML

```html
<!-- Paste HTML here with proper indentation -->
```
```

#### 5. Notes Section
Include common selector patterns and explanations:

```markdown
## Notes

### General
- Description of what these tabs do

### Active State Indicators
- `aria-current="page"` - active tab indicator
- `class="active"` - active tab indicator
- `data-selected="true"` - active tab indicator
- `wcl-tabSelected_rHdTM` - active tab CSS class

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Active Tab:** `a[aria-current="page"]` or `button[data-selected="true"]`

### Match State Differences
- **Scheduled:** *(available options)*
- **Live:** *(available options)*
- **Finished:** *(available options)*
```

### Template for Secondary Files

```markdown
# {Match State} {Sport} - {Primary Tab} Tab - Secondary Tabs

**Source URL:** *(Add URL here)*
**Date Collected:** *(Add date here)*
**Country:** *(Add country here)*
**League:** *(Add league here)*
**Match:** *(Add match teams here)*

---

## Summary

This HTML sample captures the **secondary navigation tabs** under the {Primary Tab} primary tab for a {match state} {sport} match on Flashscore.

### Tab Structure

| Tab | data-analytics-alias | URL Path | Active |
|-----|---------------------|----------|--------|
| *(To be documented)* | | | |

---

## HTML

```html
<!-- Paste secondary tabs HTML here -->
```

---

## Notes

### General
- Secondary tabs allow navigation between different {market/view} types

### Active State Indicators
- `aria-current="page"` on the `<a>` element indicates the active tab
- `class="active"` on the `<a>` element indicates the active tab
- `data-selected="true"` on the `<button>` element indicates the active tab
- `wcl-tabSelected_rHdTM` class on the `<button>` element indicates the active tab

### Selector Patterns
- **Container:** `div[data-testid="wcl-tabs"][data-type="secondary"]`
- **Tab Links:** `a[data-analytics-element="SCN_TAB"]`
- **Tab Buttons:** `button[data-testid="wcl-tab"]`
- **Active Tab:** `a[aria-current="page"]` or `button[data-selected="true"]`

### Match State Differences
- **{Match State}:** *(available options)*
- **Other States:** *(describe differences)*
```

### Template for Tertiary Files

```markdown
# {Match State} {Sport} - {Primary Tab} Tab - Tertiary Tabs

**Secondary Tab:** *(Specify which secondary tab you're documenting)*
**Source URL:** *(Add URL here)*
**Date Collected:** *(Add date here)*
**Country:** *(Add country here)*
**League:** *(Add league here)*
**Match:** *(Add match teams here)*

---

## HTML

```html
<!-- Paste tertiary tabs HTML here -->
```

---

## Tertiary Structure by Secondary Tab

### {Secondary Tab 1} > Tertiary
*(Document sub-tabs)*

### {Secondary Tab 2} > Tertiary
*(Document sub-tabs)*

---

## Notes

### General
- Tertiary tabs appear under secondary tabs
- Each secondary tab has its own unique tertiary options

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
- **{Match State}:** *(available options)*
- **Other States:** *(describe differences)*
```

---

## Folder Purpose

### navigation/
Contains HTML samples for tab navigation elements:
- `secondary.md` - Secondary tab navigation HTML
- `tertiary.md` - Tertiary tab navigation HTML

### content/
Contains actual page content for each tab. Structure:
- `content/<secondary_tab_name>/` - Folder for each secondary tab
- Add `.md` files inside each folder for the page content
- Tertiary subfolders can be added inside secondary content folders when needed

## How to Add HTML Samples

### Step 1: Navigate to Flashscore
1. Open a Flashscore match page in your browser
2. Note the match state (scheduled/live/finished)

### Step 2: Open DevTools
1. Press F12 to open Developer Tools
2. Click on the Elements tab
3. Use the Select element tool (Ctrl+Shift+C)

### Step 3: Find Tab Elements
Look for elements with these attributes:
```html
<!-- Primary/Secondary tabs -->
<a data-analytics-alias="match-summary" ...>
<a data-analytics-alias="odds-comparison" ...>
<a data-analytics-alias="h2h" ...>
<a data-analytics-alias="stats-detail" ...>
<a data-analytics-alias="player-statistics" ...>
<a data-analytics-alias="match-statistics" ...>
<a data-analytics-alias="lineups" ...>
<a data-analytics-alias="match-history" ...>

<!-- Active state indicators -->
<a ... aria-current="page">
<button data-testid="wcl-tab" data-selected="true">
```

### Step 4: Copy HTML
1. Right-click on the container element
2. Select Copy > Copy outerHTML
3. Paste into the appropriate file

### Step 5: Add Metadata
At the top of each file, fill in:
- **Source URL**: The Flashscore match URL
- **Date Collected**: When you captured the HTML
- **Country**: The country where the league is located
- **League**: The competition name
- **Match**: The teams playing

---

## Status Tracking

| Match State | Primary | Match Sec/Tert | Odds Sec/Tert | H2H Sec/Tert | Standings Sec/Tert |
|-------------|---------|----------------|---------------|--------------|---------------------|
| Scheduled | ● | ● / ● | ● / ● | ● / ● | ● / ● |
| Live | ● | ● / ● | ● / ● | ● / ● | ● / ● |
| Finished | ● | ● / ● | ● / ● | ● / ● | ● / ● |

**Legend:** ● = Empty/needs HTML, ✓ = Has HTML sample

---

## File Count

| Category | Files |
|----------|-------|
| README files | 2 |
| Scheduled basketball | 9 navigation + 5 content folders |
| Live basketball | 9 navigation + 5 content folders |
| Finished basketball | 9 navigation + 5 content folders |
| **Total** | **29 + 15 content folders** |
