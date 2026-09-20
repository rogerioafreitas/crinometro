# -*- coding: utf-8 -*-
from PyQt6.QtCore import QObject, pyqtSignal

class SessionContext(QObject):
    '''
    Coração dos Dados (State).
    Gerencia de forma isolada os parâmetros, dados brutos e estado da interface.
    Emite sinais para a UI atualizar quando propriedades críticas mudarem.
    '''
    data_loaded = pyqtSignal(str) # Emitido quando um novo áudio termina de carregar
    state_changed = pyqtSignal(str) # Emitido quando o estado interno muda (ex: 'peaks')
    params_updated = pyqtSignal() # Emitido quando algo_params mudam

    def __init__(self):
        super().__init__()
        from utils.constants import DEFAULT_ALGO_PARAMS
        self.algo_params = DEFAULT_ALGO_PARAMS.copy()
        self._adaptive_overrides = {}
        
        self.active_heavy_data = None
        self.analysis_cache = {}
        
        self.peaks_detected = []
        self.peaks_user_verified = []
        self.corrections_by_file = {}
        self.pulse_metadata = {}
        
        self.active_filename = None
        self._pulse_edit_history = []
        
        # O PulseLearner pode ser injetado aqui via import, ou passado no init
        # Vamos inicializar depois ou passar pelo config para evitar imports circulares?
        self.pulse_learner = None
        
        # O report_params continuará sendo parte do contexto, afinal é config global
        self.report_params = {"lang": "pt", "institution": "", "researcher_name": "", "role": "", "level": ""}

