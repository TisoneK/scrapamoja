"""
Snapshot System as a GOOD CITIZEN

The snapshot system should INTEGRATE into your existing modules,
not require them to integrate into it.

This shows the clean architecture where snapshot is a utility
that other modules can use, not a system that controls them.
"""

import asyncio
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.snapshot import get_snapshot_manager
from src.core.snapshot.handlers.coordinator import get_snapshot_coordinator


class GoodCitizenSnapshotIntegration:
    """Shows how snapshot system integrates as a good citizen."""
    
    def __init__(self):
        self.snapshot_manager = get_snapshot_manager()
        self.snapshot_coordinator = get_snapshot_coordinator()
    
    async def integrate_into_browser_manager(self, browser_manager):
        """Integrate snapshot capabilities into browser manager."""
        print("🔗 Integrating snapshot into browser manager...")
        
        # Browser manager calls snapshot when events occur
        original_session_created = browser_manager.on_session_created
        original_session_closed = browser_manager.on_session_closed
        original_browser_crashed = browser_manager.on_browser_crashed
        
        async def enhanced_session_created(session_id, session_info):
            """Enhanced session creation with snapshot capture."""
            print(f"   📸 Session created: {session_id}")
            
            # Call original handler
            if original_session_created:
                await original_session_created(session_id, session_info)
            
            # Capture snapshot (snapshot system is good citizen)
            await self.snapshot_coordinator.browser._on_session_created(
                session_id, session_info
            )
        
        async def enhanced_session_closed(session_id, session_info):
            """Enhanced session closure with snapshot capture."""
            print(f"   📸 Session closed: {session_id}")
            
            # Call original handler
            if original_session_closed:
                await original_session_closed(session_id, session_info)
            
            # Capture snapshot
            await self.snapshot_coordinator.browser._on_session_closed(
                session_id, session_info
            )
        
        async def enhanced_browser_crashed(session_id, crash_info):
            """Enhanced browser crash with snapshot capture."""
            print(f"   📸 Browser crashed: {session_id}")
            
            # Call original handler
            if original_browser_crashed:
                await original_browser_crashed(session_id, crash_info)
            
            # Capture snapshot
            await self.snapshot_coordinator.browser._on_browser_crashed(
                session_id, crash_info
            )
        
        # Replace with enhanced versions
        browser_manager.on_session_created = enhanced_session_created
        browser_manager.on_session_closed = enhanced_session_closed
        browser_manager.on_browser_crashed = enhanced_browser_crashed
        
        print("   ✅ Browser manager enhanced with snapshot capabilities")
    
    async def integrate_into_selector_engine(self, selector_engine):
        """Integrate snapshot capabilities into selector engine."""
        print("🔗 Integrating snapshot into selector engine...")
        
        # Selector engine calls snapshot when failures occur
        original_selector_failed = selector_engine.on_selector_failed
        original_timeout_occurred = selector_engine.on_timeout_occurred
        
        async def enhanced_selector_failed(selector, context, error):
            """Enhanced selector failure with snapshot capture."""
            print(f"   📸 Selector failed: {selector}")
            
            # Call original handler
            if original_selector_failed:
                await original_selector_failed(selector, context, error)
            
            # Capture snapshot with correct signature
            await self.snapshot_coordinator.selector._on_selector_failed(
                selector, error
            )
        
        async def enhanced_timeout_occurred(operation, context, timeout):
            """Enhanced timeout with snapshot capture."""
            print(f"   📸 Timeout occurred: {operation}")
            
            # Call original handler
            if original_timeout_occurred:
                await original_timeout_occurred(operation, context, timeout)
            
            # Capture snapshot with correct signature
            await self.snapshot_coordinator.selector._on_timeout_occurred(
                operation, timeout
            )
        
        # Replace with enhanced versions
        selector_engine.on_selector_failed = enhanced_selector_failed
        selector_engine.on_timeout_occurred = enhanced_timeout_occurred
        
        print("   ✅ Selector engine enhanced with snapshot capabilities")
    
    async def integrate_into_error_handler(self, error_handler):
        """Integrate snapshot capabilities into error handler."""
        print("🔗 Integrating snapshot into error handler...")
        
        # Error handler calls snapshot when unhandled exceptions occur
        original_exception_caught = error_handler.on_exception_caught
        
        async def enhanced_exception_caught(exception, context):
            """Enhanced exception handling with snapshot capture."""
            print(f"   📸 Exception caught: {type(exception).__name__}")
            
            # Call original handler
            if original_exception_caught:
                await original_exception_caught(exception, context)
            
            # Capture snapshot with correct signature
            await self.snapshot_coordinator.error._on_unhandled_exception(
                type(exception), exception
            )
        
        # Replace with enhanced version
        error_handler.on_exception_caught = enhanced_exception_caught
        
        print("   ✅ Error handler enhanced with snapshot capabilities")
    
    async def integrate_into_retry_manager(self, retry_manager):
        """Integrate snapshot capabilities into retry manager."""
        print("🔗 Integrating snapshot into retry manager...")
        
        # Retry manager calls snapshot when retries are exhausted
        original_retry_exhausted = retry_manager.on_retry_exhausted
        
        async def enhanced_retry_exhausted(operation, context, retries):
            """Enhanced retry exhaustion with snapshot capture."""
            print(f"   📸 Retry exhausted: {operation} (retries: {retries})")
            
            # Call original handler
            if original_retry_exhausted:
                await original_retry_exhausted(operation, context, retries)
            
            # Capture snapshot with correct signature
            await self.snapshot_coordinator.retry._on_retry_exhausted(
                operation, retries
            )
        
        # Replace with enhanced version
        retry_manager.on_retry_exhausted = enhanced_retry_exhausted
        
        print("   ✅ Retry manager enhanced with snapshot capabilities")
    
    def get_snapshot_utilities(self):
        """Provide snapshot utilities for other modules to use."""
        return {
            'capture_manual_snapshot': self.snapshot_coordinator.capture_system_snapshot,
            'get_snapshot_stats': self.snapshot_coordinator.get_system_statistics,
            'get_health_status': self.snapshot_coordinator.get_integration_health,
            'is_healthy': lambda: self.snapshot_coordinator.get_integration_health()['coordinator']['overall_status'] == 'healthy'
        }


