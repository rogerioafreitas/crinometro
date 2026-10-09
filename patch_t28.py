filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("novel_sample = {'idx': 15435, 'freq': 5200.0, 'amp': 0.75}", "novel_sample = 15435")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
