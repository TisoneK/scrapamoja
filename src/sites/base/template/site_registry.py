"""
Site registry base classes for the Site Template Integration Framework.

This module provides concrete implementations for discovering, registering, and managing
site templates in a centralized registry.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set
from enum import Enum
import json
import os

from .interfaces import ITemplateRegistry, IRegistryManager, ITemplateDiscovery, ITemplateStorage, ITemplateLoader


logger = logging.getLogger(__name__)


class RegistryStatus(Enum):
    """Registry status enumeration."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class TemplateStatus(Enum):
    """Template status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DEPRECATED = "deprecated"


class BaseSiteRegistry(IRegistryManager, ITemplateDiscovery, ITemplateStorage, ITemplateLoader):
    """
    Base implementation of the site registry that combines all registry interfaces.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base site registry.
        
        Args:
            config: Registry configuration
        """
        self.config = config or {}
        
        # Registry state
        self.status = RegistryStatus.INITIALIZING
        self.registry_version = "1.0.0"
        self.last_updated = datetime.now()
        
        # Template storage
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.template_metadata: Dict[str, Dict[str, Any]] = {}
        self.template_status: Dict[str, TemplateStatus] = {}
        
        # Discovery configuration
        self.discovery_paths: List[str] = self.config.get("discovery_paths", [])
        self.auto_refresh = self.config.get("auto_refresh", True)
        self.refresh_interval = self.config.get("refresh_interval", 300)  # 5 minutes
        
        # Registry metadata
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "total_templates": 0,
            "active_templates": 0,
            "last_scan": None,
            "scan_duration": 0.0
        }
        
        # Performance metrics
        self.scan_times: List[float] = []
        self.registration_times: Dict[str, float] = {}
        
        logger.info("BaseSiteRegistry initialized")
    
    async def initialize_registry(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the registry with configuration.
        
        Args:
            config: Registry configuration
            
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("Initializing site registry")
            
            # Update configuration
            self.config.update(config)
            self.discovery_paths = self.config.get("discovery_paths", [])
            self.auto_refresh = self.config.get("auto_refresh", True)
            self.refresh_interval = self.config.get("refresh_interval", 300)
            
            # Validate discovery paths
            if not self.discovery_paths:
                logger.warning("No discovery paths configured")
                return False
            
            # Create discovery paths if they don't exist
            for path in self.discovery_paths:
                path_obj = Path(path)
                if not path_obj.exists():
                    logger.info(f"Creating discovery path: {path}")
                    path_obj.mkdir(parents=True, exist_ok=True)
            
            # Initial scan and registration
            if not await self.scan_and_register(self.discovery_paths):
                logger.error("Initial scan and registration failed")
                return False
            
            self.status = RegistryStatus.ACTIVE
            self.last_updated = datetime.now()
            
            logger.info("Site registry initialized successfully")
            return True
            
        except Exception as e:
            self.status = RegistryStatus.ERROR
            logger.error(f"Failed to initialize registry: {e}")
            return False
    
    async def scan_and_register(self, scan_paths: List[str]) -> Dict[str, Any]:
        """
        Scan paths and automatically register discovered templates.
        
        Args:
            scan_paths: List of paths to scan for templates
            
        Returns:
            Dict[str, Any]: Scan results with registered templates
        """
        try:
            start_time = datetime.now()
            logger.info(f"Scanning {len(scan_paths)} paths for templates")
            
            scan_results = {
                "scanned_paths": scan_paths,
                "discovered_templates": [],
                "registered_templates": [],
                "failed_registrations": [],
                "discovery_errors": [],
                "scan_duration": 0.0
            }
            
            # Discover templates in each path
            for path in scan_paths:
                try:
                    discovered = await self.discover_templates_in_path(path)
                    scan_results["discovered_templates"].extend(discovered)
                    
                except Exception as e:
                    error_msg = f"Error scanning path {path}: {e}"
                    scan_results["discovery_errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Register discovered templates
            for template_info in scan_results["discovered_templates"]:
                template_name = template_info.get("name")
                if template_name:
                    try:
                        if await self.register_template(template_info):
                            scan_results["registered_templates"].append(template_name)
                        else:
                            scan_results["failed_registrations"].append(template_name)
                            
                    except Exception as e:
                        error_msg = f"Error registering template {template_name}: {e}"
                        scan_results["failed_registrations"].append(template_name)
                        logger.error(error_msg)
            
            # Update metrics
            scan_duration = (datetime.now() - start_time).total_seconds()
            scan_results["scan_duration"] = scan_duration
            self.scan_times.append(scan_duration)
            self.metadata["last_scan"] = datetime.now().isoformat()
            self.metadata["scan_duration"] = scan_duration
            
            logger.info(f"Scan completed: {len(scan_results['registered_templates'])} registered, {len(scan_results['failed_registrations'])} failed")
            return scan_results
            
        except Exception as e:
            logger.error(f"Failed to scan and register templates: {e}")
            return {
                "scanned_paths": scan_paths,
                "discovered_templates": [],
                "registered_templates": [],
                "failed_registrations": [],
                "discovery_errors": [str(e)],
                "scan_duration": 0.0
            }
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """
        Get current registry status and health.
        
        Returns:
            Dict[str, Any]: Registry status information
        """
        return {
            "registry_version": self.registry_version,
            "status": self.status.value,
            "last_updated": self.last_updated.isoformat(),
            "total_templates": len(self.templates),
            "active_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.ACTIVE),
            "discovery_paths": self.discovery_paths.copy(),
            "auto_refresh": self.auto_refresh,
            "refresh_interval": self.refresh_interval,
            "metadata": self.metadata.copy(),
            "performance_metrics": {
                "average_scan_time": sum(self.scan_times) / max(len(self.scan_times), 1),
                "total_scans": len(self.scan_times),
                "last_scan_duration": self.scan_times[-1] if self.scan_times else 0.0
            }
        }
    
    async def refresh_registry(self) -> Dict[str, Any]:
        """
        Refresh registry by rescanning all discovery paths.
        
        Returns:
            Dict[str, Any]: Refresh results
        """
        try:
            logger.info("Refreshing registry")
            
            # Clear current templates
            self.templates.clear()
            self.template_metadata.clear()
            self.template_status.clear()
            
            # Rescan and register
            results = await self.scan_and_register(self.discovery_paths)
            
            self.last_updated = datetime.now()
            
            logger.info(f"Registry refreshed: {len(results['registered_templates'])} templates")
            return results
            
        except Exception as e:
            logger.error(f"Failed to refresh registry: {e}")
            return {
                "success": False,
                "error": str(e),
                "registered_templates": []
            }
    
    async def discover_templates_in_path(self, path: str) -> List[Dict[str, Any]]:
        """
        Discover templates in a specific path.
        
        Args:
            path: Filesystem path to search
            
        Returns:
            List[Dict[str, Any]]: List of discovered template metadata
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Discovery path does not exist: {path}")
                return []
            
            discovered_templates = []
            
            # Look for template directories (contain scraper.py)
            for item in path_obj.iterdir():
                if item.is_dir():
                    template_info = await self.extract_template_metadata(str(item))
                    if template_info:
                        discovered_templates.append(template_info)
            
            logger.debug(f"Discovered {len(discovered_templates)} templates in {path}")
            return discovered_templates
            
        except Exception as e:
            logger.error(f"Failed to discover templates in {path}: {e}")
            return []
    
    async def validate_template_structure(self, template_path: str) -> bool:
        """
        Validate template directory structure.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            bool: True if structure is valid
        """
        try:
            path_obj = Path(template_path)
            
            # Check if directory exists
            if not path_obj.is_dir():
                return False
            
            # Required files
            required_files = ["scraper.py"]
            for required_file in required_files:
                if not (path_obj / required_file).exists():
                    logger.debug(f"Missing required file: {required_file}")
                    return False
            
            # Optional but recommended structure
            recommended_dirs = ["selectors", "extraction"]
            found_recommended = sum(1 for dir_name in recommended_dirs if (path_obj / dir_name).exists())
            
            # At least one recommended directory should exist
            if found_recommended == 0:
                logger.debug(f"No recommended directories found: {recommended_dirs}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating template structure {template_path}: {e}")
            return False
    
    async def extract_template_metadata(self, template_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from template directory.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if invalid
        """
        try:
            path_obj = Path(template_path)
            template_name = path_obj.name
            
            # Validate structure first
            if not await self.validate_template_structure(template_path):
                return None
            
            # Extract basic metadata
            metadata = {
                "name": template_name,
                "path": template_path,
                "created_at": datetime.fromtimestamp(path_obj.stat().st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(path_obj.stat().st_mtime).isoformat(),
                "structure": {}
            }
            
            # Check for configuration file
            config_file = path_obj / "config.py"
            if config_file.exists():
                try:
                    # Try to extract configuration info
                    config_content = config_file.read_text(encoding='utf-8')
                    metadata["has_config"] = True
                    
                    # Extract basic info from config (simplified)
                    if "SITE_DOMAIN" in config_content:
                        # Simple extraction - in real implementation, this would be more sophisticated
                        import re
                        domain_match = re.search(r'SITE_DOMAIN\s*=\s*["\']([^"\']+)["\']', config_content)
                        if domain_match:
                            metadata["site_domain"] = domain_match.group(1)
                            
                except Exception as e:
                    logger.warning(f"Error reading config file for {template_name}: {e}")
            
            # Check for selectors directory
            selectors_dir = path_obj / "selectors"
            if selectors_dir.exists():
                yaml_files = list(selectors_dir.glob("*.yaml")) + list(selectors_dir.glob("*.yml"))
                metadata["selector_count"] = len(yaml_files)
                metadata["structure"]["selectors"] = True
            
            # Check for extraction directory
            extraction_dir = path_obj / "extraction"
            if extraction_dir.exists():
                metadata["structure"]["extraction"] = True
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {template_path}: {e}")
            return None
    
    async def watch_for_changes(self, paths: List[str]) -> None:
        """
        Watch paths for template changes and updates.
        
        Args:
            paths: List of paths to watch
        """
        # This would typically use a file watching library like watchdog
        # For now, we'll implement a simple periodic check
        logger.info(f"Watching {len(paths)} paths for changes")
        
        while self.auto_refresh:
            try:
                await asyncio.sleep(self.refresh_interval)
                await self.refresh_registry()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in change monitoring: {e}")
    
    async def register_template(self, template_metadata: Dict[str, Any]) -> bool:
        """
        Register a template in the registry.
        
        Args:
            template_metadata: Template metadata to register
            
        Returns:
            bool: True if registration successful
        """
        try:
            start_time = datetime.now()
            template_name = template_metadata.get("name")
            
            if not template_name:
                logger.error("Template metadata missing 'name' field")
                return False
            
            # Validate template metadata
            validation_result = await self._validate_template_metadata(template_metadata)
            if not validation_result["valid"]:
                logger.error(f"Template validation failed: {validation_result['errors']}")
                return False
            
            # Check if template already exists
            if template_name in self.templates:
                logger.warning(f"Template {template_name} already exists, updating")
                # Update existing template
                self.templates[template_name].update(template_metadata)
                self.template_metadata[template_name].update(template_metadata)
            else:
                # Register new template
                # Store template metadata
                self.templates[template_name] = template_metadata
                self.template_metadata[template_name] = template_metadata
                self.template_status[template_name] = TemplateStatus.ACTIVE
            
            # Update registry metadata
            self.metadata["total_templates"] = len(self.templates)
            self.metadata["active_templates"] = sum(1 for status in self.template_status.values() if status == TemplateStatus.ACTIVE)
            
            # Record performance metrics
            registration_time = (datetime.now() - start_time).total_seconds()
            self.registration_times[template_name] = registration_time
            
            # Log registration event
            logger.info(f"Successfully registered template: {template_name} (v{template_metadata.get('version', 'unknown')})")
            
            # Trigger change event if watching is enabled
            if self.config.get("watch_changes", False):
                await self._notify_template_change("registered", template_name, template_metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register template: {e}")
            return False
    
    async def _validate_template_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate template metadata.
        
        Args:
            metadata: Template metadata to validate
            
        Returns:
            Dict[str, Any]: Validation result with valid flag and errors
        """
        errors = []
        
        try:
            # Required fields
            required_fields = ["name", "version", "template_path", "module_path"]
            for field in required_fields:
                if not metadata.get(field):
                    errors.append(f"Missing required field: {field}")
            
            # Validate name format
            name = metadata.get("name", "")
            if not name or not name.replace("_", "").replace("-", "").isalnum():
                errors.append("Template name must contain only alphanumeric characters, hyphens, and underscores")
            
            # Validate version format
            version = metadata.get("version", "")
            if not self._is_valid_version(version):
                errors.append(f"Invalid version format: {version}")
            
            # Validate paths exist
            template_path = metadata.get("template_path")
            if template_path and not Path(template_path).exists():
                errors.append(f"Template path does not exist: {template_path}")
            
            module_path = metadata.get("module_path")
            if module_path and not Path(module_path).exists():
                errors.append(f"Module path does not exist: {module_path}")
            
            # Validate uniqueness
            name = metadata.get("name")
            if name and name in self.templates:
                existing = self.templates[name]
                if existing.get("version") == version:
                    errors.append(f"Template {name} v{version} already exists")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"]
            }
    
    def _is_valid_version(self, version: str) -> bool:
        """
        Check if version string follows semantic versioning.
        
        Args:
            version: Version string to validate
            
        Returns:
            bool: True if valid version
        """
        try:
            if not version:
                return False
            
            parts = version.split('.')
            if len(parts) < 2:
                return False
            
            for part in parts[:3]:  # Check major.minor.patch
                if part and not part.isdigit():
                    return False
            
            return True
        except:
            return False
    
    async def _notify_template_change(self, action: str, template_name: str, metadata: Dict[str, Any]) -> None:
        """
        Notify about template changes.
        
        Args:
            action: Action type (registered, unregistered, updated)
            template_name: Template name
            metadata: Template metadata
        """
        try:
            # This could be extended to emit events or call callbacks
            logger.info(f"Template {action}: {template_name}")
            
        except Exception as e:
            logger.error(f"Failed to notify template change: {e}")
    
    async def unregister_template(self, template_name: str) -> bool:
        """
        Unregister a template from the registry.
        
        Args:
            template_name: Name of template to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            if template_name not in self.templates:
                logger.warning(f"Template {template_name} not found in registry")
                return False
            
            # Remove from all storage
            del self.templates[template_name]
            del self.template_metadata[template_name]
            del self.template_status[template_name]
            
            # Update registry metadata
            self.metadata["total_templates"] = len(self.templates)
            self.metadata["active_templates"] = sum(1 for status in self.template_status.values() if status == TemplateStatus.ACTIVE)
            
            logger.info(f"Successfully unregistered template: {template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister template {template_name}: {e}")
            return False
    
    async def discover_templates(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Discover templates from the filesystem.
        
        Args:
            force_refresh: Force refresh of discovery
            
        Returns:
            Dict[str, Dict[str, Any]]: Discovered templates
        """
        try:
            logger.info("Starting template discovery")
            
            # Check if we need to refresh
            if not force_refresh and self._is_discovery_cache_valid():
                logger.debug("Using cached discovery results")
                return self.templates
            
            discovered_templates = {}
            
            # Scan sites directory for templates
            sites_dir = Path(self.config.get("sites_directory", "src/sites"))
            
            if not sites_dir.exists():
                logger.warning(f"Sites directory not found: {sites_dir}")
                return {}
            
            # Discover templates in subdirectories
            for item in sites_dir.iterdir():
                if not item.is_dir() or item.name.startswith('_'):
                    continue
                
                template_metadata = await self._analyze_template_directory(item)
                if template_metadata:
                    discovered_templates[template_metadata["name"]] = template_metadata
            
            # Update registry with discovered templates
            for name, metadata in discovered_templates.items():
                await self.register_template(metadata)
            
            # Update discovery cache
            self.last_discovery = datetime.now()
            
            logger.info(f"Template discovery completed: {len(discovered_templates)} templates found")
            return discovered_templates
            
        except Exception as e:
            logger.error(f"Failed to discover templates: {e}")
            return {}
    
    async def _analyze_template_directory(self, template_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a directory to extract template metadata.
        
        Args:
            template_dir: Template directory path
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None
        """
        try:
            # Look for scraper.py file
            scraper_file = template_dir / "scraper.py"
            if not scraper_file.exists():
                return None
            
            # Extract basic metadata
            metadata = {
                "name": template_dir.name,
                "template_path": str(template_dir),
                "module_path": str(scraper_file),
                "discovered_at": datetime.now().isoformat(),
                "status": TemplateStatus.ACTIVE.value
            }
            
            # Try to extract more detailed metadata from the scraper file
            detailed_metadata = await self._extract_detailed_metadata(scraper_file)
            if detailed_metadata:
                metadata.update(detailed_metadata)
            
            # Extract file-based metadata
            file_metadata = await self._extract_file_metadata(template_dir)
            if file_metadata:
                metadata.update(file_metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to analyze template directory {template_dir}: {e}")
            return None
    
    async def _extract_detailed_metadata(self, scraper_file: Path) -> Optional[Dict[str, Any]]:
        """
        Extract detailed metadata from scraper file.
        
        Args:
            scraper_file: Path to scraper.py file
            
        Returns:
            Optional[Dict[str, Any]]: Extracted metadata
        """
        try:
            # Read file content
            content = scraper_file.read_text(encoding='utf-8')
            
            metadata = {}
            
            # Extract basic information using regex patterns
            import re
            
            # Extract description
            desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            if desc_match:
                metadata["description"] = desc_match.group(1)
            
            # Extract version
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                metadata["version"] = version_match.group(1)
            
            # Extract author
            author_match = re.search(r'author\s*=\s*["\']([^"\']+)["\']', content)
            if author_match:
                metadata["author"] = author_match.group(1)
            
            # Extract site domain
            domain_match = re.search(r'site_domain\s*=\s*["\']([^"\']+)["\']', content)
            if domain_match:
                metadata["site_domain"] = domain_match.group(1)
            
            # Extract supported domains
            domains_match = re.search(r'supported_domains\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if domains_match:
                domains_str = domains_match.group(1)
                domains = re.findall(r'["\']([^"\']+)["\']', domains_str)
                metadata["supported_domains"] = domains
            
            # Extract capabilities
            capabilities_match = re.search(r'capabilities\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if capabilities_match:
                caps_str = capabilities_match.group(1)
                capabilities = re.findall(r'["\']([^"\']+)["\']', caps_str)
                metadata["capabilities"] = capabilities
            
            # Extract dependencies
            deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if deps_match:
                deps_str = deps_match.group(1)
                dependencies = re.findall(r'["\']([^"\']+)["\']', deps_str)
                metadata["dependencies"] = dependencies
            
            return metadata if metadata else None
            
        except Exception as e:
            logger.debug(f"Failed to extract detailed metadata from {scraper_file}: {e}")
            return None
    
    async def _extract_file_metadata(self, template_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from template directory structure.
        
        Args:
            template_dir: Template directory path
            
        Returns:
            Optional[Dict[str, Any]]: File-based metadata
        """
        try:
            metadata = {}
            
            # Check for selectors directory
            selectors_dir = template_dir / "selectors"
            if selectors_dir.exists():
                yaml_files = list(selectors_dir.glob("*.yaml")) + list(selectors_dir.glob("*.yml"))
                metadata["selector_count"] = len(yaml_files)
                metadata["has_selectors"] = True
            else:
                metadata["has_selectors"] = False
            
            # Check for flows directory
            flows_dir = template_dir / "flows"
            if flows_dir.exists():
                flow_files = list(flows_dir.glob("*.py"))
                metadata["flow_count"] = len(flow_files)
                metadata["has_flows"] = True
            else:
                metadata["has_flows"] = False
            
            # Check for extraction directory
            extraction_dir = template_dir / "extraction"
            if extraction_dir.exists():
                extraction_files = list(extraction_dir.glob("*.py"))
                metadata["extraction_count"] = len(extraction_files)
                metadata["has_extraction"] = True
            else:
                metadata["has_extraction"] = False
            
            # Get file timestamps
            scraper_file = template_dir / "scraper.py"
            if scraper_file.exists():
                stat = scraper_file.stat()
                metadata["created_at"] = datetime.fromtimestamp(stat.st_ctime).isoformat()
                metadata["updated_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # Determine category based on structure
            metadata["category"] = self._determine_category_from_structure(template_dir, metadata)
            
            # Extract tags
            metadata["tags"] = self._extract_tags_from_structure(metadata)
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Failed to extract file metadata from {template_dir}: {e}")
            return None
    
    def _determine_category_from_structure(self, template_dir: Path, metadata: Dict[str, Any]) -> str:
        """
        Determine template category based on directory structure and metadata.
        
        Args:
            template_dir: Template directory
            metadata: Template metadata
            
        Returns:
            str: Template category
        """
        capabilities = metadata.get("capabilities", [])
        site_domain = metadata.get("site_domain", "")
        
        # Category determination logic
        if "github.com" in site_domain or "repository" in str(capabilities):
            return "code_repository"
        elif any(domain in site_domain for domain in ["twitter.com", "facebook.com", "linkedin.com"]):
            return "social_media"
        elif any(domain in site_domain for domain in ["amazon.com", "ebay.com"]):
            return "ecommerce"
        elif any(cap in capabilities for cap in ["news", "article", "blog"]):
            return "news_media"
        elif "forum" in capabilities or "discussion" in capabilities:
            return "forum_community"
        else:
            return "general"
    
    def _extract_tags_from_structure(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Extract tags based on template structure and metadata.
        
        Args:
            metadata: Template metadata
            
        Returns:
            List[str]: Template tags
        """
        tags = []
        
        # Structure-based tags
        if metadata.get("has_selectors"):
            tags.append("yaml_selectors")
        
        if metadata.get("has_flows"):
            tags.append("flows")
        
        if metadata.get("has_extraction"):
            tags.append("extraction_rules")
        
        # Capability-based tags
        capabilities = metadata.get("capabilities", [])
        capability_tags = {
            "screenshot_capture": "screenshots",
            "html_capture": "html",
            "resource_monitoring": "monitoring",
            "search": "search",
            "pagination": "pagination"
        }
        
        for capability in capabilities:
            if capability in capability_tags:
                tags.append(capability_tags[capability])
        
        return list(set(tags))
    
    def _is_discovery_cache_valid(self) -> bool:
        """
        Check if discovery cache is still valid.
        
        Returns:
            bool: True if cache is valid
        """
        if not self.last_discovery:
            return False
        
        cache_ttl = self.config.get("discovery_cache_ttl", 300)  # 5 minutes default
        cache_age = (datetime.now() - self.last_discovery).total_seconds()
        
        return cache_age < cache_ttl
    
    async def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get template metadata by name.
        
        Args:
            template_name: Name of template
            
        Returns:
            Optional[Dict[str, Any]]: Template metadata or None if not found
        """
        return self.templates.get(template_name)
    
    async def extract_registry_metadata(self) -> Dict[str, Any]:
        """
        Extract comprehensive metadata about the registry.
        
        Returns:
            Dict[str, Any]: Registry metadata
        """
        try:
            metadata = {
                "registry_info": {
                    "total_templates": len(self.templates),
                    "active_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.ACTIVE),
                    "inactive_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.INACTIVE),
                    "error_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.ERROR),
                    "deprecated_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.DEPRECATED)
                },
                "categories": {},
                "capabilities": {},
                "domains": {},
                "tags": {},
                "discovery_info": {
                    "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                    "auto_discovery_enabled": self.config.get("auto_discovery", True),
                    "discovery_paths": self.config.get("discovery_paths", [])
                },
                "performance_metrics": {
                    "average_registration_time": sum(self.registration_times.values()) / len(self.registration_times) if self.registration_times else 0,
                    "total_registrations": len(self.registration_times),
                    "fastest_registration": min(self.registration_times.values()) if self.registration_times else 0,
                    "slowest_registration": max(self.registration_times.values()) if self.registration_times else 0
                }
            }
            
            # Analyze templates by category
            for template_name, template_data in self.templates.items():
                category = template_data.get("category", "general")
                metadata["categories"][category] = metadata["categories"].get(category, 0) + 1
                
                # Analyze capabilities
                capabilities = template_data.get("capabilities", [])
                for capability in capabilities:
                    metadata["capabilities"][capability] = metadata["capabilities"].get(capability, 0) + 1
                
                # Analyze domains
                site_domain = template_data.get("site_domain", "")
                if site_domain:
                    metadata["domains"][site_domain] = metadata["domains"].get(site_domain, 0) + 1
                
                # Analyze tags
                tags = template_data.get("tags", [])
                for tag in tags:
                    metadata["tags"][tag] = metadata["tags"].get(tag, 0) + 1
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract registry metadata: {e}")
            return {}
    
    async def list_templates(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List all registered templates with optional filters.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[Dict[str, Any]]: List of template metadata
        """
        templates = list(self.templates.values())
        
        if not filters:
            return templates
        
        # Apply filters
        filtered_templates = []
        for template in templates:
            match = True
            
            # Filter by status
            if "status" in filters:
                template_name = template.get("name")
                if template_name and template_name in self.template_status:
                    if self.template_status[template_name].value != filters["status"]:
                        match = False
            
            # Filter by site domain
            if "site_domain" in filters and match:
                if template.get("site_domain") != filters["site_domain"]:
                    match = False
            
            # Filter by category
            if "category" in filters and match:
                if template.get("category") != filters["category"]:
                    match = False
            
            # Filter by capabilities
            if "capabilities" in filters and match:
                required_caps = set(filters["capabilities"])
                template_caps = set(template.get("capabilities", []))
                if not required_caps.issubset(template_caps):
                    match = False
            
            # Filter by tags
            if "tags" in filters and match:
                required_tags = set(filters["tags"])
                template_tags = set(template.get("tags", []))
                if not required_tags.intersection(template_tags):
                    match = False
            
            if match:
                filtered_templates.append(template)
        
        return filtered_templates
    
    async def load_template(self, template_name: str, page: Any, selector_engine: Any) -> Optional[Any]:
        """
        Load and instantiate a template.
        
        Args:
            template_name: Name of template to load
            page: Playwright page instance
            selector_engine: Selector engine instance
            
        Returns:
            Optional[Any]: Loaded template instance or None if failed
        """
        try:
            template_metadata = await self.get_template(template_name)
            if not template_metadata:
                logger.error(f"Template {template_name} not found in registry")
                return None
            
            module_path = template_metadata.get("module_path")
            if not module_path:
                logger.error(f"Template {template_name} missing module path")
                return None
            
            # Load the template module
            template_instance = await self._load_template_module(module_path, page, selector_engine)
            if not template_instance:
                logger.error(f"Failed to load template module: {module_path}")
                return None
            
            # Update usage statistics
            await self._update_template_usage(template_name)
            
            logger.info(f"Successfully loaded template: {template_name}")
            return template_instance
            
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            return None
    
    async def _load_template_module(self, module_path: str, page: Any, selector_engine: Any) -> Optional[Any]:
        """
        Load template module and instantiate the template class.
        
        Args:
            module_path: Path to the template module
            page: Playwright page instance
            selector_engine: Selector engine instance
            
        Returns:
            Optional[Any]: Template instance or None if failed
        """
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location("template_module", module_path)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the template class
            template_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a template class (inherits from BaseSiteTemplate)
                if hasattr(obj, '__module__') and obj.__module__ == module.__name__:
                    # Check if it has template-like attributes
                    if hasattr(obj, 'name') and hasattr(obj, 'version'):
                        template_class = obj
                        break
            
            if not template_class:
                logger.error("No template class found in module")
                return None
            
            # Instantiate the template
            template_instance = template_class(page, selector_engine)
            
            # Initialize the template
            if hasattr(template_instance, 'initialize'):
                init_result = await template_instance.initialize()
                if not init_result:
                    logger.error("Template initialization failed")
                    return None
            
            return template_instance
            
        except Exception as e:
            logger.error(f"Failed to load template module {module_path}: {e}")
            return None
    
    async def _update_template_usage(self, template_name: str) -> None:
        """
        Update template usage statistics.
        
        Args:
            template_name: Name of template
        """
        try:
            if template_name in self.templates:
                template = self.templates[template_name]
                
                # Update usage count
                template["usage_count"] = template.get("usage_count", 0) + 1
                template["last_used"] = datetime.now().isoformat()
                
                # Update in all storage locations
                self.templates[template_name] = template
                self.template_metadata[template_name] = template
            
        except Exception as e:
            logger.error(f"Failed to update template usage: {e}")
    
    async def create_template_instance(self, template_name: str, **kwargs) -> Optional[Any]:
        """
        Create a template instance without page/selector_engine.
        
        Args:
            template_name: Name of template
            **kwargs: Additional arguments for template constructor
            
        Returns:
            Optional[Any]: Template instance or None if failed
        """
        try:
            template_metadata = await self.get_template(template_name)
            if not template_metadata:
                logger.error(f"Template {template_name} not found in registry")
                return None
            
            module_path = template_metadata.get("module_path")
            if not module_path:
                logger.error(f"Template {template_name} missing module path")
                return None
            
            # Load the template module
            spec = importlib.util.spec_from_file_location("template_module", module_path)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the template class
            template_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, '__module__') and obj.__module__ == module.__name__:
                    if hasattr(obj, 'name') and hasattr(obj, 'version'):
                        template_class = obj
                        break
            
            if not template_class:
                logger.error("No template class found in module")
                return None
            
            # Create instance without arguments (for metadata access)
            template_instance = template_class.__new__(template_class)
            
            return template_instance
            
        except Exception as e:
            logger.error(f"Failed to create template instance {template_name}: {e}")
            return None
    
    async def search_templates(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        domain: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search templates by various criteria.
        
        Args:
            query: Search query for name/description
            category: Filter by category
            tags: Filter by tags
            capabilities: Filter by capabilities
            domain: Filter by domain
            limit: Maximum results to return
            
        Returns:
            List[Dict[str, Any]]: Matching templates
        """
        try:
            templates = list(self.templates.values())
            results = []
            
            for template in templates:
                # Skip inactive templates
                template_name = template.get("name")
                if template_name and template_name in self.template_status:
                    if self.template_status[template_name] == TemplateStatus.INACTIVE:
                        continue
                
                match = True
                
                # Text search
                if query:
                    query_lower = query.lower()
                    name = template.get("name", "").lower()
                    description = template.get("description", "").lower()
                    if query_lower not in name and query_lower not in description:
                        match = False
                
                # Category filter
                if category and match:
                    if template.get("category") != category:
                        match = False
                
                # Tags filter
                if tags and match:
                    template_tags = set(template.get("tags", []))
                    if not set(tags).intersection(template_tags):
                        match = False
                
                # Capabilities filter
                if capabilities and match:
                    template_caps = set(template.get("capabilities", []))
                    if not set(capabilities).issubset(template_caps):
                        match = False
                
                # Domain filter
                if domain and match:
                    if template.get("site_domain") != domain:
                        match = False
                
                if match:
                    results.append(template)
                    
                    # Limit results
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search templates: {e}")
            return []
    
    async def get_registry_health(self) -> Dict[str, Any]:
        """
        Get registry health status.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            health_status = {
                "registry_status": self.status.value,
                "total_templates": len(self.templates),
                "active_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.ACTIVE),
                "error_templates": sum(1 for status in self.template_status.values() if status == TemplateStatus.ERROR),
                "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                "auto_discovery_enabled": self.config.get("auto_discovery", True),
                "cache_enabled": self.cache_enabled,
                "performance_metrics": {
                    "average_registration_time": sum(self.registration_times.values()) / len(self.registration_times) if self.registration_times else 0,
                    "total_registrations": len(self.registration_times)
                }
            }
            
            # Determine overall health
            if health_status["error_templates"] > 0:
                health_status["overall_health"] = "degraded"
            elif health_status["active_templates"] == 0:
                health_status["overall_health"] = "unhealthy"
            else:
                health_status["overall_health"] = "healthy"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Failed to get registry health: {e}")
            return {
                "registry_status": "error",
                "overall_health": "error",
                "error": str(e)
            }
    
    async def persist_registry(self, file_path: Optional[str] = None) -> bool:
        """
        Persist registry data to file.
        
        Args:
            file_path: Optional file path, uses default if not provided
            
        Returns:
            bool: True if persistence successful
        """
        try:
            if not file_path:
                file_path = self.config.get("persistence_file", "registry_data.json")
            
            registry_data = {
                "metadata": self.metadata,
                "templates": self.templates,
                "template_status": {k: v.value for k, v in self.template_status.items()},
                "registration_times": self.registration_times,
                "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                "config": self.config
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, indent=2, default=str)
            
            logger.info(f"Registry persisted to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist registry: {e}")
            return False
    
    async def load_persisted_registry(self, file_path: Optional[str] = None) -> bool:
        """
        Load registry data from persisted file.
        
        Args:
            file_path: Optional file path, uses default if not provided
            
        Returns:
            bool: True if loading successful
        """
        try:
            if not file_path:
                file_path = self.config.get("persistence_file", "registry_data.json")
            
            if not Path(file_path).exists():
                logger.warning(f"Registry file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            # Restore registry data
            self.metadata = registry_data.get("metadata", {})
            self.templates = registry_data.get("templates", {})
            
            # Restore template status
            status_data = registry_data.get("template_status", {})
            self.template_status = {k: TemplateStatus(v) for k, v in status_data.items()}
            
            self.registration_times = registry_data.get("registration_times", {})
            
            # Restore last discovery
            last_discovery_str = registry_data.get("last_discovery")
            if last_discovery_str:
                self.last_discovery = datetime.fromisoformat(last_discovery_str)
            
            logger.info(f"Registry loaded from: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load persisted registry: {e}")
            return False
    
    async def validate_template_dependencies(self, template_name: str) -> Dict[str, Any]:
        """
        Validate template dependencies.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            template_metadata = await self.get_template(template_name)
            if not template_metadata:
                return {
                    "valid": False,
                    "errors": [f"Template {template_name} not found"]
                }
            
            dependencies = template_metadata.get("dependencies", [])
            validation_result = {
                "valid": True,
                "dependencies": dependencies,
                "missing_dependencies": [],
                "validation_errors": []
            }
            
            # Check each dependency
            for dependency in dependencies:
                if dependency.startswith("BaseSiteScraper"):
                    # Framework dependency - assume available
                    continue
                elif dependency == "selector_engine":
                    # Framework dependency - assume available
                    continue
                elif dependency == "extractor_module":
                    # Framework dependency - assume available
                    continue
                elif dependency == "playwright":
                    # External dependency - check if available
                    try:
                        import playwright
                    except ImportError:
                        validation_result["missing_dependencies"].append(dependency)
                        validation_result["valid"] = False
                else:
                    # Template dependency - check if template exists
                    dep_template = await self.get_template(dependency)
                    if not dep_template:
                        validation_result["missing_dependencies"].append(dependency)
                        validation_result["valid"] = False
            
            return validation_result
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Dependency validation error: {str(e)}"]
            }
    
    async def get_template_instance_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about template instance requirements.
        
        Args:
            template_name: Name of template
            
        Returns:
            Optional[Dict[str, Any]]: Template instance information
        """
        template_metadata = await self.get_template(template_name)
        if not template_metadata:
            return None
        
        return {
            "name": template_name,
            "path": template_metadata.get("path"),
            "site_domain": template_metadata.get("site_domain"),
            "selector_count": template_metadata.get("selector_count", 0),
            "structure": template_metadata.get("structure", {}),
            "status": self.template_status.get(template_name, TemplateStatus.INACTIVE).value,
            "registration_time": self.registration_times.get(template_name, 0.0)
        }
