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

**Cross-skin validated (stronger proxy, port 38217):** live `list_live`
confirmed on linebet (133 markets), melbet (89), helabet (114 — previously
BLOCKED) — 10 events each, clean teams + scores + GetGameZip markets. 6/8
skins reachable via proxy (megapari timeout, 888starz 203-blocked). Same
event ids across skins = shared BetB2B backend.

**Next agent:** remaining betb2b items in `tasks/backlog.md` — confirm 22bet/
betwinner/paripesa `list_live`; integrated `list_prematch` run; `G=NN`
market-group name mapping (cosmetic); `max_odds_fetch` cap/concurrency.
Entry point is `python -m src.sites.betb2b.cli` (NOT `.cli.main`).
