---
description: Define selector design standards and anti-patterns for robust scraping
---

# Selector Design Standards

**Owner:** Snapshot System  
**Scope:** Selector Engineering  
**Applies To:** All selector development  
**Last Reviewed:** 2026-02-14  
**Status:** stable

## Purpose

Defines enforceable selector engineering discipline with machine-checkable constraints, deterministic validation, and traceable evolution to prevent failures before they occur.

---

## 🎯 What Design Task Do You Need?

**Select a number (1-5) to jump to relevant standards:**

1. **[Create New Selectors](#implementation-checklist)** - Design new selectors with proper standards
2. **[Review Existing Quality](#machine-checkable-constraints)** - Check current selectors against standards
3. **[Set Performance Budgets](#performance-budget-enforcement)** - Define timing requirements
4. **[Implement Fallbacks](#formal-fallback-contract)** - Add resilience hierarchies
5. **[Fix Anti-Patterns](#anti-pattern-exceptions-policy)** - Resolve selector violations

---

## 1️⃣ Machine-Checkable Constraints

### Selector Lint Rules

```yaml
# Forbidden Patterns
forbidden:
  - pattern: ":nth-child"
    reason: "Positional selectors break easily"
  - pattern: ":nth-of-type" 
    reason: "Positional selectors break easily"
  - pattern: "(class|\\.)[a-zA-Z_-]*[0-9a-f]{8,}"
    reason: "Likely build-generated class"
  - pattern: "XPath"
    condition: "no exception block present"
    reason: "XPath allowed only with documented exception"

# Structural Constraints  
constraints:
  max_combinator_depth: 3
  max_selector_length: 100
  require_semantic_element: true
  prefer_data_attributes: true

# Combinator Depth Definition
combinator_depth: "Number of descendant ( ), child (>), adjacent (+), or sibling (~) operators"
example: "div > ul li a" # depth = 3

# Performance Gates
performance_budgets:
  critical_path: 200    # Navigation selectors
  content_extraction: 500  # Content selectors  
  optional_ui: 1000       # Optional elements
```

### PR Gate Enforcement

```bash
# CI Pipeline Integration
selector-lint --fail-on-violations
selector-performance-test --budget-check
selector-regression-test --snapshot-validation
```

**Merge blocked if any violations found.**

---

## 2️⃣ Formal Fallback Contract

### SelectorSpec Interface

```typescript
interface SelectorSpec {
  primary: string;                    // Level 1 strategy
  fallbacks: string[];                // Level 2-5 strategies
  strategy_levels: number[];           // Available fallback levels
  expected_role: string;                // Semantic purpose
  performance_budget_ms: number;          // Max allowed time
  stability_score: number;               // 0.0-1.0 reliability rating
}
```

### Stability Score Formula

```javascript
stability_score = 
  (success_rate × 0.6) + 
  ((1 - fallback_rate) × 0.2) + 
  (performance_budget_ms / p95_ms × 0.2 capped at 1.0)
```

**Prevents subjective scoring through measurable computation.**

### Implementation Example

```json
{
  "selector_id": "cookie_consent_button",
  "primary": "[data-testid='accept-cookies']",
  "fallbacks": [
    "button:contains('Accept')",
    ".cookie-banner button",
    "#cookie-notice button"
  ],
  "strategy_levels": [1, 2, 3, 4],
  "expected_role": "cookie_consent_accept",
  "performance_budget_ms": 200,
  "stability_score": 0.95
}
```

### Expected Role Taxonomy

**Controlled vocabulary to prevent free-text drift:**

```
navigation           # Page navigation elements
content_primary      # Main content elements
content_secondary    # Supporting content elements
interaction_trigger  # Interactive elements that trigger actions
modal_control       # Modal dialog controls
state_indicator      # Status/state display elements
cookie_consent      # Cookie consent dialog elements
authentication      # Login/auth form elements
```

**Benefits:**
- Uniform telemetry across all selectors
- Predictable resolution flow
- Easier regression testing
- Automated performance monitoring

---

## 3️⃣ Deterministic Validation Matrix

### Validation Requirements

| Test Case | Requirement | Success Criteria |
|------------|--------------|------------------|
| **Current DOM** | Must resolve against latest snapshot | ✅ Element found, < budget time |
| **30-Day Failures** | Must resolve against failure snapshots | ✅ 95% success rate |
| **Worst-Case DOM** | Must handle largest HTML snapshot | ✅ < p95 performance target |
| **Performance Percentiles** | Must meet budget targets | ✅ p50 < budget, p95 < 2× budget |

**Time Source:** Resolution time measured from selector invocation to first match.

### Snapshot Reference Format

**Standardized format for automatic tooling resolution:**

```
<site>/<module>/<date>/<timestamp>_<failure_type>
```

**Examples:**
- `flashscore/selector_engine/20260214/154054_failure_cookie_consent_1771062054.61608`
- `flashscore/flow/navigation/20260214/154054_flow_20260214_154054`

**Ensures future tooling can resolve references automatically.**

### Validation Results Storage

```json
{
  "validation": {
    "success_rate": 0.98,
    "fallback_rate": 0.07,
    "p50_ms": 150,
    "p95_ms": 280,
    "worst_case_ms": 420,
    "snapshot_coverage": "30-day-failures"
  }
}
```

---

## 4️⃣ Performance Budget Enforcement

### Hard Budgets by Selector Class

| Selector Class | Budget | Fail Action |
|----------------|---------|-------------|
| **Critical Path** (navigation) | ≤ 200ms | Block merge |
| **Content Extraction** | ≤ 500ms | Block merge |
| **Optional UI Elements** | ≤ 1000ms | Warning only |

### Budget Violation Handling

```bash
# CI Performance Check
if [ $p95_ms -gt $budget ]; then
  echo "❌ Performance budget exceeded: ${p95_ms}ms > ${budget}ms"
  exit 1
fi
```

---

## 5️⃣ Append-Only Evolution Ledger

### Structured Evolution Tracking

```json
{
  "selector_id": "cookie_consent_button",
  "version": "1.2",
  "replaced_version": "1.1", 
  "snapshot_ref": "20260214_154054_failure_cookie_consent_1771062054.61608",
  "content_hash": "a1b2c3d4e5f6...",
  "reason": "DOM structure changed - data-testid added",
  "metrics": {
    "success_rate": 0.98,
    "fallback_rate": 0.07,
    "p50_ms": 150,
    "p95_ms": 180,
    "stability_score": 0.95
  },
  "date": "2026-02-14T15:40:54Z",
  "author": "selector-engine-team"
}
```

### Append-Only Properties

- ✅ **Immutable history** - Never delete or modify entries
- ✅ **Content-addressed** - Reference specific DOM snapshots
- ✅ **Metric tracking** - Performance evolution over time
- ✅ **Change attribution** - Who changed what and why

---

## 6️⃣ Anti-Pattern Exceptions Policy

### Required Exception Documentation

When using forbidden patterns, must include:

```yaml
exception:
  forbidden_pattern: ":nth-child"
  documented_reason: "Dynamic list with no stable identifiers"
  snapshot_evidence: "20260214_154054_failure_dynamic_list_12345"
  expiry_review: "2026-03-14"
  temporary_workaround: true
  migration_plan: "Add data-testid to list items"
```

### Exception Review Process

1. **Document evidence** from snapshot analysis
2. **Set expiry date** for temporary workarounds
3. **Create migration plan** to permanent solution
4. **Team review** required for approval

**Prevents permanent technical debt accumulation.**

---

## 6️⃣ Merge Authority

### Override Policy

**CI gates can be overridden only with documented exceptions:**

```yaml
override_authority:
  requirements:
    - documented_exception: true
    - reviewer_approvals: 2
    - remediation_issue: true
  process:
    - create GitHub issue for remediation
    - assign to selector-engine-team
    - set review deadline: 7 days
    - automatic revert if deadline missed
```

**Prevents silent policy erosion and ensures accountability.**

---

## 7️⃣ CI Integration Specification

### Pipeline Stages

```yaml
# .github/workflows/selector-validation.yml
name: Selector Validation Pipeline

stages:
  - selector-lint:
      run: selector-lint --fail-on-violations
      artifacts: lint-report.json
      
  - snapshot-regression:
      run: selector-regression-test --snapshot-validation
      artifacts: regression-report.json
      
  - performance-benchmark:
      run: selector-performance-test --budget-check
      artifacts: performance-report.json
      
  - evolution-ledger:
      run: selector-evolution-check --append-only
      artifacts: evolution-report.json
```

### Merge Gate Conditions

```bash
# All checks must pass for merge approval
if [[ $lint_status == "passed" && 
      $regression_status == "passed" && 
      $performance_status == "passed" && 
      $evolution_status == "passed" ]]; then
  echo "✅ Selector validation passed - merge allowed"
else
  echo "❌ Validation failed - merge blocked"
  exit 1
fi
```

---

## 8️⃣ Engineering Discipline Summary

### From Guidelines to Enforceable System

| Dimension | Before | After |
|------------|----------|--------|
| **Validation** | Manual review | Automated lint + regression |
| **Performance** | Ad-hoc testing | Budget enforcement + percentiles |
| **Traceability** | Git history | Append-only ledger + snapshot refs |
| **Consistency** | Team conventions | Machine-checkable contracts |
| **Quality Gates** | Code review | CI pipeline enforcement |

### Expected Outcomes

- ✅ **Prevention**: Most failures prevented through design
- ✅ **Consistency**: All selectors follow identical contracts
- ✅ **Performance**: Predictable resolution times
- ✅ **Traceability**: Complete evolution history
- ✅ **Quality**: Automated enforcement at merge time

---

## 9️⃣ Implementation Checklist

### Before Implementation

- [ ] Review lint rules for compliance
- [ ] Define SelectorSpec with fallback hierarchy
- [ ] Set performance budget for selector class
- [ ] Identify required snapshot tests

### During Implementation  

- [ ] Follow stability heuristics
- [ ] Implement full fallback chain
- [ ] Avoid anti-patterns (or document exceptions)
- [ ] Add performance monitoring

### Before Merge

- [ ] Pass selector lint validation
- [ ] Pass snapshot regression tests
- [ ] Meet performance budget requirements
- [ ] Update evolution ledger
- [ ] Document all changes with snapshot references

---

---

## 🔧 LLM Governance & Constraints

### 📋 LLM Creation Guidelines

**When creating or modifying this workflow:**

#### ✅ Required Structure
- **YAML Frontmatter**: Must include owner, scope, status, last reviewed
- **Technical Accuracy**: All formulas, rules, and examples must be correct
- **Measurable Metrics**: Performance targets must be quantifiable
- **Cross-References**: Link to related workflows

#### 🚫 Forbidden Changes
- **Remove Core Standards**: Cannot eliminate essential engineering rules
- **Alter Performance Budgets**: Cannot change measurable targets without justification
- **Break Anti-Patterns**: Cannot remove critical quality constraints
- **Change Validation Matrix**: Cannot alter deterministic testing requirements

#### 🎯 Quality Gates
- **Technical Review**: All engineering concepts must be accurate
- **Practical Application**: Rules must be implementable in real systems
- **Consistency Check**: Follow same governance as other workflows
- **Documentation Quality**: Examples must be clear and correct

### 🤖 LLM Modification Constraints

#### ✅ Allowed Modifications
- **Add New Anti-Patterns**: Include emerging failure patterns
- **Improve Examples**: Add real-world selector scenarios
- **Update Performance Targets**: Adjust budgets based on measured data
- **Add Validation Strategies**: Include new testing approaches

#### 🚫 Restricted Modifications
- **Remove Budget Enforcement**: Cannot eliminate performance gates
- **Weaken Anti-Patterns**: Cannot allow prohibited selector types
- **Break Fallback Hierarchy**: Cannot alter structured resilience patterns
- **Change Stability Formula**: Cannot modify measurable scoring without validation

### 📊 Compliance Validation

#### Before Commit:
- [ ] Technical accuracy verified?
- [ ] Performance targets realistic?
- [ ] Anti-patterns comprehensive?
- [ ] Validation matrix complete?
- [ ] Governance guidelines followed?

#### Before Merge:
- [ ] Engineering review completed?
- [ ] Performance impact assessed?
- [ ] Implementation feasibility verified?
- [ ] LLM compliance confirmed?

---

*This governance ensures LLMs enhance engineering standards while maintaining technical rigor and implementability.*
