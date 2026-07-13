# Active Workflow (overwrite when the workflow changes)

The workflow currently in force for this repo — which protocol edition
agents follow and the standing session parameters. Update only when the
user changes the rules; note the change in your session entry.

- **Protocol:** ai-engineering-protocol-local.md (local)
- **Protocol source (raw):** https://raw.githubusercontent.com/TisoneK/.context/main/ai-engineering-protocol-local.md
- **Protocol source (blob):** https://github.com/TisoneK/.context/blob/main/ai-engineering-protocol-local.md
- **Fallback:** if the raw URL 404s, clone `TisoneK/.context` with `--depth 1` and read locally. (Package is already cloned at `../.context` on this machine.)
- **Since:** 2026-07-12
- **Default role:** engineer — unless a session says otherwise; see the package's roles/
- **Scope:** discovery + review + fix all safe issues
- **Target:** general sweep
- **Focus areas:** all — security, performance, UX, architecture, testing, docs
- **Findings handling:** fix safe, flag architectural
- **Push policy:** push to main directly after each commit
- **Commit style:** Conventional Commits with scope; `chore(context):` for this directory
- **Commit granularity:** one logical change per commit
- **Deliverable:** report in .context/reviews/ + chat summary
