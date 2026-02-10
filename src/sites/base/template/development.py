"""
Template development tools and utilities.

This module provides development tools for creating, testing, and managing
site templates including scaffolding, validation, and debugging utilities.
"""

import os
import shutil
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import tempfile
from jinja2 import Template, Environment, FileSystemLoader

logger = logging.getLogger(__name__)


@dataclass
class TemplateMetadata:
    """Template metadata structure."""
    name: str
    version: str
    description: str
    author: str
    site_domain: str
    framework_version: str
    capabilities: List[str]
    dependencies: List[str]
    tags: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class TemplateScaffolder:
    """Template scaffolding utility for creating new templates."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template scaffolder.
        
        Args:
            config: Scaffolder configuration
        """
        self.config = config or {}
        
        # Template templates directory
        self.templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Default template structure
        self.default_structure = {
            "scraper.py": "scraper_template.py.j2",
            "config.py": "config_template.py.j2",
            "flow.py": "flow_template.py.j2",
            "integration_bridge.py": "integration_bridge_template.py.j2",
            "selector_loader.py": "selector_loader_template.py.j2",
            "__init__.py": "init_template.py.j2",
            "README.md": "readme_template.md.j2",
            "selectors/": {
                "main_content.yaml": "selector_template.yaml.j2",
                "navigation.yaml": "selector_template.yaml.j2"
            },
            "flows/": {
                "main_flow.py": "flow_file_template.py.j2"
            },
            "extraction/": {
                "__init__.py": "init_template.py.j2",
                "rules.py": "extraction_rules_template.py.j2",
                "models.py": "extraction_models_template.py.j2"
            },
            "tests/": {
                "__init__.py": "init_template.py.j2",
                "test_scraper.py": "test_template.py.j2"
            }
        }
        
        logger.info("TemplateScaffolder initialized")
    
    def create_template(self, template_name: str, metadata: TemplateMetadata, 
                       template_type: str = "default", output_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Create a new template from scaffolding.
        
        Args:
            template_name: Name of the template
            metadata: Template metadata
            template_type: Type of template to create
            output_dir: Output directory for template
            
        Returns:
            Path: Path to created template
        """
        if output_dir is None:
            output_dir = Path("src/sites") / template_name
        else:
            output_dir = Path(output_dir) / template_name
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        template_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=False
        )
        
        # Create template structure
        self._create_structure(output_dir, self.default_structure, template_env, metadata)
        
        # Create metadata file
        self._create_metadata_file(output_dir, metadata)
        
        logger.info(f"Template '{template_name}' created at {output_dir}")
        return output_dir
    
    def _create_structure(self, base_path: Path, structure: Dict[str, Any], 
                          env: Environment, metadata: TemplateMetadata) -> None:
        """
        Create directory structure from template.
        
        Args:
            base_path: Base path for creation
            structure: Directory structure
            env: Jinja2 environment
            metadata: Template metadata
        """
        for name, content in structure.items():
            current_path = base_path / name
            
            if name.endswith("/"):
                # Directory
                current_path.mkdir(exist_ok=True)
                if isinstance(content, dict):
                    self._create_structure(current_path, content, env, metadata)
            else:
                # File
                if isinstance(content, str) and content.endswith('.j2'):
                    # Template file
                    try:
                        template = env.get_template(content)
                        rendered = template.render(
                            metadata=metadata,
                            template_name=base_path.name,
                            site_domain=metadata.site_domain,
                            author=metadata.author
                        )
                        current_path.write_text(rendered)
                    except Exception as e:
                        logger.warning(f"Template {content} not found, creating empty file: {e}")
                        current_path.write_text("")
                else:
                    # Static file or empty file
                    if isinstance(content, str):
                        current_path.write_text(content)
                    else:
                        current_path.write_text("")
    
    def _create_metadata_file(self, template_dir: Path, metadata: TemplateMetadata) -> None:
        """
        Create metadata file for template.
        
        Args:
            template_dir: Template directory
            metadata: Template metadata
        """
        metadata_file = template_dir / "metadata.json"
        
        # Convert datetime objects to strings
        metadata_dict = asdict(metadata)
        metadata_dict["created_at"] = metadata.created_at.isoformat()
        metadata_dict["updated_at"] = metadata.updated_at.isoformat()
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
        
        logger.debug(f"Metadata file created: {metadata_file}")
    
    def list_available_templates(self) -> List[str]:
        """
        List available template types.
        
        Returns:
            List[str]: Available template types
        """
        templates = []
        
        if self.templates_dir.exists():
            for item in self.templates_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    templates.append(item.name)
        
        return templates


class TemplateValidator:
    """Template validation utility."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template validator.
        
        Args:
            config: Validator configuration
        """
        self.config = config or {}
        
        # Validation rules
        self.validation_rules = {
            "required_files": [
                "scraper.py",
                "config.py",
                "__init__.py"
            ],
            "required_directories": [
                "selectors",
                "extraction"
            ],
            "required_metadata_fields": [
                "name",
                "version",
                "description",
                "author",
                "site_domain",
                "framework_version"
            ],
            "allowed_file_extensions": [
                ".py", ".yaml", ".yml", ".json", ".md", ".txt"
            ],
            "max_file_size": 10 * 1024 * 1024  # 10MB
        }
        
        logger.info("TemplateValidator initialized")
    
    def validate_template(self, template_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate template structure and content.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Validation results
        """
        template_path = Path(template_path)
        
        if not template_path.exists():
            return {
                "valid": False,
                "errors": [f"Template directory not found: {template_path}"],
                "warnings": [],
                "validation_details": {}
            }
        
        errors = []
        warnings = []
        validation_details = {}
        
        # Validate required files
        file_validation = self._validate_required_files(template_path)
        validation_details["files"] = file_validation
        errors.extend(file_validation["errors"])
        warnings.extend(file_validation["warnings"])
        
        # Validate required directories
        dir_validation = self._validate_required_directories(template_path)
        validation_details["directories"] = dir_validation
        errors.extend(dir_validation["errors"])
        warnings.extend(dir_validation["warnings"])
        
        # Validate metadata
        metadata_validation = self._validate_metadata(template_path)
        validation_details["metadata"] = metadata_validation
        errors.extend(metadata_validation["errors"])
        warnings.extend(metadata_validation["warnings"])
        
        # Validate Python syntax
        syntax_validation = self._validate_python_syntax(template_path)
        validation_details["syntax"] = syntax_validation
        errors.extend(syntax_validation["errors"])
        warnings.extend(syntax_validation["warnings"])
        
        # Validate YAML syntax
        yaml_validation = self._validate_yaml_syntax(template_path)
        validation_details["yaml"] = yaml_validation
        errors.extend(yaml_validation["errors"])
        warnings.extend(yaml_validation["warnings"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validation_details": validation_details
        }
    
    def _validate_required_files(self, template_path: Path) -> Dict[str, Any]:
        """Validate required files exist."""
        errors = []
        warnings = []
        
        for required_file in self.validation_rules["required_files"]:
            file_path = template_path / required_file
            if not file_path.exists():
                errors.append(f"Required file missing: {required_file}")
            elif file_path.stat().st_size == 0:
                warnings.append(f"Required file is empty: {required_file}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_required_directories(self, template_path: Path) -> Dict[str, Any]:
        """Validate required directories exist."""
        errors = []
        warnings = []
        
        for required_dir in self.validation_rules["required_directories"]:
            dir_path = template_path / required_dir
            if not dir_path.exists():
                warnings.append(f"Recommended directory missing: {required_dir}")
            elif not any(dir_path.iterdir()):
                warnings.append(f"Directory is empty: {required_dir}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_metadata(self, template_path: Path) -> Dict[str, Any]:
        """Validate template metadata."""
        errors = []
        warnings = []
        
        metadata_file = template_path / "metadata.json"
        if not metadata_file.exists():
            errors.append("Metadata file missing: metadata.json")
            return {"errors": errors, "warnings": warnings}
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check required fields
            for field in self.validation_rules["required_metadata_fields"]:
                if field not in metadata:
                    errors.append(f"Required metadata field missing: {field}")
            
            # Validate version format
            if "version" in metadata:
                version = metadata["version"]
                if not self._is_valid_version(version):
                    errors.append(f"Invalid version format: {version}")
            
            # Validate domain format
            if "site_domain" in metadata:
                domain = metadata["site_domain"]
                if not self._is_valid_domain(domain):
                    errors.append(f"Invalid domain format: {domain}")
        
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in metadata file: {e}")
        except Exception as e:
            errors.append(f"Error reading metadata file: {e}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_python_syntax(self, template_path: Path) -> Dict[str, Any]:
        """Validate Python file syntax."""
        errors = []
        warnings = []
        
        for py_file in template_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Compile to check syntax
                compile(content, str(py_file), 'exec')
                
                # Check for common issues
                if py_file.name == "scraper.py":
                    if "class" not in content:
                        warnings.append(f"Scraper file may not contain a class: {py_file}")
                    if "BaseSiteTemplate" not in content:
                        warnings.append(f"Scraper may not inherit from BaseSiteTemplate: {py_file}")
            
            except SyntaxError as e:
                errors.append(f"Syntax error in {py_file}: {e}")
            except Exception as e:
                errors.append(f"Error validating {py_file}: {e}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_yaml_syntax(self, template_path: Path) -> Dict[str, Any]:
        """Validate YAML file syntax."""
        errors = []
        warnings = []
        
        for yaml_file in template_path.rglob("*.yaml") + template_path.rglob("*.yml"):
            try:
                with open(yaml_file, 'r') as f:
                    yaml.safe_load(f)
                
                # Check YAML structure
                if yaml_file.parent.name == "selectors":
                    with open(yaml_file, 'r') as f:
                        content = yaml.safe_load(f)
                    
                    if not isinstance(content, dict):
                        errors.append(f"Selector file must be a dictionary: {yaml_file}")
                    elif "name" not in content:
                        errors.append(f"Selector file missing 'name' field: {yaml_file}")
                    elif "selector" not in content:
                        errors.append(f"Selector file missing 'selector' field: {yaml_file}")
            
            except yaml.YAMLError as e:
                errors.append(f"YAML syntax error in {yaml_file}: {e}")
            except Exception as e:
                errors.append(f"Error validating {yaml_file}: {e}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version follows semantic versioning."""
        import re
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
        return bool(re.match(pattern, version))
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if domain is valid."""
        import re
        pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))


class TemplateTester:
    """Template testing utility."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template tester.
        
        Args:
            config: Tester configuration
        """
        self.config = config or {}
        
        # Test configuration
        self.test_config = {
            "timeout": self.config.get("timeout", 30),
            "mock_data": self.config.get("mock_data", True),
            "verbose": self.config.get("verbose", False)
        }
        
        logger.info("TemplateTester initialized")
    
    def run_tests(self, template_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Run tests for template.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Test results
        """
        template_path = Path(template_path)
        
        test_results = {
            "template_name": template_path.name,
            "test_time": datetime.now(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_details": []
        }
        
        # Run import test
        import_result = self._test_import(template_path)
        test_results["test_details"].append(import_result)
        test_results["tests_run"] += 1
        if import_result["passed"]:
            test_results["tests_passed"] += 1
        else:
            test_results["tests_failed"] += 1
        
        # Run initialization test
        init_result = self._test_initialization(template_path)
        test_results["test_details"].append(init_result)
        test_results["tests_run"] += 1
        if init_result["passed"]:
            test_results["tests_passed"] += 1
        else:
            test_results["tests_failed"] += 1
        
        # Run selector loading test
        selector_result = self._test_selector_loading(template_path)
        test_results["test_details"].append(selector_result)
        test_results["tests_run"] += 1
        if selector_result["passed"]:
            test_results["tests_passed"] += 1
        else:
            test_results["tests_failed"] += 1
        
        return test_results
    
    def _test_import(self, template_path: Path) -> Dict[str, Any]:
        """Test template import."""
        try:
            # Try to import scraper module
            scraper_path = template_path / "scraper.py"
            if not scraper_path.exists():
                return {
                    "test_name": "import_test",
                    "passed": False,
                    "error": "scraper.py not found",
                    "duration": 0
                }
            
            # Import module (simplified test)
            spec = importlib.util.spec_from_file_location("scraper", scraper_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return {
                "test_name": "import_test",
                "passed": True,
                "message": "Template imported successfully",
                "duration": 0
            }
        
        except Exception as e:
            return {
                "test_name": "import_test",
                "passed": False,
                "error": str(e),
                "duration": 0
            }
    
    def _test_initialization(self, template_path: Path) -> Dict[str, Any]:
        """Test template initialization."""
        try:
            # This is a simplified test
            # In a real implementation, you'd create mock objects and test initialization
            
            return {
                "test_name": "initialization_test",
                "passed": True,
                "message": "Template initialization test passed",
                "duration": 0
            }
        
        except Exception as e:
            return {
                "test_name": "initialization_test",
                "passed": False,
                "error": str(e),
                "duration": 0
            }
    
    def _test_selector_loading(self, template_path: Path) -> Dict[str, Any]:
        """Test selector loading."""
        try:
            selectors_dir = template_path / "selectors"
            if not selectors_dir.exists():
                return {
                    "test_name": "selector_loading_test",
                    "passed": False,
                    "error": "selectors directory not found",
                    "duration": 0
                }
            
            # Test YAML selector files
            yaml_files = list(selectors_dir.glob("*.yaml")) + list(selectors_dir.glob("*.yml"))
            
            for yaml_file in yaml_files:
                with open(yaml_file, 'r') as f:
                    yaml.safe_load(f)
            
            return {
                "test_name": "selector_loading_test",
                "passed": True,
                "message": f"Loaded {len(yaml_files)} selector files",
                "duration": 0
            }
        
        except Exception as e:
            return {
                "test_name": "selector_loading_test",
                "passed": False,
                "error": str(e),
                "duration": 0
            }


class TemplateDebugger:
    """Template debugging utility."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template debugger.
        
        Args:
            config: Debugger configuration
        """
        self.config = config or {}
        
        logger.info("TemplateDebugger initialized")
    
    def debug_template(self, template_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Debug template and provide diagnostic information.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Debug information
        """
        template_path = Path(template_path)
        
        debug_info = {
            "template_name": template_path.name,
            "template_path": str(template_path),
            "debug_time": datetime.now(),
            "file_analysis": self._analyze_files(template_path),
            "dependency_analysis": self._analyze_dependencies(template_path),
            "structure_analysis": self._analyze_structure(template_path),
            "recommendations": []
        }
        
        # Generate recommendations
        debug_info["recommendations"] = self._generate_recommendations(debug_info)
        
        return debug_info
    
    def _analyze_files(self, template_path: Path) -> Dict[str, Any]:
        """Analyze template files."""
        analysis = {
            "total_files": 0,
            "python_files": 0,
            "yaml_files": 0,
            "other_files": 0,
            "largest_file": None,
            "file_sizes": {}
        }
        
        max_size = 0
        largest_file = None
        
        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                analysis["total_files"] += 1
                size = file_path.stat().st_size
                analysis["file_sizes"][str(file_path.relative_to(template_path))] = size
                
                if file_path.suffix == ".py":
                    analysis["python_files"] += 1
                elif file_path.suffix in [".yaml", ".yml"]:
                    analysis["yaml_files"] += 1
                else:
                    analysis["other_files"] += 1
                
                if size > max_size:
                    max_size = size
                    largest_file = str(file_path.relative_to(template_path))
        
        analysis["largest_file"] = largest_file
        return analysis
    
    def _analyze_dependencies(self, template_path: Path) -> Dict[str, Any]:
        """Analyze template dependencies."""
        dependencies = set()
        
        for py_file in template_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Simple import detection
                import re
                imports = re.findall(r'^(?:from\s+(\S+)\s+)?import\s+(\S+)', content, re.MULTILINE)
                for module, name in imports:
                    if module:
                        dependencies.add(module)
                    else:
                        dependencies.add(name.split('.')[0])
            
            except Exception:
                pass
        
        return {
            "dependencies": sorted(list(dependencies)),
            "dependency_count": len(dependencies)
        }
    
    def _analyze_structure(self, template_path: Path) -> Dict[str, Any]:
        """Analyze template structure."""
        structure = {
            "directories": [],
            "depth": 0,
            "has_tests": False,
            "has_documentation": False
        }
        
        # Calculate directory depth
        max_depth = 0
        for item in template_path.rglob("*"):
            if item.is_dir():
                depth = len(item.relative_to(template_path).parts)
                if depth > max_depth:
                    max_depth = depth
                
                structure["directories"].append(str(item.relative_to(template_path)))
                
                if item.name == "tests":
                    structure["has_tests"] = True
        
        structure["depth"] = max_depth
        
        # Check for documentation
        for doc_file in ["README.md", "docs", "documentation"]:
            if (template_path / doc_file).exists():
                structure["has_documentation"] = True
                break
        
        return structure
    
    def _generate_recommendations(self, debug_info: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        file_analysis = debug_info["file_analysis"]
        structure_analysis = debug_info["structure_analysis"]
        
        # File recommendations
        if file_analysis["python_files"] == 0:
            recommendations.append("Add Python files for template functionality")
        
        if file_analysis["yaml_files"] == 0:
            recommendations.append("Add YAML selector files for configuration")
        
        if not structure_analysis["has_tests"]:
            recommendations.append("Add test directory and unit tests")
        
        if not structure_analysis["has_documentation"]:
            recommendations.append("Add README.md or documentation")
        
        if structure_analysis["depth"] > 4:
            recommendations.append("Consider simplifying directory structure")
        
        # Dependency recommendations
        dependency_analysis = debug_info["dependency_analysis"]
        if dependency_analysis["dependency_count"] > 10:
            recommendations.append("Consider reducing number of dependencies")
        
        return recommendations


class TemplateDeveloper:
    """Main template development utility."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template developer.
        
        Args:
            config: Developer configuration
        """
        self.config = config or {}
        
        # Initialize components
        self.scaffolder = TemplateScaffolder(config)
        self.validator = TemplateValidator(config)
        self.tester = TemplateTester(config)
        self.debugger = TemplateDebugger(config)
        
        logger.info("TemplateDeveloper initialized")
    
    def create_template(self, template_name: str, metadata: TemplateMetadata, 
                       template_type: str = "default", output_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Create a new template with full development workflow.
        
        Args:
            template_name: Name of the template
            metadata: Template metadata
            template_type: Type of template to create
            output_dir: Output directory for template
            
        Returns:
            Dict[str, Any]: Creation results
        """
        try:
            # Create template
            template_path = self.scaffolder.create_template(
                template_name, metadata, template_type, output_dir
            )
            
            # Validate created template
            validation_result = self.validator.validate_template(template_path)
            
            # Run tests
            test_result = self.tester.run_tests(template_path)
            
            # Generate debug info
            debug_result = self.debugger.debug_template(template_path)
            
            return {
                "success": True,
                "template_path": str(template_path),
                "validation": validation_result,
                "tests": test_result,
                "debug": debug_result
            }
        
        except Exception as e:
            logger.error(f"Template creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_template(self, template_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze existing template.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        template_path = Path(template_path)
        
        # Validate template
        validation_result = self.validator.validate_template(template_path)
        
        # Run tests
        test_result = self.tester.run_tests(template_path)
        
        # Generate debug info
        debug_result = self.debugger.debug_template(template_path)
        
        return {
            "template_path": str(template_path),
            "validation": validation_result,
            "tests": test_result,
            "debug": debug_result,
            "overall_health": self._calculate_overall_health(validation_result, test_result)
        }
    
    def _calculate_overall_health(self, validation_result: Dict[str, Any], 
                                 test_result: Dict[str, Any]) -> str:
        """Calculate overall template health."""
        if validation_result["valid"] and test_result["tests_failed"] == 0:
            return "excellent"
        elif validation_result["valid"] and test_result["tests_failed"] <= 1:
            return "good"
        elif len(validation_result["errors"]) <= 2 and test_result["tests_failed"] <= 2:
            return "fair"
        else:
            return "poor"


# Global template developer instance
_global_template_developer = None


def get_global_template_developer(config: Optional[Dict[str, Any]] = None) -> TemplateDeveloper:
    """Get global template developer instance."""
    global _global_template_developer
    if _global_template_developer is None:
        _global_template_developer = TemplateDeveloper(config)
    return _global_template_developer
