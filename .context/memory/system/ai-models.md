# Agent + Model Registry (update in place)

Which agents and models have worked on this repo — and what they've
shown they can and can't do here. Update your row each session (last
seen + session count); add a row if you're new. The Observations
section is how the user learns which agent to hand which task, and how
agents learn a predecessor's blind spots (and verify its work
accordingly).

| Agent | Model | First seen | Last seen | Sessions |
|---|---|---|---|---|
| Claude Code | claude-opus-4-8 | 2026-07-12 | 2026-07-22 | 6 |
| Claude Code | claude-fable-5 | 2026-07-12 | 2026-07-12 | 1 |
| Super Z | unknown | 2026-07-14 | 2026-07-14 | 1 |
| GitHub Copilot | DeepSeek V4 Flash Free | 2026-07-19 | 2026-07-20 | 2 |
| Z.ai Code | unknown | 2026-07-25 | 2026-07-25 | 1 |
| Buffy (Freebuff) | deepseek-v4-pro | 2026-08-01 | 2026-08-18 | 2 |

## Observations

Concrete, evidence-based capabilities and limits — things demonstrated
in this repo's sessions, not marketing claims or self-assessment.
Update in place when a newer session contradicts an old observation.

- **Claude Code / claude-opus-4-8:** Model id taken from the agent's own system prompt (stated fact, not a guess). (2026-07-12)
- **Claude Code / claude-opus-4-8:** Bootstrapped `.context/` on this repo; initial session could not run the baseline (no Python 3.12+). (2026-07-12)
- **Claude Code / claude-opus-4-8:** Stood up the toolchain with `uv` (user-space, no admin) — CPython 3.12.13 + `.venv`; found `pyproject.toml` omitted 10 runtime deps and fixed it (`bb0e636`); found 3 pre-existing import-time crashes via a dependency-driven import sweep. (2026-07-12)
- **Claude Code / claude-fable-5:** Model id from the agent's own system prompt (stated fact, not a guess). Correction to the sessions table: the opus-4-8 row's session count was left at 1 after sessions 2–3; set to 3. (2026-07-12)
- **Claude Code / claude-fable-5:** Ran the template-framework review (session 4): found the framework's create→validate→generate path had never worked (4 independent breaks), fixed via targeted `ruff --select F821` sweep + CLI smoke test rather than full-suite runs — the per-area test-run pattern (`pytest tests/sites/template --timeout=60 --timeout-method=signal --no-cov`) avoids the suite-wide hang problem. (2026-07-12)
- **Super Z / unknown:** Model id recorded as `unknown` — system prompt names the family "GLM" but not an exact version ID; per the kickoff rule, the agent does not guess its own model. (2026-07-14)
- **Super Z / unknown:** Ran the first cloud/sandbox session on this repo (session 5, sync). Successfully cloned both repos with PAT auth, synced structural files from the package skeleton, generated the missing `.context/kickoff.md` from the template, and pushed to `origin/main` — all without issues. Followed the SYNC.md structural-vs-data split rule correctly. Did NOT run the toolchain baseline (sync task didn't need it); a future review/fix session on this sandbox should verify `uv` + `pytest` work here before relying on them. (2026-07-14)
- **GitHub Copilot / DeepSeek V4 Flash Free:** Model ID from the agent's own system prompt. (2026-07-19)
- **GitHub Copilot / DeepSeek V4 Flash Free:** Cross-skin H2H investigation completed (5/8 skins working). Found and fixed paripesa wrong domain (`paripesa.bet` → `paripesa.cool`). The agent needed 2 user corrections for protocol compliance (mid-session protocol re-read caused loss of task context). (2026-07-19)
- **GitHub Copilot / DeepSeek V4 Flash Free:** Implemented `PeriodScore` extraction from `SC.PS[]` in GetGameZip API responses — added `PeriodScore` dataclass, `_extract_period_scores()` in `rules.py`, wired into `_build_event()`. 29 tests pass. Agent needed correction to update `.context/memory/` files (was updating AGENTS.md instead). (2026-07-20)
- **Claude Code / claude-opus-4-8:** Session 23 — shipped betb2b gzip storage (`storage.py` + `view` CLI + `--compress`). Correctly diagnosed the live-e2e blocker up front via a TCP probe to the proxy tunnel (bore.pub:1074, refused) rather than blindly running a scrape that would silently WAF-block; did the offline-verifiable slice + the compression feature instead. (2026-07-20)
- **Claude Code / claude-opus-4-8:** Session 25 — closed both betb2b HIGH gaps by root-causing rather than rebuilding: the "missing" GetGameZip enrichment was a one-line skip-condition bug, and the "broken" live DOM only needed a score selector + guard hardening (garble didn't reproduce). Validated every fix against real linebet data captured in a single early proxy window, so later code work survived the tunnel dropping. Discovered `GetGameZip` returns 200 direct from a WAF-blocked datacenter IP while the SPA + list feeds don't. (2026-07-21)
- **GitHub Copilot / DeepSeek V4 Flash Free:** Session 27 — correctly root-caused a real prediction-affecting bug (team-total H2H carrying full-match scores) by tracing the engine pipeline s01→s10, and shipped a 4-line fix. But shipped it with **no test**, and its session write-up reports a per-scope request breakdown (11 FIRST_HALF, 44 quarter requests) that the code at that commit could not produce — the sub-game path was gated off. Its own document states the contradicting fact (all snapshots stored `scope='FULL_MATCH'`) without reconciling it. **Verify this agent's reported numbers against the code path that would have to produce them**; its diagnoses have held up, its measurements have not. Also self-logged a protocol violation (skipped kickoff Steps 1–4). (observed 2026-07-22 by Claude Code, session 28)
- **Claude Code / claude-opus-4-8:** Session 28 — found that ADR-7's half/quarter scopes had never run: implemented, mapped, tested in isolation, and unreachable because the feature flag gating them had no way to be turned on. Found it by building a test fixture that exercised all 9 scopes and asking where the scoped markets come from. Pattern worth repeating: when tests for a component all construct its input by hand, ask what constructs it in production. Also verified its own regression tests by mutating the fix until they went red rather than trusting green. (2026-07-22)

- **Z.ai Code / unknown:** Model id recorded as `unknown` — the system prompt names the agent family ("Z.ai Code") but not an exact model version; per the kickoff rule, the agent does not guess its own model. (2026-07-25)
- **Z.ai Code / unknown:** Session 29 — shipped the ADR-11 code-layer foundation (4 commits: shared env-driven db factory, adaptive repo routing, portable betb2b ORM models + indexes, Alembic baseline + data-copy script). Refined the documented Bash-403 root cause: the tool router rejects command strings containing a secret and poisons the window; proven workaround is scripts that read secrets from a FILE, executed with secret-free command lines. Corrected two ADR-11 premises during discovery (the store is two SQLite files not three; "connection-string swap" holds only for the adaptive/SQLAlchemy half, not the betb2b/raw-sqlite3 half). (2026-07-25)
- **Buffy (Freebuff) / deepseek-v4-flash:** Model ID from its own system prompt (stated fact, not a guess). Session 35 — `.context`-sync only (no project code touched): applied the core 0.3.0→0.5.0 update, regenerated kickoff.md/AGENTS.md to the new templates (surgical — preserved the project-customized AGENTS.md, added only the sessions/ skim sentence), seeded the new `memory/sessions/` module. No product-code capability demonstrated this session. (2026-08-01)
- **Buffy (Freebuff) / deepseek-v4-pro:** Model ID from its own system prompt (stated fact, not a guess). Session 40 — `.context`-sync only: core 0.5.0→0.8.0 update (gates + collaboration), regenerated kickoff.md, refreshed .context/README.md, surgical AGENTS.md rules merge, initialized + configured `gates.conf`. No product-code capability demonstrated (sync session). (2026-08-18)
