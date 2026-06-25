# Scrapamoja — Project Rules & Instructions

> Consolidated from VERT-RULES.md and adapted for the Scrapamoja repo.
> Treat as authoritative for all work on the Scrapamoja repo.

---

## 1. Project

Single repo. Brand: **Scrapamoja**.

| Repo | GitHub | Visibility |
|------|--------|------------|
| scrapamoja | https://github.com/TisoneK/scrapamoja.git | public |

User GitHub username: **TisoneK**.
Git identity: `Tisone Kironget <tisonkironget@gmail.com>`.

---

## 2. Packaging instructions

> Please package the codebase into a ZIP file with the following requirements:

- Include **only files that have been created or modified** (exclude unchanged files).
- **Preserve the full folder structure** as it exists in the project.
- **Do not include** build artifacts, dependencies, or version control files
  unless they have been changed (i.e. exclude `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `node_modules/`, `.git/`, `venv/`).

Save ZIPs to `/home/z/my-project/download/`.

---

## 3. Working preferences

- **Code changes first, packaging last.** Do NOT package until the user
  explicitly says changes are complete.
- **Work directly in the local clone** at `/home/z/my-project/repos/scrapamoja/`.
  Edit files in place.
- When the user gives "instructions" or "context", they may just be orienting
  you — don't jump to action until they ask for it.

---

## 4. Project structure

Python-based web scraping framework with a React UI overlay.

```
scrapamoja/
├── src/
│   ├── main.py                   # Unified CLI entry point (Click)
│   ├── api/                      # FastAPI endpoints and schemas
│   │   ├── main.py               # FastAPI app
│   │   ├── routers/              # API route handlers
│   │   └── schemas.py            # Pydantic request/response models
│   ├── sites/                    # Site implementations
│   │   ├── _template/            # Full-featured template for new sites
│   │   ├── base/                 # BaseSiteScraper, registry, DI container
│   │   ├── direct/               # Direct API mode implementations
│   │   ├── flashscore/           # FlashScore scraper (Basketball, Football)
│   │   └── wikipedia/            # Wikipedia scraper
│   ├── selectors/                # Selector engine (YAML-driven, multi-strategy)
│   ├── browser/                  # Browser lifecycle, sessions, tab management
│   ├── network/                  # Network interception, HTTP client, error handling
│   │   ├── direct_api/           # Direct HTTP API client (bypass browser)
│   │   ├── interception/         # Playwright request interception
│   │   ├── session.py            # Network session management
│   │   ├── credentials.py        # Credential handling
│   │   ├── redactor.py           # Sensitive data redaction
│   │   └── errors.py             # Network-specific exceptions
│   ├── resilience/               # Retries, failure classification, checkpoints
│   │   ├── retry/                # Backoff strategies, jitter, retry manager
│   │   ├── abort/                # Abort management and failure analysis
│   │   ├── checkpoint/           # State serialization and recovery
│   │   ├── resource/             # Memory monitoring, throttling, browser manager
│   │   ├── config/               # Feature flags and retry configuration
│   │   ├── logging/              # Correlation and resilience logging
│   │   └── integration/          # Browser/selector/telemetry integration
│   ├── stealth/                  # Anti-detection, fingerprinting, proxies
│   ├── telemetry/                # Metrics, alerting, audit, reporting
│   │   ├── collector/            # Strategy, quality, performance collectors
│   │   ├── processor/            # Metrics processing and aggregation
│   │   ├── storage/              # JSON, InfluxDB, tiered storage
│   │   ├── alerting/             # Threshold monitoring, anomaly detection
│   │   ├── reporting/            # Health, performance, usage reports
│   │   ├── configuration/        # Alert thresholds, logging config
│   │   ├── models/               # Telemetry data models
│   │   ├── security/             # Data protection
│   │   └── optimization/         # Performance optimizer
│   ├── navigation/               # Route planning and page discovery
│   ├── extractor/                # Data extraction and transformation
│   ├── observability/            # Structured logging and event system
│   ├── interrupt_handling/       # Graceful shutdown and signal handling
│   ├── models/                   # Data models and schemas
│   ├── config/                   # Configuration management (settings.py, YAML)
│   ├── storage/                  # Data persistence and caching
│   ├── core/                     # Core utilities and shared components
│   │   ├── snapshot/             # Snapshot debugging system
│   │   └── shutdown/             # Graceful shutdown coordination
│   ├── extraction/               # Extraction strategies and processors
│   └── utils/                    # Utility functions and helpers
├── ui/                           # Web UI for system monitoring
│   └── app/                      # React/Vite + TailwindCSS application
│       └── src/
│           ├── components/       # UI components (FeatureFlagList, AuditLogViewer, etc.)
│           ├── pages/            # Page components (FeatureFlagsPage, AuditLogPage, etc.)
│           ├── hooks/            # React hooks (useFeatureFlags, useWebSocket, useFailures)
│           ├── api/              # API client (featureFlagApi)
│           └── types/            # TypeScript type definitions
├── tests/                        # Unit, integration, performance, stealth tests
├── docs/                         # Architecture docs, workflow guides, API reference
├── examples/                     # Runnable examples
├── scripts/                      # Migration and validation utilities
├── tools/                        # Plugins and migration tools
├── pyproject.toml                # Project metadata and build config
├── requirements.txt              # Python dependencies
└── pytest.ini                    # Pytest configuration
```

**Known stubs / areas to be completed:**
- `POST /api/upload` — file upload endpoint (if needed)
- WebSocket real-time updates (partially wired in UI)
- ML-based selector optimization (roadmap)
- GraphQL API integration (roadmap)

---

## 5. Git workflow

- Token: fine-grained PAT scoped to the Scrapamoja repo.
- Stored at `~/.git-credentials` (mode 600). User will delete manually when done.
- Standard workflow when making changes:
  1. Edit files in `/home/z/my-project/repos/scrapamoja/`
  2. Show `git diff` summary for review
  3. Wait for user's "commit & push" (or just "commit") instruction
  4. Commit with descriptive message, push to `origin main`

---

## 6. GitHub & Git setup

### One-time git config (already done)

```bash
git config --global user.name "Tisone Kironget"
git config --global user.email "tisonkironget@gmail.com"
git config --global credential.helper "store --file=~/.git-credentials"
touch ~/.git-credentials && chmod 600 ~/.git-credentials
mkdir -p /home/z/my-project/repos/
```

### Token

- User creates a **fine-grained PAT** in GitHub scoped to `TisoneK/scrapamoja` with:
  - **Contents** = Read and write (enables push)
  - **Metadata** = Read (auto-required)
  - **Pull requests** = Write (if doing PR workflows)
- Token is **per-session** — user generates it at the start of a chat and deletes it when done.
- Once the user pastes the token, write it to credentials:

```bash
# Write token (replace TOKEN with the actual value)
echo "https://TisoneK:TOKEN@github.com" > ~/.git-credentials

# Verify push works
cd /home/z/my-project/repos/scrapamoja/
git remote -v
git branch
```

### Standard session flow

1. User opens a new chat → generates a fresh PAT → pastes token here
2. Run the credentials step above
3. Work normally (edit → diff → commit & push)
4. User deletes the PAT from GitHub when the session is done

---

## 7. Tech stack (quick reference)

| Layer | Choice |
|-------|--------|
| Language | Python 3.12+ |
| Package manager | pip + venv |
| Framework | Custom scraping framework (Playwright-based) |
| Browser automation | Playwright (Chromium) |
| HTTP client | httpx (Direct API mode) |
| CLI | Click |
| API | FastAPI (uvicorn) |
| Data models | Pydantic v2 |
| Database | SQLAlchemy (optional) |
| Selectors | YAML-driven multi-strategy engine |
| Structured logging | structlog + Rich |
| Testing | pytest, pytest-asyncio, pytest-cov |
| Linting / Formatting | Black + Ruff |
| Type checking | mypy (strict) |
| UI | React + Vite + TypeScript + TailwindCSS |
| Telemetry storage | JSON (default), InfluxDB (optional) |
| HTML parsing | BeautifulSoup4 + lxml |

---

## 8. Code style & conventions

- Follow Black formatting (88 char line length).
- Ruff for linting (`ruff check src/`).
- Type hints are mandatory (enforced by mypy strict).
- Async-first: all scraping operations are async.
- YAML for selector configs — never hardcode selectors in Python.
- New sites must extend `BaseSiteScraper` and follow the template pattern.
- Feature flags control experimental behavior (defined in `src/resilience/config/feature_flags.py`).
- Structured JSON logging everywhere (use `src.observability.logger.get_logger`).

---

## 9. Running & testing

```bash
# Activate venv
source venv/bin/activate

# Run CLI
python -m src.main <site> <command> ...

# Run tests
pytest tests/

# Lint
ruff check src/

# Format
black src/

# Type check
mypy src/
```

---

## 10. Other

- User timezone: Africa/Nairobi (for any time/date interpretation).
- User communicates in English.
- When user-attached files arrive, they appear in `/home/z/my-project/upload/`.
  Always check there first.
