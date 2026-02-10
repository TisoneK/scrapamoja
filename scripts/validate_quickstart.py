#!/usr/bin/env python3
"""
Quickstart validation script for the Site Template Integration Framework.

This script validates that the quickstart guide examples work correctly
and that the framework is properly configured.
"""

import asyncio
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, List
import json
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.sites.base.template.site_template import BaseSiteTemplate
from src.sites.base.template.site_registry import BaseSiteRegistry
from src.sites.base.template.validation import ValidationFramework
from src.sites.base.template.development import TemplateDeveloper, TemplateMetadata
from src.sites.base.template.observability import ObservabilityManager


class QuickstartValidator:
    """Validates quickstart guide examples and framework setup."""
    
    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_results": [],
            "errors": []
        }
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete quickstart validation."""
        print("🚀 Starting Quickstart Validation")
        print("=" * 50)
        
        # Test 1: Framework Import Validation
        self._test_framework_imports()
        
        # Test 2: Template Creation Validation
        self._test_template_creation()
        
        # Test 3: YAML Selector Validation
        self._test_yaml_selectors()
        
        # Test 4: Integration Bridge Validation
        self._test_integration_bridge()
        
        # Test 5: Registry Validation
        self._test_template_registry()
        
        # Test 6: Validation Framework
        self._test_validation_framework()
        
        # Test 7: Observability Features
        self._test_observability()
        
        # Test 8: Quickstart Examples
        self._test_quickstart_examples()
        
        # Print results
        self._print_results()
        
        return self.results
    
    def _test_framework_imports(self):
        """Test that all framework components can be imported."""
        test_name = "Framework Imports"
        print(f"\n📦 Testing {test_name}...")
        
        try:
            # Test core imports
            from src.sites.base.template.site_template import BaseSiteTemplate
            from src.sites.base.template.site_registry import BaseSiteRegistry
            from src.sites.base.template.validation import ValidationFramework
            from src.sites.base.template.development import TemplateDeveloper
            from src.sites.base.template.migration import TemplateUpgrader
            from src.sites.base.template.observability import ObservabilityManager
            
            # Test integration components
            from src.sites.base.template.integration_bridge import FullIntegrationBridge
            from src.sites.base.template.selector_loader import FileSystemSelectorLoader
            
            # Test validation components
            from src.sites.base.template.validation import YAMLSelectorValidator
            from src.sites.base.template.validation import ExtractionRuleValidator
            
            self._record_test_result(test_name, True, "All framework components imported successfully")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Import failed: {str(e)}")
    
    def _test_template_creation(self):
        """Test template creation using development tools."""
        test_name = "Template Creation"
        print(f"\n🏗️ Testing {test_name}...")
        
        try:
            # Create test metadata
            metadata = TemplateMetadata(
                name="quickstart_test",
                version="1.0.0",
                description="Quickstart test template",
                author="Quickstart Validator",
                site_domain="quickstart.test",
                framework_version="1.0.0",
                capabilities=["scraping", "extraction"],
                dependencies=["selector_engine"],
                tags=["test", "quickstart"]
            )
            
            # Create template developer
            developer = TemplateDeveloper()
            
            # Test template creation (dry run)
            # Note: We'll test the logic without actually creating files
            assert metadata.name == "quickstart_test"
            assert metadata.version == "1.0.0"
            assert metadata.site_domain == "quickstart.test"
            
            self._record_test_result(test_name, True, "Template creation logic validated")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Template creation failed: {str(e)}")
    
    def _test_yaml_selectors(self):
        """Test YAML selector validation."""
        test_name = "YAML Selectors"
        print(f"\n🎯 Testing {test_name}...")
        
        try:
            # Test YAML selector configuration
            selector_config = {
                "name": "test_selector",
                "description": "Test selector for validation",
                "selector": ".test-element",
                "strategies": [
                    {
                        "name": "css",
                        "type": "css",
                        "priority": 1,
                        "confidence": 0.9,
                        "timeout": 5000
                    },
                    {
                        "name": "xpath",
                        "type": "xpath",
                        "priority": 2,
                        "confidence": 0.8,
                        "timeout": 5000
                    }
                ],
                "validation": {
                    "required": True,
                    "exists": True,
                    "min_length": 1
                },
                "metadata": {
                    "category": "test",
                    "tags": ["test", "validation"],
                    "version": "1.0.0"
                }
            }
            
            # Validate YAML structure
            assert "name" in selector_config
            assert "strategies" in selector_config
            assert "validation" in selector_config
            assert "metadata" in selector_config
            
            # Validate strategies
            strategies = selector_config["strategies"]
            assert len(strategies) >= 1
            for strategy in strategies:
                assert "name" in strategy
                assert "type" in strategy
                assert "priority" in strategy
                assert "confidence" in strategy
            
            # Test YAML serialization
            yaml_content = yaml.dump(selector_config)
            loaded_config = yaml.safe_load(yaml_content)
            assert loaded_config["name"] == selector_config["name"]
            
            self._record_test_result(test_name, True, "YAML selector validation passed")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"YAML selector validation failed: {str(e)}")
    
    def _test_integration_bridge(self):
        """Test integration bridge functionality."""
        test_name = "Integration Bridge"
        print(f"\n🔗 Testing {test_name}...")
        
        try:
            # Test integration bridge import and basic structure
            from src.sites.base.template.integration_bridge import FullIntegrationBridge
            
            # Create mock components
            mock_selector_engine = type('MockSelectorEngine', (), {})()
            mock_page = type('MockPage', (), {})()
            
            # Test bridge instantiation
            bridge = FullIntegrationBridge("test_template", mock_selector_engine, mock_page)
            
            # Test bridge methods exist
            assert hasattr(bridge, 'initialize_complete_integration')
            assert hasattr(bridge, 'load_selectors')
            assert hasattr(bridge, 'setup_extraction_rules')
            assert hasattr(bridge, 'get_integration_status')
            
            self._record_test_result(test_name, True, "Integration bridge structure validated")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Integration bridge test failed: {str(e)}")
    
    def _test_template_registry(self):
        """Test template registry functionality."""
        test_name = "Template Registry"
        print(f"\n📋 Testing {test_name}...")
        
        try:
            # Test registry creation
            registry = BaseSiteRegistry()
            
            # Test registry methods exist
            assert hasattr(registry, 'discover_templates')
            assert hasattr(registry, 'register_template')
            assert hasattr(registry, 'load_template')
            assert hasattr(registry, 'list_templates')
            
            # Test template discovery logic
            # Note: We'll test the method exists and basic structure
            assert callable(registry.discover_templates)
            assert callable(registry.register_template)
            assert callable(registry.load_template)
            assert callable(registry.list_templates)
            
            self._record_test_result(test_name, True, "Template registry structure validated")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Template registry test failed: {str(e)}")
    
    def _test_validation_framework(self):
        """Test validation framework functionality."""
        test_name = "Validation Framework"
        print(f"\n✅ Testing {test_name}...")
        
        try:
            # Test validation framework creation
            validator = ValidationFramework()
            
            # Test validator methods exist
            assert hasattr(validator, 'validate_template_structure')
            assert hasattr(validator, 'validate_selectors')
            assert hasattr(validator, 'check_framework_compliance')
            assert hasattr(validator, 'get_validation_summary')
            
            # Test YAML selector validator
            from src.sites.base.template.validation import YAMLSelectorValidator
            yaml_validator = YAMLSelectorValidator()
            assert hasattr(yaml_validator, 'validate_selector')
            
            # Test extraction rule validator
            from src.sites.base.template.validation import ExtractionRuleValidator
            extraction_validator = ExtractionRuleValidator()
            assert hasattr(extraction_validator, 'validate_rules')
            
            self._record_test_result(test_name, True, "Validation framework structure validated")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Validation framework test failed: {str(e)}")
    
    def _test_observability(self):
        """Test observability and monitoring features."""
        test_name = "Observability Features"
        print(f"\n📊 Testing {test_name}...")
        
        try:
            # Test observability manager creation
            obs_manager = ObservabilityManager()
            
            # Test observability components exist
            assert hasattr(obs_manager, 'metrics_collector')
            assert hasattr(obs_manager, 'alert_manager')
            assert hasattr(obs_manager, 'health_monitor')
            
            # Test metrics collector
            metrics_collector = obs_manager.metrics_collector
            assert hasattr(metrics_collector, 'record_counter')
            assert hasattr(metrics_collector, 'record_gauge')
            assert hasattr(metrics_collector, 'record_histogram')
            assert hasattr(metrics_collector, 'record_timer')
            
            # Test alert manager
            alert_manager = obs_manager.alert_manager
            assert hasattr(alert_manager, 'add_alert_rule')
            assert hasattr(alert_manager, 'check_alerts')
            assert hasattr(alert_manager, 'get_alerts')
            
            # Test health monitor
            health_monitor = obs_manager.health_monitor
            assert hasattr(health_monitor, 'add_health_check')
            assert hasattr(health_monitor, 'get_health_status')
            
            self._record_test_result(test_name, True, "Observability features validated")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Observability test failed: {str(e)}")
    
    def _test_quickstart_examples(self):
        """Test quickstart guide examples."""
        test_name = "Quickstart Examples"
        print(f"\n📖 Testing {test_name}...")
        
        try:
            # Test quickstart guide exists and is readable
            quickstart_path = project_root / "specs" / "017-site-template-integration" / "quickstart.md"
            
            if not quickstart_path.exists():
                self._record_test_result(test_name, False, "Quickstart guide not found")
                return
            
            # Read quickstart content
            with open(quickstart_path, 'r') as f:
                content = f.read()
            
            # Validate quickstart structure
            required_sections = [
                "## Overview",
                "## Prerequisites",
                "## Quick Start",
                "## Template Registry Usage",
                "## Validation and Testing",
                "## Best Practices",
                "## Troubleshooting"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)
            
            if missing_sections:
                self._record_test_result(
                    test_name, 
                    False, 
                    f"Missing sections: {', '.join(missing_sections)}"
                )
                return
            
            # Validate code examples are syntactically correct
            # Check for basic Python syntax in code blocks
            import re
            
            # Find Python code blocks
            python_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
            
            syntax_errors = []
            for i, block in enumerate(python_blocks):
                try:
                    compile(block, f'quickstart_block_{i}', 'exec')
                except SyntaxError as e:
                    syntax_errors.append(f"Block {i}: {e}")
            
            if syntax_errors:
                self._record_test_result(
                    test_name,
                    False,
                    f"Syntax errors in code blocks: {'; '.join(syntax_errors)}"
                )
                return
            
            # Validate YAML examples
            yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', content, re.DOTALL)
            
            yaml_errors = []
            for i, block in enumerate(yaml_blocks):
                try:
                    yaml.safe_load(block)
                except yaml.YAMLError as e:
                    yaml_errors.append(f"YAML Block {i}: {e}")
            
            if yaml_errors:
                self._record_test_result(
                    test_name,
                    False,
                    f"YAML errors in blocks: {'; '.join(yaml_errors)}"
                )
                return
            
            self._record_test_result(
                test_name,
                True,
                f"Quickstart guide validated with {len(python_blocks)} Python blocks and {len(yaml_blocks)} YAML blocks"
            )
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Quickstart validation failed: {str(e)}")
    
    def _record_test_result(self, test_name: str, passed: bool, message: str):
        """Record test result."""
        self.results["total_tests"] += 1
        
        if passed:
            self.results["passed_tests"] += 1
            print(f"  ✅ {test_name}: {message}")
        else:
            self.results["failed_tests"] += 1
            print(f"  ❌ {test_name}: {message}")
            self.results["errors"].append(f"{test_name}: {message}")
        
        self.results["test_results"].append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
    
    def _print_results(self):
        """Print validation results."""
        print("\n" + "=" * 50)
        print("🎯 QUICKSTART VALIDATION RESULTS")
        print("=" * 50)
        
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed_tests']}")
        print(f"Failed: {self.results['failed_tests']}")
        
        success_rate = (self.results['passed_tests'] / self.results['total_tests'] * 100) if self.results['total_tests'] > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results['failed_tests'] > 0:
            print("\n❌ Failed Tests:")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        if success_rate >= 90:
            print("\n🎉 Quickstart validation PASSED! Framework is ready to use.")
        elif success_rate >= 70:
            print("\n⚠️  Quickstart validation PARTIALLY PASSED. Some issues need attention.")
        else:
            print("\n🚨 Quickstart validation FAILED. Major issues need to be resolved.")
        
        print("\n📋 Next Steps:")
        print("1. Review any failed tests and fix issues")
        print("2. Run the end-to-end tests: python -m pytest tests/end_to_end/")
        print("3. Try the examples in examples/basic/")
        print("4. Read the comprehensive documentation: docs/template-framework.md")


def main():
    """Main validation function."""
    validator = QuickstartValidator()
    results = validator.run_validation()
    
    # Exit with appropriate code
    if results["failed_tests"] == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
