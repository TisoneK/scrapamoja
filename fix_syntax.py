#!/usr/bin/env python3
"""Fix syntax error in scraper.py"""

with open('src/sites/flashscore/scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken line 399
fixed_content = content.replace(
    'return {"error": f"Failed to norm\nalize scheduled matches: {str(e)}"}',
    'return {"error": f"Failed to normalize scheduled matches: {str(e)}"}'
)

with open('src/sites/flashscore/scraper.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print('Fixed syntax error on line 399')
