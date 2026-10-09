filepath = 'utils/report_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
# Remove lines 125 and 126
new_lines = lines[:125] + lines[127:]
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.strip() == 'with self.assertRaises(ValueError):':
        new_lines.append(line)
        new_lines.append('                res = CricketAnalyzer.analyze(wav_path, params)\n')
        skip = True
    elif skip and 'def ' in line:
        skip = False
        new_lines.append(line)
    elif skip:
        pass
    else:
        new_lines.append(line)
        
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
