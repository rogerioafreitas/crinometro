"""
Crinômetro - Bioacústica para Grylloidea.
Fachada de compatibilidade retroativa para a arquitetura modular v4.0.x.

Este módulo re-exporta todas as classes, funções e constantes dos pacotes
'core', 'ui' e 'utils', permitindo que scripts legados ou chamadas diretas
como `import crinometro` continuem funcionando com total integridade.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.constants import APP_VERSION, CONFIG_FILE, DEFAULT_ALGO_PARAMS, CHANGELOG
from utils.i18n import I18N
from utils.helpers import setup_global_exception_handler, parse_version_tuple, is_version_newer
from utils.icons import APP_ICON_ICO_B64, get_app_icon, make_ui_icon, make_spinner_icon
from utils.styles import get_modern_stylesheet, DARK_STYLESHEET, LIGHT_STYLESHEET_OVERRIDES
from utils.report_generator import generate_pdf_report

from core.analyzer import CricketAnalyzer
from core.learner import PulseLearner
from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine
from core.worker import GenericWorker

from ui.panels import PlotPanel, TimelineWidget
from ui.widgets import ButtonSpinner, ThemeToggle, LoadingScreen, AudioListItemWidget
from ui.dialogs import (
    AlgoSettingsDialog,
    AdvancedAlgoSettingsDialog,
    GeneralSettingsDialog,
    ChangelogDialog,
    AboutDialog
)
from ui.main_window import MainWindow
from main import main

if __name__ == "__main__":
    raise SystemExit(main())
