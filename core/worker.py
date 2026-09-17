"""
Crinômetro - Worker Thread para Processamento Assíncrono.
"""
import threading
from PyQt6.QtCore import QThread, pyqtSignal

class GenericWorker(QThread):
    """Executa tarefas computacionalmente intensas em background sem travar a interface gráfica."""
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)   # (current, total) para lote

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
        except Exception as exc:
            if not self._abort_event.is_set():
                self.error_signal.emit(str(exc))
