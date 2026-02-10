"""
Configuration export/import functionality for the scraper framework.

This module provides comprehensive configuration I/O capabilities, including
multiple format support, validation, and backup/restore functionality.
"""

import json
import yaml
import os
import shutil
from typing import Dict, Any, List, Optional, Union, Type
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import zipfile
import tempfile

from .config_schemas import get_schema, validate_config_by_schema
from .config_validator import validate_config
from .config_merger import merge_configs
from .feature_flags import export_flags, import_flags
from .environment_detector import detect_environment


class ConfigFormat(Enum):
    """Configuration format enumeration."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    XML = "xml"
    ENV = "env"
    INI = "ini"


class ExportMode(Enum):
    """Export mode enumeration."""
    FULL = "full"
    MINIMAL = "minimal"
    ENVIRONMENT = "environment"
    SCHEMA_ONLY = "schema_only"
    FLAGS_ONLY = "flags_only"


@dataclass
class ExportOptions:
    """Configuration export options."""
    format: ConfigFormat = ConfigFormat.JSON
    mode: ExportMode = ExportMode.FULL
    include_sensitive: bool = False
    include_metadata: bool = True
    include_comments: bool = True
    pretty_print: bool = True
    compress: bool = False
    backup: bool = True
    environments: List[str] = field(default_factory=list)
    schemas: List[str] = field(default_factory=list)
    exclude_fields: List[str] = field(default_factory=list)
    include_fields: List[str] = field(default_factory=list)


@dataclass
class ImportOptions:
    """Configuration import options."""
    format: ConfigFormat = ConfigFormat.JSON
    validate: bool = True
    merge_strategy: str = "replace"
    backup_existing: bool = True
    overwrite: bool = False
    dry_run: bool = False
    environment: Optional[str] = None
    schema_name: Optional[str] = None


@dataclass
class ImportResult:
    """Configuration import result."""
    success: bool
    imported_configs: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    import_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ExportResult:
    """Configuration export result."""
    success: bool
    export_path: str
    format: str
    size_bytes: int
    configs_count: int
    backup_path: Optional[str] = None
    export_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfigIO:
    """Configuration I/O manager."""
    
    def __init__(self):
        """Initialize configuration I/O manager."""
        self._export_history: List[ExportResult] = []
        self._import_history: List[ImportResult] = []
        self._backup_dir = Path.cwd() / "config_backups"
        self._temp_dir = Path(tempfile.gettempdir()) / "config_io_temp"
        
        # Ensure directories exist
        self._backup_dir.mkdir(exist_ok=True)
        self._temp_dir.mkdir(exist_ok=True)
        
        # Supported formats
        self._format_handlers = {
            ConfigFormat.JSON: self._handle_json,
            ConfigFormat.YAML: self._handle_yaml,
            ConfigFormat.TOML: self._handle_toml,
            ConfigFormat.XML: self._handle_xml,
            ConfigFormat.ENV: self._handle_env,
            ConfigFormat.INI: self._handle_ini
        }
    
    def export_config(self, config: Dict[str, Any], 
                     output_path: Union[str, Path],
                     options: Optional[ExportOptions] = None) -> ExportResult:
        """
        Export configuration to file.
        
        Args:
            config: Configuration to export
            output_path: Output file path
            options: Export options
            
        Returns:
            Export result
        """
        start_time = datetime.utcnow()
        
        try:
            options = options or ExportOptions()
            output_path = Path(output_path)
            
            # Prepare configuration for export
            export_config = self._prepare_config_for_export(config, options)
            
            # Create backup if requested
            backup_path = None
            if options.backup and output_path.exists():
                backup_path = self._create_backup(output_path)
            
            # Export based on format
            handler = self._format_handlers.get(options.format)
            if not handler:
                raise ValueError(f"Unsupported format: {options.format}")
            
            # Write configuration
            handler(export_config, output_path, options)
            
            # Compress if requested
            if options.compress:
                output_path = self._compress_file(output_path)
            
            # Calculate export time
            end_time = datetime.utcnow()
            export_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = ExportResult(
                success=True,
                export_path=str(output_path),
                format=options.format.value,
                size_bytes=output_path.stat().st_size,
                configs_count=len(export_config.get('configs', {})),
                backup_path=str(backup_path) if backup_path else None,
                export_time_ms=export_time_ms
            )
            
            self._export_history.append(result)
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            export_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ExportResult(
                success=False,
                export_path=str(output_path),
                format=options.format.value if options else "unknown",
                size_bytes=0,
                configs_count=0,
                export_time_ms=export_time_ms
            )
    
    def import_config(self, input_path: Union[str, Path],
                     options: Optional[ImportOptions] = None) -> ImportResult:
        """
        Import configuration from file.
        
        Args:
            input_path: Input file path
            options: Import options
            
        Returns:
            Import result
        """
        start_time = datetime.utcnow()
        
        try:
            options = options or ImportOptions()
            input_path = Path(input_path)
            
            # Check if file exists
            if not input_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {input_path}")
            
            # Decompress if needed
            if input_path.suffix == '.zip':
                input_path = self._decompress_file(input_path)
            
            # Detect format if not specified
            if options.format == ConfigFormat.JSON:
                options.format = self._detect_format(input_path)
            
            # Read configuration
            handler = self._format_handlers.get(options.format)
            if not handler:
                raise ValueError(f"Unsupported format: {options.format}")
            
            config = self._read_config(input_path, options.format)
            
            # Validate if requested
            validation_results = {}
            if options.validate:
                if options.schema_name:
                    validation_results = validate_config_by_schema(
                        config, options.schema_name, options.environment
                    )
                else:
                    validation_results = validate_config(config)
            
            # Create backup if requested
            backup_path = None
            if options.backup_existing:
                backup_path = self._create_backup(input_path)
            
            # Import configuration
            imported_configs = {}
            if not options.dry_run:
                imported_configs = self._apply_config(config, options)
            
            # Calculate import time
            end_time = datetime.utcnow()
            import_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = ImportResult(
                success=True,
                imported_configs=imported_configs,
                validation_results=validation_results,
                backup_path=str(backup_path) if backup_path else None,
                import_time_ms=import_time_ms
            )
            
            self._import_history.append(result)
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            import_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ImportResult(
                success=False,
                errors=[str(e)],
                import_time_ms=import_time_ms
            )
    
    def export_all_configs(self, output_dir: Union[str, Path],
                          configs: Dict[str, Dict[str, Any]],
                          options: Optional[ExportOptions] = None) -> List[ExportResult]:
        """
        Export multiple configurations to directory.
        
        Args:
            output_dir: Output directory
            configs: Dictionary of configurations to export
            options: Export options
            
        Returns:
            List of export results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for config_name, config_data in configs.items():
            # Generate filename
            filename = f"{config_name}.{options.format.value if options else 'json'}"
            output_path = output_dir / filename
            
            # Export configuration
            result = self.export_config(config_data, output_path, options)
            results.append(result)
        
        return results
    
    def import_all_configs(self, input_dir: Union[str, Path],
                          options: Optional[ImportOptions] = None) -> List[ImportResult]:
        """
        Import multiple configurations from directory.
        
        Args:
            input_dir: Input directory
            options: Import options
            
        Returns:
            List of import results
        """
        input_dir = Path(input_dir)
        
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        results = []
        
        # Find all config files
        config_files = []
        for ext in ['.json', '.yaml', '.yml', '.toml', '.xml', '.env', '.ini']:
            config_files.extend(input_dir.glob(f"*{ext}"))
        
        for config_file in config_files:
            # Import configuration
            result = self.import_config(config_file, options)
            results.append(result)
        
        return results
    
    def backup_configs(self, configs: Dict[str, Dict[str, Any]],
                      backup_name: Optional[str] = None) -> str:
        """
        Create a backup of configurations.
        
        Args:
            configs: Configurations to backup
            backup_name: Backup name (auto-generated if None)
            
        Returns:
            Backup directory path
        """
        if backup_name is None:
            backup_name = f"config_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        backup_dir = self._backup_dir / backup_name
        backup_dir.mkdir(exist_ok=True)
        
        # Export all configurations
        options = ExportOptions(
            format=ConfigFormat.JSON,
            mode=ExportMode.FULL,
            include_sensitive=True,
            pretty_print=True
        )
        
        self.export_all_configs(backup_dir, configs, options)
        
        return str(backup_dir)
    
    def restore_configs(self, backup_path: Union[str, Path],
                       options: Optional[ImportOptions] = None) -> List[ImportResult]:
        """
        Restore configurations from backup.
        
        Args:
            backup_path: Backup directory or file
            options: Import options
            
        Returns:
            List of import results
        """
        backup_path = Path(backup_path)
        
        if backup_path.is_file():
            # Single backup file
            return [self.import_config(backup_path, options)]
        else:
            # Backup directory
            return self.import_all_configs(backup_path, options)
    
    def _prepare_config_for_export(self, config: Dict[str, Any], 
                                 options: ExportOptions) -> Dict[str, Any]:
        """Prepare configuration for export."""
        export_config = {
            'exported_at': datetime.utcnow().isoformat(),
            'format': options.format.value,
            'mode': options.mode.value,
            'configs': {}
        }
        
        # Add metadata if requested
        if options.include_metadata:
            export_config['metadata'] = {
                'environment': detect_environment().value,
                'version': '1.0.0',
                'export_options': {
                    'include_sensitive': options.include_sensitive,
                    'include_comments': options.include_comments,
                    'pretty_print': options.pretty_print
                }
            }
        
        # Filter configuration based on mode
        if options.mode == ExportMode.FULL:
            export_config['configs'] = config
        elif options.mode == ExportMode.MINIMAL:
            export_config['configs'] = self._filter_minimal_config(config)
        elif options.mode == ExportMode.ENVIRONMENT:
            export_config['configs'] = self._filter_environment_config(config, options.environments)
        elif options.mode == ExportMode.SCHEMA_ONLY:
            export_config['configs'] = self._filter_schema_config(config, options.schemas)
        elif options.mode == ExportMode.FLAGS_ONLY:
            export_config['configs'] = {'feature_flags': export_flags()}
        
        # Remove sensitive fields if requested
        if not options.include_sensitive:
            export_config['configs'] = self._remove_sensitive_fields(export_config['configs'])
        
        # Filter fields
        if options.include_fields:
            export_config['configs'] = self._include_fields(export_config['configs'], options.include_fields)
        
        if options.exclude_fields:
            export_config['configs'] = self._exclude_fields(export_config['configs'], options.exclude_fields)
        
        return export_config
    
    def _filter_minimal_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter configuration to minimal essential fields."""
        minimal_fields = [
            'site_id', 'site_name', 'base_url', 'enabled',
            'timeout', 'retry_count', 'environment'
        ]
        
        return self._include_fields(config, minimal_fields)
    
    def _filter_environment_config(self, config: Dict[str, Any], 
                                  environments: List[str]) -> Dict[str, Any]:
        """Filter configuration for specific environments."""
        if not environments:
            return config
        
        filtered = {}
        for key, value in config.items():
            if isinstance(value, dict):
                filtered[key] = {
                    k: v for k, v in value.items()
                    if any(env in str(k).lower() for env in environments)
                }
            else:
                filtered[key] = value
        
        return filtered
    
    def _filter_schema_config(self, config: Dict[str, Any], 
                            schemas: List[str]) -> Dict[str, Any]:
        """Filter configuration for specific schemas."""
        if not schemas:
            return config
        
        filtered = {}
        for schema_name in schemas:
            if schema_name in config:
                filtered[schema_name] = config[schema_name]
        
        return filtered
    
    def _remove_sensitive_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive fields from configuration."""
        sensitive_patterns = [
            'password', 'secret', 'token', 'key', 'auth',
            'credential', 'private', 'confidential'
        ]
        
        def remove_sensitive(obj):
            if isinstance(obj, dict):
                return {
                    k: remove_sensitive(v) for k, v in obj.items()
                    if not any(pattern in k.lower() for pattern in sensitive_patterns)
                }
            elif isinstance(obj, list):
                return [remove_sensitive(item) for item in obj]
            else:
                return obj
        
        return remove_sensitive(config)
    
    def _include_fields(self, config: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """Include only specified fields."""
        def include_fields_recursive(obj, fields_set):
            if isinstance(obj, dict):
                return {
                    k: include_fields_recursive(v, fields_set)
                    for k, v in obj.items()
                    if k in fields_set or isinstance(v, (dict, list))
                }
            elif isinstance(obj, list):
                return [include_fields_recursive(item, fields_set) for item in obj]
            else:
                return obj
        
        return include_fields_recursive(config, set(fields))
    
    def _exclude_fields(self, config: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """Exclude specified fields."""
        def exclude_fields_recursive(obj, fields_set):
            if isinstance(obj, dict):
                return {
                    k: exclude_fields_recursive(v, fields_set)
                    for k, v in obj.items()
                    if k not in fields_set
                }
            elif isinstance(obj, list):
                return [exclude_fields_recursive(item, fields_set) for item in obj]
            else:
                return obj
        
        return exclude_fields_recursive(config, set(fields))
    
    def _detect_format(self, file_path: Path) -> ConfigFormat:
        """Detect configuration format from file extension."""
        ext = file_path.suffix.lower()
        
        if ext == '.json':
            return ConfigFormat.JSON
        elif ext in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif ext == '.toml':
            return ConfigFormat.TOML
        elif ext == '.xml':
            return ConfigFormat.XML
        elif ext == '.env':
            return ConfigFormat.ENV
        elif ext == '.ini':
            return ConfigFormat.INI
        else:
            return ConfigFormat.JSON  # Default to JSON
    
    def _handle_json(self, config: Dict[str, Any], output_path: Path, 
                     options: ExportOptions) -> None:
        """Handle JSON format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            if options.pretty_print:
                json.dump(config, f, indent=2, default=str)
            else:
                json.dump(config, f, default=str)
    
    def _handle_yaml(self, config: Dict[str, Any], output_path: Path, 
                     options: ExportOptions) -> None:
        """Handle YAML format."""
        try:
            import yaml
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            raise ImportError("PyYAML is required for YAML support")
    
    def _handle_toml(self, config: Dict[str, Any], output_path: Path, 
                     options: ExportOptions) -> None:
        """Handle TOML format."""
        try:
            import toml
            with open(output_path, 'w', encoding='utf-8') as f:
                toml.dump(config, f)
        except ImportError:
            raise ImportError("toml is required for TOML support")
    
    def _handle_xml(self, config: Dict[str, Any], output_path: Path, 
                   options: ExportOptions) -> None:
        """Handle XML format."""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.Element("configuration")
            self._dict_to_xml(config, root)
            
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
        except Exception as e:
            raise ImportError(f"XML handling failed: {str(e)}")
    
    def _handle_env(self, config: Dict[str, Any], output_path: Path, 
                   options: ExportOptions) -> None:
        """Handle environment file format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            self._dict_to_env(config, f)
    
    def _handle_ini(self, config: Dict[str, Any], output_path: Path, 
                   options: ExportOptions) -> None:
        """Handle INI format."""
        try:
            import configparser
            
            parser = configparser.ConfigParser()
            self._dict_to_ini(config, parser)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                parser.write(f)
        except Exception as e:
            raise ImportError(f"INI handling failed: {str(e)}")
    
    def _read_config(self, input_path: Path, format: ConfigFormat) -> Dict[str, Any]:
        """Read configuration from file."""
        if format == ConfigFormat.JSON:
            with open(input_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif format == ConfigFormat.YAML:
            try:
                import yaml
                with open(input_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except ImportError:
                raise ImportError("PyYAML is required for YAML support")
        elif format == ConfigFormat.TOML:
            try:
                import toml
                with open(input_path, 'r', encoding='utf-8') as f:
                    return toml.load(f)
            except ImportError:
                raise ImportError("toml is required for TOML support")
        elif format == ConfigFormat.XML:
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(input_path)
                root = tree.getroot()
                return self._xml_to_dict(root)
            except Exception as e:
                raise ImportError(f"XML parsing failed: {str(e)}")
        elif format == ConfigFormat.ENV:
            return self._env_to_dict(input_path)
        elif format == ConfigFormat.INI:
            try:
                import configparser
                parser = configparser.ConfigParser()
                parser.read(input_path, encoding='utf-8')
                return self._ini_to_dict(parser)
            except Exception as e:
                raise ImportError(f"INI parsing failed: {str(e)}")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _dict_to_xml(self, obj: Any, parent: ET.Element) -> None:
        """Convert dictionary to XML."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                child = ET.SubElement(parent, key)
                self._dict_to_xml(value, child)
        elif isinstance(obj, list):
            for item in obj:
                child = ET.SubElement(parent, "item")
                self._dict_to_xml(item, child)
        else:
            parent.text = str(obj)
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML to dictionary."""
        result = {}
        
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self._xml_to_dict(child)
        
        return result
    
    def _dict_to_env(self, obj: Any, f, prefix: str = "") -> None:
        """Convert dictionary to environment file format."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}{key}_" if prefix else f"{key}_"
                self._dict_to_env(value, f, new_prefix)
        else:
            f.write(f"{prefix.rstrip('_')}={obj}\n")
    
    def _env_to_dict(self, input_path: Path) -> Dict[str, Any]:
        """Convert environment file to dictionary."""
        config = {}
        
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        self._set_nested_value(config, key, value)
        
        return config
    
    def _dict_to_ini(self, obj: Any, parser, section: str = "DEFAULT") -> None:
        """Convert dictionary to INI format."""
        if isinstance(obj, dict):
            if not parser.has_section(section):
                parser.add_section(section)
            
            for key, value in obj.items():
                if isinstance(value, dict):
                    self._dict_to_ini(value, parser, key)
                else:
                    parser.set(section, key, str(value))
    
    def _ini_to_dict(self, parser) -> Dict[str, Any]:
        """Convert INI to dictionary."""
        config = {}
        
        for section_name in parser.sections():
            section_config = {}
            for key, value in parser[section_name].items():
                section_config[key] = value
            config[section_name] = section_config
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: str) -> None:
        """Set nested value from environment key."""
        keys = key.lower().split('_')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
        backup_path = self._backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _compress_file(self, file_path: Path) -> Path:
        """Compress file to ZIP."""
        zip_path = file_path.with_suffix('.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, file_path.name)
        
        # Remove original file
        file_path.unlink()
        
        return zip_path
    
    def _decompress_file(self, zip_path: Path) -> Path:
        """Decompress ZIP file."""
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            if len(file_list) != 1:
                raise ValueError("ZIP file must contain exactly one file")
            
            extracted_path = self._temp_dir / file_list[0]
            zf.extract(file_list[0], self._temp_dir)
            
            return extracted_path
    
    def _apply_config(self, config: Dict[str, Any], options: ImportOptions) -> Dict[str, Any]:
        """Apply imported configuration."""
        # This would implement the actual configuration application
        # For now, return the imported config
        return config
    
    def get_export_history(self, limit: Optional[int] = None) -> List[ExportResult]:
        """Get export history."""
        if limit:
            return self._export_history[-limit:]
        return self._export_history.copy()
    
    def get_import_history(self, limit: Optional[int] = None) -> List[ImportResult]:
        """Get import history."""
        if limit:
            return self._import_history[-limit:]
        return self._import_history.copy()
    
    def clear_history(self) -> None:
        """Clear import/export history."""
        self._export_history.clear()
        self._import_history.clear()


# Global config I/O instance
_config_io = ConfigIO()


# Convenience functions
def export_config(config: Dict[str, Any], output_path: Union[str, Path],
                 options: Optional[ExportOptions] = None) -> ExportResult:
    """Export configuration to file."""
    return _config_io.export_config(config, output_path, options)


def import_config(input_path: Union[str, Path],
                 options: Optional[ImportOptions] = None) -> ImportResult:
    """Import configuration from file."""
    return _config_io.import_config(input_path, options)


def export_all_configs(output_dir: Union[str, Path],
                      configs: Dict[str, Dict[str, Any]],
                      options: Optional[ExportOptions] = None) -> List[ExportResult]:
    """Export multiple configurations to directory."""
    return _config_io.export_all_configs(output_dir, configs, options)


def import_all_configs(input_dir: Union[str, Path],
                      options: Optional[ImportOptions] = None) -> List[ImportResult]:
    """Import multiple configurations from directory."""
    return _config_io.import_all_configs(input_dir, options)


def backup_configs(configs: Dict[str, Dict[str, Any]],
                   backup_name: Optional[str] = None) -> str:
    """Create backup of configurations."""
    return _config_io.backup_configs(configs, backup_name)


def restore_configs(backup_path: Union[str, Path],
                   options: Optional[ImportOptions] = None) -> List[ImportResult]:
    """Restore configurations from backup."""
    return _config_io.restore_configs(backup_path, options)


def get_export_history(limit: Optional[int] = None) -> List[ExportResult]:
    """Get export history."""
    return _config_io.get_export_history(limit)


def get_import_history(limit: Optional[int] = None) -> List[ImportResult]:
    """Get import history."""
    return _config_io.get_import_history(limit)
