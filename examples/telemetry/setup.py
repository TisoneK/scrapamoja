#!/usr/bin/env python3
"""
Setup script for Selector Telemetry System.

This script validates the quickstart guide and sets up the telemetry system
with proper configuration and dependencies.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from src.telemetry.configuration.validation import validate_configuration, apply_corrections
    from src.telemetry.lifecycle import telemetry_system, get_lifecycle_manager
    from src.telemetry.exceptions import TelemetryError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure the telemetry module is properly installed")
    sys.exit(1)


class TelemetrySetup:
    """Setup and validation for telemetry system."""
    
    def __init__(self):
        self.setup_dir = Path(__file__).parent
        self.project_root = self.setup_dir.parent.parent
        self.telemetry_dir = self.project_root / "src" / "telemetry"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def validate_quickstart_compatibility(self) -> bool:
        """Validate that quickstart guide matches implementation."""
        self.logger.info("🔍 Validating quickstart guide compatibility...")
        
        issues = []
        
        # Check required modules
        required_modules = [
            "telemetry.configuration.telemetry_config",
            "telemetry.collector.metrics_collector", 
            "telemetry.storage.storage_manager",
            "telemetry.processor.metrics_processor",
            "telemetry.alerting.alert_engine",
            "telemetry.integration.selector_integration"
        ]
        
        for module in required_modules:
            module_path = self.telemetry_dir / module.replace(".", "/") + ".py"
            if not module_path.exists():
                issues.append(f"Missing module: {module}")
        
        # Check configuration structure
        try:
            sample_config = self._get_sample_config()
            validation_result = validate_configuration(sample_config)
            
            if not validation_result.is_valid:
                issues.extend([f"Config validation: {error}" for error in validation_result.errors])
            
        except Exception as e:
            issues.append(f"Configuration validation failed: {e}")
        
        if issues:
            self.logger.error("❌ Quickstart validation failed:")
            for issue in issues:
                self.logger.error(f"  - {issue}")
            return False
        
        self.logger.info("✅ Quickstart guide is compatible")
        return True
    
    def create_sample_config(self) -> str:
        """Create sample configuration file."""
        config_path = self.setup_dir / "telemetry_config.json"
        
        sample_config = self._get_sample_config()
        
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        self.logger.info(f"📝 Created sample config: {config_path}")
        return str(config_path)
    
    def _get_sample_config(self) -> Dict[str, Any]:
        """Get sample configuration for quickstart."""
        return {
            "collection": {
                "enabled": True,
                "buffer_size": 1000,
                "batch_size": 100,
                "flush_interval": 30.0
            },
            "storage": {
                "type": "json",
                "directory": "telemetry_data",
                "retention_days": 30,
                "file_rotation": {
                    "max_file_size_mb": 100,
                    "max_files": 10
                }
            },
            "alerting": {
                "enabled": True,
                "thresholds": {
                    "performance": {
                        "resolution_time_ms": 1000,
                        "memory_usage_mb": 100,
                        "error_rate_percent": 5.0
                    },
                    "quality": {
                        "confidence_score": 0.8,
                        "decline_percent": 20.0
                    },
                    "health": {
                        "anomaly_threshold": 2.0,
                        "timeout_frequency_percent": 10.0
                    }
                },
                "notifications": {
                    "channels": ["log"],
                    "rate_limit": {
                        "max_per_hour": 10
                    }
                }
            },
            "reporting": {
                "enabled": True,
                "types": ["performance", "usage", "health"],
                "schedule": {
                    "frequency": "daily",
                    "time_of_day": "00:00"
                }
            },
            "performance": {
                "overhead_target_percent": 2.0,
                "memory_threshold_mb": 100,
                "cache": {
                    "size": 1000,
                    "ttl_seconds": 300
                }
            },
            "log_level": "INFO",
            "correlation_id_length": 8
        }
    
    async def test_basic_functionality(self) -> bool:
        """Test basic telemetry functionality."""
        self.logger.info("🧪 Testing basic telemetry functionality...")
        
        try:
            config = self._get_sample_config()
            
            # Test system initialization
            async with telemetry_system(config) as manager:
                # Check system state
                state = manager.get_state()
                if state.value != "running":
                    self.logger.error(f"❌ System not running: {state}")
                    return False
                
                # Test health check
                health = await manager.get_health_status()
                if not health.healthy:
                    self.logger.warning(f"⚠️  System health issues: {health.issues}")
                
                # Test metrics collection
                from src.telemetry.integration.selector_integration import SelectorTelemetryIntegration
                integration = SelectorTelemetryIntegration()
                
                # Simulate selector operation
                await integration.start_selector_operation(
                    selector_id="test_selector",
                    correlation_id="test_001",
                    strategy="text_anchor"
                )
                
                await integration.record_selector_success(
                    selector_id="test_selector",
                    correlation_id="test_001",
                    confidence_score=0.85,
                    resolution_time_ms=50,
                    elements_found=1
                )
                
                # Wait for processing
                await asyncio.sleep(1)
                
                # Check metrics
                metrics = await manager.get_system_metrics()
                if metrics.total_operations == 0:
                    self.logger.warning("⚠️  No operations recorded")
                
                self.logger.info(f"✅ Basic functionality test passed")
                self.logger.info(f"   - Operations: {metrics.total_operations}")
                self.logger.info(f"   - Uptime: {metrics.uptime_seconds:.1f}s")
                self.logger.info(f"   - Memory: {health.memory_usage_mb:.1f}MB")
                
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Basic functionality test failed: {e}")
            return False
    
    def create_quickstart_script(self) -> str:
        """Create executable quickstart script."""
        script_path = self.setup_dir / "run_quickstart.py"
        
        script_content = '''#!/usr/bin/env python3
"""
Quickstart script for Selector Telemetry System.

