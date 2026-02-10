"""
Strategy Metrics Model

Information about strategy usage and effectiveness for selector operations
following the data model specification.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


class StrategyMetrics(BaseModel):
    """
    Information about strategy usage and effectiveness.
    
    Contains comprehensive strategy data including primary strategy,
    secondary strategies, execution order, success rates, and timing.
    """
    
    primary_strategy: str = Field(..., description="Name of primary strategy used")
    secondary_strategies: Optional[List[str]] = Field(default_factory=list, description="Secondary strategies attempted")
    strategy_execution_order: Optional[List[str]] = Field(default_factory=list, description="Order of strategy execution")
    strategy_success_by_type: Optional[Dict[str, bool]] = Field(default_factory=dict, description="Success status by strategy")
    strategy_timing_by_type: Optional[Dict[str, float]] = Field(default_factory=dict, description="Timing by strategy in milliseconds")
    strategy_switches_count: Optional[int] = Field(0, description="Number of strategy switches")
    
    @validator('primary_strategy')
    def validate_primary_strategy(cls, v):
        """Validate primary strategy is not empty."""
        if not v or not v.strip():
            raise ValueError("primary_strategy must be a non-empty string")
        return v.strip()
    
    @validator('secondary_strategies')
    def validate_secondary_strategies(cls, v):
        """Validate secondary strategies list."""
        if v is None:
            return []
        
        if not isinstance(v, list):
            raise ValueError("secondary_strategies must be a list")
        
        # Filter out empty strings and strip whitespace
        cleaned_strategies = [s.strip() for s in v if s and s.strip()]
        return cleaned_strategies
    
    @validator('strategy_execution_order')
    def validate_strategy_execution_order(cls, v):
        """Validate strategy execution order."""
        if v is None:
            return []
        
        if not isinstance(v, list):
            raise ValueError("strategy_execution_order must be a list")
        
        # Filter out empty strings and strip whitespace
        cleaned_order = [s.strip() for s in v if s and s.strip()]
        return cleaned_order
    
    @validator('strategy_success_by_type')
    def validate_strategy_success_by_type(cls, v):
        """Validate strategy success mapping."""
        if v is None:
            return {}
        
        if not isinstance(v, dict):
            raise ValueError("strategy_success_by_type must be a dictionary")
        
        # Ensure all values are booleans
        cleaned_success = {}
        for strategy, success in v.items():
            if strategy and strategy.strip():
                cleaned_success[strategy.strip()] = bool(success)
        
        return cleaned_success
    
    @validator('strategy_timing_by_type')
    def validate_strategy_timing_by_type(cls, v):
        """Validate strategy timing mapping."""
        if v is None:
            return {}
        
        if not isinstance(v, dict):
            raise ValueError("strategy_timing_by_type must be a dictionary")
        
        # Ensure all values are non-negative numbers
        cleaned_timing = {}
        for strategy, timing in v.items():
            if strategy and strategy.strip():
                try:
                    timing_value = float(timing)
                    if timing_value >= 0:
                        cleaned_timing[strategy.strip()] = timing_value
                except (ValueError, TypeError):
                    # Skip invalid timing values
                    continue
        
        return cleaned_timing
    
    @validator('strategy_switches_count')
    def validate_strategy_switches_count(cls, v):
        """Validate strategy switches count is non-negative."""
        if v is not None:
            if not isinstance(v, int):
                raise ValueError("strategy_switches_count must be an integer")
            if v < 0:
                raise ValueError("strategy_switches_count must be non-negative")
        return v or 0
    
    def get_all_strategies(self) -> List[str]:
        """
        Get all strategies used (primary + secondary).
        
        Returns:
            List of all strategy names
        """
        strategies = [self.primary_strategy]
        if self.secondary_strategies:
            strategies.extend(self.secondary_strategies)
        return list(set(strategies))  # Remove duplicates
    
    def get_successful_strategies(self) -> List[str]:
        """
        Get list of successful strategies.
        
        Returns:
            List of successful strategy names
        """
        if not self.strategy_success_by_type:
            return []
        
        return [
            strategy for strategy, success in self.strategy_success_by_type.items()
            if success
        ]
    
    def get_failed_strategies(self) -> List[str]:
        """
        Get list of failed strategies.
        
        Returns:
            List of failed strategy names
        """
        if not self.strategy_success_by_type:
            return []
        
        return [
            strategy for strategy, success in self.strategy_success_by_type.items()
            if not success
        ]
    
    def get_strategy_timing(self, strategy: str) -> Optional[float]:
        """
        Get timing for a specific strategy.
        
        Args:
            strategy: Strategy name
            
        Returns:
            Timing in milliseconds or None if not available
        """
        if not self.strategy_timing_by_type:
            return None
        
        return self.strategy_timing_by_type.get(strategy)
    
    def is_strategy_successful(self, strategy: str) -> Optional[bool]:
        """
        Check if a specific strategy was successful.
        
        Args:
            strategy: Strategy name
            
        Returns:
            True if successful, False if failed, None if unknown
        """
        if not self.strategy_success_by_type:
            return None
        
        return self.strategy_success_by_type.get(strategy)
    
    def get_total_strategy_time(self) -> float:
        """
        Get total time spent on all strategies.
        
        Returns:
            Total time in milliseconds
        """
        if not self.strategy_timing_by_type:
            return 0.0
        
        return sum(self.strategy_timing_by_type.values())
    
    def get_average_strategy_time(self) -> float:
        """
        Get average time per strategy.
        
        Returns:
            Average time in milliseconds
        """
        if not self.strategy_timing_by_type:
            return 0.0
        
        times = list(self.strategy_timing_by_type.values())
        return sum(times) / len(times) if times else 0.0
    
    def get_fastest_strategy(self) -> Optional[str]:
        """
        Get the fastest strategy.
        
        Returns:
            Fastest strategy name or None if no timing data
        """
        if not self.strategy_timing_by_type:
            return None
        
        return min(self.strategy_timing_by_type.items(), key=lambda x: x[1])[0]
    
    def get_slowest_strategy(self) -> Optional[str]:
        """
        Get the slowest strategy.
        
        Returns:
            Slowest strategy name or None if no timing data
        """
        if not self.strategy_timing_by_type:
            return None
        
        return max(self.strategy_timing_by_type.items(), key=lambda x: x[1])[0]
    
    def has_multiple_strategies(self) -> bool:
        """
        Check if multiple strategies were used.
        
        Returns:
            True if more than one strategy was used
        """
        return len(self.get_all_strategies()) > 1
    
    def used_secondary_strategies(self) -> bool:
        """
        Check if secondary strategies were used.
        
        Returns:
            True if secondary strategies were used
        """
        return bool(self.secondary_strategies)
    
    def has_strategy_failures(self) -> bool:
        """
        Check if any strategies failed.
        
        Returns:
            True if any strategies failed
        """
        return len(self.get_failed_strategies()) > 0
    
    def get_strategy_success_rate(self) -> float:
        """
        Calculate overall strategy success rate.
        
        Returns:
            Success rate as percentage (0.0-1.0)
        """
        if not self.strategy_success_by_type:
            return 1.0  # Assume success if no data
        
        total_strategies = len(self.strategy_success_by_type)
        successful_strategies = len(self.get_successful_strategies())
        
        return successful_strategies / total_strategies if total_strategies > 0 else 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary with all fields."""
        return {
            "primary_strategy": self.primary_strategy,
            "secondary_strategies": self.secondary_strategies or [],
            "strategy_execution_order": self.strategy_execution_order or [],
            "strategy_success_by_type": self.strategy_success_by_type or {},
            "strategy_timing_by_type": self.strategy_timing_by_type or {},
            "strategy_switches_count": self.strategy_switches_count or 0
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
