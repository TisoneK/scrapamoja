---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain-skipped", "step-06-innovation-skipped", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish"]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-06.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-03-06-15-17.md"
  - "_bmad-output/project-context.md"
workflowType: 'prd'
classification:
  projectType: 'api_backend'
  domain: 'general'
  complexity: 'low-medium'
  projectContext: 'brownfield'
---

# Product Requirements Document - scrapamoja

**Author:** Tisone
**Date:** 2026-03-06

## Executive Summary

Scrapamoja is an existing production Flashscore scraper. This PRD covers the integration of the fully-built adaptive selector module (`src/selectors/adaptive/`) into the existing flashscore scraper to eliminate selector failure debugging.

### What Makes This Special

- **Integration-Only Approach**: The adaptive selector module already exists with failure detection, alternative generation, confidence scoring, and verification workflow API. This project wires it into flashscore—no new adaptive features are being built.
- **Hybrid Architecture**: Connects existing YAML-defined selectors to adaptive resolution with a two-tier failure capture system (sync for critical selectors, async for learning).
- **Real-Time Updates**: WebSocket integration for live failure notifications and confidence score tracking.

## Project Classification

- **Project Type**: Backend/API Service
- **Domain**: General (Web Scraping / Data Extraction)
- **Complexity**: Low-Medium
- **Project Context**: Brownfield (Existing Production System)

## Success Criteria

### User Success

- **Manual Intervention Frequency**: Reduce from daily to < 1x/month (80% reduction)
- **Fallback Success Rate**: ≥80% of selector failures automatically recovered
- **Maintenance Time**: Reduce from 10 hrs/month to < 2 hrs/month (80% reduction)
- **Trust in Data**: "I can wake up and just know it worked" - confidence in data quality without manual verification

### Business Success

- **Time Saved**: ~8+ hours/month redirected to new feature development
- **Reduced Stress**: Elimination of constant selector maintenance burden

### Technical Success

- **Fallback Wiring Success**: ≥50% (MVP), ≥80% (full release)
- **Failure Capture Rate**: 100% of failures logged to adaptive DB
- **YAML Hints Coverage**: 100% critical selectors with hint schema
- **Integration Regression**: 0 breaks to existing scraper functionality
- **Multi-site Support**: Integration pattern works across flashscore, wikipedia, and future sites

### Measurable Outcomes

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Manual Intervention | Daily | < 1x/month | 6 months |
| Fallback Success Rate | N/A | ≥80% | 6 months |
| Maintenance Time | 10 hrs/mo | < 2 hrs/mo | 6 months |

## Product Scope

### MVP - Minimum Viable Product

- Basic fallback chain for critical selectors (flashscore as primary)
- 50% reduction in manual intervention
- Fallback success rate ≥50%
- YAML hints for critical selectors

### Growth Features (Post-MVP)

- Enable same integration pattern for wikipedia and other sites
- Full adaptive system operational
- 80% reduction in manual intervention
- Health API with confidence scores and blast radius

### Vision (Future)

- Generalize selector engine for any site in the scraper
- Proactive monitoring (canary selectors, layout detection)
- Apply integration pattern to other scraping targets

## User Journeys

### Primary User: The Solo Developer (Tisone)

**Persona:**
- Name: Tisone
- Role: Python Developer, ~5 years experience
- Background: Full-stack developer with Python focus, building scrapamoja as a personal project
- Context: Maintains Flashscore scraper as a personal tool, no team

#### Journey 1: Daily Scraper Operation (Success Path)

**Opening Scene:**
Tisone wakes up each morning and runs the scraper to collect yesterday's sports data. Currently, they have to manually check the output to verify data completeness - a tedious daily ritual.

**Rising Action:**
- Checks scraper logs for any errors
- Reviews data output for missing fields or gaps
- If selectors failed, identifies which one broke, understands the new DOM structure, and crafts replacements

**Climax:**
The moment of truth - "Did the scraper get all the data?" With the adaptive integration, the system automatically falls back to alternative selectors when primary ones fail.

**Resolution:**
- Tisone receives WebSocket notification if any fallback was used
- Confidence scores show which selectors are stable vs degraded
- Trust in data quality without manual verification
- Saved time: ~20-30 min/day checking outputs

#### Journey 2: Selector Failure Recovery (Edge Case)

**Opening Scene:**
Tisone receives a notification that a critical selector failed during the night. In the old world, this meant hours of debugging.

**Rising Action:**
- Opens the adaptive dashboard
- Views the failure event: selectorId, pageUrl, timestamp, failure type
- Sees the fallback that was attempted and whether it succeeded
- If fallback worked: reviews the alternative selector that recovered the data
- If fallback failed: manually investigates the new DOM structure

**Climax:**
The adaptive system either automatically recovered the data (success!) or flagged it for manual attention (still better than silent failures).

