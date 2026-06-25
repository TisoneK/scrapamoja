"""
Performance tests for Fast Triage Service.

This implements Story 7.3 (Fast Triage Workflow) requirements.
Tests performance targets: <2s page loads, <500ms actions, <5min workflow.
"""

import pytest
import time
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.selectors.adaptive.services.fast_triage_service import FastTriageService
from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository
from src.selectors.adaptive.db.repositories.triage_repository import TriageRepository
from src.selectors.adaptive.db.models.triage_metrics import TriageMetricsRepository
from src.selectors.adaptive.services.failure_service import FailureService


class TestTriagePerformance:
    """Performance tests for triage operations."""
    
    @pytest.fixture
    def triage_service(self):
        """Create triage service with in-memory databases."""
        return FastTriageService(
            failure_repository=FailureEventRepository(db_path=":memory:"),
            triage_repository=TriageRepository(db_path=":memory:"),
            metrics_repository=TriageMetricsRepository(db_path=":memory:"),
            failure_service=FailureService(db_path=":memory:"),
        )
    
    @pytest.fixture
    def large_failure_dataset(self, triage_service):
        """Create a large dataset of failures for performance testing."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Create mock failure summaries
        failures = []
        for i in range(100):
            failure = Mock()
            failure.id = i + 1
            failure.selector_id = f"selector-{i % 20}"
            failure.error_type = ["element_not_found", "selector_invalid", "timeout"][i % 3]
            failure.timestamp = base_time + timedelta(minutes=i)
            failure.severity = ["critical", "high", "medium", "minor"][i % 4]
            failure.sport = ["basketball", "football", "tennis"][i % 3]
            failure.site = ["flashscore", "other"][i % 2]
            failure.has_alternatives = i % 3 != 0  # 2/3 have alternatives
            failures.append(failure)
        
        # Mock the repository to return these failures
        triage_service.triage_repository.get_failure_summaries_fast = Mock(
            return_value=(failures[:50], 51)  # Return first 50, next cursor 51
        )
        triage_service.triage_repository.get_failure_counts = Mock(
            return_value={
                "total": 100,
                "critical": 25,
                "high": 25,
                "medium": 25,
                "minor": 25,
            }
        )
        
        yield failures
        
        # Cleanup handled by in-memory database
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_triage_workflow_performance(self, triage_service):
        """Test that complete triage workflow meets <5min target."""
        start_time = time.time()
        
        # Simulate complete triage workflow
        # 1. Load failures (should be <2s)
        result = triage_service.get_failures_fast(limit=50)
        assert result["performance"]["load_time_ms"] < 2000
        
        # 2. Quick approve a failure (should be <500ms)
        if result["failures"]:
            failure_id = result["failures"][0]["id"]
            approve_result = triage_service.quick_approve(failure_id, user_id="test-user")
            assert approve_result["performance"]["action_time_ms"] < 500
        
        total_time = time.time() - start_time
        
        # Should complete well under 5 minutes (targeting <30 seconds for test)
        assert total_time < 300, f"Workflow took {total_time:.2f} seconds, expected < 300"
    
    @pytest.mark.performance
    def test_failure_loading_performance(self, triage_service, large_failure_dataset):
        """Test failure loading meets <2 second target."""
        start_time = time.time()
        result = triage_service.get_failures_fast(limit=50)
        end_time = time.time()
        
        load_time_ms = (end_time - start_time) * 1000
        
        # Performance assertion: should load in under 2 seconds
        assert load_time_ms < 2000, f"Load took {load_time_ms:.2f}ms, expected < 2000ms"
        assert len(result["failures"]) == 50
        assert result["performance"]["target_met"] == True
    
    @pytest.mark.performance
    def test_quick_approve_performance(self, triage_service):
        """Test quick approve meets <500ms target."""
        # Mock failure service for quick approve
        triage_service.failure_service.get_failure_detail = Mock(
            return_value={
                "alternatives": [
                    {"selector": "div.new-selector", "confidence_score": 0.95},
                    {"selector": "span.backup", "confidence_score": 0.85},
                ]
            }
        )
        triage_service.failure_service.approve_alternative = Mock(
            return_value={"success": True, "message": "Approved"}
        )
        
        start_time = time.time()
        result = triage_service.quick_approve(failure_id=1, user_id="test-user")
        end_time = time.time()
        
        action_time_ms = (end_time - start_time) * 1000
        
        # Performance assertion: should complete in under 500ms
        assert action_time_ms < 500, f"Quick approve took {action_time_ms:.2f}ms, expected < 500ms"
        assert result["success"] == True
        assert result["performance"]["target_met"] == True
    
    @pytest.mark.performance
    def test_bulk_approve_performance(self, triage_service):
        """Test bulk approve performance scales linearly."""
        # Mock failure service for bulk operations
        triage_service.failure_service.get_failure_detail = Mock(
            side_effect=lambda failure_id: {
                "alternatives": [
                    {"selector": f"div.new-selector-{failure_id}", "confidence_score": 0.95}
                ]
            }
        )
        triage_service.failure_service.approve_alternative = Mock(
            return_value={"success": True, "message": "Approved"}
        )
        
        # Test with different batch sizes
        batch_sizes = [5, 10, 25, 50]
        
        for batch_size in batch_sizes:
            failure_ids = list(range(1, batch_size + 1))
            
            start_time = time.time()
            result = triage_service.bulk_approve(
                failure_ids=failure_ids,
                strategy="highest_confidence",
                user_id="test-user",
            )
            end_time = time.time()
            
            total_time_ms = (end_time - start_time) * 1000
            avg_time_per_failure = total_time_ms / batch_size
            
            # Performance assertions
            assert avg_time_per_failure < 200, f"Bulk approve avg time {avg_time_per_failure:.2f}ms per failure, expected < 200ms"
            assert total_time_ms < batch_size * 2000, f"Bulk approve took {total_time_ms:.2f}ms for {batch_size} failures"
            assert result["success_count"] == batch_size
    
    @pytest.mark.performance
    def test_bulk_reject_performance(self, triage_service):
        """Test bulk reject performance."""
        # Mock failure service for bulk reject
        triage_service.failure_service.get_failure_detail = Mock(
            side_effect=lambda failure_id: {
                "alternatives": [{"selector": f"div.failed-{failure_id}"}],
                "failed_selector": f"div.old-{failure_id}",
            }
        )
        triage_service.failure_service.reject_alternative = Mock(
            return_value={"success": True, "message": "Rejected"}
        )
        
        failure_ids = list(range(1, 26))  # 25 failures
        
        start_time = time.time()
        result = triage_service.bulk_reject(
            failure_ids=failure_ids,
            reason="Performance test reject",
            user_id="test-user",
        )
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_failure = total_time_ms / len(failure_ids)
        
        # Performance assertions
        assert avg_time_per_failure < 100, f"Bulk reject avg time {avg_time_per_failure:.2f}ms per failure, expected < 100ms"
        assert result["success_count"] == 25
    
    @pytest.mark.performance
    def test_quick_escalate_performance(self, triage_service):
        """Test quick escalation meets <2 minute target."""
        # Mock failure service for escalation
        triage_service.failure_service.flag_failure = Mock(
            return_value={"success": True, "message": "Flagged for review"}
        )
        
        failure_ids = list(range(1, 11))  # 10 failures to escalate
        
        start_time = time.time()
        result = triage_service.quick_escalate(
            failure_ids=failure_ids,
            reason="Performance test escalation",
            user_id="test-user",
        )
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        
        # Performance assertion: should complete well under 2 minutes (targeting <10 seconds)
        assert total_time_ms < 10000, f"Escalation took {total_time_ms:.2f}ms, expected < 10000ms"
        assert result["success_count"] == 10
        assert result["performance"]["target_met"] == True
    
    @pytest.mark.performance
    def test_cursor_pagination_performance(self, triage_service, large_failure_dataset):
        """Test cursor pagination performance across multiple pages."""
        # Mock multiple pages of data
        page_data = [
            (large_failure_dataset[i:i+10], i+11) for i in range(0, 50, 10)
        ]
        
        triage_service.triage_repository.get_failure_summaries_fast = Mock(
            side_effect=lambda limit=50, cursor=None, **kwargs: (
                page_data[cursor//10 - 1] if cursor and cursor <= 50 else page_data[0]
            )
        )
        
        # Test pagination through 5 pages
        cursor_times = []
        current_cursor = None
        
        for page in range(5):
            start_time = time.time()
            result = triage_service.get_failures_fast(limit=10, cursor=current_cursor)
            cursor_time = time.time() - start_time
            cursor_times.append(cursor_time)
            
            current_cursor = result.get("next_cursor")
            if not current_cursor:
                break
        
        # Performance assertions
        for i, cursor_time in enumerate(cursor_times):
            assert cursor_time < 0.5, f"Page {i+1} took {cursor_time:.2f}s, expected < 0.5s"
        
        # Average page time should be consistent
        avg_page_time = sum(cursor_times) / len(cursor_times)
        assert avg_page_time < 0.2, f"Average page time {avg_page_time:.2f}s, expected < 0.2s"
    
    @pytest.mark.performance
    def test_performance_summary_generation(self, triage_service):
        """Test performance summary generation performance."""
        # Mock metrics data
        triage_service.metrics_repository.get_average_times = Mock(
            return_value={
                "quick_approve": {
                    "avg_total_ms": 300,
                    "avg_load_ms": 50,
                    "avg_action_ms": 250,
                    "count": 100,
                },
                "bulk_approve": {
                    "avg_total_ms": 2000,
                    "avg_load_ms": 100,
                    "avg_action_ms": 1900,
                    "count": 50,
                },
                "load_failures": {
                    "avg_total_ms": 1200,
                    "avg_load_ms": 1200,
                    "avg_action_ms": 0,
                    "count": 200,
                },
            }
        )
        
        start_time = time.time()
        result = triage_service.get_performance_summary(hours=24)
        end_time = time.time()
        
        generation_time_ms = (end_time - start_time) * 1000
        
        # Performance assertion: should generate quickly
        assert generation_time_ms < 100, f"Summary generation took {generation_time_ms:.2f}ms, expected < 100ms"
        assert result["total_actions"] == 350
        assert result["status"]["load_target_met"] == True
        assert result["status"]["action_target_met"] == True
    
    @pytest.mark.performance
    def test_concurrent_triage_operations(self, triage_service):
        """Test performance with concurrent triage operations."""
        import threading
        import queue
        
        # Mock services for concurrent operations
        triage_service.failure_service.get_failure_detail = Mock(
            return_value={
                "alternatives": [{"selector": "div.test", "confidence_score": 0.9}]
            }
        )
        triage_service.failure_service.approve_alternative = Mock(
            return_value={"success": True}
        )
        
        results = queue.Queue()
        
        def worker():
            start_time = time.time()
            result = triage_service.quick_approve(failure_id=1, user_id="test-user")
            end_time = time.time()
            results.put(end_time - start_time)
        
        # Start 5 concurrent operations
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
        
        # Collect individual operation times
        operation_times = []
        while not results.empty():
            operation_times.append(results.get())
        
        # Performance assertions
        avg_operation_time = sum(operation_times) / len(operation_times)
        assert avg_operation_time < 1.0, f"Average concurrent operation time {avg_operation_time:.2f}s, expected < 1.0s"
        assert total_time < 3.0, f"Total concurrent time {total_time:.2f}s, expected < 3.0s"
    
    @pytest.mark.performance
    def test_memory_usage_with_large_datasets(self, triage_service, large_failure_dataset):
        """Test memory usage with large failure datasets."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Load a large dataset
            result = triage_service.get_failures_fast(limit=100)
            
            # Perform bulk operations
            failure_ids = list(range(1, 51))
            triage_service.bulk_approve(failure_ids=failure_ids)
            
            final_memory = process.memory_info().rss
            memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
            
            # Memory assertion: should not use excessive memory
            assert memory_increase < 100, f"Memory increased by {memory_increase:.2f} MB, expected < 100 MB"
            
        except ImportError:
            pytest.skip("psutil not available for memory testing")
    
    @pytest.mark.performance
    def test_filtering_performance(self, triage_service, large_failure_dataset):
        """Test performance with various filter combinations."""
        filter_combinations = [
            {"sport": "basketball"},
            {"site": "flashscore"},
            {"severity": "high"},
            {"sport": "basketball", "severity": "high"},
            {"site": "flashscore", "severity": "critical"},
            {"sport": "football", "site": "flashscore", "severity": "medium"},
        ]
        
        for filters in filter_combinations:
            start_time = time.time()
            result = triage_service.get_failures_fast(limit=50, **filters)
            end_time = time.time()
            
            query_time = (end_time - start_time) * 1000
            
            # Performance assertion: filtered queries should be fast
            assert query_time < 500, f"Filtered query {filters} took {query_time:.2f}ms, expected < 500ms"
            assert len(result["failures"]) <= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
