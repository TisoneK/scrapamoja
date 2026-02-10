"""
Comprehensive error messages for component failures.

This module provides detailed, user-friendly error messages for component failures,
including error classification, troubleshooting suggestions, and recovery recommendations.
"""

import traceback
import sys
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json


class ErrorSeverity(Enum):
    """Error severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category enumeration."""
    INITIALIZATION = "initialization"
    EXECUTION = "execution"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    DEPENDENCY = "dependency"
    BROWSER = "browser"
    SELECTOR = "selector"
    PLUGIN = "plugin"
    CACHE = "cache"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Recovery action enumeration."""
    RETRY = "retry"
    RESTART = "restart"
    RECONFIGURE = "reconfigure"
    UPDATE_DEPENDENCIES = "update_dependencies"
    CHECK_PERMISSIONS = "check_permissions"
    CLEAR_CACHE = "clear_cache"
    CONTACT_SUPPORT = "contact_support"
    IGNORE = "ignore"


@dataclass
class ErrorMessage:
    """Comprehensive error message."""
    error_id: str
    component_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    title: str
    description: str
    user_message: str
    technical_details: str
    troubleshooting_steps: List[str]
    recovery_actions: List[RecoveryAction]
    related_documentation: List[str]
    error_code: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


class ComponentErrorMessages:
    """Repository of component error messages."""
    
    def __init__(self):
        """Initialize error message repository."""
        self._error_templates = self._initialize_error_templates()
        self._custom_messages: Dict[str, ErrorMessage] = {}
    
    def _initialize_error_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize error message templates."""
        return {
            # Initialization Errors
            "component_not_found": {
                "category": ErrorCategory.INITIALIZATION,
                "severity": ErrorSeverity.CRITICAL,
                "title": "Component Not Found",
                "user_message": "The required component could not be found or loaded.",
                "troubleshooting_steps": [
                    "Check if the component file exists in the correct location",
                    "Verify the component name is spelled correctly",
                    "Ensure all required dependencies are installed",
                    "Check for import errors in the component module"
                ],
                "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.UPDATE_DEPENDENCIES],
                "related_documentation": ["component_development", "troubleshooting"]
            },
            
            "component_init_failed": {
                "category": ErrorCategory.INITIALIZATION,
                "severity": ErrorSeverity.HIGH,
                "title": "Component Initialization Failed",
                "user_message": "The component failed to initialize properly.",
                "troubleshooting_steps": [
                    "Check the component's __init__ method for errors",
                    "Verify all required parameters are provided",
                    "Ensure the component has all required dependencies",
                    "Check for configuration errors"
                ],
                "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.RECONFIGURE],
                "related_documentation": ["component_development", "configuration"]
            },
            
            # Execution Errors
            "component_execution_failed": {
                "category": ErrorCategory.EXECUTION,
                "severity": ErrorSeverity.HIGH,
                "title": "Component Execution Failed",
                "user_message": "The component encountered an error during execution.",
                "troubleshooting_steps": [
                    "Review the component's execute method for logic errors",
                    "Check if input data is in the expected format",
                    "Verify all required resources are available",
                    "Check for timeout or resource exhaustion issues"
                ],
                "recovery_actions": [RecoveryAction.RETRY, RecoveryAction.RESTART],
                "related_documentation": ["component_development", "execution"]
            },
            
            "execution_timeout": {
                "category": ErrorCategory.TIMEOUT,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Component Execution Timeout",
                "user_message": "The component took too long to execute and timed out.",
                "troubleshooting_steps": [
                    "Increase the timeout configuration if appropriate",
                    "Optimize the component's performance",
                    "Check for infinite loops or blocking operations",
                    "Verify network connectivity if the component makes external calls"
                ],
                "recovery_actions": [RecoveryAction.RETRY, RecoveryAction.RECONFIGURE],
                "related_documentation": ["performance_optimization", "configuration"]
            },
            
            # Configuration Errors
            "invalid_configuration": {
                "category": ErrorCategory.CONFIGURATION,
                "severity": ErrorSeverity.HIGH,
                "title": "Invalid Configuration",
                "user_message": "The component configuration is invalid or incomplete.",
                "troubleshooting_steps": [
                    "Check the configuration file for syntax errors",
                    "Verify all required configuration parameters are present",
                    "Ensure parameter values are in the correct format",
                    "Check for conflicting configuration values"
                ],
                "recovery_actions": [RecoveryAction.RECONFIGURE],
                "related_documentation": ["configuration", "validation"]
            },
            
            "missing_configuration": {
                "category": ErrorCategory.CONFIGURATION,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Missing Configuration",
                "user_message": "Required configuration parameters are missing.",
                "troubleshooting_steps": [
                    "Add the missing configuration parameters",
                    "Check the component documentation for required settings",
                    "Verify the configuration file is being loaded correctly",
                    "Use the configuration template as a reference"
                ],
                "recovery_actions": [RecoveryAction.RECONFIGURE],
                "related_documentation": ["configuration"]
            },
            
            # Network Errors
            "network_connection_failed": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Network Connection Failed",
                "user_message": "The component could not establish a network connection.",
                "troubleshooting_steps": [
                    "Check internet connectivity",
                    "Verify the target URL or service is accessible",
                    "Check firewall and proxy settings",
                    "Verify DNS resolution is working"
                ],
                "recovery_actions": [RecoveryAction.RETRY, RecoveryAction.RESTART],
                "related_documentation": ["network_troubleshooting", "configuration"]
            },
            
            "network_timeout": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Network Request Timeout",
                "user_message": "A network request timed out waiting for a response.",
                "troubleshooting_steps": [
                    "Increase the network timeout configuration",
                    "Check network latency and stability",
                    "Verify the target service is responding",
                    "Check for network congestion or issues"
                ],
                "recovery_actions": [RecoveryAction.RETRY, RecoveryAction.RECONFIGURE],
                "related_documentation": ["network_troubleshooting", "configuration"]
            },
            
            # File System Errors
            "file_not_found": {
                "category": ErrorCategory.FILE_SYSTEM,
                "severity": ErrorSeverity.MEDIUM,
                "title": "File Not Found",
                "user_message": "A required file could not be found.",
                "troubleshooting_steps": [
                    "Verify the file path is correct",
                    "Check if the file exists in the expected location",
                    "Ensure file permissions allow reading",
                    "Check for case sensitivity issues on some systems"
                ],
                "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.CHECK_PERMISSIONS],
                "related_documentation": ["file_system", "permissions"]
            },
            
            "permission_denied": {
                "category": ErrorCategory.PERMISSION,
                "severity": ErrorSeverity.HIGH,
                "title": "Permission Denied",
                "user_message": "The component doesn't have permission to perform the requested action.",
                "troubleshooting_steps": [
                    "Check file and directory permissions",
                    "Run the application with appropriate privileges",
                    "Verify the user has access to required resources",
                    "Check for security software blocking access"
                ],
                "recovery_actions": [RecoveryAction.CHECK_PERMISSIONS, RecoveryAction.RESTART],
                "related_documentation": ["permissions", "security"]
            },
            
            # Memory Errors
            "out_of_memory": {
                "category": ErrorCategory.MEMORY,
                "severity": ErrorSeverity.CRITICAL,
                "title": "Out of Memory",
                "user_message": "The component ran out of memory during execution.",
                "troubleshooting_steps": [
                    "Increase available memory or memory limits",
                    "Optimize the component's memory usage",
                    "Check for memory leaks in the component",
                    "Process data in smaller chunks if possible"
                ],
                "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.RECONFIGURE],
                "related_documentation": ["memory_optimization", "performance"]
            },
            
            # Browser Errors
            "browser_launch_failed": {
                "category": ErrorCategory.BROWSER,
                "severity": ErrorSeverity.HIGH,
                "title": "Browser Launch Failed",
                "user_message": "The web browser could not be launched.",
                "troubleshooting_steps": [
                    "Check if the browser is installed and accessible",
                    "Verify browser configuration and paths",
                    "Check for conflicting browser processes",
                    "Ensure browser drivers are up to date"
                ],
                "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.UPDATE_DEPENDENCIES],
                "related_documentation": ["browser_setup", "troubleshooting"]
            },
            
            "browser_crashed": {
                "category": ErrorCategory.BROWSER,
                "severity": ErrorSeverity.HIGH,
                "title": "Browser Crashed",
                "user_message": "The web browser crashed during execution.",
                "troubleshooting_steps": [
                    "Check browser logs for crash details",
                    "Verify system resources are sufficient",
                    "Check for problematic web content or scripts",
                    "Restart the browser and retry the operation"
                ],
                "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.RETRY],
                "related_documentation": ["browser_troubleshooting", "stability"]
            },
            
            # Selector Errors
            "selector_not_found": {
                "category": ErrorCategory.SELECTOR,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Selector Not Found",
                "user_message": "The CSS selector could not find any matching elements.",
                "troubleshooting_steps": [
                    "Verify the selector syntax is correct",
                    "Check if the web page structure has changed",
                    "Use browser developer tools to test the selector",
                    "Consider using alternative selectors"
                ],
                "recovery_actions": [RecoveryAction.RETRY, RecoveryAction.RECONFIGURE],
                "related_documentation": ["selector_guide", "web_scraping"]
            },
            
            "selector_invalid": {
                "category": ErrorCategory.SELECTOR,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Invalid Selector",
                "user_message": "The CSS selector syntax is invalid.",
                "troubleshooting_steps": [
                    "Check the selector for syntax errors",
                    "Verify all brackets and quotes are properly closed",
                    "Use a CSS validator to check the selector",
                    "Refer to CSS selector documentation"
                ],
                "recovery_actions": [RecoveryAction.RECONFIGURE],
                "related_documentation": ["selector_guide", "css_reference"]
            },
            
            # Plugin Errors
            "plugin_not_found": {
                "category": ErrorCategory.PLUGIN,
                "severity": ErrorSeverity.HIGH,
                "title": "Plugin Not Found",
                "user_message": "The required plugin could not be found or loaded.",
                "troubleshooting_steps": [
                    "Check if the plugin is installed and registered",
                    "Verify the plugin name is correct",
                    "Check plugin configuration and dependencies",
                    "Ensure the plugin is compatible with the current version"
                ],
                "recovery_actions": [RecoveryAction.UPDATE_DEPENDENCIES, RecoveryAction.RESTART],
                "related_documentation": ["plugin_development", "plugin_management"]
            },
            
            "plugin_execution_failed": {
                "category": ErrorCategory.PLUGIN,
                "severity": ErrorSeverity.MEDIUM,
                "title": "Plugin Execution Failed",
                "user_message": "A plugin encountered an error during execution.",
                "troubleshooting_steps": [
                    "Check the plugin logs for detailed error information",
                    "Verify the plugin has the required permissions",
                    "Check if the plugin configuration is correct",
                    "Test the plugin in isolation"
                ],
                "recovery_actions": [RecoveryAction.RETRY, RecoveryAction.RESTART],
                "related_documentation": ["plugin_troubleshooting", "plugin_development"]
            },
            
            # Cache Errors
            "cache_error": {
                "category": ErrorCategory.CACHE,
                "severity": ErrorSeverity.LOW,
                "title": "Cache Error",
                "user_message": "An error occurred while accessing the cache.",
                "troubleshooting_steps": [
                    "Check cache directory permissions",
                    "Verify sufficient disk space is available",
                    "Clear the cache and retry",
                    "Check cache configuration settings"
                ],
                "recovery_actions": [RecoveryAction.CLEAR_CACHE, RecoveryAction.RESTART],
                "related_documentation": ["cache_management", "troubleshooting"]
            }
        }
    
    def create_error_message(self, component_id: str, error_type: str, exception: Exception,
                            context: Optional[Dict[str, Any]] = None,
                            custom_data: Optional[Dict[str, Any]] = None) -> ErrorMessage:
        """Create a comprehensive error message."""
        # Get error template
        template = self._error_templates.get(error_type, self._get_default_template())
        
        # Generate error ID
        error_id = f"{component_id}_{error_type}_{int(datetime.utcnow().timestamp())}"
        
        # Get technical details
        technical_details = self._get_technical_details(exception)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(error_type, exception, context)
        
        # Create error message
        error_message = ErrorMessage(
            error_id=error_id,
            component_id=component_id,
            category=template["category"],
            severity=template["severity"],
            title=template["title"],
            description=template["description"],
            user_message=template["user_message"],
            technical_details=technical_details,
            troubleshooting_steps=template["troubleshooting_steps"],
            recovery_actions=template["recovery_actions"],
            related_documentation=template["related_documentation"],
            error_code=custom_data.get("error_code") if custom_data else None,
            context=context or {},
            suggestions=suggestions
        )
        
        # Add custom data if provided
        if custom_data:
            error_message.context.update(custom_data)
        
        return error_message
    
    def _get_default_template(self) -> Dict[str, Any]:
        """Get default error template for unknown errors."""
        return {
            "category": ErrorCategory.UNKNOWN,
            "severity": ErrorSeverity.MEDIUM,
            "title": "Unknown Error",
            "user_message": "An unexpected error occurred.",
            "troubleshooting_steps": [
                "Check the error details for more information",
                "Review the component logs for additional context",
                "Try restarting the component",
                "Contact support if the issue persists"
            ],
            "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.CONTACT_SUPPORT],
            "related_documentation": ["troubleshooting", "support"]
        }
    
    def _get_technical_details(self, exception: Exception) -> str:
        """Get technical details from exception."""
        details = []
        
        # Exception type and message
        details.append(f"Exception Type: {type(exception).__name__}")
        details.append(f"Exception Message: {str(exception)}")
        
        # Stack trace
        stack_trace = traceback.format_exc()
        if stack_trace:
            details.append(f"Stack Trace:\n{stack_trace}")
        
        # System information
        details.append(f"Python Version: {sys.version}")
        details.append(f"Platform: {sys.platform}")
        
        return "\n".join(details)
    
    def _generate_suggestions(self, error_type: str, exception: Exception,
                            context: Optional[Dict[str, Any]]) -> List[str]:
        """Generate contextual suggestions based on error type and context."""
        suggestions = []
        
        # Context-based suggestions
        if context:
            if "url" in context:
                suggestions.append("Try accessing the URL directly to verify it's accessible")
            
            if "selector" in context:
                suggestions.append("Test the selector in browser developer tools")
            
            if "timeout" in context:
                suggestions.append("Consider increasing the timeout value")
        
        # Exception-based suggestions
        exception_type = type(exception).__name__
        
        if exception_type == "ConnectionError":
            suggestions.append("Check network connectivity and firewall settings")
        elif exception_type == "TimeoutError":
            suggestions.append("Consider increasing timeout or optimizing performance")
        elif exception_type == "ValueError":
            suggestions.append("Validate input data format and values")
        elif exception_type == "KeyError":
            suggestions.append("Check if required keys are present in the data")
        elif exception_type == "AttributeError":
            suggestions.append("Verify object has the expected attributes")
        
        return suggestions
    
    def add_custom_message(self, error_message: ErrorMessage):
        """Add a custom error message."""
        self._custom_messages[error_message.error_id] = error_message
    
    def get_error_message(self, error_id: str) -> Optional[ErrorMessage]:
        """Get error message by ID."""
        return self._custom_messages.get(error_id)
    
    def get_error_messages_by_component(self, component_id: str) -> List[ErrorMessage]:
        """Get all error messages for a component."""
        return [msg for msg in self._custom_messages.values() if msg.component_id == component_id]
    
    def get_error_messages_by_severity(self, severity: ErrorSeverity) -> List[ErrorMessage]:
        """Get all error messages by severity."""
        return [msg for msg in self._custom_messages.values() if msg.severity == severity]
    
    def export_error_messages(self, format: str = "json") -> str:
        """Export error messages for analysis."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_messages": len(self._custom_messages),
            "messages": []
        }
        
        for msg in self._custom_messages.values():
            msg_data = {
                "error_id": msg.error_id,
                "component_id": msg.component_id,
                "category": msg.category.value,
                "severity": msg.severity.value,
                "title": msg.title,
                "description": msg.description,
                "user_message": msg.user_message,
                "technical_details": msg.technical_details,
                "troubleshooting_steps": msg.troubleshooting_steps,
                "recovery_actions": [action.value for action in msg.recovery_actions],
                "related_documentation": msg.related_documentation,
                "error_code": msg.error_code,
                "timestamp": msg.timestamp.isoformat(),
                "context": msg.context,
                "suggestions": msg.suggestions
            }
            data["messages"].append(msg_data)
        
        if format.lower() == "json":
            return json.dumps(data, indent=2)
        else:
            return str(data)


# Global error message repository
_error_messages = ComponentErrorMessages()


# Convenience functions
def create_error_message(component_id: str, error_type: str, exception: Exception,
                       context: Optional[Dict[str, Any]] = None,
                       custom_data: Optional[Dict[str, Any]] = None) -> ErrorMessage:
    """Create a comprehensive error message."""
    return _error_messages.create_error_message(component_id, error_type, exception, context, custom_data)


def get_error_message(error_id: str) -> Optional[ErrorMessage]:
    """Get error message by ID."""
    return _error_messages.get_error_message(error_id)


def get_error_messages_by_component(component_id: str) -> List[ErrorMessage]:
    """Get all error messages for a component."""
    return _error_messages.get_error_messages_by_component(component_id)


def get_error_messages_by_severity(severity: ErrorSeverity) -> List[ErrorMessage]:
    """Get all error messages by severity."""
    return _error_messages.get_error_messages_by_severity(severity)


def export_error_messages(format: str = "json") -> str:
    """Export error messages for analysis."""
    return _error_messages.export_error_messages(format)


# Error handling decorator
def handle_errors(error_type: str = "component_execution_failed",
                  reraise: bool = True,
                  return_error_message: bool = False):
    """Decorator to handle component errors and create comprehensive error messages."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Extract component ID from self or first argument
                    component_id = "unknown"
                    if args and hasattr(args[0], 'component_id'):
                        component_id = args[0].component_id
                    elif args:
                        component_id = type(args[0]).__name__
                    
                    # Create error message
                    context = {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
                    error_msg = create_error_message(component_id, error_type, e, context)
                    
                    # Store error message
                    _error_messages.add_custom_message(error_msg)
                    
                    if return_error_message:
                        return error_msg
                    elif reraise:
                        raise e
                    else:
                        return None
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Extract component ID from self or first argument
                    component_id = "unknown"
                    if args and hasattr(args[0], 'component_id'):
                        component_id = args[0].component_id
                    elif args:
                        component_id = type(args[0]).__name__
                    
                    # Create error message
                    context = {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
                    error_msg = create_error_message(component_id, error_type, e, context)
                    
                    # Store error message
                    _error_messages.add_custom_message(error_msg)
                    
                    if return_error_message:
                        return error_msg
                    elif reraise:
                        raise e
                    else:
                        return None
            
            return sync_wrapper
    
    return decorator


# User-friendly error formatting
def format_user_error(error_message: ErrorMessage) -> str:
    """Format error message for user display."""
    output = []
    
    # Title and severity
    output.append(f"❌ {error_message.title} ({error_message.severity.value.upper()})")
    output.append("")
    
    # User message
    output.append(f"📝 {error_message.user_message}")
    output.append("")
    
    # Troubleshooting steps
    if error_message.troubleshooting_steps:
        output.append("🔧 Troubleshooting Steps:")
        for i, step in enumerate(error_message.troubleshooting_steps, 1):
            output.append(f"   {i}. {step}")
        output.append("")
    
    # Recovery actions
    if error_message.recovery_actions:
        output.append("🔄 Recovery Actions:")
        for action in error_message.recovery_actions:
            output.append(f"   • {action.value.replace('_', ' ').title()}")
        output.append("")
    
    # Suggestions
    if error_message.suggestions:
        output.append("💡 Suggestions:")
        for suggestion in error_message.suggestions:
            output.append(f"   • {suggestion}")
        output.append("")
    
    # Error ID for support
    output.append(f"🆔 Error ID: {error_message.error_id}")
    
    return "\n".join(output)


# Technical error formatting
def format_technical_error(error_message: ErrorMessage) -> str:
    """Format error message for technical display."""
    output = []
    
    # Header
    output.append("=" * 80)
    output.append(f"ERROR: {error_message.title}")
    output.append("=" * 80)
    output.append("")
    
    # Basic info
    output.append(f"Error ID: {error_message.error_id}")
    output.append(f"Component: {error_message.component_id}")
    output.append(f"Category: {error_message.category.value}")
    output.append(f"Severity: {error_message.severity.value}")
    output.append(f"Timestamp: {error_message.timestamp.isoformat()}")
    output.append("")
    
    # Technical details
    output.append("TECHNICAL DETAILS:")
    output.append("-" * 40)
    output.append(error_message.technical_details)
    output.append("")
    
    # Context
    if error_message.context:
        output.append("CONTEXT:")
        output.append("-" * 40)
        for key, value in error_message.context.items():
            output.append(f"{key}: {value}")
        output.append("")
    
    # Recovery actions
    if error_message.recovery_actions:
        output.append("RECOVERY ACTIONS:")
        output.append("-" * 40)
        for action in error_message.recovery_actions:
            output.append(f"• {action.value}")
        output.append("")
    
    return "\n".join(output)
