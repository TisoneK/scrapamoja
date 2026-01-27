"""
DOM Snapshot Integration

This module provides DOM snapshot functionality for failure analysis,
following the Production Resilience constitution principle.
"""

import asyncio
import json
import time
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
        screenshot_path: Optional[str] = None
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
            "screenshot_path": self.screenshot_path
        }


class DOMSnapshotManager:
    """Manages DOM snapshots for debugging and analysis."""
    
    def __init__(self, snapshot_dir: str = "data/snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger("browser.snapshots")
        
    async def capture_snapshot(
        self,
        page: Page,
        page_id: str,
        include_screenshot: bool = True,
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
                
            # Screenshot
            screenshot_path = None
            if include_screenshot:
                screenshot_path = await self._capture_screenshot(page, page_id)
                
            snapshot = DOMSnapshot(
                page_id=page_id,
                url=url,
                title=title,
                content=content,
                selector_results=selector_results,
                network_requests=network_requests,
                console_logs=console_logs,
                screenshot_path=screenshot_path
            )
            
            # Save snapshot to file
            await self._save_snapshot(snapshot)
            
            self.logger.info(
                "DOM snapshot captured",
                page_id=page_id,
                url=url,
                title=title,
                screenshot=bool(screenshot_path)
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
        
    async def _capture_screenshot(self, page: Page, page_id: str) -> str:
        """Capture screenshot and return path."""
        try:
            timestamp = int(time.time())
            filename = f"{page_id}_{timestamp}.png"
            filepath = self.snapshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            
            return str(filepath)
            
        except Exception as e:
            self.logger.warning(
                "Failed to capture screenshot",
                page_id=page_id,
                error=str(e)
            )
            return None
            
    async def _save_snapshot(self, snapshot: DOMSnapshot) -> None:
        """Save snapshot to JSON file."""
        try:
            timestamp = int(snapshot.timestamp)
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
