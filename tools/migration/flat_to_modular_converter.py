#!/usr/bin/env python3
"""
Flat to Modular Template Converter

This tool converts existing flat template scrapers to the new modular architecture.
It analyzes legacy code, identifies components, and generates modular equivalents.
"""

import ast
import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse
import logging


@dataclass
class ComponentInfo:
    """Information about a detected component."""
    name: str
    type: str
    methods: List[str]
    attributes: List[str]
    dependencies: List[str]
    file_path: str
    line_number: int
    confidence: float


@dataclass
class MigrationPlan:
    """Migration plan for converting flat template to modular."""
    original_file: str
    components: List[ComponentInfo]
    new_files: Dict[str, str]
    config_updates: Dict[str, Any]
    migration_steps: List[str]
    warnings: List[str]
    estimated_effort: str


class FlatTemplateAnalyzer:
    """Analyzes flat template files to identify components."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.component_patterns = {
            'extractor': r'(class.*(?:Extractor|Scraper).*:|def.*extract.*\(|def.*scrape.*\()',
            'validator': r'(class.*(?:Validator|Validation).*:|def.*validate.*\()',
            'transformer': r'(class.*(?:Transformer|Processor).*:|def.*transform.*\(|def.*process.*\()',
            'config': r'(class.*(?:Config|Configuration).*:|def.*config.*\()',
            'browser': r'(class.*(?:Browser|Driver).*:|def.*browser.*\()',
        }
    
    def analyze_file(self, file_path: str) -> List[ComponentInfo]:
        """Analyze a Python file to identify components."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            components = []
            
            # Find classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    component = self._analyze_class(node, file_path, content)
                    if component:
                        components.append(component)
                elif isinstance(node, ast.FunctionDef):
                    component = self._analyze_function(node, file_path, content)
                    if component:
                        components.append(component)
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error analyzing file {file_path}: {e}")
            return []
    
    def _analyze_class(self, node: ast.ClassDef, file_path: str, content: str) -> Optional[ComponentInfo]:
        """Analyze a class node to determine component type."""
        class_name = node.name
        class_content = self._get_node_content(node, content)
        
        # Determine component type
        component_type = self._classify_component(class_name, class_content)
        if not component_type:
            return None
        
        # Extract methods and attributes
        methods = []
        attributes = []
        dependencies = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
                # Look for dependencies in method signatures
                for arg in item.args.args:
                    if arg.arg not in ['self', 'cls']:
                        dependencies.append(arg.arg)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
        
        # Calculate confidence
        confidence = self._calculate_confidence(class_name, class_content, component_type)
        
        return ComponentInfo(
            name=class_name,
            type=component_type,
            methods=methods,
            attributes=attributes,
            dependencies=dependencies,
            file_path=file_path,
            line_number=node.lineno,
            confidence=confidence
        )
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: str, content: str) -> Optional[ComponentInfo]:
        """Analyze a function node to determine if it's a component."""
        func_name = node.name
        func_content = self._get_node_content(node, content)
        
        # Determine component type
        component_type = self._classify_function(func_name, func_content)
        if not component_type:
            return None
        
        # Extract dependencies
        dependencies = []
        for arg in node.args.args:
            if arg.arg not in ['self', 'cls']:
                dependencies.append(arg.arg)
        
        return ComponentInfo(
            name=func_name,
            type=component_type,
            methods=[func_name],
            attributes=[],
            dependencies=dependencies,
            file_path=file_path,
            line_number=node.lineno,
            confidence=0.7  # Lower confidence for functions
        )
    
    def _get_node_content(self, node, content: str) -> str:
        """Get the content of an AST node."""
        lines = content.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1 if hasattr(node, 'end_lineno') else start_line
        return '\n'.join(lines[start_line:end_line + 1])
    
    def _classify_component(self, name: str, content: str) -> Optional[str]:
        """Classify a component based on name and content."""
        name_lower = name.lower()
        content_lower = content.lower()
        
        for component_type, pattern in self.component_patterns.items():
            if re.search(pattern, name_lower, re.IGNORECASE):
                return component_type
            if re.search(pattern, content_lower, re.IGNORECASE):
                return component_type
        
        return None
    
    def _classify_function(self, name: str, content: str) -> Optional[str]:
        """Classify a function based on name and content."""
        name_lower = name.lower()
        
        if 'extract' in name_lower or 'scrape' in name_lower:
            return 'extractor'
        elif 'validate' in name_lower:
            return 'validator'
        elif 'transform' in name_lower or 'process' in name_lower:
            return 'transformer'
        elif 'config' in name_lower:
            return 'config'
        elif 'browser' in name_lower or 'driver' in name_lower:
            return 'browser'
        
        return None
    
    def _calculate_confidence(self, name: str, content: str, component_type: str) -> float:
        """Calculate confidence score for component classification."""
        confidence = 0.5  # Base confidence
        
        name_lower = name.lower()
        
        # Boost confidence based on name
        if component_type in name_lower:
            confidence += 0.3
        
        # Boost confidence based on common patterns
        if component_type == 'extractor':
            if any(keyword in content.lower() for keyword in ['selenium', 'beautifulsoup', 'lxml', 'scrapy']):
                confidence += 0.2
        elif component_type == 'validator':
            if any(keyword in content.lower() for keyword in ['validate', 'check', 'verify']):
                confidence += 0.2
        elif component_type == 'transformer':
            if any(keyword in content.lower() for keyword in ['transform', 'process', 'convert']):
                confidence += 0.2
        
        return min(confidence, 1.0)


