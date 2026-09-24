from PyQt6.QtCore import QObject, pyqtSignal

class SessionContext(QObject):
    """
    Fonte da Verdade (Source of Truth) para o estado compartilhado da aplicação.
    Emite state_changed(category) sempre que uma propriedade gerenciada é atribuída.
    """
    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado Analítico / Heavy Data
        self._active_heavy_data = {}
        self._analysis_cache = {}
        self._algo_params = {}
        self.__adaptive_overrides = {}
        
        # Estado de Navegação / Seleção
        self._active_filename = None
        self._loaded_files = {}
        
        # Estado de Edição / ML
        self._peaks_detected = []
        self._peaks_user_verified = []
        self._corrections_by_file = {}
        self._pulse_learner = None
        self._use_machine_learning = False
        self._pulse_metadata = {}
        
        # Estado de Relatório / Exportação
        self._report_params = {
            "lang": "pt",
            "institution": "",
            "researcher_name": "",
            "role": "",
            "level": ""
        }

    def emit_state_changed(self, category: str):
        """Dispara o sinal informando que uma fatia do estado foi atualizada."""
        self.state_changed.emit(category)

    # --- Properties com emissão automática de state_changed ---

    @property
    def active_heavy_data(self):
        return self._active_heavy_data
    @active_heavy_data.setter
    def active_heavy_data(self, val):
        self._active_heavy_data = val
        self.emit_state_changed("active_heavy_data")

    @property
    def analysis_cache(self):
        return self._analysis_cache
    @analysis_cache.setter
    def analysis_cache(self, val):
        self._analysis_cache = val
        self.emit_state_changed("analysis_cache")

    @property
    def algo_params(self):
        return self._algo_params
    @algo_params.setter
    def algo_params(self, val):
        self._algo_params = val
        self.emit_state_changed("algo_params")

    @property
    def _adaptive_overrides(self):
        return self.__adaptive_overrides
    @_adaptive_overrides.setter
    def _adaptive_overrides(self, val):
        self.__adaptive_overrides = val
        self.emit_state_changed("_adaptive_overrides")

    @property
    def active_filename(self):
        return self._active_filename
    @active_filename.setter
    def active_filename(self, val):
        self._active_filename = val
        self.emit_state_changed("active_filename")

    @property
    def loaded_files(self):
        return self._loaded_files
    @loaded_files.setter
    def loaded_files(self, val):
        self._loaded_files = val
        self.emit_state_changed("loaded_files")

    @property
    def peaks_detected(self):
        return self._peaks_detected
    @peaks_detected.setter
    def peaks_detected(self, val):
        self._peaks_detected = val
        self.emit_state_changed("peaks_detected")

    @property
    def peaks_user_verified(self):
        return self._peaks_user_verified
    @peaks_user_verified.setter
    def peaks_user_verified(self, val):
        self._peaks_user_verified = val
        self.emit_state_changed("peaks_user_verified")

    @property
    def corrections_by_file(self):
        return self._corrections_by_file
    @corrections_by_file.setter
    def corrections_by_file(self, val):
        self._corrections_by_file = val
        self.emit_state_changed("corrections_by_file")

    @property
    def pulse_learner(self):
        return self._pulse_learner
    @pulse_learner.setter
    def pulse_learner(self, val):
        self._pulse_learner = val
        self.emit_state_changed("pulse_learner")

    @property
    def use_machine_learning(self):
        return self._use_machine_learning
    @use_machine_learning.setter
    def use_machine_learning(self, val):
        self._use_machine_learning = bool(val)
        self.emit_state_changed("use_machine_learning")

    @property
    def pulse_metadata(self):
        return self._pulse_metadata
    @pulse_metadata.setter
    def pulse_metadata(self, val):
        self._pulse_metadata = val
        self.emit_state_changed("pulse_metadata")

    @property
    def report_params(self):
        return self._report_params
    @report_params.setter
    def report_params(self, val):
        self._report_params = val
        self.emit_state_changed("report_params")

    def activate_cached_file(self, filename: str) -> bool:
        """Ativa atomicamente no SessionContext todo o estado associado a um arquivo em cache.

        Atualiza de forma consistente:
        - active_filename
        - active_heavy_data
        - peaks_detected
        - peaks_user_verified
        - pulse_metadata
        """
        if not filename or filename not in self._analysis_cache:
            return False

        d = self._analysis_cache[filename]
        self._active_filename = filename
        self._active_heavy_data = d
        self._peaks_detected = list(d.get("peaks_detected", []))

        # Sincroniza peaks_user_verified e pulse_metadata:
        # Prioriza correções armazenadas em corrections_by_file se existirem, senão extrai do cache
        stored_corr = self._corrections_by_file.get(filename)
        if stored_corr is not None:
            extracted = []
            extracted_meta = {}
            for item in stored_corr:
                if isinstance(item, dict):
                    extracted.append(item["idx"])
                    extracted_meta[item["idx"]] = item
                else:
                    extracted.append(int(item))
            self._peaks_user_verified = extracted
            self._pulse_metadata = extracted_meta
        else:
            self._peaks_user_verified = list(d.get("peaks_user_verified", self._peaks_detected))
            self._pulse_metadata = dict(d.get("pulse_metadata", {}))

        self.emit_state_changed("active_filename")
        self.emit_state_changed("active_heavy_data")
        self.emit_state_changed("peaks_detected")
        self.emit_state_changed("peaks_user_verified")
        self.emit_state_changed("pulse_metadata")
        return True

