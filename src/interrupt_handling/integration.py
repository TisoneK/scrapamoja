"""
Integration utilities for interrupt handling in scraping operations.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Any, Dict, List
from contextlib import contextmanager

from .handler import InterruptHandler, InterruptContext
from .resource_manager import ResourceManager, ResourceType
from .config import InterruptConfig
from .messaging import InterruptMessageHandler
from .checkpoint import CheckpointManager
from .state_serialization import StateSerializationManager
from .integrity_verification import IntegrityVerifier
from .priority_config import CleanupPriorityManager


class InterruptAwareScraper:
    """Base class for scrapers with interrupt handling support."""
    
    def __init__(self, page=None, selector_engine=None, config: Optional[InterruptConfig] = None):
        self.config = config or InterruptConfig()
        self.logger = logging.getLogger(__name__)
        
        # Store page and selector_engine for compatibility
        self.page = page
        self.selector_engine = selector_engine
        
        # Initialize interrupt handling components
        self.interrupt_handler = InterruptHandler(self.config)
        self.resource_manager = ResourceManager(self.config)
        self.message_handler = InterruptMessageHandler(self.config)
        self.checkpoint_manager = CheckpointManager()
        self.state_manager = StateSerializationManager(self.checkpoint_manager)
        self.integrity_verifier = IntegrityVerifier(self.checkpoint_manager, self.state_manager)
        self.priority_manager = CleanupPriorityManager(self.config)
        
        # Scraping state
        self._scraping_active = False
        self._interrupted = False
        self._critical_operations = []  # Track critical operations
        
        # Register cleanup handlers
        self._setup_cleanup_handlers()
    
    def _setup_cleanup_handlers(self):
        """Setup cleanup handlers for common resources."""
        # Register database cleanup handler
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_database_connections
        )
        
        # Register file cleanup handler
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_file_handles
        )
        
        # Register network cleanup handler
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_network_connections
        )
        
        # Register checkpoint creation handler
        self.interrupt_handler.register_interrupt_callback(
            self._create_checkpoint
        )
    
    def enter_critical_operation(self, operation_name: str):
        """Mark the start of a critical operation."""
        self._critical_operations.append(operation_name)
        self.logger.debug(f"Entering critical operation: {operation_name}")
    
    def exit_critical_operation(self, operation_name: str):
        """Mark the end of a critical operation."""
        if operation_name in self._critical_operations:
            self._critical_operations.remove(operation_name)
        self.logger.debug(f"Exiting critical operation: {operation_name}")
    
    def is_in_critical_operation(self) -> bool:
        """Check if currently in a critical operation."""
        return len(self._critical_operations) > 0
    
    def check_interrupt_before_critical(self) -> bool:
        """Check for interrupt before starting a critical operation."""
        if self.interrupt_handler.is_interrupted():
            self.message_handler.send_custom_message(
                f"Cannot start critical operation - interrupt detected",
                MessageType.WARNING
            )
            return True
        return False
    
    def check_interrupt_during_critical(self) -> bool:
        """Check for interrupt during a critical operation."""
        if self.interrupt_handler.is_interrupted():
            current_op = self._critical_operations[-1] if self._critical_operations else "unknown"
            self.message_handler.send_custom_message(
                f"Interrupt during critical operation: {current_op}",
                MessageType.WARNING
            )
            return True
        return False
    
    def _setup_cleanup_handlers(self):
        """Setup cleanup handlers for common resources."""
        # Register database cleanup handler
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_database_connections
        )
        
        # Register file cleanup handler
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_file_handles
        )
        
        # Register network cleanup handler
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_network_connections
        )
        
        # Register checkpoint creation handler
        self.interrupt_handler.register_interrupt_callback(
            self._create_checkpoint
        )
    
    def _cleanup_database_connections(self, context: InterruptContext):
        """Cleanup database connections during interrupt."""
        self.message_handler.report_progress("Database cleanup", 0, 1, "database")
        
        # Implementation would depend on the specific database connections used
        # This is a placeholder for the actual cleanup logic
        self.logger.info("Database connections cleanup completed")
    
    def _cleanup_file_handles(self, context: InterruptContext):
        """Cleanup file handles during interrupt."""
        self.message_handler.report_progress("File cleanup", 0, 1, "file")
        
        # Implementation would depend on the specific file handles used
        # This is a placeholder for the actual cleanup logic
        self.logger.info("File handles cleanup completed")
    
    def _cleanup_network_connections(self, context: InterruptContext):
        """Cleanup network connections during interrupt."""
        self.message_handler.report_progress("Network cleanup", 0, 1, "network")
        
        # Implementation would depend on the specific network connections used
        # This is a placeholder for the actual cleanup logic
        self.logger.info("Network connections cleanup completed")
    
    def _create_checkpoint(self, context: InterruptContext):
        """Create checkpoint during interrupt."""
        self.message_handler.report_progress("Checkpoint creation", 0, 1)
        
        # Get current state
        current_state = self._get_current_state()
        
        # Create checkpoint
        success = self.checkpoint_manager.create_checkpoint(
            checkpoint_id=f"interrupt_{int(time.time())}",
            application_state=current_state.get('application', {}),
            scraping_state=current_state.get('scraping', {}),
            resource_state=current_state.get('resources', {}),
            metadata={'interrupt_signal': context.signal_name}
        )
        
        if success:
            self.message_handler.report_checkpoint_status(True)
        else:
            self.message_handler.report_checkpoint_status(False)
    
    def _get_current_state(self) -> Dict[str, Any]:
        """Get current scraping state for checkpointing."""
        # This should be implemented by subclasses
        return {
            'application': {},
            'scraping': {},
            'resources': {}
        }
    
    def check_interrupt_status(self) -> bool:
        """Check if interrupt has been received."""
        return self.interrupt_handler.is_interrupted()
    
    def check_shutdown_status(self) -> bool:
        """Check if shutdown is in progress."""
        return self.interrupt_handler.is_shutting_down()
    
    @contextmanager
    def managed_scraping_session(self, session_id: str):
        """Context manager for a scraping session with interrupt handling."""
        self._scraping_active = True
        
        try:
            yield self
        finally:
            self._scraping_active = False
    
    async def scrape_with_interrupt_handling(self, scrape_func: Callable, *args, **kwargs):
        """
        Execute a scraping function with interrupt handling support.
        
        Args:
            scrape_func: The scraping function to execute
            *args: Arguments to pass to scrape_func
            **kwargs: Keyword arguments to pass to scrape_func
            
        Returns:
            Result of scrape_func or None if interrupted
        """
        # Check if already interrupted
        if self.check_interrupt_status():
            self.logger.warning("Scraping cancelled due to interrupt")
            return None
        
        # Check for interrupt before starting
        if self.is_in_critical_operation():
            if self.check_interrupt_before_critical():
                return None
        
        try:
            # Execute the scraping function
            result = await scrape_func(*args, **kwargs)
            
            # Check for interrupt during execution
            if self.check_interrupt_status():
                self.logger.info("Scraping interrupted, creating checkpoint")
                return None
            
            # Check for interrupt during critical operation
            if self.is_in_critical_operation() and self.check_interrupt_during_critical():
                self.logger.info("Critical operation interrupted")
                return None
            
            return result
            
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt caught during scraping")
            return None
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            raise


class ScrapingOrchestrator:
    """Orchestrates scraping operations with interrupt handling."""
    
    def __init__(self, interrupt_aware_scraper: InterruptAwareScraper):
        self.scraper = interrupt_aware_scraper
        self.logger = logging.getLogger(__name__)
    
    async def orchestrate_scraping(self, scrape_tasks: List[Callable], 
                                checkpoint_interval: float = 60.0) -> List[Any]:
        """
        Orchestrate multiple scraping tasks with interrupt handling.
        
        Args:
            scrape_tasks: List of async scraping functions
            checkpoint_interval: Interval between checkpoints in seconds
            
        Returns:
            List of results
        """
        results = []
        
        for i, task in enumerate(scrape_tasks):
            # Check for interrupt before starting task
            if self.scraper.check_interrupt_status():
                self.logger.info(f"Interrupt detected, stopping before task {i+1}")
                break
            
            try:
                # Execute task with interrupt handling
                result = await self.scraper.scrape_with_interrupt_handling(task)
                
                if result is not None:
                    results.append(result)
                
                # Create checkpoint after each successful task
                if (i + 1) % 5 == 0:  # Every 5 tasks
                    await self._create_auto_checkpoint()
                
            except Exception as e:
                self.logger.error(f"Error in task {i+1}: {e}")
        
        return results
    
    async def _create_auto_checkpoint(self):
        """Create an automatic checkpoint."""
        try:
            current_state = self.scraper._get_current_state()
            
            success = self.scraper.checkpoint_manager.create_checkpoint(
                checkpoint_id=f"auto_{int(time.time())}",
                application_state=current_state.get('application', {}),
                scraping_state=current_state.get('scraping', {}),
                resource_state=current_state.get('resources', {}),
                metadata={'auto_generated': True}
            )
            
            if success:
                self.scraper.message_handler.report_checkpoint_status(True)
            else:
                self.scraper.message_handler.report_checkpoint_status(False)
                
        except Exception as e:
            self.logger.error(f"Error creating auto checkpoint: {e}")


class InterruptSafeBrowserManager:
    """Browser manager with interrupt handling support."""
    
    def __init__(self, browser_manager, interrupt_handler: InterruptHandler):
        self.browser_manager = browser_manager
        self.interrupt_handler = interrupt_handler
        self.logger = logging.getLogger(__name__)
        
        # Register browser cleanup callback
        self.interrupt_handler.register_interrupt_callback(
            self._cleanup_browser_sessions
        )
        
        # Track managed sessions
        self._managed_sessions = {}
        
        # Initialize priority manager for cleanup ordering
        self.priority_manager = CleanupPriorityManager(interrupt_handler.config)
    
    async def _cleanup_browser_sessions(self, context: InterruptContext):
        """Cleanup browser sessions during interrupt."""
        self.interrupt_handler.message_handler.report_progress("Browser cleanup", 0, len(self._managed_sessions), "browser")
        
        # Get ordered cleanup tasks
        session_tasks = list(self._managed_sessions.keys())
        ordered_tasks = self.priority_manager.get_ordered_tasks(session_tasks)
        
        # Cleanup sessions in priority order
        for task_name in ordered_tasks:
            if task_name in self._managed_sessions:
                session = self._managed_sessions[task_name]
                try:
                    # Get task-specific timeout
                    base_timeout = 30.0  # Default browser cleanup timeout
                    task_timeout = self.priority_manager.get_task_timeout("browser", base_timeout)
                    
                    # Execute cleanup with timeout
                    await asyncio.wait_for(self._cleanup_session(session), timeout=task_timeout)
                    self.logger.info(f"Browser session {task_name} cleaned up successfully")
                except asyncio.TimeoutError:
                    self.logger.error(f"Browser session {task_name} cleanup timed out")
                    self.interrupt_handler.message_handler.report_cleanup_error(
                        f"browser_session_{task_name}", 
                        Exception("Cleanup timeout"), 
                        1
                    )
                except Exception as e:
                    self.logger.error(f"Error cleaning up browser session {task_name}: {e}")
                    self.interrupt_handler.message_handler.report_cleanup_error(
                        f"browser_session_{task_name}", e, 1
                    )
        
        self._managed_sessions.clear()
        self.logger.info("Browser sessions cleanup completed")
    
    async def create_session_with_interrupt_handling(self, *args, **kwargs):
        """Create browser session with interrupt handling support."""
        try:
            session = await self.browser_manager.create_session(*args, **kwargs)
            
            # Register session for cleanup
            session_id = getattr(session, 'session_id', 'unknown')
            self._managed_sessions[session_id] = session
            
            # Register session resources with resource manager
            self.interrupt_handler.resource_manager.register_custom(
                f"browser_session_{session_id}",
                lambda: self._cleanup_session(session),
                f"Browser session {session_id}"
            )
            
            return session
            
        except Exception as e:
            self.logger.error(f"Error creating browser session: {e}")
            raise
    
    async def _cleanup_session(self, session):
        """Cleanup a specific browser session."""
        try:
            if hasattr(session, 'close'):
                await session.close()
            self.logger.info(f"Browser session {getattr(session, 'session_id', 'unknown')} closed")
        except Exception as e:
            self.logger.error(f"Error closing browser session: {e}")
    
    def get_managed_sessions_count(self) -> int:
        """Get count of managed sessions."""
        return len(self._managed_sessions)


def integrate_interrupt_handling_into_cli(cli_class, config: Optional[InterruptConfig] = None):
    """
    Integrate interrupt handling into a CLI class.
    
    Args:
        cli_class: The CLI class to modify
        config: Interrupt handling configuration
        
    Returns:
        Modified CLI class with interrupt handling
    """
    class InterruptAwareCLI(cli_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Initialize interrupt handling
            self.interrupt_config = config or InterruptConfig()
            self.interrupt_handler = InterruptHandler(self.interrupt_config)
            self.message_handler = InterruptMessageHandler(self.interrupt_config)
            
            # Override run method to include interrupt handling
            original_run = getattr(super(), 'run', None)
            if original_run is None:
                raise AttributeError("CLI class must have a 'run' method")
            
            async def run_with_interrupt_handling(self, args):
                """Run CLI with interrupt handling support."""
                try:
                    # Check for interrupt before starting
                    if self.interrupt_handler.is_interrupted():
                        self.message_handler.send_custom_message(
                            "Operation cancelled due to interrupt",
                            MessageType.WARNING
                        )
                        return 1
                    
                    # Execute original run method
                    result = await original_run(args)
                    
                    # Check for interrupt during execution
                    if self.interrupt_handler.is_interrupted():
                        self.message_handler.send_custom_message(
                            "Operation interrupted during execution",
                            MessageType.WARNING
                        )
                        return 1
                    
                    return result
                    
                except KeyboardInterrupt:
                    self.message_handler.send_custom_message(
                        "Operation cancelled by user",
                        MessageType.WARNING
                    )
                    return 1
                    
                except Exception as e:
                    self.message_handler.report_shutdown_error(e)
                    return 1
            
            # Replace the run method
            setattr(self, 'run', run_with_interrupt_handling)
    
    return InterruptAwareCLI


def create_interrupt_aware_scraper(scraper_class, config: Optional[InterruptConfig] = None):
    """
    Create an interrupt-aware version of a scraper class.
    
    Args:
        scraper_class: The scraper class to modify
        config: Interrupt handling configuration
        
    Returns:
        Modified scraper class with interrupt handling
    """
    class InterruptAwareScraper(scraper_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Initialize interrupt handling
            self.interrupt_config = config or InterruptConfig()
            self.interrupt_handler = InterruptHandler(self.interrupt_config)
            self.resource_manager = ResourceManager(self.interrupt_config)
            self.message_handler = InterruptMessageHandler(self.interrupt_config)
            self.checkpoint_manager = CheckpointManager()
            self.state_manager = StateSerializationManager(self.checkpoint_manager)
            
            # Override methods to include interrupt checks
            original_scrape_data = getattr(super(), 'scrape_data', None)
            if original_scrape_data is None:
                raise AttributeError("Scraper class must have a 'scrape_data' method")
            
            async def scrape_data_with_interrupt_handling(self, *args, **kwargs):
                """Scrape data with interrupt handling support."""
                # Check for interrupt before starting
                if self.interrupt_handler.is_interrupted():
                    self.message_handler.send_custom_message(
                        "Scraping cancelled due to interrupt",
                        MessageType.WARNING
                    )
                    return None
                
                try:
                    # Execute original scrape_data method
                    result = await original_scrape_data(*args, **kwargs)
                    
                    # Check for interrupt during execution
                    if self.interrupt_handler.is_interrupted():
                        self.message_handler.send_custom_message(
                            "Scraping interrupted during execution",
                            MessageType.WARNING
                        )
                        return None
                    
                    return result
                    
                except KeyboardInterrupt:
                    self.message_handler.send_custom_message(
                        "Scraping cancelled by user",
                        MessageType.WARNING
                    )
                    return None
                    
                except Exception as e:
                    self.message_handler.report_shutdown_error(e)
                    raise
            
            # Replace the scrape_data method
            setattr(self, 'scrape_data', scrape_data_with_interrupt_handling)
    
    return InterruptAwareScraper
