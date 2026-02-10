"""
Rate limiter component template for the modular site scraper template.

This module provides rate limiting functionality with multiple algorithms
and configurable limits to prevent overwhelming target servers.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import asyncio
import time
from collections import deque, defaultdict

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class RateLimiterComponent(BaseComponent):
    """Rate limiter component with multiple rate limiting algorithms."""
    
    def __init__(
        self,
        component_id: str = "rate_limiter",
        name: str = "Rate Limiter Component",
        version: str = "1.0.0",
        description: str = "Rate limiting for web scraping to prevent overwhelming servers"
    ):
        """
        Initialize rate limiter component.
        
        Args:
            component_id: Unique identifier for the component
            name: Human-readable name for the component
            version: Component version
            description: Component description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            component_type="RATE_LIMITING"
        )
        
        # Rate limiting configuration
        self._algorithm: str = "token_bucket"  # "token_bucket", "sliding_window", "fixed_window"
        self._requests_per_second: float = 1.0
        self._requests_per_minute: int = 60
        self._requests_per_hour: int = 3600
        self._burst_capacity: int = 5
        
        # Rate limiting state
        self._token_bucket: Dict[str, float] = defaultdict(float)
        self._last_refill_time: Dict[str, datetime] = defaultdict(datetime.utcnow)
        self._request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._window_start_time: Dict[str, datetime] = defaultdict(datetime.utcnow)
        self._request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Rate limiting per domain/endpoint
        self._domain_limits: Dict[str, Dict[str, Any]] = {}
        self._endpoint_limits: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks
        self._rate_limit_hit_callback: Optional[Callable] = None
        self._rate_limit_reset_callback: Optional[Callable] = None
        
        # Statistics
        self._statistics = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'rate_limit_hits': 0,
            'average_wait_time_ms': 0.0,
            'total_wait_time_ms': 0.0
        }
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize rate limiter component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load rate limiting configuration from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            self._algorithm = config.get('rate_limit_algorithm', 'token_bucket')
            self._requests_per_second = config.get('requests_per_second', 1.0)
            self._requests_per_minute = config.get('requests_per_minute', 60)
            self._requests_per_hour = config.get('requests_per_hour', 3600)
            self._burst_capacity = config.get('burst_capacity', 5)
            
            # Load domain-specific limits
            self._domain_limits = config.get('domain_rate_limits', {})
            self._endpoint_limits = config.get('endpoint_rate_limits', {})
            
            # Initialize token bucket for default domain
            self._token_bucket['default'] = float(self._burst_capacity)
            self._last_refill_time['default'] = datetime.utcnow()
            
            self._log_operation("initialize", f"Rate limiter initialized with {self._algorithm} algorithm")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Rate limiter initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Check rate limit and wait if necessary.
        
        Args:
            **kwargs: Rate limiting parameters including 'domain', 'endpoint', etc.
            
        Returns:
            Rate limiting result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            domain = kwargs.get('domain', 'default')
            endpoint = kwargs.get('endpoint')
            wait_for_slot = kwargs.get('wait_for_slot', True)
            
            # Update statistics
            self._statistics['total_requests'] += 1
            
            # Check rate limit
            rate_limit_result = await self._check_rate_limit(domain, endpoint, wait_for_slot)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Update wait time statistics
            wait_time = rate_limit_result.get('wait_time_ms', 0)
            self._statistics['total_wait_time_ms'] += wait_time
            if self._statistics['total_requests'] > 0:
                self._statistics['average_wait_time_ms'] = (
                    self._statistics['total_wait_time_ms'] / self._statistics['total_requests']
                )
            
            return ComponentResult(
                success=rate_limit_result['allowed'],
                data={
                    'allowed': rate_limit_result['allowed'],
                    'wait_time_ms': wait_time,
                    'domain': domain,
                    'endpoint': endpoint,
                    'algorithm': self._algorithm,
                    'statistics': self._statistics.copy()
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Rate limiting failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _check_rate_limit(self, domain: str, endpoint: str, wait_for_slot: bool) -> Dict[str, Any]:
        """Check rate limit for domain/endpoint."""
        try:
            # Get effective limits
            limits = self._get_effective_limits(domain, endpoint)
            
            # Check rate limit based on algorithm
            if self._algorithm == "token_bucket":
                result = await self._token_bucket_check(domain, limits, wait_for_slot)
            elif self._algorithm == "sliding_window":
                result = await self._sliding_window_check(domain, limits, wait_for_slot)
            elif self._algorithm == "fixed_window":
                result = await self._fixed_window_check(domain, limits, wait_for_slot)
            else:
                raise ValueError(f"Unknown rate limiting algorithm: {self._algorithm}")
            
            # Update statistics
            if result['allowed']:
                self._statistics['allowed_requests'] += 1
            else:
                self._statistics['blocked_requests'] += 1
                self._statistics['rate_limit_hits'] += 1
                
                # Call rate limit hit callback
                if self._rate_limit_hit_callback:
                    await self._rate_limit_hit_callback(domain, endpoint, limits)
            
            return result
            
        except Exception as e:
            self._log_operation("_check_rate_limit", f"Rate limit check failed: {str(e)}", "error")
            return {
                'allowed': False,
                'wait_time_ms': 0,
                'error': str(e)
            }
    
    def _get_effective_limits(self, domain: str, endpoint: str) -> Dict[str, Any]:
        """Get effective rate limits for domain/endpoint."""
        # Start with default limits
        limits = {
            'requests_per_second': self._requests_per_second,
            'requests_per_minute': self._requests_per_minute,
            'requests_per_hour': self._requests_per_hour,
            'burst_capacity': self._burst_capacity
        }
        
        # Apply domain-specific limits
        if domain in self._domain_limits:
            domain_limits = self._domain_limits[domain]
            for key, value in domain_limits.items():
                if value is not None:
                    limits[key] = value
        
        # Apply endpoint-specific limits
        if endpoint and endpoint in self._endpoint_limits:
            endpoint_limits = self._endpoint_limits[endpoint]
            for key, value in endpoint_limits.items():
                if value is not None:
                    limits[key] = value
        
        return limits
    
    async def _token_bucket_check(self, domain: str, limits: Dict[str, Any], wait_for_slot: bool) -> Dict[str, Any]:
        """Token bucket rate limiting algorithm."""
        try:
            current_time = datetime.utcnow()
            
            # Refill tokens
            last_refill = self._last_refill_time[domain]
            time_diff = (current_time - last_refill).total_seconds()
            tokens_to_add = time_diff * limits['requests_per_second']
            
            self._token_bucket[domain] = min(
                limits['burst_capacity'],
                self._token_bucket[domain] + tokens_to_add
            )
            self._last_refill_time[domain] = current_time
            
            # Check if we have enough tokens
            if self._token_bucket[domain] >= 1:
                self._token_bucket[domain] -= 1
                return {
                    'allowed': True,
                    'wait_time_ms': 0,
                    'tokens_remaining': self._token_bucket[domain]
                }
            
            # Calculate wait time if requested
            wait_time_ms = 0
            if wait_for_slot:
                wait_time_ms = int((1 - self._token_bucket[domain]) * 1000 / limits['requests_per_second'])
                await asyncio.sleep(wait_time_ms / 1000.0)
                
                # After waiting, consume a token
                self._token_bucket[domain] = max(0, self._token_bucket[domain] - 1)
                return {
                    'allowed': True,
                    'wait_time_ms': wait_time_ms,
                    'tokens_remaining': self._token_bucket[domain]
                }
            
            return {
                'allowed': False,
                'wait_time_ms': wait_time_ms,
                'tokens_remaining': self._token_bucket[domain]
            }
            
        except Exception as e:
            self._log_operation("_token_bucket_check", f"Token bucket check failed: {str(e)}", "error")
            return {
                'allowed': False,
                'wait_time_ms': 0,
                'error': str(e)
            }
    
    async def _sliding_window_check(self, domain: str, limits: Dict[str, Any], wait_for_slot: bool) -> Dict[str, Any]:
        """Sliding window rate limiting algorithm."""
        try:
            current_time = datetime.utcnow()
            
            # Get request history for the domain
            history = self._request_history[domain]
            
            # Remove old requests outside the time window
            window_start = current_time - timedelta(seconds=60)  # 1-minute sliding window
            while history and history[0] < window_start:
                history.popleft()
            
            # Check if we can make a request
            if len(history) < limits['requests_per_minute']:
                history.append(current_time)
                return {
                    'allowed': True,
                    'wait_time_ms': 0,
                    'requests_in_window': len(history)
                }
            
            # Calculate wait time if requested
            wait_time_ms = 0
            if wait_for_slot and history:
                oldest_request = history[0]
                wait_time = (oldest_request + timedelta(seconds=60)) - current_time
                wait_time_ms = int(wait_time.total_seconds() * 1000)
                
                if wait_time_ms > 0:
                    await asyncio.sleep(wait_time_ms / 1000.0)
                    
                    # After waiting, remove old requests and add new one
                    while history and history[0] < (current_time + timedelta(milliseconds=wait_time_ms)):
                        history.popleft()
                    
                    history.append(current_time + timedelta(milliseconds=wait_time_ms))
                    return {
                        'allowed': True,
                        'wait_time_ms': wait_time_ms,
                        'requests_in_window': len(history)
                    }
            
            return {
                'allowed': False,
                'wait_time_ms': wait_time_ms,
                'requests_in_window': len(history)
            }
            
        except Exception as e:
            self._log_operation("_sliding_window_check", f"Sliding window check failed: {str(e)}", "error")
            return {
                'allowed': False,
                'wait_time_ms': 0,
                'error': str(e)
            }
    
    async def _fixed_window_check(self, domain: str, limits: Dict[str, Any], wait_for_slot: bool) -> Dict[str, Any]:
        """Fixed window rate limiting algorithm."""
        try:
            current_time = datetime.utcnow()
            
            # Get window start time for the domain
            window_start = self._window_start_time[domain]
            
            # Check if we need to reset the window
            if current_time - window_start >= timedelta(seconds=60):
                self._window_start_time[domain] = current_time
                self._request_counts[domain]['minute'] = 0
            
            # Check if we can make a request
            if self._request_counts[domain]['minute'] < limits['requests_per_minute']:
                self._request_counts[domain]['minute'] += 1
                return {
                    'allowed': True,
                    'wait_time_ms': 0,
                    'requests_in_window': self._request_counts[domain]['minute']
                }
            
            # Calculate wait time until next window
            wait_time_ms = 0
            if wait_for_slot:
                next_window = window_start + timedelta(seconds=60)
                wait_time = next_window - current_time
                wait_time_ms = int(wait_time.total_seconds() * 1000)
                
                if wait_time_ms > 0:
                    await asyncio.sleep(wait_time_ms / 1000.0)
                    
                    # Reset window and allow request
                    self._window_start_time[domain] = datetime.utcnow()
                    self._request_counts[domain]['minute'] = 1
                    return {
                        'allowed': True,
                        'wait_time_ms': wait_time_ms,
                        'requests_in_window': 1
                    }
            
            return {
                'allowed': False,
                'wait_time_ms': wait_time_ms,
                'requests_in_window': self._request_counts[domain]['minute']
            }
            
        except Exception as e:
            self._log_operation("_fixed_window_check", f"Fixed window check failed: {str(e)}", "error")
            return {
                'allowed': False,
                'wait_time_ms': 0,
                'error': str(e)
            }
    
    def set_domain_limits(self, domain: str, **limits) -> None:
        """
        Set rate limits for a specific domain.
        
        Args:
            domain: Domain name
            **limits: Rate limit parameters
        """
        if domain not in self._domain_limits:
            self._domain_limits[domain] = {}
        
        self._domain_limits[domain].update(limits)
        
        # Initialize token bucket for new domain
        if domain not in self._token_bucket:
            self._token_bucket[domain] = float(limits.get('burst_capacity', self._burst_capacity))
            self._last_refill_time[domain] = datetime.utcnow()
    
    def set_endpoint_limits(self, endpoint: str, **limits) -> None:
        """
        Set rate limits for a specific endpoint.
        
        Args:
            endpoint: Endpoint name
            **limits: Rate limit parameters
        """
        if endpoint not in self._endpoint_limits:
            self._endpoint_limits[endpoint] = {}
        
        self._endpoint_limits[endpoint].update(limits)
    
    def set_rate_limit_callbacks(self, hit_callback: Callable = None, reset_callback: Callable = None):
        """
        Set rate limiting callback functions.
        
        Args:
            hit_callback: Function to call when rate limit is hit
            reset_callback: Function to call when rate limit resets
        """
        self._rate_limit_hit_callback = hit_callback
        self._rate_limit_reset_callback = reset_callback
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        return self._statistics.copy()
    
    def reset_statistics(self) -> None:
        """Reset rate limiting statistics."""
        self._statistics = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'rate_limit_hits': 0,
            'average_wait_time_ms': 0.0,
            'total_wait_time_ms': 0.0
        }
    
    def get_domain_status(self, domain: str) -> Dict[str, Any]:
        """Get rate limiting status for a domain."""
        return {
            'domain': domain,
            'algorithm': self._algorithm,
            'tokens_remaining': self._token_bucket.get(domain, 0),
            'requests_in_history': len(self._request_history.get(domain, [])),
            'request_counts': dict(self._request_counts.get(domain, {})),
            'limits': self._get_effective_limits(domain, None)
        }
    
    def configure_rate_limiting(
        self,
        algorithm: str = None,
        requests_per_second: float = None,
        requests_per_minute: int = None,
        requests_per_hour: int = None,
        burst_capacity: int = None
    ) -> None:
        """
        Configure rate limiting settings.
        
        Args:
            algorithm: Rate limiting algorithm
            requests_per_second: Requests per second
            requests_per_minute: Requests per minute
            requests_per_hour: Requests per hour
            burst_capacity: Burst capacity for token bucket
        """
        if algorithm is not None:
            self._algorithm = algorithm
        if requests_per_second is not None:
            self._requests_per_second = requests_per_second
        if requests_per_minute is not None:
            self._requests_per_minute = requests_per_minute
        if requests_per_hour is not None:
            self._requests_per_hour = requests_per_hour
        if burst_capacity is not None:
            self._burst_capacity = burst_capacity
    
    def get_rate_limiting_configuration(self) -> Dict[str, Any]:
        """Get current rate limiting configuration."""
        return {
            'algorithm': self._algorithm,
            'requests_per_second': self._requests_per_second,
            'requests_per_minute': self._requests_per_minute,
            'requests_per_hour': self._requests_per_hour,
            'burst_capacity': self._burst_capacity,
            'domain_limits': self._domain_limits,
            'endpoint_limits': self._endpoint_limits,
            'statistics': self._statistics,
            **self.get_configuration()
        }
    
    async def cleanup(self) -> None:
        """Clean up rate limiter component."""
        try:
            # Clear rate limiting state
            self._token_bucket.clear()
            self._last_refill_time.clear()
            self._request_history.clear()
            self._window_start_time.clear()
            self._request_counts.clear()
            
            # Reset statistics
            self.reset_statistics()
            
            self._log_operation("cleanup", "Rate limiter component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Rate limiter cleanup failed: {str(e)}", "error")
