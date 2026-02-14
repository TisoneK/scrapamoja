"""
Snapshot data models for the web scraping system.

This module defines the core data structures used throughout the snapshot system,
including context, configuration, and bundle models.
"""

import asyncio
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import uuid


class EnumEncoder(json.JSONEncoder):
    """Custom JSON encoder for enums."""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class SnapshotMode(Enum):
    """Snapshot capture modes."""
    FULL_PAGE = "full_page"
    SELECTOR = "selector"
    MINIMAL = "minimal"
    BOTH = "both"


class RolloutStage(Enum):
    """Feature rollout stages."""
    DISABLED = "disabled"
    INTERNAL_TESTING = "internal_testing"
    BETA_TESTING = "beta_testing"
    GRADUAL_ROLLOUT = "gradual_rollout"
    FULL_ROLLOUT = "full_rollout"


@dataclass
class SnapshotContext:
    """Provides hierarchical organization and traceability for snapshots."""
    site: str
    module: str
    component: str
    session_id: str
    function: Optional[str] = None
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def generate_hierarchical_path(self, timestamp: datetime) -> str:
        """Generate hierarchical path based on context and timestamp."""
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        return f"{self.site}/{self.module}/{self.component}/{date_str}/{time_str}_{self.session_id}"


@dataclass
class SnapshotConfig:
    """Configures snapshot capture behavior."""
    mode: SnapshotMode = SnapshotMode.SELECTOR
    capture_html: bool = True
    capture_screenshot: bool = False
    capture_network: bool = False
    capture_console: bool = False
    selector: Optional[str] = None
    capture_full_page: bool = False
    deduplication_enabled: bool = True
    async_save: bool = True
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.mode == SnapshotMode.SELECTOR and not self.selector:
            raise ValueError("Selector mode requires a valid CSS selector")
        
        if self.mode == SnapshotMode.BOTH and not self.selector:
            raise ValueError("Both mode requires a selector for element capture")


@dataclass
class SnapshotMetrics:
    """Performance metrics for snapshot operations."""
    total_snapshots: int = 0
    successful_snapshots: int = 0
    failed_snapshots: int = 0
    average_capture_time: float = 0.0
    deduplication_hits: int = 0
    deduplication_misses: int = 0
    parallel_executions: int = 0
    sequential_executions: int = 0
    cache_size: int = 0
    cache_utilization: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_snapshots == 0:
            return 0.0
        return (self.successful_snapshots / self.total_snapshots) * 100.0
    
    @property
    def deduplication_rate(self) -> float:
        """Calculate deduplication rate percentage."""
        total = self.deduplication_hits + self.deduplication_misses
        if total == 0:
            return 0.0
        return (self.deduplication_hits / total) * 100.0
    
    @property
    def parallel_execution_rate(self) -> float:
        """Calculate parallel execution rate percentage."""
        total = self.parallel_executions + self.sequential_executions
        if total == 0:
            return 0.0
        return (self.parallel_executions / total) * 100.0


@dataclass
class SnapshotBundle:
    """Represents a complete snapshot with all artifacts."""
    context: SnapshotContext
    timestamp: datetime
    config: SnapshotConfig
    bundle_path: str
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: Optional[str] = None
    bundle_version: str = "1.0"
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.content_hash:
            self.content_hash = self._calculate_content_hash()
    
    def _calculate_content_hash(self) -> str:
        """Calculate MD5 hash of bundle content."""
        content = {
            "context": asdict(self.context),
            "timestamp": self.timestamp.isoformat(),
            "config": asdict(self.config),
            "artifacts": sorted(self.artifacts),
            "metadata": self.metadata
        }
        content_str = json.dumps(content, sort_keys=True, cls=EnumEncoder)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to dictionary representation."""
        return {
            "context": asdict(self.context),
            "timestamp": self.timestamp.isoformat(),
            "config": asdict(self.config),
            "bundle_path": self.bundle_path,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
            "bundle_version": self.bundle_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotBundle":
        """Create bundle from dictionary representation."""
        context = SnapshotContext(**data["context"])
        timestamp = datetime.fromisoformat(data["timestamp"])
        config = SnapshotConfig(**data["config"])
        
        return cls(
            context=context,
            timestamp=timestamp,
            config=config,
            bundle_path=data["bundle_path"],
            artifacts=data.get("artifacts", []),
            metadata=data.get("metadata", {}),
            content_hash=data.get("content_hash"),
            bundle_version=data.get("bundle_version", "1.0")
        )
    
    def validate(self) -> bool:
        """Validate bundle integrity."""
        if not os.path.exists(self.bundle_path):
            return False
        
        # Check if all artifacts exist
        for artifact in self.artifacts:
            artifact_path = os.path.join(self.bundle_path, artifact)
            if not os.path.exists(artifact_path):
                return False
        
        # Validate content hash
        calculated_hash = self._calculate_content_hash()
        if calculated_hash != self.content_hash:
            return False
        
        return True


class SnapshotError(Exception):
    """Base exception for snapshot system errors."""
    pass


class BundleCorruptionError(SnapshotError):
    """Raised when snapshot bundle is corrupted."""
    pass


class ArtifactCaptureError(SnapshotError):
    """Raised when artifact capture fails."""
    pass


class ConfigurationError(SnapshotError):
    """Raised when configuration is invalid."""
    pass


@dataclass
class RateLimiter:
    """Rate limiter for snapshot triggers."""
    max_requests_per_minute: int = 5
    request_timestamps: Dict[str, List[datetime]] = field(default_factory=dict)
    
    def should_allow(self, trigger_type: str) -> bool:
        """Check if trigger should be allowed based on rate limit."""
        now = datetime.now()
        
        # Clean old timestamps
        if trigger_type in self.request_timestamps:
            self.request_timestamps[trigger_type] = [
                ts for ts in self.request_timestamps[trigger_type]
                if (now - ts).total_seconds() < 60
            ]
        else:
            self.request_timestamps[trigger_type] = []
        
        # Check if under limit
        if len(self.request_timestamps[trigger_type]) < self.max_requests_per_minute:
            self.request_timestamps[trigger_type].append(now)
            return True
        
        return False


@dataclass
class ContentDeduplicator:
    """Content deduplication system."""
    max_cache_size: int = 1000
    content_cache: Dict[str, str] = field(default_factory=dict)
    cache_access_order: List[str] = field(default_factory=list)
    
    def get_content_hash(self, content: str) -> str:
        """Get MD5 hash of content."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_duplicate(self, content: str) -> Optional[str]:
        """Check if content is duplicate and return existing hash."""
        content_hash = self.get_content_hash(content)
        
        if content_hash in self.content_cache:
            # Update access order
            if content_hash in self.cache_access_order:
                self.cache_access_order.remove(content_hash)
            self.cache_access_order.append(content_hash)
            return content_hash
        
        return None
    
    def add_content(self, content: str) -> str:
        """Add content to cache and return hash."""
        content_hash = self.get_content_hash(content)
        
        # Evict if cache is full
        if len(self.content_cache) >= self.max_cache_size:
            oldest_hash = self.cache_access_order.pop(0)
            del self.content_cache[oldest_hash]
        
        self.content_cache[content_hash] = content
        self.cache_access_order.append(content_hash)
        
        return content_hash
    
    @property
    def cache_size(self) -> int:
        """Get current cache size."""
        return len(self.content_cache)
    
    @property
    def cache_utilization(self) -> float:
        """Get cache utilization percentage."""
        return (self.cache_size / self.max_cache_size) * 100.0
