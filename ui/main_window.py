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
from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine
from core.worker import GenericWorker

from ui.widgets import ButtonSpinner, ThemeToggle, LoadingScreen, AudioListItemWidget
from ui.panels import PlotPanel, TimelineWidget
from ui.dialogs import (
    AlgoSettingsDialog, AdvancedAlgoSettingsDialog, GeneralSettingsDialog,
    ChangelogDialog, AboutDialog
)

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
        self.use_machine_learning = True
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
        self.cursor_lines = []
        self.backgrounds = []
        self.bg_cache_valid = False
        self.panning = False
        self.active_ax = None
        self.expanded_panel = None
        self.spectro_engine = None
        self.line_engine = None
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

    def set_theme_mode(self, mode):
        mode = "light" if mode == "light" else "dark"
        if self.theme_mode == mode:
            return
        self.theme_mode = mode
        self.apply_modern_styles()
        for panel in getattr(self, "all_panels", []):
            panel.apply_dark_theme()
        if hasattr(self, "btn_collapse"):
            collapse_icon = "chevron_left" if not getattr(self, "_sidebar_collapsed", False) else "chevron_right"
            icon_col = "#E4E8EC" if self.theme_mode == "dark" else "#334155"
            self.btn_collapse.setIcon(make_ui_icon(collapse_icon, color=icon_col, size=18))
        if hasattr(self, "btn_play"):
            self._update_play_icon()
        if self.active_heavy_data:
            self._refresh_all_canvases()
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
        self.action_export = QAction(I18N[self.lang]["export"], self)
        self.action_export.triggered.connect(self.action_save_txt)
        self.file_menu.addAction(self.action_export)
        self.action_export_pdf = QAction("Exportar Relatório em PDF", self)
        self.action_export_pdf.setIcon(make_ui_icon("export", color="#2563EB", size=16))
        self.action_export_pdf.triggered.connect(self.action_save_pdf)
        self.file_menu.addAction(self.action_export_pdf)
        self.settings_menu = self.app_menu.addMenu(I18N[self.lang]["settings"])
        self.action_algo_config = QAction(I18N[self.lang]["algo_settings"], self)
        self.action_algo_config.triggered.connect(self.open_algo_settings)
        self.settings_menu.addAction(self.action_algo_config)
        self.action_report_config = QAction(I18N[self.lang]["gen_settings"], self)
        self.action_report_config.triggered.connect(self.open_report_settings)
        self.settings_menu.addAction(self.action_report_config)
        self.action_export_training = QAction(I18N[self.lang]["export_training"], self)
        self.action_export_training.triggered.connect(self.export_training_model)
        self.settings_menu.addAction(self.action_export_training)
        self.action_import_training = QAction(I18N[self.lang]["import_training"], self)
        self.action_import_training.triggered.connect(self.import_training_model)
        self.settings_menu.addAction(self.action_import_training)
        self.action_save_settings = QAction(I18N[self.lang]["save_settings"], self)
        self.action_save_settings.triggered.connect(self.save_settings)
        self.settings_menu.addAction(self.action_save_settings)
        self.action_reset_settings = QAction(I18N[self.lang]["reset_settings"], self)
        self.action_reset_settings.triggered.connect(self.reset_to_defaults)
        self.settings_menu.addAction(self.action_reset_settings)
        self.help_menu = self.app_menu.addMenu(I18N[self.lang]["help"])
        self.action_about = QAction(I18N[self.lang]["about"], self)
        self.action_about.triggered.connect(self.open_about)
        self.help_menu.addAction(self.action_about)

    def update_menu_text(self):
        l = self.lang
        self.file_menu.setTitle(I18N[l]["file"])
        self.action_load.setText(I18N[l]["load"])
        self.action_export.setText(I18N[l]["export"])
        if hasattr(self, "action_export_pdf"):
            self.action_export_pdf.setText("Exportar Relatório em PDF" if l == "pt" else "Export PDF Report")
        self.settings_menu.setTitle(I18N[l]["settings"])
        self.action_algo_config.setText(I18N[l]["algo_settings"])
        self.action_report_config.setText(I18N[l]["gen_settings"])
        self.action_export_training.setText(I18N[l]["export_training"])
        self.action_import_training.setText(I18N[l]["import_training"])
        self.action_save_settings.setText(I18N[l]["save_settings"])
        self.action_reset_settings.setText(I18N[l]["reset_settings"])
        self.help_menu.setTitle(I18N[l]["help"])
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

        self.btn_sync = QPushButton("Sincronizar (X)")
        self.btn_sync.setObjectName("btn_sync")
        self.btn_sync.setIcon(make_ui_icon("sync", color="#EAF4FB", size=18))
        self.btn_sync.setCheckable(True)
        self.btn_sync.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.toggled.connect(self.on_sync_toggled)
        self.btn_sync.setFixedHeight(36)
        self.btn_sync.setMinimumWidth(158)
        nav_l.addWidget(self.btn_sync)

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
        self.splitter.setChildrenCollapsible(True)
        root.addWidget(self.splitter, 1)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("sidebar")
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
        self.list_widget.itemSelectionChanged.connect(self.on_file_selected)
        left_layout.addWidget(self.list_widget, 1)

        self.btn_analyze_selected = QPushButton("⚡ Analisar Selecionados")
        self.btn_analyze_selected.setObjectName("summaryAction")
        self.btn_analyze_selected.setToolTip("Executar análise em todos os arquivos de áudio selecionados (marcados)")
        self.btn_analyze_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_selected.clicked.connect(self.analyze_selected_audios)
        left_layout.addWidget(self.btn_analyze_selected)

        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(14, 14, 14, 10)
        right_layout.setSpacing(10)

        # SUMMARY CARD
        self.summary_card = QFrame()
        self.summary_card.setObjectName("summaryCard")
        summary = QHBoxLayout(self.summary_card)
        summary.setContentsMargins(14, 12, 14, 12)
        summary.setSpacing(14)

        summary_info = QVBoxLayout()
        summary_info.setSpacing(3)
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
        summary_info.addWidget(self.lbl_summary_meta)
        summary.addLayout(summary_info, 1)

        actions = QHBoxLayout()
        actions.setSpacing(7)
        self.btn_reanalisar_main = QPushButton("Reanalisar")
        self.btn_reanalisar_main.setObjectName("summaryAction")
        self.btn_reanalisar_main.setIcon(make_ui_icon("reload", color="#FFFFFF", size=17))
        self.btn_reanalisar_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reanalisar_main.clicked.connect(self.force_reanalyze)
        self.btn_toggle_ml = QPushButton()
        self.btn_toggle_ml.setObjectName("summaryAction")
        self.btn_toggle_ml.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_ml.clicked.connect(self.toggle_machine_learning)
        self._update_ml_toggle_ui()
        self.btn_learn_corrections = QPushButton(I18N[self.lang]["learn_corrections"])
        self.btn_learn_corrections.setObjectName("summaryAction")
        self.btn_learn_corrections.setIcon(make_ui_icon("brain", color="#FFFFFF", size=17))
        self.btn_learn_corrections.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_learn_corrections.clicked.connect(self.learn_from_corrections)
        self.btn_export_main = QPushButton("Exportar Dados")
        self.btn_export_main.setObjectName("summaryAction")
        self.btn_export_main.setIcon(make_ui_icon("export", color="#FFFFFF", size=17))
        self.btn_export_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_main.clicked.connect(self.show_export_menu)
        actions.addWidget(self.btn_reanalisar_main)
        actions.addWidget(self.btn_toggle_ml)
        actions.addWidget(self.btn_learn_corrections)
        actions.addWidget(self.btn_export_main)
        summary.addLayout(actions)

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
        self.lbl_model_status = QLabel("🧠 Modelo: não treinado")
        self.lbl_model_status.setObjectName("metricSub")
        self.lbl_model_status.setStyleSheet("color: #F97316;")
        for _label in (self.lbl_metric_title, self.lbl_total, self.lbl_metric_sub, self.lbl_model_status):
            _label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            _label.setAutoFillBackground(False)
        metrics.addWidget(self.lbl_metric_title)
        metrics.addWidget(self.lbl_total)
        metrics.addWidget(self.lbl_metric_sub)
        metrics.addWidget(self.lbl_model_status)
        summary.addLayout(metrics)
        right_layout.addWidget(self.summary_card)

        # DASHBOARD: um painel grande + três empilhados
        self.dashboard_grid = QGridLayout()
        self.dashboard_grid.setContentsMargins(0, 0, 0, 0)
        self.dashboard_grid.setHorizontalSpacing(10)
        self.dashboard_grid.setVerticalSpacing(10)
        self.dashboard_grid.setColumnStretch(0, 3)
        self.dashboard_grid.setColumnStretch(1, 1)
        self.dashboard_grid.setRowStretch(0, 1)
        right_layout.addLayout(self.dashboard_grid, 1)

        self.main_host = QWidget()
        self.main_host_layout = QVBoxLayout(self.main_host)
        self.main_host_layout.setContentsMargins(0, 0, 0, 0)

        self.stack_host = QWidget()
        self.stack_layout = QVBoxLayout(self.stack_host)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(10)

        self.dashboard_grid.addWidget(self.main_host, 0, 0)
        self.dashboard_grid.addWidget(self.stack_host, 0, 1)

        self.panel_wave = PlotPanel("wave", self.lang, self.swap_main_panel)
        self.panel_hist = PlotPanel("hist", self.lang, self.swap_main_panel)
        self.panel_freq = PlotPanel("freq", self.lang, self.swap_main_panel)
        self.panel_spec = PlotPanel("spec", self.lang, self.swap_main_panel, main=True)
        self.all_panels = [self.panel_wave, self.panel_hist, self.panel_freq, self.panel_spec]
        self.main_panel = self.panel_spec
        self.stack_panels = [self.panel_hist, self.panel_wave, self.panel_freq]
        self._rebuild_panel_layout()

        for panel in self.all_panels:
            # O histograma é deliberadamente fixo: sem drag e sem zoom.
            if panel is self.panel_hist:
                continue
            panel.canvas.mpl_connect("scroll_event", self.zoom_graph)
            panel.canvas.mpl_connect("button_press_event", self.on_press)
            panel.canvas.mpl_connect("button_release_event", self.on_release)
            panel.canvas.mpl_connect("motion_notify_event", self.on_motion)

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

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([238, 1240])
        self.btn_collapse.setIcon(make_ui_icon("chevron_left", size=18))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        # slider legado mantido para compatibilidade com as rotinas existentes;
        # a interação visual principal ocorre na TimelineWidget.
        self.slider.setRange(0, 0)
        self.slider.setVisible(False)
        self._on_playback_state(self.player.playbackState())

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
        """Reposiciona os cards sem disparar renderizações intermediárias.
        Isso evita reentrância/lock quando a sincronização X está ativa."""
        while self.main_host_layout.count():
            item = self.main_host_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        while self.stack_layout.count():
            item = self.stack_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        self.main_host_layout.addWidget(self.main_panel)
        for panel in self.stack_panels:
            self.stack_layout.addWidget(panel, 1)
        self.main_panel.set_main(True)
        for panel in self.stack_panels:
            panel.set_main(False)

        self.main_host_layout.activate()
        self.stack_layout.activate()
        self.main_host.updateGeometry()
        self.stack_host.updateGeometry()

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

            old_main = self.main_panel
            old_stack = list(self.stack_panels)
            self.main_panel = panel
            self.stack_panels = [old_main] + [p for p in old_stack if p is not panel]
            self._rebuild_panel_layout()

            # Consolida a nova geometria sem permitir callbacks de sincronização
            # durante o reparenting. Em seguida, libera a guarda e faz um único draw.
            QApplication.processEvents()
            self._swapping_panels = False
            self._refresh_all_canvases()
        finally:
            self._swapping_panels = False

    def _fit_all_plots_to_layout(self):
        if not self.active_heavy_data:
            return
        d=self.active_heavy_data; duration=max(0.001,float(d.get("duration",0.0))); p=d.get("params",{})
        self.panel_wave.ax.set_xlim(0.0,duration); self.panel_wave.ax.set_ylim(-1.05,1.05)
        self.panel_freq.ax.set_xlim(0.0,duration)
        if len(d.get("t_spec",[])):
            self.panel_spec.ax.set_xlim(float(d["t_spec"][0]),float(d["t_spec"][-1]))
        if p: self.panel_spec.ax.set_ylim(float(p.get("b1_min",3200)),float(p.get("b1_max",6000)))
        if len(d.get("chirps",[])):
            vals=np.asarray(d["chirps"]); self.panel_hist.ax.set_xlim(float(vals.min())-0.65,float(vals.max())+0.65)
            ymax=max(1,int(np.bincount(vals.astype(int)).max()) if vals.size else 1); self.panel_hist.ax.set_ylim(0,ymax*1.20)

    def _apply_plot_geometry(self):
        """Enquadra os gráficos de forma adaptativa ao tamanho real de cada canvas.

        O ponto crítico é não usar a mesma margem para um card grande e um card
        estreito: nos painéis laterais isso reduz a área útil e corta ticks/labels.
        """
        if not hasattr(self, "all_panels"):
            return

        for panel in self.all_panels:
            fig = panel.figure
            fig.set_layout_engine(None)
            fig.set_constrained_layout(False)

            w = max(1, panel.canvas.width())
            h = max(1, panel.canvas.height())
            is_main = panel is self.main_panel

            # Margens relativas ao formato real do canvas.
            if panel is self.panel_hist:
                left, right = 0.19, 0.96
                top = 0.84
                bottom = 0.42
            elif is_main:
                left, right = 0.095, 0.975
                top = 0.935
                bottom = 0.145
            else:
                # Em cards laterais estreitos, prioriza espaço para eixo Y e X.
                left = 0.22 if w < 520 else 0.19
                right = 0.965
                top = 0.88
                bottom = 0.32 if h < 230 else 0.27

            fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom)
            panel.canvas.updateGeometry()

    def _refresh_all_canvases(self):
        if getattr(self, '_refreshing_canvases', False):
            return
        self._refreshing_canvases = True
        try:
            self.setUpdatesEnabled(False)
            self.main_host_layout.activate()
            self.stack_layout.activate()
            QApplication.processEvents()
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
        if sizes and sizes[0] <= 4:
            self.splitter.setSizes([238, max(700, self.width()-238)])
            self.btn_collapse.setIcon(make_ui_icon("chevron_left", size=18))
            self.btn_collapse.setToolTip("Ocultar painel de arquivos")
        else:
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
        item.setSizeHint(QSize(200, 36))

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
            results = {}
            for fname in checked_files:
                if fname not in self.loaded_files or not os.path.exists(self.loaded_files[fname]):
                    continue
                try:
                    fpath = self.loaded_files[fname]
                    res = CricketAnalyzer.analyze(fpath, effective_params, pulse_learner=self.pulse_learner)
                    results[fname] = res
                    success_count += 1
                except Exception as exc:
                    errors.append(f"{fname}: {exc}")
            return success_count, errors, results

        worker = GenericWorker(_task)
        self._batch_worker = worker

        def _on_finished(payload):
            for fname in checked_files:
                w = self._get_item_widget_by_name(fname)
                if w and hasattr(w, "set_loading"):
                    w.set_loading(False)

            success_count, errors, results = payload
            for fname, res in results.items():
                self._apply_analysis_results(fname, res, render=(fname == curr_name))

            if curr_name in self.analysis_cache:
                self.btn_reanalisar_main.setText("Reanalisar")
                self.btn_reanalisar_main.setIcon(make_ui_icon("reload", color="#FFFFFF", size=17))
                self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")

            if curr_name not in checked_files and checked_files and checked_files[0] in results:
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
            for fname in checked_files:
                w = self._get_item_widget_by_name(fname)
                if w and hasattr(w, "set_loading"):
                    w.set_loading(False)
            spinner.stop(None, "⚡ Analisar Selecionados")
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha na análise em lote:\n{err_msg}")

        worker.finished_signal.connect(_on_finished)
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
        files, _ = QFileDialog.getOpenFileNames(self, "Load Audio Files", "", "WAV Files (*.wav)")
        for file_path in files:
            filename = os.path.basename(file_path)
            self.loaded_files[filename] = file_path
            self._add_audio_file_item(filename, is_checked=False)
        if files:
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
            self.render_dashboard(filename)
        else:
            self.btn_reanalisar_main.setText("Analisar")
            self.btn_reanalisar_main.setIcon(make_ui_icon("play", color="#FFFFFF", size=15))
            self.btn_reanalisar_main.setToolTip("Executar análise deste áudio")
            self.active_filename = filename
            self._update_summary_ready_for_analysis(filename)

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

        # 2. Limpa histórico de edições e marcadores
        self._pulse_edit_history = []
        self.corrections_by_file = {}

        # 3. Zera o modelo de aprendizado ativo
        if hasattr(self, 'pulse_learner') and self.pulse_learner:
            self.pulse_learner.reset()

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

        # 6. Atualiza label de status do modelo se existir
        if hasattr(self, 'lbl_model_status'):
            self.lbl_model_status.setText("🧠 Modelo: não treinado")
            self.lbl_model_status.setStyleSheet("color: #F97316;")

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
                    self.corrections_by_file = {
                        str(name): [int(p) for p in peaks]
                        for name, peaks in corrections.items()
                        if isinstance(peaks, list)
                    }
                if "pulse_learner" in data:
                    self.pulse_learner.load_from_config()
                if "use_machine_learning" in data:
                    self.use_machine_learning = bool(data["use_machine_learning"])
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
            config["use_machine_learning"] = getattr(self, "use_machine_learning", True)
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
        """Ativa ou desativa a filtragem e classificação por Inteligência Artificial."""
        self.use_machine_learning = not getattr(self, "use_machine_learning", True)
        self.save_settings(silent=True)
        self._update_ml_toggle_ui()
        if self.active_filename and self.active_filename in self.loaded_files:
            self.force_reanalyze()

    def _update_ml_toggle_ui(self):
        if not hasattr(self, "btn_toggle_ml"):
            return
        is_active = getattr(self, "use_machine_learning", True)
        if is_active:
            self.btn_toggle_ml.setText("🧠 IA: Ativada")
            self.btn_toggle_ml.setToolTip("IA Ativada: filtra ruído e discrimina grilos distantes. Clique para desativar.")
            self.btn_toggle_ml.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 5px; padding: 6px 12px;")
            if hasattr(self, "lbl_model_status"):
                status_txt = "🧠 IA: Ativada (Modelo Supervisionado)" if self.pulse_learner.is_trained() else "🧠 IA: Ativada (GMM não-supervisionado)"
                self.lbl_model_status.setText(status_txt)
                self.lbl_model_status.setStyleSheet("color: #10B981;")
        else:
            self.btn_toggle_ml.setText("🧠 IA: Desativada")
            self.btn_toggle_ml.setToolTip("IA Desativada: análise executada estritamente por processamento de sinal (DSP). Clique para ativar.")
            self.btn_toggle_ml.setStyleSheet("background-color: #475569; color: #E2E8F0; font-weight: bold; border-radius: 5px; padding: 6px 12px;")
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
        loading_text = "Analisando..." if is_first_time else "Reanalisando..."
        spinner = ButtonSpinner(self.btn_reanalisar_main, loading_text)
        spinner.start()

        item_widget = self._get_item_widget_by_name(filename)
        if item_widget and hasattr(item_widget, "set_loading"):
            item_widget.set_loading(True)

        def _task():
            # 1. Se o usuário fez correções no arquivo atual, atualizamos o modelo
            if self.active_heavy_data and self.peaks_user_verified:
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
            res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner)
            return res

        worker = GenericWorker(_task)
        self._reanalyze_worker = worker

        def _on_finished(results):
            if item_widget and hasattr(item_widget, "set_loading"):
                item_widget.set_loading(False)
            spinner.stop(make_ui_icon("reload", color="#FFFFFF", size=17), "Reanalisar")
            self.btn_reanalisar_main.setToolTip("Reanalisar este áudio com os parâmetros atuais")
            self._apply_analysis_results(filename, results, render=True, validate_all=True)

        def _on_error(err_msg):
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
            learner = self.pulse_learner if getattr(self, "use_machine_learning", True) else None
            res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner)
            self._apply_analysis_results(filename, res, render=render, validate_all=validate_all, params=params)
        except Exception as e:
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha no arquivo {filename}:\n{str(e)}")

    def _apply_analysis_results(self, filename, results, render=True, validate_all=False, params=None):
        if params is None:
            params = self.algo_params.copy()
        rate, data, data_b1, env, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration = results[:14]
        distant_peaks = results[14] if len(results) > 14 else []
        self.peaks_detected = [int(p) for p in np.asarray(peaks, dtype=int)]
        self.active_filename = filename

        stored_corrections = self.corrections_by_file.get(filename)
        effective_params = {**params, **self._adaptive_overrides}
        if validate_all and (stored_corrections is not None or self.peaks_user_verified):
            working_set = stored_corrections if stored_corrections is not None else self.peaks_user_verified
            self.peaks_detected = list(sorted(set(working_set)))
            self.peaks_user_verified = list(self.peaks_detected)
            self.corrections_by_file[filename] = list(self.peaks_user_verified)
            if len(self.peaks_detected) >= 2:
                try:
                    chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
                        self.peaks_detected, effective_params, rate, env, raw_signal=data_b1
                    )
                except Exception:
                    pass
        elif stored_corrections is not None:
            self.peaks_user_verified = list(stored_corrections)
            peaks_added = sorted(set(stored_corrections) - set(self.peaks_detected))
            peaks_removed = sorted(set(self.peaks_detected) - set(stored_corrections))
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
            "chirp_peaks_list": chirp_peaks_list, "media": media, "moda": moda,
            "f_spec": f_spec, "t_spec": t_spec, "Sxx_db": Sxx_db, "dom_freqs": dom_freqs,
            "duration": audio_duration, "params": params.copy(),
            "peaks_detected": list(self.peaks_detected),
            "peaks_user_verified": list(self.peaks_user_verified),
            "distant_peaks": list(distant_peaks),
        }
        self.analysis_cache[filename] = heavy_data
        self.active_heavy_data = heavy_data
        self.active_filename = filename
        if render:
            self.render_dashboard(filename)



    def render_dashboard(self, filename):
        # Limpa referências a linhas de alinhamento do clique em eixos que serão
        # destruídos/recriados nesta renderização. Mantê-las causaria RuntimeError
        # ao chamar line.remove() na próxima chamada de _align_click_marker().
        self._click_alignment_lines = []
        d = self.active_heavy_data
        p = d["params"]
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
        p_txt = f"[Pulsos: {p['min_p']}-{p['max_p']} | Amp: {p['amp_min']}-{p['amp_max']} | Freq: {p['b1_min']}-{p['b1_max']}Hz]"
        self.lbl_summary_meta.setText(f"Duração: {d['duration']:.2f} seconds   |   Parâmetros: {p_txt}")
        self.lbl_total.setText(str(len(chirps)))
        self.lbl_metric_sub.setText(f"Moda: {d['moda']}   |   Média: {d['media']:.2f}")
        model_status_text = "🧠 Modelo: ✓ treinado" if self.pulse_learner.is_trained() else "🧠 Modelo: não treinado"
        model_status_color = "#10B981" if self.pulse_learner.is_trained() else "#F97316"
        self.lbl_model_status.setText(model_status_text)
        self.lbl_model_status.setStyleSheet(f"color: {model_status_color};")

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
        for qnt, pks in sorted(picos_por_contagem.items()):
            pks_t = np.array(pks) / rate
            ax1.plot(pks_t, env[pks], 'x', color=marker_colors.get(int(qnt), extra_pulse_color), markersize=7, markeredgewidth=1.7, zorder=7)
        distant_pks = d.get("distant_peaks", [])
        if distant_pks:
            valid_d = [dp for dp in distant_pks if 0 <= dp < len(env)]
            if valid_d:
                ax1.plot(np.array(valid_d) / rate, env[valid_d], 'x', color='#64748B', markersize=5.5, markeredgewidth=1.1, alpha=0.55, zorder=5)

        self._refresh_user_peak_markers()
        ax1.set_xlabel("seconds")
        ax1.set_ylabel("Amplitude")
        ax1.set_ylim(-1.05, 1.05)

        # HIST — fixo, sem drag/zoom, com índice de cores/pulsos no rodapé
        ax2 = self.panel_hist.ax
        ax2.clear()
        unique_pulses, counts = np.unique(chirps, return_counts=True)
        hist_palette = pulse_colors
        bars = ax2.bar(
            unique_pulses, counts,
            color=[hist_palette.get(int(x), extra_pulse_color) for x in unique_pulses],
            edgecolor='none', linewidth=0, width=0.68, zorder=3
        )
        ax2.grid(axis='y', color='#292D32' if self.theme_mode == 'dark' else '#DDE2E7', linewidth=0.6, alpha=0.8, zorder=0)
        max_count = int(max(counts)) if len(counts) else 1
        for bar in bars:
            ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max_count*0.025, str(int(bar.get_height())),
                     ha='center', va='bottom', color='#DDE1E5' if self.theme_mode == 'dark' else '#4E5660', fontsize=8.5)
        ax2.set_xticks(unique_pulses)
        ax2.set_xlabel("")
        ax2.set_ylabel("")
        ax2.tick_params(axis='x', labelsize=8.5, colors='#A9ADB5' if self.theme_mode == 'dark' else '#59616B', length=0)
        ax2.tick_params(axis='y', labelsize=8, colors='#A9ADB5' if self.theme_mode == 'dark' else '#59616B')
        ax2.set_ylim(0, max_count * 1.20)
        ax2.figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.30)
        legend_handles = [Patch(facecolor=hist_palette.get(int(x), extra_pulse_color), edgecolor='none', label=f'{int(x)} pulsos')
                          for x in unique_pulses]
        if legend_handles:
            leg = ax2.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.16),
                             ncol=min(4, len(legend_handles)), frameon=False, fontsize=9.5, handlelength=1.2,
                             columnspacing=0.9, borderaxespad=0.0)
            leg.get_frame().set_facecolor((0, 0, 0, 0))
            leg.get_frame().set_alpha(0.0)
            leg.get_frame().set_edgecolor((0, 0, 0, 0))
            leg.get_frame().set_linewidth(0)
            for text in leg.get_texts():
                text.set_color('#A9ADB5' if self.theme_mode == 'dark' else '#59616B')

        # FREQ
        ax3 = self.panel_freq.ax
        ax3.clear()
        ax3.scatter(t_spec, dom_freqs, c=dom_freqs, cmap='plasma', s=7, alpha=0.72, edgecolors='none')
        ax3.set_ylabel("Hz")
        ax3.set_xlabel("seconds")
        for qnt, pks in sorted(picos_por_contagem.items()):
            pks_t = np.array(pks) / rate
            freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
            ax3.plot(pks_t, freqs_at_pks, 'x', color=marker_colors.get(int(qnt), '#5F9ED1'), markersize=6, markeredgewidth=1.4, zorder=7)

        # SPEC
        ax4 = self.panel_spec.ax
        ax4.clear()
        ax4.set_ylabel("Hz")
        ax4.set_xlabel("seconds")
        ax4.set_xlim(t_spec[0], t_spec[-1])
        ax4.set_ylim(p['b1_min'], p['b1_max'])
        self.spectro_engine = HighPerfSpectrogramEngine(ax4, Sxx_db, t_spec, f_spec, update_bg_callback=self.capture_backgrounds)
        self.spectro_engine.render_high_detail()
        for qnt, pks in sorted(picos_por_contagem.items()):
            pks_t = np.array(pks) / rate
            freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
            ax4.plot(pks_t, freqs_at_pks, 'x', color=marker_colors.get(int(qnt), '#5F9ED1'), markersize=7, markeredgewidth=1.5, zorder=7)
        if distant_pks:
            valid_d = [dp for dp in distant_pks if 0 <= dp < len(env)]
            if valid_d:
                d_times = np.array(valid_d) / rate
                d_freqs = np.interp(d_times, t_spec, dom_freqs)
                ax4.plot(d_times, d_freqs, 'x', color='#94A3B8', markersize=5, markeredgewidth=1.0, alpha=0.5, zorder=5)

        # Atualiza mapa de eixos independente da posição atual.
        self.cursor_lines = []
        for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
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
        self._update_pulse_hover_data()
        self.capture_backgrounds()

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

        for c_idx, cp in enumerate(chirp_peaks_list):
            qnt = len(cp)
            for p_idx, pk in enumerate(cp):
                pk = int(pk)
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
                })

    def _update_summary_placeholder(self, filename=""):
        self.lbl_summary_file.setText(filename or "Nenhum arquivo selecionado")
        self.lbl_summary_meta.setText("Carregue um arquivo WAV para iniciar a análise")
        self.lbl_total.setText("—")
        self.lbl_metric_sub.setText("Moda: —   |   Média: —")
        if hasattr(self, 'lbl_elapsed'):
            self.lbl_elapsed.setText("00:00.00 / 00:00.00")
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
        menu = QMenu(self)
        menu.setObjectName("exportMenu")
        act_pdf = menu.addAction(make_ui_icon("export", color="#2563EB", size=15), "📄 Exportar Relatório Completo (.pdf)")
        act_pdf.triggered.connect(self.action_save_pdf)
        act_txt = menu.addAction(make_ui_icon("export", color="#64748B", size=15), "📝 Exportar Relatório em Texto (.txt)")
        act_txt.triggered.connect(self.action_save_txt)
        menu.exec(self.btn_export_main.mapToGlobal(self.btn_export_main.rect().bottomLeft()))

    def action_save_pdf(self):
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
        default_name = f"Relatorio_Crinometro_{now.strftime('%Y%m%d_%H%M')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Relatório em PDF", default_name, "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            from utils.report_generator import generate_pdf_report
            generate_pdf_report(file_path, self.report_params, selected_cache, self.algo_params)
            QMessageBox.information(
                self,
                I18N[self.lang]["success"],
                f"Relatório PDF gerado com sucesso para {len(selected_cache)} áudio(s) selecionado(s)!\n\nSalvo em:\n{file_path}"
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
            active_panels = [self.panel_wave, self.panel_freq, self.panel_spec]
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

        if not self.active_heavy_data or not self.peaks_user_verified:
            return

        rate = float(self.active_heavy_data.get('rate', 1.0))
        t_spec = self.active_heavy_data.get('t_spec', [])
        dom_freqs = self.active_heavy_data.get('dom_freqs', [])
        
        peaks_detected_set = set(int(p) for p in self.peaks_detected)
        peaks_verified_set = set(int(p) for p in self.peaks_user_verified)

        peaks_confirmed = sorted(peaks_verified_set & peaks_detected_set)
        peaks_added = sorted(peaks_verified_set - peaks_detected_set)
        peaks_removed = sorted(peaks_detected_set - peaks_verified_set)

        # Renderiza na onda acústica (ax1)
        ax1 = self.panel_wave.ax
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

        # Renderiza no espectrograma (ax4) e gráfico de frequência (ax3) se dados disponíveis
        if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
            ax3 = self.panel_freq.ax
            ax4 = self.panel_spec.ax
            
            for peaks, color, marker in [
                (peaks_confirmed, '#10B981', 'o'),
                (peaks_added, '#3B82F6', '^'),
                (peaks_removed, '#EF4444', 'x'),
            ]:
                if peaks:
                    pks_t = np.asarray(peaks, dtype=float) / rate
                    freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
                    
                    # Frequência
                    line_freq = ax3.plot(pks_t, freqs_at_pks, marker=marker, linestyle='none',
                                        color=color, markersize=8, markeredgewidth=1.2, zorder=4)
                    self._wave_user_markers.extend(line_freq)
                    
                    # Espectrograma
                    line_spec = ax4.plot(pks_t, freqs_at_pks, marker=marker, linestyle='none',
                                        color=color, markersize=8, markeredgewidth=1.2, zorder=4)
                    self._wave_user_markers.extend(line_spec)

        self._update_pulse_hover_data()
        # Redesenha todos os painéis
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

    def _toggle_peak_marker(self, time_sec, panel=None, event=None):
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

        if nearest is not None and nearest in self.peaks_user_verified:
            self.peaks_user_verified = [int(p) for p in self.peaks_user_verified if int(p) != nearest]
        elif nearest is not None:
            # Clicar no X vermelho desfaz a desclassificação e restaura a bolinha verde.
            self.peaks_user_verified = sorted(set(self.peaks_user_verified + [nearest]))
        else:
            self.peaks_user_verified = sorted(set(self.peaks_user_verified + [target]))
        self.active_heavy_data['peaks_user_verified'] = list(self.peaks_user_verified)
        if self.active_filename:
            self.corrections_by_file[self.active_filename] = list(self.peaks_user_verified)
            self._save_corrections_state()

        for panel in self.all_panels:
            if hasattr(panel, "btn_pulse_undo"):
                panel.btn_pulse_undo.setEnabled(True)

        # Recalcula chilreios e métricas imediatamente após a alteração do usuário de forma ultra rápida
        if self.peaks_user_verified and len(self.peaks_user_verified) >= 2:
            try:
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
            self.corrections_by_file[self.active_filename] = list(self.peaks_user_verified)
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

        if detected_set == verified_set:
            QMessageBox.information(self, "Sem mudanças", "Nenhuma correção manual foi feita no arquivo atual.")
            return

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
                model_status_text = "🧠 Modelo: ✓ treinado" if self.pulse_learner.is_trained() else "🧠 Modelo: não treinado"
                model_status_color = "#10B981" if self.pulse_learner.is_trained() else "#F97316"
                self.lbl_model_status.setText(model_status_text)
                self.lbl_model_status.setStyleSheet(f"color: {model_status_color};")
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

    # ---------- maximização / pan / zoom ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_cache_valid = False
        if hasattr(self, "all_panels") and self.active_heavy_data and not getattr(self, "_resize_refresh_pending", False) and not getattr(self, "_swapping_panels", False) and not getattr(self, "_refreshing_canvases", False):
            self._resize_refresh_pending = True
            QTimer.singleShot(0, self._finish_resize_refresh)

    def _finish_resize_refresh(self):
        self._resize_refresh_pending=False
        if self.active_heavy_data: self._refresh_all_canvases()

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
        active_panels = [self.panel_wave, self.panel_freq, self.panel_spec]
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
        if event.xdata is not None:
            self._align_click_marker(float(event.xdata))
        
        # Determina qual painel foi clicado
        clicked_panel = None
        for panel in self.all_panels:
            if event.inaxes == panel.ax:
                clicked_panel = panel
                break

        # Se modo de edição está ativo e clicou em um painel que suporta edição
        if clicked_panel and getattr(clicked_panel, 'pulse_edit_mode', False) and event.xdata is not None:
            # Converte coordenada X (tempo) para amostras
            if self.active_heavy_data:
                rate = float(self.active_heavy_data.get('rate', 1.0))
                time_sec = float(event.xdata)
                self._toggle_peak_marker(time_sec, panel=clicked_panel, event=event)
                return

        # Comportamento normal de pan/zoom quando não em modo de edição
        if clicked_panel and clicked_panel != self.panel_hist and event.button == 1:
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
        if event.button == 1:
            self.panning, self.active_ax = False, None
            for panel in self.all_panels:
                panel.canvas.draw_idle()
            QTimer.singleShot(150, self.capture_backgrounds)

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

        axes = [self.panel_wave.ax, self.panel_freq.ax, self.panel_spec.ax]
        for ax in axes:
            ax.set_xlim(0.0, duration)
        self.panel_wave.ax.set_ylim(-1.05, 1.05)
        p = self.active_heavy_data.get("params", {})
        if p:
            self.panel_spec.ax.set_ylim(p.get("b1_min", 3200), p.get("b1_max", 6000))

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
        self.panel_freq.ax.set_xlim(0.0, duration)
        self.panel_spec.ax.set_xlim(float(self.active_heavy_data["t_spec"][0]) if len(self.active_heavy_data.get("t_spec", [])) else 0.0, float(self.active_heavy_data["t_spec"][-1]) if len(self.active_heavy_data.get("t_spec", [])) else duration)
        self.panel_wave.ax.set_ylim(-1.05, 1.05)
        if p:
            self.panel_spec.ax.set_ylim(float(p.get("b1_min", 3200)), float(p.get("b1_max", 6000)))

        if self.spectro_engine:
            self.spectro_engine.render_high_detail()
        if self.line_engine:
            self.line_engine.render_high_detail()
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
        if current_time - self.sync_throttle_time < 0.042:
            return
        for panel in target_panels:
            ymin, ymax = panel.ax.get_ylim()
            if self.spectro_engine and panel == self.panel_spec:
                self.spectro_engine.render_interactive(xmin, xmax, ymin, ymax, is_sync=True)
            elif self.line_engine and panel == self.panel_wave:
                self.line_engine.render_interactive(xmin, xmax, is_sync=True)
            else:
                panel.canvas.draw_idle()
        self.sync_throttle_time = current_time

    def on_motion(self, event):
        if self.panning and self.active_ax is not None and event.inaxes == self.active_ax:
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
            time_axes = [self.panel_wave.ax, self.panel_freq.ax, self.panel_spec.ax]
            if self.btn_sync.isChecked() and self.active_ax in time_axes:
                for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
                    panel.ax.set_xlim(new_xmin, new_xmax)
                    if panel.ax == self.active_ax:
                        panel.ax.set_ylim(new_ymin, new_ymax)
                self._sync_render([self.panel_wave, self.panel_freq, self.panel_spec], new_xmin, new_xmax)
            else:
                self.active_ax.set_xlim(new_xmin, new_xmax)
                self.active_ax.set_ylim(new_ymin, new_ymax)
                mapping = {p.ax: p for p in self.all_panels}
                self._sync_render([mapping[self.active_ax]], new_xmin, new_xmax)
            return

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

                for item in self.pulse_hover_data:
                    # Determina coordenadas Y correspondentes ao eixo atual
                    if is_wave:
                        y_val = item["env_y"]
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
                    qnt = best_match["chirp_pulses"]
                    p_num = best_match["pulse_num"]
                    t_val = best_match["time"]
                    c_idx = best_match["chirp_idx"]
                    msg = (
                        f"<b>Chilreio #{c_idx}: {qnt} pulsos</b><br>"
                        f"Pulso: {p_num} de {qnt}<br>"
                        f"Tempo: {t_val:.3f} s"
                    )
                    QToolTip.showText(QCursor.pos(), msg, target_panel.canvas)
                    return
                else:
                    QToolTip.hideText()

    def zoom_graph(self, event):
        if not event.inaxes or QApplication.keyboardModifiers() != Qt.KeyboardModifier.ControlModifier:
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
        time_axes = [self.panel_wave.ax, self.panel_freq.ax, self.panel_spec.ax]
        if self.btn_sync.isChecked() and ax in time_axes:
            for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
                panel.ax.set_xlim(new_xmin, new_xmax)
                if panel.ax == ax:
                    panel.ax.set_ylim(new_ymin, new_ymax)
            self._sync_render([self.panel_wave, self.panel_freq, self.panel_spec], new_xmin, new_xmax)
        else:
            ax.set_xlim(new_xmin, new_xmax)
            ax.set_ylim(new_ymin, new_ymax)
            mapping = {p.ax: p for p in self.all_panels}
            self._sync_render([mapping[ax]], new_xmin, new_xmax)

