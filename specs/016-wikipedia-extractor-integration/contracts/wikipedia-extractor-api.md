# Wikipedia Extractor Integration API Specification

## Overview

This specification defines the API contracts for integrating the extractor module with the Wikipedia scraper, providing enhanced data extraction capabilities with structured rules, type conversion, and advanced pattern matching.

## Core Components

### EnhancedWikipediaScraper

#### Class Definition

```python
class EnhancedWikipediaScraper(WikipediaScraper):
    """Enhanced Wikipedia scraper with extractor module integration."""
    
    def __init__(self, page, selector_engine):
        """Initialize enhanced scraper with extraction capabilities."""
        
    async def scrape_with_extraction(self, **kwargs) -> Dict[str, Any]:
        """Enhanced scraping with advanced extraction."""
        
    def set_extraction_rules(self, rules: Dict[str, ExtractionRule]) -> None:
        """Set custom extraction rules."""
        
    def set_validator(self, validator: WikipediaDataValidator) -> None:
        """Set data validator."""
        
    def set_default_values(self, defaults: Dict[str, Any]) -> None:
        """Set default values for missing data."""
        
    def enable_caching(self, enabled: bool) -> None:
        """Enable/disable extraction caching."""
        
    def enable_debug_logging(self, enabled: bool) -> None:
        """Enable debug logging."""
        
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get extraction performance statistics."""
```

#### Methods

##### scrape_with_extraction

**Purpose**: Enhanced scraping with advanced extraction capabilities

**Parameters**:
- `query` (str, optional): Search query for search results extraction
- `article_title` (str, optional): Article title for article extraction
- `extraction_config` (Dict, optional): Custom extraction configuration
- `validation_enabled` (bool, optional): Enable data validation (default: True)
- `performance_monitoring` (bool, optional): Enable performance monitoring (default: True)

**Returns**:
```python
{
    "success": bool,
    "data": Dict[str, Any],
    "metadata": {
        "extraction_time_ms": float,
        "data_quality_score": float,
        "validation_results": Dict[str, Any],
        "performance_metrics": Dict[str, Any]
    },
    "errors": List[str],
    "warnings": List[str]
}
```

**Example**:
```python
result = await scraper.scrape_with_extraction(
    article_title="Python (programming language)",
    validation_enabled=True,
    performance_monitoring=True
)
```

### WikipediaExtractionConfig

#### Class Definition

```python
class WikipediaExtractionConfig:
    """Configuration for Wikipedia-specific extraction rules."""
    
    def __init__(self):
        """Initialize with default extraction rules."""
        
    def add_article_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add article extraction rule."""
        
    def add_infobox_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add infobox extraction rule."""
        
    def add_search_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add search result extraction rule."""
        
    def get_rules_by_type(self, extraction_type: str) -> Dict[str, ExtractionRule]:
        """Get rules by extraction type."""
        
    def validate_rules(self) -> ValidationResult:
        """Validate all extraction rules."""
```

#### Default Configuration

```python
DEFAULT_ARTICLE_RULES = {
    "title": ExtractionRule(
        name="title",
        field_path="title",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.TEXT,
        transformations=[TransformationType.TRIM, TransformationType.CLEAN],
        required=True
    ),
    "publication_date": ExtractionRule(
        name="publication_date",
        field_path="publication_date",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.DATE,
        regex_pattern=r"(\d{1,2}\s+\w+\s+\d{4})",
        transformations=[TransformationType.TRIM]
    ),
    "word_count": ExtractionRule(
        name="word_count",
        field_path="word_count",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.INTEGER,
        regex_pattern=r"(\d+)\s+words",
        transformations=[TransformationType.TRIM]
    ),
    "categories": ExtractionRule(
        name="categories",
        field_path="categories",
        extraction_type=ExtractionType.LIST,
        target_type=DataType.TEXT,
        transformations=[TransformationType.TRIM, TransformationType.CLEAN]
    )
}
```

### WikipediaDataValidator

#### Class Definition

```python
class WikipediaDataValidator:
    """Wikipedia-specific data validation and quality assessment."""
    
    def __init__(self):
        """Initialize with default validation rules."""
        
    def validate_article_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate article data structure and content."""
        
    def validate_infobox_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate infobox data types and formats."""
        
    def validate_search_results(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """Validate search results data."""
        
    def assess_data_quality(self, data: Dict[str, Any]) -> QualityMetrics:
        """Assess overall data quality."""
        
    def set_validation_rules(self, rules: Dict[str, Dict[str, Any]]) -> None:
        """Set custom validation rules."""
```

