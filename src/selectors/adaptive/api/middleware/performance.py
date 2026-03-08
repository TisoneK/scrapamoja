"""
Performance Monitoring Middleware

This middleware tracks API response times to ensure compliance with AC #3:
- Initial page load under 2 seconds
- Each action responds within 500ms
"""

import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.logger import get_logger

logger = get_logger("performance_middleware")


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor API response times for performance requirements."""
    
    # Performance thresholds from AC #3
    PAGE_LOAD_THRESHOLD = 2.0  # 2 seconds for initial page load
    ACTION_THRESHOLD = 0.5    # 500ms for individual actions
    
    def __init__(self, app, threshold_ms: float = ACTION_THRESHOLD * 1000):
        super().__init__(app)
        self.threshold_ms = threshold_ms
        self._logger = logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance metrics."""
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate response time
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        process_time_seconds = process_time / 1000
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{process_time:.2f}ms"
        
        # Log performance metrics
        endpoint = f"{request.method} {request.url.path}"
        
        # Check if this is a page load endpoint (GET /failures)
        is_page_load = (
            request.method == "GET" and 
            request.url.path == "/failures" and
            "page" not in request.query_params
        )
        
        threshold = self.PAGE_LOAD_THRESHOLD if is_page_load else self.ACTION_THRESHOLD
        
        if process_time_seconds > threshold:
            self._logger.warning(
                "performance_threshold_exceeded",
                endpoint=endpoint,
                process_time_ms=process_time,
                threshold_ms=threshold * 1000,
                request_id=request.headers.get("X-Request-ID", "unknown"),
            )
            
            # Add performance warning header
            response.headers["X-Performance-Warning"] = f"Response time {process_time:.2f}ms exceeds threshold {threshold * 1000:.0f}ms"
        else:
            self._logger.info(
                "performance_ok",
                endpoint=endpoint,
                process_time_ms=process_time,
                threshold_ms=threshold * 1000,
            )
        
        # Add performance metrics to response for monitoring dashboard
        if hasattr(response, 'body') and isinstance(response, JSONResponse):
            # For JSON responses, we can add performance metadata
            try:
                body = response.body.decode('utf-8')
                if body.startswith('{') and body.endswith('}'):
                    import json
                    data = json.loads(body)
                    if isinstance(data, dict):
                        data['_performance'] = {
                            'response_time_ms': round(process_time, 2),
                            'threshold_ms': threshold * 1000,
                            'within_threshold': process_time_seconds <= threshold,
                            'endpoint': endpoint,
                        }
                        response.body = json.dumps(data).encode('utf-8')
                        response.headers["content-length"] = str(len(response.body))
            except Exception as e:
                self._logger.debug(f"Could not add performance metadata to response: {e}")
        
        return response


class PerformanceTracker:
    """Utility class for tracking performance metrics."""
    
    def __init__(self):
        self._logger = logger
        self._metrics = {}
    
    def track_operation(self, operation_name: str, threshold_ms: float):
        """Context manager for tracking specific operations."""
        class OperationTracker:
            def __init__(self, tracker, name, threshold):
                self.tracker = tracker
                self.name = name
                self.threshold = threshold
                self.start_time = None
                
            def __enter__(self):
                self.start_time = time.time()
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.start_time:
                    duration = (time.time() - self.start_time) * 1000
                    threshold_seconds = self.threshold / 1000
                    
                    if duration > self.threshold:
                        self.tracker._logger.warning(
                            "operation_slow",
                            operation=self.name,
                            duration_ms=duration,
                            threshold_ms=self.threshold,
                        )
                    else:
                        self.tracker._logger.debug(
                            "operation_ok",
                            operation=self.name,
                            duration_ms=duration,
                        )
        
        return OperationTracker(self, operation_name, threshold_ms)
    
    def get_metrics_summary(self) -> dict:
        """Get a summary of performance metrics."""
        return {
            "total_operations": len(self._metrics),
            "average_response_time": sum(self._metrics.values()) / len(self._metrics) if self._metrics else 0,
            "slow_operations": [op for op, time in self._metrics.items() if time > 500],
        }


# Global performance tracker instance
performance_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return performance_tracker
