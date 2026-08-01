# Session Summary (compressed history — entries are removable)

One compact entry per session, newest at the bottom. Unlike
`agents/sessions.md` (the formal registry, append-only forever), this
file is a **working summary**: entries may be removed when a session is
no longer useful, and older detail is expected to compress over time.

The purpose is **continuity, not archival completeness**. A future agent
should understand at a glance what important work happened recently,
what significant decisions were made, and where to find detail if needed.

Entries are separated by `---` so agents can parse them as discrete
records.

<!-- TEMPLATE — copy below the last entry:
---
- **YYYY-MM-DD — Session N** — <agent> / <model> — <one-line outcome>.
  <Key decision or discovery, if any.>
  Detail: .context/memory/sessions/YYYY-MM-DD-N/notes.md (or "summary only").
-->

---
- **2026-07-27 — Session 30** — Claude Code / claude-opus-4-8 — betb2b → Supabase-backed, remotely-controllable, proxy-free pipeline (ADR-12/13/14) + cross-repo DB-mediated architecture.
  Detail: summary only (full entry in agents/sessions.md).

---
- **2026-07-28 — Session 31** — Claude Code / claude-opus-4-8 — betb2b data-quality pass: outrights dropped, persist speedup (ADR-17 persist half), market-naming traced → ADR-19 (adopt the new-builder GetGameZip MEC/SG names).
  Detail: summary only (full entry in agents/sessions.md).

---
- **2026-07-28 — Session 32** — Claude Code / claude-opus-4-8 — cross-repo doc sync + bounded-concurrency fetch (ADR-17 fetch half): ~10× faster, lossless. Closes ADR-17.
  Detail: summary only (full entry in agents/sessions.md).

---
- **2026-07-28 — Session 33** — Claude Code / claude-opus-4-8 — scheduler as a deployable Railway worker (ADR-18): SIGTERM graceful stop + Procfile + RAILWAY.md; deployed to Railway same day.
  Detail: summary only (full entry in agents/sessions.md).

---
- **2026-07-28/29 — Session 34** — Claude Code / claude-opus-4-8 — results-endpoint research → ADR-20 (statisticfeed `v1/Game`, `entity.status==3`) + the scheduler's results pass BUILT (final scores into events). Docs rebalance: betb2b de-emphasized in the main README.
  Detail: summary only (full entry in agents/sessions.md).

---
- **2026-08-01 — Session 35** — Buffy (Freebuff) / deepseek-v4-flash — `.context` sync: core 0.3.0 → **0.5.0** (session-scoped memory release), kickoff.md + AGENTS.md regenerated for the new templates, `memory/sessions/` module seeded.
  Detail: summary only (sync session, no notes file).
