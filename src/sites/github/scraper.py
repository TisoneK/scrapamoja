"""
GitHub scraper implementation using the Site Template Integration Framework.

This module demonstrates how to create a site scraper by extending the template framework
and leveraging existing Scorewise framework components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sites.base.site_scraper import BaseSiteScraper
from src.sites.base.template.site_template import BaseSiteTemplate, ConfigurableSiteTemplate
from src.sites.base.template.integration_bridge import FullIntegrationBridge
from src.sites.base.template.selector_loader import FileSystemSelectorLoader
from .flow import GitHubFlow
from .integration_bridge import GitHubIntegrationBridge
from .selector_loader import GitHubSelectorLoader
from .extraction.rules import GitHubExtractionRules


logger = logging.getLogger(__name__)


class GitHubScraper(BaseSiteTemplate):
    """
    GitHub scraper implementation using the template framework.
    
    This scraper demonstrates the template pattern by:
    - Extending BaseSiteTemplate for standardized functionality
    - Using GitHubIntegrationBridge for framework component connections
    - Leveraging GitHubSelectorLoader for YAML selector management
    - Utilizing GitHubExtractionRules for data extraction
    - Following constitutional principles (selector-centric, async-first, etc.)
    """
    
    def __init__(self, page: Any, selector_engine: Any):
        """
        Initialize GitHub scraper.
        
        Args:
            page: Playwright page instance
            selector_engine: Framework selector engine instance
        """
        super().__init__(
            name="github",
            version="1.0.0",
            description="GitHub repository and user data scraper",
            author="Scorewise Team",
            framework_version="1.0.0",
            site_domain="github.com",
            supported_domains=["api.github.com", "gist.github.com"]
        )
        
        # Initialize template-specific components
        self.flow = GitHubFlow(page, selector_engine)
        self.integration_bridge = GitHubIntegrationBridge(
            template_name="github",
            selector_engine=selector_engine,
            page=page,
            selectors_directory="src/sites/github/selectors"
        )
        self.selector_loader = GitHubSelectorLoader(
            template_name="github",
            selector_engine=selector_engine,
            selectors_directory="src/sites/github/selectors"
        )
        self.extraction_rules = GitHubExtractionRules()
        
        # Framework integration components (will be initialized in base class)
        self.browser_lifecycle = None
        self.resource_monitoring = None
        self.logging_integration = None
        
        # Set integration bridge for base template
        self.integration_bridge = self.integration_bridge
        
        # Template capabilities
        self.capabilities = [
            "repository_search",
            "repository_details",
            "user_profile",
            "issue_tracking",
            "pull_request_tracking",
            "screenshot_capture",
            "html_capture",
            "resource_monitoring",
            "performance_logging",
            "error_tracking"
        ]
        
        # Template dependencies
        self.dependencies = [
            "BaseSiteScraper",
            "selector_engine",
            "extractor_module",
            "playwright"
        ]
        
        logger.info("GitHubScraper initialized")
    
    async def _setup_template_specific(self) -> bool:
        """
        Setup template-specific configuration and validation.
        
        Returns:
            bool: True if setup successful
        """
        try:
            # Validate GitHub-specific configuration
            if not await self._validate_github_configuration():
                logger.error("GitHub configuration validation failed")
                return False
            
            # Setup GitHub-specific flows
            if not await self.flow.initialize():
                logger.error("GitHub flow initialization failed")
                return False
            
            # Setup browser lifecycle integration
            if not await self._setup_browser_lifecycle():
                logger.error("Browser lifecycle setup failed")
                return False
            
            # Setup resource monitoring integration
            if not await self._setup_resource_monitoring():
                logger.error("Resource monitoring setup failed")
                return False
            
            # Setup logging integration
            if not await self._setup_logging_integration():
                logger.error("Logging integration setup failed")
                return False
            
            # Validate template integrity
            if not await self._validate_template_integrity():
                logger.error("GitHub template integrity validation failed")
                return False
            
            logger.info("GitHub template-specific setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup GitHub-specific configuration: {e}")
            return False
    
    async def _validate_scrape_params(self, **kwargs) -> bool:
        """
        Validate scraping parameters for GitHub.
        
        Args:
            **kwargs: Scrape parameters
            
        Returns:
            bool: True if parameters are valid
        """
        # Validate required parameters
        if "action" not in kwargs:
            logger.error("Missing required parameter: action")
            return False
        
        action = kwargs["action"]
        valid_actions = ["search_repositories", "get_repository", "get_user", "get_issues"]
        
        if action not in valid_actions:
            logger.error(f"Invalid action: {action}. Valid actions: {valid_actions}")
            return False
        
        # Action-specific validation
        if action == "search_repositories":
            if "query" not in kwargs:
                logger.error("Missing required parameter for search_repositories: query")
                return False
        
        elif action in ["get_repository", "get_user"]:
            if "identifier" not in kwargs:
                logger.error(f"Missing required parameter for {action}: identifier")
                return False
        
        return True
    
    async def _execute_scrape_logic(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the core scraping logic for GitHub.
        
        Args:
            **kwargs: Scrape parameters
            
        Returns:
            Dict[str, Any]: Raw scrape results
        """
        start_time = datetime.now()
        action = kwargs["action"]
        
        try:
            logger.info(f"Starting GitHub scrape: {action} with params: {kwargs}")
            
            # Update performance metrics
            self._update_performance_metrics(action, 0.0, False)  # Will be updated with actual duration
            
            # Execute the specific scrape operation
            if action == "search_repositories":
                results = await self._scrape_repository_search(**kwargs)
            elif action == "get_repository":
                results = await self._scrape_repository_details(**kwargs)
            elif action == "get_user":
                results = await self._scrape_user_profile(**kwargs)
            elif action == "get_issues":
                results = await self._scrape_repository_issues(**kwargs)
            else:
                raise ValueError(f"Unsupported action: {action}")
            
            # Calculate duration and update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(action, duration, True)
            
            logger.info(f"Successfully completed GitHub scrape: {action} in {duration:.2f}s")
            return results
            
        except Exception as e:
            # Calculate duration and update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(action, duration, False)
            
            # Handle error with error handler
            from src.sites.base.template.error_handling import handle_error
            handle_error(e, {
                "action": action,
                "parameters": kwargs,
                "template_name": self.name,
                "duration": duration
            }, reraise=False)
            
            logger.error(f"Failed to execute scrape logic for {action}: {e}")
            raise
    
    async def _scrape_repository_search(self, **kwargs) -> Dict[str, Any]:
        """
        Scrape repository search results.
        
        Args:
            **kwargs: Search parameters including query
            
        Returns:
            Dict[str, Any]: Search results
        """
        query = kwargs["query"]
        limit = kwargs.get("limit", 10)
        
        logger.info(f"Searching repositories for query: {query}")
        
        # Navigate to GitHub search
        await self.flow.navigate_to_search(query)
        
        # Wait for results to load
        await self.page.wait_for_selector('[data-testid="results-list"]', timeout=10000)
        
        # Extract repository information using selectors
        repositories = []
        repo_elements = await self.page.query_selector_all('[data-testid="results-list"] > div')
        
        for i, element in enumerate(repo_elements[:limit]):
            try:
                # Use selector engine to find repository data
                repo_data = await self.selector_engine.find_all(element, "repository_list_item")
                
                if repo_data:
                    # Extract structured data using extraction rules
                    extracted_data = await self.extraction_rules.extract_repository_data(repo_data[0])
                    repositories.append(extracted_data)
                    
            except Exception as e:
                logger.warning(f"Failed to extract repository {i}: {e}")
                continue
        
        return {
            "action": "search_repositories",
            "query": query,
            "repositories": repositories,
            "total_found": len(repositories)
        }
    
    async def _scrape_repository_details(self, **kwargs) -> Dict[str, Any]:
        """
        Scrape detailed repository information.
        
        Args:
            **kwargs: Repository parameters including identifier
            
        Returns:
            Dict[str, Any]: Repository details
        """
        identifier = kwargs["identifier"]
        
        logger.info(f"Scraping repository details for: {identifier}")
        
        # Navigate to repository page
        await self.flow.navigate_to_repository(identifier)
        
        # Wait for page to load
        await self.page.wait_for_selector('h1[data-testid="repository-title"]', timeout=10000)
        
        # Extract repository details
        repo_element = await self.page.query_selector('main')
        
        if repo_element:
            # Use selector engine to find repository details
            repo_data = await self.selector_engine.find_all(repo_element, "repository_details")
            
            if repo_data:
                extracted_data = await self.extraction_rules.extract_repository_details(repo_data[0])
                return {
                    "action": "get_repository",
                    "identifier": identifier,
                    "repository": extracted_data
                }
        
        raise Exception(f"Failed to extract repository details for {identifier}")
    
    async def _scrape_user_profile(self, **kwargs) -> Dict[str, Any]:
        """
        Scrape user profile information.
        
        Args:
            **kwargs: User parameters including identifier
            
        Returns:
            Dict[str, Any]: User profile data
        """
        identifier = kwargs["identifier"]
        
        logger.info(f"Scraping user profile for: {identifier}")
        
        # Navigate to user profile
        await self.flow.navigate_to_user(identifier)
        
        # Wait for profile to load
        await self.page.wait_for_selector('[data-testid="profile-header"]', timeout=10000)
        
        # Extract user profile
        profile_element = await self.page.query_selector('main')
        
        if profile_element:
            # Use selector engine to find user profile data
            user_data = await self.selector_engine.find_all(profile_element, "user_profile")
            
            if user_data:
                extracted_data = await self.extraction_rules.extract_user_profile(user_data[0])
                return {
                    "action": "get_user",
                    "identifier": identifier,
                    "user": extracted_data
                }
        
        raise Exception(f"Failed to extract user profile for {identifier}")
    
    async def _scrape_repository_issues(self, **kwargs) -> Dict[str, Any]:
        """
        Scrape repository issues.
        
        Args:
            **kwargs: Repository parameters including identifier
            
        Returns:
            Dict[str, Any]: Issues data
        """
        identifier = kwargs["identifier"]
        state = kwargs.get("state", "open")
        limit = kwargs.get("limit", 20)
        
        logger.info(f"Scraping issues for repository: {identifier} (state: {state})")
        
        # Navigate to repository issues
        await self.flow.navigate_to_repository_issues(identifier, state)
        
        # Wait for issues to load
        await self.page.wait_for_selector('[data-testid="issue-list"]', timeout=10000)
        
        # Extract issues
        issues = []
        issue_elements = await self.page.query_selector_all('[data-testid="issue-list"] > div')
        
        for i, element in enumerate(issue_elements[:limit]):
            try:
                # Use selector engine to find issue data
                issue_data = await self.selector_engine.find_all(element, "issue_list_item")
                
                if issue_data:
                    # Extract structured data using extraction rules
                    extracted_data = await self.extraction_rules.extract_issue_data(issue_data[0])
                    issues.append(extracted_data)
                    
            except Exception as e:
                logger.warning(f"Failed to extract issue {i}: {e}")
                continue
        
        return {
            "action": "get_issues",
            "identifier": identifier,
            "state": state,
            "issues": issues,
            "total_found": len(issues)
        }
    
    async def _setup_browser_lifecycle(self) -> bool:
        """
        Setup browser lifecycle integration for GitHub template.
        
        Returns:
            bool: True if setup successful
        """
        try:
            # Check if browser lifecycle is available from parent class
            if not hasattr(self, 'browser_lifecycle') or not self.browser_lifecycle:
                logger.warning("Browser lifecycle integration not available in parent class")
                return True  # Not critical for GitHub template
            
            # Configure GitHub-specific browser settings
            github_browser_config = {
                "auto_screenshot": True,  # Enable automatic screenshots for debugging
                "auto_html_capture": True,  # Enable automatic HTML capture
                "screenshot_on_error": True,  # Capture screenshots on errors
                "html_capture_on_error": True,  # Capture HTML on errors
                "screenshot_format": "png",
                "screenshot_quality": 90,
                "html_capture_clean": True
            }
            
            # Update browser lifecycle configuration
            self.browser_lifecycle.update_config(github_browser_config)
            
            # Test browser capabilities
            feature_status = self.browser_lifecycle.get_feature_status()
            available_features = [feature for feature, available in feature_status.items() if available]
            
            logger.info(f"GitHub browser lifecycle features available: {available_features}")
            
            # Enable GitHub-specific features
            if feature_status.get("screenshot_capture", False):
                logger.info("GitHub screenshot capture enabled")
            
            if feature_status.get("html_capture", False):
                logger.info("GitHub HTML capture enabled")
            
            if feature_status.get("resource_monitoring", False):
                logger.info("GitHub resource monitoring enabled")
            
            logger.info("GitHub browser lifecycle setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup GitHub browser lifecycle: {e}")
            return False
    
    async def capture_github_screenshot(
        self,
        context: str = "general",
        filename: Optional[str] = None,
        full_page: bool = True
    ) -> Optional[str]:
        """
        Capture a GitHub-specific screenshot with context.
        
        Args:
            context: Context for the screenshot (e.g., "search", "repository", "issues")
            filename: Optional filename
            full_page: Whether to capture full page
            
        Returns:
            Optional[str]: Path to screenshot
        """
        try:
            if not hasattr(self, 'browser_lifecycle') or not self.browser_lifecycle:
                logger.warning("Screenshot capture not available")
                return None
            
            # Generate context-specific filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"github_{context}_{timestamp}.png"
            
            # Capture screenshot
            screenshot_path = await self.browser_lifecycle.capture_screenshot(
                filename=filename,
                full_page=full_page
            )
            
            if screenshot_path:
                logger.info(f"GitHub screenshot captured for context '{context}': {screenshot_path}")
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Failed to capture GitHub screenshot: {e}")
            return None
    
    async def capture_github_html(
        self,
        context: str = "general",
        filename: Optional[str] = None,
        clean: bool = True
    ) -> Optional[str]:
        """
        Capture GitHub-specific HTML with context.
        
        Args:
            context: Context for the HTML capture
            filename: Optional filename
            clean: Whether to clean the HTML
            
        Returns:
            Optional[str]: Path to HTML file
        """
        try:
            if not hasattr(self, 'browser_lifecycle') or not self.browser_lifecycle:
                logger.warning("HTML capture not available")
                return None
            
            # Generate context-specific filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"github_{context}_{timestamp}.html"
            
            # Capture HTML
            html_path = await self.browser_lifecycle.capture_html(
                filename=filename,
                clean=clean
            )
            
            if html_path:
                logger.info(f"GitHub HTML captured for context '{context}': {html_path}")
            
            return html_path
            
        except Exception as e:
            logger.error(f"Failed to capture GitHub HTML: {e}")
            return None
    
    async def capture_github_error_state(
        self,
        error_type: str,
        operation: str = "unknown"
    ) -> Dict[str, Optional[str]]:
        """
        Capture GitHub error state with screenshots and HTML.
        
        Args:
            error_type: Type of error that occurred
            operation: Operation that was being performed
            
        Returns:
            Dict[str, Optional[str]]: Paths to captured files
        """
        try:
            logger.info(f"Capturing GitHub error state: {error_type} during {operation}")
            
            captured_files = {
                "screenshot": None,
                "html": None,
                "error_type": error_type,
                "operation": operation,
                "timestamp": datetime.now().isoformat()
            }
            
            # Capture screenshot
            if hasattr(self, 'browser_lifecycle') and self.browser_lifecycle:
                captured_files["screenshot"] = await self.browser_lifecycle.capture_error_screenshot(error_type)
                captured_files["html"] = await self.browser_lifecycle.capture_error_html(error_type)
            
            logger.info(f"Error state captured: {captured_files}")
            return captured_files
            
        except Exception as e:
            logger.error(f"Failed to capture GitHub error state: {e}")
            return {
                "screenshot": None,
                "html": None,
                "error_type": error_type,
                "operation": operation,
                "error": str(e)
            }
    
    def get_github_browser_info(self) -> Dict[str, Any]:
        """
        Get GitHub-specific browser information.
        
        Returns:
            Dict[str, Any]: Browser information
        """
        try:
            browser_info = {
                "template": "github",
                "browser_lifecycle_available": hasattr(self, 'browser_lifecycle') and self.browser_lifecycle is not None
            }
            
            if browser_info["browser_lifecycle_available"]:
                browser_info.update({
                    "session_info": self.browser_lifecycle.get_browser_session_info(),
                    "feature_status": self.browser_lifecycle.get_feature_status(),
                    "lifecycle_events_count": len(self.browser_lifecycle.get_lifecycle_events(limit=1)),
                    "config": self.browser_lifecycle.get_config()
                })
            
            return browser_info
            
        except Exception as e:
            logger.error(f"Failed to get GitHub browser info: {e}")
            return {"template": "github", "error": str(e)}
    
    async def _setup_resource_monitoring(self) -> bool:
        """
        Setup resource monitoring integration for GitHub template.
        
        Returns:
            bool: True if setup successful
        """
        try:
            # Check if resource monitoring is available from parent class
            if not hasattr(self, 'browser_lifecycle') or not self.browser_lifecycle:
                logger.warning("Resource monitoring integration not available in parent class")
                return True  # Not critical for GitHub template
            
            # Import resource monitoring integration
            from src.sites.base.template.resource_monitoring import ResourceMonitoringIntegration
            
            # Create resource monitoring integration
            self.resource_monitoring = ResourceMonitoringIntegration(self.integration_bridge)
            
            # Initialize resource monitoring
            if not await self.resource_monitoring.initialize_resource_monitoring():
                logger.warning("Resource monitoring initialization failed")
                return True  # Not critical
            
            # Configure GitHub-specific resource settings
            github_resource_config = {
                "auto_monitoring": True,
                "monitoring_interval": 10.0,  # Check every 10 seconds
                "memory_threshold": 85.0,  # Higher threshold for GitHub scraping
                "cpu_threshold": 85.0,
                "disk_threshold": 90.0,
                "network_threshold": 5000000,  # 5MB/s for GitHub operations
                "alert_on_threshold": True,
                "cleanup_on_threshold": False,  # Don't auto-cleanup during scraping
                "max_monitoring_time": 7200  # 2 hours max
            }
            
            # Update resource monitoring configuration
            self.resource_monitoring.update_config(github_resource_config)
            
            # Start resource monitoring
            if await self.resource_monitoring.start_monitoring():
                logger.info("GitHub resource monitoring started")
            else:
                logger.warning("Failed to start resource monitoring")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup GitHub resource monitoring: {e}")
            return False
    
    async def _setup_logging_integration(self) -> bool:
        """
        Setup logging integration for GitHub template.
        
        Returns:
            bool: True if setup successful
        """
        try:
            # Check if logging integration is available from parent class
            if not hasattr(self, 'browser_lifecycle') or not self.browser_lifecycle:
                logger.warning("Logging integration not available in parent class")
                return True  # Not critical for GitHub template
            
            # Import logging integration
            from src.sites.base.template.logging_integration import LoggingFrameworkIntegration
            
            # Create logging integration
            self.logging_integration = LoggingFrameworkIntegration(self.integration_bridge)
            
            # Initialize logging integration
            if not await self.logging_integration.initialize_logging_integration():
                logger.warning("Logging integration initialization failed")
                return True  # Not critical
            
            # Configure GitHub-specific logging settings
            github_logging_config = {
                "auto_logging": True,
                "log_level": "INFO",
                "log_format": "structured",
                "include_performance": True,
                "include_correlation": True,
                "log_to_file": True,
                "log_file_path": "logs/github_scraper.log",
                "error_log_separate": True
            }
            
            # Update logging configuration
            self.logging_integration.update_config(github_logging_config)
            
            logger.info("GitHub logging integration setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup GitHub logging integration: {e}")
            return False
    
    async def _validate_github_configuration(self) -> bool:
        """
        Validate GitHub-specific configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Check if selectors directory exists and has YAML files
            import os
            selectors_dir = "src/sites/github/selectors"
            
            if not os.path.exists(selectors_dir):
                logger.error(f"Selectors directory not found: {selectors_dir}")
                return False
            
            yaml_files = [f for f in os.listdir(selectors_dir) if f.endswith(('.yaml', '.yml'))]
            if not yaml_files:
                logger.warning(f"No YAML selector files found in {selectors_dir}")
                # Not an error, but warning
            
            # Validate extraction rules
            if not self.extraction_rules:
                logger.error("Extraction rules not initialized")
                return False
            
            # Validate template components
            if not self.flow:
                logger.error("GitHub flow not initialized")
                return False
            
            if not self.integration_bridge:
                logger.error("GitHub integration bridge not initialized")
                return False
            
            if not self.selector_loader:
                logger.error("GitHub selector loader not initialized")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating GitHub configuration: {e}")
            return False
    
    async def _validate_template_integrity(self) -> bool:
        """
        Validate template integrity and framework integration.
        
        Returns:
            bool: True if template integrity is valid
        """
        try:
            logger.info("Validating GitHub template integrity")
            
            # Test selector loader
            if self.selector_loader:
                loaded_selectors = self.selector_loader.get_loaded_selectors()
                if not loaded_selectors:
                    logger.warning("No selectors loaded - attempting to load")
                    success = await self.selector_loader.load_site_selectors("github")
                    if not success:
                        logger.error("Failed to load GitHub selectors")
                        return False
            else:
                logger.error("Selector loader not available")
                return False
            
            # Test integration bridge
            if self.integration_bridge:
                bridge_status = self.integration_bridge.get_integration_status()
                if not bridge_status.get("is_integrated", False):
                    logger.warning("Integration bridge not integrated - attempting integration")
                    success = await self.integration_bridge.initialize_complete_integration()
                    if not success:
                        logger.error("Failed to initialize integration bridge")
                        return False
            else:
                logger.error("Integration bridge not available")
                return False
            
            # Test extraction rules
            if self.extraction_rules:
                rule_summary = self.extraction_rules.get_extraction_summary()
                if rule_summary.get("total_rules", 0) == 0:
                    logger.warning("No extraction rules available")
            else:
                logger.error("Extraction rules not available")
                return False
            
            # Test flow initialization
            if self.flow:
                flow_state = await self.flow.get_navigation_state()
                if not flow_state.get("capabilities"):
                    logger.warning("Flow capabilities not available")
            else:
                logger.error("GitHub flow not available")
                return False
            
            logger.info("GitHub template integrity validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate template integrity: {e}")
            return False
    
    async def _setup_error_handling(self) -> None:
        """Setup error handling for GitHub template."""
        try:
            # Configure error handling for GitHub-specific errors
            from .error_handling import get_error_handler
            
            error_handler = get_error_handler()
            
            # Add GitHub-specific error patterns
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
            
            logger.info("GitHub error handling configured")
            
        except Exception as e:
            logger.warning(f"Failed to setup error handling: {e}")
    
    async def _setup_monitoring(self) -> None:
        """Setup monitoring for GitHub template operations."""
        try:
            # Initialize performance tracking
            self.performance_metrics = {
                "scrape_count": 0,
                "total_scrape_time": 0.0,
                "average_scrape_time": 0.0,
                "error_count": 0,
                "success_count": 0
            }
            
            # Initialize operation tracking
            self.operation_history = []
            
            logger.info("GitHub monitoring setup completed")
            
        except Exception as e:
            logger.warning(f"Failed to setup monitoring: {e}")
    
    def _update_performance_metrics(self, operation: str, duration: float, success: bool) -> None:
        """
        Update performance metrics for an operation.
        
        Args:
            operation: Operation name
            duration: Operation duration in seconds
            success: Whether operation was successful
        """
        try:
            self.performance_metrics["scrape_count"] += 1
            self.performance_metrics["total_scrape_time"] += duration
            self.performance_metrics["average_scrape_time"] = (
                self.performance_metrics["total_scrape_time"] / self.performance_metrics["scrape_count"]
            )
            
            if success:
                self.performance_metrics["success_count"] += 1
            else:
                self.performance_metrics["error_count"] += 1
            
            # Add to operation history
            self.operation_history.append({
                "operation": operation,
                "duration": duration,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 100 operations
            if len(self.operation_history) > 100:
                self.operation_history = self.operation_history[-100:]
                
        except Exception as e:
            logger.warning(f"Failed to update performance metrics: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        try:
            metrics = self.performance_metrics.copy()
            
            # Calculate success rate
            total_operations = metrics["success_count"] + metrics["error_count"]
            metrics["success_rate"] = metrics["success_count"] / max(total_operations, 1)
            
            # Add recent operations
            metrics["recent_operations"] = self.operation_history[-10:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the GitHub template.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            logger.info("Performing GitHub template health check")
            
            health_status = {
                "template_name": self.name,
                "template_version": self.version,
                "initialized": self.initialized,
                "components": {},
                "overall_health": "unknown"
            }
            
            # Check selector loader
            if self.selector_loader:
                loaded_selectors = self.selector_loader.get_loaded_selectors()
                health_status["components"]["selector_loader"] = {
                    "status": "healthy",
                    "loaded_selectors": len(loaded_selectors),
                    "selectors": loaded_selectors[:5]  # First 5 for brevity
                }
            else:
                health_status["components"]["selector_loader"] = {
                    "status": "unhealthy",
                    "error": "Not initialized"
                }
            
            # Check integration bridge
            if self.integration_bridge:
                bridge_status = self.integration_bridge.get_integration_status()
                health_status["components"]["integration_bridge"] = {
                    "status": "healthy" if bridge_status.get("is_integrated") else "unhealthy",
                    "integration_status": bridge_status
                }
            else:
                health_status["components"]["integration_bridge"] = {
                    "status": "unhealthy",
                    "error": "Not initialized"
                }
            
            # Check extraction rules
            if self.extraction_rules:
                rule_summary = self.extraction_rules.get_extraction_summary()
                health_status["components"]["extraction_rules"] = {
                    "status": "healthy" if rule_summary.get("total_rules", 0) > 0 else "unhealthy",
                    "rule_summary": rule_summary
                }
            else:
                health_status["components"]["extraction_rules"] = {
                    "status": "unhealthy",
                    "error": "Not initialized"
                }
            
            # Check flow
            if self.flow:
                flow_state = await self.flow.get_navigation_state()
                health_status["components"]["flow"] = {
                    "status": "healthy",
                    "navigation_state": flow_state
                }
            else:
                health_status["components"]["flow"] = {
                    "status": "unhealthy",
                    "error": "Not initialized"
                }
            
            # Determine overall health
            component_statuses = [comp.get("status", "unhealthy") for comp in health_status["components"].values()]
            if all(status == "healthy" for status in component_statuses):
                health_status["overall_health"] = "healthy"
            elif any(status == "unhealthy" for status in component_statuses):
                health_status["overall_health"] = "unhealthy"
            else:
                health_status["overall_health"] = "degraded"
            
            # Add performance metrics
            health_status["performance"] = self.get_performance_metrics()
            
            logger.info(f"Health check completed: {health_status['overall_health']}")
            return health_status
            
        except Exception as e:
            logger.error(f"Failed to perform health check: {e}")
            return {
                "template_name": self.name,
                "overall_health": "error",
                "error": str(e)
            }
