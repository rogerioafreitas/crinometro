# coding: utf-8
"""
tests/test_report_customizations.py
-----------------------------------
Verifica as customizações cirúrgicas solicitadas no relatório e diálogo:
1. "Média IPI (ms)" no lugar de "Gap Médio (ms)" na listagem de chilreios.
2. Remoção do sufixo (Completo)/(Simplificado) do título do relatório.
3. Remoção de campos não informados, retirada permanente de Localidade e de Cód. Espécime do cabeçalho.
4. Remoção de Localidade do ExportReportDialog e de _build_meta.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.report_generator import (
    _build_metadata_rows,
    
    ReportConfig,
    ReportSectionFlags,
    generate_pdf_report
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph


class TestReportCustomizations(unittest.TestCase):
    def setUp(self):
        self.body_style = ParagraphStyle('DocBody', fontName='Helvetica', fontSize=9)
        self.bold_style = ParagraphStyle('DocBold', fontName='Helvetica-Bold', fontSize=9)

    def test_build_metadata_rows_omits_uninformed_and_omits_location_and_specimen(self):
        """Header table must NOT contain empty or 'não informado' fields,

        must NOT contain 'Localidade', and must NOT contain 'Cód. Espécime'."""
        report_params = {
            "institution": "Não informada",
            "researcher_name": "",
            "location": "São Paulo",  # should be ignored completely
            "temperature": "24 °C",
            "equipment": "Gravador Sony PCM-D100",
            "file_meta": {
                "audio1.wav": {"species": "Gryllus assimilis", "specimen": "m01"}
            }
        }
        selected_cache = {"audio1.wav": {}}
        rows = _build_metadata_rows(report_params, selected_cache, self.body_style, self.bold_style)

        # Collect all rendered text from all table cells
        cell_texts = []
        for row in rows:
            for cell in row:
                if isinstance(cell, Paragraph):
                    cell_texts.append(cell.text)

        joined = " ".join(cell_texts)

        # Deve conter os preenchidos
        self.assertIn("Gryllus assimilis", joined)
        self.assertIn("24 °C", joined)
        self.assertIn("Gravador Sony PCM-D100", joined)
        self.assertIn("1 arquivo(s)", joined)
        self.assertIn("Data da Análise", joined)

        # NÃO deve conter 'Não informada', 'Instituição', 'Pesquisador(a)', 'Localidade', nem 'Cód. Espécime'
        self.assertNotIn("Não informada", joined)
        self.assertNotIn("Não informado", joined)
        self.assertNotIn("Instituição", joined)
        self.assertNotIn("Pesquisador(a)", joined)
        self.assertNotIn("Localidade", joined)
        self.assertNotIn("Cód. Espécime", joined)

    def test_build_metadata_rows_completely_empty(self):
        """Quando o usuário não preenche nada, deve conter apenas Áudios Compilados e Data da Análise."""
        report_params = {}
        selected_cache = {"a.wav": {}, "b.wav": {}}
        rows = _build_metadata_rows(report_params, selected_cache, self.body_style, self.bold_style)

        cell_texts = []
        for row in rows:
            for cell in row:
                if isinstance(cell, Paragraph):
                    cell_texts.append(cell.text)
        joined = " ".join(cell_texts)

        self.assertIn("2 arquivo(s)", joined)
        self.assertIn("Data da Análise", joined)
        self.assertNotIn("Espécie", joined)
        self.assertNotIn("Localidade", joined)
        self.assertNotIn("Cód. Espécime", joined)

    def test_export_report_dialog_no_location(self):
        """ExportReportDialog must not have txt_location or location in _build_meta."""
        from PyQt6.QtWidgets import QApplication
        from ui.dialogs.export_report_dialog import ExportReportDialog

        app = QApplication.instance() or QApplication([])
        dummy_ctx = MagicMock()
        dummy_ctx.report_params = {}
        dlg = ExportReportDialog(dummy_ctx, checked_files=["audio1.wav"])

        self.assertFalse(hasattr(dlg, "txt_location"))
        self.assertFalse(hasattr(dlg, "chk_graficos"))
        meta = dlg._build_meta()
        self.assertNotIn("location", meta)


if __name__ == "__main__":
    unittest.main()
