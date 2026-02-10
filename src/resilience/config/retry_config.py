"""
Retry Policy Configuration Management

Manages retry policy configurations including default policies,
custom policy creation, validation, and persistence.
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from ..models.retry_policy import (
    RetryPolicy, BackoffType, JitterType, RetryCondition,
    DEFAULT_EXPONENTIAL_BACKOFF, AGGRESSIVE_RETRY, CONSERVATIVE_RETRY,
    LINEAR_RETRY, FIXED_RETRY
)
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..exceptions import RetryConfigurationError


class RetryPolicyManager:
    """Manages retry policy configurations."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize retry policy manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or "./retry_policies.json"
        self.logger = get_logger("retry_policy_manager")
        self.policies: Dict[str, RetryPolicy] = {}
        self._load_default_policies()
        self._load_policies_from_file()
    
    def _load_default_policies(self) -> None:
        """Load default retry policies."""
        default_policies = [
            DEFAULT_EXPONENTIAL_BACKOFF,
            AGGRESSIVE_RETRY,
            CONSERVATIVE_RETRY,
            LINEAR_RETRY,
            FIXED_RETRY
        ]
        
        for policy in default_policies:
            self.policies[policy.id] = policy
        
        self.logger.info(
            f"Loaded {len(default_policies)} default retry policies",
            event_type="default_policies_loaded",
            correlation_id=get_correlation_id(),
            context={
                "policy_count": len(default_policies),
                "policy_names": [p.name for p in default_policies]
            },
            component="retry_policy_manager"
        )
    
    def _load_policies_from_file(self) -> None:
        """Load retry policies from configuration file."""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            self.logger.info(
                f"Retry policy config file not found: {self.config_path}",
                event_type="config_file_not_found",
                correlation_id=get_correlation_id(),
                context={"config_path": self.config_path},
                component="retry_policy_manager"
            )
            return
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            policies_data = config_data.get("policies", [])
            loaded_count = 0
            
            for policy_data in policies_data:
                try:
                    policy = RetryPolicy.from_dict(policy_data)
                    self.policies[policy.id] = policy
                    loaded_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to load retry policy: {str(e)}",
                        event_type="policy_load_error",
                        correlation_id=get_correlation_id(),
                        context={
                            "policy_data": policy_data,
                            "error": str(e)
                        },
                        component="retry_policy_manager"
                    )
            
            self.logger.info(
                f"Loaded {loaded_count} retry policies from file",
                event_type="policies_loaded_from_file",
                correlation_id=get_correlation_id(),
                context={
                    "config_path": self.config_path,
                    "loaded_count": loaded_count,
                    "total_policies": len(self.policies)
                },
                component="retry_policy_manager"
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to load retry policy config file: {str(e)}",
                event_type="config_file_load_error",
                correlation_id=get_correlation_id(),
                context={
                    "config_path": self.config_path,
                    "error": str(e)
                },
                component="retry_policy_manager"
            )
    
    def save_policies_to_file(self) -> None:
        """Save all retry policies to configuration file."""
        config_path = Path(self.config_path)
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            config_data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "policies": [policy.to_dict() for policy in self.policies.values()]
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.logger.info(
                f"Saved {len(self.policies)} retry policies to file",
                event_type="policies_saved_to_file",
                correlation_id=get_correlation_id(),
                context={
                    "config_path": self.config_path,
                    "policy_count": len(self.policies)
                },
                component="retry_policy_manager"
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to save retry policy config file: {str(e)}",
                event_type="config_file_save_error",
                correlation_id=get_correlation_id(),
                context={
                    "config_path": self.config_path,
                    "error": str(e)
                },
                component="retry_policy_manager"
            )
    
    def create_policy(
        self,
        name: str,
        description: str,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        backoff_type: BackoffType = BackoffType.EXPONENTIAL,
        jitter_type: JitterType = JitterType.FULL,
        jitter_factor: float = 0.1,
        retry_conditions: Optional[List[RetryCondition]] = None,
        retryable_error_codes: Optional[List[int]] = None,
        retryable_error_patterns: Optional[List[str]] = None,
        enable_circuit_breaker: bool = False,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new retry policy.
        
        Args:
            name: Policy name
            description: Policy description
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier
            backoff_type: Type of backoff strategy
            jitter_type: Type of jitter strategy
            jitter_factor: Jitter factor (0.0-1.0)
            retry_conditions: Conditions for retrying
            retryable_error_codes: HTTP status codes that are retryable
            retryable_error_patterns: Error patterns that are retryable
            enable_circuit_breaker: Enable circuit breaker
            circuit_breaker_threshold: Circuit breaker failure threshold
            circuit_breaker_timeout: Circuit breaker timeout in seconds
            metadata: Additional metadata
            
        Returns:
            ID of created policy
        """
        policy = RetryPolicy(
            name=name,
            description=description,
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            multiplier=multiplier,
            backoff_type=backoff_type,
            jitter_type=jitter_type,
            jitter_factor=jitter_factor,
            retry_conditions=retry_conditions or [RetryCondition.TRANSIENT_FAILURE],
            retryable_error_codes=retryable_error_codes or [],
            retryable_error_patterns=retryable_error_patterns or [],
            enable_circuit_breaker=enable_circuit_breaker,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
            metadata=metadata or {}
        )
        
        self.policies[policy.id] = policy
        
        self.logger.info(
            f"Created retry policy: {policy.name}",
            event_type="policy_created",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy.id,
                "policy_name": policy.name,
                "max_attempts": policy.max_attempts,
                "backoff_type": policy.backoff_type.value,
                "jitter_type": policy.jitter_type.value
            },
            component="retry_policy_manager"
        )
        
        return policy.id
    
    def get_policy(self, policy_id: str) -> Optional[RetryPolicy]:
        """
        Get a retry policy by ID.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Retry policy or None if not found
        """
        return self.policies.get(policy_id)
    
    def get_policy_by_name(self, name: str) -> Optional[RetryPolicy]:
        """
        Get a retry policy by name.
        
        Args:
            name: Policy name
            
        Returns:
            Retry policy or None if not found
        """
        for policy in self.policies.values():
            if policy.name == name:
                return policy
        return None
    
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
                "base_delay": policy.base_delay,
                "max_delay": policy.max_delay,
                "multiplier": policy.multiplier,
                "backoff_type": policy.backoff_type.value,
                "jitter_type": policy.jitter_type.value,
                "jitter_factor": policy.jitter_factor,
                "enabled": policy.enabled,
                "created_at": policy.created_at.isoformat(),
                "updated_at": policy.updated_at.isoformat(),
                "is_default": policy.id in [
                    DEFAULT_EXPONENTIAL_BACKOFF.id,
                    AGGRESSIVE_RETRY.id,
                    CONSERVATIVE_RETRY.id,
                    LINEAR_RETRY.id,
                    FIXED_RETRY.id
                ]
            }
            for policy in self.policies.values()
        ]
    
    def update_policy(
        self,
        policy_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an existing retry policy.
        
        Args:
            policy_id: Policy identifier
            updates: Updates to apply
            
        Returns:
            True if updated successfully, False if not found
        """
        policy = self.policies.get(policy_id)
        if not policy:
            return False
        
        # Don't allow updating default policies
        if policy_id in [
            DEFAULT_EXPONENTIAL_BACKOFF.id,
            AGGRESSIVE_RETRY.id,
            CONSERVATIVE_RETRY.id,
            LINEAR_RETRY.id,
            FIXED_RETRY.id
        ]:
            raise RetryConfigurationError("Cannot update default retry policies")
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        
        policy.updated_at = datetime.utcnow()
        
        self.logger.info(
            f"Updated retry policy: {policy.name}",
            event_type="policy_updated",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy_id,
                "policy_name": policy.name,
                "updates": updates
            },
            component="retry_policy_manager"
        )
        
        return True
    
    def delete_policy(self, policy_id: str) -> bool:
        """
        Delete a retry policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        if policy_id not in self.policies:
            return False
        
        # Don't allow deleting default policies
        if policy_id in [
            DEFAULT_EXPONENTIAL_BACKOFF.id,
            AGGRESSIVE_RETRY.id,
            CONSERVATIVE_RETRY.id,
            LINEAR_RETRY.id,
            FIXED_RETRY.id
        ]:
            raise RetryConfigurationError("Cannot delete default retry policies")
        
        policy = self.policies[policy_id]
        del self.policies[policy_id]
        
        self.logger.info(
            f"Deleted retry policy: {policy.name}",
            event_type="policy_deleted",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy_id,
                "policy_name": policy.name
            },
            component="retry_policy_manager"
        )
        
        return True
    
    def enable_policy(self, policy_id: str) -> bool:
        """
        Enable a retry policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            True if enabled successfully, False if not found
        """
        policy = self.policies.get(policy_id)
        if not policy:
            return False
        
        policy.enabled = True
        policy.updated_at = datetime.utcnow()
        
        self.logger.info(
            f"Enabled retry policy: {policy.name}",
            event_type="policy_enabled",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy_id,
                "policy_name": policy.name
            },
            component="retry_policy_manager"
        )
        
        return True
    
    def disable_policy(self, policy_id: str) -> bool:
        """
        Disable a retry policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            True if disabled successfully, False if not found
        """
        policy = self.policies.get(policy_id)
        if not policy:
            return False
        
        policy.enabled = False
        policy.updated_at = datetime.utcnow()
        
        self.logger.info(
            f"Disabled retry policy: {policy.name}",
            event_type="policy_disabled",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy_id,
                "policy_name": policy.name
            },
            component="retry_policy_manager"
        )
        
        return True
    
    def validate_policy(self, policy_config: Dict[str, Any]) -> List[str]:
        """
        Validate a retry policy configuration.
        
        Args:
            policy_config: Policy configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = ["name", "description", "max_attempts"]
        for field in required_fields:
            if field not in policy_config:
                errors.append(f"Missing required field: {field}")
        
        # Validate max_attempts
        if "max_attempts" in policy_config:
            max_attempts = policy_config["max_attempts"]
            if not isinstance(max_attempts, int) or max_attempts < 1:
                errors.append("max_attempts must be a positive integer")
        
        # Validate delays
        for delay_field in ["base_delay", "max_delay"]:
            if delay_field in policy_config:
                delay = policy_config[delay_field]
                if not isinstance(delay, (int, float)) or delay < 0:
                    errors.append(f"{delay_field} must be a non-negative number")
        
        # Validate multiplier
        if "multiplier" in policy_config:
            multiplier = policy_config["multiplier"]
            if not isinstance(multiplier, (int, float)) or multiplier <= 0:
                errors.append("multiplier must be a positive number")
        
        # Validate jitter_factor
        if "jitter_factor" in policy_config:
            jitter_factor = policy_config["jitter_factor"]
            if not isinstance(jitter_factor, (int, float)) or not (0 <= jitter_factor <= 1):
                errors.append("jitter_factor must be between 0 and 1")
        
        # Validate backoff_type
        if "backoff_type" in policy_config:
            backoff_type = policy_config["backoff_type"]
            try:
                BackoffType(backoff_type)
            except ValueError:
                errors.append(f"Invalid backoff_type: {backoff_type}")
        
        # Validate jitter_type
        if "jitter_type" in policy_config:
            jitter_type = policy_config["jitter_type"]
            try:
                JitterType(jitter_type)
            except ValueError:
                errors.append(f"Invalid jitter_type: {jitter_type}")
        
        # Validate retry_conditions
        if "retry_conditions" in policy_config:
            retry_conditions = policy_config["retry_conditions"]
            if not isinstance(retry_conditions, list):
                errors.append("retry_conditions must be a list")
            else:
                for condition in retry_conditions:
                    try:
                        RetryCondition(condition)
                    except ValueError:
                        errors.append(f"Invalid retry_condition: {condition}")
        
        return errors
    
    def clone_policy(
        self,
        policy_id: str,
        new_name: str,
        new_description: Optional[str] = None
    ) -> str:
        """
        Clone an existing retry policy.
        
        Args:
            policy_id: Policy identifier to clone
            new_name: Name for the new policy
            new_description: Description for the new policy
            
        Returns:
            ID of cloned policy
        """
        original_policy = self.policies.get(policy_id)
        if not original_policy:
            raise RetryConfigurationError(f"Policy not found: {policy_id}")
        
        # Create clone
        cloned_policy = original_policy.clone(
            name=new_name,
            description=new_description or f"Clone of {original_policy.name}"
        )
        
        self.policies[cloned_policy.id] = cloned_policy
        
        self.logger.info(
            f"Cloned retry policy: {original_policy.name} -> {cloned_policy.name}",
            event_type="policy_cloned",
            correlation_id=get_correlation_id(),
            context={
                "original_policy_id": policy_id,
                "original_policy_name": original_policy.name,
                "cloned_policy_id": cloned_policy.id,
                "cloned_policy_name": cloned_policy.name
            },
            component="retry_policy_manager"
        )
        
        return cloned_policy.id
    
    def get_policy_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about retry policies.
        
        Returns:
            Policy statistics
        """
        total_policies = len(self.policies)
        enabled_policies = sum(1 for p in self.policies.values() if p.enabled)
        disabled_policies = total_policies - enabled_policies
        
        # Count by backoff type
        backoff_counts = {}
        for policy in self.policies.values():
            backoff_type = policy.backoff_type.value
            backoff_counts[backoff_type] = backoff_counts.get(backoff_type, 0) + 1
        
        # Count by jitter type
        jitter_counts = {}
        for policy in self.policies.values():
            jitter_type = policy.jitter_type.value
            jitter_counts[jitter_type] = jitter_counts.get(jitter_type, 0) + 1
        
        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "disabled_policies": disabled_policies,
            "backoff_type_distribution": backoff_counts,
            "jitter_type_distribution": jitter_counts,
            "default_policies": 5,
            "custom_policies": total_policies - 5
        }


# Global retry policy manager instance
_retry_policy_manager = RetryPolicyManager()


def get_retry_policy_manager() -> RetryPolicyManager:
    """Get the global retry policy manager instance."""
    return _retry_policy_manager


def get_retry_policy(policy_id: str) -> Optional[RetryPolicy]:
    """Get a retry policy using the global manager."""
    return _retry_policy_manager.get_policy(policy_id)


def create_retry_policy(**kwargs) -> str:
    """Create a retry policy using the global manager."""
    return _retry_policy_manager.create_policy(**kwargs)


def list_retry_policies() -> List[Dict[str, Any]]:
    """List all retry policies using the global manager."""
    return _retry_policy_manager.list_policies()
