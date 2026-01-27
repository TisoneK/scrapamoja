# 🔥 Deep-Research Enhanced Prompt: Production-Grade Flashscore Scraper

## Objective

Design and implement a production-grade, object-oriented, asynchronous Python web scraper using Playwright (async API) that can reliably extract all match-level data from Flashscore.com by fully emulating real human navigation behavior and adapting to Flashscore's dynamic Single Page Application (SPA) architecture and anti-automation defenses.

The scraper must be modular, fault-tolerant, extensible, and stealth-aware, capable of navigating Flashscore's multi-layer UI hierarchy (primary, secondary, tertiary tabs) while maintaining data integrity even under DOM mutations and selector obfuscation.

## 🧠 Key Characteristics of Flashscore (Research-Based Context)

The implementation must explicitly account for the following real-world properties of Flashscore:

### SPA / Client-Side Routing

* Page transitions do not trigger full reloads
* Content is injected dynamically via XHR/fetch calls
* URL changes ≠ DOM readiness

### Aggressive Anti-Bot Detection

Bot signals include:

* Missing browser fingerprints
* Unrealistic click timing
* No mouse movement / scrolling
* Headless-only execution

Detection escalates silently (data simply fails to load).

### Volatile DOM Structure

* CSS class names are frequently obfuscated or rotated
* Stable selectors are often semantic attributes, text anchors, or DOM position patterns
* Scraper must not rely on brittle static class names alone

### Tab-Driven Data Hydration

* Secondary and tertiary tabs do not preload data
* Each tab click triggers new async requests
* Odds and H2H data often load independently and lazily

## 🏗️ Required System Architecture

The scraper must be written in clean, production-ready, object-oriented Python, following separation of concerns and async-safe design.

### Modularity Requirements

**Deep modularity is required** - modules can go as deep as needed, including modules inside modules. Each component should be highly granular with single responsibilities:

* **Core modules** (navigator, tab_controller, extractor)
* **Sub-modules** within each core module (e.g., navigator.stealth, navigator.routing)
* **Utility modules** (retry, logging, validation, data_models)
* **Service modules** (network, browser_management, data_storage)
* **Helper modules** within services (e.g., data_storage.json_handler, data_storage.file_manager)

### Selector Engine (System Backbone)

**🔥 CRITICAL REQUIREMENT: The Selectors Engine is a first-class system component and must be treated as the backbone of the scraper. All extraction logic must rely on semantic selector definitions resolved through a multi-strategy, confidence-scored selector engine with snapshot-backed failure analysis and drift detection. Direct, hardcoded selectors are forbidden outside the Selectors Engine.**

**Core Principle: Selectors represent intent, not implementation.**

**Why Flashscore Demands Selector-Centric Design:**

**1️⃣ DOM Volatility Is Intentional**
* Class names rotate, containers get re-wrapped, child depth shifts
* Meaning stays the same, structure does not
* Only semantic intent survives

**2️⃣ UI ≠ Data**
* Skeleton loaders, placeholder nodes, deferred hydration
* A selector that "exists" is often not ready
* Selectors must encode readiness logic, not just location

**3️⃣ Tabs Are Not Pages**
* Each tab mutates DOM partially, injects new trees, leaves stale siblings
* Selectors must be tab-aware, context-scoped, lifecycle-aware

**🧱 Selector Engine Responsibilities:**

#### 1️⃣ Semantic Abstraction Layer (Mandatory)
Selectors map business meaning → DOM reality:

```python
home_team_name:
  intent: "home team name"
  context: "match_header"
  strategies:
    - text_near("Home")
    - role="heading"
    - dom_path_relative_to("scoreboard")
```

The rest of the system never sees selectors directly.

#### 2️⃣ Multi-Strategy Resolution (Non-Negotiable)
Every selector must have:
* Primary strategy
* Secondary fallback
* Tertiary structural fallback

**Resolution Flow:**
1. Try text anchor
2. Try attribute match
3. Try DOM relationship
4. Validate content
5. Accept or reject

**No single-strategy selectors allowed.**

#### 3️⃣ Confidence Scoring & Validation
Each selector resolution returns:
```python
{
  "element": "...",
  "confidence": 0.87,
  "strategy_used": "text_anchor",
  "validated": True
}
```

**Validation Rules:**
* Text not empty
* Matches expected format
* Located in correct DOM region
* Low confidence → snapshot + warning

#### 4️⃣ Context Scoping (Critical for Tabs)
Selectors must know:
* Which tab they belong to
* Which parent container they must live under
* Which tab state must be active

**Example:** `Selector("odds_row").within("odds_tab_container")`

