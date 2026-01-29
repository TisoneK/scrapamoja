"""
Browser Manager Lifecycle Example

This example demonstrates the complete browser manager lifecycle from initialization
through shutdown, including navigation, action execution, and snapshot capture.

It serves as both a learning resource for new developers and a practical reference
for common browser automation patterns.

Lifecycle Stages:
1. Initialization: Create browser session with default configuration
2. Navigation: Navigate to target URL and wait for page load
3. Action Execution: Interact with page elements (search form)
4. Snapshot Capture: Save page state for analysis or reference
5. Cleanup: Gracefully close browser and release resources

The example includes comprehensive error handling for common failure scenarios
and informative console output tracking progress through each stage.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError as e:
    raise ImportError(
        "Playwright is required for this example. "
        "Install it with: pip install playwright && playwright install"
    ) from e


class BrowserLifecycleExample:
    """Demonstrates complete browser manager lifecycle."""
    
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
            timeout_ms: Timeout for navigation and actions (milliseconds)
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.timeout_ms = timeout_ms
        
        # State tracking
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.start_time = None
        self.stage_times = {}
    
    async def initialize_browser(self) -> None:
        """
        Stage 1: Initialize Browser
        
        Creates a new browser instance with sensible defaults.
        This stage validates that the browser can be launched and basic
        configuration is applied correctly.
        
        Error handling: Network errors or playwright installation issues
        """
        stage_start = time.time()
        print("\n" + "=" * 50)
        print("STAGE 1: Initializing Browser")
        print("=" * 50)
        
        try:
            print("  • Starting Playwright instance...")
            # Create playwright instance with context manager support
            self.playwright = await async_playwright().start()
            
            print("  • Launching browser with default configuration...")
            # Launch browser with headless mode and basic stealth configuration
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                # Basic anti-detection: disable blink features that expose automation
                args=[
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            print("  • Creating browser context...")
            # Create context for tab isolation and state management
            self.context = await self.browser.new_context(
                # User agent to appear more human-like
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                # Disable images to speed up loading (optional)
                # extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )
            
            print("  • Creating new page...")
            # Create page for interaction
            self.page = await self.context.new_page()
            
            # Set default navigation timeout
            self.page.set_default_navigation_timeout(self.timeout_ms)
            self.page.set_default_timeout(self.timeout_ms)
            
            elapsed = time.time() - stage_start
            self.stage_times["initialization"] = elapsed
            
            print(f"  ✓ Browser initialized successfully in {elapsed:.2f}s")
            print(f"    - Browser type: Chromium (headless={self.headless})")
            print(f"    - Page context created and ready for navigation")
            
        except PlaywrightTimeoutError as e:
            raise RuntimeError(
                f"Browser initialization timeout after {self.timeout_ms}ms. "
                "Check system resources and network connectivity."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Browser initialization failed: {str(e)}. "
                "Ensure Playwright is installed: playwright install"
            ) from e
    
    async def navigate_to_google(self) -> None:
        """
        Stage 2: Navigate to Google Homepage
        
        Navigates to Google's homepage and waits for the page to load.
        This stage validates that the browser can access external sites
        and that basic navigation and page readiness detection works.
        
        Error handling: Network errors, timeout, page load failures
        """
        stage_start = time.time()
        print("\n" + "=" * 50)
        print("STAGE 2: Navigating to Google")
        print("=" * 50)
        
        try:
            print("  • Navigating to https://www.google.com...")
            # Navigate with networkidle wait condition to ensure page is fully loaded
            await self.page.goto(
                "https://www.google.com",
                wait_until="networkidle"  # Wait for network activity to settle
            )
            
            print("  • Waiting for page elements to be available...")
            # Wait for search input to be visible and interactive
            await self.page.wait_for_selector(
                "input[name='q']",  # Google's search input selector
                timeout=self.timeout_ms
            )
            
            # Get page title and URL for verification
            title = await self.page.title()
            url = self.page.url
            
            elapsed = time.time() - stage_start
            self.stage_times["navigation"] = elapsed
            
            print(f"  ✓ Google homepage loaded successfully in {elapsed:.2f}s")
            print(f"    - Page title: {title}")
            print(f"    - Current URL: {url}")
            print(f"    - Search input element found and interactive")
            
        except PlaywrightTimeoutError:
            raise RuntimeError(
                f"Navigation timeout after {self.timeout_ms}ms. "
                "Google may be inaccessible or page load is slow. "
                "Check network connectivity."
            )
        except Exception as e:
            raise RuntimeError(
                f"Navigation to Google failed: {str(e)}. "
                "Google may be inaccessible from your location/network."
            )
    
    async def execute_search(self, query: str = "Playwright browser automation") -> None:
        """
        Stage 3: Execute Search Action
        
        Submits a search query through Google's search form and waits for
        results to load. This stage validates that the browser can interact
        with page elements (fill inputs, submit forms) and detect page changes.
        
        Error handling: Element not found, action timeouts, navigation failures
        """
        stage_start = time.time()
        print("\n" + "=" * 50)
        print("STAGE 3: Executing Search Action")
        print("=" * 50)
        
        try:
            print(f"  • Filling search input with query: '{query}'...")
            # Fill the search input field with our query
            # This simulates human typing through Playwright's input simulation
            await self.page.fill("input[name='q']", query)
            
            print("  • Submitting search form...")
            # Submit the form by pressing Enter
            # This simulates human behavior more realistically than click submit
            await self.page.press("input[name='q']", "Enter")
            
            print("  • Waiting for search results to load...")
            # Wait for navigation to complete - use longer timeout for search
            try:
                await self.page.wait_for_load_state("networkidle", timeout=60000)
            except:
                # If networkidle times out, try domcontentloaded instead
                await self.page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
            
            # Wait for results container to be visible (may be div#search or other selectors)
            # Try multiple selectors as Google's structure can vary
            selectors = [
                "div#search",  # Standard results container
                "div.g",       # Individual result item (fallback)
                "div[data-sokoban-container]"  # Alternative structure
            ]
            
            result_found = False
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    result_found = True
                    break
                except:
                    continue
            
            if not result_found:
                print("  • Warning: Could not find standard results selectors, continuing...")
            
            # Get result count estimate
            results_text = ""
            try:
                # Try to get "About X results" text
                results_element = await self.page.query_selector(
                    "div#result-stats"
                )
                if results_element:
                    results_text = await results_element.text_content()
            except:
                results_text = "Results loaded (count not available)"
            
            elapsed = time.time() - stage_start
            self.stage_times["search"] = elapsed
            
            print(f"  ✓ Search executed successfully in {elapsed:.2f}s")
            print(f"    - Search query: {query}")
            print(f"    - Results: {results_text}")
            print(f"    - Results page loaded and ready for snapshot")
            
        except PlaywrightTimeoutError:
            raise RuntimeError(
                f"Search execution timeout. "
                "Results may not have loaded within the expected time. "
                "This can happen if Google blocks automated requests."
            )
        except Exception as e:
            raise RuntimeError(
                f"Search execution failed: {str(e)}. "
                "Page structure may have changed or element not found."
            )
    
    async def capture_snapshot(self) -> Optional[str]:
        """
        Stage 4: Capture Page Snapshot
        
        Captures the current page state and saves it as a JSON snapshot.
        This stage demonstrates snapshot capture for later analysis,
        debugging, or archival purposes.
        
        Returns: Path to the saved snapshot file
        Error handling: Write permission errors, serialization failures
        """
        stage_start = time.time()
        print("\n" + "=" * 50)
        print("STAGE 4: Capturing Page Snapshot")
        print("=" * 50)
        
        try:
            print("  • Capturing page content...")
            # Get page HTML content
            content = await self.page.content()
            
            print("  • Capturing page metadata...")
            # Get page metadata
            title = await self.page.title()
            url = self.page.url
            
            # Create snapshot object with metadata
            snapshot_data = {
                "schema_version": "1.0",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "page": {
                    "title": title,
                    "url": url,
                    "content_length": len(content)
                },
                "metadata": {
                    "capture_duration_ms": int((time.time() - stage_start) * 1000),
                    "stage_times": self.stage_times,
                    "total_time_ms": int((time.time() - self.start_time) * 1000)
                }
            }
            
            # Generate snapshot filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snapshot_filename = f"google_search_{timestamp}.json"
            snapshot_path = self.snapshot_dir / snapshot_filename
            
            print(f"  • Writing snapshot to {snapshot_path}...")
            # Save snapshot metadata (content is too large to include directly)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)
            
            elapsed = time.time() - stage_start
            self.stage_times["snapshot"] = elapsed
            
            print(f"  ✓ Snapshot captured and saved in {elapsed:.2f}s")
            print(f"    - File: {snapshot_path}")
            print(f"    - Page title: {title}")
            print(f"    - Content size: {len(content)} bytes")
            print(f"    - Metadata: {json.dumps(snapshot_data['metadata'], indent=6)}")
            
            return str(snapshot_path)
            
        except PermissionError as e:
            print(f"  ✗ Permission error writing snapshot: {str(e)}")
            raise RuntimeError(
                f"Cannot write snapshot to {self.snapshot_dir}. "
                "Check directory permissions: chmod u+w {self.snapshot_dir}"
            ) from e
        except Exception as e:
            print(f"  ✗ Snapshot capture failed: {str(e)}")
            raise RuntimeError(
                f"Snapshot capture failed: {str(e)}"
            ) from e
    
    async def cleanup(self) -> None:
        """
        Stage 5: Cleanup and Shutdown
        
        Gracefully closes the browser and releases all resources.
        This stage ensures proper resource cleanup even if errors occurred
        in previous stages. Uses try/finally pattern for robustness.
        """
        stage_start = time.time()
        print("\n" + "=" * 50)
        print("STAGE 5: Cleaning Up")
        print("=" * 50)
        
        try:
            if self.page:
                print("  • Closing page...")
                await self.page.close()
            
            if self.context:
                print("  • Closing context...")
                await self.context.close()
            
            if self.browser:
                print("  • Closing browser...")
                await self.browser.close()
            
            if self.playwright:
                print("  • Stopping Playwright...")
                await self.playwright.stop()
            
            elapsed = time.time() - stage_start
            self.stage_times["cleanup"] = elapsed
            
            print(f"  ✓ Cleanup completed in {elapsed:.2f}s")
            print("    - All resources released")
            print("    - Browser process terminated")
            
        except Exception as e:
            print(f"  ✗ Error during cleanup: {str(e)}")
            # Don't raise - cleanup should not fail the entire example
    
    async def run(self) -> None:
        """
        Execute the complete browser lifecycle example.
        
        Orchestrates all stages: initialization, navigation, search,
        snapshot capture, and cleanup. Handles errors gracefully with
        informative messages.
        """
        print("\n" + "=" * 60)
        print("BROWSER LIFECYCLE EXAMPLE")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.start_time = time.time()
        snapshot_path = None
        
        try:
            # Stage 1: Initialize
            await self.initialize_browser()
            
            # Stage 2: Navigate
            await self.navigate_to_google()
            
            # Stage 3: Execute action
            await self.execute_search()
            
            # Stage 4: Capture snapshot
            snapshot_path = await self.capture_snapshot()
            
        except RuntimeError as e:
            # Runtime errors with helpful messages
            print(f"\n✗ EXAMPLE FAILED: {str(e)}")
            return False
        except Exception as e:
            # Unexpected errors
            print(f"\n✗ UNEXPECTED ERROR: {str(e)}")
            return False
        finally:
            # Stage 5: Always cleanup
            await self.cleanup()
        
        # Print summary
        total_time = time.time() - self.start_time
        print("\n" + "=" * 60)
        print("EXAMPLE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Total execution time: {total_time:.2f}s")
        print(f"\nStage timings:")
        for stage, duration in self.stage_times.items():
            print(f"  {stage:15} {duration:6.2f}s")
        print(f"  {'total':15} {total_time:6.2f}s")
        
        if snapshot_path:
            print(f"\nSnapshot saved to: {snapshot_path}")
        
        print("=" * 60 + "\n")
        return True


async def main():
    """
    Main entry point for the example.
    
    Creates an example instance and runs the complete lifecycle.
    """
    # Create example instance with default configuration
    example = BrowserLifecycleExample(
        snapshot_dir="data/snapshots",
        headless=True,  # Set to False to see the browser
        timeout_ms=30000  # 30 seconds
    )
    
    # Run the complete lifecycle
    success = await example.run()
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    """
    Run the example as a standalone script.
    
    Usage:
        python examples/browser_lifecycle_example.py
    """
    asyncio.run(main())
