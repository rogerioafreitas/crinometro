MODERN_DIALOG_THEME = """
QDialog {
    background-color: #18181B;
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

QLabel, QCheckBox, QRadioButton {
    color: #E4E4E7;
}

QLabel#secondary {
    color: #A1A1AA;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #27272A;
    border: 1px solid #3F3F46;
    border-radius: 4px;
    padding: 6px 8px;
    color: #E4E4E7;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3B82F6;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #52525B;
    border-radius: 3px;
    background-color: #18181B;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
}

/* Add a visual checkmark (basic trick) or just rely on OS if not using images, 
but since it's colored blue, it looks checked */

QTableWidget {
    background-color: #18181B;
    alternate-background-color: #1E1E24;
    gridline-color: #27272A;
    border: 1px solid #3F3F46;
    color: #E4E4E7;
}

QHeaderView::section {
    background-color: #27272A;
    color: #A1A1AA;
    border: none;
    border-right: 1px solid #3F3F46;
    border-bottom: 1px solid #3F3F46;
    padding: 4px;
    font-weight: bold;
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

QTabWidget::pane {
    border: 1px solid #27272A;
    background: #18181B;
    border-radius: 4px;
}

QTabBar::tab {
    background: #1E1E24;
    color: #A1A1AA;
    padding: 8px 16px;
    border: 1px solid #27272A;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #18181B;
    color: #E4E4E7;
    border-bottom: 2px solid #3B82F6; /* Accent highlight on selected tab */
}
"""
