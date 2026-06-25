"""
Deprecation warnings and monitoring for old template usage.

This module provides comprehensive deprecation warnings, monitoring,
and migration assistance for deprecated template patterns.
"""

import warnings
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeprecationRecord:
    """Record of a deprecation warning."""
    timestamp: float
    warning_type: str
    old_pattern: str
    new_pattern: str
    file_path: str
    line_number: int
    stack_trace: str
    version: str
    severity: str = "warning"


class TemplateDeprecationWarning(UserWarning):
    """Warning for deprecated template patterns."""
    pass


class CriticalDeprecationWarning(UserWarning):
    """Warning for critically deprecated patterns that will break soon."""
    pass


class DeprecationMonitor:
    """Monitors and tracks deprecation warnings."""
    
    def __init__(self, site_path: str = None):
        """
        Initialize deprecation monitor.
        
        Args:
            site_path: Path to the site directory
        """
        self.site_path = Path(site_path) if site_path else None
        self.records: List[DeprecationRecord] = []
        self.warning_counts: Dict[str, int] = {}
        self.critical_issues: List[DeprecationRecord] = []
        self.setup_warnings()
    
    def setup_warnings(self):
        """Setup warning filters and handlers."""
        # Setup custom warning handler
        def warning_handler(message, category, filename, lineno, file=None, line=None):
            if issubclass(category, (TemplateDeprecationWarning, CriticalDeprecationWarning)):
                self.record_warning(str(message), category.__name__, filename, lineno)
        
        # Install warning handler
        warnings.showwarning = warning_handler
        
        # Setup warning filters
        warnings.filterwarnings('always', category=TemplateDeprecationWarning)
        warnings.filterwarnings('always', category=CriticalDeprecationWarning)
    
    def record_warning(self, message: str, category: str, filename: str, lineno: int):
        """Record a deprecation warning."""
        # Parse warning message to extract patterns
        old_pattern, new_pattern = self._parse_warning_message(message)
        
        record = DeprecationRecord(
            timestamp=time.time(),
            warning_type=category,
            old_pattern=old_pattern,
            new_pattern=new_pattern,
            file_path=filename,
            line_number=lineno,
            stack_trace=traceback.format_stack(),
            version=self._get_version_from_message(message),
            severity="critical" if "critical" in category.lower() else "warning"
        )
        
        self.records.append(record)
        self.warning_counts[old_pattern] = self.warning_counts.get(old_pattern, 0) + 1
        
        if record.severity == "critical":
            self.critical_issues.append(record)
        
        # Log the warning
        log_method = logger.error if record.severity == "critical" else logger.warning
        log_method(f"Template Deprecation: {message} (at {filename}:{lineno})")
    
    def _parse_warning_message(self, message: str) -> tuple:
        """Parse warning message to extract old and new patterns."""
        # Try to extract patterns from common warning formats
        if "is deprecated" in message and "use" in message:
            parts = message.split("use")
            old_pattern = parts[0].split("is deprecated")[0].strip()
            new_pattern = parts[1].strip(" .")
            return old_pattern, new_pattern
        
        return "unknown", "unknown"
    
    def _get_version_from_message(self, message: str) -> str:
        """Extract version from warning message."""
        if "version" in message.lower():
            import re
            match = re.search(r'version\s+(\d+\.\d+)', message, re.IGNORECASE)
            if match:
                return match.group(1)
        return "unknown"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get deprecation summary."""
        return {
            'total_warnings': len(self.records),
            'unique_patterns': len(self.warning_counts),
            'critical_issues': len(self.critical_issues),
            'warning_counts': self.warning_counts.copy(),
            'most_common': max(self.warning_counts.items(), key=lambda x: x[1]) if self.warning_counts else None,
            'files_affected': len(set(r.file_path for r in self.records))
        }
    
    def get_migration_plan(self) -> Dict[str, Any]:
        """Generate migration plan based on deprecation records."""
        plan = {
            'priority_issues': [],
            'recommended_actions': [],
            'estimated_effort': 'low',
            'breaking_changes': []
        }
        
        # Analyze critical issues
        for record in self.critical_issues:
            plan['priority_issues'].append({
                'pattern': record.old_pattern,
                'file': record.file_path,
                'line': record.line_number,
                'action': f"Replace with {record.new_pattern}"
            })
        
        # Estimate effort based on warning counts
        total_warnings = len(self.records)
        if total_warnings > 20:
            plan['estimated_effort'] = 'high'
        elif total_warnings > 10:
            plan['estimated_effort'] = 'medium'
        
        # Generate recommended actions
        if self.critical_issues:
            plan['recommended_actions'].append("Address critical deprecations first")
            plan['breaking_changes'].append("Critical deprecations will break in next version")
        
        if self.warning_counts:
            plan['recommended_actions'].append("Run migration tool for automated updates")
            plan['recommended_actions'].append("Update import statements")
        
        return plan


# Global deprecation monitor
_deprecation_monitor = None


def get_deprecation_monitor() -> DeprecationMonitor:
    """Get the global deprecation monitor."""
    global _deprecation_monitor
    if _deprecation_monitor is None:
        _deprecation_monitor = DeprecationMonitor()
    return _deprecation_monitor


def deprecated(old_name: str, new_name: str, version: str = "2.0", 
               critical: bool = False, migration_guide: str = None):
    """
    Decorator to mark functions or classes as deprecated.
    
    Args:
        old_name: Name of the deprecated item
        new_name: Name of the replacement item
        version: Version when the item will be removed
        critical: Whether this is a critical deprecation
        migration_guide: Path to migration guide
    """
    def decorator(func_or_class):
        @wraps(func_or_class)
        def wrapper(*args, **kwargs):
            warning_class = CriticalDeprecationWarning if critical else TemplateDeprecationWarning
            
            message = (
                f"{old_name} is deprecated and will be removed in version {version}. "
                f"Use {new_name} instead."
            )
            
            if migration_guide:
                message += f" See {migration_guide} for migration instructions."
            
            warnings.warn(message, warning_class, stacklevel=2)
            return func_or_class(*args, **kwargs)
        
        return wrapper
    
    return decorator


def deprecated_pattern(old_pattern: str, new_pattern: str, version: str = "2.0",
                     critical: bool = False, file_hint: str = None):
    """
    Emit a deprecation warning for a pattern usage.
    
    Args:
        old_pattern: Description of the deprecated pattern
        new_pattern: Description of the new pattern
        version: Version when the pattern will be removed
        critical: Whether this is a critical deprecation
        file_hint: Hint about which file to check
    """
    warning_class = CriticalDeprecationWarning if critical else TemplateDeprecationWarning
    
    message = (
        f"Pattern '{old_pattern}' is deprecated and will be removed in version {version}. "
        f"Use '{new_pattern}' instead."
    )
    
    if file_hint:
        message += f" Check {file_hint} for details."
    
    warnings.warn(message, warning_class, stacklevel=3)


# Specific deprecation warnings for template patterns

def warn_legacy_flow_class(class_name: str, base_class: str):
    """Warn about legacy flow class usage."""
    deprecated_pattern(
        f"Class {class_name}",
        f"Base{base_class}",
        version="2.0",
        critical=False,
        file_hint="UPGRADE_GUIDE.md"
    )


def warn_simple_template():
    """Warn about simple template usage in complex scenarios."""
    deprecated_pattern(
        "Simple template pattern with multiple flows",
        "Standard or Complex pattern with domain separation",
        version="2.1",
        critical=False,
        file_hint="UPGRADE_GUIDE.md"
    )


def warn_legacy_imports(import_path: str):
    """Warn about legacy import paths."""
    deprecated_pattern(
        f"Import path '{import_path}'",
        "New import paths from base_flows module",
        version="2.0",
        critical=True,
        file_hint="compatibility.py"
    )


def warn_missing_base_classes():
    """Warn about flows not inheriting from base classes."""
    deprecated_pattern(
        "Flow classes without base class inheritance",
        "Inherit from appropriate Base* class",
        version="2.0",
        critical=True,
        file_hint="base_flows.py"
    )


def warn_hardcoded_selectors():
    """Warn about hardcoded selectors without configuration."""
    deprecated_pattern(
        "Hardcoded selectors without configuration",
        "Configurable selectors with validation",
        version="2.1",
        critical=False,
        file_hint="flow_templates.py"
    )


def warn_synchronous_operations():
    """Warn about synchronous operations in async context."""
    deprecated_pattern(
        "Synchronous operations in async flows",
        "Async/await pattern throughout",
        version="2.0",
        critical=True,
        file_hint="base_flows.py"
    )


# Template analysis functions

def analyze_template_usage(file_path: str) -> Dict[str, Any]:
    """
    Analyze a file for deprecated template usage.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Analysis results with deprecation issues
    """
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Check for deprecated patterns
        for i, line in enumerate(lines, 1):
            # Check for legacy class names
            if re.search(r'class\s+(Navigation|Extraction|Filtering|Authentication)Flow\s*\(', line):
                if 'Base' not in line:
                    issues.append({
                        'line': i,
                        'type': 'legacy_class',
                        'message': f"Legacy flow class at line {i}",
                        'severity': 'warning'
                    })
            
            # Check for legacy imports
            if re.search(r'from\s+(scrapamoja\.flows|flows\.base)', line):
                issues.append({
                    'line': i,
                    'type': 'legacy_import',
                    'message': f"Legacy import at line {i}",
                    'severity': 'critical'
                })
            
            # Check for missing base classes
            if re.search(r'class\s+\w+Flow\s*\([^)]*\):', line):
                if not any(base in line for base in ['BaseNavigationFlow', 'BaseExtractionFlow', 
                                                   'BaseFilteringFlow', 'BaseAuthenticationFlow']):
                    issues.append({
                        'line': i,
                        'type': 'missing_base_class',
                        'message': f"Missing base class at line {i}",
                        'severity': 'critical'
                    })
            
            # Check for hardcoded selectors
            if re.search(r'["\']#?\w+\.\w+["\']', line) and 'selector' in line.lower():
                issues.append({
                    'line': i,
                    'type': 'hardcoded_selector',
                    'message': f"Hardcoded selector at line {i}",
                    'severity': 'info'
                })
        
        return {
            'file_path': file_path,
            'issues': issues,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i['severity'] == 'critical']),
            'warning_issues': len([i for i in issues if i['severity'] == 'warning'])
        }
        
    except Exception as e:
        return {
            'file_path': file_path,
            'issues': [],
            'error': str(e)
        }


def analyze_site_deprecations(site_path: str) -> Dict[str, Any]:
    """
    Analyze entire site for deprecation issues.
    
    Args:
        site_path: Path to the site directory
        
    Returns:
        Comprehensive deprecation analysis
    """
    site_path = Path(site_path)
    all_issues = []
    file_analyses = []
    
    # Analyze Python files
    for py_file in site_path.rglob('*.py'):
        if py_file.name in ['__pycache__', '*.pyc']:
            continue
        
        analysis = analyze_template_usage(str(py_file))
        file_analyses.append(analysis)
        all_issues.extend(analysis.get('issues', []))
    
    # Summarize issues
    summary = {
        'site_path': str(site_path),
        'total_files': len(file_analyses),
        'files_with_issues': len([f for f in file_analyses if f.get('issues')]),
        'total_issues': len(all_issues),
        'critical_issues': len([i for i in all_issues if i['severity'] == 'critical']),
        'warning_issues': len([i for i in all_issues if i['severity'] == 'warning']),
        'issue_types': {},
        'files': file_analyses
    }
    
    # Count issue types
    for issue in all_issues:
        issue_type = issue['type']
        summary['issue_types'][issue_type] = summary['issue_types'].get(issue_type, 0) + 1
    
    # Generate recommendations
    summary['recommendations'] = _generate_recommendations(summary)
    
    return summary


def _generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on analysis."""
    recommendations = []
    
    if analysis['critical_issues'] > 0:
        recommendations.append("Address critical deprecation issues immediately")
        recommendations.append("Run migration tool to automatically fix imports")
    
    if analysis['warning_issues'] > 5:
        recommendations.append("Consider upgrading to newer template patterns")
    
    issue_types = analysis['issue_types']
    
    if 'legacy_class' in issue_types:
        recommendations.append("Update legacy flow classes to use Base* classes")
    
    if 'legacy_import' in issue_types:
        recommendations.append("Update import statements to use new module paths")
    
    if 'missing_base_class' in issue_types:
        recommendations.append("Inherit flows from appropriate base classes")
    
    if 'hardcoded_selector' in issue_types:
        recommendations.append("Move hardcoded selectors to configuration")
    
    if not recommendations:
        recommendations.append("No deprecation issues found - template is up to date")
    
    return recommendations


# Setup automatic monitoring
def setup_deprecation_monitoring(site_path: str = None):
    """
    Setup automatic deprecation monitoring for a site.
    
    Args:
        site_path: Path to the site directory
    """
    global _deprecation_monitor
    _deprecation_monitor = DeprecationMonitor(site_path)
    
    # Analyze existing code for issues
    if site_path:
        analysis = analyze_site_deprecations(site_path)
        
        if analysis['critical_issues'] > 0:
            logger.error(f"Found {analysis['critical_issues']} critical deprecation issues")
        
        if analysis['warning_issues'] > 0:
            logger.warning(f"Found {analysis['warning_issues']} deprecation warnings")
        
        for recommendation in analysis['recommendations']:
            logger.info(f"Recommendation: {recommendation}")


# Export main functions
__all__ = [
    'deprecated',
    'deprecated_pattern',
    'get_deprecation_monitor',
    'setup_deprecation_monitoring',
    'analyze_template_usage',
    'analyze_site_deprecations',
    'TemplateDeprecationWarning',
    'CriticalDeprecationWarning'
]
