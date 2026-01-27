"""
State Corruption Detection and Recovery

This module provides state corruption detection and fallback logic
for browser state persistence.
"""

import json
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import structlog
from dataclasses import dataclass

from .models.state import BrowserState, StateStatus
from .models.enums import SessionStatus
from .exceptions import StateCorruptionError
from .encryption import StateEncryption


@dataclass
class CorruptionReport:
    """Report of state corruption analysis."""
    state_id: str
    is_corrupted: bool
    corruption_type: Optional[str] = None
    corruption_details: Optional[str] = None
    recoverable: bool = False
    recovery_suggestions: List[str] = None
    backup_available: bool = False
    backup_state_id: Optional[str] = None
    
    def __post_init__(self):
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []


class StateCorruptionDetector:
    """Detects and analyzes state corruption."""
    
    def __init__(self, storage_dir: str, encryption: Optional[StateEncryption] = None):
        self.storage_dir = Path(storage_dir)
        self.encryption = encryption
        self.logger = structlog.get_logger("browser.corruption_detector")
        
    async def analyze_state(self, state_id: str) -> CorruptionReport:
        """Analyze a state for corruption."""
        try:
            report = CorruptionReport(state_id=state_id)
            
            # Check if state files exist
            json_path = self.storage_dir / f"{state_id}.json"
            encrypted_path = self.storage_dir / f"{state_id}.encrypted"
            
            if not json_path.exists() and not encrypted_path.exists():
                report.is_corrupted = True
                report.corruption_type = "missing_files"
                report.corruption_details = "State files not found"
                report.recoverable = False
                return report
                
            # Load and validate state data
            state_data = None
            try:
                if encrypted_path.exists() and self.encryption:
                    with open(encrypted_path, 'rb') as f:
                        encrypted_data = f.read()
                    state_data = self.encryption.decrypt_authentication_tokens(encrypted_data)
                elif json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                else:
                    report.is_corrupted = True
                    report.corruption_type = "missing_primary_file"
                    report.corruption_details = "Neither JSON nor encrypted file found"
                    report.recoverable = False
                    return report
                    
            except Exception as e:
                report.is_corrupted = True
                report.corruption_type = "file_corruption"
                report.corruption_details = f"Failed to load state data: {str(e)}"
                report.recoverable = await self._check_for_backup(state_id)
                if report.recoverable:
                    report.recovery_suggestions.append("Restore from backup state")
                return report
                
            # Validate state structure
            structure_issues = self._validate_state_structure(state_data)
            if structure_issues:
                report.is_corrupted = True
                report.corruption_type = "structure_corruption"
                report.corruption_details = "; ".join(structure_issues)
                report.recoverable = await self._check_for_backup(state_id)
                if report.recoverable:
                    report.recovery_suggestions.append("Restore from backup state")
                report.recovery_suggestions.extend([
                    "Attempt manual data repair",
                    "Create new state from session"
                ])
                return report
                
            # Validate state content
            content_issues = self._validate_state_content(state_data)
            if content_issues:
                report.is_corrupted = True
                report.corruption_type = "content_corruption"
                report.corruption_details = "; ".join(content_issues)
                report.recoverable = True
                report.recovery_suggestions.extend([
                    "Clean invalid data fields",
                    "Reset corrupted components",
                    "Restore from backup if available"
                ])
                return report
                
            # Check for expired state
            if self._is_state_expired(state_data):
                report.is_corrupted = True
                report.corruption_type = "expiration"
                report.corruption_details = "State has expired"
                report.recoverable = True
                report.recovery_suggestions.append("Create fresh state")
                return report
                
            # State appears valid
            report.is_corrupted = False
            report.recoverable = True
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze state",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            return CorruptionReport(
                state_id=state_id,
                is_corrupted=True,
                corruption_type="analysis_failure",
                corruption_details=f"Analysis failed: {str(e)}",
                recoverable=False
            )
            
    async def repair_state(self, state_id: str, repair_strategy: str = "auto") -> Optional[BrowserState]:
        """Attempt to repair a corrupted state."""
        try:
            # Analyze corruption first
            report = await self.analyze_state(state_id)
            
            if not report.is_corrupted:
                self.logger.info(
                    "State is not corrupted, no repair needed",
                    state_id=state_id
                )
                # Load and return valid state
                return await self._load_state_safe(state_id)
                
            if not report.recoverable:
                self.logger.error(
                    "State corruption is not recoverable",
                    state_id=state_id,
                    corruption_type=report.corruption_type
                )
                return None
                
            # Attempt repair based on corruption type
            if repair_strategy == "auto":
                return await self._auto_repair_state(state_id, report)
            elif repair_strategy == "backup":
                return await self._restore_from_backup(state_id)
            elif repair_strategy == "clean":
                return await self._clean_repair_state(state_id, report)
            else:
                self.logger.error(
                    "Unknown repair strategy",
                    state_id=state_id,
                    strategy=repair_strategy
                )
                return None
                
        except Exception as e:
            self.logger.error(
                "Failed to repair state",
                state_id=state_id,
                strategy=repair_strategy,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def create_backup(self, state_id: str, backup_suffix: Optional[str] = None) -> str:
        """Create backup of a state."""
        try:
            if backup_suffix is None:
                backup_suffix = f"backup_{int(time.time())}"
                
            backup_id = f"{state_id}_{backup_suffix}"
            
            # Copy files
            json_path = self.storage_dir / f"{state_id}.json"
            backup_json_path = self.storage_dir / f"{backup_id}.json"
            
            if json_path.exists():
                import shutil
                shutil.copy2(json_path, backup_json_path)
                
            encrypted_path = self.storage_dir / f"{state_id}.encrypted"
            backup_encrypted_path = self.storage_dir / f"{backup_id}.encrypted"
            
            if encrypted_path.exists():
                import shutil
                shutil.copy2(encrypted_path, backup_encrypted_path)
                
            self.logger.info(
                "State backup created",
                original_state_id=state_id,
                backup_state_id=backup_id
            )
            
            return backup_id
            
        except Exception as e:
            self.logger.error(
                "Failed to create backup",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise StateCorruptionError(
                "backup_creation_failed",
                state_id,
                corruption_details=f"Failed to create backup: {str(e)}"
            )
            
    def _validate_state_structure(self, state_data: Dict[str, Any]) -> List[str]:
        """Validate state structure."""
        issues = []
        
        required_fields = ["state_id", "session_id", "schema_version"]
        for field in required_fields:
            if field not in state_data:
                issues.append(f"Missing required field: {field}")
                
        # Validate optional fields have correct types
        if "cookies" in state_data and not isinstance(state_data["cookies"], list):
            issues.append("Cookies field must be a list")
            
        if "local_storage" in state_data and not isinstance(state_data["local_storage"], dict):
            issues.append("Local storage field must be a dictionary")
            
        if "session_storage" in state_data and not isinstance(state_data["session_storage"], dict):
            issues.append("Session storage field must be a dictionary")
            
        return issues
        
    def _validate_state_content(self, state_data: Dict[str, Any]) -> List[str]:
        """Validate state content."""
        issues = []
        
        # Validate cookies
        if "cookies" in state_data:
            for i, cookie in enumerate(state_data["cookies"]):
                if not isinstance(cookie, dict):
                    issues.append(f"Cookie {i} is not a dictionary")
                    continue
                    
                required_cookie_fields = ["name", "value", "domain"]
                for field in required_cookie_fields:
                    if field not in cookie:
                        issues.append(f"Cookie {i} missing field: {field}")
                        
        # Validate timestamps
        if "created_at" in state_data:
            try:
                created_at = state_data["created_at"]
                if isinstance(created_at, str):
                    # Try to parse ISO format
                    from datetime import datetime
                    datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                elif not isinstance(created_at, (int, float)):
                    issues.append("created_at must be timestamp number or ISO string")
            except Exception:
                issues.append("created_at has invalid timestamp format")
                
        return issues
        
    def _is_state_expired(self, state_data: Dict[str, Any]) -> bool:
        """Check if state is expired."""
        if "expires_at" not in state_data:
            return False
            
        expires_at = state_data["expires_at"]
        if expires_at is None:
            return False
            
        try:
            if isinstance(expires_at, str):
                from datetime import datetime
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                return datetime.now().timestamp() > expires_dt.timestamp()
            else:
                return time.time() > expires_at
        except Exception:
            return False
            
    async def _check_for_backup(self, state_id: str) -> bool:
        """Check if backup is available."""
        try:
            # Look for backup files
            backup_pattern = f"{state_id}_backup_"
            for file_path in self.storage_dir.glob(f"{backup_pattern}*.json"):
                return True
                
            for file_path in self.storage_dir.glob(f"{backup_pattern}*.encrypted"):
                return True
                
            return False
            
        except Exception:
            return False
            
    async def _load_state_safe(self, state_id: str) -> Optional[BrowserState]:
        """Safely load state with corruption detection."""
        try:
            # This would use the state manager to load the state
            # For now, return None
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to load state safely",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def _auto_repair_state(self, state_id: str, report: CorruptionReport) -> Optional[BrowserState]:
        """Attempt automatic repair based on corruption type."""
        try:
            if report.corruption_type == "content_corruption":
                return await self._clean_repair_state(state_id, report)
            elif report.corruption_type == "structure_corruption":
                return await self._structure_repair_state(state_id, report)
            elif report.backup_available:
                return await self._restore_from_backup(state_id)
            else:
                self.logger.warning(
                    "No auto-repair available for corruption type",
                    state_id=state_id,
                    corruption_type=report.corruption_type
                )
                return None
                
        except Exception as e:
            self.logger.error(
                "Auto repair failed",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def _clean_repair_state(self, state_id: str, report: CorruptionReport) -> Optional[BrowserState]:
        """Clean repair by removing invalid data."""
        try:
            # Load state data
            state_data = await self._load_raw_state_data(state_id)
            if state_data is None:
                return None
                
            # Clean invalid cookies
            if "cookies" in state_data:
                valid_cookies = []
                for cookie in state_data["cookies"]:
                    if isinstance(cookie, dict) and all(field in cookie for field in ["name", "value", "domain"]):
                        valid_cookies.append(cookie)
                state_data["cookies"] = valid_cookies
                
            # Clean storage data
            for storage_key in ["local_storage", "session_storage"]:
                if storage_key in state_data and not isinstance(state_data[storage_key], dict):
                    state_data[storage_key] = {}
                    
            # Save cleaned state
            await self._save_state_data(state_id, state_data)
            
            # Load as BrowserState
            return BrowserState.from_dict(state_data)
            
        except Exception as e:
            self.logger.error(
                "Clean repair failed",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def _structure_repair_state(self, state_id: str, report: CorruptionReport) -> Optional[BrowserState]:
        """Repair state structure issues."""
        try:
            # Load state data
            state_data = await self._load_raw_state_data(state_id)
            if state_data is None:
                return None
                
            # Add missing required fields with defaults
            if "state_id" not in state_data:
                state_data["state_id"] = state_id
                
            if "session_id" not in state_data:
                state_data["session_id"] = "unknown"
                
            if "schema_version" not in state_data:
                state_data["schema_version"] = "1.0.0"
                
            # Ensure optional fields have correct types
            if "cookies" not in state_data:
                state_data["cookies"] = []
            elif not isinstance(state_data["cookies"], list):
                state_data["cookies"] = []
                
            if "local_storage" not in state_data:
                state_data["local_storage"] = {}
            elif not isinstance(state_data["local_storage"], dict):
                state_data["local_storage"] = {}
                
            if "session_storage" not in state_data:
                state_data["session_storage"] = {}
            elif not isinstance(state_data["session_storage"], dict):
                state_data["session_storage"] = {}
                
            # Save repaired state
            await self._save_state_data(state_id, state_data)
            
            # Load as BrowserState
            return BrowserState.from_dict(state_data)
            
        except Exception as e:
            self.logger.error(
                "Structure repair failed",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def _restore_from_backup(self, state_id: str) -> Optional[BrowserState]:
        """Restore state from backup."""
        try:
            # Find most recent backup
            backup_id = await self._find_most_recent_backup(state_id)
            if backup_id is None:
                return None
                
            # Load backup state
            backup_state = await self._load_state_safe(backup_id)
            if backup_state is None:
                return None
                
            # Update state ID to original
            backup_state.state_id = state_id
            
            # Save as repaired state
            await self._save_state_data(state_id, backup_state.to_dict())
            
            self.logger.info(
                "State restored from backup",
                original_state_id=state_id,
                backup_state_id=backup_id
            )
            
            return backup_state
            
        except Exception as e:
            self.logger.error(
                "Backup restore failed",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def _find_most_recent_backup(self, state_id: str) -> Optional[str]:
        """Find most recent backup for a state."""
        try:
            backup_pattern = f"{state_id}_backup_"
            backups = []
            
            # Find backup files
            for file_path in self.storage_dir.glob(f"{backup_pattern}*.json"):
                backup_id = file_path.stem
                backups.append((backup_id, file_path.stat().st_mtime))
                
            for file_path in self.storage_dir.glob(f"{backup_pattern}*.encrypted"):
                backup_id = file_path.stem
                backups.append((backup_id, file_path.stat().st_mtime))
                
            if not backups:
                return None
                
            # Return most recent backup
            return max(backups, key=lambda x: x[1])[0]
            
        except Exception:
            return None
            
    async def _load_raw_state_data(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Load raw state data without validation."""
        try:
            json_path = self.storage_dir / f"{state_id}.json"
            encrypted_path = self.storage_dir / f"{state_id}.encrypted"
            
            if encrypted_path.exists() and self.encryption:
                with open(encrypted_path, 'rb') as f:
                    encrypted_data = f.read()
                return self.encryption.decrypt_authentication_tokens(encrypted_data)
            elif json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return None
                
        except Exception:
            return None
            
    async def _save_state_data(self, state_id: str, state_data: Dict[str, Any]) -> None:
        """Save state data without validation."""
        try:
            json_path = self.storage_dir / f"{state_id}.json"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise StateCorruptionError(
                "state_save_failed",
                state_id,
                corruption_details=f"Failed to save state: {str(e)}"
            )
