"""
Link processor for Wikipedia articles.

This module provides comprehensive link analysis and categorization
for Wikipedia articles, including reference citation extraction.
"""

from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import re
from datetime import datetime


class WikipediaLinkProcessor:
    """Wikipedia-specific link processor and analyzer."""
    
    def __init__(self):
        """Initialize link processor."""
        self.wikipedia_domains = [
            'wikipedia.org',
            'en.wikipedia.org',
            'es.wikipedia.org',
            'fr.wikipedia.org',
            'de.wikipedia.org',
            'it.wikipedia.org',
            'pt.wikipedia.org',
            'ru.wikipedia.org',
            'ja.wikipedia.org',
            'zh.wikipedia.org'
        ]
        
        self.reference_patterns = [
            r'<ref[^>]*>(.*?)</ref>',
            r'\[\d+\]',
            r'\[citation needed\]',
            r'\[https?://[^\]]+\]'
        ]
    
    def categorize_link(self, url: str, context: str = "") -> str:
        """Categorize a link based on its URL and context."""
        if not url:
            return "unknown"
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Internal Wikipedia links
        if any(wiki_domain in domain for wiki_domain in self.wikipedia_domains):
            if parsed_url.fragment:
                return "internal_anchor"
            return "internal"
        
        # External links
        if domain:
            # Reference links
            if self._is_reference_link(url, context):
                return "reference"
            
            # Image links
            if self._is_image_link(url):
                return "image"
            
            # File links
            if self._is_file_link(url):
                return "file"
            
            # External website
            return "external"
        
        # Anchor links (same page)
        if url.startswith('#'):
            return "anchor"
        
        # Relative links
        if url.startswith('/') or url.startswith('./'):
            return "relative"
        
        return "unknown"
    
    def extract_references(self, content: str) -> List[Dict[str, Any]]:
        """Extract reference citations from content."""
        references = []
        
        # Extract <ref> tags
        ref_pattern = r'<ref[^>]*>(.*?)</ref>'
        ref_matches = re.finditer(ref_pattern, content, re.IGNORECASE | re.DOTALL)
        
        for i, match in enumerate(ref_matches):
            ref_content = match.group(1).strip()
            
            # Extract URL from reference
            url = self._extract_url_from_reference(ref_content)
            
            # Extract title
            title = self._extract_title_from_reference(ref_content)
            
            references.append({
                "type": "reference",
                "index": i + 1,
                "url": url,
                "title": title,
                "content": ref_content,
                "is_valid": bool(url),
                "extraction_method": "ref_tag"
            })
        
        # Extract citation patterns
        citation_pattern = r'\[citation needed\]'
        citation_matches = re.finditer(citation_pattern, content, re.IGNORECASE)
        
        for match in citation_matches:
            references.append({
                "type": "citation_needed",
                "url": None,
                "title": "Citation needed",
                "content": match.group(0),
                "position": match.start(),
                "is_valid": False,
                "extraction_method": "citation_pattern"
            })
        
        return references
    
    def extract_image_links(self, content: str, base_url: str = "") -> List[Dict[str, Any]]:
        """Extract image links with metadata."""
        image_links = []
        
        # Wikipedia image patterns
        image_patterns = [
            r'\[\[File:([^\]|]+)(?:\|([^\]]*))?\]\]',
            r'\[\[Image:([^\]|]+)(?:\|([^\]]*))?\]\]',
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
            r'https?://upload\.wikimedia\.org/[^)\s\]]+'
        ]
        
        for pattern in image_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                if pattern.startswith(r'\[\['):
                    # Wiki markup image
                    filename = match.group(1).strip()
                    metadata = match.group(2) if len(match.groups()) > 1 else ""
                    
                    # Enhanced metadata extraction
                    parsed_metadata = self._parse_image_metadata(metadata)
                    
                    image_links.append({
                        "type": "image",
                        "url": self._build_wikipedia_image_url(filename),
                        "filename": filename,
                        "metadata": parsed_metadata,
                        "caption": parsed_metadata.get('caption', ''),
                        "size": parsed_metadata.get('size', ''),
                        "alt_text": parsed_metadata.get('alt', ''),
                        "source": "wiki_markup",
                        "position": match.start(),
                        "is_valid": bool(filename),
                        "extraction_confidence": 0.9
                    })
                
                elif pattern.startswith(r'<img'):
                    # HTML img tag
                    src = match.group(1)
                    full_tag = match.group(0)
                    
                    # Extract additional attributes
                    alt_match = re.search(r'alt=["\']([^"\']*)["\']', full_tag)
                    title_match = re.search(r'title=["\']([^"\']*)["\']', full_tag)
                    width_match = re.search(r'width=["\']([^"\']*)["\']', full_tag)
                    height_match = re.search(r'height=["\']([^"\']*)["\']', full_tag)
                    
                    image_links.append({
                        "type": "image",
                        "url": urljoin(base_url, src) if base_url else src,
                        "filename": src.split('/')[-1],
                        "alt_text": alt_match.group(1) if alt_match else "",
                        "title": title_match.group(1) if title_match else "",
                        "width": width_match.group(1) if width_match else "",
                        "height": height_match.group(1) if height_match else "",
                        "source": "html_tag",
                        "position": match.start(),
                        "is_valid": bool(src),
                        "extraction_confidence": 0.8
                    })
                
                else:
                    # Direct Wikimedia URL
                    url = match.group(0)
                    filename = url.split('/')[-1]
                    
                    # Try to extract additional info from URL
                    size_match = re.search(r'/(\d+)px-', url)
                    size = size_match.group(1) + 'px' if size_match else ''
                    
                    image_links.append({
                        "type": "image",
                        "url": url,
                        "filename": filename,
                        "size": size,
                        "source": "direct_url",
                        "position": match.start(),
                        "is_valid": bool(url),
                        "extraction_confidence": 0.7
                    })
        
        # Remove duplicates and sort by position
        seen_urls = set()
        unique_links = []
        
        for link in image_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        return sorted(unique_links, key=lambda x: x.get('position', 0))
    
    def categorize_images_by_type(self, image_links: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize images by type and usage."""
        categories = {
            "infobox": [],
            "gallery": [],
            "inline": [],
            "thumbnail": [],
            "diagram": [],
            "map": [],
            "other": []
        }
        
        for image in image_links:
            filename = image.get('filename', '').lower()
            metadata = image.get('metadata', {})
            caption = image.get('caption', '').lower()
            
            # Categorize based on filename and metadata
            if any(keyword in filename for keyword in ['infobox', 'box']):
                categories["infobox"].append(image)
            elif any(keyword in filename for keyword in ['gallery', 'thumb']):
                categories["gallery"].append(image)
            elif any(keyword in filename for keyword in ['diagram', 'chart', 'graph']):
                categories["diagram"].append(image)
            elif any(keyword in filename for keyword in ['map', 'location']):
                categories["map"].append(image)
            elif metadata.get('size') or 'thumb' in metadata.get('class', ''):
                categories["thumbnail"].append(image)
            else:
                categories["other"].append(image)
        
        return categories
    
    def extract_image_statistics(self, image_links: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract statistics about images in the article."""
        if not image_links:
            return {
                "total_images": 0,
                "unique_sources": 0,
                "average_confidence": 0.0,
                "size_distribution": {},
                "source_distribution": {}
            }
        
        # Basic statistics
        total_images = len(image_links)
        unique_sources = len(set(img['source'] for img in image_links))
        avg_confidence = sum(img.get('extraction_confidence', 0) for img in image_links) / total_images
        
        # Size distribution
        size_distribution = {}
        for img in image_links:
            size = img.get('size', 'unknown')
            size_distribution[size] = size_distribution.get(size, 0) + 1
        
        # Source distribution
        source_distribution = {}
        for img in image_links:
            source = img.get('source', 'unknown')
            source_distribution[source] = source_distribution.get(source, 0) + 1
        
        # File type distribution
        file_types = {}
        for img in image_links:
            filename = img.get('filename', '')
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1
        
        return {
            "total_images": total_images,
            "unique_sources": unique_sources,
            "average_confidence": round(avg_confidence, 3),
            "size_distribution": size_distribution,
            "source_distribution": source_distribution,
            "file_type_distribution": file_types,
            "has_infobox_images": any(img for img in image_links if img.get('source') == 'infobox'),
            "has_gallery_images": any(img for img in image_links if 'gallery' in img.get('filename', '').lower())
        }
    
    def build_toc_hierarchy(self, toc_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build hierarchical TOC structure from flat sections."""
        if not toc_sections:
            return []
        
        # Sort by level and position
        sorted_sections = sorted(toc_sections, key=lambda x: (x.get('level', 0), x.get('position', 0)))
        
        hierarchy = []
        stack = []  # Stack to track parent sections
        
        for section in sorted_sections:
            level = section.get('level', 1)
            section['subsections'] = []
            
            # Find parent section
            while stack and stack[-1]['level'] >= level:
                stack.pop()
            
            if stack:
                # Add as subsection of parent
                parent = stack[-1]
                parent['subsections'].append(section)
                section['parent_section'] = parent.get('title')
            else:
                # Top-level section
                hierarchy.append(section)
                section['parent_section'] = None
            
            stack.append(section)
        
        return hierarchy
    
    def validate_link(self, url: str) -> Dict[str, Any]:
        """Validate a link and return validation results."""
        if not url:
            return {
                "is_valid": False,
                "errors": ["URL is empty"],
                "warnings": [],
                "url_type": "unknown"
            }
        
        errors = []
        warnings = []
        
        # Basic URL validation
        try:
            parsed_url = urlparse(url)
            
            if not parsed_url.scheme and not url.startswith('#'):
                errors.append("URL missing scheme (http/https)")
            
            if parsed_url.scheme and parsed_url.scheme not in ['http', 'https', 'ftp']:
                warnings.append(f"Unusual URL scheme: {parsed_url.scheme}")
            
        except Exception as e:
            errors.append(f"Invalid URL format: {str(e)}")
        
        # Categorize URL
        url_type = self.categorize_link(url)
        
        # Type-specific validation
        if url_type == "external":
            if len(url) > 2048:
                warnings.append("Very long URL")
            
            if url.count('&') > 10:
                warnings.append("URL has many parameters")
        
        elif url_type == "internal":
            if not url.startswith('#') and 'wikipedia.org' not in url:
                warnings.append("Internal link may be malformed")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "url_type": url_type
        }
    
    def calculate_link_relevance(self, url: str, context: str, position: int = 0) -> float:
        """Calculate relevance score for a link based on context and position."""
        if not url or not context:
            return 0.0
        
        score = 0.5  # Base score
        
        # Position-based scoring (earlier in content = more relevant)
        if position > 0:
            # Normalize position (0-1, where 0 is beginning)
            position_score = max(0, 1 - (position / len(context)))
            score += position_score * 0.2
        
        # Context-based scoring
        context_lower = context.lower()
        
        # Keywords that indicate importance
        important_keywords = [
            'main', 'primary', 'important', 'key', 'essential',
            'overview', 'introduction', 'summary', 'definition'
        ]
        
        for keyword in important_keywords:
            if keyword in context_lower:
                score += 0.1
        
        # Link type scoring
        link_type = self.categorize_link(url, context)
        if link_type == "internal":
            score += 0.2  # Internal links are more relevant
        elif link_type == "reference":
            score += 0.1  # References are somewhat relevant
        elif link_type == "external":
            score += 0.05  # External links are less relevant
        
        # URL length scoring (shorter = more relevant)
        if len(url) < 50:
            score += 0.1
        elif len(url) > 200:
            score -= 0.1
        
        return min(1.0, max(0.0, score))
    
    def _is_reference_link(self, url: str, context: str) -> bool:
        """Check if a link is a reference link."""
        reference_indicators = [
            'doi.org', 'pmc.ncbi.nlm.nih.gov', 'pubmed.ncbi.nlm.nih.gov',
            'jstor.org', 'scholar.google.com', 'arxiv.org',
            'books.google.com', 'news.google.com'
        ]
        
        return any(indicator in url.lower() for indicator in reference_indicators)
    
    def _is_image_link(self, url: str) -> bool:
        """Check if a link is an image link."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp']
        url_lower = url.lower()
        
        return any(url_lower.endswith(ext) for ext in image_extensions) or 'upload.wikimedia.org' in url_lower
    
    def _is_file_link(self, url: str) -> bool:
        """Check if a link is a file link."""
        file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        url_lower = url.lower()
        
        return any(url_lower.endswith(ext) for ext in file_extensions)
    
    def _extract_url_from_reference(self, ref_content: str) -> Optional[str]:
        """Extract URL from reference content."""
        # URL pattern
        url_pattern = r'https?://[^\s\]\)]+'
        match = re.search(url_pattern, ref_content)
        
        return match.group(0) if match else None
    
    def _extract_title_from_reference(self, ref_content: str) -> str:
        """Extract title from reference content."""
        # Remove HTML tags and clean up
        clean_content = re.sub(r'<[^>]+>', '', ref_content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        # Limit length
        if len(clean_content) > 200:
            clean_content = clean_content[:200] + '...'
        
        return clean_content
    
    def _build_wikipedia_image_url(self, filename: str) -> str:
        """Build Wikipedia image URL from filename."""
        # Encode filename for URL
        encoded_filename = filename.replace(' ', '_')
        encoded_filename = re.sub(r'[^\w\-_\.]', '', encoded_filename)
        
        # Use Wikimedia Commons URL
        return f"https://upload.wikimedia.org/wikipedia/commons/{encoded_filename}"
    
    def _parse_image_metadata(self, metadata: str) -> Dict[str, Any]:
        """Parse image metadata from wiki markup."""
        if not metadata:
            return {}
        
        parsed = {}
        parts = metadata.split('|')
        
        for part in parts:
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                parsed[key.strip()] = value.strip()
            else:
                # Likely the caption
                if 'caption' not in parsed:
                    parsed['caption'] = part
        
        return parsed
