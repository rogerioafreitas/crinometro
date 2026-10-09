filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'action = "added"' in line:
        for j in range(i+5, i+20):
            if j < len(lines):
                print(f'{j}: {repr(lines[j])}')
        break
