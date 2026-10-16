"""
Crinômetro - Worker Thread para Processamento Assíncrono.
"""
import threading
from PyQt6.QtCore import QThread, pyqtSignal

class GenericWorker(QThread):
    """Executa tarefas computacionalmente intensas em background sem travar a interface gráfica."""
    finished_signal = pyqtSignal(object)
    cancelled_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)   # (current, total) para lote
    result_ready_signal = pyqtSignal(str, object) # (filename, result_payload)

    def __init__(self, target_fn, *args, **kwargs):
        super().__init__()
        self.target_fn = target_fn
        self.args = args
        self.kwargs = kwargs
        self._abort_event = threading.Event()

    # ------------------------------------------------------------------ #
    # API pública                                                          #
    # ------------------------------------------------------------------ #
    def abort(self):
        """Solicita cancelamento cooperativo da tarefa em andamento."""
        self._abort_event.set()

    @property
    def abort_requested(self) -> bool:
        """Permite que a função-alvo consulte se o cancelamento foi pedido."""
        return self._abort_event.is_set()

    def run(self):
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

class WorkerRegistry:
    def __init__(self):
        self._workers = []
        self._lock = threading.Lock()
        
    def retain(self, worker):
        with self._lock:
            if worker not in self._workers:
                self._workers.append(worker)
        worker.finished.connect(lambda: self._remove(worker))
        
    def _remove(self, worker):
        with self._lock:
            if worker in self._workers:
                self._workers.remove(worker)
            
    def abort_all(self):
        with self._lock:
            snapshot = list(self._workers)
        for w in snapshot:
            if w.isRunning():
                w.abort()
                
    def wait_all(self, timeout_ms=3000):
        import time
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        with self._lock:
            snapshot = list(self._workers)
        for w in snapshot:
            if w.isRunning():
                rem_ms = max(50, int((deadline - time.monotonic()) * 1000))
                w.wait(rem_ms)
                
    def count(self):
        with self._lock:
            snapshot = list(self._workers)
        return len([w for w in snapshot if w.isRunning()])
    
    def shutdown(self, timeout_ms=3000):
        self.abort_all()
        self.wait_all(timeout_ms)
