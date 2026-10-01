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
    QRadioButton, QLabel, QPushButton, QButtonGroup,
    QFileDialog, QMessageBox, QComboBox, QProgressBar, QFrame, QWidget,
)
from PyQt6.QtCore import QThread, pyqtSignal

from ui.figure_factory import ExportConfig
from ui.dialogs.theme import MODERN_DIALOG_THEME
from ui.figure_factory import export_figures_png, export_figures_pdf


# ---------------------------------------------------------------------------
# Worker thread — exportação em background para não travar a UI
# ---------------------------------------------------------------------------


class _SnapshotCtx:
    def __init__(self, heavy, algo, name):
        self.active_heavy_data = heavy
        self.algo_params = algo
        self.active_filename = name

class _ExportWorker(QThread):
    done_export = pyqtSignal(list)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, ctx, path: str, cfg):
        super().__init__()
        self._ctx = ctx
        self._path = path
        self._cfg = cfg
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def _should_cancel(self):
        return self._is_cancelled

    def run(self):
        try:
            from ui.figure_factory import export_figures_pdf, export_figures_png
            if self._cfg.fmt == "pdf":
                out = export_figures_pdf(self._ctx, self._path, self._cfg, should_cancel=self._should_cancel)
                if self._is_cancelled:
                    self.cancelled.emit()
                else:
                    self.done_export.emit([out])
            else:
                outs = export_figures_png(self._ctx, self._path, self._cfg, should_cancel=self._should_cancel)
                if self._is_cancelled:
                    self.cancelled.emit()
                else:
                    self.done_export.emit(outs)
        except Exception as exc:
            if not self._is_cancelled:
                self.error.emit(str(exc))

