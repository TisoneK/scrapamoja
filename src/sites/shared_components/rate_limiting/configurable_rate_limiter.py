"""
Configurable rate limiting component for the scraper framework.

This module provides comprehensive rate limiting capabilities, including
per-site configuration, multiple rate limiting strategies, and feature flag integration.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import deque, defaultdict

from ...base.component_interface import BaseComponent, ComponentContext, ComponentResult
from ...base.feature_flags import is_enabled, get_value
from ...base.config_loader import get_config_value


class RateLimitStrategy(Enum):
    """Rate limiting strategy enumeration."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_requests_per_day: int = 10000
    burst_size: int = 10
    refill_rate: float = 1.0
    window_size_seconds: int = 60
    adaptive_threshold: float = 0.8
    backoff_multiplier: float = 2.0
    max_backoff_seconds: int = 300
    site_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_site_config(self, site: str) -> Dict[str, Any]:
        """Get site-specific configuration."""
        site_config = self.site_overrides.get(site, {})
        
        return {
            'enabled': site_config.get('enabled', self.enabled),
            'strategy': RateLimitStrategy(site_config.get('strategy', self.strategy.value)),
            'max_requests_per_minute': site_config.get('max_requests_per_minute', self.max_requests_per_minute),
            'max_requests_per_hour': site_config.get('max_requests_per_hour', self.max_requests_per_hour),
            'max_requests_per_day': site_config.get('max_requests_per_day', self.max_requests_per_day),
            'burst_size': site_config.get('burst_size', self.burst_size),
            'refill_rate': site_config.get('refill_rate', self.refill_rate),
            'window_size_seconds': site_config.get('window_size_seconds', self.window_size_seconds),
            'adaptive_threshold': site_config.get('adaptive_threshold', self.adaptive_threshold),
            'backoff_multiplier': site_config.get('backoff_multiplier', self.backoff_multiplier),
            'max_backoff_seconds': site_config.get('max_backoff_seconds', self.max_backoff_seconds)
        }


@dataclass
class RateLimitResult:
    """Rate limiting result."""
    allowed: bool
    wait_time_seconds: float = 0.0
    remaining_requests: int = 0
    reset_time: Optional[datetime] = None
    strategy_used: str = ""
    site: str = ""
    reason: str = ""
    backoff_applied: bool = False
    adaptive_adjustment: bool = False


class TokenBucketLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> RateLimitResult:
        """Consume tokens from the bucket."""
        with self._lock:
            now = time.time()
            
            # Refill tokens
            time_passed = now - self.last_refill
            tokens_to_add = time_passed * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return RateLimitResult(
                    allowed=True,
                    remaining_requests=int(self.tokens),
                    strategy_used="token_bucket"
                )
            else:
                wait_time = (tokens - self.tokens) / self.refill_rate
                return RateLimitResult(
                    allowed=False,
                    wait_time_seconds=wait_time,
                    remaining_requests=int(self.tokens),
                    strategy_used="token_bucket",
                    reason="Insufficient tokens"
                )


class SlidingWindowLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_size_seconds: int):
        self.max_requests = max_requests
        self.window_size_seconds = window_size_seconds
        self.requests = deque()
        self._lock = threading.Lock()
    
    def consume(self) -> RateLimitResult:
        """Consume a request from the sliding window."""
        with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_size_seconds:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return RateLimitResult(
                    allowed=True,
                    remaining_requests=self.max_requests - len(self.requests),
                    strategy_used="sliding_window"
                )
            else:
                # Calculate wait time until oldest request expires
                oldest_request = self.requests[0]
                wait_time = self.window_size_seconds - (now - oldest_request)
                return RateLimitResult(
                    allowed=False,
                    wait_time_seconds=wait_time,
                    remaining_requests=0,
                    strategy_used="sliding_window",
                    reason="Sliding window full"
                )


class FixedWindowLimiter:
    """Fixed window rate limiter."""
    
    def __init__(self, max_requests: int, window_size_seconds: int):
        self.max_requests = max_requests
        self.window_size_seconds = window_size_seconds
        self.current_window = 0
        self.request_count = 0
        self.window_start = time.time()
        self._lock = threading.Lock()
    
    def consume(self) -> RateLimitResult:
        """Consume a request from the fixed window."""
        with self._lock:
            now = time.time()
            
            # Check if we need to reset the window
            if now - self.window_start >= self.window_size_seconds:
                self.window_start = now
                self.request_count = 0
            
            if self.request_count < self.max_requests:
                self.request_count += 1
                return RateLimitResult(
                    allowed=True,
                    remaining_requests=self.max_requests - self.request_count,
                    reset_time=datetime.fromtimestamp(self.window_start + self.window_size_seconds),
                    strategy_used="fixed_window"
                )
            else:
                wait_time = self.window_size_seconds - (now - self.window_start)
                return RateLimitResult(
                    allowed=False,
                    wait_time_seconds=wait_time,
                    remaining_requests=0,
                    reset_time=datetime.fromtimestamp(self.window_start + self.window_size_seconds),
                    strategy_used="fixed_window",
                    reason="Fixed window full"
                )


