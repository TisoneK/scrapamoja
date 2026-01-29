"""
Integration test fixtures for context management

Test scenarios for Navigation & Routing Intelligence context management functionality.
"""

from typing import Dict, List, Any, Optional
from src.navigation.models import NavigationContext, PageState, AuthenticationState, NavigationEvent, NavigationOutcome
from src.navigation.context_manager import ContextManager


class ContextManagementTestScenarios:
    """Test scenarios for context management"""
    
    @staticmethod
    def get_simple_context_scenario() -> Dict[str, Any]:
        """Simple context creation scenario"""
        return {
            "name": "simple_context",
            "session_id": "test_session_001",
            "initial_page": "https://example.com",
            "expected_context_id": "ctx_test_session_001_",
            "expected_page_type": "standard",
            "expected_auth_required": False
        }
    
    @staticmethod
    def get_authentication_context_scenario() -> Dict[str, Any]:
        """Authentication context scenario"""
        return {
            "name": "authentication_context",
            "session_id": "test_session_002",
            "initial_page": "https://example.com/login",
            "expected_context_id": "ctx_test_session_002_",
            "expected_page_type": "authentication",
            "expected_auth_required": True,
            "auth_state": {
                "is_authenticated": False,
                "auth_method": "form",
                "auth_domain": "example.com",
                "session_id": "sess_test_002"
            }
        }
    
    @staticmethod
    def get_multi_page_journey_scenario() -> Dict[str, Any]:
        """Multi-page journey scenario"""
        return {
            "name": "multi_page_journey",
            "session_id": "test_session_003",
            "initial_page": "https://shop.example.com",
            "navigation_events": [
                {
                    "event_id": "nav_001",
                    "route_id": "home_to_products",
                    "outcome": "success",
                    "page_url_after": "https://shop.example.com/products"
                },
                {
                    "event_id": "nav_002", 
                    "route_id": "products_to_cart",
                    "outcome": "success",
                    "page_url_after": "https://shop.example.com/cart"
                },
                {
                    "event_id": "nav_003",
                    "route_id": "cart_to_checkout",
                    "outcome": "success",
                    "page_url_after": "https://shop.example.com/checkout"
                }
            ],
            "expected_pages_visited": 4,
            "expected_success_rate": 1.0
        }
    
    @staticmethod
    def get_session_persistence_scenario() -> Dict[str, Any]:
        """Session persistence scenario"""
        return {
            "name": "session_persistence",
            "session_id": "test_session_004",
            "initial_page": "https://app.example.com",
            "session_data": {
                "user_preferences": {
                    "theme": "dark",
                    "language": "en"
                },
                "shopping_cart": {
                    "items": ["item1", "item2"],
                    "total": 99.99
                }
            },
            "expected_persistence": True
        }
    
    @staticmethod
    def get_context_cleanup_scenario() -> Dict[str, Any]:
        """Context cleanup scenario"""
        return {
            "name": "context_cleanup",
            "session_id": "test_session_005",
            "initial_page": "https://example.com",
            "simulate_age_hours": 25,
            "expected_cleanup": True,
            "max_age_hours": 24
        }


class MockNavigationEvents:
    """Mock navigation events for testing"""
    
    @staticmethod
    def create_success_event(
        event_id: str,
        route_id: str,
        page_url_after: str,
        duration_seconds: float = 1.0
    ) -> NavigationEvent:
        """Create successful navigation event"""
        return NavigationEvent(
            event_id=event_id,
            route_id=route_id,
            context_before="step_before",
            context_after="step_after",
            outcome=NavigationOutcome.SUCCESS,
            page_url_after=page_url_after,
            performance_metrics={
                "duration_seconds": duration_seconds,
                "cpu_usage_percent": 10.0,
                "memory_usage_mb": 50.0,
                "dom_changes_count": 5
            }
        )
    
    @staticmethod
    def create_failure_event(
        event_id: str,
        route_id: str,
        error_details: str = "Element not found"
    ) -> NavigationEvent:
        """Create failed navigation event"""
        return NavigationEvent(
            event_id=event_id,
            route_id=route_id,
            context_before="step_before",
            context_after="step_before",
            outcome=NavigationOutcome.FAILURE,
            error_details=error_details,
            error_code="ELEMENT_NOT_FOUND",
            performance_metrics={
                "duration_seconds": 0.5,
                "cpu_usage_percent": 5.0,
                "memory_usage_mb": 45.0
            }
        )
    
    @staticmethod
    def create_authentication_event(
        event_id: str,
        route_id: str,
        is_authenticated: bool = True
    ) -> NavigationEvent:
        """Create authentication navigation event"""
        return NavigationEvent(
            event_id=event_id,
            route_id=route_id,
            context_before="login_page",
            context_after="dashboard_page" if is_authenticated else "login_page",
            outcome=NavigationOutcome.SUCCESS,
            page_url_after="https://example.com/dashboard" if is_authenticated else "https://example.com/login",
            performance_metrics={
                "duration_seconds": 2.0,
                "cpu_usage_percent": 15.0,
                "memory_usage_mb": 60.0
            }
        )


