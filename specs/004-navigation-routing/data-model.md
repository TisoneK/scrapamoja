# Data Model: Navigation & Routing Intelligence

**Created**: 2025-01-27  
**Purpose**: Entity definitions and relationships for Navigation & Routing Intelligence

## Core Entities

### NavigationRoute

Represents a discoverable navigation path with source, destination, and traversal metadata.

**Fields**:
- `route_id`: str - Unique identifier for the route
- `source_url`: str - Starting point URL or DOM selector
- `destination_url`: str - Target destination URL or DOM selector
- `route_type`: RouteType - Classification (LINK, FORM, API, CLIENT_SIDE)
- `traversal_method`: TraversalMethod - How to navigate (CLICK, FORM_SUBMIT, API_CALL, CLIENT_ROUTE)
- `selector_confidence`: float - Confidence score from selector engine (0.0-1.0)
- `detection_risk`: float - Risk assessment score (0.0-1.0, lower is better)
- `interaction_requirements`: List[InteractionRequirement] - Required user interactions
- `timing_constraints`: TimingConstraints - Timing and delay requirements
- `metadata`: Dict[str, Any] - Additional route-specific data

**Validation Rules**:
- `route_id` must be unique within route graph
- `selector_confidence` must be >0.8 for production use
- `detection_risk` must be <0.3 for preferred routes
- At least one traversal method must be specified

### RouteGraph

Network of interconnected navigation routes with weighted relationships and traversal costs.

**Fields**:
- `graph_id`: str - Unique identifier for the graph
- `routes`: Dict[str, NavigationRoute] - All routes in the graph
- `adjacency_matrix`: Dict[str, Dict[str, float]] - Route connections with weights
- `graph_metadata`: GraphMetadata - Graph creation and analysis data
- `last_updated`: datetime - Last modification timestamp

**Validation Rules**:
- All route IDs in adjacency matrix must exist in routes
- Graph must be connected or have valid disconnected components
- Weight values must be positive and finite

### NavigationContext

Current state information including page data, session state, and navigation history.

**Fields**:
- `context_id`: str - Unique context identifier
- `session_id`: str - Associated browser session
- `current_page`: PageState - Current page information
- `navigation_history`: List[NavigationEvent] - Historical navigation actions
- `session_data`: Dict[str, Any] - Session-specific data
- `authentication_state`: AuthenticationState - Current auth status
- `correlation_id`: str - For logging and tracing

**Validation Rules**:
- `context_id` must be unique within session
- Navigation history must be chronological
- Session data must be serializable

### PathPlan

Optimized sequence of navigation actions with timing, interactions, and fallback options.

**Fields**:
- `plan_id`: str - Unique plan identifier
- `source_context`: str - Starting context ID
- `target_destination`: str - Target destination identifier
- `route_sequence`: List[RouteStep] - Ordered navigation steps
- `total_risk_score`: float - Cumulative detection risk
- `estimated_duration`: float - Planned execution time in seconds
- `fallback_plans`: List[PathPlan] - Alternative routes if primary fails
- `plan_metadata`: PlanMetadata - Creation and optimization data

**Validation Rules**:
- Route sequence must be valid and connected
- Total risk score must be <0.3 for production plans
- Fallback plans must have different route sequences

### RouteOptimizer

Learning component that analyzes navigation outcomes and improves route selection.

**Fields**:
- `optimizer_id`: str - Unique optimizer identifier
- `learning_data`: LearningDataSet - Historical navigation data
- `optimization_rules`: List[OptimizationRule] - Learned optimization patterns
- `performance_metrics`: PerformanceMetrics - Success rates and improvements
- `last_training`: datetime - Last model update timestamp

**Validation Rules**:
- Learning data must be statistically significant (>100 samples)
- Optimization rules must be conflict-free
- Performance metrics must be current (last 30 days)

### NavigationEvent

Recorded navigation action with context, outcome, and performance metrics.

