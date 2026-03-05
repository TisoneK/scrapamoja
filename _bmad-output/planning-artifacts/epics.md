---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-02.md
---

# scrapamoja - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for scrapamoja (Adaptive Selector System), decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

The Adaptive Selector System extends the existing YAML selector engine with cooperative, human-in-loop selector generation, versioned recipes, audit logging, escalation UI, and weight-based learning.

## Requirements Inventory

### Functional Requirements

**Selector Failure Detection & Capture:**
- FR1: System can detect when a selector fails during extraction
- FR2: System captures DOM snapshot at time of failure
- FR3: System records failure context (sport, status, page state)

**Alternative Selector Proposal:**
- FR4: System analyzes DOM structure and proposes multiple alternative selector strategies
- FR5: System provides confidence scores for each proposed selector
- FR6: System shows blast radius (what other selectors might be affected)

**Human Verification Workflow:**
- FR7: Users can view proposed selectors with visual previews
- FR8: Users can approve or reject proposed selectors
- FR9: Users can flag selectors for developer review
- FR10: Users can create custom selector strategies

**Learning & Weight Adjustment:**
- FR11: System learns from human approvals to increase confidence of similar selectors
- FR12: System learns from human rejections to avoid similar strategies
- FR13: System tracks selector survival across layout generations

**Versioned Recipes:**
- FR14: System creates recipe versions when selectors are updated
- FR15: System tracks stability score per recipe
- FR16: System supports recipe inheritance (Parent → Child)

**Audit Logging:**
- FR17: System records every human decision with full context
- FR18: System maintains complete audit trail of selector changes
- FR19: Users can query audit history by selector, date, or user

**Escalation UI:**
- FR20: UI shows clear dashboard of failures (what broke, why, alternatives)
- FR21: UI supports both technical and non-technical views
- FR22: UI provides fast triage workflow (< 5 min to resolve)

**Feature Flags:**
- FR23: System can enable/disable adaptive system per sport
- FR24: System can enable/disable adaptive system per site

### NonFunctional Requirements

**Performance:**
- NFR1: Escalation UI Response Time: User can complete full approval workflow in < 5 minutes
- NFR2: Selector Proposal Generation: System generates alternative selector proposals within 30 seconds of failure detection
- NFR3: Learning System Latency: Weight adjustments are applied within 1 second of human decision

**Scalability:**
- NFR4: Multi-Site Support: System architecture supports adding new sites without code changes (feature flags)
- NFR5: Recipe Storage: System can store and manage 1000+ recipe versions without performance degradation
- NFR6: Concurrent Users: Support at least 5 concurrent users in escalation UI

**Accessibility:**
- NFR7: Non-Technical UI: Escalation UI must be usable by non-technical operations team members
- NFR8: Visual Previews: Selector proposals include visual DOM previews (not just code)
- NFR9: Clear Language: Error messages and failure descriptions use plain language

**Integration:**
- NFR10: YAML Compatibility: All selector configurations remain in YAML format
- NFR11: Selector Engine Integration: Must integrate with existing multi-strategy selector resolution
- NFR12: Playwright Integration: Must work with Playwright for DOM snapshot capture
- NFR13: Hot Reload: Configuration changes can be applied without restarting the system

### Additional Requirements

**From Architecture - Technical Requirements:**
- Starter: Existing scrapamoja codebase (brownfield extension project)
- Backend: FastAPI for Escalation UI REST API
- Database: SQLite (MVP) / PostgreSQL (production)
- ORM: SQLAlchemy 2.0 with async support
- Frontend: React + TypeScript + Vite + Tailwind CSS
- Authentication: API Keys (simple, good for integrations)
- Tables Required: recipes, audit_log, weights, feature_flags, snapshots
- New Module: `src/selectors/adaptive/` extending existing selector module

**From Architecture - Integration Points:**
- Selector Engine: Listen for resolution failures
- Snapshot System: Reference captured snapshots
- YAML Config: Extend with recipe metadata
- Site Registry: Per-site feature flags