#### Validation Rules

```python
DEFAULT_VALIDATION_RULES = {
    "title": {
        "required": True,
        "min_length": 1,
        "max_length": 255,
        "pattern": r"^[A-Za-z0-9\s\-_()]+$"
    },
    "word_count": {
        "required": False,
        "type": "integer",
        "min_value": 0,
        "max_value": 1000000
    },
    "publication_date": {
        "required": False,
        "type": "date",
        "min_date": "2000-01-01",
        "max_date": "today"
    },
    "categories": {
        "required": False,
        "type": "list",
        "min_length": 0,
        "max_length": 100
    }
}
```

## Data Structures

### ArticleExtractionResult

```python
@dataclass
class ArticleExtractionResult:
    """Structured result for article extraction."""
    
    title: str
    publication_date: Optional[datetime]
    word_count: Optional[int]
    categories: List[str]
    infobox: Dict[str, Any]
    table_of_contents: List[Dict[str, Any]]
    links: Dict[str, List[Dict[str, Any]]]
    content: str
    url: str
    scraped_at: datetime
    metadata: Dict[str, Any]
```

### SearchExtractionResult

```python
@dataclass
class SearchExtractionResult:
    """Structured result for search extraction."""
    
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    search_metadata: Dict[str, Any]
    scraped_at: datetime
    performance_metrics: Dict[str, Any]
```

### QualityMetrics

```python
@dataclass
class QualityMetrics:
    """Data quality assessment metrics."""
    
    score: float  # 0.0 to 1.0
    completeness: float  # Percentage of expected data present
    accuracy: float  # Estimated accuracy based on validation
    consistency: float  # Consistency across similar data
    issues: List[str]  # Quality issues found
    recommendations: List[str]  # Improvement recommendations
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    """Result of data validation."""
    
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    score: float  # Validation score 0.0 to 1.0
```

## API Endpoints

### Article Extraction

#### Endpoint: `/api/wikipedia/article/extract`

**Method**: POST

**Request Body**:
```json
{
    "article_title": "Python (programming language)",
    "extraction_config": {
        "include_infobox": true,
        "include_toc": true,
        "include_links": true,
        "validation_enabled": true
    },
    "performance_options": {
        "enable_caching": true,
        "timeout_ms": 5000
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "title": "Python (programming language)",
        "publication_date": "1991-02-20",
        "word_count": 15420,
        "categories": ["Programming languages", "High-level programming languages"],
        "infobox": {
            "paradigm": ["Multi-paradigm"],
            "first_appeared": 1991,
            "developer": "Guido van Rossum"
        },
        "table_of_contents": [
            {
                "title": "History",
                "depth": 1,
                "anchor": "History",
                "subsections": [...]
            }
        ],
        "links": {
            "internal": [...],
            "external": [...],
            "references": [...],
            "images": [...]
        }
    },
    "metadata": {
        "extraction_time_ms": 1234.5,
        "data_quality_score": 0.95,
        "validation_results": {...},
        "performance_metrics": {...}
    }
}
```

### Search Results Extraction

#### Endpoint: `/api/wikipedia/search/extract`

**Method**: POST

**Request Body**:
```json
{
    "query": "machine learning",
    "extraction_config": {
        "max_results": 10,
        "include_relevance_scores": true,
        "include_article_sizes": true
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "query": "machine learning",
        "results": [
            {
                "title": "Machine learning",
                "url": "https://en.wikipedia.org/wiki/Machine_learning",
                "relevance_score": 0.95,
                "article_size": 45230,
                "last_modified": "2024-01-15T10:30:00Z",
                "description": "Machine learning is a field of study..."
            }
        ],
        "total_count": 8
    }
}
```

## Error Handling

### Error Types

```python
class WikipediaExtractionError(Exception):
    """Base exception for Wikipedia extraction errors."""
    pass

class ArticleNotFoundError(WikipediaExtractionError):
    """Raised when article cannot be found."""
    pass

class ExtractionValidationError(WikipediaExtractionError):
    """Raised when data validation fails."""
    pass

class PerformanceThresholdExceeded(WikipediaExtractionError):
    """Raised when extraction exceeds performance thresholds."""
    pass
```

### Error Response Format

