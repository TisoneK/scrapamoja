"""
Base Interfaces for Resilience Managers

Defines abstract interfaces for all resilience components following deep
modularity principles with clear contracts and lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from .events import ResilienceEvent


class IResilienceManager(ABC):
    """Base interface for all resilience managers."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the resilience manager."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the resilience manager gracefully."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        pass


class ICheckpointManager(IResilienceManager):
    """Interface for checkpoint management operations."""
    
    @abstractmethod
    async def create_checkpoint(
        self,
        job_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new checkpoint for the specified job.
        
        Args:
            job_id: Unique identifier for the scraping job
            data: Job state data to checkpoint
            metadata: Optional metadata about the checkpoint
            
        Returns:
            Checkpoint ID if successful
            
        Raises:
            CheckpointCreationError: If checkpoint creation fails
            ValidationError: If data is invalid
        """
        pass
    
    @abstractmethod
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data by ID.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            Checkpoint data if found, None otherwise
            
        Raises:
            CheckpointCorruptionError: If checkpoint is corrupted
            ValidationError: If checkpoint format is invalid
        """
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self,
        job_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint metadata
        """
        pass
    
    @abstractmethod
    async def delete_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def validate_checkpoint(
        self,
        checkpoint_id: str
    ) -> bool:
        """
        Validate checkpoint integrity.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            
        Returns:
            True if valid, False otherwise
        """
        pass


class IRetryManager(IResilienceManager):
    """Interface for retry logic with configurable policies."""
    
    @abstractmethod
    async def execute_with_retry(
        self,
        operation: Callable,
        retry_policy_id: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: The operation to execute
            retry_policy_id: ID of retry policy to use
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Result of the operation
            
        Raises:
            MaxRetriesExceededError: If all retry attempts fail
            PermanentFailureError: If failure is classified as permanent
        """
        pass
    
    @abstractmethod
    async def classify_failure(
        self,
        error: Exception
    ) -> str:
        """
        Classify a failure as transient or permanent.
        
        Args:
            error: The exception to classify
            
        Returns:
            Classification result ("transient" or "permanent")
        """
        pass
    
    @abstractmethod
    async def calculate_backoff_delay(
        self,
        attempt: int,
        retry_policy_id: str
    ) -> float:
        """
        Calculate backoff delay for retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            retry_policy_id: ID of retry policy to use
            
        Returns:
            Delay in seconds before next retry
        """
        pass
    
    @abstractmethod
    async def create_retry_policy(
        self,
        policy_config: Dict[str, Any]
    ) -> str:
        """
        Create a new retry policy.
        
        Args:
            policy_config: Policy configuration parameters
            
        Returns:
            ID of created policy
        """
        pass


class IResourceMonitor(IResilienceManager):
    """Interface for system resource monitoring."""
    
    @abstractmethod
    async def start_monitoring(
        self,
        threshold_id: str,
        callback: Callable
    ) -> str:
        """
        Start resource monitoring with specified thresholds.
        
        Args:
            threshold_id: ID of resource threshold configuration
            callback: Callback function to invoke on threshold breach
            
        Returns:
            Monitoring session ID
        """
        pass
    
    @abstractmethod
    async def stop_monitoring(
        self,
        session_id: str
    ) -> bool:
        """
        Stop resource monitoring session.
        
        Args:
            session_id: Monitoring session ID
            
        Returns:
            True if stopped successfully
        """
        pass
    
    @abstractmethod
    async def get_current_metrics(
        self
    ) -> Dict[str, Any]:
        """
        Get current system resource metrics.
        
        Returns:
            Dictionary containing current metrics
        """
        pass
    
    @abstractmethod
    async def check_thresholds(
        self,
        threshold_id: str
    ) -> Dict[str, bool]:
        """
        Check if current metrics exceed specified thresholds.
        
        Args:
            threshold_id: ID of threshold configuration
            
        Returns:
            Dictionary mapping threshold names to breach status
        """
        pass
    
    @abstractmethod
    async def create_resource_threshold(
        self,
        threshold_config: Dict[str, Any]
    ) -> str:
        """
        Create a new resource threshold configuration.
        
        Args:
            threshold_config: Threshold configuration parameters
            
        Returns:
            ID of created threshold
        """
        pass


class IAbortManager(IResilienceManager):
    """Interface for abort policies and intelligent failure detection."""
    
    @abstractmethod
    async def evaluate_abort_conditions(
        self,
        job_id: str,
        abort_policy_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate abort conditions for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            abort_policy_id: ID of abort policy to use
            
        Returns:
            Evaluation result with abort decision and reasoning
        """
        pass
    
    @abstractmethod
    async def record_failure(
        self,
        job_id: str,
        failure_event: Dict[str, Any]
    ) -> None:
        """
        Record a failure event for abort evaluation.
        
        Args:
            job_id: Unique identifier for the scraping job
            failure_event: Failure event details
        """
        pass
    
    @abstractmethod
    async def execute_abort_actions(
        self,
        job_id: str,
        abort_reason: str
    ) -> bool:
        """
        Execute abort actions for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            abort_reason: Reason for abort
            
        Returns:
            True if abort actions executed successfully
        """
        pass
    
    @abstractmethod
    async def create_abort_policy(
        self,
        policy_config: Dict[str, Any]
    ) -> str:
        """
        Create a new abort policy.
        
        Args:
            policy_config: Policy configuration parameters
            
        Returns:
            ID of created policy
        """
        pass
    
    @abstractmethod
    async def get_failure_analysis(
        self,
        job_id: str,
        time_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get failure analysis for a job.
        
        Args:
            job_id: Unique identifier for the scraping job
            time_window: Time window in seconds (optional)
            
        Returns:
            Failure analysis results
        """
        pass


class IFailureHandler(IResilienceManager):
    """Interface for centralized failure handling."""
    
    @abstractmethod
    async def handle_failure(
        self,
        failure_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a failure event with appropriate recovery actions.
        
        Args:
            failure_event: Failure event details
            context: Additional context information
            
        Returns:
            Handling result with recovery actions taken
        """
        pass
    
    @abstractmethod
    async def register_failure_handler(
        self,
        failure_type: str,
        handler: Callable
    ) -> None:
        """
        Register a handler for specific failure types.
        
        Args:
            failure_type: Type of failure to handle
            handler: Handler function
        """
        pass
    
    @abstractmethod
    async def get_failure_statistics(
        self,
        job_id: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get failure statistics.
        
        Args:
            job_id: Optional job identifier filter
            time_range: Optional time range filter
            
        Returns:
            Failure statistics
        """
        pass


class IEventSubscriber(ABC):
    """Interface for event subscription handling."""
    
    @abstractmethod
    async def handle_event(self, event: ResilienceEvent) -> None:
        """
        Handle a resilience event.
        
        Args:
            event: The resilience event to handle
        """
        pass


class IBrowserLifecycleIntegration(ABC):
    """Interface for browser lifecycle integration."""
    
    @abstractmethod
    async def on_browser_restart_required(
        self,
        reason: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Handle browser restart request from resilience system.
        
        Args:
            reason: Reason for restart request
            context: Additional context information
            
        Returns:
            True if restart initiated successfully
        """
        pass
    
    @abstractmethod
    async def get_browser_state(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get current browser state for checkpointing.
        
        Args:
            session_id: Browser session ID
            
        Returns:
            Browser state data
        """
        pass
    
    @abstractmethod
    async def restore_browser_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Restore browser state from checkpoint.
        
        Args:
            session_id: Browser session ID
            state: Browser state data
            
        Returns:
            True if state restored successfully
        """
        pass


class ILoggingIntegration(ABC):
    """Interface for logging system integration."""
    
    @abstractmethod
    async def log_resilience_event(
        self,
        event: ResilienceEvent
    ) -> None:
        """
        Log a resilience event with correlation ID.
        
        Args:
            event: Resilience event to log
        """
        pass
    
    @abstractmethod
    async def log_failure_event(
        self,
        failure_event: Dict[str, Any]
    ) -> None:
        """
        Log a failure event with detailed context.
        
        Args:
            failure_event: Failure event details
        """
        pass
    
    @abstractmethod
    async def log_recovery_event(
        self,
        recovery_event: Dict[str, Any]
    ) -> None:
        """
        Log a recovery event.
        
        Args:
            recovery_event: Recovery event details
        """
        pass
