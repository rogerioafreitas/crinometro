"""
Crinômetro - Worker Thread para Processamento Assíncrono.
"""
from PyQt6.QtCore import QThread, pyqtSignal

class GenericWorker(QThread):
    """Executa tarefas computacionalmente intensas em background sem travar a interface gráfica."""
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, target_fn, *args, **kwargs):
        super().__init__()
        self.target_fn = target_fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.target_fn(*self.args, **self.kwargs)
            self.finished_signal.emit(res)
        except Exception as exc:
            self.error_signal.emit(str(exc))


