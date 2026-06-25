#!/usr/bin/env python3
"""
Test script for YAML selector configurations.

This script demonstrates loading and validating YAML selector configurations
without requiring a full browser session.
"""

import os
import sys
from pathlib import Path

# Add the examples directory to the path so we can import the config loader
sys.path.insert(0, str(Path(__file__).parent))

try:
    from selector_config_loader import get_selector_config, list_selector_configs, SelectorConfigLoader
    print("✅ Successfully imported YAML configuration loader")
except ImportError as e:
    print(f"❌ Failed to import YAML configuration loader: {e}")
    print("Make sure PyYAML is installed: pip install PyYAML")
    sys.exit(1)


def test_config_loading():
    """Test loading various selector configurations from YAML."""
    print("\n" + "=" * 60)
    print("TESTING YAML CONFIGURATION LOADING")
    print("=" * 60)
    
    try:
        # List all available configurations
        available_configs = list_selector_configs()
        print(f"Available configurations: {', '.join(available_configs)}")
        
        if not available_configs:
            print("❌ No configurations found in YAML file")
            return False
        
        # Test loading each configuration
        success_count = 0
        for config_name in available_configs:
            try:
                config = get_selector_config(config_name)
                print(f"\n✅ Loaded '{config_name}':")
                print(f"  Purpose: {config.element_purpose}")
                print(f"  Strategies: {len(config.strategies)}")
                print(f"  Confidence threshold: {config.confidence_threshold}")
                print(f"  Timeout: {config.timeout_per_strategy_ms}ms")
                print(f"  Fallback enabled: {config.enable_fallback}")
                
                # Show strategy details
                for i, strategy in enumerate(config.strategies, 1):
                    print(f"    Strategy {i}: {strategy.type.upper()} - {strategy.selector}")
                    if strategy.expected_attributes:
                        print(f"      Expected attributes: {strategy.expected_attributes}")
                    if strategy.search_context:
                        print(f"      Search context: {strategy.search_context}")
                    if strategy.description:
                        print(f"      Description: {strategy.description}")
                
                success_count += 1
                
            except Exception as e:
                print(f"❌ Failed to load '{config_name}': {e}")
        
        print(f"\n📊 Configuration Loading Summary:")
        print(f"  Total configurations: {len(available_configs)}")
        print(f"  Successfully loaded: {success_count}")
        print(f"  Failed: {len(available_configs) - success_count}")
        
        return success_count == len(available_configs)
        
    except Exception as e:
        print(f"❌ Configuration loading test failed: {e}")
        return False


def test_config_validation():
    """Test configuration validation."""
    print("\n" + "=" * 60)
    print("TESTING CONFIGURATION VALIDATION")
    print("=" * 60)
    
    try:
        loader = SelectorConfigLoader()
        
        # Test loading and validating a configuration
        config = get_selector_config('search_input')
        
        # Validate the configuration
        errors = loader.validate_config(config)
        
        if errors:
            print(f"❌ Validation errors found:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ Configuration validation passed")
            return True
            
    except Exception as e:
        print(f"❌ Configuration validation test failed: {e}")
        return False


def test_yaml_file_structure():
    """Test the YAML file structure and content."""
    print("\n" + "=" * 60)
    print("TESTING YAML FILE STRUCTURE")
    print("=" * 60)
    
    yaml_file = Path(__file__).parent / "wikipedia_selectors.yaml"
    
    if not yaml_file.exists():
        print(f"❌ YAML file not found: {yaml_file}")
        return False
    
    try:
        # Check file size
        file_size = yaml_file.stat().st_size
        print(f"✅ YAML file found: {yaml_file}")
        print(f"  File size: {file_size:,} bytes")
        
        # Try to parse the YAML file
        import yaml
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        if not yaml_data:
            print("❌ YAML file is empty or invalid")
            return False
        
        print(f"✅ YAML file parsed successfully")
        print(f"  Root sections: {list(yaml_data.keys())}")
        
        # Check each configuration section
        for config_name, config_data in yaml_data.items():
            print(f"\n  Section '{config_name}':")
            
            # Check required fields
            required_fields = ['element_purpose', 'strategies']
            missing_fields = [field for field in required_fields if field not in config_data]
            
            if missing_fields:
                print(f"    ❌ Missing required fields: {missing_fields}")
                return False
            
            print(f"    ✅ Purpose: {config_data['element_purpose']}")
            print(f"    ✅ Strategies: {len(config_data['strategies'])}")
            
            # Check strategies
            for i, strategy in enumerate(config_data['strategies'], 1):
                strategy_required = ['type', 'selector', 'priority']
                strategy_missing = [field for field in strategy_required if field not in strategy]
                
                if strategy_missing:
                    print(f"      ❌ Strategy {i} missing fields: {strategy_missing}")
                    return False
                
                print(f"      ✅ Strategy {i}: {strategy['type']} - {strategy['selector']}")
        
        print(f"\n✅ YAML file structure validation passed")
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ YAML file structure test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("YAML Selector Configuration Test Suite")
    print("=" * 60)
    
    # Check if PyYAML is available
    try:
        import yaml
        print(f"✅ PyYAML version: {yaml.__version__}")
    except ImportError:
        print("❌ PyYAML not installed. Install with: pip install PyYAML")
        return False
    
    # Run tests
    tests = [
        ("YAML File Structure", test_yaml_file_structure),
        ("Configuration Loading", test_config_loading),
        ("Configuration Validation", test_config_validation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! YAML configurations are working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
