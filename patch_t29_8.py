filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'ec.toggle_peak_marker(novel_time, f_click=5432.0, amp_click=0.88)' in line and 'print' not in line:
        lines[i] = '        ret = ec.toggle_peak_marker(novel_time, f_click=5432.0, amp_click=0.88)\n        print("REAL toggle ret:", ret)\n'
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
