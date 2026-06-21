#!/usr/bin/env python3
"""
Validation script for the hierarchical selector system for Flashscore.

This script validates the structure, tests selector loading, and demonstrates
the hierarchical selector functionality.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.sites.base.template.hierarchical_structure_validator import (
    HierarchicalStructureValidator, 
    validate_selector_structure,
    print_validation_report
)
from src.selectors.context_manager import get_context_manager, SelectorContext, DOMState
from src.selectors.context_loader import get_context_based_loader


async def validate_hierarchical_structure():
    """Validate the hierarchical directory structure."""
    print("🔍 Validating Hierarchical Structure")
    print("=" * 50)
    
    selectors_root = Path(__file__).parent / "selectors"
    
    # Validate structure
    validator = HierarchicalStructureValidator(selectors_root)
    report = validator.validate_structure()
    
    print_validation_report(report)
    
    # Get structure summary
    summary = validator.get_structure_summary()
    print(f"\n📊 Structure Summary:")
    print(f"Total files: {summary['total_files']}")
    print(f"YAML files: {summary['yaml_files']}")
    print(f"Max depth: {summary['max_depth']}")
    
    return report.is_valid


async def test_context_loading():
    """Test the context-based selector loading."""
    print("\n🚀 Testing Context-Based Selector Loading")
    print("=" * 50)
    
    selectors_root = Path(__file__).parent / "selectors"
    loader = get_context_based_loader(selectors_root)
    
    # Test loading selectors for different contexts
    test_contexts = [
        SelectorContext(primary_context="authentication"),
        SelectorContext(primary_context="navigation", secondary_context="sport_selection"),
        SelectorContext(primary_context="extraction", secondary_context="match_list"),
        SelectorContext(primary_context="extraction", secondary_context="match_stats", tertiary_context="inc_ot"),
        SelectorContext(primary_context="filtering", secondary_context="date_filter"),
    ]
    
    total_selectors = 0
    for context in test_contexts:
        result = await loader.load_selectors(context=context, force_reload=True)
        
        print(f"📁 Context: {context.get_context_path()}")
        print(f"   Selectors loaded: {result.selector_count}")
        print(f"   Load time: {result.load_time_ms:.2f}ms")
        print(f"   Cache hit: {result.cache_hit}")
        
        if result.errors:
            print(f"   Errors: {result.errors}")
        
        total_selectors += result.selector_count
        
        # Show some selector names
        if result.selectors:
            selector_names = [s.name for s in result.selectors[:3]]
            print(f"   Sample selectors: {selector_names}")
    
    print(f"\n📊 Total selectors loaded across all contexts: {total_selectors}")
    
    return True


async def main():
    """Run validation tests."""
    print("🧪 Flashscore Hierarchical Selector System Validation")
    print("=" * 60)
    
    try:
        # Test 1: Structure validation
        structure_valid = await validate_hierarchical_structure()
        
        if not structure_valid:
            print("\n❌ Structure validation failed. Fix issues before continuing.")
            return False
        
        # Test 2: Context loading
        context_loading_ok = await test_context_loading()
        
        # Summary
        print("\n🎉 Validation Summary")
        print("=" * 30)
        print(f"Structure validation: {'✅' if structure_valid else '❌'}")
        print(f"Context loading: {'✅' if context_loading_ok else '❌'}")
        
        all_passed = all([structure_valid, context_loading_ok])
        
        if all_passed:
            print("\n🚀 All validations passed! Hierarchical selector system is ready.")
        else:
            print("\n⚠️ Some validations failed. Review the output above.")
        
        return all_passed
        
    except Exception as e:
        print(f"\n💥 Validation execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
