# Current Task — Idle

**Status:** Idle — no session in progress.

Session 28 (2026-07-22, Claude Code / claude-opus-4-8) closed the regression-test
gap left by Session 27's H2H fix, then found — while building a fixture that
exercised all 9 scopes — that **6 of the 9 ADR-7 scopes had never actually run**.
`_enrich_with_subgames` was gated on `skin.features["subgames"]`: default False,
set by no skin YAML, and no CLI flag existed to turn it on. `scrape --ingest`
emitted 3 of 9 scopes and reported success. Fixed by `5f6e6db` (`--subgames`).

**Read before trusting the record:** Session 27's per-scope request counts are
not reproducible from the code at that commit, and the ADR-7 capability matrix
(`db3046c`) is stale in 4 of 7 rows. Corrections are appended to
`plans/decisions.md` — the originals stay (append-only), so check the correction
before quoting either.

**Lesson (ADR-9):** when every test for a component builds that component's
input by hand, ask what builds it in production. All three High findings this
session lived in seams between individually-green components. And a regression
test must be seen red — mutate the fix, confirm failure, restore.

**Next session should start here:** run
`python -m src.sites.betb2b.cli scrape linebet scheduled --sport basketball --subgames --ingest`
and record the true per-scope counts. Nothing has ever exercised half/quarter
ingestion end-to-end. Full list in `tasks/backlog.md` (4 items appended).

References: `reviews/2026-07-22-review-2.md`, `plans/decisions.md` (ADR-9 + the
ADR-7 correction).
