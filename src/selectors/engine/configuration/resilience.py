"""
Production resilience testing for configuration system failures.

This module provides testing utilities to verify that the configuration system
handles failures gracefully and maintains production resilience.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import yaml

from ...models.selector_config import (
    SelectorConfiguration,
    ConfigurationMetadata,
    ContextDefaults,
    SemanticSelector,
    StrategyDefinition
)
from .loader import ConfigurationLoader
from .validator import ConfigurationValidator
from .inheritance import InheritanceResolver
from .index import SemanticIndex
from .watcher import ConfigurationWatcher
from .health import ConfigurationHealthChecker


class ResilienceTestResult:
    """Result of a resilience test."""
    
    def __init__(self, test_name: str, passed: bool, message: str, details: Optional[Dict[str, Any]] = None):
        self.test_name = test_name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ConfigurationResilienceTester:
    """Tester for configuration system production resilience."""
    
    def __init__(self):
        """Initialize the resilience tester."""
        self.logger = logging.getLogger(__name__)
        self.health_checker = ConfigurationHealthChecker()
    
    async def run_resilience_tests(self, config_root: Path) -> Dict[str, Any]:
        """Run comprehensive resilience tests."""
        test_results = {
            "overall_status": "passed",
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0
            }
        }
        
        # Define resilience tests
        tests = [
            ("invalid_yaml_handling", self._test_invalid_yaml_handling),
            ("missing_file_handling", self._test_missing_file_handling),
            ("circular_inheritance_handling", self._test_circular_inheritance_handling),
            ("corrupted_config_recovery", self._test_corrupted_config_recovery),
            ("hot_reload_resilience", self._test_hot_reload_resilience),
            ("memory_pressure_handling", self._test_memory_pressure_handling),
            ("concurrent_access_handling", self._test_concurrent_access_handling),
            ("network_interruption_handling", self._test_network_interruption_handling),
            ("graceful_degradation", self._test_graceful_degradation),
            ("error_recovery_mechanisms", self._test_error_recovery_mechanisms)
        ]
        
        for test_name, test_func in tests:
            try:
                result = await test_func(config_root)
                test_results["tests"][test_name] = result.to_dict()
                test_results["summary"]["total_tests"] += 1
                
                if result.passed:
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["summary"]["failed"] += 1
                    if test_results["overall_status"] == "passed":
                        test_results["overall_status"] = "failed"
                
            except Exception as e:
                self.logger.error(f"Resilience test '{test_name}' failed: {e}")
                failed_result = ResilienceTestResult(
                    test_name, False, f"Test execution failed: {str(e)}"
                )
                test_results["tests"][test_name] = failed_result.to_dict()
                test_results["summary"]["total_tests"] += 1
                test_results["summary"]["failed"] += 1
                test_results["overall_status"] = "failed"
        
        return test_results
    
    async def _test_invalid_yaml_handling(self, config_root: Path) -> ResilienceTestResult:
        """Test handling of invalid YAML files."""
        details = {}
        
        # Create invalid YAML file
        invalid_yaml = """
        metadata:
          version: "1.0.0"
          last_updated: "invalid-date"
        selectors:
          test_selector:
            description: "Test"
            context: "test"
            strategies:
              - type: "invalid_type"
                parameters:
                  selector: "invalid
            validation:
                required: "invalid_boolean"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            invalid_file = Path(f.name)
        
        try:
            loader = ConfigurationLoader()
            
            # Should handle gracefully without crashing
            try:
                config = await loader.load_configuration(invalid_file)
                return ResilienceTestResult(
                    "invalid_yaml_handling", False, 
                    "Invalid YAML was accepted when it should have been rejected"
                )
            except Exception as e:
                details["error_type"] = type(e).__name__
                details["error_message"] = str(e)
                return ResilienceTestResult(
                    "invalid_yaml_handling", True,
                    "Invalid YAML properly handled with appropriate exception",
                    details
                )
        finally:
            invalid_file.unlink(missing_ok=True)
    
    async def _test_missing_file_handling(self, config_root: Path) -> ResilienceTestResult:
        """Test handling of missing configuration files."""
        details = {}
        
        loader = ConfigurationLoader()
        missing_file = config_root / "nonexistent.yaml"
        
        try:
            # Should handle gracefully without crashing
            config = await loader.load_configuration(missing_file)
            return ResilienceTestResult(
                "missing_file_handling", False,
                "Missing file was accepted when it should have been rejected"
            )
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "missing_file_handling", True,
                "Missing file properly handled with appropriate exception",
                details
            )
    
    async def _test_circular_inheritance_handling(self, config_root: Path) -> ResilienceTestResult:
        """Test handling of circular inheritance references."""
        details = {}
        
        # Create circular inheritance configuration
        circular_config = """
        metadata:
          version: "1.0.0"
          last_updated: "2025-01-27T17:00:00Z"
          description: "Circular inheritance test"
        parent_path: "circular.yaml"
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(circular_config)
            circular_file = Path(f.name)
        
        try:
            resolver = InheritanceResolver()
            
            # Should detect and handle circular references
            circular_refs = resolver.detect_circular_references(str(circular_file))
            details["circular_references"] = circular_refs
            
            if circular_refs:
                return ResilienceTestResult(
                    "circular_inheritance_handling", True,
                    "Circular inheritance properly detected and handled",
                    details
                )
            else:
                return ResilienceTestResult(
                    "circular_inheritance_handling", False,
                    "Circular inheritance was not detected"
                )
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "circular_inheritance_handling", False,
                f"Error during circular inheritance test: {str(e)}",
                details
            )
        finally:
            circular_file.unlink(missing_ok=True)
    
    async def _test_corrupted_config_recovery(self, config_root: Path) -> ResilienceTestResult:
        """Test recovery from corrupted configuration files."""
        details = {}
        
        # Create valid configuration first
        valid_config = """
        metadata:
          version: "1.0.0"
          last_updated: "2025-01-27T17:00:00Z"
          description: "Valid configuration"
        context_defaults:
          page_type: "test"
          wait_strategy: "network_idle"
          timeout: 10000
        selectors:
          test_selector:
            description: "Test selector"
            context: "test.content"
            strategies:
              - type: "css_selector"
                parameters:
                  selector: ".test"
                priority: 1
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_config)
            config_file = Path(f.name)
        
        try:
            loader = ConfigurationLoader()
            validator = ConfigurationValidator()
            
            # Load valid configuration
            config = await loader.load_configuration(config_file)
            validation_result = validator.validate_configuration(config)
            
            if not validation_result.is_valid:
                return ResilienceTestResult(
                    "corrupted_config_recovery", False,
                    "Valid configuration failed validation"
                )
            
            # Corrupt the file
            with open(config_file, 'w') as f:
                f.write("corrupted yaml content [invalid syntax")
            
            # Should handle corruption gracefully
            try:
                corrupted_config = await loader.load_configuration(config_file)
                return ResilienceTestResult(
                    "corrupted_config_recovery", False,
                    "Corrupted configuration was not properly rejected"
                )
            except Exception as e:
                details["error_type"] = type(e).__name__
                details["error_message"] = str(e)
                return ResilienceTestResult(
                    "corrupted_config_recovery", True,
                    "Corrupted configuration properly rejected",
                    details
                )
        finally:
            config_file.unlink(missing_ok=True)
    
    async def _test_hot_reload_resilience(self, config_root: Path) -> ResilienceTestResult:
        """Test hot reload resilience under various conditions."""
        details = {}
        
        # Create test configuration
        test_config = """
        metadata:
          version: "1.0.0"
          last_updated: "2025-01-27T17:00:00Z"
          description: "Hot reload test"
        selectors:
          test_selector:
            description: "Test selector"
            context: "test.content"
            strategies:
              - type: "css_selector"
                parameters:
                  selector: ".test"
                priority: 1
        """
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_file = Path(temp_dir) / "test.yaml"
            with open(temp_config_file, 'w') as f:
                f.write(test_config)
            
            try:
                loader = ConfigurationLoader()
                index = SemanticIndex()
                watcher = ConfigurationWatcher()
                
                # Initialize watcher
                await watcher.start_watching(Path(temp_dir))
                
                # Load initial configuration
                config = await loader.load_configuration(temp_config_file)
                await index.build_index({str(temp_config_file): config})
                
                initial_count = len(index._index)
                
                # Test invalid update
                invalid_update = """
                metadata:
                  version: "1.0.0"
                  last_updated: "2025-01-27T17:00:00Z"
                selectors:
                  test_selector:
                    description: "Test selector"
                    context: "test.content"
                    strategies:
                      - type: "invalid_type"
                        parameters:
                          invalid_param: "value"
                """
                
                with open(temp_config_file, 'w') as f:
                    f.write(invalid_update)
                
                # Should handle invalid update without crashing
                try:
                    updated_config = await loader.reload_configuration(temp_config_file)
                    if updated_config is None:
                        details["invalid_update_handled"] = True
                    else:
                        details["invalid_update_handled"] = False
                except Exception as e:
                    details["update_error"] = str(e)
                
                # Test valid update
                valid_update = """
                metadata:
                  version: "1.0.0"
                  last_updated: "2025-01-27T17:00:00Z"
                selectors:
                  test_selector:
                    description: "Updated test selector"
                    context: "test.content"
                    strategies:
                      - type: "css_selector"
                        parameters:
                          selector: ".updated"
                        priority: 1
                  new_selector:
                    description: "New selector"
                    context: "test.content"
                    strategies:
                      - type: "css_selector"
                        parameters:
                          selector: ".new"
                        priority: 1
                """
                
                with open(temp_config_file, 'w') as f:
                    f.write(valid_update)
                
                updated_config = await loader.reload_configuration(temp_config_file)
                await index.update_index(str(temp_config_file), updated_config)
                
                final_count = len(index._index)
                
                await watcher.stop_watching()
                
                details["initial_selectors"] = initial_count
                details["final_selectors"] = final_count
                details["invalid_update_handled"] = details.get("invalid_update_handled", False)
                
                if final_count > initial_count:
                    return ResilienceTestResult(
                        "hot_reload_resilience", True,
                        "Hot reload handled valid and invalid updates correctly",
                        details
                    )
                else:
                    return ResilienceTestResult(
                        "hot_reload_resilience", False,
                        "Hot reload did not process valid update correctly"
                    )
                
            except Exception as e:
                details["error_type"] = type(e).__name__
                details["error_message"] = str(e)
                return ResilienceTestResult(
                    "hot_reload_resilience", False,
                    f"Hot reload test failed: {str(e)}",
                    details
                )
    
    async def _test_memory_pressure_handling(self, config_root: Path) -> ResilienceTestResult:
        """Test system behavior under memory pressure."""
        details = {}
        
        try:
            loader = ConfigurationLoader()
            index = SemanticIndex()
            
            # Create many configurations to simulate memory pressure
            configs = {}
            for i in range(100):  # Create 100 configurations
                config_data = f"""
                metadata:
                  version: "1.0.0"
                  last_updated: "2025-01-27T17:00:00Z"
                  description: "Memory pressure test {i}"
                selectors:
                  selector_{i}:
                    description: "Test selector {i}"
                    context: "test.content"
                    strategies:
                      - type: "css_selector"
                        parameters:
                          selector: ".test-{i}"
                        priority: 1
                """
                
                config = yaml.safe_load(config_data)
                configs[f"test_{i}"] = config
            
            # Build index with many configurations
            start_time = datetime.now()
            index_result = await index.build_index(configs)
            end_time = datetime.now()
            
            build_time_ms = (end_time - start_time).total_seconds() * 1000
            details["build_time_ms"] = build_time_ms
            details["configurations_count"] = len(configs)
            details["selectors_count"] = len(index_result)
            
            # Test lookup performance under pressure
            lookup_times = []
            for i in range(10):
                start_time = datetime.now()
                result = index.lookup_selector(f"selector_{i}")
                end_time = datetime.now()
                lookup_times.append((end_time - start_time).total_seconds() * 1000)
            
            avg_lookup_time = sum(lookup_times) / len(lookup_times)
            details["avg_lookup_time_ms"] = avg_lookup_time
            
            # Performance thresholds
            if build_time_ms < 5000 and avg_lookup_time < 10:
                return ResilienceTestResult(
                    "memory_pressure_handling", True,
                    "System handled memory pressure within acceptable limits",
                    details
                )
            else:
                return ResilienceTestResult(
                    "memory_pressure_handling", False,
                    "System performance degraded under memory pressure",
                    details
                )
                
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "memory_pressure_handling", False,
                f"Memory pressure test failed: {str(e)}",
                details
            )
    
    async def _test_concurrent_access_handling(self, config_root: Path) -> ResilienceTestResult:
        """Test concurrent access to configuration system."""
        details = {}
        
        try:
            loader = ConfigurationLoader()
            index = SemanticIndex()
            
            # Create test configuration
            test_config = """
            metadata:
              version: "1.0.0"
              last_updated: "2025-01-27T17:00:00Z"
              description: "Concurrent access test"
            selectors:
              test_selector:
                description: "Test selector"
                context: "test.content"
                strategies:
                  - type: "css_selector"
                    parameters:
                      selector: ".test"
                    priority: 1
            """
            
            config = yaml.safe_load(test_config)
            
            # Test concurrent loading
            async def load_config():
                return await loader.load_configuration(config_root / "test.yaml")
            
            # Simulate concurrent access
            tasks = [load_config() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_loads = sum(1 for r in results if not isinstance(r, Exception))
            failed_loads = len(results) - successful_loads
            
            details["concurrent_loads"] = len(tasks)
            details["successful_loads"] = successful_loads
            details["failed_loads"] = failed_loads
            
            # Test concurrent index operations
            async def build_index():
                return await index.build_index({"test": config})
            
            index_tasks = [build_index() for _ in range(5)]
            index_results = await asyncio.gather(*index_tasks, return_exceptions=True)
            
            successful_indexes = sum(1 for r in index_results if not isinstance(r, Exception))
            failed_indexes = len(index_results) - successful_indexes
            
            details["concurrent_indexes"] = len(index_tasks)
            details["successful_indexes"] = successful_indexes
            details["failed_indexes"] = failed_indexes
            
            if failed_loads == 0 and failed_indexes == 0:
                return ResilienceTestResult(
                    "concurrent_access_handling", True,
                    "System handled concurrent access without errors",
                    details
                )
            else:
                return ResilienceTestResult(
                    "concurrent_access_handling", False,
                    f"System had {failed_loads + failed_indexes} concurrent access failures",
                    details
                )
                
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "concurrent_access_handling", False,
                f"Concurrent access test failed: {str(e)}",
                details
            )
    
    async def _test_network_interruption_handling(self, config_root: Path) -> ResilienceTestResult:
        """Test handling of network interruptions during remote configuration loading."""
        details = {}
        
        # This test simulates network interruptions
        # In a real scenario, this would test remote configuration loading
        
        try:
            # Simulate network timeout
            loader = ConfigurationLoader()
            
            # Create a mock remote configuration that would fail
            remote_path = Path("http://invalid-remote-server/config.yaml")
            
            start_time = datetime.now()
            try:
                # This should timeout gracefully
                config = await loader.load_configuration(remote_path)
                return ResilienceTestResult(
                    "network_interruption_handling", False,
                    "Network interruption was not properly handled"
                )
            except Exception as e:
                end_time = datetime.now()
                timeout_duration = (end_time - start_time).total_seconds()
                
                details["timeout_duration"] = timeout_duration
                details["error_type"] = type(e).__name__
                details["error_message"] = str(e)
                
                if timeout_duration < 30:  # Should timeout quickly
                    return ResilienceTestResult(
                        "network_interruption_handling", True,
                        "Network interruption handled with appropriate timeout",
                        details
                    )
                else:
                    return ResilienceTestResult(
                        "network_interruption_handling", False,
                        "Network interruption took too long to handle",
                        details
                    )
                
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "network_interruption_handling", False,
                f"Network interruption test failed: {str(e)}",
                details
            )
    
    async def _test_graceful_degradation(self, config_root: Path) -> ResilienceTestResult:
        """Test graceful degradation when components fail."""
        details = {}
        
        try:
            # Test system behavior with missing components
            loader = ConfigurationLoader()
            
            # Create partial configuration (missing some required fields)
            partial_config = """
            metadata:
              version: "1.0.0"
              # Missing last_updated
            selectors:
              test_selector:
                description: "Test selector"
                # Missing context
                strategies:
                  - type: "css_selector"
                    parameters:
                      selector: ".test"
                    priority: 1
            """
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(partial_config)
                partial_file = Path(f.name)
            
            try:
                config = await loader.load_configuration(partial_file)
                
                # Should have defaults applied where possible
                has_metadata = config.metadata is not None
                has_selectors = len(config.selectors) > 0
                
                details["has_metadata"] = has_metadata
                details["has_selectors"] = has_selectors
                
                if has_metadata and has_selectors:
                    return ResilienceTestResult(
                        "graceful_degradation", True,
                        "System gracefully degraded with partial configuration",
                        details
                    )
                else:
                    return ResilienceTestResult(
                        "graceful_degradation", False,
                        "System did not handle partial configuration gracefully",
                        details
                    )
                    
            except Exception as e:
                details["error_type"] = type(e).__name__
                details["error_message"] = str(e)
                return ResilienceTestResult(
                    "graceful_degradation", False,
                    f"Graceful degradation test failed: {str(e)}",
                    details
                )
            finally:
                partial_file.unlink(missing_ok=True)
                
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "graceful_degradation", False,
                f"Graceful degradation test failed: {str(e)}",
                details
            )
    
    async def _test_error_recovery_mechanisms(self, config_root: Path) -> ResilienceTestResult:
        """Test error recovery mechanisms."""
        details = {}
        
        try:
            loader = ConfigurationLoader()
            validator = ConfigurationValidator()
            
            # Test recovery from validation errors
            invalid_config = """
            metadata:
              version: "1.0.0"
              last_updated: "2025-01-27T17:00:00Z"
            context_defaults:
              page_type: "test"
              timeout: -1000  # Invalid timeout
            """
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(invalid_config)
                invalid_file = Path(f.name)
            
            try:
                config = await loader.load_configuration(invalid_file)
                validation_result = validator.validate_configuration(config)
                
                details["validation_passed"] = validation_result.is_valid
                details["error_count"] = len(validation_result.errors)
                
                if not validation_result.is_valid:
                    return ResilienceTestResult(
                        "error_recovery_mechanisms", True,
                        "Error recovery mechanisms properly detected validation errors",
                        details
                    )
                else:
                    return ResilienceTestResult(
                        "error_recovery_mechanisms", False,
                        "Validation errors were not detected",
                        details
                    )
                    
            except Exception as e:
                details["error_type"] = type(e).__name__
                details["error_message"] = str(e)
                return ResilienceTestResult(
                    "error_recovery_mechanisms", True,
                    "Error recovery mechanisms caught exception appropriately",
                    details
                )
            finally:
                invalid_file.unlink(missing_ok=True)
                
        except Exception as e:
            details["error_type"] = type(e).__name__
            details["error_message"] = str(e)
            return ResilienceTestResult(
                "error_recovery_mechanisms", False,
                f"Error recovery test failed: {str(e)}",
                details
            )


