"""
Wikipedia extraction configuration.

This module provides configuration management for Wikipedia-specific extraction rules,
validation settings, and performance optimization parameters.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from src.extractor import ExtractionRule


@dataclass
class WikipediaExtractionConfig:
    """Configuration for Wikipedia-specific extraction rules and settings."""
    
    # Extraction rule sets
    article_rules: Dict[str, ExtractionRule] = field(default_factory=dict)
    infobox_rules: Dict[str, ExtractionRule] = field(default_factory=dict)
    search_rules: Dict[str, ExtractionRule] = field(default_factory=dict)
    toc_rules: Dict[str, ExtractionRule] = field(default_factory=dict)
    link_rules: Dict[str, ExtractionRule] = field(default_factory=dict)
    
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
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.quality_threshold < 0.0 or self.quality_threshold > 1.0:
            raise ValueError("quality_threshold must be between 0.0 and 1.0")
        
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        
        if self.max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        
        if self.error_handling_mode not in ["graceful", "strict"]:
            raise ValueError("error_handling_mode must be 'graceful' or 'strict'")
    
    def add_article_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add article extraction rule."""
        self.article_rules[name] = rule
    
    def add_infobox_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add infobox extraction rule."""
        self.infobox_rules[name] = rule
    
    def add_search_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add search result extraction rule."""
        self.search_rules[name] = rule
    
    def add_toc_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add table of contents extraction rule."""
        self.toc_rules[name] = rule
    
    def add_link_rule(self, name: str, rule: ExtractionRule) -> None:
        """Add link extraction rule."""
        self.link_rules[name] = rule
    
    def get_rules_by_type(self, extraction_type: str) -> Dict[str, ExtractionRule]:
        """Get rules by extraction type."""
        rule_mapping = {
            "article": self.article_rules,
            "infobox": self.infobox_rules,
            "search": self.search_rules,
            "toc": self.toc_rules,
            "links": self.link_rules
        }
        return rule_mapping.get(extraction_type, {})
    
    def get_default_values(self) -> Dict[str, Any]:
        """Get default values for missing data."""
        return {
            "title": "",
            "publication_date": None,
            "word_count": 0,
            "categories": [],
            "infobox": {},
            "table_of_contents": [],
            "links": {"internal": [], "external": [], "references": [], "images": []},
            "last_modified": None,
            "page_size": 0,
            **self.default_values
        }
    
    def validate_rules(self) -> bool:
        """Validate all extraction rules."""
        all_rules = []
        all_rules.extend(self.article_rules.values())
        all_rules.extend(self.infobox_rules.values())
        all_rules.extend(self.search_rules.values())
        all_rules.extend(self.toc_rules.values())
        all_rules.extend(self.link_rules.values())
        
        # Basic validation - ensure all rules have required fields
        for rule in all_rules:
            if not rule.name or not rule.field_path:
                return False
        
        return True


# Default configuration instance
DEFAULT_CONFIG = WikipediaExtractionConfig()
