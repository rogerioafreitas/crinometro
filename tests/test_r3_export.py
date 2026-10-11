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
        from ui.controllers.export_controller import ExportController
        from utils.report_generator import ReportConfig, ReportSectionFlags
        from core.session_context import SessionContext
        from PyQt6.QtCore import QObject, pyqtSignal
        
        class FakePipe(QObject):
            batch_completed = pyqtSignal(int, list)
            batch_failed = pyqtSignal(str)
            batch_cancelled = pyqtSignal()
        pipe = FakePipe()
        
        class FakeMainWindow(QObject):
            lang = 'pt'
        fake_mw = FakeMainWindow()
        
        ctx = SessionContext()
        flags = ReportSectionFlags(resumo=True, metricas=True, cadencia=False, lista_pulsos=False)
        config = ReportConfig(metadata={}, section_flags=flags, output_path=None)
        
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "report.pdf")
            config.output_path = pdf_path
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
            
            ctrl = ExportController(ctx, pipe, fake_mw)
            ctrl._generate_pdf_report_modular(["fake_file.wav"], config, want_txt=True, txt_path=txt_path)
            
            # Since it starts a worker, we must wait
            if ctrl._report_worker:
                ctrl._report_worker.run()
            
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(os.path.exists(txt_path))


    def test_export_controller_connects_pipeline_signals(self):
        from PyQt6.QtCore import QObject, pyqtSignal
        class FakePipe(QObject):
            batch_completed = pyqtSignal(int, list)
            batch_failed = pyqtSignal(str)
            batch_cancelled = pyqtSignal()
        pipe = FakePipe()
        
        class FakeMainWindow(QObject):
            lang = 'pt'
        fake_mw = FakeMainWindow()
        
        from ui.controllers.export_controller import ExportController
        ExportController(None, pipe, fake_mw)
        for sig in ('batch_completed', 'batch_failed', 'batch_cancelled'):
            self.assertGreater(pipe.receivers(getattr(pipe, sig)), 0, sig)

if __name__ == '__main__':
    unittest.main()
