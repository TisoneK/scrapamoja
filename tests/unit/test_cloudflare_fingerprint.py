"""Unit tests for Cloudflare fingerprint randomization module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.stealth.cloudflare.core.fingerprint import (
    CanvasFingerprintRandomizer,
    WebGLSpoofer,
)
from src.stealth.cloudflare.exceptions import FingerprintRandomizerError


class TestCanvasFingerprintRandomizer:
    """Tests for CanvasFingerprintRandomizer class."""

    def test_initialization(self) -> None:
        """Test that CanvasFingerprintRandomizer initializes with correct defaults."""
        randomizer = CanvasFingerprintRandomizer()
        assert randomizer.enabled is False
        assert randomizer.applied_count == 0

    def test_repr(self) -> None:
        """Test string representation of CanvasFingerprintRandomizer."""
        randomizer = CanvasFingerprintRandomizer()
        assert "CanvasFingerprintRandomizer" in repr(randomizer)
        assert "enabled=False" in repr(randomizer)
        assert "applied_count=0" in repr(randomizer)

    def test_repr_after_apply(self) -> None:
        """Test string representation after application."""
        randomizer = CanvasFingerprintRandomizer()
        # Simulate apply by directly setting the internal state
        randomizer._enabled = True
        randomizer._applied_count = 1
        assert "enabled=True" in repr(randomizer)
        assert "applied_count=1" in repr(randomizer)

    def test_get_randomization_script(self) -> None:
        """Test that randomization script is returned correctly."""
        randomizer = CanvasFingerprintRandomizer()
        script = randomizer.get_randomization_script()
        assert isinstance(script, str)
        assert len(script) > 0
        assert "HTMLCanvasElement.prototype.toDataURL" in script
        assert "getImageData" in script

    def test_randomization_script_contains_key_elements(self) -> None:
        """Test that randomization script contains all key elements."""
        randomizer = CanvasFingerprintRandomizer()
        script = randomizer.get_randomization_script()

        # Check for canvas method overrides
        assert "toDataURL" in script
        assert "toBlob" in script
        assert "getImageData" in script

        # Check for noise injection
        assert "Math.random" in script
        assert "noise" in script or "random" in script.lower()

    @pytest.mark.asyncio
    async def test_apply_with_disabled_flag(self) -> None:
        """Test that apply does nothing when disabled."""
        randomizer = CanvasFingerprintRandomizer()
        mock_context = MagicMock()

        await randomizer.apply(mock_context, enabled=False)

        # add_init_script should not be called
        mock_context.add_init_script.assert_not_called()
        assert randomizer.enabled is False

    @pytest.mark.asyncio
    async def test_apply_success(self) -> None:
        """Test successful application of randomization script."""
        randomizer = CanvasFingerprintRandomizer()
        mock_context = MagicMock()
        mock_context.add_init_script = AsyncMock()

        await randomizer.apply(mock_context, enabled=True)

        # Verify add_init_script was called with the randomization script
        mock_context.add_init_script.assert_called_once()
        call_args = mock_context.add_init_script.call_args
        assert randomizer.CANVAS_RANDOMIZATION_SCRIPT in call_args[0]

        # Verify state was updated
        assert randomizer.enabled is True
        assert randomizer.applied_count == 1

    @pytest.mark.asyncio
    async def test_apply_multiple_contexts(self) -> None:
        """Test applying randomizer to multiple contexts."""
        randomizer = CanvasFingerprintRandomizer()

        mock_context1 = MagicMock()
        mock_context1.add_init_script = AsyncMock()

        mock_context2 = MagicMock()
        mock_context2.add_init_script = AsyncMock()

        await randomizer.apply(mock_context1, enabled=True)
        await randomizer.apply(mock_context2, enabled=True)

        assert randomizer.applied_count == 2
        assert randomizer.enabled is True

    @pytest.mark.asyncio
    async def test_apply_raises_on_invalid_context(self) -> None:
        """Test that apply raises FingerprintRandomizerError on invalid context."""
        randomizer = CanvasFingerprintRandomizer()

        # Context without add_init_script method
        mock_context = MagicMock(spec=[])  # Empty spec means no methods

        with pytest.raises(FingerprintRandomizerError, match="add_init_script"):
            await randomizer.apply(mock_context, enabled=True)

    def test_reset_state(self) -> None:
        """Test reset_state method."""
        randomizer = CanvasFingerprintRandomizer()
        randomizer._enabled = True
        randomizer._applied_count = 5

        randomizer.reset_state()

        assert randomizer.enabled is False
        assert randomizer.applied_count == 0

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test that CanvasFingerprintRandomizer works as async context manager."""
        async with CanvasFingerprintRandomizer() as randomizer:
            assert randomizer.enabled is False
            mock_context = MagicMock()
            mock_context.add_init_script = AsyncMock()
            await randomizer.apply(mock_context)
            assert randomizer.enabled is True
        # After exiting context, state should be reset
        assert randomizer.enabled is False
        assert randomizer.applied_count == 0


