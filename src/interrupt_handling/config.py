"""
Configuration management for interrupt handling behavior.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os


@dataclass
class InterruptConfig:
    """Configuration for interrupt handling behavior."""
    
    # Signal handling
    handle_sigint: bool = True
    handle_sigterm: bool = True
    handle_sigbreak: bool = True  # Windows-specific
    
    # Cleanup timeouts (seconds)
    default_cleanup_timeout: float = 30.0
    database_cleanup_timeout: float = 10.0
    file_cleanup_timeout: float = 5.0
    network_cleanup_timeout: float = 15.0
    custom_cleanup_timeout: float = 20.0
    
    # Shutdown phase timeouts (seconds)
    acknowledgment_timeout: float = 2.0
    critical_operations_timeout: float = 60.0
    resource_cleanup_timeout: float = 30.0
    data_preservation_timeout: float = 45.0
    finalization_timeout: float = 5.0
    
    # Data preservation settings
    checkpoint_directory: str = "./checkpoints"
    max_checkpoints: int = 10
    checkpoint_interval: float = 60.0  # Auto-checkpoint interval in seconds
    enable_checkpoints: bool = True
    
    # Feature flags
    enable_interrupt_handling: bool = True
    enable_resource_cleanup: bool = True
    enable_data_preservation: bool = True
    enable_user_feedback: bool = True
    
    # Cleanup priorities
    cleanup_priorities: Dict[str, int] = field(default_factory=lambda: {
        'database': 100,
        'file': 90,
    })
    
    # User feedback settings
    feedback_verbosity: str = "normal"  # minimal, normal, verbose
    enable_progress_bars: bool = True
    enable_colors: bool = True
    enable_icons: bool = True
    verbose_feedback: bool = False
    show_progress_bar: bool = True
    
    # Logging settings
    enable_shutdown_logging: bool = True
    log_file_path: Optional[str] = None
    log_level: str = "INFO"
    
    # Graceful shutdown settings
    enable_graceful_shutdown: bool = True
    shutdown_coordinator_enabled: bool = True
    force_termination_timeout: float = 120.0  # Force termination after this time
    
    # Cleanup priority settings
    enable_parallel_cleanup: bool = False
    max_parallel_cleanup_tasks: int = 3
    priority_ordering_strategy: str = "sequential"  # sequential, parallel, dependency_based
    
    # Feature flags
    experimental_features_enabled: bool = False
    performance_monitoring_enabled: bool = False
    testing_mode_enabled: bool = False
    
    # Backward compatibility
    compatibility_mode: str = "modern"  # legacy, transitional, modern, disabled
    compatibility_warnings: bool = True
    warning_threshold: int = 3
    
    @classmethod
    def from_env(cls) -> 'InterruptConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if 'SCRAPAMOJA_INTERRUPT_ENABLED' in os.environ:
            config.enable_interrupt_handling = os.environ['SCRAPAMOJA_INTERRUPT_ENABLED'].lower() == 'true'
        
        if 'SCRAPAMOJA_INTERRUPT_CLEANUP_TIMEOUT' in os.environ:
            config.default_cleanup_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_CLEANUP_TIMEOUT'])
        
        if 'SCRAPAMOJA_INTERRUPT_CHECKPOINT_DIR' in os.environ:
            config.checkpoint_directory = os.environ['SCRAPAMOJA_INTERRUPT_CHECKPOINT_DIR']
        
        if 'SCRAPAMOJA_INTERRUPT_VERBOSITY' in os.environ:
            config.feedback_verbosity = os.environ['SCRAPAMOJA_INTERRUPT_VERBOSITY']
        
        # Shutdown phase timeouts
        if 'SCRAPAMOJA_INTERRUPT_ACK_TIMEOUT' in os.environ:
            config.acknowledgment_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_ACK_TIMEOUT'])
        
        if 'SCRAPAMOJA_INTERRUPT_CRITICAL_TIMEOUT' in os.environ:
            config.critical_operations_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_CRITICAL_TIMEOUT'])
        
        if 'SCRAPAMOJA_INTERRUPT_RESOURCE_TIMEOUT' in os.environ:
            config.resource_cleanup_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_RESOURCE_TIMEOUT'])
        
        if 'SCRAPAMOJA_INTERRUPT_DATA_TIMEOUT' in os.environ:
            config.data_preservation_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_DATA_TIMEOUT'])
        
        if 'SCRAPAMOJA_INTERRUPT_FINALIZE_TIMEOUT' in os.environ:
            config.finalization_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_FINALIZE_TIMEOUT'])
        
        if 'SCRAPAMOJA_INTERRUPT_FORCE_TIMEOUT' in os.environ:
            config.force_termination_timeout = float(os.environ['SCRAPAMOJA_INTERRUPT_FORCE_TIMEOUT'])
        
        # Data preservation settings
        if 'SCRAPAMOJA_CHECKPOINT_DIR' in os.environ:
            config.checkpoint_directory = os.environ['SCRAPAMOJA_CHECKPOINT_DIR']
        
        if 'SCRAPAMOJA_MAX_CHECKPOINTS' in os.environ:
            config.max_checkpoints = int(os.environ['SCRAPAMOJA_MAX_CHECKPOINTS'])
        
        if 'SCRAPAMOJA_CHECKPOINT_INTERVAL' in os.environ:
            config.checkpoint_interval = float(os.environ['SCRAPAMOJA_CHECKPOINT_INTERVAL'])
        
        if 'SCRAPAMOJA_CHECKPOINTS_ENABLED' in os.environ:
            config.enable_checkpoints = os.environ['SCRAPAMOJA_CHECKPOINTS_ENABLED'].lower() == 'true'
        
        # Cleanup priority settings
        if 'SCRAPAMOJA_INTERRUPT_PARALLEL_CLEANUP' in os.environ:
            config.enable_parallel_cleanup = os.environ['SCRAPAMOJA_INTERRUPT_PARALLEL_CLEANUP'].lower() == 'true'
        
        if 'SCRAPAMOJA_INTERRUPT_MAX_PARALLEL' in os.environ:
            config.max_parallel_cleanup_tasks = int(os.environ['SCRAPAMOJA_INTERRUPT_MAX_PARALLEL'])
        
        if 'SCRAPAMOJA_INTERRUPT_PRIORITY_STRATEGY' in os.environ:
            config.priority_ordering_strategy = os.environ['SCRAPAMOJA_INTERRUPT_PRIORITY_STRATEGY']
        
        # Feature flags
        if 'SCRAPAMOJA_EXPERIMENTAL' in os.environ:
            config.experimental_features_enabled = os.environ['SCRAPAMOJA_EXPERIMENTAL'].lower() == 'true'
        
        if 'SCRAPAMOJA_PERFORMANCE_MONITORING' in os.environ:
            config.performance_monitoring_enabled = os.environ['SCRAPAMOJA_PERFORMANCE_MONITORING'].lower() == 'true'
        
        if 'SCRAPAMOJA_TESTING_MODE' in os.environ:
            config.testing_mode_enabled = os.environ['SCRAPAMOJA_TESTING_MODE'].lower() == 'true'
        
        # Backward compatibility
        if 'SCRAPAMOJA_COMPATIBILITY_MODE' in os.environ:
            config.compatibility_mode = os.environ['SCRAPAMOJA_COMPATIBILITY_MODE']
        
        if 'SCRAPAMOJA_COMPATIBILITY_WARNINGS' in os.environ:
            config.compatibility_warnings = os.environ['SCRAPAMOJA_COMPATIBILITY_WARNINGS'].lower() == 'true'
        
        if 'SCRAPAMOJA_WARNING_THRESHOLD' in os.environ:
            config.warning_threshold = int(os.environ['SCRAPAMOJA_WARNING_THRESHOLD'])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enable_interrupt_handling': self.enable_interrupt_handling,
            'handle_sigint': self.handle_sigint,
            'handle_sigterm': self.handle_sigterm,
            'handle_sigbreak': self.handle_sigbreak,
            'default_cleanup_timeout': self.default_cleanup_timeout,
            'database_cleanup_timeout': self.database_cleanup_timeout,
            'file_cleanup_timeout': self.file_cleanup_timeout,
            'network_cleanup_timeout': self.network_cleanup_timeout,
            'custom_cleanup_timeout': self.custom_cleanup_timeout,
            'acknowledgment_timeout': self.acknowledgment_timeout,
            'critical_operations_timeout': self.critical_operations_timeout,
            'resource_cleanup_timeout': self.resource_cleanup_timeout,
            'data_preservation_timeout': self.data_preservation_timeout,
            'finalization_timeout': self.finalization_timeout,
            'force_termination_timeout': self.force_termination_timeout,
            'enable_checkpoints': self.enable_checkpoints,
            'checkpoint_interval': self.checkpoint_interval,
            'checkpoint_directory': self.checkpoint_directory,
            'max_checkpoints': self.max_checkpoints,
            'enable_resource_cleanup': self.enable_resource_cleanup,
            'enable_data_preservation': self.enable_data_preservation,
            'enable_user_feedback': self.enable_user_feedback,
            'cleanup_priorities': self.cleanup_priorities,
            'feedback_verbosity': self.feedback_verbosity,
            'enable_progress_bars': self.enable_progress_bars,
            'enable_colors': self.enable_colors,
            'enable_icons': self.enable_icons,
            'verbose_feedback': self.verbose_feedback,
            'show_progress_bar': self.show_progress_bar,
            'enable_shutdown_logging': self.enable_shutdown_logging,
            'log_file_path': self.log_file_path,
            'log_level': self.log_level,
            'enable_graceful_shutdown': self.enable_graceful_shutdown,
            'shutdown_coordinator_enabled': self.shutdown_coordinator_enabled,
            'force_termination_timeout': self.force_termination_timeout,
            'enable_parallel_cleanup': self.enable_parallel_cleanup,
            'max_parallel_cleanup_tasks': self.max_parallel_cleanup_tasks,
            'priority_ordering_strategy': self.priority_ordering_strategy,
            'experimental_features_enabled': self.experimental_features_enabled,
            'performance_monitoring_enabled': self.performance_monitoring_enabled,
            'testing_mode_enabled': self.testing_mode_enabled,
            'compatibility_mode': self.compatibility_mode,
            'compatibility_warnings': self.compatibility_warnings,
            'warning_threshold': self.warning_threshold
        }
