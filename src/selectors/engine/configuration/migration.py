"""
Configuration migration tools for converting hardcoded selectors to YAML format.

This module provides utilities to migrate existing hardcoded selector definitions
to the YAML-based configuration system format.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from ...models.selector_config import (
    SelectorConfiguration,
    ConfigurationMetadata,
    ContextDefaults,
    ValidationDefaults,
    SemanticSelector,
    StrategyDefinition,
    ValidationRule,
    ConfidenceConfig,
    StrategyTemplate
)
from .validator import ConfigurationValidator


class ConfigurationMigrator:
    """Tool for migrating hardcoded selectors to YAML configuration format."""
    
    def __init__(self):
        """Initialize the configuration migrator."""
        self.logger = logging.getLogger(__name__)
        self.validator = ConfigurationValidator()
    
    def migrate_from_dict(self, 
                         selectors_dict: Dict[str, str],
                         output_dir: Path,
                         context: str = "migrated") -> Dict[str, Any]:
        """Migrate selectors from a dictionary to YAML configuration files."""
        migration_result = {
            "success": True,
            "migrated_selectors": [],
            "errors": [],
            "warnings": [],
            "output_files": []
        }
        
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Group selectors by context (simple heuristic)
            context_groups = self._group_selectors_by_context(selectors_dict)
            
            for context_name, selectors in context_groups.items():
                # Create configuration for this context
                config = self._create_configuration_from_selectors(
                    selectors, 
                    f"{context}.{context_name}"
                )
                
                # Validate configuration
                validation_result = self.validator.validate_configuration(config)
                if not validation_result.is_valid:
                    migration_result["errors"].extend([
                        f"Validation error for {context_name}: {error}"
                        for error in validation_result.errors
                    ])
                    continue
                
                # Write to file
                filename = f"{context_name}_selectors.yaml"
                output_file = output_dir / filename
                
                yaml_content = self._convert_to_yaml(config)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                
                migration_result["output_files"].append(str(output_file))
                migration_result["migrated_selectors"].extend(selectors.keys())
                
                if validation_result.warnings:
                    migration_result["warnings"].extend([
                        f"Warning for {context_name}: {warning}"
                        for warning in validation_result.warnings
                    ])
            
            return migration_result
            
        except Exception as e:
            migration_result["success"] = False
            migration_result["errors"].append(f"Migration failed: {str(e)}")
            return migration_result
    
    def migrate_from_python_file(self, 
                                python_file: Path,
                                output_dir: Path) -> Dict[str, Any]:
        """Migrate selectors from a Python file to YAML configuration."""
        migration_result = {
            "success": True,
            "migrated_selectors": [],
            "errors": [],
            "warnings": [],
            "output_files": []
        }
        
        try:
            # Read Python file
            with open(python_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract selector definitions
            selectors_dict = self._extract_selectors_from_python(content)
            
            if not selectors_dict:
                migration_result["warnings"].append("No selector definitions found in Python file")
                return migration_result
            
            # Migrate the extracted selectors
            return self.migrate_from_dict(selectors_dict, output_dir, "python_migrated")
            
        except Exception as e:
            migration_result["success"] = False
            migration_result["errors"].append(f"Python file migration failed: {str(e)}")
            return migration_result
    
    def analyze_selectors(self, selectors_dict: Dict[str, str]) -> Dict[str, Any]:
        """Analyze selector definitions and provide migration recommendations."""
        analysis = {
            "total_selectors": len(selectors_dict),
            "complexity_analysis": {},
            "recommendations": [],
            "strategy_suggestions": {}
        }
        
        for name, selector in selectors_dict.items():
            complexity = self._analyze_selector_complexity(selector)
            analysis["complexity_analysis"][name] = complexity
            
            # Generate strategy suggestions
            strategies = self._suggest_strategies(selector)
            analysis["strategy_suggestions"][name] = strategies
        
        # Generate overall recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis["complexity_analysis"])
        
        return analysis
    
    def _group_selectors_by_context(self, selectors_dict: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Group selectors by context using simple heuristics."""
        groups = {}
        
        for name, selector in selectors_dict.items():
            context = self._infer_context(name, selector)
            if context not in groups:
                groups[context] = {}
            groups[context][name] = selector
        
        return groups
    
    def _infer_context(self, name: str, selector: str) -> str:
        """Infer context from selector name and content."""
        name_lower = name.lower()
        selector_lower = selector.lower()
        
        # Navigation-related
        if any(keyword in name_lower for keyword in ['nav', 'menu', 'link', 'button']):
            return 'navigation'
        
        # Content-related
        if any(keyword in name_lower for keyword in ['title', 'header', 'content', 'main']):
            return 'content'
        
        # Form-related
        if any(keyword in name_lower for keyword in ['input', 'form', 'field', 'submit']):
            return 'form'
        
        # List/table-related
        if any(keyword in name_lower for keyword in ['list', 'table', 'row', 'item']):
            return 'list'
        
        # Footer-related
        if any(keyword in name_lower for keyword in ['footer', 'bottom', 'copyright']):
            return 'footer'
        
        # Default
        return 'general'
    
    def _create_configuration_from_selectors(self, 
                                            selectors: Dict[str, str],
                                            context: str) -> SelectorConfiguration:
        """Create a SelectorConfiguration from a dictionary of selectors."""
        # Create metadata
        metadata = ConfigurationMetadata(
            version="1.0.0",
            last_updated=datetime.now().isoformat(),
            description=f"Migrated selectors for {context}"
        )
        
        # Create context defaults
        context_defaults = ContextDefaults(
            page_type="migrated",
            wait_strategy="network_idle",
            timeout=10000
        )
        
        # Create validation defaults
        validation_defaults = ValidationDefaults(
            required=True,
            type="string"
        )
        
        # Create strategy templates
        strategy_templates = self._create_common_templates()
        
        # Create semantic selectors
        semantic_selectors = {}
        for name, selector in selectors.items():
            semantic_selectors[name] = self._create_semantic_selector(name, selector, context)
        
        return SelectorConfiguration(
            file_path=f"migrated/{context}.yaml",
            metadata=metadata,
            context_defaults=context_defaults,
            validation_defaults=validation_defaults,
            strategy_templates=strategy_templates,
            selectors=semantic_selectors
        )
    
    def _create_common_templates(self) -> Dict[str, StrategyTemplate]:
        """Create common strategy templates."""
        return {
            "css_selector": StrategyTemplate(
                type="css_selector",
                parameters={"selector": ""},
                confidence=ConfidenceConfig(threshold=0.7)
            ),
            "text_anchor": StrategyTemplate(
                type="text_anchor", 
                parameters={"pattern": ""},
                confidence=ConfidenceConfig(threshold=0.8)
            ),
            "attribute_match": StrategyTemplate(
                type="attribute_match",
                parameters={"attribute": "", "value": ""},
                confidence=ConfidenceConfig(threshold=0.9)
            )
        }
    
    def _create_semantic_selector(self, name: str, selector: str, context: str) -> SemanticSelector:
        """Create a SemanticSelector from a selector string."""
        # Analyze selector and create strategies
        strategies = self._create_strategies_from_selector(selector)
        
        # Create validation rule
        validation = ValidationRule(
            required=True,
            type="string"
        )
        
        # Create confidence config
        confidence = ConfidenceConfig(
            threshold=0.7,
            weight=1.0
        )
        
        return SemanticSelector(
            name=name,
            description=f"Migrated selector: {name}",
            context=context,
            strategies=strategies,
            validation=validation,
            confidence=confidence
        )
    
    def _create_strategies_from_selector(self, selector: str) -> List[StrategyDefinition]:
        """Create strategy definitions from a selector string."""
        strategies = []
        
        # CSS selector strategy
        if self._is_css_selector(selector):
            strategies.append(StrategyDefinition(
                type="css_selector",
                template="css_selector",
                parameters={"selector": selector},
                priority=1
            ))
        
        # Text anchor strategy (if selector contains text)
        if self._has_text_content(selector):
            strategies.append(StrategyDefinition(
                type="text_anchor",
                template="text_anchor",
                parameters={"pattern": selector},
                priority=2
            ))
        
        # Attribute match strategy (if selector looks like attribute)
        if self._is_attribute_selector(selector):
            attr, value = self._parse_attribute_selector(selector)
            strategies.append(StrategyDefinition(
                type="attribute_match",
                template="attribute_match",
                parameters={"attribute": attr, "value": value},
                priority=3
            ))
        
        return strategies
    
    def _is_css_selector(self, selector: str) -> bool:
        """Check if selector is a CSS selector."""
        return any(char in selector for char in ['.', '#', '[', '>', '+', '~', ':'])
    
    def _has_text_content(self, selector: str) -> bool:
        """Check if selector contains text content."""
        return selector.startswith('"') or selector.startswith("'")
    
    def _is_attribute_selector(self, selector: str) -> bool:
        """Check if selector is an attribute selector."""
        return '=' in selector and not any(char in selector for char in ['.', '#', '>', '+'])
    
    def _parse_attribute_selector(self, selector: str) -> Tuple[str, str]:
        """Parse attribute selector into attribute and value."""
        if '=' in selector:
            parts = selector.split('=', 1)
            return parts[0].strip(), parts[1].strip().strip('"\'')
        return selector, ""
    
    def _analyze_selector_complexity(self, selector: str) -> Dict[str, Any]:
        """Analyze the complexity of a selector."""
        complexity = {
            "length": len(selector),
            "type": "simple",
            "specificity": 1,
            "recommendations": []
        }
        
        # Determine type
        if self._is_css_selector(selector):
            complexity["type"] = "css"
            complexity["specificity"] = self._calculate_css_specificity(selector)
        elif self._is_attribute_selector(selector):
            complexity["type"] = "attribute"
        elif self._has_text_content(selector):
            complexity["type"] = "text"
        
        # Generate recommendations
        if complexity["specificity"] > 10:
            complexity["recommendations"].append("Consider simplifying selector")
        
        if len(selector) > 100:
            complexity["recommendations"].append("Very long selector - consider breaking down")
        
        return complexity
    
    def _calculate_css_specificity(self, selector: str) -> int:
        """Calculate CSS specificity score."""
        specificity = 0
        
        # IDs
        specificity += selector.count('#') * 100
        
        # Classes and attributes
        specificity += selector.count('.') * 10
        specificity += selector.count('[') * 10
        
        # Elements
        elements = re.findall(r'[a-zA-Z][a-zA-Z0-9]*(?=[^a-zA-Z0-9]|$)', selector)
        specificity += len(elements)
        
        return specificity
    
    def _suggest_strategies(self, selector: str) -> List[str]:
        """Suggest appropriate strategies for a selector."""
        suggestions = []
        
        if self._is_css_selector(selector):
            suggestions.append("css_selector")
        
        if self._is_attribute_selector(selector):
            suggestions.append("attribute_match")
        
        if self._has_text_content(selector):
            suggestions.append("text_anchor")
        
        # Always suggest multiple strategies for robustness
        if len(suggestions) == 1:
            suggestions.append("text_anchor")  # Fallback
        
        return suggestions
    
    def _generate_recommendations(self, complexity_analysis: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate migration recommendations based on complexity analysis."""
        recommendations = []
        
        high_complexity = [name for name, analysis in complexity_analysis.items() 
                          if analysis["specificity"] > 20]
        
        if high_complexity:
            recommendations.append(f"Consider simplifying {len(high_complexity)} high-complexity selectors")
        
        long_selectors = [name for name, analysis in complexity_analysis.items() 
                         if analysis["length"] > 80]
        
        if long_selectors:
            recommendations.append(f"Consider breaking down {len(long_selectors)} long selectors")
        
        # General recommendations
        recommendations.append("Add multiple strategies for robustness")
        recommendations.append("Set appropriate confidence thresholds")
        recommendations.append("Provide clear descriptions for migrated selectors")
        
        return recommendations
    
    def _extract_selectors_from_python(self, content: str) -> Dict[str, str]:
        """Extract selector definitions from Python code."""
        selectors = {}
        
        # Look for common patterns
        patterns = [
            r'(\w+)\s*=\s*["\']([^"\']+)["\']',  # variable = "selector"
            r'SELECTORS\s*=\s*{([^}]+)}',      # SELECTORS = {...}
            r'"([^"]+)"\s*:\s*"([^"]+)"',        # "name": "selector"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) == 2:
                    name, selector = match
                    if name and selector and name.isupper():
                        selectors[name] = selector
        
        return selectors
    
    def _convert_to_yaml(self, config: SelectorConfiguration) -> str:
        """Convert configuration to YAML string."""
        yaml_lines = []
        
        # Metadata
        yaml_lines.append("metadata:")
        yaml_lines.append(f"  version: \"{config.metadata.version}\"")
        yaml_lines.append(f"  last_updated: \"{config.metadata.last_updated}\"")
        yaml_lines.append(f"  description: \"{config.metadata.description}\"")
        yaml_lines.append("")
        
        # Context defaults
        if config.context_defaults:
            yaml_lines.append("context_defaults:")
            yaml_lines.append(f"  page_type: \"{config.context_defaults.page_type}\"")
            yaml_lines.append(f"  wait_strategy: \"{config.context_defaults.wait_strategy}\"")
            yaml_lines.append(f"  timeout: {config.context_defaults.timeout}")
            if config.context_defaults.section:
                yaml_lines.append(f"  section: \"{config.context_defaults.section}\"")
            yaml_lines.append("")
        
        # Validation defaults
        if config.validation_defaults:
            yaml_lines.append("validation_defaults:")
            yaml_lines.append(f"  required: {config.validation_defaults.required}")
            yaml_lines.append(f"  type: \"{config.validation_defaults.type}\"")
            if config.validation_defaults.min_length is not None:
                yaml_lines.append(f"  min_length: {config.validation_defaults.min_length}")
            if config.validation_defaults.max_length is not None:
                yaml_lines.append(f"  max_length: {config.validation_defaults.max_length}")
            yaml_lines.append("")
        
        # Strategy templates
        if config.strategy_templates:
            yaml_lines.append("strategy_templates:")
            for name, template in config.strategy_templates.items():
                yaml_lines.append(f"  {name}:")
                yaml_lines.append(f"    type: \"{template.type}\"")
                if template.parameters:
                    yaml_lines.append("    parameters:")
                    for key, value in template.parameters.items():
                        if isinstance(value, str):
                            yaml_lines.append(f"      {key}: \"{value}\"")
                        else:
                            yaml_lines.append(f"      {key}: {value}")
                yaml_lines.append("")
        
        # Selectors
        yaml_lines.append("selectors:")
        for name, selector in config.selectors.items():
            yaml_lines.append(f"  {name}:")
            yaml_lines.append(f"    description: \"{selector.description}\"")
            yaml_lines.append(f"    context: \"{selector.context}\"")
            yaml_lines.append("    strategies:")
            for strategy in selector.strategies:
                yaml_lines.append(f"      - type: \"{strategy.type}\"")
                if strategy.template:
                    yaml_lines.append(f"        template: \"{strategy.template}\"")
                if strategy.parameters:
                    yaml_lines.append("        parameters:")
                    for key, value in strategy.parameters.items():
                        if isinstance(value, str):
                            yaml_lines.append(f"          {key}: \"{value}\"")
                        else:
                            yaml_lines.append(f"          {key}: {value}")
                yaml_lines.append(f"        priority: {strategy.priority}")
            if selector.validation:
                yaml_lines.append("    validation:")
                if selector.validation.required is not None:
                    yaml_lines.append(f"      required: {selector.validation.required}")
                if selector.validation.type:
                    yaml_lines.append(f"      type: \"{selector.validation.type}\"")
            if selector.confidence:
                yaml_lines.append("    confidence:")
                if selector.confidence.threshold is not None:
                    yaml_lines.append(f"      threshold: {selector.confidence.threshold}")
                if selector.confidence.weight is not None:
                    yaml_lines.append(f"      weight: {selector.confidence.weight}")
            yaml_lines.append("")
        
        return '\n'.join(yaml_lines)


def create_migration_report(migration_result: Dict[str, Any]) -> str:
    """Create a migration report."""
    report = []
    report.append("# Configuration Migration Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("")
    
    if migration_result["success"]:
        report.append("## Migration Successful ✅")
        report.append(f"Migrated {len(migration_result['migrated_selectors'])} selectors")
        report.append(f"Generated {len(migration_result['output_files'])} configuration files")
        report.append("")
        
        report.append("### Output Files:")
        for file_path in migration_result["output_files"]:
            report.append(f"- {file_path}")
        report.append("")
        
        if migration_result["warnings"]:
            report.append("### Warnings:")
            for warning in migration_result["warnings"]:
                report.append(f"- {warning}")
            report.append("")
    else:
        report.append("## Migration Failed ❌")
        report.append("### Errors:")
        for error in migration_result["errors"]:
            report.append(f"- {error}")
        report.append("")
    
    return '\n'.join(report)
