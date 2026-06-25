"""
Audit logging middleware for triage API endpoints.

Logs all triage actions for compliance, debugging, and
performance analysis.

Story: 7.3 - Fast Triage Workflow
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.observability.logger import get_logger


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Audit logging middleware for API endpoints.
    
    Logs all requests and responses with relevant metadata
    for compliance and debugging purposes.
    """
    
    def __init__(self, app, log_level: str = "INFO"):
        """
        Initialize audit logging middleware.
        
        Args:
            app: FastAPI application
            log_level: Logging level for audit events
        """
        super().__init__(app)
        self.logger = get_logger("audit_logging")
        self.log_level = log_level
        
        # Endpoints that require special audit attention
        self.sensitive_endpoints = [
            "/triage/bulk-approve",
            "/triage/bulk-reject", 
            "/triage/escalate",
            "/triage/failures/{failure_id}/quick-approve",
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with audit logging.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response with audit logging
        """
        # Generate request ID for tracking
        request_id = self._generate_request_id()
        
        # Collect request metadata
        request_metadata = await self._collect_request_metadata(request, request_id)
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Collect response metadata
            response_metadata = self._collect_response_metadata(response, processing_time_ms)
            
            # Log the audit event
            await self._log_audit_event(request_metadata, response_metadata)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            processing_time_ms = (time.time() - start_time) * 1000
            error_metadata = {
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": processing_time_ms,
            }
            await self._log_audit_event(request_metadata, error_metadata, is_error=True)
            raise
    
    def _generate_request_id(self) -> str:
        """
        Generate unique request ID for tracking.
        
        Returns:
            Unique request identifier
        """
        timestamp = str(time.time())
        random_data = str(hash(timestamp))
        return hashlib.md5((timestamp + random_data).encode()).hexdigest()[:16]
    
    async def _collect_request_metadata(self, request: Request, request_id: str) -> Dict[str, Any]:
        """
        Collect metadata from incoming request.
        
        Args:
            request: Incoming request
            request_id: Unique request identifier
            
        Returns:
            Request metadata dictionary
        """
        metadata = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
            "user_id": request.headers.get("X-User-ID"),
        }
        
        # Add sensitive endpoint flag
        metadata["is_sensitive"] = any(
            endpoint in request.url.path for endpoint in self.sensitive_endpoints
        )
        
        # Collect request body for sensitive endpoints
        if metadata["is_sensitive"] and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                # Sanitize sensitive data
                metadata["request_body"] = self._sanitize_request_body(body, request.url.path)
            except Exception:
                metadata["request_body"] = "<unparseable>"
        
        return metadata
    
    def _collect_response_metadata(self, response: Response, processing_time_ms: float) -> Dict[str, Any]:
        """
        Collect metadata from response.
        
        Args:
            response: HTTP response
            processing_time_ms: Request processing time in milliseconds
            
        Returns:
            Response metadata dictionary
        """
        metadata = {
            "status_code": response.status_code,
            "processing_time_ms": round(processing_time_ms, 2),
            "response_size": len(response.body) if hasattr(response, 'body') else 0,
        }
        
        # Add response headers of interest
        headers_to_log = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Window"]
        metadata["response_headers"] = {
            header: response.headers.get(header) 
            for header in headers_to_log 
            if header in response.headers
        }
        
        return metadata
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: Incoming request
            
        Returns:
            Client IP address
        """
        # Check for forwarded IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        return request.client.host or "unknown"
    
    def _sanitize_request_body(self, body: Dict[str, Any], path: str) -> Dict[str, Any]:
        """
        Sanitize request body for logging.
        
        Removes or masks sensitive information while preserving
        useful data for audit purposes.
        
        Args:
            body: Request body dictionary
            path: Request path for context
            
        Returns:
            Sanitized request body
        """
        if not isinstance(body, dict):
            return {"type": type(body).__name__, "size": len(str(body))}
        
        sanitized = body.copy()
        
        # Mask sensitive fields
        sensitive_fields = ["password", "token", "api_key", "secret"]
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "<masked>"
        
        # For bulk operations, log counts instead of full arrays
        if "failure_ids" in sanitized and isinstance(sanitized["failure_ids"], list):
            sanitized["failure_ids"] = {
                "count": len(sanitized["failure_ids"]),
                "sample": sanitized["failure_ids"][:3] if len(sanitized["failure_ids"]) > 3 else sanitized["failure_ids"]
            }
        
        # For approval operations, log selector info but not full content
        if "selector" in sanitized:
            selector = sanitized["selector"]
            if isinstance(selector, str) and len(selector) > 100:
                sanitized["selector"] = selector[:100] + "..."
        
        return sanitized
    
    async def _log_audit_event(
        self, 
        request_metadata: Dict[str, Any], 
        response_metadata: Dict[str, Any],
        is_error: bool = False
    ):
        """
        Log audit event with metadata.
        
        Args:
            request_metadata: Request metadata
            response_metadata: Response or error metadata
            is_error: Whether this is an error event
        """
        # Combine metadata
        audit_event = {
            **request_metadata,
            **response_metadata,
            "event_type": "error" if is_error else "api_request",
        }
        
        # Determine log level
        if is_error:
            log_method = self.logger.error
        elif request_metadata["is_sensitive"]:
            log_method = self.logger.warning  # Higher priority for sensitive operations
        else:
            log_method = getattr(self.logger, self.log_level.lower(), self.logger.info)
        
        # Create log message
        action = f"{request_metadata['method']} {request_metadata['path']}"
        user_info = f"user:{request_metadata['user_id']}" if request_metadata['user_id'] else f"ip:{request_metadata['client_ip']}"
        
        if is_error:
            message = f"Audit Error: {action} by {user_info} failed"
        else:
            message = f"Audit: {action} by {user_info} completed"
        
        # Log the event
        log_method(
            message,
            extra={
                "audit_event": audit_event,
                "structured": True,
            }
        )
        
        # For sensitive operations, also log to a separate audit file
        if request_metadata["is_sensitive"]:
            await self._log_sensitive_operation(audit_event)
    
    async def _log_sensitive_operation(self, audit_event: Dict[str, Any]):
        """
        Log sensitive operations to dedicated audit log.
        
        Args:
            audit_event: Complete audit event data
        """
        try:
            # Create a simplified audit record for sensitive operations
            sensitive_record = {
                "timestamp": audit_event["timestamp"],
                "request_id": audit_event["request_id"],
                "action": f"{audit_event['method']} {audit_event['path']}",
                "user_id": audit_event["user_id"],
                "client_ip": audit_event["client_ip"],
                "operation_type": self._get_operation_type(audit_event["path"]),
                "result": "success" if audit_event["status_code"] < 400 else "failure",
                "processing_time_ms": audit_event["processing_time_ms"],
                "affected_items": self._count_affected_items(audit_event),
            }
            
            # Log to sensitive audit logger
            audit_logger = get_logger("sensitive_audit")
            audit_logger.info(
                f"Sensitive Operation: {sensitive_record['operation_type']} by {sensitive_record['user_id'] or sensitive_record['client_ip']}",
                extra={
                    "sensitive_audit": sensitive_record,
                    "structured": True,
                }
            )
            
        except Exception as e:
            # Don't let audit logging failures break the request
            self.logger.error(f"Failed to log sensitive operation: {e}")
    
    def _get_operation_type(self, path: str) -> str:
        """
        Categorize operation type from path.
        
        Args:
            path: Request path
            
        Returns:
            Operation type string
        """
        if "bulk-approve" in path:
            return "bulk_approve"
        elif "bulk-reject" in path:
            return "bulk_reject"
        elif "escalate" in path:
            return "escalate"
        elif "quick-approve" in path:
            return "quick_approve"
        elif "failures" in path:
            return "view_failures"
        elif "performance" in path:
            return "view_performance"
        else:
            return "unknown"
    
    def _count_affected_items(self, audit_event: Dict[str, Any]) -> Optional[int]:
        """
        Count affected items from audit event.
        
        Args:
            audit_event: Audit event data
            
        Returns:
            Number of affected items or None
        """
        request_body = audit_event.get("request_body", {})
        
        if "failure_ids" in request_body:
            failure_ids = request_body["failure_ids"]
            if isinstance(failure_ids, dict) and "count" in failure_ids:
                return failure_ids["count"]
            elif isinstance(failure_ids, list):
                return len(failure_ids)
        
        return None
