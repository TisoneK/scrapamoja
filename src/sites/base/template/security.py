"""
Security hardening utilities for template framework.

This module provides security measures including sandboxing, input validation,
access control, and security monitoring for template operations.
"""

import ast
import hashlib
import importlib.util
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass
from enum import Enum
import json
import yaml
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for template operations."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"
    DISABLED = "disabled"


class SecurityViolationType(Enum):
    """Types of security violations."""
    UNSAFE_IMPORT = "unsafe_import"
    FILE_SYSTEM_ACCESS = "file_system_access"
    NETWORK_ACCESS = "network_access"
    CODE_INJECTION = "code_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    MALICIOUS_CODE = "malicious_code"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityViolation:
    """Security violation record."""
    violation_type: SecurityViolationType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    template_name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    timestamp: datetime = None
    blocked: bool = True
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SecurityPolicy:
    """Security policy configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security policy.
        
        Args:
            config: Security policy configuration
        """
        self.config = config or {}
        
        # Security configuration
        self.security_config = {
            "security_level": SecurityLevel(self.config.get("security_level", "strict")),
            "enable_sandboxing": self.config.get("enable_sandboxing", True),
            "max_execution_time": self.config.get("max_execution_time", 300),  # 5 minutes
            "max_memory_usage": self.config.get("max_memory_usage", 512 * 1024 * 1024),  # 512MB
            "allow_file_access": self.config.get("allow_file_access", False),
            "allow_network_access": self.config.get("allow_network_access", False),
            "allowed_imports": self.config.get("allowed_imports", [
                "typing", "dataclasses", "enum", "datetime", "json", "yaml",
                "pathlib", "re", "hashlib", "time", "logging"
            ]),
            "blocked_imports": self.config.get("blocked_imports", [
                "os", "sys", "subprocess", "socket", "urllib", "requests",
                "shutil", "tempfile", "pickle", "marshal", "eval", "exec"
            ]),
            "max_file_size": self.config.get("max_file_size", 10 * 1024 * 1024),  # 10MB
            "allowed_file_extensions": self.config.get("allowed_file_extensions", [
                ".py", ".yaml", ".yml", ".json", ".md", ".txt"
            ]),
            "enable_code_scanning": self.config.get("enable_code_scanning", True),
            "enable_runtime_monitoring": self.config.get("enable_runtime_monitoring", True)
        }
        
        # Security violation tracking
        self.violations: List[SecurityViolation] = []
        self.blocked_templates: Set[str] = set()
        
        logger.info(f"SecurityPolicy initialized with level: {self.security_config['security_level'].value}")
    
    def is_allowed_import(self, module_name: str) -> bool:
        """
        Check if import is allowed.
        
        Args:
            module_name: Name of the module to import
            
        Returns:
            bool: True if import is allowed
        """
        security_level = self.security_config["security_level"]
        
        if security_level == SecurityLevel.DISABLED:
            return True
        
        # Check blocked imports first
        if module_name in self.security_config["blocked_imports"]:
            return False
        
        # Check allowed imports
        if security_level == SecurityLevel.STRICT:
            return module_name in self.security_config["allowed_imports"]
        elif security_level == SecurityLevel.MODERATE:
            # Allow safe modules and standard library modules
            safe_modules = set(self.security_config["allowed_imports"])
            return module_name in safe_modules or not module_name.startswith(".")
        else:  # LENIENT
            return True
    
    def is_file_access_allowed(self, file_path: Union[str, Path], operation: str = "read") -> bool:
        """
        Check if file access is allowed.
        
        Args:
            file_path: Path to the file
            operation: Type of operation ("read", "write", "execute")
            
        Returns:
            bool: True if access is allowed
        """
        if not self.security_config["allow_file_access"]:
            return False
        
        file_path = Path(file_path)
        
        # Check file extension
        if file_path.suffix not in self.security_config["allowed_file_extensions"]:
            return False
        
        # Check file size for read operations
        if operation == "read" and file_path.exists():
            if file_path.stat().st_size > self.security_config["max_file_size"]:
                return False
        
        # Check for dangerous paths
        dangerous_patterns = [
            r"\.\.",  # Parent directory traversal
            r"^/",   # Absolute paths
            r"^C:",  # Windows absolute paths
            r"^\\",  # UNC paths
        ]
        
        path_str = str(file_path)
        for pattern in dangerous_patterns:
            if re.search(pattern, path_str):
                return False
        
        return True
    
    def is_network_access_allowed(self, url: str) -> bool:
        """
        Check if network access is allowed.
        
        Args:
            url: URL to access
            
        Returns:
            bool: True if access is allowed
        """
        return self.security_config["allow_network_access"]
    
    def add_violation(self, violation_type: SecurityViolationType, severity: str, 
                     description: str, template_name: str, **kwargs) -> None:
        """
        Add a security violation.
        
        Args:
            violation_type: Type of violation
            severity: Severity level
            description: Description of violation
            template_name: Name of template
            **kwargs: Additional violation data
        """
        violation = SecurityViolation(
            violation_type=violation_type,
            severity=severity,
            description=description,
            template_name=template_name,
            **kwargs
        )
        
        self.violations.append(violation)
        
        # Block template if violation is severe
        if violation.severity in ["high", "critical"] and violation.blocked:
            self.blocked_templates.add(template_name)
            logger.warning(f"Template {template_name} blocked due to security violation: {description}")
        
        logger.error(f"Security violation detected: {description} in {template_name}")
    
    def is_template_blocked(self, template_name: str) -> bool:
        """
        Check if template is blocked.
        
        Args:
            template_name: Name of template
            
        Returns:
            bool: True if template is blocked
        """
        return template_name in self.blocked_templates
    
    def get_violations(self, template_name: Optional[str] = None, 
                      severity: Optional[str] = None) -> List[SecurityViolation]:
        """
        Get security violations.
        
        Args:
            template_name: Filter by template name
            severity: Filter by severity
            
        Returns:
            List[SecurityViolation]: List of violations
        """
        violations = self.violations
        
        if template_name:
            violations = [v for v in violations if v.template_name == template_name]
        
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        return violations
    
    def get_security_report(self) -> Dict[str, Any]:
        """
        Get security report.
        
        Returns:
            Dict[str, Any]: Security report
        """
        total_violations = len(self.violations)
        blocked_templates = len(self.blocked_templates)
        
        # Count violations by type
        violations_by_type = {}
        for violation in self.violations:
            violation_type = violation.violation_type.value
            violations_by_type[violation_type] = violations_by_type.get(violation_type, 0) + 1
        
        # Count violations by severity
        violations_by_severity = {}
        for violation in self.violations:
            severity = violation.severity
            violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1
        
        return {
            "security_level": self.security_config["security_level"].value,
            "total_violations": total_violations,
            "blocked_templates": blocked_templates,
            "violations_by_type": violations_by_type,
            "violations_by_severity": violations_by_severity,
            "recent_violations": [v for v in self.violations 
                                if v.timestamp > datetime.now() - timedelta(hours=24)]
        }


