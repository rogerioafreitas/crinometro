import unittest
from PyQt6.QtWidgets import QApplication, QWidget
from utils.i18n import I18N, plain
from ui.figure_factory import ExportConfig, get_panel_title
from core.session_context import SessionContext
from ui.dialogs.export_report_dialog import ExportReportDialog
from ui.dialogs.export_graph_dialog import ExportGraphDialog

app = QApplication.instance()
if app is None:
    app = QApplication([])


class TestI18nCoverage(unittest.TestCase):
    def test_01_dictionary_parity(self):
        """Comprova paridade exata de 100% das chaves entre PT e EN no I18N."""
        pt_keys = set(I18N["pt"].keys())
        en_keys = set(I18N["en"].keys())
        diff_pt = pt_keys - en_keys
        diff_en = en_keys - pt_keys
        self.assertEqual(diff_pt, set(), f"Chaves presentes apenas em PT: {diff_pt}")
        self.assertEqual(diff_en, set(), f"Chaves presentes apenas em EN: {diff_en}")
        self.assertGreaterEqual(len(pt_keys), 200)

    def test_02_plain_helper(self):
        """Comprova que plain() extrai o texto limpo sem quebrar em emojis."""
        self.assertEqual(plain("pt", "files"), "Arquivos")
        self.assertEqual(plain("en", "files"), "Files")
        self.assertEqual(plain("pt", "reanalyze"), "Reanalisar")
        self.assertEqual(plain("en", "reanalyze"), "Reanalyze")

    def test_03_main_window_refresh_dynamic_language_switch(self):
        """Comprova alternância instantânea de idioma na MainWindow sem exceções."""
        from ui.main_window import MainWindow
        win = MainWindow()
        try:
            # Alterna para inglês
            win.lang = "en"
            win.refresh_ui_texts()
            self.assertEqual(win.lbl_metric_title.text(), I18N["en"]["total_chirps"])
            self.assertEqual(win.theme_label.text(), I18N["en"]["theme"])
            self.assertEqual(win.lbl_eyebrow.text(), I18N["en"]["file_in_analysis"])
            self.assertEqual(win.btn_analyze_selected.text(), I18N["en"]["analyze_selected"])
            self.assertEqual(win.btn_export_main.text(), I18N["en"]["export_menu"])
            self.assertEqual(win.lbl_summary_file.text(), I18N["en"]["no_file_selected"])
            self.assertEqual(win.btn_toggle_ml.text(), I18N["en"]["ml_disabled"])

            # Alterna de volta para português
            win.lang = "pt"
            win.refresh_ui_texts()
            self.assertEqual(win.lbl_metric_title.text(), I18N["pt"]["total_chirps"])
            self.assertEqual(win.theme_label.text(), I18N["pt"]["theme"])
            self.assertEqual(win.lbl_eyebrow.text(), I18N["pt"]["file_in_analysis"])
            self.assertEqual(win.btn_analyze_selected.text(), I18N["pt"]["analyze_selected"])
            self.assertEqual(win.btn_export_main.text(), I18N["pt"]["export_menu"])
            self.assertEqual(win.lbl_summary_file.text(), I18N["pt"]["no_file_selected"])
            self.assertEqual(win.btn_toggle_ml.text(), I18N["pt"]["ml_disabled"])
        finally:
            win.close()

    def test_04_figure_factory_language_awareness(self):
        """Comprova que o figure_factory respeita os idiomas PT e EN."""
        cfg_pt = ExportConfig(lang="pt")
        cfg_en = ExportConfig(lang="en")

        self.assertEqual(get_panel_title("waveform", "pt"), "Oscilograma")
        self.assertEqual(get_panel_title("waveform", "en"), "Oscillogram")
        self.assertEqual(get_panel_title("psd", "pt"), "Espectro de Potência (PSD)")
        self.assertEqual(get_panel_title("psd", "en"), "Power Spectral Density (PSD)")
        self.assertEqual(get_panel_title("spectrogram", "pt"), "Espectrograma")
        self.assertEqual(get_panel_title("spectrogram", "en"), "Spectrogram")
        self.assertEqual(get_panel_title("histogram", "pt"), "Histograma de Chilreios")
        self.assertEqual(get_panel_title("histogram", "en"), "Chirp Histogram")

    def test_05_export_dialogs_instantiation_pt_and_en(self):
        """Comprova que ExportReportDialog e ExportGraphDialog instanciam em PT e EN sem NameError."""
        ctx = SessionContext()

        # Dummy parent widgets with lang attribute
        parent_pt = QWidget()
        parent_pt.lang = "pt"
        parent_en = QWidget()
        parent_en.lang = "en"

        # 1. ExportReportDialog em PT
        dlg_report_pt = ExportReportDialog(ctx, checked_files=["audio1.wav"], parent=parent_pt)
        self.assertEqual(dlg_report_pt.windowTitle(), I18N["pt"]["export_report_title"])
        self.assertEqual(dlg_report_pt.btn_export.text(), I18N["pt"]["btn_generate_report"])

        # 2. ExportReportDialog em EN
        dlg_report_en = ExportReportDialog(ctx, checked_files=["audio1.wav"], parent=parent_en)
        self.assertEqual(dlg_report_en.windowTitle(), I18N["en"]["export_report_title"])
        self.assertEqual(dlg_report_en.btn_export.text(), I18N["en"]["btn_generate_report"])

        # 3. ExportGraphDialog em PT
        dlg_graph_pt = ExportGraphDialog(ctx, live_view={}, parent=parent_pt)
        self.assertEqual(dlg_graph_pt.windowTitle(), I18N["pt"]["export_graphs_dialog_title"])
        self.assertEqual(dlg_graph_pt._btn_export.text(), I18N["pt"]["btn_export_dialog"])

        # 4. ExportGraphDialog em EN
        dlg_graph_en = ExportGraphDialog(ctx, live_view={}, parent=parent_en)
        self.assertEqual(dlg_graph_en.windowTitle(), I18N["en"]["export_graphs_dialog_title"])
        self.assertEqual(dlg_graph_en._btn_export.text(), I18N["en"]["btn_export_dialog"])


if __name__ == "__main__":
    unittest.main()
