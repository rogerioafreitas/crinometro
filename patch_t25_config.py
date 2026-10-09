filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def test_25' in line:
        lines.insert(i+1, '        import os; from utils.constants import CONFIG_FILE; print("\\nCONFIG AT START OF 25:\\n", open(CONFIG_FILE).read() if os.path.exists(CONFIG_FILE) else "MISSING")\n')
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
