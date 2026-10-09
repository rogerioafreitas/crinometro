filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'CONFIG AT START OF 25' in line: continue
    if 'before toggle novel_time. verified:' in line: continue
    new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
