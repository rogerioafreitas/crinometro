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
    QFileDialog, QMessageBox, QComboBox, QProgressBar, QWidget,
    QFormLayout, QGridLayout, QListView
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve

from utils.i18n import I18N
from ui.figure_factory import ExportConfig, export_figures_png, export_figures_pdf
from ui.dialogs.theme import get_dialog_theme



class _SnapshotCtx:
    def __init__(self, active_heavy_data, algo_params, active_filename):
        snap = dict(active_heavy_data) if active_heavy_data else {}
        for k in ("params", "discarded_peaks_reasons", "pulse_metadata"):
            if isinstance(snap.get(k), dict):
                snap[k] = dict(snap[k])
        for k in ("chirps", "peaks", "peaks_detected", "peaks_user_verified", "distant_peaks"):
            if isinstance(snap.get(k), list):
                snap[k] = list(snap[k])
        if isinstance(snap.get("chirp_peaks_list"), list):
            snap["chirp_peaks_list"] = [list(c) for c in snap["chirp_peaks_list"]]
        self.active_heavy_data = snap
        self.algo_params = dict(algo_params) if algo_params else {}
        self.active_filename = active_filename

class _ExportWorker(QThread):
    finished_ok = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(int, int)

    def __init__(self, config, ctx, path, parent=None):
        super().__init__(parent)
        self.config = config
        self.ctx = ctx
        self.path = path
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def _should_cancel(self):
        return self._cancel_requested

    def run(self):
        try:
            progress_cb = lambda cur, tot: self.progress_update.emit(cur, tot)
            if self.config.fmt == "png":
                export_figures_png(self.ctx, self.path, self.config, should_cancel=self._should_cancel, progress_callback=progress_cb)
            elif self.config.fmt == "pdf":
                export_figures_pdf(self.ctx, self.path, self.config, should_cancel=self._should_cancel, progress_callback=progress_cb)
            else:
                raise ValueError(f"Formato desconhecido: {self.config.fmt}")

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
        self._parent_dark = getattr(parent, "theme_mode", "dark") == "dark"
        self.lang = getattr(parent, "lang", None) or getattr(session_context, "report_params", {}).get("lang", "pt")
        t = I18N.get(self.lang, I18N["pt"])
        self.setWindowTitle(t["export_graphs_dialog_title"])
        self.setMinimumWidth(560)

        self._worker = None

        self._build_ui()

    def _build_ui(self):
        t = I18N[getattr(self, "lang", "pt")]
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(24)

        # ---- Painéis a exportar ----
        grp_panels = QGroupBox(t["panels_to_export_group"])
        panels_layout = QVBoxLayout(grp_panels)
        panels_layout.setContentsMargins(16, 16, 16, 16)
        panels_layout.setSpacing(6)

        # Botões de marcação em massa — estilo primário azul conforme design
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_mark_all = QPushButton(t["btn_mark_all"])
        self._btn_clear_all = QPushButton(t["btn_clear_all"])
        self._btn_mark_all.setObjectName("linkButton")
        self._btn_mark_all.setToolTip(t["btn_mark_all_tt"])
        self._btn_mark_all.setShortcut("Ctrl+A")
        self._btn_clear_all.setObjectName("linkButton")
        self._btn_clear_all.setToolTip(t["btn_clear_all_tt"])
        self._btn_clear_all.setShortcut("Ctrl+D")
        btn_layout.addWidget(self._btn_mark_all)
        btn_layout.addWidget(self._btn_clear_all)
        panels_layout.addLayout(btn_layout)

        self._chk_wave = QCheckBox(t["chk_wave_panel"])
        self._chk_hist = QCheckBox(t["chk_hist_panel"])
        self._chk_psd  = QCheckBox(t["chk_psd_panel"])
        self._chk_spec = QCheckBox(t["chk_spec_panel"])

        self._chk_wave.setChecked(True)
        self._chk_spec.setChecked(True)

        panels_layout.addWidget(self._chk_wave)

        # Sub-opções do oscilograma com indentação real (24dp)
        self.sub_wave_container = QWidget()
        sub_wave_layout = QVBoxLayout(self.sub_wave_container)
        sub_wave_layout.setContentsMargins(24, 0, 0, 0)
        sub_wave_layout.setSpacing(2)

        self._chk_raw = QCheckBox(t["chk_raw_signal"])
        self._chk_raw.setChecked(True)
        self._chk_env = QCheckBox(t["chk_hilbert_env"])
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
        grp_gen = QGroupBox(t["general_settings_group"])
        gen_layout = QVBoxLayout(grp_gen)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(8)

        form_gen = QFormLayout()
        form_gen.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_gen.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        form_gen.setVerticalSpacing(8)

        # Ordem conforme design: 300 (Publicação) primeiro, depois 150, depois 72
        self._cmb_dpi = QComboBox()
        self._cmb_dpi.addItems([t["dpi_opt_600"], t["dpi_opt_300"], t["dpi_opt_150"], t["dpi_opt_72"]])
        self._cmb_dpi.setCurrentIndex(1)
        self._cmb_dpi.setMaxVisibleItems(4)
        self._cmb_dpi.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        form_gen.addRow(t["dpi_label"], self._cmb_dpi)

        self._cmb_bg = QComboBox()
        self._cmb_bg.addItems([t["bg_opt_white"], t["bg_opt_theme"]])
        form_gen.addRow(t["bg_label"], self._cmb_bg)

        gen_layout.addLayout(form_gen)

        grid_chk = QGridLayout()
        grid_chk.setSpacing(8)
        self._chk_grid = QCheckBox(t["chk_show_grid"])
        self._chk_markers = QCheckBox(t["chk_pulse_markers"])
        self._chk_markers.setChecked(False)
        grid_chk.addWidget(self._chk_grid, 0, 0)
        grid_chk.addWidget(self._chk_markers, 0, 1)
        grid_chk.setColumnStretch(2, 1)
        gen_layout.addLayout(grid_chk)

        self._chk_apply_x = QCheckBox(t["chk_apply_focal_time"])
        self._chk_apply_x.setChecked(True)
        self._chk_apply_x.setToolTip(t["chk_apply_focal_time_tt"])
        gen_layout.addWidget(self._chk_apply_x)

        root.addWidget(grp_gen)

        # ---- Ajustes do Espectrograma ----
        self._grp_spec = QGroupBox(t["spec_settings_group"])
        spec_layout = QVBoxLayout(self._grp_spec)
        spec_layout.setContentsMargins(16, 16, 16, 16)
        spec_layout.setSpacing(8)

        form_spec = QFormLayout()
        form_spec.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_spec.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_spec.setVerticalSpacing(8)

        self._cmb_unit = QComboBox()
        self._cmb_unit.addItems(["kHz", "Hz"])
        form_spec.addRow(t["unit_label"], self._cmb_unit)

        self._cmb_scope = QComboBox()
        self._cmb_scope.addItems([t["scope_opt_focal"], t["scope_opt_10k"], t["scope_opt_total"], t["scope_opt_spec"]])
        form_spec.addRow(t["scope_label"], self._cmb_scope)


        spec_layout.addLayout(form_spec)
        root.addWidget(self._grp_spec)

        self._grp_spec.setVisible(self._chk_spec.isChecked())
        self._chk_spec.toggled.connect(self._toggle_spec_section)

        # ---- Formato de saída ----
        grp_fmt = QGroupBox(t["output_format_group"])
        fmt_layout = QVBoxLayout(grp_fmt)
        fmt_layout.setContentsMargins(16, 16, 16, 16)
        fmt_layout.setSpacing(6)
        self._bg_fmt = QButtonGroup(self)

        self._rdo_pdf = QRadioButton(t["rdo_multipage_pdf"])
        self._rdo_png = QRadioButton(t["rdo_individual_png"])
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

        # ---- Botões de Ação (alinhados à direita, espaçamento 26dp conforme design) ----
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setContentsMargins(0, 0, 0, 0)
        btn_action_layout.setSpacing(26)

        self._btn_cancel = QPushButton(t["cancel"])
        self._btn_export = QPushButton(t["btn_export_dialog"])
        self._btn_export.setObjectName("primaryButton")

        self._btn_cancel.clicked.connect(self.reject)
        self._btn_export.clicked.connect(self._on_export)

        btn_action_layout.addStretch()
        btn_action_layout.addWidget(self._btn_cancel)
        btn_action_layout.addWidget(self._btn_export)

        root.addLayout(btn_action_layout)

        is_dark = True
        if hasattr(self.parent(), "theme_mode"):
            is_dark = self.parent().theme_mode == "dark"
        self.setStyleSheet(get_dialog_theme(is_dark))

        # QListView explicito: permite estilizar a lista suspensa via QSS
        # e remove a moldura/sombra nativa escura do popup.
        for cmb in (self._cmb_dpi, self._cmb_bg, self._cmb_unit, self._cmb_scope):
            cmb.setView(QListView())
            cmb.view().window().setWindowFlags(
                Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.NoDropShadowWindowHint)
            cmb.view().window().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

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

    def _build_config(self) -> ExportConfig:
        # Painéis selecionados — ExportConfig espera uma lista de strings
        panels = []
        if self._chk_wave.isChecked():
            panels.append('waveform')
        if self._chk_hist.isChecked():
            panels.append('histogram')
        if self._chk_psd.isChecked():
            panels.append('psd')
        if self._chk_spec.isChecked():
            panels.append('spectrogram')

        # Escopo: espelha os presets do painel de espectrograma.
        # 10k / Focal / Total definem a FAIXA DE FREQUENCIA (eixo Y);
        # somente 'Específico' tambem recorta o TEMPO (eixo X) da vista atual.
        d = getattr(self.session_context, "active_heavy_data", None) or {}
        params = d.get("params") or {}
        nyq_hz = float(d.get("rate", 44100.0)) / 2.0
        unit = self._cmb_unit.currentText()
        scope_idx = self._cmb_scope.currentIndex()
        xmin = xmax = None
        if scope_idx == 1:
            y_hz = (0.0, min(10000.0, nyq_hz))
        elif scope_idx == 0:
            carrier = float(d.get("carrier_freq", 0.0) or 0.0)
            if carrier > 0:
                algo = getattr(self.session_context, "algo_params", None) or {}
                tol = float(params.get("freq_tolerance_hz", algo.get("freq_tolerance_hz", 700.0)))
                y_hz = (max(0.0, carrier - tol), min(nyq_hz, carrier + tol))
            else:
                y_hz = (float(params.get("b1_min", 3200.0)),
                        min(nyq_hz, float(params.get("b1_max", 6000.0))))
        elif scope_idx == 3:
            xlim = self._live_view.get("xlim")
            ylim = self._live_view.get("ylim")
            if xlim:
                xmin, xmax = float(xlim[0]), float(xlim[1])
            if ylim:
                live_scale = 1000.0 if self._live_view.get("spec_unit", "kHz") == "kHz" else 1.0
                y_hz = (float(ylim[0]) * live_scale, float(ylim[1]) * live_scale)
            else:
                y_hz = (0.0, nyq_hz)
        else:  # Total
            y_hz = (0.0, nyq_hz)
        unit_div = 1000.0 if unit == "kHz" else 1.0
        ymin, ymax = y_hz[0] / unit_div, y_hz[1] / unit_div

        # DPI
        dpi_text = self._cmb_dpi.currentText()
        dpi = 300
        if dpi_text.startswith("600"):
            dpi = 600
        elif dpi_text.startswith("150"):
            dpi = 150
        elif dpi_text.startswith("72"):
            dpi = 72

        # Fundo
        is_dark = (self._cmb_bg.currentIndex() == 1) and self._parent_dark
        bg_color   = '#1E293B' if is_dark else '#FFFFFF'
        ax_color   = '#E2E8F0' if is_dark else '#1E293B'
        text_color = '#E2E8F0' if is_dark else '#1E293B'

        # Formato
        fmt = "pdf" if self._rdo_pdf.isChecked() else "png"

        return ExportConfig(
            panels=panels,
            show_raw=self._chk_raw.isChecked(),
            show_env=self._chk_env.isChecked(),
            show_markers=self._chk_markers.isChecked(),
            grid=self._chk_grid.isChecked(),
            spec_unit=unit,
            spec_xmin=xmin,
            spec_xmax=xmax,
            wave_apply_xlim=self._chk_apply_x.isChecked(),
            spec_ymin=ymin if ymin is not None else 0.0,
            spec_ymax=ymax if ymax is not None else 10.0,
            dpi=dpi,
            bg_color=bg_color,
            ax_color=ax_color,
            text_color=text_color,
            annotation_color=text_color,
            fmt=fmt,
            lang=getattr(self, "lang", "pt"),
        )

    def _on_export(self):
        t = I18N[getattr(self, "lang", "pt")]
        if self._rdo_pdf.isChecked():
            path, _ = QFileDialog.getSaveFileName(self, t["save_pdf_graph_title"], "", "PDF Files (*.pdf)")
        else:
            path = QFileDialog.getExistingDirectory(self, t["select_png_dir_title"])

        if not path:
            return

        cfg = self._build_config()

        self._btn_export.setEnabled(False)
        self._btn_cancel.setText("Abortar")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)

        snapshot = _SnapshotCtx(
            getattr(self.session_context, "active_heavy_data", None),
            getattr(self.session_context, "algo_params", None),
            getattr(self.session_context, "active_filename", None),
        )
        self._worker = _ExportWorker(cfg, snapshot, path, parent=self)
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
        QMessageBox.information(self, I18N[self.lang]["graphs_exported_title"], I18N[self.lang]["graphs_exported_success"])
        self.accept()

    def _on_error(self, msg):
        self._worker = None
        self._btn_export.setEnabled(True)
        self._btn_cancel.setText(I18N[self.lang]["cancel"])
        self._progress.setVisible(False)
        QMessageBox.critical(self, I18N[self.lang]["graphs_export_error_title"], I18N[self.lang]["graphs_export_error_msg"].format(err=msg))

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
