# Scrapamoja 🕷️

A production-grade Python framework for building reliable, extensible web scrapers — with battle-tested resilience, stealth, and observability built in.

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue) ![Playwright](https://img.shields.io/badge/Playwright-latest-green) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

---

## What is Scrapamoja?

Scrapamoja blends the English word **Scrape** with the Swahili word **Pamoja** — meaning *together*. Scrape together. One scraper, many sites. One framework, many contributors.

It's also a quiet nod to **Moja**, Swahili for *one* — the idea that you shouldn't need a different tool for every site you want to scrape. One framework should be enough, and it should be good enough that anyone can extend it.

That philosophy shapes everything about how Scrapamoja is built. It's not a scraper — it's the infrastructure that makes scrapers reliable: handling anti-bot measures, selector drift, network failures, and browser resource leaks so you don't have to. New sites can be added by anyone, existing ones improved by the community, and the whole thing grows stronger the more people contribute to it.

*Scrape together. Build together.*

---

## Core Framework Capabilities

### 🎯 Intelligent Selector Engine

The selector engine is the heart of Scrapamoja. Instead of brittle single-selector lookups, it uses a multi-strategy approach — CSS, XPath, and text-based selectors can all be defined for the same element. Each strategy is weighted, and the engine picks the best match with a confidence score. When a selector fails, it falls back gracefully rather than crashing. Selectors are defined in YAML, not hardcoded, making them easy to maintain without touching Python.

```
Site → Sport → Status → Context → Element
```

### 🛡️ Resilience System

Built around the assumption that things will go wrong. Automatic retries with exponential backoff, failure classification (network vs. selector vs. parse errors), checkpoint-based recovery so long scrapes can resume, and a coordinator that ensures graceful shutdown even mid-scrape.

### 🕵️ Stealth & Anti-Detection

A dedicated stealth module handles fingerprint randomization, human-like behavior simulation, consent popup handling, and proxy rotation. Sites that actively fight scrapers are manageable targets.

### 🔍 Snapshot Debugging

When a scrape fails, Scrapamoja captures a full snapshot: the page HTML, a screenshot, structured logs, and selector resolution traces — all correlated by session ID. Debugging a failure means looking at exactly what the browser saw, not guessing.

### 📊 Telemetry & Observability

Structured JSON logging with correlation IDs, built-in metrics collection (execution time, success rates, selector confidence distributions), and alerting hooks. Production scrapers need production-grade monitoring.

### 🌐 Browser Lifecycle Management

Browser and page pooling, session state persistence, tab management, resource monitoring (memory, CPU), and corruption detection. Long-running scrapers won't leak memory or leave orphaned browser processes.

---

## Architecture

```
scrapamoja/
├── src/
│   ├── main.py                   # Unified CLI entry point
│   ├── sites/                    # Site implementations
│   │   ├── _template/            # Full-featured template for new sites
│   │   ├── base/                 # BaseSiteScraper, registry, DI container
│   │   ├── flashscore/           # FlashScore scraper (Basketball, Football)
│   │   └── wikipedia/            # Wikipedia scraper
│   ├── selectors/                # Selector engine (YAML-driven, multi-strategy)
│   ├── browser/                  # Browser lifecycle, sessions, tab management
│   ├── resilience/               # Retries, failure classification, checkpoints
│   ├── stealth/                  # Anti-detection, fingerprinting, proxies
│   ├── telemetry/                # Metrics, alerting, audit, reporting
│   ├── navigation/               # Route planning and page discovery
│   ├── extractor/                # Data extraction and transformation
│   ├── observability/            # Structured logging and event system
│   └── interrupt_handling/       # Graceful shutdown and signal handling
├── tests/                        # Unit, integration, performance, stealth tests
├── docs/                         # Architecture docs, workflow guides, API reference
├── specs/                        # Feature specs (17+ completed)
├── examples/                     # Runnable examples
└── scripts/                      # Migration and validation utilities
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- 2GB RAM minimum (4GB recommended)
- Internet connection
- Git (for cloning)

### Installation

**Linux / macOS**

```bash
# 1. Clone repository
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Run your first scrape
python -m src.main flashscore scrape basketball live --limit 1
```

**Windows**

```bat
:: 1. Clone repository
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja

:: 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

:: 3. Install dependencies
pip install -r requirements.txt

:: 4. Install Playwright browsers
playwright install chromium

:: 5. Run your first scrape
python -m src.main flashscore scrape basketball live --limit 1
```

### First Results

```json
{
  "sport": "Basketball",
  "status": "live",
  "matches": [
    {
      "home_team": "Los Angeles Lakers",
      "away_team": "Boston Celtics",
      "score": "89-87",
      "time": "4th Quarter"
    }
  ],
  "total": 1
}
```

---

## 📦 Installation

### Option 1: Standard Installation

**Linux / macOS**

```bash
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

**Windows**

```bat
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### Option 2: Docker Installation

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && \
    playwright install chromium --with-deps

ENTRYPOINT ["python", "-m", "src.main"]
```

```bash
docker build -t scrapamoja .
docker run scrapamoja flashscore scrape basketball live --limit 5
```

### Option 3: Development Installation

**Linux / macOS**

```bash
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
pre-commit install
pytest tests/
```

**Windows**

```bat
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pre-commit install
pytest tests/
```

---

## Building a New Scraper

Scrapamoja ships with a full site template at `src/sites/_template/` — it's not a stub, it's a working skeleton with flows, processors, validators, config management, and component wiring already in place.

**1. Copy the template**

```bash
cp -r src/sites/_template src/sites/mysite
```

**2. Implement the scraper**

```python
from src.sites.base.site_scraper import BaseSiteScraper

class MySiteScraper(BaseSiteScraper):
    site_id = "mysite"
    site_name = "My Site"
    base_url = "https://example.com"
```

**3. Define selectors in YAML**

```yaml
# src/sites/mysite/selectors/extraction/listings.yaml
description: "Product listing items"
strategies:
  - type: "css"
    selector: ".product-card"
    weight: 1.0
  - type: "xpath"
    selector: "//div[@data-type='product']"
    weight: 0.8
```

**4. Register and run**

```python
# Add to SITE_CLIS in src/main.py
'mysite': ('src.sites.mysite.cli.main', 'MySiteCLI'),
```

---

## Supported Sites

| Site | Data | Sports / Topics | Status Types |
|------|------|-----------------|--------------|
| FlashScore | Live scores, match stats, odds | Basketball, Football | Live, Finished, Scheduled |
| Wikipedia | Article content, tables, references | Any | N/A |

Both are production implementations — the FlashScore scraper handles live match updates, status-aware extraction, and real-time polling. The Wikipedia scraper handles table parsing, multi-language articles, and reference extraction.

---

## Configuration

### Global config (`config.yaml`)

```yaml
browser:
  headless: true
  timeout: 30000
  viewport:
    width: 1920
    height: 1080

scraping:
  max_retries: 5
  retry_delay: 2.0
  rate_limit: 10  # requests per minute

logging:
  level: "INFO"
  structured: true
```

### CLI options

| Flag | Description |
|------|-------------|
| `--limit N` | Cap the number of results |
| `--output, -o FORMAT` | Output format: `json`, `csv`, `xml` |
| `--file, -f PATH` | Write output to file |
| `--headless / --no-headless` | Browser visibility (`--no-headless` for debugging) |
| `--verbose, -v` | Detailed logs |
| `--quiet, -q` | Errors only |

---

## Testing

```bash
# Full suite
pytest tests/

# With coverage
pytest --cov=src tests/

# By category
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
pytest tests/stealth/
```

---

## Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && \
    playwright install chromium --with-deps

ENTRYPOINT ["python", "-m", "src.main"]
```

```bash
docker build -t scrapamoja .
docker run scrapamoja flashscore scrape basketball live --limit 5
```

---

## Documentation

| Doc | Description |
|-----|-------------|
| `features.md` | Complete feature reference |
| `modular_template_guide.md` | Guide to building new site scrapers |
| `snapshot_api_reference.md` | Snapshot debugging system API |
| `yaml-configuration.md` | YAML selector config reference |
| `browser-lifecycle-management.md` | Browser pooling and session management |
| `structured-logging-guide.md` | Logging and observability guide |

---

## Roadmap

### v1.2 (Q2 2026)
- Enhanced error recovery mechanisms
- GraphQL API integration
- Real-time WebSocket updates
- ML-based selector optimization

### v1.3 (Q3 2026)
- Tennis and Hockey sport support
- Enhanced telemetry dashboard
- Cloud deployment templates

### v2.0 (Q4 2026)
- ESPN support
- Multi-region scraping
- SaaS API offering
- Advanced analytics dashboard

---

## Contributing

1. Fork and clone the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Follow the existing code style (Black + Ruff)
4. Add tests for new functionality
5. Run `pytest tests/` and `ruff check src/` before submitting
6. Open a PR with a description of what changed and why

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ by the Scrapamoja Team*