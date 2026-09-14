# Inefficiencies archive (moved entries — verbatim)

Closed entries (explicit `RESOLVED`/`superseded`/fixed markers) moved here
verbatim from `log.md` per the log-compaction rule. Startup reads only the
active log; this file stays grep-able history.

---
## 2026-09-14 — Miles (S446) / qwen3.8-flash (Session 48)
- **Problem:** `context-sync verify` silently rewrites `memory/core.lock` (comment line's em-dash → ASCII `--`), so the next `context-gates checkpoint` shows an unexpected dirty file mid-session and costs a diff-triage to attribute it.
- **Cost:** one diff + one solo `chore(context)` commit (small — S47 had hit the same and noted it only inside its session entry, not in this log, so the trap wasn't findable at startup).
- **Cause:** the tool normalizes that comment line on every run against an LF-stamped file; the re-stamp is harmless (content fields `version=`/`verified=` unchanged when the date matches).
- **Workaround / fix:** expect it — on the same day as the last stamp, `verify` leaves only the dash diff; commit it as its own `chore(context)` and move on. No rollback, no core edit.
- **Prevent next time:** this log entry is the record: at checkpoint, `M .context/memory/core.lock` right after a verify run is the tool's own re-stamp, not peer activity.
- **Status:** superseded 2026-09-14 — core 1.1.x `ledger-sync` re-locks `core.lock` with the normalized em-dash text, so `verify` no longer rewrites it; churn observed zero after the Context Ledger migration (tested this session: `ledger-sync verify` → clean tree).
