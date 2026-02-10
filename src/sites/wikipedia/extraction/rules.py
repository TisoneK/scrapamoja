"""
Wikipedia extraction rules.

This module provides extraction rules specifically designed for Wikipedia content,
including article metadata, infobox data, search results, table of contents, and links.
"""

from typing import Dict, Any, List
from src.extractor import ExtractionRule, ExtractionType, DataType, TransformationType


class WikipediaExtractionRules:
    """Wikipedia-specific extraction rules factory."""
    
    def __init__(self):
        """Initialize with default rule sets."""
        self.article_rules = self._get_article_rules()
        self.infobox_rules = self._get_infobox_rules()
        self.search_rules = self._get_search_rules()
        self.toc_rules = self._get_toc_rules()
        self.link_rules = self._get_link_rules()
    
    def get_article_rules(self) -> Dict[str, ExtractionRule]:
        """Get article extraction rules."""
        return self.article_rules
    
    def get_infobox_rules(self) -> Dict[str, ExtractionRule]:
        """Get infobox extraction rules."""
        return self.infobox_rules
    
    def get_search_rules(self) -> Dict[str, ExtractionRule]:
        """Get search result extraction rules."""
        return self.search_rules
    
    def get_toc_rules(self) -> Dict[str, ExtractionRule]:
        """Get table of contents extraction rules."""
        return self.toc_rules
    
    def get_link_rules(self) -> Dict[str, ExtractionRule]:
        """Get link extraction rules."""
        return self.link_rules
    
    def get_all_rules(self) -> Dict[str, Dict[str, ExtractionRule]]:
        """Get all extraction rules organized by type."""
        return {
            "article": self.article_rules,
            "infobox": self.infobox_rules,
            "search": self.search_rules,
            "toc": self.toc_rules,
            "links": self.link_rules
        }
    
    def _get_article_rules(self) -> Dict[str, ExtractionRule]:
        """Create article extraction rules."""
        return {
            "title": ExtractionRule(
                name="article_title",
                field_path="title",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=True,
                selector="h1#firstHeading"  # Wikipedia article title selector
            ),
            "publication_date": ExtractionRule(
                name="publication_date",
                field_path="publication_date",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DATE,
                regex_pattern=r"(\d{1,2}\s+\w+\s+\d{4})",
                transformations=[TransformationType.TRIM],
                required=False,
                selector="#mw-content-text .infobox .published"  # Example selector for publication date
            ),
            "word_count": ExtractionRule(
                name="word_count",
                field_path="word_count",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                regex_pattern=r"(\d+)\s+words?",
                transformations=[TransformationType.TRIM],
                required=False,
                selector="#mw-content-text"  # Will extract from content
            ),
            "categories": ExtractionRule(
                name="categories",
                field_path="categories",
                extraction_type=ExtractionType.LIST,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector="#mw-normal-catlinks a"  # Wikipedia categories selector
            ),
            "last_modified": ExtractionRule(
                name="last_modified",
                field_path="last_modified",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DATETIME,
                transformations=[TransformationType.TRIM],
                required=False,
                selector="#footer-info-lastmod"  # Wikipedia last modified selector
            ),
            "page_size": ExtractionRule(
                name="page_size",
                field_path="page_size",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                regex_pattern=r"(\d+)\s+bytes?",
                transformations=[TransformationType.TRIM],
                required=False,
                selector="#mw-content-text"  # Will calculate from content
            ),
            "url": ExtractionRule(
                name="url",
                field_path="url",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="href",
                target_type=DataType.TEXT,
                required=True,
                selector="link[rel='canonical']"  # Canonical URL
            ),
            "content": ExtractionRule(
                name="content",
                field_path="content",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=True,
                selector="#mw-content-text"  # Main content area
            )
        }
    
    def _get_infobox_rules(self) -> Dict[str, ExtractionRule]:
        """Create infobox extraction rules."""
        return {
            "title": ExtractionRule(
                name="infobox_title",
                field_path="infobox.title",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".infobox caption, .infobox .infobox-title"  # Infobox title/caption
            ),
            "image": ExtractionRule(
                name="infobox_image",
                field_path="infobox.image",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="src",
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".infobox img"  # Infobox image
            ),
            "caption": ExtractionRule(
                name="infobox_caption",
                field_path="infobox.caption",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".infobox .infobox-caption"  # Image caption
            ),
            "population": ExtractionRule(
                name="population",
                field_path="infobox.population",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                regex_pattern=r"([\d,]+)",
                transformations=[TransformationType.TRIM, TransformationType.REMOVE_WHITESPACE],
                required=False,
                selector=".infobox tr:contains('Population') td"  # Population field
            ),
            "area": ExtractionRule(
                name="area",
                field_path="infobox.area",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.FLOAT,
                regex_pattern=r"([\d,.,]+)\s*(?:km|sq\s*mi|mi²)",
                transformations=[TransformationType.TRIM, TransformationType.REMOVE_WHITESPACE],
                required=False,
                selector=".infobox tr:contains('Area') td"  # Area field
            ),
            "elevation": ExtractionRule(
                name="elevation",
                field_path="infobox.elevation",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                regex_pattern=r"([\d,]+)\s*m",
                transformations=[TransformationType.TRIM, TransformationType.REMOVE_WHITESPACE],
                required=False,
                selector=".infobox tr:contains('Elevation') td"  # Elevation field
            ),
            "established": ExtractionRule(
                name="established",
                field_path="infobox.established",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DATE,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".infobox tr:contains('Established') td, .infobox tr:contains('Founded') td"  # Establishment date
            ),
            "founded": ExtractionRule(
                name="founded",
                field_path="infobox.founded",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DATE,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".infobox tr:contains('Founded') td, .infobox tr:contains('Settled') td"  # Founded date
            ),
            "independence": ExtractionRule(
                name="independence",
                field_path="infobox.independence",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DATE,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".infobox tr:contains('Independence') td"  # Independence date
            ),
            "coordinates": ExtractionRule(
                name="coordinates",
                field_path="infobox.coordinates",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DICT,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".infobox .geo-default, .infobox .coordinates"  # Geographic coordinates
            ),
            "location": ExtractionRule(
                name="location",
                field_path="infobox.location",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".infobox tr:contains('Location') td, .infobox tr:contains('Country') td"  # Location
            ),
            "government_type": ExtractionRule(
                name="government_type",
                field_path="infobox.government_type",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".infobox tr:contains('Government') td"  # Government type
            ),
            "leader_title": ExtractionRule(
                name="leader_title",
                field_path="infobox.leader_title",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".infobox tr:contains('Leader') td"  # Leader title
            ),
            "population_density": ExtractionRule(
                name="population_density",
                field_path="infobox.population_density",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.FLOAT,
                regex_pattern=r"([\d,.,]+)\s*/\s*(?:km|sq\s*mi)",
                transformations=[TransformationType.TRIM, TransformationType.REMOVE_WHITESPACE],
                required=False,
                selector=".infobox tr:contains('Population density') td"  # Population density
            ),
            "timezone": ExtractionRule(
                name="timezone",
                field_path="infobox.timezone",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".infobox tr:contains('Timezone') td"  # Timezone
            ),
            "website": ExtractionRule(
                name="website",
                field_path="infobox.website",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="href",
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".infobox tr:contains('Website') a"  # Official website
            )
        }
    
    def _get_search_rules(self) -> Dict[str, ExtractionRule]:
        """Create search result extraction rules."""
        return {
            "title": ExtractionRule(
                name="search_title",
                field_path="title",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=True,
                selector=".mw-search-result-heading a"  # Wikipedia search result title selector
            ),
            "relevance_score": ExtractionRule(
                name="relevance_score",
                field_path="relevance_score",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.FLOAT,
                regex_pattern=r"(\d+\.\d+)",
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".mw-search-result-data"  # Search result metadata
            ),
            "article_size": ExtractionRule(
                name="article_size",
                field_path="article_size",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                regex_pattern=r"(\d+)\s*(?:bytes|words|KB)",
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".mw-search-result-data"  # Size information in search results
            ),
            "last_modified": ExtractionRule(
                name="last_modified",
                field_path="last_modified",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.DATETIME,
                transformations=[TransformationType.TRIM],
                required=False,
                selector=".mw-search-result-data .mw-search-datetime"  # Last modified info
            ),
            "description": ExtractionRule(
                name="description",
                field_path="description",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".searchresult"  # Search result description/snippet
            ),
            "url": ExtractionRule(
                name="url",
                field_path="url",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="href",
                target_type=DataType.TEXT,
                required=True,
                selector=".mw-search-result-heading a"  # URL from search result link
            ),
            "pageid": ExtractionRule(
                name="pageid",
                field_path="pageid",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="data-pageid",
                target_type=DataType.INTEGER,
                required=False,
                selector=".mw-search-result"  # Wikipedia page ID
            ),
            "snippet": ExtractionRule(
                name="snippet",
                field_path="snippet",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".mw-search-result .searchresult"  # Search result snippet
            ),
            "category": ExtractionRule(
                name="category",
                field_path="category",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=False,
                selector=".mw-search-result .mw-search-result-description"  # Category information
            )
        }
    
    def _get_toc_rules(self) -> Dict[str, ExtractionRule]:
        """Create table of contents extraction rules."""
        return {
            "title": ExtractionRule(
                name="toc_title",
                field_path="title",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=True,
                selector="#toc a"  # Wikipedia TOC links
            ),
            "depth": ExtractionRule(
                name="toc_depth",
                field_path="depth",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                transformations=[TransformationType.TRIM],
                required=True,
                selector="#toc .toclevel-1, #toc .toclevel-2, #toc .toclevel-3"  # TOC levels
            ),
            "anchor": ExtractionRule(
                name="toc_anchor",
                field_path="anchor",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="href",
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=True,
                selector="#toc a"  # TOC anchor links
            ),
            "level": ExtractionRule(
                name="toc_level",
                field_path="level",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                transformations=[TransformationType.TRIM],
                required=True,
                selector="#toc .toclevel-1, #toc .toclevel-2, #toc .toclevel-3"  # TOC levels
            ),
            "section_number": ExtractionRule(
                name="section_number",
                field_path="section_number",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=False,
                selector="#toc .tocnumber"  # Section numbers
            ),
            "parent_section": ExtractionRule(
                name="parent_section",
                field_path="parent_section",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=False,
                # Will be calculated based on hierarchy
            ),
            "subsections": ExtractionRule(
                name="subsections",
                field_path="subsections",
                extraction_type=ExtractionType.LIST,
                target_type=DataType.DICT,
                required=False,
                # Will be calculated based on hierarchy
            ),
            "word_count": ExtractionRule(
                name="toc_word_count",
                field_path="word_count",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.INTEGER,
                transformations=[TransformationType.TRIM],
                required=False,
                # Will be calculated from section content
            )
        }
    
    def _get_link_rules(self) -> Dict[str, ExtractionRule]:
        """Create link extraction rules."""
        return {
            "url": ExtractionRule(
                name="link_url",
                field_path="url",
                extraction_type=ExtractionType.ATTRIBUTE,
                attribute_name="href",
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=True,
                selector="#mw-content-text a"  # All links in content
            ),
            "title": ExtractionRule(
                name="link_title",
                field_path="title",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM, TransformationType.CLEAN],
                required=True,
                selector="#mw-content-text a"  # Link text
            ),
            "link_type": ExtractionRule(
                name="link_type",
                field_path="link_type",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=True,
                # Will be determined by URL analysis
            ),
            "anchor_text": ExtractionRule(
                name="anchor_text",
                field_path="anchor_text",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=False,
                selector="#mw-content-text a"  # Link anchor text
            ),
            "target_section": ExtractionRule(
                name="target_section",
                field_path="target_section",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.TEXT,
                transformations=[TransformationType.TRIM],
                required=False,
                # Will be extracted from anchor href
            ),
            "relevance_score": ExtractionRule(
                name="link_relevance",
                field_path="relevance_score",
                extraction_type=ExtractionType.TEXT,
                target_type=DataType.FLOAT,
                transformations=[TransformationType.TRIM],
                required=False,
                # Will be calculated based on context
            )
        }
    
    def add_custom_rule(self, rule_type: str, name: str, rule: ExtractionRule) -> None:
        """Add a custom extraction rule."""
        if rule_type == "article":
            self.article_rules[name] = rule
        elif rule_type == "infobox":
            self.infobox_rules[name] = rule
        elif rule_type == "search":
            self.search_rules[name] = rule
        elif rule_type == "toc":
            self.toc_rules[name] = rule
        elif rule_type == "links":
            self.link_rules[name] = rule
        else:
            raise ValueError(f"Unknown rule type: {rule_type}")
    
    def remove_rule(self, rule_type: str, name: str) -> None:
        """Remove an extraction rule."""
        if rule_type == "article" and name in self.article_rules:
            del self.article_rules[name]
        elif rule_type == "infobox" and name in self.infobox_rules:
            del self.infobox_rules[name]
        elif rule_type == "search" and name in self.search_rules:
            del self.search_rules[name]
        elif rule_type == "toc" and name in self.toc_rules:
            del self.toc_rules[name]
        elif rule_type == "links" and name in self.link_rules:
            del self.link_rules[name]
        else:
            raise ValueError(f"Unknown rule type or rule not found: {rule_type}/{name}")
    
    def validate_rules(self) -> bool:
        """Validate all extraction rules."""
        all_rules = []
        all_rules.extend(self.article_rules.values())
        all_rules.extend(self.infobox_rules.values())
        all_rules.extend(self.search_rules.values())
        all_rules.extend(self.toc_rules.values())
        all_rules.extend(self.link_rules.values())
        
        # Basic validation
        for rule in all_rules:
            if not rule.name or not rule.field_path:
                return False
        
        return True
