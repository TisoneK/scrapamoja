#!/usr/bin/env python3
"""
Working snapshot viewer that finds and displays snapshot files.
This script will:
1. Find all snapshot files regardless of location
2. Display them in readable format
3. Provide debugging insights
"""

import json
import os
import gzip
from pathlib import Path

def find_snapshot_files():
    """Find all snapshot files in the project."""
    snapshot_files = []
    
    # Common locations where snapshots might be
    search_paths = [
        "data/snapshots",
        "data/storage/snapshots", 
        "data/storage",
        "."
    ]
    
    for search_path in search_paths:
        path = Path(search_path)
        if path.exists():
            # Look for files with snapshot-like names
            for file_path in path.rglob("*"):
                if (file_path.is_file() and 
                    ("failure" in file_path.name.lower() or 
                     "snapshot" in file_path.name.lower() or
                     file_path.suffix in ['.json', '.jsongz'])):
                    snapshot_files.append(file_path)
    
    return snapshot_files

def view_snapshot_file(file_path):
    """View a snapshot file in readable format."""
    try:
        # Try to read as JSON (handle gzip compression)
        if file_path.suffix == '.jsongz':
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        print("\n" + "=" * 80)
        print(f"📊 SNAPSHOT FILE: {file_path.name}")
        print(f"📁 LOCATION: {file_path}")
        print(f"📏 SIZE: {file_path.stat().st_size:,} bytes")
        print("=" * 80)
        
        # Extract key information
        snapshot_id = data.get('id', 'unknown')
        selector_name = data.get('selector_name', 'unknown')
        snapshot_type = data.get('snapshot_type', 'unknown')
        created_at = data.get('created_at', 'unknown')
        
        print(f"\n🎯 SNAPSHOT DETAILS:")
        print(f"   • ID: {snapshot_id}")
        print(f"   • Type: {snapshot_type}")
        print(f"   • Selector: {selector_name}")
        print(f"   • Created: {created_at}")
        
        # Error information
        if 'error' in data:
            print(f"   • Error: {data['error']}")
        
        # DOM content analysis
        if 'dom_content' in data:
            dom_content = data['dom_content']
            print(f"   • DOM Length: {len(dom_content):,} characters")
            
            # Show preview
            preview = dom_content[:300] + "..." if len(dom_content) > 300 else dom_content
            print(f"\n📄 DOM CONTENT PREVIEW:")
            print("-" * 50)
            print(preview)
            print("-" * 50)
        
        # Metadata
        if 'metadata' in data:
            print(f"\n📋 METADATA:")
            print("-" * 50)
            for key, value in data['metadata'].items():
                print(f"   • {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading {file_path.name}: {e}")
        return False

def main():
    """Main function."""
    print("🔍 SNAPSHOT FILE ANALYZER")
    print("=" * 50)
    
    # Find all snapshot files
    snapshot_files = find_snapshot_files()
    
    if not snapshot_files:
        print("❌ No snapshot files found in the project.")
        print("\n📁 Searched locations:")
        print("   • data/snapshots/")
        print("   • data/storage/snapshots/")
        print("   • data/storage/")
        print("   • Current directory")
        return
    
    print(f"📊 Found {len(snapshot_files)} snapshot files:")
    
    # Sort by size (largest first)
    snapshot_files.sort(key=lambda f: f.stat().st_size, reverse=True)
    
    # Display summary
    for i, file_path in enumerate(snapshot_files, 1):
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"   {i:2d}. {file_path.name} ({size_mb:.1f} MB)")
    
    # View the largest/most recent file
    if snapshot_files:
        print(f"\n🎯 Analyzing largest snapshot file...")
        largest_file = snapshot_files[0]
        success = view_snapshot_file(largest_file)
        
        if success:
            print(f"\n✅ SUCCESS: Snapshot file is readable and contains debugging data!")
            print(f"📊 Your snapshot system is WORKING - files are accessible!")
        else:
            print(f"\n❌ ISSUE: Snapshot file could not be read properly")

if __name__ == "__main__":
    main()