**From Architecture - Implementation Sequence:**
- Phase 1: Foundation - Set up adaptive module, SQLite database, basic FastAPI endpoints
- Phase 2: Core Workflow - Integrate failure detection, create escalation UI React app
- Phase 3: Intelligence - Implement proposal engine, learning engine, recipe versioning
- Phase 4: Polish - Add audit logging UI, feature flag management, API key management

**From Product Brief - MVP Core Features:**
1. Schema Extension - Extend existing YAML with new metadata fields
2. Audit Log - Record every human decision with full context
3. Escalation UI - Fast triage view (what broke, why, alternatives, blast radius)
4. Weight Adjustment - Per-selector learning from approvals/rejections
5. Feature Flags - Incremental rollout by sport

### FR Coverage Map

| Epic | FRs Covered |
|------|-------------|
| Epic 1: Foundation & Schema | FR1, FR2, FR3, FR14, FR15, FR16 |
| Epic 2: Failure Detection & Capture | FR1, FR2, FR3 |
| Epic 3: Alternative Selector Proposal | FR4, FR5, FR6 |
| Epic 4: Human Verification Workflow | FR7, FR8, FR9, FR10 |
| Epic 5: Learning & Weight Adjustment | FR11, FR12, FR13 |
| Epic 6: Audit Logging | FR17, FR18, FR19 |
| Epic 7: Escalation UI | FR20, FR21, FR22 |
| Epic 8: Feature Flags | FR23, FR24 |

## Epic List

**Epic 1: Foundation & Schema Extension**
- Goal: Extend existing YAML with new metadata fields for recipe versioning and stability tracking

**Epic 2: Failure Detection & Capture**
- Goal: Detect selector failures, capture DOM snapshots, and record failure context

**Epic 3: Alternative Selector Proposal**
- Goal: Analyze DOM structure and propose multiple alternative selector strategies with confidence scores

**Epic 4: Human Verification Workflow**
- Goal: Enable users to view, approve, reject, or create custom selector strategies

**Epic 5: Learning & Weight Adjustment**
- Goal: Learn from human approvals/rejections and track selector survival across generations

**Epic 6: Audit Logging**
- Goal: Record every human decision with full context and maintain queryable audit trail

**Epic 7: Escalation UI**
- Goal: Provide fast triage dashboard for both technical and non-technical users

**Epic 8: Feature Flags**
- Goal: Enable incremental rollout by sport and site

---

## Epic 1: Foundation & Schema Extension

**Goal:** Extend existing YAML configuration with new metadata fields for recipe versioning, stability scoring, and generation tracking.

### Story 1.1: Extend YAML Schema with Recipe Metadata

As a **System Architect**,
I want to extend the existing YAML configuration schema with new metadata fields
So that recipe versioning and stability tracking can be stored alongside selector configurations.

**Acceptance Criteria:**

**Given** an existing YAML selector configuration
**When** the system loads the configuration
**Then** it should recognize and parse new metadata fields: recipe_id, stability_score, generation, parent_recipe_id
**And** the fields should be optional to maintain backward compatibility with existing configs

**Given** a YAML configuration with recipe metadata
**When** the system serializes it back to YAML
**Then** the metadata fields should be preserved exactly as defined

### Story 1.2: Create Recipe Version Storage

As a **System**,
I want to store recipe versions in a database
So that I can track selector stability over time and support inheritance.

**Acceptance Criteria:**

**Given** a recipe configuration with metadata
**When** it is first created
**Then** it should be stored in the recipes table with all required fields
**And** the initial version number should be 1

**Given** an existing recipe
**When** selectors are updated
**Then** a new version should be created with incremented version number
**And** the parent_version_id should reference the previous version

### Story 1.3: Implement Recipe Stability Scoring

As a **System**,
I want to calculate and store stability scores for each recipe
So that selectors can be ranked by survival probability.

