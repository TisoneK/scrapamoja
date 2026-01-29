"""
Comprehensive error context collection for debugging

Provides detailed error context collection including system state, component status,
navigation history, and debugging information for troubleshooting navigation issues.
"""

import traceback
import sys
import os
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import asyncio

from .models import NavigationContext, NavigationEvent, NavigationOutcome
from .logging_config import get_navigation_logger


@dataclass
class SystemContext:
    """System context information"""
    python_version: str
    platform: str
    architecture: str
    cpu_count: int
    memory_total_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    process_id: int
    thread_count: int
    open_files: int


@dataclass
class ComponentContext:
    """Component-specific context"""
    component_name: str
    component_version: str
    status: str  # "active", "idle", "error", "stopped"
    last_activity: Optional[datetime]
    error_count: int
    last_error: Optional[str]
    configuration: Dict[str, Any]
    metrics: Dict[str, Any]


@dataclass
class NavigationContextInfo:
    """Navigation context information"""
    context_id: str
    session_id: str
    current_page: str
    pages_visited: int
    navigation_history: List[str]
    authentication_state: Optional[Dict[str, Any]]
    session_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class ErrorContext:
    """Comprehensive error context"""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    error_traceback: str
    correlation_id: Optional[str]
    session_id: Optional[str]
    component_name: str
    
    # Context information
    system_context: SystemContext
    component_context: ComponentContext
    navigation_context: Optional[NavigationContextInfo]
    
    # Additional debugging information
    recent_events: List[Dict[str, Any]]
    environment_variables: Dict[str, str]
    loaded_modules: List[str]
    memory_usage: Dict[str, float]
    
    # Recovery suggestions
    recovery_suggestions: List[str]
    related_errors: List[str]