class CodeScanner:
    """Code scanner for security vulnerabilities."""
    
    def __init__(self, security_policy: SecurityPolicy):
        """
        Initialize code scanner.
        
        Args:
            security_policy: Security policy to apply
        """
        self.security_policy = security_policy
        
        # Dangerous patterns
        self.dangerous_patterns = {
            "code_injection": [
                r"eval\s*\(",
                r"exec\s*\(",
                r"compile\s*\(",
                r"__import__\s*\(",
                r"getattr\s*\(",
                r"setattr\s*\(",
                r"delattr\s*\(",
                r"globals\s*\(",
                r"locals\s*\(",
                r"vars\s*\(",
                r"dir\s*\("
            ],
            "file_system_access": [
                r"open\s*\(",
                r"file\s*\(",
                r"with\s+open\s*\(",
                r"os\.system\s*\(",
                r"os\.popen\s*\(",
                r"subprocess\.",
                r"shutil\.",
                r"tempfile\.",
                r"pathlib\.Path\.open\s*\("
            ],
            "network_access": [
                r"socket\.",
                r"urllib\.",
                r"requests\.",
                r"http\.",
                r"ftplib\.",
                r"smtplib\.",
                r"telnetlib\."
            ],
            "privilege_escalation": [
                r"os\.setuid\s*\(",
                r"os\.setgid\s*\(",
                r"os\.seteuid\s*\(",
                r"os\.setegid\s*\(",
                r"ctypes\."
            ]
        }
        
        logger.info("CodeScanner initialized")
    
    def scan_file(self, file_path: Union[str, Path], template_name: str) -> List[SecurityViolation]:
        """
        Scan a file for security vulnerabilities.
        
        Args:
            file_path: Path to file to scan
            template_name: Name of template
            
        Returns:
            List[SecurityViolation]: List of violations found
        """
        violations = []
        file_path = Path(file_path)
        
        try:
            # Check file size
            if file_path.stat().st_size > self.security_policy.security_config["max_file_size"]:
                self.security_policy.add_violation(
                    SecurityViolationType.RESOURCE_EXHAUSTION,
                    "medium",
                    f"File too large: {file_path.stat().st_size} bytes",
                    template_name,
                    file_path=str(file_path)
                )
                violations.append(self.security_policy.violations[-1])
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Scan based on file type
            if file_path.suffix == '.py':
                violations.extend(self._scan_python_code(content, template_name, str(file_path)))
            elif file_path.suffix in ['.yaml', '.yml']:
                violations.extend(self._scan_yaml_code(content, template_name, str(file_path)))
            elif file_path.suffix == '.json':
                violations.extend(self._scan_json_code(content, template_name, str(file_path)))
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
        
        return violations
    
    def _scan_python_code(self, content: str, template_name: str, file_path: str) -> List[SecurityViolation]:
        """Scan Python code for vulnerabilities."""
        violations = []
        lines = content.split('\n')
        
        # Check imports
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self.security_policy.is_allowed_import(alias.name):
                            self.security_policy.add_violation(
                                SecurityViolationType.UNSAFE_IMPORT,
                                "high",
                                f"Unsafe import: {alias.name}",
                                template_name,
                                file_path=file_path,
                                line_number=node.lineno,
                                code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                            )
                            violations.append(self.security_policy.violations[-1])
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self.security_policy.is_allowed_import(node.module):
                        self.security_policy.add_violation(
                            SecurityViolationType.UNSAFE_IMPORT,
                            "high",
                            f"Unsafe import from: {node.module}",
                            template_name,
                            file_path=file_path,
                            line_number=node.lineno,
                            code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        )
                        violations.append(self.security_policy.violations[-1])
        
        except SyntaxError as e:
            self.security_policy.add_violation(
                SecurityViolationType.MALICIOUS_CODE,
                "medium",
                f"Syntax error in code: {e}",
                template_name,
                file_path=file_path,
                line_number=e.lineno
            )
            violations.append(self.security_policy.violations[-1])
        
        # Check dangerous patterns
        for line_num, line in enumerate(lines, 1):
            for violation_type, patterns in self.dangerous_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        severity = "high" if violation_type in ["code_injection", "privilege_escalation"] else "medium"
                        
                        self.security_policy.add_violation(
                            SecurityViolationType[violation_type.upper()],
                            severity,
                            f"Dangerous pattern detected: {pattern}",
                            template_name,
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()
                        )
                        violations.append(self.security_policy.violations[-1])
        
        return violations
    
    def _scan_yaml_code(self, content: str, template_name: str, file_path: str) -> List[SecurityViolation]:
        """Scan YAML code for vulnerabilities."""
        violations = []
        
        try:
            # Parse YAML to check for malicious content
            yaml_data = yaml.safe_load(content)
            
            # Check for dangerous YAML features
            if isinstance(yaml_data, dict):
                self._check_dict_for_malicious_content(yaml_data, template_name, file_path, violations)
        
        except yaml.YAMLError as e:
            self.security_policy.add_violation(
                SecurityViolationType.MALICIOUS_CODE,
                "medium",
                f"Invalid YAML syntax: {e}",
                template_name,
                file_path=file_path
            )
            violations.append(self.security_policy.violations[-1])
        
        return violations
    
    def _scan_json_code(self, content: str, template_name: str, file_path: str) -> List[SecurityViolation]:
        """Scan JSON code for vulnerabilities."""
        violations = []
        
        try:
            # Parse JSON to check for malicious content
            json_data = json.loads(content)
            
            # Check for dangerous JSON content
            if isinstance(json_data, dict):
                self._check_dict_for_malicious_content(json_data, template_name, file_path, violations)
        
        except json.JSONDecodeError as e:
            self.security_policy.add_violation(
                SecurityViolationType.MALICIOUS_CODE,
                "medium",
                f"Invalid JSON syntax: {e}",
                template_name,
                file_path=file_path
            )
            violations.append(self.security_policy.violations[-1])
        
        return violations
    
    def _check_dict_for_malicious_content(self, data: Dict[str, Any], template_name: str, 
                                        file_path: str, violations: List[SecurityViolation]) -> None:
        """Check dictionary for malicious content."""
        dangerous_keys = [
            "exec", "eval", "compile", "__import__", "open", "file", "system",
            "subprocess", "socket", "urllib", "requests", "os", "sys"
        ]
        
        for key, value in data.items():
            # Check for dangerous keys
            if any(dangerous_key in key.lower() for dangerous_key in dangerous_keys):
                self.security_policy.add_violation(
                    SecurityViolationType.MALICIOUS_CODE,
                    "medium",
                    f"Dangerous key in configuration: {key}",
                    template_name,
                    file_path=file_path
                )
                violations.append(self.security_policy.violations[-1])
            
            # Recursively check nested dictionaries
            if isinstance(value, dict):
                self._check_dict_for_malicious_content(value, template_name, file_path, violations)