**Acceptance Criteria:**

**Given** a recipe with multiple versions
**When** a selector resolves successfully over time
**Then** the stability score should incrementally increase
**And** the score should be calculated based on layout generations survived

**Given** a recipe with failed selectors
**When** the failure is detected
**Then** the stability score should be recalculated
**And** the score should decrease based on failure severity

---

## Epic 2: Failure Detection & Capture

**Goal:** Detect when selectors fail during extraction, capture DOM snapshots, and record failure context.

### Story 2.1: Detect Selector Resolution Failures

As a **System**,
I want to detect when a selector fails during extraction
So that I can trigger the adaptive workflow.

**Acceptance Criteria:**

**Given** a selector being resolved by the selector engine
**When** the resolution returns no results or an error
**Then** the failure should be detected and logged
**And** the failure event should include: selector_id, sport, site, timestamp, error_type

**Given** a failed selector
**When** the failure occurs
**Then** it should emit a failure event to the adaptive system
**And** the event should be processed within 1 second

### Story 2.2: Capture DOM Snapshot at Failure

As a **System**,
I want to capture a DOM snapshot at the time of failure
So that the snapshot can be used to propose alternative selectors.

**Acceptance Criteria:**

**Given** a selector failure event
**When** the failure is detected
**Then** a DOM snapshot should be captured using Playwright
**And** the snapshot should be stored with reference to the failure event

**Given** a captured snapshot
**When** it is stored
**Then** it should include: HTML content, viewport size, user agent, timestamp
**And** the snapshot should be compressed to save storage space

### Story 2.3: Record Failure Context

As a **System**,
I want to record comprehensive failure context
So that failures can be analyzed and proposed fixes can be evaluated.

**Acceptance Criteria:**

**Given** a selector failure
**When** the failure is recorded
**Then** it should capture: sport, page state, tab type, previous selector strategy used, confidence score at time of failure

**Given** failure context is recorded
**When** querying failures
**Then** the context should be filterable by sport, date range, selector type

---

## Epic 3: Alternative Selector Proposal

**Goal:** Analyze DOM structure and propose multiple alternative selector strategies with confidence scores.

### Story 3.1: Analyze DOM Structure

As a **System**,
I want to analyze the captured DOM snapshot
So that I can identify alternative selector strategies.

**Acceptance Criteria:**

**Given** a DOM snapshot from a failed selector
**When** the analysis runs
**Then** it should identify potential alternative selectors using multiple strategies: CSS, XPath, text anchor, attribute match, DOM relationships, role-based

**Given** the DOM analysis
**When** it identifies alternatives
**Then** each alternative should include: selector string, strategy type, confidence score

### Story 3.2: Generate Confidence Scores

As a **System**,
I want to calculate confidence scores for proposed selectors
So that users can make informed decisions.

**Acceptance Criteria:**

**Given** multiple proposed selector alternatives
**When** confidence scores are calculated
**Then** scores should range from 0.0 to 1.0
**And** the scoring should consider: historical stability, selector specificity, DOM structure similarity

**Given** proposed selectors with confidence scores
**When** they are displayed to users
**Then** they should be sorted by confidence score (highest first)

### Story 3.3: Calculate Blast Radius

As a **System**,
I want to calculate the blast radius for each proposed fix
So that users understand the impact of approving a selector change.

**Acceptance Criteria:**

**Given** a proposed selector fix
**When** blast radius is calculated
**Then** it should identify all selectors that share ancestor containers with the proposed selector
**And** the blast radius should indicate: how many selectors might be affected, which sports might be impacted

**Given** blast radius information
**When** displayed in the UI
**Then** it should clearly show: affected selector count, affected sports, severity level

---

## Epic 4: Human Verification Workflow

**Goal:** Enable users to view proposed selectors, approve or reject them, and create custom selector strategies.

### Story 4.1: View Proposed Selectors with Visual Preview

As a **Python Developer**,
I want to view proposed selectors with visual previews
So that I can understand what the selector will capture before approving.

