"""
Pacote de Recursos e Utilitários do Crinômetro.
"""
from utils.constants import APP_VERSION, CONFIG_FILE, DEFAULT_ALGO_PARAMS, CHANGELOG
from utils.i18n import I18N
from utils.helpers import setup_global_exception_handler, parse_version_tuple, is_version_newer
from utils.icons import APP_ICON_ICO_B64, get_app_icon, make_ui_icon, make_spinner_icon
from utils.styles import get_modern_stylesheet, DARK_STYLESHEET, LIGHT_STYLESHEET_OVERRIDES
from utils.report_generator import generate_pdf_report, NumberedCanvas, analyze_rhythmic_cadence
