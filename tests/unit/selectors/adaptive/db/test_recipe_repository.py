"""
Unit tests for RecipeRepository.
"""

import pytest
from typing import Dict, Any

from src.selectors.adaptive.db.repositories.recipe_repository import RecipeRepository


class TestRecipeRepository:
    """Test suite for RecipeRepository."""
    
    @pytest.fixture
    def repository(self):
        """Create in-memory repository for testing."""
        repo = RecipeRepository(db_path=":memory:")
        yield repo
        repo.close()
    
    @pytest.fixture
    def sample_selectors(self) -> Dict[str, Any]:
        """Sample selector configuration."""
        return {
            "primary": {
                "css": ".main-content",
                "xpath": "//div[@class='main']"
            },
            "fallback": {
                "text": "Click here"
            }
        }
    
    def test_create_recipe(self, repository, sample_selectors):
        """Test creating a new recipe (version 1)."""
        recipe = repository.create_recipe(
            recipe_id="recipe-1",
            selectors=sample_selectors,
        )
        
        assert recipe is not None
        assert recipe.recipe_id == "recipe-1"
        assert recipe.version == 1
        assert recipe.selectors == sample_selectors
        assert recipe.created_at is not None
    
    def test_create_recipe_with_all_fields(self, repository, sample_selectors):
        """Test creating a recipe with all optional fields."""
        recipe = repository.create_recipe(
            recipe_id="recipe-2",
            selectors=sample_selectors,
            parent_recipe_id=None,
            generation=1,
            stability_score=0.85,
        )
        
        assert recipe.generation == 1
        assert recipe.stability_score == 0.85
    
    def test_create_new_version(self, repository, sample_selectors):
        """Test creating a new version of an existing recipe."""
        # Create initial recipe
        recipe_v1 = repository.create_recipe(
            recipe_id="recipe-3",
            selectors=sample_selectors,
        )
        assert recipe_v1.version == 1
        
        # Create new version
        updated_selectors = {"primary": {"css": ".updated-content"}}
        recipe_v2 = repository.create_new_version(
            recipe_id="recipe-3",
            selectors=updated_selectors,
            parent_recipe_id="recipe-3",
            generation=2,
            stability_score=0.9,
        )
        
        assert recipe_v2.version == 2
        assert recipe_v2.selectors == updated_selectors
        assert recipe_v2.parent_recipe_id == "recipe-3"
        assert recipe_v2.generation == 2
        assert recipe_v2.stability_score == 0.9
    
    def test_get_by_id_latest_version(self, repository, sample_selectors):
        """Test retrieving the latest version of a recipe."""
        # Create two versions
        repository.create_recipe(
            recipe_id="recipe-4",
            selectors=sample_selectors,
        )
        repository.create_new_version(
            recipe_id="recipe-4",
            selectors={"primary": {"css": ".v2"}},
        )
        
        # Get latest version
        latest = repository.get_by_id("recipe-4")
        
        assert latest is not None
        assert latest.version == 2
    
    def test_get_by_id_specific_version(self, repository, sample_selectors):
        """Test retrieving a specific version of a recipe."""
        # Create two versions
        repository.create_recipe(
            recipe_id="recipe-5",
            selectors=sample_selectors,
        )
        repository.create_new_version(
            recipe_id="recipe-5",
            selectors={"primary": {"css": ".v2"}},
        )
        
        # Get version 1
        v1 = repository.get_by_id("recipe-5", version=1)
        
        assert v1 is not None
        assert v1.version == 1
        assert v1.selectors == sample_selectors
    
    def test_get_by_id_not_found(self, repository):
        """Test retrieving a non-existent recipe."""
        result = repository.get_by_id("non-existent")
        assert result is None
    
    def test_get_version_history(self, repository, sample_selectors):
        """Test retrieving complete version history."""
        # Create multiple versions
        repository.create_recipe(
            recipe_id="recipe-6",
            selectors=sample_selectors,
        )
        repository.create_new_version(
            recipe_id="recipe-6",
            selectors={"v": 2},
        )
        repository.create_new_version(
            recipe_id="recipe-6",
            selectors={"v": 3},
        )
        
        history = repository.get_version_history("recipe-6")
        
        assert len(history) == 3
        assert history[0].version == 1
        assert history[1].version == 2
        assert history[2].version == 3
    
    def test_get_latest_version(self, repository, sample_selectors):
        """Test getting the latest version of a recipe."""
        repository.create_recipe(
            recipe_id="recipe-7",
            selectors=sample_selectors,
        )
        repository.create_new_version(
            recipe_id="recipe-7",
            selectors={"v": 2},
        )
        
        latest = repository.get_latest_version("recipe-7")
        
        assert latest.version == 2
    
    def test_update_stability_score(self, repository, sample_selectors):
        """Test updating stability score."""
        recipe = repository.create_recipe(
            recipe_id="recipe-8",
            selectors=sample_selectors,
        )
        assert recipe.stability_score is None
        
        updated = repository.update_stability_score("recipe-8", 0.75)
        
        assert updated.stability_score == 0.75
        
        # Verify it persists
        retrieved = repository.get_by_id("recipe-8")
        assert retrieved.stability_score == 0.75
    
    def test_delete_recipe_specific_version(self, repository, sample_selectors):
        """Test deleting a specific version."""
        repository.create_recipe(
            recipe_id="recipe-9",
            selectors=sample_selectors,
        )
        repository.create_new_version(
            recipe_id="recipe-9",
            selectors={"v": 2},
        )
        
        # Delete version 1
        result = repository.delete_recipe("recipe-9", version=1)
        
        assert result is True
        # Version 2 should still exist
        v2 = repository.get_by_id("recipe-9", version=2)
        assert v2 is not None
    
    def test_delete_recipe_all_versions(self, repository, sample_selectors):
        """Test deleting all versions of a recipe."""
        repository.create_recipe(
            recipe_id="recipe-10",
            selectors=sample_selectors,
        )
        repository.create_new_version(
            recipe_id="recipe-10",
            selectors={"v": 2},
        )
        
        # Delete all versions
        result = repository.delete_recipe("recipe-10")
        
        assert result is True
        assert repository.get_by_id("recipe-10") is None
    
    def test_list_all_recipes(self, repository, sample_selectors):
        """Test listing all unique recipe IDs."""
        repository.create_recipe(recipe_id="recipe-a", selectors=sample_selectors)
        repository.create_recipe(recipe_id="recipe-b", selectors=sample_selectors)
        repository.create_recipe(recipe_id="recipe-c", selectors=sample_selectors)
        
        # Add another version to recipe-a
        repository.create_new_version(recipe_id="recipe-a", selectors={})
        
        recipes = repository.list_all_recipes()
        
        assert len(recipes) == 3
        assert "recipe-a" in recipes
        assert "recipe-b" in recipes
        assert "recipe-c" in recipes
    
    def test_create_new_version_increments_version(self, repository, sample_selectors):
        """Test that create_new_version increments version number correctly."""
        # Create initial recipe
        v1 = repository.create_recipe(
            recipe_id="recipe-11",
            selectors=sample_selectors,
        )
        
        # Create 5 new versions
        for i in range(5):
            new_recipe = repository.create_new_version(
                recipe_id="recipe-11",
                selectors={"version": i + 2},
            )
            assert new_recipe.version == i + 2
        
        # Verify total version count
        history = repository.get_version_history("recipe-11")
        assert len(history) == 6
        assert history[-1].version == 6
    
    # Tests for stability tracking methods
    def test_update_stability_on_success(self, repository, sample_selectors):
        """Test updating stability on successful resolution."""
        recipe = repository.create_recipe(
            recipe_id="recipe-stability-1",
            selectors=sample_selectors,
        )
        
        # Initial state
        assert recipe.success_count is None or recipe.success_count == 0
        assert recipe.consecutive_failures is None or recipe.consecutive_failures == 0
        
        # Update on success
        updated = repository.update_stability_on_success("recipe-stability-1")
        
        assert updated.success_count == 1
        assert updated.consecutive_failures == 0
        assert updated.last_successful_resolution is not None
    
    def test_update_stability_on_success_multiple(self, repository, sample_selectors):
        """Test multiple successes accumulate correctly."""
        repository.create_recipe(
            recipe_id="recipe-stability-2",
            selectors=sample_selectors,
        )
        
        # Multiple successes
        repository.update_stability_on_success("recipe-stability-2")
        repository.update_stability_on_success("recipe-stability-2")
        repository.update_stability_on_success("recipe-stability-2")
        
        recipe = repository.get_by_id("recipe-stability-2")
        assert recipe.success_count == 3
    
    def test_update_stability_on_failure(self, repository, sample_selectors):
        """Test updating stability on failed resolution."""
        recipe = repository.create_recipe(
            recipe_id="recipe-stability-3",
            selectors=sample_selectors,
        )
        
        # Update on failure
        updated = repository.update_stability_on_failure(
            "recipe-stability-3",
            severity="moderate"
        )
        
        assert updated.failure_count == 1
        assert updated.consecutive_failures == 1
        assert updated.last_failure_timestamp is not None
        assert updated.failure_severity == "moderate"
    
    def test_update_stability_on_failure_severity_escalation(self, repository, sample_selectors):
        """Test failure severity escalation (higher severity overwrites lower)."""
        repository.create_recipe(
            recipe_id="recipe-stability-4",
            selectors=sample_selectors,
        )
        
        # First failure - minor
        repository.update_stability_on_failure("recipe-stability-4", severity="minor")
        recipe = repository.get_by_id("recipe-stability-4")
        assert recipe.failure_severity == "minor"
        
        # Second failure - critical (should overwrite minor)
        repository.update_stability_on_failure("recipe-stability-4", severity="critical")
        recipe = repository.get_by_id("recipe-stability-4")
        assert recipe.failure_severity == "critical"
    
    def test_update_stability_on_failure_severity_no_escalation(self, repository, sample_selectors):
        """Test failure severity doesn't downgrade (lower severity doesn't overwrite higher)."""
        repository.create_recipe(
            recipe_id="recipe-stability-5",
            selectors=sample_selectors,
        )
        
        # First failure - critical
        repository.update_stability_on_failure("recipe-stability-5", severity="critical")
        recipe = repository.get_by_id("recipe-stability-5")
        assert recipe.failure_severity == "critical"
        
        # Second failure - minor (should NOT overwrite critical)
        repository.update_stability_on_failure("recipe-stability-5", severity="minor")
        recipe = repository.get_by_id("recipe-stability-5")
        assert recipe.failure_severity == "critical"
    
    def test_consecutive_failures_accumulate(self, repository, sample_selectors):
        """Test consecutive failures accumulate correctly and reset on success."""
        repository.create_recipe(
            recipe_id="recipe-stability-6",
            selectors=sample_selectors,
        )
        
        # Multiple failures
        repository.update_stability_on_failure("recipe-stability-6", severity="minor")
        repository.update_stability_on_failure("recipe-stability-6", severity="minor")
        repository.update_stability_on_failure("recipe-stability-6", severity="minor")
        
        recipe = repository.get_by_id("recipe-stability-6")
        assert recipe.consecutive_failures == 3
        
        # Success should reset consecutive failures
        repository.update_stability_on_success("recipe-stability-6")
        
        recipe = repository.get_by_id("recipe-stability-6")
        assert recipe.consecutive_failures == 0
    
    def test_increment_generations_survived(self, repository, sample_selectors):
        """Test incrementing generations survived."""
        recipe = repository.create_recipe(
            recipe_id="recipe-stability-7",
            selectors=sample_selectors,
        )
        
        assert recipe.generations_survived is None or recipe.generations_survived == 0
        
        # Increment generations
        repository.increment_generations_survived("recipe-stability-7")
        recipe = repository.get_by_id("recipe-stability-7")
        assert recipe.generations_survived == 1
        
        # Increment again
        repository.increment_generations_survived("recipe-stability-7")
        recipe = repository.get_by_id("recipe-stability-7")
        assert recipe.generations_survived == 2
    
    def test_get_stability_rankings(self, repository, sample_selectors):
        """Test getting recipes ordered by stability score."""
        # Create recipes with different stability scores
        repository.create_recipe(
            recipe_id="recipe-rank-1",
            selectors=sample_selectors,
            stability_score=0.5,
        )
        repository.create_recipe(
            recipe_id="recipe-rank-2",
            selectors=sample_selectors,
            stability_score=0.9,
        )
        repository.create_recipe(
            recipe_id="recipe-rank-3",
            selectors=sample_selectors,
            stability_score=0.3,
        )
        
        rankings = repository.get_stability_rankings()
        
        assert len(rankings) == 3
        # Should be ordered descending (highest first)
        assert rankings[0].stability_score == 0.9
        assert rankings[1].stability_score == 0.5
        assert rankings[2].stability_score == 0.3
    
    def test_get_stability_rankings_with_limit(self, repository, sample_selectors):
        """Test getting top N recipes by stability score."""
        for i in range(5):
            repository.create_recipe(
                recipe_id=f"recipe-rank-{i}",
                selectors=sample_selectors,
                stability_score=0.1 * i,
            )
        
        rankings = repository.get_stability_rankings(limit=3)
        
        assert len(rankings) == 3
        assert rankings[0].stability_score == 0.4  # Highest
    
    def test_get_stability_rankings_nulls_last(self, repository, sample_selectors):
        """Test that recipes with null stability scores come last."""
        repository.create_recipe(
            recipe_id="recipe-null-1",
            selectors=sample_selectors,
            stability_score=0.8,
        )
        repository.create_recipe(
            recipe_id="recipe-null-2",
            selectors=sample_selectors,
            stability_score=None,
        )
        repository.create_recipe(
            recipe_id="recipe-null-3",
            selectors=sample_selectors,
            stability_score=0.5,
        )
        
        rankings = repository.get_stability_rankings()
        
        assert len(rankings) == 3
        # Items with scores should come before nulls
        assert rankings[0].recipe_id == "recipe-null-1"
        assert rankings[1].recipe_id == "recipe-null-3"
