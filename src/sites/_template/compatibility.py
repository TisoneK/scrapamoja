"""
Backward compatibility layer for existing flow imports.

This module provides compatibility shims and deprecation warnings
to ensure existing sites continue to work with the new template architecture.
"""

import warnings
import importlib
from typing import Any, Dict, Optional, Union
from pathlib import Path

# Import new base classes
try:
    from .base_flows import (
        BaseNavigationFlow as _BaseNavigationFlow,
        BaseExtractionFlow as _BaseExtractionFlow, 
        BaseFilteringFlow as _BaseFilteringFlow,
        BaseAuthenticationFlow as _BaseAuthenticationFlow,
        NavigationResult, ExtractionResult, FilteringResult, AuthenticationResult
    )
except ImportError:
    # Fallback for when run as script
    from base_flows import (
        BaseNavigationFlow as _BaseNavigationFlow,
        BaseExtractionFlow as _BaseExtractionFlow, 
        BaseFilteringFlow as _BaseFilteringFlow,
        BaseAuthenticationFlow as _BaseAuthenticationFlow,
        NavigationResult, ExtractionResult, FilteringResult, AuthenticationResult
    )


class DeprecationWarning(UserWarning):
    """Custom deprecation warning for template changes."""
    pass


def _emit_deprecation_warning(old_name: str, new_name: str, version: str = "2.0") -> None:
    """Emit a deprecation warning with migration guidance."""
    warnings.warn(
        f"{old_name} is deprecated and will be removed in version {version}. "
        f"Use {new_name} instead. "
        f"See UPGRADE_GUIDE.md for migration instructions.",
        DeprecationWarning,
        stacklevel=3
    )


class LegacyFlowWrapper:
    """Wrapper class to provide backward compatibility for legacy flows."""
    
    def __init__(self, legacy_class: type, new_base_class: type, class_name: str):
        """
        Initialize legacy flow wrapper.
        
        Args:
            legacy_class: The legacy flow class
            new_base_class: The new base class to use
            class_name: Name of the class for warnings
        """
        self.legacy_class = legacy_class
        self.new_base_class = new_base_class
        self.class_name = class_name
        self._wrapped = None
    
    def __call__(self, *args, **kwargs):
        """Create instance with deprecation warning."""
        _emit_deprecation_warning(
            f"{self.class_name}",
            f"{self.new_base_class.__name__}",
            "2.0"
        )
        
        # Create instance of legacy class
        instance = self.legacy_class(*args, **kwargs)
        
        # Add new base class methods if missing
        self._add_compatibility_methods(instance)
        
        return instance
    
    def _add_compatibility_methods(self, instance: Any) -> None:
        """Add compatibility methods to legacy instance."""
        # Add common methods from new base classes if they don't exist
        compatibility_methods = {
            '_get_config_value': lambda self, key, default=None: getattr(self, 'config', {}).get(key, default),
            'get_execution_summary': lambda self: {'total_executions': 0, 'successful_executions': 0},
            'reset_stats': lambda self: None
        }
        
        for method_name, method_impl in compatibility_methods.items():
            if not hasattr(instance, method_name):
                setattr(instance, method_name, method_impl.__get__(instance, type(instance)))


# Legacy base class aliases with deprecation warnings
class NavigationFlow(_BaseNavigationFlow):
    """Legacy NavigationFlow class - use BaseNavigationFlow instead."""
    
    def __init__(self, *args, **kwargs):
        _emit_deprecation_warning("NavigationFlow", "BaseNavigationFlow")
        super().__init__(*args, **kwargs)


class ExtractionFlow(_BaseExtractionFlow):
    """Legacy ExtractionFlow class - use BaseExtractionFlow instead."""
    
    def __init__(self, *args, **kwargs):
        _emit_deprecation_warning("ExtractionFlow", "BaseExtractionFlow")
        super().__init__(*args, **kwargs)


class FilteringFlow(_BaseFilteringFlow):
    """Legacy FilteringFlow class - use BaseFilteringFlow instead."""
    
    def __init__(self, *args, **kwargs):
        _emit_deprecation_warning("FilteringFlow", "BaseFilteringFlow")
        super().__init__(*args, **kwargs)


class AuthenticationFlow(_BaseAuthenticationFlow):
    """Legacy AuthenticationFlow class - use BaseAuthenticationFlow instead."""
    
    def __init__(self, *args, **kwargs):
        _emit_deprecation_warning("AuthenticationFlow", "BaseAuthenticationFlow")
        super().__init__(*args, **kwargs)


