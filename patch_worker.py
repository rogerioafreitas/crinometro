filepath = 'core/worker.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.rstrip() == '        def run(self):':
        lines[i] = '    def run(self):\n'
        for j in range(i+1, i+15):
            if lines[j].startswith('        try:') or lines[j].startswith('        except Exception as exc:'):
                break # Just in case it's already correct. Wait, try is 8 spaces in my output above!
            if j < len(lines):
                lines[j] = lines[j][4:] # Remove 4 spaces from all lines in the block

# The output above says:
# 34:         def run(self):
# 35:         try:
# This means BOTH are indented 8 spaces. `def run` should be 4 spaces, and `try:` should be 8.
# So I'll just rewrite the block

new_block = """    def run(self):
        try:
            res = self.target_fn(*self.args, **self.kwargs)
            if not self._abort_event.is_set():
                self.finished_signal.emit(res)
            else:
                self.cancelled_signal.emit()
        except Exception as exc:
            if not self._abort_event.is_set():
                self.error_signal.emit(str(exc))
            else:
                self.cancelled_signal.emit()
"""

# Let's just find where it is and replace it.
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines[:33] + [new_block])
