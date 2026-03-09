"""
Repository for managing approval weights in the database.

This repository handles persistence of learned approval weights from Epic 5
so that the learning persists across service restarts.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..models.recipe import Base
from ..models.weights import ApprovalWeight, SelectorApprovalHistory, RejectionWeight, SelectorRejectionHistory, GenerationData


class WeightRepository:
    """Repository for managing approval weights in SQLite database.
    
    Provides CRUD operations for storing and retrieving learned approval weights.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the repository.
        
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
    
    def upsert_approval_weight(
        self,
        strategy_type: str,
        approval_count: int,
        total_boost: float,
        related_boost: float = 0.0,
    ) -> ApprovalWeight:
        """Insert or update an approval weight record.
        
        Args:
            strategy_type: The strategy type
            approval_count: Number of approvals
            total_boost: Direct boost from approvals
            related_boost: Boost from related strategies
            
        Returns:
            The created or updated ApprovalWeight
        """
        with self._get_session() as session:
            # Try to find existing record
            result = session.execute(
                select(ApprovalWeight).where(
                    ApprovalWeight.strategy_type == strategy_type
                )
            )
            existing = result.scalar_one_or_none()
            
            now = datetime.utcnow()
            
            if existing:
                # Update existing record
                existing.approval_count = approval_count
                existing.total_boost = total_boost
                existing.related_boost = related_boost
                existing.last_approval = now
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # Create new record
                new_weight = ApprovalWeight(
                    strategy_type=strategy_type,
                    approval_count=approval_count,
                    total_boost=total_boost,
                    related_boost=related_boost,
                    first_approval=now,
                    last_approval=now,
                    updated_at=now,
                )
                session.add(new_weight)
                session.commit()
                session.refresh(new_weight)
                return new_weight
    
    def get_all_weights(self) -> List[ApprovalWeight]:
        """Get all approval weights.
        
        Returns:
            List of all ApprovalWeight records
        """
        with self._get_session() as session:
            result = session.execute(select(ApprovalWeight))
            return list(result.scalars().all())
    
    def get_weight_by_strategy(self, strategy_type: str) -> Optional[ApprovalWeight]:
        """Get approval weight for a specific strategy.
        
        Args:
            strategy_type: The strategy type to look up
            
        Returns:
            ApprovalWeight if found, None otherwise
        """
        with self._get_session() as session:
            result = session.execute(
                select(ApprovalWeight).where(
                    ApprovalWeight.strategy_type == strategy_type
                )
            )
            return result.scalar_one_or_none()
    
    def load_weights_for_scorer(self) -> Dict[str, Any]:
        """Load all weights in format suitable for ConfidenceScorer.
        
        Returns:
            Dictionary mapping strategy types to their weight data
        """
        weights = self.get_all_weights()
        
        result = {}
        for weight in weights:
            result[weight.strategy_type] = {
                'count': weight.approval_count,
                'total_boost': weight.total_boost,
                'related_boost': weight.related_boost,
                'last_approval': weight.last_approval.isoformat() if weight.last_approval else None,
            }
        
        return result
    
    def save_approval_history(
        self,
        selector_string: str,
        strategy_type: str,
        confidence_at_approval: Optional[float] = None,
        boosted_confidence: Optional[float] = None,
        failure_id: Optional[int] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        approved_by: Optional[str] = None,
        approval_notes: Optional[str] = None,
    ) -> SelectorApprovalHistory:
        """Save an individual selector approval to history.
        
        Args:
            selector_string: The approved selector
            strategy_type: Strategy type used
            confidence_at_approval: Original confidence
            boosted_confidence: Confidence after boost
            failure_id: Associated failure ID
            sport: Sport context
            site: Site context
            approved_by: User who approved
            approval_notes: Notes from approver
            
        Returns:
            The created SelectorApprovalHistory record
        """
        with self._get_session() as session:
            history = SelectorApprovalHistory(
                selector_string=selector_string,
                strategy_type=strategy_type,
                confidence_at_approval=confidence_at_approval,
                boosted_confidence=boosted_confidence,
                failure_id=failure_id,
                sport=sport,
                site=site,
                approved_by=approved_by,
                approval_notes=approval_notes,
                approved_at=datetime.utcnow(),
            )
            
            session.add(history)
            session.commit()
            session.refresh(history)
            return history
    
    def get_selector_history(
        self,
        selector_string: Optional[str] = None,
        strategy_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SelectorApprovalHistory]:
        """Get selector approval history.
        
        Args:
            selector_string: Optional selector to filter by
            strategy_type: Optional strategy type to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of SelectorApprovalHistory records
        """
        with self._get_session() as session:
            query = select(SelectorApprovalHistory).order_by(
                SelectorApprovalHistory.approved_at.desc()
            ).limit(limit)
            
            if selector_string:
                query = query.where(
                    SelectorApprovalHistory.selector_string == selector_string
                )
            if strategy_type:
                query = query.where(
                    SelectorApprovalHistory.strategy_type == strategy_type
                )
            
            result = session.execute(query)
            return list(result.scalars().all())

    # ==================== REJECTION WEIGHT METHODS ====================
    
    def upsert_rejection_weight(
        self,
        strategy_type: str,
        rejection_count: int,
        total_penalty: float,
        related_penalty: float = 0.0,
    ) -> RejectionWeight:
        """Insert or update a rejection weight record.
        
        Args:
            strategy_type: The strategy type
            rejection_count: Number of rejections
            total_penalty: Direct penalty from rejections
            related_penalty: Penalty from related strategies
            
        Returns:
            The created or updated RejectionWeight
        """
        with self._get_session() as session:
            result = session.execute(
                select(RejectionWeight).where(
                    RejectionWeight.strategy_type == strategy_type
                )
            )
            existing = result.scalar_one_or_none()
            
            now = datetime.utcnow()
            
            if existing:
                existing.rejection_count = rejection_count
                existing.total_penalty = total_penalty
                existing.related_penalty = related_penalty
                existing.last_rejection = now
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return existing
            else:
                new_weight = RejectionWeight(
                    strategy_type=strategy_type,
                    rejection_count=rejection_count,
                    total_penalty=total_penalty,
                    related_penalty=related_penalty,
                    first_rejection=now,
                    last_rejection=now,
                    updated_at=now,
                )
                session.add(new_weight)
                session.commit()
                session.refresh(new_weight)
                return new_weight
    
    def get_all_rejection_weights(self) -> List[RejectionWeight]:
        """Get all rejection weights.
        
        Returns:
            List of all RejectionWeight records
        """
        with self._get_session() as session:
            result = session.execute(select(RejectionWeight))
            return list(result.scalars().all())
    
    def get_rejection_weight_by_strategy(self, strategy_type: str) -> Optional[RejectionWeight]:
        """Get rejection weight for a specific strategy.
        
        Args:
            strategy_type: The strategy type to look up
            
        Returns:
            RejectionWeight if found, None otherwise
        """
        with self._get_session() as session:
            result = session.execute(
                select(RejectionWeight).where(
                    RejectionWeight.strategy_type == strategy_type
                )
            )
            return result.scalar_one_or_none()
    
    def load_rejection_weights_for_scorer(self) -> Dict[str, Any]:
        """Load all rejection weights in format suitable for ConfidenceScorer.
        
        Returns:
            Dictionary mapping strategy types to their rejection weight data
        """
        weights = self.get_all_rejection_weights()
        
        result = {}
        for weight in weights:
            result[weight.strategy_type] = {
                'count': weight.rejection_count,
                'total_penalty': weight.total_penalty,
                'related_penalty': weight.related_penalty,
                'last_rejection': weight.last_rejection.isoformat() if weight.last_rejection else None,
            }
        
        return result
    
    def save_rejection_history(
        self,
        selector_string: str,
        strategy_type: str,
        confidence_at_rejection: Optional[float] = None,
        penalized_confidence: Optional[float] = None,
        rejection_reason: Optional[str] = None,
        reason_pattern: Optional[str] = None,
        failure_id: Optional[int] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        rejected_by: Optional[str] = None,
        rejection_notes: Optional[str] = None,
    ) -> SelectorRejectionHistory:
        """Save an individual selector rejection to history.
        
        Args:
            selector_string: The rejected selector
            strategy_type: Strategy type used
            confidence_at_rejection: Original confidence
            penalized_confidence: Confidence after penalty
            rejection_reason: Human-provided rejection reason
            reason_pattern: Parsed reason pattern
            failure_id: Associated failure ID
            sport: Sport context
            site: Site context
            rejected_by: User who rejected
            rejection_notes: Notes from rejecter
            
        Returns:
            The created SelectorRejectionHistory record
        """
        with self._get_session() as session:
            history = SelectorRejectionHistory(
                selector_string=selector_string,
                strategy_type=strategy_type,
                confidence_at_rejection=confidence_at_rejection,
                penalized_confidence=penalized_confidence,
                rejection_reason=rejection_reason,
                reason_pattern=reason_pattern,
                failure_id=failure_id,
                sport=sport,
                site=site,
                rejected_by=rejected_by,
                rejection_notes=rejection_notes,
                rejected_at=datetime.utcnow(),
            )
            
            session.add(history)
            session.commit()
            session.refresh(history)
            return history
    
    def get_rejection_history(
        self,
        selector_string: Optional[str] = None,
        strategy_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SelectorRejectionHistory]:
        """Get selector rejection history.
        
        Args:
            selector_string: Optional selector to filter by
            strategy_type: Optional strategy type to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of SelectorRejectionHistory records
        """
        with self._get_session() as session:
            query = select(SelectorRejectionHistory).order_by(
                SelectorRejectionHistory.rejected_at.desc()
            ).limit(limit)
            
            if selector_string:
                query = query.where(
                    SelectorRejectionHistory.selector_string == selector_string
                )
            if strategy_type:
                query = query.where(
                    SelectorRejectionHistory.strategy_type == strategy_type
                )
            
            result = session.execute(query)
            return list(result.scalars().all())

    # ==================== GENERATION DATA METHODS (STORY 5.3) ====================
    
    def upsert_generation_data(
        self,
        recipe_id: str,
        current_generation: int = 1,
        generations_survived: int = 0,
        generation_failures: int = 0,
        consecutive_failures: int = 0,
        sport: Optional[str] = None,
        site: Optional[str] = None,
    ) -> GenerationData:
        """Insert or update a generation data record.
        
        Args:
            recipe_id: The recipe identifier
            current_generation: Current generation number
            generations_survived: Number of generations survived
            generation_failures: Total number of generation failures
            consecutive_failures: Consecutive failure count
            sport: Optional sport context
            site: Optional site context
            
        Returns:
            The created or updated GenerationData
        """
        with self._get_session() as session:
            result = session.execute(
                select(GenerationData).where(
                    GenerationData.recipe_id == recipe_id
                )
            )
            existing = result.scalar_one_or_none()
            
            now = datetime.utcnow()
            
            if existing:
                # Update existing record
                existing.current_generation = current_generation
                existing.generations_survived = generations_survived
                existing.generation_failures = generation_failures
                existing.consecutive_failures = consecutive_failures
                existing.sport = sport
                existing.site = site
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # Create new record
                new_data = GenerationData(
                    recipe_id=recipe_id,
                    current_generation=current_generation,
                    generations_survived=generations_survived,
                    generation_failures=generation_failures,
                    consecutive_failures=consecutive_failures,
                    sport=sport,
                    site=site,
                    first_generation=now,
                    last_generation_change=now,
                    updated_at=now,
                )
                session.add(new_data)
                session.commit()
                session.refresh(new_data)
                return new_data
    
    def get_generation_data(self, recipe_id: str) -> Optional[GenerationData]:
        """Get generation data for a specific recipe.
        
        Args:
            recipe_id: The recipe identifier
            
        Returns:
            GenerationData if found, None otherwise
        """
        with self._get_session() as session:
            result = session.execute(
                select(GenerationData).where(
                    GenerationData.recipe_id == recipe_id
                )
            )
            return result.scalar_one_or_none()
    
    def get_all_generation_data(self) -> List[GenerationData]:
        """Get all generation data records.
        
        Returns:
            List of all GenerationData records
        """
        with self._get_session() as session:
            result = session.execute(select(GenerationData))
            return list(result.scalars().all())
    
    def load_generation_data_for_scorer(self) -> Dict[str, Any]:
        """Load all generation data in format suitable for ConfidenceScorer.
        
        Returns:
            Dictionary mapping recipe IDs to their generation data
        """
        gen_data = self.get_all_generation_data()
        
        result = {}
        for data in gen_data:
            result[data.recipe_id] = {
                'current_generation': data.current_generation,
                'generations_survived': data.generations_survived,
                'generation_failures': data.generation_failures,
                'consecutive_failures': data.consecutive_failures,
                'sport': data.sport,
                'site': data.site,
                'first_generation': data.first_generation.isoformat() if data.first_generation else None,
                'last_generation_change': data.last_generation_change.isoformat() if data.last_generation_change else None,
            }
        
        return result
    
    def delete_generation_data(self, recipe_id: str) -> bool:
        """Delete generation data for a recipe.
        
        Args:
            recipe_id: The recipe identifier
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            result = session.execute(
                select(GenerationData).where(
                    GenerationData.recipe_id == recipe_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                session.delete(existing)
                session.commit()
                return True
            return False


# Module-level instance
_weight_repository: Optional[WeightRepository] = None


def get_weight_repository(db_path: Optional[str] = None) -> WeightRepository:
    """Get the weight repository instance.
    
    Args:
        db_path: Optional database path
        
    Returns:
        WeightRepository instance
    """
    global _weight_repository
    if _weight_repository is None:
        _weight_repository = WeightRepository(db_path)
    return _weight_repository
