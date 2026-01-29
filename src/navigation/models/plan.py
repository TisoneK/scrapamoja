"""
PathPlan entity

Optimized sequence of navigation actions with timing, interactions, and fallback options.
Conforms to Constitution Principle III - Deep Modularity.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class RouteStep:
    """Single step in a navigation path"""
    
    step_number: int
    route_id: str
    action_type: str  # click, navigate, submit, wait, etc.
    target_selector: str = ""
    target_url: str = ""
    expected_delay: float = 1.0
    interaction_data: Optional[Dict[str, Any]] = None
    step_description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert route step to dictionary"""
        return {
            'step_number': self.step_number,
            'route_id': self.route_id,
            'action_type': self.action_type,
            'target_selector': self.target_selector,
            'target_url': self.target_url,
            'expected_delay': self.expected_delay,
            'interaction_data': self.interaction_data,
            'step_description': self.step_description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteStep':
        """Create route step from dictionary"""
        return cls(
            step_number=data['step_number'],
            route_id=data['route_id'],
            action_type=data['action_type'],
            target_selector=data.get('target_selector', ''),
            target_url=data.get('target_url', ''),
            expected_delay=data.get('expected_delay', 1.0),
            interaction_data=data.get('interaction_data'),
            step_description=data.get('step_description', '')
        )


@dataclass
class PlanMetadata:
    """Metadata for path plan creation and optimization"""
    
    created_by: str = "navigation_system"
    planning_algorithm: str = "dijkstra"
    risk_tolerance: float = 0.3
    optimization_criteria: List[str] = field(default_factory=lambda: ["risk", "time"])
    alternative_count: int = 0
    plan_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            'created_by': self.created_by,
            'planning_algorithm': self.planning_algorithm,
            'risk_tolerance': self.risk_tolerance,
            'optimization_criteria': self.optimization_criteria,
            'alternative_count': self.alternative_count,
            'plan_version': self.plan_version
        }


