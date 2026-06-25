"""
Rate limiting middleware for triage API endpoints.

Implements rate limiting to prevent abuse while maintaining availability
for legitimate triage operations.

Story: 7.3 - Fast Triage Workflow
"""

import time
import asyncio
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API endpoints.
    
    Implements sliding window rate limiting with different limits
    for different endpoint types and user tiers.
    """
    
    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        bulk_limit: int = 20,
        bulk_window: int = 60,
        strict_limit: int = 10,
        strict_window: int = 60,
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            default_limit: Default requests per window
            default_window: Window size in seconds
            bulk_limit: Limit for bulk operations
            bulk_window: Window size for bulk operations
            strict_limit: Limit for strict endpoints
            strict_window: Window size for strict endpoints
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.bulk_limit = bulk_limit
        self.bulk_window = bulk_window
        self.strict_limit = strict_limit
        self.strict_window = strict_window
        
        # In-memory storage for rate limiting data
        # In production, this should use Redis or similar
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.bulk_requests: Dict[str, deque] = defaultdict(deque)
        self.strict_requests: Dict[str, deque] = defaultdict(deque)
        
        # Cleanup task to remove old entries
        asyncio.create_task(self._cleanup_old_entries())
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request through rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or rate limit error
        """
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Determine rate limit based on endpoint
        limit, window, request_type = self._get_rate_limit_for_endpoint(request)
        
        # Check rate limit
        if not await self._check_rate_limit(client_id, limit, window, request_type):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "about:blank",
                    "title": "Rate Limit Exceeded",
                    "detail": f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
                    "status": 429,
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)},
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = await self._get_remaining_requests(client_id, limit, window, request_type)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Args:
            request: Incoming request
            
        Returns:
            Client identifier string
        """
        # Try to get user ID from headers (if authenticated)
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_rate_limit_for_endpoint(self, request: Request) -> Tuple[int, int, str]:
        """
        Determine rate limit based on endpoint.
        
        Args:
            request: Incoming request
            
        Returns:
            Tuple of (limit, window, request_type)
        """
        path = request.url.path
        
        # Bulk operations have stricter limits
        if "/bulk-" in path:
            return self.bulk_limit, self.bulk_window, "bulk"
        
        # Strict endpoints (escalation, performance metrics)
        if "/escalate" in path or "/performance" in path:
            return self.strict_limit, self.strict_window, "strict"
        
        # Default limits
        return self.default_limit, self.default_window, "default"
    
    async def _check_rate_limit(
        self, 
        client_id: str, 
        limit: int, 
        window: int, 
        request_type: str
    ) -> bool:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Client identifier
            limit: Request limit
            window: Time window in seconds
            request_type: Type of request for tracking
            
        Returns:
            True if request is allowed, False otherwise
        """
        current_time = time.time()
        
        # Get the appropriate request tracker
        if request_type == "bulk":
            requests_tracker = self.bulk_requests
        elif request_type == "strict":
            requests_tracker = self.strict_requests
        else:
            requests_tracker = self.requests
        
        # Clean old requests outside the window
        client_requests = requests_tracker[client_id]
        while client_requests and client_requests[0] < current_time - window:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) < limit:
            client_requests.append(current_time)
            return True
        
        return False
    
    async def _get_remaining_requests(
        self, 
        client_id: str, 
        limit: int, 
        window: int, 
        request_type: str
    ) -> int:
        """
        Get remaining requests for client.
        
        Args:
            client_id: Client identifier
            limit: Request limit
            window: Time window in seconds
            request_type: Type of request
            
        Returns:
            Number of remaining requests
        """
        current_time = time.time()
        
        # Get the appropriate request tracker
        if request_type == "bulk":
            requests_tracker = self.bulk_requests
        elif request_type == "strict":
            requests_tracker = self.strict_requests
        else:
            requests_tracker = self.requests
        
        # Count requests in window
        client_requests = requests_tracker[client_id]
        recent_requests = sum(1 for req_time in client_requests if req_time >= current_time - window)
        
        return max(0, limit - recent_requests)
    
    async def _cleanup_old_entries(self):
        """
        Background task to clean up old rate limit entries.
        Runs periodically to prevent memory leaks.
        """
        while True:
            try:
                current_time = time.time()
                
                # Clean each request tracker
                for tracker in [self.requests, self.bulk_requests, self.strict_requests]:
                    for client_id, request_times in list(tracker.items()):
                        # Remove old entries
                        while request_times and request_times[0] < current_time - 3600:  # 1 hour
                            request_times.popleft()
                        
                        # Remove empty client entries
                        if not request_times:
                            del tracker[client_id]
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception:
                # Log error but continue running
                await asyncio.sleep(300)


class BulkOperationSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate bulk operation sizes.
    
    Prevents excessively large bulk operations that could
    cause performance issues or DoS attacks.
    """
    
    def __init__(self, app, max_bulk_size: int = 100):
        """
        Initialize bulk operation size middleware.
        
        Args:
            app: FastAPI application
            max_bulk_size: Maximum size for bulk operations
        """
        super().__init__(app)
        self.max_bulk_size = max_bulk_size
    
    async def dispatch(self, request: Request, call_next):
        """
        Validate bulk operation size before processing.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or validation error
        """
        # Check if this is a bulk operation
        if "/bulk-" in request.url.path and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Get request body
                body = await request.json()
                
                # Check for failure_ids array
                if "failure_ids" in body:
                    failure_count = len(body["failure_ids"])
                    if failure_count > self.max_bulk_size:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "type": "about:blank",
                                "title": "Bulk Operation Too Large",
                                "detail": f"Bulk operations cannot exceed {self.max_bulk_size} items. "
                                        f"Requested {failure_count} items.",
                                "status": 400,
                                "max_allowed": self.max_bulk_size,
                                "requested": failure_count,
                            },
                        )
                
            except Exception:
                # If we can't parse the body, let the request continue
                # The validation will happen at the service layer
                pass
        
        # Process request
        return await call_next(request)
