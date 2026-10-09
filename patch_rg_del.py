filepath = 'utils/report_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = lines[:515] + lines[597:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
