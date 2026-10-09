filepath = 'ui/controllers/pipeline_orchestrator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

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
"""

# Just append to the end of the file, assuming PipelineOrchestrator is the last class.
# Wait, let's make sure it's indented correctly.
with open(filepath, 'a', encoding='utf-8') as f:
    f.write(methods)
