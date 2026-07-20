# Agent + Model Registry (update in place)

Which agents and models have worked on this repo — and what they've
shown they can and can't do here. Update your row each session (last
seen + session count); add a row if you're new. The Observations
section is how the user learns which agent to hand which task, and how
agents learn a predecessor's blind spots (and verify its work
accordingly).

| Agent | Model | First seen | Last seen | Sessions |
|---|---|---|---|---|
| Claude Code | claude-opus-4-8 | 2026-07-12 | 2026-07-12 | 3 |
| Claude Code | claude-fable-5 | 2026-07-12 | 2026-07-12 | 1 |
| Super Z | unknown | 2026-07-14 | 2026-07-14 | 1 |
| GitHub Copilot | DeepSeek V4 Flash Free | 2026-07-19 | 2026-07-20 | 2 |

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
