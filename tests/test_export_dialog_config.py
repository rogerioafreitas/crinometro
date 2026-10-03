# coding: utf-8
"""
tests/test_export_dialog_config.py
----------------------------------
Auditoria FASE 8/9/10 - cobre o caminho dialogo -> ExportConfig que os testes
anteriores nao exercitavam (escopo, unidade, fundo, snapshot, recorte no oscilograma).
"""
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QApplication, QWidget

from ui.figure_factory import ExportConfig, draw_waveform
from ui.dialogs import export_graph_dialog as egd
from ui.dialogs.export_graph_dialog import ExportGraphDialog, _SnapshotCtx

_app = QApplication.instance() or QApplication([])


class _Ctx:
    def __init__(self, carrier=4500.0, rate=44100.0):
        self.active_heavy_data = {
            "rate": rate,
            "carrier_freq": carrier,
            "params": {"freq_tolerance_hz": 700.0, "b1_min": 3200.0, "b1_max": 6000.0},
        }
        self.algo_params = {"freq_tolerance_hz": 700.0}
        self.active_filename = "a.wav"


class _Parent(QWidget):
    def __init__(self, mode="dark"):
        super().__init__()
        self.theme_mode = mode


def _dialog(ctx=None, live=None, mode="dark"):
    parent = _Parent(mode)
    dlg = ExportGraphDialog(ctx or _Ctx(), live_view=live, parent=parent)
    dlg._test_parent = parent  # mantem referencia viva
    return dlg


class TestScopeMapping(unittest.TestCase):
    def test_10k_khz(self):
        d = _dialog()
        d._cmb_scope.setCurrentText("10k")
        c = d._build_config()
        self.assertEqual((c.spec_ymin, c.spec_ymax), (0.0, 10.0))
        self.assertIsNone(c.spec_xmin)
        self.assertIsNone(c.spec_xmax)

    def test_10k_hz(self):
        d = _dialog()
        d._cmb_scope.setCurrentText("10k")
        d._cmb_unit.setCurrentText("Hz")
        c = d._build_config()
        self.assertEqual((c.spec_ymin, c.spec_ymax), (0.0, 10000.0))
        self.assertEqual(c.spec_unit, "Hz")

    def test_focal_usa_portadora_e_tolerancia(self):
        d = _dialog(_Ctx(carrier=4500.0))
        d._cmb_scope.setCurrentText("Focal")
        c = d._build_config()
        self.assertAlmostEqual(c.spec_ymin, 3.8)
        self.assertAlmostEqual(c.spec_ymax, 5.2)
        self.assertIsNone(c.spec_xmin)

    def test_focal_sem_portadora_usa_banda_b1(self):
        d = _dialog(_Ctx(carrier=0.0))
        d._cmb_scope.setCurrentText("Focal")
        c = d._build_config()
        self.assertAlmostEqual(c.spec_ymin, 3.2)
        self.assertAlmostEqual(c.spec_ymax, 6.0)

    def test_total_vai_ate_nyquist(self):
        d = _dialog(_Ctx(rate=44100.0))
        d._cmb_scope.setCurrentText("Total")
        c = d._build_config()
        self.assertEqual(c.spec_ymin, 0.0)
        self.assertAlmostEqual(c.spec_ymax, 22.05)

    def test_especifico_usa_vista_atual_em_khz(self):
        live = {"xlim": (1.0, 2.5), "ylim": (3.0, 7.0), "spec_unit": "kHz"}
        d = _dialog(live=live)
        d._cmb_scope.setCurrentText("Específico")
        c = d._build_config()
        self.assertEqual((c.spec_xmin, c.spec_xmax), (1.0, 2.5))
        self.assertAlmostEqual(c.spec_ymin, 3.0)
        self.assertAlmostEqual(c.spec_ymax, 7.0)

    def test_especifico_converte_unidade_da_vista(self):
        live = {"xlim": (0.0, 1.0), "ylim": (3000.0, 7000.0), "spec_unit": "Hz"}
        d = _dialog(live=live)
        d._cmb_scope.setCurrentText("Específico")
        d._cmb_unit.setCurrentText("kHz")
        c = d._build_config()
        self.assertAlmostEqual(c.spec_ymin, 3.0)
        self.assertAlmostEqual(c.spec_ymax, 7.0)

    def test_especifico_sem_vista_nao_quebra(self):
        d = _dialog(live={})
        d._cmb_scope.setCurrentText("Específico")
        c = d._build_config()
        self.assertIsNone(c.spec_xmin)
        self.assertEqual(c.spec_ymin, 0.0)


