# Selector Debugging Workflow

## Purpose

This workflow defines a standardized process for diagnosing, analyzing, and resolving selector failures using the Scrapamoja snapshot observability system.

It ensures selector maintenance is:

- **Deterministic** - Same failure produces same analysis
- **Reproducible** - Results can be verified independently  
- **Data-driven** - Decisions based on captured artifacts
- **Auditable** - Complete change history and rationale

---

## 1. When This Workflow Is Triggered

Execute this workflow when any of the following occurs:

- Selector resolution timeout
- Selector not found  
- Fallback strategy used
- Unexpected DOM structure
- Scraping result inconsistency
- Performance degradation in selector resolution

**Snapshot capture must already be automatic at failure time.**

---

## 2. Snapshot Location Convention

Failure snapshots are stored under:

```
data/snapshots/<site>/selector_engine/<YYYYMMDD>/<timestamp>_<failure_type>_<operation>/
```

Typical structure:

```
├── metadata.json          # Structured diagnostic context
├── html/
│   └── fullpage_failure_.html    # Exact browser DOM state
├── screenshots/
│   └── viewport_<timestamp>.png     # Visual page state  
└── logs/
    └── console_<timestamp>.json      # Browser console output
```

Artifacts represent the exact browser state at failure time.

---

## 3. Debugging Procedure

### Step 1 — Open metadata.json

This file provides structured diagnostic context.

**Inspect:**

| Field | Meaning |
|-------|---------|
| `operation` | Selector operation being executed |
| `failure_type` | Classification of failure |
| `resolution_time` | Time spent resolving selector |
| `strategies_attempted` | Ordered list of selector strategies |
| `fallback_used` | Whether fallback logic executed |
| `context` | Runtime environment information |

**Goal:** Identify why resolution failed without opening the browser.

### Step 2 — Inspect Captured HTML

Open the full page HTML snapshot.

**Analyze:**

- **Actual DOM structure** vs expected structure
- **Presence/absence of target elements**
- **Attribute changes** (class names, IDs, data attributes)
- **Nesting changes** (parent/child relationships)
- **Dynamic rendering differences** (lazy loading, conditional content)

**Key questions:**

- Did the element move?
- Did attributes change?
- Is content delayed or conditional?
- Is the selector too strict?
- Are there race conditions?

### Step 3 — Verify Visual State

Open the screenshot artifact.

**Check:**

- Page layout changes
- Cookie banners or overlays
- Authentication walls
- Lazy loading behavior
- Responsive layout differences

**Visual evidence validates DOM interpretation.**

### Step 4 — Review Console Logs

Inspect captured browser console output.

**Look for:**

- JavaScript errors
- Blocked resources  
- Network failures
- CSP violations
- Anti-bot responses

**Console errors often explain missing DOM nodes.**

### Step 5 — Classify Failure Type

Assign one of the standardized categories:

| Failure Type | Description |
|--------------|-------------|
| `selector_not_found` | Target element absent |
| `timeout` | Element exists but not resolved in time |
| `layout_shift` | DOM structure changed |
| `blocked` | Content hidden by overlay or gate |
| `stale_dom` | Selector references outdated structure |
| `performance` | Resolution excessively slow |

**Classification is required for trend analysis.**

### Step 6 — Update Selector Strategy

Based on observed DOM structure:

**Recommended adjustments:**

- Prefer stable attributes over dynamic classes
- Reduce excessive specificity
- Avoid positional selectors when possible
- Account for dynamic containers
- Introduce fallback hierarchy

**Document selector change rationale.**

### Step 7 — Validate Fix Against Snapshot

Use captured HTML as deterministic test input.

**Validation rule:** Updated selector must resolve successfully against stored HTML snapshot.

**This prevents reintroducing instability.**

### Step 8 — Record Selector Evolution

When modifying a selector, record metadata:

```json
{
  "selector_version": "v2.1",
  "previous_selector": ".event__match .eventRowLink",
  "snapshot_reference": "20260214_154054_failure_cookie_consent_1771062054.61608",
  "change_reason": "DOM structure changed - container div added",
  "date": "2026-02-14T15:40:54Z"
}
```

**Selector changes must be traceable to a failure snapshot.**

---

## 4. Performance Monitoring Integration

Each snapshot contains resolution timing data.

**Track over time:**

- Average resolution time per selector
- Fallback usage rate  
- Failure frequency per selector
- DOM change frequency per site

**Performance drift indicates structural site changes.**

---

## 5. Operational Best Practices

### Do Not Debug Live First
Always analyze snapshot artifacts before running new tests.

### Never Guess DOM Structure
Selectors must be derived from captured HTML evidence.

### Treat Snapshots as Ground Truth
Snapshot artifacts represent authoritative browser state.

### Maintain Failure History
Historical snapshots are required for regression analysis.

---

## 6. Expected Outcomes

After applying this workflow:

- ✅ Selector fixes are evidence-based
- ✅ Failures are reproducible  
- ✅ Debugging time is reduced
- ✅ Selector stability improves over time
- ✅ DOM change patterns become measurable

---

## 7. Future Extensions

Planned enhancements to this workflow:

- **Automated DOM diff** between snapshots
- **Selector regression test runner**
- **Failure trend analytics**
- **Content-addressed snapshot storage**
- **CI validation** against historical failures

---

## 8. Example Debugging Session

**Scenario:** Cookie consent selector failing

```
📁 data/snapshots/flashscore/selector_engine/20260214/154054_failure_cookie_consent_*/
├── metadata.json     ← "All 6 strategies failed, resolution_time: 88.982s"
├── html/
│   └── fullpage_failure_.html  ← "4034633 bytes of actual DOM"
├── screenshots/
│   └── viewport_154054.png      ← "Visual page state"
└── logs/
    └── console_154054.json      ← "JavaScript errors"
```

**Analysis Process:**

1. **Metadata** → Timeout after 30s, all strategies failed
2. **HTML** → Cookie consent elements not present in DOM
3. **Screenshot** → No cookie banner visible on page
4. **Logs** → No JavaScript errors blocking detection
5. **Classification** → `selector_not_found` (element absent)
6. **Resolution** → Update selector to handle case where consent not required

**Result:** Evidence-based selector update with documented reasoning.

---

*This workflow transforms selector maintenance from reactive debugging to proactive, data-driven engineering.*
