# FlashScore Web Scraper 🏀⚽

> **Professional-grade web scraper for FlashScore sports data** with intelligent selector strategies, multi-sport support, and production-ready resilience.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.40+-green.svg)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Examples](#-examples)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ Features

### 🎯 Core Capabilities
- **Multi-Sport Support**: Basketball, Football (easily extensible)
- **Status-Aware Scraping**: Live, Finished, and Scheduled matches
- **Smart Selectors**: Multi-strategy fallback system with confidence scoring
- **CLI Interface**: Simple command-line operation
- **Multiple Output Formats**: JSON, CSV, XML

### 🛡️ Production-Ready
- **Resilient Architecture**: Automatic retries, error recovery
- **Stealth Features**: Anti-detection measures
- **Session Management**: Cookie persistence, state tracking
- **Resource Monitoring**: Memory and performance tracking
- **Telemetry System**: Built-in metrics and alerting

### 🚀 Performance
- **Async/Await**: Non-blocking I/O for speed
- **Intelligent Caching**: Selector configuration caching
- **Rate Limiting**: Respectful scraping
- **Browser Pooling**: Efficient resource usage

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- Internet connection
- 2GB RAM minimum

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium
```

### First Scrape

```bash
# Scrape 1 scheduled basketball game
python -m src.sites.flashscore.cli.main scrape basketball scheduled --limit 1 --verbose
```

**Output:**
```json
{
  "sport": "Basketball",
  "status": "scheduled",
  "matches": [
    {
      "home_team": "Los Angeles Lakers",
      "away_team": "Boston Celtics",
      "scheduled_time": "2026-02-15 19:30",
      "url": "/basketball/usa/nba/...",
      "venue": "Crypto.com Arena",
      "competition": "NBA"
    }
  ],
  "total": 1
}
```

---

## 📦 Installation

### Option 1: Standard Installation

```bash
# Clone repository
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja

# Install with pip
pip install -r requirements.txt

# Install browsers
playwright install chromium
```

### Option 2: Docker Installation

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt && \
    playwright install chromium --with-deps

ENTRYPOINT ["python", "-m", "src.sites.flashscore.cli.main"]
```

```bash
# Build and run
docker build -t flashscore-scraper .
docker run flashscore-scraper scrape basketball live --limit 5
```

### Option 3: Development Installation

```bash
# Clone repository
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja

# Install with dev dependencies
pip install -r requirements.txt
pip install -e .

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

---

## 💻 Usage

### Basic Commands

#### Scrape Scheduled Games
```bash
python -m src.sites.flashscore.cli.main scrape basketball scheduled --limit 5
```

#### Scrape Live Games
```bash
python -m src.sites.flashscore.cli.main scrape basketball live --limit 10 --verbose
```

#### Scrape Finished Games
```bash
python -m src.sites.flashscore.cli.main scrape football finished --limit 20 -o csv -f results.csv
```

### Command Reference

```
python -m src.sites.flashscore.cli.main scrape [SPORT] [STATUS] [OPTIONS]
```

**Arguments:**
- `SPORT`: Sport to scrape
  - `basketball` - Basketball games
  - `football` - Football/Soccer games
  
- `STATUS`: Match status
  - `live` - Currently playing matches
  - `finished` - Completed matches
  - `scheduled` - Upcoming matches

**Options:**
- `--limit N` - Limit number of matches to scrape
- `--output, -o FORMAT` - Output format: `json`, `csv`, `xml` (default: json)
- `--file, -f PATH` - Save to file instead of stdout
- `--verbose, -v` - Enable detailed logging
- `--quiet, -q` - Suppress output except errors
- `--headless` - Run browser in headless mode (default)
- `--no-headless` - Show browser window (for debugging)
- `--config PATH` - Custom configuration file

### Output Formats

#### JSON (Default)
```bash
python -m src.sites.flashscore.cli.main scrape basketball live -o json
```

#### CSV
```bash
python -m src.sites.flashscore.cli.main scrape basketball live -o csv -f output.csv
```

#### XML
```bash
python -m src.sites.flashscore.cli.main scrape basketball live -o xml -f output.xml
```

### Advanced Usage

#### With Custom Configuration
```bash
python -m src.sites.flashscore.cli.main scrape basketball live \
  --config custom_config.yaml \
  --limit 50 \
  --verbose
```

#### Scrape and Save to Database
```bash
python -m src.sites.flashscore.cli.main scrape basketball finished \
  --limit 100 \
  -o json | python scripts/save_to_db.py
```

#### Continuous Scraping (Cron Job)
```bash
# Add to crontab for hourly scraping
0 * * * * cd /path/to/scrapamoja && python -m src.sites.flashscore.cli.main scrape basketball live --limit 50 -f /data/live_$(date +\%Y\%m\%d_\%H).json
```

---

## 🏗️ Architecture

### Project Structure

```
scrapamoja/
├── src/
│   ├── sites/
│   │   └── flashscore/           # FlashScore-specific implementation
│   │       ├── cli/               # Command-line interface
│   │       │   ├── main.py        # CLI entry point
│   │       │   ├── commands/      # Command implementations
│   │       │   │   ├── scrape.py  # Scraping command
│   │       │   │   ├── validate.py # Validation command
│   │       │   │   └── test.py    # Testing command
│   │       │   └── utils/         # CLI utilities
│   │       ├── flow.py            # Navigation flow logic
│   │       ├── selector_config.py # Selector configuration
│   │       └── selectors/         # YAML selector definitions
│   │           ├── authentication/ # Login, cookie consent
│   │           ├── extraction/     # Data extraction selectors
│   │           │   ├── match_summary/
│   │           │   ├── match_stats/
│   │           │   ├── match_odds/
│   │           │   └── match_h2h/
│   │           ├── filtering/      # Filter controls
│   │           └── navigation/     # Navigation elements
│   ├── browser/                   # Browser lifecycle management
│   ├── selectors/                 # Selector engine core
│   │   ├── engine/                # Selection engine
│   │   ├── strategies/            # Selection strategies
│   │   └── validation/            # Confidence validation
│   ├── navigation/                # Route planning
│   ├── resilience/                # Retry & recovery logic
│   ├── stealth/                   # Anti-detection features
│   └── telemetry/                 # Monitoring & metrics
├── tests/                         # Test suite
├── docs/                          # Documentation
├── examples/                      # Usage examples
└── requirements.txt               # Dependencies
```

### Component Overview

#### 1. **Selector System** 🎯
Hierarchical, context-aware element selection with multi-strategy fallback.

**Features:**
- YAML-based configurations
- Sport and status awareness
- Multiple fallback strategies (CSS, XPath)
- Confidence scoring (0.0-1.0)
- Tab context tracking

**Example Selector:**
```yaml
# src/sites/flashscore/selectors/extraction/match_summary/basketball/home_team.yaml
description: "Home team name"
confidence_threshold: 0.8
timeout: 3.0
retry_count: 2
strategies:
  - type: "css"
    selector: ".participant__home .participant__participantName"
    weight: 1.0
  - type: "css"
    selector: ".home-team-name"
    weight: 0.9
  - type: "xpath"
    selector: "//div[@class='participant__home']//div[@class='participant__participantName']"
    weight: 0.8
metadata:
  wait_for_element: true
  tab_context: "summary"
```

#### 2. **Flow Management** 🔄
Orchestrates navigation through FlashScore pages.

**Key Methods:**
- `open_home()` - Navigate to homepage
- `navigate_to_live_games(sport)` - Go to live matches
- `navigate_to_finished_games(sport)` - Go to finished matches
- `navigate_to_scheduled_games(sport)` - Go to scheduled matches
- `click_match(id)` - Open specific match
- `filter_by_competition(name)` - Filter by league

#### 3. **Browser Management** 🌐
Handles browser lifecycle, sessions, and stealth features.

**Features:**
- Session persistence
- Cookie management
- Stealth mode (anti-detection)
- Resource monitoring
- Automatic cleanup

#### 4. **Telemetry System** 📊
Monitors performance and collects metrics.

**Metrics Collected:**
- Selector success/failure rates
- Page load times
- Data extraction duration
- Error rates and types
- Resource usage

---

## ⚙️ Configuration

### Selector Configuration

Selectors are organized hierarchically:

```
Sport → Status → Context → Element

Example:
basketball → scheduled → summary → home_team
```

**Configuration Hierarchy:**
1. `basketball_scheduled_summary_home_team.yaml` (most specific)
2. `basketball_scheduled_home_team.yaml`
3. `basketball_home_team.yaml`
4. `home_team.yaml` (generic fallback)

### Sport Configuration

From `selector_config.yaml`:

```yaml
sports:
  basketball:
    name: "Basketball"
    path_segment: "basketball"
    data_attributes:
      sport_id: "3"
    match_periods:
      live: ["1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter", "Overtime"]
      finished: ["1st Quarter", "2nd Quarter", "3rd Quarter", "4th Quarter", "Overtime"]
    score_format:
      live: "current_score_with_periods"
      finished: "final_score_with_periods"
```

### Status Detection

```yaml
match_status_detection:
  live:
    indicators:
      - "detailScore__live"
      - "eventTime"
    status_text: ["Live", "1st Quarter", "2nd Quarter", ...]
  
  finished:
    indicators:
      - "fixedHeaderDuel__detailStatus:contains('Finished')"
    status_text: ["Finished", "After Overtime"]
  
  scheduled:
    indicators:
      - "duelParticipant__startTime"
    status_text: ["Scheduled", "Postponed"]
```

### Custom Configuration File

Create a custom configuration:

```yaml
# custom_config.yaml
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

output:
  default_format: "json"
  pretty_print: true
  include_metadata: true

logging:
  level: "INFO"
  file: "scraper.log"
```

Use it:
```bash
python -m src.sites.flashscore.cli.main scrape basketball live --config custom_config.yaml
```

---

## 📚 Examples

### Example 1: Basic Scraping

```bash
# Scrape 5 live basketball games
python -m src.sites.flashscore.cli.main scrape basketball live --limit 5
```

### Example 2: Save to File

```bash
# Scrape finished football matches and save to JSON
python -m src.sites.flashscore.cli.main scrape football finished \
  --limit 20 \
  -o json \
  -f matches_$(date +%Y%m%d).json
```

### Example 3: Verbose Debugging

```bash
# Run with visible browser and detailed logs
python -m src.sites.flashscore.cli.main scrape basketball scheduled \
  --limit 1 \
  --no-headless \
  --verbose
```

### Example 4: CSV Export

```bash
# Export to CSV for Excel/Google Sheets
python -m src.sites.flashscore.cli.main scrape basketball finished \
  --limit 100 \
  -o csv \
  -f basketball_results.csv
```

### Example 5: Continuous Monitoring

```bash
#!/bin/bash
# monitor_live_games.sh

while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    python -m src.sites.flashscore.cli.main scrape basketball live \
        --limit 50 \
        -o json \
        -f "data/live_${timestamp}.json"
    
    echo "Scraped at ${timestamp}"
    sleep 300  # Wait 5 minutes
done
```

### Example 6: Python Script Integration

```python
#!/usr/bin/env python3
"""
Example: Integrate scraper into Python script
"""
import asyncio
import json
from src.sites.flashscore.cli.commands.scrape import ScrapeCommand
from src.browser import BrowserManager
from src.selectors import get_selector_engine

async def scrape_and_process():
    """Scrape data and process it"""
    
    # Initialize components
    browser_manager = BrowserManager()
    selector_engine = get_selector_engine()
    scrape_cmd = ScrapeCommand()
    
    # Create mock args
    class Args:
        sport = "basketball"
        status = "live"
        limit = 10
        headless = True
        no_headless = False
        output = "json"
        file = None
        verbose = True
    
    # Execute scraping
    result = await scrape_cmd.execute(Args())
    
    # Process results
    if result == 0:
        print("✅ Scraping successful!")
        # Add your processing logic here
        # e.g., save to database, send notifications, etc.
    else:
        print("❌ Scraping failed!")

if __name__ == "__main__":
    asyncio.run(scrape_and_process())
```

### Example 7: Multiple Sports

```bash
#!/bin/bash
# scrape_all_sports.sh

for sport in basketball football; do
    for status in live finished scheduled; do
        echo "Scraping ${sport} ${status} matches..."
        python -m src.sites.flashscore.cli.main scrape ${sport} ${status} \
            --limit 20 \
            -o json \
            -f "data/${sport}_${status}_$(date +%Y%m%d).json"
    done
done
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError: pydantic

**Problem:**
```
ModuleNotFoundError: No module named 'pydantic'
```

**Solution:**
```bash
pip install -r requirements.txt
```

#### 2. Browser Not Installed

**Problem:**
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**Solution:**
```bash
playwright install chromium
```

#### 3. Selector Failed

**Problem:**
```
ERROR: All strategies failed for 'home_team'
```

**Solution:**
- FlashScore may have changed their HTML structure
- Update selector YAML files
- Run with `--verbose` to see which selectors are failing
- Check `src/sites/flashscore/selectors/` and update selectors

**Example Fix:**
```yaml
# Update the selector in home_team.yaml
strategies:
  - type: "css"
    selector: ".new-home-team-class"  # Updated selector
    weight: 1.0
```

#### 4. Network Timeout

**Problem:**
```
TimeoutError: Navigation timeout exceeded
```

**Solution:**
- Check internet connection
- Increase timeout in configuration
- Run with `--no-headless` to see what's happening

```yaml
# custom_config.yaml
browser:
  timeout: 60000  # Increase to 60 seconds
```

#### 5. Rate Limiting

**Problem:**
Getting blocked or seeing CAPTCHA

**Solution:**
- Add delays between requests
- Use stealth mode (enabled by default)
- Reduce scraping frequency

```bash
# Add delay between matches
python -m src.sites.flashscore.cli.main scrape basketball live \
  --limit 5 \
  --config slow_config.yaml
```

#### 6. No Matches Found

**Problem:**
```
{
  "matches": [],
  "total": 0
}
```

**Solution:**
- Verify the sport/status combination exists on FlashScore
- Check if matches are actually available
- Run with `--no-headless --verbose` to debug visually

### Debug Mode

Enable maximum verbosity:

```bash
python -m src.sites.flashscore.cli.main scrape basketball live \
  --limit 1 \
  --no-headless \
  --verbose \
  --config debug_config.yaml
```

**debug_config.yaml:**
```yaml
logging:
  level: "DEBUG"
  console: true
  file: "debug.log"

browser:
  headless: false
  devtools: true
  slow_mo: 1000  # Slow down actions by 1 second
```

### Getting Help

1. **Check logs**: Look at `scraper.log` for errors
2. **Run simulation**: Use the demo script to understand flow
3. **Check selectors**: Verify YAML configurations are correct
4. **Update dependencies**: `pip install --upgrade -r requirements.txt`
5. **Open an issue**: Provide logs, command used, and error message

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/integration/test_selector_resolution.py

# Run with coverage
pytest --cov=src tests/

# Run verbose
pytest -v tests/
```

### Test Structure

```
tests/
├── unit/                  # Unit tests
│   └── selectors/         # Selector engine tests
├── integration/           # Integration tests
│   ├── test_navigation_service.py
│   ├── test_selector_resolution.py
│   └── test_session_management.py
├── performance/           # Performance tests
└── fixtures/              # Test fixtures
    └── browser_configs/   # Browser configurations
```

---

## 📈 Performance Tips

### 1. Use Headless Mode

```bash
# Faster execution
python -m src.sites.flashscore.cli.main scrape basketball live --headless
```

### 2. Limit Concurrent Requests

```yaml
# config.yaml
scraping:
  concurrent_limit: 3  # Max 3 concurrent browser instances
```

### 3. Cache Selectors

Selector configurations are cached automatically. Clear cache if needed:

```bash
rm -rf .cache/selectors/
```

### 4. Optimize Timeouts

```yaml
# config.yaml
browser:
  timeout: 10000  # 10 seconds (default: 30s)
  
selectors:
  timeout: 3000   # 3 seconds per selector
```

### 5. Batch Processing

```python
# Process in batches
for i in range(0, 100, 10):
    cmd = f"python -m src.sites.flashscore.cli.main scrape basketball live --limit 10 -f batch_{i}.json"
    os.system(cmd)
```

---

## 🤝 Contributing

We welcome contributions! Here's how:

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/scrapamoja.git
cd scrapamoja
```

### 2. Create Branch

```bash
git checkout -b feature/new-sport-support
```

### 3. Make Changes

- Add new selectors in `src/sites/flashscore/selectors/`
- Update configuration in `selector_config.yaml`
- Add tests in `tests/`

### 4. Test

```bash
pytest tests/
black src/
ruff check src/
```

### 5. Commit & Push

```bash
git add .
git commit -m "Add tennis sport support"
git push origin feature/new-sport-support
```

### 6. Create Pull Request

Open a PR on GitHub with:
- Description of changes
- Test results
- Screenshots (if UI changes)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Playwright** - Excellent browser automation framework
- **Pydantic** - Data validation and settings management
- **FlashScore** - Sports data source

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TisoneK/scrapamoja/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TisoneK/scrapamoja/discussions)
- **Email**: support@example.com

---

## 🗺️ Roadmap

### v1.1 (Coming Soon)
- [ ] Tennis support
- [ ] Hockey support
- [ ] Enhanced telemetry dashboard
- [ ] Docker compose setup

### v1.2
- [ ] GraphQL API
- [ ] Real-time WebSocket updates
- [ ] Machine learning selector optimization
- [ ] Multi-region scraping

### v2.0
- [ ] Full ESPN support
- [ ] Full SofaScore support
- [ ] Cloud deployment templates
- [ ] SaaS API offering

---

## ⭐ Star History

If you find this useful, please star the repository!

---

**Built with ❤️ by the Scrapamoja Team**

*Last Updated: February 2026*
