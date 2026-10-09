filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def test_29' in line:
        lines.insert(i+1, '        print("toggle ret:", self.window.editor_controller.toggle_peak_marker(0.35, f_click=5432.0, amp_click=0.88))\n')
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
