
# Example: Integration with your main scraper
# Add this to your main application startup

import asyncio
from src.core.snapshot.handlers.coordinator import get_snapshot_coordinator

class YourScraperApp:
    def __init__(self):
        self.snapshot_coordinator = None
    
    async def start(self):
        """Start your scraper with snapshot integration."""
        try:
            # 1. Initialize snapshot coordinator
            self.snapshot_coordinator = get_snapshot_coordinator()
            await self.snapshot_coordinator.initialize_all_integrations()
            
            # 2. REGISTER WITH YOUR EXISTING SHUTDOWN SYSTEM
            # This is the key - snapshot system integrates, doesn't replace!
            # Your existing shutdown manager should call:
            # await self.snapshot_coordinator.shutdown()
            
            # 3. Run your scraper
            await self.run_scraper()
            
        except Exception as e:
            print(f"Scraper failed: {e}")
        finally:
            # 4. Your existing shutdown system handles everything
            # await self.shutdown_manager.shutdown("Scraper completed")
            pass
    
    async def run_scraper(self):
        """Your main scraper logic."""
        # Your existing scraper code here
        # Snapshots will be captured automatically on failures
        pass

# Usage
app = YourScraperApp()
asyncio.run(app.start())
