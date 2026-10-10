import unittest
import numpy as np
import os
import tempfile
import hashlib
from utils.report_generator import ReportConfig, ReportSectionFlags, generate_txt_report

class TestCharacterizationReport(unittest.TestCase):
    def test_report_hashes(self):
        flags = ReportSectionFlags(resumo=True, metricas=True, cadencia=False, lista_pulsos=False)
        config = ReportConfig(metadata={}, section_flags=flags)
        
        dummy_result = {
            "pulse_peaks": np.array([1000, 2000]),
            "chirp_start_indices": [0],
            "pulse_durations": [0.01, 0.01],
            "pulse_intervals": [0.01],
            "chirp_durations": [0.1],
            "chirp_intervals": [],
            "avg_pulse_rate": 10.0,
            "avg_chirp_rate": 1.0,
            "signal_duration": 1.0,
            "env": np.ones(5000),
            "Pxx": np.ones((10,10)),
            "freqs": np.ones(10),
            "bins": np.ones(10)
        }
        
        analysis_cache = {"fake_file.wav": dummy_result}
        
        with tempfile.TemporaryDirectory() as td:
            txt_path = os.path.join(td, "report.txt")
            generate_txt_report(txt_path, analysis_cache, config.metadata)
            
            with open(txt_path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
                
            self.assertTrue(len(h) == 64)

if __name__ == '__main__':
    unittest.main()
