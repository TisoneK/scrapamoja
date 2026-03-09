---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "_bmad-output/brainstorming/brainstorming-session-2026-03-06-15-17.md"
  - "docs/summary.md"
date: 2026-03-06
author: Tisone
---

# Product Brief: scrapamoja

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

Scrapamoja is an existing production Flashscore scraper with a **fully built adaptive selector module** (`src/selectors/adaptive/`). This product brief focuses on the **integration layer** — wiring the adaptive module into the existing flashscore scraper to eliminate selector failure debugging. The adaptive module is production-ready with failure detection, alternative generation, confidence scoring, and a comprehensive verification workflow API.

## Core Vision

### Problem Statement

The existing Flashscore scraper relies on static CSS/XPath selectors that are fundamentally fragile. When Flashscore changes its DOM structure (which happens frequently), selectors silently fail. The scraper continues running, producing incomplete or empty data with no indication anything went wrong. You waste hours debugging, manually identifying which selector broke, crafting replacements, and redeploying—only to repeat the process when the next change occurs.

### Problem Impact

- **Time Waste**: Hours spent debugging selector failures after they occur
- **Data Quality Risk**: Silent failures mean incomplete datasets go undetected
- **Maintenance Burden**: Constant manual monitoring and intervention required
- **Reliability Debt**: Cannot trust scraper output without manual verification

### Why Existing Solutions Fall Short

Current scraping approaches rely entirely on static selectors:
- Better logging (but you still have to check)
- More robust selector writing (but DOM still changes)
- Monitoring/alerting (but alerts mean something already broke)

The existing scraper has no mechanism to handle selector failures automatically.

### Proposed Solution

**Integrate** the fully-built adaptive selector engine into the existing Flashscore scraper. The adaptive module is complete — the work is the integration layer:

1. **Fallback chain wiring**: Connect flashscore extractors to adaptive resolution pipeline
2. **YAML hints**: Add hint schema to existing YAML selectors for adaptive resolution
3. **Failure capture**: Wire sync failure capture to send failures to adaptive DB
4. **API integration**: Connect to adaptive's REST API and WebSocket for real-time updates

### Key Differentiators

1. **Integration-Only**: Not building new adaptive features — the module already exists
2. **Hybrid Architecture**: Connects existing YAML-defined selectors to adaptive resolution
3. **Real-time Updates**: WebSocket integration for live failure notifications
4. **Blast Radius**: Leverages adaptive's existing blast radius calculation for impact analysis

## Target Users

### Primary Users

**The Solo Developer (You)**

