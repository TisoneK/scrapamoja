"""
Wikipedia scraper implementation.

Example scraper demonstrating the site scraper template system.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from src.sites.base.site_scraper import BaseSiteScraper
from .flow import WikipediaFlow
from .config import SITE_CONFIG
from .extraction.config import WikipediaExtractionConfig
from .extraction.validators import WikipediaDataValidator
from .extraction.rules import WikipediaExtractionRules
from .extraction.models import ArticleExtractionResult, SearchExtractionResult, InfoboxData
from .extraction.link_processor import WikipediaLinkProcessor
from .extraction.infobox_processor import WikipediaInfoboxProcessor
from .flows.extraction_flow import ExtractionFlow
from .selector_loader import WikipediaSelectorIntegration
from .integration_bridge import WikipediaIntegrationBridge, initialize_wikipedia_integration


class WikipediaScraper(BaseSiteScraper):
    """Wikipedia scraper implementation."""
    
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page, selector_engine, extraction_config: Optional[WikipediaExtractionConfig] = None):
        super().__init__(page, selector_engine)
        self.flow = WikipediaFlow(page, selector_engine)
        
        # Initialize extraction components
        self.extraction_config = extraction_config or WikipediaExtractionConfig()
        self.validator = WikipediaDataValidator()
        self.extraction_rules = WikipediaExtractionRules()
        self.extraction_flow = ExtractionFlow(self.extraction_config)
        
        # Initialize specialized processors
        self.link_processor = WikipediaLinkProcessor()
        self.infobox_processor = WikipediaInfoboxProcessor()
        
        # Initialize complete integration bridge (replaces separate YAML selector integration)
        self.integration_bridge = WikipediaSelectorIntegration(selector_engine)
        self.complete_integration: Optional[WikipediaIntegrationBridge] = None
        self._yaml_selectors_initialized = False

    async def initialize_yaml_selectors(self) -> bool:
        """Initialize YAML selectors for real data extraction using complete integration bridge."""
        try:
            if not self._yaml_selectors_initialized:
                # Use the complete integration bridge instead of separate YAML integration
                self.complete_integration = await initialize_wikipedia_integration(self.selector_engine)
                if self.complete_integration:
                    self._yaml_selectors_initialized = True
                    
                    # Get the DOM context bridge for extraction flow
                    dom_context_bridge = self.complete_integration.get_dom_context_bridge()
                    if dom_context_bridge:
                        # Make the bridge available to extraction flow
                        self.extraction_flow.set_dom_context_bridge(dom_context_bridge)
                    
                    # Log available selectors
                    available_selectors = self.selector_engine.list_selectors()
                    print(f"🔍 DEBUG: Available selectors after complete integration: {available_selectors}")
                return self.complete_integration is not None
            return True
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize YAML selectors: {str(e)}")
            return False

    async def navigate(self):
        """Navigate to Wikipedia home page."""
        await self.flow.open_home()

    async def scrape(self, **kwargs):
        """Perform scraping using selectors."""
        # Initialize YAML selectors first
        await self.initialize_yaml_selectors()
        
        query = kwargs.get('query', '')
        article_title = kwargs.get('article_title', '')
        
        if query:
            # Perform search
            await self.flow.perform_search(query)
            
            # Extract search results
            results = await self._extract_search_results()
            
            return {
                "query": query,
                "results": results,
                "total_count": len(results),
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        elif article_title:
            # Open specific article
            await self.flow.open_article(article_title)
            
            # Extract article content
            article_data = await self._extract_article_content()
            
            return {
                "article_title": article_title,
                "content": article_data,
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        else:
            # Extract home page content
            home_data = await self._extract_home_content()
            
            return {
                "page": "home",
                "content": home_data,
                "scraped_at": datetime.utcnow().isoformat()
            }

    async def scrape_with_extraction(self, **kwargs) -> Dict[str, Any]:
        """Scraping with extraction and type conversion."""
        query = kwargs.get('query', '')
        article_title = kwargs.get('article_title', '')
        
        try:
            if article_title:
                # Article extraction with type conversion
                result = await self.extraction_flow.extract_article_data(
                    self.page, self.selector_engine, article_title
                )
                return {
                    "type": "article",
                    "result": result,
                    "scraped_at": datetime.utcnow().isoformat()
                }
            
            elif query:
                # Search extraction with pattern matching
                result = await self.extraction_flow.extract_search_results(
                    self.page, self.selector_engine, query
                )
                return {
                    "type": "search",
                    "result": result,
                    "scraped_at": datetime.utcnow().isoformat()
                }
            
            else:
                raise ValueError("Either 'query' or 'article_title' must be provided")
                
        except ValueError as e:
            # Handle validation errors
            return {
                "type": "error",
                "error_type": "validation_error",
                "error": str(e),
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        except TimeoutError as e:
            # Handle timeout errors
            return {
                "type": "error",
                "error_type": "timeout_error",
                "error": f"Extraction timeout: {str(e)}",
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        except ConnectionError as e:
            # Handle connection errors
            return {
                "type": "error",
                "error_type": "connection_error",
                "error": f"Connection failed: {str(e)}",
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            # Handle unexpected errors
            return {
                "type": "error",
                "error_type": "unexpected_error",
                "error": f"Unexpected error during extraction: {str(e)}",
                "scraped_at": datetime.utcnow().isoformat()
            }
    
    async def scrape_search_with_fallback(self, query: str, max_retries: int = 3) -> Dict[str, Any]:
        """Search extraction with fallback mechanisms."""
        for attempt in range(max_retries):
            try:
                # Try extraction with pattern matching first
                result = await self.extraction_flow.extract_search_results(
                    self.page, self.selector_engine, query
                )
                
                # Validate result quality
                if result.quality_metrics.get('average_quality_score', 0) > 0.5:
                    return {
                        "type": "search",
                        "result": result,
                        "method": "pattern_matching",
                        "attempt": attempt + 1,
                        "scraped_at": datetime.utcnow().isoformat()
                    }
                else:
                    # Quality too low, try fallback
                    if attempt < max_retries - 1:
                        continue
                    
                    # Last attempt, return with warning
                    return {
                        "type": "search",
                        "result": result,
                        "method": "pattern_matching_low_quality",
                        "attempt": attempt + 1,
                        "warning": "Low quality results returned",
                        "scraped_at": datetime.utcnow().isoformat()
                    }
            
            except Exception as e:
                if attempt < max_retries - 1:
                    # Try fallback method
                    try:
                        fallback_result = await self._fallback_search_extraction(query)
                        return {
                            "type": "search",
                            "result": fallback_result,
                            "method": "fallback",
                            "attempt": attempt + 1,
                            "warning": f"Enhanced extraction failed: {str(e)}",
                            "scraped_at": datetime.utcnow().isoformat()
                        }
                    except Exception as fallback_error:
                        continue
                else:
                    # All attempts failed
                    return {
                        "type": "error",
                        "error_type": "extraction_failed",
                        "error": f"All extraction attempts failed: {str(e)}",
                        "attempts": max_retries,
                        "scraped_at": datetime.utcnow().isoformat()
                    }
        
        return {
            "type": "error",
            "error_type": "max_retries_exceeded",
            "error": f"Maximum retries ({max_retries}) exceeded",
            "scraped_at": datetime.utcnow().isoformat()
        }
    
    async def _fallback_search_extraction(self, query: str) -> SearchExtractionResult:
        """Fallback search extraction using basic methods."""
        try:
            # Use existing basic search extraction
            basic_results = await self._extract_search_results()
            
            # Convert to enhanced format with minimal processing
            enhanced_results = []
            for result in basic_results:
                enhanced_result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", ""),
                    "relevance_score": 0.5,  # Default relevance
                    "article_size": len(result.get("description", "")),
                    "last_modified": None,
                    "snippet": result.get("description", ""),
                    "pageid": None,
                    "category": "Unknown"
                }
                enhanced_results.append(enhanced_result)
            
            return SearchExtractionResult(
                query=query,
                results=enhanced_results,
                total_count=len(enhanced_results),
                search_metadata={
                    "extraction_method": "fallback",
                    "fallback_reason": "Enhanced extraction failed",
                    "basic_result_count": len(basic_results)
                },
                quality_metrics={
                    "average_quality_score": 0.5,
                    "completeness": 60.0,  # Basic completeness
                    "validation_passed": False
                },
                scraped_at=datetime.utcnow(),
                performance_metrics={
                    "extraction_time_ms": 0,
                    "validation_time_ms": 0,
                    "total_time_ms": 0
                }
            )
        
        except Exception as e:
            # Create minimal error result
            return SearchExtractionResult(
                query=query,
                results=[],
                total_count=0,
                search_metadata={
                    "extraction_method": "fallback_error",
                    "error": str(e)
                },
                quality_metrics={
                    "average_quality_score": 0.0,
                    "completeness": 0.0,
                    "validation_passed": False
                },
                scraped_at=datetime.utcnow(),
                performance_metrics={
                    "extraction_time_ms": 0,
                    "validation_time_ms": 0,
                    "total_time_ms": 0
                }
            )
    
    def handle_extraction_error(self, error: Exception, extraction_type: str) -> Dict[str, Any]:
        """Handle extraction errors with appropriate fallbacks."""
        error_type = type(error).__name__
        
        if isinstance(error, ValueError):
            # Validation errors - return with default values
            return {
                "type": "partial_result",
                "error_type": error_type,
                "error": str(error),
                "data": self.extraction_config.get_default_values(),
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        elif isinstance(error, (TimeoutError, ConnectionError)):
            # Network/time errors - retry with fallback
            return {
                "type": "fallback_result",
                "error_type": error_type,
                "error": str(error),
                "fallback_used": True,
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        else:
            # Unexpected errors - return error info only
            return {
                "type": "error",
                "error_type": error_type,
                "error": str(e),
                "scraped_at": datetime.utcnow().isoformat()
            }

    async def _extract_search_results(self) -> list:
        """Extract search results from the page."""
        try:
            # Get all search result elements
            result_elements = await self.selector_engine.find_all(self.page, "search_results")
            
            results = []
            for element in result_elements:
                title = await self.selector_engine.get_text(element, "result_title")
                url = await self.selector_engine.get_attribute(element, "result_url", "href")
                description = await self.selector_engine.get_text(element, "result_description")
                
                if title:
                    results.append({
                        "title": title.strip(),
                        "url": url or "",
                        "description": description.strip() if description else ""
                    })
            
            return results
            
        except Exception as e:
            return [{"error": f"Failed to extract search results: {str(e)}"}]

    async def _extract_article_content(self) -> dict:
        """Extract content from a Wikipedia article."""
        try:
            # Get article title
            title = await self.selector_engine.get_text(self.page, "article_title")
            
            # Get article content
            content = await self.selector_engine.get_text(self.page, "article_content")
            
            # Get infobox data if available
            infobox = await self._extract_infobox()
            
            # Get table of contents
            toc = await self._extract_table_of_contents()
            
            return {
                "title": title.strip() if title else "",
                "content": content.strip() if content else "",
                "infobox": infobox,
                "table_of_contents": toc,
                "url": self.page.url
            }
            
        except Exception as e:
            return {"error": f"Failed to extract article content: {str(e)}"}

    async def _extract_infobox(self) -> dict:
        """Extract infobox data from article."""
        try:
            infobox_elements = await self.selector_engine.find_all(self.page, "infobox_rows")
            
            infobox = {}
            for element in infobox_elements:
                label = await self.selector_engine.get_text(element, "infobox_label")
                value = await self.selector_engine.get_text(element, "infobox_value")
                
                if label and value:
                    infobox[label.strip()] = value.strip()
            
            return infobox
            
        except Exception:
            return {}

    async def _extract_table_of_contents(self) -> list:
        """Extract table of contents from article."""
        try:
            toc_elements = await self.selector_engine.find_all(self.page, "toc_items")
            
            toc = []
            for element in toc_elements:
                text = await self.selector_engine.get_text(element, "toc_text")
                level = await self.selector_engine.get_attribute(element, "toc_level", "data-level")
                
                if text:
                    toc.append({
                        "text": text.strip(),
                        "level": int(level) if level and level.isdigit() else 1
                    })
            
            return toc
            
        except Exception:
            return []

    async def _extract_home_content(self) -> dict:
        """Extract content from Wikipedia home page."""
        try:
            # Get featured article
            featured_article = await self.selector_engine.get_text(self.page, "featured_article")
            
            # Get in the news
            in_the_news = await self._extract_in_the_news()
            
            # Get did you know
            did_you_know = await self._extract_did_you_know()
            
            return {
                "featured_article": featured_article.strip() if featured_article else "",
                "in_the_news": in_the_news,
                "did_you_know": did_you_know,
                "url": self.page.url
            }
            
        except Exception as e:
            return {"error": f"Failed to extract home content: {str(e)}"}

    async def _extract_in_the_news(self) -> list:
        """Extract 'In the news' section from home page."""
        try:
            news_elements = await self.selector_engine.find_all(self.page, "news_items")
            
            news = []
            for element in news_elements:
                text = await self.selector_engine.get_text(element, "news_text")
                if text:
                    news.append(text.strip())
            
            return news
            
        except Exception:
            return []

    async def _extract_did_you_know(self) -> list:
        """Extract 'Did you know' section from home page."""
        try:
            dyk_elements = await self.selector_engine.find_all(self.page, "dyk_items")
            
            dyk = []
            for element in dyk_elements:
                text = await self.selector_engine.get_text(element, "dyk_text")
                if text:
                    dyk.append(text.strip())
            
            return dyk
            
        except Exception:
            return []

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw scraped data into structured output."""
        normalized = {
            "site": self.site_id,
            "site_name": self.site_name,
            "timestamp": datetime.utcnow().isoformat(),
            "data": raw_data
        }
        
        # Add specific normalization based on data type
        if "query" in raw_data:
            normalized["type"] = "search_results"
            normalized["query"] = raw_data.get("query", "")
            normalized["result_count"] = raw_data.get("total_count", 0)
        
        elif "article_title" in raw_data:
            normalized["type"] = "article"
            normalized["article_title"] = raw_data.get("article_title", "")
            normalized["article_url"] = raw_data.get("data", {}).get("url", "")
        
        elif "page" in raw_data:
            normalized["type"] = raw_data.get("page", "")
            normalized["page_url"] = raw_data.get("data", {}).get("url", "")
        
        return normalized
