import os
import sys
import tempfile
import unittest
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

class TestExportControllerR3(unittest.TestCase):
    def test_export_controller_generate_pdf(self):
        from utils.report_generator import ReportConfig, ReportSectionFlags, generate_pdf_report, generate_txt_report
        from core.session_context import SessionContext
        
        ctx = SessionContext()
        flags = ReportSectionFlags(resumo=True, metricas=True, cadencia=False, lista_pulsos=False)
        config = ReportConfig(metadata={}, section_flags=flags)
        
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "report.pdf")
            txt_path = os.path.join(td, "report.txt")
            
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
            
            ctx.analysis_cache = {"fake_file.wav": dummy_result}
            ctx.files = ["fake_file.wav"]
            ctx.sample_rates = {"fake_file.wav": 16000}
            
            generate_pdf_report(pdf_path, config, ctx.analysis_cache)
            generate_txt_report(txt_path, ctx.analysis_cache, config.metadata)
            
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(os.path.exists(txt_path))

if __name__ == '__main__':
    unittest.main()