class MockPageStates:
    """Mock page states for testing"""
    
    @staticmethod
    def get_home_page() -> PageState:
        """Get home page state"""
        return PageState(
            url="https://example.com",
            title="Home Page",
            page_type="standard",
            load_time=1.2,
            dom_elements_count=150,
            has_dynamic_content=True,
            requires_authentication=False
        )
    
    @staticmethod
    def get_login_page() -> PageState:
        """Get login page state"""
        return PageState(
            url="https://example.com/login",
            title="Login",
            page_type="authentication",
            load_time=1.5,
            dom_elements_count=80,
            has_dynamic_content=True,
            requires_authentication=True
        )
    
    @staticmethod
    def get_dashboard_page() -> PageState:
        """Get dashboard page state"""
        return PageState(
            url="https://example.com/dashboard",
            title="Dashboard",
            page_type="admin",
            load_time=2.0,
            dom_elements_count=300,
            has_dynamic_content=True,
            requires_authentication=True
        )
    
    @staticmethod
    def get_product_page() -> PageState:
        """Get product page state"""
        return PageState(
            url="https://shop.example.com/products/item1",
            title="Product 1",
            page_type="ecommerce",
            load_time=1.8,
            dom_elements_count=200,
            has_dynamic_content=True,
            requires_authentication=False
        )


class MockAuthenticationStates:
    """Mock authentication states for testing"""
    
    @staticmethod
    def get_unauthenticated_state() -> AuthenticationState:
        """Get unauthenticated state"""
        return AuthenticationState(
            is_authenticated=False,
            auth_method="",
            auth_domain="",
            session_id=None,
            user_agent="Mozilla/5.0...",
            permissions=[]
        )
    
    @staticmethod
    def get_authenticated_state() -> AuthenticationState:
        """Get authenticated state"""
        return AuthenticationState(
            is_authenticated=True,
            auth_method="form",
            auth_domain="example.com",
            session_id="sess_abc123",
            user_agent="Mozilla/5.0...",
            permissions=["read", "write", "admin"]
        )
    
    @staticmethod
    def get_expired_state() -> AuthenticationState:
        """Get expired authentication state"""
        from datetime import datetime, timedelta
        
        return AuthenticationState(
            is_authenticated=False,
            auth_method="token",
            auth_domain="example.com",
            session_id="sess_expired",
            user_agent="Mozilla/5.0...",
            permissions=["read"],
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )


class ContextManagementTestHelpers:
    """Helpers for testing context management"""
    
    @staticmethod
    def validate_context_creation(
        context: NavigationContext,
        session_id: str,
        initial_page: str
    ) -> bool:
        """Validate context creation"""
        return (
            context.session_id == session_id and
            context.current_page.url == initial_page and
            context.pages_visited == 1 and
            context.successful_navigations == 0 and
            context.failed_navigations == 0
        )
    
    @staticmethod
    def validate_context_update(
        context: NavigationContext,
        expected_pages_visited: int,
        expected_success_rate: float,
        tolerance: float = 0.1
    ) -> bool:
        """Validate context update"""
        actual_success_rate = context.get_success_rate()
        success_rate_match = abs(actual_success_rate - expected_success_rate) <= tolerance
        
        return (
            context.pages_visited == expected_pages_visited and
            success_rate_match
        )
    
    @staticmethod
    def validate_authentication_state(
        context: NavigationContext,
        expected_authenticated: bool
    ) -> bool:
        """Validate authentication state"""
        return context.is_authenticated() == expected_authenticated
    
    @staticmethod
    def validate_session_data(
        context: NavigationContext,
        expected_data: Dict[str, Any]
    ) -> bool:
        """Validate session data"""
        for key, expected_value in expected_data.items():
            actual_value = context.get_session_data(key)
            if actual_value != expected_value:
                return False
        return True
    
    @staticmethod
    def validate_navigation_history(
        context: NavigationContext,
        expected_event_ids: List[str]
    ) -> bool:
        """Validate navigation history"""
        return (
            len(context.navigation_history) == len(expected_event_ids) and
            all(event_id in context.navigation_history for event_id in expected_event_ids)
        )
    
    @staticmethod
    def validate_context_persistence(
        original_context: NavigationContext,
        loaded_context: NavigationContext
    ) -> bool:
        """Validate context persistence"""
        return (
            original_context.context_id == loaded_context.context_id and
            original_context.session_id == loaded_context.session_id and
            original_context.pages_visited == loaded_context.pages_visited and
            original_context.current_page.url == loaded_context.current_page.url
        )
    
    @staticmethod
    def calculate_context_efficiency(
        context: NavigationContext
    ) -> Dict[str, float]:
        """Calculate context efficiency metrics"""
        success_rate = context.get_success_rate()
        avg_navigation_time = context.get_average_navigation_time()
        
        return {
            "success_rate": success_rate,
            "average_navigation_time": avg_navigation_time,
            "efficiency_score": success_rate * (1.0 / (1.0 + avg_navigation_time)),
            "pages_per_second": context.pages_visited / context.total_navigation_time if context.total_navigation_time > 0 else 0
        }
    
    @staticmethod
    def simulate_context_age(
        context: NavigationContext,
        age_hours: float
    ) -> NavigationContext:
        """Simulate context age for testing"""
        from datetime import datetime, timedelta
        
        aged_context = NavigationContext(
            context_id=context.context_id,
            session_id=context.session_id,
            current_page=context.current_page,
            navigation_history=context.navigation_history.copy(),
            session_data=context.session_data.copy(),
            authentication_state=context.authentication_state,
            correlation_id=context.correlation_id,
            created_at=datetime.utcnow() - timedelta(hours=age_hours),
            updated_at=datetime.utcnow() - timedelta(hours=age_hours),
            pages_visited=context.pages_visited,
            total_navigation_time=context.total_navigation_time,
            successful_navigations=context.successful_navigations,
            failed_navigations=context.failed_navigations
        )
        
        return aged_context