class ErrorContextCollector:
    """Comprehensive error context collector"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize error context collector"""
        self.logger = get_navigation_logger("error_context_collector")
        self.config = config or {}
        
        # Collection configuration
        self.collect_system_info = self.config.get("collect_system_info", True)
        self.collect_component_info = self.config.get("collect_component_info", True)
        self.collect_navigation_info = self.config.get("collect_navigation_info", True)
        self.collect_environment_info = self.config.get("collect_environment_info", True)
        self.max_recent_events = self.config.get("max_recent_events", 50)
        
        # Component registry for context collection
        self._component_registry: Dict[str, Any] = {}
        
        # Error history
        self._error_history: List[ErrorContext] = []
        self._max_error_history = self.config.get("max_error_history", 100)
        
        self.logger.info(
            "Error context collector initialized",
            collect_system_info=self.collect_system_info,
            collect_component_info=self.collect_component_info
        )
    
    def register_component(self, name: str, component: Any) -> None:
        """Register component for context collection"""
        self._component_registry[name] = component
        self.logger.debug(
            "Component registered for error context",
            component_name=name
        )
    
    def collect_error_context(
        self,
        error: Exception,
        component_name: str,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        navigation_context: Optional[NavigationContext] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Collect comprehensive error context"""
        try:
            error_id = f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            self.logger.info(
                "Collecting error context",
                error_id=error_id,
                error_type=type(error).__name__,
                component_name=component_name
            )
            
            # Collect system context
            system_context = self._collect_system_context() if self.collect_system_info else None
            
            # Collect component context
            component_context = self._collect_component_context(component_name) if self.collect_component_info else None
            
            # Collect navigation context
            navigation_context_info = self._collect_navigation_context(navigation_context) if self.collect_navigation_info else None
            
            # Collect additional debugging information
            recent_events = self._collect_recent_events()
            environment_variables = self._collect_environment_variables() if self.collect_environment_info else {}
            loaded_modules = self._collect_loaded_modules()
            memory_usage = self._collect_memory_usage()
            
            # Generate recovery suggestions
            recovery_suggestions = self._generate_recovery_suggestions(error, component_name)
            
            # Find related errors
            related_errors = self._find_related_errors(error, component_name)
            
            # Create error context
            error_context = ErrorContext(
                error_id=error_id,
                timestamp=datetime.utcnow(),
                error_type=type(error).__name__,
                error_message=str(error),
                error_traceback=traceback.format_exc(),
                correlation_id=correlation_id,
                session_id=session_id,
                component_name=component_name,
                system_context=system_context,
                component_context=component_context,
                navigation_context=navigation_context_info,
                recent_events=recent_events,
                environment_variables=environment_variables,
                loaded_modules=loaded_modules,
                memory_usage=memory_usage,
                recovery_suggestions=recovery_suggestions,
                related_errors=related_errors
            )
            
            # Add to history
            self._add_to_history(error_context)
            
            self.logger.info(
                "Error context collected successfully",
                error_id=error_id,
                context_size=len(str(asdict(error_context)))
            )
            
            return error_context
            
        except Exception as e:
            self.logger.error(
                f"Failed to collect error context: {str(e)}",
                component_name=component_name
            )
            # Create minimal error context
            return ErrorContext(
                error_id=f"error_minimal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
                timestamp=datetime.utcnow(),
                error_type=type(error).__name__,
                error_message=str(error),
                error_traceback=traceback.format_exc(),
                correlation_id=correlation_id,
                session_id=session_id,
                component_name=component_name,
                system_context=None,
                component_context=None,
                navigation_context=None,
                recent_events=[],
                environment_variables={},
                loaded_modules=[],
                memory_usage={},
                recovery_suggestions=["Check component logs for more details"],
                related_errors=[]
            )
    
    def get_error_history(
        self,
        component_name: Optional[str] = None,
        error_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[ErrorContext]:
        """Get error history with optional filtering"""
        filtered_errors = self._error_history
        
        # Filter by component name
        if component_name:
            filtered_errors = [e for e in filtered_errors if e.component_name == component_name]
        
        # Filter by error type
        if error_type:
            filtered_errors = [e for e in filtered_errors if e.error_type == error_type]
        
        # Filter by timestamp
        if since:
            filtered_errors = [e for e in filtered_errors if e.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        filtered_errors.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered_errors[:limit]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self._error_history:
            return {
                "total_errors": 0,
                "error_types": {},
                "component_errors": {},
                "recent_errors": 0
            }
        
        # Count error types
        error_types = {}
        for error in self._error_history:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
        
        # Count component errors
        component_errors = {}
        for error in self._error_history:
            component_errors[error.component_name] = component_errors.get(error.component_name, 0) + 1
        
        # Count recent errors (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_errors = len([e for e in self._error_history if e.timestamp >= one_hour_ago])
        
        return {
            "total_errors": len(self._error_history),
            "error_types": error_types,
            "component_errors": component_errors,
            "recent_errors": recent_errors,
            "oldest_error": min(e.timestamp for e in self._error_history).isoformat(),
            "newest_error": max(e.timestamp for e in self._error_history).isoformat()
        }
    
    def clear_error_history(self) -> None:
        """Clear error history"""
        self._error_history.clear()
        self.logger.info("Error history cleared")
    
    def _collect_system_context(self) -> SystemContext:
        """Collect system context information"""
        try:
            return SystemContext(
                python_version=sys.version,
                platform=sys.platform,
                architecture=sys.architecture[0],
                cpu_count=psutil.cpu_count(),
                memory_total_mb=psutil.virtual_memory().total / (1024 * 1024),
                memory_available_mb=psutil.virtual_memory().available / (1024 * 1024),
                disk_usage_percent=psutil.disk_usage('/').percent,
                process_id=os.getpid(),
                thread_count=psutil.Process().num_threads(),
                open_files=len(psutil.Process().open_files())
            )
        except Exception as e:
            self.logger.warning(f"Failed to collect system context: {str(e)}")
            return SystemContext(
                python_version=sys.version,
                platform=sys.platform,
                architecture="unknown",
                cpu_count=0,
                memory_total_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                process_id=0,
                thread_count=0,
                open_files=0
            )
    
    def _collect_component_context(self, component_name: str) -> ComponentContext:
        """Collect component-specific context"""
        try:
            component = self._component_registry.get(component_name)
            
            if not component:
                return ComponentContext(
                    component_name=component_name,
                    component_version="unknown",
                    status="not_registered",
                    last_activity=None,
                    error_count=0,
                    last_error=None,
                    configuration={},
                    metrics={}
                )
            
            # Try to extract component information
            status = "active"
            last_activity = datetime.utcnow()
            error_count = 0
            last_error = None
            configuration = {}
            metrics = {}
            
            # Check if component has status methods
            if hasattr(component, 'get_status'):
                try:
                    status_info = component.get_status()
                    status = status_info.get('status', 'active')
                    last_activity = status_info.get('last_activity', datetime.utcnow())
                    error_count = status_info.get('error_count', 0)
                    last_error = status_info.get('last_error')
                except:
                    pass
            
            # Check if component has configuration
            if hasattr(component, 'config'):
                try:
                    configuration = dict(component.config)
                except:
                    pass
            
            # Check if component has metrics
            if hasattr(component, 'get_metrics'):
                try:
                    metrics = component.get_metrics()
                except:
                    pass
            
            # Get component version
            version = "unknown"
            if hasattr(component, '__version__'):
                version = component.__version__
            elif hasattr(component, 'VERSION'):
                version = component.VERSION
            
            return ComponentContext(
                component_name=component_name,
                component_version=version,
                status=status,
                last_activity=last_activity,
                error_count=error_count,
                last_error=last_error,
                configuration=configuration,
                metrics=metrics
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to collect component context for {component_name}: {str(e)}")
            return ComponentContext(
                component_name=component_name,
                component_version="unknown",
                status="error",
                last_activity=datetime.utcnow(),
                error_count=1,
                last_error=str(e),
                configuration={},
                metrics={}
            )
    
    def _collect_navigation_context(self, navigation_context: Optional[NavigationContext]) -> Optional[NavigationContextInfo]:
        """Collect navigation context information"""
        if not navigation_context:
            return None
        
        try:
            return NavigationContextInfo(
                context_id=navigation_context.context_id,
                session_id=navigation_context.session_id,
                current_page=navigation_context.current_page.url if navigation_context.current_page else "",
                pages_visited=navigation_context.pages_visited,
                navigation_history=list(navigation_context.navigation_history),
                authentication_state=asdict(navigation_context.authentication_state) if navigation_context.authentication_state else None,
                session_data=dict(navigation_context.session_data),
                created_at=navigation_context.created_at,
                updated_at=navigation_context.updated_at
            )
        except Exception as e:
            self.logger.warning(f"Failed to collect navigation context: {str(e)}")
            return None
    
    def _collect_recent_events(self) -> List[Dict[str, Any]]:
        """Collect recent navigation events"""
        try:
            # This would integrate with the event publisher to get recent events
            # For now, return empty list
            return []
        except Exception as e:
            self.logger.warning(f"Failed to collect recent events: {str(e)}")
            return []
    
    def _collect_environment_variables(self) -> Dict[str, str]:
        """Collect relevant environment variables"""
        relevant_vars = [
            'PATH', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV',
            'NAVIGATION_ENV', 'LOG_LEVEL', 'DEBUG'
        ]
        
        env_vars = {}
        for var in relevant_vars:
            if var in os.environ:
                env_vars[var] = os.environ[var]
        
        return env_vars
    
    def _collect_loaded_modules(self) -> List[str]:
        """Collect list of loaded modules"""
        try:
            return [name for name in sys.modules.keys() if name.startswith('navigation')]
        except Exception as e:
            self.logger.warning(f"Failed to collect loaded modules: {str(e)}")
            return []
    
    def _collect_memory_usage(self) -> Dict[str, float]:
        """Collect memory usage information"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
                "percent": process.memory_percent()
            }
        except Exception as e:
            self.logger.warning(f"Failed to collect memory usage: {str(e)}")
            return {}
    
    def _generate_recovery_suggestions(self, error: Exception, component_name: str) -> List[str]:
        """Generate recovery suggestions based on error type"""
        suggestions = []
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Common error patterns and suggestions
        if "timeout" in error_message:
            suggestions.extend([
                "Increase timeout configuration for the component",
                "Check network connectivity and response times",
                "Verify if the target service is responding properly"
            ])
        
        if "connection" in error_message:
            suggestions.extend([
                "Check network connectivity",
                "Verify service endpoints are accessible",
                "Check firewall and security settings"
            ])
        
        if "memory" in error_message or "out of memory" in error_message:
            suggestions.extend([
                "Increase available memory",
                "Check for memory leaks in the component",
                "Reduce batch sizes or processing limits"
            ])
        
        if "permission" in error_message or "access" in error_message:
            suggestions.extend([
                "Check file and directory permissions",
                "Verify user has required access rights",
                "Check security policies and restrictions"
            ])
        
        if "not found" in error_message:
            suggestions.extend([
                "Verify required files and resources exist",
                "Check installation and deployment",
                "Verify configuration paths are correct"
            ])
        
        # Component-specific suggestions
        if component_name == "route_discovery":
            suggestions.extend([
                "Check if the target URL is accessible",
                "Verify selector engine is properly initialized",
                "Check browser automation setup"
            ])
        elif component_name == "path_planning":
            suggestions.extend([
                "Verify route graph is properly constructed",
                "Check planning algorithm parameters",
                "Ensure sufficient memory for graph operations"
            ])
        elif component_name == "route_adaptation":
            suggestions.extend([
                "Check adaptation strategy configuration",
                "Verify stealth system integration",
                "Check retry and timeout settings"
            ])
        
        # Generic suggestions
        if not suggestions:
            suggestions.extend([
                "Check component logs for detailed error information",
                "Verify component configuration is correct",
                "Restart the component if the error persists",
                "Check system resources and availability"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _find_related_errors(self, error: Exception, component_name: str) -> List[str]:
        """Find related errors from history"""
        try:
            error_message = str(error).lower()
            related_errors = []
            
            for historical_error in self._error_history[-20:]:  # Check last 20 errors
                if (historical_error.component_name == component_name and
                    historical_error.error_type == type(error).__name__):
                    related_errors.append(historical_error.error_id)
            
            return related_errors[:5]  # Limit to 5 related errors
            
        except Exception as e:
            self.logger.warning(f"Failed to find related errors: {str(e)}")
            return []
    
    def _add_to_history(self, error_context: ErrorContext) -> None:
        """Add error context to history"""
        self._error_history.append(error_context)
        
        # Limit history size
        if len(self._error_history) > self._max_error_history:
            self._error_history = self._error_history[-self._max_error_history:]
    
    def export_error_context(self, error_context: ErrorContext, file_path: str) -> None:
        """Export error context to file"""
        try:
            # Convert to dictionary and handle datetime serialization
            context_dict = asdict(error_context)
            
            # Handle datetime serialization
            for key, value in context_dict.items():
                if isinstance(value, datetime):
                    context_dict[key] = value.isoformat()
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, datetime):
                            value[sub_key] = sub_value.isoformat()
            
            with open(file_path, 'w') as f:
                json.dump(context_dict, f, indent=2, default=str)
            
            self.logger.info(
                "Error context exported",
                error_id=error_context.error_id,
                file_path=file_path
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to export error context: {str(e)}",
                error_id=error_context.error_id
            )


# Global error context collector instance
_error_collector: Optional[ErrorContextCollector] = None


def get_error_collector(config: Optional[Dict[str, Any]] = None) -> ErrorContextCollector:
    """Get global error context collector instance"""
    global _error_collector
    
    if _error_collector is None:
        _error_collector = ErrorContextCollector(config)
    
    return _error_collector


def register_component_for_error_context(name: str, component: Any) -> None:
    """Register component for error context collection"""
    collector = get_error_collector()
    collector.register_component(name, component)


def collect_error_context(
    error: Exception,
    component_name: str,
    correlation_id: Optional[str] = None,
    session_id: Optional[str] = None,
    navigation_context: Optional[NavigationContext] = None
) -> ErrorContext:
    """Collect error context using global collector"""
    collector = get_error_collector()
    return collector.collect_error_context(
        error, component_name, correlation_id, session_id, navigation_context
    )
