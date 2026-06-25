"""
Snapshot System Integration Example

This file demonstrates how to use the fully integrated snapshot system
that hooks into all parts of your scraping infrastructure.

The snapshot system is now a first-class citizen that automatically
captures snapshots when ANY part of the system fails.
"""

import asyncio
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


async def main():
    """Example of using the integrated snapshot system."""
    
    # 1. Get the snapshot coordinator (central orchestration)
    coordinator = get_snapshot_coordinator()
    
    # 2. Initialize all integrations (hooks into your entire infrastructure)
    print("🚀 Initializing snapshot system integrations...")
    success = await coordinator.initialize_all_integrations()
    
    if not success:
        print("❌ Failed to initialize snapshot integrations")
        return
    
    print("✅ All snapshot integrations initialized successfully!")
    
    # 3. Get system health
    health = await coordinator.get_integration_health()
    print(f"🏥 System Health: {health['coordinator']['status']}")
    print(f"   Initialized Integrations: {health['coordinator']['initialized_integrations']}")
    
    # 4. Get comprehensive statistics
    stats = await coordinator.get_system_statistics()
    print(f"📊 System Statistics:")
    print(f"   Total Snapshots: {stats['snapshot_manager']['total_snapshots']}")
    print(f"   Success Rate: {stats['snapshot_manager']['success_rate']:.1f}%")
    
    # 5. Manual snapshot capture (if needed)
    snapshot_manager = get_snapshot_manager()
    
    # Create context for manual snapshot
    context = SnapshotContext(
        site="example_site",
        module="manual_testing",
        component="demo",
        session_id="test_session_123",
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
    
    # Note: In real usage, you'd get the actual page from your browser manager
    # page = await get_active_page()
    # bundle = await snapshot_manager.capture_snapshot(page, context, config)
    
    print("🎯 Snapshot system is now fully integrated!")
    print("   - Browser events automatically trigger snapshots")
    print("   - Session lifecycle events automatically trigger snapshots") 
    print("   - Selector failures automatically trigger snapshots")
    print("   - Scraper errors automatically trigger snapshots")
    print("   - Unhandled exceptions automatically trigger snapshots")
    print("   - Retry exhaustion automatically triggers snapshots")
    print("   - All events are monitored and reported")
    
    # 6. Real-time monitoring
    monitoring = coordinator.monitoring  # type: MonitoringSnapshot
    await monitoring.perform_health_check()
    
    print("\n📈 Integration Complete!")
    print("   Your snapshot system is now a first-class citizen")
    print("   It will automatically capture snapshots on ANY system failure")
    print("   No manual intervention required!")


if __name__ == "__main__":
    asyncio.run(main())
