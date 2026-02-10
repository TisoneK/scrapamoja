# Wikipedia YAML Selector Configurations

This document describes the comprehensive YAML selector configurations created for Wikipedia automation, based on analysis of actual Wikipedia HTML structure.

## Overview

The YAML selector configurations provide a robust, multi-strategy approach to element location on Wikipedia pages. They support:

- **Multiple page types**: Main page, article pages, search results
- **Cross-page compatibility**: Universal selectors work across different Wikipedia layouts
- **Fallback mechanisms**: Multiple strategies per element with graceful degradation
- **Production-ready**: Confidence scoring, timeouts, and error handling

## Available Configurations

### 1. `search_input` - Wikipedia Search Input Field
**Purpose**: Locate search input fields across all Wikipedia page types

**Strategies** (5 total):
1. **Main page**: `input#searchInput` (type='text')
2. **Article page**: `.mw-searchInput` (type='search')
3. **Universal**: `//input[@name='search']`
4. **Combined**: `input[type='search'], input[name='search']`
5. **Text fallback**: "Search Wikipedia" (input context)

### 2. `search_button` - Wikipedia Search Button
**Purpose**: Locate search submission buttons

**Strategies** (5 total):
1. **Main page**: `button[type='submit']`
2. **Article page**: `.cdx-search-input__end-button`
3. **Generic**: `form button`
4. **XPath**: `//form//button`
5. **Text fallback**: "Search" (button context)

### 3. `search_results` - Wikipedia Search Result Links
**Purpose**: Locate search result links on search results pages

**Strategies** (5 total):
1. **Primary**: `.mw-search-result-heading a`
2. **Alternative**: `.mw-search-result-data a`
3. **XPath nested**: `//div[@class='mw-search-result-heading']//a`
4. **XPath list**: `//li[@class='mw-search-result']//a`
5. **Text fallback**: "Python" (link context)

### 4. `article_content` - Wikipedia Article Main Content
**Purpose**: Locate main article content area

**Strategies** (3 total):
1. **Primary**: `#mw-content-text`
2. **Class**: `.mw-body-content`
3. **XPath**: `//div[@id='mw-content-text']`

### 5. `article_title` - Wikipedia Article Title
**Purpose**: Locate article title heading

**Strategies** (3 total):
1. **Primary**: `#firstHeading`
2. **Class**: `.mw-first-heading`
3. **XPath**: `//h1[@id='firstHeading']`

### 6. `main_page_content` - Wikipedia Main Page Content
**Purpose**: Locate main page featured content

**Strategies** (3 total):
1. **Primary**: `.central-featured`
2. **Wrapper**: `#main-page`
3. **XPath**: `//div[@class='central-featured']`

### 7. `navigation_links` - Wikipedia Navigation Menu Links
**Purpose**: Locate navigation menu links

**Strategies** (3 total):
1. **Navigation panel**: `#p-navigation a`
2. **Vector menu**: `.vector-menu-content a`
3. **Generic**: `//nav//a`

### 8. `table_of_contents` - Wikipedia Table of Contents
**Purpose**: Locate article table of contents

**Strategies** (3 total):
1. **Primary**: `#toc`
2. **Vector**: `.vector-toc`
3. **XPath**: `//div[@id='toc']`

### 9. `external_links` - Wikipedia External Reference Links
**Purpose**: Locate external reference links

**Strategies** (3 total):
1. **Styling**: `.external.text`
2. **Nofollow**: `a[rel='nofollow']`
3. **XPath**: `//a[contains(@class, 'external')]`

### 10. `language_links` - Wikipedia Language Selection Links
**Purpose**: Locate language selection links

**Strategies** (3 total):
1. **Language panel**: `#p-lang a`
2. **Interlanguage**: `.interlanguage-link`
3. **XPath**: `//div[@id='p-lang']//a`

## HTML Structure Analysis

### Main Page (wikipedia.org)
- **Search**: Pure-form style with `input#searchInput` (type='text')
- **Button**: `button[type='submit']`
- **Content**: `.central-featured` area
- **Navigation**: `.other-project-link` elements

### Article Pages (Vector 2022)
- **Search**: `.mw-searchInput` (type='search') with modern UI
- **Button**: `.cdx-search-input__end-button`
- **Title**: `#firstHeading` (h1 element)
- **Content**: `#mw-content-text` main area
- **TOC**: `#toc` table of contents
- **External**: `.external.text` styled links

### Search Results Pages
- **Results**: `.mw-search-result-heading a` result links
- **Data**: `.mw-search-result-data a` additional info
- **Navigation**: `.mw-search-result-list` containers

## Best Practices Implemented

### Priority Strategy
1. **Most specific first**: ID > Class > Attribute > Tag
2. **CSS for performance**: Fastest execution
3. **XPath for complexity**: Powerful relationship matching
4. **Text fallback**: Most flexible, slowest

### Robustness Features
- **Multiple fallbacks**: 3-5 strategies per element
- **Attribute validation**: Expected attributes for confidence
- **Context awareness**: Search context for text selectors
- **Confidence thresholds**: Configurable per element type

### Performance Considerations
- **CSS selectors**: Fastest (recommended)
- **XPath**: Moderate overhead, powerful
- **Text-based**: Slowest, most flexible
- **Timeouts**: 1500ms per strategy

## Usage Examples

### Basic Usage
```python
from selector_config_loader import get_selector_config

# Load configuration
search_config = get_selector_config('search_input')

# Use with selector engine
element = await selector_engine.locate_element(page, search_config)
```

### Fallback Strategy
```python
# Try multiple configurations
configs = [
    get_selector_config('search_input'),
    get_selector_config('main_page_content')
]

for config in configs:
    element = await selector_engine.locate_element(page, config)
    if element:
        break  # Found with this config
```

### Environment Configuration
```bash
# Enable debug mode
export DEBUG_SELECTOR=1

# Run example
python -m examples.browser_lifecycle_example
```

## Integration with Browser Lifecycle Example

The YAML configurations are automatically integrated into the `browser_lifecycle_example.py`:

1. **Automatic loading**: Configurations loaded from YAML when available
2. **Graceful fallback**: Falls back to hardcoded configs if YAML unavailable
3. **Enhanced search**: Uses multi-strategy approach for robust element location
4. **Telemetry**: Tracks strategy performance and success rates

## File Structure

```
examples/
├── wikipedia_selectors.yaml          # Main configuration file
├── selector_config_loader.py         # YAML loading utility
├── test_yaml_configs.py              # Configuration testing
├── wikipedia_selector_demo.py         # Comprehensive demonstration
├── browser_lifecycle_example.py      # Integration example
└── wikipedia_raw_html.html           # Reference HTML structure
```

## Testing

Run the test suite to verify configurations:

```bash
cd examples
python test_yaml_configs.py
```

Run the demonstration:

```bash
cd examples
python wikipedia_selector_demo.py
```

## Benefits

- **Cross-page compatibility**: Works on main page, articles, and search results
- **Production-ready**: Robust error handling and fallbacks
- **Maintainable**: YAML-based declarative configuration
- **Extensible**: Easy to add new configurations or strategies
- **Performance-optimized**: CSS-first approach with timeouts
- **Well-documented**: Comprehensive descriptions and examples

## Future Enhancements

- **Mobile-specific configurations**: Add mobile Wikipedia layouts
- **Language-specific**: Add configurations for different language Wikipedias
- **Dynamic loading**: Support for AJAX-loaded content
- **Visual testing**: Integration with visual regression testing
- **Performance monitoring**: Advanced telemetry and analytics

This YAML configuration system provides a solid foundation for reliable Wikipedia automation across different page types and layouts.
