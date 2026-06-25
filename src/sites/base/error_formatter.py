"""
Structured error message formatting for validation results.

Provides consistent, actionable error messages for different types of validation failures.
"""

from typing import List, Dict, Any
from datetime import datetime


class ErrorFormatter:
    """Formats validation errors into structured, actionable messages."""
    
    @staticmethod
    def format_validation_result(site_id: str, result) -> Dict[str, Any]:
        """Format a validation result into a structured error report."""
        return {
            "site_id": site_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "valid" if result.is_valid() else "invalid",
            "summary": {
                "total_errors": len(result.errors),
                "total_warnings": len(result.warnings),
                "missing_files": len(result.missing_files),
                "invalid_selectors": len(result.invalid_selectors)
            },
            "errors": ErrorFormatter.format_errors(result.errors),
            "warnings": ErrorFormatter.format_warnings(result.warnings),
            "missing_files": result.missing_files,
            "invalid_selectors": result.invalid_selectors,
            "actions": ErrorFormatter.generate_actions(result)
        }
    
    @staticmethod
    def format_errors(errors: List[str]) -> List[Dict[str, Any]]:
        """Format error messages with categorization and guidance."""
        formatted_errors = []
        
        for error in errors:
            formatted_error = {
                "message": error,
                "category": ErrorFormatter.categorize_error(error),
                "severity": "error",
                "guidance": ErrorFormatter.get_error_guidance(error)
            }
            formatted_errors.append(formatted_error)
        
        return formatted_errors
    
    @staticmethod
    def format_warnings(warnings: List[str]) -> List[Dict[str, Any]]:
        """Format warning messages with categorization."""
        formatted_warnings = []
        
        for warning in warnings:
            formatted_warning = {
                "message": warning,
                "category": ErrorFormatter.categorize_error(warning),
                "severity": "warning",
                "guidance": ErrorFormatter.get_warning_guidance(warning)
            }
            formatted_warnings.append(formatted_warning)
        
        return formatted_warnings
    
    @staticmethod
    def categorize_error(message: str) -> str:
        """Categorize error message by type."""
        message_lower = message.lower()
        
        if "missing required file" in message_lower:
            return "file_system"
        elif "missing required directory" in message_lower:
            return "file_system"
        elif "missing required class attribute" in message_lower:
            return "interface"
        elif "missing required method" in message_lower:
            return "interface"
        elif "invalid yaml syntax" in message_lower:
            return "yaml_syntax"
        elif "schema validation failed" in message_lower:
            return "yaml_schema"
        elif "configuration field" in message_lower:
            return "configuration"
        elif "site id" in message_lower and "already registered" in message_lower:
            return "registry"
        elif "must inherit from" in message_lower:
            return "inheritance"
        else:
            return "general"
    
    @staticmethod
    def get_error_guidance(message: str) -> str:
        """Get specific guidance for error messages."""
        message_lower = message.lower()
        
        if "missing required file" in message_lower:
            return "Create the missing file in the scraper directory"
        elif "missing required directory" in message_lower:
            return "Create the selectors/ directory in the scraper folder"
        elif "missing required class attribute" in message_lower:
            return "Add the required class attribute to your scraper class"
        elif "missing required method" in message_lower:
            return "Implement the required abstract method in your scraper class"
        elif "invalid yaml syntax" in message_lower:
            return "Fix the YAML syntax error in the selector file"
        elif "schema validation failed" in message_lower:
            return "Update the YAML file to match the required schema"
        elif "configuration field" in message_lower:
            return "Add the missing field to SITE_CONFIG in config.py"
        elif "site id" in message_lower and "already registered" in message_lower:
            return "Choose a different site ID or unregister the existing scraper"
        elif "must inherit from" in message_lower:
            return "Make your scraper class inherit from BaseSiteScraper"
        else:
            return "Review the error message and fix the underlying issue"
    
    @staticmethod
    def get_warning_guidance(message: str) -> str:
        """Get specific guidance for warning messages."""
        message_lower = message.lower()
        
        if "no selector files found" in message_lower:
            return "Add YAML selector files to the selectors/ directory"
        elif "should take no parameters" in message_lower:
            return "Remove unnecessary parameters from the method signature"
        elif "should only take" in message_lower:
            return "Simplify the method signature to use **kwargs"
        elif "could not validate" in message_lower:
            return "Ensure the method signature follows the expected pattern"
        else:
            return "Consider addressing the warning for better compliance"
    
    @staticmethod
    def generate_actions(result) -> List[Dict[str, Any]]:
        """Generate actionable steps to fix validation issues."""
        actions = []
        
        # File-related actions
        if result.missing_files:
            actions.append({
                "type": "create_files",
                "priority": "high",
                "description": "Create missing files",
                "files": result.missing_files,
                "steps": [
                    "Create each missing file in the scraper directory",
                    "Copy from template if needed",
                    "Ensure proper file structure"
                ]
            })
        
        # Selector-related actions
        if result.invalid_selectors:
            actions.append({
                "type": "fix_selectors",
                "priority": "high",
                "description": "Fix invalid selector files",
                "files": result.invalid_selectors,
                "steps": [
                    "Review YAML syntax in each selector file",
                    "Ensure required fields are present",
                    "Validate strategy definitions"
                ]
            })
        
        # Interface-related actions
        interface_errors = [e for e in result.errors if "class attribute" in e or "method" in e]
        if interface_errors:
            actions.append({
                "type": "implement_interface",
                "priority": "high",
                "description": "Implement required interface elements",
                "errors": interface_errors,
                "steps": [
                    "Add missing class attributes (site_id, site_name, base_url)",
                    "Implement required methods (navigate, scrape, normalize)",
                    "Ensure proper method signatures"
                ]
            })
        
        # Configuration-related actions
        config_errors = [e for e in result.errors if "configuration field" in e]
        if config_errors:
            actions.append({
                "type": "fix_configuration",
                "priority": "medium",
                "description": "Fix configuration issues",
                "errors": config_errors,
                "steps": [
                    "Update SITE_CONFIG in config.py",
                    "Add missing required fields",
                    "Validate field formats and values"
                ]
            })
        
        return actions


