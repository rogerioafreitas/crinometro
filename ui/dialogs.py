"""
Crinômetro - Janelas de Diálogo e Preferências.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QDialogButtonBox, QTextBrowser, QSizePolicy, QWidget,
    QLineEdit
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

from utils.constants import APP_VERSION, DEFAULT_ALGO_PARAMS, CHANGELOG
from utils.i18n import I18N
from utils.icons import get_app_icon
from core.updater import UpdateCheckerThread
from ui.update_dialog import UpdateDialog


class AlgoSettingsDialog(QDialog):
    def __init__(self, current_params, lang, parent=None):
        super().__init__(parent)
        self.setWindowTitle(I18N[lang]["algo_settings"])
        self.setMinimumWidth(430)
        self.lang = lang
        self.apply_styles()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form = QFormLayout()
        form.setSpacing(12)
        
        self.inputs = {}
        fields = [
            ("min_p", "Mín. Pulsos/Chilr.:" if lang == "pt" else "Min Pulses/Chirp:", QSpinBox, 1, 50, 1),
            ("max_p", "Máx. Pulsos/Chilr.:" if lang == "pt" else "Max Pulses/Chirp:", QSpinBox, 1, 100, 1),
            ("amp_min", "Altura mínima do pico:" if lang == "pt" else "Min Peak Height:", QDoubleSpinBox, 0.01, 2.00, 0.01),
            ("gap_min", "Distância mínima entre picos (ms):" if lang == "pt" else "Min Peak Distance (ms):", QDoubleSpinBox, 1.0, 500.0, 1.0),
        ]
        for key, label, WidgetClass, vmin, vmax, step in fields:
            widget = WidgetClass()
            widget.setRange(vmin, vmax)
            widget.setSingleStep(step)
            val = current_params.get(key, DEFAULT_ALGO_PARAMS.get(key, vmin))
            if WidgetClass == QSpinBox:
                widget.setValue(int(round(float(val))))
            else:
                widget.setValue(float(val))
            self.inputs[key] = widget
            form.addRow(label, widget)

        layout.addLayout(form)

        self.advanced_button = QPushButton("⚙️ Configurações Avançadas..." if lang == "pt" else "⚙️ Advanced Settings...")
        self.advanced_button.clicked.connect(self.open_advanced)
        layout.addWidget(self.advanced_button)

        # Seção de Aprendizado Ativo & Modelo de Treinamento
        training_group = QGroupBox("🧠 Aprendizado Ativo & Treinamento" if lang == "pt" else "🧠 Active Learning & Training")
        training_layout = QHBoxLayout(training_group)
        training_layout.setContentsMargins(10, 10, 10, 10)
        training_layout.setSpacing(8)

        self.btn_export_training = QPushButton("💾 Exportar Treinamento (.pkl)..." if lang == "pt" else "💾 Export Training (.pkl)...")
        self.btn_export_training.setObjectName("btn_secondary")
        self.btn_export_training.setToolTip("Salvar o classificador treinado e dados de correção em arquivo")
        self.btn_export_training.clicked.connect(self._on_export_training)
        training_layout.addWidget(self.btn_export_training)

        self.btn_import_training = QPushButton("📂 Carregar Treinamento (.pkl)..." if lang == "pt" else "📂 Load Training (.pkl)...")
        self.btn_import_training.setObjectName("btn_secondary")
        self.btn_import_training.setToolTip("Importar arquivo com modelo treinado previamente")
        self.btn_import_training.clicked.connect(self._on_import_training)
        training_layout.addWidget(self.btn_import_training)

        layout.addWidget(training_group)

        self._advanced_params = dict(current_params)

        btn_box = QHBoxLayout()
        self.btn_reset_defaults = QPushButton("Restaurar Padrões" if lang == "pt" else "Restore Defaults")
        self.btn_reset_defaults.setObjectName("btn_secondary")
        self.btn_reset_defaults.clicked.connect(self.reset_defaults)
        btn_box.addWidget(self.btn_reset_defaults)
        btn_box.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        btn_box.addWidget(buttons)
        layout.addLayout(btn_box)

    def _on_export_training(self):
        parent = self.parent()
        if parent and hasattr(parent, "export_training_model"):
            parent.export_training_model()

    def _on_import_training(self):
        parent = self.parent()
        if parent and hasattr(parent, "import_training_model"):
            parent.import_training_model()

    def reset_defaults(self):
        for key, widget in self.inputs.items():
            if key in DEFAULT_ALGO_PARAMS:
                widget.setValue(DEFAULT_ALGO_PARAMS[key])
        self._advanced_params = DEFAULT_ALGO_PARAMS.copy()

    def apply_styles(self):
        dark = True
        if self.parent() and hasattr(self.parent(), "theme_mode"):
            dark = (self.parent().theme_mode == "dark")
        
        if dark:
            self.setStyleSheet("""
                QDialog { background-color: #171A1E; color: #E7E9EC; font-family: 'Segoe UI'; }
                QLabel { font-weight: bold; font-size: 12px; color: #E7E9EC; background: transparent; background-color: transparent; border: none; }
                QSpinBox, QDoubleSpinBox { 
                    background-color: #262A30; color: #4ADE80; font-weight: bold; font-size: 13px;
                    border: 1px solid #3F444D; border-radius: 5px; padding: 4px 8px;
                }
                QSpinBox:focus, QDoubleSpinBox:focus { border-color: #3B82F6; }
                QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 5px; font-weight: bold; border: 0; }
                QPushButton:hover { background-color: #1D4ED8; }
                QPushButton#btn_secondary { background-color: #2D333B; color: #E2E8F0; border: 1px solid #444C56; font-size: 11px; }
                QPushButton#btn_secondary:hover { background-color: #373E47; }
                QGroupBox { font-weight: bold; font-size: 12px; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; margin-top: 10px; padding-top: 12px; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 4px; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #1E293B; font-family: 'Segoe UI'; }
                QLabel { font-weight: bold; font-size: 12px; color: #334155; background: transparent; background-color: transparent; border: none; }
                QSpinBox, QDoubleSpinBox { 
                    background-color: #F8FAFC; color: #15803D; font-weight: bold; font-size: 13px;
                    border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 8px;
                }
                QSpinBox:focus, QDoubleSpinBox:focus { border-color: #2563EB; background-color: #FFFFFF; }
                QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 5px; font-weight: bold; border: 0; }
                QPushButton:hover { background-color: #1D4ED8; }
                QPushButton#btn_secondary { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; font-size: 11px; }
                QPushButton#btn_secondary:hover { background-color: #E2E8F0; }
                QGroupBox { font-weight: bold; font-size: 12px; color: #64748B; border: 1px solid #E2E8F0; border-radius: 6px; margin-top: 10px; padding-top: 12px; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 4px; }
            """)

    def get_params(self):
        result = dict(self._advanced_params)
        result.update({key: widget.value() for key, widget in self.inputs.items()})
        return result

    def open_advanced(self):
        dialog = AdvancedAlgoSettingsDialog(self.get_params(), self)
        if dialog.exec():
            self._advanced_params.update(dialog.get_params())


class AdvancedAlgoSettingsDialog(QDialog):
    def __init__(self, current_params, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações Avançadas")
        self.setMinimumWidth(440)
        self.apply_styles()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        self.inputs = {}
        fields = [
            ("prominence", "Proeminência (Prominence):", 0.0, 2.0, 0.001),
            ("width_min_ms", "Largura mínima do pico (ms):", 0.0, 500.0, 0.5),
            ("width_max_ms", "Largura máxima do pico (ms):", 0.0, 500.0, 0.5),
            ("smooth_window_ms", "Janela de suavização (ms):", 1.0, 500.0, 0.5),
            ("b1_min", "Frequência passa-alta (Hz):", 100.0, 24000.0, 100.0),
            ("b1_max", "Frequência passa-baixa (Hz):", 100.0, 24000.0, 100.0),
            ("noise_floor", "Limiar de ruído dinâmico:", 0.01, 2.0, 0.01),
            ("adaptation_rate", "Taxa de adaptação:", 0.0, 1.0, 0.01),
            ("focal_sensitivity", "Sensibilidade Focal (Rejeição Grilos Distantes):", 0.0, 1.0, 0.05),
        ]
        for key, label, vmin, vmax, step in fields:
            widget = QDoubleSpinBox()
            widget.setRange(vmin, vmax)
            widget.setSingleStep(step)
            widget.setDecimals(4)
            widget.setValue(float(current_params.get(key, {
                "prominence": 0.02, "width_min_ms": 0.0, "width_max_ms": 0.0,
                "smooth_window_ms": 15.0, "noise_floor": 1.00,
                "adaptation_rate": 0.10, "focal_sensitivity": 0.60
            }.get(key, 0.0))))
            self.inputs[key] = widget
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_styles(self):
        dark = True
        if self.parent() and hasattr(self.parent(), "theme_mode"):
            dark = (self.parent().theme_mode == "dark")
        elif self.parent() and self.parent().parent() and hasattr(self.parent().parent(), "theme_mode"):
            dark = (self.parent().parent().theme_mode == "dark")

        if dark:
            self.setStyleSheet("""
                QDialog { background-color: #171A1E; color: #E7E9EC; font-family: 'Segoe UI'; }
                QLabel { font-weight: bold; font-size: 12px; color: #E7E9EC; background: transparent; background-color: transparent; border: none; }
                QDoubleSpinBox { 
                    background-color: #262A30; color: #4ADE80; font-weight: bold; font-size: 13px;
                    border: 1px solid #3F444D; border-radius: 5px; padding: 4px 8px;
                }
                QDoubleSpinBox:focus { border-color: #3B82F6; }
                QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 5px; font-weight: bold; border: 0; }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #1E293B; font-family: 'Segoe UI'; }
                QLabel { font-weight: bold; font-size: 12px; color: #334155; background: transparent; background-color: transparent; border: none; }
                QDoubleSpinBox { 
                    background-color: #F8FAFC; color: #15803D; font-weight: bold; font-size: 13px;
                    border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 8px;
                }
                QDoubleSpinBox:focus { border-color: #2563EB; background-color: #FFFFFF; }
                QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 5px; font-weight: bold; border: 0; }
                QPushButton:hover { background-color: #1D4ED8; }
            """)

    def get_params(self):
        return {key: widget.value() for key, widget in self.inputs.items()}


class GeneralSettingsDialog(QDialog):
    def __init__(self, current_params, lang, parent=None):
        super().__init__(parent)
        self.setWindowTitle(I18N[lang]["gen_settings"])
        self.setMinimumWidth(420)
        self.apply_styles()
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)
        
        self.lang_input = QComboBox()
        self.lang_input.addItems(["pt", "en"])
        self.lang_input.setCurrentText(current_params.get("lang", "pt"))
        
        self.inst_input = QLineEdit(current_params.get("institution", ""))
        self.name_input = QLineEdit(current_params.get("researcher_name", ""))
        
        self.role_input = QComboBox()
        self.role_input.addItems(["", "Discente", "Docente"] if lang == "pt" else ["", "Student", "Professor"])
        self.role_input.setCurrentText(current_params.get("role", ""))
        
        self.level_input = QComboBox()
        opts_pt = ["", "Ensino Médio", "Graduação", "Mestrado", "Doutorado", "Pós-Doutorado"]
        opts_en = ["", "High School", "Bachelor", "Master", "PhD", "Postdoc"]
        self.level_input.addItems(opts_pt if lang == "pt" else opts_en)
        
        if current_params.get("level", "") not in [self.level_input.itemText(i) for i in range(self.level_input.count())]:
             self.level_input.addItem(current_params.get("level", ""))
        self.level_input.setCurrentText(current_params.get("level", ""))

        form.addRow(I18N[lang]["lang"], self.lang_input)
        form.addRow(I18N[lang]["inst"], self.inst_input)
        form.addRow(I18N[lang]["researcher"], self.name_input)
        form.addRow(I18N[lang]["role"], self.role_input)
        form.addRow(I18N[lang]["level"], self.level_input)
        
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def apply_styles(self):
        dark = True
        if self.parent() and hasattr(self.parent(), "theme_mode"):
            dark = (self.parent().theme_mode == "dark")

        if dark:
            self.setStyleSheet("""
                QDialog { background-color: #171A1E; color: #E7E9EC; font-family: 'Segoe UI'; }
                QLabel { font-weight: bold; font-size: 12px; color: #E7E9EC; background: transparent; background-color: transparent; border: none; }
                QLineEdit, QComboBox { 
                    background-color: #262A30; color: #4ADE80; font-weight: bold; font-size: 13px;
                    border: 1px solid #3F444D; border-radius: 5px; padding: 4px 8px;
                }
                QLineEdit:focus, QComboBox:focus { border-color: #3B82F6; }
                QComboBox QAbstractItemView {
                    background-color: #171A1E; color: #E7E9EC; selection-background-color: #2563EB;
                }
                QComboBox::drop-down { border: 0px; }
                QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 5px; font-weight: bold; border: 0; }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #1E293B; font-family: 'Segoe UI'; }
                QLabel { font-weight: bold; font-size: 12px; color: #334155; background: transparent; background-color: transparent; border: none; }
                QLineEdit, QComboBox { 
                    background-color: #F8FAFC; color: #15803D; font-weight: bold; font-size: 13px;
                    border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 8px;
                }
                QLineEdit:focus, QComboBox:focus { border-color: #2563EB; background-color: #FFFFFF; }
                QComboBox QAbstractItemView {
                    background-color: #FFFFFF; color: #1E293B; selection-background-color: #DBEAFE; selection-color: #1E40AF;
                }
                QComboBox::drop-down { border: 0px; }
                QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 5px; font-weight: bold; border: 0; }
                QPushButton:hover { background-color: #1D4ED8; }
            """)

    def get_params(self):
        return {
            "lang": self.lang_input.currentText(),
            "institution": self.inst_input.text().strip(),
            "researcher_name": self.name_input.text().strip(),
            "role": self.role_input.currentText(),
            "level": self.level_input.currentText()
        }


class ChangelogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Notas de Atualização - v{APP_VERSION}")
        self.setMinimumSize(490, 370)
        self.apply_styles()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        
        lbl_header = QLabel(f"📋 Histórico de Versões e Mudanças")
        lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #3B82F6; background: transparent;")
        lbl_header.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        layout.addWidget(lbl_header)
        
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        text_browser.verticalScrollBar().setSingleStep(12)
        
        html_content = "<div style='font-family: Segoe UI, sans-serif; font-size: 13px;'>"
        for ver, changes in CHANGELOG.items():
            if ver == APP_VERSION:
                title_html = f"<h3 style='margin-top: 6px; margin-bottom: 4px; color: #2563EB; font-size: 14px;'>v{ver} (atual)</h3>"
            else:
                title_html = f"<h3 style='margin-top: 6px; margin-bottom: 4px; color: #64748B; font-size: 14px;'>v{ver}</h3>"
            html_content += title_html + "<ul style='margin-top: 4px; padding-left: 18px;'>"
            for change in changes:
                html_content += f"<li style='margin-bottom: 4px; line-height: 1.45;'>{change}</li>"
            html_content += "</ul>"
        html_content += "</div>"
        
        text_browser.setHtml(html_content)
        layout.addWidget(text_browser, 1)
        
        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("btn_secondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignRight)

    def apply_styles(self):
        dark = True
        if self.parent() and hasattr(self.parent(), "theme_mode"):
            dark = (self.parent().theme_mode == "dark")
        elif self.parent() and self.parent().parent() and hasattr(self.parent().parent(), "theme_mode"):
            dark = (self.parent().parent().theme_mode == "dark")

        if dark:
            self.setStyleSheet("""
                QDialog { background-color: #171A1E; color: #E7E9EC; font-family: 'Segoe UI'; }
                QLabel { background: transparent; background-color: transparent; border: none; color: #E7E9EC; }
                QTextBrowser { 
                    background-color: #1F2329; color: #E7E9EC; border: 1px solid #333A44; 
                    border-radius: 8px; padding: 10px; 
                }
                QScrollBar:vertical {
                    background: transparent; width: 10px; margin: 4px 2px 4px 2px; border-radius: 5px; border: none;
                }
                QScrollBar::track:vertical {
                    background-color: #16191E; border-radius: 5px; border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: #64748B; min-height: 28px; border-radius: 5px; border: none;
                }
                QScrollBar::handle:vertical:hover { background-color: #94A3B8; }
                QScrollBar::handle:vertical:pressed { background-color: #475569; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; width: 0px; background: none; border: none; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; border: none; }
                QPushButton { background-color: #2D333B; color: #E2E8F0; padding: 7px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #444C56; }
                QPushButton:hover { background-color: #373E47; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #1E293B; font-family: 'Segoe UI'; }
                QLabel { background: transparent; background-color: transparent; border: none; color: #334155; }
                QTextBrowser { 
                    background-color: #F8FAFC; color: #1E293B; border: 1px solid #CBD5E1; 
                    border-radius: 8px; padding: 10px; 
                }
                QScrollBar:vertical {
                    background: transparent; width: 10px; margin: 4px 2px 4px 2px; border-radius: 5px; border: none;
                }
                QScrollBar::track:vertical {
                    background-color: #E2E8F0; border-radius: 5px; border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: #94A3B8; min-height: 28px; border-radius: 5px; border: none;
                }
                QScrollBar::handle:vertical:hover { background-color: #64748B; }
                QScrollBar::handle:vertical:pressed { background-color: #475569; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; width: 0px; background: none; border: none; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; border: none; }
                QPushButton { background-color: #F1F5F9; color: #334155; padding: 7px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #CBD5E1; }
                QPushButton:hover { background-color: #E2E8F0; }
            """)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Crinômetro")
        self.setFixedSize(450, 275)
        self.apply_styles()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(6)
        
        lbl_title = QLabel("🦗 Crinômetro")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #3B82F6; margin-bottom: 2px; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_version = QLabel(f"<a href='changelog' style='color:#3B82F6; text-decoration: underline; font-weight: 600;'>Versão: {APP_VERSION} (ver mudanças)</a>")
        lbl_version.setTextFormat(Qt.TextFormat.RichText)
        lbl_version.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        lbl_version.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_version.setStyleSheet("font-size: 12px; background: transparent; outline: none;")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.linkActivated.connect(self._open_changelog)
        
        lbl_dev = QLabel("Criado por: <b>Rogério de Araújo Freitas</b><br><a href='https://github.com/rogerioafreitas' style='color:#3B82F6; text-decoration:none;'>github.com/rogerioafreitas</a>")
        lbl_dev.setOpenExternalLinks(True)
        lbl_dev.setStyleSheet("font-size: 13px; margin-top: 8px; margin-bottom: 8px; background: transparent;")
        lbl_dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_desc = QLabel(
            "Desenvolvido com a intenção de auxiliar em um projeto de pesquisa na <b>UNIFESP</b>.<br>"
            "Ferramenta de bioacústica focada em detecção, análise e geração de relatórios de chilreios e pulsos."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; text-align: justify; background: transparent;")
        
        for _lbl in (lbl_title, lbl_version, lbl_dev, lbl_desc):
            _lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            _lbl.setAutoFillBackground(False)

        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(10)

        self.btn_check_update = QPushButton("🔍 Verificar Atualizações")
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.clicked.connect(self._check_for_updates)
        btns_layout.addWidget(self.btn_check_update)

        btns_layout.addStretch()

        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("btn_secondary")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btns_layout.addWidget(btn_close)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_version)
        layout.addWidget(lbl_dev)
        layout.addWidget(lbl_desc)
        layout.addStretch()
        layout.addLayout(btns_layout)

    def _check_for_updates(self):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Checando...")
        self.checker = UpdateCheckerThread(self)
        self.checker.update_available.connect(self._on_update_available)
        self.checker.no_update.connect(self._on_no_update)
        self.checker.error.connect(self._on_update_error)
        self.checker.start()

    def _on_update_available(self, info):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔍 Verificar Atualizações")
        dlg = UpdateDialog(info, self)
        dlg.exec()

    def _on_no_update(self, info):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔍 Verificar Atualizações")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Crinômetro Atualizado",
            f"Você já está executando a versão mais recente do Crinômetro (v{APP_VERSION})!"
        )

    def _on_update_error(self, err_msg):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔍 Verificar Atualizações")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self,
            "Aviso de Atualização",
            f"Não foi possível verificar atualizações no momento:\n{err_msg}"
        )

    def _open_changelog(self, _link=None):
        dlg = ChangelogDialog(self)
        dlg.exec()

    def apply_styles(self):
        dark = True
        if self.parent() and hasattr(self.parent(), "theme_mode"):
            dark = (self.parent().theme_mode == "dark")

        if dark:
            self.setStyleSheet("""
                QDialog { background-color: #171A1E; color: #E7E9EC; font-family: 'Segoe UI'; }
                QLabel { background: transparent; background-color: transparent; border: none; color: #E7E9EC; }
                QLabel:focus { outline: none; border: none; }
                QPushButton { background-color: #2D333B; color: #E2E8F0; padding: 7px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #444C56; }
                QPushButton:hover { background-color: #373E47; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #1E293B; font-family: 'Segoe UI'; }
                QLabel { background: transparent; background-color: transparent; border: none; color: #334155; }
                QLabel:focus { outline: none; border: none; }
                QPushButton { background-color: #F1F5F9; color: #334155; padding: 7px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #CBD5E1; }
                QPushButton:hover { background-color: #E2E8F0; }
            """)


