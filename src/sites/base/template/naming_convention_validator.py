"""
Selector file naming convention validator.

This module provides validation for selector file naming conventions
to ensure consistency and clarity across the hierarchical structure.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class NamingConvention(Enum):
    """Supported naming conventions."""
    KEBAB_CASE = "kebab-case"
    SNAKE_CASE = "snake-case"
    CAMEL_CASE = "camel-case"


@dataclass
class NamingViolation:
    """Represents a naming convention violation."""
    file_path: Path
    violation_type: str
    expected_pattern: str
    actual_name: str
    suggestion: str
    severity: str = "warning"  # error, warning, info


@dataclass
class NamingValidationReport:
    """Report for naming convention validation."""
    is_valid: bool
    violations: List[NamingViolation]
    total_files: int
    valid_files: int
    
    @property
    def has_errors(self) -> bool:
        """Check if there are error-level violations."""
        return any(v.severity == "error" for v in self.violations)
    
    @property
    def error_count(self) -> int:
        """Count error-level violations."""
        return sum(1 for v in self.violations if v.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count warning-level violations."""
        return sum(1 for v in self.violations if v.severity == "warning")


class SelectorNamingValidator:
    """
    Validates selector file naming conventions according to
    hierarchical structure requirements.
    """
    
    # Context-specific prefixes and suffixes
    CONTEXT_PREFIXES = {
        'authentication': ['auth', 'login', 'cookie', 'consent'],
        'navigation': ['nav', 'menu', 'filter', 'search', 'sport'],
        'extraction': ['extract', 'data', 'match', 'team', 'score', 'odds', 'stats'],
        'filtering': ['filter', 'date', 'competition', 'league']
    }
    
    # Secondary context identifiers
    SECONDARY_CONTEXTS = {
        'match_list': ['list', 'matches', 'schedule', 'live', 'finished'],
        'match_summary': ['summary', 'overview', 'details', 'info'],
        'match_h2h': ['h2h', 'head-to-head', 'history', 'vs'],
        'match_odds': ['odds', 'betting', 'price', 'market'],
        'match_stats': ['stats', 'statistics', 'performance', 'incidents']
    }
    
    # Tertiary context identifiers for match_stats
    TERTIARY_CONTEXTS = {
        'inc_ot': ['incidents', 'overtime', 'events'],
        'ft': ['full-time', 'final', 'complete'],
        'q1': ['quarter1', 'q1', 'first-quarter'],
        'q2': ['quarter2', 'q2', 'second-quarter'],
        'q3': ['quarter3', 'q3', 'third-quarter'],
        'q4': ['quarter4', 'q4', 'fourth-quarter']
    }
    
    # Valid file extensions
    VALID_EXTENSIONS = {'.yaml', '.yml'}
    
    # Naming patterns
    KEBAB_CASE_PATTERN = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
    SNAKE_CASE_PATTERN = re.compile(r'^[a-z0-9]+(_[a-z0-9]+)*$')
    
    # Reserved names that should not be used
    RESERVED_NAMES = {
        'config', 'settings', 'test', 'temp', 'backup', 'old', 'new',
        'default', 'example', 'sample', 'demo', 'debug'
    }
    
    def __init__(self, selectors_root: Path):
        """
        Initialize naming validator.
        
        Args:
            selectors_root: Root directory of selectors
        """
        self.selectors_root = Path(selectors_root)
        self.violations: List[NamingViolation] = []
    
    def validate_naming_conventions(self) -> NamingValidationReport:
        """
        Validate naming conventions for all selector files.
        
        Returns:
            NamingValidationReport: Complete validation report
        """
        self.violations.clear()
        
        if not self.selectors_root.exists():
            self.violations.append(NamingViolation(
                file_path=self.selectors_root,
                violation_type="missing_directory",
                expected_pattern="Existing selectors directory",
                actual_name=str(self.selectors_root),
                suggestion="Create the selectors root directory",
                severity="error"
            ))
            return NamingValidationReport(
                is_valid=False,
                violations=self.violations.copy(),
                total_files=0,
                valid_files=0
            )
        
        # Find all YAML files recursively
        yaml_files = list(self.selectors_root.rglob('*.yaml')) + list(self.selectors_root.rglob('*.yml'))
        
        for file_path in yaml_files:
            self._validate_single_file(file_path)
        
        total_files = len(yaml_files)
        valid_files = total_files - len([v for v in self.violations if v.severity == "error"])
        
        return NamingValidationReport(
            is_valid=not any(v.severity == "error" for v in self.violations),
            violations=self.violations.copy(),
            total_files=total_files,
            valid_files=valid_files
        )
    
    def _validate_single_file(self, file_path: Path) -> None:
        """
        Validate naming convention for a single file.
        
        Args:
            file_path: Path to the file to validate
        """
        filename = file_path.stem  # Name without extension
        
        # Check basic naming rules
        self._validate_basic_naming(file_path, filename)
        
        # Check for reserved names
        self._validate_reserved_names(file_path, filename)
        
        # Check context appropriateness
        self._validate_context_appropriateness(file_path, filename)
        
        # Check descriptive naming
        self._validate_descriptive_naming(file_path, filename)
        
        # Check length constraints
        self._validate_length_constraints(file_path, filename)
    
    def _validate_basic_naming(self, file_path: Path, filename: str) -> None:
        """Validate basic naming rules."""
        # Check for kebab-case (preferred convention)
        if not self.KEBAB_CASE_PATTERN.match(filename):
            # Check if it's snake_case (acceptable but not preferred)
            if self.SNAKE_CASE_PATTERN.match(filename):
                self.violations.append(NamingViolation(
                    file_path=file_path,
                    violation_type="naming_convention",
                    expected_pattern="kebab-case (preferred)",
                    actual_name=filename,
                    suggestion=f"Convert to kebab-case: {filename.replace('_', '-')}",
                    severity="warning"
                ))
            else:
                self.violations.append(NamingViolation(
                    file_path=file_path,
                    violation_type="naming_convention",
                    expected_pattern="kebab-case (lowercase with hyphens)",
                    actual_name=filename,
                    suggestion=f"Rename using kebab-case, e.g., 'match-list-selectors'",
                    severity="error"
                ))
        
        # Check for invalid characters
        invalid_chars = re.findall(r'[^a-zA-Z0-9_-]', filename)
        if invalid_chars:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="invalid_characters",
                expected_pattern="Only letters, numbers, hyphens, and underscores",
                actual_name=filename,
                suggestion=f"Remove invalid characters: {set(invalid_chars)}",
                severity="error"
            ))
        
        # Check for consecutive hyphens or underscores
        if '--' in filename or '__' in filename:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="consecutive_separators",
                expected_pattern="Single hyphens between words",
                actual_name=filename,
                suggestion="Replace consecutive separators with single hyphens",
                severity="warning"
            ))
    
    def _validate_reserved_names(self, file_path: Path, filename: str) -> None:
        """Check for reserved names."""
        if filename.lower() in self.RESERVED_NAMES:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="reserved_name",
                expected_pattern="Descriptive, non-reserved name",
                actual_name=filename,
                suggestion=f"Use more descriptive name, e.g., '{filename}-selectors'",
                severity="error"
            ))
    
    def _validate_context_appropriateness(self, file_path: Path, filename: str) -> None:
        """Validate that filename is appropriate for its context."""
        relative_path = file_path.relative_to(self.selectors_root)
        parts = relative_path.parts
        
        if len(parts) < 2:
            # File is in root - should be in a context folder
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="missing_context",
                expected_pattern="File should be in a context folder",
                actual_name=filename,
                suggestion="Move file to appropriate context folder (authentication/, navigation/, extraction/, filtering/)",
                severity="error"
            ))
            return
        
        primary_context = parts[0]
        secondary_context = parts[1] if len(parts) > 1 else None
        tertiary_context = parts[2] if len(parts) > 2 else None
        
        # Check primary context appropriateness
        self._validate_primary_context(file_path, filename, primary_context)
        
        # Check secondary context appropriateness
        if secondary_context and primary_context == 'extraction':
            self._validate_secondary_context(file_path, filename, secondary_context)
        
        # Check tertiary context appropriateness
        if tertiary_context and secondary_context == 'match_stats':
            self._validate_tertiary_context(file_path, filename, tertiary_context)
    
    def _validate_primary_context(self, file_path: Path, filename: str, context: str) -> None:
        """Validate filename appropriateness for primary context."""
        if context not in self.CONTEXT_PREFIXES:
            return
        
        expected_keywords = self.CONTEXT_PREFIXES[context]
        filename_lower = filename.lower()
        
        # Check if filename contains relevant keywords
        has_relevant_keyword = any(keyword in filename_lower for keyword in expected_keywords)
        
        if not has_relevant_keyword:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="context_inappropriate",
                expected_pattern=f"Should contain keywords like: {', '.join(expected_keywords[:3])}...",
                actual_name=filename,
                suggestion=f"Include relevant keyword for {context} context",
                severity="warning"
            ))
    
    def _validate_secondary_context(self, file_path: Path, filename: str, context: str) -> None:
        """Validate filename appropriateness for secondary context."""
        if context not in self.SECONDARY_CONTEXTS:
            return
        
        expected_keywords = self.SECONDARY_CONTEXTS[context]
        filename_lower = filename.lower()
        
        # Check if filename contains relevant keywords
        has_relevant_keyword = any(keyword in filename_lower for keyword in expected_keywords)
        
        if not has_relevant_keyword:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="context_inappropriate",
                expected_pattern=f"Should contain keywords like: {', '.join(expected_keywords[:3])}...",
                actual_name=filename,
                suggestion=f"Include relevant keyword for {context} context",
                severity="info"
            ))
    
    def _validate_tertiary_context(self, file_path: Path, filename: str, context: str) -> None:
        """Validate filename appropriateness for tertiary context."""
        if context not in self.TERTIARY_CONTEXTS:
            return
        
        expected_keywords = self.TERTIARY_CONTEXTS[context]
        filename_lower = filename.lower()
        
        # Check if filename contains relevant keywords
        has_relevant_keyword = any(keyword in filename_lower for keyword in expected_keywords)
        
        if not has_relevant_keyword:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="context_inappropriate",
                expected_pattern=f"Should contain keywords like: {', '.join(expected_keywords)}",
                actual_name=filename,
                suggestion=f"Include relevant keyword for {context} sub-context",
                severity="info"
            ))
    
    def _validate_descriptive_naming(self, file_path: Path, filename: str) -> None:
        """Validate that filename is descriptive."""
        # Check minimum length
        if len(filename) < 3:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="too_short",
                expected_pattern="Descriptive name (3+ characters)",
                actual_name=filename,
                suggestion="Use more descriptive filename",
                severity="warning"
            ))
        
        # Check for generic names
        generic_patterns = [
            r'^test\d*$',
            r'^temp\d*$',
            r'^new\d*$',
            r'^old\d*$',
            r'^file\d*$',
            r'^data\d*$',
            r'^info\d*$'
        ]
        
        for pattern in generic_patterns:
            if re.match(pattern, filename.lower()):
                self.violations.append(NamingViolation(
                    file_path=file_path,
                    violation_type="generic_name",
                    expected_pattern="Descriptive, specific name",
                    actual_name=filename,
                    suggestion="Use more descriptive filename that indicates purpose",
                    severity="warning"
                ))
                break
    
    def _validate_length_constraints(self, file_path: Path, filename: str) -> None:
        """Validate filename length constraints."""
        # Check maximum length (filesystem and readability)
        if len(filename) > 100:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="too_long",
                expected_pattern="Filename under 100 characters",
                actual_name=filename,
                suggestion="Shorten filename while maintaining descriptiveness",
                severity="warning"
            ))
        
        # Check for very short names
        if len(filename) < 5:
            self.violations.append(NamingViolation(
                file_path=file_path,
                violation_type="very_short",
                expected_pattern="Descriptive name (5+ characters recommended)",
                actual_name=filename,
                suggestion="Use more descriptive filename",
                severity="info"
            ))
    
    def suggest_improvements(self, file_path: Path) -> List[str]:
        """
        Suggest improvements for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List[str]: List of improvement suggestions
        """
        suggestions = []
        filename = file_path.stem
        relative_path = file_path.relative_to(self.selectors_root)
        parts = relative_path.parts
        
        # Basic naming suggestion
        if not self.KEBAB_CASE_PATTERN.match(filename):
            if self.SNAKE_CASE_PATTERN.match(filename):
                suggestions.append(f"Convert to kebab-case: {filename.replace('_', '-')}")
            else:
                # Try to convert to kebab-case
                clean_name = re.sub(r'[^a-zA-Z0-9]', '-', filename)
                clean_name = re.sub(r'-+', '-', clean_name).strip('-')
                clean_name = clean_name.lower()
                suggestions.append(f"Suggested name: {clean_name}")
        
        # Context-based suggestions
        if len(parts) >= 2:
            primary_context = parts[0]
            if primary_context in self.CONTEXT_PREFIXES:
                keywords = self.CONTEXT_PREFIXES[primary_context]
                if not any(keyword in filename.lower() for keyword in keywords):
                    suggestions.append(f"Consider adding context keyword: {keywords[0]}")
        
        return suggestions


