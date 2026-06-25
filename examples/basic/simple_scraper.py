"""
Simple scraper example for the template framework.

This example demonstrates the basic usage of the Site Template Integration Framework
to create a simple blog scraper with YAML selectors and error handling.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock

from src.sites.base.template import BaseSiteTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleBlogScraper(BaseSiteTemplate):
    """
    Simple blog scraper demonstrating basic framework usage.
    
    This scraper extracts blog posts from a blog website using YAML selectors
    and demonstrates error handling, validation, and performance monitoring.
    """
    
    def __init__(self, page, selector_engine):
        """
        Initialize the simple blog scraper.
        
        Args:
            page: Playwright page instance
            selector_engine: Selector engine instance
        """
        super().__init__(
            name="simple_blog_scraper",
            version="1.0.0",
            description="Simple blog scraper example",
            author="Template Framework Team",
            framework_version="1.0.0",
            site_domain="example-blog.com"
        )
        
        # Template capabilities
        self.capabilities = ["scraping", "extraction", "navigation"]
        
        # Supported domains
        self.supported_domains = ["example-blog.com", "blog.example.com"]
        
        # Dependencies
        self.dependencies = ["selector_engine", "extractor"]
        
        logger.info(f"SimpleBlogScraper initialized for {self.site_domain}")
    
    async def _execute_scrape_logic(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute scraping logic for different actions.
        
        Args:
            action: Action to perform
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Scrape results
        """
        try:
            if action == "scrape_posts":
                return await self._scrape_posts(**kwargs)
            elif action == "scrape_authors":
                return await self._scrape_authors(**kwargs)
            elif action == "get_blog_info":
                return await self._get_blog_info(**kwargs)
            else:
                raise ValueError(f"Unknown action: {action}")
        
        except Exception as e:
            self.log_error(e, {"action": action, "kwargs": kwargs})
            raise
    
    async def _scrape_posts(self, limit: int = 10, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape blog posts from the current page.
        
        Args:
            limit: Maximum number of posts to scrape
            category: Optional category filter
            
        Returns:
            Dict[str, Any]: Scraped posts data
        """
        # Validate input parameters
        if limit <= 0 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        
        try:
            # Check if we're on a valid page
            current_url = self.page.url
            if not any(domain in current_url for domain in self.supported_domains):
                raise ValueError(f"Not on supported domain: {current_url}")
            
            # Use YAML selector to find blog posts
            posts_elements = await self.selector_engine.find_all(
                selector_name="blog_posts"
            )
            
            if not posts_elements:
                self.log_info("No blog posts found", {"url": current_url})
                return {
                    "action": "scrape_posts",
                    "posts": [],
                    "count": 0,
                    "limit": limit,
                    "category": category,
                    "message": "No posts found"
                }
            
            posts = []
            skipped_count = 0
            
            for i, post_element in enumerate(posts_elements[:limit]):
                try:
                    # Extract post data
                    post_data = await self._extract_post_data(post_element, i)
                    
                    # Apply category filter if specified
                    if category and post_data.get("category") != category:
                        skipped_count += 1
                        continue
                    
                    # Validate post data
                    if not post_data["title"].strip():
                        self.log_warning(f"Empty title for post {i}", {"index": i})
                        skipped_count += 1
                        continue
                    
                    posts.append(post_data)
                
                except Exception as e:
                    self.log_error(f"Error extracting post {i}", e, {"index": i})
                    skipped_count += 1
                    continue
            
            # Log success
            self.log_info(f"Successfully scraped {len(posts)} posts", {
                "requested": limit,
                "found": len(posts_elements),
                "extracted": len(posts),
                "skipped": skipped_count,
                "category": category
            })
            
            return {
                "action": "scrape_posts",
                "posts": posts,
                "count": len(posts),
                "limit": limit,
                "category": category,
                "skipped": skipped_count
            }
        
        except Exception as e:
            self.log_error(f"Error in scrape_posts: {e}", e, {"limit": limit, "category": category})
            raise
    
    async def _extract_post_data(self, post_element, index: int) -> Dict[str, Any]:
        """
        Extract data from a single post element.
        
        Args:
            post_element: Post DOM element
            index: Post index
            
        Returns:
            Dict[str, Any]: Extracted post data
        """
        # Extract title using YAML selector
        title_element = await self.selector_engine.find_first(
            post_element, "post_title"
        )
        title = await title_element.text_content() if title_element else ""
        
        # Extract content using YAML selector
        content_element = await self.selector_engine.find_first(
            post_element, "post_content"
        )
        content = await content_element.text_content() if content_element else ""
        
        # Extract author using YAML selector
        author_element = await self.selector_engine.find_first(
            post_element, "post_author"
        )
        author = await author_element.text_content() if author_element else ""
        
        # Extract date using YAML selector
        date_element = await self.selector_engine.find_first(
            post_element, "post_date"
        )
        date = await date_element.get_attribute("datetime") if date_element else ""
        if not date and date_element:
            date = await date_element.text_content()
        
        # Extract category using YAML selector
        category_element = await self.selector_engine.find_first(
            post_element, "post_category"
        )
        category = await category_element.text_content() if category_element else ""
        
        # Extract link using YAML selector
        link_element = await self.selector_engine.find_first(
            post_element, "post_link"
        )
        link = await link_element.get_attribute("href") if link_element else ""
        
        return {
            "title": title.strip(),
            "content": content.strip(),
            "author": author.strip(),
            "date": date.strip(),
            "category": category.strip(),
            "link": link.strip(),
            "index": index
        }
    
    async def _scrape_authors(self, limit: int = 20) -> Dict[str, Any]:
        """
        Scrape author information from the blog.
        
        Args:
            limit: Maximum number of authors to scrape
            
        Returns:
            Dict[str, Any]: Authors data
        """
        try:
            # Use YAML selector to find author elements
            author_elements = await self.selector_engine.find_all(
                selector_name="author_info"
            )
            
            authors = []
            seen_authors = set()
            
            for author_element in author_elements[:limit]:
                try:
                    # Extract author name
                    name_element = await self.selector_engine.find_first(
                        author_element, "author_name"
                    )
                    name = await name_element.text_content() if name_element else ""
                    
                    # Extract author bio
                    bio_element = await self.selector_engine.find_first(
                        author_element, "author_bio"
                    )
                    bio = await bio_element.text_content() if bio_element else ""
                    
                    # Extract author avatar
                    avatar_element = await self.selector_engine.find_first(
                        author_element, "author_avatar"
                    )
                    avatar = await avatar_element.get_attribute("src") if avatar_element else ""
                    
                    # Skip duplicates
                    if name in seen_authors:
                        continue
                    
                    seen_authors.add(name)
                    
                    authors.append({
                        "name": name.strip(),
                        "bio": bio.strip(),
                        "avatar": avatar.strip()
                    })
                
                except Exception as e:
                    self.log_error(f"Error extracting author data", e)
                    continue
            
            return {
                "action": "scrape_authors",
                "authors": authors,
                "count": len(authors),
                "limit": limit
            }
        
        except Exception as e:
            self.log_error(f"Error in scrape_authors: {e}", e, {"limit": limit})
            raise
    
    async def _get_blog_info(self) -> Dict[str, Any]:
        """
        Get general blog information.
        
        Returns:
            Dict[str, Any]: Blog information
        """
        try:
            # Extract blog title
            title_element = await self.selector_engine.find_first("blog_title")
            title = await title_element.text_content() if title_element else ""
            
            # Extract blog description
            description_element = await self.selector_engine.find_first("blog_description")
            description = await description_element.text_content() if description_element else ""
            
            # Extract blog stats (posts count, etc.)
            stats_element = await self.selector_engine.find_first("blog_stats")
            stats = await stats_element.text_content() if stats_element else ""
            
            return {
                "action": "get_blog_info",
                "title": title.strip(),
                "description": description.strip(),
                "stats": stats.strip(),
                "url": self.page.url
            }
        
        except Exception as e:
            self.log_error(f"Error in get_blog_info: {e}", e)
            raise


# Mock setup for demonstration
def create_mock_components():
    """Create mock components for demonstration."""
    # Mock page
    page = Mock()
    page.url = "https://example-blog.com/posts"
    
    # Mock selector engine
    selector_engine = Mock()
    
    # Mock blog posts
    mock_post = Mock()
    mock_title = Mock()
    mock_title.text_content = AsyncMock(return_value="Sample Blog Post")
    mock_content = Mock()
    mock_content.text_content = AsyncMock(return_value="This is a sample blog post content...")
    mock_author = Mock()
    mock_author.text_content = AsyncMock(return_value="John Doe")
    mock_date = Mock()
    mock_date.get_attribute = AsyncMock(return_value="2025-01-29")
    mock_date.text_content = AsyncMock(return_value="January 29, 2025")
    mock_category = Mock()
    mock_category.text_content = AsyncMock(return_value="Technology")
    mock_link = Mock()
    mock_link.get_attribute = AsyncMock(return_value="/posts/sample-post")
    
    # Configure selector engine mocks
    selector_engine.find_all = AsyncMock(return_value=[mock_post, mock_post])
    selector_engine.find_first = AsyncMock(side_effect=[
        mock_title,      # post_title
        mock_content,    # post_content
        mock_author,     # post_author
        mock_date,       # post_date
        mock_category,   # post_category
        mock_link,        # post_link
    ])
    
    return page, selector_engine


# Example usage
async def main():
    """Main function demonstrating the simple scraper."""
    try:
        # Create mock components (in real usage, these would be actual Playwright objects)
        page, selector_engine = create_mock_components()
        
        # Create and initialize scraper
        scraper = SimpleBlogScraper(page, selector_engine)
        await scraper.initialize()
        
        # Check health
        health = await scraper.health_check()
        print(f"Scraper health: {health['overall_health']}")
        
        # Scrape blog posts
        print("\n=== Scraping Blog Posts ===")
        posts_result = await scraper.scrape("scrape_posts", limit=5)
        print(f"Scraped {posts_result['count']} posts:")
        
        for post in posts_result["posts"]:
            print(f"- {post['title']} by {post['author']} ({post['category']})")
        
        # Scrape authors
        print("\n=== Scraping Authors ===")
        authors_result = await scraper.scrape("scrape_authors", limit=3)
        print(f"Found {authors_result['count']} authors:")
        
        for author in authors_result["authors"]:
            print(f"- {author['name']}: {author['bio'][:50]}...")
        
        # Get blog info
        print("\n=== Blog Information ===")
        blog_info = await scraper.scrape("get_blog_info")
        print(f"Blog: {blog_info['title']}")
        print(f"Description: {blog_info['description']}")
        print(f"URL: {blog_info['url']}")
        
        # Get performance metrics
        print("\n=== Performance Metrics ===")
        metrics = scraper.get_performance_metrics()
        print(f"Total scrapes: {metrics['scrape_count']}")
        print(f"Success rate: {metrics['success_rate']:.2%}")
        print(f"Average time: {metrics['average_scrape_time']:.3f}s")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    print("🚀 Simple Blog Scraper Example")
    print("=" * 50)
    
    # Run the example
    asyncio.run(main())
    
    print("\n✅ Example completed successfully!")
    print("\nNext steps:")
    print("1. Read the basic tutorial: examples/basic/tutorial_basic.md")
    print("2. Try the advanced examples: examples/advanced/")
    print("3. Check real-world examples: examples/real_world/")
    print("4. Learn best practices: examples/best_practices/")
