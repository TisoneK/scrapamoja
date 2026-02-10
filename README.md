# Scrapamoja 🕷️

> **Production-grade web scraping framework with intelligent selector strategies, multi-site support, and enterprise-ready resilience**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.40+-green.svg)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/TisoneK/scrapamoja/actions)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features) 
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [Supported Sites](#-supported-sites)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Development](#-development)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

Scrapamoja is a sophisticated web scraping framework designed for production environments. It combines intelligent selector strategies, robust error handling, and comprehensive monitoring to extract data from sports websites reliably.

### 🚀 Key Capabilities

- **Multi-Site Architecture**: Support for FlashScore, Wikipedia, and more
- **Intelligent Selectors**: Multi-strategy fallback with confidence scoring
- **Production Ready**: Built-in resilience, retries, and error recovery
- **Enterprise Features**: Telemetry, monitoring, and stealth capabilities
- **Developer Friendly**: Extensible architecture with comprehensive documentation

---

## ✨ Features

### 🎯 Core Scraping
- **Multi-Site Support**: FlashScore, Wikipedia (easily extensible)
- **Sport-Specific Logic**: Basketball, Football, Tennis, Hockey, etc.
- **Status-Aware Extraction**: Live, Finished, Scheduled matches
- **Smart Selectors**: CSS, XPath, and text-based strategies
- **Confidence Scoring**: Automatic selector validation and ranking

### 🛡️ Production Features
- **Resilient Architecture**: Automatic retries with exponential backoff
- **Stealth Mode**: Anti-detection measures and fingerprint randomization
- **Session Management**: Cookie persistence and state tracking
- **Resource Monitoring**: Memory, CPU, and performance tracking
- **Rate Limiting**: Respectful scraping with configurable delays

### 📊 Observability
- **Built-in Telemetry**: Comprehensive metrics collection
- **Structured Logging**: JSON-based logs with correlation IDs
- **Error Classification**: Intelligent error categorization and recovery
- **Performance Analytics**: Execution time and success rate tracking

### 🚀 Performance
- **Async/Await**: Non-blocking I/O for maximum speed
- **Browser Pooling**: Efficient resource utilization
- **Intelligent Caching**: Selector and response caching
- **Concurrent Processing**: Multiple sites simultaneously

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- 2GB RAM minimum (4GB recommended)
- Internet connection
- Git (for cloning)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Run your first scrape
python -m src.sites.flashscore.cli.main scrape basketball live --limit 1
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

```bash
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
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

ENTRYPOINT ["python", "-m", "src.sites.flashscore.cli.main"]
```

```bash
docker build -t scrapamoja .
docker run scrapamoja scrape basketball live --limit 5
```

### Option 3: Development Installation

```bash
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
pip install -r requirements.txt
pip install -e .
pre-commit install
pytest tests/
```

---

## 🏗️ Project Structure

```
scrapamoja/
├── src/                          # Source code
│   ├── sites/                    # Site-specific scrapers
│   │   ├── flashscore/           # FlashScore implementation
│   │   │   ├── cli/             # Command-line interface
│   │   │   ├── selectors/        # YAML selector definitions
│   │   │   ├── flow.py          # Navigation logic
│   │   │   └── scraper.py       # Main scraper class
│   │   └── wikipedia/          # Wikipedia implementation
│   ├── browser/                  # Browser lifecycle management
│   ├── selectors/                # Core selector engine
│   ├── navigation/               # Route planning and discovery
│   ├── resilience/               # Error handling and retries
│   ├── stealth/                  # Anti-detection features
│   ├── telemetry/                # Monitoring and metrics
│   └── observability/            # Logging and events
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data and configs
├── docs/                        # Documentation
├── examples/                    # Usage examples
├── scripts/                     # Utility scripts
└── requirements.txt              # Dependencies
```

---

## 🌐 Supported Sites

### FlashScore (`src/sites/flashscore/`)
**Sports**: Basketball, Football  
**Status**: Live, Finished, Scheduled  
**Features**: 
- Real-time score updates
- Match statistics and odds
- Team and player information
- Historical data access

**Documentation**: [FlashScore README](src/sites/flashscore/README.md)

### Wikipedia (`src/sites/wikipedia/`)
**Topics**: Sports, general articles  
**Features**:
- Article content extraction
- Table data parsing
- Reference and link collection
- Multi-language support

---

## 💻 Usage

### FlashScore Scraping

```bash
# Basic usage
python -m src.sites.flashscore.cli.main scrape [SPORT] [STATUS] [OPTIONS]

# Examples
python -m src.sites.flashscore.cli.main scrape basketball live --limit 10
python -m src.sites.flashscore.cli.main scrape football finished -o csv -f results.csv
python -m src.sites.flashscore.cli.main scrape basketball scheduled --no-headless --verbose
```

### Wikipedia Scraping

```bash
# Basic article extraction
python -m src.sites.wikipedia.cli.main extract "Basketball" --limit 5

# Table data extraction
python -m src.sites.wikipedia.cli.main extract "2024_Summer_Olympics" --type table
```

### Command Options

**Global Options:**
- `--verbose, -v`: Enable detailed logging
- `--quiet, -q`: Suppress output except errors
- `--config PATH`: Custom configuration file

**Scraping Options:**
- `--limit N`: Limit number of items to scrape
- `--output, -o FORMAT`: Output format (json, csv, xml)
- `--file, -f PATH`: Save to file instead of stdout
- `--headless`: Run browser in headless mode
- `--no-headless`: Show browser window (for debugging)

---

## ⚙️ Configuration

### Global Configuration

Create `config.yaml` in project root:

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
  file: "scraper.log"
  structured: true
```

### Site-Specific Configuration

Each site has its own configuration:

- **FlashScore**: `src/sites/flashscore/selector_config.yaml`
- **Wikipedia**: `src/sites/wikipedia/config.yaml`

### Selector Configuration

Selectors are organized hierarchically:

```
Site → Sport → Status → Context → Element
```

Example: `flashscore → basketball → live → summary → home_team`

---

## 🧪 Development

### Setting Up Development Environment

```bash
git clone https://github.com/TisoneK/scrapamoja.git
cd scrapamoja
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pre-commit install
```

### Adding New Sites

1. **Create Site Structure**:
   ```bash
   mkdir src/sites/mysite
   touch src/sites/mysite/__init__.py
   ```

2. **Implement Scraper**:
   ```python
   from src.sites.base.site_scraper import BaseSiteScraper
   
   class MySiteScraper(BaseSiteScraper):
       site_id = "mysite"
       site_name = "My Site"
       base_url = "https://example.com"
   ```

3. **Add CLI Interface**:
   ```python
   # src/sites/mysite/cli/main.py
   from .commands.scrape import ScrapeCommand
   
   # CLI setup similar to FlashScore
   ```

4. **Add Selectors**:
   ```yaml
   # src/sites/mysite/selectors/extraction/main_content.yaml
   description: "Main content area"
   strategies:
     - type: "css"
       selector: ".main-content"
       weight: 1.0
   ```

### Code Quality

```bash
# Run linting
black src/
ruff check src/
mypy src/

# Run tests
pytest tests/ --cov=src

# Format code
black src/
ruff format src/
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/integration/test_flashscore.py

# Run with coverage
pytest --cov=src tests/

# Run performance tests
pytest tests/performance/ -v
```

### Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_selectors/     # Selector engine tests
│   ├── test_browser/        # Browser management tests
│   └── test_resilience/    # Error handling tests
├── integration/             # End-to-end tests
│   ├── test_flashscore.py   # FlashScore integration
│   └── test_wikipedia.py   # Wikipedia integration
├── performance/            # Performance benchmarks
└── fixtures/              # Test data and configurations
```

### Writing Tests

```python
# Example test
import pytest
from src.sites.flashscore.scraper import FlashscoreScraper

@pytest.mark.asyncio
async def test_flashscore_scraper():
    """Test FlashScore scraper initialization"""
    scraper = FlashscoreScraper(mock_page, mock_selector_engine)
    assert scraper.site_id == "flashscore"
    assert scraper.base_url == "https://www.flashscore.com"
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/scrapamoja.git
cd scrapamoja
```

### 2. Create Branch

```bash
git checkout -b feature/new-feature
```

### 3. Make Changes

- Follow existing code style (Black, Ruff)
- Add tests for new functionality
- Update documentation
- Ensure all tests pass

### 4. Test & Submit

```bash
pytest tests/
black src/
ruff check src/
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

### 5. Pull Request

- Open PR on GitHub
- Include description and test results
- Ensure CI passes
- Request code review

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Playwright** - Excellent browser automation framework
- **Pydantic** - Data validation and settings management  
- **FlashScore** - Sports data source
- **Wikipedia** - Knowledge base source
- **Python Community** - Tools and libraries that make this possible

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TisoneK/scrapamoja/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TisoneK/scrapamoja/discussions)
- **Email**: support@example.com

---

## 🗺️ Roadmap

### v1.2 (Q2 2026)
- [ ] Enhanced error recovery mechanisms
- [ ] GraphQL API integration
- [ ] Real-time WebSocket updates
- [ ] Machine learning selector optimization

### v1.3 (Q3 2026)
- [ ] Tennis sport support
- [ ] Hockey sport support
- [ ] Enhanced telemetry dashboard
- [ ] Cloud deployment templates

### v2.0 (Q4 2026)
- [ ] Full ESPN support
- [ ] Multi-region scraping
- [ ] SaaS API offering
- [ ] Advanced analytics dashboard

---

## ⭐ Star History

If you find this useful, please star the repository! ⭐

---

**Built with ❤️ by the Scrapamoja Team**

*Last Updated: February 2026*
