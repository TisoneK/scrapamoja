#!/usr/bin/env python
import sys
import yaml
print('Starting...', flush=True)

file_path = 'src/sites/flashscore/selectors/extraction/match_list/match_items.yaml'
with open(file_path, 'r', encoding='utf-8') as f:
    yaml_data = yaml.safe_load(f)

print(f'Initial id: {yaml_data.get("id")}', flush=True)
print(f'Initial strategies[0]: {yaml_data.get("strategies", [])[0]}', flush=True)

from src.selectors.strategies.converter import detect_format, convert_legacy_yaml, StrategyFormat

# First detection in load_selector_from_file
fmt1 = detect_format(yaml_data)
print(f'Format 1: {fmt1}', flush=True)

if fmt1 == StrategyFormat.LEGACY:
    print('Converting in load_selector_from_file...', flush=True)
    yaml_data = convert_legacy_yaml(yaml_data, selector_id=yaml_data.get('id', 'match_items'))
    print(f'After conversion, strategies[0]: {yaml_data.get("strategies", [])[0]}', flush=True)

# Second detection in _yaml_to_selector  
fmt2 = detect_format(yaml_data)
print(f'Format 2: {fmt2}', flush=True)

if fmt2 == StrategyFormat.LEGACY:
    print('Converting again in _yaml_to_selector...', flush=True)
    yaml_data = convert_legacy_yaml(yaml_data, selector_id=yaml_data.get('id', 'match_items'))
    
print('All priorities:', [s.get('priority') for s in yaml_data.get('strategies', [])], flush=True)
print('Unique?', len(set([s.get('priority') for s in yaml_data.get('strategies', [])])) == len(yaml_data.get('strategies', [])), flush=True)