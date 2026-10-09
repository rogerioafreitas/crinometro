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
        
        from core.session_context import SessionContext
        ctx = SessionContext()
        dlg = ExportReportDialog(ctx)
        # Preencher os campos minimos
        dlg.txt_temp.setText("25")
        
        # Simular clique em aceitar
        dlg.chk_fmt_csv.setChecked(False)
        dlg.chk_fmt_txt.setChecked(False)
        dlg.chk_fmt_pdf.setChecked(True)
        from unittest.mock import patch
        with patch('ui.dialogs.export_report_dialog.QFileDialog.getSaveFileName', return_value=('dummy.pdf', '')):
            dlg._on_export()
        
        self.assertIsNotNone(dlg.config)
        self.assertIsInstance(dlg.config, ReportConfig)

if __name__ == '__main__':
    unittest.main()
