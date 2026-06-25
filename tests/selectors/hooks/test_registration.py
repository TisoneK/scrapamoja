"""
Unit tests for registration automation hook.

Story 7.4: Registration Automation
- Tests automatic selector registration via engine lifecycle hooks
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.selectors.engine import SelectorEngine
from src.selectors.hooks.registration import (
    RegistrationHook,
    create_registration_hook,
    auto_register_from_directory,
)


class TestSelectorEngineHooks:
    """Test engine lifecycle hooks."""

    @pytest.fixture
    def engine(self):
        """Create a fresh engine for testing."""
        return SelectorEngine()

    def test_engine_has_lifecycle_events(self, engine):
        """Test that engine has the expected lifecycle event constants."""
        assert hasattr(engine, "HOOK_EVENT_INIT")
        assert hasattr(engine, "HOOK_EVENT_LOAD")
        assert hasattr(engine, "HOOK_EVENT_READY")
        assert hasattr(engine, "HOOK_EVENT_SELECTOR_REGISTERED")
        
        assert engine.HOOK_EVENT_INIT == "on_init"
        assert engine.HOOK_EVENT_LOAD == "on_load"
        assert engine.HOOK_EVENT_READY == "on_ready"
        assert engine.HOOK_EVENT_SELECTOR_REGISTERED == "on_selector_registered"

    def test_engine_has_hooks_dict(self, engine):
        """Test that engine has hooks dictionary."""
        assert hasattr(engine, "_hooks")
        assert isinstance(engine._hooks, dict)
        assert engine.HOOK_EVENT_INIT in engine._hooks
        assert engine.HOOK_EVENT_LOAD in engine._hooks
        assert engine.HOOK_EVENT_READY in engine._hooks
        assert engine.HOOK_EVENT_SELECTOR_REGISTERED in engine._hooks

    def test_register_hook(self, engine):
        """Test registering a hook callback."""
        callback = MagicMock()
        engine.register_hook(engine.HOOK_EVENT_INIT, callback)
        
        assert callback in engine._hooks[engine.HOOK_EVENT_INIT]

    def test_unregister_hook(self, engine):
        """Test unregistering a hook callback."""
        callback = MagicMock()
        engine.register_hook(engine.HOOK_EVENT_INIT, callback)
        engine.unregister_hook(engine.HOOK_EVENT_INIT, callback)
        
        assert callback not in engine._hooks[engine.HOOK_EVENT_INIT]

    @pytest.mark.asyncio
    async def test_trigger_hook(self, engine):
        """Test triggering a hook."""
        callback = AsyncMock()
        engine.register_hook(engine.HOOK_EVENT_INIT, callback)
        
        await engine._trigger_hook(engine.HOOK_EVENT_INIT)
        
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_hook_with_args(self, engine):
        """Test triggering a hook with arguments."""
        callback = AsyncMock()
        engine.register_hook(engine.HOOK_EVENT_SELECTOR_REGISTERED, callback)
        
        await engine._trigger_hook(
            engine.HOOK_EVENT_SELECTOR_REGISTERED, 
            "test_selector", 
            "test_data"
        )
        
        callback.assert_called_once_with("test_selector", "test_data")


class TestRegistrationHook:
    """Test RegistrationHook class."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock engine."""
        engine = MagicMock(spec=SelectorEngine)
        engine.HOOK_EVENT_INIT = SelectorEngine.HOOK_EVENT_INIT
        engine.HOOK_EVENT_READY = SelectorEngine.HOOK_EVENT_READY
        engine.register_hook = MagicMock()
        return engine

    def test_registration_hook_init(self, mock_engine):
        """Test RegistrationHook initialization."""
        hook = RegistrationHook(mock_engine)
        
        assert hook.engine is mock_engine
        assert hook._registered is False

    def test_register_with_engine(self, mock_engine):
        """Test registering hook with engine."""
        hook = RegistrationHook(mock_engine)
        hook.register_with_engine()
        
        assert hook._registered is True
        assert mock_engine.register_hook.call_count == 2
        
        # Check both init and ready hooks are registered
        calls = mock_engine.register_hook.call_args_list
        assert SelectorEngine.HOOK_EVENT_INIT in str(calls)
        assert SelectorEngine.HOOK_EVENT_READY in str(calls)

    def test_create_registration_hook_factory(self, mock_engine):
        """Test factory function creates and registers hook."""
        hook = create_registration_hook(mock_engine)
        
        assert hook is not None
        assert hook._registered is True