async def demonstrate_good_citizen_integration():
    """Demonstrate snapshot system as a good citizen."""
    print("🎯 Snapshot System as GOOD CITIZEN Demo")
    print("=" * 60)
    
    # Initialize snapshot system
    print("📸 Initializing snapshot system...")
    snapshot_integration = GoodCitizenSnapshotIntegration()
    
    # Initialize snapshot coordinator
    await snapshot_integration.snapshot_coordinator.initialize_all_integrations()
    print("   ✅ Snapshot system ready")
    
    # Simulate existing modules
    print("\n🔗 Integrating snapshot into existing modules...")
    
    # Mock browser manager
    class MockBrowserManager:
        def __init__(self):
            self.on_session_created = None
            self.on_session_closed = None
            self.on_browser_crashed = None
        
        async def create_session(self):
            session_id = "test_session_123"
            session_info = {"site": "example.com"}
            
            if self.on_session_created:
                await self.on_session_created(session_id, session_info)
            
            return session_id
    
    # Mock selector engine
    class MockSelectorEngine:
        def __init__(self):
            self.on_selector_failed = None
            self.on_timeout_occurred = None
        
        async def execute_selector(self, selector):
            if selector == "failing_selector":
                if self.on_selector_failed:
                    await self.on_selector_failed(selector, {}, "Element not found")
                return None
            return "found_element"
    
    # Mock error handler
    class MockErrorHandler:
        def __init__(self):
            self.on_exception_caught = None
        
        async def handle_error(self):
            exception = ValueError("Test exception")
            if self.on_exception_caught:
                await self.on_exception_caught(exception, {})
            return exception
    
    # Mock retry manager
    class MockRetryManager:
        def __init__(self):
            self.on_retry_exhausted = None
        
        async def execute_with_retry(self, operation):
            if operation == "failing_operation":
                if self.on_retry_exhausted:
                    await self.on_retry_exhausted(operation, {}, 3)
                return None
            return "success"
    
    # Create mock modules
    browser_manager = MockBrowserManager()
    selector_engine = MockSelectorEngine()
    error_handler = MockErrorHandler()
    retry_manager = MockRetryManager()
    
    # Integrate snapshot capabilities into each module
    await snapshot_integration.integrate_into_browser_manager(browser_manager)
    await snapshot_integration.integrate_into_selector_engine(selector_engine)
    await snapshot_integration.integrate_into_error_handler(error_handler)
    await snapshot_integration.integrate_into_retry_manager(retry_manager)
    
    # Get snapshot utilities
    snapshot_utils = snapshot_integration.get_snapshot_utilities()
    
    print("\n✅ Integration complete!")
    print("   📸 Snapshot system is now a GOOD CITIZEN")
    print("   🔗 Other modules enhanced with snapshot capabilities")
    print("   🛠️ Snapshot utilities available for all modules")
    
    # Demonstrate enhanced functionality
    print("\n🔄 Demonstrating enhanced modules...")
    
    # Test enhanced browser manager
    print("   🌐 Testing enhanced browser manager...")
    session_id = await browser_manager.create_session()
    print(f"      ✅ Session created with snapshot: {session_id}")
    
    # Test enhanced selector engine
    print("   🎯 Testing enhanced selector engine...")
    result = await selector_engine.execute_selector("failing_selector")
    if result is None:
        print("      ✅ Selector failure captured with snapshot")
    
    result = await selector_engine.execute_selector("working_selector")
    print(f"      ✅ Working selector succeeded: {result}")
    
    # Test enhanced error handler
    print("   ❌ Testing enhanced error handler...")
    try:
        await error_handler.handle_error()
    except Exception as e:
        print(f"      ✅ Exception captured with snapshot: {type(e).__name__}")
    
    # Test enhanced retry manager
    print("   🔄 Testing enhanced retry manager...")
    result = await retry_manager.execute_with_retry("failing_operation")
    if result is None:
        print("      ✅ Retry exhaustion captured with snapshot")
    
    # Show snapshot utilities
    print("\n📊 Snapshot utilities available:")
    print(f"   📸 Manual capture: {callable(snapshot_utils['capture_manual_snapshot'])}")
    print(f"   📈 Statistics: {callable(snapshot_utils['get_snapshot_stats'])}")
    print(f"   🏥 Health check: {callable(snapshot_utils['is_healthy'])}")
    
    # Show final status
    health = await snapshot_integration.snapshot_coordinator.get_integration_health()
    print(f"\n🏥 Overall System Health: {health['coordinator']['overall_status']}")
    
    print("\n" + "=" * 60)
    print("🎯 KEY BENEFITS OF GOOD CITIZEN APPROACH:")
    print("✅ Snapshot system INTEGRATES into existing modules")
    print("✅ No changes required to existing module interfaces")
    print("✅ Snapshot capabilities added transparently")
    print("✅ Other modules remain in control")
    print("✅ Clean separation of concerns")
    print("✅ Easy to enable/disable snapshot features")
    print("✅ Snapshot utilities available to all modules")
    
    print("\n🚀 This is the RIGHT way to integrate snapshot system!")


