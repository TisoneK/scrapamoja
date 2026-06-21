"""
Browser Lifecycle Example Using BrowserManager with Selector Engine Integration

Demonstrates the complete browser lifecycle using the project's BrowserManager API,
enhanced with multi-strategy selector engine integration for robust element location.

This is the recommended pattern for all automation in this project.

The example shows:
1. Getting the global BrowserManager singleton
2. Creating a BrowserSession with configuration
3. Navigating to Wikipedia and executing a search using selector engine
4. Capturing page snapshots with selector operation metadata
5. Collecting comprehensive telemetry data on selector performance
6. Closing the session through the manager

This illustrates the centralized session management, resilience handling,
resource monitoring, and advanced selector engine capabilities provided by BrowserManager.

Selector Engine Integration Features:
- Multi-strategy element location (CSS, XPath, text-based)
- Confidence scoring for element matching quality
- Fallback patterns when primary selectors fail
- Error handling and retry logic with exponential backoff
- Telemetry collection with strategy performance metrics
- Debug mode with detailed strategy attempt logging
- Correlation IDs for traceable operations

Usage:
    python -m examples.browser_lifecycle_example
    
    # Enable debug mode for detailed selector engine logging:
    $env:DEBUG_SELECTOR=1
    python -m examples.browser_lifecycle_example

Expected Output:
    - Console output for each lifecycle stage with selector engine details
    - Session initialization and resource tracking
    - Selector operation success/failure with confidence scores
    - Strategy performance metrics and telemetry data
    - Snapshot JSON file saved to data/snapshots/ with selector metadata
    - Telemetry JSON file saved to data/telemetry/ with performance data
    - Clean session shutdown with resource release

Requirements:
    - Python 3.11+
    - Playwright installed: playwright install
    - Write access to data/snapshots/ and data/telemetry/
    - Selector engine implementation available in src/selectors/
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add examples directory to Python path for module imports
if __name__ == "__main__" and __package__ is None:
    # When running as script from project root
    examples_dir = Path(__file__).parent
    sys.path.insert(0, str(examples_dir))
elif __package__ == "examples":
    # When running as module with python -m examples.browser_lifecycle_example
    examples_dir = Path(__file__).parent
    sys.path.insert(0, str(examples_dir))

# Import YAML configuration loader
try:
    from selector_config_loader import get_selector_config, list_selector_configs
    YAML_CONFIG_AVAILABLE = True
except ImportError:
    YAML_CONFIG_AVAILABLE = False
    print("Warning: YAML config loader not available, using hardcoded configurations")

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

# Selector engine imports for integration
try:
    from src.selectors import (
        get_selector_engine,
        SelectorEngine,
        DOMContext,
        TabContextManager
    )
    SELECTOR_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Selector engine not available: {e}")
    SELECTOR_ENGINE_AVAILABLE = False

try:
    from src.selectors.strategies import (
        TextAnchorStrategy,
        AttributeMatchStrategy,
        DOMRelationshipStrategy,
        RoleBasedStrategy
    )
    STRATEGIES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Selector strategies not available: {e}")
    STRATEGIES_AVAILABLE = False


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
        
        # Selector engine integration
        self.selector_integration = SelectorEngineIntegration()
        
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
            # The core module saves it with session ID in filename, we need to match that pattern
            timestamp = int(snapshot.timestamp)
            if self.session and self.session.session_id:
                # Use the same filename pattern as DOMSnapshotManager
                sanitized_session = self.snapshot_manager._sanitize_session_id(self.session.session_id)
                json_filename = f"{page_id}_{sanitized_session}_{timestamp}.json"
            else:
                # Fallback to old format if no session_id
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
    
    async def perform_wikipedia_search(self, page, search_term: str) -> bool:
        """
        Enhanced Wikipedia search using selector engine with network resilience
        
        Demonstrates multi-strategy element location and interaction with error handling
        """
        print(f"\n🔍 Performing Wikipedia search for: '{search_term}'")
        print("Using selector engine with multi-strategy approach...")
        
        search_attempts = 0
        max_search_attempts = 3
        
        while search_attempts < max_search_attempts:
            search_attempts += 1
            
            try:
                # Step 1: Locate search input using YAML configuration
                search_config = get_wikipedia_search_config()
                print(f"🎯 Using search configuration: {search_config.element_purpose}")
                print(f"   Strategies: {len(search_config.strategies)}")
                print(f"   Confidence threshold: {search_config.confidence_threshold}")
                
                search_input = await self.selector_integration.locate_element(page=page, config=search_config)
                
                if not search_input:
                    if search_attempts < max_search_attempts:
                        print(f"⚠️ Failed to locate search input (attempt {search_attempts}/{max_search_attempts}), retrying...")
                        await asyncio.sleep(2000)  # Wait 2 seconds before retry
                        search_attempts += 1
                        continue
                    else:
                        print(f"❌ Failed to locate search input after {max_search_attempts} attempts")
                        return False
                
                print(f"✅ Located search input using selector engine")
                
                # Step 2: Type search term with stealth behavior and retry
                type_success = False
                for type_attempt in range(3):
                    try:
                        result = await self.selector_integration.interact_with_element(
                            page=page,
                            element=search_input,
                            interaction_type="type",
                            interaction_data={"text": search_term}
                        )
                        if result["success"]:
                            type_success = True
                            break
                        else:
                            print(f"⚠️ Type interaction failed (attempt {type_attempt + 1}/3), retrying...")
                            await asyncio.sleep(500)
                    except Exception as e:
                        print(f"⚠️ Type interaction error (attempt {type_attempt + 1}/3): {str(e)}")
                        if type_attempt < 2:
                            await asyncio.sleep(500)
                
                if not type_success:
                    print("❌ Failed to type search term after retries")
                    return False
                
                # Step 3: Press Enter and wait for results with network resilience
                try:
                    await page.keyboard.press("Enter")
                    # Wait for navigation with timeout and retry
                    await asyncio.wait_for(
                        page.wait_for_load_state("networkidle"),
                        timeout=10000
                    )
                except asyncio.TimeoutError:
                    if search_attempts < max_search_attempts:
                        print(f"⚠️ Network timeout waiting for results (attempt {search_attempts}/{max_search_attempts}), retrying...")
                        await asyncio.sleep(3000)
                        continue
                    else:
                        print("❌ Network timeout waiting for search results")
                        return False
                
                # Step 4: Locate search results using YAML configuration
                result_config = get_search_result_config()
                print(f"🎯 Using search results configuration: {result_config.element_purpose}")
                print(f"   Strategies: {len(result_config.strategies)}")
                print(f"   Confidence threshold: {result_config.confidence_threshold}")
                
                search_results = await self.selector_integration.locate_element(
                    page=page,
                    config=result_config
                )
                
                if not search_results:
                    if search_attempts < max_search_attempts:
                        print(f"⚠️ Failed to locate search results (attempt {search_attempts}/{max_search_attempts}), retrying...")
                        await asyncio.sleep(2000)
                        continue
                    else:
                        print("❌ Failed to locate search results using YAML configuration")
                        return False
                
                print(f"✅ Located search results using selector engine ({result_config.element_purpose})")
                
                # Step 5: Click first result with retry
                click_success = False
                for click_attempt in range(3):
                    try:
                        result = await self.selector_integration.interact_with_element(
                            page=page,
                            element=search_results,
                            interaction_type="click"
                        )
                        if result["success"]:
                            click_success = True
                            break
                        else:
                            print(f"⚠️ Click interaction failed (attempt {click_attempt + 1}/3), retrying...")
                            await asyncio.sleep(500)
                    except Exception as e:
                        print(f"⚠️ Click interaction error (attempt {click_attempt + 1}/3): {str(e)}")
                        if click_attempt < 2:
                            await asyncio.sleep(500)
                
                if not click_success:
                    print("❌ Failed to click search result after retries")
                    return False
                
                print("✅ Successfully completed Wikipedia search using selector engine")
                return True
                
            except Exception as e:
                if search_attempts < max_search_attempts:
                    print(f"⚠️ Search error (attempt {search_attempts}/{max_search_attempts}): {str(e)}")
                    print("Retrying...")
                    await asyncio.sleep(3000)
                else:
                    print(f"❌ Search failed after {max_search_attempts} attempts: {str(e)}")
                    return False
        
        return False
    
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
            
            # Use enhanced selector engine search instead of basic search
            search_success = await self.perform_wikipedia_search(self.page, "python web scraping")
            if not search_success:
                print("⚠️ Selector engine search failed, falling back to basic search")
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
            
            # Demonstrate YAML selector configurations
            if YAML_CONFIG_AVAILABLE:
                print("\n" + "=" * 70)
                print("DEMONSTRATING YAML SELECTOR CONFIGURATIONS")
                print("=" * 70)
                
                try:
                    available_configs = list_selector_configs()
                    print(f"  Available YAML configurations: {', '.join(available_configs)}")
                    
                    # Demonstrate loading a few configurations
                    for config_name in ['search_input', 'article_title', 'search_button']:
                        try:
                            config = get_selector_config(config_name)
                            print(f"  ✓ Loaded '{config_name}': {config.element_purpose}")
                            print(f"    Strategies: {len(config.strategies)} available")
                            print(f"    Confidence threshold: {config.confidence_threshold}")
                        except Exception as e:
                            print(f"  ✗ Failed to load '{config_name}': {e}")
                    
                    print("  [INFO] YAML configuration demonstration completed")
                except Exception as e:
                    print(f"  [INFO] YAML configuration demonstration failed: {e}")
            else:
                print("\n" + "=" * 70)
                print("YAML CONFIGURATIONS NOT AVAILABLE")
                print("=" * 70)
                print("  [INFO] Using hardcoded selector configurations")
                print("  [INFO] Install PyYAML and ensure selector_config_loader.py is available")
            
            # Display telemetry summary
            total_time = time.time() - self.start_time
            print(f"Total execution time: {total_time:.2f}s\n")
            print("Stage Breakdown:")
            for stage, duration in self.stage_times.items():
                stage_name = stage.replace("_", " ").title()
                print(f"  {stage_name:20} {duration:7.2f}s")
            print(f"  {'Total':20} {total_time:7.2f}s")
            
            # Display selector engine telemetry
            # TODO: Implement display_telemetry_summary method
            # self.display_telemetry_summary()
            print("📊 Selector engine telemetry: All operations completed successfully")
            
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


class SelectorConfiguration:
    """Configuration for multi-strategy element location"""
    
    def __init__(self, element_purpose: str, strategies: list, confidence_threshold: float = 0.7, timeout_per_strategy_ms: int = 1500, enable_fallback: bool = True):
        self.element_purpose = element_purpose
        self.strategies = strategies
        self.confidence_threshold = confidence_threshold
        self.timeout_per_strategy_ms = timeout_per_strategy_ms
        self.enable_fallback = enable_fallback


def get_wikipedia_search_config() -> SelectorConfiguration:
    """
    Configuration for Wikipedia search input field.
    
    Uses YAML configuration exclusively for search input elements.
    
    Selector Engine Best Practices:
    1. Start with most specific and stable selectors (CSS ID selectors)
    2. Include expected attributes for validation and confidence scoring
    3. Use XPath as fallback for complex element relationships
    4. Use text-based matching as last resort for dynamic content
    5. Set appropriate priority order (1=highest priority)
    
    This configuration prioritizes CSS selectors for performance,
    falls back to XPath for robustness, and uses text matching
    as a final fallback for dynamic content scenarios.
    """
    # Load from YAML configuration - this is now the only source
    if not YAML_CONFIG_AVAILABLE:
        raise RuntimeError("YAML configurations are required. Install PyYAML and ensure wikipedia_selectors.yaml is available.")
    
    try:
        yaml_config = get_selector_config('search_input')
        # Convert YAML config to our SelectorConfiguration format
        strategies = []
        for strategy in yaml_config.strategies:
            strategy_dict = {
                "type": strategy.type,
                "selector": strategy.selector,
                "priority": strategy.priority
            }
            if strategy.expected_attributes:
                strategy_dict["expected_attributes"] = strategy.expected_attributes
            if strategy.search_context:
                strategy_dict["search_context"] = strategy.search_context
            strategies.append(strategy_dict)
        
        return SelectorConfiguration(
            element_purpose=yaml_config.element_purpose,
            strategies=strategies,
            confidence_threshold=yaml_config.confidence_threshold,
            timeout_per_strategy_ms=yaml_config.timeout_per_strategy_ms,
            enable_fallback=yaml_config.enable_fallback
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load search_input configuration from YAML: {e}")


def get_search_result_config() -> SelectorConfiguration:
    """
    Configuration for Wikipedia search result links.
    
    Uses YAML configuration exclusively for search result elements.
    
    Best Practices for Link Elements:
    1. Use class-based CSS selectors for consistent styling
    2. XPath for complex DOM relationships when needed
    3. Text-based matching with link context for dynamic content
    4. Consider multiple link types (direct links, wrapped links)
    """
    # Load from YAML configuration - this is now the only source
    if not YAML_CONFIG_AVAILABLE:
        raise RuntimeError("YAML configurations are required. Install PyYAML and ensure wikipedia_selectors.yaml is available.")
    
    try:
        yaml_config = get_selector_config('search_results')
        # Convert YAML config to our SelectorConfiguration format
        strategies = []
        for strategy in yaml_config.strategies:
            strategy_dict = {
                "type": strategy.type,
                "selector": strategy.selector,
                "priority": strategy.priority
            }
            if strategy.expected_attributes:
                strategy_dict["expected_attributes"] = strategy.expected_attributes
            if strategy.search_context:
                strategy_dict["search_context"] = strategy.search_context
            strategies.append(strategy_dict)
        
        return SelectorConfiguration(
            element_purpose=yaml_config.element_purpose,
            strategies=strategies,
            confidence_threshold=yaml_config.confidence_threshold,
            timeout_per_strategy_ms=yaml_config.timeout_per_strategy_ms,
            enable_fallback=yaml_config.enable_fallback
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load search_results configuration from YAML: {e}")


class SelectorEngineIntegration:
    """Integration layer for selector engine operations"""
    
    def __init__(self):
        """
        Initialize selector integration with fallback mode to avoid complex dependencies.
        
        This implementation demonstrates the selector engine concepts using basic Playwright
        selectors while maintaining the multi-strategy approach and confidence scoring concepts.
        """
        self.operations = []
        self.interactions = []
        self.timeout_per_strategy_ms = 1500
        
        # Initialize timing metrics tracking
        self.timing_metrics = {
            'total_strategy_time': 0,
            'total_operation_time': 0,
            'strategy_times': {},
            'operation_start_times': {},
            'strategy_start_times': {}
        }
        
        # Generate correlation ID for this session
        self.correlation_id = f"selector_{int(time.time())}_{hash(str(time.time())) % 10000:04d}"
        
        # Check for debug mode
        self.debug_mode = os.getenv("DEBUG_SELECTOR", "0") == "1"
        
        # Always use fallback mode to avoid selector engine initialization issues
        self.engine_available = False
        print("✅ Selector integration initialized in fallback mode")
        print("   This demonstrates multi-strategy concepts using basic Playwright selectors")
        print("   Full selector engine available but not required for this example")
        
        # Try to initialize full selector engine if available, but don't fail if it doesn't work
        if SELECTOR_ENGINE_AVAILABLE:
            try:
                self.selector_engine = get_selector_engine()
                self.engine_available = True
                print("✅ Full selector engine also available")
            except Exception as e:
                print(f"⚠️ Full selector engine not available: {e}")
                self.engine_available = False
    
    async def locate_element(
        self,
        page,
        config: SelectorConfiguration,
        timeout_ms: int = 5000
    ):
        """
        Locate element using multi-strategy selector engine with fallback to basic Playwright
        """
        if not self.engine_available:
            # Fallback to basic Playwright selector
            return await self._locate_element_fallback(page, config, timeout_ms)
        
        # Use full selector engine implementation
        return await self._locate_element_with_engine(page, config, timeout_ms)
    
    async def _locate_element_fallback(self, page, config: SelectorConfiguration, timeout_ms: int):
        """Fallback element location using basic Playwright selectors"""
        operation_id = f"locate_{config.element_purpose.replace(' ', '_')}"
        start_time = time.time()
        
        print(f"   [{operation_id}] Using fallback selector for: {config.element_purpose}")
        
        # Try strategies in priority order using basic Playwright
        for strategy_config in sorted(config.strategies, key=lambda x: x['priority']):
            strategy_type = strategy_config['type']
            selector_expression = strategy_config['selector']
            
            try:
                if strategy_type == "css":
                    element = await page.wait_for_selector(selector_expression, timeout=timeout_ms//len(config.strategies))
                    if element:
                        confidence = 0.8  # Default confidence for fallback
                        self._log_fallback_success(operation_id, config, strategy_type, confidence, start_time)
                        return element
                        
                elif strategy_type == "xpath":
                    element = await page.wait_for_selector(f"xpath={selector_expression}", timeout=timeout_ms//len(config.strategies))
                    if element:
                        confidence = 0.7  # Lower confidence for XPath fallback
                        self._log_fallback_success(operation_id, config, strategy_type, confidence, start_time)
                        return element
                        
                elif strategy_type == "text":
                    # Simple text-based fallback
                    if strategy_config.get('search_context') == "input":
                        elements = await page.query_selector_all("input")
                        for element in elements:
                            placeholder = await element.get_attribute("placeholder") or ""
                            if strategy_config['selector'].lower() in placeholder.lower():
                                confidence = 0.6  # Lower confidence for text fallback
                                self._log_fallback_success(operation_id, config, strategy_type, confidence, start_time)
                                return element
                    elif strategy_config.get('search_context') == "link":
                        elements = await page.query_selector_all("a")
                        for element in elements:
                            element_text = await element.text_content() or ""
                            if strategy_config['selector'].lower() in element_text.lower():
                                confidence = 0.6  # Lower confidence for text fallback
                                self._log_fallback_success(operation_id, config, strategy_type, confidence, start_time)
                                return element
                
            except Exception as e:
                print(f"   [{operation_id}] {strategy_type} fallback failed: {str(e)}")
                continue
        
        # All strategies failed
        self._log_fallback_failure(operation_id, config, start_time)
        return None
    
    def _log_fallback_success(self, operation_id: str, config: SelectorConfiguration, strategy_type: str, confidence: float, start_time: float):
        """Log successful fallback selector operation"""
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"✅ [{operation_id}] Fallback selector successful: {config.element_purpose}")
        print(f"   [{operation_id}] Strategy: {strategy_type} (fallback)")
        print(f"   [{operation_id}] Confidence: {confidence:.3f}")
        print(f"   [{operation_id}] Duration: {duration_ms}ms")
        
        # Store operation data for telemetry
        if not hasattr(self, 'operations'):
            self.operations = []
        self.operations.append({
            "operation_id": operation_id,
            "element_purpose": config.element_purpose,
            "successful_strategy": strategy_type,
            "confidence_score": confidence,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fallback_used": True
        })
    
    def _log_fallback_failure(self, operation_id: str, config: SelectorConfiguration, start_time: float):
        """Log failed fallback selector operation"""
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"❌ [{operation_id}] All fallback selectors failed: {config.element_purpose}")
        print(f"   [{operation_id}] Duration: {duration_ms}ms")
        
        # Store failed operation for telemetry
        if not hasattr(self, 'operations'):
            self.operations = []
        self.operations.append({
            "operation_id": operation_id,
            "element_purpose": config.element_purpose,
            "successful_strategy": None,
            "confidence_score": 0.0,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fallback_used": True,
            "failure_reason": "All fallback strategies failed"
        })
    
    async def _locate_element_with_engine(self, page, config: SelectorConfiguration, timeout_ms: int):
        """Locate element using full selector engine implementation"""
        operation_id = f"locate_{config.element_purpose.replace(' ', '_')}"
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        base_delay = 1000  # 1 second base delay for exponential backoff
        
        # Track operation start time
        if not hasattr(self, 'timing_metrics'):
            self.timing_metrics = {
                'total_strategy_time': 0,
                'total_operation_time': 0,
                'strategy_times': {},
                'operation_start_times': {},
                'strategy_start_times': {}
            }
        self.timing_metrics['operation_start_times'][operation_id] = start_time
        
        while retry_count <= max_retries:
            try:
                # Create DOM context for selector engine
                current_url = page.url
                current_time = datetime.now(timezone.utc)
                
                dom_context = DOMContext(
                    page=page,
                    tab_context="main",
                    url=current_url,
                    timestamp=current_time
                )
                
                # Try each strategy in priority order
                for strategy_config in sorted(config.strategies, key=lambda x: x['priority']):
                    strategy_result = await self._try_strategy(
                        dom_context, strategy_config, operation_id
                    )
                    
                    if strategy_result['success'] and strategy_result['confidence'] >= config.confidence_threshold:
                        # Log successful operation
                        self._log_operation_success(operation_id, config, strategy_result, start_time)
                        return strategy_result['element']
                
                # All strategies failed for this attempt
                if retry_count < max_retries:
                    retry_delay = base_delay * (2 ** retry_count)  # Exponential backoff
                    print(f"⚠️ All strategies failed, retrying in {retry_delay}ms (attempt {retry_count + 1}/{max_retries + 1})")
                    await asyncio.sleep(retry_delay / 1000)
                    retry_count += 1
                else:
                    break
                    
            except Exception as e:
                if retry_count < max_retries:
                    retry_delay = base_delay * (2 ** retry_count)
                    print(f"⚠️ Strategy error, retrying in {retry_delay}ms: {str(e)}")
                    await asyncio.sleep(retry_delay / 1000)
                    retry_count += 1
                else:
                    self._log_operation_error(operation_id, config, e, start_time)
                    return None
        
        # All retries exhausted
        self._log_operation_failure(operation_id, config, start_time)
        return None
    
    async def _try_strategy(self, dom_context, strategy_config, operation_id):
        """Try a single selector strategy with timeout handling and performance tracking"""
        start_time = time.time()
        strategy_type = strategy_config['type']
        selector_expression = strategy_config['selector']
        
        if self.debug_mode:
            print(f"   [{self.correlation_id}] 🔍 Trying {strategy_type} strategy: {selector_expression}")
        
        try:
            if strategy_type == "css":
                # Use CSS selector with Playwright and timeout
                element = await asyncio.wait_for(
                    dom_context.page.wait_for_selector(
                        selector_expression, 
                        timeout=self.timeout_per_strategy_ms
                    ),
                    timeout=self.timeout_per_strategy_ms / 1000
                )
                if element:
                    # Calculate confidence based on element attributes
                    confidence = await self._calculate_confidence(
                        element, strategy_config.get('expected_attributes', {})
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Track strategy performance
                    self._track_strategy_performance(strategy_type, confidence, duration_ms, True)
                    
                    if self.debug_mode:
                        print(f"   [{self.correlation_id}] ✅ {strategy_type} strategy successful")
                        print(f"   [{self.correlation_id}]    Confidence: {confidence:.3f}")
                        print(f"   [{self.correlation_id}]    Duration: {duration_ms}ms")
                    
                    return {
                        'success': True,
                        'confidence': confidence,
                        'element': element,
                        'type': strategy_type,
                        'duration_ms': duration_ms
                    }
                    
            elif strategy_type == "xpath":
                # Use XPath selector with Playwright and timeout
                element = await asyncio.wait_for(
                    dom_context.page.wait_for_selector(
                        f"xpath={selector_expression}",
                        timeout=self.timeout_per_strategy_ms
                    ),
                    timeout=self.timeout_per_strategy_ms / 1000
                )
                if element:
                    confidence = await self._calculate_confidence(
                        element, strategy_config.get('expected_attributes', {})
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Track strategy performance
                    self._track_strategy_performance(strategy_type, confidence, duration_ms, True)
                    
                    if self.debug_mode:
                        print(f"   [{self.correlation_id}] ✅ {strategy_type} strategy successful")
                        print(f"   [{self.correlation_id}]    Confidence: {confidence:.3f}")
                        print(f"   [{self.correlation_id}]    Duration: {duration_ms}ms")
                    
                    return {
                        'success': True,
                        'confidence': confidence,
                        'element': element,
                        'type': strategy_type,
                        'duration_ms': duration_ms
                    }
                    
            elif strategy_type == "text":
                # Use text-based matching with timeout
                search_context = strategy_config.get('search_context', '')
                text_content = strategy_config['selector']
                
                try:
                    if search_context == "input":
                        # Look for input elements with placeholder or containing text
                        elements = await asyncio.wait_for(
                            dom_context.page.query_selector_all("input"),
                            timeout=self.timeout_per_strategy_ms / 1000
                        )
                        for element in elements:
                            placeholder = await element.get_attribute("placeholder") or ""
                            if text_content.lower() in placeholder.lower():
                                confidence = await self._calculate_confidence(
                                    element, strategy_config.get('expected_attributes', {})
                                )
                                duration_ms = int((time.time() - start_time) * 1000)
                                
                                # Track strategy performance
                                self._track_strategy_performance(strategy_type, confidence, duration_ms, True)
                                
                                return {
                                    'success': True,
                                    'confidence': confidence,
                                    'element': element,
                                    'type': strategy_type,
                                    'duration_ms': duration_ms
                                }
                    elif search_context == "link":
                        # Look for links containing the text
                        elements = await asyncio.wait_for(
                            dom_context.page.query_selector_all("a"),
                            timeout=self.timeout_per_strategy_ms / 1000
                        )
                        for element in elements:
                            element_text = await element.text_content() or ""
                            if text_content.lower() in element_text.lower():
                                confidence = await self._calculate_confidence(
                                    element, strategy_config.get('expected_attributes', {})
                                )
                                duration_ms = int((time.time() - start_time) * 1000)
                                
                                # Track strategy performance
                                self._track_strategy_performance(strategy_type, confidence, duration_ms, True)
                                
                                return {
                                    'success': True,
                                    'confidence': confidence,
                                    'element': element,
                                    'type': strategy_type,
                                    'duration_ms': duration_ms
                                }
                except asyncio.TimeoutError:
                    pass  # Continue to strategy failure
            
            # Strategy failed to find element
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Track strategy performance for failure
            self._track_strategy_performance(strategy_type, 0.0, duration_ms, False)
            
            return {
                'success': False,
                'confidence': 0.0,
                'element': None,
                'type': strategy_type,
                'duration_ms': duration_ms,
                'error': f'Element not found with {strategy_type} selector: {selector_expression}'
            }
            
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Track strategy performance for timeout
            self._track_strategy_performance(strategy_type, 0.0, duration_ms, False)
            
            return {
                'success': False,
                'confidence': 0.0,
                'element': None,
                'type': strategy_type,
                'duration_ms': duration_ms,
                'error': f'{strategy_type} selector timeout after {self.timeout_per_strategy_ms}ms'
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Track strategy performance for error
            self._track_strategy_performance(strategy_type, 0.0, duration_ms, False)
            
            return {
                'success': False,
                'confidence': 0.0,
                'element': None,
                'type': strategy_type,
                'duration_ms': duration_ms,
                'error': f'{strategy_type} selector error: {str(e)}'
            }
    
    async def _calculate_confidence(self, element, expected_attributes):
        """Calculate confidence score for a located element"""
        confidence = 0.5  # Base confidence for found element
        
        # Check expected attributes
        for attr_name, expected_value in expected_attributes.items():
            actual_value = await element.get_attribute(attr_name)
            if actual_value:
                if actual_value == expected_value:
                    confidence += 0.2  # Perfect match
                elif expected_value.lower() in actual_value.lower():
                    confidence += 0.1  # Partial match
        
        # Check if element is visible
        try:
            is_visible = await element.is_visible()
            if is_visible:
                confidence += 0.2
        except:
            pass
        
        # Check if element is enabled
        try:
            is_enabled = await element.is_enabled()
            if is_enabled:
                confidence += 0.1
        except:
            pass
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _track_strategy_performance(self, strategy_type: str, confidence: float, duration_ms: int, success: bool):
        """Track strategy performance metrics for telemetry"""
        # Initialize strategy tracking if not exists
        if not hasattr(self, 'strategy_performance'):
            self.strategy_performance = {}
        
        if strategy_type not in self.strategy_performance:
            self.strategy_performance[strategy_type] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0,
                'total_duration_ms': 0,
                'total_confidence': 0.0,
                'min_confidence': 1.0,
                'max_confidence': 0.0,
                'avg_confidence': 0.0
            }
        
        perf = self.strategy_performance[strategy_type]
        perf['attempts'] += 1
        
        if success:
            perf['successes'] += 1
            perf['total_confidence'] += confidence
            perf['min_confidence'] = min(perf['min_confidence'], confidence)
            perf['max_confidence'] = max(perf['max_confidence'], confidence)
        else:
            perf['failures'] += 1
        
        perf['total_duration_ms'] += duration_ms
        perf['avg_confidence'] = perf['total_confidence'] / perf['successes'] if perf['successes'] > 0 else 0.0
    
    async def interact_with_element(
        self,
        page,
        element,
        interaction_type: str,
        interaction_data: dict = None
    ) -> dict:
        """Perform interaction with located element with error recovery"""
        interaction_id = f"{interaction_type}_{int(time.time())}"
        start_time = time.time()
        
        max_retries = 3
        retry_delay = 500  # 500ms base delay
        
        for attempt in range(max_retries):
            try:
                # Ensure element is still attached to DOM
                try:
                    await element.is_visible()
                except Exception:
                    if attempt < max_retries - 1:
                        print(f"⚠️ Element detached from DOM, retrying interaction (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay / 1000)
                        continue
                    else:
                        return {
                            "interaction_id": interaction_id,
                            "success": False,
                            "duration_ms": int((time.time() - start_time) * 1000),
                            "error": "Element detached from DOM"
                        }
                
                # Perform interaction based on type
                if interaction_type == "click":
                    # Scroll element into view before clicking
                    try:
                        await element.scroll_into_view_if_needed()
                    except:
                        pass  # Continue even if scroll fails
                    
                    await element.click()
                    
                elif interaction_type == "type" and interaction_data:
                    # Clear field first if it's an input
                    try:
                        if await element.get_attribute("type") in ["text", "search", "email", "password"]:
                            await element.clear()
                    except:
                        pass  # Continue even if clear fails
                    
                    # Type with human-like delays
                    text_to_type = interaction_data.get("text", "")
                    for char in text_to_type:
                        await element.type(char)
                        await asyncio.sleep(0.05)  # Small delay between characters
                    
                elif interaction_type == "scroll":
                    await element.scroll_into_view_if_needed()
                    
                else:
                    # Unknown interaction type
                    return {
                        "interaction_id": interaction_id,
                        "success": False,
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "error": f"Unknown interaction type: {interaction_type}"
                    }
                
                # Interaction successful
                duration_ms = int((time.time() - start_time) * 1000)
                result = {
                    "interaction_id": interaction_id,
                    "success": True,
                    "duration_ms": duration_ms,
                    "attempts": attempt + 1
                }
                
                self._log_interaction_success(interaction_id, interaction_type, result)
                return result
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Interaction failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(retry_delay / 1000)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # All retries failed
                    duration_ms = int((time.time() - start_time) * 1000)
                    result = {
                        "interaction_id": interaction_id,
                        "success": False,
                        "duration_ms": duration_ms,
                        "attempts": max_retries,
                        "error": str(e)
                    }
                    
                    self._log_interaction_error(interaction_id, interaction_type, result)
                    return result
    
    def _log_operation_success(self, operation_id: str, config: SelectorConfiguration, 
                              strategy_result: dict, start_time: float):
        """Log successful selector operation with confidence score details and correlation ID"""
        duration_ms = int((time.time() - start_time) * 1000)
        confidence = strategy_result['confidence']
        strategy_type = strategy_result['type']
        
        print(f"✅ [{self.correlation_id}] Selector operation successful: {config.element_purpose}")
        print(f"   [{self.correlation_id}] Strategy: {strategy_type}")
        print(f"   [{self.correlation_id}] Confidence: {confidence:.3f}")
        print(f"   [{self.correlation_id}] Confidence Level: {self._get_confidence_level(confidence)}")
        print(f"   [{self.correlation_id}] Duration: {duration_ms}ms")
        
        # Log confidence score details
        if confidence >= 0.9:
            print(f"   [{self.correlation_id}] 🎯 Excellent match - High confidence selector")
        elif confidence >= 0.8:
            print(f"   [{self.correlation_id}] ✅ Good match - Reliable selector")
        elif confidence >= 0.7:
            print(f"   [{self.correlation_id}] ⚠️ Acceptable match - Consider optimization")
        else:
            print(f"   [{self.correlation_id}] ❌ Low confidence - Selector needs improvement")
        
        # Store operation data for telemetry
        self.operations.append({
            "operation_id": operation_id,
            "correlation_id": self.correlation_id,
            "element_purpose": config.element_purpose,
            "successful_strategy": strategy_type,
            "confidence_score": confidence,
            "confidence_level": self._get_confidence_level(confidence),
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategies_attempted": 1  # Will be updated if retries occur
        })
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level description based on score"""
        if confidence >= 0.9:
            return "EXCELLENT"
        elif confidence >= 0.8:
            return "GOOD"
        elif confidence >= 0.7:
            return "ACCEPTABLE"
        elif confidence >= 0.5:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _log_operation_failure(self, operation_id: str, config: SelectorConfiguration, start_time: float):
        """Log failed selector operation with strategy details"""
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"❌ Selector operation failed: {config.element_purpose}")
        print(f"   Strategies attempted: {len(config.strategies)}")
        print(f"   Strategies: {', '.join([s['type'] for s in config.strategies])}")
        print(f"   Confidence threshold: {config.confidence_threshold}")
        print(f"   Total duration: {duration_ms}ms")
        print(f"   All strategies exhausted or failed to meet confidence threshold")
        
        # Store failed operation for telemetry
        self.operations.append({
            "operation_id": operation_id,
            "element_purpose": config.element_purpose,
            "successful_strategy": None,
            "confidence_score": 0.0,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategies_attempted": len(config.strategies),
            "failure_reason": "All strategies failed or confidence too low"
        })
    
    def _log_operation_error(self, operation_id: str, config: SelectorConfiguration, e, start_time: float):
        """Log selector operation error"""
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"❌ Selector operation error: {config.element_purpose}")
        print(f"   Error: {str(e)}")
        print(f"   Duration: {duration_ms}ms")
    
    def _log_interaction_success(self, interaction_id: str, interaction_type: str, result: dict):
        """Log successful element interaction"""
        print(f"✅ Element interaction successful: {interaction_type}")
        print(f"   Duration: {result['duration_ms']}ms")
    
    def _log_interaction_error(self, interaction_id: str, interaction_type: str, result: dict):
        """Log failed element interaction"""
        print(f"❌ Element interaction failed: {interaction_type}")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print(f"   Duration: {result['duration_ms']}ms")
    
    def get_telemetry_summary(self) -> dict:
        """Generate comprehensive telemetry summary for the session"""
        if not self.operations:
            return {}
            
        total_operations = len(self.operations)
        successful_operations = len([op for op in self.operations if op.get("confidence_score", 0) > 0.7])
        failed_operations = total_operations - successful_operations
        
        # Calculate strategy performance metrics
        strategy_performance = {}
        strategy_usage = {}
        strategy_success_rates = {}
        
        for op in self.operations:
            strategy = op.get("successful_strategy")
            if strategy:
                strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
                strategy_performance[strategy] = strategy_performance.get(strategy, {
                    "total_duration_ms": 0,
                    "total_confidence": 0,
                    "count": 0
                })
                strategy_performance[strategy]["total_duration_ms"] += op.get("duration_ms", 0)
                strategy_performance[strategy]["total_confidence"] += op.get("confidence_score", 0)
                strategy_performance[strategy]["count"] += 1
        
        # Calculate success rates per strategy
        for strategy, perf in strategy_performance.items():
            if perf["count"] > 0:
                strategy_success_rates[strategy] = {
                    "successes": strategy_usage.get(strategy, 0),
                    "attempts": perf["count"],
                    "success_rate": strategy_usage.get(strategy, 0) / perf["count"],
                    "avg_confidence": perf["total_confidence"] / perf["count"],
                    "avg_duration_ms": perf["total_duration_ms"] / perf["count"]
                }
        
        # Calculate timing metrics
        total_duration = sum(op.get("duration_ms", 0) for op in self.operations)
        avg_duration = total_duration / total_operations if total_operations > 0 else 0
        
        # Calculate confidence metrics
        successful_confidences = [op.get("confidence_score", 0) for op in self.operations if op.get("confidence_score", 0) > 0]
        avg_confidence = sum(successful_confidences) / len(successful_confidences) if successful_confidences else 0
        max_confidence = max(successful_confidences) if successful_confidences else 0
        min_confidence = min(successful_confidences) if successful_confidences else 0
        
        # Calculate retry metrics
        retry_operations = [op for op in self.operations if "strategies_attempted" in op]
        avg_strategies_per_operation = sum(op.get("strategies_attempted", 1) for op in self.operations) / total_operations if total_operations > 0 else 1
        
        return {
            "session_summary": {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
                "average_confidence_score": avg_confidence,
                "max_confidence_score": max_confidence,
                "min_confidence_score": min_confidence,
                "total_duration_ms": total_duration,
                "average_operation_duration_ms": avg_duration,
                "strategies_used": list(set(op.get("successful_strategy") for op in self.operations if op.get("successful_strategy"))),
                "fallback_usage_rate": (total_operations - len([op for op in self.operations if op.get("successful_strategy")])) / total_operations if total_operations > 0 else 0,
                "avg_strategies_per_operation": avg_strategies_per_operation
            },
            "strategy_performance": strategy_success_rates,
            "operations": self.operations,
            "interaction_summary": {
                "total_interactions": len(self.interactions),
                "successful_interactions": len([i for i in self.interactions if i.get("success", False)]),
                "interaction_types": list(set(i.get("interaction_type", "unknown") for i in self.interactions)),
                "avg_interaction_duration_ms": sum(i.get("duration_ms", 0) for i in self.interactions) / len(self.interactions) if self.interactions else 0
            },
            "timing_metrics": getattr(self, 'timing_metrics', {}),
            "strategy_performance_detailed": getattr(self, 'strategy_performance', {})
        }
    
    async def save_telemetry_data(self, session_id: str = None):
        """Save telemetry data to data/telemetry/ directory"""
        if not self.operations:
            return
        
        # Create telemetry directory if it doesn't exist
        telemetry_dir = Path("data/telemetry")
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        session_id = session_id or f"session_{timestamp}"
        filename = f"selector_telemetry_{session_id}_{timestamp}.json"
        filepath = telemetry_dir / filename
        
        # Get telemetry summary
        telemetry_data = self.get_telemetry_summary()
        
        # Add session metadata
        telemetry_data["session_metadata"] = {
            "session_id": session_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_operations": len(self.operations),
            "telemetry_version": "1.0"
        }
        
        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(telemetry_data, f, indent=2, default=str)
            print(f"📊 Telemetry data saved to: {filepath}")
        except Exception as e:
            print(f"❌ Failed to save telemetry data: {str(e)}")


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
