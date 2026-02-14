with open('src/sites/flashscore/scraper.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 399 - remove the line break in the f-string
lines[398] = '            return {"error": f"Failed to normalize scheduled matches: {str(e)}"}\n'

with open('src/sites/flashscore/scraper.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed the broken f-string on line 399')
