"""
Shared text extraction processor for reusable text processing across sites.

This module provides comprehensive text extraction functionality that can be easily
integrated into any site scraper for extracting and processing text content.
"""

from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import json
import re
from urllib.parse import urlparse

from src.sites.base.component_interface import BaseProcessor, ProcessorContext, ProcessorResult


class TextExtractionProcessor(BaseProcessor):
    """Shared text extraction processor for cross-site usage."""
    
    def __init__(
        self,
        processor_id: str = "shared_text_extractor",
        name: str = "Shared Text Extraction Processor",
        version: str = "1.0.0",
        description: str = "Reusable text extraction processor for multiple sites"
    ):
        """
        Initialize shared text extraction processor.
        
        Args:
            processor_id: Unique identifier for the processor
            name: Human-readable name for the processor
            version: Processor version
            description: Processor description
        """
        super().__init__(
            processor_id=processor_id,
            name=name,
            version=version,
            description=description,
            processor_type="TEXT_EXTRACTION"
        )
        
        # Text extraction configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Extraction state and statistics
        self._extraction_stats: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._extraction_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'wikipedia', 'news_sites', 'blogs', 'forums', 'ecommerce',
            'social_media', 'documentation', 'articles', 'reviews', 'comments'
        ]
        
        # Common text patterns and selectors
        self._title_selectors = [
            'h1', 'title', '[class*="title"]', '[class*="headline"]',
            '[data-testid*="title"]', '.entry-title', '.post-title'
        ]
        
        self._content_selectors = [
            'article', '[class*="content"]', '[class*="article"]',
            '.post-content', '.entry-content', '.article-body',
            '[data-testid*="content"]', 'main'
        ]
        
        self._author_selectors = [
            '[class*="author"]', '[class*="byline"]', '.author', '.byline',
            '[rel="author"]', '[data-testid*="author"]'
        ]
        
        self._date_selectors = [
            '[datetime]', '[class*="date"]', '[class*="time"]', '.date',
            '.time', '[data-testid*="date"]', 'time[datetime]'
        ]
        
        # Text cleaning patterns
        self._cleaning_patterns = [
            (r'\s+', ' '),  # Multiple whitespace
            (r'\n\s*\n', '\n\n'),  # Multiple newlines
            (r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}"\'\/]', ''),  # Special chars
            (r'\s+([\.!\?\;\:])', r'\1'),  # Space before punctuation
        ]
    
    async def initialize(self, context: ProcessorContext) -> bool:
        """
        Initialize shared text extraction processor.
        
        Args:
            context: Processor context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load text extraction configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('text_extraction_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared text extraction processor initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared text extraction initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ProcessorResult:
        """
        Execute text extraction for a specific site.
        
        Args:
            **kwargs: Extraction parameters including 'site', 'page', 'selectors', etc.
            
        Returns:
            Text extraction result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            selectors = kwargs.get('selectors', {})
            auto_detect = kwargs.get('auto_detect', True)
            clean_text = kwargs.get('clean_text', True)
            extract_metadata = kwargs.get('extract_metadata', True)
            
            if not site:
                return ProcessorResult(
                    success=False,
                    data={'error': 'Site parameter is required'},
                    errors=['Site parameter is required']
                )
            
            if not page:
                return ProcessorResult(
                    success=False,
                    data={'error': 'Page parameter is required'},
                    errors=['Page parameter is required']
                )
            
            # Initialize extraction stats
            self._initialize_extraction_stats(site)
            
            # Perform text extraction
            extraction_result = await self._extract_text(
                site, page, selectors, auto_detect, clean_text, extract_metadata
            )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_extraction_stats(site, extraction_result, execution_time)
            
            # Call extraction callbacks
            await self._call_extraction_callbacks(site, extraction_result)
            
            return ProcessorResult(
                success=extraction_result['success'],
                data={
                    'site': site,
                    'extraction_timestamp': start_time.isoformat(),
                    **extraction_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Text extraction failed: {str(e)}", "error")
            return ProcessorResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register text extraction configuration for a site.
        
        Args:
            site: Site identifier
            config: Text extraction configuration
        """
        self._site_configs[site] = {
            'title_selector': config.get('title_selector'),
            'content_selector': config.get('content_selector'),
            'author_selector': config.get('author_selector'),
            'date_selector': config.get('date_selector'),
            'summary_selector': config.get('summary_selector'),
            'tags_selector': config.get('tags_selector'),
            'exclude_selectors': config.get('exclude_selectors', []),
            'clean_text': config.get('clean_text', True),
            'remove_empty_paragraphs': config.get('remove_empty_paragraphs', True),
            'min_content_length': config.get('min_content_length', 100),
            'max_content_length': config.get('max_content_length', 50000),
            'extract_links': config.get('extract_links', False),
            'extract_images': config.get('extract_images', False)
        }
        
        self._log_operation("register_site", f"Registered text extraction configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default text extraction configurations for common sites."""
        default_configs = {
            'wikipedia': {
                'title_selector': '#firstHeading',
                'content_selector': '#mw-content-text',
                'author_selector': '.author, .byline',
                'date_selector': '.date, .timestamp',
                'summary_selector': '#mw-content-text p:first-of-type',
                'exclude_selectors': ['.reflist', '.navbox', '.infobox'],
                'clean_text': True,
                'remove_empty_paragraphs': True
            },
            'news_sites': {
                'title_selector': 'h1, .headline, .article-title',
                'content_selector': 'article, .article-body, .content',
                'author_selector': '.author, .byline, .reporter',
                'date_selector': '.date, .time, .published',
                'summary_selector': '.summary, .excerpt, .lead',
                'exclude_selectors': ['.ads', '.sidebar', '.comments'],
                'clean_text': True,
                'remove_empty_paragraphs': True
            },
            'blogs': {
                'title_selector': '.entry-title, .post-title, h1',
                'content_selector': '.entry-content, .post-content, article',
                'author_selector': '.author, .post-author',
                'date_selector': '.entry-date, .post-date, time',
                'summary_selector': '.excerpt, .summary',
                'exclude_selectors': ['.sidebar', '.comments', '.related-posts'],
                'clean_text': True,
                'remove_empty_paragraphs': True
            },
            'ecommerce': {
                'title_selector': '.product-title, h1, .item-title',
                'content_selector': '.product-description, .description, .details',
                'author_selector': '.seller, .vendor',
                'date_selector': '.date-added, .listed-date',
                'summary_selector': '.summary, .short-description',
                'exclude_selectors': ['.price', '.shipping', '.reviews'],
                'clean_text': True,
                'remove_empty_paragraphs': True
            },
            'forums': {
                'title_selector': '.thread-title, .post-title, h1',
                'content_selector': '.post-content, .message, .post-body',
                'author_selector': '.username, .author, .poster',
                'date_selector': '.post-date, .timestamp, time',
                'exclude_selectors': ['.signature', '.avatar', '.user-info'],
                'clean_text': True,
                'remove_empty_paragraphs': True
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    def _initialize_extraction_stats(self, site: str) -> None:
        """Initialize extraction statistics for a site."""
        if site not in self._extraction_stats:
            self._extraction_stats[site] = {
                'extractions_performed': 0,
                'total_characters_extracted': 0,
                'total_words_extracted': 0,
                'average_extraction_time_ms': 0.0,
                'last_extraction_time': None,
                'success_count': 0,
                'error_count': 0
            }
    
    async def _extract_text(
        self, site: str, page, selectors: Dict[str, str], auto_detect: bool,
        clean_text: bool, extract_metadata: bool
    ) -> Dict[str, Any]:
        """Perform text extraction."""
        try:
            config = self._site_configs[site]
            
            # Auto-detect selectors if not provided
            if auto_detect:
                detected_selectors = await self._detect_text_selectors(page)
                # Merge with provided selectors
                final_selectors = {**detected_selectors, **selectors}
            else:
                final_selectors = {**config, **selectors}
            
            # Extract different text elements
            extracted_data = {}
            
            # Extract title
            title_selector = final_selectors.get('title_selector')
            if title_selector:
                extracted_data['title'] = await self._extract_text_content(page, title_selector)
            
            # Extract main content
            content_selector = final_selectors.get('content_selector')
            if content_selector:
                extracted_data['content'] = await self._extract_text_content(page, content_selector, clean_text)
            
            # Extract summary
            summary_selector = final_selectors.get('summary_selector')
            if summary_selector:
                extracted_data['summary'] = await self._extract_text_content(page, summary_selector, clean_text)
            
            # Extract author
            author_selector = final_selectors.get('author_selector')
            if author_selector:
                extracted_data['author'] = await self._extract_text_content(page, author_selector)
            
            # Extract date
            date_selector = final_selectors.get('date_selector')
            if date_selector:
                extracted_data['date'] = await self._extract_date_content(page, date_selector)
            
            # Extract tags
            tags_selector = final_selectors.get('tags_selector')
            if tags_selector:
                extracted_data['tags'] = await self._extract_tags_content(page, tags_selector)
            
            # Extract metadata if requested
            if extract_metadata:
                extracted_data['metadata'] = await self._extract_metadata(page, final_selectors)
            
            # Apply content filters
            extracted_data = await self._apply_content_filters(extracted_data, final_selectors)
            
            # Calculate statistics
            extracted_data['statistics'] = self._calculate_text_statistics(extracted_data)
            
            return {
                'success': True,
                'extracted_data': extracted_data,
                'selectors_used': final_selectors,
                'clean_text_applied': clean_text
            }
            
        except Exception as e:
            self._log_operation("_extract_text", f"Text extraction failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _detect_text_selectors(self, page) -> Dict[str, str]:
        """Auto-detect text selectors on the page."""
        try:
            detected_selectors = {}
            
            # Detect title
            for selector in self._title_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 5:
                        detected_selectors['title_selector'] = selector
                        break
            
            # Detect content
            for selector in self._content_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 100:
                        detected_selectors['content_selector'] = selector
                        break
            
            # Detect author
            for selector in self._author_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 2:
                        detected_selectors['author_selector'] = selector
                        break
            
            # Detect date
            for selector in self._date_selectors:
                element = await page.query_selector(selector)
                if element:
                    # Check if it has datetime attribute or contains date-like text
                    datetime_attr = await element.get_attribute('datetime')
                    text = await element.text_content()
                    if datetime_attr or (text and self._contains_date(text)):
                        detected_selectors['date_selector'] = selector
                        break
            
            self._log_operation("_detect_text_selectors", f"Detected selectors: {detected_selectors}")
            return detected_selectors
            
        except Exception as e:
            self._log_operation("_detect_text_selectors", f"Text selector detection failed: {str(e)}", "error")
            return {}
    
    async def _extract_text_content(self, page, selector: str, clean_text: bool = True) -> Optional[str]:
        """Extract text content from a selector."""
        try:
            element = await page.query_selector(selector)
            if not element:
                return None
            
            text = await element.text_content()
            if not text:
                return None
            
            # Clean text if requested
            if clean_text:
                text = self._clean_text_content(text)
            
            return text.strip()
            
        except Exception as e:
            self._log_operation("_extract_text_content", f"Failed to extract text from {selector}: {str(e)}", "error")
            return None
    
    async def _extract_date_content(self, page, selector: str) -> Optional[str]:
        """Extract date content from a selector."""
        try:
            element = await page.query_selector(selector)
            if not element:
                return None
            
            # Try datetime attribute first
            datetime_attr = await element.get_attribute('datetime')
            if datetime_attr:
                return datetime_attr
            
            # Fall back to text content
            text = await element.text_content()
            if text:
                return self._clean_text_content(text.strip())
            
            return None
            
        except Exception as e:
            self._log_operation("_extract_date_content", f"Failed to extract date from {selector}: {str(e)}", "error")
            return None
    
    async def _extract_tags_content(self, page, selector: str) -> List[str]:
        """Extract tags content from a selector."""
        try:
            elements = await page.query_selector_all(selector)
            if not elements:
                return []
            
            tags = []
            for element in elements:
                text = await element.text_content()
                if text:
                    tags.append(self._clean_text_content(text.strip()))
            
            return tags
            
        except Exception as e:
            self._log_operation("_extract_tags_content", f"Failed to extract tags from {selector}: {str(e)}", "error")
            return []
    
    async def _extract_metadata(self, page, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract additional metadata from the page."""
        try:
            metadata = {}
            
            # Extract page URL
            metadata['url'] = page.url
            
            # Extract page title
            metadata['page_title'] = await page.title()
            
            # Extract language
            lang = await page.evaluate('() => document.documentElement.lang || document.body.lang')
            if lang:
                metadata['language'] = lang
            
            # Extract description meta tag
            description = await page.evaluate('() => { const desc = document.querySelector(\'meta[name="description"]\'); return desc ? desc.getAttribute("content") : null; }')
            if description:
                metadata['description'] = description
            
            # Extract keywords meta tag
            keywords = await page.evaluate('() => { const kw = document.querySelector(\'meta[name="keywords"]\'); return kw ? kw.getAttribute("content") : null; }')
            if keywords:
                metadata['keywords'] = keywords
            
            # Extract word count
            content = selectors.get('content_selector')
            if content:
                content_element = await page.query_selector(content)
                if content_element:
                    text = await content_element.text_content()
                    metadata['word_count'] = len(text.split()) if text else 0
                    metadata['character_count'] = len(text) if text else 0
            
            return metadata
            
        except Exception as e:
            self._log_operation("_extract_metadata", f"Failed to extract metadata: {str(e)}", "error")
            return {}
    
    async def _apply_content_filters(self, extracted_data: Dict[str, Any], selectors: Dict[str, str]) -> Dict[str, Any]:
        """Apply content filters and cleaning rules."""
        try:
            # Remove empty paragraphs
            if selectors.get('remove_empty_paragraphs', True):
                for key in ['content', 'summary']:
                    if key in extracted_data and extracted_data[key]:
                        extracted_data[key] = self._remove_empty_paragraphs(extracted_data[key])
            
            # Apply length limits
            min_length = selectors.get('min_content_length', 100)
            max_length = selectors.get('max_content_length', 50000)
            
            for key in ['content', 'summary']:
                if key in extracted_data and extracted_data[key]:
                    text = extracted_data[key]
                    if len(text) < min_length:
                        extracted_data[key] = None
                    elif len(text) > max_length:
                        extracted_data[key] = text[:max_length] + "..."
            
            return extracted_data
            
        except Exception as e:
            self._log_operation("_apply_content_filters", f"Failed to apply content filters: {str(e)}", "error")
            return extracted_data
    
    def _clean_text_content(self, text: str) -> str:
        """Clean and normalize text content."""
        try:
            if not text:
                return text
            
            # Apply cleaning patterns
            for pattern, replacement in self._cleaning_patterns:
                text = re.sub(pattern, replacement, text)
            
            # Strip leading/trailing whitespace
            text = text.strip()
            
            return text
            
        except Exception as e:
            self._log_operation("_clean_text_content", f"Failed to clean text: {str(e)}", "error")
            return text
    
    def _remove_empty_paragraphs(self, text: str) -> str:
        """Remove empty or whitespace-only paragraphs."""
        try:
            # Split by double newlines (paragraphs)
            paragraphs = text.split('\n\n')
            
            # Filter out empty paragraphs
            filtered_paragraphs = []
            for paragraph in paragraphs:
                if paragraph.strip():
                    filtered_paragraphs.append(paragraph.strip())
            
            return '\n\n'.join(filtered_paragraphs)
            
        except Exception as e:
            self._log_operation("_remove_empty_paragraphs", f"Failed to remove empty paragraphs: {str(e)}", "error")
            return text
    
    def _contains_date(self, text: str) -> bool:
        """Check if text contains a date."""
        try:
            # Common date patterns
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
                r'\d{4}-\d{2}-\d{2}',      # YYYY-MM-DD
                r'\d{1,2}\s+\w+\s+\d{4}', # DD Month YYYY
                r'\w+\s+\d{1,2},\s+\d{4}', # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                if re.search(pattern, text):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _calculate_text_statistics(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate text statistics."""
        try:
            stats = {}
            
            for key in ['title', 'content', 'summary']:
                if key in extracted_data and extracted_data[key]:
                    text = extracted_data[key]
                    stats[f'{key}_character_count'] = len(text)
                    stats[f'{key}_word_count'] = len(text.split())
                    stats[f'{key}_paragraph_count'] = len(text.split('\n\n'))
            
            return stats
            
        except Exception as e:
            self._log_operation("_calculate_text_statistics", f"Failed to calculate text statistics: {str(e)}", "error")
            return {}
    
    def _update_extraction_stats(self, site: str, result: Dict[str, Any], execution_time: float) -> None:
        """Update extraction statistics for a site."""
        try:
            if site not in self._extraction_stats:
                return
            
            stats = self._extraction_stats[site]
            stats['extractions_performed'] += 1
            stats['last_extraction_time'] = datetime.utcnow()
            
            if result['success']:
                stats['success_count'] += 1
                
                # Update text statistics
                extracted_data = result.get('extracted_data', {})
                for key in ['title', 'content', 'summary']:
                    if key in extracted_data and extracted_data[key]:
                        text = extracted_data[key]
                        stats['total_characters_extracted'] += len(text)
                        stats['total_words_extracted'] += len(text.split())
            else:
                stats['error_count'] += 1
            
            # Update average execution time
            total_time = stats.get('total_execution_time', 0) + execution_time
            stats['total_execution_time'] = total_time
            stats['average_extraction_time_ms'] = total_time / stats['extractions_performed']
            
        except Exception as e:
            self._log_operation("_update_extraction_stats", f"Failed to update extraction stats: {str(e)}", "error")
    
    def add_extraction_callback(self, site: str, callback: Callable) -> None:
        """Add callback for text extraction events."""
        if site not in self._extraction_callbacks:
            self._extraction_callbacks[site] = []
        self._extraction_callbacks[site].append(callback)
    
    async def _call_extraction_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call extraction callbacks for site."""
        if site in self._extraction_callbacks:
            for callback in self._extraction_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_extraction_callbacks", f"Extraction callback failed for {site}: {str(e)}", "error")
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites."""
        return list(self._supported_sites)
    
    def get_site_config(self, site: str) -> Optional[Dict[str, Any]]:
        """Get text extraction configuration for a site."""
        return self._site_configs.get(site)
    
    def get_extraction_stats(self, site: str) -> Optional[Dict[str, Any]]:
        """Get extraction statistics for a site."""
        if site not in self._extraction_stats:
            return None
        
        stats = self._extraction_stats[site].copy()
        if 'last_extraction_time' in stats and isinstance(stats['last_extraction_time'], datetime):
            stats['last_extraction_time'] = stats['last_extraction_time'].isoformat()
        
        return stats
    
    def reset_extraction_stats(self, site: str) -> None:
        """Reset extraction statistics for a site."""
        if site in self._extraction_stats:
            del self._extraction_stats[site]
    
    async def cleanup(self) -> None:
        """Clean up shared text extraction processor."""
        try:
            # Clear all stats and callbacks
            self._extraction_stats.clear()
            self._extraction_callbacks.clear()
            
            self._log_operation("cleanup", "Shared text extraction processor cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared text extraction cleanup failed: {str(e)}", "error")


# Factory function for easy processor creation
def create_text_extraction_processor() -> TextExtractionProcessor:
    """Create a shared text extraction processor."""
    return TextExtractionProcessor()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_text_extractor',
    'name': 'Shared Text Extraction Processor',
    'version': '1.0.0',
    'type': 'TEXT_EXTRACTION',
    'description': 'Reusable text extraction processor for multiple sites',
    'supported_sites': ['wikipedia', 'news_sites', 'blogs', 'forums', 'ecommerce', 'social_media', 'documentation', 'articles', 'reviews', 'comments'],
    'features': [
        'multi_site_support',
        'auto_selector_detection',
        'text_cleaning',
        'metadata_extraction',
        'statistics_tracking',
        'callback_system',
        'content_filtering'
    ],
    'dependencies': [],
    'configuration_required': [],
    'optional_configuration': ['title_selector', 'content_selector', 'author_selector', 'date_selector', 'clean_text', 'min_content_length']
}
