# Scrapamoja — Feature Architecture & Module Placement Guide
**Version:** 1.0  
**Author:** TisoneK  
**Date:** March 2026  
**Status:** Active

---

## 1. Purpose

This document defines where each new Scrapamoja feature lives within the project, why it lives there, and what architectural principle governs that decision. It is not a file structure prescription — the internal organisation of each module is left to the developer or coding agent building it. Creativity in implementation is expected and encouraged.

What this document does prescribe is **which existing directory a feature extends** or **which new directory a feature introduces** — and the reasoning behind each decision. Getting this right at the start prevents features from bleeding into each other, keeps modules independently deployable, and makes the codebase navigable as it grows.

---

## 2. Core Architectural Principle

Every new feature in Scrapamoja is a **module**, not a file.

A module has its own directory, its own public interface, its own configuration, and its own tests. It can be developed, reviewed, merged, and if necessary removed — without touching anything outside its own boundary.

This is not bureaucracy. It is the difference between a codebase that scales and one that becomes a maze after ten features.

The second principle is equally important: **no catch-all directories**. There is no `core/`, no `utils/`, no `common/` that becomes a dumping ground. Every module lives somewhere specific because of what it does, not because it was convenient to put it there.

---

## 3. The Two Types of Placement

When a new feature is added to Scrapamoja, it does one of two things:

**It extends an existing directory** — because the concern already has a home. The feature adds a new module inside a directory that already owns that domain. Nothing outside that directory changes.

**It introduces a new directory** — because the concern is genuinely new and has no existing home. A new top-level directory under `src/` is created, and the feature becomes its first resident.

Both are valid. The decision depends entirely on whether the concern is new or existing.

---

## 4. Existing Directories and Their Concerns

Before placing any new feature, it is important to understand what the existing directories already own. These boundaries must be respected.

**`src/browser/`**  
Owns everything related to the Playwright browser lifecycle — launching, configuring, pooling, and closing browser instances. If a feature is fundamentally about what the browser is, how it is set up, or what persists between browser sessions, it belongs here.

**`src/stealth/`**  
Owns everything related to making the browser appear human — fingerprint management, user agent selection, anti-detection measures. If a feature is about evading detection or appearing legitimate to a target site's security layer, it belongs here.

**`src/selectors/`**  
Owns the selector engine — CSS, XPath, text-based strategies, confidence scoring. If a feature is about how elements are found within a rendered page, it belongs here.

**`src/navigation/`**  
Owns route planning and page discovery — how Scrapamoja moves through a site. If a feature is about how the browser traverses pages, it belongs here.

**`src/resilience/`**  
Owns error handling, retries, and recovery — the mechanisms that keep Scrapamoja running when things go wrong. If a feature is about surviving failure gracefully, it belongs here.

**`src/telemetry/`**  
Owns metrics collection and performance tracking. If a feature produces measurements about Scrapamoja's own behaviour, it belongs here.

**`src/observability/`**  
Owns logging, events, and structured output about what Scrapamoja is doing. If a feature produces human-readable insight into system behaviour, it belongs here.

**`src/sites/`**  
Owns site-specific scraping modules. Every site Scrapamoja supports is a module here. If a feature is the implementation of scraping a specific website, it belongs here.

---

## 5. Feature Placement Decisions

### SCR-001 — Direct API Mode
**Placed in:** `src/network/` *(new directory)*

Direct API mode is about making HTTP calls without a browser. This is a transport concern — it lives at the network layer, not the browser layer. No existing directory owns network transport as a concept. A new `network/` directory is introduced, and this feature is its first resident. All future features that deal with how data moves over the wire — without a browser — will live alongside it here.

---

### SCR-002 — Network Response Interception
**Placed in:** `src/network/` *(new directory, alongside SCR-001)*

Interception is also a network layer concern. It listens to traffic moving between a server and the browser, capturing responses before the browser processes them. Even though it operates within a browser session, its concern is the network data — not the browser itself, not the DOM. It belongs in `network/` alongside Direct API, because both are fundamentally about what moves over the wire.

---

### SCR-003 — Cloudflare-Protected SPA Support
**Placed in:** `src/stealth/` *(extends existing directory)*

Cloudflare bypass is a stealth concern. It is about making the browser appear legitimate to a security layer — exactly what `stealth/` already owns. This feature does not introduce a new domain; it deepens an existing one. Placing it inside `stealth/` keeps all anti-detection intelligence in one place, which is where a developer looking for it will look first.

---

### SCR-004 — Auto Encoding Detection
**Placed in:** `src/encodings/` *(new directory)*

Encoding detection is about identifying what format raw bytes are in — JSON, gzip, Brotli, protobuf, plain text. This is neither a browser concern nor a network concern nor a stealth concern. It is a data format concern, and no existing directory owns that. A new `encodings/` directory is introduced. This becomes the home for all format-awareness intelligence in Scrapamoja.

---

### SCR-005 — Protobuf Binary Decoding
**Placed in:** `src/encodings/` *(new directory, alongside SCR-004)*

Protobuf decoding is a specific implementation of data format handling — it takes binary protobuf bytes and produces structured Python data. It belongs in `encodings/` alongside the detector, because the detector identifies the format and the decoder acts on it. They are two parts of the same concern. Keeping them in the same directory makes the relationship obvious without creating a hard dependency.

---

### SCR-006 — Session Harvesting
**Placed in:** `src/browser/` *(extends existing directory)*

