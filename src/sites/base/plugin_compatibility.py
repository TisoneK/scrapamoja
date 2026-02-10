"""
Plugin version compatibility checking system.

This module provides comprehensive version compatibility checking for plugins,
including semantic version parsing, dependency resolution, and compatibility matrices.
"""

import re
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from packaging import version
import json
import threading

from .plugin_interface import IPlugin, PluginMetadata, PluginType, get_plugin_registry


class CompatibilityStatus(Enum):
    """Compatibility status enumeration."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"
    DEPRECATED = "deprecated"
    WARNING = "warning"


class DependencyType(Enum):
    """Dependency type enumeration."""
    PLUGIN = "plugin"
    FRAMEWORK = "framework"
    PYTHON = "python"
    SYSTEM = "system"
    LIBRARY = "library"


@dataclass
class VersionRequirement:
    """Version requirement specification."""
    package_name: str
    version_spec: str  # e.g., ">=1.0.0,<2.0.0"
    dependency_type: DependencyType
    optional: bool = False
    reason: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompatibilityIssue:
    """Compatibility issue description."""
    plugin_id: str
    issue_type: str
    severity: str  # "error", "warning", "info"
    description: str
    suggestion: Optional[str] = None
    affected_version: Optional[str] = None
    required_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompatibilityResult:
    """Compatibility check result."""
    plugin_id: str
    status: CompatibilityStatus
    issues: List[CompatibilityIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    check_time_ms: float = 0.0
    framework_version: Optional[str] = None
    python_version: Optional[str] = None
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PluginCompatibilityChecker:
    """Plugin compatibility checker."""
    
    def __init__(self, framework_version: str = "1.0.0"):
        """Initialize plugin compatibility checker."""
        self.framework_version = framework_version
        self.registry = get_plugin_registry()
        
        # Compatibility data
        self._compatibility_matrix: Dict[str, Dict[str, CompatibilityStatus]] = {}
        self._version_requirements: Dict[str, List[VersionRequirement]] = {}
        self._known_issues: Dict[str, List[CompatibilityIssue]] = {}
        
        # Compatibility rules
        self._compatibility_rules: Dict[str, Callable] = {}
        self._default_rules = [
            self._check_framework_version,
            self._check_python_version,
            self._check_plugin_dependencies,
            self._check_library_dependencies,
            self._check_system_requirements
        ]
        
        # Version parsing
        self._version_pattern = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+))?$')
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_checks': 0,
            'compatible_count': 0,
            'incompatible_count': 0,
            'warning_count': 0,
            'unknown_count': 0,
            'check_time_ms': 0.0,
            'average_check_time_ms': 0.0
        }
        
        # Initialize built-in compatibility rules
        self._initialize_builtin_rules()
    
    def _initialize_builtin_rules(self) -> None:
        """Initialize built-in compatibility rules."""
        # Framework version compatibility
        self.add_compatibility_rule("framework_version", self._check_framework_version)
        
        # Python version compatibility
        self.add_compatibility_rule("python_version", self._check_python_version)
        
        # Plugin dependency compatibility
        self.add_compatibility_rule("plugin_dependencies", self._check_plugin_dependencies)
        
        # Library dependency compatibility
        self.add_compatibility_rule("library_dependencies", self._check_library_dependencies)
        
        # System requirement compatibility
        self.add_compatibility_rule("system_requirements", self._check_system_requirements)
    
    def add_compatibility_rule(self, rule_name: str, rule_func: Callable) -> None:
        """
        Add a compatibility rule.
        
        Args:
            rule_name: Rule name
            rule_func: Rule function that takes plugin metadata and returns issues
        """
        with self._lock:
            self._compatibility_rules[rule_name] = rule_func
    
    def remove_compatibility_rule(self, rule_name: str) -> bool:
        """
        Remove a compatibility rule.
        
        Args:
            rule_name: Rule name
            
        Returns:
            True if removed successfully
        """
        with self._lock:
            if rule_name in self._compatibility_rules:
                del self._compatibility_rules[rule_name]
                return True
            return False
    
    def check_plugin_compatibility(self, plugin_id: str) -> CompatibilityResult:
        """
        Check compatibility of a plugin.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            Compatibility result
        """
        start_time = datetime.utcnow()
        
        try:
            # Get plugin metadata
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                return CompatibilityResult(
                    plugin_id=plugin_id,
                    status=CompatibilityStatus.UNKNOWN,
                    issues=[CompatibilityIssue(
                        plugin_id=plugin_id,
                        issue_type="plugin_not_found",
                        severity="error",
                        description=f"Plugin {plugin_id} not found in registry"
                    )]
                )
            
            metadata = plugin.metadata
            
            # Initialize result
            issues = []
            warnings = []
            suggestions = []
            
            # Run compatibility checks
            for rule_name, rule_func in self._compatibility_rules.items():
                try:
                    rule_issues = rule_func(metadata)
                    if rule_issues:
                        issues.extend(rule_issues)
                except Exception as e:
                    issues.append(CompatibilityIssue(
                        plugin_id=plugin_id,
                        issue_type=f"rule_error_{rule_name}",
                        severity="warning",
                        description=f"Compatibility rule {rule_name} failed: {str(e)}"
                    ))
            
            # Check known issues
            if plugin_id in self._known_issues:
                issues.extend(self._known_issues[plugin_id])
            
            # Determine overall status
            status = self._determine_compatibility_status(issues)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(issues, metadata)
            
            # Calculate check time
            check_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_statistics(status, check_time_ms)
            
            # Create result
            result = CompatibilityResult(
                plugin_id=plugin_id,
                status=status,
                issues=issues,
                warnings=[issue.description for issue in issues if issue.severity == "warning"],
                suggestions=suggestions,
                check_time_ms=check_time_ms,
                framework_version=self.framework_version,
                python_version=self._get_python_version()
            )
            
            # Store in compatibility matrix
            with self._lock:
                if plugin_id not in self._compatibility_matrix:
                    self._compatibility_matrix[plugin_id] = {}
                self._compatibility_matrix[plugin_id][self.framework_version] = status
            
            return result
            
        except Exception as e:
            check_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return CompatibilityResult(
                plugin_id=plugin_id,
                status=CompatibilityStatus.UNKNOWN,
                issues=[CompatibilityIssue(
                    plugin_id=plugin_id,
                    issue_type="check_failed",
                    severity="error",
                    description=f"Compatibility check failed: {str(e)}"
                )],
                check_time_ms=check_time_ms
            )
    
    def check_all_plugins_compatibility(self) -> Dict[str, CompatibilityResult]:
        """
        Check compatibility of all plugins.
        
        Returns:
            Dictionary of plugin IDs to compatibility results
        """
        results = {}
        
        # Get all plugins
        all_metadata = self.registry.get_all_metadata()
        
        for plugin_id in all_metadata:
            results[plugin_id] = self.check_plugin_compatibility(plugin_id)
        
        return results
    
    def add_version_requirement(self, plugin_id: str, requirement: VersionRequirement) -> None:
        """
        Add a version requirement for a plugin.
        
        Args:
            plugin_id: Plugin ID
            requirement: Version requirement
        """
        with self._lock:
            if plugin_id not in self._version_requirements:
                self._version_requirements[plugin_id] = []
            
            self._version_requirements[plugin_id].append(requirement)
    
    def remove_version_requirement(self, plugin_id: str, package_name: str) -> bool:
        """
        Remove a version requirement for a plugin.
        
        Args:
            plugin_id: Plugin ID
            package_name: Package name
            
        Returns:
            True if removed successfully
        """
        with self._lock:
            if plugin_id in self._version_requirements:
                requirements = self._version_requirements[plugin_id]
                for i, req in enumerate(requirements):
                    if req.package_name == package_name:
                        del requirements[i]
                        return True
            return False
    
    def get_version_requirements(self, plugin_id: str) -> List[VersionRequirement]:
        """Get version requirements for a plugin."""
        return self._version_requirements.get(plugin_id, []).copy()
    
    def add_known_issue(self, plugin_id: str, issue: CompatibilityIssue) -> None:
        """
        Add a known compatibility issue.
        
        Args:
            plugin_id: Plugin ID
            issue: Compatibility issue
        """
        with self._lock:
            if plugin_id not in self._known_issues:
                self._known_issues[plugin_id] = []
            
            self._known_issues[plugin_id].append(issue)
    
    def remove_known_issue(self, plugin_id: str, issue_type: str) -> bool:
        """
        Remove a known compatibility issue.
        
        Args:
            plugin_id: Plugin ID
            issue_type: Issue type
            
        Returns:
            True if removed successfully
        """
        with self._lock:
            if plugin_id in self._known_issues:
                issues = self._known_issues[plugin_id]
                for i, issue in enumerate(issues):
                    if issue.issue_type == issue_type:
                        del issues[i]
                        return True
            return False
    
    def get_compatibility_matrix(self) -> Dict[str, Dict[str, CompatibilityStatus]]:
        """Get the compatibility matrix."""
        with self._lock:
            return self._compatibility_matrix.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compatibility statistics."""
        with self._lock:
            stats = self._stats.copy()
            
            # Add compatibility matrix statistics
            total_entries = sum(len(matrix) for matrix in self._compatibility_matrix.values())
            stats['compatibility_matrix_size'] = total_entries
            
            # Add requirement statistics
            stats['total_requirements'] = sum(
                len(reqs) for reqs in self._version_requirements.values()
            )
            
            # Add known issues statistics
            stats['total_known_issues'] = sum(
                len(issues) for issues in self._known_issues.values()
            )
            
            return stats
    
    def export_compatibility_data(self) -> Dict[str, Any]:
        """Export compatibility data."""
        return {
            'framework_version': self.framework_version,
            'compatibility_matrix': {
                plugin_id: {
                    version: status.value
                    for version, status in matrix.items()
                }
                for plugin_id, matrix in self._compatibility_matrix.items()
            },
            'version_requirements': {
                plugin_id: [
                    {
                        'package_name': req.package_name,
                        'version_spec': req.version_spec,
                        'dependency_type': req.dependency_type.value,
                        'optional': req.optional,
                        'reason': req.reason,
                        'alternatives': req.alternatives,
                        'metadata': req.metadata
                    }
                    for req in reqs
                ]
                for plugin_id, reqs in self._version_requirements.items()
            },
            'known_issues': {
                plugin_id: [
                    {
                        'issue_type': issue.issue_type,
                        'severity': issue.severity,
                        'description': issue.description,
                        'suggestion': issue.suggestion,
                        'affected_version': issue.affected_version,
                        'required_version': issue.required_version,
                        'metadata': issue.metadata
                    }
                    for issue in issues
                ]
                for plugin_id, issues in self._known_issues.items()
            },
            'statistics': self.get_statistics(),
            'exported_at': datetime.utcnow().isoformat()
        }
    
    def import_compatibility_data(self, data: Dict[str, Any]) -> None:
        """Import compatibility data."""
        with self._lock:
            # Import compatibility matrix
            for plugin_id, matrix in data.get('compatibility_matrix', {}).items():
                if plugin_id not in self._compatibility_matrix:
                    self._compatibility_matrix[plugin_id] = {}
                
                for version_str, status_str in matrix.items():
                    self._compatibility_matrix[plugin_id][version_str] = CompatibilityStatus(status_str)
            
            # Import version requirements
            for plugin_id, reqs_data in data.get('version_requirements', {}).items():
                for req_data in reqs_data:
                    requirement = VersionRequirement(
                        package_name=req_data['package_name'],
                        version_spec=req_data['version_spec'],
                        dependency_type=DependencyType(req_data['dependency_type']),
                        optional=req_data.get('optional', False),
                        reason=req_data.get('reason'),
                        alternatives=req_data.get('alternatives', []),
                        metadata=req_data.get('metadata', {})
                    )
                    self.add_version_requirement(plugin_id, requirement)
            
            # Import known issues
            for plugin_id, issues_data in data.get('known_issues', {}).items():
                for issue_data in issues_data:
                    issue = CompatibilityIssue(
                        plugin_id=plugin_id,
                        issue_type=issue_data['issue_type'],
                        severity=issue_data['severity'],
                        description=issue_data['description'],
                        suggestion=issue_data.get('suggestion'),
                        affected_version=issue_data.get('affected_version'),
                        required_version=issue_data.get('required_version'),
                        metadata=issue_data.get('metadata', {})
                    )
                    self.add_known_issue(plugin_id, issue)
    
    def _check_framework_version(self, metadata: PluginMetadata) -> List[CompatibilityIssue]:
        """Check framework version compatibility."""
        issues = []
        
        try:
            # Parse framework version requirements
            if metadata.min_framework_version:
                if not self._is_version_compatible(
                    self.framework_version, 
                    metadata.min_framework_version
                ):
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="framework_version_incompatible",
                        severity="error",
                        description=f"Framework version {self.framework_version} is incompatible with minimum required version {metadata.min_framework_version}",
                        suggestion=f"Upgrade framework to version {metadata.min_framework_version} or higher",
                        affected_version=self.framework_version,
                        required_version=metadata.min_framework_version
                    ))
            
            # Check maximum framework version
            if metadata.max_framework_version:
                if not self._is_version_compatible(
                    metadata.max_framework_version,
                    self.framework_version
                ):
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="framework_version_too_high",
                        severity="warning",
                        description=f"Framework version {self.framework_version} is newer than maximum supported version {metadata.max_framework_version}",
                        suggestion=f"Consider upgrading plugin or downgrade framework to {metadata.max_framework_version}",
                        affected_version=self.framework_version,
                        required_version=metadata.max_framework_version
                    ))
        
        except Exception as e:
            issues.append(CompatibilityIssue(
                plugin_id=metadata.id,
                issue_type="framework_version_check_error",
                severity="warning",
                description=f"Framework version check failed: {str(e)}"
            ))
        
        return issues
    
    def _check_python_version(self, metadata: PluginMetadata) -> List[CompatibilityIssue]:
        """Check Python version compatibility."""
        issues = []
        
        try:
            python_version = self._get_python_version()
            
            # Check minimum Python version (default to 3.8 if not specified)
            min_python = metadata.metadata.get('min_python_version', '3.8')
            if not self._is_version_compatible(python_version, min_python):
                issues.append(CompatibilityIssue(
                    plugin_id=metadata.id,
                    issue_type="python_version_incompatible",
                    severity="error",
                    description=f"Python version {python_version} is incompatible with minimum required version {min_python}",
                    suggestion=f"Upgrade Python to version {min_python} or higher",
                    affected_version=python_version,
                    required_version=min_python
                ))
            
            # Check maximum Python version
            max_python = metadata.metadata.get('max_python_version')
            if max_python and not self._is_version_compatible(max_python, python_version):
                issues.append(CompatibilityIssue(
                    plugin_id=metadata.id,
                    issue_type="python_version_too_high",
                    severity="warning",
                    description=f"Python version {python_version} is newer than maximum supported version {max_python}",
                    suggestion=f"Consider upgrading plugin or downgrade Python to {max_python}",
                    affected_version=python_version,
                    required_version=max_python
                ))
        
        except Exception as e:
            issues.append(CompatibilityIssue(
                plugin_id=metadata.id,
                issue_type="python_version_check_error",
                severity="warning",
                description=f"Python version check failed: {str(e)}"
            ))
        
        return issues
    
    def _check_plugin_dependencies(self, metadata: PluginMetadata) -> List[CompatibilityIssue]:
        """Check plugin dependencies."""
        issues = []
        
        try:
            for dep_plugin_id in metadata.dependencies:
                # Check if dependency plugin exists
                dep_plugin = self.registry.get_plugin(dep_plugin_id)
                if not dep_plugin:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="missing_plugin_dependency",
                        severity="error",
                        description=f"Required plugin dependency {dep_plugin_id} not found",
                        suggestion=f"Install or enable plugin {dep_plugin_id}"
                    ))
                    continue
                
                # Check dependency compatibility
                dep_result = self.check_plugin_compatibility(dep_plugin_id)
                if dep_result.status == CompatibilityStatus.INCOMPATIBLE:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="incompatible_plugin_dependency",
                        severity="error",
                        description=f"Plugin dependency {dep_plugin_id} is incompatible",
                        suggestion=f"Update or replace plugin {dep_plugin_id} with a compatible version"
                    ))
        
        except Exception as e:
            issues.append(CompatibilityIssue(
                plugin_id=metadata.id,
                issue_type="plugin_dependency_check_error",
                severity="warning",
                description=f"Plugin dependency check failed: {str(e)}"
            ))
        
        return issues
    
    def _check_library_dependencies(self, metadata: PluginMetadata) -> List[CompatibilityIssue]:
        """Check library dependencies."""
        issues = []
        
        try:
            # Get library requirements from metadata
            library_requirements = metadata.metadata.get('library_requirements', {})
            
            for lib_name, version_spec in library_requirements.items():
                try:
                    # Try to import the library
                    module = __import__(lib_name)
                    
                    # Get library version
                    lib_version = getattr(module, '__version__', 'unknown')
                    
                    # Check version compatibility
                    if version_spec and not self._is_version_compatible(lib_version, version_spec):
                        issues.append(CompatibilityIssue(
                            plugin_id=metadata.id,
                            issue_type="library_version_incompatible",
                            severity="error",
                            description=f"Library {lib_name} version {lib_version} is incompatible with required version {version_spec}",
                            suggestion=f"Upgrade or downgrade {lib_name} to version {version_spec}",
                            affected_version=lib_version,
                            required_version=version_spec
                        ))
                
                except ImportError:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="missing_library_dependency",
                        severity="error",
                        description=f"Required library {lib_name} not found",
                        suggestion=f"Install library {lib_name}: pip install {lib_name}"
                    ))
                except Exception as e:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="library_check_error",
                        severity="warning",
                        description=f"Library {lib_name} check failed: {str(e)}"
                    ))
        
        except Exception as e:
            issues.append(CompatibilityIssue(
                plugin_id=metadata.id,
                issue_type="library_dependency_check_error",
                severity="warning",
                description=f"Library dependency check failed: {str(e)}"
            ))
        
        return issues
    
    def _check_system_requirements(self, metadata: PluginMetadata) -> List[CompatibilityIssue]:
        """Check system requirements."""
        issues = []
        
        try:
            # Get system requirements from metadata
            system_requirements = metadata.metadata.get('system_requirements', {})
            
            # Check operating system
            required_os = system_requirements.get('os')
            if required_os:
                import platform
                current_os = platform.system().lower()
                if current_os not in [os.lower() for os in required_os.split(',')]:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="os_incompatible",
                        severity="error",
                        description=f"Operating system {current_os} is not supported. Required: {required_os}",
                        suggestion=f"Use a supported operating system: {required_os}"
                    ))
            
            # Check architecture
            required_arch = system_requirements.get('architecture')
            if required_arch:
                current_arch = platform.machine().lower()
                if current_arch not in [arch.lower() for arch in required_arch.split(',')]:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="architecture_incompatible",
                        severity="error",
                        description=f"Architecture {current_arch} is not supported. Required: {required_arch}",
                        suggestion=f"Use a supported architecture: {required_arch}"
                    ))
            
            # Check memory requirements
            required_memory_mb = system_requirements.get('memory_mb')
            if required_memory_mb:
                try:
                    import psutil
                    available_memory_mb = psutil.virtual_memory().available // (1024 * 1024)
                    
                    if available_memory_mb < required_memory_mb:
                        issues.append(CompatibilityIssue(
                            plugin_id=metadata.id,
                            issue_type="insufficient_memory",
                            severity="warning",
                            description=f"Available memory {available_memory_mb}MB is less than required {required_memory_mb}MB",
                            suggestion=f"Increase available memory to at least {required_memory_mb}MB"
                        ))
                except ImportError:
                    issues.append(CompatibilityIssue(
                        plugin_id=metadata.id,
                        issue_type="memory_check_unavailable",
                        severity="info",
                        description="Cannot check memory requirements (psutil not available)"
                    ))
        
        except Exception as e:
            issues.append(CompatibilityIssue(
                plugin_id=metadata.id,
                issue_type="system_requirement_check_error",
                severity="warning",
                description=f"System requirement check failed: {str(e)}"
            ))
        
        return issues
    
    def _determine_compatibility_status(self, issues: List[CompatibilityIssue]) -> CompatibilityStatus:
        """Determine overall compatibility status from issues."""
        if not issues:
            return CompatibilityStatus.COMPATIBLE
        
        # Check for errors
        error_issues = [issue for issue in issues if issue.severity == "error"]
        if error_issues:
            return CompatibilityStatus.INCOMPATIBLE
        
        # Check for warnings
        warning_issues = [issue for issue in issues if issue.severity == "warning"]
        if warning_issues:
            return CompatibilityStatus.WARNING
        
        return CompatibilityStatus.COMPATIBLE
    
    def _generate_suggestions(self, issues: List[CompatibilityIssue], 
                            metadata: PluginMetadata) -> List[str]:
        """Generate suggestions from compatibility issues."""
        suggestions = []
        
        # Add suggestions from issues
        for issue in issues:
            if issue.suggestion:
                suggestions.append(issue.suggestion)
        
        # Add general suggestions
        if issues:
            suggestions.append("Review plugin documentation for installation requirements")
            suggestions.append("Consider updating to the latest version of the plugin")
        
        return suggestions
    
    def _is_version_compatible(self, current_version: str, required_version: str) -> bool:
        """Check if current version satisfies required version specification."""
        try:
            # Parse version specification
            if '>=' in required_version:
                min_version = required_version.replace('>=', '').strip()
                return version.parse(current_version) >= version.parse(min_version)
            elif '<=' in required_version:
                max_version = required_version.replace('<=', '').strip()
                return version.parse(current_version) <= version.parse(max_version)
            elif '>' in required_version:
                min_version = required_version.replace('>', '').strip()
                return version.parse(current_version) > version.parse(min_version)
            elif '<' in required_version:
                max_version = required_version.replace('<', '').strip()
                return version.parse(current_version) < version.parse(max_version)
            elif '==' in required_version:
                exact_version = required_version.replace('==', '').strip()
                return version.parse(current_version) == version.parse(exact_version)
            else:
                # Exact match
                return version.parse(current_version) == version.parse(required_version)
        except Exception:
            # If parsing fails, assume incompatible
            return False
    
    def _get_python_version(self) -> str:
        """Get current Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _update_statistics(self, status: CompatibilityStatus, check_time_ms: float) -> None:
        """Update compatibility statistics."""
        with self._lock:
            self._stats['total_checks'] += 1
            self._stats['check_time_ms'] += check_time_ms
            self._stats['average_check_time_ms'] = (
                self._stats['check_time_ms'] / self._stats['total_checks']
            )
            
            if status == CompatibilityStatus.COMPATIBLE:
                self._stats['compatible_count'] += 1
            elif status == CompatibilityStatus.INCOMPATIBLE:
                self._stats['incompatible_count'] += 1
            elif status == CompatibilityStatus.WARNING:
                self._stats['warning_count'] += 1
            else:
                self._stats['unknown_count'] += 1


# Global plugin compatibility checker instance
_plugin_compatibility_checker = PluginCompatibilityChecker()


# Convenience functions
def check_plugin_compatibility(plugin_id: str) -> CompatibilityResult:
    """Check compatibility of a plugin."""
    return _plugin_compatibility_checker.check_plugin_compatibility(plugin_id)


def check_all_plugins_compatibility() -> Dict[str, CompatibilityResult]:
    """Check compatibility of all plugins."""
    return _plugin_compatibility_checker.check_all_plugins_compatibility()


def add_version_requirement(plugin_id: str, requirement: VersionRequirement) -> None:
    """Add a version requirement for a plugin."""
    _plugin_compatibility_checker.add_version_requirement(plugin_id, requirement)


def get_version_requirements(plugin_id: str) -> List[VersionRequirement]:
    """Get version requirements for a plugin."""
    return _plugin_compatibility_checker.get_version_requirements(plugin_id)


def add_known_issue(plugin_id: str, issue: CompatibilityIssue) -> None:
    """Add a known compatibility issue."""
    _plugin_compatibility_checker.add_known_issue(plugin_id, issue)


def get_compatibility_statistics() -> Dict[str, Any]:
    """Get compatibility statistics."""
    return _plugin_compatibility_checker.get_statistics()


def export_compatibility_data() -> Dict[str, Any]:
    """Export compatibility data."""
    return _plugin_compatibility_checker.export_compatibility_data()


def import_compatibility_data(data: Dict[str, Any]) -> None:
    """Import compatibility data."""
    _plugin_compatibility_checker.import_compatibility_data(data)


def get_plugin_compatibility_checker() -> PluginCompatibilityChecker:
    """Get the global plugin compatibility checker."""
    return _plugin_compatibility_checker