**Prevents:**
* Cross-tab pollution
* Stale element reuse
* Ghost nodes from previous tabs

#### 5️⃣ DOM Snapshot Integration (Tightly Coupled)
Selectors Engine must trigger snapshots on:
* Failure
* Low confidence
* Structural drift

**Store:**
* Local container DOM
* Surrounding context
* Metadata

**Snapshots are selector artifacts, not navigation artifacts.**

#### 6️⃣ Selector Drift Detection
Track over time:
* Which strategies succeed
* Which fall back
* Which fail

**If primary strategy success rate drops → Flag selector as unstable**

This detects Flashscore changes before full failure.

#### 7️⃣ Adaptive Selector Evolution
Supports:
* Strategy re-ranking based on success rates
* Promotion of reliable fallbacks to primary status
* Blacklisting of consistently failing patterns
* Rule-based adaptation (initially) → learned patterns (later)

**🔥 Selector Engine Components (Theoretical Framework):**

* **Registry System** - Central repository of semantic selector definitions
* **Resolution Engine** - Multi-strategy execution with intelligent fallback logic
* **Strategy Library** - Diverse approaches (text anchors, attributes, DOM relationships, roles, positioning)
* **Validation Framework** - Content verification and sanity checking systems
* **Confidence Scoring** - Quantitative assessment of selector reliability
* **Snapshot Integration** - DOM state capture for failure analysis
* **Drift Detection** - Pattern recognition for structural changes
* **Adaptation Logic** - Evolution mechanisms for selector improvement

**🎯 Bottom Line:**
* Navigation gets you somewhere
* Stealth keeps you alive
* Retries keep you running
* **Selectors determine whether you get data**

**For Flashscore: Selector engineering is 70% of the work.**

## 🔒 Explicit Contracts & Boundaries

### Selector Engine Output Contract

**Formal Contract Between Components:**

**Selector Engine → Extractor/TabController:**

```python
# Confidence Threshold Policy
confidence < 0.6 → return None + automatic snapshot + warning
confidence 0.6–0.8 → return element + warning + continue
confidence > 0.8 → return element + accept
```

**Extractor Behavior:**
* `None` result → Skip extraction, log failure, continue to next element
* Low confidence → Extract but flag as unreliable
* High confidence → Extract normally

**TabController Behavior:**
* Multiple `None` results → Consider tab failed, trigger snapshot
* Consistent low confidence → Flag tab as unstable

### Selector Registry Format

**Hybrid Approach (Recommended):**

**Base Registry (YAML/JSON):**
* Declarative selector definitions
* Easy hotfixes and versioning
* Environment-specific overrides

**Runtime Extensions (Python):**
* Complex validation logic
* Dynamic strategy weighting
* Evolution algorithms

**Versioning Strategy:**
* Semantic versioning for selector sets
* Backward compatibility guarantees
* Migration paths for schema changes

### Research vs Production Boundaries

**Research Mode Configuration:**
* **DOM Snapshots:** Aggressive (tier 1 + tier 2)
* **Retry Limits:** High (5-10 attempts)
* **Confidence Thresholds:** Lenient (accept > 0.5)
* **Rate Limiting:** Conservative (slow but thorough)
* **Logging:** DEBUG level with full traces

**Production Mode Configuration:**
* **DOM Snapshots:** Minimal (failure-only)
* **Retry Limits:** Low (2-3 attempts)
* **Confidence Thresholds:** Strict (require > 0.8)
* **Rate Limiting:** Optimized for speed
* **Logging:** INFO level with errors only

**Mode Switching:**
* Runtime configuration via CLI flags
* Environment-based defaults
* Safety locks to prevent accidental production mode in development

### Run Exit Conditions & Auto-Abort Policies

**Failed Run Definitions:**

**League-Level Failures:**
* > 50% matches fail selector confidence thresholds
* > 30% matches have missing critical tabs
* Consistent soft-block detection across multiple IPs

**Competition-Level Failures:**
* > 70% matches fail extraction
* Persistent DOM structure changes
* All proxy IPs flagged simultaneously

**Auto-Abort Triggers:**
* **Immediate Abort:** Detection escalation across all proxies
* **League Blacklist:** 3 consecutive failed runs → 24-hour blacklist
* **Competition Blacklist:** 5 consecutive failed runs → 72-hour blacklist
* **Soft Abort:** Success rate drops below 20% → finish current match, stop

**Recovery Policies:**
* Automatic retry after blacklist period expires
* Manual override for emergency situations
* Progressive backoff for repeated failures

## 🧭 Implementation Readiness Assessment

### Current Document Status: ✅ Ready