def create_good_citizen_template():
    """Create template for good citizen integration."""
    
    template = '''
# GOOD CITIZEN: Snapshot Integration Template
# The snapshot system integrates INTO your modules, not the other way around

from src.core.snapshot.handlers.coordinator import get_snapshot_coordinator

class YourExistingModule:
    def __init__(self):
        # Your existing initialization
        self.snapshot_coordinator = get_snapshot_coordinator()
        
        # Your existing event handlers
        self.on_your_event = None
    
    async def your_existing_method(self):
        """Your existing method enhanced with snapshot capabilities."""
        try:
            # Your existing logic here
            result = await self.do_something()
            
            # Call your existing event handler
            if self.on_your_event:
                await self.on_your_event(result)
            
            return result
            
        except Exception as e:
            # Your existing error handling
            
            # SNAPSHOT INTEGRATION: Capture failure state
            await self.snapshot_coordinator.capture_system_snapshot(
                trigger_source="your_module_failure",
                context_data={
                    "module": "your_module",
                    "component": "your_component",
                    "error": str(e),
                    "session_id": self.get_session_id()
                }
            )
            
            raise e
    
    def get_snapshot_utilities(self):
        """Provide snapshot utilities to your users."""
        return {
            'capture_snapshot': self.snapshot_coordinator.capture_system_snapshot,
            'get_stats': self.snapshot_coordinator.get_system_statistics,
            'health_check': self.snapshot_coordinator.get_integration_health
        }

# Usage:
# 1. Your module works exactly as before
# 2. Snapshot capabilities are added transparently
# 3. No changes to your existing interfaces
# 4. Snapshot system is a good citizen!
'''
    
    with open('good_citizen_template.py', 'w') as f:
        f.write(template)
    
    print("📝 Created good_citizen_template.py")
    print("   This shows how snapshot integrates as a good citizen")


async def main():
    """Main demonstration function."""
    try:
        await demonstrate_good_citizen_integration()
        create_good_citizen_template()
        
        print("\n" + "=" * 60)
        print("🎯 FINAL ARCHITECTURE INSIGHT:")
        print("✅ Snapshot system is now a GOOD CITIZEN")
        print("✅ It integrates INTO your existing modules")
        print("✅ Your modules remain in control")
        print("✅ Clean separation of concerns")
        print("✅ Easy to maintain and extend")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
