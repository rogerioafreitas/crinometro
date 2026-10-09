filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'ctx.update_verified_and_metadata(new_verified, meta)' in line:
        lines.insert(i, '            print("DEBUG:", type(verified), verified, target, new_verified)\n')
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
