# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

Project is idle — no active task. Next session should consult
`tasks/backlog.md` and pick up an open item, or accept a new target
from the user.

**Reframe (Session 10, 2026-07-17):** Linebet is NOT the deliverable —
it's the live test case for a *site scraping-mode classifier* we are
building. The goal is a system that watches a site behave (live or via
HAR) and classifies which `ExtractionMode` (`raw` / `intercepted` /
`hybrid` / `playwright`) fits, then emits a recommended `SiteConfig`.
Linebet is the validation case because it exercises every hard case
(WAF, SPA, mixed DOM+API, hash-path endpoints, geo-driven query params).

**Most recent session (Session 10, 2026-07-17):** corrected an earlier
mistake where I built snapshot/HAR tooling inside the linebet package
instead of in the framework. Generalized it:
- `src/core/snapshot/normalize.py` + `diff.py` — framework-level
  normalizer + diff tool (configurable, site-agnostic). Extends the
  existing `SnapshotManager` system with post-processing on captured
  network responses.
- `src/network/har/` — new framework package: `export.py`
  (`HarExporter`), `replay.py` (`HarReplayer`), `to_snapshot.py`
  (HAR → framework `CapturedResponse` + normalized snapshot). Site-
  agnostic. Implements the proposed SCR-006 (Session Harvesting).
- Linebet now USES the framework modules via thin wrappers — no
  duplicated code.
- 66 framework + linebet tests passing (24 new framework tests + 3
  linebet integration tests + 39 existing linebet tests).
- See the Session 10 entry in `agents/sessions.md` for the full picture.

**Next planned step:** build the actual classifier
(`src/extraction/classifier/`) — the missing piece. Watches a site
behave (live or via HAR), classifies which `ExtractionMode` fits, emits
a recommended `SiteConfig`. Linebet becomes the validation case. See
the "Linebet: build site scraping-mode classifier" backlog item.
