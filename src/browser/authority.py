"""
Browser Authority Implementation

This module implements the BrowserAuthority class for centralized browser management,
following the IBrowserAuthority interface.
"""

import asyncio
import time
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

try:
    from playwright.async_api import Browser, BrowserType, Playwright
except ImportError:
    Browser = BrowserType = Playwright = None

from .interfaces import IBrowserAuthority, IBrowserSession
from .models.session import BrowserSession, BrowserConfiguration, SessionStatus
from .models.metrics import ResourceMetrics
from .monitoring import ResourceMonitor, get_resource_monitor
from .state_manager import StateManager
from .session_manager import BrowserSessionManager
from .configuration import get_configuration_manager
from .exceptions import BrowserError, SessionCreationError, ResourceExhaustionError, ConfigurationError
from .lifecycle import ModuleState, lifecycle_manager
from .resilience import resilience_manager
from ..config.settings import get_config
from .snapshot import DOMSnapshotManager, get_snapshot_manager


class BrowserAuthority(IBrowserAuthority):
    """Central authority for browser instance management and lifecycle control."""
    
    def __init__(self):
        # Configuration
        self.config = get_config()
        
        # Browser instances
        self.playwright: Optional[Playwright] = None
        self.browser_instances: Dict[str, Browser] = {}
        
        # Session management
        self.sessions: Dict[str, BrowserSessionManager] = {}
        self.session_configurations: Dict[str, BrowserConfiguration] = {}
        
        # Managers
        self.resource_monitor = get_resource_monitor()
        self.state_manager = StateManager()
        self.configuration_manager = get_configuration_manager()
        self.snapshot_manager = get_snapshot_manager()
        
        # Lifecycle state
        self.lifecycle_state = lifecycle_manager.register_module("browser_authority")
        
        # Logging
        self.logger = structlog.get_logger("browser.authority")
        
        # Statistics
        self.stats = {
            "total_sessions_created": 0,
            "total_sessions_terminated": 0,
            "active_sessions": 0,
            "peak_concurrent_sessions": 0,
            "start_time": time.time()
        }
        
    async def initialize(self) -> bool:
        """Initialize the browser authority."""
        try:
            await self.lifecycle_state.initialize()
            
            # Initialize Playwright
            if Playwright:
                self.playwright = await Playwright().start()
                self.logger.info("Playwright initialized successfully")
            else:
                raise BrowserError("PLAYWRIGHT_NOT_AVAILABLE", "Playwright is not available")
                
            # Initialize resource monitor
            await self.resource_monitor.initialize()
            
            await self.lifecycle_state.activate()
            
            self.logger.info("Browser authority initialized")
            return True
            
        except Exception as e:
            await self.lifecycle_state.handle_error(e)
            self.logger.error(
                "Failed to initialize browser authority",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def create_session(
        self, 
        configuration: Optional[BrowserConfiguration] = None
    ) -> BrowserSession:
        """Create a new browser session with optional configuration."""
        try:
            # Generate session ID
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            # Use provided configuration or get default
            if configuration is None:
                configuration = self.configuration_manager.get_default_configuration()
            else:
                # Validate the configuration
                validation_result = self.configuration_manager.validate_configuration(configuration)
                if not validation_result.is_valid:
                    raise ConfigurationError(
                        "configuration",
                        "validation_failed",
                        f"Configuration validation failed: {'; '.join(validation_result.errors)}",
                        config_id=configuration.config_id
                    )
                    
                # Cache the configuration
                self.configuration_manager._config_cache[configuration.config_id] = configuration
                
            # Check session limits
            if len(self.sessions) >= self.config.browser.max_concurrent_sessions:
                raise ResourceExhaustionError(
                    "SESSION_LIMIT_EXCEEDED",
                    f"Maximum concurrent sessions ({self.config.browser.max_concurrent_sessions}) exceeded",
                    resource_type="sessions",
                    current_usage=len(self.sessions),
                    threshold=self.config.browser.max_concurrent_sessions
                )
                
            # Create browser instance if needed
            browser_type = configuration.browser_type
            if browser_type not in self.browser_instances:
                await self._create_browser_instance(browser_type)
                
            browser = self.browser_instances[browser_type]
            
            # Create browser session entity
            session = BrowserSession(
                session_id=session_id,
                browser_type=browser_type,
                configuration=configuration
            )
            
            # Create session manager
            session_manager = BrowserSessionManager(
                session=session,
                playwright_browser=browser,
                state_manager=self.state_manager
            )
            
            # Initialize session
            await session_manager.initialize()
            
            # Store session
            self.sessions[session_id] = session_manager
            self.session_configurations[session_id] = configuration
            
            # Start resource monitoring
            await self.resource_monitor.start_monitoring(session_id)
            
            # Update statistics
            self.stats["total_sessions_created"] += 1
            self.stats["active_sessions"] = len(self.sessions)
            self.stats["peak_concurrent_sessions"] = max(
                self.stats["peak_concurrent_sessions"],
                self.stats["active_sessions"]
            )
            
            self.logger.info(
                "Browser session created",
                session_id=session_id,
                browser_type=browser_type,
                headless=configuration.headless,
                active_sessions=self.stats["active_sessions"],
                config_id=configuration.config_id
            )
            
            return session
            
        except Exception as e:
            self.logger.error(
                "Failed to create browser session",
                error=str(e),
                error_type=type(e).__name__
            )
            raise SessionCreationError(
                "SESSION_CREATION_FAILED",
                f"Failed to create session: {str(e)}",
                session_id=session_id if 'session_id' in locals() else None
            )
            
    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Retrieve an existing browser session by ID."""
        try:
            session_manager = self.sessions.get(session_id)
            if session_manager:
                return session_manager.session
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get session",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def list_sessions(self, status_filter: Optional[SessionStatus] = None) -> List[BrowserSession]:
        """List all browser sessions, optionally filtered by status."""
        try:
            sessions = []
            
            for session_manager in self.sessions.values():
                session = session_manager.session
                
                if status_filter is None or session.status == status_filter:
                    sessions.append(session)
                    
            return sessions
            
        except Exception as e:
            self.logger.error(
                "Failed to list sessions",
                status_filter=status_filter.value if status_filter else None,
                error=str(e),
                error_type=type(e).__name__
            )
            return []
            
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a browser session gracefully."""
        try:
            session_manager = self.sessions.get(session_id)
            if not session_manager:
                self.logger.warning(
                    "Session not found for termination",
                    session_id=session_id
                )
                return False
                
            # Stop resource monitoring
            await self.resource_monitor.stop_monitoring(session_id)
            
            # Shutdown session
            success = await session_manager.shutdown()
            
            if success:
                # Remove from active sessions
                del self.sessions[session_id]
                del self.session_configurations[session_id]
                
                # Update statistics
                self.stats["total_sessions_terminated"] += 1
                self.stats["active_sessions"] = len(self.sessions)
                
                self.logger.info(
                    "Browser session terminated",
                    session_id=session_id,
                    active_sessions=self.stats["active_sessions"]
                )
                
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to terminate session",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def cleanup_resources(self, session_id: str) -> bool:
        """Force cleanup of session resources."""
        try:
            session_manager = self.sessions.get(session_id)
            if not session_manager:
                self.logger.warning(
                    "Session not found for cleanup",
                    session_id=session_id
                )
                return False
                
            # Get current metrics
            metrics = await self.resource_monitor.get_metrics(session_id)
            
            # Determine cleanup level based on resource usage
            from .models.enums import CleanupLevel
            
            if metrics.is_critical():
                cleanup_level = CleanupLevel.AGGRESSIVE
            elif metrics.is_warning():
                cleanup_level = CleanupLevel.MODERATE
            else:
                cleanup_level = CleanupLevel.GENTLE
                
            # Trigger cleanup
            success = await self.resource_monitor.trigger_cleanup(session_id, cleanup_level)
            
            self.logger.info(
                "Resource cleanup completed",
                session_id=session_id,
                cleanup_level=cleanup_level.value,
                success=success,
                memory_mb=metrics.memory_usage_mb,
                cpu_percent=metrics.cpu_usage_percent
            )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup resources",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def get_system_metrics(self) -> ResourceMetrics:
        """Get system-wide browser resource metrics."""
        try:
            # Aggregate metrics from all sessions
            total_memory = 0.0
            total_cpu = 0.0
            total_tabs = 0
            total_handles = 0
            
            for session_manager in self.sessions.values():
                metrics = await self.resource_monitor.get_metrics(session_manager.session.session_id)
                total_memory += metrics.memory_usage_mb
                total_cpu += metrics.cpu_usage_percent
                total_tabs += metrics.open_tabs_count
                total_handles += metrics.process_handles_count
                
            # Create system metrics
            system_metrics = ResourceMetrics(
                session_id="system",
                memory_usage_mb=total_memory,
                cpu_usage_percent=total_cpu / len(self.sessions) if self.sessions else 0.0,
                network_requests_count=0,
                open_tabs_count=total_tabs,
                process_handles_count=total_handles
            )
            
            return system_metrics
            
        except Exception as e:
            self.logger.error(
                "Failed to get system metrics",
                error=str(e),
                error_type=type(e).__name__
            )
            return ResourceMetrics(session_id="system")
            
    async def get_active_session_count(self) -> int:
        """Get count of active browser sessions."""
        return len(self.sessions)
        
    async def shutdown_all_sessions(self) -> Dict[str, bool]:
        """Shutdown all sessions, returning success status per session."""
        try:
            results = {}
            session_ids = list(self.sessions.keys())
            
            for session_id in session_ids:
                success = await self.terminate_session(session_id)
                results[session_id] = success
                
            self.logger.info(
                "All sessions shutdown completed",
                total_sessions=len(session_ids),
                successful=sum(results.values()),
                failed=len(results) - sum(results.values())
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to shutdown all sessions",
                error=str(e),
                error_type=type(e).__name__
            )
            return {}
            
    async def shutdown(self) -> None:
        """Shutdown the browser authority."""
        try:
            # Shutdown all sessions
            await self.shutdown_all_sessions()
            
            # Close browser instances
            for browser_type, browser in self.browser_instances.items():
                await browser.close()
                self.logger.info(f"Browser instance closed: {browser_type}")
                
            self.browser_instances.clear()
            
            # Stop Playwright
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            # Shutdown resource monitor
            await self.resource_monitor.shutdown()
            
            await self.lifecycle_state.shutdown()
            
            self.logger.info("Browser authority shutdown completed")
            
        except Exception as e:
            self.logger.error(
                "Failed to shutdown browser authority",
                error=str(e),
                error_type=type(e).__name__
            )
            
    async def get_authority_status(self) -> Dict[str, Any]:
        """Get comprehensive authority status."""
        try:
            uptime = time.time() - self.stats["start_time"]
            
            status = {
                "uptime_seconds": uptime,
                "playwright_available": self.playwright is not None,
                "browser_instances": list(self.browser_instances.keys()),
                "statistics": self.stats.copy(),
                "monitoring_status": await self.resource_monitor.get_monitoring_status(),
                "sessions": {}
            }
            
            # Add session details
            for session_id, session_manager in self.sessions.items():
                session = session_manager.session
                status["sessions"][session_id] = {
                    "browser_type": session.browser_type,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "context_count": len(session.contexts),
                    "configuration": session.configuration.to_dict()
                }
                
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get authority status",
                error=str(e),
                error_type=type(e).__name__
            )
            return {"error": str(e)}
            
    async def get_configuration(self, config_id: str) -> Optional[BrowserConfiguration]:
        """Get a browser configuration by ID."""
        return self.configuration_manager.get_configuration(config_id)
        
    async def create_configuration(
        self,
        config_id: str,
        browser_type: str,
        **kwargs
    ) -> BrowserConfiguration:
        """Create a new browser configuration."""
        config = self.configuration_manager.create_configuration(config_id, browser_type, **kwargs)
        
        self.logger.info(
            "Browser configuration created",
            config_id=config_id,
            browser_type=browser_type
        )
        
        return config
        
    async def update_configuration(
        self,
        config_id: str,
        **updates
    ) -> BrowserConfiguration:
        """Update an existing browser configuration."""
        config = self.configuration_manager.update_configuration(config_id, **updates)
        
        self.logger.info(
            "Browser configuration updated",
            config_id=config_id,
            updates=updates
        )
        
        return config
        
    async def delete_configuration(self, config_id: str) -> bool:
        """Delete a browser configuration."""
        success = self.configuration_manager.delete_configuration(config_id)
        
        if success:
            self.logger.info(
                "Browser configuration deleted",
                config_id=config_id
            )
        else:
            self.logger.warning(
                "Browser configuration not found for deletion",
                config_id=config_id
            )
            
        return success
        
    async def list_configurations(self) -> List[str]:
        """List all available browser configurations."""
        return self.configuration_manager.list_configurations()
        
    async def validate_configuration(self, config: BrowserConfiguration) -> bool:
        """Validate a browser configuration."""
        validation_result = self.configuration_manager.validate_configuration(config)
        
        if validation_result.is_valid:
            self.logger.info(
                "Configuration validation passed",
                config_id=config.config_id
            )
        else:
            self.logger.error(
                "Configuration validation failed",
                config_id=config.config_id,
                errors=validation_result.errors
            )
            
        return validation_result.is_valid
        
    async def clone_configuration(self, source_config_id: str, new_config_id: str) -> BrowserConfiguration:
        """Clone an existing configuration."""
        config = self.configuration_manager.clone_configuration(source_config_id, new_config_id)
        
        self.logger.info(
            "Browser configuration cloned",
            source_config_id=source_config_id,
            new_config_id=new_config_id
        )
        
        return config
        
    async def export_configuration(self, config_id: str, file_path: str) -> bool:
        """Export configuration to file."""
        success = self.configuration_manager.export_configuration(config_id, file_path)
        
        if success:
            self.logger.info(
                "Configuration exported",
                config_id=config_id,
                file_path=file_path
            )
            
        return success
        
    async def import_configuration(self, file_path: str, config_id: Optional[str] = None) -> BrowserConfiguration:
        """Import configuration from file."""
        config = self.configuration_manager.import_configuration(file_path, config_id)
        
        self.logger.info(
            "Configuration imported",
            config_id=config.config_id,
            file_path=file_path
        )
        
        return config
        
    async def get_default_configuration(self) -> BrowserConfiguration:
        """Get the default browser configuration."""
        return self.configuration_manager.get_default_configuration()
            
    async def _create_browser_instance(self, browser_type: str) -> None:
        """Create a browser instance of the specified type."""
        try:
            if not self.playwright:
                raise BrowserError("PLAYWRIGHT_NOT_INITIALIZED", "Playwright is not initialized")
                
            # Map browser type to Playwright browser type
            browser_mapping = {
                "chromium": self.playwright.chromium,
                "firefox": self.playwright.firefox,
                "webkit": self.playwright.webkit
            }
            
            if browser_type not in browser_mapping:
                raise BrowserError(
                    "UNSUPPORTED_BROWSER_TYPE",
                    f"Browser type {browser_type} is not supported",
                    config_field="browser_type",
                    config_value=browser_type
                )
                
            browser_launcher = browser_mapping[browser_type]
            
            # Launch browser with stealth options if enabled
            launch_options = {
                "headless": self.config.browser.default_headless
            }
            
            # Add stealth options if enabled
            if self.config.browser.stealth_enabled:
                stealth_args = [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--disable-gpu"
                ]
                # Note: --no-zygote is intentionally omitted as it can cause hangs on Windows
                launch_options.update({
                    "args": stealth_args
                })
                
            browser = await browser_launcher.launch(**launch_options)
            self.browser_instances[browser_type] = browser
            
            self.logger.info(
                "Browser instance created",
                browser_type=browser_type,
                headless=launch_options["headless"]
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to create browser instance",
                browser_type=browser_type,
                error=str(e),
                error_type=type(e).__name__
            )
            raise BrowserError(
                "BROWSER_LAUNCH_FAILED",
                f"Failed to launch {browser_type} browser: {str(e)}",
                config_field="browser_type",
                config_value=browser_type
            )


# Global browser authority instance
browser_authority = BrowserAuthority()


def get_browser_authority() -> BrowserAuthority:
    """Get the global browser authority instance."""
    return browser_authority
