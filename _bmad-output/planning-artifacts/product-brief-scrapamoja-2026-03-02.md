---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/brainstorming/brainstorming-session-2026-03-02-14-57-17.md
date: 2026-03-02
author: Tisone
status: complete
---

# Product Brief: scrapamoja

## Executive Summary

**Scrapamoja** is a cooperative extraction agent that uses page snapshots combined with human guidance to generate complete YAML selector configurations for all Flashscore match page data. It addresses the fundamental challenge of extracting sports data from Flashscore despite their aggressive anti-bot detection and frequently changing DOM structure.

---

## Core Vision

### Problem Statement

Flashscore.com presents significant extraction challenges:
- **Anti-Bot Detection**: Missing browser fingerprints, unrealistic click timing, headless-only execution triggers silent failures
- **Volatile DOM**: CSS class names frequently obfuscated/rotated, stable selectors must rely on semantic attributes
- **Tab-Driven Hydration**: Secondary/tertiary tabs don't preload data, each tab triggers new async requests
- **Selector Drift**: Class rotation, container re-wrapping, child depth shifts break brittle selectors

### Problem Impact

Without a robust solution:
- Data extraction fails silently when detection escalates
- Selector maintenance becomes a constant cat-and-mouse game
- New sports/regions require extensive manual selector engineering

### Proposed Solution

A **cooperative extraction agent** that:
1. **Snapshots**: Captures page snapshots for analysis
2. **Segments DOM**: Uses hybrid structural inference to identify data regions
3. **Generates Selectors**: Creates multi-strategy YAML selectors with confidence scoring
4. **Human-in-the-Loop**: Agent proposes, human verifies, agent learns
5. **Versioned Recipes**: Tracks selector stability over layout generations

### Key Differentiators

- **Recipe Inheritance**: Parent → Child → Grandchild specialization for surgical maintenance
- **Three-Tier Selector Strategy**: Ranked by survival probability, not specificity
- **Field Variance Detection**: Classifies fields as invariant, state-dependent, tab-dependent, or volatile
- **Selector Family Detection**: Groups selectors by ancestor containers for targeted migration

---

## Target Users

### Primary Users

**Python Developers & Data Engineers**
- Build and maintain data pipelines that extract sports data from Flashscore
- Need reliable, maintainable selectors that survive DOM changes
- Work with Playwright/async Python
- Value: Reliability, automation, minimal manual intervention

### Secondary Users

**Operations Team Members (Occasional)**
- Verify suggested selectors when confidence is low
- Handle escalation cases
- Non-technical workflow for approval decisions

### User Journey

1. **Discovery**: Developer integrates scrapamoja into Python pipeline
2. **Onboarding**: Agent analyzes existing snapshots, proposes initial selectors
3. **Core Usage**: Automated extraction with agent proposing selector updates
4. **Success Moment**: Selector failure → auto-proposed fix → human approves → applied
5. **Long-term**: System learns, reduces manual intervention over time

---

## Success Metrics

### User Success Metrics

**Primary Success Criterion:**
- Selector failure produces resolved, committed recipe update in **under 5 minutes of human time**
- **Zero manual YAML editing** required outside escalation UI

**User Value Indicators:**
- Developers can focus on data pipeline logic, not selector maintenance
- Non-technical team members can verify selectors through simple approval workflow
- Reduced friction when Flashscore DOM changes break extraction

### Business Objectives

**MVP Goals:**
1. Schema extension - Extend existing YAML with new metadata fields
2. Audit log - Record every human decision with full context
3. Escalation UI - Fast triage view (what broke, why, alternatives, blast radius)
4. Basic weight adjustment - Per-selector learning from approvals/rejections
5. Feature flags - Incremental rollout by sport

**Out of MVP (Phase 2+):**
- Multi-level inheritance
- Cross-sport rule discovery
- Predictive stability
- Self-healing
- Dynamic composition
- Site-agnostic portability
- CDC layout monitoring

### Key Performance Indicators

| Metric | Target |
|--------|--------|
| Time to resolve selector failure | < 5 minutes human time |
| Manual YAML edits required | 0 (outside escalation UI) |
| Selector survival rate | Track via recipe generations survived |
| Automation level | % of selector fixes auto-approved vs human-verified |

---

## MVP Scope

### Core Features (Build Order)

1. **Schema Extension** - Extend existing YAML with new metadata fields
2. **Audit Log** - Record every human decision with full context
3. **Escalation UI** - Fast triage view (what broke, why, alternatives, blast radius)
4. **Basic Weight Adjustment** - Per-selector learning from approvals/rejections
5. **Feature Flags** - Incremental rollout by sport

### Out of Scope for MVP

- Multi-level inheritance
- Cross-sport rule discovery
- Predictive stability
- Self-healing
- Dynamic composition
- Site-agnostic portability
- CDC layout monitoring

### MVP Success Criteria

- Selector failure produces resolved, committed recipe update in **under 5 minutes of human time**
- **Zero manual YAML editing** required outside escalation UI
- MVP validation: When a selector breaks, the system proposes a fix, human verifies/approves, and the updated recipe is committed

### Future Vision

**Phase 2+ Enhancements:**
- Multi-level inheritance (Parent → Child → Grandchild specialization)
- Cross-sport rule discovery
- Predictive stability based on update patterns
- Self-healing selectors
- Dynamic composition
- Site-agnostic portability (recipe system works beyond Flashscore)
- CDC (Change Data Capture) layout monitoring