**Resolution:**
- Failure logged to adaptive DB for learning
- Blast radius shows impact: which data fields were affected
- Tisone can focus on the few cases that actually need attention

### Journey Requirements Summary

- **Onboarding**: Configure adaptive module integration (minimal - it's wiring existing components)
- **Dashboard**: View selector health, confidence scores, fallback history
- **Notifications**: WebSocket for real-time failure/fallback events
- **Investigation**: Detailed failure analysis with DOM context
- **Maintenance**: Add YAML hints for new selectors

## API Backend Specific Requirements

### API Integration Architecture

**REST API Integration:**
- Adaptive module exposes REST API for:
  - Alternative selector resolution
  - Failure event submission
  - Confidence score queries
  - Health check endpoints
- Integration pattern: In-process or HTTP (local)

**WebSocket Integration:**
- Real-time failure notifications
- Confidence score updates
- Selector health status streaming

### Data Flow Design

**Two-Tier Failure Capture:**
1. **Sync (Immediate):** Post-query intercept → trigger fallback chain
   - For critical selectors that need immediate resolution
   
2. **Async (Learning):** Validation layer → fire-and-forget to adaptive DB
   - For failure analysis and learning

**Failure Event Structure:**
```json
{
  "selectorId": "string",
  "pageUrl": "string", 
  "timestamp": "ISO8601",
  "failureType": "string",
  "extractorId": "string",
  "attemptedFallbacks": []
}
```

### Implementation Considerations

- **In-process vs HTTP:** Decide integration architecture
- **Connection pooling:** Manage adaptive API connections
- **Timeout handling:** Configure appropriate timeouts for API calls
- **Error handling:** Graceful degradation when adaptive services unavailable

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP - The core problem is selector failures causing debugging time. The MVP must solve this specific problem.

**Resource Requirements:** Solo developer (Tisone), Python 3.11+, existing adaptive module already built

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Daily scraper operation with automatic fallback recovery
- Selector failure recovery with dashboard visibility

**Must-Have Capabilities:**
- Fallback chain wiring (2-level minimum)
- YAML hints for critical selectors
- Sync failure capture (immediate)
- 50% fallback success rate target
- Structured failure logging

### Post-MVP Features

**Phase 2 (Growth):**
- Async failure capture for learning system
- Full health API with confidence scores
- Blast radius analysis
- 80% fallback success rate

**Phase 3 (Expansion):**
- Generalize integration pattern to other sites (wikipedia)
- Proactive monitoring (canary selectors)
- Layout version detection
- Full adaptive system operational

### Risk Mitigation Strategy

**Technical Risks:** Integration complexity - mitigated by starting with Flashscore only
**Market Risks:** N/A (personal project)
**Resource Risks:** Solo developer - scope is manageable, adaptive module already built

## Functional Requirements

### MVP Requirements (Phase 1)

#### Fallback Chain Management

- FR1: System can execute primary selector for data extraction
- FR2: System can execute fallback selector when primary fails
- FR3: System can chain multiple fallback levels (minimum 2)
- FR4: System can log fallback attempts with results

#### YAML Hints Integration

- FR5: System can read hint schema from YAML selectors
- FR6: System can use hints to determine fallback strategy
- FR7: System can prioritize selectors based on stability hints

#### Failure Capture & Logging

- FR8: System can capture selector failure events
- FR9: System can log failure events with full context (selectorId, URL, timestamp, failureType)
- FR10: System can submit failure events to adaptive module DB

#### Integration Architecture

- FR17: System can call adaptive REST API for alternative resolution
- FR18: System can handle adaptive service unavailability gracefully
- FR19: System can operate with sync failure capture (immediate)
- FR20: System can operate with async failure capture (learning)

### Phase 2 Requirements (Growth)

#### Real-Time Notifications

- FR11: System can receive WebSocket notifications for failures *(Phase 2)*
- FR12: System can receive confidence score updates *(Phase 2)*
- FR13: System can receive selector health status updates *(Phase 2)*

#### Health & Monitoring

- FR14: System can query adaptive module for selector confidence scores
- FR15: System can display selector health status *(Phase 2)*
- FR16: System can calculate blast radius for failures *(Phase 2)*

## Non-Functional Requirements

### Performance

- **Fallback Resolution Time**: Sync fallback path should not add more than 5 seconds to scraper execution
- **WebSocket Connection**: Maintain stable connection for real-time notifications with automatic reconnection

### Integration

- **Graceful Degradation**: When adaptive services are unavailable, scraper continues with primary selectors only (no fallback)
- **API Timeout Handling**: External API calls have configurable timeouts (default 30s) with appropriate error handling
- **Connection Pooling**: Manage adaptive API connections efficiently to avoid resource exhaustion

### Not Included (Not Applicable)

- **Security**: Personal project, no sensitive data
- **Scalability**: Single user, no growth concerns
- **Accessibility**: No public UI