class ExportGraphDialog(QDialog):
    """
    Diálogo de exportação de gráficos.

    Uso:
        dlg = ExportGraphDialog(ctx, parent=self)
        dlg.exec()
    """

    def __init__(self, ctx, parent=None, live_view=None):
        super().__init__(parent)
        self._ctx = ctx
        self._live_view = live_view or {}
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
            chk.setChecked(False)
            panels_layout.addWidget(chk)

        # Sub-opções do oscilograma (visíveis quando wave marcado)
        self._chk_raw = QCheckBox("  Sinal bruto")
        self._chk_raw.setChecked(True)
        self._chk_env = QCheckBox("  Envoltória de Hilbert")
        self._chk_env.setChecked(True)
        panels_layout.addWidget(self._chk_raw)
        panels_layout.addWidget(self._chk_env)
        self._chk_wave.toggled.connect(self._chk_raw.setVisible)
        self._chk_wave.toggled.connect(self._chk_env.setVisible)
        self._chk_raw.setVisible(False)
        self._chk_env.setVisible(False)

        root.addWidget(grp_panels)

        # ---- Aparência ----
        grp_app = QGroupBox("Aparência")
        app_layout = QVBoxLayout(grp_app)

        row_grid = QHBoxLayout()
        self._chk_grid = QCheckBox("Mostrar grade")
        self._chk_markers = QCheckBox("Mostrar marcadores de pulsos")
        self._chk_markers.setChecked(False)
        row_grid.addWidget(self._chk_grid)
        row_grid.addWidget(self._chk_markers)
        app_layout.addLayout(row_grid)

        row_bg = QHBoxLayout()
        row_bg.addWidget(QLabel("Fundo:"))
        self._cmb_bg = QComboBox()
        self._cmb_bg.addItems(["Branco (papel)", "Tema atual da janela"])
        row_bg.addWidget(self._cmb_bg)
        row_bg.addStretch()
        app_layout.addLayout(row_bg)

        row_spec = QHBoxLayout()
        row_spec.addWidget(QLabel("Unidade do espectrograma:"))
        self._cmb_unit = QComboBox()
        self._cmb_unit.addItems(["kHz", "Hz"])
        row_spec.addWidget(self._cmb_unit)
        row_spec.addStretch()
        app_layout.addLayout(row_spec)

        self._widget_scope = QWidget()
        scope_layout = QVBoxLayout(self._widget_scope)
        scope_layout.setContentsMargins(0, 0, 0, 0)
        row_scope = QHBoxLayout()
        row_scope.addWidget(QLabel("Escopo do Espectrograma:"))
        self._cmb_scope = QComboBox()
        self._cmb_scope.addItems(["Focal", "10k", "Total", "Específico"])
        row_scope.addWidget(self._cmb_scope)
        row_scope.addStretch()
        scope_layout.addLayout(row_scope)
        self._chk_apply_x = QCheckBox("Aplicar recorte de tempo ao oscilograma")
        self._chk_apply_x.setChecked(True)
        scope_layout.addWidget(self._chk_apply_x)
        app_layout.addWidget(self._widget_scope)

        # Oculta inicialmente e vincula o estado do checkbox
        self._widget_scope.setVisible(self._chk_spec.isChecked())
        self._chk_spec.toggled.connect(self._widget_scope.setVisible)

        row_dpi = QHBoxLayout()
        row_dpi.addWidget(QLabel("DPI (Resolução):"))
        self._cmb_dpi = QComboBox()
        self._cmb_dpi.addItems(["150 (Rascunho)", "300 (Publicação)", "600 (Alta Resolução)"])
        self._cmb_dpi.setCurrentIndex(1) # Default 300
        row_dpi.addWidget(self._cmb_dpi)
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
        self.setStyleSheet(MODERN_DIALOG_THEME)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_export)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------

    def reject(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._btn_cancel.setEnabled(False)
            return
        super().reject()

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._btn_cancel.setEnabled(False)
            event.ignore()
            return
        super().closeEvent(event)


    def _build_config(self) -> ExportConfig:
        panels = []
        if self._chk_wave.isChecked(): panels.append("waveform")
        if self._chk_hist.isChecked(): panels.append("histogram")
        if self._chk_psd.isChecked(): panels.append("psd")
        if self._chk_spec.isChecked(): panels.append("spectrogram")

        xmin = xmax = None
        ymin, ymax = 0.0, 10.0
        
        scope = self._cmb_scope.currentText()
        unit = self._cmb_unit.currentText()
        rate = self._ctx.active_heavy_data.get("rate", 44100) if self._ctx.active_heavy_data else 44100
        
        if self._widget_scope.isVisible():
            if scope.startswith("Específico"):
                xmin = self._live_view.get("xlim", (None, None))[0]
                xmax = self._live_view.get("xlim", (None, None))[1]
                lymin, lymax = self._live_view.get("ylim", (0.0, 10.0))
                lunit = self._live_view.get("spec_unit", "kHz")
                if lunit == "Hz" and unit == "kHz":
                    ymin, ymax = lymin / 1000.0, lymax / 1000.0
                elif lunit == "kHz" and unit == "Hz":
                    ymin, ymax = lymin * 1000.0, lymax * 1000.0
                else:
                    ymin, ymax = lymin, lymax
            elif scope.startswith("10k"):
                ymin, ymax = 0.0, 10.0 if unit == "kHz" else 10000.0
            elif scope.startswith("Total"):
                ymax = (rate / 2000.0) if unit == "kHz" else (rate / 2.0)
                ymin = 0.0
            elif scope.startswith("Focal"):
                carrier = self._ctx.active_heavy_data.get("carrier_freq", 0.0) if self._ctx.active_heavy_data else 0.0
                algo_params = self._ctx.algo_params or {}
                tol_val = float(algo_params.get("freq_tolerance_hz", 700.0))
                if carrier > 0:
                    y_min_hz = max(0.0, carrier - tol_val)
                    y_max_hz = carrier + tol_val
                    ymin = y_min_hz / 1000.0 if unit == "kHz" else y_min_hz
                    ymax = y_max_hz / 1000.0 if unit == "kHz" else y_max_hz
                else:
                    ymin = 3.2 if unit == "kHz" else 3200.0
                    ymax = 6.0 if unit == "kHz" else 6000.0
        
        if not self._chk_apply_x.isChecked():
            xmin = xmax = None
            
        is_light = getattr(self.parent(), "theme_mode", "dark") == "light"
        if self._cmb_bg.currentIndex() == 0:
            bg_color = "#FFFFFF"
            ax_color = "#000000"
            text_color = "#000000"
            ann_color = "#000000"
        else:
            bg_color = "#FFFFFF" if is_light else "#0F172A"
            ax_color = "#475569" if is_light else "#94A3B8"
            text_color = "#0F172A" if is_light else "#CBD5E1"
            ann_color = "#0F172A" if is_light else "#F8FAFC"

        return ExportConfig(
            panels=panels,
            show_raw=self._chk_raw.isChecked(),
            show_env=self._chk_env.isChecked(),
            show_markers=self._chk_markers.isChecked(),
            grid=self._chk_grid.isChecked(),
            fmt="pdf" if self._rdo_pdf.isChecked() else "png",
            spec_unit=unit,
            spec_xmin=xmin,
            spec_xmax=xmax,
            spec_ymin=ymin,
            spec_ymax=ymax,
            dpi=int(self._cmb_dpi.currentText().split()[0]),
            bg_color=bg_color,
            ax_color=ax_color,
            text_color=text_color,
            annotation_color=ann_color
        )

    def _on_export(self):
        if not self._ctx or not self._ctx.active_heavy_data:
            QMessageBox.warning(self, self.tr("Sem dados"),
                                self.tr("Nenhum arquivo analisado está ativo. Abra e analise um arquivo antes de exportar."))
            return

        cfg = self._build_config()
        if not cfg.panels:
            QMessageBox.warning(self, self.tr("Nenhum painel"),
                                self.tr("Selecione ao menos um painel para exportar."))
            return

        base_name = os.path.splitext(
            os.path.basename(getattr(self._ctx, "active_filename", "exportacao") or "exportacao")
        )[0]

        is_pdf = self._rdo_pdf.isChecked()

        
        if is_pdf:
            dlg = QFileDialog(self, "Salvar PDF", base_name + "_graficos.pdf", "PDF Files (*.pdf)")
            dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            dlg.setDefaultSuffix("pdf")
            dlg.setOptions(QFileDialog.Option.DontConfirmOverwrite)
            if dlg.exec() == QFileDialog.DialogCode.Accepted:
                path = dlg.selectedFiles()[0]
            else:
                path = ""
        else:
            path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para PNGs")
            if path:
                path = os.path.join(path, base_name)

        if not path:
            return

        self._btn_export.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._progress.setVisible(True)

        heavy_snap = dict(self._ctx.active_heavy_data) if getattr(self._ctx, "active_heavy_data", None) else {}
        algo_snap = dict(self._ctx.algo_params) if getattr(self._ctx, "algo_params", None) else {}
        name_snap = getattr(self._ctx, "active_filename", "")
        snap_ctx = _SnapshotCtx(heavy_snap, algo_snap, name_snap)

        self._worker = _ExportWorker(snap_ctx, path, cfg)
        self._worker.done_export.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_finished(self, paths: list):
        self._progress.setVisible(False)
        self._btn_cancel.setEnabled(True)
        self._btn_export.setEnabled(True)
        n = len(paths)
        if n == 1:
            msg = f"Gráfico exportado com sucesso:\n{paths[0]}"
        elif n > 1:
            msg = f"{n} gráficos exportados com sucesso:\n" + "\n".join(paths)
        else:
            msg = "Nenhum arquivo gravado."
        QMessageBox.information(self, "Sucesso", msg)
        self.accept()

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._btn_cancel.setEnabled(True)
        self._btn_export.setEnabled(True)
        QMessageBox.critical(self, "Erro na Exportação", msg)

    def _on_cancelled(self):
        self._progress.setVisible(False)
        self._btn_cancel.setEnabled(True)
        self._btn_export.setEnabled(True)
        QMessageBox.information(self, "Cancelado", "A exportação foi cancelada.")