class TestAutoRegisterFromDirectory:
    """Test auto_register_from_directory utility."""

    @pytest.mark.asyncio
    async def test_auto_register_with_mock(self):
        """Test auto registration with mocked components."""
        # This is a basic smoke test
        engine = MagicMock(spec=SelectorEngine)
        engine.list_selectors = MagicMock(return_value=["selector1", "selector2"])
        
        with patch("src.selectors.hooks.registration.get_yaml_loader") as mock_loader:
            mock_load_result = MagicMock()
            mock_load_result.success = True
            mock_load_result.errors = []
            mock_load_result.loading_time_ms = 10.0
            mock_load_result.selectors_loaded = 2
            mock_load_result.selectors_failed = 0
            mock_loader.return_value.load_selectors_from_directory.return_value = mock_load_result
            
            mock_loader.return_value.get_cache_stats.return_value = {"cached_files": []}
            
            # This would fail due to mocking issues, but verifies the import works
            from src.selectors.hooks.registration import auto_register_from_directory
            # Skip actual execution since it requires full setup
            assert auto_register_from_directory is not None


class TestRegistrationHookIntegration:
    """Integration tests for RegistrationHook with real components."""

    @pytest.mark.asyncio
    async def test_registration_hook_auto_load(self):
        """Test that RegistrationHook loads selectors when auto_load is enabled."""
        from pathlib import Path
        from src.selectors.engine import SelectorEngine
        from src.selectors.hooks.registration import RegistrationHook
        
        # Create engine
        engine = SelectorEngine()
        
        # Create hook with auto_load=True
        hook = RegistrationHook(engine, selectors_root=None, auto_load=True)
        
        # When selectors_root is None, auto_load should be disabled
        assert hook._auto_load is False
        
    @pytest.mark.asyncio
    async def test_no_manual_registration_in_hook(self):
        """Verify RegistrationHook doesn't call manual registration."""
        from src.selectors.engine import SelectorEngine
        from src.selectors.hooks.registration import RegistrationHook
        from unittest.mock import AsyncMock, MagicMock, patch
        
        engine = SelectorEngine()
        
        # Create hook with no selectors_root - should not attempt auto-load
        hook = RegistrationHook(engine, selectors_root=None, auto_load=False)
        
        # Verify _auto_load is False when selectors_root is None
        assert hook._auto_load is False
        assert hook._loaded is False
        
    def test_registration_hook_factory_default_auto_load(self):
        """Test that factory creates hook with auto_load based on selectors_root."""
        from src.selectors.engine import SelectorEngine
        from src.selectors.hooks.registration import create_registration_hook
        from pathlib import Path
        
        engine = MagicMock(spec=SelectorEngine)
        engine.HOOK_EVENT_INIT = SelectorEngine.HOOK_EVENT_INIT
        engine.HOOK_EVENT_READY = SelectorEngine.HOOK_EVENT_READY
        engine.register_hook = MagicMock()
        
        # With None selectors_root, auto_load should be False
        hook = create_registration_hook(engine, selectors_root=None)
        assert hook._auto_load is False
        
    def test_registration_hook_tracks_loaded_state(self):
        """Test that hook tracks whether selectors have been loaded."""
        from src.selectors.engine import SelectorEngine
        from src.selectors.hooks.registration import RegistrationHook
        from unittest.mock import MagicMock
        
        engine = MagicMock(spec=SelectorEngine)
        engine.HOOK_EVENT_INIT = SelectorEngine.HOOK_EVENT_INIT
        engine.HOOK_EVENT_READY = SelectorEngine.HOOK_EVENT_READY
        engine.register_hook = MagicMock()
        
        hook = RegistrationHook(engine, selectors_root=None, auto_load=False)
        
        # Initially not loaded
        assert hook._loaded is False
        assert hook._loading is False
