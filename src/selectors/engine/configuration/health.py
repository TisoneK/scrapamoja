"""
Configuration system health checks and diagnostics.

This module provides comprehensive health monitoring for the YAML-based
selector configuration system, including validation, performance, and integrity checks.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from ...models.selector_config import (
    SelectorConfiguration,
    ValidationResult,
    ConfigurationState
)
from .validator import ConfigurationValidator
from .inheritance import InheritanceResolver
from .index import SemanticIndex
from .watcher import ConfigurationWatcher


class HealthCheckResult:
    """Result of a health check."""
    
    def __init__(self, name: str, status: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.status = status  # "healthy", "warning", "critical"
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ConfigurationHealthChecker:
    """Comprehensive health checker for the configuration system."""
    
    def __init__(self):
        """Initialize the health checker."""
        self.logger = logging.getLogger(__name__)
        self.validator = ConfigurationValidator()
    
    async def run_comprehensive_health_check(self, 
                                            config_root: Path,
                                            loaded_configurations: Optional[Dict[str, SelectorConfiguration]] = None,
                                            semantic_index: Optional[SemanticIndex] = None,
                                            inheritance_resolver: Optional[InheritanceResolver] = None,
                                            config_watcher: Optional[ConfigurationWatcher] = None) -> Dict[str, Any]:
        """Run comprehensive health check of the configuration system."""
        health_report = {
            "overall_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {
                "total_checks": 0,
                "healthy": 0,
                "warnings": 0,
                "critical": 0
            },
            "recommendations": []
        }
        
        # Run all health checks
        checks = [
            ("file_system", self._check_file_system_health, config_root),
            ("configuration_integrity", self._check_configuration_integrity, loaded_configurations),
            ("semantic_index", self._check_semantic_index_health, semantic_index),
            ("inheritance_system", self._check_inheritance_system_health, inheritance_resolver),
            ("file_watcher", self._check_file_watcher_health, config_watcher),
            ("performance", self._check_performance_health, loaded_configurations, semantic_index),
            ("security", self._check_security_health, config_root),
            ("compliance", self._check_compliance_health)
        ]
        
        for check_name, check_func, *args in checks:
            try:
                result = await check_func(*args) if asyncio.iscoroutinefunction(check_func) else check_func(*args)
                health_report["checks"][check_name] = result.to_dict()
                health_report["summary"]["total_checks"] += 1
                
                if result.status == "healthy":
                    health_report["summary"]["healthy"] += 1
                elif result.status == "warning":
                    health_report["summary"]["warnings"] += 1
                    if health_report["overall_status"] == "healthy":
                        health_report["overall_status"] = "warning"
                elif result.status == "critical":
                    health_report["summary"]["critical"] += 1
                    health_report["overall_status"] = "critical"
                
            except Exception as e:
                self.logger.error(f"Health check '{check_name}' failed: {e}")
                error_result = HealthCheckResult(
                    check_name, "critical", f"Health check failed: {str(e)}"
                )
                health_report["checks"][check_name] = error_result.to_dict()
                health_report["summary"]["total_checks"] += 1
                health_report["summary"]["critical"] += 1
                health_report["overall_status"] = "critical"
        
        # Generate recommendations
        health_report["recommendations"] = self._generate_recommendations(health_report["checks"])
        
        return health_report
    
    def _check_file_system_health(self, config_root: Path) -> HealthCheckResult:
        """Check file system health."""
        details = {}
        warnings = []
        
        if not config_root.exists():
            return HealthCheckResult(
                "file_system", "critical", f"Configuration root directory does not exist: {config_root}"
            )
        
        if not config_root.is_dir():
            return HealthCheckResult(
                "file_system", "critical", f"Configuration root is not a directory: {config_root}"
            )
        
        # Check directory permissions
        try:
            test_file = config_root / ".health_check"
            test_file.write_text("test")
            test_file.unlink()
            details["permissions"] = "writable"
        except Exception as e:
            warnings.append(f"Directory permission issue: {e}")
            details["permissions"] = "read_only"
        
        # Check for YAML files
        yaml_files = list(config_root.rglob("*.yaml"))
        details["yaml_files_count"] = len(yaml_files)
        
        if len(yaml_files) == 0:
            warnings.append("No YAML configuration files found")
        
        # Check for context files
        context_files = list(config_root.rglob("_context.yaml"))
        details["context_files_count"] = len(context_files)
        
        # Check directory structure
        expected_dirs = ["main", "fixture", "match"]
        missing_dirs = []
        for dir_name in expected_dirs:
            dir_path = config_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            warnings.append(f"Missing expected directories: {missing_dirs}")
        
        details["missing_directories"] = missing_dirs
        
        status = "healthy" if not warnings else "warning"
        message = "File system is healthy" if not warnings else f"File system has {len(warnings)} warnings"
        
        return HealthCheckResult("file_system", status, message, details)
    
    def _check_configuration_integrity(self, loaded_configurations: Optional[Dict[str, SelectorConfiguration]]) -> HealthCheckResult:
        """Check configuration integrity."""
        if not loaded_configurations:
            return HealthCheckResult(
                "configuration_integrity", "warning", "No configurations loaded"
            )
        
        details = {
            "total_configurations": len(loaded_configurations),
            "validation_errors": 0,
            "validation_warnings": 0,
            "invalid_configurations": []
        }
        
        total_errors = 0
        total_warnings = 0
        
        for file_path, config in loaded_configurations.items():
            validation_result = self.validator.validate_configuration(config)
            
            if not validation_result.is_valid:
                details["invalid_configurations"].append(file_path)
                total_errors += len(validation_result.errors)
            else:
                total_warnings += len(validation_result.warnings)
        
        details["validation_errors"] = total_errors
        details["validation_warnings"] = total_warnings
        
        if total_errors > 0:
            return HealthCheckResult(
                "configuration_integrity", "critical", 
                f"{total_errors} configuration validation errors found", details
            )
        elif total_warnings > 0:
            return HealthCheckResult(
                "configuration_integrity", "warning", 
                f"{total_warnings} configuration warnings found", details
            )
        else:
            return HealthCheckResult(
                "configuration_integrity", "healthy", 
                "All configurations are valid", details
            )
    
    def _check_semantic_index_health(self, semantic_index: Optional[SemanticIndex]) -> HealthCheckResult:
        """Check semantic index health."""
        if not semantic_index:
            return HealthCheckResult(
                "semantic_index", "warning", "Semantic index not initialized"
            )
        
        details = {}
        warnings = []
        
        # Get index statistics
        stats = semantic_index.get_index_stats()
        details.update(stats)
        
        # Check for conflicts
        conflicts = semantic_index.find_conflicts()
        details["conflicts_count"] = len(conflicts)
        
        if conflicts:
            warnings.append(f"Found {len(conflicts)} selector name conflicts")
            details["conflicts"] = list(conflicts.keys())
        
        # Check index size
        if stats["total_selectors"] == 0:
            warnings.append("No selectors indexed")
        
        # Check available contexts
        contexts = semantic_index.get_available_contexts()
        details["available_contexts"] = contexts
        
        status = "healthy" if not warnings else "warning"
        message = "Semantic index is healthy" if not warnings else f"Semantic index has {len(warnings)} warnings"
        
        return HealthCheckResult("semantic_index", status, message, details)
    
    def _check_inheritance_system_health(self, inheritance_resolver: Optional[InheritanceResolver]) -> HealthCheckResult:
        """Check inheritance system health."""
        if not inheritance_resolver:
            return HealthCheckResult(
                "inheritance_system", "warning", "Inheritance resolver not initialized"
            )
        
        details = {}
        warnings = []
        
        # Get cache statistics
        cache_stats = inheritance_resolver.get_cache_stats()
        details.update(cache_stats)
        
        # Check cache size
        if cache_stats["cached_chains"] > 1000:
            warnings.append("Large inheritance cache size - consider cleanup")
        
        # Check for stale cache entries
        if cache_stats["cached_chains"] > 0:
            details["cache_health"] = "active"
        else:
            details["cache_health"] = "empty"
        
        status = "healthy" if not warnings else "warning"
        message = "Inheritance system is healthy" if not warnings else f"Inheritance system has {len(warnings)} warnings"
        
        return HealthCheckResult("inheritance_system", status, message, details)
    
    def _check_file_watcher_health(self, config_watcher: Optional[ConfigurationWatcher]) -> HealthCheckResult:
        """Check file watcher health."""
        if not config_watcher:
            return HealthCheckResult(
                "file_watcher", "warning", "File watcher not initialized"
            )
        
        details = {}
        warnings = []
        
        # Check if watcher is active
        if hasattr(config_watcher, 'is_watching'):
            details["is_watching"] = config_watcher.is_watching
            if not config_watcher.is_watching:
                warnings.append("File watcher is not active")
        else:
            warnings.append("File watcher status unknown")
        
        # Get watched files
        if hasattr(config_watcher, 'get_watched_files'):
            watched_files = config_watcher.get_watched_files()
            details["watched_files_count"] = len(watched_files)
            
            if len(watched_files) == 0:
                warnings.append("No files being watched")
        
        # Get validation result
        if hasattr(config_watcher, 'validate_watch_configuration'):
            validation = config_watcher.validate_watch_configuration()
            details["watch_validation"] = validation
            if not validation["valid"]:
                warnings.append("File watcher configuration issues")
        
        status = "healthy" if not warnings else "warning"
        message = "File watcher is healthy" if not warnings else f"File watcher has {len(warnings)} warnings"
        
        return HealthCheckResult("file_watcher", status, message, details)
    
    def _check_performance_health(self, 
                                 loaded_configurations: Optional[Dict[str, SelectorConfiguration]],
                                 semantic_index: Optional[SemanticIndex]) -> HealthCheckResult:
        """Check performance health."""
        details = {}
        warnings = []
        
        # Check configuration count
        if loaded_configurations:
            details["configurations_count"] = len(loaded_configurations)
            if len(loaded_configurations) > 500:
                warnings.append("Large number of configurations may impact performance")
        
        # Check index size
        if semantic_index:
            stats = semantic_index.get_index_stats()
            details["index_size"] = stats["total_selectors"]
            
            if stats["total_selectors"] > 10000:
                warnings.append("Large semantic index may impact lookup performance")
        
        # Memory usage estimation
        estimated_memory = 0
        if loaded_configurations:
            estimated_memory += len(loaded_configurations) * 1024  # ~1KB per config
        if semantic_index:
            estimated_memory += details.get("index_size", 0) * 512  # ~512B per selector
        
        details["estimated_memory_kb"] = estimated_memory
        
        if estimated_memory > 100 * 1024:  # >100MB
            warnings.append("High memory usage detected")
        
        status = "healthy" if not warnings else "warning"
        message = "Performance is healthy" if not warnings else f"Performance has {len(warnings)} warnings"
        
        return HealthCheckResult("performance", status, message, details)
    
    def _check_security_health(self, config_root: Path) -> HealthCheckResult:
        """Check security health."""
        details = {}
        warnings = []
        
        # Check for sensitive files
        sensitive_patterns = [".key", ".pem", ".crt", "password", "secret", "token"]
        sensitive_files = []
        
        for pattern in sensitive_patterns:
            files = list(config_root.rglob(f"*{pattern}*"))
            sensitive_files.extend(files)
        
        details["sensitive_files_count"] = len(sensitive_files)
        
        if sensitive_files:
            warnings.append(f"Found {len(sensitive_files)} potentially sensitive files")
        
        # Check file permissions
        try:
            test_file = config_root / ".security_check"
            test_file.write_text("test")
            test_file.unlink()
            details["write_permissions"] = True
        except Exception:
            details["write_permissions"] = False
            warnings.append("Limited write permissions detected")
        
        # Check for executable files
        executable_files = list(config_root.rglob("*.exe"))
        details["executable_files_count"] = len(executable_files)
        
        if executable_files:
            warnings.append(f"Found {len(executable_files)} executable files")
        
        status = "healthy" if not warnings else "warning"
        message = "Security is healthy" if not warnings else f"Security has {len(warnings)} warnings"
        
        return HealthCheckResult("security", status, message, details)
    
    def _check_compliance_health(self) -> HealthCheckResult:
        """Check compliance with system requirements."""
        details = {}
        warnings = []
        
        # Check for required modules
        required_modules = ["yaml", "watchdog", "pathlib", "datetime", "logging"]
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        details["missing_modules"] = missing_modules
        
        if missing_modules:
            warnings.append(f"Missing required modules: {missing_modules}")
        
        # Check Python version (basic check)
        import sys
        details["python_version"] = sys.version_info[:2]
        if sys.version_info < (3, 8):
            warnings.append("Python version < 3.8 may have compatibility issues")
        
        status = "healthy" if not warnings else "warning"
        message = "Compliance is healthy" if not warnings else f"Compliance has {len(warnings)} warnings"
        
        return HealthCheckResult("compliance", status, message, details)
    
    def _generate_recommendations(self, checks: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate health recommendations based on check results."""
        recommendations = []
        
        for check_name, check_result in checks.items():
            if check_result["status"] == "warning":
                recommendations.append(f"Address {check_name} warnings")
            elif check_result["status"] == "critical":
                recommendations.append(f"Fix {check_name} issues immediately")
        
        # General recommendations
        critical_count = sum(1 for check in checks.values() if check["status"] == "critical")
        warning_count = sum(1 for check in checks.values() if check["status"] == "warning")
        
        if critical_count == 0 and warning_count == 0:
            recommendations.append("System is healthy - continue monitoring")
        elif critical_count == 0 and warning_count <= 2:
            recommendations.append("System is mostly healthy - address warnings soon")
        else:
            recommendations.append("System needs attention - address critical issues first")
        
        return recommendations


async def run_quick_health_check(config_root: Path) -> Dict[str, Any]:
    """Run a quick health check focusing on critical issues."""
    checker = ConfigurationHealthChecker()
    
    # Run only critical checks
    critical_checks = [
        ("file_system", checker._check_file_system_health, config_root),
        ("compliance", checker._check_compliance_health)
    ]
    
    quick_report = {
        "overall_status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "summary": {"total_checks": 0, "healthy": 0, "warnings": 0, "critical": 0}
    }
    
    for check_name, check_func in critical_checks:
        result = check_func()
        quick_report["checks"][check_name] = result.to_dict()
        quick_report["summary"]["total_checks"] += 1
        
        if result.status == "healthy":
            quick_report["summary"]["healthy"] += 1
        elif result.status == "warning":
            quick_report["summary"]["warnings"] += 1
            if quick_report["overall_status"] == "healthy":
                quick_report["overall_status"] = "warning"
        elif result.status == "critical":
            quick_report["summary"]["critical"] += 1
            quick_report["overall_status"] = "critical"
    
    return quick_report
