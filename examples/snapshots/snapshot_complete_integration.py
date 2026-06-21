"""
Complete Snapshot System Integration Example

This demonstrates how to initialize and use the fully integrated snapshot system
with clean, consistent naming throughout your scraping infrastructure.

The snapshot system is now a first-class citizen that automatically captures
snapshots when ANY part of your system fails.
"""

import asyncio
from typing import Any

from src.core.snapshot import (
    SnapshotManager, get_snapshot_manager,
    SnapshotContext, SnapshotConfig, SnapshotMode,
    get_snapshot_coordinator
)
from src.core.snapshot.handlers import (
    BrowserSnapshot, SessionSnapshot, ScraperSnapshot,
    SelectorSnapshot, ErrorSnapshot, RetrySnapshot,
    MonitoringSnapshot, SnapshotCoordinator
)


async def initialize_snapshot_system():
    """Initialize the complete snapshot system."""
    print("🚀 Initializing Snapshot System...")
    
    # 1. Get the snapshot coordinator (central orchestration)
    coordinator = get_snapshot_coordinator()
    
    # 2. Initialize all integrations (hooks into your entire infrastructure)
    success = await coordinator.initialize_all_integrations()
    
    if not success:
        print("❌ Failed to initialize snapshot integrations")
        return False
    
    print("✅ All snapshot integrations initialized successfully!")
    
    # 3. Display integration health
    health = await coordinator.get_integration_health()
    print(f"🏥 System Health: {health['coordinator']['status']}")
    print(f"   Initialized: {health['coordinator']['initialized_integrations']}")
    
    return coordinator


async def demonstrate_automatic_snapshots(coordinator: SnapshotCoordinator):
    """Demonstrate automatic snapshot capture on various events."""
    print("\n📸 Demonstrating Automatic Snapshot Capture...")
    
    # Simulate browser session creation (would normally be triggered by browser manager)
    print("   🔄 Simulating browser session creation...")
    await coordinator.browser._on_session_created("test_session_123", {
        "site": "example.com",
        "user_agent": "Test Browser",
        "created_at": "2024-02-13T16:08:00Z"
    })
    
    # Simulate selector failure (would normally be triggered by selector engine)
    print("   🔄 Simulating selector failure...")
    await coordinator.selector._on_selector_executed(".non-existent-element", {
        "matched_count": 0,
        "execution_time_ms": 150,
        "page_url": "https://example.com/page"
    })
    
    # Simulate retry exhaustion (would normally be triggered by retry manager)
    print("   🔄 Simulating retry exhaustion...")
    await coordinator.retry._on_retry_exhausted("operation_456", {
        "operation": "data_extraction",
        "retry_count": 3,
        "max_retries": 3,
        "last_error": "Timeout waiting for element"
    })
    
    # Simulate unhandled exception (would normally be triggered by error handler)
    print("   🔄 Simulating unhandled exception...")
    await coordinator.error._on_unhandled_exception(
        Exception, 
        ValueError("Element not found"), 
        None
    )
    
    print("   📊 All events captured and logged!")


async def show_system_statistics(coordinator: SnapshotCoordinator):
    """Display comprehensive system statistics."""
    print("\n📊 System Statistics:")
    
    # Get integration statistics
    stats = await coordinator.get_system_statistics()
    
    # Display snapshot manager stats
    snapshot_stats = stats['snapshot_manager']
    print(f"   Total Snapshots: {snapshot_stats['total_snapshots']}")
    print(f"   Successful: {snapshot_stats['successful_snapshots']}")
    print(f"   Failed: {snapshot_stats['failed_snapshots']}")
    print(f"   Success Rate: {snapshot_stats['success_rate']:.1f}%")
    print(f"   Avg Capture Time: {snapshot_stats['average_capture_time']:.0f}ms")
    
    # Display integration stats
    print("\n   Integration Breakdown:")
    for integration_name, integration_stats in stats['integrations'].items():
        if isinstance(integration_stats, dict) and 'statistics' in integration_stats:
            stats_data = integration_stats['statistics']
            print(f"   {integration_name}:")
            print(f"     Initialized: {stats_data.get('initialized', False)}")
            if 'snapshots_captured' in stats_data:
                print(f"     Snapshots Captured: {stats_data['snapshots_captured']}")
    
    # Display health status
    health = await coordinator.get_integration_health()
    print(f"\n🏥 Overall Health: {health['coordinator']['overall_status']}")
    for integration_name, health_data in health['integrations'].items():
        if isinstance(health_data, dict):
            status = health_data.get('status', 'unknown')
            print(f"   {integration_name}: {status}")


