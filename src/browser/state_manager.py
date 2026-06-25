"""
State Manager Implementation

This module implements the StateManager class for browser state persistence,
following the IStateManager interface.
"""

import asyncio
import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .interfaces import IStateManager
from .models.state import BrowserState, CookieData, ViewportSettings
from .models.enums import StateStatus
from .exceptions import StateCorruptionError, ConfigurationError
from ..config.settings import get_config


class StateManager(IStateManager):
    """Manages browser state persistence with encryption and validation."""
    
    def __init__(self, storage_dir: Optional[str] = None, encryption_key: Optional[str] = None):
        self.storage_dir = Path(storage_dir or "data/storage/browser-states")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encryption_key = encryption_key
        self._cipher_suite: Optional[Fernet] = None
        self.logger = structlog.get_logger("browser.state_manager")
        
        # Initialize encryption if key provided
        if self.encryption_key:
            self._initialize_encryption()
            
        # Load configuration
        self.config = get_config()
        
    def _initialize_encryption(self) -> None:
        """Initialize encryption cipher suite."""
        try:
            # Derive key from encryption key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'scorewise_browser_state',  # Fixed salt for consistency
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            self._cipher_suite = Fernet(key)
            
            self.logger.info("State encryption initialized")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize encryption",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ConfigurationError(
                "state_manager", "encryption", 
                f"Failed to initialize encryption: {e}"
            )
            
    async def save_state(self, session: "BrowserSession", state_id: Optional[str] = None) -> str:
        """Save browser state to storage."""
        try:
            # Generate state ID if not provided
            if state_id is None:
                state_id = f"{session.session_id}_{int(time.time())}"
                
            # Create browser state from session
            browser_state = await self._extract_state_from_session(session, state_id)
            
            # Validate state
            validation_issues = browser_state.validate()
            if validation_issues:
                self.logger.warning(
                    "State validation issues found",
                    state_id=state_id,
                    issues=validation_issues
                )
                
            # Serialize and optionally encrypt
            state_data = browser_state.to_dict()
            if self._cipher_suite and self.config.browser.state_encryption_enabled:
                state_json = json.dumps(state_data, ensure_ascii=False)
                encrypted_data = self._cipher_suite.encrypt(state_json.encode('utf-8'))
                file_path = self.storage_dir / f"{state_id}.encrypted"
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)
            else:
                file_path = self.storage_dir / f"{state_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                    
            self.logger.info(
                "Browser state saved",
                state_id=state_id,
                session_id=session.session_id,
                encrypted=bool(self._cipher_suite),
                file_path=str(file_path)
            )
            
            return state_id
            
        except Exception as e:
            self.logger.error(
                "Failed to save state",
                state_id=state_id,
                session_id=session.session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise StateCorruptionError(
                f"Failed to save state {state_id}",
                state_id=state_id,
                corruption_details=str(e)
            )
            
    async def load_state(self, state_id: str) -> Optional[BrowserState]:
        """Load browser state from storage."""
        try:
            # Try encrypted file first
            encrypted_path = self.storage_dir / f"{state_id}.encrypted"
            json_path = self.storage_dir / f"{state_id}.json"
            
            state_data = None
            
            if encrypted_path.exists():
                # Load encrypted state
                if not self._cipher_suite:
                    self.logger.error(
                        "Cannot load encrypted state without encryption key",
                        state_id=state_id
                    )
                    return None
                    
                with open(encrypted_path, 'rb') as f:
                    encrypted_data = f.read()
                    
                try:
                    decrypted_data = self._cipher_suite.decrypt(encrypted_data)
                    state_data = json.loads(decrypted_data.decode('utf-8'))
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to decrypt state",
                        state_id=state_id,
                        error=str(e)
                    )
                    return None
                    
            elif json_path.exists():
                # Load unencrypted state
                with open(json_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    
            else:
                self.logger.warning(
                    "State file not found",
                    state_id=state_id
                )
                return None
                
            # Create BrowserState from data
            browser_state = BrowserState.from_dict(state_data)
            
            # Validate loaded state
            validation_issues = browser_state.validate()
            if validation_issues:
                self.logger.warning(
                    "Loaded state validation issues",
                    state_id=state_id,
                    issues=validation_issues
                )
                
            # Check if state is expired
            if browser_state.is_expired():
                self.logger.warning(
                    "Loaded state is expired",
                    state_id=state_id,
                    expires_at=browser_state.expires_at
                )
                return None
                
            self.logger.info(
                "Browser state loaded",
                state_id=state_id,
                session_id=browser_state.session_id,
                cookies=len(browser_state.cookies),
                storage_items=len(browser_state.local_storage) + len(browser_state.session_storage)
            )
            
            return browser_state
            
        except Exception as e:
            self.logger.error(
                "Failed to load state",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def list_states(self, session_id: Optional[str] = None) -> List[str]:
        """List saved state IDs, optionally filtered by session."""
        try:
            state_ids = []
            
            # Scan storage directory
            for file_path in self.storage_dir.glob("*.json"):
                state_id = file_path.stem
                if await self._should_include_state(state_id, session_id):
                    state_ids.append(state_id)
                    
            # Also scan encrypted files
            for file_path in self.storage_dir.glob("*.encrypted"):
                state_id = file_path.stem
                if state_id not in state_ids and await self._should_include_state(state_id, session_id):
                    state_ids.append(state_id)
                    
            # Sort by creation time (newest first)
            state_ids.sort(key=lambda x: self._get_state_timestamp(x), reverse=True)
            
            return state_ids
            
        except Exception as e:
            self.logger.error(
                "Failed to list states",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
            
    async def delete_state(self, state_id: str) -> bool:
        """Delete a saved state."""
        try:
            deleted = False
            
            # Delete JSON file
            json_path = self.storage_dir / f"{state_id}.json"
            if json_path.exists():
                json_path.unlink()
                deleted = True
                
            # Delete encrypted file
            encrypted_path = self.storage_dir / f"{state_id}.encrypted"
            if encrypted_path.exists():
                encrypted_path.unlink()
                deleted = True
                
            if deleted:
                self.logger.info(
                    "State deleted",
                    state_id=state_id
                )
            else:
                self.logger.warning(
                    "State file not found for deletion",
                    state_id=state_id
                )
                
            return deleted
            
        except Exception as e:
            self.logger.error(
                "Failed to delete state",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def cleanup_expired_states(self) -> int:
        """Clean up expired states, returns count deleted."""
        try:
            deleted_count = 0
            retention_days = self.config.browser.state_retention_days
            cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
            
            # Get all state IDs
            all_states = await self.list_states()
            
            for state_id in all_states:
                timestamp = self._get_state_timestamp(state_id)
                
                # Delete if older than retention period
                if timestamp < cutoff_time:
                    if await self.delete_state(state_id):
                        deleted_count += 1
                        
            self.logger.info(
                "Expired states cleanup completed",
                deleted_count=deleted_count,
                retention_days=retention_days
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup expired states",
                error=str(e),
                error_type=type(e).__name__
            )
            return 0
            
    async def encrypt_state_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt state data for secure storage."""
        if not self._cipher_suite:
            raise ConfigurationError(
                "state_manager", "encryption",
                "Encryption not initialized"
            )
            
        try:
            state_json = json.dumps(data, ensure_ascii=False)
            return self._cipher_suite.encrypt(state_json.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt state data",
                error=str(e),
                error_type=type(e).__name__
            )
            raise StateCorruptionError(
                "encryption_failed",
                "state_data",
                corruption_details=str(e)
            )
            
    async def decrypt_state_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt state data from secure storage."""
        if not self._cipher_suite:
            raise ConfigurationError(
                "state_manager", "encryption",
                "Encryption not initialized"
            )
            
        try:
            decrypted_data = self._cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt state data",
                error=str(e),
                error_type=type(e).__name__
            )
            raise StateCorruptionError(
                "decryption_failed",
                "state_data",
                corruption_details=str(e)
            )
            
    async def _extract_state_from_session(self, session: "BrowserSession", state_id: str) -> BrowserState:
        """Extract state data from browser session."""
        # This would be implemented when we have the actual BrowserSession class
        # For now, create a basic state
        return BrowserState(
            state_id=state_id,
            session_id=session.session_id,
            created_at=time.time(),
            expires_at=time.time() + (self.config.browser.state_retention_days * 24 * 60 * 60)
        )
        
    async def _should_include_state(self, state_id: str, session_id: Optional[str]) -> bool:
        """Check if state should be included in listing."""
        if session_id is None:
            return True
            
        # Load state to check session ID (lightweight check)
        try:
            state = await self.load_state(state_id)
            return state is not None and state.session_id == session_id
        except Exception:
            return False
            
    def _get_state_timestamp(self, state_id: str) -> float:
        """Extract timestamp from state ID."""
        # State IDs are formatted as "session_id_timestamp"
        parts = state_id.split('_')
        if len(parts) >= 2:
            try:
                return float(parts[-1])
            except ValueError:
                pass
        return 0.0


# Global state manager instance
state_manager = StateManager()
