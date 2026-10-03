# Flaws archive (moved entries — verbatim)

Closed entries (explicit `RESOLVED`/`superseded`/fixed markers) moved here
verbatim from `log.md` per the log-compaction rule. Startup reads only the
active log; this file stays grep-able history.

---
## 2026-09-06 — ZCode / GLM-5.3-Flash (Session 41)
- **Flaw:** On a Windows checkout with `core.autocrlf=true`, the 0.8.0 `context-sync verify` reported CORE INTEGRITY FAILURE for 13 files missing `eol=lf` attribute coverage (`bin/*`, `VERSION`, `*.json`, `core.lock`, `.gitignore`, `gates.conf`) — CRLF checkout mangling, not corruption. The advised remediation (`rollback`) would have restored the same CRLF bytes — an unfixable loop.
- **Symptom:** verify failed under BOTH the sh script (`sha256sum: 'CHANGELOG.md'$'\r'` parse errors on every line) and the ps1 port (13 FAILED lines) on a freshly-pulled, unmodified 0.8.0 core. Manifest hashes matched the committed git blobs exactly; only the working tree differed.
- **Root cause:** the 0.8.0 verifier hashed raw on-disk bytes, and the project's root `.gitattributes` pinned only `*.py/*.yaml/*.md` to LF — attribute-less core files were checked out CRLF while the manifest hashed LF blobs.
- **Suggested fix:** none needed upstream — fixed in core 0.9.0/0.9.1 (`.context/.gitattributes` + CR-stripped hashing). Confirmed fixed here after migrating to 0.16.1 (verify passes on the CRLF working tree). Kept as the documented local instance of the known defect; do NOT rollback on this signature — diagnose with `git ls-files --eol` first.
- **Status:** fixed in package core 0.9.1 (observed fixed here on 0.16.1, 2026-09-06)
