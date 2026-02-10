"""
Wikipedia extraction data models.

This module contains data structures for extraction results, quality metrics,
and validation results specific to Wikipedia content extraction.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


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
    validation_results: Dict[str, Any]
    performance_metrics: Dict[str, Any]


@dataclass
class SearchExtractionResult:
    """Structured result for search extraction."""
    
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    
    # Enhanced search data
    search_metadata: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    
    # Performance data
    scraped_at: datetime
    performance_metrics: Dict[str, Any]


@dataclass
class InfoboxData:
    """Structured infobox data with type conversion."""
    
    # Basic info
    title: Optional[str] = None
    image: Optional[str] = None
    caption: Optional[str] = None
    
    # Numeric data
    population: Optional[int] = None
    area: Optional[float] = None
    elevation: Optional[int] = None
    
    # Date data
    established: Optional[datetime] = None
    founded: Optional[datetime] = None
    independence: Optional[datetime] = None
    
    # Geographic data
    coordinates: Optional[Dict[str, float]] = None
    location: Optional[str] = None
    
    # Metadata
    data_source: str = "wikipedia"
    extraction_confidence: float = 0.0
    validation_status: str = "pending"


@dataclass
class TOCSection:
    """Table of contents section with hierarchy."""
    
    title: str
    depth: int
    anchor: str
    level: int
    
    # Hierarchical data
    parent_section: Optional[str] = None
    subsections: List['TOCSection'] = field(default_factory=list)
    
    # Metadata
    section_number: Optional[str] = None
    word_count: Optional[int] = None
    
    # Quality metrics
    extraction_confidence: float = 0.0
    validation_status: str = "pending"


@dataclass
class LinkData:
    """Structured link data with categorization."""
    
    url: str
    title: str
    link_type: str  # "internal", "external", "reference", "image"
    
    # Link metadata
    anchor_text: str
    target_section: Optional[str] = None
    relevance_score: Optional[float] = None
    
    # Validation data
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # Quality metrics
    extraction_confidence: float = 0.0
    last_verified: Optional[datetime] = None


@dataclass
class QualityMetrics:
    """Data quality assessment metrics."""
    
    score: float  # 0.0 to 1.0
    completeness: float  # Percentage of expected data present
    accuracy: float  # Estimated accuracy based on validation
    consistency: float  # Consistency across similar data
    
    # Quality issues
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Assessment metadata
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    assessment_version: str = "1.0"
    confidence_level: float = 0.0


@dataclass
class ValidationResult:
    """Result of data validation."""
    
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0  # Validation score 0.0 to 1.0
    
    # Validation metadata
    validated_at: datetime = field(default_factory=datetime.utcnow)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


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
    text_extraction_time: float = 0.0
    type_conversion_time: float = 0.0
    validation_processing_time: float = 0.0
    error_handling_time: float = 0.0


@dataclass
class ExtractionStatistics:
    """Extraction statistics tracking."""
    
    total_extractions: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    average_extraction_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Type-specific statistics
    article_extractions: int = 0
    search_extractions: int = 0
    infobox_extractions: int = 0
    toc_extractions: int = 0
    link_extractions: int = 0
    
    # Performance statistics
    performance_metrics: List[ExtractionPerformance] = field(default_factory=list)
    
    def update_statistics(self, success: bool, extraction_time_ms: float, extraction_type: str) -> None:
        """Update statistics with new extraction result."""
        self.total_extractions += 1
        
        if success:
            self.successful_extractions += 1
        else:
            self.failed_extractions += 1
        
        # Update average time
        if self.total_extractions == 1:
            self.average_extraction_time_ms = extraction_time_ms
        else:
            self.average_extraction_time_ms = (
                (self.average_extraction_time_ms * (self.total_extractions - 1) + extraction_time_ms) / 
                self.total_extractions
            )
        
        # Update type-specific statistics
        if extraction_type == "article":
            self.article_extractions += 1
        elif extraction_type == "search":
            self.search_extractions += 1
        elif extraction_type == "infobox":
            self.infobox_extractions += 1
        elif extraction_type == "toc":
            self.toc_extractions += 1
        elif extraction_type == "links":
            self.link_extractions += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_extractions == 0:
            return 0.0
        return (self.successful_extractions / self.total_extractions) * 100
