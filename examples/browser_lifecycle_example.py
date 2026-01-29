"""
Browser Lifecycle Example Using BrowserManager

Demonstrates the complete browser lifecycle using the project's BrowserManager API.
This is the recommended pattern for all automation in this project.

The example shows:
1. Getting the global BrowserManager singleton
2. Creating a BrowserSession with configuration
3. Navigating to Google and executing a search
4. Capturing page snapshots
5. Closing the session through the manager

This illustrates the centralized session management, resilience handling,
and resource monitoring provided by BrowserManager.

Usage:
    python -m examples.browser_lifecycle_example

Expected Output:
    - Console output for each lifecycle stage
    - Session initialization and resource tracking
    - Snapshot JSON file saved to data/snapshots/
    - Clean session shutdown with resource release

Requirements:
    - Python 3.11+
    - Playwright installed: playwright install
    - Write access to data/snapshots/
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.browser import (
    get_browser_manager,
    BrowserConfiguration,
    BrowserType,
)


class BrowserLifecycleExample:
    """Demonstrates browser lifecycle using the project's BrowserManager."""
    
    def __init__(
        self,
        snapshot_dir: str = "data/snapshots",
        headless: bool = True,
        timeout_ms: int = 30000
    ):
        """
        Initialize the example.
        
        Args:
            snapshot_dir: Directory to save snapshots
            headless: Whether to run browser in headless mode
            timeout_ms: Timeout for page operations (milliseconds)
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.timeout_ms = timeout_ms
        
        # Browser manager and session
        self.browser_manager = None
        self.session = None
        self.page = None
        
        # Timing tracking
        self.start_time = None
        self.stage_times = {}
    
    async def initialize_browser(self) -> None:
        """
        Stage 1: Initialize Browser Through BrowserManager
        
        Demonstrates:
        - Getting the global BrowserManager singleton
        - Creating BrowserConfiguration with stealth and other settings
        - Creating a BrowserSession through the manager
        - Creating a page for automation
        
        The BrowserManager handles:
        - Session isolation and resource tracking
        - Resilience and retry logic
        - State persistence
        - Resource monitoring
        
        Error handling: Manager initialization, session creation failures
        """
        stage_start = time.time()
        print("\n" + "=" * 60)
        print("STAGE 1: Initialize Browser (via BrowserManager)")
        print("=" * 60)
        
        try:
            print("  * Getting global BrowserManager instance...")
            # Get the singleton browser manager
            # Handles initialization automatically
            self.browser_manager = await get_browser_manager()
            
            print("  * Creating BrowserConfiguration...")
            # Create configuration with project defaults
            # Includes stealth, proxy, resource limits, and other settings
            config = BrowserConfiguration(
                browser_type=BrowserType.CHROMIUM,
                headless=self.headless,
                # Stealth configuration is built-in to BrowserConfiguration
                # It handles user-agent, viewport, locale, timezone, etc.
            )
            
            print("  * Creating browser session through manager...")
            # Create a session through the manager
            # The manager handles:
            # - Session lifecycle management
            # - Resilience and retry logic
            # - Resource monitoring
            # - State persistence
            self.session = await self.browser_manager.create_session(
                configuration=config
            )
            
            print(f"  * Creating page in session {self.session.session_id[:8]}...")
            # Create a page for automation
            # The session manages the browser instance
            self.page = await self.session.create_page()
            
            # Set timeouts for page operations
            self.page.set_default_navigation_timeout(self.timeout_ms)
            self.page.set_default_timeout(self.timeout_ms)
            
            elapsed = time.time() - stage_start
            self.stage_times["initialization"] = elapsed
            
            print(f"  [PASS] Browser initialized successfully in {elapsed:.2f}s")
            print(f"    - Session ID: {self.session.session_id[:8]}...")
            print(f"    - Browser type: {config.browser_type.value}")
            print(f"    - Headless: {self.headless}")
            print(f"    - Session status: {self.session.status.value}")
            
        except Exception as e:
            raise RuntimeError(
                f"Browser initialization failed: {str(e)}. "
                "Check that BrowserManager is properly configured."
            ) from e
    
    async def navigate_to_google(self) -> None:
        """
        Stage 2: Navigate to Google
        
        Demonstrates:
        - Navigating through a page managed by BrowserSession
        - Using wait conditions for reliable loading
        - Verifying page state after navigation
        
        Error handling: Network timeouts, navigation failures
        """
        stage_start = time.time()
        print("\n" + "=" * 60)
        print("STAGE 2: Navigate to Google")
        print("=" * 60)
        
        url = "https://www.google.com"
        
        try:
            print(f"  * Navigating to {url}...")
            # Navigate using the page from BrowserSession
            # The page is a standard Playwright AsyncPage
            await self.page.goto(url, wait_until="networkidle")
            
            print("  * Waiting for search input...")
            # Ensure search input is available
            await self.page.wait_for_selector(
                "input[name='q']",
                timeout=self.timeout_ms
            )
            
            # Verify navigation
            title = await self.page.title()
            current_url = self.page.url
            
            elapsed = time.time() - stage_start
            self.stage_times["navigation"] = elapsed
            
            print(f"  [PASS] Navigation completed in {elapsed:.2f}s")
            print(f"    - Page title: {title}")
            print(f"    - Current URL: {current_url}")
            
        except Exception as e:
            raise RuntimeError(
                f"Navigation failed: {str(e)}. "
                "Check internet connection and Google accessibility."
            ) from e
    
    async def execute_search(self, query: str = "Playwright browser automation") -> None:
        """
        Stage 3: Execute Search Action
        
        Demonstrates:
        - Form interaction through Playwright
        - Form submission
        - Waiting for results to load
        
        Error handling: Element not found, action timeouts
        """
        stage_start = time.time()
        print("\n" + "=" * 60)
        print("STAGE 3: Execute Search Action")
        print("=" * 60)
        
        try:
            print(f"  * Searching for: '{query}'...")
            
            # Fill the search input
            await self.page.fill("input[name='q']", query)
            
            print("  * Pressing Enter to submit search...")
            # Submit by pressing Enter
            await self.page.press("input[name='q']", "Enter")
            
            print("  * Waiting for results to load...")
            # Wait for search results page
            try:
                await self.page.wait_for_load_state("networkidle", timeout=60000)
            except:
                # Fallback if networkidle times out
                await self.page.wait_for_load_state("domcontentloaded")
            
            # Verify results loaded
            found_results = False
            for selector in ["div#search", "div.g", "div[data-sokoban-container]"]:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    found_results = True
                    break
                except:
                    pass
            
            # Try to get result count
            result_text = "Results loaded"
            try:
                elem = await self.page.query_selector("div#result-stats")
                if elem:
                    result_text = await elem.text_content()
            except:
                pass
            
            elapsed = time.time() - stage_start
            self.stage_times["search"] = elapsed
            
            print(f"  [PASS] Search completed in {elapsed:.2f}s")
            print(f"    - Query: {query}")
            print(f"    - Results: {result_text}")
            
        except Exception as e:
            raise RuntimeError(
                f"Search failed: {str(e)}. "
                "Page structure may have changed."
            ) from e
    
    async def capture_snapshot(self) -> Optional[str]:
        """
        Stage 4: Capture Page Snapshot
        
        Demonstrates:
        - Capturing page properties through BrowserSession
        - Creating snapshots with schema versioning
        - Persisting snapshots to disk
        
        Returns: Path to saved snapshot file
        Error handling: File I/O errors, serialization failures
        """
        stage_start = time.time()
        print("\n" + "=" * 60)
        print("STAGE 4: Capture Page Snapshot")
        print("=" * 60)
        
        try:
            print("  * Capturing page content...")
            # Get page content through Playwright
            content = await self.page.content()
            title = await self.page.title()
            url = self.page.url
            
            print("  * Building snapshot metadata...")
            # Create snapshot with schema versioning
            snapshot_data = {
                "schema_version": "1.0",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "page": {
                    "title": title,
                    "url": url,
                    "content_length": len(content)
                },
                "session": {
                    "session_id": self.session.session_id,
                    "status": self.session.status.value,
                    "browser_type": self.session.configuration.browser_type.value
                },
                "timing": {
                    "initialization_ms": int(self.stage_times.get("initialization", 0) * 1000),
                    "navigation_ms": int(self.stage_times.get("navigation", 0) * 1000),
                    "search_ms": int(self.stage_times.get("search", 0) * 1000),
                    "total_ms": int((time.time() - self.start_time) * 1000)
                }
            }
            
            # Generate timestamped filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"google_search_{timestamp}.json"
            filepath = self.snapshot_dir / filename
            
            print(f"  * Writing snapshot to {filepath}...")
            # Write snapshot to disk
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)
            
            elapsed = time.time() - stage_start
            self.stage_times["snapshot"] = elapsed
            
            print(f"  [PASS] Snapshot saved in {elapsed:.2f}s")
            print(f"    - File: {filepath.name}")
            print(f"    - Title: {title}")
            print(f"    - Size: {len(content)} bytes")
            
            return str(filepath)
            
        except PermissionError as e:
            raise RuntimeError(
                f"Permission denied writing to {self.snapshot_dir}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Snapshot capture failed: {str(e)}") from e
    
    async def cleanup(self) -> None:
        """
        Stage 5: Cleanup and Close Session
        
        Demonstrates:
        - Proper session shutdown through BrowserManager
        - Resource cleanup with error handling
        - Manager handling of session lifecycle
        
        The BrowserManager handles:
        - Page cleanup
        - Browser process termination
        - Resource monitoring cleanup
        - State persistence
        """
        print("\n" + "=" * 60)
        print("STAGE 5: Cleanup and Close Session")
        print("=" * 60)
        
        try:
            stage_start = time.time()
            
            if self.session and self.browser_manager:
                session_id = self.session.session_id
                print(f"  * Closing session {session_id[:8]}...")
                
                # Close through the browser manager
                # The manager handles:
                # - Page cleanup
                # - Browser closure
                # - Resource release
                # - Monitoring cleanup
                await self.browser_manager.close_session(session_id)
            
            elapsed = time.time() - stage_start
            self.stage_times["cleanup"] = elapsed
            
            print(f"  [PASS] Cleanup completed in {elapsed:.2f}s")
            print("    - Session closed through BrowserManager")
            print("    - All resources released")
            print("    - Browser process terminated")
            
        except Exception as e:
            print(f"  [FAIL] Cleanup error: {str(e)}")
            # Continue even if cleanup fails
        
        finally:
            # Clear references
            self.page = None
            self.session = None
    
    async def run(self) -> bool:
        """
        Execute the complete browser lifecycle example.
        
        Orchestrates all stages and handles errors gracefully.
        
        Returns: True if successful, False otherwise
        """
        print("\n" + "=" * 70)
        print("BROWSER LIFECYCLE EXAMPLE - Using BrowserManager")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.start_time = time.time()
        
        try:
            # Execute all stages
            await self.initialize_browser()
            await self.navigate_to_google()
            await self.execute_search()
            snapshot_file = await self.capture_snapshot()
            
            # Print summary
            total_time = time.time() - self.start_time
            
            print("\n" + "=" * 70)
            print("LIFECYCLE COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print(f"Total execution time: {total_time:.2f}s\n")
            print("Stage Breakdown:")
            for stage, duration in self.stage_times.items():
                stage_name = stage.replace("_", " ").title()
                print(f"  {stage_name:20} {duration:7.2f}s")
            print(f"  {'Total':20} {total_time:7.2f}s")
            
            if snapshot_file:
                print(f"\nSnapshot saved to: {snapshot_file}")
            
            print("=" * 70 + "\n")
            return True
            
        except RuntimeError as e:
            print(f"\n[FAIL] EXAMPLE FAILED: {str(e)}\n")
            return False
        except Exception as e:
            print(f"\n[FAIL] ERROR: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()


async def main():
    """Entry point for the example."""
    example = BrowserLifecycleExample(
        snapshot_dir="data/snapshots",
        headless=True,  # Set to False to see the browser
        timeout_ms=30000
    )
    
    success = await example.run()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
