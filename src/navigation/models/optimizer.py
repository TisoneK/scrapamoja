"""
RouteOptimizer entity

Learning component that analyzes navigation outcomes and improves route selection.
Conforms to Constitution Principle III - Deep Modularity.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import json

from .event import NavigationEvent


@dataclass
class OptimizationRule:
    """Learned optimization rule for route selection"""
    
    rule_id: str
    rule_type: str  # timing, risk, success_rate, pattern
    condition: Dict[str, Any]  # When this rule applies
    action: Dict[str, Any]    # What action to take
    confidence: float = 0.0   # Confidence in this rule (0.0-1.0)
    success_rate: float = 0.0 # Historical success rate
    usage_count: int = 0      # How many times this rule was applied
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_applied: Optional[datetime] = None
    
    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """Check if this rule applies to the given context"""
        # Simple condition matching - can be enhanced with more complex logic
        for key, expected_value in self.condition.items():
            if key not in context or context[key] != expected_value:
                return False
        return True
    
    def apply_rule(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply this optimization rule to route data"""
        modified_data = route_data.copy()
        
        # Apply actions based on rule type
        if self.rule_type == "timing":
            if "timing_adjustment" in self.action:
                modified_data["timing_multiplier"] = self.action["timing_adjustment"]
        
        elif self.rule_type == "risk":
            if "risk_adjustment" in self.action:
                modified_data["risk_adjustment"] = self.action["risk_adjustment"]
        
        elif self.rule_type == "success_rate":
            if "success_bonus" in self.action:
                modified_data["success_bonus"] = self.action["success_bonus"]
        
        elif self.rule_type == "pattern":
            if "pattern_override" in self.action:
                modified_data.update(self.action["pattern_override"])
        
        self.usage_count += 1
        self.last_applied = datetime.utcnow()
        
        return modified_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary"""
        return {
            'rule_id': self.rule_id,
            'rule_type': self.rule_type,
            'condition': self.condition,
            'action': self.action,
            'confidence': self.confidence,
            'success_rate': self.success_rate,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat(),
            'last_applied': self.last_applied.isoformat() if self.last_applied else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationRule':
        """Create rule from dictionary"""
        rule = cls(
            rule_id=data['rule_id'],
            rule_type=data['rule_type'],
            condition=data['condition'],
            action=data['action'],
            confidence=data.get('confidence', 0.0),
            success_rate=data.get('success_rate', 0.0),
            usage_count=data.get('usage_count', 0)
        )
        
        if 'created_at' in data:
            rule.created_at = datetime.fromisoformat(data['created_at'])
        if 'last_applied' in data and data['last_applied']:
            rule.last_applied = datetime.fromisoformat(data['last_applied'])
        
        return rule


@dataclass
class PerformanceMetrics:
    """Performance metrics for route optimization"""
    
    total_navigations: int = 0
    successful_navigations: int = 0
    average_duration: float = 0.0
    average_risk_score: float = 0.0
    detection_rate: float = 0.0
    timeout_rate: float = 0.0
    optimization_improvement: float = 0.0  # Improvement percentage from optimization
    
    def calculate_success_rate(self) -> float:
        """Calculate navigation success rate"""
        if self.total_navigations == 0:
            return 0.0
        return self.successful_navigations / self.total_navigations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'total_navigations': self.total_navigations,
            'successful_navigations': self.successful_navigations,
            'success_rate': self.calculate_success_rate(),
            'average_duration': self.average_duration,
            'average_risk_score': self.average_risk_score,
            'detection_rate': self.detection_rate,
            'timeout_rate': self.timeout_rate,
            'optimization_improvement': self.optimization_improvement
        }


@dataclass
class LearningDataSet:
    """Historical navigation data for learning"""
    
    events: List[NavigationEvent] = field(default_factory=list)
    routes_analyzed: Set[str] = field(default_factory=set)
    min_samples_for_learning: int = 100
    max_events_stored: int = 100000
    
    def add_event(self, event: NavigationEvent) -> None:
        """Add navigation event to learning dataset"""
        self.events.append(event)
        self.routes_analyzed.add(event.route_id)
        
        # Maintain maximum size
        if len(self.events) > self.max_events_stored:
            # Remove oldest events (simple FIFO)
            self.events = self.events[-self.max_events_stored:]
    
    def get_events_for_route(self, route_id: str) -> List[NavigationEvent]:
        """Get all events for a specific route"""
        return [event for event in self.events if event.route_id == route_id]
    
    def get_successful_events(self) -> List[NavigationEvent]:
        """Get all successful navigation events"""
        return [event for event in self.events if event.is_successful()]
    
    def get_failed_events(self) -> List[NavigationEvent]:
        """Get all failed navigation events"""
        return [event for event in self.events if event.is_failure()]
    
    def get_events_in_timerange(self, start_time: datetime, end_time: datetime) -> List[NavigationEvent]:
        """Get events within a time range"""
        return [
            event for event in self.events 
            if start_time <= event.timestamp <= end_time
        ]
    
    def is_ready_for_learning(self) -> bool:
        """Check if dataset has enough samples for learning"""
        return len(self.events) >= self.min_samples_for_learning
    
    def get_dataset_summary(self) -> Dict[str, Any]:
        """Get summary of the learning dataset"""
        successful_events = self.get_successful_events()
        failed_events = self.get_failed_events()
        
        return {
            'total_events': len(self.events),
            'successful_events': len(successful_events),
            'failed_events': len(failed_events),
            'unique_routes': len(self.routes_analyzed),
            'success_rate': len(successful_events) / len(self.events) if self.events else 0.0,
            'ready_for_learning': self.is_ready_for_learning(),
            'oldest_event': min(event.timestamp for event in self.events).isoformat() if self.events else None,
            'newest_event': max(event.timestamp for event in self.events).isoformat() if self.events else None
        }


@dataclass
class RouteOptimizer:
    """Learning component for route optimization"""
    
    # Core identification
    optimizer_id: str
    
    # Learning data
    learning_data: LearningDataSet = field(default_factory=LearningDataSet)
    
    # Optimization rules
    optimization_rules: List[OptimizationRule] = field(default_factory=list)
    
    # Performance metrics
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Configuration
    learning_threshold: float = 0.7  # Confidence threshold for applying rules
    rule_confidence_decay: float = 0.95  # Decay factor for rule confidence
    max_rules_per_type: int = 50  # Maximum rules per optimization type
    
    # Timestamps
    last_training: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_navigation_event(self, event: NavigationEvent) -> None:
        """Add navigation event for learning"""
        self.learning_data.add_event(event)
        self._update_performance_metrics()
        self.updated_at = datetime.utcnow()
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics from learning data"""
        events = self.learning_data.events
        if not events:
            return
        
        successful_events = self.learning_data.get_successful_events()
        failed_events = self.learning_data.get_failed_events()
        
        self.performance_metrics.total_navigations = len(events)
        self.performance_metrics.successful_navigations = len(successful_events)
        
        # Calculate averages
        total_duration = sum(event.performance_metrics.duration_seconds for event in events)
        self.performance_metrics.average_duration = total_duration / len(events)
        
        total_risk = sum(event.stealth_score_after for event in events)
        self.performance_metrics.average_risk_score = total_risk / len(events)
        
        # Calculate rates
        detection_events = [e for e in events if e.has_detection_triggers()]
        self.performance_metrics.detection_rate = len(detection_events) / len(events)
        
        timeout_events = [e for e in events if e.outcome.value == "timeout"]
        self.performance_metrics.timeout_rate = len(timeout_events) / len(events)
    
    def analyze_outcomes(self) -> Dict[str, float]:
        """Analyze navigation outcomes for patterns"""
        if not self.learning_data.is_ready_for_learning():
            return {}
        
        events = self.learning_data.events
        analysis = {}
        
        # Analyze by route type
        route_performance = {}
        for event in events:
            if event.route_id not in route_performance:
                route_performance[event.route_id] = {'success': 0, 'total': 0, 'duration': 0, 'risk': 0}
            
            route_performance[event.route_id]['total'] += 1
            route_performance[event.route_id]['duration'] += event.performance_metrics.duration_seconds
            route_performance[event.route_id]['risk'] += event.stealth_score_after
            
            if event.is_successful():
                route_performance[event.route_id]['success'] += 1
        
        # Calculate performance metrics for each route
        for route_id, data in route_performance.items():
            analysis[f'route_{route_id}_success_rate'] = data['success'] / data['total']
            analysis[f'route_{route_id}_avg_duration'] = data['duration'] / data['total']
            analysis[f'route_{route_id}_avg_risk'] = data['risk'] / data['total']
        
        # Analyze timing patterns
        timing_analysis = self._analyze_timing_patterns(events)
        analysis.update(timing_analysis)
        
        # Analyze detection patterns
        detection_analysis = self._analyze_detection_patterns(events)
        analysis.update(detection_analysis)
        
        return analysis
    
    def _analyze_timing_patterns(self, events: List[NavigationEvent]) -> Dict[str, float]:
        """Analyze timing patterns in navigation events"""
        timing_patterns = {}
        
        # Group events by time of day
        hour_performance = {}
        for event in events:
            hour = event.timestamp.hour
            if hour not in hour_performance:
                hour_performance[hour] = {'success': 0, 'total': 0, 'duration': 0}
            
            hour_performance[hour]['total'] += 1
            hour_performance[hour]['duration'] += event.performance_metrics.duration_seconds
            
            if event.is_successful():
                hour_performance[hour]['success'] += 1
        
        # Find best and worst hours
        best_hour = max(hour_performance.keys(), 
                       key=lambda h: hour_performance[h]['success'] / hour_performance[h]['total'])
        worst_hour = min(hour_performance.keys(),
                        key=lambda h: hour_performance[h]['success'] / hour_performance[h]['total'])
        
        timing_patterns['best_success_hour'] = best_hour
        timing_patterns['best_success_rate'] = (hour_performance[best_hour]['success'] / 
                                               hour_performance[best_hour]['total'])
        timing_patterns['worst_success_hour'] = worst_hour
        timing_patterns['worst_success_rate'] = (hour_performance[worst_hour]['success'] / 
                                                hour_performance[worst_hour]['total'])
        
        return timing_patterns
    
    def _analyze_detection_patterns(self, events: List[NavigationEvent]) -> Dict[str, float]:
        """Analyze detection patterns in navigation events"""
        detection_patterns = {}
        
        events_with_detections = [e for e in events if e.has_detection_triggers()]
        if not events_with_detections:
            return detection_patterns
        
        # Analyze common detection triggers
        trigger_counts = {}
        for event in events_with_detections:
            for trigger in event.detection_triggers:
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        # Most common triggers
        common_triggers = sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)
        detection_patterns['most_common_trigger'] = common_triggers[0][0] if common_triggers else ""
        detection_patterns['most_common_trigger_count'] = common_triggers[0][1] if common_triggers else 0
        
        # Detection rate by route
        route_detection_rates = {}
        for event in events:
            if event.route_id not in route_detection_rates:
                route_detection_rates[event.route_id] = {'detections': 0, 'total': 0}
            
            route_detection_rates[event.route_id]['total'] += 1
            if event.has_detection_triggers():
                route_detection_rates[event.route_id]['detections'] += 1
        
        # Find routes with highest detection rates
        detection_rates = {
            route_id: data['detections'] / data['total']
            for route_id, data in route_detection_rates.items()
        }
        
        if detection_rates:
            highest_detection_route = max(detection_rates.keys(), key=lambda r: detection_rates[r])
            detection_patterns['highest_detection_route'] = highest_detection_route
            detection_patterns['highest_detection_rate'] = detection_rates[highest_detection_route]
        
        return detection_patterns
    
    def generate_optimization_rules(self, analysis_data: Dict[str, float]) -> List[OptimizationRule]:
        """Generate optimization rules from analysis data"""
        new_rules = []
        
        # Generate timing-based rules
        timing_rules = self._generate_timing_rules(analysis_data)
        new_rules.extend(timing_rules)
        
        # Generate risk-based rules
        risk_rules = self._generate_risk_rules(analysis_data)
        new_rules.extend(risk_rules)
        
        # Generate success rate rules
        success_rules = self._generate_success_rules(analysis_data)
        new_rules.extend(success_rules)
        
        # Add new rules if they don't conflict with existing ones
        for rule in new_rules:
            if not self._rule_conflicts(rule):
                self.optimization_rules.append(rule)
        
        # Limit rules per type
        self._limit_rules_per_type()
        
        self.last_training = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        return new_rules
    
    def _generate_timing_rules(self, analysis_data: Dict[str, float]) -> List[OptimizationRule]:
        """Generate timing-based optimization rules"""
        rules = []
        
        # Rule for best success hour
        if 'best_success_hour' in analysis_data and 'best_success_rate' in analysis_data:
            if analysis_data['best_success_rate'] > 0.8:  # High success rate threshold
                rule = OptimizationRule(
                    rule_id=f"timing_best_hour_{analysis_data['best_success_hour']}",
                    rule_type="timing",
                    condition={"hour_of_day": analysis_data['best_success_hour']},
                    action={"timing_adjustment": 0.8},  # Reduce timing by 20%
                    confidence=analysis_data['best_success_rate']
                )
                rules.append(rule)
        
        return rules
    
    def _generate_risk_rules(self, analysis_data: Dict[str, float]) -> List[OptimizationRule]:
        """Generate risk-based optimization rules"""
        rules = []
        
        # Rule for routes with high detection rates
        if 'highest_detection_route' in analysis_data and 'highest_detection_rate' in analysis_data:
            if analysis_data['highest_detection_rate'] > 0.3:  # High detection threshold
                rule = OptimizationRule(
                    rule_id=f"risk_avoid_{analysis_data['highest_detection_route']}",
                    rule_type="risk",
                    condition={"route_id": analysis_data['highest_detection_route']},
                    action={"risk_adjustment": 1.5},  # Increase risk score by 50%
                    confidence=analysis_data['highest_detection_rate']
                )
                rules.append(rule)
        
        return rules
    
    def _generate_success_rules(self, analysis_data: Dict[str, float]) -> List[OptimizationRule]:
        """Generate success rate-based optimization rules"""
        rules = []
        
        # Generate rules for high-performing routes
        for key, value in analysis_data.items():
            if key.startswith('route_') and key.endswith('_success_rate'):
                route_id = key[6:-13]  # Extract route ID from key
                if value > 0.9:  # High success rate threshold
                    rule = OptimizationRule(
                        rule_id=f"success_bonus_{route_id}",
                        rule_type="success_rate",
                        condition={"route_id": route_id},
                        action={"success_bonus": 0.1},  # 10% success bonus
                        confidence=value
                    )
                    rules.append(rule)
        
        return rules
    
    def _rule_conflicts(self, new_rule: OptimizationRule) -> bool:
        """Check if new rule conflicts with existing rules"""
        for existing_rule in self.optimization_rules:
            # Simple conflict detection - can be enhanced
            if (existing_rule.rule_type == new_rule.rule_type and 
                existing_rule.condition == new_rule.condition):
                return True
        return False
    
    def _limit_rules_per_type(self) -> None:
        """Limit number of rules per optimization type"""
        rule_types = {}
        
        # Group rules by type
        for rule in self.optimization_rules:
            if rule.rule_type not in rule_types:
                rule_types[rule.rule_type] = []
            rule_types[rule.rule_type].append(rule)
        
        # Keep only the best rules for each type
        for rule_type, rules in rule_types.items():
            if len(rules) > self.max_rules_per_type:
                # Sort by confidence and keep the best ones
                rules.sort(key=lambda r: r.confidence, reverse=True)
                kept_rules = rules[:self.max_rules_per_type]
                
                # Update the main rules list
                self.optimization_rules = [
                    r for r in self.optimization_rules 
                    if r.rule_type != rule_type or r in kept_rules
                ]
    
    def apply_optimizations(self, route_contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply optimization rules to route contexts"""
        optimized_contexts = []
        
        for context in route_contexts:
            optimized_context = context.copy()
            
            # Apply applicable rules
            for rule in self.optimization_rules:
                if rule.confidence >= self.learning_threshold and rule.is_applicable(context):
                    optimized_context = rule.apply_rule(optimized_context)
            
            optimized_contexts.append(optimized_context)
        
        return optimized_contexts
    
    def update_performance_metrics(self, new_events: List[NavigationEvent]) -> bool:
        """Update performance metrics with new events"""
        for event in new_events:
            self.add_navigation_event(event)
        
        return True
    
    def get_optimizer_summary(self) -> Dict[str, Any]:
        """Get summary of the route optimizer"""
        return {
            'optimizer_id': self.optimizer_id,
            'learning_dataset': self.learning_data.get_dataset_summary(),
            'optimization_rules_count': len(self.optimization_rules),
            'performance_metrics': self.performance_metrics.to_dict(),
            'last_training': self.last_training.isoformat() if self.last_training else None,
            'learning_threshold': self.learning_threshold,
            'ready_for_optimization': self.learning_data.is_ready_for_learning(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert optimizer to dictionary representation"""
        return {
            'optimizer_id': self.optimizer_id,
            'learning_data': {
                'events': [event.to_dict() for event in self.learning_data.events],
                'routes_analyzed': list(self.learning_data.routes_analyzed),
                'min_samples_for_learning': self.learning_data.min_samples_for_learning,
                'max_events_stored': self.learning_data.max_events_stored
            },
            'optimization_rules': [rule.to_dict() for rule in self.optimization_rules],
            'performance_metrics': self.performance_metrics.to_dict(),
            'learning_threshold': self.learning_threshold,
            'rule_confidence_decay': self.rule_confidence_decay,
            'max_rules_per_type': self.max_rules_per_type,
            'last_training': self.last_training.isoformat() if self.last_training else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteOptimizer':
        """Create optimizer from dictionary representation"""
        # Reconstruct learning data
        learning_data = LearningDataSet(
            min_samples_for_learning=data['learning_data']['min_samples_for_learning'],
            max_events_stored=data['learning_data']['max_events_stored']
        )
        
        for event_data in data['learning_data']['events']:
            from .event import NavigationEvent
            event = NavigationEvent.from_dict(event_data)
            learning_data.add_event(event)
        
        # Reconstruct optimization rules
        optimization_rules = [
            OptimizationRule.from_dict(rule_data) 
            for rule_data in data['optimization_rules']
        ]
        
        # Reconstruct performance metrics
        performance_metrics = PerformanceMetrics(**data['performance_metrics'])
        
        optimizer = cls(
            optimizer_id=data['optimizer_id'],
            learning_data=learning_data,
            optimization_rules=optimization_rules,
            performance_metrics=performance_metrics,
            learning_threshold=data.get('learning_threshold', 0.7),
            rule_confidence_decay=data.get('rule_confidence_decay', 0.95),
            max_rules_per_type=data.get('max_rules_per_type', 50)
        )
        
        # Set timestamps
        if 'last_training' in data and data['last_training']:
            optimizer.last_training = datetime.fromisoformat(data['last_training'])
        if 'created_at' in data:
            optimizer.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            optimizer.updated_at = datetime.fromisoformat(data['updated_at'])
        
        return optimizer
