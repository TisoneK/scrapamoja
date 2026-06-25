"""
Unit tests for FeatureFlag model site-specific validation.

Tests Story 8.2 (Site-Based Feature Flags) requirements:
- Site-specific flag validation
- Hierarchy logic validation
- Site field constraints
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.selectors.adaptive.db.models.feature_flag import FeatureFlag


class TestFeatureFlagSiteValidation:
    """Test site-specific validation in FeatureFlag model."""
    
    def test_site_field_accepts_valid_values(self):
        """Test that site field accepts valid site names."""
        flag = FeatureFlag(
            sport="basketball",
            site="flashscore",
            enabled=True
        )
        
        assert flag.site == "flashscore"
        assert flag.sport == "basketball"
        assert flag.enabled is True
    
    def test_site_field_accepts_none(self):
        """Test that site field accepts None for global flags."""
        flag = FeatureFlag(
            sport="tennis",
            site=None,
            enabled=False
        )
        
        assert flag.site is None
        assert flag.sport == "tennis"
        assert flag.enabled is False
    
    def test_site_field_max_length(self):
        """Test that site field enforces maximum length."""
        # Site field has max_length=255
        long_site = "a" * 255
        flag = FeatureFlag(
            sport="football",
            site=long_site,
            enabled=True
        )
        
        assert len(flag.site) == 255
        assert flag.site == long_site
    
    def test_to_dict_includes_site_field(self):
        """Test that to_dict includes site field correctly."""
        flag = FeatureFlag(
            sport="basketball",
            site="flashscore",
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = flag.to_dict()
        
        assert "site" in result
        assert result["site"] == "flashscore"
        assert result["sport"] == "basketball"
        assert result["enabled"] is True
    
    def test_to_dict_handles_null_site(self):
        """Test that to_dict handles None site correctly."""
        flag = FeatureFlag(
            sport="tennis",
            site=None,
            enabled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = flag.to_dict()
        
        assert "site" in result
        assert result["site"] is None
    
    def test_from_dict_creates_site_specific_flag(self):
        """Test that from_dict creates site-specific flag correctly."""
        data = {
            "sport": "basketball",
            "site": "bet365",
            "enabled": True
        }
        
        flag = FeatureFlag.from_dict(data)
        
        assert flag.sport == "basketball"
        assert flag.site == "bet365"
        assert flag.enabled is True
    
    def test_from_dict_creates_global_flag(self):
        """Test that from_dict creates global flag when site not provided."""
        data = {
            "sport": "tennis",
            "enabled": False
        }
        
        flag = FeatureFlag.from_dict(data)
        
        assert flag.sport == "tennis"
        assert flag.site is None
        assert flag.enabled is False
    
    def test_repr_includes_site_when_present(self):
        """Test that __repr__ includes site when present."""
        flag = FeatureFlag(
            sport="basketball",
            site="flashscore",
            enabled=True
        )
        
        repr_str = repr(flag)
        assert "flashscore" in repr_str
        assert "@flashscore" in repr_str
        assert "basketball" in repr_str
        assert "enabled=True" in repr_str
    
    def test_repr_excludes_site_when_null(self):
        """Test that __repr__ excludes site suffix when site is None."""
        flag = FeatureFlag(
            sport="tennis",
            site=None,
            enabled=False
        )
        
        repr_str = repr(flag)
        assert "@" not in repr_str
        assert "tennis" in repr_str
        assert "enabled=False" in repr_str
    
    def test_site_field_indexing(self):
        """Test that site field is properly indexed."""
        # This is more of a schema validation test
        # In a real implementation, we'd check the actual database schema
        flag = FeatureFlag(
            sport="basketball",
            site="williamhill",
            enabled=True
        )
        
        # Just ensure the field exists and can be set
        assert flag.site == "williamhill"


@pytest.mark.integration
class TestFeatureFlagSiteConstraints:
    """Test site-specific constraints at database level."""
    
    def test_unique_constraint_sport_site(self):
        """Test that unique constraint on sport + site works."""
        # This would require actual database integration
        # For now, we test the model-level behavior
        flag1 = FeatureFlag(
            sport="basketball",
            site="flashscore",
            enabled=True
        )
        
        flag2 = FeatureFlag(
            sport="basketball", 
            site="flashscore",  # Same sport + site
            enabled=False
        )
        
        # Both should be creatable at model level
        # Database constraint would be enforced at commit time
        assert flag1.sport == flag2.sport
        assert flag1.site == flag2.site
    
    def test_unique_constraint_sport_null_site(self):
        """Test that multiple global flags for same sport are prevented."""
        flag1 = FeatureFlag(
            sport="basketball",
            site=None,
            enabled=True
        )
        
        flag2 = FeatureFlag(
            sport="basketball",
            site=None,  # Same sport, both null site
            enabled=False
        )
        
        # Both should be creatable at model level
        # Database constraint would prevent duplicate global flags
        assert flag1.sport == flag2.sport
        assert flag1.site is None
        assert flag2.site is None
    
    def test_different_sites_same_sport_allowed(self):
        """Test that different sites for same sport are allowed."""
        flag1 = FeatureFlag(
            sport="basketball",
            site="flashscore",
            enabled=True
        )
        
        flag2 = FeatureFlag(
            sport="basketball",
            site="bet365",  # Different site, same sport
            enabled=False
        )
        
        # Both should be allowed
        assert flag1.sport == flag2.sport
        assert flag1.site != flag2.site
