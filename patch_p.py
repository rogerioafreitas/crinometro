filepath = 'ui/panels.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'def _toggle_pulse_edit_mode' in line:
        for j in range(max(0, i-2), i+15):
            if j < len(lines):
                print(f'{j}: {repr(lines[j])}')
        break
