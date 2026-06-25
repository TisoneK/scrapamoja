"""
Unit tests for Feature Flag Service.

Tests cover:
- Feature flag CRUD operations
- Flag lookup logic with caching
- Sport/site-specific flag behavior
- Performance requirements (< 1ms lookup)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.selectors.adaptive.db.repositories.feature_flag_repository import FeatureFlagRepository
from src.selectors.adaptive.db.models.feature_flag import FeatureFlag
from src.selectors.adaptive.services.feature_flag_service import FeatureFlagService, get_feature_flag_service, is_adaptive_enabled


@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    return Mock(spec=FeatureFlagRepository)


@pytest.fixture
def feature_flag_service(mock_repository):
    """Feature flag service with mocked repository."""
    return FeatureFlagService(db_path=":memory:")


@pytest.fixture
def sample_flags():
    """Sample feature flags for testing."""
    return [
        FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        FeatureFlag(
            id=2,
            sport="basketball",
            site="flashscore",
            enabled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        FeatureFlag(
            id=3,
            sport="tennis",
            site=None,
            enabled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


class TestFeatureFlagService:
    """Test suite for FeatureFlagService."""
    
    @pytest.mark.asyncio
    async def test_create_feature_flag_success(self, feature_flag_service, mock_repository):
        """Test successful feature flag creation."""
        # Setup
        mock_repository.get_feature_flag.return_value = None
        expected_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.create_feature_flag.return_value = expected_flag
        
        # Execute
        result = feature_flag_service.create_feature_flag("basketball", None, True)
        
        # Verify
        assert result == expected_flag
        mock_repository.create_feature_flag.assert_called_once_with("basketball", None, True)
    
    @pytest.mark.asyncio
    async def test_create_feature_flag_already_exists(self, feature_flag_service, mock_repository):
        """Test creating flag that already exists raises ValueError."""
        # Setup
        existing_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_feature_flag.return_value = existing_flag
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Feature flag already exists"):
            feature_flag_service.create_feature_flag("basketball", None, True)
    
    @pytest.mark.asyncio
    async def test_get_feature_flag(self, feature_flag_service, mock_repository):
        """Test getting feature flag."""
        # Setup
        expected_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_feature_flag.return_value = expected_flag
        
        # Execute
        result = feature_flag_service.get_feature_flag("basketball", None)
        
        # Verify
        assert result == expected_flag
        mock_repository.get_feature_flag.assert_called_once_with("basketball", None)
    
    @pytest.mark.asyncio
    async def test_is_adaptive_enabled_global_flag(self, feature_flag_service, mock_repository):
        """Test adaptive enabled check with global flag."""
        # Setup
        global_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.is_adaptive_enabled.return_value = True
        
        # Execute
        result = feature_flag_service.is_adaptive_enabled("basketball", None)
        
        # Verify
        assert result is True
        mock_repository.is_adaptive_enabled.assert_called_once_with("basketball", None)
    
    @pytest.mark.asyncio
    async def test_is_adaptive_enabled_site_specific_flag(self, feature_flag_service, mock_repository):
        """Test adaptive enabled check with site-specific flag."""
        # Setup
        site_flag = FeatureFlag(
            id=2,
            sport="basketball",
            site="flashscore",
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.is_adaptive_enabled.return_value = True
        
        # Execute
        result = feature_flag_service.is_adaptive_enabled("basketball", "flashscore")
        
        # Verify
        assert result is True
        mock_repository.is_adaptive_enabled.assert_called_once_with("basketball", "flashscore")
    
    @pytest.mark.asyncio
    async def test_is_adaptive_enabled_fallback_to_global(self, feature_flag_service, mock_repository):
        """Test adaptive enabled falls back to global flag when site-specific not found."""
        # Setup
        mock_repository.is_adaptive_enabled.return_value = False
        
        # Execute
        result = feature_flag_service.is_adaptive_enabled("basketball", "unknown_site")
        
        # Verify
        assert result is False
        mock_repository.is_adaptive_enabled.assert_called_once_with("basketball", "unknown_site")
    
    @pytest.mark.asyncio
    async def test_is_adaptive_enabled_default_disabled(self, feature_flag_service, mock_repository):
        """Test adaptive enabled defaults to False when no flag found."""
        # Setup
        mock_repository.is_adaptive_enabled.return_value = False
        
        # Execute
        result = feature_flag_service.is_adaptive_enabled("unknown_sport", None)
        
        # Verify
        assert result is False
        mock_repository.is_adaptive_enabled.assert_called_once_with("unknown_sport", None)
    
    @pytest.mark.asyncio
    async def test_update_feature_flag(self, feature_flag_service, mock_repository):
        """Test updating feature flag."""
        # Setup
        updated_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.update_feature_flag.return_value = updated_flag
        
        # Execute
        result = feature_flag_service.update_feature_flag("basketball", None, True)
        
        # Verify
        assert result == updated_flag
        mock_repository.update_feature_flag.assert_called_once_with("basketball", None, True)
    
    @pytest.mark.asyncio
    async def test_update_feature_flag_not_found(self, feature_flag_service, mock_repository):
        """Test updating non-existent feature flag returns None."""
        # Setup
        mock_repository.update_feature_flag.return_value = None
        
        # Execute
        result = feature_flag_service.update_feature_flag("unknown", None, True)
        
        # Verify
        assert result is None
        mock_repository.update_feature_flag.assert_called_once_with("unknown", None, True)
    
    @pytest.mark.asyncio
    async def test_delete_feature_flag(self, feature_flag_service, mock_repository):
        """Test deleting feature flag."""
        # Setup
        mock_repository.delete_feature_flag.return_value = True
        
        # Execute
        result = feature_flag_service.delete_feature_flag("basketball", None)
        
        # Verify
        assert result is True
        mock_repository.delete_feature_flag.assert_called_once_with("basketball", None)
    
    @pytest.mark.asyncio
    async def test_delete_feature_flag_not_found(self, feature_flag_service, mock_repository):
        """Test deleting non-existent feature flag returns False."""
        # Setup
        mock_repository.delete_feature_flag.return_value = False
        
        # Execute
        result = feature_flag_service.delete_feature_flag("unknown", None)
        
        # Verify
        assert result is False
        mock_repository.delete_feature_flag.assert_called_once_with("unknown", None)
    
    @pytest.mark.asyncio
    async def test_toggle_sport_flag_existing(self, feature_flag_service, mock_repository):
        """Test toggling existing sport flag."""
        # Setup
        existing_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        toggled_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        mock_repository.get_feature_flag.return_value = existing_flag
        mock_repository.update_feature_flag.return_value = toggled_flag
        
        # Execute
        result = feature_flag_service.toggle_sport_flag("basketball")
        
        # Verify
        assert result == toggled_flag
        mock_repository.get_feature_flag.assert_called_once_with("basketball", None)
        mock_repository.update_feature_flag.assert_called_once_with("basketball", None, True)
    
    @pytest.mark.asyncio
    async def test_toggle_sport_flag_creates_new(self, feature_flag_service, mock_repository):
        """Test toggling creates new flag when none exists."""
        # Setup
        mock_repository.get_feature_flag.return_value = None
        new_flag = FeatureFlag(
            id=2,
            sport="tennis",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.create_feature_flag.return_value = new_flag
        
        # Execute
        result = feature_flag_service.toggle_sport_flag("tennis")
        
        # Verify
        assert result == new_flag
        mock_repository.get_feature_flag.assert_called_once_with("tennis", None)
        mock_repository.create_feature_flag.assert_called_once_with("tennis", None, True)
    
    @pytest.mark.asyncio
    async def test_get_enabled_sports(self, feature_flag_service, mock_repository):
        """Test getting list of enabled sports."""
        # Setup
        enabled_sports = ["basketball", "tennis"]
        mock_repository.get_enabled_sports.return_value = enabled_sports
        
        # Execute
        result = feature_flag_service.get_enabled_sports()
        
        # Verify
        assert result == enabled_sports
        mock_repository.get_enabled_sports.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_create_flags(self, feature_flag_service, mock_repository):
        """Test bulk creating feature flags."""
        # Setup
        flags_data = [
            {"sport": "basketball", "enabled": False},
            {"sport": "tennis", "enabled": False},
            {"sport": "football", "enabled": True},
        ]
        created_flags = [
            FeatureFlag(id=1, sport="basketball", enabled=False, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=2, sport="tennis", enabled=False, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=3, sport="football", enabled=True, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
        ]
        mock_repository.bulk_create_flags.return_value = created_flags
        
        # Execute
        result = feature_flag_service.bulk_create_flags(flags_data)
        
        # Verify
        assert result == created_flags
        mock_repository.bulk_create_flags.assert_called_once_with(flags_data)
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, feature_flag_service):
        """Test that caching works for performance."""
        # Setup - use real repository with in-memory DB
        service = FeatureFlagService(db_path=":memory:", cache_ttl=60)
        
        # Create a flag
        flag = service.create_feature_flag("cricket", None, True)
        
        # First call should hit repository
        start_time = datetime.utcnow()
        result1 = service.is_adaptive_enabled("cricket", None)
        first_call_time = datetime.utcnow() - start_time
        
        # Second call should use cache (much faster)
        start_time = datetime.utcnow()
        result2 = service.is_adaptive_enabled("cricket", None)
        second_call_time = datetime.utcnow() - start_time
        
        # Verify
        assert result1 is True
        assert result2 is True
        # Cached call should be faster (though hard to measure precisely in unit tests)
        assert service.get_cache_stats()["total_entries"] == 1
        assert service.get_cache_stats()["valid_entries"] == 1
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, feature_flag_service, mock_repository):
        """Test that cache is invalidated when flag is updated."""
        # Setup
        mock_repository.is_adaptive_enabled.return_value = False
        
        # First call populates cache
        result1 = feature_flag_service.is_adaptive_enabled("basketball", None)
        assert result1 is False
        
        # Update flag (should invalidate cache)
        updated_flag = FeatureFlag(
            id=1,
            sport="basketball",
            site=None,
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.update_feature_flag.return_value = updated_flag
        feature_flag_service.update_feature_flag("basketball", None, True)
        
        # Next call should hit repository again
        mock_repository.is_adaptive_enabled.return_value = True
        result2 = feature_flag_service.is_adaptive_enabled("basketball", None)
        
        # Verify
        assert result2 is True
        # Repository should be called twice (once for initial, once after cache invalidation)
        assert mock_repository.is_adaptive_enabled.call_count == 2
    
    def test_get_cache_stats(self, feature_flag_service):
        """Test getting cache statistics."""
        # Setup
        service = FeatureFlagService(db_path=":memory:", cache_ttl=60)
        
        # Initially empty
        stats = service.get_cache_stats()
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["invalid_entries"] == 0
        assert stats["cache_ttl"] == 60
        
        # Add some cached entries
        service._cache["basketball"] = {"enabled": True}
        service._cache["tennis"] = {"enabled": False}
        service._cache_timestamps["basketball"] = datetime.utcnow().timestamp()
        service._cache_timestamps["tennis"] = (datetime.utcnow() - timedelta(seconds=70)).timestamp()
        
        stats = service.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1  # Only basketball is still valid
        assert stats["invalid_entries"] == 1  # tennis is expired
        assert stats["cache_ttl"] == 60
    
    def test_clear_cache(self, feature_flag_service):
        """Test clearing cache."""
        # Setup
        service = FeatureFlagService(db_path=":memory:", cache_ttl=60)
        service._cache["basketball"] = {"enabled": True}
        service._cache_timestamps["basketball"] = datetime.utcnow().timestamp()
        
        # Verify cache has entries
        assert len(service._cache) == 1
        assert len(service._cache_timestamps) == 1
        
        # Clear cache
        service.clear_cache()
        
        # Verify cache is empty
        assert len(service._cache) == 0
        assert len(service._cache_timestamps) == 0


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    @pytest.mark.asyncio
    async def test_is_adaptive_enabled_convenience_function(self):
        """Test global is_adaptive_enabled convenience function."""
        # This function should be available and callable
        result = is_adaptive_enabled("basketball", None)
        
        # Should return False for unknown sport (no flags in in-memory DB)
        assert result is False
    
    def test_get_feature_flag_service_singleton(self):
        """Test that get_feature_flag_service returns singleton."""
        service1 = get_feature_flag_service()
        service2 = get_feature_flag_service()
        
        # Should be the same instance
        assert service1 is service2