def validate_selector_naming(selectors_root: Path) -> NamingValidationReport:
    """
    Convenience function to validate selector naming conventions.
    
    Args:
        selectors_root: Root directory of selectors
        
    Returns:
        NamingValidationReport: Validation report
    """
    validator = SelectorNamingValidator(selectors_root)
    return validator.validate_naming_conventions()


def print_naming_report(report: NamingValidationReport) -> None:
    """
    Print naming validation report in a readable format.
    
    Args:
        report: Naming validation report to print
    """
    print(f"\n{'='*60}")
    print(f"NAMING CONVENTION VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Overall Status: {'✓ VALID' if report.is_valid else '✗ INVALID'}")
    print(f"Files Analyzed: {report.total_files}")
    print(f"Valid Files: {report.valid_files}")
    print(f"Errors: {report.error_count}")
    print(f"Warnings: {report.warning_count}")
    
    if report.violations:
        print(f"\nVIOLATIONS ({len(report.violations)}):")
        
        # Group violations by type
        violations_by_type = {}
        for violation in report.violations:
            vtype = violation.violation_type
            if vtype not in violations_by_type:
                violations_by_type[vtype] = []
            violations_by_type[vtype].append(violation)
        
        for vtype, violations in violations_by_type.items():
            print(f"\n🔸 {vtype.replace('_', ' ').title()} ({len(violations)}):")
            for violation in violations:
                severity_icon = "🔴" if violation.severity == "error" else "🟡" if violation.severity == "warning" else "🔵"
                print(f"  {severity_icon} {violation.file_path.name}")
                print(f"     Expected: {violation.expected_pattern}")
                print(f"     Actual: {violation.actual_name}")
                if violation.suggestion:
                    print(f"     Suggestion: {violation.suggestion}")
                print()
    
    print(f"{'='*60}")
