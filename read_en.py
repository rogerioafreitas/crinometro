with open('utils/i18n.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_en = False
out = []
for line in lines:
    if '"en": {' in line:
        in_en = True
    if in_en and ('ml_enabled' in line or 'ml_disabled' in line):
        out.append(line)
with open('en_lines.txt', 'w', encoding='utf-8') as f:
    f.writelines(out)