@dataclass
class PathPlan:
    """Optimized sequence of navigation actions"""
    
    # Core identification
    plan_id: str
    
    # Path definition
    source_context: str
    target_destination: str
    
    # Route sequence
    route_sequence: List[RouteStep] = field(default_factory=list)
    
    # Quality metrics
    total_risk_score: float = 0.0
    estimated_duration: float = 0.0
    
    # Fallback options
    fallback_plans: List[str] = field(default_factory=list)  # Plan IDs
    
    # Metadata
    plan_metadata: PlanMetadata = field(default_factory=PlanMetadata)
    
    # Status tracking
    status: str = "planned"  # planned, executing, completed, failed, aborted
    current_step: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    execution_started: Optional[datetime] = None
    execution_completed: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate plan after dataclass creation"""
        self._validate_plan()
    
    def _validate_plan(self) -> None:
        """Validate plan data according to business rules"""
        if not self.plan_id:
            raise ValueError("Plan ID cannot be empty")
        
        if not self.source_context:
            raise ValueError("Source context cannot be empty")
        
        if not self.target_destination:
            raise ValueError("Target destination cannot be empty")
        
        if not 0.0 <= self.total_risk_score <= 1.0:
            raise ValueError("Total risk score must be between 0.0 and 1.0")
        
        if self.estimated_duration < 0:
            raise ValueError("Estimated duration must be non-negative")
        
        # Validate route sequence
        for i, step in enumerate(self.route_sequence):
            if step.step_number != i + 1:
                raise ValueError(f"Step {i + 1} has incorrect step_number: {step.step_number}")
    
    def is_production_ready(self) -> bool:
        """Check if plan meets production quality thresholds"""
        return (
            self.total_risk_score < 0.3 and
            len(self.route_sequence) > 0 and
            self.estimated_duration > 0
        )
    
    def add_route_step(
        self,
        step_number: int,
        route_id: str,
        action_type: str,
        target_selector: str = "",
        target_url: str = "",
        expected_delay: float = 1.0,
        interaction_data: Optional[Dict[str, Any]] = None,
        step_description: str = ""
    ) -> None:
        """Add a route step to the plan"""
        step = RouteStep(
            step_number=step_number,
            route_id=route_id,
            action_type=action_type,
            target_selector=target_selector,
            target_url=target_url,
            expected_delay=expected_delay,
            interaction_data=interaction_data,
            step_description=step_description
        )
        
        # Insert step in correct position
        self.route_sequence.append(step)
        self.route_sequence.sort(key=lambda s: s.step_number)
        
        # Recalculate estimated duration
        self._recalculate_duration()
        self.updated_at = datetime.utcnow()
    
    def remove_route_step(self, step_number: int) -> None:
        """Remove a route step from the plan"""
        self.route_sequence = [
            step for step in self.route_sequence 
            if step.step_number != step_number
        ]
        
        # Renumber remaining steps
        for i, step in enumerate(self.route_sequence):
            step.step_number = i + 1
        
        # Recalculate estimated duration
        self._recalculate_duration()
        self.updated_at = datetime.utcnow()
    
    def get_current_step(self) -> Optional[RouteStep]:
        """Get the current step in execution"""
        if 0 <= self.current_step < len(self.route_sequence):
            return self.route_sequence[self.current_step]
        return None
    
    def get_next_step(self) -> Optional[RouteStep]:
        """Get the next step to execute"""
        next_step_index = self.current_step + 1
        if next_step_index < len(self.route_sequence):
            return self.route_sequence[next_step_index]
        return None
    
    def advance_to_next_step(self) -> bool:
        """Advance to the next step in the plan"""
        if self.current_step < len(self.route_sequence) - 1:
            self.current_step += 1
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def reset_execution(self) -> None:
        """Reset plan execution to beginning"""
        self.current_step = 0
        self.status = "planned"
        self.execution_started = None
        self.execution_completed = None
        self.updated_at = datetime.utcnow()
    
    def start_execution(self) -> None:
        """Mark plan as being executed"""
        self.status = "executing"
        self.execution_started = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete_execution(self, success: bool = True) -> None:
        """Mark plan execution as completed"""
        self.status = "completed" if success else "failed"
        self.execution_completed = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def abort_execution(self) -> None:
        """Abort plan execution"""
        self.status = "aborted"
        self.execution_completed = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def get_execution_progress(self) -> float:
        """Get execution progress as percentage"""
        if len(self.route_sequence) == 0:
            return 0.0
        return (self.current_step + 1) / len(self.route_sequence)
    
    def get_remaining_steps(self) -> List[RouteStep]:
        """Get remaining steps to execute"""
        return self.route_sequence[self.current_step + 1:]
    
    def get_completed_steps(self) -> List[RouteStep]:
        """Get completed steps"""
        return self.route_sequence[:self.current_step + 1]
    
    def add_fallback_plan(self, fallback_plan_id: str) -> None:
        """Add a fallback plan"""
        if fallback_plan_id not in self.fallback_plans:
            self.fallback_plans.append(fallback_plan_id)
            self.plan_metadata.alternative_count = len(self.fallback_plans)
            self.updated_at = datetime.utcnow()
    
    def remove_fallback_plan(self, fallback_plan_id: str) -> None:
        """Remove a fallback plan"""
        if fallback_plan_id in self.fallback_plans:
            self.fallback_plans.remove(fallback_plan_id)
            self.plan_metadata.alternative_count = len(self.fallback_plans)
            self.updated_at = datetime.utcnow()
    
    def _recalculate_duration(self) -> None:
        """Recalculate estimated duration from steps"""
        self.estimated_duration = sum(
            step.expected_delay for step in self.route_sequence
        )
    
    def update_risk_score(self, new_risk_score: float) -> None:
        """Update total risk score"""
        if 0.0 <= new_risk_score <= 1.0:
            self.total_risk_score = new_risk_score
            self.updated_at = datetime.utcnow()
        else:
            raise ValueError("Risk score must be between 0.0 and 1.0")
    
    def get_plan_summary(self) -> Dict[str, Any]:
        """Get summary of the path plan"""
        return {
            'plan_id': self.plan_id,
            'source_context': self.source_context,
            'target_destination': self.target_destination,
            'total_steps': len(self.route_sequence),
            'current_step': self.current_step,
            'total_risk_score': self.total_risk_score,
            'estimated_duration': self.estimated_duration,
            'status': self.status,
            'progress_percentage': self.get_execution_progress(),
            'fallback_plans_count': len(self.fallback_plans),
            'is_production_ready': self.is_production_ready(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary representation"""
        return {
            'plan_id': self.plan_id,
            'source_context': self.source_context,
            'target_destination': self.target_destination,
            'route_sequence': [step.to_dict() for step in self.route_sequence],
            'total_risk_score': self.total_risk_score,
            'estimated_duration': self.estimated_duration,
            'fallback_plans': self.fallback_plans,
            'plan_metadata': self.plan_metadata.to_dict(),
            'status': self.status,
            'current_step': self.current_step,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'execution_started': self.execution_started.isoformat() if self.execution_started else None,
            'execution_completed': self.execution_completed.isoformat() if self.execution_completed else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PathPlan':
        """Create plan from dictionary representation"""
        plan = cls(
            plan_id=data['plan_id'],
            source_context=data['source_context'],
            target_destination=data['target_destination'],
            total_risk_score=data.get('total_risk_score', 0.0),
            estimated_duration=data.get('estimated_duration', 0.0),
            fallback_plans=data.get('fallback_plans', []),
            plan_metadata=PlanMetadata(**data.get('plan_metadata', {})),
            status=data.get('status', 'planned'),
            current_step=data.get('current_step', 0)
        )
        
        # Add route steps
        for step_data in data.get('route_sequence', []):
            step = RouteStep.from_dict(step_data)
            plan.route_sequence.append(step)
        
        # Set timestamps
        if 'created_at' in data:
            plan.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            plan.updated_at = datetime.fromisoformat(data['updated_at'])
        if 'execution_started' in data and data['execution_started']:
            plan.execution_started = datetime.fromisoformat(data['execution_started'])
        if 'execution_completed' in data and data['execution_completed']:
            plan.execution_completed = datetime.fromisoformat(data['execution_completed'])
        
        return plan
    
    def to_json(self) -> str:
        """Convert plan to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PathPlan':
        """Create plan from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
