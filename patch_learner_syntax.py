filepath = 'core/learner.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip() == 'self.model = None':
        if 'def __init__' in ''.join(lines[max(0, i-50):i]):
            pass # Keep looking

# Actually it's easier to just fix the broken part around 906-916

lines_new = lines[:908] + ["                    self.model = None\n", "                    self.training_features = np.empty((0, len(self.feature_names)))\n", "                    self.training_labels = np.empty(0, dtype=int)\n", "                    return False\n"] + lines[916:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines_new)
