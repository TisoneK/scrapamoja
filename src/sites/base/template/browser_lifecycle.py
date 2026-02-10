"""
Browser lifecycle integration for template framework.

This module provides automatic integration with browser lifecycle management,
including screenshot capture, HTML capture, and resource monitoring.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .integration_bridge import BaseIntegrationBridge


logger = logging.getLogger(__name__)


class BrowserLifecycleIntegration:
    """
    Browser lifecycle integration for template framework.
    
    This class provides automatic integration with browser lifecycle management
    features, enabling templates to leverage existing browser capabilities without
    manual configuration.
    """
    
    def __init__(self, integration_bridge: BaseIntegrationBridge):
        """
        Initialize browser lifecycle integration.
        
        Args:
            integration_bridge: The integration bridge instance
        """
        self.integration_bridge = integration_bridge
        self.page = integration_bridge.page
        self.template_name = integration_bridge.template_name
        
        # Browser lifecycle state
        self.browser_session_id = None
        self.browser_capabilities = {}
        self.lifecycle_events = []
        
        # Feature availability
        self.features_available = {
            "screenshot_capture": False,
            "html_capture": False,
            "resource_monitoring": False,
            "stealth_features": False,
            "performance_monitoring": False
        }
        
        # Configuration
        self.config = {
            "auto_screenshot": False,
            "auto_html_capture": False,
            "auto_resource_monitoring": False,
            "screenshot_on_error": True,
            "html_capture_on_error": True,
            "screenshot_format": "png",
            "screenshot_quality": 80,
            "html_capture_clean": True
        }
        
        logger.info(f"BrowserLifecycleIntegration initialized for {template_name}")
    
    async def initialize_browser_integration(self) -> bool:
        """
        Initialize browser lifecycle integration.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info(f"Initializing browser lifecycle integration for {self.template_name}")
            
            # Detect browser capabilities
            await self._detect_browser_capabilities()
            
            # Initialize browser session
            await self._initialize_browser_session()
            
            # Setup automatic features
            await self._setup_automatic_features()
            
            # Register event handlers
            await self._register_event_handlers()
            
            logger.info(f"Browser lifecycle integration initialized successfully for {self.template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser lifecycle integration: {e}")
            return False
    
    async def _detect_browser_capabilities(self) -> None:
        """Detect browser capabilities and features."""
        try:
            # Get browser capabilities from integration bridge
            available_components = self.integration_bridge.get_available_components()
            
            # Detect screenshot capture capabilities
            browser_lifecycle = available_components.get("browser_lifecycle", {})
            screenshot_capture = available_components.get("screenshot_capture", {})
            
            self.features_available["screenshot_capture"] = (
                browser_lifecycle.get("available", False) and 
                screenshot_capture.get("available", False)
            )
            
            # Detect HTML capture capabilities
            html_capture = available_components.get("html_capture", {})
            self.features_available["html_capture"] = html_capture.get("available", False)
            
            # Detect resource monitoring capabilities
            resource_monitoring = available_components.get("resource_monitoring", {})
            self.features_available["resource_monitoring"] = resource_monitoring.get("available", False)
            
            # Detect stealth features
            stealth_features = available_components.get("stealth_features", {})
            self.features_available["stealth_features"] = stealth_features.get("available", False)
            
            # Store browser capabilities
            self.browser_capabilities = {
                "browser_type": browser_lifecycle.get("browser_type", "unknown"),
                "supports_screenshot": self.features_available["screenshot_capture"],
                "supports_html_capture": self.features_available["html_capture"],
                "supports_resource_monitoring": self.features_available["resource_monitoring"],
                "supports_stealth": self.features_available["stealth_features"],
                "browser_lifecycle": browser_lifecycle,
                "screenshot_capture": screenshot_capture,
                "html_capture": html_capture,
                "resource_monitoring": resource_monitoring,
                "stealth_features": stealth_features
            }
            
            logger.debug(f"Browser capabilities detected: {list(self.browser_capabilities.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to detect browser capabilities: {e}")
    
    async def _initialize_browser_session(self) -> None:
        """Initialize browser session tracking."""
        try:
            # Generate unique session ID
            import uuid
            self.browser_session_id = str(uuid.uuid4())
            
            # Get browser information
            browser_info = await self.page.evaluate("""
                () => ({
                    userAgent: navigator.userAgent,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    url: window.location.href,
                    timestamp: new Date().toISOString()
                })
            """)
            
            # Record session start
            self.lifecycle_events.append({
                "type": "session_start",
                "session_id": self.browser_session_id,
                "browser_info": browser_info,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Browser session initialized: {self.browser_session_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser session: {e}")
    
    async def _setup_automatic_features(self) -> None:
        """Setup automatic browser features based on configuration."""
        try:
            # Setup automatic screenshot capture
            if self.config.get("auto_screenshot", False) and self.features_available["screenshot_capture"]:
                await self._setup_automatic_screenshots()
            
            # Setup automatic HTML capture
            if self.config.get("auto_html_capture", False) and self.features_available["html_capture"]:
                await self._setup_automatic_html_capture()
            
            # Setup automatic resource monitoring
            if self.config.get("auto_resource_monitoring", False) and self.features_available["resource_monitoring"]:
                await self._setup_automatic_resource_monitoring()
            
            logger.debug("Automatic browser features setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup automatic features: {e}")
    
    async def _register_event_handlers(self) -> None:
        """Register event handlers for browser lifecycle events."""
        try:
            # Register page error handler
            self.page.on("pageerror", self._on_page_error)
            
            # Register console error handler
            self.page.on("console", self._on_console_message)
            
            # Register response handler
            self.page.on("response", self._on_response)
            
            # Register request handler
            self.page.on("request", self._on_request)
            
            logger.debug("Browser event handlers registered")
            
        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")
    
    async def _on_page_error(self, error: Any) -> None:
        """Handle page error events."""
        try:
            error_info = {
                "type": "page_error",
                "session_id": self.browser_session_id,
                "error": str(error),
                "timestamp": datetime.now().isoformat()
            }
            
            self.lifecycle_events.append(error_info)
            
            # Take screenshot on error if configured
            if self.config.get("screenshot_on_error", True):
                await self.capture_error_screenshot("page_error")
            
            # Capture HTML on error if configured
            if self.config.get("html_capture_on_error", True):
                await self.capture_error_html("page_error")
            
            logger.error(f"Page error in {self.template_name}: {error}")
            
        except Exception as e:
            logger.error(f"Failed to handle page error: {e}")
    
    async def _on_console_message(self, message: Any) -> None:
        """Handle console message events."""
        try:
            if message.type() == "error":
                console_info = {
                    "type": "console_error",
                    "session_id": self.browser_session_id,
                    "message": message.text(),
                    "location": message.location(),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.lifecycle_events.append(console_info)
                logger.warning(f"Console error in {self.template_name}: {message.text()}")
            
        except Exception as e:
            logger.debug(f"Failed to handle console message: {e}")
    
    async def _on_response(self, response: Any) -> None:
        """Handle response events."""
        try:
            # Track important responses
            if response.status >= 400:
                response_info = {
                    "type": "error_response",
                    "session_id": self.browser_session_id,
                    "url": response.url,
                    "status": response.status,
                    "status_text": response.status_text(),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.lifecycle_events.append(response_info)
                logger.warning(f"Error response in {self.template_name}: {response.status} {response.url}")
            
        except Exception as e:
            logger.debug(f"Failed to handle response: {e}")
    
    async def _on_request(self, request: Any) -> None:
        """Handle request events."""
        try:
            # Track important requests
            if request.resource_type in ["xhr", "fetch"]:
                request_info = {
                    "type": "api_request",
                    "session_id": self.browser_session_id,
                    "url": request.url,
                    "method": request.method,
                    "resource_type": request.resource_type,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.lifecycle_events.append(request_info)
                logger.debug(f"API request in {self.template_name}: {request.method} {request.url}")
            
        except Exception as e:
            logger.debug(f"Failed to handle request: {e}")
    
    async def capture_screenshot(
        self,
        filename: Optional[str] = None,
        full_page: bool = True,
        quality: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Capture a screenshot of the current page.
        
        Args:
            filename: Optional filename for the screenshot
            full_page: Whether to capture the full page
            quality: Image quality (for JPEG)
            format_type: Image format (png, jpeg)
            
        Returns:
            Optional[str]: Path to the captured screenshot
        """
        try:
            if not self.features_available["screenshot_capture"]:
                logger.warning("Screenshot capture not available")
                return None
            
            logger.info(f"Capturing screenshot for {self.template_name}")
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.template_name}_{timestamp}.png"
            
            # Set screenshot options
            options = {
                "full_page": full_page,
                "type": format_type or self.config.get("screenshot_format", "png")
            }
            
            # Add quality for JPEG
            if options["type"] == "jpeg" and quality:
                options["quality"] = quality
            elif not quality:
                options["quality"] = self.config.get("screenshot_quality", 80)
            
            # Capture screenshot
            screenshot_path = await self.page.screenshot(
                path=filename,
                **options
            )
            
            # Record screenshot event
            screenshot_info = {
                "type": "screenshot",
                "session_id": self.browser_session_id,
                "filename": filename,
                "path": screenshot_path,
                "options": options,
                "timestamp": datetime.now().isoformat()
            }
            
            self.lifecycle_events.append(screenshot_info)
            
            logger.info(f"Screenshot captured: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    async def capture_html(
        self,
        filename: Optional[str] = None,
        clean: Optional[bool] = None,
        element: Optional[Any] = None
    ) -> Optional[str]:
        """
        Capture HTML content of the current page or element.
        
        Args:
            filename: Optional filename for the HTML file
            clean: Whether to clean the HTML
            element: Optional element to capture HTML from
            
        Returns:
            Optional[str]: Path to the captured HTML file
        """
        try:
            if not self.features_available["html_capture"]:
                logger.warning("HTML capture not available")
                return None
            
            logger.info(f"Capturing HTML for {self.template_name}")
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.template_name}_{timestamp}.html"
            
            # Get HTML content
            if element:
                html_content = await element.inner_html()
            else:
                html_content = await self.page.content()
            
            # Clean HTML if requested
            if clean or self.config.get("html_capture_clean", True):
                html_content = await self._clean_html(html_content)
            
            # Write HTML to file
            html_path = Path(filename)
            html_path.write_text(html_content, encoding='utf-8')
            
            # Record HTML capture event
            html_info = {
                "type": "html_capture",
                "session_id": self.browser_session_id,
                "filename": filename,
                "path": str(html_path),
                "cleaned": clean or self.config.get("html_capture_clean", True),
                "element_captured": element is not None,
                "timestamp": datetime.now().isoformat()
            }
            
            self.lifecycle_events.append(html_info)
            
            logger.info(f"HTML captured: {html_path}")
            return str(html_path)
            
        except Exception as e:
            logger.error(f"Failed to capture HTML: {e}")
            return None
    
    async def _clean_html(self, html_content: str) -> str:
        """
        Clean HTML content by removing scripts and other unwanted elements.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            str: Cleaned HTML content
        """
        try:
            # Use BeautifulSoup to clean HTML if available
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style tags
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Remove comments
                from bs4 import Comment
                for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                    comment.extract()
                
                return str(soup)
                
            except ImportError:
                # Fallback to simple regex cleaning
                import re
                
                # Remove script tags
                html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                
                # Remove style tags
                html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                
                # Remove HTML comments
                html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
                
                return html_content
                
        except Exception as e:
            logger.debug(f"Failed to clean HTML: {e}")
            return html_content
    
    async def capture_error_screenshot(self, error_type: str) -> Optional[str]:
        """
        Capture a screenshot when an error occurs.
        
        Args:
            error_type: Type of error for filename
            
        Returns:
            Optional[str]: Path to the captured screenshot
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.template_name}_error_{error_type}_{timestamp}.png"
            
            return await self.capture_screenshot(filename=filename)
            
        except Exception as e:
            logger.error(f"Failed to capture error screenshot: {e}")
            return None
    
    async def capture_error_html(self, error_type: str) -> Optional[str]:
        """
        Capture HTML content when an error occurs.
        
        Args:
            error_type: Type of error for filename
            
        Returns:
            Optional[str]: Path to the captured HTML
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.template_name}_error_{error_type}_{timestamp}.html"
            
            return await self.capture_html(filename=filename)
            
        except Exception as e:
            logger.error(f"Failed to capture error HTML: {e}")
            return None
    
    async def _setup_automatic_screenshots(self) -> None:
        """Setup automatic screenshot capture."""
        try:
            # This would typically involve setting up periodic screenshots
            # For now, we'll just log that automatic screenshots are enabled
            logger.info("Automatic screenshot capture enabled")
            
        except Exception as e:
            logger.error(f"Failed to setup automatic screenshots: {e}")
    
    async def _setup_automatic_html_capture(self) -> None:
        """Setup automatic HTML capture."""
        try:
            # This would typically involve setting up periodic HTML capture
            # For now, we'll just log that automatic HTML capture is enabled
            logger.info("Automatic HTML capture enabled")
            
        except Exception as e:
            logger.error(f"Failed to setup automatic HTML capture: {e}")
    
    async def _setup_automatic_resource_monitoring(self) -> None:
        """Setup automatic resource monitoring."""
        try:
            # Initialize resource monitoring if available
            if self.features_available["resource_monitoring"]:
                # This would integrate with the resource monitoring system
                logger.info("Automatic resource monitoring enabled")
            
        except Exception as e:
            logger.error(f"Failed to setup automatic resource monitoring: {e}")
    
    def get_browser_session_info(self) -> Dict[str, Any]:
        """
        Get browser session information.
        
        Returns:
            Dict[str, Any]: Browser session information
        """
        return {
            "session_id": self.browser_session_id,
            "template_name": self.template_name,
            "capabilities": self.browser_capabilities,
            "features_available": self.features_available,
            "config": self.config,
            "lifecycle_events_count": len(self.lifecycle_events),
            "session_start": self.lifecycle_events[0]["timestamp"] if self.lifecycle_events else None
        }
    
    def get_lifecycle_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get lifecycle events.
        
        Args:
            event_type: Optional event type filter
            limit: Maximum number of events to return
            
        Returns:
            List[Dict[str, Any]]: Lifecycle events
        """
        events = self.lifecycle_events
        
        # Filter by event type if specified
        if event_type:
            events = [event for event in events if event.get("type") == event_type]
        
        # Return most recent events
        return events[-limit:] if events else []
    
    def get_feature_status(self) -> Dict[str, bool]:
        """
        Get status of available features.
        
        Returns:
            Dict[str, bool]: Feature availability status
        """
        return self.features_available.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update configuration.
        
        Args:
            new_config: New configuration values
        """
        self.config.update(new_config)
        logger.info(f"Browser lifecycle configuration updated: {list(new_config.keys())}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns:
            Dict[str, Any]: Current configuration
        """
        return self.config.copy()