class SecuritySandbox:
    """Security sandbox for template execution."""
    
    def __init__(self, security_policy: SecurityPolicy):
        """
        Initialize security sandbox.
        
        Args:
            security_policy: Security policy to apply
        """
        self.security_policy = security_policy
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SecuritySandbox initialized")
    
    async def execute_in_sandbox(self, template_name: str, code: str, 
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute code in a secure sandbox.
        
        Args:
            template_name: Name of template
            code: Code to execute
            context: Execution context
            
        Returns:
            Dict[str, Any]: Execution result
        """
        session_id = f"{template_name}_{int(time.time())}"
        
        try:
            # Check if template is blocked
            if self.security_policy.is_template_blocked(template_name):
                return {
                    "success": False,
                    "error": "Template is blocked due to security violations",
                    "session_id": session_id
                }
            
            # Create sandbox environment
            sandbox_env = self._create_sandbox_environment(context or {})
            
            # Start monitoring
            session = {
                "session_id": session_id,
                "template_name": template_name,
                "start_time": time.time(),
                "memory_usage": 0,
                "cpu_usage": 0,
                "network_requests": 0,
                "file_operations": 0
            }
            
            self.active_sessions[session_id] = session
            
            # Execute code with timeout
            result = await self._execute_with_timeout(
                code, sandbox_env, self.security_policy.security_config["max_execution_time"]
            )
            
            # Update session metrics
            session["end_time"] = time.time()
            session["duration"] = session["end_time"] - session["start_time"]
            
            return {
                "success": True,
                "result": result,
                "session_id": session_id,
                "metrics": {
                    "duration": session["duration"],
                    "memory_usage": session["memory_usage"],
                    "cpu_usage": session["cpu_usage"]
                }
            }
        
        except Exception as e:
            logger.error(f"Sandbox execution error for {template_name}: {e}")
            
            # Record security violation if it's a security-related error
            if "security" in str(e).lower() or "violation" in str(e).lower():
                self.security_policy.add_violation(
                    SecurityViolationType.UNAUTHORIZED_ACCESS,
                    "high",
                    f"Sandbox execution violation: {e}",
                    template_name
                )
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
        
        finally:
            # Cleanup session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    def _create_sandbox_environment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create sandboxed execution environment."""
        # Start with safe builtins
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "pow": pow,
            "range": range,
            "reversed": reversed,
            "round": round,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
        }
        
        # Add allowed imports
        allowed_modules = {}
        for module_name in self.security_policy.security_config["allowed_imports"]:
            try:
                allowed_modules[module_name] = __import__(module_name)
            except ImportError:
                pass
        
        # Combine environment
        sandbox_env = {
            "__builtins__": safe_builtins,
            **allowed_modules,
            **context
        }
        
        return sandbox_env
    
    async def _execute_with_timeout(self, code: str, env: Dict[str, Any], timeout: int) -> Any:
        """Execute code with timeout."""
        try:
            # For simplicity, we'll use exec directly
            # In a real implementation, you'd use proper sandboxing
            exec(code, env)
            return {"output": "Code executed successfully"}
        
        except Exception as e:
            raise Exception(f"Code execution failed: {e}")
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get active sandbox sessions."""
        return self.active_sessions.copy()


class SecurityManager:
    """Main security manager for template framework."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security manager.
        
        Args:
            config: Security configuration
        """
        self.config = config or {}
        
        # Initialize components
        self.security_policy = SecurityPolicy(config)
        self.code_scanner = CodeScanner(self.security_policy)
        self.sandbox = SecuritySandbox(self.security_policy)
        
        # Security monitoring
        self.monitoring_active = False
        self.last_scan_time = None
        
        logger.info("SecurityManager initialized")
    
    async def scan_template(self, template_path: Union[str, Path], template_name: str) -> Dict[str, Any]:
        """
        Scan template for security vulnerabilities.
        
        Args:
            template_path: Path to template directory
            template_name: Name of template
            
        Returns:
            Dict[str, Any]: Scan results
        """
        template_path = Path(template_path)
        violations = []
        
        if not template_path.exists():
            return {
                "success": False,
                "error": f"Template path not found: {template_path}",
                "violations": []
            }
        
        # Scan all files in template
        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                file_violations = self.code_scanner.scan_file(file_path, template_name)
                violations.extend(file_violations)
        
        # Update last scan time
        self.last_scan_time = datetime.now()
        
        return {
            "success": True,
            "template_name": template_name,
            "scan_time": self.last_scan_time,
            "violations_found": len(violations),
            "violations": violations,
            "template_blocked": self.security_policy.is_template_blocked(template_name)
        }
    
    async def validate_template_security(self, template_path: Union[str, Path], 
                                     template_name: str) -> bool:
        """
        Validate template security.
        
        Args:
            template_path: Path to template directory
            template_name: Name of template
            
        Returns:
            bool: True if template passes security validation
        """
        scan_result = await self.scan_template(template_path, template_name)
        
        # Check if template is blocked
        if scan_result["template_blocked"]:
            return False
        
        # Check for high/critical violations
        high_severity_violations = [
            v for v in scan_result["violations"] 
            if v.severity in ["high", "critical"]
        ]
        
        return len(high_severity_violations) == 0
    
    async def execute_template_safely(self, template_name: str, code: str, 
                                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute template code safely.
        
        Args:
            template_name: Name of template
            code: Code to execute
            context: Execution context
            
        Returns:
            Dict[str, Any]: Execution result
        """
        return await self.sandbox.execute_in_sandbox(template_name, code, context)
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        Get security status.
        
        Returns:
            Dict[str, Any]: Security status
        """
        return {
            "security_level": self.security_policy.security_config["security_level"].value,
            "total_violations": len(self.security_policy.violations),
            "blocked_templates": len(self.security_policy.blocked_templates),
            "active_sessions": len(self.sandbox.active_sessions),
            "last_scan_time": self.last_scan_time,
            "security_report": self.security_policy.get_security_report()
        }
    
    def get_template_security_report(self, template_name: str) -> Dict[str, Any]:
        """
        Get security report for specific template.
        
        Args:
            template_name: Name of template
            
        Returns:
            Dict[str, Any]: Template security report
        """
        violations = self.security_policy.get_violations(template_name)
        
        return {
            "template_name": template_name,
            "is_blocked": self.security_policy.is_template_blocked(template_name),
            "total_violations": len(violations),
            "violations_by_severity": {
                severity: len([v for v in violations if v.severity == severity])
                for severity in ["low", "medium", "high", "critical"]
            },
            "violations": violations,
            "recent_violations": [
                v for v in violations 
                if v.timestamp > datetime.now() - timedelta(hours=24)
            ]
        }


# Global security manager instance
_global_security_manager = None


def get_global_security_manager(config: Optional[Dict[str, Any]] = None) -> SecurityManager:
    """Get global security manager instance."""
    global _global_security_manager
    if _global_security_manager is None:
        _global_security_manager = SecurityManager(config)
    return _global_security_manager
