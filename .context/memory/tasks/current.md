# Current Task — Idle

**Status:** Idle — no session in progress.

Session 29 (2026-07-25, Z.ai Code / unknown model, cloud/sandbox) shipped the
ADR-11 code-layer foundation (4 commits `e03da90`..`c0802a2`): shared env-driven
db factory, adaptive repository routing, portable betb2b ORM models + indexes,
Alembic baseline + one-time data-copy script. 189 tests green. The Railway-side
cutover is operator-side (this sandbox has no Docker/Railway/live Postgres).

**Where ADR-11 stands:** the code layer is ready — `DATABASE_URL` routing,
portable schema, migrations, and the copy tool all exist and are verified on the
SQLite fallback. What remains is (1) the operator cutover on Railway, and (2)
the betb2b persist-path rewrite from raw sqlite3 to ORM (F2 — the largest
remaining code piece; high-risk: 13 store tests + CLI depend on the current
conn API; needs a live Postgres to verify against).

**Next session (with Railway access):** provision the Postgres plugin, set
`DATABASE_URL`, `alembic upgrade head`, run `scripts/migrate_sqlite_to_postgres.py`
against the live DB, verify row counts, then do F2. Until F2 ships the betb2b
data still writes to `odds.db`.

**Pre-existing (not ADR-11):** the adaptive/API integration test suite fails at
collection under fastapi 0.140.0 (F3, verified via `git stash` to pre-exist).
Backlogged separately.

References: `reviews/2026-07-25-review.md`, `plans/decisions.md` (ADR-11 +
ADR-11 PROGRESS), `tasks/backlog.md` (6 open).
