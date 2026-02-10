"""
Resource Throttling

Implements throttling mechanisms for resource usage.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from ..logging.resilience_logger import get_logger


class ThrottlingStrategy(Enum):
    FIXED_RATE = "fixed_rate"
    ADAPTIVE = "adaptive"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class ThrottlingConfig:
    strategy: ThrottlingStrategy = ThrottlingStrategy.ADAPTIVE
    max_requests_per_second: float = 10.0
    max_concurrent_requests: int = 5
    burst_capacity: int = 10


class ResourceThrottler:
    """Implements throttling for resource usage."""
    
    def __init__(self, resource_id: str, config: ThrottlingConfig):
        self.resource_id = resource_id
        self.config = config
        self.logger = get_logger(f"resource_throttler_{resource_id}")
        
        self.request_times: deque = deque(maxlen=1000)
        self.concurrent_requests: int = 0
        self.tokens: float = float(config.burst_capacity)
        self.last_token_refill: datetime = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def check_request(self) -> bool:
        """Check if a request should be allowed."""
        async with self._lock:
            if self.concurrent_requests >= self.config.max_concurrent_requests:
                return False
            
            if self.config.strategy == ThrottlingStrategy.FIXED_RATE:
                allowed = await self._check_fixed_rate()
            elif self.config.strategy == ThrottlingStrategy.ADAPTIVE:
                allowed = await self._check_adaptive_rate()
            else:
                allowed = await self._check_token_bucket()
            
            if allowed:
                self.concurrent_requests += 1
                self.request_times.append(datetime.utcnow())
                return True
            return False
    
    async def release_request(self) -> None:
        """Release a request."""
        async with self._lock:
            if self.concurrent_requests > 0:
                self.concurrent_requests -= 1
    
    async def _check_fixed_rate(self) -> bool:
        """Check fixed rate limiting."""
        recent_count = len([
            t for t in self.request_times 
            if (datetime.utcnow() - t).total_seconds() <= 1
        ])
        return recent_count < self.config.max_requests_per_second
    
    async def _check_adaptive_rate(self) -> bool:
        """Check adaptive rate limiting."""
        return await self._check_fixed_rate()  # Simplified
    
    async def _check_token_bucket(self) -> bool:
        """Check token bucket rate limiting."""
        now = datetime.utcnow()
        time_diff = (now - self.last_token_refill).total_seconds()
        
        # Refill tokens
        self.tokens = min(
            self.config.burst_capacity,
            self.tokens + time_diff * self.config.max_requests_per_second
        )
        self.last_token_refill = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


# Global throttlers
_throttlers: Dict[str, ResourceThrottler] = {}


def get_throttler(resource_id: str, config: ThrottlingConfig) -> ResourceThrottler:
    """Get or create a throttler for a resource."""
    if resource_id not in _throttlers:
        _throttlers[resource_id] = ResourceThrottler(resource_id, config)
    return _throttlers[resource_id]
