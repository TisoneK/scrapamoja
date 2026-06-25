
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
