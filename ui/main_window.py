"""
Crinômetro - Janela Principal e Dashboard Científico (MainWindow).
"""
import os

import time
import datetime
import json

import numpy as np
import scipy.io.wavfile as wavfile


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QSplitter, QMessageBox, QPushButton,
    QSlider, QFileDialog, QFrame, QListWidgetItem,
    QSizePolicy, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QAction, QPainter
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput




from utils.constants import APP_VERSION, APP_VERSION_LABEL, CONFIG_FILE, DEFAULT_ALGO_PARAMS
from utils.i18n import I18N
from utils.icons import get_app_icon, make_ui_icon
from utils.styles import get_modern_stylesheet


from core.learner import PulseLearner



from ui.widgets import ButtonSpinner, ThemeToggle, AudioListItemWidget
from ui.panels import PlotPanel
from ui.dialogs.export_graph_dialog import ExportGraphDialog
from ui.dialogs import (
    AlgoSettingsDialog, GeneralSettingsDialog,
    AboutDialog
)
from core.updater import UpdateCheckerThread
from ui.update_dialog import UpdateDialog
from core.session_context import SessionContext

class MainWindow(QMainWindow):
    # --- PROPRIEDADES REDIRECIONADAS PARA O SESSIONCONTEXT ---
















    # ---------- FASE 3: Aliases de compatibilidade para engines e estado de plot ----------






    # ---------- FASE 4: Aliases de compatibilidade para NavigationController ----------













    # ---------- FASE 5: Aliases de compatibilidade para EditorController ----------

    def __init__(self):
        super().__init__()
        self.ctx = SessionContext(self)
        self._swapping_panels = False
        
        from ui.controllers.pipeline_orchestrator import PipelineOrchestrator
        self.pipeline = PipelineOrchestrator(self.ctx, self)
        self.pipeline.analysis_started.connect(self._on_analysis_started)
        self.pipeline.analysis_completed.connect(self._on_pipeline_completed)
        self.pipeline.analysis_failed.connect(self._on_pipeline_failed)
        self.pipeline.analysis_cancelled.connect(self._on_pipeline_cancelled)
        self.pipeline.analysis_progress.connect(self._on_batch_progress)
        self.pipeline.realtime_tolerance_updated.connect(self._on_realtime_tolerance_updated)
        self.pipeline.batch_started.connect(self._on_batch_started)
        self.pipeline.batch_item_completed.connect(self._on_batch_item_completed)
        self.pipeline.batch_completed.connect(self._on_batch_completed)
        self.pipeline.batch_failed.connect(self._on_batch_failed)
        self.pipeline.batch_cancelled.connect(self._on_batch_cancelled)

        # Parâmetros base do algoritmo — editados pelo usuário via menu.
        # NÃO inclui sobreposições adaptativas (prominence, noise_floor adaptados).
        self.ctx.algo_params = DEFAULT_ALGO_PARAMS.copy()
        # Sobreposições adaptativas: aplicadas por _adapt_advanced_params() mas
        # NUNCA persistidas no JSON e limpas no reset.
        self.ctx._adaptive_overrides = {}
        self.ctx.report_params = {"lang": "pt", "institution": "", "researcher_name": "", "role": "", "level": ""}


        # Inicializa o idioma ANTES de qualquer rotina que possa usar I18N.
        # Isso evita AttributeError caso alguma ação seja disparada durante a inicialização.
        self.lang = "pt"
        self.theme_mode = "dark"
        self.ctx.pulse_learner = PulseLearner(CONFIG_FILE)
        self.ctx.peaks_detected = []
        self.ctx.peaks_user_verified = []
        self.ctx.corrections_by_file = {}
        self.ctx.active_filename = None
        self.ctx.use_machine_learning = False
        self.load_settings()
        self.lang = self.ctx.report_params.get("lang", "pt") or "pt"

        self.setWindowTitle(I18N[self.lang]["app_title"])
        self.setGeometry(80, 70, 1480, 900)
        # Centraliza a janela principal na tela disponível.
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(available.center())
            self.move(frame.topLeft())
        self.setMinimumSize(1120, 700)
        self.setAcceptDrops(True)
        self.setWindowIcon(get_app_icon())

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)
        self.player.positionChanged.connect(self.update_playback_cursor)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self._on_playback_state)

        # Timer de alta precisão (10 ms) para atualização suave e responsiva da timeline e cursor
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(10)
        self.playback_timer.timeout.connect(self._on_playback_timer_tick)

        self.ctx.loaded_files = {}
        self.last_audio_dir = ""
        self.expanded_panel = None
        self.last_pan_time = 0
        self.ctx.analysis_cache = {}
        self.ctx.active_heavy_data = {}
        self.loop_enabled = False
        self.playback_speed = 1.0
        self.main_panel = None
        self.stack_panels = []
        self._building_dashboard = False

        self.setup_menu()
        self.setup_ui()
        self._update_theme_icons()

        # FASE 3 — PlotRenderers: instanciado depois de setup_ui para garantir que
        # panel_wave, panel_spec, panel_hist e panel_freq já existam.
        from ui.controllers.plot_renderers import PlotRenderers
        self.plot_renderers = PlotRenderers(
            session_context=self.ctx,
            main_window=self,
            panel_wave=self.panel_wave,
            panel_spec=self.panel_spec,
            panel_hist=self.panel_hist,
            panel_psd=None,
            panel_freq=self.panel_freq,
        )

        # FASE 4 — NavigationController: isolamento de viewport, pan, zoom, hover e blitting
        from ui.controllers.navigation_controller import NavigationController
        self.nav_controller = NavigationController(
            session_context=self.ctx,
            plot_renderers=self.plot_renderers,
            main_window=self,
            panel_wave=self.panel_wave,
            panel_spec=self.panel_spec,
            panel_hist=self.panel_hist,
            panel_psd=None,
            panel_freq=self.panel_freq,
            parent=self,
        )
        self.plot_renderers.set_navigation_controller(self.nav_controller)

        # FASE 5 — EditorController: edição de pulsos, undo history e retreinamento
        from ui.controllers.editor_controller import EditorController
        self.editor_controller = EditorController(
            session_context=self.ctx,
            plot_renderers=self.plot_renderers,
            navigation_controller=self.nav_controller,
            pipeline_orchestrator=self.pipeline,
            main_window=self,
            parent=self,
        )
        self.plot_renderers.set_editor_controller(self.editor_controller)

        # Início limpo: nenhum arquivo fictício é carregado automaticamente.

    # ---------- tema ----------
    # ---------- tema ----------
        self.btn_abort_batch.clicked.connect(self.pipeline.abort_current_analysis)
        self.btn_reanalisar_main.clicked.connect(lambda: self.pipeline.force_reanalyze(self._get_item_filename(self.list_widget.currentItem()) or getattr(self.ctx, "active_filename", None)))
        self.btn_abort_analysis.clicked.connect(self.pipeline.abort_current_analysis)
        self.btn_learn_corrections.clicked.connect(lambda: self.editor_controller.learn_from_corrections())
        self.editor_controller.learning_failed.connect(lambda err: QMessageBox.critical(self, "Falha", err))
        self.editor_controller.learning_completed.connect(lambda n, fn: QMessageBox.information(self, "Sucesso", f"IA treinada com {n} correcoes!"))
        self.btn_sync.toggled.connect(self.nav_controller.on_sync_toggled)
        self.nav_controller.pulse_edit_handler = self.editor_controller.toggle_peak_marker

        for panel in self.all_panels:
            panel.undo_requested.connect(self.editor_controller.undo)
            panel.spectrogram_y_limits_changed.connect(self.plot_renderers.apply_spectrogram_y_limits)
            panel.freq_tolerance_changed.connect(self.pipeline.apply_realtime_freq_tolerance)
            panel.wave_visibility_changed.connect(self.plot_renderers.update_wave_visibility)
            if panel is self.panel_hist:
                continue
            panel.canvas.mpl_connect('scroll_event', self.nav_controller.zoom_graph)
            panel.canvas.mpl_connect('button_press_event', self.nav_controller.on_press)
            panel.canvas.mpl_connect('button_release_event', self.nav_controller.on_release)
            panel.canvas.mpl_connect('motion_notify_event', self.nav_controller.on_motion)
            panel.canvas.mpl_connect('axes_leave_event', self.nav_controller.on_axes_leave)

    def apply_modern_styles(self):
        self.setStyleSheet(get_modern_stylesheet(self.theme_mode))
        for btn in self.findChildren(QPushButton):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        for chk in self.findChildren(QCheckBox):
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
        for sld in self.findChildren(QSlider):
            sld.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_theme_icons(self):
        """Atualiza ícones que dependem do tema para garantir alto contraste nos dois modos."""
        dark = self.theme_mode == "dark"
        icon_col = "#E4E8EC" if dark else "#334155"
        sec_icon_col = "#FFFFFF" if dark else "#334155"
        if hasattr(self, "btn_collapse"):
            collapse_icon = "chevron_left" if not getattr(self, "_sidebar_collapsed", False) else "chevron_right"
            self.btn_collapse.setIcon(make_ui_icon(collapse_icon, color=icon_col, size=18))
        if hasattr(self, "btn_menu"):
            self.btn_menu.setIcon(make_ui_icon("menu", color=icon_col, size=18))
        if hasattr(self, "btn_learn_corrections"):
            self.btn_learn_corrections.setIcon(make_ui_icon("brain", color=sec_icon_col, size=14))
        if hasattr(self, "btn_export_main"):
            self.btn_export_main.setIcon(make_ui_icon("export", color=sec_icon_col, size=14))
        if hasattr(self, "btn_sync") and not self.btn_sync.isChecked():
            self.btn_sync.setIcon(make_ui_icon("sync", color="#CBD5E1" if dark else "#475569", size=14))
        if hasattr(self, "transport_panel"):
            self._update_play_icon()

    def set_theme_mode(self, mode):
        mode = "light" if mode == "light" else "dark"
        if self.theme_mode == mode:
            return
        self.theme_mode = mode
        self.apply_modern_styles()
        for panel in getattr(self, "all_panels", []):
            panel.apply_dark_theme()
        self._update_theme_icons()
        if self.ctx.active_heavy_data:
            if self.ctx.active_filename:
                self.plot_renderers.render_dashboard(self.ctx.active_filename)
            else:
                self._refresh_all_canvases()
        else:
            self._draw_empty_plots()
        self.update_menu_text()

    def toggle_theme(self):
        self.set_theme_mode("light" if self.theme_mode == "dark" else "dark")
        if hasattr(self, "theme_toggle"):
            self.theme_toggle.blockSignals(True)
            self.theme_toggle.setChecked(self.theme_mode == "light")
            self.theme_toggle.blockSignals(False)

    # ---------- menu ----------
    def setup_menu(self):
        self.menu_bar = self.menuBar()
        self.menu_bar.setVisible(False)
        self.app_menu = QMenu(self)
        self.file_menu = self.app_menu.addMenu(I18N[self.lang]["file"])
        self.action_load = QAction(I18N[self.lang]["load"], self)
        self.action_load.triggered.connect(self.action_load_wav)
        self.file_menu.addAction(self.action_load)
        
        self.export_submenu = self.file_menu.addMenu("Exportar" if self.lang == "pt" else "Export")
        self.export_submenu.setIcon(make_ui_icon("export", color="#FFFFFF", size=16))
        
        self.action_export = QAction(I18N[self.lang]["export"], self)
        self.action_export.triggered.connect(self.action_save_txt)
        self.export_submenu.addAction(self.action_export)
        self.action_export_pdf_mod = QAction("Exportar Relatório Modular...", self)
        self.action_export_pdf_mod.setIcon(make_ui_icon("export", color="#0284C7", size=16))
        self.action_export_pdf_mod.triggered.connect(self.open_export_report_dialog)
        self.export_submenu.addAction(self.action_export_pdf_mod)
        self.export_submenu.addSeparator()
        self.action_export_graphs = QAction("Exportar Gráficos (PNG/PDF)…", self)
        self.action_export_graphs.setIcon(make_ui_icon("export", color="#10B981", size=16))
        self.action_export_graphs.triggered.connect(self.open_export_graph_dialog)
        self.export_submenu.addAction(self.action_export_graphs)
        

        self.settings_menu = self.app_menu.addMenu(I18N[self.lang]["settings"])
        self.action_algo_config = QAction(I18N[self.lang]["algo_settings"], self)
        self.action_algo_config.triggered.connect(self.open_algo_settings)
        self.settings_menu.addAction(self.action_algo_config)
        self.action_report_config = QAction(I18N[self.lang]["gen_settings"], self)
        self.action_report_config.triggered.connect(self.open_report_settings)
        self.settings_menu.addAction(self.action_report_config)
        
        self.action_ai_params = QAction("Parâmetros de IA" if self.lang == "pt" else "AI Parameters", self)
        self.action_ai_params.triggered.connect(self.open_ai_params)
        self.settings_menu.addAction(self.action_ai_params)
        self.view_menu = self.app_menu.addMenu("Exibir" if self.lang == "pt" else "View")
        self.action_view_wave = QAction("Forma de Onda" if self.lang == "pt" else "Waveform", self, checkable=True)
        self.action_view_wave.setChecked(True)
        self.action_view_wave.triggered.connect(lambda c: self.toggle_plot_panel_by_key("wave", c))
        self.view_menu.addAction(self.action_view_wave)
        self.action_view_hist = QAction("Histograma de Intervalos" if self.lang == "pt" else "Interval Histogram", self, checkable=True)
        self.action_view_hist.setChecked(True)
        self.action_view_hist.triggered.connect(lambda c: self.toggle_plot_panel_by_key("hist", c))
        self.view_menu.addAction(self.action_view_hist)
        self.action_view_freq = QAction("Espectro de Potência (PSD)" if self.lang == "pt" else "Power Spectral Density (PSD)", self, checkable=True)
        self.action_view_freq.setChecked(True)
        self.action_view_freq.triggered.connect(lambda c: self.toggle_plot_panel_by_key("freq", c))
        self.view_menu.addAction(self.action_view_freq)
        self.action_view_spec = QAction("Espectrograma Focal" if self.lang == "pt" else "Focal Spectrogram", self, checkable=True)
        self.action_view_spec.setChecked(True)
        self.action_view_spec.triggered.connect(lambda c: self.toggle_plot_panel_by_key("spec", c))
        self.view_menu.addAction(self.action_view_spec)
        self.view_menu.addSeparator()
        self.action_reset_layout = QAction("↺ Restaurar Layout Padrão" if self.lang == "pt" else "↺ Reset Plot Layout", self)
        self.action_reset_layout.triggered.connect(self.reset_plot_layout)
        self.view_menu.addAction(self.action_reset_layout)

        self.help_menu = self.app_menu.addMenu(I18N[self.lang]["help"])
        self.action_check_updates = QAction(I18N[self.lang].get("check_updates", "Verificar Atualizações..."), self)
        self.action_check_updates.setIcon(make_ui_icon("export", color="#10B981", size=16))
        self.action_check_updates.triggered.connect(self.check_for_updates)
        self.help_menu.addAction(self.action_check_updates)
        self.action_about = QAction(I18N[self.lang]["about"], self)
        self.action_about.triggered.connect(self.open_about)
        self.help_menu.addAction(self.action_about)


    def update_menu_text(self):
        l = self.lang
        self.file_menu.setTitle(I18N[l]["file"])
        if hasattr(self, "export_submenu"):
            self.export_submenu.setTitle("Exportar" if l == "pt" else "Export")
        self.action_load.setText(I18N[l]["load"])
        self.action_export.setText(I18N[l]["export"])
        if hasattr(self, "action_export_pdf_full"):
            self.action_export_pdf_full.setText("Exportar Relatório Completo (.pdf)" if l == "pt" else "Export Full Report (.pdf)")
        if hasattr(self, "action_export_pdf_simple"):
            self.action_export_pdf_simple.setText("Exportar Relatório Simplificado (.pdf)" if l == "pt" else "Export Simplified Report (.pdf)")
        self.settings_menu.setTitle(I18N[l]["settings"])
        self.action_algo_config.setText(I18N[l]["algo_settings"])
        self.action_report_config.setText(I18N[l]["gen_settings"])
        
        
        
        
        if hasattr(self, "view_menu"):
            self.view_menu.setTitle("Exibir" if l == "pt" else "View")
        if hasattr(self, "action_view_wave"):
            self.action_view_wave.setText("Forma de Onda" if l == "pt" else "Waveform")
        if hasattr(self, "action_view_hist"):
            self.action_view_hist.setText("Histograma de Intervalos" if l == "pt" else "Interval Histogram")
        if hasattr(self, "action_view_freq"):
            self.action_view_freq.setText("Espectro de Potência (PSD)" if l == "pt" else "Power Spectral Density (PSD)")
        if hasattr(self, "action_view_spec"):
            self.action_view_spec.setText("Espectrograma Focal" if l == "pt" else "Focal Spectrogram")
        if hasattr(self, "action_reset_layout"):
            self.action_reset_layout.setText("↺ Restaurar Layout Padrão" if l == "pt" else "↺ Reset Plot Layout")
        if hasattr(self, "btn_plots_menu"):
            self.btn_plots_menu.setText("Gráficos ▾" if l == "pt" else "Graphs ▾")
        if hasattr(self, "btn_reset_layout"):
            self.btn_reset_layout.setText("↺ Padrão" if l == "pt" else "↺ Default")
        self.help_menu.setTitle(I18N[l]["help"])
        if hasattr(self, "action_check_updates"):
            self.action_check_updates.setText(I18N[l].get("check_updates", "Verificar Atualizações..."))
        self.action_about.setText(I18N[l]["about"])
        self.setWindowTitle(I18N[l]["app_title"])

    def show_app_menu(self):
        self.app_menu.popup(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft()))

    # ---------- construção da interface ----------
    def setup_ui(self):
        self.apply_modern_styles()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # NAV BAR
        nav = QFrame()
        nav.setObjectName("topNav")
        nav.setFixedHeight(54)
        nav_l = QHBoxLayout(nav)
        nav_l.setContentsMargins(15, 0, 15, 0)
        nav_l.setSpacing(8)

        self.btn_menu = QPushButton()
        self.btn_menu.setObjectName("menuButton")
        self.btn_menu.setIcon(make_ui_icon("menu", size=18))
        self.btn_menu.setIconSize(QSize(18, 18))
        self.btn_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_menu.setFixedSize(34, 34)
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_menu.clicked.connect(self.show_app_menu)
        nav_l.addWidget(self.btn_menu)

        self.btn_collapse = QPushButton()
        self.btn_collapse.setObjectName("navIcon")
        self.btn_collapse.setIcon(make_ui_icon("chevron_left", size=18))
        self.btn_collapse.setIconSize(QSize(16, 16))
        self.btn_collapse.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_collapse.setFixedSize(30, 30)
        self.btn_collapse.setToolTip("Ocultar/mostrar painel de arquivos")
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.clicked.connect(self.toggle_sidebar)
        nav_l.addWidget(self.btn_collapse)

        brand = QLabel("CRINÔMETRO")
        brand.setObjectName("brand")
        brand.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        brand.setAutoFillBackground(False)
        nav_l.addWidget(brand)
        version = QLabel(f"v{APP_VERSION_LABEL}")
        version.setObjectName("version")
        version.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        version.setAutoFillBackground(False)
        nav_l.addWidget(version)
        nav_l.addStretch()

        self.theme_label = QLabel("Tema")
        self.theme_label.setObjectName("themeLabel")
        nav_l.addWidget(self.theme_label)
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.setChecked(self.theme_mode == "light")
        self.theme_toggle.toggled.connect(lambda checked: self.set_theme_mode("light" if checked else "dark"))
        self.theme_toggle.setToolTip("Alternar modo claro/escuro")
        nav_l.addWidget(self.theme_toggle)

        root.addWidget(nav)

        # CONTEÚDO: sidebar + dashboard
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("mainSplitter")
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setOpaqueResize(True)
        self.splitter.setHandleWidth(4)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        root.addWidget(self.splitter, 1)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("sidebar")
        self.left_panel.setFrameShape(QFrame.Shape.NoFrame)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(8, 12, 8, 10)
        left_layout.setSpacing(6)

        side_head = QHBoxLayout()
        side_head.setContentsMargins(4, 0, 4, 0)
        self.lbl_arquivos = QLabel("Arquivos")
        self.lbl_arquivos.setObjectName("sidebarTitle")
        side_head.addWidget(self.lbl_arquivos)
        side_head.addStretch()

        self.container_select_all = QWidget()
        self.container_select_all.setObjectName("containerSelectAll")
        self.container_select_all.setStyleSheet("background: transparent; background-color: transparent; border: none; margin: 0; padding: 0;")
        layout_sel_all = QHBoxLayout(self.container_select_all)
        layout_sel_all.setContentsMargins(0, 0, 0, 0)
        layout_sel_all.setSpacing(4)

        self.lbl_select_all = QLabel("Selecionar tudo")
        self.lbl_select_all.setObjectName("select_all_lbl")
        self.lbl_select_all.setStyleSheet("background: transparent; border: none; font-size: 11px; color: #64748B;")
        layout_sel_all.addWidget(self.lbl_select_all)

        self.chk_select_all = QCheckBox()
        self.chk_select_all.setChecked(False)
        self.chk_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_select_all.setStyleSheet("background: transparent; border: none;")
        self.chk_select_all.setToolTip("Marcar / Desmarcar todos os arquivos para lote e relatório")
        self.chk_select_all.stateChanged.connect(self.toggle_select_all_files)
        layout_sel_all.addWidget(self.chk_select_all)

        self.container_select_all.setVisible(False)
        side_head.addWidget(self.container_select_all)

        left_layout.addLayout(side_head)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(15, 15))
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.itemSelectionChanged.connect(self.on_file_selected)
        left_layout.addWidget(self.list_widget, 1)

        batch_btn_layout = QHBoxLayout()
        batch_btn_layout.setContentsMargins(0, 0, 0, 0)
        batch_btn_layout.setSpacing(6)

        self.btn_analyze_selected = QPushButton("⚡ Analisar Selecionados")
        self.btn_analyze_selected.setObjectName("summaryAction")
        self.btn_analyze_selected.setToolTip("Executar análise em todos os arquivos de áudio selecionados (marcados)")
        self.btn_analyze_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_selected.clicked.connect(self.analyze_selected_audios)
        batch_btn_layout.addWidget(self.btn_analyze_selected, 1)

        self.btn_abort_batch = QPushButton("✕ Abortar")
        self.btn_abort_batch.setObjectName("summaryAbortAction")
        self.btn_abort_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abort_batch.setFixedHeight(28)
        self.btn_abort_batch.setToolTip("Cancelar a análise em lote em andamento")
        self.btn_abort_batch.setVisible(False)
        batch_btn_layout.addWidget(self.btn_abort_batch)

        left_layout.addLayout(batch_btn_layout)

        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(14, 14, 14, 10)
        right_layout.setSpacing(10)

        # SUMMARY CARD
        self.summary_card = QFrame()
        self.summary_card.setObjectName("summaryCard")
        summary = QHBoxLayout(self.summary_card)
        summary.setContentsMargins(12, 10, 12, 10)
        summary.setSpacing(10)

        summary_info = QVBoxLayout()
        summary_info.setSpacing(2)
        self.lbl_eyebrow = QLabel("Arquivo em Análise")
        self.lbl_eyebrow.setObjectName("eyebrow")
        self.lbl_summary_file = QLabel("Nenhum arquivo selecionado")
        self.lbl_summary_file.setObjectName("summaryFile")
        self.lbl_summary_meta = QLabel("Carregue um arquivo WAV para iniciar a análise")
        self.lbl_summary_meta.setObjectName("summaryMeta")
        for _label in (self.lbl_eyebrow, self.lbl_summary_file, self.lbl_summary_meta):
            _label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            _label.setAutoFillBackground(False)
        summary_info.addWidget(self.lbl_eyebrow)
        summary_info.addWidget(self.lbl_summary_file)
        self.lbl_summary_meta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        summary_info.addWidget(self.lbl_summary_meta)
        summary.addLayout(summary_info, 1)

        actions_box = QWidget()
        actions_box.setObjectName("actionsBox")
        actions_box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        actions_layout = QVBoxLayout(actions_box)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)

        # Linha 1: Pipeline Analítico — Reanalisar e Abortar à esquerda; IA e Correções alinhados à direita
        row_analysis = QHBoxLayout()
        row_analysis.setContentsMargins(0, 0, 0, 0)
        row_analysis.setSpacing(6)

        self.btn_reanalisar_main = QPushButton("Analisar")
        self.btn_reanalisar_main.setObjectName("summaryPrimaryAction")
        self.btn_reanalisar_main.setIcon(make_ui_icon("play", color="#FFFFFF", size=15))
        self.btn_reanalisar_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reanalisar_main.setFixedHeight(26)
        self.btn_reanalisar_main.setToolTip("Executar análise deste áudio")
        row_analysis.addWidget(self.btn_reanalisar_main)

        # Botão Abortar Análise (ao lado direto de Reanalisar, visível apenas durante análise)
        self.btn_abort_analysis = QPushButton("✕ Abortar")
        self.btn_abort_analysis.setObjectName("summaryAbortAction")
        self.btn_abort_analysis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abort_analysis.setFixedHeight(26)
        self.btn_abort_analysis.setToolTip("Cancelar a análise em andamento")
        self.btn_abort_analysis.setVisible(False)
        row_analysis.addWidget(self.btn_abort_analysis)

        row_analysis.addStretch()

        self.btn_toggle_ml = QPushButton()
        self.btn_toggle_ml.setObjectName("summaryToggleMl")
        self.btn_toggle_ml.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_ml.setFixedHeight(26)
        self.btn_toggle_ml.clicked.connect(self.toggle_machine_learning)
        row_analysis.addWidget(self.btn_toggle_ml)

        self.btn_learn_corrections = QPushButton(I18N[self.lang]["learn_corrections"])
        self.btn_learn_corrections.setObjectName("summaryAction")
        init_sec_icon = "#FFFFFF" if self.theme_mode == "dark" else "#334155"
        self.btn_learn_corrections.setIcon(make_ui_icon("brain", color=init_sec_icon, size=14))
        self.btn_learn_corrections.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_learn_corrections.setFixedHeight(26)
        self.btn_learn_corrections.setToolTip("Treinar classificador com base nas correções manuais de pulsos")
        row_analysis.addWidget(self.btn_learn_corrections)

        actions_layout.addLayout(row_analysis)

        # Linha 2: Operações, Exportação e Exibição de Gráficos (alocados da direita para a esquerda)
        row_tools = QHBoxLayout()
        row_tools.setContentsMargins(0, 0, 0, 0)
        row_tools.setSpacing(6)
        row_tools.addStretch()

        self.btn_sync = QPushButton()
        self.btn_sync.setObjectName("btn_sync")
        self.btn_sync.setIcon(make_ui_icon("sync", color="#CBD5E1" if self.theme_mode == "dark" else "#475569", size=14))
        self.btn_sync.setCheckable(True)
        self.btn_sync.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.setFixedSize(26, 26)
        self.btn_sync.setToolTip("Sincronizar gráficos no eixo X")
        row_tools.addWidget(self.btn_sync)

        self.btn_export_main = QPushButton("Exportar ▾")
        self.btn_export_main.setObjectName("summaryAction")
        self.btn_export_main.setIcon(make_ui_icon("export", color=init_sec_icon, size=14))
        self.btn_export_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_main.setFixedHeight(26)
        self.btn_export_main.setToolTip("Exportar dados e relatórios em PDF ou TXT")
        self.btn_export_main.clicked.connect(self.show_export_menu)
        row_tools.addWidget(self.btn_export_main)

        self.btn_plots_menu = QPushButton("Gráficos ▾" if self.lang == "pt" else "Graphs ▾")
        self.btn_plots_menu.setObjectName("summaryAction")
        self.btn_plots_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plots_menu.setFixedHeight(26)
        self.btn_plots_menu.setToolTip("Exibir, ocultar ou restaurar layout dos gráficos")
        self.btn_plots_menu.clicked.connect(self.show_plots_menu)
        row_tools.addWidget(self.btn_plots_menu)

        actions_layout.addLayout(row_tools)

        summary.addWidget(actions_box)

        divider = QLabel("│")
        divider.setObjectName("metricDivider")
        summary.addWidget(divider)

        metrics = QVBoxLayout()
        metrics.setSpacing(1)
        self.lbl_metric_title = QLabel("Chilreios Totais")
        self.lbl_metric_title.setObjectName("metricTitle")
        self.lbl_total = QLabel("—")
        self.lbl_total.setObjectName("metricValue")
        self.lbl_metric_sub = QLabel("Moda: —   |   Média: —")
        self.lbl_metric_sub.setObjectName("metricSub")
        self.lbl_model_status = QLabel("")
        self.lbl_model_status.setObjectName("metricSub")
        for _label in (self.lbl_metric_title, self.lbl_total, self.lbl_metric_sub, self.lbl_model_status):
            _label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            _label.setAutoFillBackground(False)
        metrics.addWidget(self.lbl_metric_title)
        metrics.addWidget(self.lbl_total)
        metrics.addWidget(self.lbl_metric_sub)
        metrics.addWidget(self.lbl_model_status)
        summary.addLayout(metrics)
        right_layout.addWidget(self.summary_card)

        # DASHBOARD: Painel principal + pilha lateral livremente redimensionáveis com QSplitter
        self.dashboard_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.dashboard_splitter.setObjectName("dashboardSplitter")
        self.dashboard_splitter.setChildrenCollapsible(False)
        self.dashboard_splitter.setOpaqueResize(True)
        self.dashboard_splitter.splitterMoved.connect(self._on_dashboard_splitter_moved)
        right_layout.addWidget(self.dashboard_splitter, 1)

        self.main_host = QWidget()
        self.main_host.setObjectName("mainHostWidget")
        self.main_host_layout = QVBoxLayout(self.main_host)
        self.main_host_layout.setContentsMargins(0, 0, 0, 0)
        self.main_host_layout.setSpacing(0)

        self.stack_splitter = QSplitter(Qt.Orientation.Vertical)
        self.stack_splitter.setObjectName("stackSplitter")
        self.stack_splitter.setChildrenCollapsible(False)
        self.stack_splitter.setOpaqueResize(True)
        self.stack_splitter.splitterMoved.connect(self._on_dashboard_splitter_moved)

        self.dashboard_splitter.addWidget(self.main_host)
        self.dashboard_splitter.addWidget(self.stack_splitter)
        self.dashboard_splitter.setStretchFactor(0, 3)
        self.dashboard_splitter.setStretchFactor(1, 1)

        self.panel_wave = PlotPanel("wave", self.lang, self.swap_main_panel)
        self.panel_hist = PlotPanel("hist", self.lang, self.swap_main_panel)
        self.panel_freq = PlotPanel("freq", self.lang, self.swap_main_panel)
        self.panel_spec = PlotPanel("spec", self.lang, self.swap_main_panel, main=True)
        self.all_panels = [self.panel_wave, self.panel_hist, self.panel_freq, self.panel_spec]

        # Configuração padrão: apenas Espectrograma (principal) e Histograma (lateral) visíveis
        self.panel_wave._user_closed = True
        self.panel_wave.hide()
        self.panel_freq._user_closed = True
        self.panel_freq.hide()

        self.main_panel = self.panel_spec
        self.stack_panels = [self.panel_hist, self.panel_wave, self.panel_freq]
        self._rebuild_panel_layout()
        self._draw_empty_plots()

        for panel in self.all_panels:
            # O histograma é deliberadamente fixo: sem drag e sem zoom.
            if panel is self.panel_hist:
                continue

        from ui.panels import AudioTransportPanel
        self.transport_panel = AudioTransportPanel()
        self.transport_panel.play_toggled.connect(self.toggle_playback)
        self.transport_panel.speed_cycled.connect(self.cycle_playback_speed)
        self.transport_panel.volume_changed.connect(lambda val: self.audio_output.setVolume(val / 100.0))
        self.transport_panel.position_seeked.connect(self.set_position)
        
        right_layout.addWidget(self.transport_panel)

        self.left_panel.setMinimumWidth(220)
        self.left_panel.setMaximumWidth(450)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([260, 1220])
        self.btn_collapse.setIcon(make_ui_icon("chevron_left", size=18))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        # slider legado mantido para compatibilidade com as rotinas existentes;
        # a interação visual principal ocorre na TimelineWidget.
        self.slider.setRange(0, 0)
        self.slider.setVisible(False)
        self._on_playback_state(self.player.playbackState())
        
        # Sincroniza labels e botões de IA agora que todos estão criados
        self.update_ml_toggle_ui()

    @staticmethod
    def _file_icon():
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#AEB4BD"))
        painter.setBrush(QColor("#AEB4BD"))
        painter.drawRoundedRect(4, 2, 10, 14, 2, 2)
        painter.setPen(QColor("#17191C"))
        painter.drawLine(7, 7, 11, 7)
        painter.drawLine(7, 10, 11, 10)
        painter.end()
        return QIcon(pix)

    def _rebuild_panel_layout(self):
        """Reposiciona os cards nos splitters sem disparar renderizações intermediárias.
        Isso evita reentrância/lock quando a sincronização X está ativa."""
        # Apenas removemos do layout, sem setParent(None) que causa lags massivos no SO
        while self.main_host_layout.count():
            item = self.main_host_layout.takeAt(0)

        if self.main_panel is not None:
            self.main_host_layout.addWidget(self.main_panel)
            self.main_panel.set_main(True)
            if not getattr(self.main_panel, "_user_closed", False):
                self.main_panel.show()
            else:
                self.main_panel.hide()

        for panel in self.stack_panels:
            if panel is not self.main_panel:
                self.stack_splitter.addWidget(panel)
                panel.set_main(False)
                if not getattr(panel, "_user_closed", False):
                    panel.show()
                else:
                    panel.hide()

        self.main_host_layout.activate()
        self.main_host.updateGeometry()
        self.stack_splitter.updateGeometry()
        self._update_plot_visibility_state()
        self._update_plot_menu_checks()
        # Atrasa update de foco para evitar cascata de setVisible/repaint durante arrastar splitter
        self._schedule_focus_update()

    def swap_main_panel(self, panel):
        if panel is self.main_panel or getattr(self, "_swapping_panels", False):
            return

        self._swapping_panels = True
        try:
            # Interrompe renderizações LOD pendentes antes de reparentar os canvases.
            if self.plot_renderers.line_engine is not None:
                self.plot_renderers.line_engine.debounce_timer.stop()
            if self.plot_renderers.spectro_engine is not None:
                self.plot_renderers.spectro_engine.debounce_timer.stop()
            if self.plot_renderers.freq_engine is not None:
                self.plot_renderers.freq_engine.debounce_timer.stop()

            old_stack_sizes = self.stack_splitter.sizes()
            old_main = self.main_panel
            old_stack = list(self.stack_panels)
            self.main_panel = panel
            self.stack_panels = [old_main] + [p for p in old_stack if p is not panel]
            self._rebuild_panel_layout()
            self._schedule_focus_update(50)  # Curto delay — já passou pelo rebuild

            if old_stack_sizes and len(old_stack_sizes) == len(self.stack_splitter.sizes()):
                self.stack_splitter.setSizes(old_stack_sizes)

            # Consolida a nova geometria sem permitir callbacks de sincronização
            # durante o reparenting. Em seguida, libera a guarda e faz um único draw.
            # QApplication.processEvents()  # Removido (Preveno de Reentrncia - FASE 11)
            self._swapping_panels = False
            self._refresh_all_canvases()
        finally:
            self._swapping_panels = False

    def move_stack_panel(self, panel, delta):
        """Move a mini janela na pilha lateral para cima (delta=-1) ou para baixo (delta=1)."""
        if panel not in self.stack_panels or getattr(self, "_swapping_panels", False):
            return
        idx = self.stack_panels.index(panel)
        new_idx = idx + delta
        if 0 <= new_idx < len(self.stack_panels):
            self._swapping_panels = True
            try:
                self.stack_panels[idx], self.stack_panels[new_idx] = self.stack_panels[new_idx], self.stack_panels[idx]
                self._rebuild_panel_layout()
                self.apply_plot_geometry()
                for p in self.all_panels:
                    p.canvas.draw_idle()
            finally:
                self._swapping_panels = False

    def reorder_stack_panels(self, source_panel, target_panel):
        """Reordena os painéis da pilha lateral ao soltar (drag & drop fluido)."""
        if source_panel not in self.stack_panels or target_panel not in self.stack_panels:
            return
        if source_panel is target_panel or getattr(self, "_swapping_panels", False):
            return
        self._swapping_panels = True
        try:
            self.stack_panels.remove(source_panel)
            target_idx = self.stack_panels.index(target_panel)
            self.stack_panels.insert(target_idx, source_panel)
            self._rebuild_panel_layout()
            self.apply_plot_geometry()
            for p in self.all_panels:
                p.canvas.draw_idle()
        finally:
            self._swapping_panels = False

    def _on_dashboard_splitter_moved(self, pos, index):
        if not hasattr(self, "_dashboard_splitter_debounce_timer"):
            self._dashboard_splitter_debounce_timer = QTimer(self)
            self._dashboard_splitter_debounce_timer.setSingleShot(True)
            self._dashboard_splitter_debounce_timer.timeout.connect(self._finish_resize_refresh)
        self._dashboard_splitter_debounce_timer.start(80)

    def _get_panel_by_key(self, key: str):
        if key == "wave":
            return getattr(self, "panel_wave", None)
        elif key == "hist":
            return getattr(self, "panel_hist", None)
        elif key == "freq":
            return getattr(self, "panel_freq", None)
        elif key == "spec":
            return getattr(self, "panel_spec", None)
        return None

    def toggle_plot_panel_by_key(self, key: str, visible: bool):
        panel = self._get_panel_by_key(key)
        if panel is not None:
            self.toggle_plot_panel(panel, visible)

    def toggle_plot_panel(self, panel, visible: bool):
        if visible:
            self.show_plot_panel(panel)
        else:
            self.close_plot_panel(panel)

    def close_plot_panel(self, panel):
        """Oculta/fecha um painel individual do dashboard."""
        if panel is None:
            return
        panel._user_closed = True
        panel.hide()

        # Se o painel fechado era o main_panel, promove o primeiro painel visível da pilha lateral
        if panel is self.main_panel:
            next_main = None
            for p in self.stack_panels:
                if not getattr(p, "_user_closed", False):
                    next_main = p
                    break

            if next_main is not None:
                old_main = self.main_panel
                self.stack_panels = [p for p in self.stack_panels if p is not next_main]
                self.stack_panels.append(old_main)
                self.main_panel = next_main
                self._rebuild_panel_layout()
                self.apply_plot_geometry()
                self._refresh_all_canvases()
            else:
                self.main_panel = None
                self._update_plot_visibility_state()
        else:
            self._update_plot_visibility_state()

        self._schedule_focus_update()
        self._update_plot_menu_checks()

    def show_plot_panel(self, panel):
        """Reabre/exibe um painel previamente fechado."""
        if panel is None:
            return
        panel._user_closed = False

        if self.main_panel is None or getattr(self.main_panel, "_user_closed", False):
            if self.main_panel is not None and self.main_panel is not panel:
                if self.main_panel not in self.stack_panels:
                    self.stack_panels.append(self.main_panel)
            self.main_panel = panel
            if panel in self.stack_panels:
                self.stack_panels.remove(panel)
        else:
            if panel is not self.main_panel and panel not in self.stack_panels:
                self.stack_panels.append(panel)

        panel.show()
        self._rebuild_panel_layout()
        self._update_plot_visibility_state()
        self._schedule_focus_update()
        self._refresh_all_canvases()
        self._update_plot_menu_checks()

    def _update_plot_visibility_state(self):
        """Ajusta a visibilidade dos splitters conforme painéis abertos."""
        main_vis = (self.main_panel is not None and not getattr(self.main_panel, "_user_closed", False))
        self.main_host.setVisible(main_vis)

        visible_stack = [p for p in self.stack_panels if not getattr(p, "_user_closed", False)]
        self.stack_splitter.setVisible(len(visible_stack) > 0)
        self.dashboard_splitter.setVisible(main_vis or len(visible_stack) > 0)

        # Se ambos estão visíveis, garante proporções válidas no dashboard_splitter
        if main_vis and len(visible_stack) > 0:
            sizes = self.dashboard_splitter.sizes()
            if len(sizes) == 2 and (sizes[1] <= 10 or sizes[0] <= 10):
                w = max(500, self.dashboard_splitter.width())
                self.dashboard_splitter.setSizes([int(w * 0.68), int(w * 0.32)])

    def _update_plot_menu_checks(self):
        """Sincroniza o estado marcado dos menus com a visibilidade dos gráficos."""
        if hasattr(self, "action_view_wave") and hasattr(self, "panel_wave"):
            self.action_view_wave.blockSignals(True)
            self.action_view_wave.setChecked(not getattr(self.panel_wave, "_user_closed", False))
            self.action_view_wave.blockSignals(False)
        if hasattr(self, "action_view_hist") and hasattr(self, "panel_hist"):
            self.action_view_hist.blockSignals(True)
            self.action_view_hist.setChecked(not getattr(self.panel_hist, "_user_closed", False))
            self.action_view_hist.blockSignals(False)
        if hasattr(self, "action_view_freq") and hasattr(self, "panel_freq"):
            self.action_view_freq.blockSignals(True)
            self.action_view_freq.setChecked(not getattr(self.panel_freq, "_user_closed", False))
            self.action_view_freq.blockSignals(False)
        if hasattr(self, "action_view_spec") and hasattr(self, "panel_spec"):
            self.action_view_spec.blockSignals(True)
            self.action_view_spec.setChecked(not getattr(self.panel_spec, "_user_closed", False))
            self.action_view_spec.blockSignals(False)

    def reset_plot_layout(self):
        """Restaura o layout padrão: Espectrograma como principal e Histograma na lateral."""
        if not hasattr(self, "all_panels"):
            return

        self.panel_spec._user_closed = False
        self.panel_hist._user_closed = False
        self.panel_wave._user_closed = True
        self.panel_freq._user_closed = True

        self.main_panel = self.panel_spec
        self.stack_panels = [self.panel_hist, self.panel_wave, self.panel_freq]

        self._rebuild_panel_layout()
        self.main_host.show()
        self.stack_splitter.show()
        self.dashboard_splitter.show()

        # Restaura proporção horizontal: 68% main, 32% lateral (+10% histograma)
        total_w = self.dashboard_splitter.width()
        if total_w < 300:
            total_w = 1200
        self.dashboard_splitter.setSizes([int(total_w * 0.68), int(total_w * 0.32)])

        total_h = self.stack_splitter.height()
        if total_h < 200:
            total_h = 750
        self.stack_splitter.setSizes([total_h, 0, 0])

        # QApplication.processEvents()  # Removido (Preveno de Reentrncia - FASE 11)
        self.apply_plot_geometry()
        self._schedule_focus_update()
        self._refresh_all_canvases()
        self._update_plot_menu_checks()

    def show_plots_menu(self):
        """Exibe/oculta o dropdown de gráficos (toggle: clique abre, outro clique fecha)."""
        now = time.time()
        if now - getattr(self, "_plots_menu_last_close_time", 0.0) < 0.25:
            return

        # Fecha se já está aberto
        if getattr(self, "_plots_menu_open", False):
            if hasattr(self, "_plots_menu_ref") and self._plots_menu_ref is not None:
                self._plots_menu_ref.close()
            self._plots_menu_open = False
            return

        menu = QMenu(self)
        menu.setObjectName("plotsDropdownMenu")

        panels_info = [
            ("spec", "Espectrograma Focal" if self.lang == "pt" else "Focal Spectrogram", self.panel_spec),
            ("hist", "Histograma de Intervalos" if self.lang == "pt" else "Interval Histogram", self.panel_hist),
            ("wave", "Forma de Onda" if self.lang == "pt" else "Waveform", self.panel_wave),
            ("freq", "Espectro de Potência (PSD)" if self.lang == "pt" else "Power Spectral Density (PSD)", self.panel_freq),
        ]
        for key, label, panel in panels_info:
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(not getattr(panel, "_user_closed", False))
            act.toggled.connect(lambda checked, p=panel: self.toggle_plot_panel(p, checked))

        menu.addSeparator()
        act_reset = menu.addAction("↺ Restaurar Layout Padrão" if self.lang == "pt" else "↺ Reset Default Layout")
        act_reset.triggered.connect(self.reset_plot_layout)

        def _on_close():
            self._plots_menu_open = False
            self._plots_menu_last_close_time = time.time()

        menu.aboutToHide.connect(_on_close)
        self._plots_menu_ref = menu
        self._plots_menu_open = True
        menu.popup(self.btn_plots_menu.mapToGlobal(self.btn_plots_menu.rect().bottomLeft()))

    def _fit_all_plots_to_layout(self):
        if not self.ctx.active_heavy_data:
            return
        d=self.ctx.active_heavy_data; duration=max(0.001,float(d.get("duration",0.0))); p=d.get("params",{})
        self.panel_wave.ax.set_xlim(0.0,duration); self.panel_wave.ax.set_ylim(-1.05,1.05)
        if len(d.get("t_spec",[])):
            self.panel_spec.ax.set_xlim(float(d["t_spec"][0]),float(d["t_spec"][-1]))
        if p:
            spec_unit = getattr(self.panel_spec, "spec_unit", "kHz")
            rate = float(d.get("rate", 44100.0))
            nyq = rate / 2.0
            ymin_f = 0.0
            ymax_f = nyq
                
            if spec_unit == "kHz":
                self.panel_spec.ax.set_ylim(ymin_f / 1000.0, ymax_f / 1000.0)
            else:
                self.panel_spec.ax.set_ylim(ymin_f, ymax_f)
                
            if hasattr(self.panel_spec, "spin_spec_ymin") and hasattr(self.panel_spec, "spin_spec_ymax"):
                self.panel_spec.spin_spec_ymin.blockSignals(True)
                self.panel_spec.spin_spec_ymax.blockSignals(True)
                self.panel_spec.spin_spec_ymin.setValue(ymin_f / 1000.0 if spec_unit == "kHz" else ymin_f)
                self.panel_spec.spin_spec_ymax.setValue(ymax_f / 1000.0 if spec_unit == "kHz" else ymax_f)
                self.panel_spec.spin_spec_ymin.blockSignals(False)
                self.panel_spec.spin_spec_ymax.blockSignals(False)
            
            # Garante que o preset visual "Total" esteja marcado, se houver painel
            if hasattr(self.panel_spec, "btn_spec_preset_full"):
                self.panel_spec._set_active_preset(self.panel_spec.btn_spec_preset_full)
        if len(d.get("chirps",[])):
            vals=np.asarray(d["chirps"]); self.panel_hist.ax.set_xlim(float(vals.min())-0.65,float(vals.max())+0.65)
            ymax=max(1,int(np.bincount(vals.astype(int)).max()) if vals.size else 1); self.panel_hist.ax.set_ylim(0,ymax*1.20)

    def apply_plot_geometry(self):
        """Enquadra os gráficos de forma adaptativa ao tamanho real de cada canvas.

        Garante proporções perfeitas para mini janelinhas sem cortar rótulos, títulos nem ticks.
        """
        if not hasattr(self, "all_panels"):
            return

        for panel in self.all_panels:
            fig = panel.figure
            fig.set_layout_engine(None)
            fig.set_constrained_layout(False)

            w = max(1, panel.canvas.width())
            h = max(1, panel.canvas.height())
            is_main = (panel is self.main_panel)

            if is_main:
                # Painel principal central (amplo)
                right = 1.0 - max(0.015, min(0.04, 16.0 / w))
                top = 1.0 - max(0.03, min(0.08, 18.0 / h))
                if panel is self.panel_hist:
                    left = max(0.06, min(0.12, 50.0 / w))
                    bottom = max(0.12, min(0.20, 50.0 / h))
                elif panel in (self.panel_spec, self.panel_freq):
                    left = max(0.08, min(0.15, 70.0 / w))
                    bottom = max(0.10, min(0.18, 44.0 / h))
                else:  # panel_wave
                    left = max(0.07, min(0.13, 60.0 / w))
                    bottom = max(0.10, min(0.18, 44.0 / h))
                font_size = 8.5
            else:
                # Mini janelinhas na coluna lateral direita
                top = 1.0 - max(0.04, min(0.10, 12.0 / h))
                right = 1.0 - max(0.02, min(0.05, 10.0 / w))

                if panel is self.panel_hist:
                    left = max(0.11, min(0.20, 40.0 / w))
                    bottom = max(0.24, min(0.40, 48.0 / h))
                elif panel in (self.panel_freq, self.panel_spec):
                    left = max(0.18, min(0.30, 64.0 / w))
                    bottom = max(0.22, min(0.35, 38.0 / h))
                else:  # panel_wave
                    left = max(0.14, min(0.24, 48.0 / w))
                    bottom = max(0.22, min(0.35, 38.0 / h))

                font_size = 6.8 if (w < 260 or h < 130) else 7.5

            fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom)

            tick_pad = 1.5 if not is_main else 2.5
            tick_len = 2.0 if not is_main else 3.0
            panel.ax.tick_params(labelsize=font_size, pad=tick_pad, length=tick_len)
            if hasattr(panel.ax, "xaxis") and panel.ax.xaxis.label is not None:
                panel.ax.xaxis.label.set_size(font_size + 0.5)
            if hasattr(panel.ax, "yaxis") and panel.ax.yaxis.label is not None:
                panel.ax.yaxis.label.set_size(font_size + 0.5)
                panel.ax.yaxis.labelpad = 3.0

            panel.canvas.updateGeometry()

    def _draw_empty_plots(self):
        """Inicializa os 4 painéis gráficos com enquadramento perfeito mesmo sem áudio carregado."""
        if not hasattr(self, "all_panels"):
            return
        if hasattr(self, "nav_controller") and self.nav_controller is not None:
            self.nav_controller.reset()
        else:
            pass
        for p in self.all_panels:
            p.ax.clear()
            p.apply_dark_theme()

        self.panel_wave.ax.set_xlim(0.0, 10.0)
        self.panel_wave.ax.set_ylim(-1.05, 1.05)
        self.panel_wave.ax.set_xlabel("seconds")
        self.panel_wave.ax.set_ylabel("Amplitude")

        self.panel_hist.ax.set_xlim(1.5, 6.5)
        self.panel_hist.ax.set_ylim(0, 10)
        self.panel_hist.ax.set_xticks([2, 3, 4, 5, 6])
        self.panel_hist.ax.set_xlabel("")
        self.panel_hist.ax.set_ylabel("")

        self.panel_freq.ax.set_xlim(0.0, 10.0)
        self.panel_freq.ax.set_ylim(-120, 0)
        self.panel_freq.ax.set_xlabel("Frequency (kHz)")
        self.panel_freq.ax.set_ylabel("Power (dB/Hz)")

        self.panel_spec.ax.set_xlim(0.0, 10.0)
        self.panel_spec.ax.set_ylim(3200, 6000)
        self.panel_spec.ax.set_xlabel("seconds")
        self.panel_spec.ax.set_ylabel("Hz")

        self.apply_plot_geometry()
        for p in self.all_panels:
            p.canvas.draw_idle()

    def _refresh_all_canvases(self):
        if getattr(self, '_refreshing_canvases', False):
            return
        self._refreshing_canvases = True
        try:
            self.setUpdatesEnabled(False)
            self.main_host_layout.activate()
            if hasattr(self, "stack_splitter"):
                self.stack_splitter.updateGeometry()
            elif hasattr(self, "stack_layout"):
                self.stack_layout.activate()
            self._fit_all_plots_to_layout()
            self.apply_plot_geometry()
            for panel in self.all_panels:
                panel.canvas.updateGeometry()
                panel.figure.set_constrained_layout(False)
                panel.canvas.draw()
            if self.ctx.active_heavy_data:
                self.nav_controller.capture_backgrounds()
        finally:
            self.setUpdatesEnabled(True)
            self._refreshing_canvases = False
            self.update()

    # ---------- textos / sidebar ----------
    def refresh_ui_texts(self):
        l = self.lang
        self.lbl_arquivos.setText(I18N[l]["files"].replace("🎧 ", ""))
        self.btn_reanalisar_main.setText("Reanalisar")
        self.btn_learn_corrections.setText(I18N[l]["learn_corrections"])
        self.btn_sync.setText(I18N[l]["sync"].replace("🔗 ", ""))
        self.lbl_metric_title.setText("Chilreios Totais" if l == "pt" else "Total Chirps")
        for p in self.all_panels:
            p.update_lang(l)
        self.update_menu_text()

    def toggle_sidebar(self):
        sizes = self.splitter.sizes()
        if sizes and sizes[0] <= 10:
            self.left_panel.setMinimumWidth(220)
            self.left_panel.setMaximumWidth(450)
            self.splitter.setSizes([260, max(700, self.width() - 260)])
            self.btn_collapse.setIcon(make_ui_icon("chevron_left", size=18))
            self.btn_collapse.setToolTip("Ocultar painel de arquivos")
        else:
            self.left_panel.setMinimumWidth(0)
            self.splitter.setSizes([0, self.width()])
            self.btn_collapse.setIcon(make_ui_icon("chevron_right", size=18))
            self.btn_collapse.setToolTip("Mostrar painel de arquivos")

    # ---------- arquivos ----------
    def _get_item_filename(self, item):
        if not item:
            return None
        widget = self.list_widget.itemWidget(item)
        if widget and hasattr(widget, "filename"):
            return widget.filename
        return item.data(Qt.ItemDataRole.UserRole) or item.text()

    def update_audio_list_active_states(self, active_filename):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and hasattr(widget, "set_active"):
                is_act = (widget.filename == active_filename)
                widget.set_active(is_act)

    def _add_audio_file_item(self, filename, is_checked=False):
        """Adiciona um item com card de áudio e botões de ação externos à lista."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = self._get_item_filename(item)
            if name == filename:
                return item

        item = QListWidgetItem(self.list_widget)
        item.setText("")  # Deixa vazio no QListWidgetItem para evitar sobreposição visual
        item.setData(Qt.ItemDataRole.UserRole, filename)
        item.setSizeHint(QSize(0, 36))

        widget = AudioListItemWidget(
            filename,
            is_checked=is_checked,
            is_active=False,
            on_toggle=self.on_file_check_toggled,
            on_delete=self.remove_audio_by_name,
            on_select=self.select_file_by_name
        )
        self.list_widget.setItemWidget(item, widget)
        self._update_select_all_visibility()
        return item

    def get_checked_files(self):
        """Retorna os nomes dos arquivos que estão marcados com a caixinha de seleção."""
        checked = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            widget = self.list_widget.itemWidget(item)
            if widget and hasattr(widget, "is_checked") and widget.is_checked():
                checked.append(widget.filename)
        return checked

    def _update_select_all_visibility(self):
        """Exibe o controle 'Selecionar tudo' apenas quando houver pelo menos 1 arquivo marcado."""
        if not hasattr(self, 'container_select_all') or not hasattr(self, 'chk_select_all'):
            return
        checked = self.get_checked_files()
        total_count = self.list_widget.count() if hasattr(self, 'list_widget') else 0

        has_any_checked = (len(checked) > 0)
        self.container_select_all.setVisible(has_any_checked)

        self.chk_select_all.blockSignals(True)
        if total_count > 0 and len(checked) == total_count:
            self.chk_select_all.setChecked(True)
        else:
            self.chk_select_all.setChecked(False)
        self.chk_select_all.blockSignals(False)

    def on_file_check_toggled(self, filename, is_checked):
        self._update_select_all_visibility()

    def toggle_select_all_files(self, state):
        checked = (state == Qt.CheckState.Checked.value or state == 2 or state is True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            widget = self.list_widget.itemWidget(item)
            if widget and hasattr(widget, "checkbox"):
                widget.checkbox.blockSignals(True)
                widget.set_checked(checked)
                widget.checkbox.blockSignals(False)
        self._update_select_all_visibility()

    def select_file_by_name(self, filename):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = self._get_item_filename(item)
            if name == filename:
                self.list_widget.setCurrentItem(item)
                self.update_audio_list_active_states(filename)
                break

    def analyze_selected_audios(self):
        """Analisa em lote todos os áudios marcados com a caixinha de seleção em background sem travar a interface."""
        checked_files = self.get_checked_files()
        if not checked_files:
            QMessageBox.warning(
                self,
                "Nenhum áudio selecionado",
                "Marque a caixinha de pelo menos um áudio na lista para analisar."
            )
            return

        # Desativa a ferramenta de edição caso esteja ativa
        self.editor_controller.update_pulse_edit_buttons(None)

        for fname in checked_files:
            w = self._get_item_widget_by_name(fname)
            if w and hasattr(w, "set_loading"):
                w.set_loading(True)

        if hasattr(self, "btn_analyze_selected"):
            self.btn_analyze_selected.setEnabled(False)

        spinner = ButtonSpinner(self.btn_analyze_selected, "Analisando em lote...")
        spinner.start()
        self._batch_spinner = spinner

        # Delega inteiramente ao PipelineOrchestrator sem tocar no GenericWorker
        self.pipeline.run_batch_analysis(checked_files, self.ctx.algo_params)

    def remove_audio(self):
        curr_item = self.list_widget.currentItem()
        if not curr_item:
            return
        fname = self._get_item_filename(curr_item)
        self.remove_audio_by_name(fname)

    def remove_audio_by_name(self, fname):
        if not fname:
            return
        if self.player.source().toLocalFile() == self.ctx.loaded_files.get(fname):
            self.player.stop()
            self.transport_panel.btn_play.setEnabled(False)
            self._update_play_icon()
            self.slider.setValue(0)
        self.ctx.loaded_files.pop(fname, None)
        self.ctx.analysis_cache.pop(fname, None)
        self.ctx.corrections_by_file.pop(fname, None)

        # Remove o item da lista
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = self._get_item_filename(item)
            if name == fname:
                self.list_widget.takeItem(i)
                break

        self._update_select_all_visibility()

        if self.list_widget.count() == 0:
            self.ctx.active_heavy_data = {}
            self.ctx.peaks_detected = []
            self.ctx.peaks_user_verified = []
            self.ctx.active_filename = ""
            for p in self.all_panels:
                p.ax.clear()
                p.canvas.draw_idle()
            self._update_summary_placeholder()
        else:
            if getattr(self.ctx, "active_filename", None) == fname:
                first_item = self.list_widget.item(0)
                if first_item:
                    self.list_widget.setCurrentItem(first_item)
                    next_fname = self._get_item_filename(first_item)
                    self.update_audio_list_active_states(next_fname)

    def action_load_wav(self):
        start_dir = getattr(self, "last_audio_dir", "")
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = ""
        files, _ = QFileDialog.getOpenFileNames(self, "Load Audio Files", start_dir, "WAV Files (*.wav)")
        for file_path in files:
            filename = os.path.basename(file_path)
            self.ctx.loaded_files[filename] = file_path
            self._add_audio_file_item(filename, is_checked=False)
        if files:
            self.last_audio_dir = os.path.dirname(files[0])
            self.save_settings(silent=True)
            target = os.path.basename(files[-1])
            self.select_file_by_name(target)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        loaded_any = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.wav'):
                filename = os.path.basename(file_path)
                self.ctx.loaded_files[filename] = file_path
                self._add_audio_file_item(filename, is_checked=False)
                loaded_any.append(filename)
        if loaded_any:
            first_name = loaded_any[0]
            if first_name in self.ctx.loaded_files:
                self.last_audio_dir = os.path.dirname(self.ctx.loaded_files[first_name])
                self.save_settings(silent=True)
            self.select_file_by_name(loaded_any[-1])
        event.acceptProposedAction()

    def on_file_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        curr_item = selected[0]
        filename = self._get_item_filename(curr_item)
        if not filename:
            return
        self.update_audio_list_active_states(filename)
        self.lbl_summary_file.setText(filename)
        if filename not in self.ctx.loaded_files or not os.path.exists(self.ctx.loaded_files[filename]):
            self.player.stop()
            self.transport_panel.btn_play.setEnabled(False)
            self._update_summary_placeholder(filename)
            return
        self.player.stop()
        self.playback_speed = 1.0
        self.player.setPlaybackRate(1.0)
        self.transport_panel.btn_speed.setText("1×")
        self._update_play_icon()
        self.player.setSource(QUrl.fromLocalFile(self.ctx.loaded_files[filename]))
        self.transport_panel.btn_play.setEnabled(True)

        if filename in self.ctx.analysis_cache:
            self.btn_reanalisar_main.setText("Reanalisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("reload", color="#FFFFFF", size=17))
            self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")
            self.ctx.activate_cached_file(filename)
            carrier_freq = float(self.ctx.active_heavy_data.get("carrier_freq", 0.0))
            tol_val = float(self.ctx.algo_params.get("freq_tolerance_hz", 700.0))
            if hasattr(self, "panel_spec"):
                self.panel_spec.set_carrier_info(carrier_freq, tol_val)
            if hasattr(self, "panel_freq"):
                self.panel_freq.set_carrier_info(carrier_freq, tol_val)
            self.plot_renderers.render_dashboard(filename)
        else:
            self.btn_reanalisar_main.setText("Analisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("play", color="#FFFFFF", size=15))
            self.btn_reanalisar_main.setToolTip("Executar análise deste áudio")
            self.reset_audio_state(filename)
            self._update_summary_ready_for_analysis(filename)

    def reset_audio_state(self, filename):
        """Reinicia atomicamente as variáveis de edição e picos para o arquivo especificado, prevenindo contaminação."""
        self.ctx.active_filename = filename
        stored = self.ctx.corrections_by_file.get(filename)
        if stored is not None:
            self.ctx.peaks_user_verified = list(stored)
        else:
            self.ctx.peaks_user_verified = []

        cached = self.ctx.analysis_cache.get(filename)
        if cached is not None:
            self.ctx.peaks_detected = list(cached.get("peaks_detected", []))
            self.ctx.active_heavy_data = cached
        else:
            self.ctx.peaks_detected = []
            self.ctx.active_heavy_data = None
            self.ctx._adaptive_overrides = {}

        if self.plot_renderers.line_engine:
            self.plot_renderers.line_engine.debounce_timer.stop()
        if self.plot_renderers.spectro_engine:
            self.plot_renderers.spectro_engine.debounce_timer.stop()
        if getattr(self, "freq_engine", None):
            self.plot_renderers.freq_engine.debounce_timer.stop()

    def _get_item_widget_by_name(self, filename):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = self._get_item_filename(item)
            if name == filename:
                return self.list_widget.itemWidget(item)
        return None

    def _update_summary_ready_for_analysis(self, filename):
        self.lbl_summary_file.setText(filename)
        try:
            rate, data = wavfile.read(self.ctx.loaded_files[filename])
            if len(data.shape) > 1:
                data = data[:, 0]
            dur = len(data) / float(rate)
            mins = int(dur // 60)
            secs = dur % 60
            self.lbl_summary_meta.setText(f"Duração: {mins:02d}:{secs:04.1f}   •   Taxa: {int(rate):,} Hz   •   Pronto para análise")
            self.transport_panel.timeline.set_data(dur, [])
        except Exception:
            self.lbl_summary_meta.setText("Áudio carregado • Clique em 'Analisar'")
            self.transport_panel.timeline.set_data(0.0, [])
        self.lbl_total.setText("--")
        self.lbl_metric_sub.setText("Moda: --   |   Média: --")
        for panel in self.all_panels:
            panel.ax.clear()
            panel.canvas.draw_idle()

    # ---------- configurações ----------

    def open_ai_params(self):
        from ui.dialogs import AIParamsDialog
        d = AIParamsDialog(self, self.lang, parent=self)
        d.exec()

    def open_algo_settings(self):
        dialog = AlgoSettingsDialog(self.ctx.algo_params, self.lang, self)
        if dialog.exec():
            new_params = dialog.get_params()
            if new_params != self.ctx.algo_params:
                self.ctx.algo_params = new_params
                if self.ctx.analysis_cache:
                    reply = QMessageBox.question(self, "Reanalisar?", "Configurações alteradas! Deseja refazer as análises no cache?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        curr = self.list_widget.currentItem()
                        curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
                        for fname in list(self.ctx.analysis_cache.keys()):
                            if fname != curr_name:
                                self.ctx.analysis_cache.pop(fname, None)
                        if curr_name and curr_name in self.ctx.loaded_files:
                            self.pipeline.force_reanalyze(curr_name)

    def export_training_model(self):
        """Abre caixa de diálogo para salvar o arquivo com o treinamento ativo."""
        if not hasattr(self, "pulse_learner") or not self.ctx.pulse_learner:
            QMessageBox.warning(self, "Sem Modelo", "Não há módulo de aprendizado ativo.")
            return
        if not self.ctx.pulse_learner.is_trained() and len(self.ctx.pulse_learner.training_features) == 0:
            QMessageBox.warning(self, "Sem Treinamento", "Não há nenhum treinamento de modelo realizado para salvar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Arquivo de Treinamento",
            "modelo_treinado_crinometro.pkl",
            "Modelos Treinados (*.pkl *.crntrain);;Todos os Arquivos (*)"
        )
        if not file_path:
            return

        try:
            self.ctx.pulse_learner.export_model_file(file_path)
            QMessageBox.information(
                self,
                I18N[self.lang]["success"],
                f"Treinamento salvo com sucesso em:\n{file_path}"
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                I18N[self.lang]["error"],
                f"Falha ao exportar arquivo de treinamento:\n{exc}"
            )

    def import_training_model(self):
        """Abre caixa de diálogo para carregar um arquivo de treinamento previamente salvo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Carregar Arquivo de Treinamento",
            "",
            "Modelos Treinados (*.pkl *.crntrain);;Todos os Arquivos (*)"
        )
        if not file_path:
            return

        try:
            self.ctx.pulse_learner.import_model_file(file_path)
            self.editor_controller._adapt_advanced_params()

            n_samples = len(self.ctx.pulse_learner.training_features)
            msg = f"Treinamento carregado com sucesso!\n• Amostras de treino: {n_samples}\n• Classificador Random Forest (500 árvores) ativo."

            # Se houver arquivo carregado, pergunta se deseja reanalisar agora
            curr = self.list_widget.currentItem()
            curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
            if curr_name and curr_name in self.ctx.loaded_files:
                reply = QMessageBox.question(
                    self,
                    "Reanalisar com Novo Treinamento?",
                    msg + "\n\nDeseja reanalisar o áudio atual com este novo modelo de treinamento?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.pipeline.force_reanalyze(curr_name)
            else:
                QMessageBox.information(self, I18N[self.lang]["success"], msg)

        except Exception as exc:
            QMessageBox.critical(
                self,
                I18N[self.lang]["error"],
                f"Falha ao carregar arquivo de treinamento:\n{exc}"
            )

    def reset_learning(self):
        """Reseta completamente o modelo de IA e os dados de treinamento."""
        from PyQt6.QtWidgets import QMessageBox
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        if self.lang == "pt":
            msg_box.setWindowTitle("Atenção: Reset de Aprendizado!")
            msg_box.setText("<b>TODO O APRENDIZADO DA IA SERÁ PERDIDO!</b>")
            msg_box.setInformativeText(
                "Isso apagará definitivamente todo o histórico de correções manuais e as árvores de decisão geradas.\n\n"
                "Recomendamos fortemente que você salve este treinamento em outro local da máquina usando a opção "
                "<b>'Exportar .pkl'</b> antes de prosseguir, para não perdê-lo permanentemente.\n\n"
                "Você tem certeza que deseja executar esta ação?"
            )
            btn_reset = msg_box.addButton("Resetar mesmo assim", QMessageBox.ButtonRole.DestructiveRole)
            btn_abort = msg_box.addButton("Abortar", QMessageBox.ButtonRole.RejectRole)
        else:
            msg_box.setWindowTitle("Warning: Learning Reset!")
            msg_box.setText("<b>ALL AI LEARNING WILL BE LOST!</b>")
            msg_box.setInformativeText(
                "This will permanently erase all manual correction history and the generated decision trees.\n\n"
                "We strongly recommend saving this training somewhere else on your machine using the "
                "<b>'Export .pkl'</b> option before proceeding, so you don't lose it permanently.\n\n"
                "Are you absolutely sure you want to execute this action?"
            )
            btn_reset = msg_box.addButton("Reset anyway", QMessageBox.ButtonRole.DestructiveRole)
            btn_abort = msg_box.addButton("Abort", QMessageBox.ButtonRole.RejectRole)
            
        msg_box.setDefaultButton(btn_abort)
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_reset:
            try:
                if hasattr(self, 'pulse_learner') and self.ctx.pulse_learner:
                    self.ctx.pulse_learner.reset()
                
                # Desativa a IA após o reset para forçar o usuário a trabalhar com DSP puro
                self.ctx.use_machine_learning = False
                self.save_settings(silent=True)
                self.update_ml_toggle_ui()
                
                
                QMessageBox.information(
                    self, 
                    "Reset Concluído", 
                    "O aprendizado de máquina foi completamente zerado. O algoritmo retornou ao estado original DSP."
                )
                
                # Se houver áudio carregado, força reanálise para aplicar o DSP limpo
                curr = self.list_widget.currentItem()
                curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
                if curr_name and curr_name in self.ctx.loaded_files:
                    self.pipeline.force_reanalyze(curr_name)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao resetar a IA:\n{e}")

    def reset_to_defaults(self):
        """Restaura todos os parâmetros para os valores padrão de fábrica,
        apaga o modelo de aprendizado treinado e limpa todas as correções manuais.
        """
        l = self.lang
        reply = QMessageBox.question(
            self,
            I18N[l].get("reset_confirm_title", "Resetar Configurações?"),
            I18N[l].get("reset_confirm_msg", "Deseja resetar para as configurações padrão?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 1. Restaura parâmetros do algoritmo para os padrões originais
        self.ctx.algo_params = DEFAULT_ALGO_PARAMS.copy()
        self.ctx._adaptive_overrides = {}

        # 2. IA e marcações não são resetadas aqui mais

        # 4. Limpa o arquivo de configuração persistido
        try:
            clean_config = {
                "algo_params": self.ctx.algo_params,
                "report_params": self.ctx.report_params,
                "theme": getattr(self, "theme_mode", "dark"),
                "corrections_by_file": {},
                "pulse_learner": None
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(clean_config, f, indent=4, ensure_ascii=False)
        except Exception as exc:
            print(f"Erro ao limpar config: {exc}")

        # 5. Se houver arquivo ativo, reanalisa do zero com os padrões
        curr = self.list_widget.currentItem()
        curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
        if curr_name and curr_name in self.ctx.loaded_files:
            self.ctx.analysis_cache.clear()
            self.pipeline.force_reanalyze(curr_name)
        else:
            self.ctx.analysis_cache.clear()

        if hasattr(self, 'lbl_model_status'):
            self.update_ml_toggle_ui()

        QMessageBox.information(
            self,
            I18N[l]["success"],
            I18N[l].get("reset_done", "Configurações resetadas com sucesso!")
        )

    def open_report_settings(self):
        dialog = GeneralSettingsDialog(self.ctx.report_params, self.lang, self)
        if dialog.exec():
            self.ctx.report_params = dialog.get_params()
            if self.ctx.report_params["lang"] != self.lang:
                self.lang = self.ctx.report_params["lang"]
                self.refresh_ui_texts()

    def open_about(self):
        AboutDialog(self).exec()

    def check_for_updates(self, silent=False):
        """Verifica se há novas atualizações disponíveis no GitHub."""
        self._checker_thread = UpdateCheckerThread(self)

        def _on_available(info):
            dlg = UpdateDialog(info, self)
            dlg.exec()

        def _on_no_update(info):
            if not silent:
                QMessageBox.information(
                    self,
                    "Crinômetro Atualizado",
                    f"Você já está executando a versão mais recente do Crinômetro (v{APP_VERSION_LABEL})!"
                )

        def _on_error(err_msg):
            if not silent:
                QMessageBox.warning(
                    self,
                    "Aviso de Atualização",
                    f"Não foi possível verificar atualizações no momento:\n{err_msg}"
                )

        self._checker_thread.update_available.connect(_on_available)
        self._checker_thread.no_update.connect(_on_no_update)
        self._checker_thread.error.connect(_on_error)
        self._checker_thread.start()


    def load_settings(self):
        """Carrega as configurações persistidas, mantendo os valores padrão quando ausentes."""
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if isinstance(data.get("algo_params"), dict):
                    self.ctx.algo_params.update(data["algo_params"])
                if isinstance(data.get("report_params"), dict):
                    self.ctx.report_params.update(data["report_params"])
                theme = data.get("theme")
                if theme in {"dark", "light"}:
                    self.theme_mode = theme
                corrections = data.get("corrections_by_file")
                if isinstance(corrections, dict):
                    self.ctx.corrections_by_file = {}
                    for name, data_val in corrections.items():
                        if isinstance(data_val, list):
                            # Old format: just a list of peak indices
                            # Or new format if it's a list of dicts
                            parsed = []
                            for p in data_val:
                                if isinstance(p, dict) and "idx" in p:
                                    parsed.append(p)
                                else:
                                    try:
                                        parsed.append(int(p))
                                    except (TypeError, ValueError):
                                        pass
                            self.ctx.corrections_by_file[str(name)] = parsed
                if "pulse_learner" in data:
                    self.ctx.pulse_learner.load_from_config()
                if "last_audio_dir" in data and isinstance(data["last_audio_dir"], str) and os.path.isdir(data["last_audio_dir"]):
                    self.last_audio_dir = data["last_audio_dir"]
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")

    def save_settings(self, silent=False):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            if not isinstance(config, dict):
                config = {}
            config["algo_params"] = self.ctx.algo_params
            config["report_params"] = self.ctx.report_params
            config["theme"] = self.theme_mode
            config["corrections_by_file"] = self.ctx.corrections_by_file
            config["last_audio_dir"] = getattr(self, "last_audio_dir", "")
            if not "pulse_learner" in config:
                config["pulse_learner"] = None
            if self.ctx.pulse_learner.model is not None:
                config["pulse_learner"] = self.ctx.pulse_learner.serialize()
                self.ctx.pulse_learner.save_persisted_training()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            if not silent:
                QMessageBox.information(self, I18N[self.lang]["success"], I18N[self.lang]["config_saved"])
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, I18N[self.lang]["error"], f"Failed to save:\n{e}")

    def toggle_machine_learning(self):
        """Ativa ou desativa a filtragem e classificação por Inteligência Artificial sem forçar reanálise imediata."""
        is_active = not getattr(self.ctx, "use_machine_learning", False)
        if is_active:
            QMessageBox.warning(
                self, 
                "Aviso de IA", 
                "A Inteligência Artificial pode cometer erros!\n\n"
                "Lembre-se de que correções mal feitas pelo usuário podem 'quebrar' as análises da IA e piorar os resultados.\n\n"
                "Recomendação: Se a IA começar a apresentar resultados quebrados ou irregulares, utilize o botão 'Resetar Aprendizado' no menu Opções (Configurações) para restaurar os valores originais do DSP."
            )
        self.ctx.use_machine_learning = is_active
        self.save_settings(silent=True)
        self.update_ml_toggle_ui()

    def update_ml_toggle_ui(self):
        if not hasattr(self, "btn_toggle_ml"):
            return
        is_active = getattr(self.ctx, "use_machine_learning", False)
        self.btn_toggle_ml.setProperty("active", "true" if is_active else "false")
        self.btn_toggle_ml.setStyleSheet("")
        self.btn_toggle_ml.style().unpolish(self.btn_toggle_ml)
        self.btn_toggle_ml.style().polish(self.btn_toggle_ml)
        if is_active:
            self.btn_toggle_ml.setText("🧠 IA: Ativada")
            self.btn_toggle_ml.setToolTip("IA Ativada: filtra ruído e discrimina grilos distantes. Clique para desativar.")
            if hasattr(self, "lbl_model_status"):
                status_txt = "🧠 IA: Ativada (Modelo Supervisionado)" if self.ctx.pulse_learner.is_trained() else "🧠 IA: Ativada (GMM não-supervisionado)"
                self.lbl_model_status.setText(status_txt)
                self.lbl_model_status.setStyleSheet("color: #10B981;")
        else:
            self.btn_toggle_ml.setText("🧠 IA: Desativada")
            self.btn_toggle_ml.setToolTip("IA Desativada: análise executada estritamente por processamento de sinal (DSP). Clique para ativar.")
            if hasattr(self, "lbl_model_status"):
                self.lbl_model_status.setText("🧠 IA: Desativada (Modo DSP)")
                self.lbl_model_status.setStyleSheet("color: #94A3B8;")

    # ---------- análise ----------
    # ---------- análise (delegada ao PipelineOrchestrator) ----------

    def _on_analysis_started(self, filename, is_first_time):
        loading_text = "Analisando..." if is_first_time else "Reanalisando..."
        from ui.widgets import ButtonSpinner
        spinner = ButtonSpinner(self.btn_reanalisar_main, loading_text)
        spinner.start()
        self._reanalyze_spinner = spinner
        self.btn_reanalisar_main.setEnabled(False)
        self.btn_abort_analysis.setVisible(True)

    def _on_pipeline_completed(self, filename):
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        item_widget = self._get_item_widget_by_name(filename)
        if item_widget and hasattr(item_widget, "set_loading"):
            item_widget.set_loading(False)
        if getattr(self, "_reanalyze_spinner", None) is not None:
            self._reanalyze_spinner.stop(make_ui_icon("reload", color="#FFFFFF", size=17), "Reanalisar")
            self._reanalyze_spinner = None
        if hasattr(self, "btn_reanalisar_main"):
            self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")
        if self.ctx.active_filename == filename:
            if self.ctx.active_heavy_data:
                carrier_freq = float(self.ctx.active_heavy_data.get("carrier_freq", 0.0))
                tol_val = float(self.ctx.algo_params.get("freq_tolerance_hz", 700.0))
                if hasattr(self, "panel_spec"):
                    self.panel_spec.set_carrier_info(carrier_freq, tol_val)
                if hasattr(self, "panel_freq"):
                    self.panel_freq.set_carrier_info(carrier_freq, tol_val)
            self.plot_renderers.render_dashboard(filename)
            vp = getattr(self, "_saved_viewport", None)
            if vp is not None and self.ctx.active_heavy_data:
                dur = self.ctx.active_heavy_data.get("duration", 0.0)
                x0, x1 = vp.get("wave_xlim", (0, dur))
                if x1 <= x0: x1 = x0 + 1.0
                self.panel_wave.ax.set_xlim(x0, x1)

                sx0, sx1 = vp.get("spec_xlim", (x0, x1))
                if sx1 <= sx0: sx1 = sx0 + 1.0
                self.panel_spec.ax.set_xlim(sx0, sx1)
                if not getattr(self.panel_spec, "_y_locked", False):
                    self.panel_spec.ax.set_ylim(vp.get("spec_ylim", (0, 10)))

                for p in [self.panel_wave, self.panel_freq, self.panel_spec]:
                    p.canvas.draw()
                self.nav_controller.capture_backgrounds()
                self._saved_viewport = None

    def _on_batch_started(self, total_files):
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(True)
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(True)

    def _on_batch_progress(self, current, total):
        if hasattr(self, "_batch_spinner") and getattr(self._batch_spinner, "button", None) is not None:
            self._batch_spinner.button.setText(f"Analisando... ({current}/{total})")

    def _on_batch_item_completed(self, fname):
        w = self._get_item_widget_by_name(fname)
        if w and hasattr(w, "set_loading"):
            w.set_loading(False)

    def _on_batch_completed(self, success_count, errors):
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(False)
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        if hasattr(self, "btn_analyze_selected"):
            self.btn_analyze_selected.setEnabled(True)

        curr = self.list_widget.currentItem()
        curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
        if curr_name in self.ctx.analysis_cache and hasattr(self, "btn_reanalisar_main"):
            self.btn_reanalisar_main.setText("Reanalisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("reload", color="#FFFFFF", size=17))
            self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")

        pending = getattr(self, "_pending_export_action", None)
        if getattr(self, "_batch_spinner", None) is not None:
            self._batch_spinner.stop()
            self._batch_spinner = None
        if pending:
            self._pending_export_action = None
            if not errors:
                action, args = pending
                if action == 'txt':
                    self._generate_txt_report(self.get_checked_files())

                elif action == 'pdf_modular':
                    cfg, wcsv, cpath, wtxt, tpath, cmode = args if isinstance(args, tuple) and len(args) == 6 else (args[0], args[1], args[2], args[3], args[4], "brazilian") if isinstance(args, tuple) and len(args)==5 else (args, False, None, False, None, "brazilian")
                    self._generate_pdf_report_modular(self.get_checked_files(), cfg, want_csv=wcsv, csv_path=cpath, want_txt=wtxt, txt_path=tpath, csv_mode=cmode)
            else:
                QMessageBox.warning(self, "Falha na Análise", "Não foi possível gerar o relatório pois alguns arquivos falharam na análise.")
            return

        total = success_count + len(errors)
        msg = f"Análise concluída!\n\n• {success_count} de {total} arquivo(s) analisado(s) com sucesso."
        if errors:
            msg += f"\n\nFalhas ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n...e mais {len(errors)-5} erros."
            QMessageBox.warning(self, "Análise em Lote", msg)
        else:
            QMessageBox.information(self, I18N[self.lang]["success"], msg)

    def _on_batch_failed(self, err_msg):
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(False)
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        if hasattr(self, "btn_analyze_selected"):
            self.btn_analyze_selected.setEnabled(True)
        pending = getattr(self, "_pending_export_action", None)
        if getattr(self, "_batch_spinner", None) is not None:
            self._batch_spinner.stop()
            self._batch_spinner = None
        QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha na análise em lote:\n{err_msg}")

    def _on_batch_cancelled(self):
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(False)
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        if hasattr(self, "btn_analyze_selected"):
            self.btn_analyze_selected.setEnabled(True)
        pending = getattr(self, "_pending_export_action", None)
        if getattr(self, "_batch_spinner", None) is not None:
            self._batch_spinner.stop()
            self._batch_spinner = None

    def _on_pipeline_failed(self, filename, err_msg):
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        item_widget = self._get_item_widget_by_name(filename)
        if item_widget and hasattr(item_widget, "set_loading"):
            item_widget.set_loading(False)
        if getattr(self, "_reanalyze_spinner", None) is not None:
            is_first_time = (filename not in self.ctx.analysis_cache)
            restore_text = "Analisar" if is_first_time else "Reanalisar"
            restore_icon = make_ui_icon("play", color="#FFFFFF", size=15) if is_first_time else make_ui_icon("reload", color="#FFFFFF", size=17)
            self._reanalyze_spinner.stop(restore_icon, restore_text)
            self._reanalyze_spinner = None
        QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha na análise:\n{err_msg}")

    def _on_pipeline_cancelled(self, filename):
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(False)
        if getattr(self, "_reanalyze_spinner", None) is not None:
            is_first_time = (filename not in self.ctx.analysis_cache)
            restore_text = "Analisar" if is_first_time else "Reanalisar"
            restore_icon = make_ui_icon("play", color="#FFFFFF", size=15) if is_first_time else make_ui_icon("reload", color="#FFFFFF", size=17)
            self._reanalyze_spinner.stop(restore_icon, restore_text)
            self._reanalyze_spinner = None
        pending = getattr(self, "_pending_export_action", None)
        if getattr(self, "_batch_spinner", None) is not None:
            self._batch_spinner.stop()
            self._batch_spinner = None












    def _on_realtime_tolerance_updated(self, filename):
        d = self.ctx.active_heavy_data
        if not d:
            return
        cf = float(d.get("carrier_freq", 0.0))
        new_tol = float(d.get("params", {}).get("freq_tolerance_hz", 700.0))
        if hasattr(self, "panel_spec"):
            self.panel_spec.set_carrier_info(cf, new_tol)
        if hasattr(self, "panel_freq"):
            self.panel_freq.set_carrier_info(cf, new_tol)

        cur_xlim = self.panel_wave.ax.get_xlim() if hasattr(self, "panel_wave") else None

        if self.ctx.active_filename:
            self.plot_renderers.render_dashboard(self.ctx.active_filename)

        if cur_xlim is not None and cur_xlim[0] is not None and cur_xlim[1] is not None:
            for panel in (self.panel_wave, self.panel_spec):
                if hasattr(panel, "ax"):
                    panel.ax.set_xlim(cur_xlim)
            for panel in self.all_panels:
                panel.canvas.draw_idle()

    def _update_summary_placeholder(self, filename=""):
        self.lbl_summary_file.setText(filename or "Nenhum arquivo selecionado")
        self.lbl_summary_meta.setText("Carregue um arquivo WAV para iniciar a análise")
        self.lbl_total.setText("—")
        self.lbl_metric_sub.setText("Moda: —   |   Média: —")
        if hasattr(self, 'lbl_elapsed'):
            self.transport_panel.lbl_elapsed.setText("00:00.00 / 00:00.00")
        if hasattr(self, 'btn_reanalisar_main'):
            self.btn_reanalisar_main.setText("Analisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("play", color="#FFFFFF", size=15))
            self.btn_reanalisar_main.setToolTip("Executar análise deste áudio")
        self.transport_panel.timeline.set_data(0, [])
        self.transport_panel.timeline.set_position(0)

    # ---------- exportação ----------
    def open_export_graph_dialog(self):
        from ui.dialogs.export_graph_dialog import ExportGraphDialog
        live_view = {}
        if hasattr(self, 'plot_renderers') and hasattr(self.plot_renderers, 'panel_spec') and self.plot_renderers.panel_spec and self.plot_renderers.panel_spec.ax:
            try:
                ax = self.plot_renderers.panel_spec.ax
                live_view['xlim'] = ax.get_xlim()
                live_view['ylim'] = ax.get_ylim()
                live_view['spec_unit'] = getattr(self.plot_renderers.panel_spec, 'spec_unit', 'kHz')
            except Exception:
                QMessageBox.warning(self, "Aviso", "Não foi possível ler a vista atual do espectrograma para o recorte 'Específico'.")
                pass

        dlg = ExportGraphDialog(self.ctx, live_view=live_view, parent=self)
        dlg.exec()


    def _start_batch_for_export(self, unprocessed):
        for fname in unprocessed:
            w = self._get_item_widget_by_name(fname)
            if w and hasattr(w, "set_loading"):
                w.set_loading(True)
        if hasattr(self, "btn_analyze_selected"):
            self.btn_analyze_selected.setEnabled(False)
        from ui.widgets import ButtonSpinner
        spinner = ButtonSpinner(self.btn_export_main, "Analisando pendentes...")
        spinner.start()
        self._batch_spinner = spinner
        self.pipeline.run_batch_analysis(unprocessed, self.ctx.algo_params)

    def action_save_txt(self):
        checked_files = self.get_checked_files()
        if not checked_files:
            QMessageBox.warning(
                self,
                "Nenhum áudio selecionado",
                "Marque a caixinha de pelo menos um arquivo de áudio na lista para gerar o relatório."
            )
            return

        # Analisa em segundo plano qualquer arquivo marcado que ainda não esteja no cache
        unprocessed = [f for f in checked_files if f not in self.ctx.analysis_cache and f in self.ctx.loaded_files]
        if unprocessed:
            self._pending_export_action = ('txt', None)
            self._start_batch_for_export(unprocessed)
            return

        self._generate_txt_report(checked_files)

    def _generate_txt_report(self, checked_files):
        selected_cache = {
            fname: self.ctx.analysis_cache[fname]
            for fname in checked_files
            if fname in self.ctx.analysis_cache
        }

        if not selected_cache:
            QMessageBox.warning(
                self,
                "Sem dados",
                "Nenhum dos áudios selecionados possui dados de análise válidos para o relatório."
            )
            return

        now = datetime.datetime.now()
        default_name = f"Relatorio_Crinometro_{now.strftime('%Y%m%d_%H%M')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(self, I18N[self.lang]["export"], default_name, "Text Files (*.txt)")
        if not file_path:
            return

        with open(file_path, 'w', encoding='utf-8') as f:
            inst = self.ctx.report_params.get('institution', '').strip()
            name = self.ctx.report_params.get('researcher_name', '').strip()
            role = self.ctx.report_params.get('role', '').strip()
            level = self.ctx.report_params.get('level', '').strip()
            header_lines = []
            if inst: header_lines.append(f"Instituição: {inst.upper()}")
            if name: header_lines.append(f"Pesquisador(a): {name}")
            if role: header_lines.append(f"Função: {role}")
            if level: header_lines.append(f"Grau Acadêmico: {level}")
            header_text = "\n".join(header_lines) + "\n\n" if header_lines else ""
            params_list = [d['params'] for d in selected_cache.values()]
            all_same_params = all(p == params_list[0] for p in params_list)
            texto = (
                f"RELATÓRIO MULTIPLEXADO DE ANÁLISE BIOACÚSTICA - CRINÔMETRO\n"
                f"{'='*58}\n"
                f"{header_text}"
                f"Data da Geração: {now.strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"Total de Arquivos Selecionados Compilados: {len(selected_cache)}\n\n"
            )
            def get_pulse_distribution_text(chirps_list):
                unique_p, counts_p = np.unique(chirps_list, return_counts=True)
                return "; ".join([f"{int(cnt)} chilreiro(s) com {int(up)} pulso(s)" for up, cnt in zip(unique_p, counts_p)])
            if all_same_params:
                p = params_list[0]
                texto += (
                    f"1. PARÂMETROS METODOLÓGICOS (CONFIGURAÇÕES GERAIS)\n"
                    f"{'-'*58}\n"
                    f"- Filtro de Amplitude: Mín={p['amp_min']} | Máx={p['amp_max']}\n"
                    f"- Limites de Duração de Pulso: {p['dur_min']}ms a {p['dur_max']}ms\n"
                    f"- Banda de Frequência Analisada: {p['b1_min']}Hz a {p['b1_max']}Hz\n\n"
                    f"2. RESULTADOS POR ÁUDIO SELECIONADO\n"
                    f"{'-'*58}\n\n"
                )
                for fname, d in selected_cache.items():
                    texto += f"• ARQUIVO: {fname}\n  - Duração Total: {d['duration']:.2f} segundos\n  - Chilreios Validados: {len(d['chirps'])}\n  - Moda (Padrão): {d['moda']} pulsos/chilreio | Média: {d['media']:.2f}\n  - Distribuição: {get_pulse_distribution_text(d['chirps'])}\n\n"
            else:
                texto += "RESULTADOS DETALHADOS POR ÁUDIO SELECIONADO\n"
                for fname, d in selected_cache.items():
                    texto += f"Arquivo: {fname} | Chilreios: {len(d['chirps'])}\n"
            f.write(texto)
        QMessageBox.information(self, I18N[self.lang]["success"], f"Relatório gerado com sucesso para {len(selected_cache)} áudio(s) selecionado(s).")

    def show_export_menu(self):
        """Exibe/oculta o dropdown de exportação (toggle: clique abre, outro clique fecha)."""
        now = time.time()
        if now - getattr(self, "_export_menu_last_close_time", 0.0) < 0.25:
            return

        if getattr(self, "_export_menu_open", False):
            if hasattr(self, "_export_menu_ref") and self._export_menu_ref is not None:
                self._export_menu_ref.close()
            self._export_menu_open = False
            return

        menu = QMenu(self)
        menu.setObjectName("exportMenu")
        act_txt = menu.addAction(make_ui_icon("export", color="#64748B", size=15), I18N[self.lang]["export"])
        act_txt.triggered.connect(self.action_save_txt)
        act_pdf_mod = menu.addAction(make_ui_icon("export", color="#0284C7", size=15), "📊 Exportar Relatório Modular...")
        act_pdf_mod.triggered.connect(self.open_export_report_dialog)
        menu.addSeparator()
        act_graphs = menu.addAction(make_ui_icon("export", color="#10B981", size=15), "📊 Exportar Gráficos (PNG/PDF)…")
        act_graphs.triggered.connect(self.open_export_graph_dialog)

        def _on_close():
            self._export_menu_open = False
            self._export_menu_last_close_time = time.time()

        menu.aboutToHide.connect(_on_close)
        self._export_menu_ref = menu
        self._export_menu_open = True
        menu.popup(self.btn_export_main.mapToGlobal(self.btn_export_main.rect().bottomLeft()))


    def open_export_report_dialog(self):
        checked_files = self.get_checked_files()
        if not checked_files:
            QMessageBox.warning(self, "Nenhum áudio", "Marque pelo menos um arquivo na lista para gerar o relatório.")
            return

        from ui.dialogs.export_report_dialog import ExportReportDialog
        dlg = ExportReportDialog(self.ctx, checked_files=checked_files, parent=self)
        if dlg.exec():
            config    = dlg.config
            want_csv  = dlg.export_csv
            csv_path  = dlg.csv_path
            want_txt  = dlg.export_txt
            txt_path  = dlg.txt_path
            csv_mode  = getattr(dlg, 'csv_mode', 'brazilian')
            unprocessed = [f for f in checked_files if f not in self.ctx.analysis_cache and f in self.ctx.loaded_files]
            if unprocessed:
                self._pending_export_action = ('pdf_modular', (config, want_csv, csv_path, want_txt, txt_path, csv_mode))
                self._start_batch_for_export(unprocessed)
                return
            self._generate_pdf_report_modular(checked_files, config, want_csv=want_csv, csv_path=csv_path, want_txt=want_txt, txt_path=txt_path, csv_mode=csv_mode)
            
    def _generate_pdf_report_modular(self, checked_files, config, want_csv=False, csv_path=None, want_txt=False, txt_path=None, csv_mode="brazilian"):
        selected_cache = {fname: self.ctx.analysis_cache[fname] for fname in checked_files if fname in self.ctx.analysis_cache}
        if not selected_cache:
            QMessageBox.warning(self, "Sem dados", "Nenhum dos áudios selecionados possui dados válidos.")
            return

        from core.worker import GenericWorker
        def _task():
            results = []
            if config.output_path:
                from utils.report_generator import generate_pdf_report
                generate_pdf_report(config.output_path, config, selected_cache, self.ctx.algo_params)
                results.append(config.output_path)
            if want_csv and csv_path:
                from utils.report_generator import generate_csv_report
                generate_csv_report(csv_path, selected_cache, config.metadata, csv_mode=csv_mode)
                results.append(csv_path)
            if want_txt and txt_path:
                from utils.report_generator import generate_txt_report
                generate_txt_report(txt_path, selected_cache, config.metadata)
                results.append(txt_path)
            return results

        def _on_finished(paths):
            paths_str = "\n".join(paths) if paths else ""
            QMessageBox.information(self, I18N[self.lang]["success"],
                                    f"Relatório gerado com sucesso!\n\nSalvo em:\n{paths_str}")
            if getattr(self, "_batch_spinner", None) is not None:
                self._batch_spinner.stop()
                self._batch_spinner = None

        def _on_error(err_msg):
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha ao gerar relatório:\n{err_msg}")
            if getattr(self, "_batch_spinner", None) is not None:
                self._batch_spinner.stop()
                self._batch_spinner = None

        worker = GenericWorker(_task)
        self._report_worker = worker
        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)

        if hasattr(self, "btn_export_main"):
            from ui.widgets import ButtonSpinner
            if not getattr(self, "_batch_spinner", None):
                spinner = ButtonSpinner(self.btn_export_main, "Gerando relatório...")
                spinner.start()
                self._batch_spinner = spinner

        worker.start()

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.source().isEmpty():
                return
            self.player.play()

    def _update_play_icon(self):
        if not hasattr(self, "transport_panel"):
            return
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        icon_color = "#FFFFFF" if getattr(self, "theme_mode", "light") == "dark" else "#123B5D"
        self.transport_panel.set_play_icon("pause" if playing else "play", icon_color)

    def _on_playback_state(self, state):
        self._update_play_icon()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_timer.start(10)
        else:
            self.playback_timer.stop()

    def _on_playback_timer_tick(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.update_playback_cursor(self.player.position())

    def cycle_playback_speed(self):
        """Alterna entre velocidade normal e velocidades reduzidas, sem alterar o áudio original."""
        options = [1.0, 0.75, 0.5, 0.25]
        try:
            idx = options.index(round(float(self.playback_speed), 2))
        except ValueError:
            idx = 0
        self.playback_speed = options[(idx + 1) % len(options)]
        self.player.setPlaybackRate(self.playback_speed)
        label = f"{self.playback_speed:g}×" if self.playback_speed != 1.0 else "1×"
        self.transport_panel.btn_speed.setText(label)
        self.transport_panel.btn_speed.setToolTip(
            "Velocidade de reprodução: " + label + ". Clique para reduzir ou voltar a 1×."
        )


    @staticmethod
    def _format_playback_time(seconds):
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        secs = seconds - minutes * 60
        return f"{minutes:02d}:{secs:05.2f}"

    def update_duration(self, duration_ms):
        self.slider.setRange(0, max(0, duration_ms))
        duration_s = duration_ms / 1000.0
        if hasattr(self, 'lbl_elapsed'):
            self.transport_panel.lbl_elapsed.setText(f"{self._format_playback_time(self.player.position()/1000.0)} / {self._format_playback_time(duration_s)}")
        markers = self.transport_panel.timeline.markers if hasattr(self, 'timeline') else []
        self.transport_panel.timeline.set_data(duration_s, markers)

    def set_position(self, position_ms, is_final=False):
        """Atualiza a posição de reprodução com throttling seguro contra sobrecarga de seeks no driver de áudio."""
        pos_ms = max(0, int(position_ms))
        self.update_playback_cursor(pos_ms)

        current_time = time.time()
        # Throttling de chamadas de seek ao player para evitar crash em drivers de áudio/WMF (Windows)
        if is_final or (current_time - getattr(self, '_last_seek_time', 0) > 0.04):
            self._last_seek_time = current_time
            try:
                self.player.setPosition(pos_ms)
            except Exception as exc:
                print(f"Aviso ao posicionar reprodução: {exc}")

    def update_playback_cursor(self, position_ms):
        if hasattr(self, 'slider') and not self.slider.isSliderDown():
            try:
                self.slider.setValue(int(position_ms))
            except Exception:
                pass
        position_sec = float(position_ms) / 1000.0
        if hasattr(self, 'lbl_elapsed'):
            try:
                duration_sec = self.player.duration() / 1000.0
                self.transport_panel.lbl_elapsed.setText(f"{self._format_playback_time(position_sec)} / {self._format_playback_time(duration_sec)}")
            except Exception:
                pass
        if hasattr(self, 'timeline'):
            try:
                self.transport_panel.timeline.set_position(position_sec)
            except Exception:
                pass

        # FASE 4: Delega renderização do cursor e blitting para NavigationController
        self.nav_controller.update_playback_cursor(position_sec)
    def on_double_click(self, event):
        if event.inaxes == self.panel_wave.ax and event.xdata is not None:
            self.editor_controller.toggle_peak_marker(event.xdata, panel=self.panel_wave, event=event)

    def _on_splitter_moved(self, pos, index):
        sizes = self.splitter.sizes()
        if sizes and sizes[0] <= 10:
            self.btn_collapse.setIcon(make_ui_icon("chevron_right", size=18))
            self.btn_collapse.setToolTip("Mostrar painel de arquivos")
        else:
            self.btn_collapse.setIcon(make_ui_icon("chevron_left", size=18))
            self.btn_collapse.setToolTip("Ocultar painel de arquivos")

        if not hasattr(self, "_splitter_debounce_timer"):
            self._splitter_debounce_timer = QTimer(self)
            self._splitter_debounce_timer.setSingleShot(True)
            self._splitter_debounce_timer.timeout.connect(self._finish_resize_refresh)
        self._splitter_debounce_timer.start(80)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_has_shown_initial_layout", False):
            self._has_shown_initial_layout = True
            self.splitter.setStretchFactor(0, 0)
            self.splitter.setStretchFactor(1, 1)
            self.splitter.setSizes([260, max(700, self.width() - 260)])
            if hasattr(self, "dashboard_splitter"):
                dash_w = max(500, self.dashboard_splitter.width())
                self.dashboard_splitter.setSizes([int(dash_w * 0.68), int(dash_w * 0.32)])
            if hasattr(self, "stack_splitter"):
                stack_h = max(300, self.stack_splitter.height())
                h_each = max(60, stack_h // 3)
                self.stack_splitter.setSizes([h_each, h_each, h_each])
            QTimer.singleShot(30, self.apply_plot_geometry)
            if not self.ctx.active_heavy_data:
                QTimer.singleShot(45, self._draw_empty_plots)

    # ---------- maximização / pan / zoom ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "all_panels") and not getattr(self, "_swapping_panels", False) and not getattr(self, "_refreshing_canvases", False):
            if not hasattr(self, "_resize_debounce_timer"):
                self._resize_debounce_timer = QTimer(self)
                self._resize_debounce_timer.setSingleShot(True)
                self._resize_debounce_timer.timeout.connect(self._finish_resize_refresh)
            self._resize_debounce_timer.start(100)

    def _schedule_focus_update(self, delay_ms: int = 200):
        """Agenda _update_active_focus_panel com debounce para evitar cascata durante drag."""
        if not hasattr(self, "_focus_debounce_timer"):
            self._focus_debounce_timer = QTimer(self)
            self._focus_debounce_timer.setSingleShot(True)
            self._focus_debounce_timer.timeout.connect(self._update_active_focus_panel)
        self._focus_debounce_timer.start(delay_ms)

    def _update_active_focus_panel(self):
        """Identifica o gráfico ocupando a maior área na tela e aplica nele a borda azul de maximizado.
        Usa bloqueio de sinal para evitar recálculos desnecessários de layout."""
        if not hasattr(self, "all_panels") or getattr(self, "_swapping_panels", False):
            return
        visible_panels = [p for p in self.all_panels if p.isVisible() and not getattr(p, "_user_closed", False)]
        if not visible_panels:
            return

        # Calcula a área (largura x altura) de cada painel ativo
        largest_panel = max(visible_panels, key=lambda p: max(0, p.width()) * max(0, p.height()))

        for p in self.all_panels:
            is_largest = (p is largest_panel)
            # Chama set_main apenas se o estado realmente mudou — evita repaint desnecessário
            if getattr(p, "_is_main_focused", None) != is_largest:
                p._is_main_focused = is_largest
                p.set_main(is_largest)

    def _finish_resize_refresh(self):
        self._schedule_focus_update(50)
        self.apply_plot_geometry()
        for p in self.all_panels:
            p.canvas.draw_idle()
        if self.ctx.active_heavy_data:
            QTimer.singleShot(150, self.nav_controller.capture_backgrounds)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.expanded_panel is not None:
            self.swap_main_panel(self.expanded_panel)
        else:
            super().keyPressEvent(event)

    def toggle_expand(self, panel):
        self.swap_main_panel(panel)













