# Scrapamoja — Module Dependency Graph & Build Order
**Version:** 1.0  
**Author:** TisoneK  
**Date:** March 2026  
**Status:** Active

---

## 1. Purpose

This document answers one question: **in what order should the nine new features be built?**

The answer is determined entirely by dependencies. A module that other modules rely on must exist before those modules can be built. A module that relies on nothing can be built at any time, independently, in parallel with anything else.

Getting this order wrong means building a module that cannot be tested because its dependency does not exist yet, or worse — building a module and then having to rebuild it when the dependency it assumed turns out to work differently than expected.

---

## 2. Dependency Rules Recap

From the Architecture Guide:

- Site modules depend on core modules — never the reverse
- Foundation modules (`browser/`, `stealth/`, `resilience/`) depend on nothing inside Scrapamoja
- Higher-level modules (`network/`, `encodings/`) may depend on foundation modules
- Site modules (`sites/aiscore/`) may depend on any of the above

---

## 3. Full Dependency Map

For each feature, what does it need to exist before it can function?

---

### SCR-001 — Direct API Mode
**Depends on:** Nothing internal  
**Reason:** Makes raw HTTP calls. No browser. No other Scrapamoja module needed. It is a standalone transport layer.

---

### SCR-002 — Network Response Interception
**Depends on:** Nothing internal  
**Reason:** Attaches a listener to a Playwright page object passed in from outside. It does not create the browser or the session — it only listens. It is self-contained.

---

### SCR-003 — Cloudflare Support
**Depends on:** Nothing internal
**Reason:** Configures the Playwright browser context before navigation. It is a browser configuration concern and does not need any other Scrapamoja module. It is standalone.

---

### SCR-004 — Auto Encoding Detection
**Depends on:** Nothing internal  
**Reason:** Inspects raw bytes and identifies their format. Pure logic — no browser, no network, no other module. Completely standalone.

---

### SCR-005 — Protobuf Binary Decoding
**Depends on:** SCR-004 (Auto Encoding Detection)  
**Reason:** The protobuf decoder is registered in the encoding detector's registry. The detector identifies protobuf bytes and routes them to this decoder. Without the detector, the decoder has no entry point into the pipeline. SCR-004 must exist first.

---

### SCR-006 — Session Harvesting
**Depends on:** Nothing internal  
**Reason:** Reaches into an active Playwright browser context and extracts cookies and tokens. The browser context is passed in from outside — this module does not create it. Standalone.

---

### SCR-007 — Session Bootstrap Mode
**Depends on:** SCR-001, SCR-003, SCR-006  
**Reason:** Session Bootstrap orchestrates three things in sequence — Cloudflare bypass (SCR-003) to get in, session harvesting (SCR-006) to extract credentials, and direct API calls (SCR-001) to extract data without the browser. All three must exist before this orchestration layer can be built.

---

### SCR-008 — AiScore Site Module
**Depends on:** SCR-002, SCR-003, SCR-004, SCR-005, SCR-007  
**Reason:** AiScore requires the full pipeline. Cloudflare bypass (SCR-003) to access the site, network interception (SCR-002) to capture the API response, encoding detection (SCR-004) to identify the binary format, protobuf decoding (SCR-005) to extract structured data, and session bootstrap (SCR-007) for high-frequency polling. This is the most dependent module — it is the final assembly of everything built before it.

---

### SCR-009 — Persistent Browser Profile
**Depends on:** Nothing internal  
**Reason:** Manages a browser profile directory on disk. It configures the Playwright browser context to use a persistent storage path. No other Scrapamoja module is needed. It is standalone — but it enhances SCR-003 and SCR-007 when used alongside them.

---

## 4. Dependency Graph

```
SCR-001  Direct API          ──────────────────────────┐
                                                        │
SCR-002  Network Intercept   ────────────────────┐     │
                                                  │     │
SCR-003  Cloudflare Support  ──────────┐         │     │
                                       │         │     ▼
SCR-004  Encoding Detection  ──┐       ├────► SCR-007  Session Bootstrap
                               │       │         │
SCR-005  Protobuf Decoding  ◄──┘       │         │
                                       │         │
SCR-006  Session Harvesting  ──────────┘         │
                                                  │
SCR-009  Persistent Profile  (standalone)         │
                                                  │
                                                  ▼
                                           SCR-008  AiScore Module
                                    (depends on 002, 003, 004, 005, 007)
```

---

## 5. Module Tiers

Based on the dependency graph, the nine features fall into three clear tiers.

---

### Tier 1 — Foundation Modules
*Standalone. No internal dependencies. Can be built in any order, in parallel.*