**What You Have Achieved:**
* ✅ Internally consistent architecture
* ✅ Technically realistic approach
* ✅ Production-aware constraints
* ✅ Selector-centric design (correct priority)
* ✅ Explicit contracts and boundaries
* ✅ Clear failure handling policies

### Recommended Next Steps

**Option A - SpecKit Artifacts:**
* Extract formal specifications
* Create implementation tasks
* Mechanical development process

**Option B - Selector Engine Prototype:**
* Build Selector Engine first
* Implement snapshot system
* Validate with single tab (Odds → 1X2)
* Prove backbone before full build

**Option C - Framework Development:**
* Generic Flashscore framework
* Hostile SPA scraping platform
* Reusable architecture

**🎯 Strong Recommendation:**
**Freeze this document and extract a formal "Selector Engine Specification" as a standalone artifact.**

**Why:**
* It is the system backbone
* Everything else depends on it
* It will dictate long-term success or failure

**Final Verdict:**
You are no longer exploring — you are architecting. From here forward, every step should be deliberate and scoped, not additive brainstorming.

## 🔧 Technology Stack Architecture (Layered System Design)

### 1️⃣ Runtime Execution Platform
**What it represents:** The computational environment in which the system lives and executes.

**Responsibilities:**
* Event-driven execution
* Non-blocking task coordination
* Deterministic shutdown and recovery
* Resource lifecycle control

**Technology Category:** Asynchronous execution runtime

**Why it exists:** Flashscore requires waiting, reacting, and coordinating multiple uncertain events without freezing the system.

### 2️⃣ Browser Automation Substrate
**What it represents:** A full browser execution environment capable of rendering, executing, and interacting with modern SPAs.

**Responsibilities:**
* JavaScript execution
* DOM mutation handling
* Client-side routing awareness
* Full rendering pipeline

**Technology Category:** Real browser automation engine

**Why it exists:** Flashscore cannot be scraped at the HTTP layer. The UI is the data source.

### 3️⃣ Interaction Simulation Technology
**What it represents:** Human-behavior emulation at the interaction level.

**Responsibilities:**
* Mouse movement modeling
* Scroll behavior simulation
* Timing irregularity
* Imperfect execution patterns

**Technology Category:** Behavioral interaction simulation

**Why it exists:** Anti-bot systems analyze behavioral entropy, not just headers.

### 4️⃣ Stealth & Identity Masking Layer
**What it represents:** Digital identity control and fingerprint consistency.

**Responsibilities:**
* Browser fingerprint normalization
* Device characteristic realism
* Locale/timezone coherence
* Session continuity

**Technology Category:** Client fingerprint obfuscation & identity management

**Why it exists:** A browser that looks real but behaves unreal is still detectable.

### 5️⃣ Navigation & Routing Intelligence
**What it represents:** Intent-driven movement through a UI graph.

**Responsibilities:**
* Hierarchical route reasoning
* State-aware navigation
* Soft-failure recovery
* Sequential traversal logic

**Technology Category:** UI navigation intelligence

**Why it exists:** SPAs do not expose linear paths — navigation is contextual.

### 6️⃣ Selector Resolution Technology (Core Stack Element)
**What it represents:** The translation of semantic intent into DOM elements.

**Responsibilities:**
* Semantic selector abstraction
* Multi-strategy resolution
* Confidence scoring
* Drift detection

**Technology Category:** Semantic DOM resolution engine

**Why it exists:** DOM structures mutate; meaning persists.

### 7️⃣ DOM State Capture & Forensics
**What it represents:** Historical memory of page structures.

**Responsibilities:**
* DOM snapshot capture
* Contextual element preservation
* Structural comparison
* Failure evidence retention

**Technology Category:** DOM forensics & state archival

**Why it exists:** Long-lived systems require historical context to adapt.

### 8️⃣ Load Validation & Readiness Detection
**What it represents:** Truth verification for UI hydration.

**Responsibilities:**
* Detect skeleton vs real content
* Verify completeness
* Cross-element consistency checks
* Network-DOM correlation

**Technology Category:** Content readiness verification system

**Why it exists:** Presence ≠ readiness in SPA architectures.

### 9️⃣ Data Interpretation & Normalization
**What it represents:** Transformation from UI text into domain knowledge.

**Responsibilities:**
* Sports-domain normalization
* Temporal interpretation
* Odds structure parsing
* Contextual disambiguation

**Technology Category:** Domain-aware data interpretation layer

**Why it exists:** Raw strings are not data — meaning is.

### 🔟 Persistence & Versioned Storage
**What it represents:** Long-term data integrity and evolution.

**Responsibilities:**
* Schema versioning
* Partial data handling
* Historical compatibility
* Atomic persistence

**Technology Category:** Versioned structured data storage

