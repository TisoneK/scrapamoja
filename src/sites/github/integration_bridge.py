"""
GitHub integration bridge for connecting GitHub-specific components with framework infrastructure.

This module implements the integration bridge pattern for GitHub, providing seamless
connection between GitHub-specific components and the existing Scorewise framework.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.sites.base.template.integration_bridge import FullIntegrationBridge, BridgeType
from src.sites.base.template.selector_loader import FileSystemSelectorLoader
from .selector_loader import GitHubSelectorLoader
from .extraction.rules import GitHubExtractionRules


logger = logging.getLogger(__name__)


class GitHubIntegrationBridge(FullIntegrationBridge):
    """
    GitHub-specific integration bridge.
    
    This bridge handles the integration between GitHub-specific components
    and the existing framework infrastructure, including:
    - YAML selector loading and registration
    - Extraction rule setup and validation
    - Framework component health checking
    - Error handling and recovery
    """
    
    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        page: Any,
        selectors_directory: Optional[str] = None,
        extraction_configs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize GitHub integration bridge.
        
        Args:
            template_name: Name of the associated template
            selector_engine: Framework selector engine instance
            page: Playwright page instance
            selectors_directory: Directory containing GitHub YAML selectors
            extraction_configs: Extraction rule configurations
            **kwargs: Additional arguments
        """
        super().__init__(
            template_name=template_name,
            bridge_type=BridgeType.FULL_INTEGRATION,
            selector_engine=selector_engine,
            page=page,
            selector_configs={},  # Will be loaded from filesystem
            extraction_configs=extraction_configs or {},
            **kwargs
        )
        
        # GitHub-specific configuration
        self.selectors_directory = selectors_directory or "src/sites/github/selectors"
        self.extraction_configs = extraction_configs or {}
        
        # Initialize GitHub-specific components
        self.github_selector_loader = GitHubSelectorLoader(
            template_name=template_name,
            selector_engine=selector_engine,
            selectors_directory=self.selectors_directory
        )
        self.github_extraction_rules = GitHubExtractionRules()
        
        # Integration status tracking
        self.github_integration_status = {
            "selectors_loaded": False,
            "extraction_rules_setup": False,
            "framework_components_connected": False,
            "last_integration_check": None
        }
        
        logger.info(f"GitHubIntegrationBridge initialized for {template_name}")
    
    async def _get_selector_configurations(self) -> Dict[str, Any]:
        """
        Get selector configurations for GitHub.
        
        Returns:
            Dict[str, Any]: Selector configurations
        """
        try:
            # Load selectors from filesystem using GitHub selector loader
            await self.github_selector_loader.load_site_selectors("github")
            
            # Get loaded selectors and convert to configuration format
            loaded_selectors = self.github_selector_loader.get_loaded_selectors()
            selector_configs = {}
            
            for selector_name in loaded_selectors:
                # Get selector configuration from YAML files
                config = await self._load_selector_config_from_file(selector_name)
                if config:
                    selector_configs[selector_name] = config
            
            return selector_configs
            
        except Exception as e:
            logger.error(f"Failed to get GitHub selector configurations: {e}")
            return {}
    
    async def _load_selector_config_from_file(self, selector_name: str) -> Optional[Dict[str, Any]]:
        """
        Load selector configuration from YAML file.
        
        Args:
            selector_name: Name of the selector
            
        Returns:
            Optional[Dict[str, Any]]: Selector configuration
        """
        try:
            import yaml
            
            # Look for YAML file
            yaml_file = Path(self.selectors_directory) / f"{selector_name}.yaml"
            if not yaml_file.exists():
                yaml_file = Path(self.selectors_directory) / f"{selector_name}.yml"
            
            if not yaml_file.exists():
                logger.warning(f"YAML file not found for selector: {selector_name}")
                return None
            
            # Load YAML configuration
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Ensure selector name is set
            if config and "name" not in config:
                config["name"] = selector_name
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load selector config for {selector_name}: {e}")
            return None
    
    async def _get_extraction_rule_configurations(self) -> Dict[str, Any]:
        """
        Get extraction rule configurations for GitHub.
        
        Returns:
            Dict[str, Any]: Extraction rule configurations
        """
        try:
            # Get extraction rules from GitHub extraction rules component
            return self.github_extraction_rules.get_all_rule_configs()
            
        except Exception as e:
            logger.error(f"Failed to get GitHub extraction rule configurations: {e}")
            return {}
    
    async def _setup_single_rule_set(self, rule_set_name: str, config: Dict[str, Any]) -> bool:
        """
        Setup a single extraction rule set for GitHub.
        
        Args:
            rule_set_name: Name of the rule set
            config: Rule set configuration
            
        Returns:
            bool: True if setup successful
        """
        try:
            # Use GitHub extraction rules to setup the rule set
            success = await self.github_extraction_rules.setup_rule_set(rule_set_name, config)
            
            if success:
                logger.info(f"Successfully setup GitHub rule set: {rule_set_name}")
            else:
                logger.warning(f"Failed to setup GitHub rule set: {rule_set_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to setup GitHub rule set {rule_set_name}: {e}")
            return False
    
    async def _finalize_integration(self) -> bool:
        """
        Finalize the GitHub integration process.
        
        Returns:
            bool: True if finalization successful
        """
        try:
            logger.info("Finalizing GitHub integration")
            
            # Update GitHub integration status
            self.github_integration_status.update({
                "selectors_loaded": self.selector_count > 0,
                "extraction_rules_setup": self.extraction_rule_count > 0,
                "framework_components_connected": True,
                "last_integration_check": datetime.now().isoformat()
            })
            
            # Perform GitHub-specific finalization steps
            await self._setup_github_specific_integrations()
            
            # Validate integration completeness
            if not await self._validate_github_integration():
                logger.error("GitHub integration validation failed")
                return False
            
            logger.info("GitHub integration finalized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to finalize GitHub integration: {e}")
            return False
    
    async def _setup_github_specific_integrations(self) -> None:
        """Setup GitHub-specific integrations."""
        try:
            # Setup GitHub-specific selector aliases
            await self._setup_github_selector_aliases()
            
            # Setup GitHub-specific extraction mappings
            await self._setup_github_extraction_mappings()
            
            # Setup GitHub-specific error handling
            await self._setup_github_error_handling()
            
        except Exception as e:
            logger.error(f"Failed to setup GitHub-specific integrations: {e}")
    
    async def _setup_github_selector_aliases(self) -> None:
        """Setup GitHub-specific selector aliases."""
        try:
            # Common GitHub selector aliases
            github_aliases = {
                "repo_title": "repository_title",
                "repo_description": "repository_description",
                "repo_stats": "repository_statistics",
                "user_name": "profile_name",
                "user_bio": "profile_bio",
                "issue_title": "issue_title",
                "issue_body": "issue_content"
            }
            
            # Register aliases with selector engine if supported
            if hasattr(self.selector_engine, 'register_alias'):
                for alias, target in github_aliases.items():
                    self.selector_engine.register_alias(alias, target)
                    logger.debug(f"Registered selector alias: {alias} -> {target}")
                    
        except Exception as e:
            logger.warning(f"Failed to setup GitHub selector aliases: {e}")
    
    async def _setup_github_extraction_mappings(self) -> None:
        """Setup GitHub-specific extraction mappings."""
        try:
            # GitHub-specific field mappings
            github_mappings = {
                "repository": {
                    "name": "title",
                    "description": "about",
                    "stars": "stargazers_count",
                    "forks": "forks_count",
                    "language": "primary_language"
                },
                "user": {
                    "username": "login",
                    "name": "display_name",
                    "bio": "about",
                    "followers": "followers_count",
                    "following": "following_count"
                },
                "issue": {
                    "title": "issue_title",
                    "body": "issue_body",
                    "state": "issue_state",
                    "created_at": "created_timestamp"
                }
            }
            
            # Store mappings for use in extraction
            self.github_extraction_rules.set_field_mappings(github_mappings)
            
        except Exception as e:
            logger.warning(f"Failed to setup GitHub extraction mappings: {e}")
    
    async def _setup_github_error_handling(self) -> None:
        """Setup GitHub-specific error handling."""
        try:
            # GitHub-specific error patterns and recovery strategies
            github_error_patterns = {
                "rate_limit": {
                    "pattern": "rate limit",
                    "recovery": "wait_and_retry",
                    "wait_time": 60
                },
                "not_found": {
                    "pattern": "404|not found",
                    "recovery": "skip_item"
                },
                "authentication": {
                    "pattern": "401|unauthorized",
                    "recovery": "skip_item"
                },
                "server_error": {
                    "pattern": "500|502|503",
                    "recovery": "retry_with_backoff"
                }
            }
            
            # Store error patterns for use in error handling
            self.github_error_patterns = github_error_patterns
            
        except Exception as e:
            logger.warning(f"Failed to setup GitHub error handling: {e}")
    
    async def _validate_github_integration(self) -> bool:
        """
        Validate GitHub integration completeness.
        
        Returns:
            bool: True if integration is valid
        """
        try:
            validation_results = {
                "selectors_available": False,
                "extraction_rules_available": False,
                "framework_connection": False,
                "github_components_ready": False
            }
            
            # Check selectors
            if self.selector_count > 0:
                validation_results["selectors_available"] = True
                logger.debug(f"GitHub selectors available: {self.selector_count}")
            else:
                logger.warning("No GitHub selectors loaded")
            
            # Check extraction rules
            if self.extraction_rule_count > 0:
                validation_results["extraction_rules_available"] = True
                logger.debug(f"GitHub extraction rules available: {self.extraction_rule_count}")
            else:
                logger.warning("No GitHub extraction rules loaded")
            
            # Check framework connection
            if self.selector_engine and self.page:
                validation_results["framework_connection"] = True
            else:
                logger.error("Framework components not connected")
            
            # Check GitHub components
            if (self.github_selector_loader and 
                self.github_extraction_rules and
                self.github_selector_loader.get_loaded_selectors()):
                validation_results["github_components_ready"] = True
            else:
                logger.warning("GitHub components not fully ready")
            
            # Overall validation
            all_valid = all(validation_results.values())
            
            if all_valid:
                logger.info("GitHub integration validation passed")
            else:
                logger.warning(f"GitHub integration validation issues: {validation_results}")
            
            return all_valid
            
        except Exception as e:
            logger.error(f"Failed to validate GitHub integration: {e}")
            return False
    
    def get_github_integration_status(self) -> Dict[str, Any]:
        """
        Get GitHub-specific integration status.
        
        Returns:
            Dict[str, Any]: GitHub integration status
        """
        base_status = self.get_integration_status()
        
        github_status = {
            "github_integration_status": self.github_integration_status.copy(),
            "selectors_directory": self.selectors_directory,
            "loaded_selectors": self.github_selector_loader.get_loaded_selectors() if self.github_selector_loader else [],
            "extraction_rule_sets": list(self.github_extraction_rules.get_all_rule_configs().keys()) if self.github_extraction_rules else [],
            "github_components": {
                "selector_loader": self.github_selector_loader is not None,
                "extraction_rules": self.github_extraction_rules is not None
            }
        }
        
        # Merge with base status
        base_status.update(github_status)
        return base_status
    
    async def reload_github_selectors(self) -> bool:
        """
        Reload GitHub selectors from filesystem.
        
        Returns:
            bool: True if reload successful
        """
        try:
            logger.info("Reloading GitHub selectors")
            
            # Clear current selectors
            self.selector_count = 0
            self.loaded_selectors.clear()
            
            # Reload using GitHub selector loader
            success = await self.github_selector_loader.reload_selectors()
            
            if success:
                # Update selector count
                self.selector_count = len(self.github_selector_loader.get_loaded_selectors())
                logger.info(f"Reloaded {self.selector_count} GitHub selectors")
            else:
                logger.error("Failed to reload GitHub selectors")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to reload GitHub selectors: {e}")
            return False
    
    async def test_github_integration(self) -> Dict[str, Any]:
        """
        Test GitHub integration by performing basic operations.
        
        Returns:
            Dict[str, Any]: Test results
        """
        try:
            logger.info("Testing GitHub integration")
            
            test_results = {
                "selector_test": False,
                "extraction_test": False,
                "framework_test": False,
                "overall_success": False
            }
            
            # Test selector availability
            try:
                loaded_selectors = self.github_selector_loader.get_loaded_selectors()
                if loaded_selectors:
                    test_results["selector_test"] = True
                    logger.debug(f"Selector test passed: {len(loaded_selectors)} selectors available")
                else:
                    logger.warning("Selector test failed: No selectors loaded")
            except Exception as e:
                logger.error(f"Selector test error: {e}")
            
            # Test extraction rules
            try:
                rule_configs = self.github_extraction_rules.get_all_rule_configs()
                if rule_configs:
                    test_results["extraction_test"] = True
                    logger.debug(f"Extraction test passed: {len(rule_configs)} rule sets available")
                else:
                    logger.warning("Extraction test failed: No extraction rules available")
            except Exception as e:
                logger.error(f"Extraction test error: {e}")
            
            # Test framework connection
            try:
                if self.selector_engine and self.page:
                    test_results["framework_test"] = True
                    logger.debug("Framework test passed: Components connected")
                else:
                    logger.warning("Framework test failed: Components not connected")
            except Exception as e:
                logger.error(f"Framework test error: {e}")
            
            # Overall success
            test_results["overall_success"] = all([
                test_results["selector_test"],
                test_results["extraction_test"],
                test_results["framework_test"]
            ])
            
            if test_results["overall_success"]:
                logger.info("GitHub integration test passed")
            else:
                logger.warning(f"GitHub integration test failed: {test_results}")
            
            return test_results
            
        except Exception as e:
            logger.error(f"Failed to test GitHub integration: {e}")
            return {
                "selector_test": False,
                "extraction_test": False,
                "framework_test": False,
                "overall_success": False,
                "error": str(e)
            }
