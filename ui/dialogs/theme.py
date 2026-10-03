import os
import tempfile

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap


def _icon_path(kind: str, color: str) -> str:
    """Gera (e reutiliza) um PNG 48x48 transparente para uso em QSS via url()."""
    folder = os.path.join(tempfile.gettempdir(), "crinometro_qss_icons")
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, f"{kind}_{color.lstrip('#').lower()}.png")
    if os.path.exists(out):
        return out.replace("\\", "/")

    size = 48
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(6.0 if kind == "check" else 5.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    if kind == "check":
        pts = [QPointF(11, 25), QPointF(21, 35), QPointF(38, 14)]
    else:  # chevron
        pts = [QPointF(11, 18), QPointF(24, 31), QPointF(37, 18)]
    p.drawPolyline(pts)
    p.end()
    pix.save(out, "PNG")
    return out.replace("\\", "/")


def get_dialog_theme(is_dark: bool) -> str:
    """Retorna o QSS moderno ajustado para Dark ou Light theme."""
    
    # Cores baseadas no modo
    bg_base = "#18181B" if is_dark else "#F8FAFC"
    bg_surface = "#1E1E24" if is_dark else "#FFFFFF"
    bg_input = "#27272A" if is_dark else "#F1F5F9"
    border_main = "#27272A" if is_dark else "#E2E8F0"
    border_input = "#3F3F46" if is_dark else "#CBD5E1"
    border_checkbox = "#52525B" if is_dark else "#94A3B8"
    
    text_primary = "#E4E4E7" if is_dark else "#1E293B"
    text_secondary = "#A1A1AA" if is_dark else "#64748B"
    text_disabled = "#71717A" if is_dark else "#94A3B8"
    
    accent = "#3B82F6"
    accent_hover = "#1D4ED8"
    accent_disabled = "#1E3A8A" if is_dark else "#BFDBFE"
    text_on_accent = "#FFFFFF"
    
    # Qt NAO le imagens data: em QSS -> gera PNGs em disco (cache por cor)
    combo_arrow = _icon_path("chevron", "#A1A1AA" if is_dark else "#64748B")
    check_icon = _icon_path("check", "#FFFFFF")
    popup_hover = "#2F2F37" if is_dark else "#E2E8F0"

    return f"""
QPushButton#linkButton {{
    background: transparent;
    border: none;
    color: {accent};
    padding: 2px 8px;
}}
QPushButton#linkButton:hover {{
    text-decoration: underline;
    background: transparent;
}}
QDialog {{
    background-color: {bg_base};
}}

/* Protege os widgets internos contra o background global preto do app */
QDialog QWidget {{
    background-color: transparent;
}}

QGroupBox {{
    background-color: {bg_surface};
    border: 1px solid {border_main};
    border-radius: 6px;
    margin-top: 18px; 
    padding-top: 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    color: {text_primary};
    font-weight: bold;
}}

QLabel, QCheckBox {{
    color: {text_primary};
}}

QLabel#secondary {{
    color: {text_secondary};
}}

QLineEdit, QSpinBox {{
    background-color: {bg_input};
    border: 1px solid {border_input};
    border-radius: 4px;
    padding: 6px 8px;
    color: {text_primary};
}}

QComboBox {{
    min-width: 140px;
    min-height: 28px;
    background-color: {bg_input};
    border: 1px solid {border_input};
    border-radius: 4px;
    padding: 2px 28px 2px 8px;
    color: {text_primary};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: url({combo_arrow});
    width: 12px;
    height: 12px;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {bg_surface};
    color: {text_primary};
    border: 1px solid {border_input};
    border-radius: 4px;
    padding: 4px;
    outline: 0;
    selection-background-color: {accent};
    selection-color: {text_on_accent};
}}

QComboBox QAbstractItemView::item {{
    min-height: 26px;
    padding: 2px 8px;
    border-radius: 3px;
    background-color: transparent;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {popup_hover};
    color: {text_primary};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {accent};
    color: {text_on_accent};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {border_checkbox};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {accent};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_checkbox};
    border-radius: 3px;
    background-color: {bg_base};
}}

QCheckBox::indicator:checked {{
    background-color: {accent};
    border: 1px solid {accent};
    image: url({check_icon});
}}

QRadioButton {{ 
    background: transparent; 
    color: {text_primary}; 
    spacing: 8px; 
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid {border_checkbox};
    background: {bg_base};
}}

QRadioButton::indicator:checked {{
    border: 1px solid {accent};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.4, fx:0.5, fy:0.5, stop:0 {accent}, stop:1 {accent});
}}

QTableWidget {{
    background-color: {bg_base};
    alternate-background-color: {bg_surface};
    gridline-color: {border_main};
    border: 1px solid {border_input};
    color: {text_primary};
}}

QTableWidget::item {{
    padding: 6px;
}}

QHeaderView::section {{
    background-color: {bg_surface};
    color: {text_primary};
    border: none;
    border-right: 1px solid {border_main};
    border-bottom: 1px solid {border_main};
    padding: 4px;
    font-weight: bold;
}}

QTableCornerButton::section {{
    background-color: {bg_surface};
    border: 1px solid {border_main};
}}

QTableWidget QLineEdit {{
    background-color: {bg_input};
    color: {text_primary};
    border: 1px solid {accent};
    border-radius: 0px;
    padding: 2px 4px;
    margin: 0px;
}}

QPushButton {{
    background-color: transparent;
    border: 1px solid {border_input};
    border-radius: 4px;
    color: {text_primary};
    padding: 8px 16px;
}}

QPushButton:hover {{
    background-color: {bg_input};
}}

QPushButton:disabled {{
    color: {text_disabled};
    border: 1px solid {border_main};
}}

QPushButton#primaryButton {{
    background-color: {accent};
    border: none;
    color: {text_on_accent};
    font-weight: bold;
}}

QPushButton#primaryButton:hover {{
    background-color: {accent_hover};
}}

QTabWidget {{ background: transparent; }}

QTabWidget {{
    background: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {border_main};
    background: transparent;
    top: -1px;
}}

QTabBar::tab {{
    background: {bg_surface};
    color: {text_secondary};
    padding: 8px 16px;
    border: 1px solid {border_main};
    border-bottom: 1px solid {border_main};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background: {bg_base};
    color: {text_primary};
    border-bottom: 2px solid {accent};
}}

QPushButton#primaryButton:disabled {{
    background-color: {accent_disabled};
    color: {text_disabled};
}}
"""