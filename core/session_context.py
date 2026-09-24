from PyQt6.QtCore import QObject, pyqtSignal

class SessionContext(QObject):
    """
    Fonte (Source of Truth) para o estado compartilhado da aplicação.
    """
    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado Analítico / Heavy Data
        self.active_heavy_data = None
        self.analysis_cache = {}
        self.algo_params = {}
        self._adaptive_overrides = {}
        
        # Estado de Navegação / Seleção
        self.active_filename = None
        self.loaded_files = {}
        
        # Estado de Edição / ML
        self.peaks_detected = []
        self.peaks_user_verified = []
        self.corrections_by_file = {}
        self.pulse_learner = None
        
        # Estado de Relatório / Exportação
        self.report_params = {
            "lang": "pt",
            "institution": "",
            "researcher_name": "",
            "role": "",
            "level": ""
        }

    def emit_state_changed(self, category: str):
        """Dispara o sinal informando que uma fatia do estado foi atualizada."""
        self.state_changed.emit(category)
