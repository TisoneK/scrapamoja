"""
GitHub extraction rules using the existing extractor module.

This module defines extraction rules for GitHub-specific data elements,
leveraging the existing Scorewise extractor module for data transformation
and validation.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal

from src.extractor import ExtractionRule, ExtractionType, DataType, TransformationType


logger = logging.getLogger(__name__)


class GitHubExtractionRules:
    """
    GitHub-specific extraction rules.
    
    This class provides extraction rules for GitHub data elements,
    including repositories, users, issues, and search results.
    """
    
    def __init__(self):
        """Initialize GitHub extraction rules."""
        self.field_mappings = {}
        self.rule_configs = {}
        self.extraction_cache = {}
        
        # Initialize extraction rules
        self._initialize_repository_rules()
        self._initialize_user_rules()
        self._initialize_issue_rules()
        self._initialize_search_rules()
        
        logger.info("GitHubExtractionRules initialized")
    
    def _initialize_repository_rules(self) -> None:
        """Initialize repository extraction rules."""
        self.rule_configs["repository"] = {
            "name": ExtractionRule(
                selector="repository_title",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=True,
                default_value=""
            ),
            "description": ExtractionRule(
                selector="repository_description",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN,
                    TransformationType.NORMALIZE
                ],
                required=False,
                default_value=""
            ),
            "stars": ExtractionRule(
                selector="repository_stats",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-stars",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=0
            ),
            "forks": ExtractionRule(
                selector="repository_stats",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-forks",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=0
            ),
            "issues": ExtractionRule(
                selector="repository_stats",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-issues",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=0
            ),
            "language": ExtractionRule(
                selector="repository_stats",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN,
                    TransformationType.NORMALIZE
                ],
                required=False,
                default_value=""
            ),
            "url": ExtractionRule(
                selector="repository_title",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="href",
                transformations=[
                    TransformationType.URL_NORMALIZE
                ],
                required=True,
                default_value=""
            ),
            "updated_at": ExtractionRule(
                selector="repository_stats",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.DATETIME,
                attribute_name="data-updated-at",
                transformations=[
                    TransformationType.DATE_PARSE
                ],
                required=False,
                default_value=None
            )
        }
    
    def _initialize_user_rules(self) -> None:
        """Initialize user extraction rules."""
        self.rule_configs["user"] = {
            "username": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN,
                    TransformationType.NORMALIZE
                ],
                required=True,
                default_value=""
            ),
            "name": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=""
            ),
            "bio": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN,
                    TransformationType.NORMALIZE
                ],
                required=False,
                default_value=""
            ),
            "followers": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-followers",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=0
            ),
            "following": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-following",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=0
            ),
            "location": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=""
            ),
            "url": ExtractionRule(
                selector="user_profile",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="href",
                transformations=[
                    TransformationType.URL_NORMALIZE
                ],
                required=True,
                default_value=""
            )
        }
    
    def _initialize_issue_rules(self) -> None:
        """Initialize issue extraction rules."""
        self.rule_configs["issue"] = {
            "title": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=True,
                default_value=""
            ),
            "number": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-issue-number",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=True,
                default_value=0
            ),
            "state": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="data-state",
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.NORMALIZE
                ],
                required=True,
                default_value="open"
            ),
            "author": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.TEXT,
                data_type=DataType.STRING,
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=""
            ),
            "created_at": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.DATETIME,
                attribute_name="data-created-at",
                transformations=[
                    TransformationType.DATE_PARSE
                ],
                required=False,
                default_value=None
            ),
            "updated_at": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.DATETIME,
                attribute_name="data-updated-at",
                transformations=[
                    TransformationType.DATE_PARSE
                ],
                required=False,
                default_value=None
            ),
            "url": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="href",
                transformations=[
                    TransformationType.URL_NORMALIZE
                ],
                required=True,
                default_value=""
            ),
            "labels": ExtractionRule(
                selector="issue_list_item",
                extraction_type=ExtractionType.LIST,
                data_type=DataType.STRING,
                list_selector=".issue-label",
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=[]
            )
        }
    
    def _initialize_search_rules(self) -> None:
        """Initialize search extraction rules."""
        self.rule_configs["search"] = {
            "query": ExtractionRule(
                selector="search_input",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="value",
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=""
            ),
            "total_results": ExtractionRule(
                selector="search_results",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.INTEGER,
                attribute_name="data-total-results",
                transformations=[
                    TransformationType.NUMBER_EXTRACT,
                    TransformationType.CLEAN
                ],
                required=False,
                default_value=0
            ),
            "search_type": ExtractionRule(
                selector="search_results",
                extraction_type=ExtractionType.ATTRIBUTE,
                data_type=DataType.STRING,
                attribute_name="data-search-type",
                transformations=[
                    TransformationType.TRIM,
                    TransformationType.NORMALIZE
                ],
                required=False,
                default_value="repositories"
            )
        }
    
    async def extract_repository_data(self, element: Any) -> Dict[str, Any]:
        """
        Extract repository data from an element.
        
        Args:
            element: DOM element to extract data from
            
        Returns:
            Dict[str, Any]: Extracted repository data
        """
        try:
            logger.debug("Extracting repository data")
            
            # Get repository extraction rules
            rules = self.rule_configs.get("repository", {})
            
            # Extract data using existing extractor module
            extracted_data = {}
            
            for field_name, rule in rules.items():
                try:
                    # Use the extractor module to extract data
                    from src.extractor import Extractor
                    extractor = Extractor()
                    
                    # Extract the data
                    value = await extractor.extract(element, rule)
                    
                    # Apply field mapping if available
                    mapped_field = self.field_mappings.get("repository", {}).get(field_name, field_name)
                    extracted_data[mapped_field] = value
                    
                except Exception as e:
                    logger.warning(f"Failed to extract repository field {field_name}: {e}")
                    # Use default value
                    mapped_field = self.field_mappings.get("repository", {}).get(field_name, field_name)
                    extracted_data[mapped_field] = rule.default_value
            
            # Add metadata
            extracted_data["extracted_at"] = datetime.now().isoformat()
            extracted_data["extraction_type"] = "repository"
            
            logger.debug(f"Repository data extracted: {len(extracted_data)} fields")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to extract repository data: {e}")
            return {
                "error": str(e),
                "extracted_at": datetime.now().isoformat(),
                "extraction_type": "repository"
            }
    
    async def extract_repository_details(self, element: Any) -> Dict[str, Any]:
        """
        Extract detailed repository information.
        
        Args:
            element: DOM element to extract data from
            
        Returns:
            Dict[str, Any]: Extracted repository details
        """
        try:
            logger.debug("Extracting repository details")
            
            # Use repository extraction rules
            data = await self.extract_repository_data(element)
            
            # Add additional detail extraction
            additional_details = await self._extract_additional_repository_details(element)
            data.update(additional_details)
            
            logger.debug(f"Repository details extracted: {len(data)} fields")
            return data
            
        except Exception as e:
            logger.error(f"Failed to extract repository details: {e}")
            return {
                "error": str(e),
                "extracted_at": datetime.now().isoformat(),
                "extraction_type": "repository_details"
            }
    
    async def extract_user_profile(self, element: Any) -> Dict[str, Any]:
        """
        Extract user profile data from an element.
        
        Args:
            element: DOM element to extract data from
            
        Returns:
            Dict[str, Any]: Extracted user profile data
        """
        try:
            logger.debug("Extracting user profile data")
            
            # Get user extraction rules
            rules = self.rule_configs.get("user", {})
            
            # Extract data using existing extractor module
            extracted_data = {}
            
            for field_name, rule in rules.items():
                try:
                    # Use the extractor module to extract data
                    from src.extractor import Extractor
                    extractor = Extractor()
                    
                    # Extract the data
                    value = await extractor.extract(element, rule)
                    
                    # Apply field mapping
                    mapped_field = self.field_mappings.get("user", {}).get(field_name, field_name)
                    extracted_data[mapped_field] = value
                    
                except Exception as e:
                    logger.warning(f"Failed to extract user field {field_name}: {e}")
                    # Use default value
                    mapped_field = self.field_mappings.get("user", {}).get(field_name, field_name)
                    extracted_data[mapped_field] = rule.default_value
            
            # Add metadata
            extracted_data["extracted_at"] = datetime.now().isoformat()
            extracted_data["extraction_type"] = "user_profile"
            
            logger.debug(f"User profile data extracted: {len(extracted_data)} fields")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to extract user profile data: {e}")
            return {
                "error": str(e),
                "extracted_at": datetime.now().isoformat(),
                "extraction_type": "user_profile"
            }
    
    async def extract_issue_data(self, element: Any) -> Dict[str, Any]:
        """
        Extract issue data from an element.
        
        Args:
            element: DOM element to extract data from
            
        Returns:
            Dict[str, Any]: Extracted issue data
        """
        try:
            logger.debug("Extracting issue data")
            
            # Get issue extraction rules
            rules = self.rule_configs.get("issue", {})
            
            # Extract data using existing extractor module
            extracted_data = {}
            
            for field_name, rule in rules.items():
                try:
                    # Use the extractor module to extract data
                    from src.extractor import Extractor
                    extractor = Extractor()
                    
                    # Extract the data
                    value = await extractor.extract(element, rule)
                    
                    # Apply field mapping
                    mapped_field = self.field_mappings.get("issue", {}).get(field_name, field_name)
                    extracted_data[mapped_field] = value
                    
                except Exception as e:
                    logger.warning(f"Failed to extract issue field {field_name}: {e}")
                    # Use default value
                    mapped_field = self.field_mappings.get("issue", {}).get(field_name, field_name)
                    extracted_data[mapped_field] = rule.default_value
            
            # Add metadata
            extracted_data["extracted_at"] = datetime.now().isoformat()
            extracted_data["extraction_type"] = "issue"
            
            logger.debug(f"Issue data extracted: {len(extracted_data)} fields")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to extract issue data: {e}")
            return {
                "error": str(e),
                "extracted_at": datetime.now().isoformat(),
                "extraction_type": "issue"
            }
    
    async def _extract_additional_repository_details(self, element: Any) -> Dict[str, Any]:
        """
        Extract additional repository details not covered by standard rules.
        
        Args:
            element: DOM element to extract data from
            
        Returns:
            Dict[str, Any]: Additional repository details
        """
        additional_data = {}
        
        try:
            # Extract license information
            license_info = await self._extract_license_info(element)
            if license_info:
                additional_data["license"] = license_info
            
            # Extract topics/tags
            topics = await self._extract_repository_topics(element)
            if topics:
                additional_data["topics"] = topics
            
            # Extract contributor count
            contributors = await self._extract_contributor_count(element)
            if contributors:
                additional_data["contributors"] = contributors
            
        except Exception as e:
            logger.warning(f"Failed to extract additional repository details: {e}")
        
        return additional_data
    
    async def _extract_license_info(self, element: Any) -> Optional[str]:
        """Extract license information."""
        try:
            # Look for license information
            license_selectors = [
                "[data-testid='license']",
                ".license",
                "span[itemprop='license']"
            ]
            
            for selector in license_selectors:
                try:
                    license_element = await element.query_selector(selector)
                    if license_element:
                        license_text = await license_element.text_content()
                        if license_text and license_text.strip():
                            return license_text.strip()
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract license info: {e}")
            return None
    
    async def _extract_repository_topics(self, element: Any) -> List[str]:
        """Extract repository topics/tags."""
        try:
            topics = []
            
            # Look for topic elements
            topic_selectors = [
                ".topic-tag",
                "[data-testid='topic']",
                "a[href*='/topics/']"
            ]
            
            for selector in topic_selectors:
                try:
                    topic_elements = await element.query_selector_all(selector)
                    for topic_element in topic_elements:
                        topic_text = await topic_element.text_content()
                        if topic_text and topic_text.strip():
                            topics.append(topic_text.strip())
                except:
                    continue
            
            return topics[:10]  # Limit to first 10 topics
            
        except Exception as e:
            logger.debug(f"Failed to extract repository topics: {e}")
            return []
    
    async def _extract_contributor_count(self, element: Any) -> Optional[int]:
        """Extract contributor count."""
        try:
            # Look for contributor count
            contributor_selectors = [
                "[data-testid='contributors']",
                ".contributors",
                "a[href*='/contributors']"
            ]
            
            for selector in contributor_selectors:
                try:
                    contributor_element = await element.query_selector(selector)
                    if contributor_element:
                        contributor_text = await contributor_element.text_content()
                        if contributor_text:
                            # Extract number from text like "123 contributors"
                            match = re.search(r'(\d+[,\d]*)', contributor_text)
                            if match:
                                return int(match.group(1).replace(',', ''))
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract contributor count: {e}")
            return None
    
    def get_all_rule_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all extraction rule configurations.
        
        Returns:
            Dict[str, Dict[str, Any]]: All rule configurations
        """
        return self.rule_configs.copy()
    
    def get_rule_config(self, entity_type: str) -> Dict[str, Any]:
        """
        Get extraction rule configuration for a specific entity type.
        
        Args:
            entity_type: Type of entity (repository, user, issue, search)
            
        Returns:
            Dict[str, Any]: Rule configuration
        """
        return self.rule_configs.get(entity_type, {})
    
    def set_field_mappings(self, mappings: Dict[str, Dict[str, str]]) -> None:
        """
        Set field mappings for extraction results.
        
        Args:
            mappings: Field mappings dictionary
        """
        self.field_mappings.update(mappings)
    
    async def setup_rule_set(self, rule_set_name: str, config: Dict[str, Any]) -> bool:
        """
        Setup a rule set from configuration.
        
        Args:
            rule_set_name: Name of the rule set
            config: Rule set configuration
            
        Returns:
            bool: True if setup successful
        """
        try:
            # Convert configuration to ExtractionRule objects
            rules = {}
            
            for field_name, rule_config in config.items():
                try:
                    rule = ExtractionRule(
                        selector=rule_config.get("selector", ""),
                        extraction_type=ExtractionType(rule_config.get("extraction_type", "TEXT")),
                        data_type=DataType(rule_config.get("data_type", "STRING")),
                        transformations=[
                            TransformationType(t) for t in rule_config.get("transformations", [])
                        ],
                        required=rule_config.get("required", False),
                        default_value=rule_config.get("default_value", None),
                        attribute_name=rule_config.get("attribute_name"),
                        list_selector=rule_config.get("list_selector")
                    )
                    rules[field_name] = rule
                    
                except Exception as e:
                    logger.error(f"Failed to create rule for {field_name}: {e}")
                    return False
            
            # Store the rule set
            self.rule_configs[rule_set_name] = rules
            
            logger.info(f"Successfully setup rule set: {rule_set_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup rule set {rule_set_name}: {e}")
            return False
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        Get summary of available extraction rules.
        
        Returns:
            Dict[str, Any]: Extraction summary
        """
        summary = {
            "total_rule_sets": len(self.rule_configs),
            "rule_sets": {},
            "total_rules": 0
        }
        
        for entity_type, rules in self.rule_configs.items():
            rule_count = len(rules)
            summary["rule_sets"][entity_type] = {
                "rule_count": rule_count,
                "required_fields": sum(1 for rule in rules.values() if rule.required),
                "optional_fields": sum(1 for rule in rules.values() if not rule.required)
            }
            summary["total_rules"] += rule_count
        
        return summary