class TestCanvasFingerprintRandomizerScript:
    """Tests for the canvas randomization script content."""

    def test_script_is_iife(self) -> None:
        """Test that script is wrapped in an IIFE."""
        randomizer = CanvasFingerprintRandomizer()
        script = randomizer.get_randomization_script()

        # Should start with (function() {
        assert "(function()" in script
        # Should end with })();
        assert "})();" in script

    def test_script_overrides_toDataURL(self) -> None:
        """Test that script properly overrides toDataURL."""
        randomizer = CanvasFingerprintRandomizer()
        script = randomizer.get_randomization_script()

        assert "HTMLCanvasElement.prototype.toDataURL" in script
        assert "originalToDataURL" in script

    def test_script_overrides_toBlob(self) -> None:
        """Test that script properly overrides toBlob."""
        randomizer = CanvasFingerprintRandomizer()
        script = randomizer.get_randomization_script()

        assert "HTMLCanvasElement.prototype.toBlob" in script
        assert "originalToBlob" in script

    def test_script_adds_noise_to_pixels(self) -> None:
        """Test that script adds noise to pixel data."""
        randomizer = CanvasFingerprintRandomizer()
        script = randomizer.get_randomization_script()

        assert "getImageData" in script
        assert "putImageData" in script
        assert "Math.random" in script


