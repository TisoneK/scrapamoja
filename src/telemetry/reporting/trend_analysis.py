"""
Trend Analysis for Selector Telemetry System

This module provides advanced trend analysis capabilities including
trend detection, forecasting, seasonality analysis, and
pattern recognition in telemetry data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import statistics
import uuid
from collections import defaultdict, deque

from ..models.selector_models import (
    TelemetryEvent, TelemetryEventType, MetricType, SeverityLevel
)
from ..processor.metrics_processor import MetricsProcessor, ProcessedMetric
from ..processor.aggregator import Aggregator, AggregatedMetric
from ..report_generator import ReportGenerator, ReportType, ReportFormat, ReportSection


class TrendDirection(Enum):
    """Trend direction types"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class TrendStrength(Enum):
    """Trend strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SeasonalityType(Enum):
    """Types of seasonality"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class TrendData:
    """Trend analysis data"""
    metric_name: str
    time_series: List[Tuple[datetime, float]]
    trend_direction: TrendDirection
    trend_strength: TrendStrength
    trend_slope: float
    confidence: float
    seasonality: Optional[Dict[str, Any]] = None
    forecast: Optional[List[Tuple[datetime, float]]] = None


@dataclass
class SeasonalityData:
    """Seasonality analysis data"""
    seasonality_type: SeasonalityType
    strength: float
    pattern: Dict[str, Any]
    confidence: float
    detected_at: datetime


@dataclass
class TrendInsight:
    """Trend insight"""
    insight_id: str
    insight_type: str
    title: str
    description: str
    impact: str
    confidence: float
    recommendations: List[str]
    supporting_data: Dict[str, Any]