class TestBackgroundTheme(unittest.TestCase):
    def test_tema_atual_escuro(self):
        d = _dialog(mode="dark")
        d._cmb_bg.setCurrentIndex(1)
        self.assertEqual(d._build_config().bg_color, "#1E293B")

    def test_tema_atual_claro_nao_vira_escuro(self):
        d = _dialog(mode="light")
        d._cmb_bg.setCurrentIndex(1)
        self.assertEqual(d._build_config().bg_color, "#FFFFFF")

    def test_papel_sempre_branco(self):
        d = _dialog(mode="dark")
        d._cmb_bg.setCurrentIndex(0)
        self.assertEqual(d._build_config().bg_color, "#FFFFFF")


class TestDialogState(unittest.TestCase):
    def test_apply_x_e_propagado(self):
        d = _dialog()
        d._chk_apply_x.setChecked(False)
        self.assertFalse(d._build_config().wave_apply_xlim)
        d._chk_apply_x.setChecked(True)
        self.assertTrue(d._build_config().wave_apply_xlim)

    def test_limpar_nao_zera_subopcoes(self):
        d = _dialog()
        d._clear_all()
        self.assertTrue(d._chk_raw.isChecked())
        self.assertTrue(d._chk_env.isChecked())
        self.assertFalse(d._btn_export.isEnabled())
        d._chk_wave.setChecked(True)
        self.assertTrue(d._btn_export.isEnabled())

    def test_botoes_utilitarios_nao_sao_cta(self):
        d = _dialog()
        self.assertEqual(d._btn_mark_all.objectName(), "linkButton")
        self.assertEqual(d._btn_clear_all.objectName(), "linkButton")
        self.assertEqual(d._btn_export.objectName(), "primaryButton")

    def test_dpi_opcoes(self):
        d = _dialog()
        self.assertEqual(d._build_config().dpi, 300)  # padrao
        for idx, expected in enumerate((600, 300, 150, 72)):
            d._cmb_dpi.setCurrentIndex(idx)
            self.assertEqual(d._build_config().dpi, expected)

    def test_icones_qss_sao_arquivos_reais(self):
        import re
        from ui.dialogs.theme import get_dialog_theme
        for dark in (True, False):
            qss = get_dialog_theme(dark)
            self.assertNotIn("data:image", qss)
            paths = re.findall(r"url\(([^)]+)\)", qss)
            self.assertGreaterEqual(len(paths), 2)
            for p in paths:
                self.assertTrue(os.path.exists(p), p)

    def test_lista_do_combo_tem_estilo_nos_dois_temas(self):
        from ui.dialogs.theme import get_dialog_theme
        self.assertIn("QComboBox QAbstractItemView", get_dialog_theme(True))
        self.assertIn("#FFFFFF", get_dialog_theme(False))

    def test_worker_recebe_snapshot_isolado(self):
        ctx = _Ctx()
        d = _dialog(ctx)
        with mock.patch.object(egd.QFileDialog, "getSaveFileName", return_value=("x.pdf", "")), \
                mock.patch.object(egd, "_ExportWorker") as worker_cls:
            d._on_export()
        passed_ctx = worker_cls.call_args[0][1]
        self.assertIsInstance(passed_ctx, _SnapshotCtx)
        self.assertIsNot(passed_ctx, ctx)
        # mutar o contexto vivo nao altera o snapshot
        ctx.active_heavy_data["rate"] = 1.0
        self.assertEqual(passed_ctx.active_heavy_data["rate"], 44100.0)


class TestWaveformCrop(unittest.TestCase):
    def _xlim(self, apply_x):
        rate = 1000.0
        data = np.sin(np.linspace(0, 20, 5000))
        cfg = ExportConfig(spec_xmin=1.0, spec_xmax=2.0, wave_apply_xlim=apply_x)
        ax = Figure().add_subplot(111)
        draw_waveform(ax, data, rate, env=None, chirp_peaks_list=[], cfg=cfg)
        return ax.get_xlim()

    def test_com_recorte(self):
        lo, hi = self._xlim(True)
        self.assertAlmostEqual(lo, 1.0)
        self.assertAlmostEqual(hi, 2.0)

    def test_sem_recorte_mostra_gravacao_completa(self):
        lo, hi = self._xlim(False)
        self.assertAlmostEqual(lo, 0.0, places=2)
        self.assertGreater(hi, 4.9)


class TestMenuRouting(unittest.TestCase):
    """FASE 10: o dropdown da toolbar deve oferecer as tres acoes de exportacao."""

    def test_dropdown_tem_txt_relatorio_e_graficos(self):
        import inspect
        from ui.main_window import MainWindow
        src = inspect.getsource(MainWindow.show_export_menu)
        self.assertIn("request_txt_export", src)
        self.assertIn("request_modular_report", src)
        self.assertIn("request_graph_export", src)


if __name__ == "__main__":
    unittest.main()
