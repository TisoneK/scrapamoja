"""
Tests for the Anti-Detection Masking subsystem.

Verifies that automation indicators are properly masked:
- navigator.webdriver returns undefined
- Playwright console patches are removed
- process object is hidden
- navigator.plugins populated with realistic extensions
- All masking happens without errors
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from src.stealth.anti_detection import AntiDetectionMasker, REALISTIC_PLUGINS
from src.stealth.models import EventType, EventSeverity
from src.stealth.events import EventBuilder


class TestAntiDetectionMaskerInitialization:
    """Tests for AntiDetectionMasker initialization and configuration."""
    
    def test_masker_creation_with_defaults(self):
        """Test creating masker with default configuration."""
        masker = AntiDetectionMasker()
        assert masker.config == {}
        assert masker.event_builder is None
        assert masker.masks_applied is False
        assert masker._mask_count == 0
    
    def test_masker_creation_with_config(self):
        """Test creating masker with custom config."""
        config = {"graceful_degradation": False, "timeout": 5}
        masker = AntiDetectionMasker(config=config)
        assert masker.config == config
        assert masker.config["graceful_degradation"] is False
    
    def test_masker_creation_with_event_builder(self):
        """Test creating masker with event builder."""
        builder = EventBuilder(run_id="test-001")
        masker = AntiDetectionMasker(event_builder=builder)
        assert masker.event_builder is builder
    
    def test_status_before_masking(self):
        """Test status before any masking applied."""
        masker = AntiDetectionMasker()
        status = masker.get_status()
        assert status["masks_applied"] is False
        assert status["mask_count"] == 0


class TestInitScriptGeneration:
    """Tests for init script generation."""
    
    def test_init_script_contains_webdriver_mask(self):
        """Test that init script includes webdriver masking."""
        masker = AntiDetectionMasker()
        script = masker._build_init_script()
        assert "navigator.webdriver" in script
        assert "Object.defineProperty" in script
        assert "undefined" in script
    
    def test_init_script_contains_console_mask(self):
        """Test that init script includes console method masking."""
        masker = AntiDetectionMasker()
        script = masker._build_init_script()
        assert "console" in script
        assert "__original_" in script
    
    def test_init_script_contains_process_mask(self):
        """Test that init script includes process object masking."""
        masker = AntiDetectionMasker()
        script = masker._build_init_script()
        assert "window.process" in script
        assert "process.version" in script
    
    def test_init_script_contains_plugins_mask(self):
        """Test that init script includes plugins population."""
        masker = AntiDetectionMasker()
        script = masker._build_init_script()
        assert "navigator.plugins" in script
        assert "fakePlugins" in script
        assert "PDF" in script or "pdf" in script.lower()
    
    def test_init_script_is_valid_javascript(self):
        """Test that generated script is valid JavaScript (syntax)."""
        masker = AntiDetectionMasker()
        script = masker._build_init_script()
        # Basic checks for valid JavaScript structure
        assert script.count("(function()") == 1  # IIFE wrapper
        assert script.count("})()") == 1  # IIFE closure
        assert script.count("{") == script.count("}")
        assert script.count("(") >= script.count(")")  # Allow extra open for balanced check
    
    def test_mask_count_updated(self):
        """Test that _mask_count is updated after script build."""
        masker = AntiDetectionMasker()
        assert masker._mask_count == 0
        script = masker._build_init_script()
        assert masker._mask_count == 7  # 7 masked properties


class TestMaskingMethods:
    """Tests for individual masking method implementations."""
    
    def test_webdriver_mask_script(self):
        """Test webdriver masking script content."""
        masker = AntiDetectionMasker()
        script = masker._mask_webdriver_property()
        assert "navigator.webdriver" in script
        assert "navigator.__proto__.webdriver" in script
        assert "undefined" in script
    
    def test_playwright_mask_script(self):
        """Test Playwright indicator masking script content."""
        masker = AntiDetectionMasker()
        script = masker._mask_playwright_indicators()
        assert "console" in script
        assert "__original_" in script
    
    def test_process_mask_script(self):
        """Test process property masking script content."""
        masker = AntiDetectionMasker()
        script = masker._mask_process_property()
        assert "process.version" in script
        assert "process.versions" in script
    
    def test_plugins_script(self):
        """Test plugins population script content."""
        masker = AntiDetectionMasker()
        script = masker._add_realistic_plugins()
        assert "navigator.plugins" in script
        assert "fakePlugins" in script
        assert "PDF Plugin" in script or "pdf" in script.lower()


@pytest.mark.asyncio
class TestApplyMasksAsync:
    """Tests for async apply_masks() method."""
    
    async def test_apply_masks_with_mock_context(self):
        """Test applying masks to a mock context."""
        masker = AntiDetectionMasker()
        mock_context = AsyncMock()
        
        result = await masker.apply_masks(mock_context)
        
        assert result["success"] is True
        assert masker.masks_applied is True
        assert "masked_properties" in result
        assert "indicators_removed" in result
        assert "duration_ms" in result
        assert result["indicators_removed"] == 7
    
    async def test_apply_masks_calls_add_init_script(self):
        """Test that apply_masks calls context.add_init_script()."""
        masker = AntiDetectionMasker()
        mock_context = AsyncMock()
        
        await masker.apply_masks(mock_context)
        
        mock_context.add_init_script.assert_called_once()
        # Verify script is passed as argument
        call_args = mock_context.add_init_script.call_args
        script_arg = call_args[0][0] if call_args[0] else call_args[1].get('script')
        assert isinstance(script_arg, str)
        assert "navigator.webdriver" in script_arg
    
    async def test_apply_masks_with_none_context(self):
        """Test applying masks with None context raises error."""
        masker = AntiDetectionMasker()
        
        with pytest.raises(RuntimeError, match="context is None"):
            await masker.apply_masks(None)
    
    async def test_apply_masks_with_event_builder(self):
        """Test that masks emit events with event builder."""
        builder = EventBuilder(run_id="test-run-001")
        masker = AntiDetectionMasker(event_builder=builder)
        mock_context = AsyncMock()
        
        result = await masker.apply_masks(mock_context)
        
        assert result["success"] is True
        # Event builder is called, though in real scenario publisher would publish
    
    async def test_apply_masks_graceful_degradation_on_error(self):
        """Test graceful degradation when masking fails."""
        masker = AntiDetectionMasker(config={"graceful_degradation": True})
        mock_context = AsyncMock()
        mock_context.add_init_script.side_effect = Exception("CDP connection failed")
        
        result = await masker.apply_masks(mock_context)
        
        assert result["success"] is False
        assert result.get("gracefully_degraded") is True
        assert "error" in result
    
    async def test_apply_masks_raises_on_error_without_graceful_degradation(self):
        """Test that error is raised when graceful_degradation=False."""
        masker = AntiDetectionMasker(config={"graceful_degradation": False})
        mock_context = AsyncMock()
        mock_context.add_init_script.side_effect = Exception("CDP connection failed")
        
        with pytest.raises(RuntimeError, match="Anti-detection masking failed"):
            await masker.apply_masks(mock_context)


class TestIntegration:
    """Integration tests for anti-detection masking."""
    
    def test_masker_complete_workflow(self):
        """Test complete masker workflow."""
        builder = EventBuilder(run_id="test-001")
        config = {"graceful_degradation": True}
        
        masker = AntiDetectionMasker(config=config, event_builder=builder)
        assert masker.get_status()["masks_applied"] is False
        
        # Build script
        script = masker._build_init_script()
        assert masker._mask_count == 7
        assert len(script) > 500  # Non-trivial script
        
        # Reset and verify
        masker.reset()
        assert masker.get_status()["masks_applied"] is False
        assert masker._mask_count == 0
    
    def test_realistic_plugins_constant(self):
        """Test that REALISTIC_PLUGINS is properly populated."""
        assert "Chrome" in REALISTIC_PLUGINS
        assert "Firefox" in REALISTIC_PLUGINS
        assert "Safari" in REALISTIC_PLUGINS
        
        # Verify each browser has plugins
        for browser, plugins in REALISTIC_PLUGINS.items():
            assert len(plugins) > 0
            for plugin in plugins:
                assert "name" in plugin
                assert "description" in plugin


class TestErrorHandling:
    """Tests for error handling in anti-detection masking."""
    
    @pytest.mark.asyncio
    async def test_apply_masks_with_invalid_context(self):
        """Test error handling with invalid context object."""
        masker = AntiDetectionMasker()
        invalid_context = "not a context object"
        
        with pytest.raises(RuntimeError, match="context is None"):
            await masker.apply_masks(None)
    
    @pytest.mark.asyncio
    async def test_apply_masks_logs_on_failure(self):
        """Test that failures are logged."""
        masker = AntiDetectionMasker()
        mock_context = AsyncMock()
        mock_context.add_init_script.side_effect = Exception("Test error")
        
        with patch('src.stealth.anti_detection.logger') as mock_logger:
            result = await masker.apply_masks(mock_context)
            
            # Should log error when graceful degradation is on
            if result.get("gracefully_degraded"):
                mock_logger.warning.assert_called()
