"""
Unit tests for Recipe SQLAlchemy model.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.selectors.adaptive.db.models.recipe import Recipe, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestRecipeModel:
    """Test suite for Recipe model."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_recipe_with_required_fields(self, session):
        """Test creating a recipe with required fields only."""
        recipe = Recipe(
            recipe_id="test-recipe-1",
            version=1,
            selectors={"primary": {"css": ".test"}},
        )
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        
        assert recipe.id is not None
        assert recipe.recipe_id == "test-recipe-1"
        assert recipe.version == 1
        assert recipe.selectors == {"primary": {"css": ".test"}}
        assert recipe.created_at is not None
        assert recipe.updated_at is not None
    
    def test_create_recipe_with_all_fields(self, session):
        """Test creating a recipe with all fields."""
        recipe = Recipe(
            recipe_id="test-recipe-2",
            version=1,
            selectors={"primary": {"css": ".test"}},
            parent_recipe_id="test-recipe-1",
            generation=2,
            stability_score=0.85,
        )
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        
        assert recipe.recipe_id == "test-recipe-2"
        assert recipe.parent_recipe_id == "test-recipe-1"
        assert recipe.generation == 2
        assert recipe.stability_score == 0.85
    
    def test_recipe_to_dict(self, session):
        """Test converting recipe to dictionary."""
        recipe = Recipe(
            recipe_id="test-recipe-3",
            version=1,
            selectors={"primary": {"css": ".test"}},
            parent_recipe_id="parent-1",
            generation=1,
            stability_score=0.75,
        )
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        
        result = recipe.to_dict()
        
        assert result["recipe_id"] == "test-recipe-3"
        assert result["version"] == 1
        assert result["selectors"] == {"primary": {"css": ".test"}}
        assert result["parent_recipe_id"] == "parent-1"
        assert result["generation"] == 1
        assert result["stability_score"] == 0.75
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_recipe_from_dict(self):
        """Test creating recipe from dictionary."""
        data = {
            "recipe_id": "test-recipe-4",
            "version": 2,
            "selectors": {"primary": {"css": ".updated"}},
            "parent_recipe_id": "test-recipe-3",
            "generation": 3,
            "stability_score": 0.9,
        }
        
        recipe = Recipe.from_dict(data)
        
        assert recipe.recipe_id == "test-recipe-4"
        assert recipe.version == 2
        assert recipe.selectors == {"primary": {"css": ".updated"}}
        assert recipe.parent_recipe_id == "test-recipe-3"
        assert recipe.generation == 3
        assert recipe.stability_score == 0.9
    
    def test_recipe_repr(self, session):
        """Test recipe string representation."""
        recipe = Recipe(
            recipe_id="test-recipe-5",
            version=1,
            selectors={},
        )
        session.add(recipe)
        session.commit()
        
        assert "test-recipe-5" in repr(recipe)
        assert "1" in repr(recipe)
    
    def test_unique_constraint_recipe_version(self, engine):
        """Test that recipe_id + version must be unique."""
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create first recipe
        recipe1 = Recipe(
            recipe_id="unique-test",
            version=1,
            selectors={},
        )
        session.add(recipe1)
        session.commit()
        
        # Try to create duplicate - should fail
        recipe2 = Recipe(
            recipe_id="unique-test",
            version=1,
            selectors={},
        )
        session.add(recipe2)
        
        with pytest.raises(Exception):
            session.commit()
        
        session.close()
    
    def test_optional_fields_default_to_none(self, session):
        """Test that optional fields default to None."""
        recipe = Recipe(
            recipe_id="test-recipe-6",
            version=1,
            selectors={},
        )
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        
        assert recipe.parent_recipe_id is None
        assert recipe.generation is None
        assert recipe.stability_score is None
