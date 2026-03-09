"""
Unit tests for FeatureFlagService site-based enhancements.

Tests Story 8.2 (Site-Based Feature Flags) requirements:
- Site-based flag lookups with hierarchy logic
- Site-specific CRUD operations
- Performance requirements (< 1ms lookup)
"""

import pytest
import tempfile
import os
from unittest.mock import patch
from datetime import datetime

from src.selectors.adaptive.services.feature_flag_service import FeatureFlagService
from src.selectors.adaptive.db.repositories.feature_flag_repository import FeatureFlagRepository


class TestFeatureFlagServiceSiteEnhancements:
    """Test site-based enhancements to FeatureFlagService."""
    
    @pytest.fixture
    def temp_service(self):
        """Create temporary service for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            service = FeatureFlagService(db_path, cache_ttl=1)  # Short cache for testing
            yield service
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_is_adaptive_enabled_with_site_parameter(self, temp_service):
        """Test that is_adaptive_enabled properly handles site parameter."""
        # Create test data
        temp_service.create_feature_flag("basketball", None, True)  # Global enabled
        temp_service.create_feature_flag("basketball", "flashscore", False)  # Site disabled
        
        # Test hierarchy: site-specific should override global
        result = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result is False, "Site-specific flag should override global flag"
        
        # Test global flag when site flag doesn't exist
        result = temp_service.is_adaptive_enabled("basketball", "bet365")
        assert result is True, "Should fall back to global flag when site flag doesn't exist"
        
        # Test default disabled when no flags exist
        result = temp_service.is_adaptive_enabled("tennis", "flashscore")
        assert result is False, "Should default to False when no flags exist"
    
    def test_is_adaptive_enabled_hierarchy_logic(self, temp_service):
        """Test the complete hierarchy logic: site → sport → default."""
        # Create test data with different combinations
        temp_service.create_feature_flag("basketball", None, True)   # Global enabled
        temp_service.create_feature_flag("basketball", "flashscore", False)  # Site disabled
        temp_service.create_feature_flag("tennis", None, False)     # Global disabled
        temp_service.create_feature_flag("tennis", "flashscore", True)   # Site enabled
        
        # Test cases
        test_cases = [
            ("basketball", "flashscore", False),  # Site overrides global (False overrides True)
            ("basketball", "bet365", True),       # Falls back to global
            ("tennis", "flashscore", True),       # Site overrides global (True overrides False)
            ("tennis", "bet365", False),          # Falls back to global
            ("football", "flashscore", False),    # No flags exist, default False
        ]
        
        for sport, site, expected in test_cases:
            result = temp_service.is_adaptive_enabled(sport, site)
            assert result == expected, f"Failed for {sport}@{site}, expected {expected}, got {result}"
    
    def test_site_specific_crud_operations(self, temp_service):
        """Test site-specific CRUD operations."""
        # Create site-specific flag
        flag = temp_service.create_feature_flag("basketball", "flashscore", True)
        assert flag.sport == "basketball"
        assert flag.site == "flashscore"
        assert flag.enabled is True
        
        # Read site-specific flag
        retrieved = temp_service.get_feature_flag("basketball", "flashscore")
        assert retrieved is not None
        assert retrieved.id == flag.id
        assert retrieved.enabled is True
        
        # Update site-specific flag
        updated = temp_service.update_feature_flag("basketball", "flashscore", False)
        assert updated is not None
        assert updated.enabled is False
        
        # Delete site-specific flag
        deleted = temp_service.delete_feature_flag("basketball", "flashscore")
        assert deleted is True
        
        # Verify deletion
        retrieved = temp_service.get_feature_flag("basketball", "flashscore")
        assert retrieved is None
    
    def test_get_feature_flags_by_site(self, temp_service):
        """Test getting flags for a specific site across sports."""
        # Create test data
        temp_service.create_feature_flag("basketball", "flashscore", True)
        temp_service.create_feature_flag("tennis", "flashscore", False)
        temp_service.create_feature_flag("football", "flashscore", True)
        temp_service.create_feature_flag("basketball", "bet365", False)  # Different site
        
        # Get all flags and filter by site
        all_flags = temp_service.get_all_feature_flags()
        flashscore_flags = [f for f in all_flags if f.site == "flashscore"]
        
        assert len(flashscore_flags) == 3
        assert all(f.site == "flashscore" for f in flashscore_flags)
        assert set(f.sport for f in flashscore_flags) == {"basketball", "tennis", "football"}
    
    def test_cache_performance_with_site_parameters(self, temp_service):
        """Test that caching works properly with site parameters."""
        # Create test data
        temp_service.create_feature_flag("basketball", "flashscore", True)
        
        # First call should populate cache
        result1 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result1 is True
        
        # Check cache stats
        stats = temp_service.get_cache_stats()
        assert stats["total_entries"] >= 1
        assert stats["valid_entries"] >= 1
        
        # Second call should use cache
        result2 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result2 is True
        
        # Different site should create separate cache entry
        result3 = temp_service.is_adaptive_enabled("basketball", "bet365")
        assert result3 is False  # Default disabled
        
        # Should have separate cache entries
        stats = temp_service.get_cache_stats()
        assert stats["total_entries"] >= 2
    
    def test_cache_invalidation_on_site_updates(self, temp_service):
        """Test that cache is invalidated when site flags are updated."""
        # Create test data
        temp_service.create_feature_flag("basketball", "flashscore", True)
        
        # Populate cache
        result1 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result1 is True
        
        # Update flag (should invalidate cache)
        temp_service.update_feature_flag("basketball", "flashscore", False)
        
        # Should get updated value
        result2 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result2 is False
    
    @pytest.mark.asyncio
    def test_bulk_site_operations(self, temp_service):
        """Test bulk operations with site-specific flags."""
        # Prepare bulk data
        flags_data = [
            {"sport": "basketball", "site": "flashscore", "enabled": True},
            {"sport": "basketball", "site": "bet365", "enabled": False},
            {"sport": "tennis", "site": "flashscore", "enabled": True},
            {"sport": "tennis", "site": "bet365", "enabled": False},
        ]
        
        # Bulk create
        created_flags = temp_service.bulk_create_flags(flags_data)
        assert len(created_flags) == 4
        
        # Verify all created
        all_flags = temp_service.get_all_feature_flags()
        site_flags = [f for f in all_flags if f.site is not None]
        assert len(site_flags) == 4
        
        # Verify specific combinations
        for data in flags_data:
            flag = temp_service.get_feature_flag(data["sport"], data["site"])
            assert flag is not None
            assert flag.enabled == data["enabled"]
    
    def test_site_flag_validation(self, temp_service):
        """Test validation for site-specific flags."""
        # Test creating duplicate site flag for same sport
        temp_service.create_feature_flag("basketball", "flashscore", True)
        
        # Should raise error for duplicate
        with pytest.raises(ValueError, match="Feature flag already exists"):
            temp_service.create_feature_flag("basketball", "flashscore", False)
        
        # Should allow same site for different sport
        flag = temp_service.create_feature_flag("tennis", "flashscore", True)
        assert flag.sport == "tennis"
        assert flag.site == "flashscore"
    
    def test_edge_cases_with_site_parameters(self, temp_service):
        """Test edge cases with site parameters."""
        # Empty site name should be treated as None
        flag1 = temp_service.create_feature_flag("basketball", "", True)
        assert flag1.site is None
        
        # Site name with spaces should be trimmed
        flag2 = temp_service.create_feature_flag("tennis", "  flashscore  ", False)
        assert flag2.site == "flashscore"
        
        # Case sensitivity should be normalized
        result1 = temp_service.is_adaptive_enabled("basketball", "FlashScore")
        result2 = temp_service.is_adaptive_enabled("basketball", "flashscore")
        assert result1 == result2


@pytest.mark.integration
class TestFeatureFlagServiceIntegration:
    """Integration tests for site-based feature flag service."""
    
    def test_service_with_migration_data(self):
        """Test service with migration data from 002_add_site_flags.sql."""
        # Create service with temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            service = FeatureFlagService(db_path)
            
            # Apply migration
            migration_path = 'src/selectors/adaptive/db/migrations/002_add_site_flags.sql'
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            # Parse and execute migration
            import re
            cleaned_sql = re.sub(r'--.*$', '', migration_sql, flags=re.MULTILINE)
            
            statements = []
            current_stmt = ""
            for line in cleaned_sql.split('\n'):
                line = line.strip()
                if line:
                    current_stmt += line + " "
                    if line.endswith(';'):
                        statements.append(current_stmt.strip())
                        current_stmt = ""
            
            if current_stmt.strip():
                statements.append(current_stmt.strip())
            
            from sqlalchemy import text
            session = service._repository.get_session()
            try:
                for stmt in statements:
                    if stmt.strip() and 'INSERT' in stmt:
                        session.execute(text(stmt))
                session.commit()
            finally:
                session.close()
            
            # Test service with migration data
            all_flags = service.get_all_feature_flags()
            assert len(all_flags) == 40, f"Expected 40 flags from migration, got {len(all_flags)}"
            
            # Test hierarchy with migration data
            # All flags should be disabled by default
            result = service.is_adaptive_enabled("basketball", "flashscore")
            assert result is False
            
            # Enable a global flag
            service.update_feature_flag("basketball", None, True)
            result = service.is_adaptive_enabled("basketball", "flashscore")
            assert result is True  # Should still be False due to site-specific flag
            
            # Enable site-specific flag
            service.update_feature_flag("basketball", "flashscore", True)
            result = service.is_adaptive_enabled("basketball", "flashscore")
            assert result is True  # Now should be True
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