class LeakyBucketLimiter:
    """Leaky bucket rate limiter."""
    
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.volume = 0.0
        self.last_leak = time.time()
        self._lock = threading.Lock()
    
    def consume(self) -> RateLimitResult:
        """Consume a request from the leaky bucket."""
        with self._lock:
            now = time.time()
            
            # Leak volume
            time_passed = now - self.last_leak
            self.volume = max(0, self.volume - time_passed * self.leak_rate)
            self.last_leak = now
            
            if self.volume < self.capacity:
                self.volume += 1
                return RateLimitResult(
                    allowed=True,
                    remaining_requests=int(self.capacity - self.volume),
                    strategy_used="leaky_bucket"
                )
            else:
                wait_time = (self.volume - self.capacity + 1) / self.leak_rate
                return RateLimitResult(
                    allowed=False,
                    wait_time_seconds=wait_time,
                    remaining_requests=0,
                    strategy_used="leaky_bucket",
                    reason="Leaky bucket full"
                )


class AdaptiveLimiter:
    """Adaptive rate limiter that adjusts based on response patterns."""
    
    def __init__(self, base_config: Dict[str, Any]):
        self.base_config = base_config
        self.current_limit = base_config['max_requests_per_minute']
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment = time.time()
        self.adjustment_window = 300  # 5 minutes
        self._lock = threading.Lock()
        
        # Use token bucket as the underlying limiter
        self.token_bucket = TokenBucketLimiter(
            self.current_limit,
            self.current_limit / 60.0
        )
    
    def consume(self) -> RateLimitResult:
        """Consume a request with adaptive adjustment."""
        with self._lock:
            now = time.time()
            
            # Check if we should adjust the rate
            if now - self.last_adjustment >= self.adjustment_window:
                self._adjust_rate()
                self.last_adjustment = now
            
            result = self.token_bucket.consume()
            result.strategy_used = "adaptive"
            result.adaptive_adjustment = True
            
            return result
    
    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self.success_count += 1
    
    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self.failure_count += 1
    
    def _adjust_rate(self) -> None:
        """Adjust the rate based on success/failure patterns."""
        total_requests = self.success_count + self.failure_count
        
        if total_requests == 0:
            return
        
        success_rate = self.success_count / total_requests
        threshold = self.base_config['adaptive_threshold']
        
        if success_rate < threshold:
            # Reduce rate
            new_limit = max(
                1,
                int(self.current_limit * self.base_config['backoff_multiplier'])
            )
            self.current_limit = new_limit
        elif success_rate > 0.95:
            # Increase rate gradually
            new_limit = min(
                self.base_config['max_requests_per_minute'],
                int(self.current_limit * 1.1)
            )
            self.current_limit = new_limit
        
        # Reset counters
        self.success_count = 0
        self.failure_count = 0
        
        # Update token bucket
        self.token_bucket = TokenBucketLimiter(
            self.current_limit,
            self.current_limit / 60.0
        )


