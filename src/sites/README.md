# Wikipedia Site Implementation 📖

> **The Wikipedia scraper is a reference implementation built on the Scrapamoja framework.** It demonstrates how to build a content-focused scraper with structured extraction, data validation, and link/infobox processing.

---

## What It Scrapes

Wikipedia serves as a general-purpose knowledge source. This implementation extracts:

- **Article content** — title, body text, and sections
- **Infoboxes** — structured metadata panels (dates, locations, statistics, etc.)
- **Tables** — tabular data within articles
- **Links** — internal and external references
- **Search results** — article titles, URLs, and result descriptions from Wikipedia search

---

## Structure

```
wikipedia/
├── scraper.py              # WikipediaScraper — main scraper class
├── flow.py                 # WikipediaFlow — page navigation logic
├── config.py               # Site config (ID, base URL)
├── selector_loader.py      # YAML selector integration
├── integration_bridge.py   # Bridges selector engine with DOM context
├── extraction/             # Extraction logic and data models
│   ├── config.py           # Extraction configuration
│   ├── models.py           # ArticleExtractionResult, SearchExtractionResult, InfoboxData
│   ├── rules.py            # Extraction rules and heuristics
│   ├── validators.py       # Data validation
│   ├── statistics.py       # Extraction quality metrics
│   ├── cache.py            # Result caching
│   ├── infobox_processor.py  # Infobox parsing and normalization
│   └── link_processor.py    # Link extraction and classification
├── flows/
│   └── extraction_flow.py  # Orchestrates the full extraction pipeline
└── selectors/              # YAML selector definitions
    ├── search_input.yaml
    ├── search_results.yaml
    ├── result_title.yaml
    ├── result_url.yaml
    ├── result_description.yaml
    ├── article_title.yaml
    └── article_content.yaml
```

---

## How It Works

### Navigation Flow

The `WikipediaFlow` class handles page navigation:

```
Wikipedia search → Search results list → Article page → Content extraction
```

### Extraction Pipeline

The `ExtractionFlow` orchestrates extraction in stages:

1. **Basic content extraction** — title and body text via YAML selectors
2. **Rule application** — heuristics for cleaning and structuring raw content
3. **Specialized processing** — infobox parsing, link classification
4. **Validation** — checks data completeness and quality
5. **Quality metrics** — scores the extraction result

### Integration Bridge

Wikipedia uses a `WikipediaIntegrationBridge` that connects the YAML selector system with the DOM context — allowing selectors to be aware of page structure when resolving elements. This is initialized asynchronously after scraper creation via `initialize_yaml_selectors()`.

### Data Models

- `ArticleExtractionResult` — full article data including content, infobox, links, and quality metrics
- `SearchExtractionResult` — list of search result items with title, URL, and description
- `InfoboxData` — parsed key-value pairs from Wikipedia infobox panels
- `QualityMetrics` — confidence and completeness scores for the extraction

---

## Usage

```bash
# From the project root using the unified CLI
python -m src.main wikipedia extract "Python (programming language)"
python -m src.main wikipedia extract "2024_Summer_Olympics" --type table

# Or using the site CLI directly
python -m src.sites.wikipedia.cli.main extract "Basketball" --limit 5
```

---

## Selector Configuration

Selectors are defined in `selectors/` as YAML files. Example:

```yaml
# selectors/article_title.yaml
description: "Wikipedia article title"
strategies:
  - type: "css"
    selector: "#firstHeading"
    weight: 1.0
  - type: "css"
    selector: "h1.firstHeading"
    weight: 0.9
  - type: "xpath"
    selector: "//h1[@id='firstHeading']"
    weight: 0.8
```

---

## Extending

**Add a new extraction type (e.g. references section):**
1. Add a selector YAML under `selectors/`
2. Add a processing method in the relevant extractor or create a new processor class
3. Add a field to the appropriate data model in `extraction/models.py`
4. Update `extraction_flow.py` to include the new step

**Support a different language:**
Wikipedia's URL structure supports language subdomains (`en.wikipedia.org`, `fr.wikipedia.org`, etc.). Update `config.py` with the target language base URL and adjust selectors if the HTML structure differs.

---

## Troubleshooting

**Empty article content:**
Wikipedia's page structure can vary by article type (disambiguation pages, redirects, stub articles). Run with `--verbose` to see which selectors are resolving and which are falling back.

**Infobox not parsed:**
Not all articles have infoboxes. The `InfoboxData` field will be `None` for articles without one — this is expected behaviour.

**Search returning no results:**
Verify the search term matches Wikipedia's expected input format. Quoted phrases and special characters may need encoding.
