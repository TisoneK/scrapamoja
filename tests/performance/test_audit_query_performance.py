"""
Performance tests for Audit Query Service.

This implements Epic 6 (Audit Logging) requirements for Story 6.3.
Tests performance with large datasets to ensure efficiency.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.selectors.adaptive.services.audit_query_service import (
    AuditQueryService,
    AuditQueryParams,
    SortField,
    SortOrder,
)
from src.selectors.adaptive.db.repositories.audit_event_repository import AuditEventRepository


class TestAuditQueryPerformance:
    """Performance tests for audit query operations."""
    
    @pytest.fixture
    def audit_service(self):
        """Create audit query service with in-memory database."""
        return AuditQueryService(db_path=":memory:")
    
    @pytest.fixture
    def large_dataset(self, audit_service):
        """Create a large dataset for performance testing."""
        repository = audit_service.repository
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Create 1000 audit events
        events = []
        for i in range(1000):
            event = repository.create_audit_event(
                action_type=["selector_approved", "selector_rejected", "selector_flagged"][i % 3],
                selector=f"div.test-{i % 100}",  # 100 different selectors
                user_id=f"user-{i % 50}",  # 50 different users
                selector_id=f"selector-{i % 100}",
                confidence_at_time=0.5 + (i % 50) * 0.01,
                reason=f"Performance test reason {i}",
                context_snapshot={"test_data": f"data-{i}"} if i % 10 == 0 else None,
            )
            events.append(event)
        
        yield events
        
        # Cleanup
        session = repository.get_session()
        try:
            for event in events:
                session.delete(event)
            session.commit()
        finally:
            session.close()
    
    def test_query_performance_with_large_dataset(self, audit_service, large_dataset):
        """Test query performance with large dataset."""
        params = AuditQueryParams(
            limit=100,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        
        start_time = time.time()
        result = audit_service.query_audit_history(params)
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Performance assertion: should complete within 1 second
        assert query_time < 1.0, f"Query took {query_time:.2f} seconds, expected < 1.0"
        assert len(result.events) <= 100
        assert result.total_count >= 1000
    
    def test_filtered_query_performance(self, audit_service, large_dataset):
        """Test filtered query performance."""
        params = AuditQueryParams(
            selector_id="selector-0",
            user_id="user-0",
            limit=50,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        
        start_time = time.time()
        result = audit_service.query_audit_history(params)
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Performance assertion: filtered queries should be fast
        assert query_time < 0.5, f"Filtered query took {query_time:.2f} seconds, expected < 0.5"
        assert result.total_count >= 10  # Should have multiple events for this selector/user combo
    
    def test_date_range_query_performance(self, audit_service, large_dataset):
        """Test date range query performance."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        params = AuditQueryParams(
            start_date=start_date,
            end_date=end_date,
            limit=100,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        
        start_time = time.time()
        result = audit_service.query_audit_history(params)
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Performance assertion: date range queries should be efficient
        assert query_time < 0.5, f"Date range query took {query_time:.2f} seconds, expected < 0.5"
        assert result.total_count >= 1000  # All events should be in range
    
    def test_count_query_performance(self, audit_service, large_dataset):
        """Test count query performance with COUNT optimization."""
        start_time = time.time()
        count = audit_service._get_filtered_count(
            selector_id="selector-0",
            user_id="user-0",
        )
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Performance assertion: count queries should be very fast
        assert query_time < 0.1, f"Count query took {query_time:.2f} seconds, expected < 0.1"
        assert count >= 10  # Should have multiple events
    
    def test_pagination_performance(self, audit_service, large_dataset):
        """Test pagination performance with different offsets."""
        # Test first page
        params = AuditQueryParams(limit=50, offset=0)
        start_time = time.time()
        result1 = audit_service.query_audit_history(params)
        first_page_time = time.time() - start_time
        
        # Test middle page
        params.offset = 500
        start_time = time.time()
        result2 = audit_service.query_audit_history(params)
        middle_page_time = time.time() - start_time
        
        # Test last page
        params.offset = 950
        start_time = time.time()
        result3 = audit_service.query_audit_history(params)
        last_page_time = time.time() - start_time
        
        # Performance assertions
        assert first_page_time < 0.5, f"First page took {first_page_time:.2f} seconds"
        assert middle_page_time < 0.5, f"Middle page took {middle_page_time:.2f} seconds"
        assert last_page_time < 0.5, f"Last page took {last_page_time:.2f} seconds"
        
        # All pages should have consistent performance
        time_variance = max(first_page_time, middle_page_time, last_page_time) - min(first_page_time, middle_page_time, last_page_time)
        assert time_variance < 0.2, f"Page time variance {time_variance:.2f} seconds, expected < 0.2"
    
    def test_cursor_pagination_performance(self, audit_service, large_dataset):
        """Test cursor-based pagination performance."""
        # Get first page
        params = AuditQueryParams(limit=50)
        result1 = audit_service.query_audit_history(params)
        
        # Test cursor pagination for multiple pages
        cursor_times = []
        current_cursor = result1.next_cursor
        page_count = 0
        
        while current_cursor and page_count < 5:  # Test 5 pages
            params = AuditQueryParams(limit=50, cursor=current_cursor)
            start_time = time.time()
            result = audit_service.query_audit_history(params)
            cursor_time = time.time() - start_time
            cursor_times.append(cursor_time)
            
            current_cursor = result.next_cursor
            page_count += 1
        
        # Performance assertions
        for i, cursor_time in enumerate(cursor_times):
            assert cursor_time < 0.3, f"Cursor page {i+1} took {cursor_time:.2f} seconds, expected < 0.3"
        
        # Cursor pagination should be consistently fast
        avg_cursor_time = sum(cursor_times) / len(cursor_times)
        assert avg_cursor_time < 0.2, f"Average cursor time {avg_cursor_time:.2f} seconds, expected < 0.2"
    
    def test_sorting_performance(self, audit_service, large_dataset):
        """Test sorting performance across different fields."""
        sort_fields = [SortField.TIMESTAMP, SortField.USER, SortField.SELECTOR, SortField.ACTION]
        
        for sort_field in sort_fields:
            params = AuditQueryParams(
                limit=100,
                sort_by=sort_field,
                sort_order=SortOrder.DESC,
            )
            
            start_time = time.time()
            result = audit_service.query_audit_history(params)
            end_time = time.time()
            
            query_time = end_time - start_time
            
            # Performance assertion: sorting should be efficient
            assert query_time < 0.5, f"Sort by {sort_field.value} took {query_time:.2f} seconds, expected < 0.5"
            assert len(result.events) <= 100
    
    def test_complex_query_performance(self, audit_service, large_dataset):
        """Test performance with complex multi-criteria queries."""
        params = AuditQueryParams(
            selector_id="selector-0",
            user_id="user-0",
            action_types=["selector_approved", "selector_rejected"],
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            limit=50,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        
        start_time = time.time()
        result = audit_service.query_audit_history(params)
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Performance assertion: complex queries should still be fast
        assert query_time < 0.5, f"Complex query took {query_time:.2f} seconds, expected < 0.5"
        assert len(result.events) <= 50
    
    def test_memory_usage_with_large_results(self, audit_service, large_dataset):
        """Test memory usage with large result sets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Query a large result set
        params = AuditQueryParams(limit=500, offset=0)
        result = audit_service.query_audit_history(params)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Memory assertion: should not use excessive memory
        assert memory_increase < 50, f"Memory increased by {memory_increase:.2f} MB, expected < 50 MB"
        assert len(result.events) <= 500
    
    def test_concurrent_query_performance(self, audit_service, large_dataset):
        """Test performance with concurrent queries."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker():
            params = AuditQueryParams(limit=50, offset=0)
            start_time = time.time()
            result = audit_service.query_audit_history(params)
            end_time = time.time()
            results.put(end_time - start_time)
        
        # Start 5 concurrent queries
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect individual query times
        query_times = []
        while not results.empty():
            query_times.append(results.get())
        
        # Performance assertions
        avg_query_time = sum(query_times) / len(query_times)
        assert avg_query_time < 1.0, f"Average concurrent query time {avg_query_time:.2f} seconds, expected < 1.0"
        assert total_time < 2.0, f"Total concurrent time {total_time:.2f} seconds, expected < 2.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
