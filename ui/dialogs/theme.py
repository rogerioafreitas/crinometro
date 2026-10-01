MODERN_DIALOG_THEME = """
QPushButton#linkButton {
    background: transparent;
    border: none;
    color: #3B82F6;
    padding: 2px 8px;
}
QPushButton#linkButton:hover {
    text-decoration: underline;
    background: transparent;
}
QDialog {
    background-color: #18181B;
}

/* Protege os widgets internos contra o background global preto (#000000) do app */
QDialog QWidget {
    background-color: transparent;
}

QGroupBox {
    background-color: #1E1E24;
    border: 1px solid #27272A;
    border-radius: 6px;
    margin-top: 18px; 
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    color: #E4E4E7;
    font-weight: bold;
}

QLabel, QCheckBox {
    color: #E4E4E7;
}

QLabel#secondary {
    color: #A1A1AA;
}

QLineEdit, QSpinBox {
    background-color: #27272A;
    border: 1px solid #3F3F46;
    border-radius: 4px;
    padding: 6px 8px;
    color: #E4E4E7;
}

QComboBox {
    min-width: 140px;
    min-height: 28px;
    background-color: #27272A;
    border: 1px solid #3F3F46;
    border-radius: 4px;
    padding: 2px 28px 2px 8px;
    color: #F4F4F5;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjQTFBMUFBIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iNiA5IDEyIDE1IDE4IDkiPjwvcG9seWxpbmU+PC9zdmc+);
    width: 12px;
    height: 12px;
    margin-right: 8px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3B82F6;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #52525B;
    border-radius: 3px;
    background-color: #18181B;
}

QCheckBox::indicator:checked {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg==);
}

QRadioButton { 
    background: transparent; 
    color: #E4E4E7; 
    spacing: 8px; 
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #52525B;
    background: #18181B;
}

QRadioButton::indicator:checked {
    border: 1px solid #3B82F6;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.4, fx:0.5, fy:0.5, stop:0 #3B82F6, stop:1 #3B82F6);
}

QTableWidget {
    background-color: #18181B;
    alternate-background-color: #1E1E24;
    gridline-color: #27272A;
    border: 1px solid #3F3F46;
    color: #E4E4E7;
}

QTableWidget::item {
    padding: 6px;
}

QHeaderView::section {
    background-color: #1E1E24;
    color: #D4D4D8;
    border: none;
    border-right: 1px solid #27272A;
    border-bottom: 1px solid #27272A;
    padding: 4px;
    font-weight: bold;
}

QTableCornerButton::section {
    background-color: #1E1E24;
    border: 1px solid #27272A;
}

QTableWidget QLineEdit {
    background-color: #121214;
    color: #F4F4F5;
    border: 1px solid #3B82F6;
    border-radius: 0px;
    padding: 2px 4px;
    margin: 0px;
}

QPushButton {
    background-color: transparent;
    border: 1px solid #3F3F46;
    border-radius: 4px;
    color: #E4E4E7;
    padding: 8px 16px;
}

QPushButton:hover {
    background-color: #27272A;
}

QPushButton:disabled {
    color: #71717A;
    border: 1px solid #27272A;
}

QPushButton#primaryButton {
    background-color: #2563EB;
    border: none;
    color: #FFFFFF;
    font-weight: bold;
}

QPushButton#primaryButton:hover {
    background-color: #1D4ED8;
}

QTabWidget { background: transparent; }

QTabWidget {
    background: transparent;
}

QTabWidget::pane {
    border: 1px solid #27272A;
    background: transparent;
    top: -1px;
}

QTabBar::tab {
    background: #1E1E24;
    color: #A1A1AA;
    padding: 8px 16px;
    border: 1px solid #27272A;
    border-bottom: 1px solid #27272A;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #18181B;
    color: #E4E4E7;
    border-bottom: 2px solid #3B82F6;
}

QPushButton#primaryButton:disabled {
    background-color: #1E3A8A;
    color: #71717A;
}
"""