---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain-skipped, step-06-innovation, step-07-project-type-skipped, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-02.md
  - _bmad-output/brainstorming/brainstorming-session-2026-03-02-14-57-17.md
  - docs/yaml-configuration.md
  - docs/workflows/workflows.start.md
workflowType: 'prd'
project_name: scrapamoja
feature_name: Adaptive Selector System
author: Tisone
date: 2026-03-02
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: brownfield
---

# Product Requirements Document - Adaptive Selector System

**Project:** Scrapamoja  
**Feature:** Adaptive Selector System  
**Author:** Tisone  
**Date:** 2026-03-02

---

## Executive Summary

**Adaptive Selector System** is a feature within Scrapamoja that extends the existing YAML selector engine with cooperative, human-in-loop selector generation, versioned recipes, audit logging, escalation UI, and weight-based learning. It sits as an extension layer on top of the existing multi-strategy selector engine.

### How It Works

**Existing Selector Engine (Base Layer):**
- Multi-strategy resolution (CSS, XPath, text anchor, attribute match, DOM relationships, role-based)
- Confidence scoring with weighted factors
- Context-aware resolution
- Fallback mechanisms
- Integration with Playwright and snapshot system

**Adaptive Selector System (Extension Layer):**
- When selectors fail → System captures snapshot, proposes fix → Human verifies → System learns
- Versioned recipes → Track selector stability over layout generations
- Audit logging → Record every human decision
- Escalation UI → Fast triage view (what broke, why, alternatives)
- Weight adjustment → Per-selector learning from approvals/rejections

### Target Users

**Primary:** Python Developers & Data Engineers who build and maintain data pipelines that extract sports data from Flashscore. They need reliable, maintainable selectors that survive DOM changes and work with Playwright/async Python.

**Secondary:** Operations Team Members who verify suggested selectors when confidence is low and handle escalation cases through a non-technical approval workflow.

### Problem Statement

Flashscore presents significant extraction challenges:
- **Anti-Bot Detection**: Missing browser fingerprints, unrealistic click timing, headless-only execution triggers silent failures
- **Volatile DOM**: CSS class names frequently obfuscated/rotated, stable selectors must rely on semantic attributes
- **Tab-Driven Hydration**: Secondary/tertiary tabs don't preload data, each tab triggers new async requests
- **Selector Drift**: Class rotation, container re-wrapping, child depth shifts break brittle selectors

### What Makes This Special

The cooperative agent model differs fundamentally from traditional selector engineering:
- **Human-in-the-Loop**: Agent proposes selectors, human verifies, agent learns from feedback
- **Versioned Recipes**: Tracks selector stability over layout generations with recipe inheritance (Parent → Child → Grandchild)
- **Three-Tier Selector Strategy**: Ranked by survival probability, not specificity
- **Field Variance Detection**: Classifies fields as invariant, state-dependent, tab-dependent, or volatile

---

## Success Criteria

### User Success

- **Primary:** Selector failure produces resolved, committed recipe update in **under 5 minutes of human time**
- **Zero Manual YAML Editing:** No manual YAML editing required outside the escalation UI
- **Developer Experience:** Focus on data pipeline logic, not selector maintenance
- **Operations Ease:** Non-technical team members can verify selectors through simple approval workflow

### Business Success

- **Reduced Maintenance Overhead:** Less developer time spent on selector fixes
- **Knowledge Retention:** System learns and reduces manual intervention over time
- **Reliability:** Predictable extraction pipeline with fewer failures

### Technical Success

- **Selector Survival Rate:** Track via recipe generations survived
- **Automation Level:** % of selector fixes auto-approved vs human-verified
- **Recipe Stability:** Layout generations survived = recipe confidence
- **Learning Accuracy:** Weight adjustment from approvals/rejections working correctly

### Measurable Outcomes

| Metric | Target |
|--------|--------|
| Time to resolve selector failure | < 5 minutes human time |
| Manual YAML edits required | 0 (outside escalation UI) |
| Selector survival rate | Track via recipe generations |
| Automation level | % auto-approved vs human-verified |

---

## Product Scope

### MVP - Minimum Viable Product

