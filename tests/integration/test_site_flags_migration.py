"""
Integration tests for site flags migration (002_add_site_flags.sql).

Tests Story 8.2 (Site-Based Feature Flags) requirements:
- Site-specific seed data creation
- Migration execution
- Data verification
"""

import pytest
import os
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.selectors.adaptive.db.repositories.feature_flag_repository import FeatureFlagRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestSiteFlagsMigration:
    """Test site flags migration functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Create repository with temp database
            repo = FeatureFlagRepository(db_path)
            yield repo
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.fixture
    def migrated_repo(self, temp_db):
        """Repository with migrations applied."""
        # The repository already creates the base table, so we just need to apply the site flags migration
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/selectors/adaptive/db/migrations/002_add_site_flags.sql"
        )
        
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        session = temp_db.get_session()
        try:
            # Parse and execute migration properly
            import re
            
            # Remove comments first
            cleaned_sql = re.sub(r'--.*$', '', migration_sql, flags=re.MULTILINE)
            
            # Split by semicolon and clean up
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
            
            # Execute only INSERT statements
            for stmt in statements:
                stmt = stmt.strip()
                if stmt and 'INSERT' in stmt:
                    session.execute(text(stmt))
            session.commit()
        finally:
            session.close()
        
        return temp_db
    
    def test_site_flags_seed_data_created(self, migrated_repo):
        """Test that site-specific seed data is created correctly."""
        all_flags = migrated_repo.get_all_feature_flags()
        
        # Should have 30 site-specific flags (10 sports × 3 sites)
        site_flags = [f for f in all_flags if f.site is not None]
        assert len(site_flags) == 30, f"Expected 30 site flags, got {len(site_flags)}"
        
        # Should still have 10 global flags
        global_flags = [f for f in all_flags if f.site is None]
        assert len(global_flags) == 10, f"Expected 10 global flags, got {len(global_flags)}"
        
        # Total should be 40 flags
        assert len(all_flags) == 40, f"Expected 40 total flags, got {len(all_flags)}"
    
    def test_expected_sites_created(self, migrated_repo):
        """Test that expected sites are created for each sport."""
        expected_sites = ['flashscore', 'bet365', 'williamhill']
        expected_sports = ['basketball', 'tennis', 'football', 'soccer', 
                          'baseball', 'hockey', 'volleyball', 'rugby', 
                          'cricket', 'golf']
        
        for sport in expected_sports:
            sport_flags = migrated_repo.get_feature_flags_by_sport(sport)
            
            # Should have 4 flags for each sport: 1 global + 3 site-specific
            assert len(sport_flags) == 4, f"Expected 4 flags for {sport}, got {len(sport_flags)}"
            
            # Check site-specific flags
            site_flags_for_sport = [f for f in sport_flags if f.site is not None]
            assert len(site_flags_for_sport) == 3, f"Expected 3 site flags for {sport}, got {len(site_flags_for_sport)}"
            
            # Verify all expected sites are present
            actual_sites = {f.site for f in site_flags_for_sport}
            expected_sites_set = set(expected_sites)
            assert actual_sites == expected_sites_set, f"Sites mismatch for {sport}: expected {expected_sites_set}, got {actual_sites}"
    
    def test_site_flags_disabled_by_default(self, migrated_repo):
        """Test that all site-specific flags are disabled by default."""
        all_flags = migrated_repo.get_all_feature_flags()
        site_flags = [f for f in all_flags if f.site is not None]
        
        # All site flags should be disabled
        enabled_site_flags = [f for f in site_flags if f.enabled]
        assert len(enabled_site_flags) == 0, f"Expected all site flags to be disabled, but {len(enabled_site_flags)} are enabled"
        
        # Verify all site flags have enabled=False
        for flag in site_flags:
            assert flag.enabled is False, f"Site flag for {flag.sport}@{flag.site} should be disabled"
    
    def test_hierarchy_logic_works(self, migrated_repo):
        """Test that hierarchy logic works correctly with seed data."""
        # Test with a specific sport and site
        sport = "basketball"
        site = "flashscore"
        
        # Initially, all flags should be disabled
        is_enabled = migrated_repo.is_adaptive_enabled(sport, site)
        assert is_enabled is False, f"Adaptive should be disabled for {sport}@{site}"
        
        # Enable site-specific flag
        migrated_repo.update_feature_flag(sport, site, enabled=True)
        
        # Now it should be enabled
        is_enabled = migrated_repo.is_adaptive_enabled(sport, site)
        assert is_enabled is True, f"Adaptive should be enabled for {sport}@{site} after enabling site flag"
        
        # Disable site flag and enable global flag
        migrated_repo.update_feature_flag(sport, site, enabled=False)
        migrated_repo.update_feature_flag(sport, None, enabled=True)
        
        # Should still be enabled due to global flag
        is_enabled = migrated_repo.is_adaptive_enabled(sport, site)
        assert is_enabled is True, f"Adaptive should be enabled for {sport}@{site} due to global flag"
        
        # Disable global flag
        migrated_repo.update_feature_flag(sport, None, enabled=False)
        
        # Should be disabled again
        is_enabled = migrated_repo.is_adaptive_enabled(sport, site)
        assert is_enabled is False, f"Adaptive should be disabled for {sport}@{site} when both flags are disabled"
    
    def test_unique_constraints_maintained(self, migrated_repo):
        """Test that unique constraints are maintained with seed data."""
        all_flags = migrated_repo.get_all_feature_flags()
        
        # Check for duplicates in sport+site combinations
        seen_combinations = set()
        for flag in all_flags:
            combination = (flag.sport, flag.site)
            assert combination not in seen_combinations, f"Duplicate combination found: {combination}"
            seen_combinations.add(combination)
        
        # Should have exactly 40 unique combinations
        assert len(seen_combinations) == 40, f"Expected 40 unique combinations, got {len(seen_combinations)}"


@pytest.mark.integration
class TestMigrationFileExists:
    """Test that migration file exists and is readable."""
    
    def test_migration_file_exists(self):
        """Test that 002_add_site_flags.sql migration file exists."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/selectors/adaptive/db/migrations/002_add_site_flags.sql"
        )
        
        assert os.path.exists(migration_path), f"Migration file not found: {migration_path}"
    
    def test_migration_file_readable(self):
        """Test that migration file is readable and contains expected content."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/selectors/adaptive/db/migrations/002_add_site_flags.sql"
        )
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        # Check for expected content
        assert "INSERT INTO feature_flags" in content
        assert "flashscore" in content
        assert "bet365" in content
        assert "williamhill" in content
        assert "FALSE" in content  # All flags disabled by default
