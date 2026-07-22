# Current Task — Idle

**Status:** Idle — no session in progress.

Session 28 (2026-07-22, Claude Code / claude-opus-4-8) closed the regression-test
gap left by Session 27's H2H fix, found that **6 of the 9 ADR-7 scopes had never
run** (`_enrich_with_subgames` was gated on a feature flag nothing could turn on
— fixed by `5f6e6db`, `--subgames`), then ran the first scoped scrape+ingest
end-to-end through a proxy the user supplied.

**Where ADR-7 now stands:** the scraper side is **done and proven** — 65 requests
from 11 events across all 9 scopes, 721 non-FULL_MATCH markets, ADR-8's
team-total contract confirmed on live data (86/91/109 against lines of
90.5/84.5/114.5, where pre-fix it sent 175/154/214).

**And it is blocked downstream.** The engine stores one prediction per
`match_id`, not per `(match_id, scope)` — 11 of 11 matches stored exactly one
record and it was the last scope sent, so 54 of 65 predictions are overwritten
on arrival and no half or quarter record survives. That is a **scorewise-engine
change, a different repo**; nothing on the scraper side can work around it. Until
then `--subgames` validates the pipeline but should not feed production — it
costs ~6 extra requests per event for data the engine drops. See ADR-10.

This also **resolves the HOME_TEAM_TOTAL asymmetry** Session 27 investigated
(10 sent, 1 stored, 9 AWAY) — the identical signature, not engine state and not
market data.

**Read before trusting the record:** Session 27's per-scope counts are not
reproducible, and the ADR-7 capability matrix (`db3046c`) is stale in 4 of 7
rows. Corrections appended to `plans/decisions.md` (append-only, so the
originals stay — check the correction before quoting either).

**Lesson (ADR-9):** when every test for a component builds that component's input
by hand, ask what builds it in production. A regression test must be seen red —
mutate the fix, confirm failure, restore.

**Next session:** the engine keying change is the only thing that unblocks ADR-7;
everything else is secondary. Remaining items in `tasks/backlog.md` (4 open):
engine keying, H2H coverage (only 4 of 11 events had any), the uncertain `(G,T)`
prop groups, and the inert `[tool.ruff]` config.

**Note:** the bore.pub proxy is in `secrets/betb2b-proxy` (gitignored). Its port
rotates per tunnel session — if it stops connecting, ask the user for the current
port rather than debugging the scraper.

References: `reviews/2026-07-22-review-2.md` (§8 = the live run),
`plans/decisions.md` (ADR-9, ADR-10, and the ADR-7 correction).