class ModularCodeGenerator:
    """Generates modular code from component analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Load code templates."""
        return {
            'extractor': '''from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult

class {name}Component(BaseComponent):
    """Generated extractor component from {original_file}."""
    
    def __init__(self):
        super().__init__("{name_lower}_extractor")
    
    async def execute(self, context: ComponentContext, **kwargs) -> ComponentResult:
        """Execute extraction logic."""
        try:
            # TODO: Migrate extraction logic from original code
            # Original file: {original_file}
            # Line: {line_number}
            
            # Placeholder extraction logic
            data = context.data.get("input_data", {{}})
            
            # Add your extraction logic here
            extracted_data = {{
                "extracted": True,
                "source": "migrated_component"
            }}
            
            return ComponentResult(
                success=True,
                data=extracted_data
            )
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {{e}}")
            return ComponentResult(
                success=False,
                errors=[str(e)]
            )
''',
            
            'validator': '''from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult

class {name}Component(BaseComponent):
    """Generated validator component from {original_file}."""
    
    def __init__(self):
        super().__init__("{name_lower}_validator")
    
    async def execute(self, context: ComponentContext, **kwargs) -> ComponentResult:
        """Execute validation logic."""
        try:
            # TODO: Migrate validation logic from original code
            # Original file: {original_file}
            # Line: {line_number}
            
            data = context.data.get("input_data", {{}})
            
            # Add your validation logic here
            validation_result = {{
                "valid": True,
                "errors": [],
                "warnings": []
            }}
            
            return ComponentResult(
                success=validation_result["valid"],
                data=validation_result
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed: {{e}}")
            return ComponentResult(
                success=False,
                errors=[str(e)]
            )
''',
            
            'transformer': '''from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult

class {name}Component(BaseComponent):
    """Generated transformer component from {original_file}."""
    
    def __init__(self):
        super().__init__("{name_lower}_transformer")
    
    async def execute(self, context: ComponentContext, **kwargs) -> ComponentResult:
        """Execute transformation logic."""
        try:
            # TODO: Migrate transformation logic from original code
            # Original file: {original_file}
            # Line: {line_number}
            
            data = context.data.get("input_data", {{}})
            
            # Add your transformation logic here
            transformed_data = {{
                "transformed": True,
                "original": data
            }}
            
            return ComponentResult(
                success=True,
                data=transformed_data
            )
            
        except Exception as e:
            self.logger.error(f"Transformation failed: {{e}}")
            return ComponentResult(
                success=False,
                errors=[str(e)]
            )
''',
            
            'config': '''"""
Configuration for migrated components.
Generated from {original_file}
"""

from typing import Dict, Any

# Component configuration
COMPONENT_CONFIG = {{
    "{name_lower}": {{
        "enabled": True,
        "priority": 1,
        "retry_count": 3,
        "timeout": 30
    }}
}}

# Migration notes
MIGRATION_NOTES = [
    "Configuration migrated from {original_file}",
    "Line: {line_number}",
    "Review and update configuration as needed"
]
'''
        }
    
    def generate_component_file(self, component: ComponentInfo) -> str:
        """Generate a component file from component info."""
        template = self.templates.get(component.type, self.templates['extractor'])
        
        return template.format(
            name=component.name,
            name_lower=component.name.lower(),
            original_file=component.file_path,
            line_number=component.line_number
        )
    
    def generate_config_file(self, components: List[ComponentInfo], original_file: str) -> str:
        """Generate configuration file for migrated components."""
        config_data = {
            "components": {},
            "plugins": {},
            "browser": {
                "headless": True,
                "viewport": {"width": 1920, "height": 1080}
            },
            "selectors": {},
            "migration_info": {
                "original_file": original_file,
                "migrated_at": datetime.utcnow().isoformat(),
                "component_count": len(components)
            }
        }
        
        # Add component configurations
        for component in components:
            config_data["components"][component.name.lower()] = {
                "enabled": True,
                "priority": 1,
                "retry_count": 3,
                "timeout": 30,
                "migration": {
                    "original_file": component.file_path,
                    "line_number": component.line_number,
                    "confidence": component.confidence
                }
            }
        
        return yaml.dump(config_data, default_flow_style=False, indent=2)
    
    def generate_main_scraper(self, components: List[ComponentInfo], original_file: str) -> str:
        """Generate main modular scraper file."""
        component_imports = []
        component_registrations = []
        
        for component in components:
            component_name = component.name
            component_file = f"{component_name.lower()}_component"
            
            component_imports.append(f"from .components.{component_file} import {component_name}Component")
            component_registrations.append(f"    register_component({component_name}Component())")
        
        return f'''"""
Modular scraper migrated from {original_file}
Generated on: {datetime.utcnow().isoformat()}
"""

import asyncio
from src.sites.base.component_interface import register_component
from src.sites.base.site_scraper import ModularSiteScraper

# Import migrated components
{chr(10).join(component_imports)}

class MigratedScraper(ModularSiteScraper):
    """Migrated modular scraper."""
    
    def __init__(self):
        super().__init__("migrated_site")
    
    async def setup_components(self):
        """Setup migrated components."""
        # Register migrated components
{chr(10).join(component_registrations)}

# Auto-register components
def auto_register_components():
    """Auto-register all migrated components."""
{chr(10).join(component_registrations)}

# Execute auto-registration
auto_register_components()
'''