**Acceptance Criteria:**

**Given** a selector failure with proposed alternatives
**When** I view the failure details
**Then** I should see: the failed selector, each proposed alternative with confidence score, visual preview highlighting what each selector captures

**Given** the visual preview
**When** displayed
**Then** it should clearly show: matched elements highlighted, unmatched elements dimmed, context around the match

### Story 4.2: Approve or Reject Proposed Selectors

As a **User**,
I want to approve or reject proposed selectors
So that the system can apply the selected selector and learn from my decision.

**Acceptance Criteria:**

**Given** proposed selector alternatives
**When** I click "Approve" on one
**Then** the selected selector should be applied to the recipe
**And** the approval should be recorded in the audit log
**And** the learning system should be updated

**Given** proposed selector alternatives
**When** I click "Reject" on one
**Then** the rejection should be recorded with my reason
**And** the learning system should be updated to avoid similar strategies

### Story 4.3: Flag Selectors for Developer Review

As an **Operations Team Member**,
I want to flag selectors for developer review
So that complex cases can be handled by technical team members.

**Acceptance Criteria:**

**Given** a proposed selector with low confidence
**When** I am unsure about approving it
**Then** I should be able to flag it for developer review
**And** the flag should include my note about what I'm unsure about

**Given** a selector flagged for review
**When** a developer views it
**Then** they should see: the flag note, the proposed alternatives, the failure context

### Story 4.4: Create Custom Selector Strategies

As a **Python Developer**,
I want to create custom selector strategies
So that I can handle edge cases that the system cannot auto-propose.

**Acceptance Criteria:**

**Given** the escalation UI
**When** I want to create a custom selector
**Then** I should be able to: enter custom selector string, specify strategy type, add notes about my approach

**Given** a custom selector I created
**When** I submit it
**Then** it should be treated as a proposed alternative
**And** my custom strategy should be recorded for learning purposes

---

## Epic 5: Learning & Weight Adjustment

**Goal:** Learn from human approvals and rejections to improve future selector proposals.

### Story 5.1: Learn from Approvals

As a **System**,
I want to learn from human approvals
So that future selector proposals improve in accuracy.

**Acceptance Criteria:**

**Given** a human approves a proposed selector
**When** the approval is recorded
**Then** the weight of the selector strategy should increase
**And** similar selector strategies should get a slight weight boost

**Given** approvals accumulate over time
**When** proposing new selectors
**Then** strategies that have been approved before should receive higher confidence scores

### Story 5.2: Learn from Rejections

As a **System**,
I want to learn from human rejections
So that similar selector strategies are avoided in the future.

**Acceptance Criteria:**

**Given** a human rejects a proposed selector
**When** the rejection is recorded
**Then** the weight of that selector strategy should decrease
**And** the rejection reason should be analyzed to identify patterns to avoid

**Given** rejections accumulate over time
**When** proposing new selectors
**Then** strategies that have been rejected before should receive lower confidence scores

### Story 5.3: Track Selector Survival Across Generations

As a **System**,
I want to track selector survival across layout generations
So that stability scores can be calculated accurately.

**Acceptance Criteria:**

**Given** a recipe version
**When** selectors survive a layout generation change on the target site
**Then** the generation_survived count should increment
**And** the stability score should reflect the survival rate

**Given** a selector that fails
**When** the failure is detected
**Then** it should be recorded as a generation failure
**And** the recipe should be marked for review

---

## Epic 6: Audit Logging

**Goal:** Record every human decision with full context and maintain a queryable audit trail.

### Story 6.1: Record Human Decisions

As a **System**,
I want to record every human decision with full context
So that there is a complete audit trail.

**Acceptance Criteria:**

**Given** a human takes an action (approve, reject, flag, create custom)
**When** the action is processed
**Then** it should be recorded in the audit_log table with: action_type, selector_id, user_id, timestamp, context_snapshot

