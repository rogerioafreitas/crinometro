# coding: utf-8
"""
ui/dialogs/export_graph_dialog.py
----------------------------------
FASE 8 — Diálogo de Exportação de Gráficos
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QRadioButton, QLabel, QPushButton, QButtonGroup,
    QFileDialog, QMessageBox, QComboBox, QProgressBar, QWidget, QFormLayout, QGridLayout
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve

from ui.figure_factory import ExportConfig, export_figures_png, export_figures_pdf
from ui.dialogs.theme import MODERN_DIALOG_THEME

# ---------------------------------------------------------------------------
# Worker thread e Contexto Snapshot (mantidos iguais)
# ---------------------------------------------------------------------------

class _SnapshotCtx:
    def __init__(self, spec_data, wave_data, chirps, active_filename):
        self.spec_data = spec_data
        self.wave_data = wave_data
        self.chirps = chirps
        self.active_filename = active_filename

class _ExportWorker(QThread):
    finished_ok = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(int, int)

    def __init__(self, config, ctx, parent=None):
        super().__init__(parent)
        self.config = config
        self.ctx = ctx
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def _should_cancel(self):
        return self._cancel_requested

    def run(self):
        try:
            if self.config.format == "png":
                export_figures_png(self.config, self.ctx, progress_callback=self.progress_update.emit, cancel_check=self._should_cancel)
            elif self.config.format == "pdf":
                export_figures_pdf(self.config, self.ctx, progress_callback=self.progress_update.emit, cancel_check=self._should_cancel)
            else:
                raise ValueError(f"Formato desconhecido: {self.config.format}")

            if not self._cancel_requested:
                self.finished_ok.emit()
        except Exception as e:
            if not self._cancel_requested:
                self.error_occurred.emit(str(e))

# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class ExportGraphDialog(QDialog):
    def __init__(self, session_context, live_view=None, parent=None):
        super().__init__(parent)
        self.session_context = session_context
        self._live_view = live_view or {}
        
        self.setWindowTitle("Exportar Gráficos")
        self.setMinimumWidth(450)
        
        self._worker = None

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # ---- Painéis a exportar ----
        grp_panels = QGroupBox("Painéis a exportar")
        panels_layout = QVBoxLayout(grp_panels)
        
        # Botões de marcação em massa
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_mark_all = QPushButton("Marcar todos")
        self._btn_clear_all = QPushButton("Limpar")
        # Estilo sutil para ações em massa
        self._btn_mark_all.setObjectName("linkButton")
        self._btn_mark_all.setToolTip("Marcar todos os painéis (Ctrl+A)")
        self._btn_mark_all.setShortcut("Ctrl+A")
        
        self._btn_clear_all.setObjectName("linkButton")
        self._btn_clear_all.setToolTip("Desmarcar todos os painéis (Ctrl+D)")
        self._btn_clear_all.setShortcut("Ctrl+D")
        btn_layout.addWidget(self._btn_mark_all)
        btn_layout.addWidget(self._btn_clear_all)
        panels_layout.addLayout(btn_layout)

        self._chk_wave = QCheckBox("Oscilograma (forma de onda)")
        self._chk_hist = QCheckBox("Histograma de Chilreios")
        self._chk_psd  = QCheckBox("Espectro de Potência (PSD)")
        self._chk_spec = QCheckBox("Espectrograma")

        self._chk_wave.setChecked(True)
        self._chk_spec.setChecked(True)

        panels_layout.addWidget(self._chk_wave)
        
        # Sub-opções do oscilograma com indentação real
        self.sub_wave_container = QWidget()
        sub_wave_layout = QVBoxLayout(self.sub_wave_container)
        sub_wave_layout.setContentsMargins(24, 0, 0, 0)
        sub_wave_layout.setSpacing(2)

        self._chk_raw = QCheckBox("Sinal bruto")
        self._chk_raw.setChecked(True)
        self._chk_env = QCheckBox("Envoltória de Hilbert")
        self._chk_env.setChecked(True)

        sub_wave_layout.addWidget(self._chk_raw)
        sub_wave_layout.addWidget(self._chk_env)
        panels_layout.addWidget(self.sub_wave_container)
        
        self._chk_wave.toggled.connect(self.sub_wave_container.setVisible)
        self.sub_wave_container.setVisible(self._chk_wave.isChecked())
        
        panels_layout.addWidget(self._chk_hist)
        panels_layout.addWidget(self._chk_psd)
        panels_layout.addWidget(self._chk_spec)
        panels_layout.addStretch()

        root.addWidget(grp_panels)

        # Conectar botões de massa
        self._btn_mark_all.clicked.connect(self._mark_all)
        self._btn_clear_all.clicked.connect(self._clear_all)

        # Conectar validação de exportação
        for chk in [self._chk_wave, self._chk_hist, self._chk_psd, self._chk_spec, self._chk_raw, self._chk_env]:
            chk.toggled.connect(self._validate_export_state)

        # ---- Configurações Gerais ----
        grp_gen = QGroupBox("Configurações Gerais")
        gen_layout = QVBoxLayout(grp_gen)
        
        form_gen = QFormLayout()
        form_gen.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_gen.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        
        self._cmb_dpi = QComboBox()
        self._cmb_dpi.addItems(["150 (Rascunho)", "300 (Publicação)", "600 (Alta Resolução)"])
        self._cmb_dpi.setCurrentIndex(1)
        self._cmb_dpi.setMaxVisibleItems(3)
        self._cmb_dpi.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        form_gen.addRow("Resolução:", self._cmb_dpi)
        
        self._cmb_bg = QComboBox()
        self._cmb_bg.addItems(["Branco (papel)", "Tema atual da janela"])
        form_gen.addRow("Fundo:", self._cmb_bg)
        
        gen_layout.addLayout(form_gen)
        
        grid_chk = QGridLayout()
        self._chk_grid = QCheckBox("Mostrar grade")
        self._chk_markers = QCheckBox("Marcadores de pulsos")
        self._chk_markers.setChecked(False)
        grid_chk.addWidget(self._chk_grid, 0, 0)
        grid_chk.addWidget(self._chk_markers, 0, 1)
        grid_chk.setColumnStretch(2, 1)
        gen_layout.addLayout(grid_chk)
        
        self._chk_apply_x = QCheckBox("Aplicar recorte de tempo focal ao oscilograma")
        self._chk_apply_x.setChecked(True)
        self._chk_apply_x.setToolTip("Quando ativo, o oscilograma exportado usa o mesmo recorte de tempo do espectrograma focal em vez da gravação completa.")
        gen_layout.addWidget(self._chk_apply_x)
        
        root.addWidget(grp_gen)

        # ---- Ajustes do Espectrograma ----
        self._grp_spec = QGroupBox("Ajustes do Espectrograma")
        spec_layout = QVBoxLayout(self._grp_spec)
        
        form_spec = QFormLayout()
        form_spec.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_spec.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        
        self._cmb_unit = QComboBox()
        self._cmb_unit.addItems(["kHz", "Hz"])
        form_spec.addRow("Unidade:", self._cmb_unit)
        
        self._cmb_scope = QComboBox()
        self._cmb_scope.addItems(["Focal", "10k", "Total", "Específico"])
        form_spec.addRow("Escopo:", self._cmb_scope)
        
        spec_layout.addLayout(form_spec)
        root.addWidget(self._grp_spec)
        
        self._grp_spec.setVisible(self._chk_spec.isChecked())
        self._chk_spec.toggled.connect(self._toggle_spec_section)

        # ---- Formato de saída ----
        grp_fmt = QGroupBox("Formato de saída")
        fmt_layout = QVBoxLayout(grp_fmt)
        self._bg_fmt = QButtonGroup(self)
        
        self._rdo_pdf = QRadioButton("PDF multipágina (um arquivo único)")
        self._rdo_png = QRadioButton("PNG individual por painel")
        self._rdo_pdf.setChecked(True)
        
        self._bg_fmt.addButton(self._rdo_pdf)
        self._bg_fmt.addButton(self._rdo_png)
        
        fmt_layout.addWidget(self._rdo_pdf)
        fmt_layout.addWidget(self._rdo_png)
        
        self._lbl_png_count = QLabel("")
        self._lbl_png_count.setObjectName("secondary")
        self._lbl_png_count.setVisible(False)
        fmt_layout.addWidget(self._lbl_png_count)
        
        fmt_layout.addStretch()
        root.addWidget(grp_fmt)
        
        self._rdo_png.toggled.connect(self._update_png_count_label)
        for chk in [self._chk_wave, self._chk_hist, self._chk_psd, self._chk_spec, self._chk_raw, self._chk_env]:
            chk.toggled.connect(self._update_png_count_label)

        # ---- Barra de Progresso ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # ---- Botões de Ação ----
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setContentsMargins(0, 16, 0, 0)
        
        self._btn_cancel = QPushButton("Cancelar")
        self._btn_export = QPushButton("Exportar...")
        self._btn_export.setObjectName("primaryButton")
        
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_export.clicked.connect(self._on_export)
        
        btn_action_layout.addStretch()
        btn_action_layout.addWidget(self._btn_cancel)
        btn_action_layout.addWidget(self._btn_export)
        
        root.addLayout(btn_action_layout)

        self.setStyleSheet(MODERN_DIALOG_THEME)
        
        # Chamada inicial para validar estado
        self._validate_export_state()
        self._update_png_count_label()

    def _mark_all(self):
        for chk in [self._chk_wave, self._chk_hist, self._chk_psd, self._chk_spec]:
            chk.setChecked(True)
        if self._chk_wave.isChecked():
            self._chk_raw.setChecked(True)
            self._chk_env.setChecked(True)

    def _clear_all(self):
        for chk in [self._chk_wave, self._chk_hist, self._chk_psd, self._chk_spec]:
            chk.setChecked(False)
        self._chk_raw.setChecked(False)
        self._chk_env.setChecked(False)

    def _validate_export_state(self):
        has_panel = any(chk.isChecked() for chk in [self._chk_wave, self._chk_hist, self._chk_psd, self._chk_spec])
        if self._chk_wave.isChecked() and not (self._chk_raw.isChecked() or self._chk_env.isChecked()):
            has_panel = False
            
        self._btn_export.setEnabled(has_panel)
        
    def _update_png_count_label(self):
        if not self._rdo_png.isChecked():
            self._lbl_png_count.setVisible(False)
            return
        count = sum([
            self._chk_wave.isChecked() and self._chk_raw.isChecked(),
            self._chk_wave.isChecked() and self._chk_env.isChecked(),
            self._chk_hist.isChecked(),
            self._chk_psd.isChecked(),
            self._chk_spec.isChecked(),
        ])
        self._lbl_png_count.setText(f"  {count} arquivo(s) PNG serão gerados")
        self._lbl_png_count.setVisible(True)

    def _toggle_spec_section(self, visible: bool):
        self._grp_spec.setVisible(visible)
        target_height = self.sizeHint().height()
        self._anim = QPropertyAnimation(self, b"minimumHeight")
        self._anim.setDuration(150)
        self._anim.setEndValue(target_height)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _build_config(self, filepath: str) -> ExportConfig:
        scope = self._cmb_scope.currentText()
        if scope == "Focal":
            t_min, t_max = self._live_view.get('focal_xlim', (None, None))
        elif scope == "Específico":
            t_min, t_max = self._live_view.get('xlim', (None, None))
        else:
            t_min, t_max = None, None

        unit = self._cmb_unit.currentText()
        if unit == "kHz":
            f_min, f_max = self._live_view.get('ylim_khz', (None, None))
        else:
            f_min, f_max = self._live_view.get('ylim_hz', (None, None))
            
        dpi_text = self._cmb_dpi.currentText()
        dpi = 300
        if "150" in dpi_text: dpi = 150
        elif "600" in dpi_text: dpi = 600

        is_dark = (self._cmb_bg.currentIndex() == 1)

        fmt = "pdf" if self._rdo_pdf.isChecked() else "png"

        return ExportConfig(
            filepath=filepath,
            panels={
                "wave_raw": self._chk_wave.isChecked() and self._chk_raw.isChecked(),
                "wave_env": self._chk_wave.isChecked() and self._chk_env.isChecked(),
                "psd": self._chk_psd.isChecked(),
                "spectrogram": self._chk_spec.isChecked(),
                "histogram": self._chk_hist.isChecked()
            },
            time_range=(t_min, t_max),
            freq_range=(f_min, f_max),
            apply_x_to_wave=self._chk_apply_x.isChecked(),
            grid=self._chk_grid.isChecked(),
            markers=self._chk_markers.isChecked(),
            spec_unit=unit,
            dpi=dpi,
            dark_mode=is_dark,
            format=fmt
        )

    def _on_export(self):
        if self._rdo_pdf.isChecked():
            path, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "", "PDF Files (*.pdf)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Selecionar pasta para PNGs")
            
        if not path:
            return

        cfg = self._build_config(path)
        ctx = _SnapshotCtx(
            spec_data=self.session_context.analysis_cache.get('spec_data'),
            wave_data=self.session_context.analysis_cache.get('wave_data'),
            chirps=self.session_context.analysis_cache.get('chirps'),
            active_filename=getattr(self.session_context, 'active_filename', 'export')
        )

        self._btn_export.setEnabled(False)
        self._btn_cancel.setText("Abortar")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        
        self._worker = _ExportWorker(cfg, ctx, parent=self)
        self._worker.progress_update.connect(self._on_progress_update)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
        
    def _on_progress_update(self, current: int, total: int):
        if self._progress.maximum() == 0 and total > 0:
            self._progress.setRange(0, total)
        self._progress.setValue(current)

    def _on_finished(self):
        self._worker = None
        QMessageBox.information(self, "Exportação", "Gráficos exportados com sucesso!")
        self.accept()

    def _on_error(self, msg):
        self._worker = None
        self._btn_export.setEnabled(True)
        self._btn_cancel.setText("Cancelar")
        self._progress.setVisible(False)
        QMessageBox.critical(self, "Erro na Exportação", f"Ocorreu um erro ao exportar:\n\n{msg}")

    def reject(self):
        if self._worker and self._worker.isRunning():
            try:
                self._worker.finished_ok.disconnect()
                self._worker.error_occurred.disconnect()
            except TypeError:
                pass
            self._worker.cancel()
            self._worker.wait()
        super().reject()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            try:
                self._worker.finished_ok.disconnect()
                self._worker.error_occurred.disconnect()
            except TypeError:
                pass
            self._worker.cancel()
            self._worker.wait()
        event.accept()
