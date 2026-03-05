---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Designing a cooperative extraction agent for Scrapamoja that uses page snapshots + human guidance to generate complete YAML selector configurations for all Flashscore match page data'
session_goals: '1. Agent methodology: Inspect snapshots, detect page state, identify tab context, propose YAML selectors
2. YAML selector schema: State-aware fields, tab-scoped fields, reusable patterns, metadata for validation
3. Human-in-the-loop workflow: Agent proposes, human verifies, agent learns, configs versioned
4. Capture architecture: Snapshot → DOM segmentation → field detection → YAML generation, modular extractors, page-state rules, change-resilience'
selected_approach: 'Progressive Technique Flow'
techniques_used: ['What If Scenarios', 'Concept Blending', 'Morphological Analysis', 'SCAMPER Method', 'Decision Tree Mapping']
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Tisone
**Date:** 2026-03-02

## Session Overview

**Topic:** Designing a cooperative extraction agent for Scrapamoja that uses page snapshots + human guidance to generate complete YAML selector configurations for all Flashscore match page data

**Goals:**
1. Agent methodology: Inspect snapshots, detect page state, identify tab context, propose YAML selectors
2. YAML selector schema: State-aware fields, tab-scoped fields, reusable patterns, metadata for validation
3. Human-in-the-loop workflow: Agent proposes, human verifies, agent learns, configs versioned
4. Capture architecture: Snapshot → DOM segmentation → field detection → YAML generation, modular extractors, page-state rules, change-resilience

### Current Architecture Context

The user has provided details about their existing FlashScore selector architecture:

**Hierarchical Design:**
- 4-level structure: sport → status → context → element
- Example: basketball → live → match_summary → home_team

**Key Components:**
1. Context-Aware System with Primary (authentication, navigation, extraction, filtering), Secondary (match_list, match_summary, match_stats, etc.), and Tertiary (inc_ot, ft, q1, q2, etc.) contexts
2. DOM State: LIVE, SCHEDULED, FINISHED, UNKNOWN
3. Multi-Strategy Approach with CSS, XPath, weighted confidence, automatic fallback
4. Sport & Status Awareness with sport-specific and status-specific selectors

**Directory Organization:**
- selectors/authentication/, extraction/match_list/, match_summary/, match_stats/, match_odds/, match_h2h/, filtering/, navigation/

**Loading Strategy:** Sport-specific → Status-specific → Generic

**Key Benefits:** Resilient to UI changes, context-aware, maintainable (YAML-based), extensible, observable

---

## Technique Selection

**Approach:** Progressive Technique Flow
**Journey Design:** Systematic development from exploration to action

**Progressive Techniques:**

- **Phase 1 - Exploration:** What If Scenarios + Concept Blending for maximum idea generation
- **Phase 2 - Pattern Recognition:** Morphological Analysis for organizing insights
- **Phase 3 - Development:** SCAMPER Method for refining concepts
- **Phase 4 - Action Planning:** Decision Tree Mapping for implementation planning

**Journey Rationale:** Systematic progression from wild ideas about the cooperative extraction agent to structured implementation planning

---

## Phase 1: Expansive Exploration - What If Scenarios

### Key Breakthroughs from Exploration:

#### 1. Snapshot → Selector Recipe Compiler
The agent transforms page snapshots into reusable "selector recipes" that:
- Segment DOM into structural regions aligned with hierarchy (sport → status → context → element)
- Detect candidate data fields within each region
- Generate multi-strategy YAML selectors with confidence and metadata
- Produce versioned recipes reusable across match states and sports
- Compare snapshots across live/scheduled/finished to detect field variance
- Suggest schema or context extensions when new data structures appear

#### 2. DOM Segmentation Strategy (Hybrid Structural Inference)
- **Primary:** Repeated container patterns, node density clusters, label-value pair proximity, stable ancestor containers
- **Supporting:** Flex/grid grouping, alignment patterns, block separation, tab-scoped visibility
- **Weak Signals:** Role attributes, ARIA labels, heading hierarchy
- **On Layout Change:** Attempt structural remapping using similarity scoring, downgrade confidence if region mapping shifts, flag "layout generation change" when similarity < threshold

#### 3. Three-Tier Selector Strategy
Ranked by survival probability (not specificity):
- **Tier 1:** Structural anchors (ancestor + role + position pattern)
- **Tier 2:** Semantic class patterns
- **Tier 3:** Direct class or XPath matches
- Balance precision vs resilience: score selectors on uniqueness AND structural stability, allow ambiguity if semantic validation resolves it, attach stability_score separate from match_confidence

#### 4. Versioned Recipe Model
Recipe contains:
- recipe_id, applicable_sport, applicable_status
- structural_regions, field_definitions, selector_strategies
- generation_reasoning, stability_profile, layout_signature
- **Composability:** Recipes inherit regions through region inheritance (e.g., base_match_identity + live_score_cluster + sport_specific_stats)

