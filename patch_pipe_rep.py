import re

# 1. PipelineOrchestrator _retain
filepath = 'ui/controllers/pipeline_orchestrator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

methods = """
    def _retain(self, worker):
        if not hasattr(self, '_retained_workers'):
            self._retained_workers = set()
        self._retained_workers.add(worker)
        worker.finished.connect(lambda w=worker: self._retained_workers.discard(w))

    def shutdown(self, timeout_ms=8000):
        if not hasattr(self, '_retained_workers'):
            return
        pending = list(self._retained_workers)
        for w in pending:
            w.abort()
        for w in pending:
            w.wait(timeout_ms)

    def _connect_worker_signals(self, worker):"""

content = content.replace("    def _connect_worker_signals(self, worker):", methods)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. report_generator.py indentation
filepath = 'utils/report_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'def analyze_rhythmic_cadence(chirp_peaks_list, rate):' in line:
        lines[i] = 'def analyze_rhythmic_cadence(chirp_peaks_list, rate):\n'
    if 'if not chirp_peaks_list or len(chirp_peaks_list) < 3:' in line:
        # Check its indentation
        ind = len(line) - len(line.lstrip())
        if ind != 4:
            lines[i] = '    if not chirp_peaks_list or len(chirp_peaks_list) < 3:\n'

# Well, let's just do it simple:
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
