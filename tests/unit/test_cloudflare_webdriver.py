"""Unit tests for Cloudflare webdriver automation signal suppression module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.stealth.cloudflare.core.webdriver import WebdriverMasker
from src.stealth.cloudflare.exceptions import WebdriverMaskerError


class TestWebdriverMasker:
    """Tests for WebdriverMasker class."""

    def test_initialization(self) -> None:
        """Test that WebdriverMasker initializes with correct defaults."""
        masker = WebdriverMasker()
        assert masker.enabled is False
        assert masker.applied_count == 0

    def test_repr(self) -> None:
        """Test string representation of WebdriverMasker."""
        masker = WebdriverMasker()
        assert "WebdriverMasker" in repr(masker)
        assert "enabled=False" in repr(masker)
        assert "applied_count=0" in repr(masker)

    def test_repr_after_apply(self) -> None:
        """Test string representation after application."""
        masker = WebdriverMasker()
        # Simulate apply by directly setting the internal state
        masker._enabled = True
        masker._applied_count = 1
        assert "enabled=True" in repr(masker)
        assert "applied_count=1" in repr(masker)

    def test_get_suppression_script(self) -> None:
        """Test that suppression script is returned correctly."""
        masker = WebdriverMasker()
        script = masker.get_suppression_script()
        assert isinstance(script, str)
        assert len(script) > 0
        assert "navigator.webdriver" in script
        assert "$cdc_adoQpoasnfa76pfcZLmcfl_Array" in script

    def test_suppression_script_contains_key_elements(self) -> None:
        """Test that suppression script contains all key automation signals."""
        masker = WebdriverMasker()
        script = masker.get_suppression_script()

        # Check for navigator.webdriver suppression
        assert "navigator.webdriver" in script

        # Check for CDC property masks
        assert "$cdc_adoQpoasnfa76pfcZLmcfl_Array" in script
        assert "$cdc_adoQpoasnfa76pfcZLmcfl_Object" in script
        assert "$cdc_adoQpoasnfa76pfcZLmcfl_Promise" in script
        assert "$cdc_adoQpoasnfa76pfcZLmcfl_Symbol" in script

        # Check for Chrome runtime override
        assert "chrome.runtime" in script

    @pytest.mark.asyncio
    async def test_apply_with_disabled_flag(self) -> None:
        """Test that apply does nothing when disabled."""
        masker = WebdriverMasker()
        mock_context = MagicMock()

        await masker.apply(mock_context, enabled=False)

        # add_init_script should not be called
        mock_context.add_init_script.assert_not_called()
        assert masker.enabled is False

    @pytest.mark.asyncio
    async def test_apply_success(self) -> None:
        """Test successful application of suppression script."""
        masker = WebdriverMasker()
        mock_context = MagicMock()
        mock_context.add_init_script = AsyncMock()

        await masker.apply(mock_context, enabled=True)

        # Verify add_init_script was called with the suppression script
        mock_context.add_init_script.assert_called_once()
        call_args = mock_context.add_init_script.call_args
        assert masker.SUPPRESSION_SCRIPT in call_args[0]

        # Verify state was updated
        assert masker.enabled is True
        assert masker.applied_count == 1

    @pytest.mark.asyncio
    async def test_apply_multiple_contexts(self) -> None:
        """Test applying masker to multiple contexts."""
        masker = WebdriverMasker()

        mock_context1 = MagicMock()
        mock_context1.add_init_script = AsyncMock()

        mock_context2 = MagicMock()
        mock_context2.add_init_script = AsyncMock()

        await masker.apply(mock_context1, enabled=True)
        await masker.apply(mock_context2, enabled=True)

        assert masker.applied_count == 2
        assert masker.enabled is True

    @pytest.mark.asyncio
    async def test_apply_raises_on_invalid_context(self) -> None:
        """Test that apply raises TypeError on invalid context."""
        masker = WebdriverMasker()

        # Context without add_init_script method
        mock_context = MagicMock(spec=[])  # Empty spec means no methods

        with pytest.raises(TypeError, match="add_init_script"):
            await masker.apply(mock_context, enabled=True)

    @pytest.mark.asyncio
    async def test_remove_logs_request(self) -> None:
        """Test that remove logs the request (actual removal not supported)."""
        masker = WebdriverMasker()
        masker._enabled = True
        mock_context = MagicMock()

        await masker.remove(mock_context)

        # Note: enabled state remains as init scripts can't be removed
        assert masker.enabled is True

    def test_reset_state(self) -> None:
        """Test reset_state method."""
        masker = WebdriverMasker()
        masker._enabled = True
        masker._applied_count = 5

        masker.reset_state()

        assert masker.enabled is False
        assert masker.applied_count == 0


class TestWebdriverMaskerScript:
    """Tests for the suppression script content."""

    def test_script_is_iife(self) -> None:
        """Test that script is wrapped in an IIFE."""
        masker = WebdriverMasker()
        script = masker.get_suppression_script()

        # Should start with (function() {
        assert "(function()" in script
        # Should end with })();
        assert "})();" in script

    def test_script_defines_navigator_webdriver(self) -> None:
        """Test that script properly defines navigator.webdriver."""
        masker = WebdriverMasker()
        script = masker.get_suppression_script()

        assert "Object.defineProperty(navigator, 'webdriver'" in script
        assert "get: function() { return undefined; }" in script

    def test_script_handles_automation_props(self) -> None:
        """Test that script handles automation properties correctly."""
        masker = WebdriverMasker()
        script = masker.get_suppression_script()

        assert "automationProps" in script
        assert "forEach" in script
        assert "hasOwnProperty" in script
        assert "delete" in script