async def manual_snapshot_example(coordinator: SnapshotCoordinator, page: Any):
    """Example of manual snapshot capture."""
    print("\n📸 Manual Snapshot Example:")
    
    # Create context for manual snapshot
    context = SnapshotContext(
        site="manual_example.com",
        module="demo",
        component="manual_capture",
        session_id="manual_session_456",
        function="manual_snapshot_demo"
    )
    
    # Create config for comprehensive capture
    config = SnapshotConfig(
        mode=SnapshotMode.BOTH,  # Capture both full page and element
        capture_html=True,
        capture_screenshot=True,
        capture_console=True,
        capture_network=True,
        selector=".important-element",
        async_save=True,
        deduplication_enabled=True
    )
    
    # Capture manual snapshot
    snapshot_id = await coordinator.capture_system_snapshot(
        trigger_source="manual_demo",
        context_data={
            "site": "manual_example.com",
            "module": "demo",
            "component": "manual_capture",
            "session_id": "manual_session_456",
            "function": "manual_snapshot_demo",
            "reason": "User requested manual snapshot"
        },
        page=page
    )
    
    if snapshot_id:
        print(f"   ✅ Manual snapshot captured: {snapshot_id}")
    else:
        print("   ❌ Failed to capture manual snapshot")
    
    return snapshot_id


async def main():
    """Main demonstration function."""
    print("🎯 Snapshot System Integration Demo")
    print("=" * 50)
    
    # 1. Initialize the snapshot system
    coordinator = await initialize_snapshot_system()
    
    # 2. Demonstrate automatic snapshot capture
    await demonstrate_automatic_snapshots(coordinator)
    
    # 3. Show system statistics
    await show_system_statistics(coordinator)
    
    # 4. Manual snapshot example
    # Note: In real usage, you'd get the actual page from your browser manager
    # page = await get_active_page_from_browser_manager()
    # await manual_snapshot_example(coordinator, page)
    
    print("\n" + "=" * 50)
    print("🎉 Integration Complete!")
    print("   Your snapshot system is now a first-class citizen")
    print("   It automatically captures snapshots on ANY system failure")
    print("   No manual intervention required!")
    print("   Ready for production use! 🚀")


# Example of how to integrate into your existing scraper
class ExampleScraper:
    """Example of how to integrate snapshot system into your scraper."""
    
    def __init__(self):
        self.snapshot_coordinator = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize scraper with snapshot integration."""
        print("🔧 Initializing scraper with snapshot support...")
        
        # Initialize snapshot system
        self.snapshot_coordinator = await initialize_snapshot_system()
        self.initialized = True
        
        print("✅ Scraper initialized with automatic snapshot support!")
    
    async def scrape_with_snapshots(self, url: str):
        """Example scraping method with automatic snapshot support."""
        if not self.initialized:
            await self.initialize()
        
        print(f"🕷 Scraping {url} with automatic snapshot protection...")
        
        try:
            # Your scraping logic here
            # If any error occurs, snapshots are automatically captured
            # by the integrated system - no manual handling needed!
            
            print("✅ Scraping completed successfully!")
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            # Snapshot automatically captured by ErrorSnapshot handler
            # No need to manually call snapshot capture!
            
            raise  # Re-raise exception if needed


if __name__ == "__main__":
    asyncio.run(main())