Run this script to quickly set up and test telemetry functionality.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.telemetry.lifecycle import telemetry_system
from src.telemetry.integration.selector_integration import SelectorTelemetryIntegration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def quickstart_demo():
    """Run quickstart demonstration."""
    logger.info("🚀 Starting Selector Telemetry Quickstart Demo")
    
    # Load configuration
    config_path = Path(__file__).parent / "telemetry_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Run telemetry system
    async with telemetry_system(config) as manager:
        logger.info("✅ Telemetry system initialized and running")
        
        # Create integration
        integration = SelectorTelemetryIntegration()
        
        # Simulate selector operations
        logger.info("📊 Simulating selector operations...")
        
        for i in range(10):
            correlation_id = f"demo_{i:03d}"
            selector_id = f"selector_{i % 3}"
            strategy = ["text_anchor", "attribute_match", "dom_relationship"][i % 3]
            
            # Start operation
            await integration.start_selector_operation(
                selector_id=selector_id,
                correlation_id=correlation_id,
                strategy=strategy
            )
            
            # Simulate processing
            await asyncio.sleep(0.05 + (i % 3) * 0.02)
            
            # Record success
            await integration.record_selector_success(
                selector_id=selector_id,
                correlation_id=correlation_id,
                confidence_score=0.8 + (i % 5) * 0.04,
                resolution_time_ms=50 + (i % 4) * 10,
                elements_found=1 + (i % 3)
            )
            
            logger.info(f"  ✅ Operation {i+1}: {selector_id} ({strategy})")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Show results
        health = await manager.get_health_status()
        metrics = await manager.get_system_metrics()
        
        logger.info("📈 Quickstart Results:")
        logger.info(f"   - Total operations: {metrics.total_operations}")
        logger.info(f"   - Success rate: {metrics.successful_operations / max(metrics.total_operations, 1) * 100:.1f}%")
        logger.info(f"   - System healthy: {health.healthy}")
        logger.info(f"   - Memory usage: {health.memory_usage_mb:.1f}MB")
        logger.info(f"   - Uptime: {metrics.uptime_seconds:.1f}s")
        
        if health.issues:
            logger.warning("⚠️  Health issues:")
            for issue in health.issues:
                logger.warning(f"   - {issue}")
        
        logger.info("🎉 Quickstart demo completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(quickstart_demo())
    except KeyboardInterrupt:
        logger.info("👋 Quickstart demo interrupted")
    except Exception as e:
        logger.error(f"❌ Quickstart demo failed: {e}")
        sys.exit(1)
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        self.logger.info(f"📝 Created quickstart script: {script_path}")
        return str(script_path)
    
    def create_requirements_file(self) -> str:
        """Create requirements file for telemetry dependencies."""
        requirements_path = self.setup_dir / "requirements.txt"
        
        requirements = [
            "# Core dependencies",
            "asyncio-mqtt>=0.13.0",
            "psutil>=5.9.0",
            "pydantic>=2.0.0",
            
            "# Optional InfluxDB support",
            "influxdb-client>=1.38.0",
            
            "# JSON schema validation",
            "jsonschema>=4.17.0",
            
            "# Performance monitoring",
            "memory-profiler>=0.60.0",
            
            "# Development dependencies",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ]
        
        with open(requirements_path, 'w') as f:
            f.write('\n'.join(requirements))
        
        self.logger.info(f"📝 Created requirements file: {requirements_path}")
        return str(requirements_path)
    
    async def run_setup(self) -> bool:
        """Run complete setup process."""
        self.logger.info("🔧 Starting Selector Telemetry System Setup")
        
        # Step 1: Validate quickstart compatibility
        if not self.validate_quickstart_compatibility():
            return False
        
        # Step 2: Create configuration files
        config_file = self.create_sample_config()
        requirements_file = self.create_requirements_file()
        quickstart_script = self.create_quickstart_script()
        
        # Step 3: Test basic functionality
        if not await self.test_basic_functionality():
            self.logger.error("❌ Basic functionality test failed")
            return False
        
        # Step 4: Create setup summary
        self._create_setup_summary(config_file, requirements_file, quickstart_script)
        
        self.logger.info("🎉 Setup completed successfully!")
        return True
    
    def _create_setup_summary(self, config_file: str, requirements_file: str, quickstart_script: str):
        """Create setup summary file."""
        summary_path = self.setup_dir / "SETUP_SUMMARY.md"
        
        summary_content = f"""# Selector Telemetry System Setup Summary

**Date**: {asyncio.get_event_loop().time()}
**Status**: ✅ Setup completed successfully

## Created Files

1. **Configuration**: `{config_file}`
   - Sample telemetry configuration
   - Optimized for development and testing
   - Easily customizable for production

2. **Requirements**: `{requirements_file}`
   - All required dependencies
   - Optional InfluxDB support
   - Development tools included

3. **Quickstart Script**: `{quickstart_script}`
   - Executable demonstration script
   - Shows basic telemetry functionality
   - Ready to run: `python {quickstart_script}`

## Next Steps

1. **Install Dependencies**:
   ```bash
   pip install -r {requirements_file}
   ```

2. **Run Quickstart Demo**:
   ```bash
   python {quickstart_script}
   ```

3. **Customize Configuration**:
   - Edit `{config_file}` for your needs
   - Adjust thresholds and retention policies
   - Configure storage backend (JSON/InfluxDB)

4. **Integrate with Your Code**:
   - Follow the quickstart guide
   - Add telemetry hooks to selector operations
   - Configure alerts and reporting

5. **Production Setup**:
   - Set up InfluxDB for high-performance storage
   - Configure appropriate retention policies
   - Set up monitoring dashboards

## Validation Results

✅ Quickstart guide compatibility verified
✅ Basic functionality test passed
✅ Configuration validation successful
✅ All required modules present

## Support

- Quickstart Guide: `specs/007-selector-telemetry/quickstart.md`
- Examples: `examples/telemetry/integration_examples.py`
- Documentation: `docs/telemetry/`
- Issues: Check logs in `logs/telemetry.log`
"""
        
        with open(summary_path, 'w') as f:
            f.write(summary_content)
        
        self.logger.info(f"📝 Created setup summary: {summary_path}")


async def main():
    """Main setup function."""
    setup = TelemetrySetup()
    
    try:
        success = await setup.run_setup()
        if success:
            print("\n🎉 Selector Telemetry System setup completed successfully!")
            print("\nNext steps:")
            print("1. Install dependencies: pip install -r requirements.txt")
            print("2. Run quickstart: python run_quickstart.py")
            print("3. Check setup summary: SETUP_SUMMARY.md")
        else:
            print("\n❌ Setup failed. Check the logs above for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Setup interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
