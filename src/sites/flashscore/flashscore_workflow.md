# Flashscore Workflow Architecture

## Overview

This document outlines the **Complex Pattern** flow organization for Flashscore.com, a challenging Single Page Application (SPA) with multi-layered navigation and dynamic data hydration.

## Domain-Driven Flow Structure

```
flows/
├── authentication/
│   └── cookie_consent.py          # Step 1: Handle cookie consent
│
├── navigation/
│   ├── sport_selection.py         # Step 2: Navigate to sport (football → basketball)
│   ├── event_filter.py            # Step 3: Filter by live/finished/scheduled
│   ├── match_navigation.py        # Step 4: Click into specific match
│   ├── tab_switching.py           # Step 5: Navigate SUMMARY, H2H, ODDS, STATS tabs
│   └── tertiary_tabs.py           # Step 6: Navigate Inc OT, FT, Q1 subtabs
│
├── extraction/
│   ├── match_list.py              # Extract match URLs, times, names, IDs from listing
│   ├── match_summary.py           # Extract data from SUMMARY tab
│   ├── match_h2h.py               # Extract data from H2H tab
│   ├── match_odds.py              # Extract data from ODDS tab
│   └── match_stats.py             # Extract data from STATS tab (with tertiary context)
│
└── filtering/
    ├── date_filter.py             # Filter by specific date
    └── competition_filter.py      # Filter by league/tournament
```

## Multi-Layer Navigation Model

### **Primary Layer: Sport Selection**
- **Purpose**: Navigate between different sports categories
- **Examples**: Football → Basketball → Tennis → Cricket
- **Challenge**: Each sport has different URL structure and data models
- **Hydration**: Triggers complete page reload with new sport data

### **Secondary Layer: Match Tabs**
- **Purpose**: Navigate within a specific match
- **Tabs**: SUMMARY, H2H (Head-to-Head), ODDS, STATS
- **Challenge**: Each tab loads data independently via AJAX
- **Hydration**: Triggers partial DOM updates without full page reload

### **Tertiary Layer: Sub-Tab Navigation**
- **Purpose**: Navigate detailed statistics within tabs
- **Examples**: Inc OT (Incidents + Overtime), FT (Full Time), Q1 (Quarter 1)
- **Challenge**: Context-dependent selectors and state management
- **Hydration**: Triggers granular data updates within tab context

## Key Architectural Challenge

**Each navigation layer triggers new data hydration** - this is exactly why Flashscore requires **Complex Pattern** architecture:

1. **Primary navigation** → Full page reload, new DOM structure
2. **Secondary navigation** → AJAX data injection, partial DOM updates  
3. **Tertiary navigation** → Context-specific data, tab-scoped selectors

## Implementation Questions

### **1. Tertiary Tab Scope**
**Question**: Do tertiary tabs (Inc OT, FT, Q1) only exist under STATS? Or do other tabs also have tertiary navigation?

**Impact**: 
- If STATS-only → Simpler tertiary navigation logic
- If multiple tabs → Need generic tertiary tab handling system

### **2. Loading Behavior**
**Question**: When you "Wait for matches to load" - is this a pagination issue, or just waiting for initial AJAX load?

**Impact**:
- Pagination → Need infinite scroll/page navigation flows
- AJAX load → Simple timeout + element detection

### **3. Data Collection Strategy**
**Question**: Do you need to scrape ALL matches in a day, or specific matches?

**Impact**:
- All matches → Need `match_list.py` + batch processing
- Specific matches → Can go direct to match URLs, skip listing extraction

## Recommended Implementation Approach

### **Phase 1: Foundation**
1. **Authentication Flow** - Cookie consent handling
2. **Sport Selection** - Basic navigation between sports
3. **Event Filtering** - Live/finished/scheduled filtering

### **Phase 2: Core Navigation**
1. **Match Navigation** - Click into specific matches
2. **Tab Switching** - Navigate between SUMMARY/H2H/ODDS/STATS
3. **Loading Detection** - Wait for data hydration

### **Phase 3: Advanced Features**
1. **Tertiary Navigation** - Handle sub-tabs within STATS
2. **Extraction Pipelines** - Domain-specific data extraction
3. **Filtering System** - Date and competition filters

## Technical Considerations

### **State Management**
- **Tab Context**: Track which tab is currently active
- **Sport Context**: Track which sport is being scraped
- **Match Context**: Track which match data is being extracted

### **Selector Strategy**
- **Tab-Scoped Selectors**: Different selectors for each tab context
- **Dynamic Wait Conditions**: Wait for specific data patterns per tab
- **Fallback Mechanisms**: Multiple selector strategies per element

### **Error Handling**
- **Tab Switch Failures**: Recovery when tab navigation fails
- **Data Hydration Timeouts**: Handle slow AJAX loads
- **SPA Navigation**: Handle client-side routing changes

## Success Metrics

### **Navigation Success**
- Tab switching reliability > 95%
- Data hydration detection > 90%
- Error recovery success > 80%

### **Extraction Quality**
- Data completeness > 85%
- Field accuracy > 90%
- Cross-tab consistency > 80%

---
**This architecture positions Flashscore scraper as a showcase for complex SPA navigation patterns in the scrapamoja framework.**