class FlatToModularConverter:
    """Main converter class for flat to modular template conversion."""
    
    def __init__(self, output_dir: str = "migrated_output"):
        self.output_dir = Path(output_dir)
        self.analyzer = FlatTemplateAnalyzer()
        self.generator = ModularCodeGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
    
    def convert_file(self, file_path: str) -> MigrationPlan:
        """Convert a single flat template file to modular architecture."""
        self.logger.info(f"Converting file: {file_path}")
        
        # Analyze the file
        components = self.analyzer.analyze_file(file_path)
        
        if not components:
            self.logger.warning(f"No components found in {file_path}")
            return MigrationPlan(
                original_file=file_path,
                components=[],
                new_files={},
                config_updates={},
                migration_steps=[f"No components found in {file_path}"],
                warnings=[f"No components detected in {file_path}"],
                estimated_effort="Low"
            )
        
        # Generate new files
        new_files = {}
        
        # Generate component files
        for component in components:
            component_code = self.generator.generate_component_file(component)
            component_file_name = f"{component.name.lower()}_component.py"
            component_path = self.output_dir / "components" / component_file_name
            
            # Create components directory
            component_path.parent.mkdir(exist_ok=True)
            
            new_files[str(component_path)] = component_code
        
        # Generate configuration
        config_code = self.generator.generate_config_file(components, file_path)
        config_path = self.output_dir / "config.yaml"
        new_files[str(config_path)] = config_code
        
        # Generate main scraper
        scraper_code = self.generator.generate_main_scraper(components, file_path)
        scraper_path = self.output_dir / "scraper.py"
        new_files[str(scraper_path)] = scraper_code
        
        # Create migration plan
        migration_steps = [
            f"Analyzed {file_path} and found {len(components)} components",
            f"Generated {len(components)} component files",
            "Generated configuration file (config.yaml)",
            "Generated main scraper file (scraper.py)",
            "Review and test generated code",
            "Update imports and dependencies as needed"
        ]
        
        warnings = []
        for component in components:
            if component.confidence < 0.7:
                warnings.append(f"Low confidence ({component.confidence:.2f}) for component {component.name}")
        
        estimated_effort = self._estimate_effort(components)
        
        return MigrationPlan(
            original_file=file_path,
            components=components,
            new_files=new_files,
            config_updates={},
            migration_steps=migration_steps,
            warnings=warnings,
            estimated_effort=estimated_effort
        )
    
    def convert_directory(self, dir_path: str) -> List[MigrationPlan]:
        """Convert all Python files in a directory."""
        self.logger.info(f"Converting directory: {dir_path}")
        
        migration_plans = []
        
        for py_file in Path(dir_path).rglob("*.py"):
            if py_file.name != "__init__.py":
                try:
                    plan = self.convert_file(str(py_file))
                    migration_plans.append(plan)
                except Exception as e:
                    self.logger.error(f"Error converting {py_file}: {e}")
        
        return migration_plans
    
    def execute_migration_plan(self, plan: MigrationPlan) -> bool:
        """Execute a migration plan by writing new files."""
        try:
            for file_path, content in plan.new_files.items():
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.logger.info(f"Created: {file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing migration plan: {e}")
            return False
    
    def generate_migration_report(self, plans: List[MigrationPlan]) -> str:
        """Generate a comprehensive migration report."""
        report = {
            "summary": {
                "total_files": len(plans),
                "total_components": sum(len(plan.components) for plan in plans),
                "total_new_files": sum(len(plan.new_files) for plan in plans),
                "generated_at": datetime.utcnow().isoformat()
            },
            "files": []
        }
        
        for plan in plans:
            file_report = {
                "original_file": plan.original_file,
                "components_found": len(plan.components),
                "components": [
                    {
                        "name": comp.name,
                        "type": comp.type,
                        "confidence": comp.confidence,
                        "methods": comp.methods
                    }
                    for comp in plan.components
                ],
                "new_files": list(plan.new_files.keys()),
                "warnings": plan.warnings,
                "estimated_effort": plan.estimated_effort
            }
            report["files"].append(file_report)
        
        return json.dumps(report, indent=2)
    
    def _estimate_effort(self, components: List[ComponentInfo]) -> str:
        """Estimate migration effort based on components."""
        total_confidence = sum(comp.confidence for comp in components)
        avg_confidence = total_confidence / len(components) if components else 0
        
        if avg_confidence > 0.8:
            return "Low"
        elif avg_confidence > 0.6:
            return "Medium"
        else:
            return "High"


def main():
    """Main entry point for the converter."""
    parser = argparse.ArgumentParser(description="Convert flat templates to modular architecture")
    parser.add_argument("input", help="Input file or directory to convert")
    parser.add_argument("-o", "--output", default="migrated_output", help="Output directory")
    parser.add_argument("-e", "--execute", action="store_true", help="Execute migration (write files)")
    parser.add_argument("-r", "--report", help="Generate migration report file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create converter
    converter = FlatToModularConverter(args.output)
    
    # Convert input
    input_path = Path(args.input)
    
    if input_path.is_file():
        plans = [converter.convert_file(str(input_path))]
    elif input_path.is_dir():
        plans = converter.convert_directory(str(input_path))
    else:
        print(f"Error: Input path {args.input} does not exist")
        return 1
    
    # Generate report
    report = converter.generate_migration_report(plans)
    
    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"Migration report saved to: {args.report}")
    else:
        print(report)
    
    # Execute migration if requested
    if args.execute:
        print("\nExecuting migration plans...")
        for plan in plans:
            success = converter.execute_migration_plan(plan)
            if success:
                print(f"✅ Successfully migrated: {plan.original_file}")
            else:
                print(f"❌ Failed to migrate: {plan.original_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
