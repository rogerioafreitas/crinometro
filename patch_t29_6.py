filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == 'return None':
        new_lines.append(f'            print("Returning None at line", {len(new_lines)})\n')
    new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
