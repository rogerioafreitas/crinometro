filepath = 'ui/main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.strip() == 'if hasattr(self, "btn_analyze_selected"):':
        if i + 1 < len(lines) and lines[i+1].strip() == '':
            lines[i+2] = '            ' + lines[i+2].lstrip()
            lines[i+3] = '            ' + lines[i+3].lstrip()
            lines[i+4] = '                ' + lines[i+4].lstrip()
            lines[i+5] = '                ' + lines[i+5].lstrip()
            lines[i+6] = '\n'
            lines[i+7] = '            ' + lines[i+7].lstrip()
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
