# Basic Template Framework Tutorial

## Overview

This tutorial teaches you the fundamentals of the Site Template Integration Framework through practical examples.

## Prerequisites

- Python 3.8+
- Basic understanding of web scraping
- Familiarity with Playwright
- Knowledge of YAML configuration

## Learning Objectives

By the end of this tutorial, you will:
- Understand the template framework architecture
- Create a basic scraper using templates
- Use YAML selectors for element selection
- Implement basic error handling
- Configure template settings

## Step 1: Understanding the Framework

The Site Template Integration Framework provides:

- **BaseSiteTemplate**: Core template class
- **YAML Selectors**: Declarative element selection
- **Integration Bridge**: Framework component integration
- **Validation**: Built-in validation and error handling
- **Performance**: Optimized scraping operations

## Step 2: Creating Your First Template

Let's create a simple scraper for a blog site:

```python
# simple_scraper.py
import asyncio
from src.sites.base.template import BaseSiteTemplate

class BlogScraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__(
            name="blog_scraper",
            version="1.0.0",
            description="Simple blog scraper",
            author="Your Name",
            framework_version="1.0.0",
            site_domain="example-blog.com"
        )
        
        self.capabilities = ["scraping", "extraction"]
        self.supported_domains = ["example-blog.com"]
    
    async def _execute_scrape_logic(self, action: str, **kwargs):
        if action == "scrape_posts":
            return await self._scrape_posts(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _scrape_posts(self, limit: int = 10):
        # Implementation will be added in next steps
        return {
            "action": "scrape_posts",
            "posts": [],
            "limit": limit
        }

# Usage example
async def main():
    # This would be your actual Playwright page and selector engine
    page = None  # Your Playwright page
    selector_engine = None  # Your selector engine
    
    scraper = BlogScraper(page, selector_engine)
    await scraper.initialize()
    
    result = await scraper.scrape("scrape_posts", limit=5)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 3: Adding YAML Selectors

Create a YAML selector file:

```yaml
# selectors/blog_posts.yaml
name: blog_posts
description: Blog post list selector
selector: .blog-post
strategies:
  - name: css
    type: css
    priority: 1
    confidence: 0.9
    timeout: 30000
  - name: xpath
    type: xpath
    priority: 2
    confidence: 0.8
    timeout: 30000
validation:
  required: true
  exists: true
  min_length: 50
metadata:
  category: content
  tags: [blog, posts, list]
  version: 1.0.0

---
name: post_title
description: Blog post title selector
selector: .blog-post h2
strategies:
  - name: css
    type: css
    priority: 1
    confidence: 0.95
validation:
  required: true
  exists: true
  text_pattern: "^.+$"
metadata:
  category: content
  tags: [blog, title, text]
  version: 1.0.0

---
name: post_content
description: Blog post content selector
selector: .blog-post .content
strategies:
  - name: css
    type: css
    priority: 1
    confidence: 0.9
validation:
  required: true
  exists: true
  min_length: 100
metadata:
  category: content
  tags: [blog, content, text]
  version: 1.0.0
```

## Step 4: Using Selectors in Your Template

Update your scraper to use YAML selectors:

```python
# simple_scraper.py (updated)
import asyncio
from src.sites.base.template import BaseSiteTemplate

class BlogScraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__(
            name="blog_scraper",
            version="1.0.0",
            description="Simple blog scraper",
            author="Your Name",
            framework_version="1.0.0",
            site_domain="example-blog.com"
        )
        
        self.capabilities = ["scraping", "extraction"]
        self.supported_domains = ["example-blog.com"]
    
    async def _execute_scrape_logic(self, action: str, **kwargs):
        if action == "scrape_posts":
            return await self._scrape_posts(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _scrape_posts(self, limit: int = 10):
        try:
            # Use YAML selector to find blog posts
            posts_elements = await self.selector_engine.find_all(
                selector_name="blog_posts"
            )
            
            posts = []
            for i, post_element in enumerate(posts_elements[:limit]):
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
                
                posts.append({
                    "title": title.strip(),
                    "content": content.strip(),
                    "index": i
                })
            
            return {
                "action": "scrape_posts",
                "posts": posts,
                "count": len(posts),
                "limit": limit
            }
        
        except Exception as e:
            self.log_error(e, {"action": "scrape_posts", "limit": limit})
            raise

# Usage example remains the same
```

## Step 5: Adding Configuration

Create a configuration file:

```python
# config.py
from typing import Dict, Any

# Site configuration
SITE_CONFIG = {
    "name": "blog_scraper",
    "domain": "example-blog.com",
    "base_url": "https://example-blog.com",
    "version": "1.0.0",
    "author": "Your Name"
}

# Scraping configuration
SCRAPING_CONFIG = {
    "timeout": 30,
    "retry_count": 3,
    "rate_limit": {
        "requests_per_minute": 60
    }
}

# Selector configuration
SELECTOR_CONFIG = {
    "default_timeout": 30.0,
    "default_strategy": "css",
    "validation_enabled": True
}

# Combine all configurations
CONFIG = {
    "site": SITE_CONFIG,
    "scraping": SCRAPING_CONFIG,
    "selectors": SELECTOR_CONFIG
}
```

## Step 6: Error Handling and Validation

Add comprehensive error handling:

```python
# simple_scraper.py (with error handling)
import asyncio
from src.sites.base.template import BaseSiteTemplate

class BlogScraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__(
            name="blog_scraper",
            version="1.0.0",
            description="Simple blog scraper",
            author="Your Name",
            framework_version="1.0.0",
            site_domain="example-blog.com"
        )
        
        self.capabilities = ["scraping", "extraction"]
        self.supported_domains = ["example-blog.com"]
    
    async def _execute_scrape_logic(self, action: str, **kwargs):
        try:
            if action == "scrape_posts":
                return await self._scrape_posts(**kwargs)
            else:
                raise ValueError(f"Unknown action: {action}")
        
        except Exception as e:
            self.log_error(e, {"action": action, "kwargs": kwargs})
            raise
    
    async def _scrape_posts(self, limit: int = 10):
        # Validate input
        if limit <= 0 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        
        try:
            # Check if we're on the right page
            current_url = self.page.url
            if "example-blog.com" not in current_url:
                raise ValueError(f"Not on blog page: {current_url}")
            
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
                    "message": "No posts found"
                }
            
            posts = []
            for i, post_element in enumerate(posts_elements[:limit]):
                try:
                    # Extract title
                    title_element = await self.selector_engine.find_first(
                        post_element, "post_title"
                    )
                    title = await title_element.text_content() if title_element else ""
                    
                    # Extract content
                    content_element = await self.selector_engine.find_first(
                        post_element, "post_content"
                    )
                    content = await content_element.text_content() if content_element else ""
                    
                    # Validate extracted data
                    if not title.strip():
                        self.log_warning(f"Empty title for post {i}", {"index": i})
                        continue
                    
                    posts.append({
                        "title": title.strip(),
                        "content": content.strip(),
                        "index": i
                    })
                
                except Exception as e:
                    self.log_error(f"Error extracting post {i}", e, {"index": i})
                    continue
            
            self.log_info(f"Successfully scraped {len(posts)} posts", {
                "requested": limit,
                "found": len(posts_elements),
                "extracted": len(posts)
            })
            
            return {
                "action": "scrape_posts",
                "posts": posts,
                "count": len(posts),
                "limit": limit
            }
        
        except Exception as e:
            self.log_error(f"Error in scrape_posts: {e}", e, {"limit": limit})
            raise

