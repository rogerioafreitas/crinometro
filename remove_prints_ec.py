filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'print("target=' in line: continue
    if 'print("Returning None at line"' in line: continue
    if 'print("new_verified inside toggle' in line: continue
    if 'print("DEBUG:' in line: continue
    if 'print("POST-UPDATE:' in line: continue
    new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
