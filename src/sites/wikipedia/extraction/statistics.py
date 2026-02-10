"""
Extraction statistics tracking for Wikipedia articles.

This module provides comprehensive statistics tracking for extraction operations,
including performance metrics, success rates, and quality assessments.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from .models import ExtractionPerformance, ExtractionStatistics


@dataclass
class ExtractionEvent:
    """Single extraction event record."""
    
    timestamp: datetime
    extraction_type: str
    success: bool
    extraction_time_ms: float
    validation_time_ms: float
    total_time_ms: float
    data_size_bytes: int
    quality_score: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExtractionStatisticsTracker:
    """Comprehensive extraction statistics tracker."""
    
    def __init__(self):
        """Initialize statistics tracker."""
        self.events: List[ExtractionEvent] = []
        self.statistics = ExtractionStatistics()
        self.performance_history: List[ExtractionPerformance] = []
        self.type_specific_stats: Dict[str, Dict[str, Any]] = {}
    
    def record_extraction(self, event: ExtractionEvent) -> None:
        """Record an extraction event."""
        self.events.append(event)
        
        # Update overall statistics
        self.statistics.update_statistics(
            success=event.success,
            extraction_time_ms=event.extraction_time_ms,
            extraction_type=event.extraction_type
        )
        
        # Update type-specific statistics
        self._update_type_specific_stats(event)
        
        # Record performance metrics
        performance = ExtractionPerformance(
            extraction_time_ms=event.extraction_time_ms,
            validation_time_ms=event.validation_time_ms,
            caching_time_ms=0,  # Will be calculated separately
            total_time_ms=event.total_time_ms,
            memory_usage_mb=event.data_size_bytes / (1024 * 1024),
            cache_hit_rate=0,  # Will be calculated separately
            success_rate=1.0 if event.success else 0.0
        )
        self.performance_history.append(performance)
        
        # Keep only recent performance history (last 1000 events)
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def record_search_extraction(self, 
                                success: bool, 
                                extraction_time_ms: float, 
                                validation_time_ms: float,
                                result_count: int,
                                quality_score: float,
                                error_message: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record search-specific extraction event."""
        total_time_ms = extraction_time_ms + validation_time_ms
        
        event = ExtractionEvent(
            timestamp=datetime.utcnow(),
            extraction_type="search",
            success=success,
            extraction_time_ms=extraction_time_ms,
            validation_time_ms=validation_time_ms,
            total_time_ms=total_time_ms,
            data_size_bytes=result_count * 1000,  # Estimate 1KB per result
            quality_score=quality_score,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        self.record_extraction(event)
    
    def get_search_extraction_stats(self) -> Dict[str, Any]:
        """Get search-specific extraction statistics."""
        search_events = [event for event in self.events if event.extraction_type == "search"]
        
        if not search_events:
            return {
                'total_extractions': 0,
                'successful_extractions': 0,
                'failed_extractions': 0,
                'success_rate_percent': 0,
                'average_extraction_time_ms': 0,
                'average_validation_time_ms': 0,
                'average_quality_score': 0,
                'average_result_count': 0,
                'total_results_processed': 0
            }
        
        successful_events = [event for event in search_events if event.success]
        
        # Calculate statistics
        total_extractions = len(search_events)
        successful_extractions = len(successful_events)
        failed_extractions = total_extractions - successful_extractions
        success_rate = (successful_extractions / total_extractions) * 100
        
        avg_extraction_time = sum(event.extraction_time_ms for event in search_events) / total_extractions
        avg_validation_time = sum(event.validation_time_ms for event in search_events) / total_extractions
        
        quality_scores = [event.quality_score for event in successful_events if event.quality_score > 0]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Calculate result count statistics
        result_counts = []
        for event in successful_events:
            result_count = event.metadata.get('result_count', 0)
            result_counts.append(result_count)
        
        avg_result_count = sum(result_counts) / len(result_counts) if result_counts else 0
        total_results_processed = sum(result_counts)
        
        # Get recent performance trend
        recent_events = search_events[-10:] if len(search_events) >= 10 else search_events
        performance_trend = self._calculate_performance_trend_for_events(recent_events)
        
        # Calculate quality distribution
        quality_distribution = self._calculate_search_quality_distribution(successful_events)
        
        return {
            'total_extractions': total_extractions,
            'successful_extractions': successful_extractions,
            'failed_extractions': failed_extractions,
            'success_rate_percent': round(success_rate, 2),
            'average_extraction_time_ms': round(avg_extraction_time, 2),
            'average_validation_time_ms': round(avg_validation_time, 2),
            'average_quality_score': round(avg_quality_score, 3),
            'average_result_count': round(avg_result_count, 1),
            'total_results_processed': total_results_processed,
            'performance_trend': performance_trend,
            'quality_distribution': quality_distribution,
            'recent_errors': [event.error_message for event in recent_events if not event.success and event.error_message]
        }
    
    def get_search_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed search performance metrics."""
        search_events = [event for event in self.events if event.extraction_type == "search"]
        
        if not search_events:
            return {
                'throughput_metrics': {},
                'latency_metrics': {},
                'quality_metrics': {},
                'error_analysis': {}
            }
        
        # Throughput metrics
        successful_events = [event for event in search_events if event.success]
        result_counts = [event.metadata.get('result_count', 0) for event in successful_events]
        
        throughput_metrics = {
            'total_results_processed': sum(result_counts),
            'average_results_per_extraction': sum(result_counts) / len(result_counts) if result_counts else 0,
            'results_per_second': self._calculate_results_per_second(successful_events),
            'peak_results_per_extraction': max(result_counts) if result_counts else 0,
            'min_results_per_extraction': min(result_counts) if result_counts else 0
        }
        
        # Latency metrics
        extraction_times = [event.extraction_time_ms for event in search_events]
        validation_times = [event.validation_time_ms for event in search_events]
        total_times = [event.total_time_ms for event in search_events]
        
        latency_metrics = {
            'average_extraction_time_ms': sum(extraction_times) / len(extraction_times),
            'median_extraction_time_ms': self._calculate_median(extraction_times),
            'p95_extraction_time_ms': self._calculate_percentile(extraction_times, 95),
            'p99_extraction_time_ms': self._calculate_percentile(extraction_times, 99),
            'average_validation_time_ms': sum(validation_times) / len(validation_times),
            'average_total_time_ms': sum(total_times) / len(total_times),
            'extraction_time_variance': self._calculate_variance(extraction_times)
        }
        
        # Quality metrics
        quality_scores = [event.quality_score for event in successful_events if event.quality_score > 0]
        quality_metrics = {
            'average_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'median_quality_score': self._calculate_median(quality_scores),
            'quality_score_variance': self._calculate_variance(quality_scores),
            'high_quality_percentage': len([q for q in quality_scores if q > 0.8]) / len(quality_scores) * 100 if quality_scores else 0,
            'low_quality_percentage': len([q for q in quality_scores if q < 0.5]) / len(quality_scores) * 100 if quality_scores else 0
        }
        
        # Error analysis
        failed_events = [event for event in search_events if not event.success]
        error_types = {}
        for event in failed_events:
            error_type = type(event.error_message).__name__ if event.error_message else "Unknown"
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        error_analysis = {
            'total_errors': len(failed_events),
            'error_rate_percent': (len(failed_events) / len(search_events)) * 100,
            'error_types': error_types,
            'most_common_error': max(error_types.items(), key=lambda x: x[1])[0] if error_types else None,
            'recent_errors': [event.error_message for event in failed_events[-5:]]
        }
        
        return {
            'throughput_metrics': throughput_metrics,
            'latency_metrics': latency_metrics,
            'quality_metrics': quality_metrics,
            'error_analysis': error_analysis,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_search_quality_distribution(self, events: List[ExtractionEvent]) -> Dict[str, int]:
        """Calculate quality score distribution for search results."""
        distribution = {
            'excellent': 0,    # 0.9 - 1.0
            'good': 0,         # 0.7 - 0.9
            'fair': 0,         # 0.5 - 0.7
            'poor': 0          # 0.0 - 0.5
        }
        
        quality_scores = [event.quality_score for event in events if event.quality_score > 0]
        
        for score in quality_scores:
            if score >= 0.9:
                distribution['excellent'] += 1
            elif score >= 0.7:
                distribution['good'] += 1
            elif score >= 0.5:
                distribution['fair'] += 1
            else:
                distribution['poor'] += 1
        
        return distribution
    
    def _calculate_results_per_second(self, events: List[ExtractionEvent]) -> float:
        """Calculate results processed per second."""
        if not events:
            return 0.0
        
        total_results = sum(event.metadata.get('result_count', 0) for event in events)
        total_time_seconds = sum(event.total_time_ms for event in events) / 1000
        
        return total_results / total_time_seconds if total_time_seconds > 0 else 0.0
    
    def _calculate_median(self, values: List[float]) -> float:
        """Calculate median value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance
    
    def get_article_extraction_stats(self) -> Dict[str, Any]:
        """Get article-specific extraction statistics."""
        article_events = [event for event in self.events if event.extraction_type == "article"]
        
        if not article_events:
            return {
                'total_extractions': 0,
                'successful_extractions': 0,
                'failed_extractions': 0,
                'success_rate_percent': 0,
                'average_extraction_time_ms': 0,
                'average_validation_time_ms': 0,
                'average_quality_score': 0,
                'average_data_size_kb': 0
            }
        
        successful_events = [event for event in article_events if event.success]
        
        # Calculate statistics
        total_extractions = len(article_events)
        successful_extractions = len(successful_events)
        failed_extractions = total_extractions - successful_extractions
        success_rate = (successful_extractions / total_extractions) * 100
        
        avg_extraction_time = sum(event.extraction_time_ms for event in article_events) / total_extractions
        avg_validation_time = sum(event.validation_time_ms for event in article_events) / total_extractions
        
        quality_scores = [event.quality_score for event in successful_events if event.quality_score > 0]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        avg_data_size_kb = sum(event.data_size_bytes for event in article_events) / total_extractions / 1024
        
        # Get recent performance trend
        recent_events = article_events[-10:] if len(article_events) >= 10 else article_events
        performance_trend = self._calculate_performance_trend_for_events(recent_events)
        
        return {
            'total_extractions': total_extractions,
            'successful_extractions': successful_extractions,
            'failed_extractions': failed_extractions,
            'success_rate_percent': round(success_rate, 2),
            'average_extraction_time_ms': round(avg_extraction_time, 2),
            'average_validation_time_ms': round(avg_validation_time, 2),
            'average_quality_score': round(avg_quality_score, 3),
            'average_data_size_kb': round(avg_data_size_kb, 2),
            'performance_trend': performance_trend,
            'recent_errors': [event.error_message for event in recent_events if not event.success and event.error_message]
        }
    
    def get_extraction_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive extraction performance summary."""
        if not self.events:
            return {
                'overall': {},
                'by_type': {},
                'performance_metrics': {},
                'quality_metrics': {},
                'error_analysis': {}
            }
        
        # Overall statistics
        overall_stats = self.get_overall_statistics()
        
        # Type-specific statistics
        type_stats = {}
        for extraction_type in ['article', 'search', 'infobox', 'toc', 'links']:
            type_stats[extraction_type] = self.get_type_specific_statistics(extraction_type)
        
        # Performance metrics
        performance_stats = self.get_performance_statistics()
        
        # Quality metrics
        quality_stats = self.get_quality_statistics()
        
        # Error analysis
        error_stats = self.get_error_statistics()
        
        return {
            'overall': overall_stats,
            'by_type': type_stats,
            'performance_metrics': performance_stats,
            'quality_metrics': quality_stats,
            'error_analysis': error_stats,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_performance_trend_for_events(self, events: List[ExtractionEvent]) -> str:
        """Calculate performance trend for specific events."""
        if len(events) < 5:
            return 'insufficient_data'
        
        # Compare recent performance with older performance
        recent_events = events[-3:]
        older_events = events[-6:-3] if len(events) >= 6 else events[:-3]
        
        if not older_events:
            return 'insufficient_data'
        
        recent_avg = sum(event.extraction_time_ms for event in recent_events) / len(recent_events)
        older_avg = sum(event.extraction_time_ms for event in older_events) / len(older_events)
        
        if recent_avg < older_avg * 0.9:
            return 'improving'
        elif recent_avg > older_avg * 1.1:
            return 'degrading'
        else:
            return 'stable'
    
    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall extraction statistics."""
        return {
            'total_extractions': self.statistics.total_extractions,
            'successful_extractions': self.statistics.successful_extractions,
            'failed_extractions': self.statistics.failed_extractions,
            'success_rate_percent': self.statistics.get_success_rate(),
            'average_extraction_time_ms': self.statistics.average_extraction_time_ms,
            'cache_hit_rate_percent': self.statistics.cache_hit_rate,
            'type_breakdown': {
                'article_extractions': self.statistics.article_extractions,
                'search_extractions': self.statistics.search_extractions,
                'infobox_extractions': self.statistics.infobox_extractions,
                'toc_extractions': self.statistics.toc_extractions,
                'link_extractions': self.statistics.link_extractions
            }
        }
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.performance_history:
            return {
                'average_extraction_time_ms': 0,
                'average_validation_time_ms': 0,
                'average_total_time_ms': 0,
                'average_memory_usage_mb': 0,
                'performance_trend': 'stable'
            }
        
        # Calculate averages
        avg_extraction = sum(p.extraction_time_ms for p in self.performance_history) / len(self.performance_history)
        avg_validation = sum(p.validation_time_ms for p in self.performance_history) / len(self.performance_history)
        avg_total = sum(p.total_time_ms for p in self.performance_history) / len(self.performance_history)
        avg_memory = sum(p.memory_usage_mb for p in self.performance_history) / len(self.performance_history)
        
        # Calculate performance trend
        trend = self._calculate_performance_trend()
        
        return {
            'average_extraction_time_ms': round(avg_extraction, 2),
            'average_validation_time_ms': round(avg_validation, 2),
            'average_total_time_ms': round(avg_total, 2),
            'average_memory_usage_mb': round(avg_memory, 2),
            'performance_trend': trend,
            'recent_performance': self._get_recent_performance_stats()
        }
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get quality statistics."""
        if not self.events:
            return {
                'average_quality_score': 0,
                'quality_trend': 'stable',
                'quality_distribution': {}
            }
        
        # Calculate quality statistics
        quality_scores = [event.quality_score for event in self.events if event.quality_score > 0]
        
        if not quality_scores:
            return {
                'average_quality_score': 0,
                'quality_trend': 'stable',
                'quality_distribution': {}
            }
        
        avg_quality = sum(quality_scores) / len(quality_scores)
        quality_trend = self._calculate_quality_trend()
        quality_distribution = self._calculate_quality_distribution(quality_scores)
        
        return {
            'average_quality_score': round(avg_quality, 3),
            'quality_trend': quality_trend,
            'quality_distribution': quality_distribution,
            'total_quality_assessments': len(quality_scores)
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        failed_events = [event for event in self.events if not event.success]
        
        if not failed_events:
            return {
                'total_errors': 0,
                'error_rate_percent': 0,
                'common_errors': [],
                'error_trend': 'stable'
            }
        
        # Calculate error statistics
        error_rate = (len(failed_events) / len(self.events)) * 100
        common_errors = self._get_common_errors(failed_events)
        error_trend = self._calculate_error_trend()
        
        return {
            'total_errors': len(failed_events),
            'error_rate_percent': round(error_rate, 2),
            'common_errors': common_errors,
            'error_trend': error_trend,
            'recent_errors': self._get_recent_errors(failed_events)
        }
    
    def get_type_specific_statistics(self, extraction_type: str) -> Dict[str, Any]:
        """Get statistics for specific extraction type."""
        type_events = [event for event in self.events if event.extraction_type == extraction_type]
        
        if not type_events:
            return {
                'total_extractions': 0,
                'success_rate_percent': 0,
                'average_time_ms': 0,
                'average_quality_score': 0
            }
        
        successful_events = [event for event in type_events if event.success]
        success_rate = (len(successful_events) / len(type_events)) * 100
        
        avg_time = sum(event.extraction_time_ms for event in type_events) / len(type_events)
        quality_scores = [event.quality_score for event in successful_events if event.quality_score > 0]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'total_extractions': len(type_events),
            'successful_extractions': len(successful_events),
            'success_rate_percent': round(success_rate, 2),
            'average_time_ms': round(avg_time, 2),
            'average_quality_score': round(avg_quality, 3),
            'error_count': len(type_events) - len(successful_events)
        }
    
    def get_time_series_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get time series statistics for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [event for event in self.events if event.timestamp >= cutoff_time]
        
        if not recent_events:
            return {
                'period_hours': hours,
                'total_extractions': 0,
                'hourly_breakdown': {},
                'peak_hour': None
            }
        
        # Group events by hour
        hourly_data = {}
        for event in recent_events:
            hour_key = event.timestamp.strftime('%Y-%m-%d %H:00')
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'avg_time_ms': 0,
                    'total_time_ms': 0
                }
            
            hourly_data[hour_key]['total'] += 1
            hourly_data[hour_key]['total_time_ms'] += event.extraction_time_ms
            
            if event.success:
                hourly_data[hour_key]['successful'] += 1
            else:
                hourly_data[hour_key]['failed'] += 1
        
        # Calculate averages and find peak hour
        peak_hour = None
        max_extractions = 0
        
        for hour, data in hourly_data.items():
            if data['total'] > 0:
                data['avg_time_ms'] = data['total_time_ms'] / data['total']
                data['success_rate_percent'] = (data['successful'] / data['total']) * 100
            
            if data['total'] > max_extractions:
                max_extractions = data['total']
                peak_hour = hour
        
        return {
            'period_hours': hours,
            'total_extractions': len(recent_events),
            'hourly_breakdown': hourly_data,
            'peak_hour': peak_hour
        }
    
    def export_statistics(self, format: str = 'json') -> str:
        """Export statistics in specified format."""
        data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'overall_statistics': self.get_overall_statistics(),
            'performance_statistics': self.get_performance_statistics(),
            'quality_statistics': self.get_quality_statistics(),
            'error_statistics': self.get_error_statistics(),
            'type_specific_statistics': {
                'article': self.get_type_specific_statistics('article'),
                'search': self.get_type_specific_statistics('search'),
                'infobox': self.get_type_specific_statistics('infobox'),
                'toc': self.get_type_specific_statistics('toc'),
                'links': self.get_type_specific_statistics('links')
            }
        }
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.events.clear()
        self.statistics = ExtractionStatistics()
        self.performance_history.clear()
        self.type_specific_stats.clear()
    
    def _update_type_specific_stats(self, event: ExtractionEvent) -> None:
        """Update type-specific statistics."""
        if event.extraction_type not in self.type_specific_stats:
            self.type_specific_stats[event.extraction_type] = {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'total_time_ms': 0,
                'quality_scores': []
            }
        
        stats = self.type_specific_stats[event.extraction_type]
        stats['total'] += 1
        stats['total_time_ms'] += event.extraction_time_ms
        
        if event.success:
            stats['successful'] += 1
            if event.quality_score > 0:
                stats['quality_scores'].append(event.quality_score)
        else:
            stats['failed'] += 1
    
    def _calculate_performance_trend(self) -> str:
        """Calculate performance trend."""
        if len(self.performance_history) < 10:
            return 'insufficient_data'
        
        # Compare recent performance with older performance
        recent = self.performance_history[-5:]
        older = self.performance_history[-10:-5]
        
        recent_avg = sum(p.extraction_time_ms for p in recent) / len(recent)
        older_avg = sum(p.extraction_time_ms for p in older) / len(older)
        
        if recent_avg < older_avg * 0.9:
            return 'improving'
        elif recent_avg > older_avg * 1.1:
            return 'degrading'
        else:
            return 'stable'
    
    def _calculate_quality_trend(self) -> str:
        """Calculate quality trend."""
        quality_events = [event for event in self.events if event.quality_score > 0]
        
        if len(quality_events) < 10:
            return 'insufficient_data'
        
        # Compare recent quality with older quality
        recent = quality_events[-5:]
        older = quality_events[-10:-5]
        
        recent_avg = sum(event.quality_score for event in recent) / len(recent)
        older_avg = sum(event.quality_score for event in older) / len(older)
        
        if recent_avg > older_avg * 1.05:
            return 'improving'
        elif recent_avg < older_avg * 0.95:
            return 'degrading'
        else:
            return 'stable'
    
    def _calculate_error_trend(self) -> str:
        """Calculate error trend."""
        if len(self.events) < 20:
            return 'insufficient_data'
        
        # Compare recent error rate with older error rate
        recent_events = self.events[-10:]
        older_events = self.events[-20:-10]
        
        recent_errors = sum(1 for event in recent_events if not event.success)
        older_errors = sum(1 for event in older_events if not event.success)
        
        recent_rate = recent_errors / len(recent_events)
        older_rate = older_errors / len(older_events)
        
        if recent_rate < older_rate * 0.8:
            return 'improving'
        elif recent_rate > older_rate * 1.2:
            return 'degrading'
        else:
            return 'stable'
    
    def _calculate_quality_distribution(self, quality_scores: List[float]) -> Dict[str, int]:
        """Calculate quality score distribution."""
        distribution = {
            'excellent': 0,    # 0.9 - 1.0
            'good': 0,         # 0.7 - 0.9
            'fair': 0,         # 0.5 - 0.7
            'poor': 0          # 0.0 - 0.5
        }
        
        for score in quality_scores:
            if score >= 0.9:
                distribution['excellent'] += 1
            elif score >= 0.7:
                distribution['good'] += 1
            elif score >= 0.5:
                distribution['fair'] += 1
            else:
                distribution['poor'] += 1
        
        return distribution
    
    def _get_common_errors(self, failed_events: List[ExtractionEvent]) -> List[Dict[str, Any]]:
        """Get most common errors."""
        error_counts = {}
        for event in failed_events:
            error_msg = event.error_message or 'Unknown error'
            error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
        
        # Sort by frequency and return top 5
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'error': error, 'count': count} for error, count in sorted_errors[:5]]
    
    def _get_recent_errors(self, failed_events: List[ExtractionEvent]) -> List[Dict[str, Any]]:
        """Get recent errors."""
        recent_failed = sorted(failed_events, key=lambda x: x.timestamp, reverse=True)[:5]
        return [
            {
                'timestamp': event.timestamp.isoformat(),
                'error': event.error_message,
                'extraction_type': event.extraction_type
            }
            for event in recent_failed
        ]
    
    def _get_recent_performance_stats(self) -> Dict[str, Any]:
        """Get recent performance statistics."""
        if len(self.performance_history) < 5:
            return {}
        
        recent = self.performance_history[-5:]
        return {
            'average_extraction_time_ms': round(sum(p.extraction_time_ms for p in recent) / len(recent), 2),
            'average_total_time_ms': round(sum(p.total_time_ms for p in recent) / len(recent), 2),
            'average_memory_usage_mb': round(sum(p.memory_usage_mb for p in recent) / len(recent), 2)
        }


# Global statistics tracker instance
statistics_tracker = ExtractionStatisticsTracker()
