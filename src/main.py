#!/usr/bin/env python3
"""
Scorewise CLI main entry point.

Provides unified command-line interface for all scraping operations.
"""

import asyncio
import sys
import importlib
import signal
import logging
import warnings
import os

# Suppress asyncio cleanup warnings on Windows
if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", message=".*unclosed transport.*")
    warnings.filterwarnings("ignore", message=".*I/O operation on closed pipe.*")
    
    # Directly suppress asyncio proactor cleanup errors
    try:
        import asyncio.proactor_events
        # Override the _warn function to suppress transport cleanup errors
        original_warn = asyncio.proactor_events._warn
        
        def suppressed_warn(message, category=None, source=None):
            if (isinstance(message, str) and 
                ("unclosed transport" in message or "closed pipe" in message)):
                return
            return original_warn(message, category, source)
        
        asyncio.proactor_events._warn = suppressed_warn
    except (ImportError, AttributeError):
        pass
    
    # Also suppress the print statements for these specific errors
    import builtins
    original_print = builtins.print
    
    def suppressed_print(*args, **kwargs):
        # Filter out asyncio cleanup errors
        if args and any("Exception ignored while calling deallocator" in str(arg) for arg in args):
            return
        if args and any("I/O operation on closed pipe" in str(arg) for arg in args):
            return
        return original_print(*args, **kwargs)
    
    builtins.print = suppressed_print

# Import logging configuration first
from src.core.logging_config import JsonLoggingConfigurator

# Import shutdown coordination
from src.core.shutdown import ShutdownCoordinator

# Import interrupt handling
from src.interrupt_handling.compatibility import create_compatible_handler
from src.interrupt_handling.config import InterruptConfig


# Site registry - maps site names to their CLI class paths
SITE_CLIS = {
    'flashscore': ('src.sites.flashscore.cli.main', 'FlashscoreCLI'),
    'wikipedia': ('src.sites.wikipedia.cli.main', 'WikipediaCLI'),
}


async def cli():
    """Main CLI entry point with graceful shutdown support."""
    import sys
    
    # Get logger for CLI operations
    from src.observability.logger import get_logger
    cli_logger = get_logger("cli")
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <site> <command> ...")
        print(f"Available sites: {', '.join(SITE_CLIS.keys())}")
        print("Example: python -m src.main flashscore scrape basketball scheduled --limit 1")
        return 1
    
    site_name = sys.argv[1]
    
    if site_name not in SITE_CLIS:
        print(f"Unknown site: {site_name}")
        print(f"Available sites: {', '.join(SITE_CLIS.keys())}")
        return 1
    
    # Check for verbose flag before importing site CLI
    verbose = '--verbose' in sys.argv
    
    # Initialize logging with verbose flag
    JsonLoggingConfigurator.setup(verbose=verbose)
    
    # Initialize shutdown coordinator
    shutdown_coordinator = ShutdownCoordinator()
    
    # Get logger for shutdown coordinator (use centralized JSON logger)
    from src.observability.logger import get_logger
    logger = get_logger("shutdown_coordinator")
    shutdown_coordinator.set_logger(logger)
    
    # Setup signal handlers through coordinator
    shutdown_coordinator.setup_signal_handlers()
    
    # Initialize interrupt handling (for compatibility with existing system)
    config = InterruptConfig.from_env()
    interrupt_handler = create_compatible_handler(config)
    
    try:
        # Import the site's CLI module and class
        module_path, class_name = SITE_CLIS[site_name]
        module = importlib.import_module(module_path)
        site_cli_class = getattr(module, class_name)
        site_cli = site_cli_class()
        
        # Create parser and parse remaining args
        parser = site_cli.create_parser()
        args = parser.parse_args(sys.argv[2:])
        
        # Run the site CLI with shutdown coordination
        result = await site_cli.run(args, interrupt_handler=interrupt_handler, shutdown_coordinator=shutdown_coordinator)
        
        # Normal shutdown through coordinator
        if not shutdown_coordinator.is_shutting_down():
            shutdown_success = await shutdown_coordinator.shutdown()
            return 0 if shutdown_success else 1
        
        return result
        
    except KeyboardInterrupt:
        cli_logger.info("Operation cancelled by user")
        # Graceful shutdown through coordinator
        try:
            shutdown_success = await shutdown_coordinator.shutdown()
            return 0 if shutdown_success else 1
        except Exception as e:
            cli_logger.error("Error during shutdown", extra={"error": str(e)})
            return 1
    except Exception as e:
        cli_logger.error("Error", extra={"error": str(e)})
        if config.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        
        # Attempt graceful shutdown even on error
        try:
            await shutdown_coordinator.shutdown()
        except Exception as shutdown_error:
            cli_logger.error("Error during shutdown", extra={"error": str(shutdown_error)})
        
        return 1


if __name__ == "__main__":
    asyncio.run(cli())
