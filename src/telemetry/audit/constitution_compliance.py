"""
Constitution compliance audit for Selector Telemetry System.

This module performs comprehensive audit of telemetry system compliance
with the Scorewise Scraper Constitution principles.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ComplianceIssue:
    """Constitution compliance issue."""
    principle: str
    severity: str  # "low", "medium", "high", "critical"
    file_path: str
    line_number: int
    description: str
    suggestion: str


@dataclass
class ComplianceReport:
    """Constitution compliance report."""
    total_files: int = 0
    compliant_files: int = 0
    issues: List[ComplianceIssue] = field(default_factory=list)
    principle_scores: Dict[str, float] = field(default_factory=dict)
    
    @property
    def overall_compliance(self) -> float:
        """Calculate overall compliance percentage."""
        if self.total_files == 0:
            return 100.0
        return (self.compliant_files / self.total_files) * 100.0


class ConstitutionAuditor:
    """Audits code compliance with Scorewise Scraper Constitution."""
    
    def __init__(self):
        self.telemetry_dir = Path(__file__).parent.parent  # Go up to telemetry directory
        
        # Constitution principles and their requirements
        self.principles = {
            "selector_first": {
                "name": "Selector-First Engineering",
                "description": "Semantic selector definitions with confidence scoring",
                "checks": [
                    self._check_selector_first_patterns,
                    self._check_confidence_scoring,
                    self._check_semantic_selectors
                ]
            },
            "stealth_aware": {
                "name": "Stealth-Aware Design", 
                "description": "Human behavior emulation and anti-bot detection",
                "checks": [
                    self._check_performance_overhead,
                    self._check_async_operations,
                    self._check_stealth_compliance
                ]
            },
            "deep_modularity": {
                "name": "Deep Modularity",
                "description": "Granular components with single responsibilities",
                "checks": [
                    self._check_module_structure,
                    self._check_single_responsibility,
                    self._check_interface_separation
                ]
            },
            "test_first": {
                "name": "Test-First Validation",
                "description": "Failing tests before implementation",
                "checks": [
                    self._check_test_structure,
                    self._check_validation_patterns,
                    self._check_error_handling
                ]
            },
            "production_resilience": {
                "name": "Production Resilience",
                "description": "Graceful failure handling with retry and recovery",
                "checks": [
                    self._check_error_recovery,
                    self._check_graceful_degradation,
                    self._check_correlation_ids
                ]
            },
            "neutral_naming": {
                "name": "Neutral Naming Convention",
                "description": "Structural, descriptive language only",
                "checks": [
                    self._check_neutral_naming,
                    self._check_forbidden_terms,
                    self._check_descriptive_names
                ]
            }
        }
        
        # Forbidden terms for neutral naming
        self.forbidden_terms = {
            "advanced", "powerful", "sophisticated", "robust", "scalable",
            "modern", "cutting-edge", "state-of-the-art", "revolutionary",
            "innovative", "breakthrough", "game-changing", "next-generation",
            "enterprise-grade", "production-ready", "military-grade", "professional"
        }
    
    async def audit_compliance(self) -> ComplianceReport:
        """Perform comprehensive constitution compliance audit."""
        logger.info("🔍 Starting Constitution compliance audit...")
        
        report = ComplianceReport()
        
        # Find all Python files in telemetry module
        python_files = list(self.telemetry_dir.rglob("*.py"))
        report.total_files = len(python_files)
        
        logger.info(f"📁 Found {report.total_files} Python files to audit")
        
        if report.total_files == 0:
            logger.warning("⚠️  No Python files found in telemetry directory")
            return report
        
        # Audit each file
        for file_path in python_files:
            file_issues = await self._audit_file(file_path)
            report.issues.extend(file_issues)
            
            if not file_issues:
                report.compliant_files += 1
        
        # Calculate principle scores
        report.principle_scores = self._calculate_principle_scores(report.issues)
        
        # Log summary
        self._log_audit_summary(report)
        
        return report
    
    async def _audit_file(self, file_path: Path) -> List[ComplianceIssue]:
        """Audit a single file for constitution compliance."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Parse AST for structural analysis
            try:
                tree = ast.parse(content)
            except SyntaxError:
                issues.append(ComplianceIssue(
                    principle="syntax",
                    severity="critical",
                    file_path=str(file_path),
                    line_number=1,
                    description="Syntax error in file",
                    suggestion="Fix syntax errors before compliance audit"
                ))
                return issues
            
            # Run all principle checks
            for principle_id, principle_config in self.principles.items():
                for check_func in principle_config["checks"]:
                    try:
                        check_issues = await check_func(file_path, content, lines, tree)
                        issues.extend(check_issues)
                    except Exception as e:
                        logger.warning(f"Check failed for {principle_id}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to audit file {file_path}: {e}")
        
        return issues
    
    async def _check_selector_first_patterns(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check selector-first engineering patterns."""
        issues = []
        
        # Look for selector-related classes and functions
        selector_patterns = [
            r'class.*Selector.*:',
            r'def.*selector.*:',
            r'selector_id',
            r'confidence_score',
            r'resolution_time'
        ]
        
        has_selector_content = any(re.search(pattern, content, re.IGNORECASE) for pattern in selector_patterns)
        
        if has_selector_content:
            # Check for confidence scoring
            if 'confidence' not in content.lower():
                issues.append(ComplianceIssue(
                    principle="selector_first",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=1,
                    description="Selector-related code missing confidence scoring",
                    suggestion="Add confidence score tracking for selector operations"
                ))
            
            # Check for semantic selector definitions
            if re.search(r'selector.*=.*["\'][^"\']*["\']', content):
                # Found hardcoded selector, check if it's semantic
                if not any(semantic in content.lower() for semantic in ['title', 'price', 'button', 'link', 'input']):
                    issues.append(ComplianceIssue(
                        principle="selector_first",
                        severity="low",
                        file_path=str(file_path),
                        line_number=self._find_line_number(content, 'selector'),
                        description="Non-semantic selector detected",
                        suggestion="Use semantic selector names (title, price, button, etc.)"
                    ))
        
        return issues
    
    async def _check_confidence_scoring(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check confidence scoring implementation."""
        issues = []
        
        if 'confidence' in content.lower():
            # Check for confidence calculation
            if not any(method in content for method in ['calculate_confidence', 'compute_confidence', 'confidence_score']):
                issues.append(ComplianceIssue(
                    principle="selector_first",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=self._find_line_number(content, 'confidence'),
                    description="Confidence mentioned but no calculation method found",
                    suggestion="Implement confidence scoring calculation"
                ))
        
        return issues
    
    async def _check_semantic_selectors(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check for semantic selector naming."""
        issues = []
        
        # Look for selector definitions
        selector_matches = re.finditer(r'selector.*=.*["\']([^"\']*)["\']', content, re.IGNORECASE)
        
        for match in selector_matches:
            selector_value = match.group(1)
            line_num = self._find_line_number(content, match.group(0))
            
            # Check if selector is semantic
            non_semantic_patterns = [
                r'^\.?[a-z]\d+',  # .a1, .b2, etc.
                r'^#?[a-z]\d+',   # #a1, #b2, etc.
                r'^\.?\w{1,2}$',  # .a, .b, .ab, etc.
            ]
            
            if any(re.search(pattern, selector_value) for pattern in non_semantic_patterns):
                issues.append(ComplianceIssue(
                    principle="selector_first",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=line_num,
                    description=f"Non-semantic selector: {selector_value}",
                    suggestion="Use semantic selector names that describe content"
                ))
        
        return issues
    
    async def _check_performance_overhead(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check performance overhead compliance."""
        issues = []
        
        # Look for performance-related code
        if any(keyword in content.lower() for keyword in ['performance', 'overhead', 'telemetry', 'monitoring']):
            # Check for overhead limits
            if not any(limit in content for limit in ['0.02', '2%', 'overhead_target']):
                issues.append(ComplianceIssue(
                    principle="stealth_aware",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=1,
                    description="Performance monitoring without overhead limits",
                    suggestion="Define and enforce <2% performance overhead target"
                ))
        
        return issues
    
    async def _check_async_operations(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check for non-blocking async operations."""
        issues = []
        
        # Look for blocking operations
        blocking_patterns = [
            r'time\.sleep\(',
            r'requests\.',
            r'urllib\.',
            r'http\.client\.',
            r'socket\.',
        ]
        
        for pattern in blocking_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = self._find_line_number(content, match.group(0))
                
                # Check if it's in an async context
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                if 'async def' not in line_content and 'await' not in line_content:
                    issues.append(ComplianceIssue(
                        principle="stealth_aware",
                        severity="high",
                        file_path=str(file_path),
                        line_number=line_num,
                        description=f"Blocking operation detected: {match.group(0)}",
                        suggestion="Use async alternatives (asyncio.sleep, aiohttp, etc.)"
                    ))
        
        return issues
    
    async def _check_stealth_compliance(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check stealth-aware design compliance."""
        issues = []
        
        # Check for stealth-related patterns
        stealth_keywords = ['fingerprint', 'detection', 'anti-bot', 'stealth']
        
        if any(keyword in content.lower() for keyword in stealth_keywords):
            # Should have human behavior emulation
            if not any(pattern in content.lower() for pattern in ['human', 'behavior', 'emulation', 'random_delay']):
                issues.append(ComplianceIssue(
                    principle="stealth_aware",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=1,
                    description="Anti-detection features without human behavior emulation",
                    suggestion="Add human behavior emulation patterns"
                ))
        
        return issues
    
    async def _check_module_structure(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check deep modularity - module structure."""
        issues = []
        
        # Count classes and functions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        # Check for overly complex modules
        total_entities = len(classes) + len(functions)
        if total_entities > 20:
            issues.append(ComplianceIssue(
                principle="deep_modularity",
                severity="medium",
                file_path=str(file_path),
                line_number=1,
                description=f"Module has {total_entities} classes/functions (suggest <20)",
                suggestion="Split into smaller, more focused modules"
            ))
        
        # Check class size
        for cls in classes:
            methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)]
            if len(methods) > 10:
                issues.append(ComplianceIssue(
                    principle="deep_modularity",
                    severity="low",
                    file_path=str(file_path),
                    line_number=cls.lineno,
                    description=f"Class {cls.name} has {len(methods)} methods (suggest <10)",
                    suggestion="Consider splitting class or extracting functionality"
                ))
        
        return issues
    
    async def _check_single_responsibility(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check single responsibility principle."""
        issues = []
        
        # Look for functions with multiple concerns
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        for func in functions:
            # Check function length
            func_lines = func.end_lineno - func.lineno + 1 if hasattr(func, 'end_lineno') else 0
            if func_lines > 50:
                issues.append(ComplianceIssue(
                    principle="deep_modularity",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=func.lineno,
                    description=f"Function {func.name} is {func_lines} lines long (suggest <50)",
                    suggestion="Break function into smaller, focused functions"
                ))
        
        return issues
    
    async def _check_interface_separation(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check interface separation principle."""
        issues = []
        
        # Look for interface classes
        interfaces = [cls for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef) and 'Interface' in cls.name]
        
        for interface in interfaces:
            # Check interface methods
            methods = [node for node in interface.body if isinstance(node, ast.FunctionDef)]
            
            # Interfaces should have only abstract methods
            concrete_methods = [m for m in methods if not any(
                isinstance(node, (ast.Raise, ast.Pass)) for node in ast.walk(m)
            )]
            
            if concrete_methods:
                issues.append(ComplianceIssue(
                    principle="deep_modularity",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=interface.lineno,
                    description=f"Interface {interface.name} has concrete implementations",
                    suggestion="Interfaces should only define abstract methods"
                ))
        
        return issues
    
    async def _check_test_structure(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check test-first validation patterns."""
        issues = []
        
        # If this is a test file
        if 'test' in file_path.name.lower():
            # Check for test structure
            if not any(pattern in content for pattern in ['def test_', 'class Test', 'pytest']):
                issues.append(ComplianceIssue(
                    principle="test_first",
                    severity="high",
                    file_path=str(file_path),
                    line_number=1,
                    description="Test file missing proper test structure",
                    suggestion="Use pytest conventions (test_ prefix, Test classes)"
                ))
        
        return issues
    
    async def _check_validation_patterns(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check validation patterns."""
        issues = []
        
        # Look for validation-related code
        if 'validation' in content.lower() or 'validate' in content.lower():
            # Check for proper validation structure
            if not any(pattern in content for pattern in ['ValidationError', 'ValidationResult', 'try:']):
                issues.append(ComplianceIssue(
                    principle="test_first",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=self._find_line_number(content, 'validation'),
                    description="Validation without proper error handling",
                    suggestion="Implement proper validation error handling"
                ))
        
        return issues
    
    async def _check_error_handling(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check error handling patterns."""
        issues = []
        
        # Look for try-except blocks
        try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
        
        for try_block in try_blocks:
            # Check for bare except
            for handler in try_block.handlers:
                if handler.type is None:
                    issues.append(ComplianceIssue(
                        principle="test_first",
                        severity="medium",
                        file_path=str(file_path),
                        line_number=handler.lineno,
                        description="Bare except clause detected",
                        suggestion="Specify exception types for better error handling"
                    ))
        
        return issues
    
    async def _check_error_recovery(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check error recovery mechanisms."""
        issues = []
        
        # Look for error handling
        if any(pattern in content for pattern in ['except', 'error', 'Error']):
            # Check for recovery patterns
            if not any(pattern in content for pattern in ['retry', 'fallback', 'recovery', 'graceful']):
                issues.append(ComplianceIssue(
                    principle="production_resilience",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=1,
                    description="Error handling without recovery mechanisms",
                    suggestion="Implement retry, fallback, or graceful degradation"
                ))
        
        return issues
    
    async def _check_graceful_degradation(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check graceful degradation patterns."""
        issues = []
        
        # Look for graceful degradation keywords
        if 'graceful' in content.lower() or 'degradation' in content.lower():
            # Should have fallback mechanisms
            if not any(pattern in content for pattern in ['fallback', 'alternative', 'backup']):
                issues.append(ComplianceIssue(
                    principle="production_resilience",
                    severity="low",
                    file_path=str(file_path),
                    line_number=self._find_line_number(content, 'graceful'),
                    description="Graceful degradation mentioned but no fallback found",
                    suggestion="Implement fallback mechanisms for graceful degradation"
                ))
        
        return issues
    
    async def _check_correlation_ids(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check correlation ID usage."""
        issues = []
        
        # Look for telemetry/monitoring code
        if any(keyword in content.lower() for keyword in ['telemetry', 'logging', 'trace']):
            # Should have correlation IDs
            if 'correlation' not in content.lower() and 'trace_id' not in content.lower():
                issues.append(ComplianceIssue(
                    principle="production_resilience",
                    severity="medium",
                    file_path=str(file_path),
                    line_number=1,
                    description="Telemetry/logging without correlation IDs",
                    suggestion="Add correlation IDs for end-to-end tracing"
                ))
        
        return issues
    
    async def _check_neutral_naming(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check neutral naming convention."""
        issues = []
        
        # Check for forbidden terms in comments and strings
        for line_num, line in enumerate(lines, 1):
            # Check comments
            comment_match = re.search(r'#.*', line)
            if comment_match:
                comment = comment_match.group(0).lower()
                for term in self.forbidden_terms:
                    if term in comment:
                        issues.append(ComplianceIssue(
                            principle="neutral_naming",
                            severity="medium",
                            file_path=str(file_path),
                            line_number=line_num,
                            description=f"Forbidden term in comment: {term}",
                            suggestion=f"Replace '{term}' with descriptive alternative"
                        ))
            
            # Check strings
            string_matches = re.finditer(r'["\']([^"\']*)["\']', line)
            for match in string_matches:
                string_content = match.group(1).lower()
                for term in self.forbidden_terms:
                    if term in string_content:
                        issues.append(ComplianceIssue(
                            principle="neutral_naming",
                            severity="low",
                            file_path=str(file_path),
                            line_number=line_num,
                            description=f"Forbidden term in string: {term}",
                            suggestion=f"Replace '{term}' with descriptive alternative"
                        ))
        
        return issues
    
    async def _check_forbidden_terms(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check for forbidden terms in identifiers."""
        issues = []
        
        # Check class and function names
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                name = node.name.lower()
                for term in self.forbidden_terms:
                    if term in name:
                        issues.append(ComplianceIssue(
                            principle="neutral_naming",
                            severity="high",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            description=f"Forbidden term in identifier: {node.name}",
                            suggestion=f"Rename to avoid '{term}' - use descriptive name"
                        ))
        
        return issues
    
    async def _check_descriptive_names(self, file_path: Path, content: str, lines: List[str], tree: ast.AST) -> List[ComplianceIssue]:
        """Check for descriptive naming."""
        issues = []
        
        # Check for overly short names
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.name) < 3 and node.name not in ['__init__', '__str__', '__repr__']:
                    issues.append(ComplianceIssue(
                        principle="neutral_naming",
                        severity="low",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        description=f"Overly short function name: {node.name}",
                        suggestion="Use more descriptive function names"
                    ))
        
        return issues
    
    def _find_line_number(self, content: str, pattern: str) -> int:
        """Find line number for a pattern in content."""
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if pattern in line:
                return i
        return 1
    
    def _calculate_principle_scores(self, issues: List[ComplianceIssue]) -> Dict[str, float]:
        """Calculate compliance scores for each principle."""
        scores = {}
        
        for principle_id in self.principles.keys():
            principle_issues = [i for i in issues if i.principle == principle_id]
            
            # Calculate score based on issue severity
            severity_weights = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            total_weight = sum(severity_weights.get(i.severity, 1) for i in principle_issues)
            
            # Score is 100 - (weighted penalty, capped at 100)
            score = max(0, 100 - (total_weight * 5))
            scores[principle_id] = score
        
        return scores
    
    def _log_audit_summary(self, report: ComplianceReport) -> None:
        """Log audit summary."""
        logger.info(f"📊 Constitution Compliance Audit Summary")
        logger.info(f"   Total files: {report.total_files}")
        logger.info(f"   Compliant files: {report.compliant_files}")
        logger.info(f"   Overall compliance: {report.overall_compliance:.1f}%")
        logger.info(f"   Total issues: {len(report.issues)}")
        
        # Log principle scores
        logger.info("📈 Principle Scores:")
        for principle_id, score in report.principle_scores.items():
            principle_name = self.principles[principle_id]["name"]
            logger.info(f"   {principle_name}: {score:.1f}%")
        
        # Log high-severity issues
        high_issues = [i for i in report.issues if i.severity in ["high", "critical"]]
        if high_issues:
            logger.warning(f"⚠️  High-severity issues ({len(high_issues)}):")
            for issue in high_issues[:5]:  # Show first 5
                logger.warning(f"   - {issue.file_path}:{issue.line_number} - {issue.description}")


async def run_constitution_audit() -> ComplianceReport:
    """Run constitution compliance audit."""
    auditor = ConstitutionAuditor()
    return await auditor.audit_compliance()


if __name__ == "__main__":
    import asyncio
    
    async def main():
        report = await run_constitution_audit()
        
        print(f"\n🎯 Constitution Compliance Audit Results")
        print(f"Overall Compliance: {report.overall_compliance:.1f}%")
        print(f"Files Audited: {report.total_files}")
        print(f"Compliant Files: {report.compliant_files}")
        print(f"Issues Found: {len(report.issues)}")
        
        if report.overall_compliance >= 90:
            print("✅ Excellent compliance!")
        elif report.overall_compliance >= 80:
            print("✅ Good compliance")
        elif report.overall_compliance >= 70:
            print("⚠️  Acceptable compliance")
        else:
            print("❌ Compliance needs improvement")
    
    asyncio.run(main())
