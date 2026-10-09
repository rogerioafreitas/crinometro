filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def tearDown(self):' in line:
        for j in range(i, i+20):
            if '_original_config_text' in lines[j]:
                lines[j] = '        # Ensure next test gets a clean slate\n'
                lines[j+1] = '        try:\n'
                lines[j+2] = '            with open(CONFIG_FILE, "w", encoding="utf-8") as f:\n'
                lines[j+3] = '                f.write("{}")\n'
                lines[j+4] = '        except Exception:\n'
                lines[j+5] = '            pass\n'
                break
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
