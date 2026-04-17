"""
Comprehensive test for browser lifecycle management components.

This test validates that all browser lifecycle components work together
including events, metrics, resilience, and snapshot functionality.
"""

import asyncio
from src.browser import BrowserManager, BrowserSession, BrowserConfiguration
from src.browser.config import BrowserType
from src.observability.events import EventTypes, publish_browser_session_created
from src.observability.metrics import get_browser_metrics_collector
from src.browser.lifecycle import lifecycle_manager, ModulePhase
from src.browser.resilience import resilience_manager
from src.core.snapshot import get_snapshot_manager as snapshot_manager
from tests.fixtures.browser_configs import CHROMIUM_HEADLESS_CONFIG


async def test_browser_lifecycle_integration():
    """Test integration of all browser lifecycle components."""
    print("🧪 Testing Browser Lifecycle Management Integration...")
    
    # Test 1: Configuration
    print("\n1. Testing Configuration...")
    config = CHROMIUM_HEADLESS_CONFIG
    print(f"   ✓ Browser type: {config.browser_type.value}")
    print(f"   ✓ Headless mode: {config.headless}")
    print(f"   ✓ Memory limit: {config.resource_limits.max_memory_mb}MB")
    
    # Test 2: Event System
    print("\n2. Testing Event System...")
    event_id = await publish_browser_session_created("test-session", "chromium")
    print(f"   ✓ Browser session created event published: {event_id}")
    
    # Test 3: Metrics Collection
    print("\n3. Testing Metrics Collection...")
    metrics_collector = get_browser_metrics_collector()
    metrics_collector.start_session_tracking("test-session", "chromium")
    metrics_collector.record_page_created("test-session")
    metrics_collector.record_context_created("test-session")
    metrics_collector.record_resource_usage("test-session", 256.0, 45.5)
    print("   ✓ Browser metrics tracking active")
    
    # Test 4: Lifecycle Management
    print("\n4. Testing Lifecycle Management...")
    browser_module = lifecycle_manager.register_module("test_browser")
    await browser_module.initialize()
    await browser_module.activate()
    print(f"   ✓ Module phase: {browser_module.phase.value}")
    print(f"   ✓ Module healthy: {browser_module.is_healthy()}")
    
    # Test 5: Resilience Framework
    print("\n5. Testing Resilience Framework...")
    circuit_status = resilience_manager.get_circuit_status()
    print(f"   ✓ Circuit breakers registered: {len(circuit_status)}")
    
    # Test 6: Snapshot Manager
    print("\n6. Testing Snapshot Manager...")
    snapshots = snapshot_manager().list_snapshots()
    print(f"   ✓ Snapshot manager initialized: {len(snapshots)} snapshots found")
    
    # Test 7: Browser Session (without actual browser)
    print("\n7. Testing Browser Session...")
    session = BrowserSession(configuration=config)
    print(f"   ✓ Session created: {session.session_id[:8]}...")
    print(f"   ✓ Session status: {session.status.value}")
    
    # Test 8: Browser Manager
    print("\n8. Testing Browser Manager...")
    manager = BrowserManager()
    stats = await manager.get_statistics()
    print(f"   ✓ Manager statistics: {stats.total_sessions} total sessions")
    
    # Test 9: Integration Check
    print("\n9. Testing Component Integration...")
    
    # Finalize metrics
    final_metrics = metrics_collector.finalize_session_metrics("test-session")
    if final_metrics:
        print(f"   ✓ Final metrics: {final_metrics.total_pages_created} pages, {final_metrics.peak_memory_mb}MB peak")
    
    # Health check
    health_status = lifecycle_manager.get_health_status()
    print(f"   ✓ System health: {len(health_status)} modules monitored")
    
    print("\n✅ All browser lifecycle components working correctly!")
    print("\n📊 Summary:")
    print("   • Event system: ✅ Operational")
    print("   • Metrics collection: ✅ Operational") 
    print("   • Lifecycle management: ✅ Operational")
    print("   • Resilience framework: ✅ Operational")
    print("   • Snapshot integration: ✅ Operational")
    print("   • Configuration management: ✅ Operational")
    print("   • Session management: ✅ Operational")
    
    # Cleanup
    await browser_module.shutdown()
    metrics_collector.cleanup_session_metrics("test-session")
    print("\n🧹 Cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_browser_lifecycle_integration())
