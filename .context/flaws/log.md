# Flaws Log (append-only — flows to the protocol package)

Friction caused by the `.context/` system or the protocol itself. See
`README.md` in this directory for the split between `flaws/` and
`inefficiencies/`.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — <agent> / <model> (Session N)

- **Flaw:** <what in the protocol or .context/ system didn't work>
- **Symptom:** <what happened to the agent — the observable friction>
- **Root cause:** <why the protocol/.context/ let this happen>
- **Suggested fix:** <concrete change to the package — a step, a pitfall,
  a template, a rule>
- **Status:** open | fixed in package <commit-sha or date>
-->

---
## 2026-07-12 — Claude Code / claude-opus-4-8 (Session 1)

- **Flaw:** The kickoff/protocol Zero-Interruption Principle ("never ask the user; use documented defaults") collides with safety when the Pre-Flight is left as a raw, unfilled template. The blank defaults silently authorize the highest-impact actions — "fix all safe issues" + **"push to main directly"** — under a git identity the agent had to infer.
- **Symptom:** Agent faced a choice: rubber-stamp push-to-main + autonomous fixes on an unowned identity (per Zero-Interruption), or pause to confirm (per the "don't rubber-stamp significant decisions" rule and general safety). It chose to ask three scoping questions before any outward action.
- **Root cause:** The protocol treats Pre-Flight as always-filled and doesn't distinguish "user accepted the default" from "user never touched the field." An all-placeholder Pre-Flight is indistinguishable from a deliberate all-defaults one.
- **Suggested fix:** Add a kickoff pre-flight-completeness gate: if Project/identity/push-policy fields still contain `<PLACEHOLDER>` tokens, the agent must confirm scope + push policy + commit identity once before Phase 1, rather than proceeding on defaults. Defaults should only auto-apply to fields the user explicitly left blank, not to an untouched template.
- **Status:** open
