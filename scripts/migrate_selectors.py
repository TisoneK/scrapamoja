#!/usr/bin/env python3
"""Migration script to add required fields to YAML selector files."""

import re
from pathlib import Path

def migrate_yaml_files():
    selectors_dir = Path('src/sites/flashscore/selectors')
    yaml_files = list(selectors_dir.rglob('*.yaml'))
    print(f'Found {len(yaml_files)} YAML files to migrate')
    
    count = 0
    for yaml_file in yaml_files:
        content = yaml_file.read_text(encoding='utf-8')
        
        # Check if id is already present
        first_lines = content.split('\n')[:5]
        has_id = any(line.strip().startswith('id:') for line in first_lines)
        
        # Generate id from filename
        filename = yaml_file.stem
        selector_id = re.sub(r'[^a-zA-Z0-9_]', '_', filename)
        if selector_id[0].isdigit():
            selector_id = 's_' + selector_id
        
        # Generate name from filename
        name = filename.replace('_', ' ').title()
        
        # Insert id at the beginning (if not already there)
        lines = content.split('\n')
        
        if not has_id:
            lines.insert(0, f'id: {selector_id}')
            # After id, add name and selector_type
            lines.insert(1, f'name: {name}')
            lines.insert(2, 'selector_type: css')
        else:
            # Just add name and selector_type after id
            # Find where id is
            for i, line in enumerate(lines):
                if line.strip().startswith('id:'):
                    # Add name after id
                    lines.insert(i+1, f'name: {name}')
                    # Add selector_type after name
                    lines.insert(i+2, 'selector_type: css')
                    break
        
        # Write back
        new_content = '\n'.join(lines)
        yaml_file.write_text(new_content, encoding='utf-8')
        
        print(f'Migrated {yaml_file.name} -> id: {selector_id}, name: {name}')
        count += 1
    
    print(f'\nMigration complete! Migrated {count} files')

if __name__ == '__main__':
    migrate_yaml_files()
