"""
Capture engine for snapshot system with async parallel processing.

This module handles the actual capture of browser artifacts including HTML,
screenshots, console logs, and network logs with parallel execution.
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import hashlib

from .models import (
    SnapshotConfig, SnapshotContext, SnapshotBundle, SnapshotMode, EnumEncoder,
    ContentDeduplicator, ArtifactCaptureError, SnapshotError
)
from .storage import SnapshotStorage, AtomicFileWriter


class SnapshotCapture:
    """Handles the capture of browser artifacts with async parallel processing."""
    
    def __init__(self, storage: SnapshotStorage, deduplicator: Optional[ContentDeduplicator] = None):
        """Initialize capture engine."""
        self.storage = storage
        self.deduplicator = deduplicator or ContentDeduplicator()
        
    async def capture_snapshot(self, 
                             page: Any,
                             context: SnapshotContext,
                             config: SnapshotConfig) -> SnapshotBundle:
        """Capture complete snapshot with parallel artifact processing."""
        print(f"🔍 DIAGNOSTIC: CAPTURE SNAPSHOT STARTED - context: {context}, config: {config}")
        start_time = datetime.now()
        
        try:
            # Validate configuration
            config.validate()
            
            # Generate bundle path
            bundle_path = self.storage.get_bundle_path(context, start_time)
            
            # Create bundle directory
            await self.storage.create_bundle_directory(bundle_path)
            
            # Prepare artifact directories
            html_dir = bundle_path / "html"
            screenshots_dir = bundle_path / "screenshots"
            logs_dir = bundle_path / "logs"
            
            # Prepare capture tasks
            capture_tasks = []
            artifact_paths = []
            
            if config.capture_html:
                # Always capture full page HTML
                capture_tasks.append(
                    self._capture_full_html(page, html_dir)
                )
                
                # Capture element HTML if selector is available (regardless of mode)
                if config.selector and config.mode in [SnapshotMode.SELECTOR, SnapshotMode.BOTH, SnapshotMode.FULL_PAGE]:
                    capture_tasks.append(
                        self._capture_element_html(page, config.selector, html_dir)
                    )
            
            if config.capture_screenshot:
                capture_tasks.append(
                    self._capture_screenshot(page, screenshots_dir)
                )
            
            if config.capture_console:
                capture_tasks.append(
                    self._capture_console_logs(page, logs_dir)
                )
            
            if config.capture_network:
                capture_tasks.append(
                    self._capture_network_logs(page, logs_dir)
                )
            
            # Execute capture tasks
            if config.async_save and len(capture_tasks) > 1:
                # Parallel execution
                results = await asyncio.gather(*capture_tasks, return_exceptions=True)
                artifact_paths = self._process_capture_results(results)
            else:
                # Sequential execution
                artifact_paths = []
                for task in capture_tasks:
                    try:
                        result = await task
                        if result:
                            artifact_paths.append(result)
                    except Exception as e:
                        raise ArtifactCaptureError(f"Failed to capture artifact: {e}")
            
            # Create bundle
            end_time = datetime.now()
            bundle = SnapshotBundle(
                context=context,
                timestamp=start_time,
                config=config,
                bundle_path=str(bundle_path),
                artifacts=artifact_paths,
                metadata={
                    "capture_duration_seconds": (end_time - start_time).total_seconds(),
                    "capture_mode": config.mode.value,
                    "parallel_execution": config.async_save and len(capture_tasks) > 1
                }
            )
            
            # Save bundle metadata
            await self.storage.save_bundle_metadata(bundle)
            
            return bundle
            
        except Exception as e:
            # Cleanup on failure
            if 'bundle_path' in locals():
                await self.storage.delete_bundle(str(bundle_path))
            raise SnapshotError(f"Failed to capture snapshot: {e}")
    
    def _process_capture_results(self, results: List[Union[str, Exception]]) -> List[str]:
        """Process results from parallel capture operations."""
        artifact_paths = []
        
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other artifacts
                print(f"Capture artifact failed: {result}")
                continue
            elif result:
                artifact_paths.append(result)
        
        return artifact_paths
    
    async def _capture_full_html(self, page: Any, html_dir: Path) -> Optional[str]:
        """Capture full page HTML."""
        try:
            # Get page HTML
            html_content = await page.content()
            
            # Check deduplication
            if self.deduplicator:
                existing_hash = self.deduplicator.is_duplicate(html_content)
                if existing_hash:
                    return f"html/fullpage_{existing_hash}.html"
            
            # Generate filename
            content_hash = hashlib.md5(html_content.encode()).hexdigest()[:8]
            filename = f"fullpage_{content_hash}.html"
            file_path = html_dir / filename
            
            # Write atomically
            await AtomicFileWriter.write_text(file_path, html_content)
            
            # Add to deduplicator
            if self.deduplicator:
                self.deduplicator.add_content(html_content)
            
            return f"html/{filename}"
            
        except Exception as e:
            raise ArtifactCaptureError(f"Failed to capture full HTML: {e}")
    
    async def _capture_element_html(self, page: Any, selector: str, html_dir: Path) -> Optional[str]:
        """Capture element-specific HTML."""
        try:
            print(f"🔍 DIAGNOSTIC: Attempting to capture element HTML with selector: {selector}")
            
            # Find element
            element = await page.query_selector(selector)
            if not element:
                print(f"🔍 DIAGNOSTIC: Element not found for selector: {selector}")
                raise ArtifactCaptureError(f"Element not found for selector: {selector}")
            
            # Get element HTML
            html_content = await element.inner_html()
            
            print(f"🔍 DIAGNOSTIC: Successfully captured element HTML, length: {len(html_content)}")
            
            # Check deduplication
            if self.deduplicator:
                existing_hash = self.deduplicator.is_duplicate(html_content)
                if existing_hash:
                    return f"html/element_{existing_hash}.html"
            
            # Generate filename
            content_hash = hashlib.md5(html_content.encode()).hexdigest()[:8]
            filename = f"element_{content_hash}.html"
            file_path = html_dir / filename
            
            print(f"🔍 DIAGNOSTIC: Saving element HTML to: {file_path}")
            
            # Write atomically
            await AtomicFileWriter.write_text(file_path, html_content)
            
            # Add to deduplicator
            if self.deduplicator:
                self.deduplicator.add_content(html_content)
            
            result = f"html/{filename}"
            print(f"🔍 DIAGNOSTIC: Element HTML capture completed: {result}")
            return result
            
        except Exception as e:
            print(f"🔍 DIAGNOSTIC: Failed to capture element HTML: {e}")
            raise ArtifactCaptureError(f"Failed to capture element HTML: {e}")
    
    async def _capture_screenshot(self, page: Any, screenshots_dir: Path) -> Optional[str]:
        """Capture page screenshot."""
        try:
            # Take screenshot
            screenshot_bytes = await page.screenshot(type='png')
            
            # Generate filename
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"viewport_{timestamp}.png"
            file_path = screenshots_dir / filename
            
            # Write atomically
            await AtomicFileWriter.write_bytes(file_path, screenshot_bytes)
            
            return f"screenshots/{filename}"
            
        except Exception as e:
            raise ArtifactCaptureError(f"Failed to capture screenshot: {e}")
    
    async def _capture_console_logs(self, page: Any, logs_dir: Path) -> Optional[str]:
        """Capture browser console logs."""
        try:
            # Get console logs
            logs = []
            
            # Listen for console messages
            async def handle_console(msg):
                logs.append({
                    "type": msg.type,
                    "text": msg.text,
                    "location": {
                        "url": msg.location.get("url") if msg.location else None,
                        "lineNumber": msg.location.get("lineNumber") if msg.location else None,
                        "columnNumber": msg.location.get("columnNumber") if msg.location else None
                    },
                    "timestamp": datetime.now().isoformat()
                })
            
            # Add console listener
            page.on("console", handle_console)
            
            # Wait a moment to collect recent logs
            await asyncio.sleep(0.1)
            
            # Remove listener
            page.remove_listener("console", handle_console)
            
            # Generate filename
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"console_{timestamp}.json"
            file_path = logs_dir / filename
            
            # Write atomically
            await AtomicFileWriter.write_text(file_path, json.dumps(logs, indent=2, cls=EnumEncoder))
            
            return f"logs/{filename}"
            
        except Exception as e:
            raise ArtifactCaptureError(f"Failed to capture console logs: {e}")
    
    async def _capture_network_logs(self, page: Any, logs_dir: Path) -> Optional[str]:
        """Capture network activity logs."""
        try:
            # Get network logs
            network_logs = []
            
            # Listen for network responses
            async def handle_response(response):
                network_logs.append({
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "headers": dict(response.headers),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Add response listener
            page.on("response", handle_response)
            
            # Wait a moment to collect recent responses
            await asyncio.sleep(0.1)
            
            # Remove listener
            page.remove_listener("response", handle_response)
            
            # Generate filename
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"network_{timestamp}.json"
            file_path = logs_dir / filename
            
            # Write atomically
            await AtomicFileWriter.write_text(file_path, json.dumps(network_logs, indent=2, cls=EnumEncoder))
            
            return f"logs/{filename}"
            
        except Exception as e:
            raise ArtifactCaptureError(f"Failed to capture network logs: {e}")
    
    async def capture_minimal_snapshot(self,
                                     page: Any,
                                     context: SnapshotContext) -> SnapshotBundle:
        """Capture minimal snapshot with metadata only."""
        try:
            start_time = datetime.now()
            
            # Generate bundle path
            bundle_path = self.storage.get_bundle_path(context, start_time)
            
            # Create bundle directory
            await self.storage.create_bundle_directory(bundle_path)
            
            # Create minimal bundle
            bundle = SnapshotBundle(
                context=context,
                timestamp=start_time,
                config=SnapshotConfig(mode=SnapshotMode.MINIMAL),
                bundle_path=str(bundle_path),
                artifacts=[],
                metadata={
                    "capture_mode": "minimal",
                    "capture_duration_seconds": 0.0
                }
            )
            
            # Save bundle metadata
            await self.storage.save_bundle_metadata(bundle)
            
            return bundle
            
        except Exception as e:
            # Cleanup on failure
            if 'bundle_path' in locals():
                await self.storage.delete_bundle(str(bundle_path))
            raise SnapshotError(f"Failed to capture minimal snapshot: {e}")
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        if not self.deduplicator:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "cache_size": self.deduplicator.cache_size,
            "cache_utilization": self.deduplicator.cache_utilization,
            "max_cache_size": self.deduplicator.max_cache_size
        }