| Feature | ID | Why It Is Foundation |
|---|---|---|
| Direct API Mode | SCR-001 | Pure HTTP transport, no dependencies |
| Network Response Interception | SCR-002 | Standalone listener, no dependencies |
| Cloudflare Support | SCR-003 | Browser configuration, no dependencies |
| Auto Encoding Detection | SCR-004 | Pure byte inspection logic, no dependencies |
| Session Harvesting | SCR-006 | Browser context extraction, no dependencies |
| Persistent Browser Profile | SCR-009 | Profile management, no dependencies |

---

### Tier 2 — Composite Modules
*Depend on one or more Tier 1 modules. Must be built after their dependencies.*

| Feature | ID | Depends On |
|---|---|---|
| Protobuf Binary Decoding | SCR-005 | SCR-004 |
| Session Bootstrap Mode | SCR-007 | SCR-001, SCR-003, SCR-006 |

---

### Tier 3 — Assembly Module
*Depends on multiple Tier 1 and Tier 2 modules. Built last.*

| Feature | ID | Depends On |
|---|---|---|
| AiScore Site Module | SCR-008 | SCR-002, SCR-003, SCR-004, SCR-005, SCR-007 |

---

## 6. Recommended Build Order

The tiers define the constraint. Within each tier, the order is a recommendation based on which modules unlock the most value earliest.

### Phase 1 — Build the Foundation
*Build any or all of these first. They are independent of each other.*

1. **SCR-004 — Auto Encoding Detection** *(build this first among all — SCR-005 waits for it)*
2. **SCR-001 — Direct API Mode** *(needed by SCR-007)*
3. **SCR-003 — Cloudflare Support** *(needed by SCR-007 and SCR-008)*
4. **SCR-006 — Session Harvesting** *(needed by SCR-007)*
5. **SCR-002 — Network Response Interception** *(needed by SCR-008)*
6. **SCR-009 — Persistent Browser Profile** *(standalone, can be built anytime)*

### Phase 2 — Build the Composite Modules
*Build after Phase 1 is complete.*

7. **SCR-005 — Protobuf Binary Decoding** *(SCR-004 must exist)*
8. **SCR-007 — Session Bootstrap Mode** *(SCR-001, SCR-003, SCR-006 must exist)*

### Phase 3 — Build the Assembly
*Build after Phase 2 is complete.*

9. **SCR-008 — AiScore Site Module** *(everything must exist)*

---

## 7. What Can Be Built in Parallel

For teams or agents working concurrently, here is what can safely be built at the same time without stepping on each other:

**Parallel Group A** *(all Phase 1, no dependencies between them)*
- SCR-001, SCR-002, SCR-003, SCR-004, SCR-006, SCR-009 can all be built simultaneously

**Parallel Group B** *(both Phase 2, independent of each other)*
- SCR-005 and SCR-007 can be built simultaneously — they do not depend on each other

**SCR-008 must be built alone, last** — it depends on the output of both parallel groups.

---

## 8. The Critical Path

If a single developer is building everything sequentially, the longest chain of blocking dependencies is:

```
SCR-004 → SCR-005 → SCR-008
SCR-001 → SCR-007 → SCR-008
SCR-003 → SCR-007 → SCR-008
SCR-006 → SCR-007 → SCR-008
SCR-002 ──────────► SCR-008
```

The critical path — the sequence that cannot be shortened — runs through SCR-007:

```
SCR-001 + SCR-003 + SCR-006 → SCR-007 → SCR-008
```

This means **SCR-007 is the most important module to unblock**. As soon as SCR-001, SCR-003, and SCR-006 are done, SCR-007 should be the immediate next task. Everything else can fill in around it.

---

## 9. Summary

| Build Order | Feature | ID | Tier | Blocked By |
|---|---|---|---|---|
| 1 | Auto Encoding Detection | SCR-004 | Foundation | Nothing |
| 2 | Direct API Mode | SCR-001 | Foundation | Nothing |
| 3 | Cloudflare Support | SCR-003 | Foundation | Nothing |
| 4 | Session Harvesting | SCR-006 | Foundation | Nothing |
| 5 | Network Interception | SCR-002 | Foundation | Nothing |
| 6 | Persistent Browser Profile | SCR-009 | Foundation | Nothing |
| 7 | Protobuf Binary Decoding | SCR-005 | Composite | SCR-004 |
| 8 | Session Bootstrap Mode | SCR-007 | Composite | SCR-001, SCR-003, SCR-006 |
| 9 | AiScore Site Module | SCR-008 | Assembly | SCR-002, SCR-003, SCR-004, SCR-005, SCR-007 |

---

*Document prepared March 2026. Update whenever a new feature is added or a dependency relationship changes.*