class TestWebGLSpoofer:
    """Tests for WebGLSpoofer class."""

    def test_initialization(self) -> None:
        """Test that WebGLSpoofer initializes with correct defaults."""
        spoofer = WebGLSpoofer()
        assert spoofer.enabled is False
        assert spoofer.applied_count == 0
        assert spoofer.gpu_renderer == "ANGLE (NVIDIA GeForce RTX 3080)"
        assert spoofer.gpu_vendor == "NVIDIA Corporation"

    def test_initialization_custom_gpu(self) -> None:
        """Test that WebGLSpoofer initializes with custom GPU values."""
        spoofer = WebGLSpoofer(
            gpu_renderer="ANGLE (AMD Radeon RX 6800)",
            gpu_vendor="Advanced Micro Devices, Inc.",
        )
        assert spoofer.gpu_renderer == "ANGLE (AMD Radeon RX 6800)"
        assert spoofer.gpu_vendor == "Advanced Micro Devices, Inc."

    def test_repr(self) -> None:
        """Test string representation of WebGLSpoofer."""
        spoofer = WebGLSpoofer()
        assert "WebGLSpoofer" in repr(spoofer)
        assert "enabled=False" in repr(spoofer)
        assert "applied_count=0" in repr(spoofer)
        assert "NVIDIA GeForce RTX 3080" in repr(spoofer)

    def test_repr_after_apply(self) -> None:
        """Test string representation after application."""
        spoofer = WebGLSpoofer()
        # Simulate apply by directly setting the internal state
        spoofer._enabled = True
        spoofer._applied_count = 1
        assert "enabled=True" in repr(spoofer)
        assert "applied_count=1" in repr(spoofer)

    def test_get_spoofing_script(self) -> None:
        """Test that spoofing script is returned correctly."""
        spoofer = WebGLSpoofer()
        script = spoofer.get_spoofing_script()
        assert isinstance(script, str)
        assert len(script) > 0
        assert "WebGLRenderingContext.prototype.getParameter" in script
        assert "getExtension" in script

    def test_custom_gpu_in_script(self) -> None:
        """Test that custom GPU values are in the script."""
        spoofer = WebGLSpoofer(
            gpu_renderer="ANGLE (AMD Radeon RX 6800)",
            gpu_vendor="Advanced Micro Devices, Inc.",
        )
        script = spoofer.get_spoofing_script()
        assert "AMD Radeon RX 6800" in script
        assert "Advanced Micro Devices, Inc." in script

    @pytest.mark.asyncio
    async def test_apply_with_disabled_flag(self) -> None:
        """Test that apply does nothing when disabled."""
        spoofer = WebGLSpoofer()
        mock_context = MagicMock()

        await spoofer.apply(mock_context, enabled=False)

        # add_init_script should not be called
        mock_context.add_init_script.assert_not_called()
        assert spoofer.enabled is False

    @pytest.mark.asyncio
    async def test_apply_success(self) -> None:
        """Test successful application of spoofing script."""
        spoofer = WebGLSpoofer()
        mock_context = MagicMock()
        mock_context.add_init_script = AsyncMock()

        await spoofer.apply(mock_context, enabled=True)

        # Verify add_init_script was called
        mock_context.add_init_script.assert_called_once()

        # Verify state was updated
        assert spoofer.enabled is True
        assert spoofer.applied_count == 1

    @pytest.mark.asyncio
    async def test_apply_multiple_contexts(self) -> None:
        """Test applying spoofer to multiple contexts."""
        spoofer = WebGLSpoofer()

        mock_context1 = MagicMock()
        mock_context1.add_init_script = AsyncMock()

        mock_context2 = MagicMock()
        mock_context2.add_init_script = AsyncMock()

        await spoofer.apply(mock_context1, enabled=True)
        await spoofer.apply(mock_context2, enabled=True)

        assert spoofer.applied_count == 2
        assert spoofer.enabled is True

    @pytest.mark.asyncio
    async def test_apply_raises_on_invalid_context(self) -> None:
        """Test that apply raises FingerprintRandomizerError on invalid context."""
        spoofer = WebGLSpoofer()

        # Context without add_init_script method
        mock_context = MagicMock(spec=[])  # Empty spec means no methods

        with pytest.raises(FingerprintRandomizerError, match="add_init_script"):
            await spoofer.apply(mock_context, enabled=True)

    def test_reset_state(self) -> None:
        """Test reset_state method."""
        spoofer = WebGLSpoofer()
        spoofer._enabled = True
        spoofer._applied_count = 5

        spoofer.reset_state()

        assert spoofer.enabled is False
        assert spoofer.applied_count == 0

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test that WebGLSpoofer works as async context manager."""
        async with WebGLSpoofer() as spoofer:
            assert spoofer.enabled is False
            mock_context = MagicMock()
            mock_context.add_init_script = AsyncMock()
            await spoofer.apply(mock_context)
            assert spoofer.enabled is True
        # After exiting context, state should be reset
        assert spoofer.enabled is False
        assert spoofer.applied_count == 0


class TestWebGLSpooferScript:
    """Tests for the WebGL spoofing script content."""

    def test_script_is_iife(self) -> None:
        """Test that script is wrapped in an IIFE."""
        spoofer = WebGLSpoofer()
        script = spoofer.get_spoofing_script()

        # Should start with (function() {
        assert "(function()" in script
        # Should end with })();
        assert "})();" in script

    def test_script_overrides_getParameter(self) -> None:
        """Test that script properly overrides getParameter."""
        spoofer = WebGLSpoofer()
        script = spoofer.get_spoofing_script()

        assert "WebGLRenderingContext.prototype.getParameter" in script
        assert "originalGetParameter" in script

    def test_script_handles_webgl2(self) -> None:
        """Test that script handles WebGL2."""
        spoofer = WebGLSpoofer()
        script = spoofer.get_spoofing_script()

        assert "WebGL2RenderingContext" in script

    def test_script_spoofs_gpu_vendor(self) -> None:
        """Test that script spoofs GPU vendor."""
        spoofer = WebGLSpoofer()
        script = spoofer.get_spoofing_script()

        # Check for GPU_VENDOR parameter (37445)
        assert "37445" in script
        assert "NVIDIA Corporation" in script

    def test_script_spoofs_gpu_renderer(self) -> None:
        """Test that script spoofs GPU renderer."""
        spoofer = WebGLSpoofer()
        script = spoofer.get_spoofing_script()

        # Check for GPU_RENDERER parameter (37446)
        assert "37446" in script
        assert "NVIDIA GeForce RTX 3080" in script


class TestFingerprintIntegration:
    """Integration tests for fingerprint modules."""

    @pytest.mark.asyncio
    async def test_both_applied_together(self) -> None:
        """Test that both canvas and WebGL can be applied to same context."""
        canvas_randomizer = CanvasFingerprintRandomizer()
        webgl_spoofer = WebGLSpoofer()

        mock_context = MagicMock()
        mock_context.add_init_script = AsyncMock()

        # Apply both to the same context
        await canvas_randomizer.apply(mock_context)
        await webgl_spoofer.apply(mock_context)

        # Both should have been applied
        assert canvas_randomizer.enabled is True
        assert webgl_spoofer.enabled is True
        assert canvas_randomizer.applied_count == 1
        assert webgl_spoofer.applied_count == 1

        # add_init_script should have been called twice
        assert mock_context.add_init_script.call_count == 2