class ConfigurableRateLimiterComponent(BaseComponent):
    """Configurable rate limiting component."""
    
    COMPONENT_METADATA = {
        'id': 'configurable_rate_limiter',
        'name': 'Configurable Rate Limiter',
        'version': '1.0.0',
        'type': 'rate_limiting',
        'description': 'Configurable rate limiting with multiple strategies and feature flag integration',
        'dependencies': [],
        'sites': ['all'],
        'tags': ['rate_limiting', 'performance', 'configuration']
    }
    
    def __init__(self):
        """Initialize configurable rate limiter."""
        super().__init__()
        self._limiters: Dict[str, Any] = {}
        self._config = RateLimitConfig()
        self._stats = defaultdict(lambda: {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'total_wait_time': 0.0,
            'average_wait_time': 0.0,
            'last_request_time': None,
            'backoff_count': 0
        })
        self._lock = threading.Lock()
    
    async def initialize(self, context: ComponentContext) -> bool:
        """Initialize the rate limiter component."""
        try:
            # Load configuration
            await self._load_configuration(context)
            
            # Check feature flags
            if not is_enabled('rate_limiting_enabled'):
                self.logger.info("Rate limiting disabled by feature flag")
                return True
            
            # Initialize limiters for each site
            await self._initialize_limiters()
            
            self.logger.info("Configurable rate limiter initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize rate limiter: {str(e)}")
            return False
    
    async def execute(self, site: str, **kwargs) -> ComponentResult:
        """Execute rate limiting check."""
        try:
            # Check if rate limiting is enabled
            if not self._is_enabled_for_site(site):
                return ComponentResult(
                    success=True,
                    data={'allowed': True, 'reason': 'Rate limiting disabled'},
                    execution_time_ms=0
                )
            
            # Get or create limiter for site
            limiter = self._get_limiter(site)
            
            # Perform rate limiting check
            start_time = time.time()
            result = limiter.consume()
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(site, result)
            
            # Apply wait time if needed
            if not result.allowed and result.wait_time_seconds > 0:
                await asyncio.sleep(result.wait_time_seconds)
                result.backoff_applied = True
            
            # Record result for adaptive limiter
            if isinstance(limiter, AdaptiveLimiter):
                if result.allowed:
                    limiter.record_success()
                else:
                    limiter.record_failure()
            
            return ComponentResult(
                success=True,
                data={
                    'allowed': result.allowed,
                    'wait_time_seconds': result.wait_time_seconds,
                    'remaining_requests': result.remaining_requests,
                    'strategy_used': result.strategy_used,
                    'backoff_applied': result.backoff_applied,
                    'adaptive_adjustment': result.adaptive_adjustment,
                    'reason': result.reason
                },
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            self.logger.error(f"Rate limiting check failed: {str(e)}")
            return ComponentResult(
                success=False,
                errors=[str(e)],
                execution_time_ms=0
            )
    
    async def _load_configuration(self, context: ComponentContext) -> None:
        """Load rate limiting configuration."""
        # Load from context
        config_data = context.config.get('rate_limiting', {})
        
        # Load from global config
        global_config = {
            'enabled': get_config_value('rate_limiting.enabled', True),
            'strategy': get_config_value('rate_limiting.strategy', 'token_bucket'),
            'max_requests_per_minute': get_config_value('rate_limiting.max_requests_per_minute', 60),
            'max_requests_per_hour': get_config_value('rate_limiting.max_requests_per_hour', 1000),
            'max_requests_per_day': get_config_value('rate_limiting.max_requests_per_day', 10000),
            'burst_size': get_config_value('rate_limiting.burst_size', 10),
            'refill_rate': get_config_value('rate_limiting.refill_rate', 1.0),
            'window_size_seconds': get_config_value('rate_limiting.window_size_seconds', 60),
            'adaptive_threshold': get_config_value('rate_limiting.adaptive_threshold', 0.8),
            'backoff_multiplier': get_config_value('rate_limiting.backoff_multiplier', 2.0),
            'max_backoff_seconds': get_config_value('rate_limiting.max_backoff_seconds', 300)
        }
        
        # Merge configurations
        merged_config = {**global_config, **config_data}
        
        # Create RateLimitConfig
        self._config = RateLimitConfig(
            enabled=merged_config.get('enabled', True),
            strategy=RateLimitStrategy(merged_config.get('strategy', 'token_bucket')),
            max_requests_per_minute=merged_config.get('max_requests_per_minute', 60),
            max_requests_per_hour=merged_config.get('max_requests_per_hour', 1000),
            max_requests_per_day=merged_config.get('max_requests_per_day', 10000),
            burst_size=merged_config.get('burst_size', 10),
            refill_rate=merged_config.get('refill_rate', 1.0),
            window_size_seconds=merged_config.get('window_size_seconds', 60),
            adaptive_threshold=merged_config.get('adaptive_threshold', 0.8),
            backoff_multiplier=merged_config.get('backoff_multiplier', 2.0),
            max_backoff_seconds=merged_config.get('max_backoff_seconds', 300),
            site_overrides=merged_config.get('site_overrides', {})
        )
    
    async def _initialize_limiters(self) -> None:
        """Initialize rate limiters for all sites."""
        # Common sites that might need rate limiting
        common_sites = [
            'google', 'facebook', 'twitter', 'amazon', 'wikipedia',
            'linkedin', 'instagram', 'youtube', 'reddit', 'github'
        ]
        
        for site in common_sites:
            self._get_limiter(site)
    
    def _is_enabled_for_site(self, site: str) -> bool:
        """Check if rate limiting is enabled for a site."""
        # Check global feature flag
        if not is_enabled('rate_limiting_enabled'):
            return False
        
        # Check site-specific configuration
        site_config = self._config.get_site_config(site)
        return site_config['enabled']
    
    def _get_limiter(self, site: str) -> Any:
        """Get or create a limiter for a site."""
        with self._lock:
            if site not in self._limiters:
                site_config = self._config.get_site_config(site)
                self._limiters[site] = self._create_limiter(site_config)
            
            return self._limiters[site]
    
    def _create_limiter(self, config: Dict[str, Any]) -> Any:
        """Create a rate limiter based on configuration."""
        strategy = config['strategy']
        
        if strategy == RateLimitStrategy.TOKEN_BUCKET:
            return TokenBucketLimiter(
                config['max_requests_per_minute'],
                config['refill_rate']
            )
        elif strategy == RateLimitStrategy.SLIDING_WINDOW:
            return SlidingWindowLimiter(
                config['max_requests_per_minute'],
                config['window_size_seconds']
            )
        elif strategy == RateLimitStrategy.FIXED_WINDOW:
            return FixedWindowLimiter(
                config['max_requests_per_minute'],
                config['window_size_seconds']
            )
        elif strategy == RateLimitStrategy.LEAKY_BUCKET:
            return LeakyBucketLimiter(
                config['burst_size'],
                config['refill_rate']
            )
        elif strategy == RateLimitStrategy.ADAPTIVE:
            return AdaptiveLimiter(config)
        else:
            # Default to token bucket
            return TokenBucketLimiter(
                config['max_requests_per_minute'],
                config['refill_rate']
            )
    
    def _update_stats(self, site: str, result: RateLimitResult) -> None:
        """Update rate limiting statistics."""
        with self._lock:
            stats = self._stats[site]
            stats['total_requests'] += 1
            stats['last_request_time'] = datetime.utcnow()
            
            if result.allowed:
                stats['allowed_requests'] += 1
            else:
                stats['blocked_requests'] += 1
                stats['total_wait_time'] += result.wait_time_seconds
            
            if result.backoff_applied:
                stats['backoff_count'] += 1
            
            # Calculate average wait time
            if stats['total_requests'] > 0:
                stats['average_wait_time'] = stats['total_wait_time'] / stats['total_requests']
    
    def get_stats(self, site: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        with self._lock:
            if site:
                return dict(self._stats.get(site, {}))
            else:
                return {site: dict(stats) for site, stats in self._stats.items()}
    
    def reset_stats(self, site: Optional[str] = None) -> None:
        """Reset rate limiting statistics."""
        with self._lock:
            if site:
                if site in self._stats:
                    self._stats[site] = {
                        'total_requests': 0,
                        'allowed_requests': 0,
                        'blocked_requests': 0,
                        'total_wait_time': 0.0,
                        'average_wait_time': 0.0,
                        'last_request_time': None,
                        'backoff_count': 0
                    }
            else:
                self._stats.clear()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update rate limiting configuration."""
        with self._lock:
            # Update configuration
            for key, value in config.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            
            # Recreate limiters
            self._limiters.clear()
    
    def get_site_config(self, site: str) -> Dict[str, Any]:
        """Get configuration for a specific site."""
        return self._config.get_site_config(site)
    
    def set_site_override(self, site: str, config: Dict[str, Any]) -> None:
        """Set site-specific configuration override."""
        with self._lock:
            self._config.site_overrides[site] = config
            
            # Recreate limiter for this site
            if site in self._limiters:
                del self._limiters[site]
    
    def remove_site_override(self, site: str) -> None:
        """Remove site-specific configuration override."""
        with self._lock:
            if site in self._config.site_overrides:
                del self._config.site_overrides[site]
            
            # Recreate limiter for this site
            if site in self._limiters:
                del self._limiters[site]


# Convenience functions
def create_rate_limiter() -> ConfigurableRateLimiterComponent:
    """Create a new rate limiter component."""
    return ConfigurableRateLimiterComponent()


def check_rate_limit(site: str, **kwargs) -> RateLimitResult:
    """Check rate limit for a site."""
    limiter = create_rate_limiter()
    # This would need proper initialization in a real scenario
    # For now, return a default result
    return RateLimitResult(allowed=True, site=site)


def get_rate_limit_stats(site: Optional[str] = None) -> Dict[str, Any]:
    """Get rate limiting statistics."""
    limiter = create_rate_limiter()
    return limiter.get_stats(site)
