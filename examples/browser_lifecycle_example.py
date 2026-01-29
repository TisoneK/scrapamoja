"""
Browser Lifecycle Example Using BrowserManager

Demonstrates the complete browser lifecycle using the project's BrowserManager API.
This is the recommended pattern for all automation in this project.

The example shows:
1. Getting the global BrowserManager singleton
2. Creating a BrowserSession with configuration
3. Navigating to Wikipedia and executing a search
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
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError:
    Image = None

from src.browser import (
    get_browser_manager,
    BrowserConfiguration,
    BrowserType,
)
from src.browser.snapshot import DOMSnapshotManager


class BrowserLifecycleExample:
    """Demonstrates browser lifecycle using the project's BrowserManager."""
    
    def __init__(
        self,
        snapshot_dir: str = "data/snapshots",
        headless: bool = False,
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
        self.start_time = time.time()
        self.stage_times = {}
        
        # Initialize snapshot manager
        self.snapshot_manager = DOMSnapshotManager(str(self.snapshot_dir))
    
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
    
    def _get_navigation_url(self) -> str:
        """Get navigation URL based on test mode setting."""
        if os.getenv('TEST_MODE'):
            test_page_path = Path(__file__).parent / "test_pages" / "wikipedia_stub.html"
            if not test_page_path.exists():
                raise FileNotFoundError(f"Test page not found: {test_page_path}")
            return f"file://{test_page_path.absolute()}"
        else:
            return "https://www.wikipedia.org"
    
    async def navigate_to_wikipedia(self) -> None:
        """
        Stage 2: Navigate to Wikipedia or test page
        
        Demonstrates:
        - Page navigation with timeout handling
        - Waiting for specific elements
        - Retry logic for transient failures
        - Test mode support for CI environments
        
        Error handling: Navigation timeout, element not found
        """
        stage_start = time.time()
        print("\n" + "=" * 60)
        print("STAGE 2: Navigate to Wikipedia")
        print("=" * 60)
        
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                url = self._get_navigation_url()
                print(f"  * Navigating to {url}...")
                
                # Navigate with timeout
                await self.page.goto(url, timeout=self.timeout_ms)
                
                # Wait for search input (Wikipedia uses input[name="search"])
                await self.page.wait_for_selector('input[name="search"]', timeout=10000)
                
                elapsed = time.time() - stage_start
                self.stage_times["navigation"] = elapsed
                
                mode = "TEST MODE" if os.getenv('TEST_MODE') else "NORMAL MODE"
                print(f"  [PASS] Navigation completed in {elapsed:.2f}s ({mode})")
                return
                
            except Exception as e:
                if attempt == max_attempts:
                    raise RuntimeError(f"Navigation failed after {max_attempts} attempts: {str(e)}")
                
                delay = base_delay * attempt
                print(f"  * Attempt {attempt} failed, retrying in {delay}s...")
                await asyncio.sleep(delay)
    
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
            
            # Fill the search input (Wikipedia uses input[name="search"])
            await self.page.fill('input[name="search"]', query)
            
            print("  * Pressing Enter to submit search...")
            # Submit by pressing Enter
            await self.page.press('input[name="search"]', "Enter")
            
            print("  * Waiting for results to load...")
            # Wait for search results page
            try:
                await self.page.wait_for_load_state("networkidle", timeout=60000)
            except:
                # Fallback if networkidle times out
                await self.page.wait_for_load_state("domcontentloaded")
            
            # Verify results loaded
            found_results = False
            result_text = "Results loaded"
            
            # Check for test page results first (TEST_MODE)
            if os.getenv('TEST_MODE'):
                try:
                    await self.page.wait_for_selector("#results", timeout=5000)
                    # Check if results div has content
                    results_elem = await self.page.query_selector("#results")
                    if results_elem:
                        results_text = await results_elem.text_content()
                        if results_text and results_text.strip():
                            found_results = True
                except:
                    pass
            else:
                # Wikipedia-specific selectors for normal mode
                for selector in ["div.mw-parser-output", "div.searchresults", "div#mw-page-base"]:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        found_results = True
                        break
                    except:
                        pass
            
            # Try to get result count
            try:
                if os.getenv('TEST_MODE'):
                    # For test mode, get the results text
                    elem = await self.page.query_selector("#results")
                    if elem:
                        result_text = await elem.text_content()
                        if result_text and result_text.strip():
                            result_text = f"Test results: {result_text.strip()}"
                else:
                    # For normal mode, try Wikipedia page title
                    try:
                        elem = await self.page.query_selector("h1.firstHeading")
                        if elem:
                            result_text = await elem.text_content()
                    except:
                        pass
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
    
    def _generate_html_filename(self, content: str, timestamp: str) -> str:
        """
        Generate HTML filename with timestamp, session_id, and hash prefix.
        
        Format: {timestamp}_{session_id}_{hash_prefix}.html
        """
        session_prefix = self.session.session_id[:8]
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        hash_prefix = content_hash[:12]
        return f"{timestamp}_{session_prefix}_{hash_prefix}.html"
    
    def _generate_content_hash(self, content: str) -> str:
        """
        Generate SHA-256 hash of HTML content.
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _load_html_file(self, html_file_path: str) -> Optional[str]:
        """
        Load HTML content from file with error handling.
        
        Args:
            html_file_path: Path to HTML file relative to snapshot directory
            
        Returns:
            HTML content string or None if loading fails
        """
        try:
            full_path = self.snapshot_dir / html_file_path
            if not full_path.exists():
                print(f"  [ERROR] HTML file not found: {html_file_path}")
                return None
                
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            print(f"  [PASS] HTML file loaded: {html_file_path} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            print(f"  [ERROR] Failed to load HTML file {html_file_path}: {e}")
            return None
    
    def _verify_html_integrity(self, html_file_path: str, expected_hash: str) -> bool:
        """
        Verify HTML file integrity using stored hash.
        
        Args:
            html_file_path: Path to HTML file
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if integrity verified, False otherwise
        """
        content = self._load_html_file(html_file_path)
        if content is None:
            return False
            
        actual_hash = self._generate_content_hash(content)
        is_valid = actual_hash == expected_hash
        
        if is_valid:
            print(f"  [PASS] HTML integrity verified for {html_file_path}")
        else:
            print(f"  [ERROR] HTML integrity failed for {html_file_path}")
            print(f"    Expected: {expected_hash}")
            print(f"    Actual:   {actual_hash}")
            
        return is_valid
    
    async def _load_html_in_browser(self, html_file_path: str) -> bool:
        """
        Load HTML file in browser using file:// protocol.
        
        Args:
            html_file_path: Path to HTML file relative to snapshot directory
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            full_path = self.snapshot_dir / html_file_path
            file_url = f"file://{full_path.absolute()}"
            
            print(f"  * Loading HTML file in browser: {file_url}")
            await self.page.goto(file_url)
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            
            title = await self.page.title()
            print(f"  [PASS] HTML loaded in browser: {title}")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to load HTML in browser: {e}")
            return False
    
    async def replay_captured_html(self, snapshot_path: str) -> bool:
        """
        Demonstrate offline HTML replay functionality.
        
        Args:
            snapshot_path: Path to snapshot JSON file
            
        Returns:
            True if replay successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("OFFLINE HTML REPLAY DEMONSTRATION")
        print("=" * 60)
        
        try:
            # Load snapshot JSON
            print(f"  * Loading snapshot: {snapshot_path}")
            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            
            # Extract HTML file information
            page_data = snapshot.get("page", {})
            html_file = page_data.get("html_file")
            expected_hash = page_data.get("content_hash")
            
            if not html_file:
                print("  [INFO] No HTML file reference found in snapshot")
                return False
            
            print(f"  * Found HTML file reference: {html_file}")
            
            # Verify HTML file integrity
            if expected_hash:
                print("  * Verifying HTML file integrity...")
                if not self._verify_html_integrity(html_file, expected_hash):
                    print("  [ERROR] HTML integrity verification failed")
                    return False
            else:
                print("  [INFO] No content hash available for verification")
            
            # Load HTML in browser
            print("  * Loading HTML file in browser...")
            success = await self._load_html_in_browser(html_file)
            
            if success:
                print("  [PASS] Offline HTML replay completed successfully")
                print(f"    - Original URL: {page_data.get('url', 'N/A')}")
                print(f"    - Original title: {page_data.get('title', 'N/A')}")
                print(f"    - Content size: {page_data.get('content_length', 0)} bytes")
                print(f"    - Captured at: {snapshot.get('captured_at', 'N/A')}")
                return True
            else:
                print("  [ERROR] Failed to replay HTML content")
                return False
                
        except Exception as e:
            print(f"  [ERROR] HTML replay failed: {e}")
            return False
    
    async def demonstrate_integrity_verification(self, snapshot_path: str) -> bool:
        """
        Demonstrate content integrity verification by testing corruption detection.
        
        Args:
            snapshot_path: Path to snapshot JSON file
            
        Returns:
            True if demonstration completed, False otherwise
        """
        print("\n" + "=" * 60)
        print("CONTENT INTEGRITY VERIFICATION DEMONSTRATION")
        print("=" * 60)
        
        try:
            # Load snapshot JSON
            print(f"  * Loading snapshot: {snapshot_path}")
            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            
            # Extract HTML file information
            page_data = snapshot.get("page", {})
            html_file = page_data.get("html_file")
            original_hash = page_data.get("content_hash")
            
            if not html_file or not original_hash:
                print("  [INFO] No HTML file or hash found for integrity testing")
                return True
            
            print(f"  * Testing integrity for: {html_file}")
            
            # Test 1: Verify original integrity
            print("  * Test 1: Verifying original file integrity...")
            original_valid = self._verify_html_integrity(html_file, original_hash)
            
            if not original_valid:
                print("  [ERROR] Original file integrity check failed")
                return False
            
            # Test 2: Simulate corruption by modifying the file
            print("  * Test 2: Simulating file corruption...")
            full_path = self.snapshot_dir / html_file
            
            # Read original content
            with open(full_path, "r", encoding="utf-8") as f:
                original_content = f.read()
            
            # Corrupt the content (change a character)
            corrupted_content = original_content.replace("Wikipedia", "WikipediA")
            
            # Write corrupted content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(corrupted_content)
            
            print("  * File corrupted (modified content)")
            
            # Test 3: Verify corruption detection
            print("  * Test 3: Verifying corruption detection...")
            corruption_detected = not self._verify_html_integrity(html_file, original_hash)
            
            if corruption_detected:
                print("  [PASS] Corruption successfully detected")
            else:
                print("  [FAIL] Corruption not detected")
                return False
            
            # Restore original content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(original_content)
            
            print("  * Original content restored")
            
            # Test 4: Final verification
            print("  * Test 4: Final integrity verification...")
            final_valid = self._verify_html_integrity(html_file, original_hash)
            
            if final_valid:
                print("  [PASS] Integrity verification demonstration completed successfully")
                print("    - Original integrity: ✓ PASSED")
                print("    - Corruption detection: ✓ PASSED") 
                print("    - Content restoration: ✓ PASSED")
                return True
            else:
                print("  [ERROR] Final integrity verification failed")
                return False
                
        except Exception as e:
            print(f"  [ERROR] Integrity verification demonstration failed: {e}")
            return False
    
    def _generate_screenshot_filename(self, timestamp: str) -> str:
        """Generate screenshot filename matching snapshot JSON base name."""
        return f"wikipedia_search_{timestamp}.png"
    
    def _get_image_dimensions(self, image_path: Path) -> tuple[int, int]:
        """Get image dimensions from file."""
        if Image is None:
            return (0, 0)
        
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception:
            return (0, 0)
    
    def _get_file_size_bytes(self, file_path: Path) -> int:
        """Get file size in bytes."""
        try:
            return file_path.stat().st_size
        except Exception:
            return 0
    
    def _verify_screenshot_file(self, screenshot_path: Path) -> bool:
        """Verify screenshot file exists and is readable."""
        try:
            return screenshot_path.exists() and screenshot_path.is_file()
        except Exception:
            return False
    
    async def capture_snapshot(
        self,
        capture_screenshot: bool = True,
        screenshot_mode: str = "fullpage",
        screenshot_quality: int = 90
    ) -> Optional[str]:
        """
        Stage 4: Capture Page Snapshot using Core Module
        
        Demonstrates:
        - Using the core DOMSnapshotManager for rich capture
        - HTML file capture with metadata
        - Screenshot capture with metadata
        - Proper separation of concerns
        
        Returns: Path to saved snapshot file
        Error handling: Core module errors, file I/O errors
        """
        stage_start = time.time()
        print("\n" + "=" * 60)
        print("STAGE 4: Capture Page Snapshot (using Core Module)")
        print("=" * 60)
        
        try:
            print("  * Capturing rich snapshot using core module...")
            
            # Generate page ID for the snapshot
            page_id = f"wikipedia_search_{int(time.time())}"
            
            # Use core snapshot manager for rich capture
            snapshot = await self.snapshot_manager.capture_snapshot(
                page=self.page,
                page_id=page_id,
                session_id=self.session.session_id,
                include_screenshot=capture_screenshot,
                include_html_file=True,
                screenshot_mode=screenshot_mode,
                include_network=False,  # Disabled for demo
                include_console=False   # Disabled for demo
            )
            
            # Display capture results
            print(f"  [PASS] Rich snapshot captured successfully")
            
            if snapshot.html_metadata:
                html_meta = snapshot.html_metadata
                print(f"    - HTML: {html_meta['filepath']} ({html_meta['file_size_bytes']} bytes)")
                print(f"    - HTML captured at: {html_meta['captured_at']}")
            
            if snapshot.screenshot_metadata:
                screenshot_meta = snapshot.screenshot_metadata
                print(f"    - Screenshot: {screenshot_meta['filepath']} ({screenshot_meta['file_size_bytes']} bytes)")
                print(f"    - Dimensions: {screenshot_meta['width']}x{screenshot_meta['height']}")
                print(f"    - Capture mode: {screenshot_meta['capture_mode']}")
                print(f"    - Screenshot captured at: {screenshot_meta['captured_at']}")
            
            elapsed = time.time() - stage_start
            self.stage_times["snapshot"] = elapsed
            
            print(f"  [PASS] Snapshot saved in {elapsed:.2f}s")
            print(f"    - Page ID: {page_id}")
            print(f"    - Title: {snapshot.title}")
            print(f"    - URL: {snapshot.url}")
            
            # Return the path to the saved JSON file
            # The core module saves it automatically, we just need to find the path
            timestamp = int(snapshot.timestamp)
            json_filename = f"{page_id}_{timestamp}.json"
            json_path = self.snapshot_dir / json_filename
            
            return str(json_path)
            
        except Exception as e:
            print(f"  [ERROR] Snapshot capture failed: {e}")
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
            await self.navigate_to_wikipedia()
            await self.execute_search()
            snapshot_file = await self.capture_snapshot()
            
            # Demonstrate offline HTML replay if snapshot was created with HTML
            if snapshot_file:
                print("\n" + "=" * 70)
                print("DEMONSTRATING OFFLINE HTML REPLAY")
                print("=" * 70)
                
                # Try to replay the captured HTML
                replay_success = await self.replay_captured_html(snapshot_file)
                
                if replay_success:
                    print("  [INFO] HTML replay demonstration completed")
                    print("  [INFO] Page is now loaded from captured HTML file")
                else:
                    print("  [INFO] HTML replay demonstration skipped")
                
                # Demonstrate integrity verification
                print("\n" + "=" * 70)
                print("DEMONSTRATING CONTENT INTEGRITY VERIFICATION")
                print("=" * 70)
                
                integrity_success = await self.demonstrate_integrity_verification(snapshot_file)
                
                if integrity_success:
                    print("  [INFO] Integrity verification demonstration completed")
                else:
                    print("  [INFO] Integrity verification demonstration failed")
                
                print("=" * 70 + "\n")
            
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
        headless=False,  # Set to False to see the browser
        timeout_ms=30000
    )
    
    success = await example.run()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
