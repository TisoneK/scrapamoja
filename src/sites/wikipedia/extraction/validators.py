"""
Wikipedia data validator.

This module provides Wikipedia-specific data validation and quality assessment
for extracted content, ensuring data integrity and consistency.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from .models import ValidationResult, QualityMetrics


class WikipediaDataValidator:
    """Wikipedia-specific data validation and quality assessment."""
    
    def __init__(self):
        """Initialize with default validation rules."""
        self.validation_rules = self._get_default_validation_rules()
        self.quality_thresholds = self._get_default_quality_thresholds()
    
    def validate_article_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate article data structure and content."""
        errors = []
        warnings = []
        
        # Validate required fields
        if not data.get('title'):
            errors.append("Article title is required")
        
        # Validate title format
        title = data.get('title', '')
        if title and len(title) > 255:
            errors.append("Article title exceeds maximum length of 255 characters")
        
        # Validate publication date
        pub_date = data.get('publication_date')
        if pub_date is not None:
            if not isinstance(pub_date, (datetime, date)):
                errors.append("Publication date must be a valid datetime or date object")
            else:
                # Check if date is reasonable (not too far in future or past)
                today = datetime.utcnow().date()
                if isinstance(pub_date, datetime):
                    pub_date = pub_date.date()
                
                if pub_date > today:
                    warnings.append("Publication date is in the future")
                elif pub_date.year < 1990:
                    warnings.append("Publication date is very old, may be incorrect")
        
        # Validate word count
        word_count = data.get('word_count')
        if word_count is not None:
            if not isinstance(word_count, int) or word_count < 0:
                errors.append("Word count must be a non-negative integer")
            elif word_count > 1000000:
                warnings.append("Word count seems unusually large")
            elif word_count < 50:
                warnings.append("Word count seems very small for a Wikipedia article")
        
        # Validate categories
        categories = data.get('categories', [])
        if not isinstance(categories, list):
            errors.append("Categories must be a list")
        elif len(categories) > 100:
            warnings.append("Number of categories exceeds recommended limit of 100")
        elif len(categories) == 0:
            warnings.append("No categories found - article may be poorly categorized")
        
        # Validate content
        content = data.get('content', '')
        if content:
            if len(content) < 100:
                warnings.append("Article content seems too short")
            elif len(content) > 1000000:  # 1MB
                warnings.append("Article content is very large")
        else:
            warnings.append("No article content found")
        
        # Validate URL
        url = data.get('url', '')
        if url:
            if not url.startswith(('http://', 'https://')):
                errors.append("URL must be a valid HTTP/HTTPS URL")
            elif 'wikipedia.org' not in url:
                warnings.append("URL does not appear to be from Wikipedia")
        else:
            errors.append("Article URL is required")
        
        # Validate last modified date
        last_modified = data.get('last_modified')
        if last_modified is not None:
            if not isinstance(last_modified, (datetime, date)):
                errors.append("Last modified date must be a valid datetime or date object")
            else:
                today = datetime.utcnow().date()
                if isinstance(last_modified, datetime):
                    last_modified = last_modified.date()
                
                if last_modified > today:
                    errors.append("Last modified date cannot be in the future")
        
        # Validate page size
        page_size = data.get('page_size')
        if page_size is not None:
            if not isinstance(page_size, int) or page_size < 0:
                errors.append("Page size must be a non-negative integer")
            elif page_size > 10000000:  # 10MB
                warnings.append("Page size seems unusually large")
        
        # Cross-validation checks
        if word_count is not None and content:
            # Check if word count is reasonable compared to content length
            estimated_words = len(content.split())
            if word_count > 0 and estimated_words > 0:
                ratio = min(word_count, estimated_words) / max(word_count, estimated_words)
                if ratio < 0.5:
                    warnings.append("Word count may not match actual content")
        
        # Calculate validation score
        score = self._calculate_validation_score(errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=score,
            validation_rules=self.validation_rules
        )
    
    def validate_infobox_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate infobox data types and formats."""
        errors = []
        warnings = []
        
        # Validate numeric fields
        numeric_fields = ['population', 'area', 'elevation']
        for field in numeric_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"{field} must be a non-negative number")
                elif isinstance(value, float) and field in ['population', 'elevation']:
                    warnings.append(f"{field} should ideally be an integer")
        
        # Validate date fields
        date_fields = ['established', 'founded', 'independence']
        for field in date_fields:
            value = data.get(field)
            if value is not None and not isinstance(value, (datetime, date)):
                errors.append(f"{field} must be a valid datetime or date object")
        
        # Validate coordinates
        coords = data.get('coordinates')
        if coords is not None:
            if not isinstance(coords, dict):
                errors.append("Coordinates must be a dictionary")
            else:
                lat = coords.get('lat')
                lon = coords.get('lon')
                if lat is not None and not (-90 <= lat <= 90):
                    errors.append("Latitude must be between -90 and 90")
                if lon is not None and not (-180 <= lon <= 180):
                    errors.append("Longitude must be between -180 and 180")
        
        # Calculate validation score
        score = self._calculate_validation_score(errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=score
        )
    
    def validate_search_results(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """Validate search results data."""
        errors = []
        warnings = []
        
        if not isinstance(data, list):
            errors.append("Search results must be a list")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                score=0.0
            )
        
        # Validate each search result
        for i, result in enumerate(data):
            if not isinstance(result, dict):
                errors.append(f"Search result {i} must be a dictionary")
                continue
            
            # Validate title
            title = result.get('title')
            if not title:
                errors.append(f"Search result {i} missing required title")
            elif not isinstance(title, str):
                errors.append(f"Search result {i} title must be a string")
            elif len(title) > 255:
                warnings.append(f"Search result {i} title exceeds maximum length")
            elif len(title.strip()) < 3:
                warnings.append(f"Search result {i} title seems too short")
            
            # Validate URL
            url = result.get('url')
            if not url:
                errors.append(f"Search result {i} missing required URL")
            elif not isinstance(url, str):
                errors.append(f"Search result {i} URL must be a string")
            elif not url.startswith(('http://', 'https://')):
                errors.append(f"Search result {i} URL must be a valid HTTP/HTTPS URL")
            elif 'wikipedia.org' not in url:
                warnings.append(f"Search result {i} URL does not appear to be from Wikipedia")
            
            # Validate relevance score
            relevance = result.get('relevance_score')
            if relevance is not None:
                if not isinstance(relevance, (int, float)):
                    errors.append(f"Search result {i} relevance score must be numeric")
                elif not (0.0 <= relevance <= 1.0):
                    errors.append(f"Search result {i} relevance score must be between 0.0 and 1.0")
                elif relevance < 0.1:
                    warnings.append(f"Search result {i} has very low relevance score")
            
            # Validate article size
            size = result.get('article_size')
            if size is not None:
                if not isinstance(size, int) or size < 0:
                    errors.append(f"Search result {i} article size must be a non-negative integer")
                elif size > 1000000:
                    warnings.append(f"Search result {i} article size seems unusually large")
                elif size < 100:
                    warnings.append(f"Search result {i} article size seems very small")
            
            # Validate last modified date
            last_modified = result.get('last_modified')
            if last_modified is not None:
                if not isinstance(last_modified, (datetime, date, str)):
                    errors.append(f"Search result {i} last modified date must be a valid date")
                elif isinstance(last_modified, str):
                    try:
                        # Try to parse the date string
                        from dateutil import parser
                        parser.parse(last_modified)
                    except:
                        errors.append(f"Search result {i} last modified date string is invalid")
                else:
                    today = datetime.utcnow().date()
                    if isinstance(last_modified, datetime):
                        last_modified = last_modified.date()
                    
                    if last_modified > today:
                        errors.append(f"Search result {i} last modified date cannot be in the future")
            
            # Validate description/snippet
            description = result.get('description') or result.get('snippet')
            if description:
                if not isinstance(description, str):
                    errors.append(f"Search result {i} description must be a string")
                elif len(description) > 1000:
                    warnings.append(f"Search result {i} description is very long")
                elif len(description.strip()) < 10:
                    warnings.append(f"Search result {i} description seems too short")
            else:
                warnings.append(f"Search result {i} has no description or snippet")
            
            # Validate page ID
            pageid = result.get('pageid')
            if pageid is not None:
                if not isinstance(pageid, int) or pageid <= 0:
                    errors.append(f"Search result {i} page ID must be a positive integer")
            
            # Validate category
            category = result.get('category')
            if category is not None:
                if not isinstance(category, str):
                    errors.append(f"Search result {i} category must be a string")
                elif len(category) > 100:
                    warnings.append(f"Search result {i} category seems too long")
        
        # Cross-validation checks
        if len(data) > 0:
            # Check for duplicate URLs
            urls = [result.get('url') for result in data if result.get('url')]
            if len(urls) != len(set(urls)):
                warnings.append("Duplicate URLs found in search results")
            
            # Check for duplicate titles
            titles = [result.get('title') for result in data if result.get('title')]
            if len(titles) != len(set(titles)):
                warnings.append("Duplicate titles found in search results")
            
            # Check relevance score distribution
            relevance_scores = [result.get('relevance_score') for result in data if result.get('relevance_score') is not None]
            if relevance_scores:
                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                if avg_relevance < 0.3:
                    warnings.append("Average relevance score seems low")
                elif avg_relevance > 0.9:
                    warnings.append("Average relevance score seems unusually high")
        
        # Calculate validation score
        score = self._calculate_validation_score(errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=score,
            validation_rules=self.validation_rules
        )
    
    def assess_data_quality(self, data: Dict[str, Any]) -> QualityMetrics:
        """Assess overall data quality."""
        issues = []
        warnings = []
        recommendations = []
        
        # Assess completeness
        expected_fields = ['title', 'content', 'url']
        missing_fields = [field for field in expected_fields if not data.get(field)]
        completeness = 1.0 - (len(missing_fields) / len(expected_fields))
        
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
            recommendations.append(f"Ensure all required fields are present: {', '.join(expected_fields)}")
        
        # Assess accuracy based on validation
        validation_result = self.validate_article_data(data)
        accuracy = validation_result.score
        
        # Assess consistency
        consistency = self._assess_data_consistency(data)
        
        # Assess content quality
        content = data.get('content', '')
        if content:
            if len(content) < 100:
                issues.append("Article content is very short")
                recommendations.append("Consider adding more comprehensive content")
            elif len(content) > 100000:
                warnings.append("Article content is very long")
        
        # Assess metadata quality
        categories = data.get('categories', [])
        if not categories:
            warnings.append("No categories found")
            recommendations.append("Add relevant categories to improve discoverability")
        
        # Calculate overall quality score
        score = (completeness + accuracy + consistency) / 3.0
        
        return QualityMetrics(
            score=score,
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def set_validation_rules(self, rules: Dict[str, Dict[str, Any]]) -> None:
        """Set custom validation rules."""
        self.validation_rules.update(rules)
    
    def set_quality_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set custom quality thresholds."""
        self.quality_thresholds.update(thresholds)
    
    def _get_default_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get default validation rules."""
        return {
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
    
    def _get_default_quality_thresholds(self) -> Dict[str, float]:
        """Get default quality thresholds."""
        return {
            "min_score": 0.7,
            "min_completeness": 0.8,
            "min_accuracy": 0.8,
            "min_consistency": 0.7
        }
    
    def _calculate_validation_score(self, errors: List[str], warnings: List[str]) -> float:
        """Calculate validation score based on errors and warnings."""
        # Start with perfect score
        score = 1.0
        
        # Deduct for errors (more severe)
        error_penalty = 0.2 * len(errors)
        score -= error_penalty
        
        # Deduct for warnings (less severe)
        warning_penalty = 0.05 * len(warnings)
        score -= warning_penalty
        
        # Ensure score doesn't go below 0
        return max(0.0, score)
    
    def _assess_data_consistency(self, data: Dict[str, Any]) -> float:
        """Assess data consistency across different fields."""
        consistency_score = 1.0
        
        # Check for logical consistency between related fields
        word_count = data.get('word_count')
        content = data.get('content', '')
        
        if word_count is not None and content:
            # Estimate word count from content and compare
            estimated_words = len(content.split())
            if word_count > 0:
                ratio = min(word_count, estimated_words) / max(word_count, estimated_words)
                consistency_score = max(0.0, ratio)
        
        # Check for consistency in metadata
        categories = data.get('categories', [])
        infobox = data.get('infobox', {})
        
        if categories and infobox:
            # If there are categories but no infobox, that might be inconsistent
            if not infobox:
                consistency_score *= 0.9
        
        return consistency_score
