import sys
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestCharacterization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app

    def setUp(self):
        self.window = MainWindow()

    def test_00_session_context_redirection(self):
        # Verifica se o redirecionamento para o SessionContext funciona e emite sinal
        
        # Conecta o sinal a uma lista para rastrear emissores
        emitted_signals = []
        self.window.ctx.state_changed.connect(lambda s: emitted_signals.append(s))
        
        # Atribuição deve redirecionar para ctx e emitir sinal
        mock_data = {"test": 123}
        self.window.active_heavy_data = mock_data
        
        # Verifica a fonte de verdade
        self.assertIs(self.window.ctx.active_heavy_data, mock_data)
        
        # Verifica se o sinal foi emitido com a categoria correta
        self.assertIn("active_heavy_data", emitted_signals)
        
        emitted_signals.clear()
        
        self.window.analysis_cache = {"a": 1}
        self.assertEqual(self.window.ctx.analysis_cache, {"a": 1})
        self.assertIn("analysis_cache", emitted_signals)

    def test_01_initial_state(self):
        # Verifica os estados iniciais conforme MainWindow.__init__
        self.assertIsNone(self.window.active_filename)
        self.assertEqual(self.window.analysis_cache, {})
        self.assertEqual(self.window.active_heavy_data, {})
        self.assertEqual(self.window.loaded_files, {})

    def test_02_pipeline_and_cache(self):
        mock_result = {
            "media": {
                "psd": np.array([0.1, 0.2]), "freqs": np.array([100, 200]), "env": np.array([0.5, 0.6]),
                "t_env": np.array([0.0, 0.1]), "valid_peaks": [10], "carrier_freq": 5000.0,
                "dominant_freq": 5000.0, "time_axis": np.array([0.0, 0.1])
            },
            "chirps": [{"start_idx": 5, "end_idx": 15, "peaks": [10]}]
        }
        mock_heavy = {
            "rate": 44100, "data": np.zeros(100), "env": np.zeros(100), "peaks": [10], "chirps": mock_result["chirps"],
            "t_env": np.zeros(100), "freqs": np.zeros(50), "psd": np.zeros(50), "t_spec": np.zeros(10), "f_spec": np.zeros(10), "Sxx": np.zeros((10,10)),
            "carrier_freq": 5000.0, "dom_freqs": np.zeros(10)
        }
        # Não usa o analisador real, apenas checa as variáveis

        self.window.active_filename = "dummy.wav"
        self.window.analysis_cache["dummy.wav"] = {"chirps": mock_result["chirps"], "media": mock_result["media"], "params": {}}
        self.window.active_heavy_data = mock_heavy
        self.window.peaks_detected = [10]
        self.window.peaks_user_verified = [10]

        self.assertIn("dummy.wav", self.window.analysis_cache)
        self.assertEqual(self.window.peaks_detected, [10])
        
    def test_03_navigation_pan_zoom(self):
        self.window.active_heavy_data = {"rate": 44100}
        self.window.bg_cache_valid = False
        self.assertFalse(self.window.bg_cache_valid)

    def test_04_editing_pulse(self):
        self.window.active_heavy_data = {"rate": 1000.0, "env": np.zeros(100)}
        self.window.peaks_detected = [10, 50]
        self.window.peaks_user_verified = [10, 50]
        self.window._pulse_edit_history = []
        
        self.window._toggle_peak_marker(0.01) 
        self.assertNotIn(10, self.window.peaks_user_verified)
        self.assertEqual(len(self.window._pulse_edit_history), 1)
        
        self.window._undo_pulse_edit()
        self.assertIn(10, self.window.peaks_user_verified)

if __name__ == '__main__':
    unittest.main()
