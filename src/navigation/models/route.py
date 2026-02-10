"""
NavigationRoute entity

Represents a discoverable navigation path with source, destination, and traversal metadata.
Conforms to Constitution Principle VII - Neutral Naming Convention.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json


class RouteType(Enum):
    """Classification of navigation route types"""
    LINK = "link"           # Standard hyperlink navigation
    FORM = "form"           # Form submission navigation
    API = "api"             # API-driven navigation
    CLIENT_SIDE = "client" # Client-side routing
    JAVASCRIPT = "js"       # JavaScript-triggered navigation


class TraversalMethod(Enum):
    """Method for navigating the route"""
    CLICK = "click"                    # Click interaction
    FORM_SUBMIT = "form_submit"        # Form submission
    API_CALL = "api_call"              # API request
    CLIENT_ROUTE = "client_route"      # Client-side route change
    JAVASCRIPT_EXECUTION = "js_exec"   # JavaScript execution


@dataclass
class InteractionRequirement:
    """Required user interaction for route traversal"""
    interaction_type: str
    element_selector: str
    required_data: Optional[Dict[str, Any]] = None
    timing_delay: float = 0.0


@dataclass
class TimingConstraints:
    """Timing and delay requirements for route traversal"""
    min_delay: float = 0.5
    max_delay: float = 3.0
    interaction_delay: float = 1.0
    page_load_wait: float = 2.0


@dataclass
class NavigationRoute:
    """Represents a discoverable navigation path with metadata"""
    
    # Core identification
    route_id: str
    source_url: str
    destination_url: str
    route_type: RouteType
    traversal_method: TraversalMethod
    
    # Quality metrics
    selector_confidence: float = 0.0
    detection_risk: float = 0.0
    
    # Interaction requirements
    interaction_requirements: List[InteractionRequirement] = field(default_factory=list)
    timing_constraints: TimingConstraints = field(default_factory=TimingConstraints)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_validated: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate route data after initialization"""
        self._validate_route()
    
    def _validate_route(self) -> None:
        """Validate route data according to business rules"""
        if not self.route_id:
            raise ValueError("Route ID cannot be empty")
        
        if not self.source_url:
            raise ValueError("Source URL cannot be empty")
        
        if not self.destination_url:
            raise ValueError("Destination URL cannot be empty")
        
        if not 0.0 <= self.selector_confidence <= 1.0:
            raise ValueError("Selector confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= self.detection_risk <= 1.0:
            raise ValueError("Detection risk must be between 0.0 and 1.0")
        
        if not self.interaction_requirements and self.traversal_method == TraversalMethod.FORM_SUBMIT:
            raise ValueError("Form submission routes require interaction requirements")
    
    def is_production_ready(self) -> bool:
        """Check if route meets production quality thresholds"""
        return (
            self.selector_confidence > 0.8 and
            self.detection_risk < 0.3 and
            self.last_validated is not None
        )
    
    def is_preferred_route(self) -> bool:
        """Check if route is preferred for navigation"""
        return self.detection_risk < 0.3
    
    def update_validation_status(self, confidence: float, risk: float) -> None:
        """Update validation metrics and timestamp"""
        self.selector_confidence = confidence
        self.detection_risk = risk
        self.last_validated = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_interaction_requirement(
        self, 
        interaction_type: str, 
        element_selector: str,
        required_data: Optional[Dict[str, Any]] = None,
        timing_delay: float = 0.0
    ) -> None:
        """Add interaction requirement to route"""
        requirement = InteractionRequirement(
            interaction_type=interaction_type,
            element_selector=element_selector,
            required_data=required_data,
            timing_delay=timing_delay
        )
        self.interaction_requirements.append(requirement)
        self.updated_at = datetime.utcnow()
    
    def update_timing_constraints(
        self,
        min_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        interaction_delay: Optional[float] = None,
        page_load_wait: Optional[float] = None
    ) -> None:
        """Update timing constraints for route"""
        if min_delay is not None:
            self.timing_constraints.min_delay = min_delay
        if max_delay is not None:
            self.timing_constraints.max_delay = max_delay
        if interaction_delay is not None:
            self.timing_constraints.interaction_delay = interaction_delay
        if page_load_wait is not None:
            self.timing_constraints.page_load_wait = page_load_wait
        
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert route to dictionary representation"""
        return {
            'route_id': self.route_id,
            'source_url': self.source_url,
            'destination_url': self.destination_url,
            'route_type': self.route_type.value,
            'traversal_method': self.traversal_method.value,
            'selector_confidence': self.selector_confidence,
            'detection_risk': self.detection_risk,
            'interaction_requirements': [
                {
                    'interaction_type': ir.interaction_type,
                    'element_selector': ir.element_selector,
                    'required_data': ir.required_data,
                    'timing_delay': ir.timing_delay
                }
                for ir in self.interaction_requirements
            ],
            'timing_constraints': {
                'min_delay': self.timing_constraints.min_delay,
                'max_delay': self.timing_constraints.max_delay,
                'interaction_delay': self.timing_constraints.interaction_delay,
                'page_load_wait': self.timing_constraints.page_load_wait
            },
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_validated': self.last_validated.isoformat() if self.last_validated else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NavigationRoute':
        """Create route from dictionary representation"""
        # Convert timing constraints
        timing_data = data.get('timing_constraints', {})
        timing_constraints = TimingConstraints(
            min_delay=timing_data.get('min_delay', 0.5),
            max_delay=timing_data.get('max_delay', 3.0),
            interaction_delay=timing_data.get('interaction_delay', 1.0),
            page_load_wait=timing_data.get('page_load_wait', 2.0)
        )
        
        # Convert interaction requirements
        interaction_requirements = []
        for ir_data in data.get('interaction_requirements', []):
            requirement = InteractionRequirement(
                interaction_type=ir_data['interaction_type'],
                element_selector=ir_data['element_selector'],
                required_data=ir_data.get('required_data'),
                timing_delay=ir_data.get('timing_delay', 0.0)
            )
            interaction_requirements.append(requirement)
        
        # Create route
        route = cls(
            route_id=data['route_id'],
            source_url=data['source_url'],
            destination_url=data['destination_url'],
            route_type=RouteType(data['route_type']),
            traversal_method=TraversalMethod(data['traversal_method']),
            selector_confidence=data.get('selector_confidence', 0.0),
            detection_risk=data.get('detection_risk', 0.0),
            interaction_requirements=interaction_requirements,
            timing_constraints=timing_constraints,
            metadata=data.get('metadata', {})
        )
        
        # Set timestamps
        if 'created_at' in data:
            route.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            route.updated_at = datetime.fromisoformat(data['updated_at'])
        if 'last_validated' in data and data['last_validated']:
            route.last_validated = datetime.fromisoformat(data['last_validated'])
        
        return route
    
    def to_json(self) -> str:
        """Convert route to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NavigationRoute':
        """Create route from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