Session harvesting is about extracting what the browser has accumulated — cookies, tokens, storage state — from an active browser context. This is a browser lifecycle concern. The browser created it, the browser holds it, and the harvester reaches into the browser to retrieve it. `browser/` already owns the browser lifecycle, so this feature extends it. It does not belong in `network/` even though the harvested credentials are used for network calls — the harvesting act itself is a browser operation.

---

### SCR-007 — Session Bootstrap Mode
**Placed in:** `src/network/` *(new directory, alongside SCR-001 and SCR-002)*

Session Bootstrap is an orchestration mode — it coordinates a browser phase followed by a direct HTTP phase. Its primary concern is the data extraction pipeline: browser unlocks, session harvested, HTTP takes over. The end result is a network extraction. The browser involvement is temporary and instrumental. Because the feature's identity is defined by how data is ultimately extracted — over direct HTTP using a harvested session — it belongs in `network/` alongside the other extraction modes.

---

### SCR-008 — AiScore Site Module
**Placed in:** `src/sites/` *(extends existing directory)*

AiScore is a site. Every site Scrapamoja supports lives in `src/sites/`. This is not a new architectural concern — it is the application of new capabilities (network interception, protobuf decoding, Cloudflare bypass) to a specific target. The module lives in `sites/` and uses the new modules from `network/`, `encodings/`, and `stealth/` as dependencies. It does not duplicate their logic — it composes them.

---

### SCR-009 — Persistent Browser Profile
**Placed in:** `src/browser/` *(extends existing directory)*

A persistent profile is a browser concern through and through. It defines what the browser is — its identity, its history, its accumulated state. `browser/` owns the browser lifecycle, and a persistent profile is a fundamental part of that lifecycle: how the browser is born, how it is preserved, and how it is restored. This feature extends `browser/` in the same way session harvesting does — deepening the existing domain rather than introducing a new one.

---

## 6. The Network Directory — A Closer Look

`src/network/` is the most significant new addition introduced by these features. It will house three modules — Direct API, Network Interception, and Session Bootstrap — that are related but distinct.

The relationship between them is important to understand:

**Direct API** operates without any browser involvement at all. It is pure HTTP.

**Network Interception** operates within a browser session but captures data from the network layer before it reaches the DOM.

**Session Bootstrap** uses a browser to establish a session, then hands off to direct HTTP for all subsequent extraction.

These three represent a spectrum of how Scrapamoja can relate to the network — from fully browserless to browser-assisted to browser-initiated. Grouping them in `network/` reflects that shared identity. A developer thinking about how Scrapamoja moves data will look in `network/` and find all three options clearly available.

---

## 7. The Encodings Directory — A Closer Look

`src/encodings/` houses two modules — Auto Encoding Detection and Protobuf Decoding — that have a natural producer-consumer relationship.

The detector identifies what format a response is in. The decoder acts on a specific format. They are not the same thing and should not be merged into one module — the detector is general-purpose and format-agnostic, while the protobuf decoder is format-specific.

As new formats are encountered in future site integrations, new decoder modules will be added to `encodings/` alongside the existing ones. The detector gains a new format signature. The registry gains a new decoder entry. No other part of Scrapamoja is touched.

This is the extensibility pattern working correctly.

---

## 8. Dependency Direction

Features may depend on each other, but the dependency direction must always flow in one way: **site modules depend on core modules, never the reverse**.

Specifically:

- `src/sites/aiscore/` may import from `src/network/`, `src/encodings/`, and `src/stealth/`
- `src/network/session_bootstrap/` may import from `src/browser/session_harvester/`
- `src/browser/session_harvester/` must not import from `src/sites/`
- `src/encodings/` must not import from `src/network/`

The general rule: directories deeper in the dependency chain (sites, network, encodings) depend on directories closer to the foundation (browser, stealth, resilience). Foundation directories never depend on higher-level ones.

This keeps the foundation stable. Changes in site modules cannot break the browser module. Changes in the encoding layer cannot break the stealth module.

---

## 9. What Belongs in Tests

Every module introduced by these features should have corresponding tests. The existing test structure mirrors the source structure:

- Unit tests cover individual module behaviour in isolation
- Integration tests cover how modules interact with real or simulated targets

No test file should span multiple feature modules. A test that covers both session harvesting and network interception in the same file is a sign that the boundary between those modules is unclear.

---

## 10. Summary Table

| Feature | ID | Placement | Type |
|---|---|---|---|
| Direct API Mode | SCR-001 | `src/network/` | New directory |
| Network Response Interception | SCR-002 | `src/network/` | New directory |
| Cloudflare Support | SCR-003 | `src/stealth/` | Extends existing |
| Auto Encoding Detection | SCR-004 | `src/encodings/` | New directory |
| Protobuf Binary Decoding | SCR-005 | `src/encodings/` | New directory |
| Session Harvesting | SCR-006 | `src/browser/` | Extends existing |
| Session Bootstrap Mode | SCR-007 | `src/network/` | New directory |
| AiScore Site Module | SCR-008 | `src/sites/` | Extends existing |
| Persistent Browser Profile | SCR-009 | `src/browser/` | Extends existing |

---

## 11. A Note on Implementation Freedom

This document defines *where* features live and *why*. It does not define *how* they are built internally.

The internal design of each module — what classes it exposes, how it handles errors, what abstractions it introduces, how it structures its own sub-concerns — is entirely the responsibility of the developer or agent building it. That freedom is intentional.

Good architecture constrains placement, not creativity. The module boundaries defined here create a stable skeleton. What grows inside each module is where ingenuity belongs.

---

*Document prepared March 2026. Update when new features are proposed.*
