"""
Confidence Query Service for querying selector confidence scores.

This service provides REST-friendly query methods for:
- Single selector confidence query
- Batch selector confidence query
- Paginated all-selectors query
- Default score handling for unknown selectors

Story: 6.1 - Confidence Score Query API
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.selectors.adaptive.db.repositories.failure_event_repository import (
    FailureEventRepository,
)
from src.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConfidenceScoreResult:
    """Result model for single selector confidence query."""

    selector_id: str
    confidence_score: float
    last_updated: datetime
    is_estimated: bool = False


@dataclass
class BatchConfidenceResult:
    """Result model for batch confidence query."""

    results: Dict[str, Optional[ConfidenceScoreResult]] = field(default_factory=dict)
    missing_selectors: List[str] = field(default_factory=list)


@dataclass
class PaginatedConfidenceResult:
    """Result model for paginated confidence query."""

    results: List[ConfidenceScoreResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConfidenceQueryConfig:
    """Configuration for confidence query service."""

    # Default score for selectors with no history
    default_confidence_score: float = 0.5

    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int = 100

    # Cache TTL for confidence scores (seconds)
    cache_ttl: int = 30


class ConfidenceQueryService:
    """
    Service for querying selector confidence scores.

    Provides query methods for single, batch, and paginated confidence lookups
    with default score handling for unknown selectors.
    """

    def __init__(
        self,
        failure_repository: Optional[FailureEventRepository] = None,
        config: Optional[ConfidenceQueryConfig] = None,
    ):
        """
        Initialize the confidence query service.

        Args:
            failure_repository: Repository for failure events (for historical data)
            config: Configuration for the service
        """
        self.failure_repository = failure_repository or FailureEventRepository()
        self.confidence_scorer = None  # Reserved for future use with advanced scoring
        self.config = config or ConfidenceQueryConfig()

        # Cache for confidence scores (selector_id -> (score, timestamp))
        self._score_cache: Dict[str, tuple[float, datetime]] = {}

    def _get_cached_score(self, selector_id: str) -> Optional[float]:
        """Get cached score if still valid."""
        if selector_id in self._score_cache:
            score, timestamp = self._score_cache[selector_id]
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if age < self.config.cache_ttl:
                return score
            else:
                del self._score_cache[selector_id]
        return None

    def _cache_score(self, selector_id: str, score: float) -> None:
        """Cache a confidence score."""
        self._score_cache[selector_id] = (score, datetime.now(timezone.utc))

    def _calculate_confidence_from_history(
        self, selector_id: str
    ) -> tuple[float, datetime, bool]:
        """
        Calculate confidence from historical failure data.

        Args:
            selector_id: The selector ID to query

        Returns:
            Tuple of (confidence_score, last_updated, is_estimated)
        """
        # Check cache first
        cached_score = self._get_cached_score(selector_id)
        if cached_score is not None:
            return cached_score, datetime.now(timezone.utc), False

        # Get failure events for this selector
        events = self.failure_repository.get_by_selector(selector_id, limit=100)

        if not events:
            # No history - return default score
            return (
                self.config.default_confidence_score,
                datetime.now(timezone.utc),
                True,
            )

        # Calculate confidence from failure history
        # Success rate = (total - failures) / total
        # We consider a "failure" as an event with an error_type
        total_events = len(events)
        failure_count = sum(1 for e in events if e.error_type)
        success_count = total_events - failure_count

        if total_events > 0:
            confidence_score = success_count / total_events
        else:
            confidence_score = self.config.default_confidence_score

        # Get the most recent event timestamp
        last_updated = datetime.now(timezone.utc)
        if events:
            try:
                latest = max(events, key=lambda e: e.timestamp)
                last_updated = latest.timestamp
            except Exception:
                pass

        # Cache the score
        self._cache_score(selector_id, confidence_score)

        return confidence_score, last_updated, False

    def query_single(self, selector_id: str) -> ConfidenceScoreResult:
        """
        Query confidence score for a single selector.

        Args:
            selector_id: The selector ID to query

        Returns:
            ConfidenceScoreResult with score, timestamp, and estimated flag
        """
        logger.info("Querying confidence for selector", selector_id=selector_id)

        score, last_updated, is_estimated = self._calculate_confidence_from_history(
            selector_id
        )

        return ConfidenceScoreResult(
            selector_id=selector_id,
            confidence_score=score,
            last_updated=last_updated,
            is_estimated=is_estimated,
        )

    def query_batch(self, selector_ids: List[str]) -> BatchConfidenceResult:
        """
        Query confidence scores for multiple selectors.

        Args:
            selector_ids: List of selector IDs to query

        Returns:
            BatchConfidenceResult with results and missing selectors
        """
        logger.info(
            "Batch querying confidence",
            count=len(selector_ids),
            selector_ids=selector_ids,
        )

        results: Dict[str, Optional[ConfidenceScoreResult]] = {}
        missing_selectors: List[str] = []

        for selector_id in selector_ids:
            try:
                result = self.query_single(selector_id)
                results[selector_id] = result
            except Exception as e:
                logger.warning(
                    "Failed to query selector",
                    selector_id=selector_id,
                    error=str(e),
                )
                results[selector_id] = None
                missing_selectors.append(selector_id)

        return BatchConfidenceResult(
            results=results,
            missing_selectors=missing_selectors,
        )

    def query_all_paginated(
        self, page: int = 1, page_size: Optional[int] = None
    ) -> PaginatedConfidenceResult:
        """
        Query all selector confidence scores with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            PaginatedConfidenceResult with paginated results
        """
        if page_size is None:
            page_size = self.config.default_page_size

        # Clamp page_size to max
        page_size = min(page_size, self.config.max_page_size)

        logger.info("Querying all confidence scores", page=page, page_size=page_size)

        # Get all unique selectors from failure events
        all_results: List[ConfidenceScoreResult] = []

        # Query all unique selectors from the repository
        try:
            unique_selectors = self.failure_repository.get_unique_selectors()

            selector_scores: Dict[str, ConfidenceScoreResult] = {}

            for selector_id in unique_selectors:
                try:
                    result = self.query_single(selector_id)
                    selector_scores[selector_id] = result
                except Exception:
                    pass

            all_results = list(selector_scores.values())
        except Exception as e:
            logger.warning("Failed to get all selectors", error=str(e))
            all_results = []

        # If no selectors found, return default results
        if not all_results:
            return PaginatedConfidenceResult(
                results=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

        total = len(all_results)
        total_pages = (total + page_size - 1) // page_size

        # Calculate pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        page_results = all_results[start_idx:end_idx]

        return PaginatedConfidenceResult(
            results=page_results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def clear_cache(self) -> None:
        """Clear the confidence score cache."""
        self._score_cache.clear()
        logger.info("Confidence score cache cleared")


# Global service instance
_confidence_query_service: Optional[ConfidenceQueryService] = None


def get_confidence_query_service() -> ConfidenceQueryService:
    """
    Get the global confidence query service instance.

    Returns:
        The global ConfidenceQueryService instance
    """
    global _confidence_query_service
    if _confidence_query_service is None:
        _confidence_query_service = ConfidenceQueryService()
    return _confidence_query_service