class TrendAnalysis:
    """
    Advanced trend analysis system
    
    This class provides comprehensive trend analysis capabilities:
    - Trend detection and classification
    - Trend strength measurement
    - Seasonality pattern detection
    - Forecasting and prediction
    - Anomaly detection in trends
    - Pattern recognition
    """
    
    def __init__(
        self,
        report_generator: ReportGenerator,
        metrics_processor: Optional[MetricsProcessor] = None,
        aggregator: Optional[Aggregator] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize trend analysis"""
        self.report_generator = report_generator
        self.metrics_processor = metrics_processor
        self.aggregator = aggregator
        
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Trend analysis statistics
        self._stats = {
            "trends_analyzed": 0,
            "forecasts_generated": 0,
            "seasonal_patterns_detected": 0,
            "anomalies_detected": 0,
            "insights_generated": 0
        }
        
        # Trend cache
        self._trend_cache = {}
        self._seasonality_cache = {}
    
    async def analyze_trends(
        self,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime],
        window_size: str = "1h",
        include_forecast: bool = True,
        forecast_periods: int = 24,
        include_seasonality: bool = True
    ) -> Dict[str, TrendData]:
        """
        Analyze trends for specified metrics
        
        Args:
            metric_names: List of metrics to analyze
            time_range: Time range for analysis
            window_size: Time window for data aggregation
            include_forecast: Whether to generate forecasts
            forecast_periods: Number of periods to forecast
            include_seasonality: Whether to include seasonality analysis
            
        Returns:
            Dict[str, TrendData]: Trend analysis results
        """
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting trend analysis {analysis_id} for {len(metric_names)} metrics")
            
            trend_results = {}
            
            for metric_name in metric_names:
                # Get time series data
                time_series = await self._get_time_series_data(
                    metric_name, time_range, window_size
                )
                
                if len(time_series) < 3:
                    continue
                
                # Analyze trend
                trend_data = await self._analyze_metric_trend(
                    metric_name, time_series, include_forecast, forecast_periods, include_seasonality
                )
                
                trend_results[metric_name] = trend_data
                
                # Cache results
                self._trend_cache[metric_name] = trend_data
            
            # Update statistics
            self._stats["trends_analyzed"] += len(trend_results)
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Completed trend analysis {analysis_id} in {analysis_time:.2f}s"
            )
            
            return trend_results
            
        except Exception as e:
            self.logger.error(f"Error in trend analysis {analysis_id}: {e}")
            raise
    
    async def detect_seasonality(
        self,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime],
        seasonality_types: Optional[List[SeasonalityType]] = None
    ) -> Dict[str, List[SeasonalityData]]:
        """
        Detect seasonality patterns in metrics
        
        Args:
            metric_names: List of metrics to analyze
            time_range: Time range for analysis
            seasonality_types: Types of seasonality to detect
            
        Returns:
            Dict[str, List[SeasonalityData]]: Seasonality analysis results
        """
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        if seasonality_types is None:
            seasonality_types = [SeasonalityType.DAILY, SeasonalityType.WEEKLY]
        
        try:
            self.logger.info(f"Starting seasonality detection {analysis_id}")
            
            seasonality_results = {}
            
            for metric_name in metric_names:
                # Get time series data
                time_series = await self._get_time_series_data(metric_name, time_range)
                
                if len(time_series) < 24:  # Need at least 24 data points for seasonality
                    continue
                
                # Detect seasonality patterns
                metric_seasonality = await self._detect_metric_seasonality(
                    metric_name, time_series, seasonality_types
                )
                
                if metric_seasonality:
                    seasonality_results[metric_name] = metric_seasonality
                    
                    # Cache results
                    self._seasonality_cache[metric_name] = metric_seasonality
            
            # Update statistics
            self._stats["seasonal_patterns_detected"] += sum(
                len(patterns) for patterns in seasonality_results.values()
            )
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Completed seasonality detection {analysis_id} in {analysis_time:.2f}s"
            )
            
            return seasonality_results
            
        except Exception as e:
            self.logger.error(f"Error in seasonality detection {analysis_id}: {e}")
            raise
    
    async def generate_forecasts(
        self,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime],
        forecast_periods: int = 48,
        confidence_level: float = 0.95,
        method: str = "linear"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate forecasts for specified metrics
        
        Args:
            metric_names: List of metrics to forecast
            time_range: Historical time range for training
            forecast_periods: Number of periods to forecast
            confidence_level: Confidence level for prediction intervals
            method: Forecasting method to use
            
        Returns:
            Dict[str, Dict[str, Any]]: Forecast results
        """
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting forecast generation {analysis_id}")
            
            forecast_results = {}
            
            for metric_name in metric_names:
                # Get historical data
                time_series = await self._get_time_series_data(metric_name, time_range)
                
                if len(time_series) < 10:
                    continue
                
                # Generate forecast
                forecast = await self._generate_metric_forecast(
                    metric_name, time_series, forecast_periods, confidence_level, method
                )
                
                forecast_results[metric_name] = forecast
            
            # Update statistics
            self._stats["forecasts_generated"] += len(forecast_results)
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Completed forecast generation {analysis_id} in {analysis_time:.2f}s"
            )
            
            return forecast_results
            
        except Exception as e:
            self.logger.error(f"Error in forecast generation {analysis_id}: {e}")
            raise
    
    async def detect_trend_anomalies(
        self,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime],
        sensitivity: float = 0.05,
        window_size: str = "1h"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect anomalies in trend patterns
        
        Args:
            metric_names: List of metrics to analyze
            time_range: Time range for analysis
            sensitivity: Sensitivity threshold for anomaly detection
            window_size: Time window for data aggregation
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Anomaly detection results
        """
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting trend anomaly detection {analysis_id}")
            
            anomaly_results = {}
            
            for metric_name in metric_names:
                # Get time series data
                time_series = await self._get_time_series_data(metric_name, time_range, window_size)
                
                if len(time_series) < 10:
                    continue
                
                # Detect anomalies
                anomalies = await self._detect_metric_anomalies(metric_name, time_series, sensitivity)
                
                if anomalies:
                    anomaly_results[metric_name] = anomalies
            
            # Update statistics
            self._stats["anomalies_detected"] += sum(
                len(anomalies) for anomalies in anomaly_results.values()
            )
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Completed trend anomaly detection {analysis_id} in {analysis_time:.2f}s"
            )
            
            return anomaly_results
            
        except Exception as e:
            self.logger.error(f"Error in trend anomaly detection {analysis_id}: {e}")
            raise
    
    async def get_trend_insights(
        self,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime],
        insight_types: Optional[List[str]] = None,
        min_confidence: float = 0.7
    ) -> List[TrendInsight]:
        """
        Get trend insights
        
        Args:
            metric_names: List of metrics to analyze
            time_range: Time range for analysis
            insight_types: Types of insights to generate
            min_confidence: Minimum confidence threshold
            
        Returns:
            List[TrendInsight]: Trend insights
        """
        try:
            # Analyze trends first
            trend_data = await self.analyze_trends(metric_names, time_range)
            
            # Generate insights
            insights = await self._generate_trend_insights(
                trend_data, insight_types, min_confidence
            )
            
            # Update statistics
            self._stats["insights_generated"] += len(insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating trend insights: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get trend analysis statistics"""
        return self._stats.copy()
    
    # Private helper methods
    
    async def _get_time_series_data(
        self,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        window_size: str = "1h"
    ) -> List[Tuple[datetime, float]]:
        """Get time series data for a metric"""
        # This would integrate with metrics processor and aggregator
        # For now, generate sample data
        time_series = []
        current_time = time_range[0]
        
        # Determine step size based on window_size
        if window_size == "1h":
            step = timedelta(hours=1)
        elif window_size == "1d":
            step = timedelta(days=1)
        else:
            step = timedelta(hours=1)
        
        while current_time <= time_range[1]:
            # Generate sample value with some trend and noise
            base_value = 100
            trend_factor = (current_time - time_range[0]).total_seconds() / 3600 * 0.1
            noise = statistics.normalvariate(0, 10)
            value = base_value + trend_factor + noise
            
            time_series.append((current_time, value))
            current_time += step
        
        return time_series
    
    async def _analyze_metric_trend(
        self,
        metric_name: str,
        time_series: List[Tuple[datetime, float]],
        include_forecast: bool,
        forecast_periods: int,
        include_seasonality: bool
    ) -> TrendData:
        """Analyze trend for a specific metric"""
        values = [value for _, value in time_series]
        
        # Calculate trend using linear regression
        if len(values) >= 3:
            x = list(range(len(values)))
            # Simple linear regression
            n = len(values)
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            # Calculate slope and intercept
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
            
            # Calculate R-squared for confidence
            y_mean = sum_y / n
            ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
            ss_res = sum((values[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Determine trend direction
            if abs(slope) < 0.01:
                trend_direction = TrendDirection.STABLE
            elif slope > 0:
                trend_direction = TrendDirection.INCREASING
            else:
                trend_direction = TrendDirection.DECREASING
            
            # Determine trend strength
            strength_value = abs(r_squared)
            if strength_value < 0.3:
                trend_strength = TrendStrength.WEAK
            elif strength_value < 0.6:
                trend_strength = TrendStrength.MODERATE
            elif strength_value < 0.8:
                trend_strength = TrendStrength.STRONG
            else:
                trend_strength = TrendStrength.VERY_STRONG
            
        else:
            slope = 0
            intercept = values[0] if values else 0
            r_squared = 0
            trend_direction = TrendDirection.STABLE
            trend_strength = TrendStrength.WEAK
        
        # Generate forecast if requested
        forecast = None
        if include_forecast and len(values) >= 10:
            forecast = await self._generate_simple_forecast(time_series, forecast_periods, slope, intercept)
        
        # Detect seasonality if requested
        seasonality = None
        if include_seasonality and len(time_series) >= 24:
            seasonality = await self._detect_simple_seasonality(time_series)
        
        return TrendData(
            metric_name=metric_name,
            time_series=time_series,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            trend_slope=slope,
            confidence=r_squared,
            seasonality=seasonality,
            forecast=forecast
        )
    
    async def _generate_simple_forecast(
        self,
        time_series: List[Tuple[datetime, float]],
        periods: int,
        slope: float,
        intercept: float
    ) -> List[Tuple[datetime, float]]:
        """Generate simple linear forecast"""
        if len(time_series) < 2:
            return []
        
        forecast = []
        last_timestamp = time_series[-1][0]
        last_x = len(time_series) - 1
        
        # Determine time step
        if len(time_series) >= 2:
            time_step = time_series[1][0] - time_series[0][0]
        else:
            time_step = timedelta(hours=1)
        
        for i in range(periods):
            future_x = last_x + i + 1
            forecast_value = slope * future_x + intercept
            forecast_timestamp = last_timestamp + time_step * (i + 1)
            forecast.append((forecast_timestamp, forecast_value))
        
        return forecast
    
    async def _detect_simple_seasonality(self, time_series: List[Tuple[datetime, float]]) -> Optional[Dict[str, Any]]:
        """Detect simple seasonality patterns"""
        if len(time_series) < 24:
            return None
        
        values = [value for _, value in time_series]
        
        # Check for daily patterns (24-hour cycle)
        if len(values) >= 24:
            daily_pattern = self._check_daily_pattern(time_series)
            if daily_pattern["strength"] > 0.3:
                return {
                    "type": "daily",
                    "strength": daily_pattern["strength"],
                    "peak_hours": daily_pattern["peak_hours"],
                    "low_hours": daily_pattern["low_hours"]
                }
        
        return None
    
    def _check_daily_pattern(self, time_series: List[Tuple[datetime, float]]) -> Dict[str, Any]:
        """Check for daily patterns in time series"""
        hourly_values = defaultdict(list)
        
        for timestamp, value in time_series:
            hour = timestamp.hour
            hourly_values[hour].append(value)
        
        # Calculate hourly averages
        hourly_avg = {hour: statistics.mean(values) for hour, values in hourly_values.items()}
        
        # Calculate overall average
        all_values = [value for _, value in time_series]
        overall_avg = statistics.mean(all_values)
        
        # Find peak and low hours
        peak_hours = [hour for hour, avg in hourly_avg.items() if avg > overall_avg * 1.1]
        low_hours = [hour for hour, avg in hourly_avg.items() if avg < overall_avg * 0.9]
        
        # Calculate pattern strength
        if len(hourly_avg) > 0:
            max_deviation = max(abs(avg - overall_avg) for avg in hourly_avg.values())
            strength = max_deviation / overall_avg if overall_avg != 0 else 0
        else:
            strength = 0
        
        return {
            "strength": strength,
            "peak_hours": peak_hours,
            "low_hours": low_hours
        }
    
    async def _detect_metric_seasonality(
        self,
        metric_name: str,
        time_series: List[Tuple[datetime, float]],
        seasonality_types: List[SeasonalityType]
    ) -> List[SeasonalityData]:
        """Detect seasonality for a specific metric"""
        seasonality_patterns = []
        
        for seasonality_type in seasonality_types:
            if seasonality_type == SeasonalityType.DAILY and len(time_series) >= 24:
                pattern = await self._detect_daily_seasonality(time_series)
                if pattern:
                    seasonality_patterns.append(pattern)
            elif seasonality_type == SeasonalityType.WEEKLY and len(time_series) >= 168:  # 7*24
                pattern = await self._detect_weekly_seasonality(time_series)
                if pattern:
                    seasonality_patterns.append(pattern)
        
        return seasonality_patterns
    
    async def _detect_daily_seasonality(self, time_series: List[Tuple[datetime, float]]) -> Optional[SeasonalityData]:
        """Detect daily seasonality"""
        pattern_data = self._check_daily_pattern(time_series)
        
        if pattern_data["strength"] > 0.3:
            return SeasonalityData(
                seasonality_type=SeasonalityType.DAILY,
                strength=pattern_data["strength"],
                pattern={
                    "peak_hours": pattern_data["peak_hours"],
                    "low_hours": pattern_data["low_hours"]
                },
                confidence=pattern_data["strength"],
                detected_at=datetime.now()
            )
        
        return None
    
    async def _detect_weekly_seasonality(self, time_series: List[Tuple[datetime, float]]) -> Optional[SeasonalityData]:
        """Detect weekly seasonality"""
        # Group by day of week
        daily_values = defaultdict(list)
        
        for timestamp, value in time_series:
            day_of_week = timestamp.weekday()
            daily_values[day_of_week].append(value)
        
        # Calculate daily averages
        daily_avg = {day: statistics.mean(values) for day, values in daily_values.items()}
        
        # Calculate overall average
        all_values = [value for _, value in time_series]
        overall_avg = statistics.mean(all_values)
        
        # Calculate pattern strength
        if len(daily_avg) > 0:
            max_deviation = max(abs(avg - overall_avg) for avg in daily_avg.values())
            strength = max_deviation / overall_avg if overall_avg != 0 else 0
        else:
            strength = 0
        
        if strength > 0.2:
            peak_days = [day for day, avg in daily_avg.items() if avg > overall_avg * 1.1]
            low_days = [day for day, avg in daily_avg.items() if avg < overall_avg * 0.9]
            
            return SeasonalityData(
                seasonality_type=SeasonalityType.WEEKLY,
                strength=strength,
                pattern={
                    "peak_days": peak_days,
                    "low_days": low_days
                },
                confidence=strength,
                detected_at=datetime.now()
            )
        
        return None
    
    async def _generate_metric_forecast(
        self,
        metric_name: str,
        time_series: List[Tuple[datetime, float]],
        forecast_periods: int,
        confidence_level: float,
        method: str
    ) -> Dict[str, Any]:
        """Generate forecast for a specific metric"""
        values = [value for _, value in time_series]
        
        if method == "linear":
            # Use linear regression
            trend_data = await self._analyze_metric_trend(metric_name, time_series, True, forecast_periods, False)
            forecast_values = trend_data.forecast or []
            
            # Calculate prediction intervals
            residuals = [values[i] - (trend_data.trend_slope * i + trend_data.time_series[0][1]) for i in range(len(values))]
            std_error = statistics.stdev(residuals) if len(residuals) > 1 else 0
            
            # Simple confidence intervals
            z_score = 1.96 if confidence_level == 0.95 else 1.645  # 90% confidence
            margin_of_error = z_score * std_error
            
            forecast_with_intervals = []
            for timestamp, value in forecast_values:
                forecast_with_intervals.append({
                    "timestamp": timestamp,
                    "value": value,
                    "lower_bound": value - margin_of_error,
                    "upper_bound": value + margin_of_error
                })
            
            return {
                "method": method,
                "forecast": forecast_with_intervals,
                "confidence_level": confidence_level,
                "trend_slope": trend_data.trend_slope,
                "r_squared": trend_data.confidence
            }
        
        return {"method": method, "forecast": [], "confidence_level": confidence_level}
    
    async def _detect_metric_anomalies(
        self,
        metric_name: str,
        time_series: List[Tuple[datetime, float]],
        sensitivity: float
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in metric time series"""
        anomalies = []
        values = [value for _, value in time_series]
        
        if len(values) < 10:
            return anomalies
        
        # Calculate moving average and standard deviation
        window_size = min(10, len(values) // 2)
        moving_avg = []
        moving_std = []
        
        for i in range(window_size, len(values)):
            window = values[i-window_size:i]
            moving_avg.append(statistics.mean(window))
            moving_std.append(statistics.stdev(window) if len(window) > 1 else 0)
        
        # Detect anomalies using z-score
        for i in range(window_size, len(values)):
            if i - window_size < len(moving_avg):
                avg = moving_avg[i - window_size]
                std = moving_std[i - window_size]
                
                if std > 0:
                    z_score = abs(values[i] - avg) / std
                    
                    # Use sensitivity threshold (convert to z-score threshold)
                    z_threshold = 2.5 if sensitivity < 0.05 else 2.0 if sensitivity < 0.1 else 1.5
                    
                    if z_score > z_threshold:
                        anomalies.append({
                            "timestamp": time_series[i][0],
                            "value": values[i],
                            "expected_value": avg,
                            "z_score": z_score,
                            "severity": "high" if z_score > 3 else "medium",
                            "anomaly_type": "statistical"
                        })
        
        return anomalies
    
    async def _generate_trend_insights(
        self,
        trend_data: Dict[str, TrendData],
        insight_types: Optional[List[str]],
        min_confidence: float
    ) -> List[TrendInsight]:
        """Generate insights from trend analysis"""
        insights = []
        
        for metric_name, trend in trend_data.items():
            if trend.confidence < min_confidence:
                continue
            
            # Generate trend direction insight
            if trend.trend_direction in [TrendDirection.INCREASING, TrendDirection.DECREASING]:
                if trend.trend_strength in [TrendStrength.STRONG, TrendStrength.VERY_STRONG]:
                    insights.append(TrendInsight(
                        insight_id=str(uuid.uuid4()),
                        insight_type="trend_direction",
                        title=f"Strong {trend.trend_direction.value} trend in {metric_name}",
                        description=f"{metric_name} shows a {trend.trend_strength.value} {trend.trend_direction.value} trend",
                        impact="high" if trend.trend_strength == TrendStrength.VERY_STRONG else "medium",
                        confidence=trend.confidence,
                        recommendations=[
                            f"Monitor {metric_name} closely",
                            "Investigate drivers of this trend"
                        ],
                        supporting_data={
                            "trend_direction": trend.trend_direction.value,
                            "trend_strength": trend.trend_strength.value,
                            "slope": trend.trend_slope
                        }
                    ))
            
            # Generate seasonality insight
            if trend.seasonality and trend.seasonality.get("strength", 0) > 0.5:
                insights.append(TrendInsight(
                    insight_id=str(uuid.uuid4()),
                    insight_type="seasonality",
                    title=f"Seasonal pattern detected in {metric_name}",
                    description=f"{metric_name} exhibits {trend.seasonality['type']} seasonality",
                    impact="medium",
                    confidence=trend.seasonality["strength"],
                    recommendations=[
                        "Consider seasonal adjustments in planning",
                        "Optimize resource allocation based on patterns"
                    ],
                    supporting_data=trend.seasonality
                ))
        
        return insights
