# Architectural Decisions (append-only, ADR-style)

Decisions already made — future agents respect these rather than
relitigating them. To reverse one, append a new ADR that supersedes it.

<!-- TEMPLATE — copy below the last entry:
---
## ADR-N: <short title> (YYYY-MM-DD)
- **Status:** accepted | superseded by ADR-M
- **Context:** <what forced the decision>
- **Decision:** <what was decided>
- **Consequences:** <trade-offs accepted; what future agents must respect>
-->

---
## ADR-1: Carry-over — the standing technical decisions of the previous office (2026-10-03)
- **Status:** accepted
- **Context:** the office closed; its ADRs are frozen in `history/office-001/plans/decisions.md`, which the new office does not read at session start.
- **Decision:** the following stay in force: control plane via Dockerfile with no scrape jobs in the API; transport separate from extraction mode; DOM extraction is the primary BetB2B path and the rotating auth header is never chased in code; `GetGameZip` is the market-depth path and the discovery pipeline is proxy-free; scraped odds live in a structured time-series store (local SQLite default, any Postgres optional, a stored match is scraped once); event ids are not stable across skins or time, sub-games are not matches, failed is not empty; team-total scopes zero the other team's H2H score; every request path goes through the security guard and is paced; a real browser may clear a vendor challenge but its JS is never reimplemented; hosted stores need retention and a quota monitor; import health is a tested invariant.
- **Consequences:** reverse any of these only with a new ADR that supersedes this one. Per-decision rationale and evidence: `history/office-001/plans/decisions.md`.

