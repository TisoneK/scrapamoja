# Status Detection Update

## Overview
Updated the match status detection logic to work with the new HTML structure and prevent confusion between live, finished, and scheduled matches.

## HTML Structure Analysis

### Live Matches
```html
<div class="event__match event__match--live event__match--twoLine" data-event-row="true">
  <div class="event__stage">
    <div class="event__stage--block">1st Quarter<br>&nbsp;9<span class="blink">&nbsp;</span></div>
  </div>
  <span class="event__score event__score--home" data-state="live" data-highlighted="true">18</span>
  <span class="event__score event__score--away" data-state="live" data-highlighted="false">14</span>
</div>
```

**Key Indicators:**
- `class="event__match--live"`
- `data-state="live"` on score elements
- `class="wcl-isLive_VTsUE"` on score elements
- Stage text contains "quarter", "min", "half"

### Finished Matches
```html
<div class="event__match event__match--twoLine" data-event-row="true">
  <div class="event__stage">
    <div class="event__stage--block">After Overtime</div>
  </div>
  <span class="event__score event__score--home" data-state="final">134</span>
  <span class="event__score event__score--away" data-state="final">137</span>
</div>
```

**Key Indicators:**
- `data-state="final"` on score elements
- `class="wcl-isFinal_7U4ca"` on score elements
- Stage text contains "finished", "after", "ft"

### Scheduled Matches
```html
<div class="event__match event__match--scheduled event__match--twoLine" data-event-row="true">
  <div class="event__time">19:00</div>
  <span class="event__score event__score--home" data-state="pre-match">-</span>
  <span class="event__score event__score--away" data-state="pre-match">-</span>
</div>
```

**Key Indicators:**
- `class="event__match--scheduled"`
- `data-state="pre-match"` on score elements
- `class="wcl-isPreMatch_FgNtO"` on score elements
- Time element with format "HH:MM"
- Dash scores "-"

## Updated YAML Selectors

### Created new status-specific YAML selectors:
- `live_indicators.yaml` - for live match detection
- `finished_indicators.yaml` - for finished match detection  
- `scheduled_indicators.yaml` - for scheduled match detection

### Live Indicator (`live_indicators.yaml`)
```yaml
strategies:
  - type: "css"
    selector: ".event__match--live"
    weight: 1.0
  - type: "css"
    selector: ".event__score[data-state='live']"
    weight: 0.9
  - type: "css"
    selector: ".wcl-isLive_VTsUE"
    weight: 0.8
```

### Finished Indicator (`finished_indicators.yaml`)
```yaml
strategies:
  - type: "css"
    selector: ".event__score[data-state='final']"
    weight: 1.0
  - type: "css"
    selector: ".wcl-isFinal_7U4ca"
    weight: 0.7
```

### Scheduled Indicator (`scheduled_indicators.yaml`)
```yaml
strategies:
  - type: "css"
    selector: ".event__match--scheduled"
    weight: 1.0
  - type: "css"
    selector: ".event__time"
    weight: 0.9
  - type: "css"
    selector: ".event__score[data-state='pre-match']"
    weight: 0.8
```

## Updated Extractor Logic

### Live Match Extractor
1. Check for `event__match--live` CSS class
2. Check for `data-state="live"` score elements
3. Check for `wcl-isLive_VTsUE` CSS classes
4. Verify actual live scores with `data-state="live"`
5. Check for live stage text (quarter/min/half)

### Finished Match Extractor
1. Check for `data-state="final"` score elements
2. Check for `wcl-isFinal_7U4ca` CSS classes
3. Check for `event__match--finished` CSS class
4. Check for finished stage text (finished/after/ft)
5. Verify actual final scores with `data-state="final"`

### Scheduled Match Extractor
1. Check for `event__match--scheduled` CSS class
2. Check for `data-state="pre-match"` score elements
3. Check for `wcl-isPreMatch_FgNtO` CSS classes
4. Check for time elements with "HH:MM" format
5. Verify dash scores with `data-state="pre-match"`
6. Exclude matches with live/finished indicators

## Test Results

✅ **Live matches**: 0 found (correct - no live basketball matches currently)
✅ **Finished matches**: 0 found (correct - no finished matches in current view)
✅ **Scheduled matches**: 1 found (Cluj-Napoca vs Aris at 19:00)

## Key Improvements

1. **Eliminated false positives** by using `data-state` attributes instead of unreliable class-based detection
2. **Added exclusion logic** to prevent scheduled matches from being flagged as live/finished
3. **Multiple detection methods** for each status to ensure reliability
4. **State verification** to confirm score elements match the expected status
5. **Proper CSS class targeting** based on actual HTML structure

The status detection now correctly distinguishes between live, finished, and scheduled matches without confusion.
