# Agent + Model Registry (update in place)

Which agents and models have worked on this repo — and what they've
shown they can and can't do here. Update your row each session (last
seen + session count); add a row if you're new. The Observations
section is how the user learns which agent to hand which task, and how
agents learn a predecessor's blind spots (and verify its work
accordingly).

| Agent | Model | First seen | Last seen | Sessions |
|---|---|---|---|---|
| Claude Code | claude-opus-4-8 | 2026-07-12 | 2026-07-12 | 1 |

## Observations

Concrete, evidence-based capabilities and limits — things demonstrated
in this repo's sessions, not marketing claims or self-assessment.
Update in place when a newer session contradicts an old observation.

- **Claude Code / claude-opus-4-8:** Model id taken from the agent's own system prompt (stated fact, not a guess). (2026-07-12)
- **Claude Code / claude-opus-4-8:** Bootstrapped `.context/` on this repo; initial session could not run the baseline (no Python 3.12+). (2026-07-12)
- **Claude Code / claude-opus-4-8:** Stood up the toolchain with `uv` (user-space, no admin) — CPython 3.12.13 + `.venv`; found `pyproject.toml` omitted 10 runtime deps and fixed it (`bb0e636`); found 3 pre-existing import-time crashes via a dependency-driven import sweep. (2026-07-12)
