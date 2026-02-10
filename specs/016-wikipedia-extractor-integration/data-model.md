# Wikipedia Extractor Integration Data Model

## Overview

This document defines the data model for the Wikipedia extractor integration, including entities, relationships, validation rules, and state transitions.

## Core Entities

### WikipediaExtractionConfig

Configuration for Wikipedia-specific extraction rules and settings.

```python
@dataclass
class WikipediaExtractionConfig:
    """Configuration for Wikipedia-specific extraction rules."""
    
    # Extraction rule sets
    article_rules: Dict[str, ExtractionRule]
    infobox_rules: Dict[str, ExtractionRule]
    search_rules: Dict[str, ExtractionRule]
    toc_rules: Dict[str, ExtractionRule]
    link_rules: Dict[str, ExtractionRule]
    
    # Configuration options
    validation_enabled: bool = True
    strict_mode: bool = False
    quality_threshold: float = 0.8
    cache_enabled: bool = True
    cache_size: int = 1000
    cache_ttl: int = 3600
    
    # Performance settings
    timeout_ms: int = 5000
    max_concurrent: int = 10
    enable_monitoring: bool = True
    
    # Error handling
    default_values: Dict[str, Any] = field(default_factory=dict)
    error_handling_mode: str = "graceful"  # "graceful", "strict"
    log_level: str = "INFO"
```

**Validation Rules**:
- `article_rules`: Must contain at least title rule
- `validation_enabled`: Must be boolean
- `quality_threshold`: Must be between 0.0 and 1.0
- `timeout_ms`: Must be positive integer
- `max_concurrent`: Must be positive integer

**State Transitions**:
- `active` → `disabled`: When validation fails
- `disabled` → `active`: When issues resolved

### EnhancedWikipediaScraper

Enhanced Wikipedia scraper with extractor module integration.

```python
class EnhancedWikipediaScraper(WikipediaScraper):
    """Enhanced Wikipedia scraper with extractor module integration."""
    
    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.extractor = Extractor()
        self.extraction_config = WikipediaExtractionConfig()
        self.validator = WikipediaDataValidator()
        self.cache = ExtractionCache()
        self.statistics = ExtractionStatistics()
    
    async def scrape_with_extraction(self, **kwargs) -> Dict[str, Any]:
        """Enhanced scraping with advanced extraction."""
        pass
    
    def set_extraction_rules(self, rules: Dict[str, ExtractionRule]) -> None:
        """Set custom extraction rules."""
        pass
    
    def set_validator(self, validator: WikipediaDataValidator) -> None:
        """Set data validator."""
        pass
    
    def set_default_values(self, defaults: Dict[str, Any]) -> None:
        """Set default values for missing data."""
        pass
```

**Validation Rules**:
- `extractor`: Must be properly initialized
- `extraction_config`: Must pass validation
- `page`: Must be valid Playwright page
- `selector_engine`: Must be compatible

**State Transitions**:
- `initializing` → `ready`: When setup completes
- `ready` → `extracting`: During extraction
- `extracting` → `ready`: After extraction completes
- `ready` → `error`: When extraction fails

### WikipediaDataValidator

Wikipedia-specific data validation and quality assessment.

```python
class WikipediaDataValidator:
    """Wikipedia-specific data validation and quality assessment."""
    
    def __init__(self):
        self.validation_rules = DEFAULT_VALIDATION_RULES
        self.quality_thresholds = DEFAULT_QUALITY_THRESHOLDS
    
    def validate_article_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate article data structure and content."""
        pass
    
    def validate_infobox_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate infobox data types and formats."""
        pass
    
    def validate_search_results(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """Validate search results data."""
        pass
    
    def assess_data_quality(self, data: Dict[str, Any]) -> QualityMetrics:
        """Assess overall data quality."""
        pass
    
    def set_validation_rules(self, rules: Dict[str, Dict[str, Any]]) -> None:
        """Set custom validation rules."""
        pass
```

**Validation Rules**:
- `validation_rules`: Must contain required field validations
- `quality_thresholds`: Must be between 0.0 and 1.0

**State Transitions**:
- `ready` → `validating`: During validation
- `validating` → `ready`: After validation completes

## Data Structures

### ArticleExtractionResult

Structured result for article extraction.

```python
@dataclass
class ArticleExtractionResult:
    """Structured result for article extraction."""
    
    # Core article data
    title: str
    publication_date: Optional[datetime]
    word_count: Optional[int]
    categories: List[str]
    
    # Enhanced content
    infobox: Dict[str, Any]
    table_of_contents: List[Dict[str, Any]]
    links: Dict[str, List[Dict[str, Any]]]
    content: str
    
    # Metadata
    url: str
    scraped_at: datetime
    extraction_metadata: Dict[str, Any]
    
    # Quality metrics
    quality_score: float
    validation_results: ValidationResult
    performance_metrics: Dict[str, Any]
```

**Validation Rules**:
- `title`: Required, max 255 characters, alphanumeric with spaces
- `publication_date`: Optional, valid date if present
- `word_count`: Optional, positive integer if present
- `categories`: List of strings, max 100 items
- `quality_score`: Float between 0.0 and 1.0