class ContextManagementTestUtils:
    """Utilities for context management testing"""
    
    @staticmethod
    def create_test_context_manager(
        storage_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> ContextManager:
        """Create test context manager"""
        if config is None:
            config = {
                "max_context_age_hours": 24,
                "max_history_items": 100,
                "auto_save_enabled": False,  # Disable for testing
                "cleanup_interval_hours": 6
            }
        
        return ContextManager(storage_path=storage_path, config=config)
    
    @staticmethod
    def generate_test_events(
        count: int,
        success_rate: float = 0.8
    ) -> List[NavigationEvent]:
        """Generate test navigation events"""
        events = []
        success_count = int(count * success_rate)
        
        for i in range(count):
            if i < success_count:
                event = MockNavigationEvents.create_success_event(
                    f"test_event_{i}",
                    f"route_{i}",
                    f"https://example.com/page_{i}",
                    1.0 + (i * 0.1)
                )
            else:
                event = MockNavigationEvents.create_failure_event(
                    f"test_event_{i}",
                    f"route_{i}",
                    f"Test error {i}"
                )
            
            events.append(event)
        
        return events
    
    @staticmethod
    def create_test_session_data() -> Dict[str, Any]:
        """Create test session data"""
        return {
            "user_id": "test_user_001",
            "preferences": {
                "theme": "light",
                "language": "en",
                "timezone": "UTC"
            },
            "shopping_cart": {
                "items": [],
                "total": 0.0,
                "currency": "USD"
            },
            "last_activity": "2025-01-27T10:00:00Z",
            "device_info": {
                "browser": "Chrome",
                "os": "Windows",
                "screen_resolution": "1920x1080"
            }
        }
    
    @staticmethod
    def simulate_context_lifecycle(
        context_manager: ContextManager,
        session_id: str,
        pages: List[str],
        events: List[NavigationEvent]
    ) -> NavigationContext:
        """Simulate complete context lifecycle"""
        # Create context
        context = context_manager.create_context(session_id, pages[0])
        
        # Update with events
        for i, event in enumerate(events):
            if i < len(pages) - 1:
                event.page_url_after = pages[i + 1]
            context_manager.update_context(context.context_id, event)
        
        return context
    
    @staticmethod
    def validate_storage_cleanup(
        storage_path: str,
        context_id: str
    ) -> bool:
        """Validate storage cleanup"""
        from pathlib import Path
        
        storage = Path(storage_path)
        context_file = storage / f"{context_id}.json"
        events_dir = storage / "events"
        
        # Check context file is removed
        if context_file.exists():
            return False
        
        # Check event files are removed
        if events_dir.exists():
            event_files = list(events_dir.glob(f"{context_id}_*.json"))
            if event_files:
                return False
        
        return True
    
    @staticmethod
    def measure_context_performance(
        context_manager: ContextManager,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Measure context management performance"""
        import time
        
        start_time = time.time()
        
        for operation in operations:
            op_type = operation["type"]
            
            if op_type == "create":
                context_manager.create_context(
                    operation["session_id"],
                    operation["initial_page"]
                )
            elif op_type == "update":
                context_manager.update_context(
                    operation["context_id"],
                    operation["event"]
                )
            elif op_type == "get":
                context_manager.get_context(operation["context_id"])
            elif op_type == "cleanup":
                context_manager.cleanup_context(operation["context_id"])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return {
            "total_time": total_time,
            "operations_per_second": len(operations) / total_time,
            "average_operation_time": total_time / len(operations)
        }
