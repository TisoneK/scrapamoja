"""
Migration tool for existing sites using old template.

This tool helps migrate existing sites from the old template structure
to the new advanced template architecture.
"""

import os
import shutil
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TemplateMigrationTool:
    """Tool for migrating existing sites to new template architecture."""
    
    def __init__(self, site_path: str, config: Dict[str, Any] = None):
        """
        Initialize migration tool.
        
        Args:
            site_path: Path to the existing site directory
            config: Migration configuration options
        """
        self.site_path = Path(site_path)
        self.config = config or {}
        self.backup_path = self.site_path.parent / f"{self.site_path.name}_backup"
        self.migration_log = []
        
        # Migration options
        self.create_backup = self.config.get('create_backup', True)
        self.preserve_original = self.config.get('preserve_original', True)
        self.target_complexity = self.config.get('target_complexity', 'auto')
        self.migrate_flows = self.config.get('migrate_flows', True)
        self.update_imports = self.config.get('update_imports', True)
    
    def analyze_current_structure(self) -> Dict[str, Any]:
        """Analyze the current site structure."""
        analysis = {
            'site_name': self.site_path.name,
            'current_pattern': 'unknown',
            'has_flow_py': False,
            'has_flows_dir': False,
            'has_domain_subdirs': False,
            'flow_files': [],
            'import_statements': [],
            'complexity_indicators': {
                'flow_count': 0,
                'domain_count': 0,
                'has_navigation': False,
                'has_extraction': False,
                'has_filtering': False,
                'has_authentication': False
            },
            'migration_complexity': 'simple'
        }
        
        # Check for flow.py
        flow_py_path = self.site_path / 'flow.py'
        if flow_py_path.exists():
            analysis['has_flow_py'] = True
            analysis['flow_files'].append('flow.py')
        
        # Check for flows/ directory
        flows_dir = self.site_path / 'flows'
        if flows_dir.exists():
            analysis['has_flows_dir'] = True
            
            # List flow files
            for flow_file in flows_dir.glob('*.py'):
                if flow_file.name != '__init__.py':
                    analysis['flow_files'].append(f"flows/{flow_file.name}")
            
            # Check for domain subdirectories
            domain_dirs = [d for d in flows_dir.iterdir() 
                          if d.is_dir() and d.name != '__pycache__']
            if domain_dirs:
                analysis['has_domain_subdirs'] = True
                analysis['complexity_indicators']['domain_count'] = len(domain_dirs)
        
        # Analyze flow files for complexity
        for flow_file in analysis['flow_files']:
            flow_path = self.site_path / flow_file
            if flow_path.exists():
                with open(flow_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Count flows (classes ending with 'Flow')
                    flow_matches = re.findall(r'class\s+(\w*Flow)\s*\(', content)
                    analysis['complexity_indicators']['flow_count'] += len(flow_matches)
                    
                    # Check for domain indicators
                    if any(keyword in content.lower() for keyword in ['navigate', 'click', 'goto']):
                        analysis['complexity_indicators']['has_navigation'] = True
                    if any(keyword in content.lower() for keyword in ['extract', 'scrape', 'data']):
                        analysis['complexity_indicators']['has_extraction'] = True
                    if any(keyword in content.lower() for keyword in ['filter', 'validate', 'clean']):
                        analysis['complexity_indicators']['has_filtering'] = True
                    if any(keyword in content.lower() for keyword in ['login', 'auth', 'session']):
                        analysis['complexity_indicators']['has_authentication'] = True
                    
                    # Extract import statements
                    import_matches = re.findall(r'^(?:from|import)\s+.*$', content, re.MULTILINE)
                    analysis['import_statements'].extend(import_matches)
        
        # Determine current pattern
        if analysis['has_flow_py'] and not analysis['has_flows_dir']:
            analysis['current_pattern'] = 'simple'
        elif analysis['has_flows_dir'] and not analysis['has_domain_subdirs']:
            analysis['current_pattern'] = 'standard'
        elif analysis['has_domain_subdirs']:
            analysis['current_pattern'] = 'complex'
        
        # Determine migration complexity
        flow_count = analysis['complexity_indicators']['flow_count']
        domain_count = analysis['complexity_indicators']['domain_count']
        
        if flow_count <= 2 and domain_count == 0:
            analysis['migration_complexity'] = 'simple'
        elif flow_count <= 5 and domain_count <= 2:
            analysis['migration_complexity'] = 'standard'
        else:
            analysis['migration_complexity'] = 'complex'
        
        return analysis
    
    def recommend_target_pattern(self, analysis: Dict[str, Any]) -> str:
        """Recommend target pattern based on analysis."""
        if self.target_complexity != 'auto':
            return self.target_complexity
        
        flow_count = analysis['complexity_indicators']['flow_count']
        domain_count = analysis['complexity_indicators']['domain_count']
        has_multiple_domains = sum([
            analysis['complexity_indicators']['has_navigation'],
            analysis['complexity_indicators']['has_extraction'],
            analysis['complexity_indicators']['has_filtering'],
            analysis['complexity_indicators']['has_authentication']
        ]) > 1
        
        if flow_count <= 2 and not has_multiple_domains:
            return 'simple'
        elif flow_count <= 5 and domain_count <= 2:
            return 'standard'
        else:
            return 'complex'
    
    def create_backup_directory(self) -> bool:
        """Create backup of current site."""
        if not self.create_backup:
            return True
        
        try:
            if self.backup_path.exists():
                shutil.rmtree(self.backup_path)
            
            shutil.copytree(self.site_path, self.backup_path)
            self.log_action(f"Created backup at: {self.backup_path}")
            return True
            
        except Exception as e:
            self.log_action(f"Failed to create backup: {str(e)}", level='error')
            return False
    
    def migrate_to_simple_pattern(self) -> bool:
        """Migrate to simple pattern (single flow.py)."""
        try:
            # Create new flow.py if it doesn't exist
            flow_py_path = self.site_path / 'flow.py'
            
            if not flow_py_path.exists():
                # Look for existing flows to consolidate
                flows_dir = self.site_path / 'flows'
                if flows_dir.exists():
                    # Consolidate flows into single file
                    consolidated_content = self._consolidate_flows(flows_dir)
                    with open(flow_py_path, 'w', encoding='utf-8') as f:
                        f.write(consolidated_content)
                    
                    self.log_action("Consolidated flows into single flow.py")
            
            # Remove flows directory if it exists
            flows_dir = self.site_path / 'flows'
            if flows_dir.exists() and not self.preserve_original:
                shutil.rmtree(flows_dir)
                self.log_action("Removed flows directory")
            
            return True
            
        except Exception as e:
            self.log_action(f"Simple pattern migration failed: {str(e)}", level='error')
            return False
    
    def migrate_to_standard_pattern(self) -> bool:
        """Migrate to standard pattern (flow.py + flows/)."""
        try:
            # Ensure flows directory exists
            flows_dir = self.site_path / 'flows'
            flows_dir.mkdir(exist_ok=True)
            
            # Create __init__.py
            init_py_path = flows_dir / '__init__.py'
            if not init_py_path.exists():
                with open(init_py_path, 'w', encoding='utf-8') as f:
                    f.write('"""Flows module."""\n')
                self.log_action("Created flows/__init__.py")
            
            # Split flow.py if it has multiple classes
            flow_py_path = self.site_path / 'flow.py'
            if flow_py_path.exists():
                self._split_flow_file(flow_py_path, flows_dir)
            
            return True
            
        except Exception as e:
            self.log_action(f"Standard pattern migration failed: {str(e)}", level='error')
            return False
    
    def migrate_to_complex_pattern(self) -> bool:
        """Migrate to complex pattern (flows/ with domain subfolders)."""
        try:
            # First migrate to standard pattern
            if not self.migrate_to_standard_pattern():
                return False
            
            flows_dir = self.site_path / 'flows'
            
            # Create domain subdirectories
            domains = ['navigation', 'extraction', 'filtering', 'authentication']
            for domain in domains:
                domain_dir = flows_dir / domain
                domain_dir.mkdir(exist_ok=True)
                
                # Create __init__.py
                init_py_path = domain_dir / '__init__.py'
                if not init_py_path.exists():
                    with open(init_py_path, 'w', encoding='utf-8') as f:
                        f.write(f'"""{domain.title()} flows module."""\n')
            
            # Organize flows by domain
            self._organize_flows_by_domain(flows_dir)
            
            return True
            
        except Exception as e:
            self.log_action(f"Complex pattern migration failed: {str(e)}", level='error')
            return False
    
    def update_import_statements(self) -> bool:
        """Update import statements to use new base classes."""
        if not self.update_imports:
            return True
        
        try:
            # Update flow files to use new base classes
            for flow_file in self.site_path.rglob('*.py'):
                if flow_file.name in ['__init__.py', 'base_flows.py', 'flow_templates.py', 'migration_tool.py']:
                    continue
                
                with open(flow_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add imports for base classes if needed
                if 'BaseNavigationFlow' in content or 'BaseExtractionFlow' in content:
                    if 'from .base_flows import' not in content:
                        content = 'from .base_flows import *\n\n' + content
                
                # Update class inheritance
                content = self._update_class_inheritance(content)
                
                with open(flow_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.log_action("Updated import statements")
            return True
            
        except Exception as e:
            self.log_action(f"Import update failed: {str(e)}", level='error')
            return False
    
    def execute_migration(self) -> Dict[str, Any]:
        """Execute the complete migration process."""
        migration_result = {
            'success': False,
            'analysis': None,
            'target_pattern': None,
            'actions_performed': [],
            'errors': [],
            'backup_path': str(self.backup_path) if self.create_backup else None
        }
        
        try:
            # Step 1: Analyze current structure
            self.log_action("Analyzing current structure...")
            analysis = self.analyze_current_structure()
            migration_result['analysis'] = analysis
            
            # Step 2: Determine target pattern
            target_pattern = self.recommend_target_pattern(analysis)
            migration_result['target_pattern'] = target_pattern
            self.log_action(f"Recommended target pattern: {target_pattern}")
            
            # Step 3: Create backup
            if self.create_backup:
                if not self.create_backup_directory():
                    migration_result['errors'].append("Failed to create backup")
                    return migration_result
            
            # Step 4: Execute migration based on target pattern
            if target_pattern == 'simple':
                success = self.migrate_to_simple_pattern()
            elif target_pattern == 'standard':
                success = self.migrate_to_standard_pattern()
            elif target_pattern == 'complex':
                success = self.migrate_to_complex_pattern()
            else:
                success = False
                migration_result['errors'].append(f"Unknown target pattern: {target_pattern}")
            
            if not success:
                migration_result['errors'].append("Pattern migration failed")
                return migration_result
            
            migration_result['actions_performed'].append(f"Migrated to {target_pattern} pattern")
            
            # Step 5: Update imports
            if self.update_imports:
                if self.update_import_statements():
                    migration_result['actions_performed'].append("Updated import statements")
                else:
                    migration_result['errors'].append("Import update failed")
            
            # Step 6: Create migration report
            report_path = self.site_path / 'migration_report.json'
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(migration_result, f, indent=2)
            
            migration_result['actions_performed'].append("Created migration report")
            migration_result['success'] = True
            
            self.log_action("Migration completed successfully")
            
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            self.log_action(error_msg, level='error')
            migration_result['errors'].append(error_msg)
        
        migration_result['log'] = self.migration_log
        return migration_result
    
    def _consolidate_flows(self, flows_dir: Path) -> str:
        """Consolidate multiple flow files into single content."""
        content = '"""Consolidated flow module."""\n\n'
        
        for flow_file in flows_dir.glob('*.py'):
            if flow_file.name == '__init__.py':
                continue
            
            with open(flow_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Remove imports and docstring to avoid duplication
            lines = file_content.split('\n')
            filtered_lines = []
            skip_imports = True
            
            for line in lines:
                if line.strip().startswith(('import', 'from', '"""', "'''")):
                    if skip_imports and (line.strip().startswith(('import', 'from')) or 
                                       line.strip().startswith(('"""', "'''"))):
                        continue
                    else:
                        skip_imports = False
                
                if not skip_imports:
                    filtered_lines.append(line)
            
            content += '\n'.join(filtered_lines) + '\n\n'
        
        return content
    
    def _split_flow_file(self, flow_py_path: Path, flows_dir: Path) -> None:
        """Split single flow file into multiple files."""
        with open(flow_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find class definitions
        class_matches = re.finditer(r'class\s+(\w+Flow)\s*\([^)]*\):', content)
        
        for match in class_matches:
            class_name = match.group(1)
            start_pos = match.start()
            
            # Find the end of the class
            class_content = self._extract_class_content(content, start_pos)
            
            # Write to separate file
            flow_file_path = flows_dir / f"{class_name.lower()}.py"
            with open(flow_file_path, 'w', encoding='utf-8') as f:
                f.write(f'"""{class_name} implementation."""\n\n')
                f.write('from ..base_flows import *\n\n')
                f.write(class_content)
        
        # Remove original flow.py if not preserving
        if not self.preserve_original:
            flow_py_path.unlink()
            self.log_action("Removed original flow.py")
    
    def _extract_class_content(self, content: str, start_pos: int) -> str:
        """Extract class content from full file content."""
        lines = content[start_pos:].split('\n')
        class_lines = []
        indent_level = 0
        
        for line in lines:
            class_lines.append(line)
            
            # Track indentation to find class end
            if line.strip():
                current_indent = len(line) - len(line.lstrip())
                if current_indent == 0 and line.strip().startswith('class '):
                    break
                elif current_indent == 0 and class_lines[-2].strip():
                    break
        
        return '\n'.join(class_lines[:-1])  # Remove the last line (next class)
    
    def _organize_flows_by_domain(self, flows_dir: Path) -> None:
        """Organize flows into domain-specific subdirectories."""
        domain_keywords = {
            'navigation': ['navigate', 'click', 'goto', 'page', 'browser'],
            'extraction': ['extract', 'scrape', 'data', 'content'],
            'filtering': ['filter', 'validate', 'clean', 'process'],
            'authentication': ['login', 'auth', 'session', 'credential']
        }
        
        for flow_file in flows_dir.glob('*.py'):
            if flow_file.name == '__init__.py':
                continue
            
            with open(flow_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Determine domain based on content
            target_domain = 'navigation'  # default
            for domain, keywords in domain_keywords.items():
                if any(keyword in content for keyword in keywords):
                    target_domain = domain
                    break
            
            # Move file to domain directory
            domain_dir = flows_dir / target_domain
            target_path = domain_dir / flow_file.name
            
            if not target_path.exists():
                shutil.move(str(flow_file), str(target_path))
                self.log_action(f"Moved {flow_file.name} to {target_domain}/")
    
    def _update_class_inheritance(self, content: str) -> str:
        """Update class inheritance to use new base classes."""
        # Update NavigationFlow classes
        content = re.sub(
            r'class\s+(\w*Navigate\w*Flow)\s*\([^)]*\):',
            r'class \1(BaseNavigationFlow):',
            content
        )
        
        # Update ExtractionFlow classes
        content = re.sub(
            r'class\s+(\w*Extract\w*Flow)\s*\([^)]*\):',
            r'class \1(BaseExtractionFlow):',
            content
        )
        
        # Update FilteringFlow classes
        content = re.sub(
            r'class\s+(\w*Filter\w*Flow)\s*\([^)]*\):',
            r'class \1(BaseFilteringFlow):',
            content
        )
        
        # Update AuthenticationFlow classes
        content = re.sub(
            r'class\s+(\w*Auth\w*Flow)\s*\([^)]*\):',
            r'class \1(BaseAuthenticationFlow):',
            content
        )
        
        return content
    
    def log_action(self, message: str, level: str = 'info') -> None:
        """Log migration action."""
        log_entry = {
            'timestamp': str(Path().resolve()),
            'level': level,
            'message': message
        }
        self.migration_log.append(log_entry)
        
        if level == 'error':
            logger.error(message)
        else:
            logger.info(message)


def migrate_site(site_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to migrate a site.
    
    Args:
        site_path: Path to the site directory
        config: Migration configuration
        
    Returns:
        Migration result dictionary
    """
    migrator = TemplateMigrationTool(site_path, config)
    return migrator.execute_migration()


def analyze_site(site_path: str) -> Dict[str, Any]:
    """
    Analyze a site structure without migrating.
    
    Args:
        site_path: Path to the site directory
        
    Returns:
        Analysis dictionary
    """
    migrator = TemplateMigrationTool(site_path)
    return migrator.analyze_current_structure()
