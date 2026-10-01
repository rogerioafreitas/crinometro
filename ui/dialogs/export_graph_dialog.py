# coding: utf-8
"""
ui/dialogs/export_graph_dialog.py
----------------------------------
FASE 8 — Diálogo de Exportação de Gráficos

Permite ao usuário selecionar quais painéis exportar, opções de aparência
(grade, marcadores, DPI, unidade do espectrograma) e o formato de saída
(PNG por painel ou PDF multipágina).

Não depende de controllers de UI ao vivo: usa apenas o SessionContext e a
FigureFactory, garantindo que a exportação funcione independente da geometria
atual da janela.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QRadioButton, QSpinBox, QLabel, QPushButton, QButtonGroup,
    QFileDialog, QMessageBox, QComboBox, QProgressBar, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ui.figure_factory import ExportConfig, export_figures_png, export_figures_pdf


# ---------------------------------------------------------------------------
# Worker thread — exportação em background para não travar a UI
# ---------------------------------------------------------------------------

class _ExportWorker(QThread):
    finished = pyqtSignal(list)   # lista de caminhos escritos
    error = pyqtSignal(str)

    def __init__(self, ctx, path: str, cfg: ExportConfig):
        super().__init__()
        self._ctx = ctx
        self._path = path
        self._cfg = cfg

    def run(self):
        try:
            if self._cfg.fmt == "pdf":
                out = export_figures_pdf(self._ctx, self._path, self._cfg)
                self.finished.emit([out])
            else:
                outs = export_figures_png(self._ctx, self._path, self._cfg)
                self.finished.emit(outs)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Diálogo principal
# ---------------------------------------------------------------------------

class ExportGraphDialog(QDialog):
    """
    Diálogo de exportação de gráficos.

    Uso:
        dlg = ExportGraphDialog(ctx, parent=self)
        dlg.exec()
    """

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self._ctx = ctx
        self._worker: _ExportWorker | None = None

        self.setWindowTitle("Exportar Gráficos")
        self.setMinimumWidth(440)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ---- Painéis ----
        grp_panels = QGroupBox("Painéis a exportar")
        panels_layout = QVBoxLayout(grp_panels)
        self._chk_wave = QCheckBox("Oscilograma (forma de onda)")
        self._chk_hist = QCheckBox("Histograma de Chilreios")
        self._chk_psd  = QCheckBox("Espectro de Potência (PSD)")
        self._chk_spec = QCheckBox("Espectrograma")
        for chk in (self._chk_wave, self._chk_hist, self._chk_psd, self._chk_spec):
            chk.setChecked(True)
            panels_layout.addWidget(chk)
        root.addWidget(grp_panels)

        # ---- Aparência ----
        grp_app = QGroupBox("Aparência")
        app_layout = QVBoxLayout(grp_app)

        row_grid = QHBoxLayout()
        self._chk_grid = QCheckBox("Mostrar grade")
        self._chk_markers = QCheckBox("Mostrar marcadores de pulsos")
        self._chk_markers.setChecked(True)
        row_grid.addWidget(self._chk_grid)
        row_grid.addWidget(self._chk_markers)
        app_layout.addLayout(row_grid)

        row_spec = QHBoxLayout()
        row_spec.addWidget(QLabel("Unidade do espectrograma:"))
        self._cmb_unit = QComboBox()
        self._cmb_unit.addItems(["kHz", "Hz"])
        row_spec.addWidget(self._cmb_unit)
        row_spec.addStretch()
        app_layout.addLayout(row_spec)

        row_dpi = QHBoxLayout()
        row_dpi.addWidget(QLabel("DPI:"))
        self._spn_dpi = QSpinBox()
        self._spn_dpi.setRange(72, 600)
        self._spn_dpi.setValue(150)
        self._spn_dpi.setSingleStep(50)
        row_dpi.addWidget(self._spn_dpi)
        row_dpi.addStretch()
        app_layout.addLayout(row_dpi)

        root.addWidget(grp_app)

        # ---- Formato ----
        grp_fmt = QGroupBox("Formato de saída")
        fmt_layout = QVBoxLayout(grp_fmt)
        self._bg_fmt = QButtonGroup(self)
        self._rdo_pdf = QRadioButton("PDF multipágina (um arquivo)")
        self._rdo_png = QRadioButton("PNG separado por painel")
        self._rdo_pdf.setChecked(True)
        self._bg_fmt.addButton(self._rdo_pdf)
        self._bg_fmt.addButton(self._rdo_png)
        fmt_layout.addWidget(self._rdo_pdf)
        fmt_layout.addWidget(self._rdo_png)
        root.addWidget(grp_fmt)

        # ---- Progresso ----
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)    # indeterminate
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # ---- Botões ----
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_export = QPushButton("Exportar…")
        self._btn_export.setDefault(True)
        self._btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_export)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _build_config(self) -> ExportConfig:
        panels = []
        if self._chk_wave.isChecked():
            panels.append("waveform")
        if self._chk_hist.isChecked():
            panels.append("histogram")
        if self._chk_psd.isChecked():
            panels.append("psd")
        if self._chk_spec.isChecked():
            panels.append("spectrogram")

        return ExportConfig(
            panels=panels,
            show_markers=self._chk_markers.isChecked(),
            grid=self._chk_grid.isChecked(),
            spec_unit=self._cmb_unit.currentText(),
            dpi=self._spn_dpi.value(),
            fmt="pdf" if self._rdo_pdf.isChecked() else "png",
            # Tema claro (papel branco)
            bg_color="#FFFFFF",
            ax_color="#334155",
            text_color="#1E293B",
            annotation_color="#1E293B",
        )

    def _on_export(self):
        if not self._ctx or not self._ctx.active_heavy_data:
            QMessageBox.warning(self, "Sem dados",
                                "Nenhum arquivo analisado está ativo. Abra e analise um arquivo antes de exportar.")
            return

        cfg = self._build_config()
        if not cfg.panels:
            QMessageBox.warning(self, "Nenhum painel",
                                "Selecione ao menos um painel para exportar.")
            return

        # Determina filtro e extensão
        if cfg.fmt == "pdf":
            flt = "PDF Files (*.pdf)"
            default_ext = ".pdf"
        else:
            flt = "PNG Files (*.png)"
            default_ext = ".png"

        base_name = os.path.splitext(
            os.path.basename(self._ctx.active_filename or "exportacao")
        )[0]
        default_name = f"{base_name}_graficos{default_ext}"

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Gráfico", default_name, flt
        )
        if not path:
            return

        self._btn_export.setEnabled(False)
        self._btn_cancel.setEnabled(False)
        self._progress.setVisible(True)

        self._worker = _ExportWorker(self._ctx, path, cfg)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, paths: list):
        self._progress.setVisible(False)
        self._btn_cancel.setEnabled(True)
        n = len(paths)
        if n == 1:
            msg = f"Gráfico exportado com sucesso:\n{paths[0]}"
        else:
            msg = f"{n} arquivos exportados em:\n{os.path.dirname(paths[0])}"
        QMessageBox.information(self, "Exportação concluída", msg)
        self.accept()

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._btn_export.setEnabled(True)
        self._btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Erro na exportação",
                             f"Não foi possível exportar os gráficos:\n\n{msg}")
