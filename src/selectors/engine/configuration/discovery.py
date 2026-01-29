"""
YAML configuration file discovery utilities.

This module provides functionality for discovering and organizing YAML
configuration files in the hierarchical folder structure.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
import logging


class ConfigurationDiscovery:
    """Utility class for discovering YAML configuration files."""
    
    def __init__(self):
        """Initialize the configuration discovery."""
        self.logger = logging.getLogger(__name__)
        self._correlation_counter = 0
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"discovery_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def discover_configurations(self, root_path: Path) -> Dict[str, List[Path]]:
        """Discover all YAML configuration files in the directory tree."""
        correlation_id = self._generate_correlation_id()
        
        if not root_path.exists():
            raise ValueError(f"Configuration root path does not exist: {root_path}")
        
        self.logger.info(f"Discovering configurations in {root_path} (correlation: {correlation_id})")
        
        configurations = {
            "main": [],
            "fixture": [],
            "match": [],
            "context": []
        }
        
        try:
            # Discover main configurations
            main_path = root_path / "main"
            if main_path.exists():
                configurations["main"] = await self._discover_yaml_files(main_path)
            
            # Discover fixture configurations
            fixture_path = root_path / "fixture"
            if fixture_path.exists():
                configurations["fixture"] = await self._discover_yaml_files(fixture_path)
            
            # Discover match configurations (recursive)
            match_path = root_path / "match"
            if match_path.exists():
                configurations["match"] = await self._discover_yaml_files(match_path, recursive=True)
            
            # Discover context files (_context.yaml)
            configurations["context"] = await self._discover_context_files(root_path)
            
            total_files = sum(len(files) for files in configurations.values())
            self.logger.info(f"Discovered {total_files} configuration files (correlation: {correlation_id})")
            
            return configurations
            
        except Exception as e:
            self.logger.error(f"Error discovering configurations: {e}")
            raise
    
    async def _discover_yaml_files(self, directory: Path, recursive: bool = False) -> List[Path]:
        """Discover YAML files in a directory."""
        yaml_files = []
        
        if recursive:
            # Recursively find all YAML files
            for yaml_file in directory.rglob("*.yaml"):
                if yaml_file.is_file() and not yaml_file.name.startswith("_"):
                    yaml_files.append(yaml_file)
        else:
            # Find YAML files only in this directory
            for yaml_file in directory.glob("*.yaml"):
                if yaml_file.is_file() and not yaml_file.name.startswith("_"):
                    yaml_files.append(yaml_file)
        
        # Sort by path for consistent ordering
        yaml_files.sort()
        return yaml_files
    
    async def _discover_context_files(self, root_path: Path) -> List[Path]:
        """Discover context files (_context.yaml) in the directory tree."""
        context_files = []
        
        for context_file in root_path.rglob("_context.yaml"):
            if context_file.is_file():
                context_files.append(context_file)
        
        # Sort by path for consistent ordering
        context_files.sort()
        return context_files
    
    def organize_by_hierarchy(self, configurations: Dict[str, List[Path]]) -> Dict[str, Dict[str, List[Path]]]:
        """Organize configurations by navigation hierarchy."""
        organized = {
            "main": {"files": configurations.get("main", [])},
            "fixture": {"files": configurations.get("fixture", [])},
            "match": {}
        }
        
        # Organize match configurations by hierarchy
        match_files = configurations.get("match", [])
        hierarchy = self._build_match_hierarchy(match_files)
        organized["match"] = hierarchy
        
        return organized
    
    def _build_match_hierarchy(self, match_files: List[Path]) -> Dict[str, List[Path]]:
        """Build hierarchical organization for match configurations."""
        hierarchy = {}
        
        for file_path in match_files:
            # Extract hierarchy level from path
            relative_path = file_path.relative_to(file_path.parents[2])  # Skip config/match
            parts = relative_path.parts[:-1]  # Exclude filename
            
            if not parts:
                # Root level match files
                if "root" not in hierarchy:
                    hierarchy["root"] = []
                hierarchy["root"].append(file_path)
            else:
                # Nested hierarchy
                level_key = "/".join(parts)
                if level_key not in hierarchy:
                    hierarchy[level_key] = []
                hierarchy[level_key].append(file_path)
        
        return hierarchy
    
    def validate_configuration_structure(self, root_path: Path) -> Dict[str, List[str]]:
        """Validate the expected configuration directory structure."""
        validation_result = {
            "errors": [],
            "warnings": []
        }
        
        # Check root exists
        if not root_path.exists():
            validation_result["errors"].append(f"Configuration root does not exist: {root_path}")
            return validation_result
        
        # Check expected directories
        expected_dirs = ["main", "fixture", "match"]
        for dir_name in expected_dirs:
            dir_path = root_path / dir_name
            if not dir_path.exists():
                validation_result["warnings"].append(f"Expected directory missing: {dir_name}")
            elif not dir_path.is_dir():
                validation_result["errors"].append(f"Expected directory is not a directory: {dir_name}")
        
        # Check for YAML files
        yaml_files = list(root_path.rglob("*.yaml"))
        if not yaml_files:
            validation_result["errors"].append("No YAML configuration files found")
        
        # Check for context files
        context_files = list(root_path.rglob("_context.yaml"))
        if not context_files:
            validation_result["warnings"].append("No context files (_context.yaml) found")
        
        # Validate file naming conventions
        for yaml_file in yaml_files:
            if yaml_file.name.startswith("_") and yaml_file.name != "_context.yaml":
                validation_result["warnings"].append(f"Unexpected underscore file: {yaml_file}")
            
            if not yaml_file.suffix.lower() == ".yaml":
                validation_result["warnings"].append(f"Non-YAML extension: {yaml_file}")
        
        return validation_result
    
    def get_configuration_summary(self, root_path: Path) -> Dict[str, any]:
        """Get a summary of configuration files."""
        try:
            configurations = asyncio.run(self.discover_configurations(root_path))
            organized = self.organize_by_hierarchy(configurations)
            
            summary = {
                "root_path": str(root_path),
                "total_files": sum(len(files) for files in configurations.values()),
                "by_category": {
                    category: len(files) for category, files in configurations.items()
                },
                "hierarchy": {
                    "main_files": len(organized["main"]["files"]),
                    "fixture_files": len(organized["fixture"]["files"]),
                    "match_levels": len(organized["match"]),
                    "match_files": sum(len(files) for files in organized["match"].values())
                },
                "validation": self.validate_configuration_structure(root_path)
            }
            
            return summary
            
        except Exception as e:
            return {
                "root_path": str(root_path),
                "error": str(e),
                "total_files": 0
            }
    
    async def find_configuration_by_selector_name(self, root_path: Path, selector_name: str) -> Optional[Path]:
        """Find configuration file containing a specific selector name."""
        configurations = await self.discover_configurations(root_path)
        
        # Search in all configuration files
        all_files = []
        for files in configurations.values():
            all_files.extend(files)
        
        # Search for selector name in files
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f"selectors:" in content and selector_name in content:
                        # More specific check - look for selector definition
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip() == f"{selector_name}:" and i > 0:
                                # Check if this is under selectors section
                                prev_lines = lines[:i]
                                if any("selectors:" in prev_line for prev_line in prev_lines):
                                    return file_path
            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")
                continue
        
        return None
    
    def get_dependency_order(self, configurations: Dict[str, List[Path]]) -> List[Path]:
        """Determine the order in which configurations should be loaded."""
        load_order = []
        
        # 1. Load context files first (they provide inheritance)
        context_files = configurations.get("context", [])
        load_order.extend(context_files)
        
        # 2. Load main configurations
        main_files = configurations.get("main", [])
        load_order.extend(main_files)
        
        # 3. Load fixture configurations (may depend on main)
        fixture_files = configurations.get("fixture", [])
        load_order.extend(fixture_files)
        
        # 4. Load match configurations (most specific)
        match_files = configurations.get("match", [])
        load_order.extend(match_files)
        
        return load_order
    
    def detect_orphaned_files(self, root_path: Path) -> List[Path]:
        """Detect configuration files that are not in the expected structure."""
        expected_patterns = [
            "main/*.yaml",
            "fixture/*.yaml", 
            "match/**/*.yaml",
            "**/_context.yaml"
        ]
        
        orphaned = []
        all_yaml_files = list(root_path.rglob("*.yaml"))
        
        for yaml_file in all_yaml_files:
            relative_path = yaml_file.relative_to(root_path)
            path_str = str(relative_path)
            
            # Check if file matches any expected pattern
            matched = False
            for pattern in expected_patterns:
                if yaml_file.match(pattern):
                    matched = True
                    break
            
            if not matched and not yaml_file.name.startswith("_"):
                orphaned.append(yaml_file)
        
        return orphaned
