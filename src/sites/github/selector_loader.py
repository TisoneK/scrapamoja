"""
GitHub selector loader for loading YAML selectors into the existing selector engine.

This module implements the GitHub-specific selector loading functionality,
extending the base selector loader with GitHub-specific patterns and configurations.
"""

import asyncio
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from src.sites.base.template.selector_loader import FileSystemSelectorLoader, SelectorLoadStatus


logger = logging.getLogger(__name__)


class GitHubSelectorLoader(FileSystemSelectorLoader):
    """
    GitHub-specific selector loader.
    
    This loader handles GitHub-specific YAML selector configurations,
    including repository selectors, user profile selectors, and issue selectors.
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        selectors_directory: Union[str, Path],
        **kwargs
    ):
        """
        Initialize GitHub selector loader.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            selectors_directory: Directory containing GitHub YAML selectors
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            selector_engine=selector_engine,
            selectors_directory=selectors_directory,
            **kwargs
        )
        
        # GitHub-specific configuration
        self.github_selector_patterns = self._load_github_selector_patterns()
        self.github_selector_validators = self._load_github_selector_validators()
        
        # Selector categories
        self.selector_categories = {
            "repository": ["repository_list", "repository_details", "repository_stats"],
            "user": ["user_profile", "user_stats", "user_repositories"],
            "search": ["search_input", "search_results", "search_filters"],
            "issues": ["issue_list", "issue_details", "issue_comments"],
            "navigation": ["main_menu", "breadcrumb", "pagination"]
        }
        
        logger.info(f"GitHubSelectorLoader initialized for {template_name}")
    
    def _load_github_selector_patterns(self) -> Dict[str, Any]:
        """Load GitHub-specific selector patterns."""
        return {
            "repository": {
                "title": ["h1", ".repository-title", "[data-testid='repository-title']"],
                "description": ["p.repository-description", ".repository-description", "[data-testid='repository-description']"],
                "stats": ["ul.repository-stats", ".repository-stats", "[data-testid='repository-stats']"],
                "language": ["span[itemprop='programmingLanguage']", ".language-color", "[data-testid='language']"],
                "stars": ["a[href$='/stargazers']", ".stargazers", "[data-testid='stargazers']"],
                "forks": ["a[href$='/forks']", ".forks", "[data-testid='forks']"],
                "issues": ["a[href$='/issues']", ".issues", "[data-testid='issues']"]
            },
            "user": {
                "name": ["span[itemprop='name']", ".profile-name", "[data-testid='profile-name']"],
                "username": ["span[itemprop='additionalName']", ".profile-username", "[data-testid='profile-username']"],
                "bio": ["div[itemprop='description']", ".profile-bio", "[data-testid='profile-bio']"],
                "followers": ["a[href$='/followers']", ".followers", "[data-testid='followers']"],
                "following": ["a[href$='/following']", ".following", "[data-testid='following']"],
                "location": ["span[itemprop='homeLocation']", ".profile-location", "[data-testid='profile-location']"]
            },
            "search": {
                "input": ["input[name='q']", "#search-form input", "[data-testid='search-input']"],
                "results": ["[data-testid='results-list']", ".search-results", ".repo-list"],
                "filters": ["[data-testid='search-filters']", ".search-filters", ".filters"]
            },
            "issues": {
                "title": ["a.issue-title", ".issue-title", "[data-testid='issue-title']"],
                "body": ["div.issue-body", ".issue-body", "[data-testid='issue-body']"],
                "state": ["span.issue-state", ".issue-state", "[data-testid='issue-state']"],
                "author": ["a.author", ".issue-author", "[data-testid='issue-author']"],
                "labels": ["a.issue-label", ".issue-labels", "[data-testid='issue-labels']"]
            }
        }
    
    def _load_github_selector_validators(self) -> Dict[str, Any]:
        """Load GitHub-specific selector validation rules."""
        return {
            "required_attributes": {
                "repository": ["href", "title"],
                "user": ["href"],
                "search": ["name", "placeholder"],
                "issues": ["href"]
            },
            "text_patterns": {
                "repository": {
                    "stars": r"^\d+[,\d]*\s*stars?$",
                    "forks": r"^\d+[,\d]*\s*forks?$",
                    "issues": r"^\d+[,\d]*\s*issues?$"
                },
                "user": {
                    "followers": r"^\d+[,\d]*\s*followers?$",
                    "following": r"^\d+[,\d]*\s*following?$"
                }
            },
            "url_patterns": {
                "repository": r"github\.com/[^/]+/[^/]+",
                "user": r"github\.com/[^/]+$",
                "issues": r"github\.com/[^/]+/[^/]+/issues/\d+"
            }
        }
    
    async def validate_selector_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate selector configuration with GitHub-specific rules.
        
        Args:
            config: Selector configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        # First perform base validation
        if not await super().validate_selector_config(config):
            return False
        
        # GitHub-specific validation
        try:
            selector_name = config.get("name", "")
            selector_type = config.get("selector_type", "semantic")
            strategies = config.get("strategies", [])
            
            # Validate GitHub selector naming conventions
            if not self._validate_github_selector_name(selector_name):
                logger.warning(f"Invalid GitHub selector name: {selector_name}")
                return False
            
            # Validate strategies for GitHub
            if not await self._validate_github_strategies(strategies, selector_name):
                logger.warning(f"Invalid strategies for GitHub selector: {selector_name}")
                return False
            
            # Validate GitHub-specific attributes
            if not self._validate_github_attributes(config):
                logger.warning(f"Invalid GitHub attributes for selector: {selector_name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating GitHub selector config: {e}")
            return False
    
    def _validate_github_selector_name(self, selector_name: str) -> bool:
        """
        Validate GitHub selector naming conventions.
        
        Args:
            selector_name: Selector name to validate
            
        Returns:
            bool: True if name is valid
        """
        # Check if selector name follows GitHub conventions
        github_prefixes = ["repo_", "user_", "search_", "issue_", "nav_"]
        
        # Should start with a GitHub prefix or be a common selector
        has_valid_prefix = any(selector_name.startswith(prefix) for prefix in github_prefixes)
        is_common_selector = selector_name in ["main_content", "navigation", "footer", "header"]
        
        return has_valid_prefix or is_common_selector
    
    async def _validate_github_strategies(self, strategies: List[Dict[str, Any]], selector_name: str) -> bool:
        """
        Validate strategies for GitHub selectors.
        
        Args:
            strategies: List of strategies to validate
            selector_name: Name of the selector
            
        Returns:
            bool: True if strategies are valid
        """
        try:
            for i, strategy in enumerate(strategies):
                strategy_type = strategy.get("type", "")
                selector = strategy.get("selector", "")
                weight = strategy.get("weight", 0.0)
                
                # Validate strategy type
                valid_types = ["semantic", "attribute", "text_anchor", "dom_relationship", "role_based"]
                if strategy_type not in valid_types:
                    logger.warning(f"Invalid strategy type: {strategy_type}")
                    return False
                
                # Validate weight
                if not 0.0 <= weight <= 1.0:
                    logger.warning(f"Invalid strategy weight: {weight}")
                    return False
                
                # GitHub-specific selector validation
                if not self._validate_github_strategy_selector(selector, strategy_type, selector_name):
                    logger.warning(f"Invalid GitHub selector: {selector}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating GitHub strategies: {e}")
            return False
    
    def _validate_github_strategy_selector(self, selector: str, strategy_type: str, selector_name: str) -> bool:
        """
        Validate individual GitHub strategy selector.
        
        Args:
            selector: CSS selector string
            strategy_type: Type of strategy
            selector_name: Name of the selector
            
        Returns:
            bool: True if selector is valid
        """
        if not selector:
            return False
        
        # Check for common GitHub selectors
        if any(pattern in selector for pattern in ["github.com", "data-testid", "itemprop"]):
            return True
        
        # Check for semantic selectors
        if strategy_type == "semantic":
            semantic_patterns = ["h1", "h2", "h3", "nav", "main", "article", "section"]
            return any(pattern in selector for pattern in semantic_patterns)
        
        # Check for attribute selectors
        if strategy_type == "attribute":
            return "[" in selector and "]" in selector
        
        # Basic validation for other types
        return len(selector) > 0 and not selector.isspace()
    
    def _validate_github_attributes(self, config: Dict[str, Any]) -> bool:
        """
        Validate GitHub-specific attributes in selector configuration.
        
        Args:
            config: Selector configuration
            
        Returns:
            bool: True if attributes are valid
        """
        try:
            # Check for GitHub-specific attributes
            github_attributes = ["github_element", "data-testid", "itemprop", "data-repository-hovercards-enabled"]
            
            strategies = config.get("strategies", [])
            for strategy in strategies:
                selector = strategy.get("selector", "")
                
                # Check for GitHub attributes in selector
                has_github_attribute = any(attr in selector for attr in github_attributes)
                
                # If it's a GitHub selector, it should have GitHub attributes
                selector_name = config.get("name", "")
                if any(selector_name.startswith(prefix) for prefix in ["repo_", "user_", "search_", "issue_"]):
                    if not has_github_attribute:
                        logger.warning(f"GitHub selector {selector_name} should use GitHub attributes")
                        # Not a failure, just a warning
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating GitHub attributes: {e}")
            return False
    
    async def load_github_selectors_by_category(self, category: str) -> List[str]:
        """
        Load selectors by GitHub category.
        
        Args:
            category: Category of selectors to load
            
        Returns:
            List[str]: List of loaded selector names
        """
        try:
            if category not in self.selector_categories:
                logger.error(f"Unknown GitHub selector category: {category}")
                return []
            
            selector_names = self.selector_categories[category]
            loaded_selectors = []
            
            for selector_name in selector_names:
                try:
                    # Load individual selector
                    config = await self._load_selector_config_from_file(selector_name)
                    if config and await self.register_selector(selector_name, config):
                        loaded_selectors.append(selector_name)
                        logger.debug(f"Loaded GitHub selector: {selector_name}")
                    else:
                        logger.warning(f"Failed to load GitHub selector: {selector_name}")
                        
                except Exception as e:
                    logger.error(f"Error loading GitHub selector {selector_name}: {e}")
            
            logger.info(f"Loaded {len(loaded_selectors)} selectors for category: {category}")
            return loaded_selectors
            
        except Exception as e:
            logger.error(f"Failed to load GitHub selectors by category {category}: {e}")
            return []
    
    async def _load_selector_config_from_file(self, selector_name: str) -> Optional[Dict[str, Any]]:
        """
        Load selector configuration from YAML file with GitHub-specific handling.
        
        Args:
            selector_name: Name of the selector
            
        Returns:
            Optional[Dict[str, Any]]: Selector configuration
        """
        try:
            # Try to load from GitHub selectors directory
            yaml_file = Path(self.selectors_directory) / f"{selector_name}.yaml"
            if not yaml_file.exists():
                yaml_file = Path(self.selectors_directory) / f"{selector_name}.yml"
            
            if not yaml_file.exists():
                # Try to generate default configuration for common GitHub selectors
                return self._generate_default_github_selector_config(selector_name)
            
            # Load YAML configuration
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Enhance with GitHub-specific defaults
            config = self._enhance_github_selector_config(config, selector_name)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load GitHub selector config for {selector_name}: {e}")
            return None
    
    def _generate_default_github_selector_config(self, selector_name: str) -> Optional[Dict[str, Any]]:
        """
        Generate default configuration for common GitHub selectors.
        
        Args:
            selector_name: Name of the selector
            
        Returns:
            Optional[Dict[str, Any]]: Default configuration
        """
        try:
            # Check if we have default patterns for this selector
            for category, patterns in self.github_selector_patterns.items():
                if selector_name in patterns:
                    return self._create_config_from_patterns(selector_name, patterns[selector_name])
            
            # Generate basic configuration for unknown selectors
            return {
                "name": selector_name,
                "description": f"GitHub selector for {selector_name}",
                "selector_type": "semantic",
                "confidence_threshold": 0.7,
                "strategies": [
                    {
                        "type": "attribute",
                        "selector": f"[data-testid='{selector_name}']",
                        "weight": 0.8
                    },
                    {
                        "type": "semantic",
                        "selector": f".{selector_name}",
                        "weight": 0.6
                    }
                ],
                "validation_rules": [
                    {
                        "type": "existence",
                        "required": True
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate default config for {selector_name}: {e}")
            return None
    
    def _create_config_from_patterns(self, selector_name: str, patterns: List[str]) -> Dict[str, Any]:
        """
        Create selector configuration from pattern list.
        
        Args:
            selector_name: Name of the selector
            patterns: List of CSS selector patterns
            
        Returns:
            Dict[str, Any]: Selector configuration
        """
        strategies = []
        
        for i, pattern in enumerate(patterns):
            weight = 0.8 - (i * 0.1)  # Decreasing weights
            
            # Determine strategy type based on pattern
            if "data-testid" in pattern:
                strategy_type = "attribute"
            elif "[" in pattern and "]" in pattern:
                strategy_type = "attribute"
            elif any(tag in pattern for tag in ["h1", "h2", "h3", "nav", "main"]):
                strategy_type = "semantic"
            else:
                strategy_type = "attribute"
            
            strategies.append({
                "type": strategy_type,
                "selector": pattern,
                "weight": max(weight, 0.1)
            })
        
        return {
            "name": selector_name,
            "description": f"GitHub selector for {selector_name}",
            "selector_type": "hybrid",
            "confidence_threshold": 0.7,
            "strategies": strategies,
            "validation_rules": [
                {
                    "type": "existence",
                    "required": True
                }
            ]
        }
    
    def _enhance_github_selector_config(self, config: Dict[str, Any], selector_name: str) -> Dict[str, Any]:
        """
        Enhance selector configuration with GitHub-specific defaults.
        
        Args:
            config: Original configuration
            selector_name: Name of the selector
            
        Returns:
            Dict[str, Any]: Enhanced configuration
        """
        # Ensure name is set
        config["name"] = selector_name
        
        # Set default confidence threshold if not provided
        if "confidence_threshold" not in config:
            config["confidence_threshold"] = 0.7
        
        # Set default selector type if not provided
        if "selector_type" not in config:
            config["selector_type"] = "hybrid"
        
        # Add GitHub-specific validation rules if not provided
        if "validation_rules" not in config:
            config["validation_rules"] = [
                {
                    "type": "existence",
                    "required": True
                }
            ]
        
        # Add GitHub-specific metadata
        config["github_specific"] = True
        config["template_name"] = self.template_name
        config["created_at"] = datetime.now().isoformat()
        
        return config
    
    def get_github_selector_categories(self) -> Dict[str, List[str]]:
        """
        Get available GitHub selector categories.
        
        Returns:
            Dict[str, List[str]]: Categories and their selectors
        """
        return self.selector_categories.copy()
    
    def get_loaded_github_selectors_by_category(self) -> Dict[str, List[str]]:
        """
        Get loaded selectors grouped by category.
        
        Returns:
            Dict[str, List[str]]: Categories and their loaded selectors
        """
        loaded_by_category = {}
        loaded_selectors = set(self.get_loaded_selectors())
        
        for category, selector_names in self.selector_categories.items():
            loaded_in_category = [name for name in selector_names if name in loaded_selectors]
            loaded_by_category[category] = loaded_in_category
        
        return loaded_by_category
    
    async def validate_github_selector_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of loaded GitHub selectors.
        
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            validation_results = {
                "total_selectors": len(self.get_loaded_selectors()),
                "categories_covered": 0,
                "missing_selectors": [],
                "invalid_selectors": [],
                "overall_integrity": 0.0
            }
            
            loaded_selectors = set(self.get_loaded_selectors())
            categories_covered = 0
            
            for category, selector_names in self.selector_categories.items():
                category_selectors = [name for name in selector_names if name in loaded_selectors]
                
                if category_selectors:
                    categories_covered += 1
                else:
                    validation_results["missing_selectors"].extend(selector_names)
            
            validation_results["categories_covered"] = categories_covered
            
            # Calculate overall integrity score
            total_expected = sum(len(selectors) for selectors in self.selector_categories.values())
            integrity_score = len(loaded_selectors) / max(total_expected, 1)
            validation_results["overall_integrity"] = integrity_score
            
            logger.info(f"GitHub selector integrity validation: {integrity_score:.2f}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate GitHub selector integrity: {e}")
            return {
                "total_selectors": 0,
                "categories_covered": 0,
                "missing_selectors": [],
                "invalid_selectors": [],
                "overall_integrity": 0.0,
                "error": str(e)
            }