**Relationships**:
- `infobox`: One-to-one with InfoboxData
- `table_of_contents`: One-to-many with TOCSection
- `links`: One-to-many with LinkData

### SearchExtractionResult

Structured result for search extraction.

```python
@dataclass
class SearchExtractionResult:
    """Structured result for search extraction."""
    
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    
    # Enhanced search data
    search_metadata: Dict[str, Any]
    quality_metrics: QualityMetrics
    
    # Performance data
    scraped_at: datetime
    performance_metrics: Dict[str, Any]
```

**Validation Rules**:
- `query`: Required, max 500 characters
- `results`: List, max 100 items
- `total_count`: Integer, non-negative

### InfoboxData

Structured infobox data with type conversion.

```python
@dataclass
class InfoboxData:
    """Structured infobox data with type conversion."""
    
    # Basic info
    title: Optional[str]
    image: Optional[str]
    caption: Optional[str]
    
    # Numeric data
    population: Optional[int]
    area: Optional[float]
    elevation: Optional[int]
    
    # Date data
    established: Optional[date]
    founded: Optional[date]
    independence: Optional[date]
    
    # Geographic data
    coordinates: Optional[Dict[str, float]]
    location: Optional[str]
    
    # Metadata
    data_source: str
    extraction_confidence: float
    validation_status: str
```

**Validation Rules**:
- Numeric fields: Positive integers/floats if present
- Date fields: Valid dates if present
- Coordinates: Valid lat/long if present
- `extraction_confidence`: Float between 0.0 and 1.0

### TOCSection

Table of contents section with hierarchy.

```python
@dataclass
class TOCSection:
    """Table of contents section with hierarchy."""
    
    title: str
    depth: int
    anchor: str
    level: int
    
    # Hierarchical data
    parent_section: Optional[str]
    subsections: List['TOCSection']
    
    # Metadata
    section_number: Optional[str]
    word_count: Optional[int]
    
    # Quality metrics
    extraction_confidence: float
    validation_status: str
```

**Validation Rules**:
- `title`: Required, max 200 characters
- `depth`: Integer between 1 and 10
- `level`: Integer between 1 and 6
- `extraction_confidence`: Float between 0.0 and 1.0

**Relationships**:
- `parent_section`: Self-reference to parent section
- `subsections`: One-to-many with TOCSection

### LinkData

Structured link data with categorization.

```python
@dataclass
class LinkData:
    """Structured link data with categorization."""
    
    url: str
    title: str
    link_type: str  # "internal", "external", "reference", "image"
    
    # Link metadata
    anchor_text: str
    target_section: Optional[str]
    relevance_score: Optional[float]
    
    # Validation data
    is_valid: bool
    validation_errors: List[str]
    
    # Quality metrics
    extraction_confidence: float
    last_verified: Optional[datetime]
```

**Validation Rules**:
- `url`: Required, valid URL format
- `title`: Required, max 200 characters
- `link_type`: Must be one of allowed types
- `relevance_score`: Float between 0.0 and 1.0 if present

## Validation Rules

### Article Validation Rules

```python
ARTICLE_VALIDATION_RULES = {
    "title": {
        "required": True,
        "type": "string",
        "min_length": 1,
        "max_length": 255,
        "pattern": r"^[A-Za-z0-9\s\-_()]+$"
    },
    "publication_date": {
        "required": False,
        "type": "date",
        "min_date": "2000-01-01",
        "max_date": "today"
    },
    "word_count": {
        "required": False,
        "type": "integer",
        "min_value": 0,
        "max_value": 1000000
    },
    "categories": {
        "required": False,
        "type": "list",
        "min_length": 0,
        "max_length": 100,
        "item_pattern": r"^[A-Za-z0-9\s\-_]+$"
    }
}
```

### Infobox Validation Rules

```python
INFOBOX_VALIDATION_RULES = {
    "population": {
        "required": False,
        "type": "integer",
        "min_value": 0,
        "max_value": 10000000000
    },
    "area": {
        "required": False,
        "type": "float",
        "min_value": 0.0,
        "max_value": 100000000.0
    },
    "coordinates": {
        "required": False,
        "type": "coordinates",
        "lat_range": [-90, 90],
        "lon_range": [-180, 180]
    }
}
```

### Search Results Validation Rules

```python
SEARCH_VALIDATION_RULES = {
    "title": {
        "required": True,
        "type": "string",
        "min_length": 1,
        "max_length": 255
    },
    "relevance_score": {
        "required": False,
        "type": "float",
        "min_value": 0.0,
        "max_value": 1.0
    },
    "article_size": {
        "required": False,
        "type": "integer",
        "min_value": 0,
        "max_value": 1000000
    }
}
```

## Quality Metrics

### QualityMetrics

```python
@dataclass
class QualityMetrics:
    """Data quality assessment metrics."""
    
    score: float  # 0.0 to 1.0
    completeness: float  # Percentage of expected data present
    accuracy: float  # Estimated accuracy based on validation
    consistency: float  # Consistency across similar data
    
    # Quality issues
    issues: List[str]  # Quality issues found
    warnings: List[str]  # Quality warnings
    recommendations: List[str]  # Improvement recommendations
    
    # Assessment metadata
    assessed_at: datetime
    assessment_version: str
    confidence_level: float
```

