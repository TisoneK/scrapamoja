"""
Integration tests for selector engine site-based feature flag integration.

Tests Story 8.2 (Site-Based Feature Flags) requirements:
- Selector resolution checks site-specific flags
- Proper fallback hierarchy (site → sport → default)
- Integration with failure detector
"""

import pytest
import tempfile
import os
from unittest.mock import patch, AsyncMock

from src.selectors.adaptive.services.failure_detector import FailureDetectorService
from src.selectors.adaptive.services.feature_flag_service import get_feature_flag_service, FeatureFlagService


@pytest.mark.integration
class TestSelectorEngineSiteIntegration:
    """Test selector engine integration with site-based feature flags."""
    
    @pytest.fixture
    def temp_service(self):
        """Create temporary feature flag service for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            service = FeatureFlagService(db_path)
            yield service
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.fixture
    def failure_detector(self):
        """Create failure detector for testing."""
        return FailureDetectorService()
    
    def test_failure_detector_uses_site_flags(self, temp_service, failure_detector):
        """Test that failure detector checks site-specific flags."""
        # Mock the global service to use our temp service
        with patch('src.selectors.adaptive.services.failure_detector.get_feature_flag_service') as mock_get_service:
            mock_get_service.return_value = temp_service
            
            # Create test data
            temp_service.create_feature_flag("basketball", None, True)   # Global enabled
            temp_service.create_feature_flag("basketball", "flashscore", False)  # Site disabled
            
            # Create test event
            test_event = AsyncMock()
            test_event.correlation_id = "test-123"
            test_event.data = {
                "selector_name": "test-selector",
                "sport": "basketball",
                "site": "flashscore",
                "failure_reason": "Test failure"
            }
            
            # Test that site-specific flag overrides global
            # The failure detector should skip adaptive processing for flashscore
            # because the site-specific flag is disabled, even though global is enabled
            
            # Mock the async handler method to track if it's called
            failure_detector.on_selector_failed = AsyncMock()
            
            # Run the event handler
            import asyncio
            asyncio.run(failure_detector.handle_selector_failure_event(test_event))
            
            # Verify that the adaptive handler was NOT called
            # because site-specific flag overrides global flag
            failure_detector.on_selector_failed.assert_not_called()
    
    def test_failure_detector_fallback_to_global(self, temp_service, failure_detector):
        """Test that failure detector falls back to global flag when site flag doesn't exist."""
        # Mock the global service to use our temp service
        with patch('src.selectors.adaptive.services.failure_detector.get_feature_flag_service') as mock_get_service:
            mock_get_service.return_value = temp_service
            
            # Create test data - only global flag
            temp_service.create_feature_flag("basketball", None, True)   # Global enabled
            # No site-specific flag for flashscore
            
            # Create test event
            test_event = AsyncMock()
            test_event.correlation_id = "test-456"
            test_event.data = {
                "selector_name": "test-selector",
                "sport": "basketball",
                "site": "flashscore",  # Site flag doesn't exist
                "failure_reason": "Test failure"
            }
            
            # Mock the async handler method to track if it's called
            failure_detector.on_selector_failed = AsyncMock()
            
            # Run the event handler
            import asyncio
            asyncio.run(failure_detector.handle_selector_failure_event(test_event))
            
            # Verify that the adaptive handler WAS called
            # because it falls back to global flag which is enabled
            failure_detector.on_selector_failed.assert_called_once()
    
    def test_failure_detector_default_disabled(self, temp_service, failure_detector):
        """Test that failure detector defaults to disabled when no flags exist."""
        # Mock the global service to use our temp service
        with patch('src.selectors.adaptive.services.failure_detector.get_feature_flag_service') as mock_get_service:
            mock_get_service.return_value = temp_service
            
            # No flags created - should default to disabled
            
            # Create test event
            test_event = AsyncMock()
            test_event.correlation_id = "test-789"
            test_event.data = {
                "selector_name": "test-selector",
                "sport": "tennis",  # No flags for this sport
                "site": "flashscore",
                "failure_reason": "Test failure"
            }
            
            # Mock the async handler method to track if it's called
            failure_detector.on_selector_failed = AsyncMock()
            
            # Run the event handler
            import asyncio
            asyncio.run(failure_detector.handle_selector_failure_event(test_event))
            
            # Verify that the adaptive handler was NOT called
            # because no flags exist, default is disabled
            failure_detector.on_selector_failed.assert_not_called()
    
    def test_failure_detector_without_sport(self, temp_service, failure_detector):
        """Test failure detector behavior when sport is not provided."""
        # Mock the global service to use our temp service
        with patch('src.selectors.adaptive.services.failure_detector.get_feature_flag_service') as mock_get_service:
            mock_get_service.return_value = temp_service
            
            # Create test event without sport
            test_event = AsyncMock()
            test_event.correlation_id = "test-no-sport"
            test_event.data = {
                "selector_name": "test-selector",
                "site": "flashscore",
                "failure_reason": "Test failure"
                # No sport field
            }
            
            # Mock the async handler method to track if it's called
            failure_detector.on_selector_failed = AsyncMock()
            
            # Run the event handler
            import asyncio
            asyncio.run(failure_detector.handle_selector_failure_event(test_event))
            
            # Should still call the handler because sport check is bypassed
            failure_detector.on_selector_failed.assert_called_once()
    
    def test_service_integration_hierarchy(self, temp_service):
        """Test the complete hierarchy logic through the service."""
        # Create comprehensive test data
        temp_service.create_feature_flag("basketball", None, True)   # Global enabled
        temp_service.create_feature_flag("basketball", "flashscore", False)  # Site disabled
        temp_service.create_feature_flag("tennis", None, False)     # Global disabled
        temp_service.create_feature_flag("tennis", "flashscore", True)   # Site enabled
        
        # Test hierarchy cases
        test_cases = [
            # (sport, site, expected_result, description)
            ("basketball", "flashscore", False, "Site overrides global (False overrides True)"),
            ("basketball", "bet365", True, "Falls back to global when site flag missing"),
            ("tennis", "flashscore", True, "Site overrides global (True overrides False)"),
            ("tennis", "bet365", False, "Falls back to global when site flag missing"),
            ("football", "flashscore", False, "Default disabled when no flags exist"),
            ("basketball", None, True, "Global flag when site is None"),
            ("tennis", None, False, "Global flag when site is None"),
            ("football", None, False, "Default disabled when no global flag"),
        ]
        
        for sport, site, expected, description in test_cases:
            result = temp_service.is_adaptive_enabled(sport, site)
            assert result == expected, f"Failed: {description}. Expected {expected}, got {result} for {sport}@{site}"
    
    def test_service_caching_with_sites(self, temp_service):
        """Test that caching works correctly with site parameters."""
        # Create test data
        temp_service.create_feature_flag("basketball", "flashscore", True)
        
        # First call should populate cache
        result1 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result1 is True
        
        # Check cache was populated
        cache_key = temp_service._get_cache_key("basketball", "flashscore")
        assert cache_key in temp_service._cache
        
        # Second call should use cache
        result2 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result2 is True
        
        # Different site should have separate cache entry
        result3 = temp_service.is_adaptive_enabled("basketball", "bet365")
        assert result3 is False  # Default disabled
        
        # Should have separate cache entries
        cache_key_2 = temp_service._get_cache_key("basketball", "bet365")
        assert cache_key_2 in temp_service._cache
        assert cache_key != cache_key_2
        
        # Update should invalidate cache
        temp_service.update_feature_flag("basketball", "flashscore", False)
        result4 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result4 is False  # Updated value


@pytest.mark.integration
class TestFeatureFlagServiceRealIntegration:
    """Test integration with actual feature flag service."""
    
    def test_global_service_integration(self):
        """Test integration with the global service instance."""
        # This test verifies that the global service function works correctly
        from src.selectors.adaptive.services.feature_flag_service import is_adaptive_enabled
        
        # Test with no database (should default to False)
        result = is_adaptive_enabled("test-sport", "test-site")
        assert result is False, "Should default to False when no database/configured"
    
    def test_service_factory_pattern(self):
        """Test that the service factory pattern works."""
        from src.selectors.adaptive.services.feature_flag_service import get_feature_flag_service
        
        # Get service instance
        service = get_feature_flag_service()
        assert isinstance(service, FeatureFlagService)
        
        # Should be able to call methods
        result = service.is_adaptive_enabled("test", "test")
        assert isinstance(result, bool)
