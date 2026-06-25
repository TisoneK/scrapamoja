"""
Recipe repository for database CRUD operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..models.recipe import Base, Recipe


class RecipeRepository:
    """
    Repository for managing recipe versions in SQLite database.
    
    Provides CRUD operations for recipe versioning and history tracking.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the recipe repository.
        
        Args:
            db_path: Optional path to SQLite database file.
                    If not provided, uses ':memory:' for testing.
        """
        if db_path is None:
            db_path = ":memory:"
        
        self.db_path = db_path
        # Create engine with check_same_thread=False for SQLite
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False} if db_path != ":memory:" else {}
        )
        # Create tables
        Base.metadata.create_all(self.engine)
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def create_recipe(
        self,
        recipe_id: str,
        selectors: Dict[str, Any],
        version: int = 1,
        parent_recipe_id: Optional[str] = None,
        generation: Optional[int] = None,
        stability_score: Optional[float] = None,
    ) -> Recipe:
        """
        Create a new recipe (version 1).
        
        Args:
            recipe_id: Unique identifier for the recipe
            selectors: Selector configuration data
            version: Version number (default 1)
            parent_recipe_id: Reference to parent recipe if this is derived
            generation: Recipe generation number
            stability_score: Stability score (0.0 - 1.0)
            
        Returns:
            Created Recipe instance
        """
        with self._get_session() as session:
            recipe = Recipe(
                recipe_id=recipe_id,
                version=version,
                selectors=selectors,
                parent_recipe_id=parent_recipe_id,
                generation=generation,
                stability_score=stability_score,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(recipe)
            session.commit()
            session.refresh(recipe)
            return recipe
    
    def create_new_version(
        self,
        recipe_id: str,
        selectors: Dict[str, Any],
        parent_recipe_id: Optional[str] = None,
        generation: Optional[int] = None,
        stability_score: Optional[float] = None,
    ) -> Recipe:
        """
        Create a new version of an existing recipe.
        
        Increments the version number and sets parent_recipe_id to reference
        the previous version.
        
        Args:
            recipe_id: Unique identifier for the recipe
            selectors: Updated selector configuration data
            parent_recipe_id: Reference to parent recipe
            generation: Recipe generation number
            stability_score: Updated stability score
            
        Returns:
            Created Recipe instance with incremented version
        """
        with self._get_session() as session:
            # Get the latest version for this recipe
            latest = session.execute(
                select(Recipe)
                .where(Recipe.recipe_id == recipe_id)
                .order_by(Recipe.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            # Determine new version number
            new_version = (latest.version + 1) if latest else 1
            
            recipe = Recipe(
                recipe_id=recipe_id,
                version=new_version,
                selectors=selectors,
                parent_recipe_id=parent_recipe_id,
                generation=generation,
                stability_score=stability_score,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(recipe)
            session.commit()
            session.refresh(recipe)
            return recipe
    
    def get_by_id(self, recipe_id: str, version: Optional[int] = None) -> Optional[Recipe]:
        """
        Retrieve a recipe by ID and optionally version.
        
        Args:
            recipe_id: Unique identifier for the recipe
            version: Optional specific version to retrieve.
                    If not provided, returns the latest version.
                    
        Returns:
            Recipe instance if found, None otherwise
        """
        with self._get_session() as session:
            query = select(Recipe).where(Recipe.recipe_id == recipe_id)
            
            if version is not None:
                query = query.where(Recipe.version == version)
            else:
                query = query.order_by(Recipe.version.desc())
            
            # Use .scalars().first() instead of .scalar_one_or_none() when getting latest version
            # because there may be multiple versions without version filter
            if version is None:
                return session.execute(query).scalars().first()
            return session.execute(query).scalar_one_or_none()
    
    def get_version_history(self, recipe_id: str) -> List[Recipe]:
        """
        Get the complete version history for a recipe.
        
        Returns all versions ordered by version number (ascending).
        
        Args:
            recipe_id: Unique identifier for the recipe
            
        Returns:
            List of Recipe instances ordered by version
        """
        with self._get_session() as session:
            return list(
                session.execute(
                    select(Recipe)
                    .where(Recipe.recipe_id == recipe_id)
                    .order_by(Recipe.version.asc())
                ).scalars().all()
            )
    
    def get_latest_version(self, recipe_id: str) -> Optional[Recipe]:
        """
        Get the latest version of a recipe.
        
        Args:
            recipe_id: Unique identifier for the recipe
            
        Returns:
            Latest Recipe instance if found, None otherwise
        """
        with self._get_session() as session:
            return session.execute(
                select(Recipe)
                .where(Recipe.recipe_id == recipe_id)
                .order_by(Recipe.version.desc())
                .limit(1)
            ).scalar_one_or_none()
    
    def update_stability_score(
        self, 
        recipe_id: str, 
        stability_score: float,
        version: Optional[int] = None
    ) -> Optional[Recipe]:
        """
        Update the stability score for a recipe.
        
        Args:
            recipe_id: Unique identifier for the recipe
            stability_score: New stability score (0.0 - 1.0)
            version: Optional specific version to update.
                    If not provided, updates the latest version.
                    
        Returns:
            Updated Recipe instance if found, None otherwise
        """
        with self._get_session() as session:
            # Get the recipe within the same session
            query = select(Recipe).where(Recipe.recipe_id == recipe_id)
            if version is not None:
                query = query.where(Recipe.version == version)
                recipe = session.execute(query).scalar_one_or_none()
            else:
                query = query.order_by(Recipe.version.desc())
                recipe = session.execute(query).scalars().first()
            
            if recipe:
                recipe.stability_score = stability_score
                recipe.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(recipe)
            
            return recipe
    
    def update_stability_on_success(
        self,
        recipe_id: str,
        version: Optional[int] = None
    ) -> Optional[Recipe]:
        """
        Update stability metrics when a selector resolves successfully.
        
        Increments success_count, resets consecutive_failures to 0,
        and updates last_successful_resolution timestamp.
        
        Args:
            recipe_id: Unique identifier for the recipe
            version: Optional specific version to update.
                    If not provided, updates the latest version.
                    
        Returns:
            Updated Recipe instance if found, None otherwise
        """
        with self._get_session() as session:
            query = select(Recipe).where(Recipe.recipe_id == recipe_id)
            if version is not None:
                query = query.where(Recipe.version == version)
                recipe = session.execute(query).scalar_one_or_none()
            else:
                query = query.order_by(Recipe.version.desc())
                recipe = session.execute(query).scalars().first()
            
            if recipe:
                # Increment success count
                recipe.success_count = (recipe.success_count or 0) + 1
                # Reset consecutive failures
                recipe.consecutive_failures = 0
                # Update last successful resolution timestamp
                recipe.last_successful_resolution = datetime.utcnow()
                recipe.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(recipe)
            
            return recipe
    
    def update_stability_on_failure(
        self,
        recipe_id: str,
        severity: str = "minor",
        version: Optional[int] = None
    ) -> Optional[Recipe]:
        """
        Update stability metrics when a selector fails.
        
        Increments failure_count and consecutive_failures, updates
        last_failure_timestamp and failure_severity (if higher than current).
        
        Args:
            recipe_id: Unique identifier for the recipe
            severity: Failure severity level ("minor", "moderate", "critical")
            version: Optional specific version to update.
                    If not provided, updates the latest version.
                    
        Returns:
            Updated Recipe instance if found, None otherwise
        """
        # Severity ordering for comparison
        severity_order = {"minor": 1, "moderate": 2, "critical": 3}
        
        with self._get_session() as session:
            query = select(Recipe).where(Recipe.recipe_id == recipe_id)
            if version is not None:
                query = query.where(Recipe.version == version)
                recipe = session.execute(query).scalar_one_or_none()
            else:
                query = query.order_by(Recipe.version.desc())
                recipe = session.execute(query).scalars().first()
            
            if recipe:
                # Increment failure counts
                recipe.failure_count = (recipe.failure_count or 0) + 1
                recipe.consecutive_failures = (recipe.consecutive_failures or 0) + 1
                
                # Update last failure timestamp
                recipe.last_failure_timestamp = datetime.utcnow()
                
                # Update failure severity if higher than current
                current_severity = recipe.failure_severity
                current_severity_level = severity_order.get(current_severity, 0) if current_severity else 0
                new_severity_level = severity_order.get(severity, 1)
                
                if new_severity_level > current_severity_level:
                    recipe.failure_severity = severity
                
                recipe.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(recipe)
            
            return recipe
    
    def increment_generations_survived(
        self,
        recipe_id: str,
        version: Optional[int] = None
    ) -> Optional[Recipe]:
        """
        Increment generations_survived when a recipe survives a layout generation change.
        
        Args:
            recipe_id: Unique identifier for the recipe
            version: Optional specific version to update.
                    If not provided, updates the latest version.
                    
        Returns:
            Updated Recipe instance if found, None otherwise
        """
        with self._get_session() as session:
            query = select(Recipe).where(Recipe.recipe_id == recipe_id)
            if version is not None:
                query = query.where(Recipe.version == version)
                recipe = session.execute(query).scalar_one_or_none()
            else:
                query = query.order_by(Recipe.version.desc())
                recipe = session.execute(query).scalars().first()
            
            if recipe:
                recipe.generations_survived = (recipe.generations_survived or 0) + 1
                recipe.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(recipe)
            
            return recipe
    
    def get_stability_rankings(
        self,
        recipe_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Recipe]:
        """
        Get recipes ordered by stability score (highest first).
        
        Args:
            recipe_id: Optional filter for specific recipe_id
            limit: Optional limit on number of results
            
        Returns:
            List of Recipe instances ordered by stability_score descending
        """
        with self._get_session() as session:
            query = select(Recipe).order_by(Recipe.stability_score.desc().nullslast())
            
            if recipe_id is not None:
                query = query.where(Recipe.recipe_id == recipe_id)
            
            if limit is not None:
                query = query.limit(limit)
            
            return list(session.execute(query).scalars().all())
    
    def delete_recipe(self, recipe_id: str, version: Optional[int] = None) -> bool:
        """
        Delete a recipe or specific version.
        
        Args:
            recipe_id: Unique identifier for the recipe
            version: Optional specific version to delete.
                    If not provided, deletes all versions.
                    
        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            query = select(Recipe).where(Recipe.recipe_id == recipe_id)
            
            if version is not None:
                query = query.where(Recipe.version == version)
                recipe = session.execute(query).scalar_one_or_none()
                
                if recipe:
                    session.delete(recipe)
                    session.commit()
                    return True
                return False
            else:
                # Delete all versions
                recipes = session.execute(query).scalars().all()
                if recipes:
                    for recipe in recipes:
                        session.delete(recipe)
                    session.commit()
                    return True
                return False
    
    def list_all_recipes(self) -> List[str]:
        """
        List all unique recipe IDs in the database.
        
        Returns:
            List of unique recipe_id strings
        """
        with self._get_session() as session:
            results = session.execute(
                select(Recipe.recipe_id)
                .distinct()
                .order_by(Recipe.recipe_id)
            ).scalars().all()
            return list(results)
    
    def close(self):
        """Close the database connection."""
        self.engine.dispose()