**Why it exists:** Data outlives the scraper version that created it.

### 1️⃣1️⃣ Resilience, Recovery & Continuity
**What it represents:** Operational survivability.

**Responsibilities:**
* Checkpointing
* Resume logic
* Failure isolation
* Graceful degradation

**Technology Category:** Fault-tolerant execution control

**Why it exists:** Production systems fail by default.

### 1️⃣2️⃣ Observability & Diagnostics
**What it represents:** System self-awareness.

**Responsibilities:**
* Structured logging
* Performance metrics
* Failure correlation
* Run traceability

**Technology Category:** Operational observability stack

**Why it exists:** Invisible failures are worse than loud ones.

### 1️⃣3️⃣ Risk, Ethics & Rate Governance
**What it represents:** Operational boundaries.

**Responsibilities:**
* Rate control
* Session longevity protection
* Detection escalation response
* Kill-switch logic

**Technology Category:** Risk governance & policy enforcement

**Why it exists:** Longevity requires restraint.

## 🔗 Final Stack Summary

| Layer | Technology Category |
|-------|-------------------|
| Execution | Async runtime |
| Rendering | Real browser engine |
| Interaction | Human behavior simulation |
| Identity | Fingerprint masking |
| Navigation | UI routing intelligence |
| Selectors | Semantic DOM resolution |
| Memory | DOM forensics |
| Validation | Content readiness verification |
| Interpretation | Domain normalization |
| Storage | Versioned structured persistence |
| Resilience | Fault tolerance |
| Observability | System diagnostics |
| Governance | Risk & rate control |

**🎯 Key Clarification:** This is a tech stack — just not a vendor stack. It defines what kinds of technology must exist, why each exists, and how they relate. Only after this is defined do tools (Playwright, Python, etc.) make sense.

## 🧰 Concrete Tool Stack (Mapped to Flashscore Architecture)

### 1️⃣ Runtime Execution Platform
**Purpose:** Async coordination, lifecycle control

**Tools:**
* Python 3.11+
* asyncio

**Why:** Mature async model, deterministic task scheduling, excellent ecosystem support

### 2️⃣ Browser Automation Substrate
**Purpose:** Execute Flashscore's SPA exactly as a real user sees it

**Tools:**
* Playwright (Python, async API)
* Chromium (primary)
* (Optional) Firefox / WebKit for differential testing

**Why:** True browser execution, first-class SPA handling, strong async support, superior selector + DOM APIs vs Selenium

### 3️⃣ Interaction Simulation Technology
**Purpose:** Human-like UI behavior

**Tools:**
* Playwright native mouse & keyboard APIs
* Custom human-behavior utilities (timing, scrolling, jitter)

**Why:** Precise control over mouse paths, scroll velocity, click hesitation, no external dependency needed

### 4️⃣ Stealth & Identity Masking Layer
**Purpose:** Fingerprint realism & bot-signal reduction

**Tools:**
* playwright-stealth (Python port / custom patches)
* Custom fingerprint normalizer
* User-Agent rotation pool

**Why:** Removes webdriver traces, aligns browser signals, Flashscore flags default Playwright quickly without this

### 5️⃣ Navigation & Routing Intelligence
**Purpose:** Intent-driven movement through SPA routes

**Tools:**
* Custom Navigator module (Python OOP)
* Playwright Page + Locator APIs

**Why:** Navigation logic must be domain-aware, cannot rely on URLs alone in SPA, needs semantic routing logic

### 6️⃣ Selector Resolution Engine (Backbone)
**Purpose:** Semantic → DOM translation

**Tools:**
* Custom Selector Engine (Python)
* Playwright Locators
* Text-based, role-based, relational selector strategies

**Why:** No off-the-shelf library supports multi-strategy selectors, confidence scoring, drift detection - proprietary logic by necessity

### 7️⃣ DOM State Capture & Forensics
**Purpose:** Remember failures, analyze drift

**Tools:**
* Playwright page.content()
* Playwright screenshots
* Local file storage (HTML + metadata)

**Why:** Full DOM snapshots required, needed for selector evolution, enables post-mortem debugging

### 8️⃣ Load Validation & Readiness Detection
**Purpose:** Verify data is real, not skeleton UI

**Tools:**
* Playwright wait_for_selector
* Custom readiness validators
* (Optional) Playwright network event listeners (read-only)

**Why:** networkidle is unreliable for Flashscore, must validate semantic completeness

### 9️⃣ Tab Intelligence Layer
**Purpose:** Manage secondary & tertiary UI states

**Tools:**
* Custom TabController (Python OOP)
* Playwright text-based & hierarchical locators

