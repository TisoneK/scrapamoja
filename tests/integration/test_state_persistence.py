"""
State Persistence Integration Tests

Integration tests for browser state persistence functionality.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.browser.models.state import BrowserState, CookieData, ViewportSettings
from src.browser.state import StateManager
from src.browser import BrowserSession
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


class TestStateManagerIntegration:
    """Integration tests for StateManager."""
    
    @pytest.fixture
    async def temp_storage_dir(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    async def state_manager(self, temp_storage_dir):
        """Create StateManager instance."""
        return StateManager(str(temp_storage_dir))
        
    @pytest.fixture
    async def encrypted_state_manager(self, temp_storage_dir):
        """Create StateManager with encryption."""
        return StateManager(str(temp_storage_dir), encryption_key="test_key_123")
        
    @pytest.fixture
    async def sample_browser_state(self):
        """Create sample browser state."""
        cookies = [
            CookieData(
                name="session_id",
                value="abc123",
                domain="example.com"
            ),
            CookieData(
                name="auth_token", 
                value="token456",
                domain="example.com",
                secure=True
            )
        ]
        
        local_storage = {
            "theme": "dark",
            "language": "en-US",
            "user_preferences": json.dumps({"notifications": True})
        }
        
        session_storage = {
            "current_page": "dashboard",
            "last_action": str(time.time())
        }
        
        return BrowserState(
            state_id="test_state_1",
            session_id="test_session_1",
            cookies=cookies,
            local_storage=local_storage,
            session_storage=session_storage,
            user_agent="Mozilla/5.0 Test Browser",
            viewport=ViewportSettings(width=1920, height=1080)
        )
        
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, state_manager, sample_browser_state):
        """Test basic save and load functionality."""
        # Save state
        state_id = await state_manager.save_state(Mock(), sample_browser_state.state_id)
        
        # Verify file exists
        assert (state_manager.storage_dir / f"{state_id}.json").exists()
        
        # Load state
        loaded_state = await state_manager.load_state(state_id)
        
        # Verify loaded state
        assert loaded_state is not None
        assert loaded_state.state_id == sample_browser_state.state_id
        assert loaded_state.session_id == sample_browser_state.session_id
        assert len(loaded_state.cookies) == len(sample_browser_state.cookies)
        assert loaded_state.local_storage == sample_browser_state.local_storage
        assert loaded_state.session_storage == sample_browser_state.session_storage
        
    @pytest.mark.asyncio
    async def test_save_and_load_encrypted_state(self, encrypted_state_manager, sample_browser_state):
        """Test encrypted save and load functionality."""
        # Save state
        state_id = await encrypted_state_manager.save_state(Mock(), sample_browser_state.state_id)
        
        # Verify encrypted file exists
        assert (encrypted_state_manager.storage_dir / f"{state_id}.encrypted").exists()
        
        # Load state
        loaded_state = await encrypted_state_manager.load_state(state_id)
        
        # Verify loaded state
        assert loaded_state is not None
        assert loaded_state.state_id == sample_browser_state.state_id
        assert loaded_state.cookies == sample_browser_state.cookies
        
    @pytest.mark.asyncio
    async def test_list_states(self, state_manager, sample_browser_state):
        """Test listing saved states."""
        # Save multiple states
        state_ids = []
        for i in range(3):
            state_id = await state_manager.save_state(Mock(), f"test_state_{i}")
            state_ids.append(state_id)
            
        # List all states
        all_states = await state_manager.list_states()
        assert len(all_states) >= 3
        
        # List states for specific session
        session_states = await state_manager.list_states("test_session_1")
        assert len(session_states) >= 3
        
    @pytest.mark.asyncio
    async def test_delete_state(self, state_manager, sample_browser_state):
        """Test state deletion."""
        # Save state
        state_id = await state_manager.save_state(Mock(), sample_browser_state.state_id)
        
        # Verify file exists
        assert (state_manager.storage_dir / f"{state_id}.json").exists()
        
        # Delete state
        result = await state_manager.delete_state(state_id)
        assert result is True
        
        # Verify file is deleted
        assert not (state_manager.storage_dir / f"{state_id}.json").exists()
        
    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, state_manager, sample_browser_state):
        """Test cleanup of expired states."""
        # Create state with short expiration
        expired_state = BrowserState(
            state_id="expired_state",
            session_id="test_session",
            expires_at=time.time() - 3600  # Expired 1 hour ago
        )
        
        # Save expired state
        expired_id = await state_manager.save_state(Mock(), expired_state.state_id)
        
        # Save valid state
        valid_id = await state_manager.save_state(Mock(), sample_browser_state.state_id)
        
        # Cleanup expired states
        deleted_count = await state_manager.cleanup_expired_states()
        assert deleted_count >= 1
        
        # Verify expired state is deleted
        assert not await state_manager.load_state(expired_id)
        
        # Verify valid state still exists
        assert await state_manager.load_state(valid_id) is not None


class TestStateEncryptionIntegration:
    """Integration tests for StateEncryption."""
    
    @pytest.fixture
    def encryption(self):
        """Create StateEncryption instance."""
        return StateEncryption("test_encryption_key_123")
        
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_authentication_tokens(self, encryption):
        """Test encryption and decryption of authentication tokens."""
        tokens = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "def5020032b3a4c5d6e7f8...",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        # Encrypt tokens
        encrypted_data = encryption.encrypt_authentication_tokens(tokens)
        assert encrypted_data is not None
        assert isinstance(encrypted_data, bytes)
        
        # Decrypt tokens
        decrypted_tokens = encryption.decrypt_authentication_tokens(encrypted_data)
        assert decrypted_tokens == tokens
        
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_cookies(self, encryption):
        """Test encryption and decryption of cookies."""
        cookies = [
            {
                "name": "session_id",
                "value": "abc123",
                "domain": "example.com",
                "path": "/",
                "secure": False,
                "httpOnly": True
            },
            {
                "name": "user_pref",
                "value": "dark_mode",
                "domain": ".example.com",
                "path": "/settings",
                "secure": True,
                "httpOnly": False
            }
        ]
        
        # Encrypt cookies
        encrypted_data = encryption.encrypt_cookies(cookies)
        assert encrypted_data is not None
        
        # Decrypt cookies
        decrypted_cookies = encryption.decrypt_cookies(encrypted_data)
        assert decrypted_cookies == cookies
        
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_storage_data(self, encryption):
        """Test encryption and decryption of storage data."""
        storage_data = {
            "theme": "dark",
            "language": "en-US",
            "user_id": "12345",
            "preferences": json.dumps({"notifications": True, "auto_save": False})
        }
        
        # Encrypt local storage
        encrypted_local = encryption.encrypt_storage_data(storage_data, "local")
        decrypted_local, storage_type = encryption.decrypt_storage_data(encrypted_local)
        assert decrypted_local == storage_data
        assert storage_type == "local"
        
        # Encrypt session storage
        encrypted_session = encryption.encrypt_storage_data(storage_data, "session")
        decrypted_session, storage_type = encryption.decrypt_storage_data(encrypted_session)
        assert decrypted_session == storage_data
        assert storage_type == "session"
        
    @pytest.mark.asyncio
    async def test_secure_hash_and_integrity(self, encryption):
        """Test secure hash creation and integrity verification."""
        data = {
            "user_id": "12345",
            "session_data": "sensitive_info",
            "timestamp": time.time()
        }
        
        # Create hash
        hash_value = encryption.create_secure_hash(data)
        assert hash_value is not None
        assert isinstance(hash_value, str)
        
        # Verify integrity
        is_valid = encryption.verify_integrity(data, hash_value)
        assert is_valid is True
        
        # Modify data and verify integrity fails
        modified_data = data.copy()
        modified_data["user_id"] = "67890"
        
        is_valid_modified = encryption.verify_integrity(modified_data, hash_value)
        assert is_valid_modified is False


class TestCorruptionDetectorIntegration:
    """Integration tests for StateCorruptionDetector."""
    
    @pytest.fixture
    async def temp_storage_dir(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def corruption_detector(self, temp_storage_dir):
        """Create StateCorruptionDetector instance."""
        return StateCorruptionDetector(str(temp_storage_dir))
        
    @pytest.mark.asyncio
    async def test_analyze_valid_state(self, corruption_detector, temp_storage_dir):
        """Test analysis of valid state."""
        # Create valid state file
        valid_state = {
            "state_id": "valid_state",
            "session_id": "test_session",
            "schema_version": "1.0.0",
            "cookies": [
                {
                    "name": "test_cookie",
                    "value": "test_value",
                    "domain": "example.com"
                }
            ],
            "local_storage": {"key": "value"},
            "created_at": time.time()
        }
        
        state_file = temp_storage_dir / "valid_state.json"
        with open(state_file, 'w') as f:
            json.dump(valid_state, f)
            
        # Analyze state
        report = await corruption_detector.analyze_state("valid_state")
        
        assert report.is_corrupted is False
        assert report.corruption_type is None
        assert report.recoverable is True
        
    @pytest.mark.asyncio
    async def test_analyze_corrupted_state(self, corruption_detector, temp_storage_dir):
        """Test analysis of corrupted state."""
        # Create corrupted state file (missing required fields)
        corrupted_state = {
            "state_id": "corrupted_state",
            # Missing session_id and schema_version
            "cookies": "invalid_format"  # Should be list
        }
        
        state_file = temp_storage_dir / "corrupted_state.json"
        with open(state_file, 'w') as f:
            json.dump(corrupted_state, f)
            
        # Analyze state
        report = await corruption_detector.analyze_state("corrupted_state")
        
        assert report.is_corrupted is True
        assert report.corruption_type == "structure_corruption"
        assert report.recoverable is True
        assert len(report.recovery_suggestions) > 0
        
    @pytest.mark.asyncio
    async def test_repair_corrupted_state(self, corruption_detector, temp_storage_dir):
        """Test repair of corrupted state."""
        # Create corrupted state
        corrupted_state = {
            "state_id": "repairable_state",
            # Missing required fields for corruption
            "cookies": [
                {
                    "name": "valid_cookie",
                    "value": "valid_value",
                    "domain": "example.com"
                },
                {
                    # Invalid cookie missing required fields
                    "name": "invalid_cookie"
                }
            ]
        }
        
        state_file = temp_storage_dir / "repairable_state.json"
        with open(state_file, 'w') as f:
            json.dump(corrupted_state, f)
            
        # Repair state
        repaired_state = await corruption_detector.repair_state("repairable_state", "clean")
        
        assert repaired_state is not None
        assert repaired_state.state_id == "repairable_state"
        assert len(repaired_state.cookies) == 1  # Only valid cookie should remain
        
    @pytest.mark.asyncio
    async def test_create_and_restore_backup(self, corruption_detector, temp_storage_dir):
        """Test backup creation and restoration."""
        # Create original state
        original_state = {
            "state_id": "backup_test_state",
            "session_id": "test_session",
            "schema_version": "1.0.0",
            "cookies": [{"name": "backup_cookie", "value": "backup_value", "domain": "example.com"}],
            "created_at": time.time()
        }
        
        state_file = temp_storage_dir / "backup_test_state.json"
        with open(state_file, 'w') as f:
            json.dump(original_state, f)
            
        # Create backup
        backup_id = await corruption_detector.create_backup("backup_test_state")
        
        assert backup_id is not None
        assert backup_id != "backup_test_state"
        assert (temp_storage_dir / f"{backup_id}.json").exists()
        
        # Modify original state
        original_state["cookies"][0]["value"] = "modified_value"
        with open(state_file, 'w') as f:
            json.dump(original_state, f)
            
        # Restore from backup
        restored_state = await corruption_detector._restore_from_backup("backup_test_state")
        
        assert restored_state is not None
        assert restored_state.cookies[0]["value"] == "backup_value"  # Should be original value


class TestStateLoggerIntegration:
    """Integration tests for StateLogger."""
    
    @pytest.fixture
    def state_logger(self):
        """Create StateLogger instance."""
        return get_state_logger()
        
    @pytest.mark.asyncio
    async def test_log_save_operation(self, state_logger):
        """Test logging of save operation."""
        # Log successful save
        state_logger.log_save_operation(
            session_id="test_session",
            state_id="test_state",
            success=True,
            file_path="/path/to/state.json",
            encrypted=False,
            cookie_count=5,
            storage_items=10,
            file_size_bytes=1024
        )
        
        # Log failed save
        state_logger.log_save_operation(
            session_id="test_session",
            state_id="test_state",
            success=False,
            error="Disk full",
            correlation_id="test_correlation_123"
        )
        
        # Verify operations were logged
        active_ops = state_logger.get_active_operations()
        # Operations should be completed and removed from active list
        assert len(active_ops) == 0
        
    @pytest.mark.asyncio
    async def test_log_load_operation(self, state_logger):
        """Test logging of load operation."""
        # Log successful load
        state_logger.log_load_operation(
            state_id="test_state",
            success=True,
            session_id="test_session",
            encrypted=True,
            cookie_count=3,
            storage_items=7,
            validation_issues=["minor_issue"]
        )
        
        # Log failed load
        state_logger.log_load_operation(
            state_id="test_state",
            success=False,
            error="File corrupted",
            correlation_id="test_correlation_456"
        )
        
    @pytest.mark.asyncio
    async def test_operation_context_tracking(self, state_logger):
        """Test operation context tracking."""
        # Start operation
        context = state_logger.start_operation(
            StateOperation.SAVE,
            session_id="test_session",
            state_id="test_state",
            correlation_id="test_correlation_789"
        )
        
        assert context.operation_id is not None
        assert context.status.value == "started"
        
        # Update operation
        updated_context = state_logger.update_operation(
            context.operation_id,
            metadata={"progress": 50}
        )
        
        assert updated_context is not None
        assert updated_context.metadata["progress"] == 50
        
        # Complete operation
        completed_context = state_logger.complete_operation(
            context.operation_id,
            success=True
        )
        
        assert completed_context is not None
        assert completed_context.status.value == "completed"
        assert completed_context.duration_ms is not None


class TestStateErrorHandlerIntegration:
    """Integration tests for StateErrorHandler."""
    
    @pytest.fixture
    async def temp_storage_dir(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def error_handler(self, temp_storage_dir):
        """Create StateErrorHandler instance."""
        return StateErrorHandler(str(temp_storage_dir))
        
    @pytest.mark.asyncio
    async def test_handle_save_error_with_recovery(self, error_handler, temp_storage_dir):
        """Test error handling with recovery for save operations."""
        session_id = "test_session"
        state_id = "test_state"
        state_data = {"test": "data"}
        
        # Simulate file not found error (should create new)
        file_not_found_error = FileNotFoundError("No such file or directory")
        
        result = await error_handler.handle_save_error(
            file_not_found_error,
            session_id,
            state_id,
            state_data
        )
        
        # Should recover by creating new file
        assert result is True
        
    @pytest.mark.asyncio
    async def test_handle_load_error_with_recovery(self, error_handler, temp_storage_dir):
        """Test error handling with recovery for load operations."""
        state_id = "nonexistent_state"
        
        # Simulate file not found error
        file_not_found_error = FileNotFoundError("No such file or directory")
        
        result = await error_handler.handle_load_error(
            file_not_found_error,
            state_id
        )
        
        # Should return None for nonexistent file
        assert result is None
        
    @pytest.mark.asyncio
    async def test_error_classification(self, error_handler):
        """Test error classification."""
        # Test file not found
        file_error = FileNotFoundError("File not found")
        context = error_handler._create_error_context(
            file_error, "session", "state", StateOperation.LOAD
        )
        assert context.error_type.value == "file_not_found"
        
        # Test permission error
        perm_error = PermissionError("Permission denied")
        context = error_handler._create_error_context(
            perm_error, "session", "state", StateOperation.SAVE
        )
        assert context.error_type.value == "permission_denied"
        
        # Test unknown error
        unknown_error = ValueError("Unknown error")
        context = error_handler._create_error_context(
            unknown_error, "session", "state", StateOperation.DELETE
        )
        assert context.error_type.value == "unknown_error"
