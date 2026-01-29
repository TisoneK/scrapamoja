"""
Performance Metrics Model

Timing and resource usage information for selector operations
following the data model specification.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class PerformanceMetrics(BaseModel):
    """
    Timing and resource usage information for selector operations.
    
    Contains comprehensive performance data including timing information,
    resource usage, and operation counts for detailed performance analysis.
    """
    
    resolution_time_ms: float = Field(..., description="Time taken for selector resolution in milliseconds")
    strategy_execution_time_ms: float = Field(..., description="Time for strategy execution in milliseconds")
    total_duration_ms: float = Field(..., description="Total operation duration in milliseconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory consumed during operation in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU utilization during operation (0-100)")
    network_requests_count: Optional[int] = Field(None, description="Number of network requests made")
    dom_operations_count: Optional[int] = Field(None, description="Number of DOM operations performed")
    
    @validator('resolution_time_ms')
    def validate_resolution_time_ms(cls, v):
        """Validate resolution time is non-negative."""
        if v < 0:
            raise ValueError("resolution_time_ms must be non-negative")
        return v
    
    @validator('strategy_execution_time_ms')
    def validate_strategy_execution_time_ms(cls, v):
        """Validate strategy execution time is non-negative."""
        if v < 0:
            raise ValueError("strategy_execution_time_ms must be non-negative")
        return v
    
    @validator('total_duration_ms')
    def validate_total_duration_ms(cls, v):
        """Validate total duration is non-negative."""
        if v < 0:
            raise ValueError("total_duration_ms must be non-negative")
        return v
    
    @validator('memory_usage_mb')
    def validate_memory_usage_mb(cls, v):
        """Validate memory usage is reasonable."""
        if v is not None:
            if v < 0:
                raise ValueError("memory_usage_mb must be non-negative")
            if v > 1024:  # 1GB limit per operation
                raise ValueError("memory_usage_mb must be less than 1024 MB")
        return v
    
    @validator('cpu_usage_percent')
    def validate_cpu_usage_percent(cls, v):
        """Validate CPU usage is within valid range."""
        if v is not None:
            if not 0 <= v <= 100:
                raise ValueError("cpu_usage_percent must be between 0 and 100")
        return v
    
    @validator('network_requests_count')
    def validate_network_requests_count(cls, v):
        """Validate network requests count is non-negative."""
        if v is not None:
            if v < 0:
                raise ValueError("network_requests_count must be non-negative")
        return v
    
    @validator('dom_operations_count')
    def validate_dom_operations_count(cls, v):
        """Validate DOM operations count is non-negative."""
        if v is not None:
            if v < 0:
                raise ValueError("dom_operations_count must be non-negative")
        return v
    
    def get_strategy_overhead_percentage(self) -> float:
        """
        Calculate strategy execution overhead as percentage of total time.
        
        Returns:
            Strategy overhead percentage (0-100)
        """
        if self.total_duration_ms == 0:
            return 0.0
        return (self.strategy_execution_time_ms / self.total_duration_ms) * 100
    
    def get_resolution_efficiency(self) -> float:
        """
        Calculate resolution efficiency (resolution time vs total time).
        
        Returns:
            Resolution efficiency percentage (0-100)
        """
        if self.total_duration_ms == 0:
            return 0.0
        return (self.resolution_time_ms / self.total_duration_ms) * 100
    
    def is_high_memory_usage(self, threshold_mb: float = 100.0) -> bool:
        """
        Check if memory usage is high.
        
        Args:
            threshold_mb: Memory threshold in MB
            
        Returns:
            True if memory usage exceeds threshold
        """
        return self.memory_usage_mb is not None and self.memory_usage_mb > threshold_mb
    
    def is_high_cpu_usage(self, threshold_percent: float = 50.0) -> bool:
        """
        Check if CPU usage is high.
        
        Args:
            threshold_percent: CPU usage threshold percentage
            
        Returns:
            True if CPU usage exceeds threshold
        """
        return self.cpu_usage_percent is not None and self.cpu_usage_percent > threshold_percent
    
    def is_network_intensive(self, threshold_requests: int = 10) -> bool:
        """
        Check if operation is network intensive.
        
        Args:
            threshold_requests: Network request threshold
            
        Returns:
            True if network requests exceed threshold
        """
        return self.network_requests_count is not None and self.network_requests_count > threshold_requests
    
    def is_dom_intensive(self, threshold_operations: int = 50) -> bool:
        """
        Check if operation is DOM intensive.
        
        Args:
            threshold_operations: DOM operations threshold
            
        Returns:
            True if DOM operations exceed threshold
        """
        return self.dom_operations_count is not None and self.dom_operations_count > threshold_operations
    
    def to_dict(self) -> dict:
        """Convert to dictionary with all fields."""
        return {
            "resolution_time_ms": self.resolution_time_ms,
            "strategy_execution_time_ms": self.strategy_execution_time_ms,
            "total_duration_ms": self.total_duration_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "network_requests_count": self.network_requests_count,
            "dom_operations_count": self.dom_operations_count
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
