import os
import sys
import tempfile
import unittest
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

app = QApplication.instance() or QApplication(sys.argv)

class TestExportControllerR3(unittest.TestCase):
    def test_export_controller_generate_pdf(self):
        from ui.controllers.export_controller import ExportController
        from utils.report_generator import ReportConfig, ReportSectionFlags, generate_pdf_report, generate_txt_report
        from core.analyzer import CricketAnalyzer
        from core.session_context import SessionContext
        from unittest.mock import MagicMock
        
        ctx = SessionContext()
        pipeline = MagicMock()
        main_window = MagicMock()
        main_window.lang = 'pt'
        ctrl = ExportController(ctx, pipeline, main_window)
        
        flags = ReportSectionFlags(resumo=True, metricas=True, cadencia=False, lista_pulsos=False)
        config = ReportConfig(metadata={}, section_flags=flags)
        
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "report.pdf")
            txt_path = os.path.join(td, "report.txt")
            
            # create mock cache
            class DummyResult:
                pulse_peaks = np.array([1000, 2000])
                chirp_start_indices = [0]
                pulse_durations = [0.01, 0.01]
                pulse_intervals = [0.01]
                chirp_durations = [0.1]
                chirp_intervals = []
                avg_pulse_rate = 10.0
                avg_chirp_rate = 1.0
                signal_duration = 1.0
                env = np.ones(5000)
            
            ctx.analysis_cache = {"fake_file.wav": DummyResult()}
            ctx.files = ["fake_file.wav"]
            ctx.sample_rates = {"fake_file.wav": 16000}
            
            ctrl._generate_pdf_report_modular(pdf_path, txt_path, config, None)
            
            # wait for it to finish
            QTest.qWait(2000)
            
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(os.path.exists(txt_path))
            
            # verify direct output match
            pdf_path2 = os.path.join(td, "report2.pdf")
            txt_path2 = os.path.join(td, "report2.txt")
            generate_pdf_report(pdf_path2, ctx.analysis_cache, ctx.files, ctx.sample_rates, config, None)
            generate_txt_report(txt_path2, ctx.analysis_cache, ctx.files, ctx.sample_rates, config, None)
            
            # just assert sizes are non zero
            self.assertGreater(os.path.getsize(pdf_path), 0)
            self.assertGreater(os.path.getsize(txt_path), 0)

if __name__ == '__main__':
    unittest.main()