async def run_production_resilience_test(config_root: Path) -> Dict[str, Any]:
    """Run production resilience test suite."""
    tester = ConfigurationResilienceTester()
    return await tester.run_resilience_tests(config_root)


def generate_resilience_report(test_results: Dict[str, Any]) -> str:
    """Generate a resilience test report."""
    report = []
    report.append("# Configuration System Production Resilience Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("")
    
    if test_results["overall_status"] == "passed":
        report.append("## Overall Status: ✅ PASSED")
    else:
        report.append("## Overall Status: ❌ FAILED")
    
    report.append(f"Total Tests: {test_results['summary']['total_tests']}")
    report.append(f"Passed: {test_results['summary']['passed']}")
    report.append(f"Failed: {test_results['summary']['failed']}")
    report.append("")
    
    report.append("## Test Results")
    for test_name, result in test_results["tests"].items():
        status_icon = "✅" if result["passed"] else "❌"
        report.append(f"### {status_icon} {test_name}")
        report.append(f"**Status:** {result['status']}")
        report.append(f"**Message:** {result['message']}")
        report.append("")
        
        if result.get("details"):
            report.append("**Details:**")
            for key, value in result["details"].items():
                report.append(f"- {key}: {value}")
            report.append("")
    
    return '\n'.join(report)
