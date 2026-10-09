filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.strip() == 'res = CricketAnalyzer.analyze(wav_path, params)':
        new_lines.append(line)
        new_lines.append('        finally:\n')
        new_lines.append('            import os\n')
        new_lines.append('            if os.path.exists(wav_path):\n')
        new_lines.append('                os.remove(wav_path)\n')
        new_lines.append('\n')
    else:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