class ValidationReport:
    """Generates comprehensive validation reports."""
    
    @staticmethod
    def generate_summary_report(results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary report for multiple validation results."""
        total_sites = len(results)
        valid_sites = sum(1 for result in results.values() if result.get("status") == "valid")
        invalid_sites = total_sites - valid_sites
        
        total_errors = sum(result.get("summary", {}).get("total_errors", 0) for result in results.values())
        total_warnings = sum(result.get("summary", {}).get("total_warnings", 0) for result in results.values())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_sites": total_sites,
                "valid_sites": valid_sites,
                "invalid_sites": invalid_sites,
                "success_rate": (valid_sites / total_sites * 100) if total_sites > 0 else 0,
                "total_errors": total_errors,
                "total_warnings": total_warnings
            },
            "status": "passed" if invalid_sites == 0 else "failed",
            "sites": list(results.keys()),
            "failed_sites": [site_id for site_id, result in results.items() if result.get("status") == "invalid"]
        }
    
    @staticmethod
    def generate_detailed_report(results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed validation report with all issues."""
        summary = ValidationReport.generate_summary_report(results)
        
        detailed_issues = {}
        for site_id, result in results.items():
            if result.get("status") == "invalid":
                detailed_issues[site_id] = {
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "actions": result.get("actions", []),
                    "missing_files": result.get("missing_files", []),
                    "invalid_selectors": result.get("invalid_selectors", [])
                }
        
        return {
            **summary,
            "detailed_issues": detailed_issues,
            "recommendations": ValidationReport._generate_recommendations(results)
        }
    
    @staticmethod
    def _generate_recommendations(results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Common issues across sites
        all_missing_files = []
        all_invalid_selectors = []
        
        for result in results.values():
            all_missing_files.extend(result.get("missing_files", []))
            all_invalid_selectors.extend(result.get("invalid_selectors", []))
        
        # File-related recommendations
        if all_missing_files:
            file_counts = {}
            for file_path in all_missing_files:
                file_name = file_path.split("/")[-1]
                file_counts[file_name] = file_counts.get(file_name, 0) + 1
            
            most_common = max(file_counts, key=file_counts.get)
            recommendations.append(f"Most common missing file: {most_common} ({file_counts[most_common]} sites)")
        
        # Selector-related recommendations
        if all_invalid_selectors:
            recommendations.append(f"Fix {len(all_invalid_selectors)} invalid selector files across all sites")
        
        # General recommendations
        invalid_sites = [site_id for site_id, result in results.items() if result.get("status") == "invalid"]
        if invalid_sites:
            recommendations.append(f"Focus on fixing {len(invalid_sites)} sites with validation failures")
        
        return recommendations
