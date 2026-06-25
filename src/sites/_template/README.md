# Site Template

A production-ready template for building new Scrapamoja site implementations. Copy this directory to get flows, processors, validators, components, and multi-environment config wiring out of the box.

```bash
cp -r src/sites/_template src/sites/your_site_name
```

---

## Choosing an Architectural Pattern

The template supports four patterns — pick based on your site's complexity:

| Pattern | Best For | Structure |
|---------|----------|-----------|
| **Simple** | Static sites, basic navigation | Single `flow.py` |
| **Standard** | Dynamic sites, search + pagination | `flow.py` + `flows/` directory |
| **Complex** | SPAs, multi-domain operations (nav/extraction/filtering/auth) | Domain-separated `flows/` subdirectories |
| **Legacy** | Backward compatibility | Original flat flow structure |

**Decision guide:**
- Static site with simple navigation → **Simple**
- Dynamic site with search or pagination → **Standard**
- SPA with distinct navigation, extraction, filtering, and auth concerns → **Complex**
- Maintaining an existing scraper → **Legacy** (or migrate gradually)

---

## Directory Structure

```
_template/
├── scraper.py               # Main scraper — inherits ModularSiteScraper
├── flow.py                  # Navigation logic
├── config.py                # Site config entry point
├── models.py                # Site-specific data models
├── validation.py            # Validation helpers
├── patterns/                # Architectural patterns
│   ├── simple/              # Single flow.py
│   ├── standard/            # flow.py + flows/ (search, pagination, extraction)
│   └── complex/             # Domain-separated flows (navigation, extraction, filtering, auth)
├── flows/                   # Legacy flat flow structure
│   ├── base_flow.py
│   ├── search_flow.py
│   ├── login_flow.py
│   └── pagination_flow.py
├── config/                  # Multi-environment configuration
│   ├── base.py
│   ├── dev.py
│   ├── prod.py
│   └── feature_flags.py
├── processors/              # Data processing pipeline
│   ├── normalizer.py        # HTML decoding, whitespace, case
│   ├── validator.py         # Type checks, business rules
│   └── transformer.py       # Field mapping, calculated fields
├── validators/              # Config and data validation
├── components/              # Reusable components
│   ├── oauth_auth.py        # OAuth 1.0a / 2.0
│   ├── rate_limiter.py      # Token bucket, sliding window, fixed window
│   └── stealth_handler.py   # Fingerprint randomization, anti-detection
└── DOMAINS/                 # Domain reference docs
```

---

## Quick Setup

**1. Copy and rename**
```bash
cp -r src/sites/_template src/sites/your_site_name
```

**2. Update `config.py`**
```python
SITE_CONFIG = {
    "id": "your_site_name",       # lowercase, underscores only
    "name": "Your Site Name",
    "base_url": "https://example.com",
    "version": "1.0.0",
    "maintainer": "you@example.com",
    "description": "What this scraper does",
    "tags": ["category"]
}
```

**3. Implement `scraper.py`**
```python
from src.sites.base.site_scraper import BaseSiteScraper
from .flow import YourSiteFlow
from .config import SITE_CONFIG

class YourSiteScraper(BaseSiteScraper):
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.flow = YourSiteFlow(page, selector_engine)

    async def navigate(self):
        await self.flow.open_home()

    async def scrape(self, **kwargs):
        return {"data": []}

    def normalize(self, raw_data):
        return raw_data
```

**4. Define selectors in `selectors/`**
```yaml
# selectors/search_input.yaml
description: "Search input field"
confidence_threshold: 0.7
strategies:
  - type: "css"
    selector: "input[type='search']"
    weight: 1.0
  - type: "xpath"
    selector: "//input[@type='search']"
    weight: 0.8
```

**5. Register in `src/main.py`**
```python
SITE_CLIS = {
    ...
    'your_site_name': ('src.sites.your_site_name.cli.main', 'YourSiteCLI'),
}
```

---

## Components

### Rate Limiter
```python
rate_limiter = RateLimiterComponent()
rate_limiter.set_domain_limits("example.com", requests_per_second=2.0)
```

### Stealth Handler
```python
stealth = StealthHandlerComponent()
await stealth.execute(page=page, apply_all=True)
```

### OAuth Authentication
```python
oauth = OAuthAuthComponent()
oauth.configure_oauth(
    oauth_version="2.0",
    client_id="your_client_id",
    client_secret="your_client_secret",
    authorization_url="https://example.com/oauth/authorize",
    token_url="https://example.com/oauth/token"
)
```

---

## Configuration

**Development (`config/dev.py`)**
```python
class DevConfig(BaseConfig):
    headless = False
    debug = True
    log_level = "DEBUG"
    requests_per_second = 1.0
```

**Production (`config/prod.py`)**
```python
class ProdConfig(BaseConfig):
    headless = True
    debug = False
    log_level = "INFO"
    requests_per_second = 0.5
```

**Feature flags (`config/feature_flags.py`)**
```python
FEATURE_FLAGS = {
    "advanced_search": {
        "enabled": True,
        "environments": ["dev", "prod"],
        "percentage": 100
    }
}
```

---

## Reference Implementations

- [`src/sites/flashscore/`](../flashscore/) — Complex pattern: sport-aware extraction, status-based flows, hierarchical selectors, snapshot integration
- [`src/sites/wikipedia/`](../wikipedia/) — Standard pattern: search flow, article extraction pipeline, infobox and link processing
