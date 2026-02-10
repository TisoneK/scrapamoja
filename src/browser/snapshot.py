"""
DOM Snapshot Integration

This module provides DOM snapshot functionality for failure analysis,
following the Production Resilience constitution principle.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
import structlog

try:
    from playwright.async_api import Page
except ImportError:
    Page = None

from .exceptions import BrowserError


class DOMSnapshot:
    """DOM snapshot for debugging and failure analysis."""
    
    def __init__(
        self,
        page_id: str,
        url: Optional[str] = None,
        timestamp: Optional[float] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        selector_results: Optional[Dict[str, Any]] = None,
        network_requests: Optional[List[Dict[str, Any]]] = None,
        console_logs: Optional[List[Dict[str, Any]]] = None,
        screenshot_path: Optional[str] = None,
        html_metadata: Optional[Dict[str, Any]] = None,
        screenshot_metadata: Optional[Dict[str, Any]] = None
    ):
        self.page_id = page_id
        self.url = url
        self.timestamp = timestamp or time.time()
        self.title = title
        self.content = content
        self.selector_results = selector_results or {}
        self.network_requests = network_requests or []
        self.console_logs = console_logs or []
        self.screenshot_path = screenshot_path
        self.html_metadata = html_metadata
        self.screenshot_metadata = screenshot_metadata
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "page_id": self.page_id,
            "url": self.url,
            "timestamp": self.timestamp,
            "title": self.title,
            "content": self.content,
            "selector_results": self.selector_results,
            "network_requests": self.network_requests,
            "console_logs": self.console_logs,
            "screenshot_path": self.screenshot_path,
            "html_metadata": self.html_metadata,
            "screenshot_metadata": self.screenshot_metadata
        }


class DOMSnapshotManager:
    """Manages DOM snapshots for debugging and analysis."""
    
    def __init__(self, snapshot_dir: str = "data/snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger("browser.snapshots")
        
    def _sanitize_session_id(self, session_id: str) -> str:
        """
        Sanitize session ID for use in filenames.
        
        Allows only alphanumeric characters and underscores.
        Replaces invalid characters with underscores.
        
        Args:
            session_id: Original session ID (may contain hyphens, etc.)
            
        Returns:
            Sanitized session ID safe for filenames
        """
        import re
        # Replace any non-alphanumeric characters (except underscore) with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', session_id)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized or "unknown"
    
    def _generate_filename(self, page_name: str, session_id: str, timestamp: int) -> str:
        """
        Generate session-aware snapshot filename.
        
        Format: {page_name}_{session_id}_{timestamp}.json
        
        Args:
            page_name: Base name for the snapshot (e.g., 'wikipedia_search')
            session_id: Session identifier for uniqueness
            timestamp: Unix timestamp as integer
            
        Returns:
            Complete filename with session ID included
        """
        sanitized_session = self._sanitize_session_id(session_id)
        return f"{page_name}_{sanitized_session}_{timestamp}.json"
    
    def _generate_screenshot_filename(self, page_name: str, session_id: str, timestamp: int) -> str:
        """
        Generate session-aware screenshot filename.
        
        Format: {page_name}_{session_id}_{timestamp}.png
        
        Args:
            page_name: Base name for the screenshot
            session_id: Session identifier for uniqueness
            timestamp: Unix timestamp as integer
            
        Returns:
            Complete PNG filename with session ID included
        """
        sanitized_session = self._sanitize_session_id(session_id)
        return f"{page_name}_{sanitized_session}_{timestamp}.png"
    
    def _generate_screenshot_path(self, page_name: str, session_id: str, timestamp: int) -> str:
        """
        Generate session-aware screenshot file path reference.
        
        Used in JSON metadata to reference the screenshot file.
        
        Format: screenshots/{page_name}_{session_id}_{timestamp}.png
        
        Args:
            page_name: Base name for the screenshot
            session_id: Session identifier for uniqueness
            timestamp: Unix timestamp as integer
            
        Returns:
            Relative path for screenshot reference in JSON
        """
        filename = self._generate_screenshot_filename(page_name, session_id, timestamp)
        return f"screenshots/{filename}"
        
    async def capture_snapshot(
        self,
        page: Page,
        page_id: str,
        session_id: Optional[str] = None,
        include_screenshot: bool = True,
        include_html_file: bool = True,
        screenshot_mode: str = "fullpage",
        include_network: bool = True,
        include_console: bool = True,
        custom_selectors: Optional[List[str]] = None
    ) -> DOMSnapshot:
        """Capture comprehensive DOM snapshot."""
        if Page is None:
            raise BrowserError("PLAYWRIGHT_NOT_AVAILABLE", "Playwright is not available")
            
        try:
            # Basic page information
            url = page.url
            title = await page.title()
            
            # DOM content
            content = await page.content()
            
            # Network requests
            network_requests = []
            if include_network:
                # This would require network interception setup
                network_requests = await self._get_network_requests(page)
                
            # Console logs
            console_logs = []
            if include_console:
                console_logs = await self._get_console_logs(page)
                
            # Custom selector results
            selector_results = {}
            if custom_selectors:
                selector_results = await self._evaluate_selectors(page, custom_selectors)
                
            # Screenshot with rich metadata
            screenshot_metadata = None
            if include_screenshot:
                screenshot_metadata = await self._capture_screenshot(page, page_id, session_id, screenshot_mode)
            
            # HTML file with rich metadata
            html_metadata = None
            if include_html_file:
                html_metadata = await self._capture_html_file(page, page_id, content)
                
            snapshot = DOMSnapshot(
                page_id=page_id,
                url=url,
                title=title,
                content=content,
                selector_results=selector_results,
                network_requests=network_requests,
                console_logs=console_logs,
                screenshot_path=screenshot_metadata["filepath"] if screenshot_metadata else None,
                html_metadata=html_metadata,
                screenshot_metadata=screenshot_metadata
            )
            
            # Save snapshot to file with session ID
            await self._save_snapshot(snapshot, session_id)
            
            self.logger.info(
                "DOM snapshot captured",
                page_id=page_id,
                url=url,
                title=title,
                screenshot=bool(screenshot_metadata["filepath"] if screenshot_metadata else False)
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error(
                "Failed to capture DOM snapshot",
                page_id=page_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise BrowserError("SNAPSHOT_CAPTURE_FAILED", f"Failed to capture snapshot: {str(e)}")
            
    async def _get_network_requests(self, page: Page) -> List[Dict[str, Any]]:
        """Get network requests from page."""
        # This would require network event listeners setup during page creation
        # For now, return empty list
        return []
        
    async def _get_console_logs(self, page: Page) -> List[Dict[str, Any]]:
        """Get console logs from page."""
        # This would require console event listeners setup during page creation
        # For now, return empty list
        return []
        
    async def _evaluate_selectors(self, page: Page, selectors: List[str]) -> Dict[str, Any]:
        """Evaluate custom selectors and return results."""
        results = {}
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                results[selector] = {
                    "count": len(elements),
                    "found": len(elements) > 0
                }
                
                # Get text content for first few elements
                if elements:
                    texts = []
                    for i, element in enumerate(elements[:5]):  # Limit to first 5
                        text = await element.text_content()
                        texts.append(text.strip() if text else "")
                    results[selector]["sample_texts"] = texts
                    
            except Exception as e:
                results[selector] = {
                    "error": str(e),
                    "found": False
                }
                
        return results
        
    async def _capture_screenshot(self, page: Page, page_id: str, session_id: Optional[str] = None, screenshot_mode: str = "fullpage") -> dict:
        """Capture screenshot and return rich metadata with session ID in filename."""
        try:
            timestamp = int(time.time())
            
            # Ensure screenshots directory exists
            screenshots_dir = self.snapshot_dir / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with session_id if available
            if session_id:
                filename = self._generate_screenshot_filename(page_id, session_id, timestamp)
            else:
                # Fallback to old format if no session_id provided
                filename = f"{page_id}_{timestamp}.png"
            
            filepath = screenshots_dir / filename
            
            # Configure screenshot options
            screenshot_options = {
                "path": str(filepath),
                "type": "png"
            }
            
            if screenshot_mode == "fullpage":
                screenshot_options["full_page"] = True
            
            await page.screenshot(**screenshot_options)
            
            # Get screenshot metadata
            file_size = filepath.stat().st_size
            
            # Try to get dimensions if PIL is available
            width, height = 0, 0
            try:
                from PIL import Image
                with Image.open(filepath) as img:
                    width, height = img.size
            except ImportError:
                self.logger.debug("PIL not available, screenshot dimensions set to 0")
            
            return {
                "filepath": f"screenshots/{filename}",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "width": width,
                "height": height,
                "file_size_bytes": file_size,
                "capture_mode": screenshot_mode,
                "format": "png"
            }
            
        except Exception as e:
            self.logger.warning(
                "Failed to capture screenshot",
                page_id=page_id,
                error=str(e)
            )
            return None
    
    async def _capture_html_file(self, page: Page, page_id: str, content: str) -> dict:
        """Capture HTML content to file and return rich metadata."""
        try:
            timestamp = int(time.time())
            filename = f"{page_id}_{timestamp}.html"
            filepath = self.snapshot_dir / filename
            
            # Create HTML subdirectory
            html_dir = self.snapshot_dir / "html"
            html_dir.mkdir(exist_ok=True)
            html_filepath = html_dir / filename
            
            # Write HTML content
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Generate content hash
            import hashlib
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            return {
                "filepath": f"html/{filename}",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "file_size_bytes": len(content),
                "content_length": len(content),
                "content_hash": content_hash,
                "format": "html"
            }
            
        except Exception as e:
            self.logger.warning(
                "Failed to capture HTML file",
                page_id=page_id,
                error=str(e)
            )
            return None
            
    async def _save_snapshot(self, snapshot: DOMSnapshot, session_id: Optional[str] = None) -> None:
        """Save snapshot to JSON file with optional session ID in filename."""
        try:
            timestamp = int(snapshot.timestamp)
            
            # Generate filename with session_id if available
            if session_id:
                filename = self._generate_filename(snapshot.page_id, session_id, timestamp)
            else:
                # Fallback to old format if no session_id provided
                filename = f"{snapshot.page_id}_{timestamp}.json"
            
            filepath = self.snapshot_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(
                "Failed to save snapshot file",
                page_id=snapshot.page_id,
                error=str(e)
            )
            
    async def load_snapshot(self, page_id: str, timestamp: Optional[float] = None) -> Optional[DOMSnapshot]:
        """Load snapshot from file."""
        try:
            if timestamp:
                filename = f"{page_id}_{int(timestamp)}.json"
            else:
                # Find the most recent snapshot for this page_id
                pattern = f"{page_id}_*.json"
                files = list(self.snapshot_dir.glob(pattern))
                if not files:
                    return None
                filename = max(files, key=lambda f: f.stat().st_mtime).name
                
            filepath = self.snapshot_dir / filename
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return DOMSnapshot(**data)
            
        except Exception as e:
            self.logger.error(
                "Failed to load snapshot",
                page_id=page_id,
                timestamp=timestamp,
                error=str(e)
            )
            return None
            
    async def cleanup_old_snapshots(self, max_age_days: int = 7) -> int:
        """Clean up old snapshots."""
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            deleted_count = 0
            
            for filepath in self.snapshot_dir.glob("*.json"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    deleted_count += 1
                    
            # Also clean up corresponding screenshots
            for filepath in self.snapshot_dir.glob("*.png"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    
            self.logger.info(
                "Cleaned up old snapshots",
                deleted_count=deleted_count,
                max_age_days=max_age_days
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup old snapshots",
                error=str(e)
            )
            return 0
            
    def list_snapshots(self, page_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available snapshots."""
        snapshots = []
        
        try:
            pattern = f"{page_id}_*.json" if page_id else "*.json"
            
            for filepath in self.snapshot_dir.glob(pattern):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    snapshots.append({
                        "page_id": data["page_id"],
                        "url": data["url"],
                        "title": data["title"],
                        "timestamp": data["timestamp"],
                        "filename": filepath.name,
                        "screenshot": data.get("screenshot_path")
                    })
                    
                except Exception as e:
                    self.logger.warning(
                        "Failed to read snapshot file",
                        filename=filepath.name,
                        error=str(e)
                    )
                    
            return sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            self.logger.error(
                "Failed to list snapshots",
                error=str(e)
            )
            return []


# Global snapshot manager
snapshot_manager = DOMSnapshotManager()
