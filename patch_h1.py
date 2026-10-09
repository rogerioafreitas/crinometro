import re

filepath = 'utils/helpers.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix helpers.py
content = re.sub(r'def :\n\s+""".*?"""\n\s+def handle_exception', 'def handle_exception', content)
# Unindent handle_exception body? 
# Wait, if `def :` was at line 9 and `def handle_exception` at 11, let's just rewrite helpers.py handling.

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
