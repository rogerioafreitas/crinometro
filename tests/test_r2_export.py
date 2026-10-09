import os
import sys
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

class TestExportDialogR2(unittest.TestCase):
    def test_export_report_dialog_config(self):
        from ui.dialogs.export_report_dialog import ExportReportDialog
        from utils.report_generator import ReportConfig
        
        dlg = ExportReportDialog()
        # Preencher os campos minimos
        dlg.txt_specimen.setText("Test")
        
        # Simular clique em aceitar
        dlg.accept()
        
        self.assertIsNotNone(dlg.config)
        self.assertIsInstance(dlg.config, ReportConfig)

if __name__ == '__main__':
    unittest.main()
