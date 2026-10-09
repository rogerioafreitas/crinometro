filepath = 'utils/report_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'if not chirp_peaks_list or len(chirp_peaks_list) < 3:' in line:
        if 'def analyze_rhythmic_cadence' not in lines[i-1] and 'def analyze_rhythmic_cadence' not in lines[i-2]:
            lines.insert(i, 'def analyze_rhythmic_cadence(chirp_peaks_list, rate):\n')
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
