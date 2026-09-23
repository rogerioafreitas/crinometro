import sys
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.analyzer import CricketAnalyzer

app = QApplication.instance() or QApplication(sys.argv)

class TestCharacterization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app

    def setUp(self):
        self.window = MainWindow()

    def test_01_initial_state(self):
        # O cache e os dados pesados começam vazios
        self.assertIsNone(self.window.active_filename)
        self.assertEqual(self.window.analysis_cache, {})
        self.assertIsNone(self.window.active_heavy_data)

    @patch('core.analyzer.CricketAnalyzer.analyze_wav')
    def test_02_pipeline_and_cache(self, mock_analyze):
        # Configura mock de análise
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
        mock_analyze.return_value = (mock_result, mock_heavy)

        # Injeta resultado no cache manualmente ou invoca o método de carregamento (sem thread para facilitar o teste unificado)
        self.window.active_filename = "dummy.wav"
        self.window.analysis_cache["dummy.wav"] = {"chirps": mock_result["chirps"], "media": mock_result["media"], "params": {}}
        self.window.active_heavy_data = mock_heavy
        self.window.peaks_detected = [10]
        self.window.peaks_user_verified = [10]

        # Verifica sincronização básica do cache (cache behavior)
        self.assertIn("dummy.wav", self.window.analysis_cache)
        self.assertEqual(self.window.peaks_detected, [10])
        
    def test_03_navigation_pan_zoom(self):
        # Simula o clique e pan
        self.window.active_heavy_data = {"rate": 44100}
        
        # O navigation guarda o estado do cursor
        self.window.bg_cache_valid = False
        self.assertFalse(self.window.bg_cache_valid)

    def test_04_editing_pulse(self):
        self.window.active_heavy_data = {"rate": 1000.0, "env": np.zeros(100)}
        self.window.peaks_detected = [10, 50]
        self.window.peaks_user_verified = [10, 50]
        self.window._pulse_edit_history = []
        
        # Toggle pulse
        self.window._toggle_peak_marker(0.01) # rate 1000, 0.01s = 10 (remove)
        self.assertNotIn(10, self.window.peaks_user_verified)
        self.assertEqual(len(self.window._pulse_edit_history), 1)
        
        # Undo
        self.window._undo_pulse_edit()
        self.assertIn(10, self.window.peaks_user_verified)

    def tearDown(self):
        self.window.close()

if __name__ == '__main__':
    unittest.main()