- **Name**: Tisone (that's you!)
- **Role**: Python Developer, ~5 years experience
- **Background**: Full-stack developer with Python focus, building scrapamoja as a personal project
- **Context**: Maintains the Flashscore scraper as a personal tool, no team, no plans to offer as service

**Problem Experience:**
- **Discovery**: Currently discovers selector failures by manually checking output and noticing missing data - no automatic alerting
- **Time to Fix**: Typically 1-4 hours per failure to identify the broken selector, understand the new DOM structure, and craft a replacement
- **Current Workarounds**: None effective - just accepts the manual maintenance burden
- **Emotional Impact**: "Frustrated but resigned" - has accepted this as part of scraping but knows it shouldn't be this hard

**Success Vision:**
- **Primary Goal**: Trust the data without manual verification
- **Aha Moment**: "I can wake up and just know it worked"
- **What Changes**: No more checking output first thing; confidence in data quality; ability to focus on new features instead of maintenance
- **Quote**: "I want my scraper to just work without constant babysitting"

### Secondary Users

**N/A** - This is a solo project with no current plans to expand to other users or offer as a service.

### User Journey

1. **Discovery**: You've been dealing with selector failures for months, each one requiring manual debugging
2. **Onboarding**: After integration, minimal onboarding - just configure adaptive module and let it run
3. **Core Usage**: Scraper runs automatically; adaptive system handles failures silently in background
4. **Success Moment**: You realize it's been X days/weeks since you last had to fix a selector manually
5. **Long-term**: The system gets smarter over time; maintenance burden decreases; you can focus on building new features

## Success Metrics

### User Success Metrics

**Primary Success Criteria:**

| Metric | Current State | Target | Timeline |
|--------|---------------|--------|----------|
| Manual Intervention Frequency | Daily | < 1x/month | 6 months |
| Fallback Success Rate | N/A (no fallbacks) | ≥80% | 6 months |
| Maintenance Time | 10 hrs/month | < 2 hrs/month (80% reduction) | 6 months |

**Key Indicators:**

1. **Manual Intervention Frequency** (Priority #1)
   - **Definition**: Number of times developer must manually fix or investigate selector issues
   - **Current**: Daily intervention required to check outputs and fix broken selectors
   - **Target**: Less than once per month
   - **Measurement**: Logged manual intervention events per time period

2. **Fallback Success Rate** (Priority #2)
   - **Definition**: Percentage of selector failures where fallback strategies successfully recover data
   - **Current**: No fallback system exists
   - **Target**: ≥80% of selector failures are automatically recovered
   - **Measurement**: (Fallbacks that recovered data / Total fallback attempts) × 100

3. **Maintenance Time Reduction** (Priority #3)
   - **Definition**: Total time spent on selector-related maintenance per month
   - **Current**: ~10 hours/month debugging and fixing selectors
   - **Target**: < 2 hours/month (80% reduction)
   - **Measurement**: Tracked time spent on selector maintenance tasks

### Business Objectives

**N/A** - This is a personal/solo project with no revenue or business metrics.

**Personal Development Impact:**
- Time saved: ~8+ hours/month can be redirected to:
  - New feature development
  - Other projects
  - Reduced stress and maintenance burden

**Note:** All adaptive services (confidence scoring, learning, health API) are already built. The integration work simply wires flashscore to use them.

### Key Performance Indicators

| KPI | Target | Measurement Method |
|-----|--------|-------------------|
| Fallback Wiring Success | ≥50% (MVP), ≥80% (full) | Adaptive alternative used / Total failures |
| Failure Capture Rate | 100% | Failures logged to adaptive DB |
| YAML Hints Coverage | 100% critical selectors | Selectors with hint schema |
| Integration Regression | 0 breaks | Existing scraper functionality |

**Milestones:**

- **MVP (3 months)**:
  - Basic fallback chain working for critical selectors
  - 50% reduction in manual intervention
  - Fallback success rate ≥50%

- **Full Release (6 months)**:
  - Full adaptive system operational
  - 80% reduction in manual intervention
  - Fallback success rate ≥80%
  - Maintenance time < 2 hrs/month

## MVP Scope

**Important**: The adaptive selector module (`src/selectors/adaptive/`) is already fully built with:
- Failure detection and analysis
- Multi-strategy DOM analysis for alternative generation
- Confidence scoring with tiered classification
- REST API + WebSocket for verification workflow
- Feature flag management
- Audit logging

**This brief covers ONLY the integration work** — wiring the existing module into flashscore. No new adaptive features are being built.

### Core Integration Tasks (In Priority Order)

**#1 Priority: Fallback Chain Wiring**
- Connect flashscore extractors to adaptive's resolution pipeline
- When primary selector fails → trigger adaptive alternative generation
- Pass resolution context: sport, site, recipe, error type
- Handle response: use adaptive's alternative or mark as failed
- Target: ≥50% fallback success rate in MVP

**#2 Priority: YAML Hints Integration**
- Add hint schema to existing YAML selectors
- Hint fields: priority, stability, fallback_references, strategy_hints
- Map existing selectors to adaptive's expected format
- Initial hint population for critical selectors

**#3 Priority: Failure Capture Wiring**
- Wire sync failure capture to send failures to adaptive's FailureEvent model
- Capture: selectorId, pageUrl, timestamp, failureType, extractorId, attemptedFallbacks[]
- Structured logging to file (also sent to adaptive DB)
- Enable adaptive's stability analysis with real failure data

### Out of Scope for MVP

**Not building these** — they already exist in the adaptive module:

1. ~~Confidence Scoring~~ - Already built in adaptive module
2. ~~Learning System~~ - Already built (failure analysis, pattern recognition)
3. ~~Health API~~ - Already built in adaptive's REST API
4. ~~WebSocket Support~~ - Already built for real-time updates
5. ~~Blast Radius Calculator~~ - Already built in adaptive module
6. ~~Feature Flag Management~~ - Already built in adaptive module
7. ~~Audit Logging~~ - Already built in adaptive module
8. ~~Human-in-Loop Verification UI API~~ - Already built

**This integration only:** Fallback wiring, YAML hints, failure capture → to existing adaptive services.

### MVP Success Criteria

**Definition of Done:**
- [ ] Fallback chain handles at least 2 levels for critical selectors
- [ ] Fallback success rate ≥50% on forced failure tests
- [ ] Structured failure logs written to file
- [ ] YAML hints added to all critical selectors
- [ ] Integration does not break existing scraper functionality

**Validation Approach:**
- Force selector failures in test environment
- Verify fallback strategies trigger correctly
- Confirm fallback success rate meets threshold
- Ensure no regression in existing functionality

**Go/No-Go Decision Points:**
- If fallback success rate < 30%: Re-evaluate fallback strategies
- If integration complexity too high: Simplify architecture
- If existing scraper breaks: Rollback and fix integration

### Future Vision (Post-MVP Integration)

Once the integration is complete, leverage the full adaptive module capabilities:

**Phase 2: Enable Full Adaptive Features**
- Enable confidence scoring for all selectors
- Enable learning system with real failure data
- Full blast radius analysis for impact assessment
- Feature flag gradual rollout

**Phase 3: Enhanced Monitoring**
- Configure canary selectors for pre-scrape checks
- Layout version detection for proactive monitoring
- Health dashboard using adaptive's existing API

**Phase 4: Scale & Extend**
- Apply integration pattern to other scraping targets
- Generalize selector engine for non-Flashscore sites
