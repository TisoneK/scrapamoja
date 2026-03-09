---
stepsCompleted: [1, 2]
inputDocuments: []
session_topic: 'Adaptive Selectors × Flashscore Integration'
session_goals: 'Design integration architecture between adaptive selector engine and flashscore scraper, plan migration strategy, define failure capture flow, identify missing pieces for MVP'
selected_approach: 'AI-Recommended Techniques'
techniques_used: ['Mind Mapping']
ideas_generated: ['Hybrid wiring: Orchestrator (major decisions) + Extractors (fine-grained fallback)', 'Hybrid YAML: hints in YAML, adaptive engine handles resolution', 'Two-tier failure capture: sync for critical selectors, async for learning', 'Comprehensive health API: confidence scores, blast radius, dashboard', 'Proactive monitoring: canary selectors, layout detection', 'Partial dependency mapping exists - needs augmentation']
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Tisone
**Date:** 2026-03-06

## Session Overview

**Topic:** Adaptive Selectors × Flashscore Integration
**Goals:** Design integration architecture between adaptive selector engine and flashscore scraper, plan migration strategy, define failure capture flow, identify missing pieces for MVP

### Context

The user has two modules to integrate:
- `src/selectors/adaptive/` — General-purpose adaptive selector engine with confidence scoring, failure detection, DOM analysis, blast radius calculation, custom strategies & fallback recipes, REST API + DB persistence
- `src/sites/flashscore/` — Live scraper with YAML-defined selectors, sport-specific extractors, scrapers + orchestrator

**Integration Problem:** Flashscore selectors are static — they either work or silently fail. The adaptive module exists but is not wired in.

**Four Questions to Brainstorm:**
1. Wiring: How does the adaptive engine slot into the scraping flow?
2. Selector migration: What changes to the YAML selectors?
3. Failure capture: How do failures flow from flashscore → adaptive DB?
4. New selectors for adaptive features

**Constraints:** Flashscore page structure changes frequently; REST API allows in-process or out-of-process integration; blast radius requires selector → extractor → data field dependency mapping

---

## Mind Map Results

### Integration Architecture (Mind Mapping Technique)

```
Flashscore Adaptive Integration
├── Wiring Architecture ✓
│   └── Hybrid: Orchestrator (major decisions) + Extractors (fine-grained fallback)
├── Selector Layer ✓
│   └── Hybrid: YAML has hints, adaptive engine handles resolution
├── Failure Pipeline ✓
│   └── Two-tier failure capture:
│       • Sync (immediate): Post-query intercept → trigger fallback chain
│       • Async (learning): Validation layer → fire-and-forget to adaptive DB
│   └── Failure event: { selectorId, pageUrl, timestamp, failureType, extractorId, attemptedFallbacks[] }
├── Health Signals ✓
│   └── Comprehensive Health API:
│       • Per-selector confidence score + historical trend
│       • Blast radius - extractor/data field impact
│       • Selector health dashboard - failing/degraded/healthy
├── New Probes (Nice-to-Have)
│   └── Proactive selector monitoring:
│       • Canary selectors - lightweight pre-scrape checks
│       • Layout version fingerprint
│       • Pre-scrape health check API
└── Data Dependencies
    └── Partial mapping exists in extractor definitions - needs augmentation
```

---

## MVP+ Scope Definition

### Phase 1: MVP (Basic Wiring + Failure Capture)
- Hybrid orchestrator/extractor wiring
- YAML hints + adaptive resolution
- Sync failure capture for critical selectors
- Basic failure logging

### Phase 2: MVP+ (Add Health API)
- Comprehensive health API
- Confidence score tracking
- Selector health dashboard
- Async failure capture for learning
- Partial blast radius (extractor-level)

### Phase 3: Nice-to-Have
- Canary selectors
- Layout version detection
- Pre-scrape health checks
- Full dependency mapping for accurate blast radius

---

## Identified Missing Pieces

1. **Selector → Extractor → Data Field Mapping** — Partial exists, needs augmentation
2. **YAML Hint Schema** — Define what hints look like (priority, stability, fallback references)
3. **Adaptive API Contract** — Define how flashscore calls adaptive engine (in-process vs HTTP)
4. **Failure Event Schema** — Standardize failure event structure for adaptive DB

---

## Suggested Next Steps

1. Create YAML hint schema proposal
2. Define adaptive API contract (in-process vs HTTP decision)
3. Prototype sync failure capture in one extractor
4. Map existing extractor → data field dependencies