# Enhanced usage example
async def main():
    try:
        # Initialize components
        page = None  # Your Playwright page
        selector_engine = None  # Your selector engine
        
        # Create and initialize scraper
        scraper = BlogScraper(page, selector_engine)
        await scraper.initialize()
        
        # Check health
        health = await scraper.health_check()
        if health["overall_health"] != "healthy":
            print(f"Scraper health check failed: {health}")
            return
        
        # Scrape posts
        result = await scraper.scrape("scrape_posts", limit=5)
        print(f"Scraped {result['count']} posts:")
        
        for post in result["posts"]:
            print(f"- {post['title']}")
        
        # Get performance metrics
        metrics = scraper.get_performance_metrics()
        print(f"Performance: {metrics}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 7: Testing Your Template

Create a simple test:

```python
# test_scraper.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from simple_scraper import BlogScraper

class TestBlogScraper:
    def test_initialization(self):
        """Test scraper initialization."""
        page = Mock()
        selector_engine = Mock()
        
        scraper = BlogScraper(page, selector_engine)
        
        assert scraper.name == "blog_scraper"
        assert scraper.version == "1.0.0"
        assert scraper.site_domain == "example-blog.com"
        assert "scraping" in scraper.capabilities
    
    @pytest.mark.asyncio
    async def test_scrape_posts_success(self):
        """Test successful post scraping."""
        page = Mock()
        page.url = "https://example-blog.com/posts"
        selector_engine = Mock()
        
        # Mock selector responses
        selector_engine.find_all = AsyncMock(return_value=[Mock(), Mock()])
        selector_engine.find_first = AsyncMock(side_effect=[
            Mock(text_content=AsyncMock(return_value="Test Title")),
            Mock(text_content=AsyncMock(return_value="Test Content"))
        ])
        
        scraper = BlogScraper(page, selector_engine)
        await scraper.initialize()
        
        result = await scraper.scrape("scrape_posts", limit=2)
        
        assert result["action"] == "scrape_posts"
        assert result["count"] == 2
        assert len(result["posts"]) == 2
        assert result["posts"][0]["title"] == "Test Title"
    
    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test invalid action handling."""
        page = Mock()
        selector_engine = Mock()
        
        scraper = BlogScraper(page, selector_engine)
        await scraper.initialize()
        
        with pytest.raises(ValueError, match="Unknown action"):
            await scraper.scrape("invalid_action")

if __name__ == "__main__":
    pytest.main([__file__])
```

## Exercises

1. **Add a new action**: Create a `scrape_author` action to extract author information
2. **Add pagination**: Modify `scrape_posts` to handle multiple pages
3. **Add validation**: Validate that titles are not empty and content has minimum length
4. **Add caching**: Cache results to avoid re-scraping the same content
5. **Add logging**: Add structured logging for better debugging

## Next Steps

1. Read the [Advanced Tutorial](../advanced/tutorial_advanced.md)
2. Explore [Real-World Examples](../real_world/)
3. Learn about [Best Practices](../best_practices/)
4. Check the [Troubleshooting Guide](../troubleshooting/)

## Summary

In this tutorial, you learned:

- How to create a basic template using BaseSiteTemplate
- How to define and use YAML selectors
- How to implement error handling and validation
- How to add configuration and testing
- Best practices for template development

You're now ready to explore more advanced features! 🚀
