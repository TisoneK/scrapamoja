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
- **Claude Code / claude-opus-4-8:** Bootstrapped `.context/` on this repo; could not run the test/lint/typecheck baseline because the machine lacks a Python 3.12+ interpreter — did a static-only review instead. (2026-07-12)
