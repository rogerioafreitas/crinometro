filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def test_29' in line:
        lines.insert(i+1, '        print("heavy:", self.window.ctx.active_heavy_data is not None)\n')
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
