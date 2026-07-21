# Current Task — Idle

**Status:** Idle — no session in progress.

Last session (25, 2026-07-21, Claude Code / claude-opus-4-8) closed both
HIGH-priority betb2b gaps from Session 24:

- **Market depth** — root-caused to a skip-condition bug in
  `_enrich_dom_events_with_odds` (not a missing feature); DOM stubs now get
  the full `GetGameZip` market tree (1 → 10–40 markets). `99be8ac`.
- **Live DOM** — the garbled names didn't reproduce on a fresh capture; the
  real gaps were missing live scores (`.ui-game-scores__item--total`) and a
  fragile fixed-settle render. Fixed + hardened the name guard.
  `58f9a46`, `26b08d5`, `d173c6a`.

Also updated core 0.2.0 → 0.3.0 (`409aae0`) and hardened proxy verification
against flaky tunnels (`7f59edc`). Full betb2b suite green (79 tests).
Report: `reviews/2026-07-21-review-2.md`.

**Integrated live run CONFIRMED green** (operator restarted the tunnel):
`scrape --skin linebet --sport basketball --action list_live` → 10 live
events, 100% clean teams + scores, 8/10 with GetGameZip markets (133 total),
76s. All fixes verified composing in the real pipeline.

**Next agent:** pick up from `tasks/backlog.md` — remaining betb2b items are
`G=NN` market-group name mapping (cosmetic) and cross-skin proxy validation.
Entry point is `python -m src.sites.betb2b.cli` (NOT `.cli.main`).
