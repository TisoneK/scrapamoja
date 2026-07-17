# Architectural Decisions (append-only, ADR-style)

Decisions already made — future agents respect these rather than
relitigating them. To reverse one, append a new ADR that supersedes it.

<!-- TEMPLATE — copy below the last entry:
---
## ADR-N: <short title> (YYYY-MM-DD)
- **Status:** accepted | superseded by ADR-M
- **Context:** <what forced the decision>
- **Decision:** <what was decided>
- **Consequences:** <trade-offs accepted; what future agents must respect>
-->

---
## ADR-1: Deploy the FastAPI control plane to Railway via Dockerfile (2026-07-17)
- **Status:** accepted
- **Context:** Scrapamoja ships two entry points — `src/api/main.py` (a long-running FastAPI control plane exposing feature-flag + failure-escalation REST endpoints, consumed by the React UI at `ui/app/`) and `src/main.py` (a CLI for one-off scrape jobs). The project needed a public deployment target. Railway was chosen because (a) the user already had a Railway account with a generous plan (8 vCPU / 8 GB per-replica cap), (b) Railway's GitHub integration gives auto-deploy on push to `main`, and (c) Railway supports Dockerfile builders — necessary because the app pulls in Playwright + Chromium, which need OS-level deps that Nixpacks (Railway's default buildpack) can't easily install.
- **Decision:**
  1. Deploy ONLY the FastAPI control plane (`src/api/main:app`) as the long-running web service. The CLI ships inside the image for `railway run python -m src.main ...` invocations but is NOT the deployed process.
  2. Use a multi-stage Dockerfile on `python:3.12-slim-bookworm`: builder stage installs Python deps, runtime stage copies the venv + installs `playwright install --with-deps chromium` + runs as non-root `appuser` (uid 10001) + starts gunicorn with uvicorn workers.
  3. Do NOT deploy the React UI in the same service. The UI is a separate Vite SPA — deploy it as a separate Railway static site pointing at the API service's public URL.
  4. Do NOT run scrape jobs inside the API service in production. Each Chromium spawn costs ~500 MB; under load they'd compete with API requests for the same browser pool. Run scrapes as `railway run` jobs or a separate worker service.
  5. Mount a Railway Volume at `/app/data` for the SQLite DB (`ADAPTIVE_DB_PATH=/app/data/adaptive.db`) — without it, every redeploy wipes feature flags + failure events.
- **Consequences:**
  - Image is ~1.5 GB (Chromium + Playwright + Python deps). First deploy takes ~5–8 min; subsequent builds hit the cache.
  - Minimum viable service size is 1 GB RAM (Chromium needs ~500 MB just to spawn). The 8 GB plan headroom is more than enough — `GUNICORN_WORKERS=2` is the conservative default; safe to bump to 4–8 under real traffic.
  - The non-root `appuser` constraint surfaced an import-time `os.makedirs` smell in `src/core/snapshot/__init__.py` (see `inefficiencies/log.md` 2026-07-17 entry). Dockerfile fix applied; source-level fix backlogged.
  - Future agents: do NOT add the UI build to this Dockerfile. If the UI needs to ship in the same image, add a separate `Dockerfile.ui` and a multi-stage build that serves the built static assets from the FastAPI app via `StaticFiles` — but that's a separate decision (would require superceding this ADR).
  - Future agents: if you swap the DB from SQLite to Postgres (Railway has a Postgres add-on), remove the Volume mount and the `ADAPTIVE_DB_PATH` env var; the Dockerfile's pre-created `/app/data` dir becomes unnecessary but harmless.