**Fields**:
- `event_id`: str - Unique event identifier
- `timestamp`: datetime - When the navigation occurred
- `route_id`: str - Route that was attempted
- `context_before`: str - Context ID before navigation
- `context_after`: str - Context ID after navigation
- `outcome`: NavigationOutcome - Success/failure status
- `performance_metrics`: EventPerformanceMetrics - Timing and resource usage
- `error_details`: Optional[str] - Error information if failed

**Validation Rules**:
- Event ID must be unique globally
- Timestamp must be valid and chronological
- Performance metrics must be positive values

## Supporting Enums and Types

### RouteType
```python
class RouteType(Enum):
    LINK = "link"           # Standard hyperlink navigation
    FORM = "form"           # Form submission navigation
    API = "api"             # API-driven navigation
    CLIENT_SIDE = "client" # Client-side routing
    JAVASCRIPT = "js"       # JavaScript-triggered navigation
```

### TraversalMethod
```python
class TraversalMethod(Enum):
    CLICK = "click"                    # Click interaction
    FORM_SUBMIT = "form_submit"        # Form submission
    API_CALL = "api_call"              # API request
    CLIENT_ROUTE = "client_route"      # Client-side route change
    JAVASCRIPT_EXECUTION = "js_exec"   # JavaScript execution
```

### NavigationOutcome
```python
class NavigationOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DETECTED = "detected"
    REDIRECTED = "redirected"
```

## Relationships

### Primary Relationships
1. **RouteGraph** contains 1..* **NavigationRoute** entities
2. **NavigationContext** references 0..* **NavigationEvent** entities
3. **PathPlan** references 1..* **NavigationRoute** entities
4. **RouteOptimizer** analyzes 0..* **NavigationEvent** entities
5. **NavigationEvent** references 1 **NavigationRoute** entity

### Secondary Relationships
- **PathPlan** may reference alternative **PathPlan** entities (fallbacks)
- **NavigationContext** may reference **AuthenticationState** for auth-gated routes
- **RouteOptimizer** updates **NavigationRoute** weights based on learning

## State Transitions

### NavigationRoute States
1. **DISCOVERED** → **VALIDATED** → **ACTIVE** → **DEPRECATED**
2. **ACTIVE** → **BLOCKED** → **ACTIVE** (when unblocked)
3. **ACTIVE** → **HIGH_RISK** → **ACTIVE** (when risk reduced)

### NavigationContext States
1. **INITIALIZING** → **ACTIVE** → **NAVIGATING** → **ACTIVE**
2. **ACTIVE** → **ERROR** → **RECOVERING** → **ACTIVE**
3. **ACTIVE** → **EXPIRED** → **TERMINATED**

### PathPlan States
1. **PLANNED** → **EXECUTING** → **COMPLETED**
2. **EXECUTING** → **FAILED** → **FALLBACK** → **EXECUTING**
3. **EXECUTING** → **ABORTED** → **TERMINATED**

## Data Validation

### Schema Versioning
All entities support JSON schema versioning for backward compatibility:
- Current version: "1.0.0"
- Migration strategy: Additive changes only, never remove fields
- Validation: Strict schema validation on load, lenient on save

### Performance Constraints
- RouteGraph: Maximum 10,000 routes, memory <200MB
- NavigationContext: Maximum 1000 events per session
- PathPlan: Maximum 50 steps per plan, calculation <100ms
- RouteOptimizer: Maximum 100,000 historical events

## Integration Points

### Selector Engine Integration
- NavigationRoute.selector_confidence from selector engine scoring
- TraversalMethod based on selector type and interaction patterns
- Context scoping maintained through NavigationContext

### Stealth System Integration
- NavigationRoute.detection_risk from stealth risk assessment
- TimingConstraints aligned with human behavior patterns
- Fallback routes based on stealth trigger responses

### Browser System Integration
- NavigationContext.session_id from browser session management
- PageState from browser page analysis
- AuthenticationState from browser auth handling
