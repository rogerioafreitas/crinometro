"""
Crinômetro - Janela Principal e Dashboard Científico (MainWindow).
"""
import os
import sys
import time
import datetime
import json
import re
import copy
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import spectrogram

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QSplitter, QMessageBox, QPushButton,
    QSlider, QFileDialog, QGridLayout, QFrame, QListWidgetItem,
    QSizePolicy, QMenu, QCheckBox, QToolTip, QDialog
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize, QPointF, QRectF
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPen, QCursor, QAction, QPainter
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from matplotlib.figure import Figure
from matplotlib.patches import Patch

from utils.constants import APP_VERSION, CONFIG_FILE, DEFAULT_ALGO_PARAMS, CHANGELOG
from utils.i18n import I18N
from utils.helpers import parse_version_tuple, is_version_newer
from utils.icons import get_app_icon, make_ui_icon, make_spinner_icon
from utils.styles import get_modern_stylesheet

from core.analyzer import CricketAnalyzer
from core.learner import PulseLearner
from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine, HighPerfFreqEngine
from core.worker import GenericWorker

from ui.widgets import ButtonSpinner, ThemeToggle, LoadingScreen, AudioListItemWidget
from ui.panels import PlotPanel, TimelineWidget
from ui.dialogs import (
    AlgoSettingsDialog, AdvancedAlgoSettingsDialog, GeneralSettingsDialog,
    ChangelogDialog, AboutDialog
)
from core.updater import UpdateCheckerThread
from ui.update_dialog import UpdateDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Parâmetros base do algoritmo — editados pelo usuário via menu.
        # NÃO inclui sobreposições adaptativas (prominence, noise_floor adaptados).
        self.algo_params = DEFAULT_ALGO_PARAMS.copy()
        # Sobreposições adaptativas: aplicadas por _adapt_advanced_params() mas
        # NUNCA persistidas no JSON e limpas no reset.
        self._adaptive_overrides = {}
        self.report_params = {"lang": "pt", "institution": "", "researcher_name": "", "role": "", "level": ""}


        # Inicializa o idioma ANTES de qualquer rotina que possa usar I18N.
        # Isso evita AttributeError caso alguma ação seja disparada durante a inicialização.
        self.lang = "pt"
        self.theme_mode = "dark"
        self.pulse_learner = PulseLearner(CONFIG_FILE)
        self.peaks_detected = []
        self.peaks_user_verified = []
        self.corrections_by_file = {}
        self.active_filename = None
        self._pulse_edit_history = []
        self._wave_user_markers = []
        self._click_alignment_lines = []
        self.use_machine_learning = False
        self.load_settings()
        self.lang = self.report_params.get("lang", "pt") or "pt"

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

        self.loaded_files = {}
        self.last_audio_dir = ""
        self.cursor_lines = []
        self.backgrounds = []
        self.bg_cache_valid = False
        self.panning = False
        self.active_ax = None
        self.expanded_panel = None
        self.spectro_engine = None
        self.line_engine = None
        self.freq_engine = None
        self.last_draw_time = 0
        self.last_pan_time = 0
        self.sync_throttle_time = 0
        self.analysis_cache = {}
        self.active_heavy_data = {}
        self.loop_enabled = False
        self.playback_speed = 1.0
        self.main_panel = None
        self.stack_panels = []
        self._building_dashboard = False

        self.setup_menu()
        self.setup_ui()
        self._update_theme_icons()
        # Início limpo: nenhum arquivo fictício é carregado automaticamente.

    # ---------- tema ----------
    # ---------- tema ----------
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
        if hasattr(self, "btn_play"):
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
        if self.active_heavy_data:
            if hasattr(self, "active_filename") and self.active_filename:
                self.render_dashboard(self.active_filename)
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
        self.action_export_pdf_full = QAction("Exportar Relatório Completo (.pdf)", self)
        self.action_export_pdf_full.setIcon(make_ui_icon("export", color="#2563EB", size=16))
        self.action_export_pdf_full.triggered.connect(lambda: self.action_save_pdf(include_chirp_list=True))
        self.export_submenu.addAction(self.action_export_pdf_full)
        self.action_export_pdf_simple = QAction("Exportar Relatório Simplificado (.pdf)", self)
        self.action_export_pdf_simple.setIcon(make_ui_icon("export", color="#0284C7", size=16))
        self.action_export_pdf_simple.triggered.connect(lambda: self.action_save_pdf(include_chirp_list=False))
        self.export_submenu.addAction(self.action_export_pdf_simple)
        
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
        version = QLabel(f"v{APP_VERSION}")
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
        self.btn_abort_batch.clicked.connect(self.abort_current_analysis)
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
        self.btn_reanalisar_main.clicked.connect(self.force_reanalyze)
        row_analysis.addWidget(self.btn_reanalisar_main)

        # Botão Abortar Análise (ao lado direto de Reanalisar, visível apenas durante análise)
        self.btn_abort_analysis = QPushButton("✕ Abortar")
        self.btn_abort_analysis.setObjectName("summaryAbortAction")
        self.btn_abort_analysis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abort_analysis.setFixedHeight(26)
        self.btn_abort_analysis.setToolTip("Cancelar a análise em andamento")
        self.btn_abort_analysis.setVisible(False)
        self.btn_abort_analysis.clicked.connect(self.abort_current_analysis)
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
        self.btn_learn_corrections.clicked.connect(self.learn_from_corrections)
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
        self.btn_sync.toggled.connect(self.on_sync_toggled)
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
            panel.canvas.mpl_connect("scroll_event", self.zoom_graph)
            panel.canvas.mpl_connect("button_press_event", self.on_press)
            panel.canvas.mpl_connect("button_release_event", self.on_release)
            panel.canvas.mpl_connect("motion_notify_event", self.on_motion)
            panel.canvas.mpl_connect("axes_leave_event", self.on_axes_leave)

        # CONTROLES DE REPRODUÇÃO — velocidade à esquerda, play no centro, volume à direita
        self.playback_card = QFrame()
        self.playback_card.setObjectName("playbackCard")
        self.playback_card.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        root_play = QVBoxLayout(self.playback_card)
        root_play.setContentsMargins(14, 5, 14, 5)
        root_play.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(12)
        row.addStretch(2)

        self.btn_speed = self._transport_button("1×", "Reduzir velocidade de reprodução")
        self.btn_speed.setObjectName("speedButton")
        self.btn_speed.setFixedSize(50, 38)
        self.btn_speed.clicked.connect(self.cycle_playback_speed)
        row.addWidget(self.btn_speed, 0, Qt.AlignmentFlag.AlignVCenter)

        center = QWidget()
        center.setObjectName("playCenter")
        center.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(0,0,0,0)
        center_l.setSpacing(0)
        center_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_play = self._transport_button("", "Reproduzir", play=True)
        self.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_play.setAutoDefault(False)
        self.btn_play.setDefault(False)
        self.btn_play.setFlat(True)
        self.btn_play.setFixedSize(46,46)
        self.btn_play.setIconSize(QSize(19,19))
        self.btn_play.clicked.connect(self.toggle_playback)
        center_l.addWidget(self.btn_play,0,Qt.AlignmentFlag.AlignCenter)
        self.lbl_elapsed = QLabel("00:00.00 / 00:00.00")
        self.lbl_elapsed.setObjectName("elapsedLabel")
        self.lbl_elapsed.setFixedWidth(138)
        self.lbl_elapsed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_l.addWidget(self.lbl_elapsed,0,Qt.AlignmentFlag.AlignCenter)
        row.addWidget(center,0,Qt.AlignmentFlag.AlignVCenter)

        self.volume_cluster = QWidget()
        self.volume_cluster.setObjectName("volumeCluster")
        self.volume_cluster.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        vol_l = QHBoxLayout(self.volume_cluster)
        vol_l.setContentsMargins(0,0,0,0)
        vol_l.setSpacing(6)
        self.lbl_volume = QLabel()
        self.lbl_volume.setObjectName("volumeLabel")
        self.lbl_volume.setPixmap(make_ui_icon("volume", size=16).pixmap(16,16))
        self.lbl_volume.setFixedSize(18,18)
        vol_l.addWidget(self.lbl_volume)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0,100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.valueChanged.connect(lambda val: self.audio_output.setVolume(val / 100.0))
        vol_l.addWidget(self.volume_slider)
        row.addWidget(self.volume_cluster,0,Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(2)
        root_play.addLayout(row)

        # CONTÊINER ÚNICO: controles + cursor/timeline do áudio
        self.transport_timeline_card = QFrame()
        self.transport_timeline_card.setObjectName("transportTimelineCard")
        self.transport_timeline_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.transport_timeline_card.setAutoFillBackground(True)
        transport_timeline_layout = QVBoxLayout(self.transport_timeline_card)
        transport_timeline_layout.setContentsMargins(8, 8, 8, 8)
        transport_timeline_layout.setSpacing(2)
        transport_timeline_layout.addWidget(self.playback_card)

        self.timeline = TimelineWidget(self.set_position)
        transport_timeline_layout.addWidget(self.timeline)
        right_layout.addWidget(self.transport_timeline_card)

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
        self._update_ml_toggle_ui()

    def _transport_button(self, text, tooltip, play=False, checkable=False):
        b = QPushButton(text)
        b.setObjectName("playButton" if play else "transport")
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setFixedSize(44 if not play else 46, 44 if not play else 46)
        b.setToolTip(tooltip)
        b.setCheckable(checkable)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

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
            if self.line_engine is not None:
                self.line_engine.debounce_timer.stop()
            if self.spectro_engine is not None:
                self.spectro_engine.debounce_timer.stop()
            if self.freq_engine is not None:
                self.freq_engine.debounce_timer.stop()

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
            QApplication.processEvents()
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
                self._apply_plot_geometry()
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
            self._apply_plot_geometry()
            for p in self.all_panels:
                p.canvas.draw_idle()
        finally:
            self._swapping_panels = False

    def _on_dashboard_splitter_moved(self, pos, index):
        self.bg_cache_valid = False
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
                self._apply_plot_geometry()
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

        QApplication.processEvents()
        self._apply_plot_geometry()
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
        if not self.active_heavy_data:
            return
        d=self.active_heavy_data; duration=max(0.001,float(d.get("duration",0.0))); p=d.get("params",{})
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

    def _apply_plot_geometry(self):
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

        self._apply_plot_geometry()
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
            self._apply_plot_geometry()
            for panel in self.all_panels:
                panel.canvas.updateGeometry()
                panel.figure.set_constrained_layout(False)
                panel.canvas.draw()
            if self.active_heavy_data:
                self.capture_backgrounds()
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
        self._update_pulse_edit_buttons(None)

        spinner = ButtonSpinner(self.btn_analyze_selected, "Analisando...")
        spinner.start()
        self._batch_spinner = spinner

        for fname in checked_files:
            w = self._get_item_widget_by_name(fname)
            if w and hasattr(w, "set_loading"):
                w.set_loading(True)

        curr = self.list_widget.currentItem()
        curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
        effective_params = {**self.algo_params, **self._adaptive_overrides}

        def _task():
            success_count = 0
            errors = []
            
            for i, fname in enumerate(checked_files):
                if worker.abort_requested:
                    break
                
                if fname not in self.loaded_files or not os.path.exists(self.loaded_files[fname]):
                    continue
                
                try:
                    fpath = self.loaded_files[fname]
                    # Analysis runs sequentially. It takes ~1s per file, leaving GIL frequently.
                    res = CricketAnalyzer.analyze(fpath, effective_params, pulse_learner=self.pulse_learner)
                    
                    # Emitir resultado imediatamente para a UI thread processar
                    if not worker.abort_requested:
                        worker.result_ready_signal.emit(fname, res)
                        success_count += 1
                        
                except Exception as exc:
                    errors.append(f"{fname}: {exc}")
                    
                if not worker.abort_requested:
                    worker.progress_signal.emit(i + 1, len(checked_files))

            return success_count, errors

        worker = GenericWorker(_task)
        self._batch_worker = worker
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(True)
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(True)

        def _cleanup_batch():
            if hasattr(self, "btn_abort_batch"):
                self.btn_abort_batch.setVisible(False)
            if hasattr(self, "btn_abort_analysis"):
                self.btn_abort_analysis.setVisible(False)
            for fname in checked_files:
                w = self._get_item_widget_by_name(fname)
                if w and hasattr(w, "set_loading"):
                    w.set_loading(False)
                    
        def _on_single_result(fname, res):
            # Chamado no fluxo da main thread, processa as arrays um arquivo por vez
            self._apply_analysis_results(fname, res, render=(fname == curr_name))
            
            # Atualiza o estado da UI para este item especifico
            w = self._get_item_widget_by_name(fname)
            if w and hasattr(w, "set_loading"):
                w.set_loading(False)

        def _on_finished(payload):
            _cleanup_batch()
            success_count, errors = payload

            if curr_name in self.analysis_cache:
                self.btn_reanalisar_main.setText("Reanalisar")
                self.btn_reanalisar_main.setIcon(make_ui_icon("reload", color="#FFFFFF", size=17))
                self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")

            if curr_name not in checked_files and checked_files and checked_files[0] in self.analysis_cache:
                self.select_file_by_name(checked_files[0])

            spinner.stop(None, "⚡ Analisar Selecionados")
            total = len(checked_files)
            msg = f"Análise concluída!\n\n• {success_count} de {total} arquivo(s) analisado(s) com sucesso."
            if errors:
                msg += f"\n\nFalhas ({len(errors)}):\n" + "\n".join(errors[:5])
                QMessageBox.warning(self, "Análise em Lote", msg)
            else:
                QMessageBox.information(self, I18N[self.lang]["success"], msg)

        def _on_error(err_msg):
            _cleanup_batch()
            spinner.stop(None, "⚡ Analisar Selecionados")
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha na análise em lote:\n{err_msg}")

        def _on_progress(current, total):
            if hasattr(self, "_batch_spinner") and getattr(self._batch_spinner, "button", None) is not None:
                self._batch_spinner.button.setText(f"Analisando... ({current}/{total})")

        worker.finished_signal.connect(_on_finished)
        worker.result_ready_signal.connect(_on_single_result)
        worker.progress_signal.connect(_on_progress)
        worker.error_signal.connect(_on_error)
        worker.start()

    def remove_audio(self):
        curr_item = self.list_widget.currentItem()
        if not curr_item:
            return
        fname = self._get_item_filename(curr_item)
        self.remove_audio_by_name(fname)

    def remove_audio_by_name(self, fname):
        if not fname:
            return
        if self.player.source().toLocalFile() == self.loaded_files.get(fname):
            self.player.stop()
            self.btn_play.setEnabled(False)
            self._update_play_icon()
            self.slider.setValue(0)
        self.loaded_files.pop(fname, None)
        self.analysis_cache.pop(fname, None)
        self.corrections_by_file.pop(fname, None)

        # Remove o item da lista
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = self._get_item_filename(item)
            if name == fname:
                self.list_widget.takeItem(i)
                break

        self._update_select_all_visibility()

        if self.list_widget.count() == 0:
            self.active_heavy_data = {}
            self.peaks_detected = []
            self.peaks_user_verified = []
            self.active_filename = ""
            for p in self.all_panels:
                p.ax.clear()
                p.canvas.draw_idle()
            self._update_summary_placeholder()
        else:
            if getattr(self, "active_filename", None) == fname:
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
            self.loaded_files[filename] = file_path
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
                self.loaded_files[filename] = file_path
                self._add_audio_file_item(filename, is_checked=False)
                loaded_any.append(filename)
        if loaded_any:
            first_name = loaded_any[0]
            if first_name in self.loaded_files:
                self.last_audio_dir = os.path.dirname(self.loaded_files[first_name])
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
        if filename not in self.loaded_files or not os.path.exists(self.loaded_files[filename]):
            self.player.stop()
            self.btn_play.setEnabled(False)
            self._update_summary_placeholder(filename)
            return
        self.player.stop()
        self.playback_speed = 1.0
        self.player.setPlaybackRate(1.0)
        self.btn_speed.setText("1×")
        self._update_play_icon()
        self.player.setSource(QUrl.fromLocalFile(self.loaded_files[filename]))
        self.btn_play.setEnabled(True)

        if filename in self.analysis_cache:
            self.btn_reanalisar_main.setText("Reanalisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("reload", color="#FFFFFF", size=17))
            self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")
            self.active_heavy_data = self.analysis_cache[filename]
            self.peaks_detected = list(self.active_heavy_data.get("peaks_detected", []))
            self.peaks_user_verified = list(self.active_heavy_data.get("peaks_user_verified", []))
            self.active_filename = filename
            self._pulse_edit_history = []
            self.render_dashboard(filename)
        else:
            self.btn_reanalisar_main.setText("Analisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("play", color="#FFFFFF", size=15))
            self.btn_reanalisar_main.setToolTip("Executar análise deste áudio")
            self.reset_audio_state(filename)
            self._update_summary_ready_for_analysis(filename)

    def reset_audio_state(self, filename):
        """Reinicia atomicamente as variáveis de edição e picos para o arquivo especificado, prevenindo contaminação."""
        self.active_filename = filename
        self._pulse_edit_history = []
        self._click_alignment_lines = []
        stored = self.corrections_by_file.get(filename)
        if stored is not None:
            self.peaks_user_verified = list(stored)
        else:
            self.peaks_user_verified = []

        cached = self.analysis_cache.get(filename)
        if cached is not None:
            self.peaks_detected = list(cached.get("peaks_detected", []))
            self.active_heavy_data = cached
        else:
            self.peaks_detected = []
            self.active_heavy_data = None
            self._adaptive_overrides = {}

        if self.line_engine:
            self.line_engine.debounce_timer.stop()
        if self.spectro_engine:
            self.spectro_engine.debounce_timer.stop()
        if getattr(self, "freq_engine", None):
            self.freq_engine.debounce_timer.stop()

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
            rate, data = wavfile.read(self.loaded_files[filename])
            if len(data.shape) > 1:
                data = data[:, 0]
            dur = len(data) / float(rate)
            mins = int(dur // 60)
            secs = dur % 60
            self.lbl_summary_meta.setText(f"Duração: {mins:02d}:{secs:04.1f}   •   Taxa: {int(rate):,} Hz   •   Pronto para análise")
            self.timeline.set_data(dur, [])
        except Exception:
            self.lbl_summary_meta.setText("Áudio carregado • Clique em 'Analisar'")
            self.timeline.set_data(0.0, [])
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
        dialog = AlgoSettingsDialog(self.algo_params, self.lang, self)
        if dialog.exec():
            new_params = dialog.get_params()
            if new_params != self.algo_params:
                self.algo_params = new_params
                if self.analysis_cache:
                    reply = QMessageBox.question(self, "Reanalisar?", "Configurações alteradas! Deseja refazer as análises no cache?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        curr = self.list_widget.currentItem()
                        curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
                        for fname in list(self.analysis_cache.keys()):
                            if fname != curr_name:
                                self.run_analysis(fname, self.algo_params, render=False)
                        if curr_name and curr_name in self.loaded_files:
                            self.run_analysis(curr_name, self.algo_params, render=True)

    def export_training_model(self):
        """Abre caixa de diálogo para salvar o arquivo com o treinamento ativo."""
        if not hasattr(self, "pulse_learner") or not self.pulse_learner:
            QMessageBox.warning(self, "Sem Modelo", "Não há módulo de aprendizado ativo.")
            return
        if not self.pulse_learner.is_trained() and len(self.pulse_learner.training_features) == 0:
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
            self.pulse_learner.export_model_file(file_path)
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
            self.pulse_learner.import_model_file(file_path)
            self._adapt_advanced_params()

            n_samples = len(self.pulse_learner.training_features)
            msg = f"Treinamento carregado com sucesso!\n• Amostras de treino: {n_samples}\n• Classificador Random Forest (500 árvores) ativo."

            # Se houver arquivo carregado, pergunta se deseja reanalisar agora
            curr = self.list_widget.currentItem()
            curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
            if curr_name and curr_name in self.loaded_files:
                reply = QMessageBox.question(
                    self,
                    "Reanalisar com Novo Treinamento?",
                    msg + "\n\nDeseja reanalisar o áudio atual com este novo modelo de treinamento?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.run_analysis(curr_name, self.algo_params, render=True)
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
                if hasattr(self, 'pulse_learner') and self.pulse_learner:
                    self.pulse_learner.reset()
                
                # Desativa a IA após o reset para forçar o usuário a trabalhar com DSP puro
                self.use_machine_learning = False
                self.save_settings(silent=True)
                self._update_ml_toggle_ui()
                
                
                QMessageBox.information(
                    self, 
                    "Reset Concluído", 
                    "O aprendizado de máquina foi completamente zerado. O algoritmo retornou ao estado original DSP."
                )
                
                # Se houver áudio carregado, força reanálise para aplicar o DSP limpo
                curr = self.list_widget.currentItem()
                curr_name = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
                if curr_name and curr_name in self.loaded_files:
                    self.run_analysis(curr_name, self.algo_params, render=True)
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
        self.algo_params = DEFAULT_ALGO_PARAMS.copy()
        self._adaptive_overrides = {}

        # 2. IA e marcações não são resetadas aqui mais

        # 4. Limpa o arquivo de configuração persistido
        try:
            clean_config = {
                "algo_params": self.algo_params,
                "report_params": self.report_params,
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
        if curr_name and curr_name in self.loaded_files:
            self.analysis_cache.clear()
            self.run_analysis(curr_name, self.algo_params, render=True)
        else:
            self.analysis_cache.clear()

        if hasattr(self, 'lbl_model_status'):
            self._update_ml_toggle_ui()

        QMessageBox.information(
            self,
            I18N[l]["success"],
            I18N[l].get("reset_done", "Configurações resetadas com sucesso!")
        )

    def open_report_settings(self):
        dialog = GeneralSettingsDialog(self.report_params, self.lang, self)
        if dialog.exec():
            self.report_params = dialog.get_params()
            if self.report_params["lang"] != self.lang:
                self.lang = self.report_params["lang"]
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
                    f"Você já está executando a versão mais recente do Crinômetro (v{APP_VERSION})!"
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
                    self.algo_params.update(data["algo_params"])
                if isinstance(data.get("report_params"), dict):
                    self.report_params.update(data["report_params"])
                theme = data.get("theme")
                if theme in {"dark", "light"}:
                    self.theme_mode = theme
                corrections = data.get("corrections_by_file")
                if isinstance(corrections, dict):
                    self.corrections_by_file = {}
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
                            self.corrections_by_file[str(name)] = parsed
                if "pulse_learner" in data:
                    self.pulse_learner.load_from_config()
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
            config["algo_params"] = self.algo_params
            config["report_params"] = self.report_params
            config["theme"] = self.theme_mode
            config["corrections_by_file"] = self.corrections_by_file
            config["last_audio_dir"] = getattr(self, "last_audio_dir", "")
            if not "pulse_learner" in config:
                config["pulse_learner"] = None
            if self.pulse_learner.model is not None:
                config["pulse_learner"] = self.pulse_learner.serialize()
                self.pulse_learner.save_persisted_training()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            if not silent:
                QMessageBox.information(self, I18N[self.lang]["success"], I18N[self.lang]["config_saved"])
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, I18N[self.lang]["error"], f"Failed to save:\n{e}")

    def toggle_machine_learning(self):
        """Ativa ou desativa a filtragem e classificação por Inteligência Artificial sem forçar reanálise imediata."""
        is_active = not getattr(self, "use_machine_learning", False)
        if is_active:
            QMessageBox.warning(
                self, 
                "Aviso de IA", 
                "A Inteligência Artificial pode cometer erros!\n\n"
                "Lembre-se de que correções mal feitas pelo usuário podem 'quebrar' as análises da IA e piorar os resultados.\n\n"
                "Recomendação: Se a IA começar a apresentar resultados quebrados ou irregulares, utilize o botão 'Resetar Aprendizado' no menu Opções (Configurações) para restaurar os valores originais do DSP."
            )
        self.use_machine_learning = is_active
        self.save_settings(silent=True)
        self._update_ml_toggle_ui()

    def _update_ml_toggle_ui(self):
        if not hasattr(self, "btn_toggle_ml"):
            return
        is_active = getattr(self, "use_machine_learning", False)
        self.btn_toggle_ml.setProperty("active", "true" if is_active else "false")
        self.btn_toggle_ml.setStyleSheet("")
        self.btn_toggle_ml.style().unpolish(self.btn_toggle_ml)
        self.btn_toggle_ml.style().polish(self.btn_toggle_ml)
        if is_active:
            self.btn_toggle_ml.setText("🧠 IA: Ativada")
            self.btn_toggle_ml.setToolTip("IA Ativada: filtra ruído e discrimina grilos distantes. Clique para desativar.")
            if hasattr(self, "lbl_model_status"):
                status_txt = "🧠 IA: Ativada (Modelo Supervisionado)" if self.pulse_learner.is_trained() else "🧠 IA: Ativada (GMM não-supervisionado)"
                self.lbl_model_status.setText(status_txt)
                self.lbl_model_status.setStyleSheet("color: #10B981;")
        else:
            self.btn_toggle_ml.setText("🧠 IA: Desativada")
            self.btn_toggle_ml.setToolTip("IA Desativada: análise executada estritamente por processamento de sinal (DSP). Clique para ativar.")
            if hasattr(self, "lbl_model_status"):
                self.lbl_model_status.setText("🧠 IA: Desativada (Modo DSP)")
                self.lbl_model_status.setStyleSheet("color: #94A3B8;")

    # ---------- análise ----------
    def force_reanalyze(self):
        curr = self.list_widget.currentItem()
        filename = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
        if not filename or filename not in self.loaded_files or not os.path.exists(self.loaded_files[filename]):
            QMessageBox.information(self, "Arquivo não carregado", "Selecione ou carregue o arquivo WAV antes de analisar.")
            return

        # Desativa a ferramenta de edição caso esteja ativa
        self._update_pulse_edit_buttons(None)

        is_first_time = (filename not in self.analysis_cache)
        if is_first_time:
            self.reset_audio_state(filename)
        loading_text = "Analisando..." if is_first_time else "Reanalisando..."
        spinner = ButtonSpinner(self.btn_reanalisar_main, loading_text)
        spinner.start()
        self._reanalyze_spinner = spinner
        
        self._saved_viewport = None
        if not is_first_time and getattr(self, "panel_spec", None):
            self._saved_viewport = {
                "wave_xlim": self.panel_wave.ax.get_xlim(),
                "wave_ylim": self.panel_wave.ax.get_ylim(),
                "freq_xlim": self.panel_freq.ax.get_xlim(),
                "freq_ylim": self.panel_freq.ax.get_ylim(),
                "spec_xlim": self.panel_spec.ax.get_xlim(),
                "spec_ylim": self.panel_spec.ax.get_ylim(),
            }

        item_widget = self._get_item_widget_by_name(filename)
        if item_widget and hasattr(item_widget, "set_loading"):
            item_widget.set_loading(True)

        def _task():
            # 1. Se o usuário fez correções no arquivo atual, atualizamos o modelo
            if (self.active_heavy_data and self.active_filename == filename and
                filename in self.corrections_by_file and self.peaks_user_verified):
                rate = float(self.active_heavy_data.get("rate", 1.0))
                env = self.active_heavy_data.get("env")
                data_b1 = self.active_heavy_data.get("data_b1")
                if env is not None:
                    try:
                        self.pulse_learner.update_from_corrections(
                            self.peaks_detected, self.peaks_user_verified, rate, env, raw_signal=data_b1
                        )
                        self._adapt_advanced_params()
                        self.pulse_learner.save_to_config()
                    except Exception:
                        pass

            effective_params = {**self.algo_params, **self._adaptive_overrides}
            file_path = self.loaded_files[filename]
            learner = self.pulse_learner if getattr(self, "use_machine_learning", True) else None
            
            cached_spec = None
            if self.active_heavy_data and self.active_filename == filename:
                cached_spec = {
                    "f_spec": self.active_heavy_data.get("f_spec"),
                    "t_spec": self.active_heavy_data.get("t_spec"),
                    "Sxx_db": self.active_heavy_data.get("Sxx_db"),
                    "dom_freqs": self.active_heavy_data.get("dom_freqs"),
                }
                
            res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner, cached_spec=cached_spec)
            return res

        worker = GenericWorker(_task)
        self._reanalyze_worker = worker
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(True)

        def _cleanup():
            if hasattr(self, "btn_abort_analysis"):
                self.btn_abort_analysis.setVisible(False)

        def _on_finished(results):
            _cleanup()
            if item_widget and hasattr(item_widget, "set_loading"):
                item_widget.set_loading(False)
            spinner.stop(make_ui_icon("reload", color="#FFFFFF", size=17), "Reanalisar")
            self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")
            self._apply_analysis_results(filename, results, render=True, validate_all=True)

        def _on_error(err_msg):
            _cleanup()
            if item_widget and hasattr(item_widget, "set_loading"):
                item_widget.set_loading(False)
            restore_text = "Analisar" if is_first_time else "Reanalisar"
            restore_icon = make_ui_icon("play", color="#FFFFFF", size=15) if is_first_time else make_ui_icon("reload", color="#FFFFFF", size=17)
            spinner.stop(restore_icon, restore_text)
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha na análise:\n{err_msg}")

        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)
        worker.start()

    def run_analysis(self, filename, params, render=True, validate_all=False):
        file_path = self.loaded_files[filename]
        try:
            effective_params = {**params, **self._adaptive_overrides}
            learner = self.pulse_learner if getattr(self, "use_machine_learning", False) else None
            res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner)
            self._apply_analysis_results(filename, res, render=render, validate_all=validate_all, params=params)
        except Exception as e:
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha no arquivo {filename}:\n{str(e)}")

    def abort_current_analysis(self):
        """Cancela cooperativamente a análise em andamento (single ou lote)."""
        aborted = False
        for attr in ("_reanalyze_worker", "_batch_worker"):
            worker = getattr(self, attr, None)
            if worker is not None and worker.isRunning():
                worker.abort()
                aborted = True
        
        if hasattr(self, "btn_abort_analysis"):
            self.btn_abort_analysis.setVisible(False)
        if hasattr(self, "btn_abort_batch"):
            self.btn_abort_batch.setVisible(False)
            
        if getattr(self, "_reanalyze_spinner", None) is not None:
            is_first_time = (getattr(self, "active_filename", None) not in self.analysis_cache)
            restore_text = "Analisar" if is_first_time else "Reanalisar"
            restore_icon = make_ui_icon("play", color="#FFFFFF", size=15) if is_first_time else make_ui_icon("reload", color="#FFFFFF", size=17)
            self._reanalyze_spinner.stop(restore_icon, restore_text)
            self._reanalyze_spinner = None
            
        if getattr(self, "_batch_spinner", None) is not None:
            self._batch_spinner.stop(None, "⚡ Analisar Selecionados")
            self._batch_spinner = None

        if aborted:
            if hasattr(self, "btn_reanalisar_main"):
                self.btn_reanalisar_main.setEnabled(True)
            if hasattr(self, "btn_analyze_selected"):
                self.btn_analyze_selected.setEnabled(True)
                
            curr_name = getattr(self, 'active_filename', None)
            if curr_name:
                item_widget = self._get_item_widget_by_name(curr_name)
                if item_widget and hasattr(item_widget, "set_loading"):
                    item_widget.set_loading(False)
            
            checked_files = self.get_checked_files() if hasattr(self, "get_checked_files") else []
            for fname in checked_files:
                w = self._get_item_widget_by_name(fname)
                if w and hasattr(w, "set_loading"):
                    w.set_loading(False)

    def _apply_analysis_results(self, filename, results, render=True, validate_all=False, params=None):
        if params is None:
            params = self.algo_params.copy()
        rate, data, data_b1, env, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration = results[:14]
        distant_peaks = results[14] if len(results) > 14 else []
        carrier_freq = float(results[15]) if len(results) > 15 else 0.0
        discarded_peaks_reasons = results[16] if len(results) > 16 else {}
        valid_peaks_stage2 = results[17] if len(results) > 17 else list(peaks)
        peak_dur_dict = results[18] if len(results) > 18 else {}
        f_psd = results[19] if len(results) > 19 else np.array([])
        Pxx_db = results[20] if len(results) > 20 else np.array([])

        # Converte dados volumosos de ponto flutuante para float32 (reduz 50% do consumo de RAM)
        if isinstance(data, np.ndarray) and data.dtype != np.float32:
            data = data.astype(np.float32)
        if isinstance(data_b1, np.ndarray) and data_b1.dtype != np.float32:
            data_b1 = data_b1.astype(np.float32)
        if isinstance(env, np.ndarray) and env.dtype != np.float32:
            env = env.astype(np.float32)
        if isinstance(Sxx_db, np.ndarray) and Sxx_db.dtype != np.float32:
            Sxx_db = Sxx_db.astype(np.float32)

        self.peaks_detected = [int(p) for p in np.asarray(peaks, dtype=int)]
        self.active_filename = filename

        stored_corrections = self.corrections_by_file.get(filename)
        effective_params = {**params, **self._adaptive_overrides}
        
        self.pulse_metadata = {}

        # Aplica estritamente correções específicas deste arquivo
        if stored_corrections is not None:
            extracted_peaks = []
            for item in stored_corrections:
                if isinstance(item, dict):
                    extracted_peaks.append(item["idx"])
                    self.pulse_metadata[item["idx"]] = item
                else:
                    extracted_peaks.append(int(item))
            self.peaks_user_verified = extracted_peaks
            peaks_added = sorted(set(extracted_peaks) - set(self.peaks_detected))
            peaks_removed = sorted(set(self.peaks_detected) - set(extracted_peaks))
            
            if peaks_removed:
                # Se o algoritmo ou modelo ML ainda achou que o pulso era válido, 
                # mas o usuário removeu explicitamente, force-o a ser exibido como ruído (distant_peak)
                distant_peaks = sorted(list(set(distant_peaks) | set(peaks_removed)))
                for pk in peaks_removed:
                    discarded_peaks_reasons[int(pk)] = "Removido manualmente pelo usuário"
            
            if peaks_added or peaks_removed:
                effective_peaks = np.asarray(
                    sorted(set(self.peaks_detected) | set(peaks_added) - set(peaks_removed)),
                    dtype=int
                )
                if len(effective_peaks) >= 2:
                    try:
                        chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
                            effective_peaks, effective_params, rate, env, raw_signal=data_b1
                        )
                    except Exception:
                        pass
        else:
            self.peaks_user_verified = list(self.peaks_detected)

        heavy_data = {
            "rate": rate, "data": data, "data_b1": data_b1, "env": env, "peaks": list(self.peaks_detected), "chirps": chirps,
            "chirp_peaks_list": chirp_peaks_list, "chirp_peaks": list(chirp_peaks_list), "media": media, "moda": moda,
            "f_spec": f_spec, "t_spec": t_spec, "Sxx_db": Sxx_db, "dom_freqs": dom_freqs,
            "duration": audio_duration, "params": params.copy(),
            "peaks_detected": list(self.peaks_detected),
            "peaks_user_verified": list(self.peaks_user_verified),
            "distant_peaks": list(distant_peaks),
            "carrier_freq": carrier_freq,
            "discarded_peaks_reasons": discarded_peaks_reasons,
            "valid_peaks_stage2": list(valid_peaks_stage2),
            "peak_dur_dict": peak_dur_dict,
            "f_psd": f_psd,
            "Pxx_db": Pxx_db,
        }
        self.analysis_cache[filename] = heavy_data
        
        if render:
            # Captura o zoom atual antes que o render_dashboard o destrua
            has_active = hasattr(self, "active_filename") and self.active_filename == filename
            if has_active and hasattr(self, "panel_wave") and hasattr(self, "panel_spec"):
                current_vp = {
                    "wave_xlim": self.panel_wave.ax.get_xlim(),
                    "wave_ylim": self.panel_wave.ax.get_ylim(),
                    "freq_xlim": self.panel_freq.ax.get_xlim(),
                    "freq_ylim": self.panel_freq.ax.get_ylim(),
                    "spec_xlim": self.panel_spec.ax.get_xlim(),
                    "spec_ylim": self.panel_spec.ax.get_ylim(),
                }
            else:
                current_vp = None

            self.active_heavy_data = heavy_data
            self.active_filename = filename

            # Sincroniza informações da frequência portadora e tolerância nos painéis
            tol_val = float(params.get("freq_tolerance_hz", 300.0))
            if hasattr(self, "panel_spec"):
                self.panel_spec.set_carrier_info(carrier_freq, tol_val)
            if hasattr(self, "panel_freq"):
                self.panel_freq.set_carrier_info(carrier_freq, tol_val)

            self.render_dashboard(filename)
            
            # Restaurar a viewport anterior
            vp = current_vp or getattr(self, "_saved_viewport", None)
            if vp is not None and has_active:
                dur = heavy_data.get("duration", 0.0)
                
                # wave
                x0, x1 = vp.get("wave_xlim", (0, dur))
                if x1 <= x0: x1 = x0 + 1.0
                self.panel_wave.ax.set_xlim(x0, x1)
                
                # freq não precisa restaurar limites X, pois agora é um espectro estático (PSD)
                
                # spec
                sx0, sx1 = vp.get("spec_xlim", (x0, x1))
                if sx1 <= sx0: sx1 = sx0 + 1.0
                self.panel_spec.ax.set_xlim(sx0, sx1)
                if not getattr(self.panel_spec, "_y_locked", False):
                    self.panel_spec.ax.set_ylim(vp.get("spec_ylim", (0, 10)))
                    
                # redraw
                for p in [self.panel_wave, self.panel_freq, self.panel_spec]:
                    p.canvas.draw()  # Must be synchronous draw() before capturing backgrounds
                # É crucial recapturar o background porque o render_dashboard capturou o fundo no zoom 0-dur
                # O usuário precisa do background com o zoom exato para poder fazer pan suavemente
                self.capture_backgrounds()
                
            self._saved_viewport = None



    def render_dashboard(self, filename):
        cur_splitter_sizes = self.splitter.sizes() if hasattr(self, "splitter") else None
        # Limpa referências a linhas de alinhamento do clique em eixos que serão
        # destruídos/recriados nesta renderização. Mantê-las causaria RuntimeError
        # ao chamar line.remove() na próxima chamada de _align_click_marker().
        self._click_alignment_lines = []
        d = self.active_heavy_data
        p = d.get("params") or {}
        rate = d["rate"]
        data = d["data"]
        env = d["env"]
        chirp_peaks_list = d["chirp_peaks_list"]
        chirps = d["chirps"]
        f_spec = d["f_spec"]
        t_spec = d["t_spec"]
        Sxx_db = d["Sxx_db"]
        dom_freqs = d["dom_freqs"]

        self.lbl_summary_file.setText(filename)
        p_txt = f"[Pulsos: {p['min_p']}-{p['max_p']} | Amp: {p['amp_min']:.2f}-{p['amp_max']:.2f} | Freq: {int(p['b1_min'])}-{int(p['b1_max'])} Hz]"
        meta_str = f"Duração: {d['duration']:.2f}s   |   Parâmetros: {p_txt}"
        self.lbl_summary_meta.setText(meta_str)
        self.lbl_summary_meta.setToolTip(f"Duração: {d['duration']:.2f} segundos\nParâmetros: {p_txt}")
        self.lbl_total.setText(str(len(chirps)))
        self.lbl_metric_sub.setText(f"Moda: {d['moda']}   |   Média: {d['media']:.2f}")
        self._update_ml_toggle_ui()

        paleta_cores = ['#03A9F4', '#4CAF50', '#FF5252', '#E040FB', '#FFAB40', '#00E676', '#FF4081', '#FFEA00']
        # Visual solicitado: verde/orange/magenta como categorias dominantes.
        # Paleta canônica por quantidade de pulsos (2 a 10 + 1 extra para escopos maiores).
        # A mesma cor é usada no histograma, nos X da onda, frequência e espectrograma.
        pulse_colors = {
            2: '#2563EB',   # Azul Royal
            3: '#8B5CF6',   # Roxo / Violeta
            4: '#F97316',   # Laranja
            5: '#10B981',   # Verde Esmeralda
            6: '#EC4899',   # Rosa Magenta
            7: '#06B6D4',   # Ciano Turquesa
            8: '#EAB308',   # Amarelo Dourado
            9: '#6366F1',   # Índigo
            10: '#14B8A6',  # Teal Menta
        }
        extra_pulse_color = '#F43F5E'  # Vermelho Rubi (cor extra para > 10 pulsos ou outros escopos)
        marker_colors = pulse_colors

        picos_por_contagem = {}
        for cp in chirp_peaks_list:
            qnt = len(cp)
            picos_por_contagem.setdefault(qnt, []).extend(cp)
        time_sec = np.arange(len(data)) / rate

        # WAVE
        ax1 = self.panel_wave.ax
        ax1.clear()
        self.line_engine = HighPerfLineEngine(ax1, time_sec, data, base_color='#21A8D8', update_bg_callback=self.capture_backgrounds)
        self.line_engine.render_high_detail()
        decimation = max(1, len(env) // 5000)
        ax1.plot(time_sec[::decimation], env[::decimation], color='#6E747C', alpha=0.55, linewidth=0.8, zorder=2)

        ax1.set_xlabel("seconds")
        ax1.set_ylabel("Amplitude")
        ax1.set_ylim(-1.05, 1.05)

        # HIST — fixo, sem drag/zoom, com índice de cores/pulsos no rodapé
        self._refresh_histogram()

        # FREQ (PSD)
        ax3 = self.panel_freq.ax
        ax3.clear()
        
        f_psd = self.active_heavy_data.get("f_psd", [])
        Pxx_db = self.active_heavy_data.get("Pxx_db", [])
        unit = getattr(self.panel_spec, "spec_unit", "kHz")
        scale = 1000.0 if unit == "kHz" else 1.0
        
        ax3.set_ylabel("Power (dB/Hz)")
        ax3.set_xlabel(f"Frequency ({unit})")
        
        if len(f_psd) > 0 and len(Pxx_db) > 0:
            ax3.plot(f_psd / scale, Pxx_db, color='#8B5CF6', linewidth=1.5, zorder=2)
            
            # Highlight carrier peak
            carrier_freq_hz = self.active_heavy_data.get("carrier_freq", 0.0)
            if carrier_freq_hz > 0:
                # Encontra o índice no PSD mais próximo à portadora
                idx_c = np.argmin(np.abs(f_psd - carrier_freq_hz))
                carrier_x = f_psd[idx_c] / scale
                carrier_y = Pxx_db[idx_c]
            else:
                idx_max = np.argmax(Pxx_db)
                carrier_x = f_psd[idx_max] / scale
                carrier_y = Pxx_db[idx_max]
                
            ax3.plot(carrier_x, carrier_y, 'ro', markersize=6, zorder=3)
            ax3.annotate(f"{carrier_x:.2f} {unit}", 
                         xy=(carrier_x, carrier_y), xytext=(5, 5),
                         textcoords='offset points', color='white',
                         fontsize=9, zorder=4)
                         
            # Limite superior para focar na banda acústica relevante de insetos (ou Nyquist)
            rate = self.active_heavy_data.get("rate", 44100)
            max_khz = min(15.0, rate / 2000.0)
            ax3.set_xlim(0.0, max_khz if unit == "kHz" else max_khz * 1000.0)
            
            y_range = np.ptp(Pxx_db) if len(Pxx_db) > 0 else 10
            ax3.set_ylim(np.min(Pxx_db) - y_range*0.1, np.max(Pxx_db) + y_range*0.1)

        self.freq_engine = None

        # SPEC
        ax4 = self.panel_spec.ax
        ax4.clear()
        unit = getattr(self.panel_spec, "spec_unit", "kHz")
        scale = 1000.0 if unit == "kHz" else 1.0
        ymin = self.panel_spec.spin_spec_ymin.value() if hasattr(self.panel_spec, "spin_spec_ymin") else 0.0
        ymax = self.panel_spec.spin_spec_ymax.value() if hasattr(self.panel_spec, "spin_spec_ymax") else (10.0 if unit == "kHz" else 10000.0)
        ax4.set_ylabel(unit)
        ax4.set_xlabel("seconds")
        ax4.set_xlim(t_spec[0], t_spec[-1])
        ax4.set_ylim(ymin, ymax)
        self.spectro_engine = HighPerfSpectrogramEngine(ax4, Sxx_db, t_spec, f_spec, update_bg_callback=self.capture_backgrounds, unit=unit)
        self.spectro_engine.render_high_detail()

        # Atualiza mapa de eixos independente da posição atual.
        self.cursor_lines = []
        for panel in [self.panel_wave, self.panel_spec]:
            self.cursor_lines.append(panel.ax.axvline(x=0, color='#E5E8EB', linewidth=1.2, linestyle='-', zorder=9))

        for panel in self.all_panels:
            panel.apply_dark_theme()
        self._apply_plot_geometry()

        # Desenho inicial explícito: o histograma não participa do cache do cursor,
        # então precisa receber seu primeiro draw aqui para aparecer imediatamente.
        self.setUpdatesEnabled(False)
        try:
            for panel in self.all_panels:
                panel.canvas.draw()
        finally:
            self.setUpdatesEnabled(True)

        markers = []
        for idx, cp in enumerate(chirp_peaks_list):
            if not cp:
                continue
            t = float(cp[0] / rate)
            markers.append({"time": t, "color": "#F0A84B" if idx % 2 == 0 else "#3F94D5"})
        self.timeline.set_data(d["duration"], markers)
        self.timeline.set_position(self.player.position() / 1000.0)
        self._refresh_user_peak_markers()
        self._update_pulse_hover_data()
        self.capture_backgrounds()
        if cur_splitter_sizes and len(cur_splitter_sizes) >= 2 and cur_splitter_sizes[0] >= 50:
            self.splitter.setSizes(cur_splitter_sizes)

    def apply_spectrogram_y_limits(self, ymin, ymax, unit="kHz"):
        """Atualiza dinamicamente a escala, limites e unidade do eixo Y do espectrograma."""
        if not hasattr(self, "panel_spec"):
            return
        ax4 = self.panel_spec.ax
        unit_changed = (getattr(self, "_last_applied_spec_unit", None) != unit)
        self._last_applied_spec_unit = unit

        ax4.set_ylabel(unit)
        ax4.set_ylim(ymin, ymax)
        if hasattr(self, "spectro_engine") and self.spectro_engine:
            if unit_changed:
                self.spectro_engine.set_unit(unit)
            self.spectro_engine.render_high_detail()

        if unit_changed and getattr(self, "active_heavy_data", None):
            scale = 1000.0 if unit == "kHz" else 1.0
            rate = float(self.active_heavy_data.get("rate", 1.0))
            t_spec = self.active_heavy_data.get("t_spec")
            dom_freqs = self.active_heavy_data.get("dom_freqs")
            chirp_peaks_list = self.active_heavy_data.get("chirp_peaks_list", [])
            distant_pks = self.active_heavy_data.get("distant_peaks", [])
            env = self.active_heavy_data.get("env")
            marker_colors = {
                1: '#F59E0B', 2: '#EC4899', 3: '#8B5CF6', 4: '#3B82F6',
                5: '#10B981', 6: '#F97316', 7: '#06B6D4', 8: '#84CC16',
                9: '#EAB308', 10: '#A855F7', 11: '#14B8A6', 12: '#6366F1'
            }
            lines_to_keep = set(getattr(self, "cursor_lines", []) + getattr(self, "_click_alignment_lines", []))
            lines_to_remove = [line for line in ax4.lines if line not in lines_to_keep]
            for line in lines_to_remove:
                try:
                    line.remove()
                except Exception:
                    pass

            picos_por_contagem = {}
            for cp in chirp_peaks_list:
                qnt = len(cp)
                picos_por_contagem.setdefault(qnt, []).extend(cp)

            if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
                for qnt, pks in sorted(picos_por_contagem.items()):
                    pks_t = np.array(pks) / rate
                    freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs) / scale
                    ax4.plot(pks_t, freqs_at_pks, 'x', color=marker_colors.get(int(qnt), '#5F9ED1'), markersize=7, markeredgewidth=1.5, zorder=7)
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                    if valid_d:
                        d_times = np.array(valid_d) / rate
                        d_freqs = np.interp(d_times, t_spec, dom_freqs) / scale
                        ax4.plot(d_times, d_freqs, 'x', color='#9CA3AF', markersize=4.5, markeredgewidth=1.0, alpha=0.6, zorder=6)

        self.panel_spec.canvas.draw_idle()

    def apply_realtime_freq_tolerance(self, new_tol, source_panel=None):
        """Ajusta em tempo real a tolerância espectral (±Hz) em torno da frequência portadora."""
        new_tol = float(new_tol)
        self.algo_params["freq_tolerance_hz"] = new_tol

        # Sincroniza controles dos painéis para manter o mesmo valor visual
        if hasattr(self, "panel_spec") and self.panel_spec is not source_panel and hasattr(self.panel_spec, "set_carrier_tolerance"):
            self.panel_spec.set_carrier_tolerance(new_tol, notify=False)
        if hasattr(self, "panel_freq") and self.panel_freq is not source_panel and hasattr(self.panel_freq, "set_carrier_tolerance"):
            self.panel_freq.set_carrier_tolerance(new_tol, notify=False)

        d = getattr(self, "active_heavy_data", None)
        if not d:
            return

        # Debounce suave de 25 ms para deslizamento contínuo sem sobrecarga
        if not hasattr(self, "_carrier_tol_timer"):
            self._carrier_tol_timer = QTimer(self)
            self._carrier_tol_timer.setSingleShot(True)
            self._carrier_tol_timer.timeout.connect(self._execute_realtime_freq_tolerance)

        self._pending_carrier_tol = new_tol
        self._carrier_tol_timer.start(25)

    def _execute_realtime_freq_tolerance(self):
        d = getattr(self, "active_heavy_data", None)
        if not d:
            return
        new_tol = getattr(self, "_pending_carrier_tol", float(self.algo_params.get("freq_tolerance_hz", 300.0)))

        valid_peaks_stage2 = d.get("valid_peaks_stage2", d.get("peaks_detected", []))
        carrier_freq = float(d.get("carrier_freq", 5000.0))
        rate = float(d.get("rate", 44100))
        t_spec = d.get("t_spec", np.array([]))
        dom_freqs = d.get("dom_freqs", np.array([]))
        env = d.get("env1_smooth", d.get("env", np.array([])))
        data_b1 = d.get("data_b1", None)
        effective_params = {**self.algo_params, **self._adaptive_overrides, "freq_tolerance_hz": new_tol}
        learner = self.pulse_learner if getattr(self, "use_machine_learning", False) else None
        raw_peaks = d.get("peaks_detected", None)
        peak_dur_dict = d.get("peak_dur_dict", None)

        peaks_detected_set = set(int(p) for p in d.get("peaks_detected", []))
        peaks_verified_set = set(int(p) for p in d.get("peaks_user_verified", []))
        peaks_added = sorted(peaks_verified_set - peaks_detected_set)
        
        peaks, chirps, chirp_peaks_list, media, moda, all_distant, discarded_reasons = (
            CricketAnalyzer.reevaluate_carrier_tolerance(
                valid_peaks_stage2, carrier_freq, new_tol,
                rate, t_spec, dom_freqs, env, effective_params,
                data_b1=data_b1, pulse_learner=learner,
                base_discarded_reasons=d.get("discarded_peaks_reasons", {})
            )
        )

        d["peaks"] = list(peaks)
        d["chirps"] = chirps
        d["chirp_peaks_list"] = chirp_peaks_list
        d["media"] = media
        d["moda"] = moda
        d["distant_peaks"] = list(all_distant)
        d["discarded_peaks_reasons"] = discarded_reasons
        if "params" in d:
            d["params"]["freq_tolerance_hz"] = new_tol
            
        cf = d.get("carrier_freq", 0.0)
        if hasattr(self, "panel_spec"):
            self.panel_spec.set_carrier_info(cf, new_tol)
        if hasattr(self, "panel_freq"):
            self.panel_freq.set_carrier_info(cf, new_tol)

        # Preserva o enquadramento (zoom e pan X) atual dos gráficos
        cur_xlim = self.panel_wave.ax.get_xlim() if hasattr(self, "panel_wave") else None

        if self.active_filename:
            self.render_dashboard(self.active_filename)

        if cur_xlim is not None and cur_xlim[0] is not None and cur_xlim[1] is not None:
            for panel in (self.panel_wave, self.panel_spec):
                if hasattr(panel, "ax"):
                    panel.ax.set_xlim(cur_xlim)
            for panel in self.all_panels:
                panel.canvas.draw_idle()

    def _update_pulse_hover_data(self):
        """Atualiza a tabela de metadados de cada pulso para exibição de tooltip no hover."""
        self.pulse_hover_data = []
        d = getattr(self, "active_heavy_data", None)
        if not d:
            return
        rate = float(d.get("rate", 44100))
        env = d.get("env1_smooth", d.get("env", np.array([])))
        chirp_peaks_list = d.get("chirp_peaks_list", [])
        dom_freqs = d.get("dom_freqs", np.array([]))
        t_spec = d.get("t_spec", np.array([]))
        carrier_freq = float(d.get("carrier_freq", 0.0))
        freq_tol = float(d.get("params", {}).get("freq_tolerance_hz", 300.0))

        # 1. Pulsos válidos agrupados em chilreios
        seen_samples = set()
        for c_idx, cp in enumerate(chirp_peaks_list):
            qnt = len(cp)
            for p_idx, pk in enumerate(cp):
                pk = int(pk)
                seen_samples.add(pk)
                t_val = float(pk) / rate
                y_env = float(env[pk]) if (env is not None and len(env) > pk) else 0.0
                if len(t_spec) > 0 and len(dom_freqs) > 0:
                    y_freq = float(np.interp(t_val, t_spec, dom_freqs))
                else:
                    y_freq = 0.0
                self.pulse_hover_data.append({
                    "sample": pk,
                    "time": t_val,
                    "env_y": y_env,
                    "freq_y": y_freq,
                    "chirp_pulses": qnt,
                    "chirp_idx": c_idx + 1,
                    "pulse_num": p_idx + 1,
                    "status": "valid",
                    "carrier_freq": carrier_freq,
                })

        # 2. Pulsos descartados (marcados em cinza)
        distant_pks = d.get("distant_peaks", [])
        discarded_reasons = d.get("discarded_peaks_reasons", {})

        for pk in distant_pks:
            pk = int(pk)
            if pk in seen_samples:
                continue
            t_val = float(pk) / rate
            y_env = float(env[pk]) if (env is not None and len(env) > pk) else 0.0
            if len(t_spec) > 0 and len(dom_freqs) > 0:
                y_freq = float(np.interp(t_val, t_spec, dom_freqs))
            else:
                y_freq = 0.0

            reason = discarded_reasons.get(pk)
            if not reason:
                if carrier_freq > 0 and abs(y_freq - carrier_freq) > freq_tol:
                    diff = y_freq - carrier_freq
                    reason = (
                        f"Frequência fora da tolerância da portadora "
                        f"({y_freq:.0f} Hz; desvio de {diff:+.0f} Hz da portadora {carrier_freq:.0f} Hz; limite ±{freq_tol:.0f} Hz)"
                    )
                else:
                    reason = "Pulso isolado / ruído fora do padrão rítmico focal"

            self.pulse_hover_data.append({
                "sample": pk,
                "time": t_val,
                "env_y": y_env,
                "freq_y": y_freq,
                "status": "discarded",
                "reason": reason,
                "carrier_freq": carrier_freq,
            })

    def _update_summary_placeholder(self, filename=""):
        self.lbl_summary_file.setText(filename or "Nenhum arquivo selecionado")
        self.lbl_summary_meta.setText("Carregue um arquivo WAV para iniciar a análise")
        self.lbl_total.setText("—")
        self.lbl_metric_sub.setText("Moda: —   |   Média: —")
        if hasattr(self, 'lbl_elapsed'):
            self.lbl_elapsed.setText("00:00.00 / 00:00.00")
        if hasattr(self, 'btn_reanalisar_main'):
            self.btn_reanalisar_main.setText("Analisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("play", color="#FFFFFF", size=15))
            self.btn_reanalisar_main.setToolTip("Executar análise deste áudio")
        self.timeline.set_data(0, [])
        self.timeline.set_position(0)

    # ---------- exportação ----------
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
        unprocessed = [f for f in checked_files if f not in self.analysis_cache and f in self.loaded_files]
        for f in unprocessed:
            try:
                self.run_analysis(f, self.algo_params, render=False)
            except Exception as exc:
                print(f"Aviso ao processar {f} para relatório: {exc}")

        selected_cache = {
            fname: self.analysis_cache[fname]
            for fname in checked_files
            if fname in self.analysis_cache
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
            inst = self.report_params.get('institution', '').strip()
            name = self.report_params.get('researcher_name', '').strip()
            role = self.report_params.get('role', '').strip()
            level = self.report_params.get('level', '').strip()
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
        act_pdf_full = menu.addAction(make_ui_icon("export", color="#2563EB", size=15), "📄 Exportar Relatório Completo (.pdf)")
        act_pdf_full.triggered.connect(lambda: self.action_save_pdf(include_chirp_list=True))
        act_pdf_simple = menu.addAction(make_ui_icon("export", color="#0284C7", size=15), "📑 Exportar Relatório Simplificado (.pdf)")
        act_pdf_simple.triggered.connect(lambda: self.action_save_pdf(include_chirp_list=False))
        act_txt = menu.addAction(make_ui_icon("export", color="#64748B", size=15), "📝 Exportar Relatório em Texto (.txt)")
        act_txt.triggered.connect(self.action_save_txt)

        def _on_close():
            self._export_menu_open = False
            self._export_menu_last_close_time = time.time()

        menu.aboutToHide.connect(_on_close)
        self._export_menu_ref = menu
        self._export_menu_open = True
        menu.popup(self.btn_export_main.mapToGlobal(self.btn_export_main.rect().bottomLeft()))

    def action_save_pdf(self, include_chirp_list=True):
        checked_files = self.get_checked_files()
        if not checked_files:
            QMessageBox.warning(
                self,
                "Nenhum áudio selecionado",
                "Marque a caixinha de pelo menos um arquivo de áudio na lista para gerar o relatório em PDF."
            )
            return

        # Analisa em segundo plano qualquer arquivo marcado que ainda não esteja no cache
        unprocessed = [f for f in checked_files if f not in self.analysis_cache and f in self.loaded_files]
        for f in unprocessed:
            try:
                self.run_analysis(f, self.algo_params, render=False)
            except Exception as exc:
                print(f"Aviso ao processar {f} para relatório PDF: {exc}")

        selected_cache = {
            fname: self.analysis_cache[fname]
            for fname in checked_files
            if fname in self.analysis_cache
        }

        if not selected_cache:
            QMessageBox.warning(
                self,
                "Sem dados",
                "Nenhum dos áudios selecionados possui dados de análise válidos para o relatório."
            )
            return

        now = datetime.datetime.now()
        tipo_str = "Completo" if include_chirp_list else "Simplificado"
        default_name = f"Relatorio_{tipo_str}_Crinometro_{now.strftime('%Y%m%d_%H%M')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Exportar Relatório {tipo_str} em PDF", default_name, "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            from utils.report_generator import generate_pdf_report
            generate_pdf_report(
                file_path,
                self.report_params,
                selected_cache,
                self.algo_params,
                include_chirp_list=include_chirp_list
            )
            QMessageBox.information(
                self,
                I18N[self.lang]["success"],
                f"Relatório PDF ({tipo_str}) gerado com sucesso para {len(selected_cache)} áudio(s) selecionado(s)!\n\nSalvo em:\n{file_path}"
            )
        except Exception as err:
            QMessageBox.critical(
                self,
                I18N[self.lang]["error"],
                f"Falha ao gerar relatório em PDF:\n{str(err)}"
            )

    # ---------- reprodução ----------
    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.source().isEmpty():
                return
            self.player.play()

    def _update_play_icon(self):
        if not hasattr(self, "btn_play"):
            return
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        icon_color = "#FFFFFF" if self.theme_mode == "dark" else "#123B5D"
        self.btn_play.setIcon(make_ui_icon("pause" if playing else "play", color=icon_color, size=19))
        self.btn_play.setIconSize(QSize(19,19))
        self.btn_play.setToolTip("Pausar" if playing else "Reproduzir")

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
        self.btn_speed.setText(label)
        self.btn_speed.setToolTip(
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
            self.lbl_elapsed.setText(f"{self._format_playback_time(self.player.position()/1000.0)} / {self._format_playback_time(duration_s)}")
        markers = self.timeline.markers if hasattr(self, 'timeline') else []
        self.timeline.set_data(duration_s, markers)

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
                self.lbl_elapsed.setText(f"{self._format_playback_time(position_sec)} / {self._format_playback_time(duration_sec)}")
            except Exception:
                pass
        if hasattr(self, 'timeline'):
            try:
                self.timeline.set_position(position_sec)
            except Exception:
                pass
        for line in self.cursor_lines:
            try:
                line.set_xdata([position_sec, position_sec])
            except Exception:
                pass

        if not getattr(self, 'bg_cache_valid', False) or getattr(self, 'panning', False):
            current_time = time.time()
            if current_time - self.last_draw_time > 0.01:
                for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
                    try:
                        panel.canvas.draw_idle()
                    except Exception:
                        pass
                self.last_draw_time = current_time
            return

        if not self.backgrounds:
            return

        try:
            active_panels = [self.panel_wave, self.panel_spec]
            for panel, bg, line in zip(active_panels, self.backgrounds, self.cursor_lines):
                if bg is not None and hasattr(panel, 'ax') and panel.ax.bbox.width > 0 and panel.ax.bbox.height > 0:
                    panel.canvas.restore_region(bg)
                    panel.ax.draw_artist(line)
                    panel.canvas.blit(panel.ax.bbox)
        except Exception:
            self.bg_cache_valid = False
            for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
                try:
                    panel.canvas.draw_idle()
                except Exception:
                    pass

    def _refresh_histogram(self):
        """Redesenha o histograma bivariado: barras de contagem (eixo Y esquerdo)
        e linha de tendência de duração média do chilreio em ms (eixo Y direito)."""
        if not hasattr(self, 'panel_hist') or not getattr(self, 'active_heavy_data', None):
            return
        chirps = self.active_heavy_data.get('chirps', [])
        chirp_peaks_list = self.active_heavy_data.get('chirp_peaks_list', [])
        rate = float(self.active_heavy_data.get('rate', 1.0))
        pulse_colors = {
            2: '#2563EB',   # Azul Royal
            3: '#8B5CF6',   # Roxo / Violeta
            4: '#F97316',   # Laranja
            5: '#10B981',   # Verde Esmeralda
            6: '#EC4899',   # Rosa Magenta
            7: '#06B6D4',   # Ciano Turquesa
            8: '#EAB308',   # Amarelo Ouro
            9: '#84CC16',   # Verde Lima
            10: '#A855F7',  # Púrpura Forte
            1: '#94A3B8'    # Cinza ardósia
        }
        extra_pulse_color = '#F43F5E'
        hist_palette = pulse_colors
        
        ax_hist = self.panel_hist.ax
        ax_hist.clear()
        
        # Remove eixos secundários antigos para evitar acúmulo
        for child_ax in self.panel_hist.figure.get_axes():
            if child_ax is not ax_hist:
                self.panel_hist.figure.delaxes(child_ax)
        
        if len(chirps) == 0:
            self.panel_hist.canvas.draw_idle()
            return
        
        unique_pulses, counts = np.unique(chirps, return_counts=True)
        bars = ax_hist.bar(
            unique_pulses, counts,
            color=[hist_palette.get(int(x), extra_pulse_color) for x in unique_pulses],
            edgecolor='none', linewidth=0, width=0.68, zorder=3
        )
        
        is_dark = self.theme_mode == 'dark'
        ax_hist.grid(axis='y', color='#292D32' if is_dark else '#E2E8F0', linewidth=0.6, alpha=0.8, zorder=0)
        max_count = int(max(counts)) if len(counts) else 1
        hist_text_color = '#DDE1E5' if is_dark else '#1F2937'
        hist_tick_color = '#A9ADB5' if is_dark else '#1F2937'
        for bar in bars:
            ax_hist.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max_count*0.025, str(int(bar.get_height())),
                     ha='center', va='bottom', color=hist_text_color, fontsize=8.5, fontweight='bold')
        ax_hist.set_xticks(unique_pulses)
        ax_hist.set_xlabel("")
        ax_hist.set_ylabel("")
        ax_hist.tick_params(axis='x', labelsize=8.5, colors=hist_tick_color, length=0)
        ax_hist.tick_params(axis='y', labelsize=8, colors=hist_tick_color)
        ax_hist.set_ylim(0, max_count * 1.20)
        
        # ——— Eixo Y secundário: Duração média do chilreio (ms) ———
        dur_color = '#FF6B6B' if is_dark else '#DC2626'
        
        # Calcular duração média por classe de pulsos
        duration_by_class = {}
        for cp in chirp_peaks_list:
            n_pulses = len(cp)
            if n_pulses >= 1 and rate > 0:
                dur_ms = (cp[-1] - cp[0]) / rate * 1000.0
                duration_by_class.setdefault(n_pulses, []).append(dur_ms)
        
        avg_durations = {}
        for n_p, durs in duration_by_class.items():
            avg_durations[n_p] = float(np.mean(durs))
        
        if len(avg_durations) >= 2:
            ax2 = ax_hist.twinx()
            # Armazenar referência para o tema poder estilizar
            self.panel_hist._ax2 = ax2
            
            sorted_classes = sorted(avg_durations.keys())
            x_pts = np.array(sorted_classes, dtype=float)
            y_pts = np.array([avg_durations[k] for k in sorted_classes], dtype=float)
            
            ax2.plot(x_pts, y_pts, color=dur_color, linewidth=1.5, linestyle='--',
                     marker='o', markersize=5, markerfacecolor=dur_color,
                     markeredgecolor='white' if is_dark else '#1F2937',
                     markeredgewidth=0.8, zorder=5, alpha=0.9)
            
            # Anotações discretas de duração sobre cada marcador
            for xv, yv in zip(x_pts, y_pts):
                ax2.annotate(f'{yv:.0f}', (xv, yv), textcoords='offset points',
                             xytext=(0, 7), ha='center', fontsize=6.5,
                             color=dur_color, fontweight='bold')
            
            dur_label_color = dur_color
            ax2.set_ylabel("Duração (ms)", fontsize=7.5, color=dur_label_color)
            ax2.tick_params(axis='y', labelsize=7, colors=dur_label_color, length=2)
            for sp in ax2.spines.values():
                sp.set_visible(False)
            ax2.spines['right'].set_visible(True)
            ax2.spines['right'].set_color(dur_color)
            ax2.spines['right'].set_linewidth(0.8)
            ax2.spines['right'].set_alpha(0.5)
            ax2.grid(False)
            
            # Margem vertical para não colar nos limites
            y_min_d = min(y_pts) * 0.85 if min(y_pts) > 0 else 0
            y_max_d = max(y_pts) * 1.20
            ax2.set_ylim(y_min_d, y_max_d)
            ax2.set_facecolor('none')
        else:
            self.panel_hist._ax2 = None
        
        # ——— Legenda unificada ———
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        legend_handles = [Patch(facecolor=hist_palette.get(int(x), extra_pulse_color), edgecolor='none', label=f'{int(x)} pulsos')
                          for x in unique_pulses]
        if len(avg_durations) >= 2:
            legend_handles.append(Line2D([0], [0], color=dur_color, linewidth=1.5, linestyle='--',
                                         marker='o', markersize=4, label='Duração (ms)'))
        if legend_handles:
            hist_w = self.panel_hist.width()
            leg_ncol = min(3 if hist_w < 340 else 4, len(legend_handles))
            leg_fs = 7.0 if hist_w < 280 else (7.5 if hist_w < 340 else 8.0)
            leg = ax_hist.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.11),
                             ncol=leg_ncol, frameon=False, fontsize=leg_fs, handlelength=0.9,
                             columnspacing=0.5, borderaxespad=0.0)
            leg.get_frame().set_facecolor((0, 0, 0, 0))
            leg.get_frame().set_alpha(0.0)
            leg.get_frame().set_edgecolor((0, 0, 0, 0))
            leg.get_frame().set_linewidth(0)
            for text in leg.get_texts():
                text.set_color(hist_tick_color)
        
        self.panel_hist.canvas.draw_idle()

    def _refresh_user_peak_markers(self):
        """Renderiza marcadores de picos do usuário em todos os gráficos relevantes (onda, freq, spec)."""
        if not hasattr(self, 'panel_wave'):
            return
        
        # Limpa marcadores antigos de todos os painéis
        for artist in getattr(self, '_wave_user_markers', []):
            try:
                artist.remove()
            except Exception:
                pass
        self._wave_user_markers = []

        if not self.active_heavy_data:
            return

        rate = float(self.active_heavy_data.get('rate', 1.0))
        t_spec = self.active_heavy_data.get('t_spec', [])
        dom_freqs = self.active_heavy_data.get('dom_freqs', [])
        env = self.active_heavy_data.get('env')
        
        # 1. Desenhar marcadores de chirps classificados
        chirp_peaks_list = self.active_heavy_data.get('chirp_peaks_list', [])
        picos_por_contagem = {}
        for cp in chirp_peaks_list:
            qnt = len(cp)
            picos_por_contagem.setdefault(qnt, []).extend(cp)
            
        pulse_colors = {
            2: '#2563EB',   # Azul Royal
            3: '#8B5CF6',   # Roxo / Violeta
            4: '#F97316',   # Laranja
            5: '#10B981',   # Verde Esmeralda
            6: '#EC4899',   # Rosa Magenta
            7: '#06B6D4',   # Ciano Turquesa
            8: '#EAB308',   # Amarelo Ouro
            9: '#84CC16',   # Verde Lima
            10: '#A855F7',  # Púrpura Forte
            1: '#94A3B8'    # Cinza ardósia
        }
        extra_pulse_color = '#F43F5E'
        
        # 2. Distant Peaks
        distant_pks = self.active_heavy_data.get('distant_peaks', [])
        
        ax1 = getattr(self.panel_wave, 'ax', None)
        ax3 = getattr(self.panel_freq, 'ax', None)
        ax4 = getattr(self.panel_spec, 'ax', None)
        
        if ax1 and env is not None:
            for qnt, pks in sorted(picos_por_contagem.items()):
                pks_t = np.array(pks) / rate
                lines = ax1.plot(pks_t, env[pks], 'x', color=pulse_colors.get(int(qnt), extra_pulse_color), markersize=7, markeredgewidth=1.7, zorder=7)
                self._wave_user_markers.extend(lines)
            if distant_pks:
                valid_d = [dp for dp in distant_pks if 0 <= dp < len(env)]
                if valid_d:
                    lines = ax1.plot(np.array(valid_d) / rate, env[valid_d], 'x', color='#64748B', markersize=5.5, markeredgewidth=1.1, alpha=0.55, zorder=5)
                    self._wave_user_markers.extend(lines)

        if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
            pulse_meta = getattr(self, "pulse_metadata", {})
            
            def get_freqs_for_peaks(pks):
                pks_t = np.array(pks) / rate
                f = np.interp(pks_t, t_spec, dom_freqs)
                for i, p in enumerate(pks):
                    if p in pulse_meta and "freq" in pulse_meta[p]:
                        f[i] = pulse_meta[p]["freq"]
                return pks_t, f

            if ax3:
                for qnt, pks in sorted(picos_por_contagem.items()):
                    pks_t, freqs_at_pks = get_freqs_for_peaks(pks)
                    lines = ax3.plot(pks_t, freqs_at_pks, 'x', color=pulse_colors.get(int(qnt), '#5F9ED1'), markersize=6, markeredgewidth=1.4, zorder=7)
                    self._wave_user_markers.extend(lines)
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                    if valid_d:
                        d_times, d_freqs = get_freqs_for_peaks(valid_d)
                        lines = ax3.plot(d_times, d_freqs, 'x', color='#64748B', markersize=5, markeredgewidth=1.1, alpha=0.55, zorder=5)
                        self._wave_user_markers.extend(lines)

            if ax4:
                unit = getattr(self.panel_spec, "spec_unit", "kHz")
                scale = 1000.0 if unit == "kHz" else 1.0
                for qnt, pks in sorted(picos_por_contagem.items()):
                    pks_t, freqs_at_pks = get_freqs_for_peaks(pks)
                    lines = ax4.plot(pks_t, freqs_at_pks / scale, 'x', color=pulse_colors.get(int(qnt), '#5F9ED1'), markersize=7, markeredgewidth=1.5, zorder=7)
                    self._wave_user_markers.extend(lines)
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                    if valid_d:
                        d_times, d_freqs = get_freqs_for_peaks(valid_d)
                        lines = ax4.plot(d_times, d_freqs / scale, 'x', color='#94A3B8', markersize=5, markeredgewidth=1.0, alpha=0.5, zorder=5)
                        self._wave_user_markers.extend(lines)

        # 3. Marcadores do Usuário (Adicionados, Confirmados, Removidos)
        if self.peaks_user_verified and self.peaks_detected:
            peaks_detected_set = set(int(p) for p in self.peaks_detected)
            peaks_verified_set = set(int(p) for p in self.peaks_user_verified)

            peaks_confirmed = sorted(peaks_verified_set & peaks_detected_set)
            peaks_added = sorted(peaks_verified_set - peaks_detected_set)
            peaks_removed = sorted(peaks_detected_set - peaks_verified_set)

            if ax1:
                if peaks_confirmed:
                    xdata = np.asarray(peaks_confirmed, dtype=float) / rate
                    scatter = ax1.scatter(xdata, np.zeros_like(xdata), s=60, marker='o', 
                                         color='#10B981', edgecolors='#047857', linewidths=1.5, zorder=4)
                    self._wave_user_markers.append(scatter)

                if peaks_added:
                    xdata = np.asarray(peaks_added, dtype=float) / rate
                    scatter = ax1.scatter(xdata, np.zeros_like(xdata), s=60, marker='^', 
                                         color='#3B82F6', edgecolors='#1E40AF', linewidths=1.5, zorder=4)
                    self._wave_user_markers.append(scatter)

                if peaks_removed:
                    xdata = np.asarray(peaks_removed, dtype=float) / rate
                    scatter = ax1.scatter(xdata, np.zeros_like(xdata), s=80, marker='x', 
                                         color='#EF4444', linewidths=2.0, zorder=4)
                    self._wave_user_markers.append(scatter)

            if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
                for peaks, color, marker in [
                    (peaks_confirmed, '#10B981', 'o'),
                    (peaks_added, '#3B82F6', '^'),
                    (peaks_removed, '#EF4444', 'x'),
                ]:
                    if peaks:
                        pks_t = np.asarray(peaks, dtype=float) / rate
                        freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
                        
                        # Usa a frequência manual exata caso o usuário tenha clicado no espectrograma
                        pulse_meta = getattr(self, "pulse_metadata", {})
                        for i, p in enumerate(peaks):
                            if p in pulse_meta and "freq" in pulse_meta[p]:
                                freqs_at_pks[i] = pulse_meta[p]["freq"]
                        
                        if ax3:
                            lines = ax3.plot(pks_t, freqs_at_pks, marker=marker, linestyle='none',
                                            color=color, markersize=8, markeredgewidth=1.2, zorder=4)
                            self._wave_user_markers.extend(lines)
                            
                        if ax4:
                            unit = getattr(self.panel_spec, "spec_unit", "kHz")
                            scale = 1000.0 if unit == "kHz" else 1.0
                            freqs_at_pks_spec = freqs_at_pks / scale
                            lines = ax4.plot(pks_t, freqs_at_pks_spec, marker=marker, linestyle='none',
                                            color=color, markersize=8, markeredgewidth=1.2, zorder=4)
                            self._wave_user_markers.extend(lines)

        self._update_pulse_hover_data()
        for panel in self.all_panels:
            try:
                panel.canvas.draw_idle()
            except Exception:
                pass

    def _find_nearest_user_peak(self, time_sec, tolerance_sec=0.005):
        """Encontra o pico mais próximo ao clique, com tolerância precisa de 5 ms."""
        if not self.peaks_user_verified or not self.active_heavy_data:
            return None
        rate = float(self.active_heavy_data.get('rate', 1.0))
        tolerance_samples = max(2, int(round(tolerance_sec * rate)))
        peak_samples = np.asarray(self.peaks_user_verified, dtype=int)
        target = int(round(float(time_sec) * rate))
        diffs = np.abs(peak_samples - target)
        if diffs.size == 0:
            return None
        nearest_idx = int(np.argmin(diffs))
        if diffs[nearest_idx] <= tolerance_samples:
            return int(peak_samples[nearest_idx])
        return None

    def _toggle_peak_marker(self, time_sec, panel=None, event=None, f_click=None, amp_click=None):
        """Alterna a classificação do pico mais próximo com snapping inteligente em pixels ou adiciona um novo pico."""
        if not self.active_heavy_data:
            return
        rate = float(self.active_heavy_data.get('rate', 1.0))
        target = int(round(float(time_sec) * rate))
        candidates = sorted(set(int(p) for p in self.peaks_detected) |
                            set(int(p) for p in self.peaks_user_verified))
        nearest = None

        if candidates:
            # Hit-box snapping adaptativo em pixels de tela (tolerância suave de ~15px)
            ax = panel.ax if (panel and hasattr(panel, 'ax')) else (event.inaxes if event else None)
            if ax is not None and event is not None and getattr(event, 'x', None) is not None:
                xlim = ax.get_xlim()
                pad = max(0.1, (xlim[1] - xlim[0]) * 0.1)
                vis_cands = [p for p in candidates if (xlim[0] - pad) <= (p / rate) <= (xlim[1] + pad)]
                if not vis_cands:
                    vis_cands = candidates
                cand_times = np.asarray(vis_cands, dtype=float) / rate
                pts_disp = ax.transData.transform(np.column_stack([cand_times, np.zeros_like(cand_times)]))
                pixel_dists = np.abs(pts_disp[:, 0] - event.x)
                min_idx = int(np.argmin(pixel_dists))
                if pixel_dists[min_idx] <= 15.0 and abs(cand_times[min_idx] - float(time_sec)) <= 0.020:
                    nearest = vis_cands[min_idx]
            else:
                # Fallback adaptativo à janela temporal visível ou 5 ms
                if ax is not None:
                    xlim = ax.get_xlim()
                    vis_span = max(0.01, xlim[1] - xlim[0])
                    time_tol_sec = min(0.020, max(0.003, vis_span * 0.015))
                else:
                    time_tol_sec = 0.005
                distances = np.abs(np.asarray(candidates, dtype=int) - target)
                min_dist_idx = int(np.argmin(distances))
                if distances[min_dist_idx] <= int(round(time_tol_sec * rate)):
                    nearest = candidates[min_dist_idx]

        self._pulse_edit_history.append(list(self.peaks_user_verified))
        if len(self._pulse_edit_history) > 50:
            self._pulse_edit_history = self._pulse_edit_history[-50:]

        self.pulse_metadata = getattr(self, "pulse_metadata", {})

        if nearest is not None and nearest in self.peaks_user_verified:
            self.peaks_user_verified = [int(p) for p in self.peaks_user_verified if int(p) != nearest]
        elif nearest is not None:
            self.peaks_user_verified = sorted(set(self.peaks_user_verified + [nearest]))
            if f_click is not None or amp_click is not None:
                self.pulse_metadata[nearest] = {"idx": nearest}
                if f_click is not None: self.pulse_metadata[nearest]["freq"] = f_click
                if amp_click is not None: self.pulse_metadata[nearest]["amp"] = amp_click
        else:
            self.peaks_user_verified = sorted(set(self.peaks_user_verified + [target]))
            if f_click is not None or amp_click is not None:
                self.pulse_metadata[target] = {"idx": target}
                if f_click is not None: self.pulse_metadata[target]["freq"] = f_click
                if amp_click is not None: self.pulse_metadata[target]["amp"] = amp_click
        self.active_heavy_data['peaks_user_verified'] = list(self.peaks_user_verified)
        if self.active_filename:
            combined = []
            for p in self.peaks_user_verified:
                if getattr(self, "pulse_metadata", None) and p in self.pulse_metadata:
                    combined.append(self.pulse_metadata[p])
                else:
                    combined.append(int(p))
            self.corrections_by_file[self.active_filename] = combined
            self._save_corrections_state()

        for panel in self.all_panels:
            if hasattr(panel, "btn_pulse_undo"):
                panel.btn_pulse_undo.setEnabled(True)

        # Recalcula chilreios e métricas imediatamente após a alteração do usuário de forma ultra rápida
        if self.peaks_user_verified and len(self.peaks_user_verified) >= 2:
            try:
                peaks_detected_set = set(int(p) for p in self.peaks_detected)
                peaks_verified_set = set(int(p) for p in self.peaks_user_verified)
                peaks_added = sorted(peaks_verified_set - peaks_detected_set)
                
                effective_params = {**self.algo_params, **self._adaptive_overrides}
                chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
                    self.peaks_user_verified,
                    effective_params,
                    rate,
                    self.active_heavy_data['env'],
                    raw_signal=self.active_heavy_data.get('data_b1')
                )
                self.active_heavy_data['chirps'] = chirps
                self.active_heavy_data['chirp_peaks_list'] = chirp_peaks_list
                self.active_heavy_data['media'] = media
                self.active_heavy_data['moda'] = moda
                if hasattr(self, 'lbl_total'):
                    self.lbl_total.setText(str(len(chirps)))
                if hasattr(self, 'lbl_metric_sub'):
                    self.lbl_metric_sub.setText(f"Moda: {moda}   |   Média: {media:.2f}")
                if self.active_filename and self.active_filename in self.analysis_cache:
                    self.analysis_cache[self.active_filename]["chirps"] = chirps
                    self.analysis_cache[self.active_filename]["media"] = media
                    self.analysis_cache[self.active_filename]["moda"] = moda
            except Exception:
                pass

        # Atualiza a contagem dos chilreios e as marcações de forma ultra-rápida!
        self._refresh_histogram()
        self._refresh_user_peak_markers()

    def _adapt_advanced_params(self):
        """Atualiza sobreposições adaptativas com estatísticas das correções atuais.

        Os valores calculados são armazenados em self._adaptive_overrides — um dict
        separado de self.algo_params — garantindo que os parâmetros base do usuário
        nunca sejam corrompidos pela adaptação automática. As sobreposições são
        mescladas em tempo de análise dentro de run_analysis().
        """
        if not self.active_heavy_data or not self.peaks_user_verified:
            return
        env = self.active_heavy_data.get("env")
        if env is None:
            return
        rate = float(self.active_heavy_data.get("rate", 1.0))
        features = np.asarray([
            PulseLearner.extract_features_for_peak(p, rate, env)
            for p in self.peaks_user_verified
        ])
        if features.size == 0 or features.shape[1] < 14:
            return

        adaptation = float(self.algo_params.get("adaptation_rate", 0.10))
        adaptation = min(0.15, max(0.0, adaptation))

        # Ajuste seguro e fisiológico de proeminência relativa
        target_prom = float(np.percentile(features[:, 6], 20)) * 0.08
        current_prominence = float(self._adaptive_overrides.get(
            "prominence", self.algo_params.get("prominence", 0.01)
        ))
        new_prom = (1.0 - adaptation) * current_prominence + adaptation * target_prom
        self._adaptive_overrides["prominence"] = float(np.clip(new_prom, 0.002, 0.08))

        # Manutenção de noise_floor em faixa segura (0.85 a 1.05)
        current_noise = float(self._adaptive_overrides.get(
            "noise_floor", self.algo_params.get("noise_floor", 0.90)
        ))
        self._adaptive_overrides["noise_floor"] = float(np.clip(current_noise, 0.85, 1.05))

        target_width_ms = float(np.median(features[:, 1]) * 1000.0)
        if target_width_ms > 0:
            current_width = float(self._adaptive_overrides.get(
                "width_min_ms", self.algo_params.get("width_min_ms", 0.0)
            ))
            new_width = (1.0 - adaptation) * current_width + adaptation * (target_width_ms * 0.40)
            self._adaptive_overrides["width_min_ms"] = float(np.clip(new_width, 0.0, 25.0))

    def _undo_pulse_edit(self):
        if not self._pulse_edit_history:
            return
        self.peaks_user_verified = self._pulse_edit_history.pop()
        self.active_heavy_data['peaks_user_verified'] = list(self.peaks_user_verified)
        if self.active_filename:
            combined = []
            for p in self.peaks_user_verified:
                if getattr(self, "pulse_metadata", None) and p in self.pulse_metadata:
                    combined.append(self.pulse_metadata[p])
                else:
                    combined.append(int(p))
            self.corrections_by_file[self.active_filename] = combined
            self._save_corrections_state()
        enabled = bool(self._pulse_edit_history)
        for panel in self.all_panels:
            if hasattr(panel, "btn_pulse_undo"):
                panel.btn_pulse_undo.setEnabled(enabled)

        # Recalcula chilreios e métricas após desfeita
        if self.active_heavy_data and self.peaks_user_verified and len(self.peaks_user_verified) >= 2:
            try:
                rate = float(self.active_heavy_data.get('rate', 1.0))
                effective_params = {**self.algo_params, **self._adaptive_overrides}
                chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
                    self.peaks_user_verified,
                    effective_params,
                    rate,
                    self.active_heavy_data['env'],
                    raw_signal=self.active_heavy_data.get('data_b1')
                )
                self.active_heavy_data['chirps'] = chirps
                self.active_heavy_data['chirp_peaks_list'] = chirp_peaks_list
                self.active_heavy_data['media'] = media
                self.active_heavy_data['moda'] = moda
                if hasattr(self, 'lbl_total'):
                    self.lbl_total.setText(str(len(chirps)))
                if hasattr(self, 'lbl_metric_sub'):
                    self.lbl_metric_sub.setText(f"Moda: {moda}   |   Média: {media:.2f}")
                if self.active_filename and self.active_filename in self.analysis_cache:
                    self.analysis_cache[self.active_filename]["chirps"] = chirps
                    self.analysis_cache[self.active_filename]["media"] = media
                    self.analysis_cache[self.active_filename]["moda"] = moda
            except Exception:
                pass
        self._refresh_histogram()
        self._refresh_user_peak_markers()

    def _save_corrections_state(self):
        """Persiste correções sem exibir o diálogo de confirmação das configurações."""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            if not isinstance(config, dict):
                config = {}
            config["corrections_by_file"] = self.corrections_by_file
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except (OSError, ValueError, TypeError) as exc:
            print(f"Erro ao persistir correções: {exc}")

    def learn_from_corrections(self):
        curr = self.list_widget.currentItem()
        filename = self._get_item_filename(curr) if curr else getattr(self, 'active_filename', None)
        if not filename:
            QMessageBox.warning(self, "Nenhum arquivo", "Selecione um arquivo antes de treinar.")
            return

        if not self.active_heavy_data:
            QMessageBox.warning(self, "Sem dados", "Primeiro carregue um arquivo WAV antes de treinar o classificador.")
            return

        detected = list(self.peaks_detected)
        verified = list(self.peaks_user_verified)
        detected_set = set(int(p) for p in detected)
        verified_set = set(int(p) for p in verified)

        if not detected_set or not verified_set:
            QMessageBox.warning(self, "Dados insuficientes", "Você precisa ter tanto pulsos detectados quanto verificados para treinar.")
            return

        # O usuário confirmou que o estado atual é o correto, então salvamos no cache
        self.corrections_by_file[filename] = list(verified)
        self._save_corrections_state()

        spinner = ButtonSpinner(self.btn_learn_corrections, "Treinando...")
        spinner.start()

        rate = float(self.active_heavy_data.get('rate', 1.0))
        env = self.active_heavy_data.get('env')
        data_b1 = self.active_heavy_data.get('data_b1')

        def _task():
            self.pulse_learner.update_from_corrections(
                detected, verified, rate, env, raw_signal=data_b1
            )
            self._adapt_advanced_params()
            self.pulse_learner.save_to_config()
            return len(detected_set ^ verified_set)

        worker = GenericWorker(_task)
        self._learn_worker = worker

        def _on_finished(num_corrections):
            spinner.stop(make_ui_icon("brain", color="#FFFFFF", size=17), I18N[self.lang]["learn_corrections"])
            if hasattr(self, 'lbl_model_status'):
                self._update_ml_toggle_ui()
            QMessageBox.information(
                self, 
                I18N[self.lang]['success'], 
                f'Modelo treinado com sucesso!\n\n'
                f'Arquivo: {filename}\n'
                f'Picos analisados: {len(detected)}\n'
                f'Correções aprendidas: {num_corrections}\n'
                f'Picos verificados: {len(verified)}\n\n'
                f'O modelo com 500 árvores foi atualizado e salvo.'
            )

        def _on_error(err_msg):
            spinner.stop(make_ui_icon("brain", color="#FFFFFF", size=17), I18N[self.lang]["learn_corrections"])
            QMessageBox.critical(self, I18N[self.lang]['error'], f'Não foi possível treinar o classificador:\n{err_msg}')

        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)
        worker.start()

    def on_double_click(self, event):
        if event.inaxes == self.panel_wave.ax and event.xdata is not None:
            self._toggle_peak_marker(event.xdata, panel=self.panel_wave, event=event)

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
            QTimer.singleShot(30, self._apply_plot_geometry)
            if not self.active_heavy_data:
                QTimer.singleShot(45, self._draw_empty_plots)

    # ---------- maximização / pan / zoom ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_cache_valid = False
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
        self._apply_plot_geometry()
        for p in self.all_panels:
            p.canvas.draw_idle()
        if self.active_heavy_data:
            QTimer.singleShot(150, self.capture_backgrounds)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.expanded_panel is not None:
            self.swap_main_panel(self.expanded_panel)
        else:
            super().keyPressEvent(event)

    def toggle_expand(self, panel):
        self.swap_main_panel(panel)

    def capture_backgrounds(self):
        if not self.cursor_lines:
            return
        for line in self.cursor_lines:
            line.set_animated(False)
            line.set_visible(False)
        active_panels = [self.panel_wave, self.panel_spec]
        self.backgrounds = []
        for panel in active_panels:
            panel.canvas.draw()
            self.backgrounds.append(panel.canvas.copy_from_bbox(panel.ax.bbox))
        for line in self.cursor_lines:
            line.set_visible(True)
            line.set_animated(True)
        self.bg_cache_valid = True

    def on_press(self, event):
        """Gerencia cliques em painéis. Se modo de edição de pulsos estiver ativo, permite editar."""
        # Alinha o marcador de referência temporal com o botão esquerdo (button == 1)
        if event.button == 1 and event.xdata is not None:
            self._align_click_marker(float(event.xdata))
        
        # Determina qual painel foi clicado
        clicked_panel = None
        for panel in self.all_panels:
            if event.inaxes == panel.ax:
                clicked_panel = panel
                break

        # Se modo de edição está ativo e clicou com o botão esquerdo em um painel que suporta edição
        if event.button == 1 and clicked_panel and getattr(clicked_panel, 'pulse_edit_mode', False) and event.xdata is not None:
            if self.active_heavy_data:
                rate = float(self.active_heavy_data.get('rate', 1.0))
                time_sec = float(event.xdata)
                kwargs = {"panel": clicked_panel, "event": event}
                if event.ydata is not None:
                    if clicked_panel == self.panel_spec:
                        # ydata is in the displayed unit (Hz or kHz). Normalizing to Hz.
                        unit = getattr(self.panel_spec, "spec_unit", "kHz")
                        kwargs["f_click"] = float(event.ydata) * (1000.0 if unit == "kHz" else 1.0)
                    elif clicked_panel == self.panel_wave:
                        kwargs["amp_click"] = float(event.ydata)
                self._toggle_peak_marker(time_sec, **kwargs)
                return

        # Arrastar / Pan dos gráficos com o BOTÃO DIREITO do mouse (button == 3)
        if clicked_panel and clicked_panel != self.panel_hist and event.button == 3:
            self.panning = True
            self.active_ax = event.inaxes
            self.start_xlim = self.active_ax.get_xlim()
            self.start_ylim = self.active_ax.get_ylim()
            self.start_x, self.start_y = event.x, event.y
            self.bg_cache_valid = False
            for line in self.cursor_lines:
                line.set_animated(False)

    def _align_click_marker(self, time_sec):
        """Desenha a referência vertical do clique em todos os eixos temporais."""
        for line in self._click_alignment_lines:
            line.remove()
        self._click_alignment_lines = []
        for panel in (self.panel_wave, self.panel_freq, self.panel_spec):
            for ax in panel.figure.axes:
                self._click_alignment_lines.append(
                    ax.axvline(x=time_sec, color="#FACC15", linewidth=1.0,
                               linestyle="--", alpha=0.75, zorder=8)
                )
            panel.canvas.draw_idle()

    def _update_pulse_edit_buttons(self, activated_panel):
        """Quando um painel é ativado para edição de pulsos, desativa os outros."""
        for panel in self.all_panels:
            if panel != activated_panel:
                panel.pulse_edit_mode = False
                if hasattr(panel, 'btn_pulse_edit'):
                    panel.btn_pulse_edit.blockSignals(True)
                    panel.btn_pulse_edit.setChecked(False)
                    panel.btn_pulse_edit.setStyleSheet("")
                    panel.btn_pulse_edit.setToolTip("Ativar modo de edição de pulsos (clique para adicionar/remover)")
                    panel.btn_pulse_edit.blockSignals(False)

    def on_release(self, event):
        if event.button == 3:
            self.panning, self.active_ax = False, None
            for panel in self.all_panels:
                panel.canvas.draw_idle()
            
            # Deixamos o recálculo do render_high_detail a encargo do debounce_timer das engines (250ms),
            # para não travar a UI ao soltar o mouse. Agendamos o background cache para logo após.
            QTimer.singleShot(350, self.capture_backgrounds)

    def on_sync_toggled(self, enabled):
        """Reestabelece uma geometria consistente nos três eixos temporais ao ativar a sincronização."""
        if getattr(self, "_swapping_panels", False):
            return
        self.bg_cache_valid = False
        for line in self.cursor_lines:
            line.set_animated(False)
        if not self.active_heavy_data:
            return

        duration = float(self.active_heavy_data.get("duration", 0.0))
        if duration <= 0:
            return

        axes = [self.panel_wave.ax, self.panel_spec.ax]
        for ax in axes:
            ax.set_xlim(0.0, duration)
        self.panel_wave.ax.set_ylim(-1.05, 1.05)
        p = self.active_heavy_data.get("params", {})
        if hasattr(self, "panel_spec") and hasattr(self.panel_spec, "spin_spec_ymin"):
            self.panel_spec.ax.set_ylim(self.panel_spec.spin_spec_ymin.value(), self.panel_spec.spin_spec_ymax.value())
        elif p:
            rate = float(self.active_heavy_data.get("rate", 44100.0))
            nyq = rate / 2.0
            unit = getattr(self.panel_spec, "spec_unit", "kHz") if hasattr(self, "panel_spec") else "kHz"
            if unit == "kHz":
                self.panel_spec.ax.set_ylim(0.0, nyq / 1000.0)
            else:
                self.panel_spec.ax.set_ylim(0.0, nyq)

        # Conclui a geometria do Qt e renderiza imediatamente, sem esperar timers.
        QApplication.processEvents()
        self._refresh_synced_views()

    def _refresh_synced_views(self):
        """Redesenha os painéis depois que o Qt estabiliza as geometrias.
        Usa renderização de alta definição para evitar tiles/viewport cortados.
        """
        if not self.active_heavy_data:
            return
        QApplication.processEvents()
        self.bg_cache_valid = False
        for line in self.cursor_lines:
            line.set_animated(False)
            line.set_visible(False)

        duration = float(self.active_heavy_data.get("duration", 0.0))
        p = self.active_heavy_data.get("params", {})
        self.panel_wave.ax.set_xlim(0.0, duration)
        self.panel_spec.ax.set_xlim(float(self.active_heavy_data["t_spec"][0]) if len(self.active_heavy_data.get("t_spec", [])) else 0.0, float(self.active_heavy_data["t_spec"][-1]) if len(self.active_heavy_data.get("t_spec", [])) else duration)
        self.panel_wave.ax.set_ylim(-1.05, 1.05)
        if hasattr(self, "panel_spec") and hasattr(self.panel_spec, "spin_spec_ymin"):
            self.panel_spec.ax.set_ylim(self.panel_spec.spin_spec_ymin.value(), self.panel_spec.spin_spec_ymax.value())
        elif p:
            rate = float(self.active_heavy_data.get("rate", 44100.0))
            nyq = rate / 2.0
            unit = getattr(self.panel_spec, "spec_unit", "kHz") if hasattr(self, "panel_spec") else "kHz"
            if unit == "kHz":
                self.panel_spec.ax.set_ylim(0.0, nyq / 1000.0)
            else:
                self.panel_spec.ax.set_ylim(0.0, nyq)

        if self.spectro_engine:
            self.spectro_engine.render_high_detail()
        if self.line_engine:
            self.line_engine.render_high_detail()
        if getattr(self, "freq_engine", None):
            self.freq_engine.render_high_detail()
        for panel in self.all_panels:
            panel.canvas.draw()

        for line in self.cursor_lines:
            line.set_visible(True)
            line.set_animated(True)
        QTimer.singleShot(40, self.capture_backgrounds)

    def _sync_render(self, target_panels, xmin, xmax):
        if getattr(self, "_swapping_panels", False):
            return
        current_time = time.time()
        if current_time - self.sync_throttle_time < 0.025:
            return
        for panel in target_panels:
            if not panel.isVisible():
                continue
            ymin, ymax = panel.ax.get_ylim()
            if self.spectro_engine and panel == self.panel_spec:
                self.spectro_engine.render_interactive(xmin, xmax, ymin, ymax, is_sync=True)
            elif self.line_engine and panel == self.panel_wave:
                self.line_engine.render_interactive(xmin, xmax, is_sync=True)
            elif getattr(self, "freq_engine", None) and panel == self.panel_freq:
                self.freq_engine.render_interactive(xmin, xmax, is_sync=True)
            else:
                panel.canvas.draw_idle()
        self.sync_throttle_time = current_time

    def _clamp_bounds(self, ax, xmin, xmax, ymin, ymax):
        if not self.active_heavy_data: return xmin, xmax, ymin, ymax
        d = self.active_heavy_data
        dur = float(d.get("duration", 0.0))
        rate = float(d.get("rate", 44100))
        nyq = rate / 2.0
        
        c_xmin, c_xmax, c_ymin, c_ymax = None, None, None, None

        if ax == self.panel_wave.ax:
            c_xmin, c_xmax = 0.0, dur
            c_ymin, c_ymax = -1.05, 1.05
        elif getattr(self, "panel_freq", None) and ax == self.panel_freq.ax:
            unit = getattr(self.panel_spec, "spec_unit", "kHz")
            max_x = nyq / 1000.0
            if unit != "kHz": max_x = nyq
            c_xmin, c_xmax = 0.0, max_x
            
            Pxx_db = d.get("Pxx_db", [])
            if len(Pxx_db) > 0:
                yr = np.ptp(Pxx_db)
                c_ymin, c_ymax = np.min(Pxx_db) - yr*0.1, np.max(Pxx_db) + yr*0.1
        elif ax == self.panel_spec.ax:
            c_xmin, c_xmax = 0.0, dur
            unit = getattr(self.panel_spec, "spec_unit", "kHz")
            c_ymin, c_ymax = 0.0, nyq / 1000.0 if unit == "kHz" else nyq
        elif getattr(self, "panel_hist", None) and ax == self.panel_hist.ax:
            chirps = np.asarray(d.get("chirps", []))
            if chirps.size > 0:
                c_xmin, c_xmax = float(chirps.min()) - 0.65, float(chirps.min()) + 0.65
                ym = max(1, int(np.bincount(chirps.astype(int)).max()))
                c_ymin, c_ymax = 0, ym * 1.20

        # Clamping
        # Se a largura desejada for maior que o limite, centralizamos.
        if c_xmin is not None and c_xmax is not None:
            if (xmax - xmin) > (c_xmax - c_xmin):
                xmin, xmax = c_xmin, c_xmax
            else:
                if xmin < c_xmin:
                    xmax += (c_xmin - xmin)
                    xmin = c_xmin
                if xmax > c_xmax:
                    xmin -= (xmax - c_xmax)
                    xmax = c_xmax
                    
        if c_ymin is not None and c_ymax is not None:
            if (ymax - ymin) > (c_ymax - c_ymin):
                ymin, ymax = c_ymin, c_ymax
            else:
                if ymin < c_ymin:
                    ymax += (c_ymin - ymin)
                    ymin = c_ymin
                if ymax > c_ymax:
                    ymin -= (ymax - c_ymax)
                    ymax = c_ymax
                    
        return xmin, xmax, ymin, ymax

    def on_axes_leave(self, event):
        """Oculta o label de coordenadas quando o cursor sai do eixo."""
        for panel in self.all_panels:
            if hasattr(panel, "coord_label") and event.inaxes == panel.ax:
                panel.coord_label.setVisible(False)

    def on_motion(self, event):
        if self.panning and self.active_ax is not None and event.inaxes == self.active_ax:
            now_t = time.time()
            if now_t - getattr(self, "_last_pan_time", 0) < 0.018:
                return
            self._last_pan_time = now_t
            dx, dy = event.x - self.start_x, event.y - self.start_y
            x0, x1 = self.start_xlim
            y0, y1 = self.start_ylim
            bbox = self.active_ax.get_window_extent()
            if bbox.width == 0 or bbox.height == 0:
                return
            new_xmin = x0 - dx * (x1-x0) / bbox.width
            new_xmax = x1 - dx * (x1-x0) / bbox.width
            new_ymin = y0 - dy * (y1-y0) / bbox.height
            new_ymax = y1 - dy * (y1-y0) / bbox.height
            
            new_xmin, new_xmax, new_ymin, new_ymax = self._clamp_bounds(self.active_ax, new_xmin, new_xmax, new_ymin, new_ymax)
            
            time_axes = [self.panel_wave.ax, self.panel_spec.ax]
            if self.btn_sync.isChecked() and self.active_ax in time_axes:
                for panel in [self.panel_wave, self.panel_spec]:
                    panel.ax.set_xlim(new_xmin, new_xmax)
                    if panel.ax == self.active_ax:
                        if not (panel == self.panel_spec and getattr(self.panel_spec, "_y_locked", False)):
                            panel.ax.set_ylim(new_ymin, new_ymax)
                self._sync_render([self.panel_wave, self.panel_spec], new_xmin, new_xmax)
            else:
                self.active_ax.set_xlim(new_xmin, new_xmax)
                if not (self.active_ax == self.panel_spec.ax and getattr(self.panel_spec, "_y_locked", False)):
                    self.active_ax.set_ylim(new_ymin, new_ymax)
                mapping = {p.ax: p for p in self.all_panels}
                self._sync_render([mapping[self.active_ax]], new_xmin, new_xmax)

            if self.active_ax == self.panel_spec.ax and hasattr(self.panel_spec, "spin_spec_ymin"):
                if not getattr(self.panel_spec, "_y_locked", False):
                    self.panel_spec.spin_spec_ymin.blockSignals(True)
                    self.panel_spec.spin_spec_ymax.blockSignals(True)
                    self.panel_spec.spin_spec_ymin.setValue(max(self.panel_spec.spin_spec_ymin.minimum(), new_ymin))
                    self.panel_spec.spin_spec_ymax.setValue(min(self.panel_spec.spin_spec_ymax.maximum(), new_ymax))
                    self.panel_spec.spin_spec_ymin.blockSignals(False)
                    self.panel_spec.spin_spec_ymax.blockSignals(False)
            return

        # Tooltip de coordenadas em tempo real (Bloco 3.3)
        if not self.panning:
            for panel in self.all_panels:
                if hasattr(panel, "coord_label"):
                    if event.inaxes == panel.ax and event.xdata is not None and event.ydata is not None:
                        if panel == self.panel_spec:
                            unit = getattr(self.panel_spec, "spec_unit", "kHz")
                            f_val = event.ydata if unit == "kHz" else event.ydata / 1000.0
                            panel.coord_label.setText(f"[ t: {event.xdata:.3f} s | f: {f_val:.2f} kHz ]")
                        elif panel == self.panel_wave:
                            panel.coord_label.setText(f"[ t: {event.xdata:.3f} s | amp: {event.ydata:+.4f} ]")
                        elif panel == getattr(self, "panel_freq", None):
                            unit = getattr(self.panel_spec, "spec_unit", "kHz")
                            panel.coord_label.setText(f"[ f: {event.xdata:.2f} {unit} | pot: {event.ydata:.1f} dB ]")
                        elif panel == getattr(self, "panel_hist", None):
                            panel.coord_label.setText(f"[ pulsos: {int(event.xdata)} | contagem: {int(event.ydata)} ]")
                        else:
                            panel.coord_label.setText(f"[ x: {event.xdata:.3f} | y: {event.ydata:.3f} ]")
                        panel.coord_label.adjustSize()
                        panel.coord_label.setVisible(True)
                    else:
                        panel.coord_label.setVisible(False)

        # Hover interativo em cima dos marcadores de pulsos (X)
        if not self.panning and event.inaxes and event.xdata is not None and getattr(self, "pulse_hover_data", None):
            ax = event.inaxes
            target_panel = None
            is_wave = (ax == self.panel_wave.ax)
            is_freq = (ax == self.panel_freq.ax)
            is_spec = (ax == self.panel_spec.ax)

            if is_wave:
                target_panel = self.panel_wave
            elif is_freq:
                target_panel = self.panel_freq
            elif is_spec:
                target_panel = self.panel_spec

            if target_panel is not None:
                best_match = None
                min_pixel_dist = 20.0  # tolerância de 20 pixels para acionamento fácil do hover

                # Otimização crítica de performance: janela temporal em torno do cursor do mouse
                # Elimina o lag catastrófico gerado pela transformação de milhares de pontos no hover
                xlim = ax.get_xlim()
                bbox = ax.get_window_extent()
                px_per_sec = bbox.width / max(1e-6, (xlim[1] - xlim[0]))
                dt_max = max(0.04, 30.0 / max(1.0, px_per_sec))
                t_mouse = event.xdata

                unit = getattr(self.panel_spec, "spec_unit", "kHz")
                spec_scale = 1000.0 if unit == "kHz" else 1.0

                for item in self.pulse_hover_data:
                    if abs(item["time"] - t_mouse) > dt_max:
                        continue

                    # Determina coordenadas Y correspondentes ao eixo atual
                    if is_wave:
                        y_val = item["env_y"]
                    elif is_spec:
                        y_val = item["freq_y"] / spec_scale
                    else:
                        y_val = item["freq_y"]

                    try:
                        pt_disp = ax.transData.transform((item["time"], y_val))
                        dx_pix = abs(pt_disp[0] - event.x)
                        dy_pix = abs(pt_disp[1] - event.y)
                        dist_pix = np.hypot(dx_pix, dy_pix)

                        # Na onda acústica, também considera proximidade na linha de base y=0
                        if is_wave:
                            pt_zero = ax.transData.transform((item["time"], 0.0))
                            dist_zero = np.hypot(abs(pt_zero[0] - event.x), abs(pt_zero[1] - event.y))
                            dist_pix = min(dist_pix, dist_zero)

                        if dist_pix < min_pixel_dist:
                            min_pixel_dist = dist_pix
                            best_match = item
                    except Exception:
                        continue

                if best_match is not None:
                    if best_match.get("status") == "discarded":
                        t_val = best_match["time"]
                        f_val = best_match.get("freq_y", 0.0)
                        c_freq = best_match.get("carrier_freq", 0.0)
                        reason = best_match.get("reason", "Pulso descartado pelo filtro acústico")

                        freq_line = ""
                        if f_val > 0:
                            if c_freq > 0:
                                diff = f_val - c_freq
                                freq_line = f"<b>Frequência:</b> {f_val:.0f} Hz (Portadora: {c_freq:.0f} Hz | Desvio: {diff:+.0f} Hz)<br>"
                            else:
                                freq_line = f"<b>Frequência:</b> {f_val:.0f} Hz<br>"

                        msg = (
                            f"<div style='font-family: sans-serif; line-height: 1.35;'>"
                            f"<span style='color: #F87171; font-weight: 700;'>✖ Pulso Descartado</span><br>"
                            f"<b>Tempo:</b> {t_val:.3f} s<br>"
                            f"{freq_line}"
                            f"<b>Motivo:</b> <span style='color: #E2E8F0;'>{reason}</span>"
                            f"</div>"
                        )
                    else:
                        qnt = best_match["chirp_pulses"]
                        p_num = best_match["pulse_num"]
                        t_val = best_match["time"]
                        c_idx = best_match["chirp_idx"]
                        f_val = best_match.get("freq_y", 0.0)
                        freq_line = f"<br><b>Frequência:</b> {f_val:.0f} Hz" if f_val > 0 else ""
                        msg = (
                            f"<div style='font-family: sans-serif; line-height: 1.35;'>"
                            f"<b style='color: #38BDF8;'>Chilreio #{c_idx}: {qnt} pulsos</b><br>"
                            f"<b>Pulso:</b> {p_num} de {qnt}<br>"
                            f"<b>Tempo:</b> {t_val:.3f} s"
                            f"{freq_line}"
                            f"</div>"
                        )
                    QToolTip.showText(QCursor.pos(), msg, target_panel.canvas)
                    return
                else:
                    QToolTip.hideText()

    def zoom_graph(self, event):
        if not event.inaxes:
            return
        self.bg_cache_valid = False
        for line in self.cursor_lines:
            line.set_animated(False)
        base_scale = 1.2
        scale = 1/base_scale if event.button == 'up' else base_scale if event.button == 'down' else None
        if not scale or event.xdata is None or event.ydata is None:
            return
        ax = event.inaxes
        if ax is self.panel_hist.ax:
            return
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        new_xw = (xmax-xmin)*scale
        rel_x = (event.xdata-xmin)/(xmax-xmin)
        new_xmin = event.xdata-new_xw*rel_x
        new_xmax = event.xdata+new_xw*(1-rel_x)
        new_yw = (ymax-ymin)*scale
        rel_y = (event.ydata-ymin)/(ymax-ymin)
        new_ymin = event.ydata-new_yw*rel_y
        new_ymax = event.ydata+new_yw*(1-rel_y)
        
        new_xmin, new_xmax, new_ymin, new_ymax = self._clamp_bounds(ax, new_xmin, new_xmax, new_ymin, new_ymax)
        
        time_axes = [self.panel_wave.ax, self.panel_spec.ax]
        if self.btn_sync.isChecked() and ax in time_axes:
            for panel in [self.panel_wave, self.panel_spec]:
                panel.ax.set_xlim(new_xmin, new_xmax)
                if panel.ax == ax:
                    if not (panel == self.panel_spec and getattr(self.panel_spec, "_y_locked", False)):
                        panel.ax.set_ylim(new_ymin, new_ymax)
            self._sync_render([self.panel_wave, self.panel_spec], new_xmin, new_xmax)
        else:
            ax.set_xlim(new_xmin, new_xmax)
            if not (ax == self.panel_spec.ax and getattr(self.panel_spec, "_y_locked", False)):
                ax.set_ylim(new_ymin, new_ymax)
            mapping = {p.ax: p for p in self.all_panels}
            self._sync_render([mapping[ax]], new_xmin, new_xmax)

        if ax == self.panel_spec.ax and hasattr(self.panel_spec, "spin_spec_ymin"):
            if not getattr(self.panel_spec, "_y_locked", False):
                self.panel_spec.spin_spec_ymin.blockSignals(True)
                self.panel_spec.spin_spec_ymax.blockSignals(True)
                self.panel_spec.spin_spec_ymin.setValue(max(self.panel_spec.spin_spec_ymin.minimum(), new_ymin))
                self.panel_spec.spin_spec_ymax.setValue(min(self.panel_spec.spin_spec_ymax.maximum(), new_ymax))
                self.panel_spec.spin_spec_ymin.blockSignals(False)
                self.panel_spec.spin_spec_ymax.blockSignals(False)

