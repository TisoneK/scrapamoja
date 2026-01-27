"""
Browser Module Lifecycle Management

This module provides the lifecycle management framework for browser components,
following the constitution's Module Lifecycle Management principle.
"""

import asyncio
from typing import Optional, Dict, Any, Callable, Awaitable
from enum import Enum
import structlog

from .exceptions import BrowserError


class ModulePhase(Enum):
    """Module lifecycle phases."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    RECOVERING = "recovering"
    SHUTDOWN = "shutdown"


class ModuleState:
    """Manages module state and lifecycle phases."""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.phase = ModulePhase.INITIALIZING
        self.internal_state: Dict[str, Any] = {}
        self.error_details: Optional[Dict[str, Any]] = None
        self.logger = structlog.get_logger(f"browser.{module_name}")
        
    async def initialize(self, **kwargs) -> None:
        """Initialize the module."""
        self.phase = ModulePhase.INITIALIZING
        self.logger.info("Module initializing", module=self.module_name)
        
    async def activate(self) -> None:
        """Transition to active phase."""
        self.phase = ModulePhase.ACTIVE
        self.logger.info("Module activated", module=self.module_name)
        
    async def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle error and transition to error phase."""
        self.phase = ModulePhase.ERROR
        self.error_details = {
            "error": str(error),
            "type": type(error).__name__,
            "context": context or {}
        }
        self.logger.error(
            "Module error occurred",
            module=self.module_name,
            error=str(error),
            error_type=type(error).__name__,
            context=context
        )
        
    async def recover(self) -> bool:
        """Attempt to recover from error."""
        self.phase = ModulePhase.RECOVERING
        self.logger.info("Module recovering", module=self.module_name)
        # Recovery logic would be implemented by specific modules
        return True
        
    async def shutdown(self) -> None:
        """Shutdown the module."""
        self.phase = ModulePhase.SHUTDOWN
        self.logger.info("Module shutting down", module=self.module_name)
        self.internal_state.clear()
        
    def is_active(self) -> bool:
        """Check if module is in active phase."""
        return self.phase == ModulePhase.ACTIVE
        
    def is_healthy(self) -> bool:
        """Check if module is healthy (not in error or shutdown)."""
        return self.phase in [ModulePhase.INITIALIZING, ModulePhase.ACTIVE, ModulePhase.RECOVERING]


class LifecycleManager:
    """Manages lifecycle for browser modules."""
    
    def __init__(self):
        self.modules: Dict[str, ModuleState] = {}
        self.logger = structlog.get_logger("browser.lifecycle")
        
    def register_module(self, module_name: str) -> ModuleState:
        """Register a new module."""
        if module_name in self.modules:
            raise BrowserError("MODULE_EXISTS", f"Module {module_name} already registered")
            
        module_state = ModuleState(module_name)
        self.modules[module_name] = module_state
        self.logger.info("Module registered", module=module_name)
        return module_state
        
    def get_module(self, module_name: str) -> Optional[ModuleState]:
        """Get module state by name."""
        return self.modules.get(module_name)
        
    async def initialize_all(self) -> None:
        """Initialize all registered modules."""
        for module_name, module_state in self.modules.items():
            await module_state.initialize()
            
    async def activate_all(self) -> None:
        """Activate all registered modules."""
        for module_name, module_state in self.modules.items():
            await module_state.activate()
            
    async def shutdown_all(self) -> None:
        """Shutdown all registered modules."""
        for module_name, module_state in self.modules.items():
            await module_state.shutdown()
            
    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all modules."""
        return {
            name: {
                "phase": state.phase.value,
                "healthy": state.is_healthy(),
                "active": state.is_active(),
                "error_details": state.error_details
            }
            for name, state in self.modules.items()
        }


# Global lifecycle manager instance
lifecycle_manager = LifecycleManager()
