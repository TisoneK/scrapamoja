"""
Automated migration validation scripts.

This module provides comprehensive validation tools to ensure
migration success and detect potential issues.
"""

import os
import sys
import ast
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    success: bool
    message: str
    details: Dict[str, Any] = None
    severity: str = "error"  # error, warning, info
    file_path: str = None
    line_number: int = None


@dataclass
class MigrationValidationReport:
    """Comprehensive migration validation report."""
    site_path: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings: int
    results: List[ValidationResult]
    summary: Dict[str, Any]
    recommendations: List[str]


class MigrationValidator:
    """Validates migration success and detects issues."""
    
    def __init__(self, site_path: str, config: Dict[str, Any] = None):
        """
        Initialize migration validator.
        
        Args:
            site_path: Path to the site directory
            config: Validation configuration
        """
        self.site_path = Path(site_path)
        self.config = config or {}
        self.results: List[ValidationResult] = []
        
        # Validation options
        self.strict_mode = self.config.get('strict_mode', False)
        self.check_imports = self.config.get('check_imports', True)
        self.check_syntax = self.config.get('check_syntax', True)
        self.check_functionality = self.config.get('check_functionality', True)
        self.check_compatibility = self.config.get('check_compatibility', True)
    
    def validate_migration(self) -> MigrationValidationReport:
        """
        Perform comprehensive migration validation.
        
        Returns:
            Detailed validation report
        """
        self.results = []
        
        logger.info(f"Starting migration validation for {self.site_path}")
        
        # Core validation checks
        self._check_directory_structure()
        self._check_file_integrity()
        
        if self.check_syntax:
            self._check_syntax_validity()
        
        if self.check_imports:
            self._check_import_validity()
        
        if self.check_functionality:
            self._check_functionality()
        
        if self.check_compatibility:
            self._check_backward_compatibility()
        
        # Advanced checks
        self._check_base_class_usage()
        self._check_flow_organization()
        self._check_configuration_completeness()
        self._check_error_handling()
        
        # Generate report
        report = self._generate_report()
        
        logger.info(f"Validation complete: {report.passed_checks}/{report.total_checks} checks passed")
        
        return report
    
    def _check_directory_structure(self):
        """Check if directory structure is valid."""
        # Check for required files
        required_files = ['flow.py']
        for file_name in required_files:
            file_path = self.site_path / file_name
            if file_path.exists():
                self.results.append(ValidationResult(
                    check_name="directory_structure",
                    success=True,
                    message=f"Required file {file_name} exists",
                    details={"file": file_name},
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="directory_structure",
                    success=False,
                    message=f"Required file {file_name} missing",
                    details={"file": file_name},
                    severity="error"
                ))
        
        # Check flows directory
        flows_dir = self.site_path / 'flows'
        if flows_dir.exists():
            self.results.append(ValidationResult(
                check_name="directory_structure",
                success=True,
                message="Flows directory exists",
                details={"type": "standard_or_complex"},
                severity="info"
            ))
            
            # Check for domain subdirectories
            domains = ['navigation', 'extraction', 'filtering', 'authentication']
            domain_dirs = [d for d in flows_dir.iterdir() 
                          if d.is_dir() and d.name in domains]
            
            if domain_dirs:
                self.results.append(ValidationResult(
                    check_name="directory_structure",
                    success=True,
                    message=f"Domain directories found: {[d.name for d in domain_dirs]}",
                    details={"domains": [d.name for d in domain_dirs], "type": "complex"},
                    severity="info"
                ))
    
    def _check_file_integrity(self):
        """Check integrity of key files."""
        # Check flow.py
        flow_py = self.site_path / 'flow.py'
        if flow_py.exists():
            try:
                with open(flow_py, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for basic structure
                if 'import' in content or 'from' in content:
                    self.results.append(ValidationResult(
                        check_name="file_integrity",
                        success=True,
                        message="flow.py has import statements",
                        severity="info"
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name="file_integrity",
                        success=False,
                        message="flow.py missing import statements",
                        severity="warning"
                    ))
                
                # Check for class definitions
                if 'class ' in content:
                    self.results.append(ValidationResult(
                        check_name="file_integrity",
                        success=True,
                        message="flow.py contains class definitions",
                        severity="info"
                    ))
                
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name="file_integrity",
                    success=False,
                    message=f"Error reading flow.py: {str(e)}",
                    severity="error"
                ))
        
        # Check flows directory files
        flows_dir = self.site_path / 'flows'
        if flows_dir.exists():
            for py_file in flows_dir.rglob('*.py'):
                if py_file.name == '__init__.py':
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if len(content.strip()) == 0:
                        self.results.append(ValidationResult(
                            check_name="file_integrity",
                            success=False,
                            message=f"Empty flow file: {py_file.name}",
                            file_path=str(py_file),
                            severity="warning"
                        ))
                
                except Exception as e:
                    self.results.append(ValidationResult(
                        check_name="file_integrity",
                        success=False,
                        message=f"Error reading {py_file.name}: {str(e)}",
                        file_path=str(py_file),
                        severity="error"
                    ))
    
    def _check_syntax_validity(self):
        """Check syntax validity of Python files."""
        python_files = list(self.site_path.rglob('*.py'))
        
        for py_file in python_files:
            if py_file.name == '__pycache__':
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to check syntax
                ast.parse(content)
                
                self.results.append(ValidationResult(
                    check_name="syntax_validity",
                    success=True,
                    message=f"Valid syntax: {py_file.name}",
                    file_path=str(py_file),
                    severity="info"
                ))
                
            except SyntaxError as e:
                self.results.append(ValidationResult(
                    check_name="syntax_validity",
                    success=False,
                    message=f"Syntax error in {py_file.name}: {str(e)}",
                    file_path=str(py_file),
                    line_number=e.lineno,
                    severity="error"
                ))
            
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name="syntax_validity",
                    success=False,
                    message=f"Error checking {py_file.name}: {str(e)}",
                    file_path=str(py_file),
                    severity="error"
                ))
    
    def _check_import_validity(self):
        """Check validity of import statements."""
        python_files = list(self.site_path.rglob('*.py'))
        
        for py_file in python_files:
            if py_file.name in ['__init__.py', '__pycache__']:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to find imports
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._validate_import(str(alias.name), str(py_file))
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._validate_import(node.module, str(py_file))
            
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name="import_validity",
                    success=False,
                    message=f"Error checking imports in {py_file.name}: {str(e)}",
                    file_path=str(py_file),
                    severity="error"
                ))
    
    def _validate_import(self, import_name: str, file_path: str):
        """Validate a specific import."""
        # Check for deprecated imports
        deprecated_imports = {
            'scrapamoja.flows.base': 'base_flows',
            'flows.base': 'base_flows',
            'scrapamoja.templates.base': 'base_flows'
        }
        
        if import_name in deprecated_imports:
            self.results.append(ValidationResult(
                check_name="import_validity",
                success=False,
                message=f"Deprecated import: {import_name}",
                details={
                    "old_import": import_name,
                    "new_import": deprecated_imports[import_name]
                },
                file_path=file_path,
                severity="warning"
            ))
        
        # Check for relative imports
        if import_name.startswith('.'):
            self.results.append(ValidationResult(
                check_name="import_validity",
                success=True,
                message=f"Using relative import: {import_name}",
                file_path=file_path,
                severity="info"
            ))
    
    def _check_functionality(self):
        """Check basic functionality of flows."""
        # Try to import and instantiate flows
        try:
            # Add site path to sys.path
            site_path_str = str(self.site_path)
            if site_path_str not in sys.path:
                sys.path.insert(0, site_path_str)
            
            # Try to import main module
            spec = importlib.util.spec_from_file_location("flow", self.site_path / "flow.py")
            if spec and spec.loader:
                flow_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(flow_module)
                
                self.results.append(ValidationResult(
                    check_name="functionality",
                    success=True,
                    message="Successfully imported main flow module",
                    severity="info"
                ))
                
                # Check for flow classes
                flow_classes = [name for name in dir(flow_module) 
                              if name.endswith('Flow') and not name.startswith('_')]
                
                if flow_classes:
                    self.results.append(ValidationResult(
                        check_name="functionality",
                        success=True,
                        message=f"Found flow classes: {flow_classes}",
                        details={"classes": flow_classes},
                        severity="info"
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name="functionality",
                        success=False,
                        message="No flow classes found",
                        severity="warning"
                    ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="functionality",
                success=False,
                message=f"Failed to import flow module: {str(e)}",
                details={"traceback": traceback.format_exc()},
                severity="error"
            ))
        
        # Clean up sys.path
        if site_path_str in sys.path:
            sys.path.remove(site_path_str)
    
    def _check_backward_compatibility(self):
        """Check backward compatibility issues."""
        python_files = list(self.site_path.rglob('*.py'))
        
        for py_file in python_files:
            if py_file.name in ['__init__.py', '__pycache__']:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for legacy patterns
                legacy_patterns = [
                    ('NavigationFlow(', 'BaseNavigationFlow should be used'),
                    ('ExtractionFlow(', 'BaseExtractionFlow should be used'),
                    ('FilteringFlow(', 'BaseFilteringFlow should be used'),
                    ('AuthenticationFlow(', 'BaseAuthenticationFlow should be used'),
                    ('class Flow(', 'Simple Flow pattern should be upgraded'),
                ]
                
                for pattern, message in legacy_patterns:
                    if pattern in content:
                        self.results.append(ValidationResult(
                            check_name="backward_compatibility",
                            success=False,
                            message=f"Legacy pattern found: {message}",
                            details={"pattern": pattern, "file": py_file.name},
                            file_path=str(py_file),
                            severity="warning"
                        ))
            
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name="backward_compatibility",
                    success=False,
                    message=f"Error checking {py_file.name}: {str(e)}",
                    file_path=str(py_file),
                    severity="error"
                ))
    
    def _check_base_class_usage(self):
        """Check proper base class usage."""
        python_files = list(self.site_path.rglob('*.py'))
        
        for py_file in python_files:
            if py_file.name in ['__init__.py', '__pycache__']:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for proper base class inheritance
                if 'class ' in content and 'Flow' in content:
                    # Look for class definitions
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and 'Flow' in node.name:
                            if node.bases:
                                base_names = []
                                for base in node.bases:
                                    if isinstance(base, ast.Name):
                                        base_names.append(base.id)
                                    elif isinstance(base, ast.Attribute):
                                        base_names.append(ast.unparse(base))
                                
                                # Check if using proper base classes
                                proper_bases = ['BaseNavigationFlow', 'BaseExtractionFlow', 
                                             'BaseFilteringFlow', 'BaseAuthenticationFlow']
                                
                                if any(base in proper_bases for base in base_names):
                                    self.results.append(ValidationResult(
                                        check_name="base_class_usage",
                                        success=True,
                                        message=f"Proper base class usage in {node.name}",
                                        details={"class": node.name, "bases": base_names},
                                        file_path=str(py_file),
                                        severity="info"
                                    ))
                                else:
                                    self.results.append(ValidationResult(
                                        check_name="base_class_usage",
                                        success=False,
                                        message=f"Improper base class in {node.name}: {base_names}",
                                        details={"class": node.name, "bases": base_names},
                                        file_path=str(py_file),
                                        severity="warning"
                                    ))
                            else:
                                self.results.append(ValidationResult(
                                    check_name="base_class_usage",
                                    success=False,
                                    message=f"Missing base class in {node.name}",
                                    details={"class": node.name},
                                    file_path=str(py_file),
                                    severity="error"
                                ))
            
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name="base_class_usage",
                    success=False,
                    message=f"Error checking {py_file.name}: {str(e)}",
                    file_path=str(py_file),
                    severity="error"
                ))
    
    def _check_flow_organization(self):
        """Check flow organization and structure."""
        flows_dir = self.site_path / 'flows'
        
        if flows_dir.exists():
            # Check for __init__.py files
            for subdir in flows_dir.iterdir():
                if subdir.is_dir() and subdir.name != '__pycache__':
                    init_file = subdir / '__init__.py'
                    if init_file.exists():
                        self.results.append(ValidationResult(
                            check_name="flow_organization",
                            success=True,
                            message=f"__init__.py exists in {subdir.name}",
                            file_path=str(init_file),
                            severity="info"
                        ))
                    else:
                        self.results.append(ValidationResult(
                            check_name="flow_organization",
                            success=False,
                            message=f"Missing __init__.py in {subdir.name}",
                            file_path=str(subdir),
                            severity="warning"
                        ))
            
            # Check for empty directories
            for subdir in flows_dir.iterdir():
                if subdir.is_dir() and subdir.name != '__pycache__':
                    py_files = list(subdir.glob('*.py'))
                    if not py_files or (len(py_files) == 1 and py_files[0].name == '__init__.py'):
                        self.results.append(ValidationResult(
                            check_name="flow_organization",
                            success=False,
                            message=f"Empty flow directory: {subdir.name}",
                            file_path=str(subdir),
                            severity="warning"
                        ))
    
    def _check_configuration_completeness(self):
        """Check configuration completeness."""
        # Look for configuration files
        config_files = ['config.py', 'settings.py', 'config.yaml', 'settings.yaml']
        
        found_configs = []
        for config_file in config_files:
            config_path = self.site_path / config_file
            if config_path.exists():
                found_configs.append(config_file)
        
        if found_configs:
            self.results.append(ValidationResult(
                check_name="configuration_completeness",
                success=True,
                message=f"Configuration files found: {found_configs}",
                details={"configs": found_configs},
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="configuration_completeness",
                success=False,
                message="No configuration files found",
                severity="warning"
            ))
    
    def _check_error_handling(self):
        """Check error handling patterns."""
        python_files = list(self.site_path.rglob('*.py'))
        
        for py_file in python_files:
            if py_file.name in ['__init__.py', '__pycache__']:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for error handling patterns
                has_try_except = 'try:' in content and 'except' in content
                has_logging = 'logger.' in content or 'logging.' in content
                
                if has_try_except:
                    self.results.append(ValidationResult(
                        check_name="error_handling",
                        success=True,
                        message=f"Error handling found in {py_file.name}",
                        file_path=str(py_file),
                        severity="info"
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name="error_handling",
                        success=False,
                        message=f"No error handling in {py_file.name}",
                        file_path=str(py_file),
                        severity="warning"
                    ))
                
                if has_logging:
                    self.results.append(ValidationResult(
                        check_name="error_handling",
                        success=True,
                        message=f"Logging found in {py_file.name}",
                        file_path=str(py_file),
                        severity="info"
                    ))
            
            except Exception as e:
                self.results.append(ValidationResult(
                    check_name="error_handling",
                    success=False,
                    message=f"Error checking {py_file.name}: {str(e)}",
                    file_path=str(py_file),
                    severity="error"
                ))
    
    def _generate_report(self) -> MigrationValidationReport:
        """Generate comprehensive validation report."""
        total_checks = len(self.results)
        passed_checks = len([r for r in self.results if r.success])
        failed_checks = len([r for r in self.results if not r.success])
        warnings = len([r for r in self.results if r.severity == 'warning'])
        
        # Generate summary
        summary = {
            'validation_mode': 'strict' if self.strict_mode else 'standard',
            'checks_performed': [r.check_name for r in self.results],
            'severity_distribution': {
                'error': len([r for r in self.results if r.severity == 'error']),
                'warning': len([r for r in self.results if r.severity == 'warning']),
                'info': len([r for r in self.results if r.severity == 'info'])
            }
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        return MigrationValidationReport(
            site_path=str(self.site_path),
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            results=self.results,
            summary=summary,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Analyze failed checks
        error_results = [r for r in self.results if not r.success and r.severity == 'error']
        warning_results = [r for r in self.results if not r.success and r.severity == 'warning']
        
        if error_results:
            recommendations.append("Address critical errors before proceeding")
            recommendations.append("Run migration tool to fix structural issues")
        
        if warning_results:
            recommendations.append("Review and address warnings for better compatibility")
        
        # Check for specific patterns
        import_issues = [r for r in self.results if r.check_name == 'import_validity' and not r.success]
        if import_issues:
            recommendations.append("Update deprecated import statements")
        
        base_class_issues = [r for r in self.results if r.check_name == 'base_class_usage' and not r.success]
        if base_class_issues:
            recommendations.append("Update flow classes to use proper base classes")
        
        functionality_issues = [r for r in self.results if r.check_name == 'functionality' and not r.success]
        if functionality_issues:
            recommendations.append("Fix import and syntax issues to restore functionality")
        
        if not error_results and not warning_results:
            recommendations.append("Migration validation passed - no issues found")
        
        return recommendations


def validate_migration(site_path: str, config: Dict[str, Any] = None) -> MigrationValidationReport:
    """
    Validate migration for a site.
    
    Args:
        site_path: Path to the site directory
        config: Validation configuration
        
    Returns:
        Migration validation report
    """
    validator = MigrationValidator(site_path, config)
    return validator.validate_migration()


def quick_validation(site_path: str) -> bool:
    """
    Perform quick validation check.
    
    Args:
        site_path: Path to the site directory
        
    Returns:
        True if validation passes, False otherwise
    """
    config = {
        'strict_mode': False,
        'check_functionality': False,
        'check_compatibility': False
    }
    
    report = validate_migration(site_path, config)
    return report.failed_checks == 0


def save_validation_report(report: MigrationValidationReport, output_path: str):
    """
    Save validation report to file.
    
    Args:
        report: Validation report to save
        output_path: Path to save the report
    """
    # Convert to serializable format
    report_data = {
        'site_path': report.site_path,
        'total_checks': report.total_checks,
        'passed_checks': report.passed_checks,
        'failed_checks': report.failed_checks,
        'warnings': report.warnings,
        'summary': report.summary,
        'recommendations': report.recommendations,
        'results': [
            {
                'check_name': r.check_name,
                'success': r.success,
                'message': r.message,
                'details': r.details,
                'severity': r.severity,
                'file_path': r.file_path,
                'line_number': r.line_number
            }
            for r in report.results
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)


# CLI interface
def main():
    """Command line interface for migration validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate migration success')
    parser.add_argument('site_path', help='Path to the site directory')
    parser.add_argument('--output', '-o', help='Output report file')
    parser.add_argument('--strict', action='store_true', help='Enable strict mode')
    parser.add_argument('--quick', action='store_true', help='Quick validation only')
    
    args = parser.parse_args()
    
    # Setup configuration
    config = {
        'strict_mode': args.strict,
        'check_functionality': not args.quick,
        'check_compatibility': not args.quick
    }
    
    # Run validation
    report = validate_migration(args.site_path, config)
    
    # Print summary
    print(f"\nMigration Validation Report")
    print(f"Site: {report.site_path}")
    print(f"Total Checks: {report.total_checks}")
    print(f"Passed: {report.passed_checks}")
    print(f"Failed: {report.failed_checks}")
    print(f"Warnings: {report.warnings}")
    
    # Print recommendations
    if report.recommendations:
        print(f"\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    
    # Save report if requested
    if args.output:
        save_validation_report(report, args.output)
        print(f"\nReport saved to: {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if report.failed_checks == 0 else 1)


if __name__ == '__main__':
    main()
