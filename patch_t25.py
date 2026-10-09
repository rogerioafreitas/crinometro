filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def test_25' in line:
        lines[i+40] = '        print("before toggle novel_time. verified:", self.window.ctx.peaks_user_verified)\n' + lines[i+40]
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
