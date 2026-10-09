from contextlib import contextmanager
from PyQt6.QtCore import QObject, pyqtSignal

class SessionContext(QObject):
    """
    Fonte da Verdade (Source of Truth) para o estado compartilhado da aplicação.
    Emite state_changed(category) sempre que uma propriedade gerenciada é atribuída.
    Suporta transações atômicas via batch_update() para evitar emissão de estados parciais.
    """
    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Controle de transação/batch para atualizações atômicas
        self._batch_depth = 0
        self._pending_state_changes = set()

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
        """Dispara o sinal informando que uma fatia do estado foi atualizada,
        ou adia a emissão se estiver dentro de uma transação batch_update()."""
        if getattr(self, "_batch_depth", 0) > 0:
            self._pending_state_changes.add(category)
            return
        self.state_changed.emit(category)

    @contextmanager
    def batch_update(self):
        """Gerenciador de contexto para atualizações transacionais atômicas.
        Adia a emissão de sinais state_changed até que todas as atribuições
        sejam concluídas, emitindo os sinais consolidados apenas no final."""
        self._batch_depth = getattr(self, "_batch_depth", 0) + 1
        try:
            yield self
        except Exception:
            # Não limpar _pending_state_changes, para que finally emita as mudanças parciais
            raise
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._pending_state_changes:
                pending = sorted(self._pending_state_changes)
                self._pending_state_changes.clear()
                for cat in pending:
                    self.state_changed.emit(cat)

    transaction = batch_update  # Alias semântico

    def update_verified_and_metadata(self, peaks_user_verified, pulse_metadata):
        """Atualiza atomicamente peaks_user_verified e pulse_metadata,
        garantindo que nenhum observador veja estado parcial ou dessincronizado."""
        with self.batch_update():
            self.peaks_user_verified = list(peaks_user_verified)
            self.pulse_metadata = dict(pulse_metadata)

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

        Atualiza de forma transacional e consistente:
        - active_filename
        - active_heavy_data
        - peaks_detected
        - peaks_user_verified
        - pulse_metadata
        """
        if not filename or filename not in self._analysis_cache:
            return False

        d = self._analysis_cache[filename]
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
            verified_target = extracted
            meta_target = extracted_meta
        else:
            verified_target = list(d.get("peaks_user_verified", d.get("peaks_detected", [])))
            meta_target = dict(d.get("pulse_metadata", {}))

        with self.batch_update():
            self.active_filename = filename
            self.active_heavy_data = d
            self.peaks_detected = list(d.get("peaks_detected", []))
            self.peaks_user_verified = verified_target
            self.pulse_metadata = meta_target

        return True