#### 5. Field Variance Detection
Across snapshots, classify fields as:
- invariant, state-dependent, tab-dependent, volatile
- Each selector receives: stability_score, state_coverage, layout_generations_observed

#### 6. Recipe Inheritance Architecture
- Parent → Child → Grandchild specialization chain
- Children inherit regions and override only what differs
- Maintenance becomes surgical - change parent, children inherit

#### 7. Selector Family Detection
- Selectors share ancestor containers (same "gene pool")
- Fail together = likely same CSS framework change
- CSS framework patterns as "family signatures"
- Enables: targeted migration, early-warning through family instability, automatic propagation of improvements

#### 8. Stability Tracking Over Time
- Layout generations survived = recipe confidence
- Metrics: match_success_rate, variance_score, decay_rate
- Early warning: increased retry attempts, longer match times, lower confidence scores
- Predictive stability based on update patterns

#### 9. Human-in-the-Loop Balance
- **Levels:** Passive Observation → Suggestion Mode → Approved Autonomy → Full Autonomy
- Trust calibration: New recipes = low trust, proven = high trust
- Escalation triggers for automatic level changes
- Undo/rollback mechanisms for failures
- Learning from human rejections

### Agent Reasoning Pipeline

```
Snapshot → structural segmentation → region classification → 
candidate field detection → semantic inference → 
selector strategy synthesis → confidence scoring → 
variance comparison → recipe emission
```

**Human Role:**
- Confirm semantic labels
- Approve schema placement
- Accept or reject recipe

---

## Transition to Phase 2: Pattern Recognition

Using **Morphological Analysis** to systematically map all parameter combinations for the agent capabilities.

**Morphological Analysis Parameters to Explore:**

1. **Input Types:** Snapshot formats, page states, tab contexts
2. **Processing Methods:** DOM segmentation approaches, field detection algorithms, strategy generation
3. **Output Formats:** Recipe structures, YAML schemas, version histories
4. **Learning Modes:** Supervised, unsupervised, reinforcement
5. **Human Interaction Levels:** Passive, suggestion, approval, full autonomy
6. **Stability Mechanisms:** Tracking, prediction, migration

---

### Selected High-Capability System:

| Parameter | Choice |
|-----------|--------|
| Input Processing | Historical snapshot comparison + Multi-page context |
| DOM Segmentation | Hybrid (repeated patterns primary) |
| Selector Generation | Hybrid scoring (survival + uniqueness + semantic) |
| Recipe Complexity | Multi-level inheritance + Dynamic composition |
| Stability | Predictive + Self-healing |
| Human Interaction | Verify-new mode |
| Learning | Human feedback + Automated A/B testing |

---

### Three-Level Learning System:

1. **Per-Selector (Fast, Local, Low-Risk):**
   - Immediate weight adjustment on approval/rejection
   - Updates specific strategy's survival score

2. **Per-Region (Pattern Inference):**
   - If 2+ selectors rejected in same structural region → infer region anchor unstable
   - Trigger re-analysis of entire region

3. **Per-Family (Rule Discovery):****
   - If 3+ modifications share a pattern → extract as new rule
   - Only after 3+ occurrences across different sports/states (prevents overfitting)

---

### SCAMPER Refinements:

**S - Substitute:** AI-auto-approval only when confidence > 0.90 AND field has 5+ survived generations

**C - Combine:** Visual diff + semantic validation = two failure types (structural miss vs. wrong data)

**A - Adapt:** Git model (commits, branches, merges) + CDC patterns for layout change detection

**M - Modify:** Field-criticality-aware thresholds (score/team: 0.85+, stats: 0.65+)

**P - Put to other uses:** Recipe system site-agnostic from day one

**E - Eliminate:** Remove Tier 3 if zero survival after 10 generations

**R - Reverse:** For new sports: human-proposes-agent-validates until 3+ recipes exist

---

### Phase 4: Action Planning - Decision Tree

**Minimal Viable Version (5 Steps):**

1. **Schema Extension** - Extend existing YAML with new metadata fields
2. **Audit Log** - Record every human decision with full context
3. **Escalation UI** - Fast triage view (what broke, why, alternatives, blast radius)
4. **Basic Weight Adjustment** - Per-selector learning from approvals/rejections
5. **Feature Flags** - Incremental rollout by sport

**Build Order:** Schema extension → Audit log → Escalation UI → Weight adjustment → Feature flags (strict sequence)

**Out of MVP:** Multi-level inheritance, cross-sport rule discovery, predictive stability, self-healing, dynamic composition, site-agnostic portability, CDC layout monitoring

**Success Criteria:** MVP works when selector failure produces resolved, committed recipe update in under 5 minutes of human time, with zero manual YAML editing outside escalation UI
