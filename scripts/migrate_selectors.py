#!/usr/bin/env python3
"""
Flat to Hierarchical Selector Migration Script

This script migrates existing flat YAML selector files to the new
hierarchical structure required by the flashscore workflow.

Usage:
    python scripts/migrate_selectors.py --source <source_dir> --target <target_dir> [options]

Examples:
    # Basic migration
    python scripts/migrate_selectors.py --source src/sites/flashscore/selectors --target src/sites/flashscore/selectors_new
    
    # Migration with backup
    python scripts/migrate_selectors.py --source src/sites/flashscore/selectors --target src/sites/flashscore/selectors_new --backup
    
    # Dry run (no actual file operations)
    python scripts/migrate_selectors.py --source src/sites/flashscore/selectors --target src/sites/flashscore/selectors_new --dry-run
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.selectors.migration_utils import (
    FlatToHierarchicalMigrator,
    SelectorBackupManager,
    create_backup,
    migrate_flat_to_hierarchical,
    validate_migration
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Migrate flat YAML selector files to hierarchical structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source src/sites/flashscore/selectors --target src/sites/flashscore/selectors_new
  %(prog)s --source src/sites/flashscore/selectors --target src/sites/flashscore/selectors_new --backup --validate
  %(prog)s --source src/sites/flashscore/selectors --target src/sites/flashscore/selectors_new --dry-run
        """
    )
    
    parser.add_argument(
        '--source',
        required=True,
        type=Path,
        help='Source directory containing flat YAML selector files'
    )
    
    parser.add_argument(
        '--target',
        required=True,
        type=Path,
        help='Target directory for hierarchical selector structure'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of source files before migration'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate migration result after completion'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform dry run without actual file operations'
    )
    
    parser.add_argument(
        '--backup-root',
        type=Path,
        default=Path('./backups'),
        help='Root directory for backups (default: ./backups)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force migration even if target directory exists'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """Validate command line arguments."""
    errors = []
    
    # Check source directory
    if not args.source.exists():
        errors.append(f"Source directory does not exist: {args.source}")
    
    if not args.source.is_dir():
        errors.append(f"Source path is not a directory: {args.source}")
    
    # Check source has YAML files
    yaml_files = list(args.source.glob("*.yaml")) + list(args.source.glob("*.yml"))
    if not yaml_files:
        errors.append(f"No YAML files found in source directory: {args.source}")
    
    # Check target directory
    if args.target.exists() and not args.force:
        errors.append(f"Target directory already exists: {args.target} (use --force to override)")
    
    # Check backup directory
    if not args.backup_root.exists():
        try:
            args.backup_root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create backup directory: {e}")
    
    return errors


async def create_dry_run_report(source_dir: Path, target_dir: Path) -> dict:
    """Create a dry run report showing what would be migrated."""
    migrator = FlatToHierarchicalMigrator(source_dir, target_dir)
    
    # Get source files
    yaml_files = list(source_dir.glob("*.yaml")) + list(source_dir.glob("*.yml"))
    
    report = {
        "source_directory": str(source_dir),
        "target_directory": str(target_dir),
        "source_files": [],
        "migration_plan": [],
        "estimated_changes": {
            "files_to_migrate": len(yaml_files),
            "primary_folders": 4,
            "secondary_folders": 5,
            "tertiary_folders": 6
        }
    }
    
    # Analyze each file
    for yaml_file in yaml_files:
        file_info = {
            "name": yaml_file.name,
            "size": yaml_file.stat().st_size,
            "modified": yaml_file.stat().st_mtime
        }
        
        # Determine target context
        target_context = migrator._determine_target_context(yaml_file)
        if target_context:
            file_info["target_context"] = target_context
        else:
            file_info["target_context"] = {
                "primary": "navigation",
                "secondary": None,
                "tertiary": None
            }
            file_info["warning"] = "Context unclear, will place in navigation"
        
        report["source_files"].append(file_info)
    
    return report


async def main():
    """Main migration function."""
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    errors = validate_arguments(args)
    if errors:
        logger.error("Argument validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info(f"Starting migration from {args.source} to {args.target}")
    
    try:
        if args.dry_run:
            # Dry run mode
            logger.info("DRY RUN MODE - No files will be modified")
            
            report = await create_dry_run_report(args.source, args.target)
            
            print("\n" + "="*60)
            print("MIGRATION DRY RUN REPORT")
            print("="*60)
            print(f"Source: {report['source_directory']}")
            print(f"Target: {report['target_directory']}")
            print(f"Files to migrate: {report['estimated_changes']['files_to_migrate']}")
            print("\nMigration Plan:")
            
            for file_info in report["source_files"]:
                target = file_info["target_context"]
                target_path = f"{target['primary']}"
                if target.get('secondary'):
                    target_path += f"/{target['secondary']}"
                if target.get('tertiary'):
                    target_path += f"/{target['tertiary']}"
                
                print(f"  {file_info['name']} -> {target_path}")
                if 'warning' in file_info:
                    print(f"    WARNING: {file_info['warning']}")
            
            print("="*60)
            
            # Save dry run report
            report_file = Path("migration_dry_run_report.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\nDry run report saved to: {report_file}")
            
        else:
            # Actual migration
            if args.backup:
                logger.info("Creating backup before migration...")
                backup_result = await create_backup(args.source, args.backup_root)
                
                if not backup_result.success:
                    logger.error("Backup creation failed:")
                    for error in backup_result.errors:
                        logger.error(f"  - {error}")
                    sys.exit(1)
                
                logger.info(f"Backup created: {backup_result.backup_path}")
                logger.info(f"Backed up {backup_result.files_backed_up} files ({backup_result.backup_size_mb:.2f}MB)")
            
            # Ensure target directory exists
            args.target.mkdir(parents=True, exist_ok=True)
            
            # Perform migration
            logger.info("Starting migration...")
            migration_result = await migrate_flat_to_hierarchical(
                args.source,
                args.target,
                create_backup=False  # Already created if requested
            )
            
            # Report results
            print("\n" + "="*60)
            print("MIGRATION RESULTS")
            print("="*60)
            
            if migration_result.success:
                print(f"✓ Migration completed successfully")
                print(f"✓ Files migrated: {migration_result.files_migrated}")
                print(f"✓ Files failed: {migration_result.files_failed}")
                print(f"✓ Migration time: {migration_result.migration_time_ms:.2f}ms")
                
                if migration_result.backup_path:
                    print(f"✓ Backup: {migration_result.backup_path}")
                
                if migration_result.warnings:
                    print("\nWarnings:")
                    for warning in migration_result.warnings:
                        print(f"  ⚠ {warning}")
            else:
                print(f"✗ Migration failed")
                print(f"✗ Files migrated: {migration_result.files_migrated}")
                print(f"✗ Files failed: {migration_result.files_failed}")
                
                print("\nErrors:")
                for error in migration_result.errors:
                    print(f"  ✗ {error}")
                sys.exit(1)
            
            # Validation if requested
            if args.validate:
                logger.info("Validating migration result...")
                validation_results = await validate_migration(args.target, args.source)
                
                print("\n" + "="*60)
                print("VALIDATION RESULTS")
                print("="*60)
                
                # Structure validation
                structure_valid = validation_results.get("structure_valid", False)
                print(f"Structure validation: {'✓ PASS' if structure_valid else '✗ FAIL'}")
                
                if not structure_valid:
                    structure_errors = validation_results.get("structure_errors", [])
                    for error in structure_errors:
                        print(f"  ✗ {error['message']}")
                        if error.get('suggestion'):
                            print(f"    Suggestion: {error['suggestion']}")
                
                # Naming validation
                naming_valid = validation_results.get("naming_valid", False)
                print(f"Naming convention: {'✓ PASS' if naming_valid else '✗ FAIL'}")
                
                if not naming_valid:
                    naming_violations = validation_results.get("naming_violations", [])
                    for violation in naming_violations[:5]:  # Limit output
                        print(f"  ✗ {violation['file']}: {violation['type']}")
                        print(f"    Suggestion: {violation['suggestion']}")
                    
                    if len(naming_violations) > 5:
                        print(f"  ... and {len(naming_violations) - 5} more violations")
                
                # Completeness check
                completeness = validation_results.get("completeness", {})
                missing_contexts = completeness.get("missing_contexts", [])
                
                if missing_contexts:
                    print(f"\nMissing contexts: {len(missing_contexts)}")
                    for missing in missing_contexts:
                        print(f"  ✗ {missing}")
                else:
                    print(f"\nCompleteness: ✓ All required contexts present")
                
                # Conflicts
                conflicts = validation_results.get("conflicts", [])
                if conflicts:
                    print(f"\nConflicts detected: {len(conflicts)}")
                    for conflict in conflicts:
                        print(f"  ✗ {conflict['type']}: {conflict.get('filename', 'unknown')}")
                else:
                    print(f"\nConflicts: ✓ None detected")
                
                # Recommendations
                recommendations = validation_results.get("recommendations", [])
                if recommendations:
                    print(f"\nRecommendations:")
                    for rec in recommendations:
                        print(f"  → {rec}")
                
                print("="*60)
                
                # Save validation report
                validation_file = Path("migration_validation_report.json")
                with open(validation_file, 'w') as f:
                    json.dump(validation_results, f, indent=2, default=str)
                
                print(f"\nValidation report saved to: {validation_file}")
            
            print("="*60)
            logger.info("Migration process completed")
    
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