1. **Schema Extension** - Extend existing YAML with new metadata fields
2. **Audit Log** - Record every human decision with full context
3. **Escalation UI** - Fast triage view (what broke, why, alternatives, blast radius)
4. **Weight Adjustment** - Per-selector learning from approvals/rejections
5. **Feature Flags** - Incremental rollout by sport

### Growth Features (Post-MVP)

- Multi-level inheritance
- Cross-sport rule discovery
- Predictive stability

### Vision (Future)

- Self-healing selectors
- Dynamic composition
- Site-agnostic portability
- CDC layout monitoring

---

## User Journeys

### 1. Primary User: Python Developer - Success Path

**Persona:** Alex, a Data Engineer at a sports analytics company

**Journey:**
- **Opening:** Alex runs their daily data pipeline to extract Flashscore match data. Everything works smoothly - the selectors resolve correctly, data flows into their database.
- **Rising Action:** One morning, the pipeline fails. The selector for "match odds" returns nothing. Flashscore has changed their DOM structure again.
- **Climax:** Alex checks the Escalation UI. The Adaptive Selector System has already captured the failure, analyzed the new DOM, and proposed 3 alternative selector strategies with confidence scores. Alex reviews them, picks the best one, and clicks "Approve."
- **Resolution:** The recipe is updated. The selector now uses the new strategy. Future failures with similar selectors will be auto-resolved based on learned patterns. Alex returns to their actual work.

### 2. Primary User: Python Developer - Edge Case

**Persona:** Alex, dealing with a tricky edge case

**Journey:**
- **Opening:** A selector for a rarely-used tertiary tab (quarter scores in basketball) keeps failing intermittently.
- **Rising Action:** The Escalation UI shows multiple failure patterns. The proposed fixes have low confidence. Alex needs to investigate deeper.
- **Climax:** Alex examines the DOM snapshots, notices the tab only loads on hover (not on click), and manually creates a new selector strategy. The system learns from this manual intervention.
- **Resolution:** Future selectors for similar tertiary elements now include the hover-state strategy. The system has learned something new.

### 3. Secondary User: Operations Team Member

**Persona:** Jordan, a non-technical operations analyst

**Journey:**
- **Opening:** Jordan receives a notification that 5 selectors failed overnight. They log into the Escalation UI (which is designed for non-technical users).
- **Rising Action:** The UI shows a clear dashboard: "What broke: 5 selectors in match_stats. Why: CSS class rotation in odds container. Blast radius: Basketball and Tennis only."
- **Climax:** Jordan sees the proposed fixes with visual previews. They've been trained to look for "does the data look right?" They approve 4 fixes, flagging 1 as "not sure" for developer review.
- **Resolution:** The fixes are applied. Jordan feels productive without needing to write code.

### 4. API/Integration User

**Persona:** Sam, a developer building a dashboard on top of Scrapamoja

**Journey:**
- **Opening:** Sam is building a real-time dashboard that shows selector health across their entire extraction fleet.
- **Rising Action:** They use the Adaptive Selector System's API to query selector success rates, get notified of failures via webhook, and programmatically approve/reject proposed changes.
- **Climax:** Sam integrates the system into their monitoring stack, getting alerts before selectors fail (based on confidence score degradation).
- **Resolution:** Sam's dashboard provides value to the whole team without them needing to check the UI manually.

---

## Innovation & Novel Patterns

### Detected Innovation Areas

1. **Cooperative Human-in-the-Loop Selector Generation**
   - Unlike static selector tools or pure AI solutions, the system uses a cooperative model where AI proposes selectors and humans verify/approve
   - The system learns from human feedback to improve future proposals
   - Novel combination of automation efficiency with human judgment

2. **Recipe Inheritance Model (Parent → Child → Grandchild)**
   - New pattern for surgical selector maintenance
   - Children inherit regions from parents and override only what differs
   - Enables targeted changes without breaking related selectors

3. **Field Variance Classification**
   - Novel classification system: invariant, state-dependent, tab-dependent, or volatile
   - Enables intelligent selector strategies based on field behavior patterns

4. **Three-Tier Selector Strategy (Ranked by Survival)**
   - Tier 1: Structural anchors (highest survival)
   - Tier 2: Semantic class patterns
   - Tier 3: Direct class/XPath matches

5. **Selector Family Detection**
   - Groups selectors by ancestor containers ("gene pool" concept)
   - Enables targeted migration and early warning

