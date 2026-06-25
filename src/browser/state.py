"""
Browser State Manager

This module implements the StateManager class for browser state persistence
with JSON persistence, schema versioning, encryption, and corruption detection.
"""

import json
import os
import time
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from cryptography.fernet import Fernet
import structlog

from .interfaces import IStateManager
from .models.state import BrowserState, CookieData, ViewportSettings
from .models.enums import StateStatus
from src.utils.exceptions import BrowserStateError


class StateManager(IStateManager):
    """Manages browser state persistence with encryption and corruption detection."""
    
    def __init__(
        self,
        storage_dir: str = "data/browser_states",
        encryption_key: Optional[bytes] = None,
        default_ttl_hours: int = 24,
        schema_version: str = "1.0.0"
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self.default_ttl_hours = default_ttl_hours
        self.schema_version = schema_version
        
        self.logger = structlog.get_logger("browser.state_manager")
        
        # Initialize state index
        self._state_index_file = self.storage_dir / "state_index.json"
        self._state_index = self._load_state_index()
        
    def _generate_encryption_key(self) -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
        
    def _load_state_index(self) -> Dict[str, Any]:
        """Load the state index from disk."""
        if self._state_index_file.exists():
            try:
                with open(self._state_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    "Failed to load state index, creating new one",
                    error=str(e)
                )
                return {"states": {}, "version": "1.0.0", "last_updated": time.time()}
        return {"states": {}, "version": "1.0.0", "last_updated": time.time()}
        
    def _save_state_index(self) -> None:
        """Save the state index to disk."""
        self._state_index["last_updated"] = time.time()
        try:
            with open(self._state_index_file, 'w', encoding='utf-8') as f:
                json.dump(self._state_index, f, indent=2)
        except IOError as e:
            self.logger.error(
                "Failed to save state index",
                error=str(e)
            )
            raise BrowserStateError(
                "state_index_save_failed",
                f"Failed to save state index: {e}"
            )
            
    def _get_state_file_path(self, state_id: str) -> Path:
        """Get the file path for a state."""
        return self.storage_dir / f"{state_id}.json"
        
    def _get_state_metadata(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a state from the index."""
        return self._state_index["states"].get(state_id)
        
    def _update_state_metadata(self, state_id: str, metadata: Dict[str, Any]) -> None:
        """Update metadata for a state in the index."""
        self._state_index["states"][state_id] = {
            **metadata,
            "updated_at": time.time()
        }
        self._save_state_index()
        
    def _remove_state_metadata(self, state_id: str) -> None:
        """Remove metadata for a state from the index."""
        self._state_index["states"].pop(state_id, None)
        self._save_state_index()
        
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for data corruption detection."""
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        
    def _verify_checksum(self, data: Dict[str, Any], expected_checksum: str) -> bool:
        """Verify data integrity using checksum."""
        actual_checksum = self._calculate_checksum(data)
        return actual_checksum == expected_checksum
        
    async def save_state(self, session: "BrowserSession", state_id: Optional[str] = None) -> str:
        """Save browser state to storage."""
        try:
            # Generate state ID if not provided
            if state_id is None:
                state_id = f"state_{session.session_id}_{int(time.time())}"
            
            # Create browser state from session
            browser_state = await self._extract_state_from_session(session)
            
            # Validate state
            validation_issues = browser_state.validate()
            if validation_issues:
                self.logger.warning(
                    "State validation issues found",
                    state_id=state_id,
                    issues=validation_issues
                )
            
            # Convert to dictionary
            state_data = browser_state.to_dict()
            
            # Add checksum for corruption detection
            checksum = self._calculate_checksum(state_data)
            state_data["checksum"] = checksum
            
            # Encrypt sensitive data
            if state_data.get("authentication_tokens"):
                encrypted_tokens = await self.encrypt_state_data(
                    {"authentication_tokens": state_data["authentication_tokens"]}
                )
                state_data["encrypted_auth_tokens"] = encrypted_tokens.hex()
                del state_data["authentication_tokens"]
            
            # Save to file
            state_file = self._get_state_file_path(state_id)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
            
            # Update index
            metadata = {
                "state_id": state_id,
                "session_id": session.session_id,
                "created_at": time.time(),
                "expires_at": time.time() + (self.default_ttl_hours * 3600),
                "schema_version": self.schema_version,
                "checksum": checksum,
                "size_bytes": browser_state.get_size_bytes(),
                "cookie_count": len(browser_state.cookies),
                "has_auth_tokens": bool(browser_state.authentication_tokens)
            }
            self._update_state_metadata(state_id, metadata)
            
            self.logger.info(
                "State saved successfully",
                state_id=state_id,
                session_id=session.session_id,
                size_bytes=metadata["size_bytes"],
                cookie_count=metadata["cookie_count"]
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
            raise BrowserStateError(
                "state_save_failed",
                f"Failed to save state: {e}"
            )
            
    async def load_state(self, state_id: str) -> Optional[BrowserState]:
        """Load browser state from storage."""
        try:
            # Check metadata
            metadata = self._get_state_metadata(state_id)
            if not metadata:
                self.logger.warning(
                    "State not found in index",
                    state_id=state_id
                )
                return None
            
            # Check expiration
            if time.time() > metadata.get("expires_at", float('inf')):
                self.logger.info(
                    "State expired, cleaning up",
                    state_id=state_id
                )
                await self.delete_state(state_id)
                return None
            
            # Load state file
            state_file = self._get_state_file_path(state_id)
            if not state_file.exists():
                self.logger.warning(
                    "State file not found",
                    state_id=state_id
                )
                self._remove_state_metadata(state_id)
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # Verify checksum
            stored_checksum = state_data.pop("checksum", None)
            if stored_checksum and not self._verify_checksum(state_data, stored_checksum):
                self.logger.error(
                    "State corruption detected",
                    state_id=state_id,
                    stored_checksum=stored_checksum
                )
                await self.delete_state(state_id)
                return None
            
            # Decrypt authentication tokens if present
            if "encrypted_auth_tokens" in state_data:
                encrypted_data = bytes.fromhex(state_data["encrypted_auth_tokens"])
                decrypted_data = await self.decrypt_state_data(encrypted_data)
                state_data["authentication_tokens"] = decrypted_data.get("authentication_tokens", {})
                del state_data["encrypted_auth_tokens"]
            
            # Create BrowserState object
            browser_state = BrowserState.from_dict(state_data)
            
            self.logger.info(
                "State loaded successfully",
                state_id=state_id,
                session_id=browser_state.session_id,
                cookie_count=len(browser_state.cookies)
            )
            
            return browser_state
            
        except Exception as e:
            self.logger.error(
                "Failed to load state",
                state_id=state_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Don't raise error for load failures, just return None
            return None
            
    async def list_states(self, session_id: Optional[str] = None) -> List[str]:
        """List saved state IDs, optionally filtered by session."""
        try:
            states = []
            current_time = time.time()
            
            for state_id, metadata in self._state_index["states"].items():
                # Filter by session ID if provided
                if session_id and metadata.get("session_id") != session_id:
                    continue
                
                # Skip expired states
                if current_time > metadata.get("expires_at", float('inf')):
                    continue
                
                states.append(state_id)
            
            return sorted(states, key=lambda x: self._state_index["states"][x].get("created_at", 0), reverse=True)
            
        except Exception as e:
            self.logger.error(
                "Failed to list states",
                session_id=session_id,
                error=str(e)
            )
            return []
            
    async def delete_state(self, state_id: str) -> bool:
        """Delete a saved state."""
        try:
            # Delete state file
            state_file = self._get_state_file_path(state_id)
            if state_file.exists():
                state_file.unlink()
            
            # Remove from index
            self._remove_state_metadata(state_id)
            
            self.logger.info(
                "State deleted successfully",
                state_id=state_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete state",
                state_id=state_id,
                error=str(e)
            )
            return False
            
    async def cleanup_expired_states(self) -> int:
        """Clean up expired states, returns count deleted."""
        try:
            current_time = time.time()
            expired_states = []
            
            for state_id, metadata in self._state_index["states"].items():
                if current_time > metadata.get("expires_at", float('inf')):
                    expired_states.append(state_id)
            
            # Delete expired states
            deleted_count = 0
            for state_id in expired_states:
                if await self.delete_state(state_id):
                    deleted_count += 1
            
            self.logger.info(
                "Expired states cleanup completed",
                total_expired=len(expired_states),
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup expired states",
                error=str(e)
            )
            return 0
            
    async def encrypt_state_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt state data for secure storage."""
        try:
            data_str = json.dumps(data, separators=(',', ':'))
            encrypted_data = self.cipher.encrypt(data_str.encode('utf-8'))
            return encrypted_data
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt state data",
                error=str(e)
            )
            raise BrowserStateError(
                "encryption_failed",
                f"Failed to encrypt state data: {e}"
            )
            
    async def decrypt_state_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt state data from secure storage."""
        try:
            decrypted_str = self.cipher.decrypt(encrypted_data).decode('utf-8')
            return json.loads(decrypted_str)
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt state data",
                error=str(e)
            )
            raise BrowserStateError(
                "decryption_failed",
                f"Failed to decrypt state data: {e}"
            )
            
    async def _extract_state_from_session(self, session: "BrowserSession") -> BrowserState:
        """Extract browser state from a session."""
        try:
            # Extract cookies from all contexts
            cookies = []
            for tab_context in session.tab_contexts.values():
                if tab_context._playwright_context:
                    context_cookies = await tab_context._playwright_context.cookies()
                    for cookie in context_cookies:
                        cookies.append(CookieData(
                            name=cookie["name"],
                            value=cookie["value"],
                            domain=cookie["domain"],
                            path=cookie["path"],
                            expires=cookie.get("expires"),
                            secure=cookie.get("secure", False),
                            http_only=cookie.get("httpOnly", False),
                            same_site=cookie.get("sameSite", "Lax")
                        ))
            
            # Extract local storage and session storage from active tab
            local_storage = {}
            session_storage = {}
            
            active_tab = await session.get_active_tab_context()
            if active_tab and active_tab._playwright_page:
                try:
                    # Get local storage
                    local_storage_data = await active_tab._playwright_page.evaluate("""
                        () => {
                            const storage = {};
                            for (let i = 0; i < localStorage.length; i++) {
                                const key = localStorage.key(i);
                                storage[key] = localStorage.getItem(key);
                            }
                            return storage;
                        }
                    """)
                    local_storage = local_storage_data or {}
                    
                    # Get session storage
                    session_storage_data = await active_tab._playwright_page.evaluate("""
                        () => {
                            const storage = {};
                            for (let i = 0; i < sessionStorage.length; i++) {
                                const key = sessionStorage.key(i);
                                storage[key] = sessionStorage.getItem(key);
                            }
                            return storage;
                        }
                    """)
                    session_storage = session_storage_data or {}
                    
                except Exception as e:
                    self.logger.warning(
                        "Failed to extract storage data",
                        session_id=session.session_id,
                        error=str(e)
                    )
            
            # Create browser state
            browser_state = BrowserState(
                state_id="",  # Will be set by save_state
                session_id=session.session_id,
                cookies=cookies,
                local_storage=local_storage,
                session_storage=session_storage,
                user_agent=session.configuration.stealth.user_agent,
                viewport=ViewportSettings(
                    width=session.configuration.stealth.viewport.get("width", 1920),
                    height=session.configuration.stealth.viewport.get("height", 1080),
                    device_scale_factor=session.configuration.stealth.viewport.get("device_scale_factor", 1.0),
                    is_mobile=session.configuration.stealth.viewport.get("is_mobile", False),
                    has_touch=session.configuration.stealth.viewport.get("has_touch", False)
                ),
                expires_at=time.time() + (self.default_ttl_hours * 3600),
                schema_version=self.schema_version
            )
            
            return browser_state
            
        except Exception as e:
            self.logger.error(
                "Failed to extract state from session",
                session_id=session.session_id,
                error=str(e)
            )
            raise BrowserStateError(
                "state_extraction_failed",
                f"Failed to extract state from session: {e}"
            )