class CompatibilityManager:
    """Manages backward compatibility for existing sites."""
    
    def __init__(self, site_path: str):
        """
        Initialize compatibility manager.
        
        Args:
            site_path: Path to the site directory
        """
        self.site_path = Path(site_path)
        self.compatibility_mode = self._detect_compatibility_mode()
        self.legacy_imports = {}
        self._setup_compatibility_shims()
    
    def _detect_compatibility_mode(self) -> str:
        """Detect the compatibility mode needed for the site."""
        # Check for legacy patterns
        flow_py_path = self.site_path / 'flow.py'
        flows_dir = self.site_path / 'flows'
        
        if flow_py_path.exists():
            with open(flow_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Look for legacy imports
                if 'from scrapamoja.flows' in content:
                    return 'legacy_v1'
                elif 'NavigationFlow(' in content and 'BaseNavigationFlow' not in content:
                    return 'legacy_base_classes'
                elif 'class Flow(' in content:
                    return 'legacy_simple'
        
        if flows_dir.exists():
            for flow_file in flows_dir.rglob('*.py'):
                if flow_file.name == '__init__.py':
                    continue
                    
                with open(flow_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if 'NavigationFlow(' in content and 'BaseNavigationFlow' not in content:
                        return 'legacy_base_classes'
        
        return 'modern'
    
    def _setup_compatibility_shims(self) -> None:
        """Setup compatibility shims based on detected mode."""
        if self.compatibility_mode == 'legacy_v1':
            self._setup_v1_compatibility()
        elif self.compatibility_mode == 'legacy_base_classes':
            self._setup_base_class_compatibility()
        elif self.compatibility_mode == 'legacy_simple':
            self._setup_simple_compatibility()
    
    def _setup_v1_compatibility(self) -> None:
        """Setup compatibility for v1 template structure."""
        # Create shims for old import paths
        self.legacy_imports.update({
            'scrapamoja.flows.base': '.base_flows',
            'scrapamoja.templates.base': '.base_flows',
            'flows.base': '.base_flows'
        })
    
    def _setup_base_class_compatibility(self) -> None:
        """Setup compatibility for legacy base class names."""
        # Map old class names to new ones
        self.legacy_classes = {
            'NavigationFlow': NavigationFlow,
            'ExtractionFlow': ExtractionFlow,
            'FilteringFlow': FilteringFlow,
            'AuthenticationFlow': AuthenticationFlow
        }
    
    def _setup_simple_compatibility(self) -> None:
        """Setup compatibility for simple template structure."""
        # Create a simple Flow class that wraps the new architecture
        class SimpleFlow:
            """Simple flow class for backward compatibility."""
            
            def __init__(self, page, selector_engine, config=None):
                _emit_deprecation_warning("Simple Flow class", "Domain-specific base classes")
                self.page = page
                self.selector_engine = selector_engine
                self.config = config or {}
                self.navigation = _BaseNavigationFlow(page, selector_engine, config)
                self.extraction = _BaseExtractionFlow(page, selector_engine, config)
                self.filtering = _BaseFilteringFlow(page, selector_engine, config)
                self.authentication = _BaseAuthenticationFlow(page, selector_engine, config)
            
            async def navigate(self, *args, **kwargs):
                """Delegate to navigation flow."""
                return await self.navigation.navigate_to_url(*args, **kwargs)
            
            async def extract(self, *args, **kwargs):
                """Delegate to extraction flow."""
                return await self.extraction.extract_data(*args, **kwargs)
            
            async def filter(self, *args, **kwargs):
                """Delegate to filtering flow."""
                return await self.filtering.filter_data(*args, **kwargs)
            
            async def authenticate(self, *args, **kwargs):
                """Delegate to authentication flow."""
                return await self.authentication.authenticate(*args, **kwargs)
        
        self.legacy_classes = {'Flow': SimpleFlow}
    
    def get_compatibility_import(self, module_name: str) -> Optional[str]:
        """Get compatibility import mapping."""
        return self.legacy_imports.get(module_name)
    
    def get_compatibility_class(self, class_name: str) -> Optional[type]:
        """Get compatibility class mapping."""
        return self.legacy_classes.get(class_name, None)
    
    def patch_imports(self) -> None:
        """Patch imports to use compatibility shims."""
        import sys
        from unittest.mock import MagicMock
        
        # Create mock modules for legacy import paths
        for old_path, new_path in self.legacy_imports.items():
            if old_path not in sys.modules:
                mock_module = MagicMock()
                
                # Import the actual module and copy its attributes
                try:
                    actual_module = importlib.import_module(new_path, package=__package__)
                    for attr_name in dir(actual_module):
                        if not attr_name.startswith('_'):
                            setattr(mock_module, attr_name, getattr(actual_module, attr_name))
                except ImportError:
                    pass
                
                sys.modules[old_path] = mock_module


# Global compatibility manager instance
_compatibility_manager = None


def setup_compatibility(site_path: str) -> CompatibilityManager:
    """
    Setup backward compatibility for a site.
    
    Args:
        site_path: Path to the site directory
        
    Returns:
        Compatibility manager instance
    """
    global _compatibility_manager
    _compatibility_manager = CompatibilityManager(site_path)
    _compatibility_manager.patch_imports()
    return _compatibility_manager


def get_compatibility_manager() -> Optional[CompatibilityManager]:
    """Get the global compatibility manager."""
    return _compatibility_manager


# Import hook for legacy class names
class LegacyImportHook:
    """Import hook to handle legacy class names."""
    
    def __init__(self):
        self.compatibility_classes = {
            'NavigationFlow': NavigationFlow,
            'ExtractionFlow': ExtractionFlow,
            'FilteringFlow': FilteringFlow,
            'AuthenticationFlow': AuthenticationFlow
        }
    
    def find_spec(self, fullname, path, target=None):
        """Find module spec for legacy imports."""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated import handling
        return None
    
    def find_module(self, fullname, path=None):
        """Find module for legacy imports."""
        return None


# Install import hook if needed
def install_legacy_import_hook():
    """Install import hook for legacy class names."""
    if _compatibility_manager and _compatibility_manager.compatibility_mode != 'modern':
        import sys
        hook = LegacyImportHook()
        sys.meta_path.insert(0, hook)


# Utility functions for migration
def check_compatibility(site_path: str) -> Dict[str, Any]:
    """
    Check compatibility status of a site.
    
    Args:
        site_path: Path to the site directory
        
    Returns:
        Compatibility status dictionary
    """
    manager = CompatibilityManager(site_path)
    
    return {
        'compatibility_mode': manager.compatibility_mode,
        'needs_migration': manager.compatibility_mode != 'modern',
        'legacy_imports': list(manager.legacy_imports.keys()),
        'legacy_classes': list(manager.legacy_classes.keys()) if hasattr(manager, 'legacy_classes') else [],
        'recommendations': _get_migration_recommendations(manager.compatibility_mode)
    }


def _get_migration_recommendations(compatibility_mode: str) -> List[str]:
    """Get migration recommendations based on compatibility mode."""
    recommendations = []
    
    if compatibility_mode == 'legacy_v1':
        recommendations.extend([
            "Update import statements to use new base_flows module",
            "Replace legacy base classes with new Base* classes",
            "Run migration tool for automated updates"
        ])
    elif compatibility_mode == 'legacy_base_classes':
        recommendations.extend([
            "Replace NavigationFlow with BaseNavigationFlow",
            "Replace ExtractionFlow with BaseExtractionFlow", 
            "Replace FilteringFlow with BaseFilteringFlow",
            "Replace AuthenticationFlow with BaseAuthenticationFlow"
        ])
    elif compatibility_mode == 'legacy_simple':
        recommendations.extend([
            "Consider upgrading to Standard pattern for better organization",
            "Split Flow class into domain-specific flows",
            "Use new base classes for enhanced functionality"
        ])
    
    return recommendations


# Auto-setup compatibility when module is imported
def _auto_setup_compatibility():
    """Auto-setup compatibility if we can detect the site path."""
    try:
        # Try to detect site path from call stack
        import inspect
        frame = inspect.currentframe()
        
        # Look for a frame that's not in this module
        while frame:
            filename = frame.f_code.co_filename
            if not filename.endswith('compatibility.py'):
                # Found potential site file
                site_path = Path(filename).parent
                if (site_path / 'flow.py').exists() or (site_path / 'flows').exists():
                    setup_compatibility(str(site_path))
                    break
            frame = frame.f_back
            
    except Exception:
        # If auto-detection fails, continue without compatibility setup
        pass


# Auto-setup compatibility
_auto_setup_compatibility()