### Validation Approach

- **MVP Validation**: When a selector breaks, system proposes fix → human verifies/approves → recipe committed
- **Success Metric**: < 5 minutes human time to resolve selector failure

### Risk Mitigation

- If human-in-loop doesn't scale: Increase automation threshold over time as system learns
- If recipe inheritance causes complexity: Start with flat structure, add hierarchy incrementally

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP - Focus on solving the core selector maintenance problem  
**MVP Focus:** Flashscore as primary proof point, with site-agnostic architecture  
**Resource Requirements:** 1-2 developers

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
1. Python Developer - Success Path (selector failure → proposed fix → approve)
2. Operations Team Member - Non-technical approval workflow

**Must-Have Capabilities:**
1. **Schema Extension** - Extend YAML with metadata fields (recipe_id, stability_score, generation)
2. **Audit Log** - Record every human decision with full context
3. **Escalation UI** - Fast triage view (what broke, why, alternatives, blast radius)
4. **Weight Adjustment** - Per-selector learning from approvals/rejections
5. **Feature Flags** - Incremental rollout by sport within Flashscore

### Post-MVP Features

**Phase 2:**
- Multi-site rollout (Wikipedia, GitHub)
- Multi-level recipe inheritance
- Cross-site rule discovery

**Phase 3:**
- Predictive stability
- Self-healing selectors
- CDC layout monitoring

### Risk Mitigation Strategy

**Technical Risks:**
- Site-agnostic design complexity → Start with Flashscore, validate patterns before expanding
- Learning system accuracy → Require human feedback to train, increase automation over time

---

## Functional Requirements

### Selector Failure Detection & Capture

- FR1: System can detect when a selector fails during extraction
- FR2: System captures DOM snapshot at time of failure
- FR3: System records failure context (sport, status, page state)

### Alternative Selector Proposal

- FR4: System analyzes DOM structure and proposes multiple alternative selector strategies
- FR5: System provides confidence scores for each proposed selector
- FR6: System shows blast radius (what other selectors might be affected)

### Human Verification Workflow

- FR7: Users can view proposed selectors with visual previews
- FR8: Users can approve or reject proposed selectors
- FR9: Users can flag selectors for developer review
- FR10: Users can create custom selector strategies

### Learning & Weight Adjustment

- FR11: System learns from human approvals to increase confidence of similar selectors
- FR12: System learns from human rejections to avoid similar strategies
- FR13: System tracks selector survival across layout generations

### Versioned Recipes

- FR14: System creates recipe versions when selectors are updated
- FR15: System tracks stability score per recipe
- FR16: System supports recipe inheritance (Parent → Child)

### Audit Logging

- FR17: System records every human decision with full context
- FR18: System maintains complete audit trail of selector changes
- FR19: Users can query audit history by selector, date, or user

### Escalation UI

- FR20: UI shows clear dashboard of failures (what broke, why, alternatives)
- FR21: UI supports both technical and non-technical views
- FR22: UI provides fast triage workflow (< 5 min to resolve)

### Feature Flags

- FR23: System can enable/disable adaptive system per sport
- FR24: System can enable/disable adaptive system per site

---

## Non-Functional Requirements

### Performance

- **Escalation UI Response Time:** User can complete full approval workflow in < 5 minutes
- **Selector Proposal Generation:** System generates alternative selector proposals within 30 seconds of failure detection
- **Learning System Latency:** Weight adjustments are applied within 1 second of human decision

### Scalability

- **Multi-Site Support:** System architecture supports adding new sites without code changes (feature flags)
- **Recipe Storage:** System can store and manage 1000+ recipe versions without performance degradation
- **Concurrent Users:** Support at least 5 concurrent users in escalation UI

### Accessibility

- **Non-Technical UI:** Escalation UI must be usable by non-technical operations team members
- **Visual Previews:** Selector proposals include visual DOM previews (not just code)
- **Clear Language:** Error messages and failure descriptions use plain language

### Integration

- **YAML Compatibility:** All selector configurations remain in YAML format
- **Selector Engine Integration:** Must integrate with existing multi-strategy selector resolution
- **Playwright Integration:** Must work with Playwright for DOM snapshot capture
- **Hot Reload:** Configuration changes can be applied without restarting the system
