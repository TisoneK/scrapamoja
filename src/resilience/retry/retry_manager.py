"""
Retry Manager

Manages retry operations with configurable policies, backoff strategies,
failure classification, and circuit breaker functionality.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field

from ..interfaces import IRetryManager, IResilienceManager
from ..models.retry_policy import RetryPolicy, BackoffType, JitterType
from ..failure_classifier import classify_failure, is_transient_failure
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id, with_correlation_id
from ..events import publish_retry_event, publish_failure_event
from ..exceptions import MaxRetriesExceededError, PermanentFailureError, RetryConfigurationError


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    delay: float = 0.0
    error: Optional[Exception] = None
    success: bool = False
    duration: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrySession:
    """Information about a retry session."""
    session_id: str
    policy_id: str
    operation: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_result: Optional[Any] = None
    final_error: Optional[Exception] = None
    success: bool = False
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_attempts(self) -> int:
        """Get total number of attempts."""
        return len(self.attempts)
    
    @property
    def total_duration(self) -> float:
        """Get total duration of the retry session."""
        end_time = self.end_time or datetime.utcnow()
        return (end_time - self.start_time).total_seconds()
    
    @property
    def retry_count(self) -> int:
        """Get number of retry attempts (excluding first attempt)."""
        return max(0, self.total_attempts - 1)


class RetryManager(IRetryManager, IResilienceManager):
    """Manages retry operations with configurable policies and strategies."""
    
    def __init__(self):
        """Initialize retry manager."""
        self.logger = get_logger("retry_manager")
        self.policies: Dict[str, RetryPolicy] = {}
        self.active_sessions: Dict[str, RetrySession] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the retry manager."""
        if self._initialized:
            return
        
        # Register default policies
        from ..models.retry_policy import (
            DEFAULT_EXPONENTIAL_BACKOFF,
            AGGRESSIVE_RETRY,
            CONSERVATIVE_RETRY,
            LINEAR_RETRY,
            FIXED_RETRY
        )
        
        self.policies[DEFAULT_EXPONENTIAL_BACKOFF.id] = DEFAULT_EXPONENTIAL_BACKOFF
        self.policies[AGGRESSIVE_RETRY.id] = AGGRESSIVE_RETRY
        self.policies[CONSERVATIVE_RETRY.id] = CONSERVATIVE_RETRY
        self.policies[LINEAR_RETRY.id] = LINEAR_RETRY
        self.policies[FIXED_RETRY.id] = FIXED_RETRY
        
        self._initialized = True
        
        self.logger.info(
            "Retry manager initialized",
            event_type="retry_manager_initialized",
            correlation_id=get_correlation_id(),
            context={
                "policies_count": len(self.policies),
                "default_policies": [
                    DEFAULT_EXPONENTIAL_BACKOFF.name,
                    AGGRESSIVE_RETRY.name,
                    CONSERVATIVE_RETRY.name,
                    LINEAR_RETRY.name,
                    FIXED_RETRY.name
                ]
            },
            component="retry_manager"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the retry manager gracefully."""
        if not self._initialized:
            return
        
        # Cancel all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.cancel_session(session_id)
        
        self._initialized = False
        
        self.logger.info(
            "Retry manager shutdown",
            event_type="retry_manager_shutdown",
            correlation_id=get_correlation_id(),
            component="retry_manager"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "policies_count": len(self.policies),
            "active_sessions": len(self.active_sessions),
            "circuit_breakers": len(self.circuit_breakers)
        }
    
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
            RetryConfigurationError: If retry policy is not found
        """
        if not self._initialized:
            await self.initialize()
        
        # Get retry policy
        policy = self.policies.get(retry_policy_id)
        if not policy:
            raise RetryConfigurationError(f"Retry policy not found: {retry_policy_id}")
        
        if not policy.enabled:
            raise RetryConfigurationError(f"Retry policy is disabled: {retry_policy_id}")
        
        # Create retry session
        session_id = f"{retry_policy_id}_{int(time.time() * 1000)}"
        session = RetrySession(
            session_id=session_id,
            policy_id=retry_policy_id,
            operation=operation.__name__ if hasattr(operation, '__name__') else str(operation)
        )
        
        self.active_sessions[session_id] = session
        
        try:
            return await self._execute_retry_session(session, policy, operation, *args, **kwargs)
        finally:
            # Clean up session
            session.end_time = datetime.utcnow()
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
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
        failure_type, _, _ = classify_failure(error)
        return failure_type.value
    
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
        policy = self.policies.get(retry_policy_id)
        if not policy:
            raise RetryConfigurationError(f"Retry policy not found: {retry_policy_id}")
        
        return policy.calculate_delay(attempt)
    
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
        policy = RetryPolicy.from_dict(policy_config)
        self.policies[policy.id] = policy
        
        self.logger.info(
            f"Retry policy created: {policy.name}",
            event_type="retry_policy_created",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy.id,
                "policy_name": policy.name,
                "max_attempts": policy.max_attempts,
                "backoff_type": policy.backoff_type.value
            },
            component="retry_manager"
        )
        
        return policy.id
    
    async def _execute_retry_session(
        self,
        session: RetrySession,
        policy: RetryPolicy,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a retry session with the given policy.
        
        Args:
            session: Retry session information
            policy: Retry policy to use
            operation: Operation to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Result of the operation
        """
        attempt = 0
        last_error = None
        
        while attempt < policy.max_attempts:
            attempt += 1
            attempt_start = time.time()
            
            # Create retry attempt
            retry_attempt = RetryAttempt(
                attempt_number=attempt,
                context=session.context.copy()
            )
            
            try:
                # Check if we should retry (for attempts > 1)
                if attempt > 1:
                    should_retry = policy.should_retry(attempt, last_error, session.context)
                    if not should_retry:
                        raise MaxRetriesExceededError(
                            f"Retry policy does not allow retry for attempt {attempt}",
                            context={
                                "attempt": attempt,
                                "max_attempts": policy.max_attempts,
                                "policy_id": policy.id
                            }
                        )
                    
                    # Calculate delay
                    delay = policy.calculate_delay(attempt)
                    retry_attempt.delay = delay
                    
                    # Publish retry event
                    await publish_retry_event(
                        operation=session.operation,
                        attempt=attempt,
                        max_attempts=policy.max_attempts,
                        delay=delay,
                        job_id=session.context.get("job_id"),
                        context={
                            "session_id": session.session_id,
                            "policy_id": policy.id,
                            "last_error": str(last_error) if last_error else None
                        },
                        component="retry_manager"
                    )
                    
                    # Wait before retry
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                # Execute the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Success!
                retry_attempt.success = True
                retry_attempt.duration = time.time() - attempt_start
                session.attempts.append(retry_attempt)
                
                session.final_result = result
                session.success = True
                
                self.logger.info(
                    f"Operation succeeded on attempt {attempt}: {session.operation}",
                    event_type="operation_succeeded",
                    correlation_id=get_correlation_id(),
                    context={
                        "session_id": session.session_id,
                        "operation": session.operation,
                        "attempt": attempt,
                        "duration": retry_attempt.duration,
                        "policy_id": policy.id
                    },
                    component="retry_manager"
                )
                
                return result
                
            except Exception as error:
                # Handle the error
                last_error = error
                retry_attempt.error = error
                retry_attempt.duration = time.time() - attempt_start
                session.attempts.append(retry_attempt)
                
                # Classify the failure
                failure_type = await self.classify_failure(error)
                
                # Check if it's a permanent failure
                if failure_type == "permanent" or not policy.is_retryable_error(error):
                    session.final_error = error
                    session.success = False
                    
                    self.logger.error(
                        f"Permanent failure detected: {session.operation} - {str(error)}",
                        event_type="permanent_failure",
                        correlation_id=get_correlation_id(),
                        context={
                            "session_id": session.session_id,
                            "operation": session.operation,
                            "attempt": attempt,
                            "failure_type": failure_type,
                            "error": str(error)
                        },
                        component="retry_manager"
                    )
                    
                    raise PermanentFailureError(
                        f"Permanent failure: {str(error)}",
                        context={
                            "operation": session.operation,
                            "attempt": attempt,
                            "failure_type": failure_type
                        }
                    )
                
                # Log the retry attempt
                self.logger.warning(
                    f"Operation failed on attempt {attempt}: {session.operation} - {str(error)}",
                    event_type="operation_failed",
                    correlation_id=get_correlation_id(),
                    context={
                        "session_id": session.session_id,
                        "operation": session.operation,
                        "attempt": attempt,
                        "failure_type": failure_type,
                        "error": str(error),
                        "will_retry": attempt < policy.max_attempts
                    },
                    component="retry_manager"
                )
                
                # Update circuit breaker if enabled
                if policy.enable_circuit_breaker:
                    await self._update_circuit_breaker(policy.id, error)
        
        # All attempts failed
        session.final_error = last_error
        session.success = False
        
        raise MaxRetriesExceededError(
            f"Maximum retry attempts exceeded: {attempt}/{policy.max_attempts}",
            context={
                "operation": session.operation,
                "attempts": attempt,
                "max_attempts": policy.max_attempts,
                "policy_id": policy.id,
                "last_error": str(last_error) if last_error else None
            }
        )
    
    async def _update_circuit_breaker(
        self,
        policy_id: str,
        error: Exception
    ) -> None:
        """
        Update circuit breaker state for a policy.
        
        Args:
            policy_id: Policy identifier
            error: The error that occurred
        """
        if policy_id not in self.circuit_breakers:
            policy = self.policies.get(policy_id)
            if not policy:
                return
            
            self.circuit_breakers[policy_id] = {
                "failure_count": 0,
                "last_failure_time": None,
                "state": "closed",  # closed, open, half_open
                "threshold": policy.circuit_breaker_threshold,
                "timeout": policy.circuit_breaker_timeout
            }
        
        circuit_breaker = self.circuit_breakers[policy_id]
        circuit_breaker["failure_count"] += 1
        circuit_breaker["last_failure_time"] = datetime.utcnow()
        
        # Check if circuit should open
        if circuit_breaker["failure_count"] >= circuit_breaker["threshold"]:
            circuit_breaker["state"] = "open"
            
            self.logger.warning(
                f"Circuit breaker opened for policy {policy_id}",
                event_type="circuit_breaker_opened",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "failure_count": circuit_breaker["failure_count"],
                    "threshold": circuit_breaker["threshold"]
                },
                component="retry_manager"
            )
    
    async def cancel_session(self, session_id: str) -> bool:
        """
        Cancel a retry session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was cancelled, False if not found
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.end_time = datetime.utcnow()
            session.success = False
            
            del self.active_sessions[session_id]
            
            self.logger.info(
                f"Retry session cancelled: {session_id}",
                event_type="session_cancelled",
                correlation_id=get_correlation_id(),
                context={
                    "session_id": session_id,
                    "attempts": session.total_attempts,
                    "duration": session.total_duration
                },
                component="retry_manager"
            )
            
            return True
        
        return False
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a retry session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status information or None if not found
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "policy_id": session.policy_id,
            "operation": session.operation,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "total_attempts": session.total_attempts,
            "retry_count": session.retry_count,
            "success": session.success,
            "duration": session.total_duration,
            "attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "timestamp": attempt.timestamp.isoformat(),
                    "delay": attempt.delay,
                    "success": attempt.success,
                    "duration": attempt.duration,
                    "error": str(attempt.error) if attempt.error else None
                }
                for attempt in session.attempts
            ]
        }
    
    def get_policy(self, policy_id: str) -> Optional[RetryPolicy]:
        """
        Get a retry policy by ID.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Retry policy or None if not found
        """
        return self.policies.get(policy_id)
    
    def list_policies(self) -> List[Dict[str, Any]]:
        """
        List all available retry policies.
        
        Returns:
            List of policy information
        """
        return [
            {
                "id": policy.id,
                "name": policy.name,
                "description": policy.description,
                "max_attempts": policy.max_attempts,
                "backoff_type": policy.backoff_type.value,
                "jitter_type": policy.jitter_type.value,
                "enabled": policy.enabled,
                "created_at": policy.created_at.isoformat(),
                "updated_at": policy.updated_at.isoformat()
            }
            for policy in self.policies.values()
        ]
    
    def get_circuit_breaker_status(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get circuit breaker status for a policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Circuit breaker status or None if not found
        """
        return self.circuit_breakers.get(policy_id)


# Global retry manager instance
_retry_manager = RetryManager()


def get_retry_manager() -> RetryManager:
    """Get the global retry manager instance."""
    return _retry_manager


async def execute_with_retry(
    operation: Callable,
    retry_policy_id: str,
    *args,
    **kwargs
) -> Any:
    """Execute an operation with retry logic using the global retry manager."""
    return await _retry_manager.execute_with_retry(operation, retry_policy_id, *args, **kwargs)


async def create_retry_policy(policy_config: Dict[str, Any]) -> str:
    """Create a retry policy using the global retry manager."""
    return await _retry_manager.create_retry_policy(policy_config)
