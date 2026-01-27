"""
State Persistence Error Handling

This module provides graceful error handling for state persistence operations,
following the Production Resilience constitution principle.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable, Awaitable
from enum import Enum
import structlog

from .exceptions import StateCorruptionError, BrowserError
from .state_logger import StateOperation, get_state_logger
from .resilience import resilience_manager, RetryConfig, RetryStrategy
from .corruption_detector import StateCorruptionDetector, CorruptionReport
from .encryption import StateEncryption


class StateErrorType(Enum):
    """Types of state persistence errors."""
    FILE_NOT_FOUND = "file_not_found"
    FILE_CORRUPTION = "file_corruption"
    ENCRYPTION_FAILURE = "encryption_failure"
    DECRYPTION_FAILURE = "decryption_failure"
    VALIDATION_FAILURE = "validation_failure"
    PERMISSION_DENIED = "permission_denied"
    DISK_FULL = "disk_full"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


class StateRecoveryAction(Enum):
    """Recovery actions for state errors."""
    RETRY = "retry"
    USE_BACKUP = "use_backup"
    REPAIR_STATE = "repair_state"
    CREATE_NEW = "create_new"
    FALLBACK_DEFAULT = "fallback_default"
    ABORT = "abort"


@dataclass
class StateErrorContext:
    """Context for state persistence errors."""
    error_type: StateErrorType
    original_error: Exception
    session_id: Optional[str] = None
    state_id: Optional[str] = None
    operation: Optional[StateOperation] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    retry_count: int = 0
    recovery_attempts: List[StateRecoveryAction] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.recovery_attempts is None:
            self.recovery_attempts = []


class StateErrorHandler:
    """Handles errors in state persistence operations with graceful recovery."""
    
    def __init__(
        self,
        storage_dir: str,
        corruption_detector: Optional[StateCorruptionDetector] = None,
        encryption: Optional[StateEncryption] = None
    ):
        self.storage_dir = storage_dir
        self.corruption_detector = corruption_detector or StateCorruptionDetector(storage_dir, encryption)
        self.encryption = encryption
        self.logger = structlog.get_logger("browser.state_error_handler")
        self.state_logger = get_state_logger()
        
        # Configure retry strategies for different error types
        self.retry_configs = {
            StateErrorType.TIMEOUT: RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=10.0
            ),
            StateErrorType.NETWORK_ERROR: RetryConfig(
                max_attempts=5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=2.0,
                max_delay=30.0
            ),
            StateErrorType.DISK_FULL: RetryConfig(
                max_attempts=2,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                base_delay=5.0
            )
        }
        
    async def handle_save_error(
        self,
        error: Exception,
        session_id: str,
        state_id: str,
        state_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Handle save operation errors with recovery."""
        error_context = self._create_error_context(
            error, session_id, state_id, StateOperation.SAVE, correlation_id
        )
        
        self.logger.warning(
            "State save error occurred",
            **error_context.__dict__
        )
        
        # Attempt recovery based on error type
        recovery_actions = self._get_recovery_actions(error_context.error_type)
        
        for action in recovery_actions:
            try:
                error_context.recovery_attempts.append(action)
                success = await self._attempt_recovery(action, error_context, state_data)
                
                if success:
                    self.logger.info(
                        "State save error recovered",
                        recovery_action=action.value,
                        session_id=session_id,
                        state_id=state_id
                    )
                    return True
                    
            except Exception as recovery_error:
                self.logger.error(
                    "Recovery attempt failed",
                    recovery_action=action.value,
                    error=str(recovery_error),
                    error_type=type(recovery_error).__name__
                )
                continue
                
        # All recovery attempts failed
        self.logger.error(
            "State save error recovery failed",
            session_id=session_id,
            state_id=state_id,
            attempted_actions=[action.value for action in error_context.recovery_attempts]
        )
        
        return False
        
    async def handle_load_error(
        self,
        error: Exception,
        state_id: str,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Handle load operation errors with recovery."""
        error_context = self._create_error_context(
            error, session_id, state_id, StateOperation.LOAD, correlation_id
        )
        
        self.logger.warning(
            "State load error occurred",
            **error_context.__dict__
        )
        
        # Attempt recovery based on error type
        recovery_actions = self._get_recovery_actions(error_context.error_type)
        
        for action in recovery_actions:
            try:
                error_context.recovery_attempts.append(action)
                result = await self._attempt_load_recovery(action, error_context)
                
                if result is not None:
                    self.logger.info(
                        "State load error recovered",
                        recovery_action=action.value,
                        state_id=state_id
                    )
                    return result
                    
            except Exception as recovery_error:
                self.logger.error(
                    "Load recovery attempt failed",
                    recovery_action=action.value,
                    error=str(recovery_error),
                    error_type=type(recovery_error).__name__
                )
                continue
                
        # All recovery attempts failed
        self.logger.error(
            "State load error recovery failed",
            state_id=state_id,
            attempted_actions=[action.value for action in error_context.recovery_attempts]
        )
        
        return None
        
    async def handle_delete_error(
        self,
        error: Exception,
        state_id: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Handle delete operation errors with recovery."""
        error_context = self._create_error_context(
            error, None, state_id, StateOperation.DELETE, correlation_id
        )
        
        self.logger.warning(
            "State delete error occurred",
            **error_context.__dict__
        )
        
        # For delete operations, we're more lenient - if we can't delete, log and continue
        recovery_actions = self._get_recovery_actions(error_context.error_type)
        
        for action in recovery_actions:
            try:
                error_context.recovery_attempts.append(action)
                success = await self._attempt_delete_recovery(action, error_context)
                
                if success:
                    self.logger.info(
                        "State delete error recovered",
                        recovery_action=action.value,
                        state_id=state_id
                    )
                    return True
                    
            except Exception as recovery_error:
                self.logger.error(
                    "Delete recovery attempt failed",
                    recovery_action=action.value,
                    error=str(recovery_error),
                    error_type=type(recovery_error).__name__
                )
                continue
                
        # For delete operations, we consider it "successful" even if recovery fails
        # to avoid blocking the system
        self.logger.warning(
            "State delete could not be recovered, continuing",
            state_id=state_id
        )
        
        return True
        
    async def execute_with_error_handling(
        self,
        operation: Callable[[], Awaitable[T]],
        error_handler: Callable[[Exception, StateErrorContext], Awaitable[T]],
        operation_type: StateOperation,
        session_id: Optional[str] = None,
        state_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> T:
        """Execute an operation with comprehensive error handling."""
        try:
            return await operation()
            
        except Exception as error:
            error_context = self._create_error_context(
                error, session_id, state_id, operation_type, correlation_id, **kwargs
            )
            
            try:
                return await error_handler(error, error_context)
                
            except Exception as handler_error:
                self.logger.error(
                    "Error handler failed",
                    original_error=str(error),
                    handler_error=str(handler_error),
                    operation_type=operation_type.value
                )
                raise handler_error
                
    def _create_error_context(
        self,
        error: Exception,
        session_id: Optional[str],
        state_id: Optional[str],
        operation: Optional[StateOperation],
        correlation_id: Optional[str] = None,
        **metadata
    ) -> StateErrorContext:
        """Create error context from exception."""
        error_type = self._classify_error(error)
        
        return StateErrorContext(
            error_type=error_type,
            original_error=error,
            session_id=session_id,
            state_id=state_id,
            operation=operation,
            correlation_id=correlation_id,
            metadata=metadata
        )
        
    def _classify_error(self, error: Exception) -> StateErrorType:
        """Classify error type for appropriate recovery strategy."""
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # File-related errors
        if "file not found" in error_message or "no such file" in error_message:
            return StateErrorType.FILE_NOT_FOUND
        elif "permission denied" in error_message or "access denied" in error_message:
            return StateErrorType.PERMISSION_DENIED
        elif "disk full" in error_message or "no space left" in error_message:
            return StateErrorType.DISK_FULL
        elif "corrupt" in error_message or "invalid" in error_message:
            return StateErrorType.FILE_CORRUPTION
            
        # Encryption-related errors
        elif "encrypt" in error_type_name or "decrypt" in error_type_name:
            if "encrypt" in error_type_name:
                return StateErrorType.ENCRYPTION_FAILURE
            else:
                return StateErrorType.DECRYPTION_FAILURE
                
        # Network and timeout errors
        elif "timeout" in error_message or "timed out" in error_message:
            return StateErrorType.TIMEOUT
        elif "network" in error_message or "connection" in error_message:
            return StateErrorType.NETWORK_ERROR
            
        # Validation errors
        elif "validation" in error_message or "invalid" in error_type_name:
            return StateErrorType.VALIDATION_FAILURE
            
        return StateErrorType.UNKNOWN_ERROR
        
    def _get_recovery_actions(self, error_type: StateErrorType) -> List[StateRecoveryAction]:
        """Get recovery actions for specific error types."""
        recovery_map = {
            StateErrorType.FILE_NOT_FOUND: [StateRecoveryAction.CREATE_NEW],
            StateErrorType.FILE_CORRUPTION: [StateRecoveryAction.REPAIR_STATE, StateRecoveryAction.USE_BACKUP, StateRecoveryAction.CREATE_NEW],
            StateErrorType.ENCRYPTION_FAILURE: [StateRecoveryAction.RETRY, StateRecoveryAction.FALLBACK_DEFAULT],
            StateErrorType.DECRYPTION_FAILURE: [StateRecoveryAction.REPAIR_STATE, StateRecoveryAction.USE_BACKUP],
            StateErrorType.VALIDATION_FAILURE: [StateRecoveryAction.REPAIR_STATE],
            StateErrorType.PERMISSION_DENIED: [StateRecoveryAction.RETRY],
            StateErrorType.DISK_FULL: [StateRecoveryAction.RETRY, StateRecoveryAction.ABORT],
            StateErrorType.NETWORK_ERROR: [StateRecoveryAction.RETRY],
            StateErrorType.TIMEOUT: [StateRecoveryAction.RETRY],
            StateErrorType.UNKNOWN_ERROR: [StateRecoveryAction.RETRY, StateRecoveryAction.USE_BACKUP]
        }
        
        return recovery_map.get(error_type, [StateRecoveryAction.RETRY])
        
    async def _attempt_recovery(
        self,
        action: StateRecoveryAction,
        error_context: StateErrorContext,
        state_data: Dict[str, Any]
    ) -> bool:
        """Attempt recovery for save operations."""
        if action == StateRecoveryAction.RETRY:
            return await self._retry_save(error_context, state_data)
        elif action == StateRecoveryAction.USE_BACKUP:
            return await self._save_to_backup(error_context, state_data)
        elif action == StateRecoveryAction.CREATE_NEW:
            return await self._create_new_state_file(error_context, state_data)
        elif action == StateRecoveryAction.FALLBACK_DEFAULT:
            return await self._save_unencrypted(error_context, state_data)
        else:
            return False
            
    async def _attempt_load_recovery(
        self,
        action: StateRecoveryAction,
        error_context: StateErrorContext
    ) -> Optional[Dict[str, Any]]:
        """Attempt recovery for load operations."""
        if action == StateRecoveryAction.REPAIR_STATE:
            return await self._repair_and_load_state(error_context)
        elif action == StateRecoveryAction.USE_BACKUP:
            return await self._load_from_backup(error_context)
        elif action == StateRecoveryAction.RETRY:
            return await self._retry_load(error_context)
        else:
            return None
            
    async def _attempt_delete_recovery(
        self,
        action: StateRecoveryAction,
        error_context: StateErrorContext
    ) -> bool:
        """Attempt recovery for delete operations."""
        if action == StateRecoveryAction.RETRY:
            return await self._retry_delete(error_context)
        else:
            return False
            
    async def _retry_save(self, error_context: StateErrorContext, state_data: Dict[str, Any]) -> bool:
        """Retry save operation with exponential backoff."""
        retry_config = self.retry_configs.get(error_context.error_type)
        if not retry_config:
            return False
            
        try:
            await resilience_manager.execute_with_resilience(
                "retry_save",
                self._perform_save,
                error_context.state_id,
                state_data,
                retry_config="custom" if retry_config else "default"
            )
            return True
        except Exception:
            return False
            
    async def _retry_load(self, error_context: StateErrorContext) -> Optional[Dict[str, Any]]:
        """Retry load operation with exponential backoff."""
        retry_config = self.retry_configs.get(error_context.error_type)
        if not retry_config:
            return None
            
        try:
            return await resilience_manager.execute_with_resilience(
                "retry_load",
                self._perform_load,
                error_context.state_id,
                retry_config="custom" if retry_config else "default"
            )
        except Exception:
            return None
            
    async def _retry_delete(self, error_context: StateErrorContext) -> bool:
        """Retry delete operation."""
        try:
            # Simple retry for delete operations
            return await self._perform_delete(error_context.state_id)
        except Exception:
            return False
            
    async def _save_to_backup(self, error_context: StateErrorContext, state_data: Dict[str, Any]) -> bool:
        """Save state to backup location."""
        try:
            backup_id = await self.corruption_detector.create_backup(
                error_context.state_id or "unknown",
                "error_recovery"
            )
            
            # Save to backup file
            backup_path = Path(self.storage_dir) / f"{backup_id}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception:
            return False
            
    async def _create_new_state_file(self, error_context: StateErrorContext, state_data: Dict[str, Any]) -> bool:
        """Create new state file with timestamp."""
        try:
            timestamp = int(time.time())
            new_state_id = f"{error_context.state_id}_recovered_{timestamp}"
            
            # Update state data with new ID
            state_data["state_id"] = new_state_id
            state_data["recovery_timestamp"] = timestamp
            state_data["original_state_id"] = error_context.state_id
            
            new_path = Path(self.storage_dir) / f"{new_state_id}.json"
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception:
            return False
            
    async def _save_unencrypted(self, error_context: StateErrorContext, state_data: Dict[str, Any]) -> bool:
        """Save state without encryption as fallback."""
        try:
            file_path = Path(self.storage_dir) / f"{error_context.state_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception:
            return False
            
    async def _repair_and_load_state(self, error_context: StateErrorContext) -> Optional[Dict[str, Any]]:
        """Repair corrupted state and load it."""
        try:
            repaired_state = await self.corruption_detector.repair_state(
                error_context.state_id,
                "auto"
            )
            
            if repaired_state:
                return repaired_state.to_dict()
            else:
                return None
        except Exception:
            return None
            
    async def _load_from_backup(self, error_context: StateErrorContext) -> Optional[Dict[str, Any]]:
        """Load state from backup."""
        try:
            backup_state = await self.corruption_detector._restore_from_backup(error_context.state_id)
            
            if backup_state:
                return backup_state.to_dict()
            else:
                return None
        except Exception:
            return None
            
    async def _perform_save(self, state_id: str, state_data: Dict[str, Any]) -> None:
        """Perform the actual save operation."""
        file_path = Path(self.storage_dir) / f"{state_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
            
    async def _perform_load(self, state_id: str) -> Dict[str, Any]:
        """Perform the actual load operation."""
        file_path = Path(self.storage_dir) / f"{state_id}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    async def _perform_delete(self, state_id: str) -> bool:
        """Perform the actual delete operation."""
        file_path = Path(self.storage_dir) / f"{state_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False


# Global error handler instance
_error_handler_instance: Optional[StateErrorHandler] = None


def get_state_error_handler(storage_dir: str, **kwargs) -> StateErrorHandler:
    """Get or create state error handler instance."""
    global _error_handler_instance
    
    if _error_handler_instance is None:
        _error_handler_instance = StateErrorHandler(storage_dir, **kwargs)
        
    return _error_handler_instance
