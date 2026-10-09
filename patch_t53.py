filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if "res = CricketAnalyzer.analyze(wav_path, params)" in line and "test_53" in "".join(lines[i-15:i]):
        new_lines.append(line.replace("res = CricketAnalyzer.analyze(wav_path, params)", "learner.import_model_file(corrupted_path)"))
    elif "if os.path.exists(wav_path):" in line and "test_53" in "".join(lines[i-15:i]):
        new_lines.append(line.replace("wav_path", "corrupted_path"))
    elif "os.remove(wav_path)" in line and "test_53" in "".join(lines[i-15:i]):
        new_lines.append(line.replace("wav_path", "corrupted_path"))
    else:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
