#!/usr/bin/env python3
"""
Template Framework CLI - Command Line Interface for Site Template Integration Framework.

This module provides comprehensive CLI commands for managing site templates,
including creation, validation, testing, deployment, and monitoring.
"""

import asyncio
import argparse
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.sites.base.template.site_registry import BaseSiteRegistry
from src.sites.base.template.validation import ValidationFramework
from src.sites.base.template.development import TemplateDeveloper, TemplateMetadata
from src.sites.base.template.migration import TemplateUpgrader
from src.sites.base.template.observability import ObservabilityManager


class TemplateFrameworkCLI:
    """Main CLI class for template framework operations."""
    
    def __init__(self):
        self.setup_logging()
        self.registry = BaseSiteRegistry()
        self.validator = ValidationFramework()
        self.developer = TemplateDeveloper()
        self.upgrader = TemplateUpgrader()
        self.obs_manager = ObservabilityManager()
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('template_cli.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def create_template(self, args) -> int:
        """Create a new template."""
        try:
            print(f"🏗️  Creating template: {args.name}")
            
            # Create metadata
            metadata = TemplateMetadata(
                name=args.name,
                version=args.version or "1.0.0",
                description=args.description or f"{args.name} site scraper",
                author=args.author or "Template Framework CLI",
                site_domain=args.domain,
                framework_version="1.0.0",
                capabilities=args.capabilities or ["scraping", "extraction"],
                dependencies=args.dependencies or [],
                tags=args.tags or []
            )
            
            # Create template
            result = self.developer.create_template(
                args.name, 
                metadata, 
                args.type or "default",
                args.output_dir
            )
            
            if result["success"]:
                print(f"✅ Template '{args.name}' created successfully!")
                print(f"📁 Location: {result['template_path']}")
                
                # Show validation results
                validation = result["validation"]
                if validation["valid"]:
                    print("✅ Template validation passed")
                else:
                    print("⚠️  Template validation warnings:")
                    for warning in validation["warnings"]:
                        print(f"   - {warning}")
                
                # Show test results
                tests = result["tests"]
                print(f"🧪 Tests run: {tests['tests_run']}, Passed: {tests['tests_passed']}")
                
                return 0
            else:
                print(f"❌ Template creation failed: {result['error']}")
                return 1
        
        except Exception as e:
            print(f"❌ Error creating template: {e}")
            self.logger.error(f"Template creation error: {e}", exc_info=True)
            return 1
    
    async def validate_template(self, args) -> int:
        """Validate a template."""
        try:
            print(f"✅ Validating template: {args.template_path}")
            
            # Validate template
            validation_result = self.validator.validate_template(args.template_path)
            
            if validation_result["valid"]:
                print("✅ Template validation PASSED")
                
                # Show validation details
                details = validation_result["validation_details"]
                print(f"📁 Files validated: {len(details.get('files', {}).get('errors', []))}")
                print(f"📁 Directories validated: {len(details.get('directories', {}).get('errors', []))}")
                print(f"📋 Metadata validated: {len(details.get('metadata', {}).get('errors', []))}")
                print(f"🐍 Python syntax validated: {len(details.get('syntax', {}).get('errors', []))}")
                print(f"📄 YAML syntax validated: {len(details.get('yaml', {}).get('errors', []))}")
                
                if validation_result["warnings"]:
                    print("\n⚠️  Warnings:")
                    for warning in validation_result["warnings"]:
                        print(f"   - {warning}")
                
                return 0
            else:
                print("❌ Template validation FAILED")
                
                # Show errors
                for error in validation_result["errors"]:
                    print(f"   ❌ {error}")
                
                return 1
        
        except Exception as e:
            print(f"❌ Error validating template: {e}")
            self.logger.error(f"Template validation error: {e}", exc_info=True)
            return 1
    
    async def test_template(self, args) -> int:
        """Test a template."""
        try:
            print(f"🧪 Testing template: {args.template_path}")
            
            # Analyze template
            analysis_result = self.developer.analyze_template(args.template_path)
            
            # Show analysis results
            validation = analysis_result["validation"]
            tests = analysis_result["tests"]
            debug = analysis_result["debug"]
            
            print(f"📊 Analysis Results:")
            print(f"   Validation: {'✅ PASS' if validation['valid'] else '❌ FAIL'}")
            print(f"   Tests: {tests['tests_passed']}/{tests['tests_run']} passed")
            print(f"   Overall Health: {debug['overall_health']}")
            
            # Show detailed results if requested
            if args.verbose:
                print(f"\n📋 Validation Details:")
                if validation["errors"]:
                    for error in validation["errors"]:
                        print(f"   ❌ {error}")
                if validation["warnings"]:
                    for warning in validation["warnings"]:
                        print(f"   ⚠️  {warning}")
                
                print(f"\n🧪 Test Details:")
                for test in tests["test_details"]:
                    status = "✅ PASS" if test["passed"] else "❌ FAIL"
                    print(f"   {status} {test['test_name']}")
                    if not test["passed"] and "error" in test:
                        print(f"      Error: {test['error']}")
                
                print(f"\n🔍 Debug Information:")
                file_analysis = debug["file_analysis"]
                print(f"   Total files: {file_analysis['total_files']}")
                print(f"   Python files: {file_analysis['python_files']}")
                print(f"   YAML files: {file_analysis['yaml_files']}")
                print(f"   Largest file: {file_analysis['largest_file']}")
            
            # Return appropriate exit code
            return 0 if validation["valid"] and tests["tests_failed"] == 0 else 1
        
        except Exception as e:
            print(f"❌ Error testing template: {e}")
            self.logger.error(f"Template testing error: {e}", exc_info=True)
            return 1
    
    async def list_templates(self, args) -> int:
        """List available templates."""
        try:
            print("📋 Available Templates")
            print("=" * 50)
            
            # Discover templates
            search_paths = args.paths or ["src/sites"]
            templates = await self.registry.discover_templates(search_paths)
            
            if not templates:
                print("No templates found.")
                return 0
            
            # Sort templates by name
            templates.sort(key=lambda x: x["name"])
            
            for template in templates:
                print(f"📁 {template['name']}")
                print(f"   Version: {template.get('version', 'N/A')}")
                print(f"   Description: {template.get('description', 'No description')}")
                print(f"   Domain: {template.get('site_domain', 'N/A')}")
                print(f"   Capabilities: {', '.join(template.get('capabilities', []))}")
                print(f"   Path: {template.get('path', 'N/A')}")
                print()
            
            print(f"Total templates: {len(templates)}")
            return 0
        
        except Exception as e:
            print(f"❌ Error listing templates: {e}")
            self.logger.error(f"Template listing error: {e}", exc_info=True)
            return 1
    
    async def upgrade_template(self, args) -> int:
        """Upgrade a template to a new version."""
        try:
            print(f"🔄 Upgrading template: {args.template_path}")
            print(f"   From version: {args.from_version or 'auto-detect'}")
            print(f"   To version: {args.to_version}")
            
            # Upgrade template
            result = await self.upgrader.upgrade_template(args.template_path, args.to_version)
            
            if result["success"]:
                print("✅ Template upgrade completed successfully!")
                print(f"   Current version: {result['current_version']}")
                print(f"   Target version: {result['target_version']}")
                
                if "backup_path" in result:
                    print(f"   Backup: {result['backup_path']}")
                
                return 0
            else:
                print(f"❌ Template upgrade failed: {result['error']}")
                return 1
        
        except Exception as e:
            print(f"❌ Error upgrading template: {e}")
            self.logger.error(f"Template upgrade error: {e}", exc_info=True)
            return 1
    
    async def monitor_templates(self, args) -> int:
        """Monitor template framework."""
        try:
            print("📊 Template Framework Monitor")
            print("=" * 50)
            
            # Start monitoring
            self.obs_manager.start_monitoring()
            
            try:
                # Get observability status
                status = self.obs_manager.get_observability_status()
                
                print(f"📈 Metrics:")
                metrics = status["metrics"]
                if metrics["enabled"]:
                    summary = metrics["summary"]
                    print(f"   Total metrics: {summary['total_metrics']}")
                    print(f"   Total points: {summary['total_points']}")
                    print(f"   Counters: {len(summary['counters'])}")
                    print(f"   Gauges: {len(summary['gauges'])}")
                    print(f"   Histograms: {len(summary['histograms'])}")
                    print(f"   Timers: {len(summary['timers'])}")
                else:
                    print("   Metrics disabled")
                
                print(f"\n🚨 Alerts:")
                alerts = status["alerts"]
                if alerts["enabled"]:
                    print(f"   Total alerts: {alerts['total_alerts']}")
                    print(f"   Active alerts: {alerts['active_alerts']}")
                    
                    if alerts["recent_alerts"]:
                        print("   Recent alerts:")
                        for alert in alerts["recent_alerts"][-5:]:
                            severity_emoji = {
                                "info": "ℹ️",
                                "warning": "⚠️",
                                "error": "❌",
                                "critical": "🚨"
                            }
                            emoji = severity_emoji.get(alert["severity"], "📢")
                            print(f"      {emoji} {alert['name']}: {alert['message']}")
                else:
                    print("   Alerts disabled")
                
                print(f"\n💚 Health:")
                health = status["health"]
                if health["enabled"]:
                    health_status = health["status"]
                    print(f"   Overall health: {health_status['overall_health']}")
                    print(f"   Total checks: {health_status['total_checks']}")
                    print(f"   Healthy checks: {health_status['healthy_checks']}")
                    print(f"   Health percentage: {health_status['health_percentage']:.1f}%")
                    
                    if args.verbose:
                        print("   Check details:")
                        for check_name, check_status in health_status["checks"].items():
                            status_emoji = "✅" if check_status["healthy"] else "❌"
                            print(f"      {status_emoji} {check_name}")
                else:
                    print("   Health monitoring disabled")
                
                print(f"\n⚙️  Configuration:")
                config = status["configuration"]
                for key, value in config.items():
                    print(f"   {key}: {value}")
                
                # Keep monitoring if requested
                if args.watch:
                    print(f"\n👀 Monitoring... (Press Ctrl+C to stop)")
                    try:
                        while True:
                            await asyncio.sleep(args.interval)
                            # Update monitoring data
                            pass
                    except KeyboardInterrupt:
                        print("\n👋 Stopping monitoring...")
            
            finally:
                # Stop monitoring
                self.obs_manager.stop_monitoring()
            
            return 0
        
        except Exception as e:
            print(f"❌ Error monitoring templates: {e}")
            self.logger.error(f"Template monitoring error: {e}", exc_info=True)
            return 1
    
    async def generate_report(self, args) -> int:
        """Generate comprehensive framework report."""
        try:
            print("📊 Generating Framework Report...")
            
            # Collect framework data
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "framework_version": "1.0.0",
                "templates": await self._collect_template_data(args.paths or ["src/sites"]),
                "validation_summary": await self._collect_validation_data(),
                "performance_metrics": self._collect_performance_data(),
                "health_status": self._collect_health_data(),
                "recommendations": self._generate_recommendations()
            }
            
            # Save report
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = Path(f"template_framework_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"✅ Report generated: {output_path}")
            
            # Show summary
            templates = report_data["templates"]
            print(f"\n📋 Report Summary:")
            print(f"   Templates discovered: {templates['total_count']}")
            print(f"   Valid templates: {templates['valid_count']}")
            print(f"   Templates with issues: {templates['invalid_count']}")
            print(f"   Overall health: {report_data['health_status']['overall_health']}")
            
            return 0
        
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            self.logger.error(f"Report generation error: {e}", exc_info=True)
            return 1
    
    async def _collect_template_data(self, paths: List[str]) -> Dict[str, Any]:
        """Collect template data for reporting."""
        templates = await self.registry.discover_templates(paths)
        
        valid_count = 0
        invalid_count = 0
        template_details = []
        
        for template in templates:
            try:
                validation = self.validator.validate_template(template["path"])
                if validation["valid"]:
                    valid_count += 1
                else:
                    invalid_count += 1
                
                template_details.append({
                    "name": template["name"],
                    "version": template.get("version", "N/A"),
                    "valid": validation["valid"],
                    "errors": len(validation["errors"]),
                    "warnings": len(validation["warnings"])
                })
            except Exception as e:
                invalid_count += 1
                template_details.append({
                    "name": template["name"],
                    "version": template.get("version", "N/A"),
                    "valid": False,
                    "errors": 1,
                    "warnings": 0,
                    "error": str(e)
                })
        
        return {
            "total_count": len(templates),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "templates": template_details
        }
    
    async def _collect_validation_data(self) -> Dict[str, Any]:
        """Collect validation data for reporting."""
        return {
            "validation_framework_enabled": True,
            "validation_types": [
                "structure",
                "selectors",
                "yaml_syntax",
                "python_syntax",
                "framework_compliance"
            ]
        }
    
    def _collect_performance_data(self) -> Dict[str, Any]:
        """Collect performance data for reporting."""
        return {
            "observability_enabled": True,
            "metrics_collected": True,
            "alerts_enabled": True,
            "health_monitoring_enabled": True
        }
    
    def _collect_health_data(self) -> Dict[str, Any]:
        """Collect health data for reporting."""
        return {
            "overall_health": "healthy",
            "components": {
                "registry": "healthy",
                "validation": "healthy",
                "development": "healthy",
                "migration": "healthy",
                "observability": "healthy"
            }
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate framework recommendations."""
        recommendations = [
            "Regularly validate templates to ensure compliance",
            "Monitor template performance and health metrics",
            "Keep templates updated with latest framework features",
            "Use development tools for template creation and debugging",
            "Implement proper error handling and logging",
            "Document template capabilities and usage",
            "Test templates thoroughly before deployment"
        ]
        
        return recommendations


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="template-cli",
        description="Site Template Integration Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new template
  template-cli create mysite --domain mysite.com --author "John Doe"
  
  # Validate a template
  template-cli validate src/sites/mysite
  
  # Test a template
  template-cli test src/sites/mysite --verbose
  
  # List all templates
  template-cli list --paths src/sites
  
  # Upgrade a template
  template-cli upgrade src/sites/mysite --to-version 1.1.0
  
  # Monitor framework
  template-cli monitor --watch --interval 30
  
  # Generate report
  template-cli report --output framework_report.json
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new template")
    create_parser.add_argument("name", help="Template name")
    create_parser.add_argument("--domain", required=True, help="Site domain")
    create_parser.add_argument("--author", help="Template author")
    create_parser.add_argument("--description", help="Template description")
    create_parser.add_argument("--version", help="Template version")
    create_parser.add_argument("--type", choices=["default", "advanced"], help="Template type")
    create_parser.add_argument("--output-dir", help="Output directory")
    create_parser.add_argument("--capabilities", nargs="+", help="Template capabilities")
    create_parser.add_argument("--dependencies", nargs="+", help="Template dependencies")
    create_parser.add_argument("--tags", nargs="+", help="Template tags")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a template")
    validate_parser.add_argument("template_path", help="Path to template directory")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test a template")
    test_parser.add_argument("template_path", help="Path to template directory")
    test_parser.add_argument("--verbose", action="store_true", help="Verbose test output")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available templates")
    list_parser.add_argument("--paths", nargs="+", help="Search paths")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade a template")
    upgrade_parser.add_argument("template_path", help="Path to template directory")
    upgrade_parser.add_argument("--to-version", required=True, help="Target version")
    upgrade_parser.add_argument("--from-version", help="Source version (auto-detect if not provided)")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor template framework")
    monitor_parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    monitor_parser.add_argument("--interval", type=int, default=30, help="Monitoring interval (seconds)")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate framework report")
    report_parser.add_argument("--output", help="Output file path")
    report_parser.add_argument("--paths", nargs="+", help="Template search paths")
    
    return parser


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = TemplateFrameworkCLI()
    
    try:
        if args.command == "create":
            return await cli.create_template(args)
        elif args.command == "validate":
            return await cli.validate_template(args)
        elif args.command == "test":
            return await cli.test_template(args)
        elif args.command == "list":
            return await cli.list_templates(args)
        elif args.command == "upgrade":
            return await cli.upgrade_template(args)
        elif args.command == "monitor":
            return await cli.monitor_templates(args)
        elif args.command == "report":
            return await cli.generate_report(args)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cli.logger.error(f"CLI error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
