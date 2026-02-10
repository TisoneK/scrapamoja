"""
Hierarchical selector structure validation utilities.

This module provides validation for the hierarchical folder organization
required by the flashscore workflow and other complex navigation patterns.
"""

import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    level: ValidationLevel
    message: str
    path: Optional[Path] = None
    suggestion: Optional[str] = None


@dataclass
class StructureReport:
    """Complete validation report for selector structure."""
    is_valid: bool
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    info: List[ValidationResult]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def total_issues(self) -> int:
        """Get total number of issues."""
        return len(self.errors) + len(self.warnings)


class HierarchicalStructureValidator:
    """
    Validates hierarchical selector folder structure according to
    the flashscore workflow requirements.
    """
    
    # Required primary folders
    PRIMARY_FOLDERS = {
        'authentication',
        'navigation', 
        'extraction',
        'filtering'
    }
    
    # Required secondary folders within extraction
    EXTRACTION_SECONDARY_FOLDERS = {
        'match_list',
        'match_summary', 
        'match_h2h',
        'match_odds',
        'match_stats'
    }
    
    # Required tertiary folders within match_stats
    MATCH_STATS_TERTIARY_FOLDERS = {
        'inc_ot',
        'ft',
        'q1',
        'q2', 
        'q3',
        'q4'
    }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.yaml', '.yml'}
    
    def __init__(self, selectors_root: Path):
        """
        Initialize validator.
        
        Args:
            selectors_root: Root directory of selectors
        """
        self.selectors_root = Path(selectors_root)
        self.results: List[ValidationResult] = []
    
    def validate_structure(self) -> StructureReport:
        """
        Validate the complete hierarchical structure.
        
        Returns:
            StructureReport: Complete validation report
        """
        self.results.clear()
        
        # Validate root directory
        self._validate_root_directory()
        
        # Validate primary folders
        self._validate_primary_folders()
        
        # Validate extraction secondary folders
        extraction_path = self.selectors_root / 'extraction'
        if extraction_path.exists():
            self._validate_extraction_secondary_folders(extraction_path)
            
            # Validate match_stats tertiary folders
            match_stats_path = extraction_path / 'match_stats'
            if match_stats_path.exists():
                self._validate_match_stats_tertiary_folders(match_stats_path)
        
        # Validate file naming conventions
        self._validate_file_naming_conventions()
        
        # Validate file permissions and readability
        self._validate_file_accessibility()
        
        # Separate results by level
        errors = [r for r in self.results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in self.results if r.level == ValidationLevel.WARNING]
        info = [r for r in self.results if r.level == ValidationLevel.INFO]
        
        return StructureReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _validate_root_directory(self) -> None:
        """Validate the root selectors directory."""
        if not self.selectors_root.exists():
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"Selectors root directory does not exist: {self.selectors_root}",
                path=self.selectors_root,
                suggestion="Create the selectors root directory"
            ))
            return
        
        if not self.selectors_root.is_dir():
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"Selectors path is not a directory: {self.selectors_root}",
                path=self.selectors_root,
                suggestion="Ensure the path points to a directory"
            ))
    
    def _validate_primary_folders(self) -> None:
        """Validate required primary folders exist."""
        existing_folders = {f.name for f in self.selectors_root.iterdir() if f.is_dir()}
        
        # Check for missing required folders
        missing_folders = self.PRIMARY_FOLDERS - existing_folders
        for folder in missing_folders:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"Missing required primary folder: {folder}",
                path=self.selectors_root / folder,
                suggestion=f"Create directory: {folder}"
            ))
        
        # Check for unexpected folders
        unexpected_folders = existing_folders - self.PRIMARY_FOLDERS
        for folder in unexpected_folders:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"Unexpected primary folder: {folder}",
                path=self.selectors_root / folder,
                suggestion="Ensure this folder follows the hierarchical structure requirements"
            ))
    
    def _validate_extraction_secondary_folders(self, extraction_path: Path) -> None:
        """Validate secondary folders within extraction."""
        existing_folders = {f.name for f in extraction_path.iterdir() if f.is_dir()}
        
        # Check for missing required folders
        missing_folders = self.EXTRACTION_SECONDARY_FOLDERS - existing_folders
        for folder in missing_folders:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"Missing required extraction secondary folder: {folder}",
                path=extraction_path / folder,
                suggestion=f"Create directory: extraction/{folder}"
            ))
        
        # Check for unexpected folders
        unexpected_folders = existing_folders - self.EXTRACTION_SECONDARY_FOLDERS
        for folder in unexpected_folders:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"Unexpected extraction secondary folder: {folder}",
                path=extraction_path / folder,
                suggestion="Ensure this folder is needed for the extraction workflow"
            ))
    
    def _validate_match_stats_tertiary_folders(self, match_stats_path: Path) -> None:
        """Validate tertiary folders within match_stats."""
        existing_folders = {f.name for f in match_stats_path.iterdir() if f.is_dir()}
        
        # Check for missing required folders
        missing_folders = self.MATCH_STATS_TERTIARY_FOLDERS - existing_folders
        for folder in missing_folders:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"Missing required match_stats tertiary folder: {folder}",
                path=match_stats_path / folder,
                suggestion=f"Create directory: extraction/match_stats/{folder}"
            ))
        
        # Check for unexpected folders
        unexpected_folders = existing_folders - self.MATCH_STATS_TERTIARY_FOLDERS
        for folder in unexpected_folders:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"Unexpected match_stats tertiary folder: {folder}",
                path=match_stats_path / folder,
                suggestion="Ensure this tertiary folder is needed for statistics workflow"
            ))
    
    def _validate_file_naming_conventions(self) -> None:
        """Validate file naming conventions across the structure."""
        for yaml_file in self.selectors_root.rglob('*'):
            if yaml_file.is_file() and yaml_file.suffix.lower() in self.ALLOWED_EXTENSIONS:
                self._validate_single_file_naming(yaml_file)
    
    def _validate_single_file_naming(self, file_path: Path) -> None:
        """Validate naming convention for a single file."""
        filename = file_path.stem
        
        # Check for kebab-case naming
        if not self._is_kebab_case(filename):
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"File name should use kebab-case: {file_path.name}",
                path=file_path,
                suggestion="Rename file using kebab-case (lowercase with hyphens)"
            ))
        
        # Check for descriptive naming
        if len(filename) < 3:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"File name too short: {file_path.name}",
                path=file_path,
                suggestion="Use more descriptive file names"
            ))
        
        # Check for context-specific naming if in nested structure
        relative_path = file_path.relative_to(self.selectors_root)
        parts = relative_path.parts
        
        if len(parts) > 1:  # File is in a subfolder
            context = parts[0]  # Primary folder
            if context == 'extraction' and len(parts) > 2:  # Secondary level
                secondary_context = parts[1]
                if not self._has_context_identifier(filename, secondary_context):
                    self.results.append(ValidationResult(
                        level=ValidationLevel.INFO,
                        message=f"Consider adding context identifier to file name: {file_path.name}",
                        path=file_path,
                        suggestion=f"Include '{secondary_context}' in filename for clarity"
                    ))
    
    def _validate_file_accessibility(self) -> None:
        """Validate that all YAML files are accessible."""
        for yaml_file in self.selectors_root.rglob('*'):
            if yaml_file.is_file() and yaml_file.suffix.lower() in self.ALLOWED_EXTENSIONS:
                try:
                    # Try to read the file
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        f.read(1)  # Just read first character to check accessibility
                except PermissionError:
                    self.results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        message=f"Permission denied accessing file: {yaml_file}",
                        path=yaml_file,
                        suggestion="Check file permissions"
                    ))
                except UnicodeDecodeError:
                    self.results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        message=f"File encoding issue: {yaml_file}",
                        path=yaml_file,
                        suggestion="Ensure file is saved as UTF-8"
                    ))
                except Exception as e:
                    self.results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        message=f"Error accessing file {yaml_file}: {str(e)}",
                        path=yaml_file,
                        suggestion="Check file integrity"
                    ))
    
    def _is_kebab_case(self, name: str) -> bool:
        """Check if a string follows kebab-case convention."""
        if not name:
            return False
        
        # Kebab-case: lowercase letters, numbers, and hyphens only
        # Cannot start or end with hyphen, no consecutive hyphens
        import re
        pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
        return bool(re.match(pattern, name))
    
    def _has_context_identifier(self, filename: str, context: str) -> bool:
        """Check if filename contains context identifier."""
        # Simple check - see if context name is part of filename
        # This is a basic implementation - could be enhanced
        context_parts = context.split('_')
        return any(part in filename for part in context_parts)
    
    def get_structure_summary(self) -> Dict[str, any]:
        """
        Get a summary of the current structure.
        
        Returns:
            Dict with structure statistics
        """
        if not self.selectors_root.exists():
            return {"error": "Root directory does not exist"}
        
        summary = {
            "root_path": str(self.selectors_root),
            "primary_folders": {},
            "total_files": 0,
            "yaml_files": 0,
            "max_depth": 0
        }
        
        # Analyze primary folders
        for primary in self.selectors_root.iterdir():
            if primary.is_dir():
                primary_info = {
                    "exists": True,
                    "secondary_folders": {},
                    "file_count": 0,
                    "yaml_count": 0
                }
                
                # Analyze secondary folders
                for secondary in primary.iterdir():
                    if secondary.is_dir():
                        secondary_info = {
                            "exists": True,
                            "tertiary_folders": {},
                            "file_count": 0,
                            "yaml_count": 0
                        }
                        
                        # Analyze tertiary folders
                        for tertiary in secondary.iterdir():
                            if tertiary.is_dir():
                                tertiary_files = list(tertiary.rglob('*.yaml')) + list(tertiary.rglob('*.yml'))
                                secondary_info["tertiary_folders"][tertiary.name] = {
                                    "file_count": len(tertiary_files),
                                    "yaml_count": len([f for f in tertiary_files if f.suffix.lower() in self.ALLOWED_EXTENSIONS])
                                }
                        
                        # Count files in secondary folder
                        secondary_files = list(secondary.rglob('*'))
                        secondary_info["file_count"] = len([f for f in secondary_files if f.is_file()])
                        secondary_info["yaml_count"] = len([f for f in secondary_files if f.is_file() and f.suffix.lower() in self.ALLOWED_EXTENSIONS])
                        
                        primary_info["secondary_folders"][secondary.name] = secondary_info
                
                # Count files in primary folder
                primary_files = list(primary.rglob('*'))
                primary_info["file_count"] = len([f for f in primary_files if f.is_file()])
                primary_info["yaml_count"] = len([f for f in primary_files if f.is_file() and f.suffix.lower() in self.ALLOWED_EXTENSIONS])
                
                summary["primary_folders"][primary.name] = primary_info
        
        # Overall counts
        all_files = list(self.selectors_root.rglob('*'))
        summary["total_files"] = len([f for f in all_files if f.is_file()])
        summary["yaml_files"] = len([f for f in all_files if f.is_file() and f.suffix.lower() in self.ALLOWED_EXTENSIONS])
        
        # Calculate max depth
        for file_path in all_files:
            if file_path.is_file():
                depth = len(file_path.relative_to(self.selectors_root).parts)
                summary["max_depth"] = max(summary["max_depth"], depth)
        
        return summary