**Why:** Tabs mutate DOM without clearing old nodes, requires scoped, context-aware control

### 🔟 Data Interpretation & Normalization
**Purpose:** Convert UI text → structured sports data

**Tools:**
* Python standard library (datetime, re, decimal)
* Custom domain parsers

**Why:** Odds, scores, time formats need precision, no external parsing libraries required

### 1️⃣1️⃣ Persistence & Versioned Storage
**Purpose:** Durable, evolvable data output

**Tools:**
* JSON (primary output)
* Local filesystem
* (Optional) SQLite for checkpoints

**Why:** JSON is portable and inspectable, schema versioning is trivial, SQLite useful for resume state

### 1️⃣2️⃣ Resilience & Recovery
**Purpose:** Never lose progress

**Tools:**
* Custom retry decorators
* State manager (JSON / SQLite)
* Graceful shutdown handlers

**Why:** Long-running Playwright sessions will fail, recovery must be native, not bolted on

### 1️⃣3️⃣ Observability & Diagnostics
**Purpose:** Understand behavior over long runs

**Tools:**
* Python logging (JSON structured logs)
* Run-ID / Match-ID correlation
* Performance timers

**Why:** Scrapers fail silently, logs are your only truth

### 1️⃣4️⃣ Proxy & Network Strategy
**Purpose:** IP reputation & session safety

**Tools:**
* Playwright proxy configuration
* Residential proxy providers
* Custom proxy manager

**Why:** Datacenter IPs are fragile, sticky sessions reduce detection, rotation must be intelligent

### 1️⃣5️⃣ Configuration & Control Interface
**Purpose:** Change behavior without code edits

**Tools:**
* YAML / JSON config files
* Environment variables
* CLI argument parser (argparse)

**Why:** Production systems require runtime control, enables experimentation safely

## 🧩 Final Tool Stack Snapshot

| Category | Tools |
|----------|-------|
| Language | Python 3.11+ |
| Async Runtime | asyncio |
| Browser Engine | Playwright (Chromium) |
| Stealth | playwright-stealth + custom |
| Interaction | Playwright mouse/keyboard |
| Selectors | Custom semantic selector engine |
| DOM Memory | HTML snapshots + screenshots |
| Validation | Selector + content validators |
| Data Output | JSON (+ optional SQLite) |
| Logging | Python logging (structured) |
| Proxies | Playwright proxy + residential IPs |
| Config | YAML / JSON / env vars |

**🎯 Key Takeaway:** Playwright is the engine, Python is the nervous system, your selector engine is the brain, everything else is support infrastructure.

## 📚 Module Documentation Standards

### README Requirements for Each Module

**Every module must include its own README.md** with the following structure:

#### **Core Module README Template:**

```markdown
# [Module Name]

## Purpose
[Clear, concise statement of what this module does]

## Responsibilities
- [Key responsibility 1]
- [Key responsibility 2]
- [Key responsibility 3]

## Dependencies
- [Internal dependencies from other modules]
- [External libraries required]

## Public API
### Main Classes/Functions
- `ClassName` - [Brief description]
- `function_name()` - [Brief description]

### Usage Example
```python
# Basic usage example
```

## Configuration
[Any configuration options this module accepts]

## Error Handling
[Common error scenarios and how they're handled]

## Testing Notes
[How to test this module, if applicable]

## Integration Points
[How this module connects to other system components]
```

#### **Module-Specific Documentation Requirements:**

**Selector Engine Modules:**
- Strategy examples and fallback logic
- Confidence scoring thresholds
- Selector drift detection patterns

**Navigator Module:**
- Stealth configuration options
- Browser lifecycle management
- Proxy integration details

**TabController Module:**
- Tab availability detection
- Context scoping rules
- Failure recovery procedures

**Extractor Module:**
- Data normalization rules
- Domain-specific parsing logic
- Output schema definitions

**Storage Modules:**
- Schema versioning approach
- Data migration strategies
- Backup and recovery procedures

### Documentation Hierarchy

**Project-Level Documentation:**
- `README.md` - Project overview and quick start
- `ARCHITECTURE.md` - System design and module relationships
- `DEPLOYMENT.md` - Production deployment guide
- `TROUBLESHOOTING.md` - Common issues and solutions

**Module-Level Documentation:**
- Each module directory contains its own `README.md`
- Inline code documentation for all public APIs
- Example usage in docstrings

### Documentation Maintenance

**Update Requirements:**
- README must be updated with any API changes
- Examples must be kept current with implementation
- Configuration options must be documented when added

**Review Process:**
- Documentation reviewed during code reviews
- Examples tested to ensure they work
- Cross-references between modules verified

### 1. Navigator Class (Browser & Routing Authority)

