#!/usr/bin/env python
import sys
print('Starting...', flush=True)
sys.stdout.flush()

from src.selectors.yaml_loader import YAMLSelectorLoader
print('Loader imported', flush=True)
sys.stdout.flush()

loader = YAMLSelectorLoader()
print('Loader created', flush=True)
sys.stdout.flush()

try:
    sel = loader.load_selector_from_file('src/sites/flashscore/selectors/extraction/match_list/match_items.yaml')
    print(f'Loaded: {sel.id}', flush=True)
    print(f'Strategies: {len(sel.strategies)}', flush=True)
    for i, s in enumerate(sel.strategies):
        print(f'  {i}: priority={s.priority}', flush=True)
except Exception as e:
    print(f'ERROR: {str(e)[:300]}', flush=True)
    import traceback
    traceback.print_exc()
