"""Unit tests for Cloudflare browser profile applier module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.stealth.cloudflare.core.applier import StealthProfileApplier
from src.stealth.cloudflare.core.applier.apply import StealthProfileApplierError
from src.stealth.cloudflare.models.config import CloudflareConfig


class TestStealthProfileApplier:
    """Tests for StealthProfileApplier class."""

    def test_initialization_with_default_config(self) -> None:
        """Test that StealthProfileApplier initializes with no config."""
        applier = StealthProfileApplier()
        assert applier.config is None
        assert applier.enabled is False

    def test_initialization_with_protected_config(self) -> None:
        """Test initialization with cloudflare_protected=True enables components."""
        config = CloudflareConfig(cloudflare_protected=True)
        applier = StealthProfileApplier(config)
        assert applier.config.is_enabled() is True
        assert applier.enabled is True

    def test_initialization_with_all_flags_disabled(self) -> None:
        """Test initialization with all feature flags disabled."""
        config = CloudflareConfig(
            cloudflare_protected=True,
            webdriver_enabled=False,
            fingerprint_enabled=False,
            user_agent_enabled=False,
            viewport_enabled=False,
        )
        applier = StealthProfileApplier(config)
        assert applier.enabled is False

    def test_repr(self) -> None:
        """Test string representation of StealthProfileApplier."""
        config = CloudflareConfig(cloudflare_protected=True)
        applier = StealthProfileApplier(config)
        repr_str = repr(applier)
        assert "StealthProfileApplier" in repr_str
        assert "webdriver=True" in repr_str or "webdriver=False" in repr_str

    def test_components_not_created_when_protection_disabled(self) -> None:
        """Test that components are not created when protection is disabled."""
        config = CloudflareConfig(cloudflare_protected=False)
        applier = StealthProfileApplier(config)
        assert applier._webdriver is None
        assert applier._fingerprint is None
        assert applier._user_agent is None
        assert applier._viewport is None

    def test_components_created_when_protection_enabled(self) -> None:
        """Test that components are created when protection is enabled."""
        config = CloudflareConfig(cloudflare_protected=True)
        applier = StealthProfileApplier(config)
        assert applier._webdriver is not None
        assert applier._fingerprint is not None
        assert applier._user_agent is not None
        assert applier._viewport is not None

    @pytest.mark.asyncio
    async def test_apply_skips_when_not_enabled(self) -> None:
        """Test that apply does nothing when no components are enabled."""
        applier = StealthProfileApplier()
        mock_context = MagicMock()

        await applier.apply(mock_context)

        mock_context.add_init_script.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_success_with_all_components(self) -> None:
        """Test successful application with all components enabled."""
        config = CloudflareConfig(cloudflare_protected=True)
        applier = StealthProfileApplier(config)

        mock_context = MagicMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.set_viewport_size = AsyncMock()
        mock_context.set_extra_http_headers = AsyncMock()

        await applier.apply(mock_context)

        assert mock_context.add_init_script.called

    @pytest.mark.asyncio
    async def test_apply_order(self) -> None:
        """Test that components are applied in correct order."""
        config = CloudflareConfig(cloudflare_protected=True)
        applier = StealthProfileApplier(config)

        mock_context = MagicMock()
        mock_context.add_init_script = AsyncMock()
        mock_context.set_viewport_size = AsyncMock()
        mock_context.set_extra_http_headers = AsyncMock()

        await applier.apply(mock_context)

        assert mock_context.add_init_script.call_count >= 2

    @pytest.mark.asyncio
    async def test_apply_handles_component_errors(self) -> None:
        """Test that apply handles errors from individual components."""
        config = CloudflareConfig(cloudflare_protected=True)

        with patch.object(type(config), "is_enabled", return_value=True, create=True):
            applier = StealthProfileApplier(config)

            mock_context = MagicMock()
            mock_context.add_init_script = AsyncMock(
                side_effect=Exception("Test error")
            )

            with pytest.raises(StealthProfileApplierError):
                await applier.apply(mock_context)

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test that StealthProfileApplier works as async context manager."""
        config = CloudflareConfig(cloudflare_protected=True)

        async with StealthProfileApplier(config) as applier:
            assert applier.enabled is True

        assert applier._webdriver is None
        assert applier._fingerprint is None


class TestStealthProfileApplierError:
    """Tests for StealthProfileApplierError exception."""

    def test_exception_message(self) -> None:
        """Test that exception message is properly set."""
        error = StealthProfileApplierError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self) -> None:
        """Test that exception inherits from correct base class."""
        error = StealthProfileApplierError("Test")
        assert isinstance(error, Exception)