**Responsibilities:**

* Initialize and manage:
	+ Playwright browser
	+ Browser context
	+ Persistent cookies/session
* Apply stealth configuration:
	+ Custom user-agent rotation
	+ Viewport randomization
	+ Locale, timezone, and language consistency
* Control high-level navigation flow:
	+ Main Page → Sport Page → League Page → Match Page

**Key Design Requirements:**

* Use non-headless mode optionally for debugging
* Simulate:
	+ Natural scrolling
	+ Human-like mouse movement
	+ Randomized dwell times
* Detect and recover from soft-blocks (content partially missing)

### 2. TabController Class (UI Interaction Engine)

**Responsibilities:**

* Abstract all logic related to clicking and validating:
	+ Primary tabs (Match Overview / Match Details)
	+ Secondary tabs (Summary, Odds, H2H, Standings)
	+ Tertiary filters (e.g., Home/Away, Over/Under types)

**Critical Capabilities:**

* Determine tab availability dynamically (some tabs are match-dependent)
* Use text-based or hierarchical selectors instead of fragile class names
* Verify tab success via:
	+ Element-based readiness checks
	+ Presence of known semantic DOM patterns
* Gracefully fail and continue if a tab is unavailable or blocked

### 3. Extractor Class (Data Parsing & Normalization)

**Responsibilities:**

* Extract structured data from a fully rendered DOM state
* Use **only Playwright selectors** for dynamic content extraction
* **No requests library or BeautifulSoup** - rely solely on Playwright's built-in capabilities
* Normalize raw text into typed, schema-safe values

**Data Domains to Extract:**

* Match header metadata
* Team statistics
* Lineups & formations
* Odds markets
* H2H history
* Standings context

## 🧭 Step-by-Step Navigation & Extraction Logic

### Level 1 – Entry Point

* Load Flashscore main landing page
* Accept runtime parameters:
	+ Target sport (e.g., Football)
	+ League or competition URL
* Confirm page hydration (not just load event)

### Level 2 – Match Discovery

* Identify:
	+ Live matches
	+ Scheduled matches
* Extract match URLs robustly
* Iterate sequentially (not parallel — Flashscore flags concurrency)

### Level 3 – Match Details Page

For each match:

* Open match page
* Extract Header Info:
	+ Match ID (from URL)
	+ Home / Away teams
	+ Score
	+ Match status (Live, HT, FT, Scheduled)
	+ Kick-off time

### Level 4 – Secondary & Tertiary Tabs

#### A. Summary Tab

* Extract:
	+ Match statistics (possession, shots, fouls, cards)
	+ Lineups & formations (if available)
* Handle cases where stats appear only after scroll

#### B. Odds Tab

* Click Odds tab
* Iterate tertiary markets:
	+ 1X2
	+ Over / Under
	+ Asian Handicap
* For each market:
	+ Extract bookmaker rows
	+ Capture opening odds and closing odds
* Account for odds tables loading asynchronously and independently

#### C. H2H Tab

* Click H2H tab
* Iterate filters:
	+ Overall
	+ Home
	+ Away
* Extract last 5 completed matches:
	+ Date
	+ Competition
	+ Score
	+ Home/Away designation

#### D. Standings Tab

* Extract:
	+ League rank
	+ Points
	+ Matches played
	+ Recent form (W/D/L pattern)
* Match standings row to correct team reliably

## 🛡️ Technical & Production Requirements

### Legal, Ethical & Operational Constraints

**Risk Posture & Compliance:**

* **Terms of Service Awareness** - Flashscore explicitly disallows scraping in robots.txt
* **Usage Classification** - Designed for personal research and educational purposes only
* **Kill Switch Implementation** - Automatic shutdown on detection escalation
* **Rate Limiting** - Configurable caps per hour/day to avoid blocking

**Production Impact on Stealth:**

* **Conservative Aggression** - Stealth settings adapt based on risk tolerance
* **Proxy Strategy** - Enabled by default for production use
* **Retry Behavior** - Silent retries for research, abort on commercial detection

### Proxy & IP Strategy

**Proxy Management Architecture:**

* **proxy_manager** module with comprehensive IP lifecycle management
* **Residential Proxies** - Primary choice for Flashscore (lower detection risk)
* **Sticky Sessions** - Maintain same IP for entire match extraction
* **Rotating Strategy** - IP rotation between matches, not within matches

**IP Reputation & Health:**

* **Proxy Health Monitoring** - Continuous checking of proxy performance
* **Automatic Retirement** - Remove proxies showing soft-block symptoms
* **Country Targeting** - Match proxy location to desired content locale
* **Reputation Scoring** - Track success rates per proxy