def validate_selector_structure(selectors_root: Path) -> StructureReport:
    """
    Convenience function to validate selector structure.
    
    Args:
        selectors_root: Root directory of selectors
        
    Returns:
        StructureReport: Validation report
    """
    validator = HierarchicalStructureValidator(selectors_root)
    return validator.validate_structure()


def print_validation_report(report: StructureReport) -> None:
    """
    Print validation report in a readable format.
    
    Args:
        report: Validation report to print
    """
    print(f"\n{'='*60}")
    print(f"STRUCTURE VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Overall Status: {'✓ VALID' if report.is_valid else '✗ INVALID'}")
    print(f"Total Issues: {report.total_issues}")
    
    if report.errors:
        print(f"\n🔴 ERRORS ({len(report.errors)}):")
        for error in report.errors:
            print(f"  • {error.message}")
            if error.path:
                print(f"    Path: {error.path}")
            if error.suggestion:
                print(f"    Suggestion: {error.suggestion}")
    
    if report.warnings:
        print(f"\n🟡 WARNINGS ({len(report.warnings)}):")
        for warning in report.warnings:
            print(f"  • {warning.message}")
            if warning.path:
                print(f"    Path: {warning.path}")
            if warning.suggestion:
                print(f"    Suggestion: {warning.suggestion}")
    
    if report.info:
        print(f"\n🔵 INFO ({len(report.info)}):")
        for info in report.info:
            print(f"  • {info.message}")
            if info.path:
                print(f"    Path: {info.path}")
            if info.suggestion:
                print(f"    Suggestion: {info.suggestion}")
    
    print(f"\n{'='*60}")