**Validation Rules**:
- `score`: Float between 0.0 and 1.0
- `completeness`: Float between 0.0 and 1.0
- `accuracy`: Float between 0.0 and 1.0
- `consistency`: Float between 0.0 and 1.0

### ValidationResult

```python
@dataclass
class ValidationResult:
    """Result of data validation."""
    
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    score: float  # Validation score 0.0 to 1.0
    
    # Validation metadata
    validated_at: datetime
    validation_rules: Dict[str, Any]
    performance_metrics: Dict[str, Any]
```

**Validation Rules**:
- `score`: Float between 0.0 and 1.0
- `errors`: List of ValidationError objects
- `warnings`: List of ValidationWarning objects

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

### Error Recovery

```python
@dataclass
class ErrorRecoveryResult:
    """Result of error recovery attempt."""
    
    success: bool
    recovery_method: str
    original_error: Exception
    recovered_data: Optional[Dict[str, Any]]
    recovery_time_ms: float
    quality_impact: float
```

## State Management

### Extraction States

```python
class ExtractionState(Enum):
    """Extraction process states."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    CACHING = "caching"
    COMPLETED = "completed"
    ERROR = "error"
    RECOVERING = "recovering"
```

### State Transitions

```python
EXTRACTION_STATE_TRANSITIONS = {
    ExtractionState.IDLE: [ExtractionState.INITIALIZING],
    ExtractionState.INITIALIZING: [ExtractionState.EXTRACTING, ExtractionState.ERROR],
    ExtractionState.EXTRACTING: [ExtractionState.VALIDATING, ExtractionState.ERROR],
    ExtractionState.VALIDATING: [ExtractionState.CACHING, ExtractionState.ERROR],
    ExtractionState.CACHING: [ExtractionState.COMPLETED, ExtractionState.ERROR],
    ExtractionState.COMPLETED: [ExtractionState.IDLE],
    ExtractionState.ERROR: [ExtractionState.RECOVERING, ExtractionState.IDLE],
    ExtractionState.RECOVERING: [ExtractionState.EXTRACTING, ExtractionState.ERROR]
}
```

## Performance Models

### Extraction Performance

```python
@dataclass
class ExtractionPerformance:
    """Extraction performance metrics."""
    
    extraction_time_ms: float
    validation_time_ms: float
    caching_time_ms: float
    total_time_ms: float
    
    memory_usage_mb: float
    cache_hit_rate: float
    success_rate: float
    
    # Performance breakdown
    text_extraction_time: float
    type_conversion_time: float
    validation_processing_time: float
    error_handling_time: float
```

### Resource Usage

```python
@dataclass
class ResourceUsage:
    """Resource usage metrics."""
    
    cpu_usage_percent: float
    memory_usage_mb: float
    network_requests: int
    disk_io_mb: float
    
    # Resource limits
    cpu_limit_percent: float
    memory_limit_mb: float
    network_limit_requests: int
    disk_io_limit_mb: float
```

## Configuration Models

### Cache Configuration

```python
@dataclass
class CacheConfiguration:
    """Cache configuration settings."""
    
    enabled: bool
    size_limit: int
    ttl_seconds: int
    eviction_policy: str  # "lru", "lfu", "fifo"
    
    # Cache statistics
    hit_count: int
    miss_count: int
    eviction_count: int
    
    # Performance metrics
    avg_access_time_ms: float
    memory_usage_mb: float
```

### Monitoring Configuration

```python
@dataclass
class MonitoringConfiguration:
    """Monitoring configuration settings."""
    
    enabled: bool
    metrics_collection_interval: int
    performance_thresholds: Dict[str, float]
    alert_thresholds: Dict[str, float]
    
    # Monitoring data
    extraction_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    error_metrics: Dict[str, Any]
```

## Data Relationships

### Entity Relationship Diagram

```
EnhancedWikipediaScraper
├── WikipediaExtractionConfig
├── WikipediaDataValidator
├── ExtractionCache
└── ExtractionStatistics

ArticleExtractionResult
├── InfoboxData
├── TOCSection (one-to-many)
└── LinkData (one-to-many)

SearchExtractionResult
└── SearchResult (one-to-many)

QualityMetrics
├── ValidationResult
└── ErrorRecoveryResult
```

### Data Flow

```
Page Content → Extractor Module → Type Conversion → Validation → Quality Assessment → Structured Result
```

## Conclusion

This data model provides a comprehensive foundation for the Wikipedia extractor integration. The entities are designed to be modular, extensible, and maintainable while supporting the required functionality for enhanced data extraction with type conversion and validation.

The model follows the Scorewise Scraper Constitution principles:
- **Deep Modularity**: Each entity has a single responsibility
- **Production Resilience**: Comprehensive error handling and recovery
- **Observability**: Detailed metrics and monitoring support
- **Selector-First Engineering**: Integration with existing selector system
- **Stealth-Aware Design**: No impact on browser stealth capabilities