**Missing Modules:**

* **proxy_manager.health_checker** - Monitor proxy performance
* **proxy_manager.rotation_engine** - Smart IP rotation logic
* **proxy_manager.block_detector** - Detect soft-blocking patterns

### Session Lifecycle & Persistence

**Session Management Strategy:**

* **Cross-Run Persistence** - Cookies and sessions saved to disk
* **Session Warming** - Pre-navigation browsing to establish legitimacy
* **Invalidation Detection** - Monitor for session expiration signals
* **Consent Handler** - One-time consent banner handling with reuse

**Persistence Decisions:**

* **Cookie Storage** - Persistent across program executions
* **Session Reuse** - Maintain browser context across multiple matches
* **Consent Caching** - Store consent decisions to avoid repeated interactions

**Impact on Operations:**

* **Detection Risk Reduction** - Established sessions appear more human
* **Performance Improvement** - Skip repeated consent/cookie flows
* **Reliability Enhancement** - Stable session state across long runs

### Consent, Geo & Compliance UI Handling

**UI Obstruction Management:**

* **ConsentHandler** module for GDPR/cookie consent management
* **Geo-UI Adaptation** - Handle locale-dependent interface variations
* **Language Detection** - Auto-detect and adapt to language switches
* **Overlay Detection** - Identify and dismiss blocking UI elements

**Compliance Features:**

* **Consent State Tracking** - Remember consent choices across sessions
* **Geo-Location Awareness** - Adapt selectors based on regional UI differences
* **Banner Dismissal Logic** - Smart handling of various consent modal types

### Network-Layer Intelligence

**Network Monitoring (Read-Only):**

* **network_monitor** module for passive network observation
* **XHR Failure Detection** - Identify failed API calls affecting DOM
* **Tab-Response Correlation** - Link user actions with network responses
* **Readiness Validation** - Use network signals for content load confirmation

**Network-Aware Reliability:**

* **Retry Decision Logic** - Base retry decisions on network error patterns
* **Performance Metrics** - Track network response times and success rates
* **Silent Failure Detection** - Catch issues not visible in DOM

### Data Versioning & Schema Evolution

**Schema Management:**

* **schema_version** field in all output files
* **Backward Compatibility** - Support reading older schema versions
* **Field Deprecation Strategy** - Gradual phase-out of obsolete fields
* **Partial Data Handling** - Graceful handling of missing tabs/sections

**Production Data Challenges:**

* **Missing Tab Scenarios** - Handle matches without odds/H2H/standings
* **Market Evolution** - Adapt to new betting markets being added
* **Field Nullability** - Clear rules for optional vs required data

### Match State Transitions & Live Data Handling

**Match State Awareness:**

* **Live Match Detection** - Identify ongoing vs completed matches
* **Dynamic DOM Handling** - Adapt to changing content during live matches
* **State Transition Logic** - Handle halftime, full-time, postponed matches
* **Odds Availability** - Detect matches without betting markets

**Live Data Strategy:**

* **Repeated Scraping** - Configurable refresh intervals for live matches
* **Final State Waiting** - Option to wait for match completion
* **Partial Data Storage** - Save intermediate live states

### Time & Clock Normalization

**Time Handling Strategy:**

* **Timezone Normalization** - Convert all times to UTC
* **Relative Time Parsing** - Handle "Today/Tomorrow" labels
* **Locale Format Support** - Parse various time format conventions
* **Server vs Local Time** - Explicit timezone handling

**Normalization Rules:**

* **UTC Conversion** - Standardize all timestamps
* **Format Consistency** - ISO 8601 format for all time outputs
* **Ambiguity Resolution** - Handle timezone-ambiguous times

### Performance & Resource Control

**Resource Management:**

* **Max Matches Per Run** - Configurable limits to prevent memory issues
* **Browser Restart Strategy** - Periodic browser restarts for memory cleanup
* **Context Recycling** - Reuse browser contexts efficiently
* **Memory Leak Mitigation** - Proactive memory management

**Operational Limits:**

* **Browser Lifecycle** - When to restart vs continue
* **Context Discard Rules** - Memory pressure thresholds
* **Data Flush Triggers** - When to write accumulated data

### Observability & Run Diagnostics

**Comprehensive Logging:**

* **Structured Logging** - JSON format with correlation IDs
* **Log Levels** - DEBUG/INFO/WARN/ERROR with appropriate usage
* **Run Identifiers** - Unique IDs for each scraping session
* **Per-Match Traceability** - Track individual match execution

**Performance Metrics:**

* **Time Per Tab** - Performance tracking for each extraction phase
* **Success Rates** - Track success/failure patterns
* **Resource Usage** - Memory and CPU monitoring

