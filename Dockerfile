# syntax=docker/dockerfile:1.7
# =============================================================================
# Scrapamoja — Railway Dockerfile
# -----------------------------------------------------------------------------
# Deploys the FastAPI control plane (src/api/main.py) as a long-running web
# service. The CLI (src/main.py) is for one-off scrape jobs and is NOT the
# deployed process — but it IS importable inside this image for `railway run`
# invocations from the Railway CLI.
#
# Image layout:
#   /app                       — project root (WORKDIR)
#   /app/.venv                 — Python virtualenv (deps installed here)
#   /app/data                  — runtime data dir (SQLite db lands here)
#                                Mount a Railway Volume here to persist
#                                data/adaptive.db across redeploys.
#   /home/appuser              — non-root runtime user's home
#
# Build args (override with --build-arg):
#   PYTHON_VERSION   default 3.12
#   PLAYWRIGHT_BROWSERS  chromium   (only chromium is installed — flashscore
#                                    and wikipedia scrapers don't need FF/WebKit)
# =============================================================================

ARG PYTHON_VERSION=3.12

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder
# ──────────────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

# Install build-time OS deps (curl for healthcheck probe, build-essential +
# libxml2/libxslt for lxml, libffi for cryptography). These stay in the
# final image only where runtime needs them — slim-bookworm already ships
# most runtime libs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv OUTSIDE the system Python so the final stage can copy it cleanly.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Python dependencies first (cached layer — only rebuilds when
# requirements.txt or pyproject.toml change).
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip wheel setuptools \
    && pip install -r requirements.txt \
    && pip install ".[prod]"

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
# ──────────────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ARG PLAYWRIGHT_BROWSERS=chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    # Default DB path — override ADAPTIVE_DB_PATH to point at a mounted
    # Railway Volume for persistence across redeploys.
    ADAPTIVE_DB_PATH=/app/data/adaptive.db

# Runtime OS deps:
#   - curl        — used by Railway's healthcheck probe
#   - Playwright's Chromium runtime libs — installed by `playwright install
#                  --with-deps` below (it adds ~30 packages: libnss3,
#                  libatk1.0, libxcomposite1, fonts, etc.)
# We let Playwright own the apt install so the dep list tracks the
# installed Playwright version exactly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the venv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Install the Chromium browser + its OS deps into the runtime image.
# This is the heavy layer (~500 MB) but it's cached and only rebuilt when
# Playwright's version changes.
RUN playwright install --with-deps ${PLAYWRIGHT_BROWSERS}

# Non-root runtime user. We create it with a fixed UID/GID (10001) so a
# Railway Volume mounted at /app/data is owned by the runtime user.
RUN groupadd --system --gid 10001 appuser \
    && useradd  --system --uid 10001 --gid appuser \
                --home-dir /home/appuser --create-home \
                --shell /usr/sbin/nologin appuser

WORKDIR /app

# Create the runtime data directory and chown it. If a Railway Volume is
# mounted at /app/data, Railway will overlay this — the chown still applies
# to the volume's root on first mount.
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Copy the project. .dockerignore strips tests/, .git/, .context/, node_modules,
# caches, and other build artifacts so the layer stays small.
COPY --chown=appuser:appuser . /app

USER appuser

# Railway injects $PORT. We bind to 0.0.0.0 so the Railway proxy can reach us.
# Gunicorn with uvicorn workers is the production-grade runner; one worker per
# CPU is the default uvicorn recommendation for I/O-bound async apps.
EXPOSE 8000

# Healthcheck — Railway also probes /health via its own HTTP healthcheck
# config (see railway.json), but having a Docker-level HEALTHCHECK helps
# local `docker run` debugging.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

# Use gunicorn with uvicorn workers. Override workers via GUNICORN_WORKERS env
# var (default: 2 — modest for a control plane; bump if you serve heavy
# traffic). The uvicorn worker class runs the FastAPI app on the async loop.
CMD ["sh", "-c", "gunicorn src.api.main:app \
    --workers ${GUNICORN_WORKERS:-2} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --forwarded-allow-ips '*'"]
