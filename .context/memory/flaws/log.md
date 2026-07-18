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

---
## 2026-07-18 — Super Z / GLM (cloud sandbox) — Session 12
- **Problem:** The Bash tool returned `broken session: 403 Forbidden` on every
  invocation (including `echo probe`), five separate times in one session. Each
  outage lasted 10+ retries and always hit right before executing
  `python -m src.sites.betb2b.scripts.validate_live --skin linebet` or the
  `git commit + push` step. During the widest outage the `Write` / `Edit` / `Read`
  tools also went down — the entire tool-execution layer was unreachable.
- **Cost:** The betb2b live end-to-end validation did NOT run this session; the
  git push was delayed across 4+ session restarts by the user. Each restart lost
  the in-flight Bash window.
- **Cause:** Session-level tool-execution layer outage. NOT a code, proxy, or
  invocation-style issue — the `Bash` function was called correctly with JSON
  parameters every time. The 403 surfaces in the tool router, before the command
  reaches a shell. Not related to network or to the operator's Kenya proxy
  (which was verified live mid-session: `102.210.56.70 (KE)`).
- **Workaround / fix:** Restarting the session clears it (briefly — the outage
  recurred within the same long session after every restart). No in-session
  workaround found. Switching to `Write` / `Edit` worked for file creation
  during the Bash-only outages, but those tools also failed during the widest
  outage. The successful finish strategy was: prepare ALL context-file content
  via the `Write` tool to disk first (so it survives a restart), then execute
  the appends + git in a single quick Bash window the moment one opens.
- **Prevent next time:**
  1. When the Bash tool returns `broken session: 403 Forbidden` on 2+ consecutive
     calls, STOP retrying immediately and tell the user to restart the session.
     Do not burn 10+ retries on a single probe — the outage does not self-heal
     within a session.
  2. If the work is multi-step, prepare every file-write step via the `Write` /
     `Edit` tool first (those went down less often than Bash), then batch all
     Bash-dependent steps (appends, git) into ONE shell script so a single clean
     Bash window finishes the whole job.
  3. For long sessions, prefer committing work in small increments as soon as a
     Bash window opens — do not accumulate multiple steps of uncommitted work
     that all need Bash at the end.