### Crash Recovery & Resume Capability

**State Management:**

* **state_manager** module for progress tracking
* **Checkpointing** - Save progress after each successful match
* **Resume Logic** - Restart from last successful checkpoint
* **Deduplication** - Avoid re-scraping completed matches

**Recovery Features:**

* **resume_from_match_id** - Start from specific match
* **Idempotent Operations** - Safe re-execution of completed work
* **Partial Data Handling** - Recover from incomplete extractions

### CLI & Configuration Interface

**Configuration Management:**

* **config_manager** module for runtime settings
* **CLI Arguments** - Command-line interface for all parameters
* **Config Files** - YAML/JSON configuration support
* **Environment Overrides** - Environment variable support

**Separation of Concerns:**

* **Code vs Config** - Clear separation of logic and settings
* **Runtime Flexibility** - Change behavior without code changes

### Data Validation & Sanity Checks

**Validation Framework:**

* **data_validator** module for comprehensive validation
* **Sanity Checks** - Numeric validation for odds, scores
* **Cross-Field Consistency** - Validate related data relationships
* **Empty Table Detection** - Handle missing data gracefully

**Quality Assurance:**

* **Data Type Validation** - Ensure correct data types
* **Range Validation** - Check for reasonable value ranges
* **Completeness Checks** - Verify required fields are present

### Screenshot & Video Recording Policy

**Visual Documentation:**

* **Full-Page Screenshots** - Capture complete page state per match
* **Failure-State Screenshots** - Automatic capture on errors
* **Optional Video Recording** - Playwright video support for debugging
* **Element Highlighting** - Visual indication of extracted elements

**Debugging Support:**

* **Selector Breakage Evidence** - Visual proof of DOM changes
* **Soft-Blocking Documentation** - Evidence of detection measures

### Shutdown & Cleanup Semantics

**Graceful Operations:**

* **Signal Handling** - Proper Ctrl+C and termination signal handling
* **Browser Cleanup** - Ensure proper browser/context shutdown
* **Data Flush on Exit** - Save all accumulated data before exit
* **Resource Release** - Clean up file handles and network connections

### Success Criteria & Thresholds

**Explicit Success Metrics:**

* **Minimum Data Completeness** - Required fields for successful extraction
* **Acceptable Failure Rate** - Maximum failure percentage per run
* **Abort vs Continue Logic** - When to stop vs continue extraction
* **Quality Thresholds** - Minimum data quality standards

**Production Success Definition:**

* **Data Completeness** - Percentage of required fields successfully extracted
* **Reliability Metrics** - Consistency across multiple runs
* **Performance Standards** - Acceptable extraction times

### Environment Setup

**Always use virtual environment (venv) to run code:**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependency Policy

**Solely use Playwright** - no additional HTTP libraries:

* **Only Playwright** for all browser automation and data extraction
* **No requests library** - all HTTP interactions through Playwright
* **No BeautifulSoup** - use Playwright's built-in DOM querying capabilities
* **No other scraping libraries** - keep dependencies minimal and focused

### Testing Policy

**No tests should be included** in this implementation. Focus solely on the production scraper code without any unit tests, integration tests, or test files.

### Anti-Detection

Integrate Playwright stealth techniques:

* Mask webdriver flags
* Realistic browser fingerprints
* Randomized delays:
	+ 2–5 seconds between clicks
	+ Longer pauses between matches

### Dynamic Loading Control

Use:

* **Element-based readiness checks** - Wait for specific DOM elements to appear
* **Timeout-based waits** - Use reasonable timeouts instead of network idle
* **Content validation** - Verify expected content is present before proceeding
* **Retry mechanisms** - Implement retry logic for failed content loads
* Never scrape immediately after navigation

### Error Handling & Resilience

Implement:

* Retry decorator with capped retries
* Structured logging (tab-level, match-level)
* On failure:
	+ Skip failed tab
	+ Continue match
	+ Never crash full run

### Output Schema

Save output as hierarchical JSON:

```json
{
  "match_id": {
    "header": {...},
    "summary": {...},
    "odds": {
      "1X2": {...},
      "OverUnder": {...},
      "AsianHandicap": {...}
    },
    "h2h": {
      "overall": [...],
      "home": [...],
      "away": [...]
    },
    "standings": {...}
  }
}
```

## 🚀 Final Instruction to the AI / Developer

Please implement the full Python codebase following the architecture and logic above, using:

* `asyncio`
* `playwright.async_api`
* Object-oriented design
* Clear separation of concerns

**Include:**

* All necessary imports
* Class definitions
* Retry utilities
* Logging setup
* Main asynchronous execution loop