#!/usr/bin/env python3
"""
Automated migration script for existing snapshots.

This script migrates existing flat snapshot files to the new
context-aware hierarchical bundle architecture.

Usage:
    python migrate_snapshots.py [--old-path PATH] [--new-path PATH] [--dry-run] [--validate]
"""

import argparse
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.snapshot.migration import SnapshotMigrator, MigrationValidator
from src.core.snapshot.compatibility import enable_deprecation_warnings


class MigrationScript:
    """Main migration script orchestrator."""
    
    def __init__(self, old_path: str, new_path: str):
        self.old_path = Path(old_path)
        self.new_path = Path(new_path)
        self.migrator = SnapshotMigrator(str(old_path), str(new_path))
        self.validator = MigrationValidator(str(new_path))
        
        # Ensure deprecation warnings are visible
        enable_deprecation_warnings()
    
    async def run_migration(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run the complete migration process."""
        print(f"🚀 Starting snapshot migration...")
        print(f"📁 Source: {self.old_path}")
        print(f"📁 Target: {self.new_path}")
        print(f"🔍 Dry run: {dry_run}")
        print()
        
        # Check source directory
        if not self.old_path.exists():
            print(f"❌ Source directory does not exist: {self.old_path}")
            return {"success": False, "error": "Source directory not found"}
        
        # Create target directory if it doesn't exist
        if not dry_run:
            self.new_path.mkdir(parents=True, exist_ok=True)
        
        # Scan existing snapshots
        print("🔍 Scanning existing snapshots...")
        candidates = self.migrator.scan_existing_snapshots()
        
        if not candidates:
            print("ℹ️  No snapshot files found to migrate")
            return {"success": True, "migrated": 0, "message": "No files to migrate"}
        
        print(f"📊 Found {len(candidates)} snapshot files to migrate")
        
        # Show migration summary
        self._show_migration_summary(candidates)
        
        # Confirm migration
        if not dry_run:
            response = input("\n⚠️  This will migrate files. Continue? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                return {"success": False, "error": "User cancelled"}
        
        # Run migration
        print("\n🔄 Running migration...")
        start_time = datetime.now()
        
        results = await self.migrator.migrate_snapshots(dry_run=dry_run)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Show results
        self._show_migration_results(results, duration, dry_run)
        
        # Validate migration if not dry run
        if not dry_run and results["migrated"] > 0:
            print("\n✅ Validating migrated snapshots...")
            validation_results = await self.validator.validate_migration()
            self._show_validation_results(validation_results)
        
        return {
            "success": True,
            "results": results,
            "duration": duration,
            "dry_run": dry_run
        }
    
    def _show_migration_summary(self, candidates: List[Dict[str, Any]]) -> None:
        """Show summary of files to be migrated."""
        # Group by file type
        file_types = {}
        sites = set()
        
        for candidate in candidates:
            file_type = candidate["file_type"]
            file_types[file_type] = file_types.get(file_type, 0) + 1
            sites.add(candidate["context"]["site"])
        
        print("📋 Migration Summary:")
        print(f"   📁 Sites: {len(sites)} ({', '.join(sorted(sites))})")
        print(f"   📄 File types: {dict(file_types)}")
        print(f"   📊 Total size: {sum(c['size'] for c in candidates) / 1024 / 1024:.2f} MB")
        
        # Show oldest and newest files
        oldest = min(candidates, key=lambda x: x["modified_time"])
        newest = max(candidates, key=lambda x: x["modified_time"])
        
        print(f"   📅 Date range: {oldest['modified_time'].strftime('%Y-%m-%d')} to {newest['modified_time'].strftime('%Y-%m-%d')}")
    
    def _show_migration_results(self, results: Dict[str, Any], duration: float, dry_run: bool) -> None:
        """Show migration results."""
        action = "Would migrate" if dry_run else "Migrated"
        
        print(f"\n📊 Migration Results ({action}):")
        print(f"   ✅ {action}: {results['migrated']} files")
        print(f"   ❌ Failed: {results['failed']} files")
        print(f"   ⏭️  Skipped: {results['skipped']} files")
        print(f"   ⏱️  Duration: {duration:.2f} seconds")
        
        if results["errors"]:
            print(f"\n❌ Errors encountered:")
            for error in results["errors"]:
                print(f"   • {error}")
    
    def _show_validation_results(self, results: Dict[str, Any]) -> None:
        """Show validation results."""
        print(f"\n✅ Validation Results:")
        print(f"   📦 Total bundles: {results['total_bundles']}")
        print(f"   ✅ Valid bundles: {results['valid_bundles']}")
        print(f"   ❌ Invalid bundles: {results['invalid_bundles']}")
        
        if results["issues"]:
            print(f"\n⚠️  Validation issues:")
            for issue in results["issues"]:
                print(f"   • {issue}")
    
    def save_migration_log(self, output_path: str) -> None:
        """Save migration log to file."""
        log_path = Path(output_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.migrator.save_migration_log(str(log_path))
        print(f"📝 Migration log saved to: {log_path}")


class MigrationConfig:
    """Configuration for migration operations."""
    
    DEFAULT_OLD_PATH = "data/snapshots"
    DEFAULT_NEW_PATH = "data/snapshots_new"
    
    @classmethod
    def get_default_paths(cls) -> Dict[str, str]:
        """Get default migration paths."""
        return {
            "old_path": cls.DEFAULT_OLD_PATH,
            "new_path": cls.DEFAULT_NEW_PATH
        }
    
    @classmethod
    def validate_paths(cls, old_path: str, new_path: str) -> bool:
        """Validate migration paths."""
        old = Path(old_path)
        new = Path(new_path)
        
        # Check if old path exists
        if not old.exists():
            print(f"❌ Source path does not exist: {old_path}")
            return False
        
        # Check if new path would conflict with old path
        if old.resolve() == new.resolve():
            print(f"❌ Source and target paths cannot be the same: {old_path}")
            return False
        
        # Check if new path already has content
        if new.exists() and any(new.iterdir()):
            print(f"⚠️  Target path already exists and is not empty: {new_path}")
            return True  # Allow but warn
        
        return True


async def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate existing snapshots to new hierarchical structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default paths
  %(prog)s --old-path ./old --new-path ./new  # Custom paths
  %(prog)s --dry-run                         # Preview migration
  %(prog)s --validate                        # Validate existing migration
        """
    )
    
    parser.add_argument(
        "--old-path",
        default=MigrationConfig.DEFAULT_OLD_PATH,
        help="Path to existing flat snapshots (default: %(default)s)"
    )
    
    parser.add_argument(
        "--new-path", 
        default=MigrationConfig.DEFAULT_NEW_PATH,
        help="Path for new hierarchical snapshots (default: %(default)s)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing migration instead of running new migration"
    )
    
    parser.add_argument(
        "--log-file",
        help="Save migration log to specified file"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not MigrationConfig.validate_paths(args.old_path, args.new_path):
        sys.exit(1)
    
    try:
        if args.validate:
            # Validation mode
            print(f"🔍 Validating migration at: {args.new_path}")
            validator = MigrationValidator(args.new_path)
            results = await validator.validate_migration()
            
            script = MigrationScript(args.old_path, args.new_path)
            script._show_validation_results(results)
            
            # Exit with error code if validation failed
            if results["invalid_bundles"] > 0:
                sys.exit(1)
        
        else:
            # Migration mode
            script = MigrationScript(args.old_path, args.new_path)
            results = await script.run_migration(dry_run=args.dry_run)
            
            # Save log if requested
            if args.log_file:
                script.save_migration_log(args.log_file)
            
            # Exit with appropriate code
            if not results["success"]:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n❌ Migration interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