```json
{
    "success": false,
    "error": {
        "type": "ArticleNotFoundError",
        "message": "Article 'Non-existent Article' not found",
        "code": "ARTICLE_NOT_FOUND",
        "details": {
            "article_title": "Non-existent Article",
            "suggested_alternatives": [...]
        }
    },
    "timestamp": "2024-01-29T18:45:00Z"
}
```

## Performance Requirements

### Response Times

- Article extraction: < 5 seconds
- Search extraction: < 3 seconds
- Validation processing: < 500ms
- Caching operations: < 100ms

### Memory Usage

- Extraction operations: < 50MB
- Caching storage: < 100MB
- Concurrent processing: < 200MB

### Throughput

- Concurrent extractions: 10+ articles
- Cache hit rate: > 80%
- Success rate: > 95%

## Configuration

### Environment Variables

```bash
# Extraction configuration
WIKIPEDIA_EXTRACTOR_CACHE_ENABLED=true
WIKIPEDIA_EXTRACTOR_CACHE_SIZE=1000
WIKIPEDIA_EXTRACTOR_CACHE_TTL=3600

# Performance configuration
WIKIPEDIA_EXTRACTOR_TIMEOUT_MS=5000
WIKIPEDIA_EXTRACTOR_MAX_CONCURRENT=10

# Validation configuration
WIKIPEDIA_EXTRACTOR_VALIDATION_ENABLED=true
WIKIPEDIA_EXTRACTOR_DEBUG_LOGGING=false
```

### Configuration File

```yaml
# wikipedia_extractor_config.yaml
extraction:
  cache_enabled: true
  cache_size: 1000
  cache_ttl: 3600
  timeout_ms: 5000

validation:
  enabled: true
  strict_mode: false
  quality_threshold: 0.8

performance:
  max_concurrent: 10
  enable_monitoring: true
  log_performance_metrics: true

logging:
  level: INFO
  enable_debug: false
  log_extraction_details: false
```

## Testing

### Unit Tests

```python
@pytest.mark.asyncio
async def test_article_extraction():
    """Test article extraction functionality."""
    scraper = EnhancedWikipediaScraper(mock_page, mock_selector_engine)
    
    result = await scraper.scrape_with_extraction(
        article_title="Test Article"
    )
    
    assert result['success'] is True
    assert 'title' in result['data']
    assert result['metadata']['extraction_time_ms'] < 5000
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end_extraction():
    """Test complete extraction pipeline."""
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        result = await scraper.scrape_with_extraction(
            article_title="Python (programming language)"
        )
        
        assert result['success'] is True
        assert result['metadata']['data_quality_score'] > 0.8
```

### Performance Tests

```python
@pytest.mark.asyncio
async def test_extraction_performance():
    """Test extraction performance requirements."""
    start_time = time.time()
    
    result = await scraper.scrape_with_extraction(
        article_title="Performance Test Article"
    )
    
    extraction_time = (time.time() - start_time) * 1000
    assert extraction_time < 5000  # 5 second limit
```

## Monitoring

### Metrics

```python
EXTRACTION_METRICS = {
    "extraction_count": Counter,
    "extraction_duration": Histogram,
    "extraction_success_rate": Gauge,
    "data_quality_score": Histogram,
    "cache_hit_rate": Gauge,
    "error_count": Counter
}
```

### Health Checks

```python
async def health_check():
    """Health check for extraction service."""
    try:
        # Test basic extraction
        result = await scraper.scrape_with_extraction(
            article_title="Main Page"
        )
        
        return {
            "status": "healthy",
            "extraction_working": result['success'],
            "cache_status": scraper.get_cache_status(),
            "performance_metrics": scraper.get_performance_metrics()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Version Compatibility

### API Versioning

- Current version: v1.0.0
- Backward compatibility: Maintained for minor versions
- Breaking changes: Major version increments only

### Migration Guide

```python
# v0.x (basic scraper)
scraper = WikipediaScraper(page, selector_engine)
result = await scraper.scrape(article_title="Python")

# v1.0 (enhanced scraper)
scraper = EnhancedWikipediaScraper(page, selector_engine)
result = await scraper.scrape_with_extraction(article_title="Python")
```

## Security Considerations

### Input Validation

- Sanitize all user inputs
- Validate article titles and queries
- Limit extraction request sizes
- Prevent injection attacks

### Rate Limiting

- Implement request rate limiting
- Limit concurrent extractions per user
- Monitor for abuse patterns
- Implement caching to reduce load

### Data Privacy

- No personal data collection
- Respect Wikipedia's terms of service
- Implement appropriate data retention policies
- Secure storage of extraction results
