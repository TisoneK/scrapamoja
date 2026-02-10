"""
Logging framework integration for template framework.

This module provides automatic integration with structured logging,
including correlation IDs, performance logging, and template-specific logging.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .integration_bridge import BaseIntegrationBridge


logger = logging.getLogger(__name__)


class LoggingFrameworkIntegration:
    """
    Logging framework integration for template framework.
    
    This class provides automatic integration with structured logging
    features, enabling templates to use consistent logging with correlation
    IDs and performance tracking.
    """
    
    def __init__(self, integration_bridge: BaseIntegrationBridge):
        """
        Initialize logging framework integration.
        
        Args:
            integration_bridge: The integration bridge instance
        """
        self.integration_bridge = integration_bridge
        self.template_name = integration_bridge.template_name
        
        # Logging state
        self.logging_active = False
        self.correlation_id = None
        self.session_id = None
        self.logger = None
        
        # Feature availability
        self.features_available = {
            "structured_logging": False,
            "correlation_ids": False,
            "performance_logging": False,
            "error_tracking": False,
            "log_aggregation": False
        }
        
        # Configuration
        self.config = {
            "auto_logging": True,
            "log_level": "INFO",
            "log_format": "structured",
            "include_performance": True,
            "include_correlation": True,
            "log_to_file": False,
            "log_file_path": None,
            "max_log_size": 10485760,  # 10MB
            "log_rotation": True,
            "error_log_separate": True
        }
        
        # Performance tracking
        self.performance_log = []
        self.error_log = []
        
        logger.info(f"LoggingFrameworkIntegration initialized for {template_name}")
    
    async def initialize_logging_integration(self) -> bool:
        """
        Initialize logging framework integration.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info(f"Initializing logging framework for {self.template_name}")
            
            # Detect logging capabilities
            await self._detect_logging_capabilities()
            
            # Initialize structured logging
            if not await self._initialize_structured_logging():
                logger.warning("Structured logging initialization failed")
                return False
            
            # Setup correlation IDs
            await self._setup_correlation_ids()
            
            # Setup performance logging
            await self._setup_performance_logging()
            
            # Setup error tracking
            await self._setup_error_tracking()
            
            logger.info(f"Logging framework initialized successfully for {self.template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize logging framework: {e}")
            return False
    
    async def _detect_logging_capabilities(self) -> None:
        """Detect logging framework capabilities."""
        try:
            # Get logging capabilities from integration bridge
            available_components = self.integration_bridge.get_available_components()
            
            # Detect logging framework capabilities
            logging_framework = available_components.get("logging_framework", {})
            
            self.features_available["structured_logging"] = logging_framework.get("supports_structured_logging", False)
            self.features_available["correlation_ids"] = logging_framework.get("supports_correlation_ids", False)
            self.features_available["performance_logging"] = logging_framework.get("supports_performance_logging", False)
            
            # Try to detect structlog
            try:
                import structlog
                self.features_available["structured_logging"] = True
                self.features_available["correlation_ids"] = True
                self.features_available["performance_logging"] = True
                logger.debug("structlog available for enhanced logging")
            except ImportError:
                logger.debug("structlog not available, using standard logging")
            
            # Try to detect log aggregation
            try:
                # Check for log aggregation libraries
                import elasticsearch
                import redis
                self.features_available["log_aggregation"] = True
                logger.debug("log aggregation available")
            except ImportError:
                self.features_available["log_aggregation"] = False
                logger.debug("log aggregation not available")
            
            logger.debug(f"Logging framework capabilities detected: {list(self.features_available.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to detect logging capabilities: {e}")
    
    async def _initialize_structured_logging(self) -> bool:
        """Initialize structured logging."""
        try:
            if self.features_available["structured_logging"]:
                # Use structlog for structured logging
                await self._setup_structlog()
            else:
                # Use standard logging with structured format
                await self._setup_standard_logging()
            
            self.logging_active = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize structured logging: {e}")
            return False
    
    async def _setup_structlog(self) -> None:
        """Setup structlog for structured logging."""
        try:
            import structlog
            
            # Configure structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            # Create template-specific logger
            self.logger = structlog.get_logger(f"template.{self.template_name}")
            
            logger.info("structlog configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup structlog: {e}")
            raise
    
    async def _setup_standard_logging(self) -> None:
        """Setup standard logging with structured format."""
        try:
            # Create template-specific logger
            self.logger = logging.getLogger(f"template.{self.template_name}")
            
            # Set log level
            log_level = getattr(logging, self.config.get("log_level", "INFO").upper())
            self.logger.setLevel(log_level)
            
            # Create formatter
            if self.config.get("log_format") == "structured":
                formatter = self._create_structured_formatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            # Add console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # Add file handler if configured
            if self.config.get("log_to_file", False):
                await self._setup_file_logging(formatter)
            
            logger.info("Standard logging configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup standard logging: {e}")
            raise
    
    def _create_structured_formatter(self) -> logging.Formatter:
        """Create a structured formatter for standard logging."""
        try:
            import json
            
            class StructuredFormatter(logging.Formatter):
                def format(self, record):
                    log_entry = {
                        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        "template": self.template_name,
                        "correlation_id": getattr(record, 'correlation_id', None),
                        "session_id": getattr(record, 'session_id', None)
                    }
                    
                    # Add exception info if present
                    if record.exc_info:
                        log_entry["exception"] = self.formatException(record.exc_info)
                    
                    # Add extra fields
                    for key, value in record.__dict__.items():
                        if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                      'pathname', 'filename', 'module', 'lineno', 
                                      'funcName', 'created', 'msecs', 'relativeCreated', 
                                      'thread', 'threadName', 'processName', 'process',
                                      'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                            log_entry[key] = value
                    
                    return json.dumps(log_entry)
            
            return StructuredFormatter()
            
        except Exception as e:
            logger.error(f"Failed to create structured formatter: {e}")
            return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    async def _setup_file_logging(self, formatter: logging.Formatter) -> None:
        """Setup file logging."""
        try:
            log_file_path = self.config.get("log_file_path")
            if not log_file_path:
                # Generate default log file path
                timestamp = datetime.now().strftime("%Y%m%d")
                log_file_path = f"logs/{self.template_name}_{timestamp}.log"
            
            # Create log directory if needed
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file handler
            if self.config.get("log_rotation", True):
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=self.config.get("max_log_size", 10485760),
                    backupCount=5
                )
            else:
                file_handler = logging.FileHandler(log_file_path)
            
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            logger.info(f"File logging configured: {log_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup file logging: {e}")
    
    async def _setup_correlation_ids(self) -> None:
        """Setup correlation IDs for request tracking."""
        try:
            # Generate correlation ID
            self.correlation_id = str(uuid.uuid4())
            
            # Generate session ID
            self.session_id = str(uuid.uuid4())
            
            # Add correlation context to logger
            if self.logger and hasattr(self.logger, 'bind'):
                self.logger = self.logger.bind(
                    correlation_id=self.correlation_id,
                    session_id=self.session_id,
                    template=self.template_name
                )
            
            logger.info(f"Correlation IDs setup: {self.correlation_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup correlation IDs: {e}")
    
    async def _setup_performance_logging(self) -> None:
        """Setup performance logging."""
        try:
            if not self.features_available["performance_logging"]:
                logger.debug("Performance logging not available")
                return
            
            # Performance logging will be handled by log_performance method
            logger.info("Performance logging setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup performance logging: {e}")
    
    async def _setup_error_tracking(self) -> None:
        """Setup error tracking."""
        try:
            # Error tracking will be handled by log_error method
            logger.info("Error tracking setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup error tracking: {e}")
    
    def log_performance(self, operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log performance metrics.
        
        Args:
            operation: Operation name
            duration: Operation duration in seconds
            metadata: Additional metadata
        """
        try:
            if not self.logging_active or not self.logger:
                return
            
            performance_data = {
                "operation": operation,
                "duration": duration,
                "template": self.template_name,
                "timestamp": datetime.now().isoformat()
            }
            
            if metadata:
                performance_data.update(metadata)
            
            # Add to performance log
            self.performance_log.append(performance_data)
            
            # Keep only recent entries
            if len(self.performance_log) > 1000:
                self.performance_log = self.performance_log[-1000:]
            
            # Log performance
            if hasattr(self.logger, 'info'):
                self.logger.info("Performance metric", **performance_data)
            else:
                self.logger.info(f"Performance: {operation} took {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"Failed to log performance: {e}")
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error with context.
        
        Args:
            error: Exception that occurred
            context: Additional context
        """
        try:
            if not self.logging_active or not self.logger:
                return
            
            error_data = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "template": self.template_name,
                "timestamp": datetime.now().isoformat()
            }
            
            if context:
                error_data.update(context)
            
            # Add to error log
            self.error_log.append(error_data)
            
            # Keep only recent entries
            if len(self.error_log) > 1000:
                self.error_log = self.error_log[-1000:]
            
            # Log error
            if hasattr(self.logger, 'error'):
                self.logger.error("Error occurred", **error_data, exc_info=True)
            else:
                self.logger.error(f"Error in {self.template_name}: {error}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        try:
            if not self.logging_active or not self.logger:
                return
            
            log_data = {
                "template": self.template_name,
                "timestamp": datetime.now().isoformat()
            }
            log_data.update(kwargs)
            
            if hasattr(self.logger, 'info'):
                self.logger.info(message, **log_data)
            else:
                self.logger.info(f"{message} - {log_data}")
                
        except Exception as e:
            logger.error(f"Failed to log info: {e}")
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        try:
            if not self.logging_active or not self.logger:
                return
            
            log_data = {
                "template": self.template_name,
                "timestamp": datetime.now().isoformat()
            }
            log_data.update(kwargs)
            
            if hasattr(self.logger, 'warning'):
                self.logger.warning(message, **log_data)
            else:
                self.logger.warning(f"{message} - {log_data}")
                
        except Exception as e:
            logger.error(f"Failed to log warning: {e}")
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        try:
            if not self.logging_active or not self.logger:
                return
            
            log_data = {
                "template": self.template_name,
                "timestamp": datetime.now().isoformat()
            }
            log_data.update(kwargs)
            
            if hasattr(self.logger, 'debug'):
                self.logger.debug(message, **log_data)
            else:
                self.logger.debug(f"{message} - {log_data}")
                
        except Exception as e:
            logger.error(f"Failed to log debug: {e}")
    
    def get_logging_status(self) -> Dict[str, Any]:
        """
        Get current logging status.
        
        Returns:
            Dict[str, Any]: Logging status
        """
        return {
            "template_name": self.template_name,
            "logging_active": self.logging_active,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "features_available": self.features_available,
            "config": self.config,
            "performance_log_count": len(self.performance_log),
            "error_log_count": len(self.error_log)
        }
    
    def get_performance_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get performance log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: Performance log entries
        """
        return self.performance_log[-limit:] if self.performance_log else []
    
    def get_error_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get error log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: Error log entries
        """
        return self.error_log[-limit:] if self.error_log else []
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update logging configuration.
        
        Args:
            new_config: New configuration values
        """
        self.config.update(new_config)
        logger.info(f"Logging configuration updated: {list(new_config.keys())}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current logging configuration.
        
        Returns:
            Dict[str, Any]: Current configuration
        """
        return self.config.copy()
    
    def get_correlation_id(self) -> Optional[str]:
        """
        Get current correlation ID.
        
        Returns:
            Optional[str]: Correlation ID
        """
        return self.correlation_id
    
    def get_session_id(self) -> Optional[str]:
        """
        Get current session ID.
        
        Returns:
            Optional[str]: Session ID
        """
        return self.session_id