**Given** a decision is recorded
**When** stored
**Then** it should include: before_state, after_state, reason_if_provided, confidence_at_time

### Story 6.2: Maintain Complete Audit Trail

As a **System**,
I want to maintain a complete audit trail of selector changes
So that changes can be traced back to their source.

**Acceptance Criteria:**

**Given** multiple decisions over time
**When** viewing the audit trail
**Then** it should show: chronological history, connected decisions (e.g., reject after approval), user attribution

**Given** the audit trail
**When** needed for compliance
**Then** it should be exportable in standard formats (JSON, CSV)

### Story 6.3: Query Audit History

As a **User**,
I want to query audit history by selector, date, or user
So that I can investigate past decisions.

**Acceptance Criteria:**

**Given** the audit log
**When** I query by selector_id
**Then** I should see all decisions related to that selector

**Given** the audit log
**When** I query by date range
**Then** I should see all decisions within that period

**Given** the audit log
**When** I query by user
**Then** I should see all decisions made by that user

---

## Epic 7: Escalation UI

**Goal:** Provide a fast triage dashboard that supports both technical and non-technical users.

### Story 7.1: Failure Dashboard

As a **User**,
I want to see a clear dashboard of failures
So that I can quickly understand what broke and prioritize fixes.

**Acceptance Criteria:**

**Given** multiple selector failures
**When** I view the dashboard
**Then** I should see: list of failures, what broke, why it broke, severity level

**Given** the dashboard
**When** failures exist
**Then** they should be sorted by: severity, time since failure, blast radius

### Story 7.2: Technical and Non-Technical Views

As a **User**,
I want views appropriate to my technical level
So that I can efficiently do my job without being overwhelmed.

**Given** a non-technical user (Operations)
**When** viewing the UI
**Then** they should see: plain language descriptions, visual previews, simple approve/reject actions

**Given** a technical user (Developer)
**When** viewing the UI
**Then** they should see: full selector details, DOM structure, confidence score breakdown, ability to create custom strategies

### Story 7.3: Fast Triage Workflow

As a **User**,
I want to complete the approval workflow in under 5 minutes
So that selector failures don't block data pipelines.

**Acceptance Criteria:**

**Given** a simple selector failure with clear proposed fix
**When** I approve the fix
**Then** the entire workflow (view → understand → approve) should take less than 5 minutes

**Given** the escalation UI
**When** loaded
**Then** initial page load should be under 2 seconds
**And** each action should respond within 500ms

---

## Epic 8: Feature Flags

**Goal:** Enable incremental rollout by sport and site through a feature flag system.

### Story 8.1: Sport-Based Feature Flags

As a **System Administrator**,
I want to enable/disable the adaptive system per sport
So that I can roll out features gradually.

**Acceptance Criteria:**

**Given** the feature flag system
**When** I enable the adaptive system for Basketball
**Then** only Basketball selectors should trigger the adaptive workflow

**Given** the feature flag system
**When** I disable the adaptive system for a sport
**Then** selectors for that sport should use the traditional fallback mechanism

### Story 8.2: Site-Based Feature Flags

As a **System Administrator**,
I want to enable/disable the adaptive system per site
So that I can test on specific sites before full rollout.

**Acceptance Criteria:**

**Given** the feature flag system
**When** I enable the adaptive system for Flashscore
**Then** only Flashscore selectors should trigger the adaptive workflow

**Given** the feature flag system
**When** I disable the adaptive system for a site
**Then** selectors for that site should use the traditional fallback mechanism

### Story 8.3: Feature Flag Management UI

As a **System Administrator**,
I want a UI to manage feature flags
So that I can easily configure rollout settings.

**Acceptance Criteria:**

**Given** the feature flag management UI
**When** I view current flags
**Then** I should see: all flags, current status (enabled/disabled), last modified

**Given** the feature flag management UI
**When** I toggle a flag
**Then** the change should take effect immediately (hot-reload)
**And** the change should be recorded in audit log
