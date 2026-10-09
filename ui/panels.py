"""
Crinômetro - Painéis Gráficos e Timeline Interativa.
"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QDoubleSpinBox, QSpinBox, QSlider, QComboBox, QAbstractSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QSize, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPolygonF, QPen
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.i18n import I18N
from utils.icons import make_ui_icon


class PlotTitleBar(QFrame):
    """Barra de título da mini janela com suporte a arrastar e soltar (drag & drop fluido com preview)."""
    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.panel = panel
        self._drag_start_pos = None
        self._is_dragging = False
        self._preview_frame = None
        self._hover_target = None

    def _get_preview_frame(self, win):
        if self._preview_frame is None or self._preview_frame.window() != win:
            self._preview_frame = QFrame(win)
            self._preview_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._preview_frame.setStyleSheet(
                "QFrame { "
                "background-color: rgba(37, 99, 235, 0.22); "
                "border: 2px dashed #3B82F6; "
                "border-radius: 8px; "
                "}"
            )
        return self._preview_frame

    def _find_drop_target(self, global_pos, win):
        """Identifica qual painel ou host está sob o cursor."""
        if not getattr(win, "all_panels", None):
            return None

        # Verifica primeiro se está sobre o main_host / main_panel
        if hasattr(win, "main_host") and win.main_host is not None:
            m_top_left = win.main_host.mapToGlobal(win.main_host.rect().topLeft())
            m_rect = win.main_host.rect()
            m_rect.moveTo(m_top_left)
            if m_rect.contains(global_pos):
                if self.panel is not win.main_panel:
                    return win.main_panel

        # Verifica se está sobre algum card na pilha lateral
        if hasattr(win, "stack_panels"):
            for p in win.stack_panels:
                p_top_left = p.mapToGlobal(p.rect().topLeft())
                p_rect = p.rect()
                p_rect.moveTo(p_top_left)
                if p_rect.contains(global_pos):
                    return p

        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._is_dragging = False
            self._hover_target = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            cur_pos = event.globalPosition().toPoint()
            dist = (cur_pos - self._drag_start_pos).manhattanLength()
            if dist > 8:
                self._is_dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                win = self.window()
                target = self._find_drop_target(cur_pos, win)
                self._hover_target = target

                preview = self._get_preview_frame(win)
                if target is not None and target is not self.panel:
                    # Mapeia a geometria do widget alvo para as coordenadas da janela principal
                    target_rect = target.rect()
                    top_left_win = win.mapFromGlobal(target.mapToGlobal(target_rect.topLeft()))
                    preview.setGeometry(top_left_win.x(), top_left_win.y(), target.width(), target.height())
                    preview.show()
                    preview.raise_()
                else:
                    preview.hide()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        win = self.window()
        if self._preview_frame is not None:
            self._preview_frame.hide()

        self.setCursor(Qt.CursorShape.OpenHandCursor)

        if self._is_dragging and event.button() == Qt.MouseButton.LeftButton:
            cur_pos = event.globalPosition().toPoint()
            target = self._find_drop_target(cur_pos, win)

            if target is not None and target is not self.panel:
                # Se soltou sobre o painel principal: efetua swap com o painel maximizado
                if hasattr(win, "main_panel") and (target is win.main_panel or target is getattr(win, "main_host", None)):
                    if hasattr(win, "swap_main_panel"):
                        win.swap_main_panel(self.panel)
                # Se soltou sobre outro painel da pilha lateral
                elif hasattr(win, "stack_panels") and target in win.stack_panels and self.panel in win.stack_panels:
                    if hasattr(win, "reorder_stack_panels"):
                        win.reorder_stack_panels(self.panel, target)
                # Se o painel arrastado era o main_panel e foi solto sobre um painel da pilha lateral
                elif hasattr(win, "main_panel") and self.panel is win.main_panel and target in win.stack_panels:
                    if hasattr(win, "swap_main_panel"):
                        win.swap_main_panel(target)

        self._drag_start_pos = None
        self._is_dragging = False
        self._hover_target = None
        super().mouseReleaseEvent(event)


class CompactCtrlBar(QFrame):
    """Barra de controle adaptativa com minimumSizeHint flexível para permitir redimensionamento livre sem travar."""
    def minimumSizeHint(self):
        return QSize(0, 0)


class PlotPanel(QFrame):
    undo_requested = pyqtSignal()
    spectrogram_y_limits_changed = pyqtSignal(float, float, str)
    freq_tolerance_changed = pyqtSignal(int, object)
    wave_visibility_changed = pyqtSignal(bool, bool, bool, bool)
    """Mini janela / Card de gráfico com cantos arredondados e suporte a reordenação."""
    def __init__(self, title_key, lang, expand_callback, main=False):
        super().__init__()
        self.title_key = title_key
        self.expand_callback = expand_callback
        self.pulse_edit_mode = False
        self._y_locked = False
        self.main = bool(main)

        self.setObjectName("plotCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 6)
        self.layout.setSpacing(0)

        self.title_bar = PlotTitleBar(self)
        self.title_bar.setObjectName("plotTitleBar")
        self.title_bar.setCursor(Qt.CursorShape.OpenHandCursor)
        self.title_bar.setToolTip("Arraste esta barra para reorganizar as posições dos gráficos")
        bar = QHBoxLayout(self.title_bar)
        bar.setContentsMargins(12, 6, 8, 6)
        bar.setSpacing(4)

        self.lbl_title = QLabel(I18N[lang][title_key])
        self.lbl_title.setObjectName("plotTitle")
        bar.addWidget(self.lbl_title)
        bar.addStretch()

        if self.title_key == "wave":
            self.show_raw = True
            self.show_env = True
            self.show_lod = False
            self.show_peaks = True

            self.btn_toggle_raw = self._chip_toggle(
                "Sinal Bruto", "Exibir/Ocultar Sinal Bruto Filtrado (Amostras Reais)",
                checked=True, accent_color="#94A3B8"
            )
            self.btn_toggle_env = self._chip_toggle(
                "Envoltória", "Exibir/Ocultar Envoltória de Hilbert Suavizada",
                checked=True, accent_color="#0284C7"
            )
            self.btn_toggle_lod = self._chip_toggle(
                "Min-Max LOD", "Exibir/Ocultar Decimação Min-Max LOD",
                checked=False, accent_color="#F97316"
            )
            self.btn_toggle_peaks = self._chip_toggle(
                "Pulsos", "Exibir/Ocultar Marcadores de Pulsos Detectados",
                checked=True, accent_color="#10B981"
            )

            bar.addWidget(self.btn_toggle_raw)
            bar.addWidget(self.btn_toggle_env)
            bar.addWidget(self.btn_toggle_lod)
            bar.addWidget(self.btn_toggle_peaks)

            sep_wave = QFrame()
            sep_wave.setFrameShape(QFrame.Shape.VLine)
            sep_wave.setFixedHeight(16)
            sep_wave.setStyleSheet("background-color: rgba(150, 150, 150, 0.25); border: none; margin: 0 4px;")
            bar.addWidget(sep_wave)

        # Botão de edição de pulsos (ativa/desativa modo de seleção)
        self.btn_pulse_edit = self._tool_button("", "Ativar modo de edição de pulsos (clique para adicionar/remover)")
        self.btn_pulse_edit.setObjectName("plotTool")
        self.btn_pulse_edit.setIcon(make_ui_icon("pencil", color="#D7DCE2", size=14))
        self.btn_pulse_edit.setIconSize(QSize(13, 13))
        self.btn_pulse_edit.setCheckable(True)
        self.btn_pulse_edit.toggled.connect(self._toggle_pulse_edit_mode)
        bar.addWidget(self.btn_pulse_edit)

        self.btn_pulse_undo = self._tool_button("↶", "Desfazer última edição de pulso")
        self.btn_pulse_undo.setObjectName("plotTool")
        self.btn_pulse_undo.setEnabled(False)
        self.btn_pulse_undo.clicked.connect(self.undo_requested.emit)
        bar.addWidget(self.btn_pulse_undo)

        # Ações do gráfico: somente maximizar/restaurar, que possui comportamento real.
        self.btn_expand = self._tool_button("", "Colocar este gráfico na posição principal")
        self.btn_expand.setObjectName("plotMaximize")
        self.btn_expand.setIcon(make_ui_icon("maximize", color="#D7DCE2", size=14))
        self.btn_expand.setIconSize(QSize(13, 13))
        self.btn_expand.clicked.connect(lambda: self.expand_callback(self))
        bar.addWidget(self.btn_expand)

        self.btn_close = self._tool_button("✕", "Fechar este gráfico (reabra no menu 'Gráficos' ou restaure o padrão)")
        self.btn_close.setObjectName("plotClose")
        self.btn_close.clicked.connect(self._on_close_clicked)
        bar.addWidget(self.btn_close)

        self.figure = Figure(facecolor="none")
        self.figure.patch.set_alpha(0.0)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setStyleSheet("background: transparent; border: 0; padding: 0; margin: 0;")
        self.ax = self.figure.add_subplot(111, facecolor="#101214")
        self.apply_dark_theme()

        self.layout.addWidget(self.title_bar)

        if self.title_key == "freq":
            self.freq_ctrl_bar = CompactCtrlBar()
            self.freq_ctrl_bar.setObjectName("freqCtrlBar")
            self.freq_ctrl_bar.setStyleSheet(self._ctrl_bar_style())
            fctrl_layout = QHBoxLayout(self.freq_ctrl_bar)
            fctrl_layout.setContentsMargins(4, 2, 4, 3)
            fctrl_layout.setSpacing(6)
            self._build_carrier_controls(fctrl_layout)
            fctrl_layout.addStretch()
            self.layout.addWidget(self.freq_ctrl_bar)

        if self.title_key == "spec":
            self.spec_unit = "kHz"
            self.spec_ctrl_bar = CompactCtrlBar()
            self.spec_ctrl_bar.setObjectName("specCtrlBar")
            self.spec_ctrl_bar.setStyleSheet(self._ctrl_bar_style())
            ctrl_layout = QHBoxLayout(self.spec_ctrl_bar)
            ctrl_layout.setContentsMargins(4, 2, 4, 3)
            ctrl_layout.setSpacing(4)

            # 1. Bloco de Escala Y Compacto e Unificado
            self.y_scale_box = QFrame()
            self.y_scale_box.setObjectName("yScaleBox")
            self.y_scale_box.setFixedWidth(168)
            y_layout = QHBoxLayout(self.y_scale_box)
            y_layout.setContentsMargins(6, 1, 4, 1)
            y_layout.setSpacing(3)

            lbl_y = QLabel("Y:")
            lbl_y.setProperty("class", "specCtrlMuted")
            y_layout.addWidget(lbl_y)

            self.spin_spec_ymin = QDoubleSpinBox()
            self.spin_spec_ymin.setProperty("class", "specScaleSpin")
            self.spin_spec_ymin.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.spin_spec_ymin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self.spin_spec_ymin.setRange(0.0, 30.0)
            self.spin_spec_ymin.setSingleStep(0.5)
            self.spin_spec_ymin.setDecimals(1)
            self.spin_spec_ymin.setValue(0.0)
            self.spin_spec_ymin.setFixedWidth(34)
            self.spin_spec_ymin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.spin_spec_ymin.setToolTip("Limite inferior do eixo Y (frequência)")
            self.spin_spec_ymin.valueChanged.connect(self._on_spec_limits_changed)
            y_layout.addWidget(self.spin_spec_ymin)

            lbl_to = QLabel("–")
            lbl_to.setProperty("class", "specCtrlSep")
            y_layout.addWidget(lbl_to)

            self.spin_spec_ymax = QDoubleSpinBox()
            self.spin_spec_ymax.setProperty("class", "specScaleSpin")
            self.spin_spec_ymax.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.spin_spec_ymax.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self.spin_spec_ymax.setRange(0.5, 50.0)
            self.spin_spec_ymax.setSingleStep(0.5)
            self.spin_spec_ymax.setDecimals(1)
            self.spin_spec_ymax.setValue(10.0)
            self.spin_spec_ymax.setFixedWidth(44)
            self.spin_spec_ymax.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.spin_spec_ymax.setToolTip("Limite superior do eixo Y (frequência)")
            self.spin_spec_ymax.valueChanged.connect(self._on_spec_limits_changed)
            y_layout.addWidget(self.spin_spec_ymax)

            self.combo_spec_unit = QComboBox()
            self.combo_spec_unit.setObjectName("specUnitCombo")
            self.combo_spec_unit.setProperty("class", "specUnitCombo")
            self.combo_spec_unit.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.combo_spec_unit.setFixedWidth(46)
            self.combo_spec_unit.setFixedHeight(20)
            self.combo_spec_unit.addItems(["kHz", "Hz"])
            self.combo_spec_unit.setCurrentText("kHz")
            self.combo_spec_unit.setToolTip("Alternar unidade da escala de frequência (kHz / Hz)")
            self.combo_spec_unit.currentTextChanged.connect(self._on_spec_unit_combo_changed)
            y_layout.addWidget(self.combo_spec_unit)

            # Compatibilidade de referência
            self.btn_spec_unit = self.combo_spec_unit

            ctrl_layout.addWidget(self.y_scale_box)

            # Separador vertical sutil
            self.sep_y_scale = self._make_vsep()
            ctrl_layout.addWidget(self.sep_y_scale)

            # 2. Grupo de Presets Estilo Segmented Control
            self.preset_group_box = QFrame()
            self.preset_group_box.setObjectName("presetGroupBox")
            preset_layout = QHBoxLayout(self.preset_group_box)
            preset_layout.setContentsMargins(1, 1, 1, 1)
            preset_layout.setSpacing(0)

            self.btn_spec_preset_10k = QPushButton("10k")
            self.btn_spec_preset_10k.setProperty("class", "segBtn")
            self.btn_spec_preset_10k.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_spec_preset_10k.setToolTip("Enquadrar de 0 a 10 kHz")
            self.btn_spec_preset_10k.clicked.connect(lambda: self._apply_preset("10k"))
            preset_layout.addWidget(self.btn_spec_preset_10k)

            self.btn_spec_preset_focal = QPushButton("Focal")
            self.btn_spec_preset_focal.setProperty("class", "segBtn")
            self.btn_spec_preset_focal.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_spec_preset_focal.setToolTip("Zoom na banda focal estridulatória")
            self.btn_spec_preset_focal.clicked.connect(lambda: self._apply_preset("focal"))
            preset_layout.addWidget(self.btn_spec_preset_focal)

            self.btn_spec_preset_full = QPushButton(I18N[self.lang]["total"] if hasattr(self, "lang") else "Total")
            self.btn_spec_preset_full.setProperty("class", "segBtn")
            self.btn_spec_preset_full.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_spec_preset_full.setToolTip("Visualização completa até a frequência de Nyquist")
            self.btn_spec_preset_full.clicked.connect(lambda: self._apply_preset("full"))
            preset_layout.addWidget(self.btn_spec_preset_full)

            self._set_active_preset(self.btn_spec_preset_10k)
            ctrl_layout.addWidget(self.preset_group_box)

            # Separador vertical sutil
            self.sep_presets = self._make_vsep()
            ctrl_layout.addWidget(self.sep_presets)

            # 3. Controle da Portadora e Slider do Filtro
            self._build_carrier_controls(ctrl_layout)

            ctrl_layout.addStretch()
            self.layout.addWidget(self.spec_ctrl_bar)

        if self.title_key == "spec":
            self.canvas_container = QWidget()
            self.canvas_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            canvas_layout = QHBoxLayout(self.canvas_container)
            canvas_layout.setContentsMargins(4, 0, 4, 4)
            canvas_layout.setSpacing(2)

            self.slider_spec_y = QSlider(Qt.Orientation.Vertical)
            self.slider_spec_y.setObjectName("specYSlider")
            self.slider_spec_y.setFixedWidth(16)
            self.slider_spec_y.setCursor(Qt.CursorShape.PointingHandCursor)
            self.slider_spec_y.setToolTip("Ajuste direto da altura/frequência máxima do eixo Y")
            self.slider_spec_y.setRange(500, 50000)
            self.slider_spec_y.setSingleStep(500)
            self.slider_spec_y.setPageStep(2000)
            self.slider_spec_y.setValue(10000)
            self.slider_spec_y.valueChanged.connect(self._on_spec_y_slider_changed)

            canvas_layout.addWidget(self.slider_spec_y)
            canvas_layout.addWidget(self.canvas, 1)
            self.layout.addWidget(self.canvas_container, 1)
        else:
            self.layout.addWidget(self.canvas, 1)

        self.setMinimumSize(0, 0)
        self.canvas.setMinimumSize(0, 0)
        if hasattr(self, "spec_ctrl_bar"):
            self.spec_ctrl_bar.setMinimumWidth(0)
            
        self.coord_label = QLabel("", self.canvas)
        self.coord_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.coord_label.setStyleSheet("background-color: rgba(16, 18, 20, 180); color: #4ADE80; font-family: 'Consolas', 'Courier New', monospace; font-size: 10px; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(74, 222, 128, 50);")
        self.coord_label.setVisible(False)

        self.set_main(main)
        self.apply_dark_theme()

    def _tool_button(self, glyph, tooltip):
        b = QPushButton(glyph)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setToolTip(tooltip)
        b.setFixedSize(26, 26)
        b.setObjectName("plotTool")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _chip_toggle(self, text, tooltip, checked=True, accent_color="#3B82F6"):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setFixedHeight(22)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._apply_chip_style(btn, accent_color, checked)
        btn.toggled.connect(lambda c, b=btn, col=accent_color: self._on_chip_toggled(b, col, c))
        return btn

    def _on_chip_toggled(self, btn, accent_color, checked):
        self._apply_chip_style(btn, accent_color, checked)
        if hasattr(self, 'btn_toggle_raw'):
            self.show_raw = self.btn_toggle_raw.isChecked()
            self.show_env = self.btn_toggle_env.isChecked()
            self.show_lod = self.btn_toggle_lod.isChecked()
            self.show_peaks = self.btn_toggle_peaks.isChecked()
            self.wave_visibility_changed.emit(self.show_raw, self.show_env, self.show_lod, self.show_peaks)

    def _apply_chip_style(self, btn, accent_color, checked):
        dark = True
        win = self.window()
        if win and hasattr(win, "theme_mode"):
            dark = (win.theme_mode == "dark")
        try:
            r = int(accent_color[1:3], 16)
            g = int(accent_color[3:5], 16)
            b = int(accent_color[5:7], 16)
        except Exception:
            r, g, b = 59, 130, 246

        if checked:
            alpha = 0.22 if dark else 0.14
            fg = accent_color if dark else ("#1E293B" if accent_color == "#94A3B8" else accent_color)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba({r}, {g}, {b}, {alpha});
                    border: 1.5px solid {accent_color};
                    border-radius: 4px;
                    padding: 0 7px;
                    font-size: 11px;
                    font-weight: bold;
                    color: {fg};
                }}
                QPushButton:hover {{
                    background-color: rgba({r}, {g}, {b}, {alpha + 0.12});
                }}
            """)
        else:
            border_col = "#334155" if dark else "#CBD5E1"
            fg_col = "#64748B" if dark else "#94A3B8"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {border_col};
                    border-radius: 4px;
                    padding: 0 7px;
                    font-size: 11px;
                    font-weight: normal;
                    color: {fg_col};
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border-color: #64748B;
                }}
            """)

    def _toggle_pulse_edit_mode(self, checked):
        """Ativa/desativa o modo de edição de pulsos para este painel."""
        self.pulse_edit_mode = checked
        parent = self.window()
        if hasattr(parent, 'editor_controller') and hasattr(parent.editor_controller, 'update_pulse_edit_buttons'):
            parent.editor_controller.update_pulse_edit_buttons(self)
        elif hasattr(parent, '_update_pulse_edit_buttons'):
            parent._update_pulse_edit_buttons(self)
        if checked:
            self.btn_pulse_edit.setToolTip("Modo de edição ativo! Clique nos picos para adicionar/remover")
            self.btn_pulse_edit.setStyleSheet("QPushButton { background: #1F6FEB; border-radius: 4px; }")
        else:
            self.btn_pulse_edit.setToolTip("Ativar modo de edição de pulsos (clique para adicionar/remover)")
            self.btn_pulse_edit.setStyleSheet("")


    def _on_move_clicked(self, delta):
        win = self.window()
        if hasattr(win, "move_stack_panel"):
            win.move_stack_panel(self, delta)

    def _set_main_visual(self, main):
        self.setProperty("mainPlot", bool(main))
        self.style().unpolish(self)
        self.style().polish(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_controls()
        if hasattr(self, "coord_label") and hasattr(self, "canvas"):
            cw, ch = self.canvas.width(), self.canvas.height()
            self.coord_label.setGeometry(10, ch - 26, 250, 18)

    def _update_responsive_controls(self):
        if self.title_key == "spec":
            # Quando o painel for estreito (< 520px) ou não for o principal, comprime
            # a barra de configurações apenas para o filtro e a FP (como na Freq. Dominante vs Tempo).
            is_main = bool(self.property("mainPlot"))
            is_wide = self.width() >= 520
            show_scale_and_presets = is_main and is_wide

            if hasattr(self, "y_scale_box") and self.y_scale_box.isVisible() != show_scale_and_presets:
                self.y_scale_box.setVisible(show_scale_and_presets)
            if hasattr(self, "preset_group_box") and self.preset_group_box.isVisible() != show_scale_and_presets:
                self.preset_group_box.setVisible(show_scale_and_presets)
            if hasattr(self, "sep_y_scale") and self.sep_y_scale.isVisible() != show_scale_and_presets:
                self.sep_y_scale.setVisible(show_scale_and_presets)
            if hasattr(self, "sep_presets") and self.sep_presets.isVisible() != show_scale_and_presets:
                self.sep_presets.setVisible(show_scale_and_presets)

            # Os chips rápidos de tolerância (±300, ±500, ±700, ±1000) aparecem quando houver largura suficiente (>= 720px no main)
            show_chips = (not is_main and self.width() >= 360) or (is_main and self.width() >= 720)
            if hasattr(self, "chip_box") and self.chip_box.isVisible() != show_chips:
                self.chip_box.setVisible(show_chips)

    def set_main(self, main):
        self.main = bool(main)
        self._set_main_visual(main)
        self.btn_expand.setToolTip(
            "Restaurar posição" if main else "Colocar este gráfico na posição principal"
        )
        self._update_responsive_controls()

    def update_lang(self, lang):
        self.lang = lang
        t = I18N[lang]
        self.lbl_title.setText(t[self.title_key])
        if hasattr(self, "lbl_tol_ref"):
            self.lbl_tol_ref.setText(t["filter"])
        if hasattr(self, "btn_spec_preset_full"):
            self.btn_spec_preset_full.setText(t["total"])
        if hasattr(self, "title_bar"):
            self.title_bar.setToolTip(t["drag_bar_reorder_tt"])
        if hasattr(self, "spin_spec_ymin"):
            self.spin_spec_ymin.setToolTip(t["spec_ymin_tt"])
        if hasattr(self, "spin_spec_ymax"):
            self.spin_spec_ymax.setToolTip(t["spec_ymax_tt"])
        if hasattr(self, "combo_spec_unit"):
            self.combo_spec_unit.setToolTip(t["spec_unit_tt"])
        if hasattr(self, "btn_spec_preset_focal"):
            self.btn_spec_preset_focal.setToolTip(t["spec_preset_focal_tt"])
        if hasattr(self, "btn_spec_preset_full"):
            self.btn_spec_preset_full.setToolTip(t["spec_preset_full_tt"])
        if hasattr(self, "slider_spec_y"):
            self.slider_spec_y.setToolTip(t["spec_slider_y_tt"])
        if hasattr(self, "btn_pulse_edit"):
            self.btn_pulse_edit.setToolTip(t["pulse_edit_on_tt"] if self.pulse_edit_mode else t["pulse_edit_off_tt"])
        if hasattr(self, "btn_expand"):
            self.btn_expand.setToolTip(t["expand_restore_tt"] if self.main else t["expand_main_tt"])
        if hasattr(self, "slider_carrier_tol"):
            self.slider_carrier_tol.setToolTip(t["carrier_tol_slider_tt"])
        if hasattr(self, "spin_carrier_tol"):
            self.spin_carrier_tol.setToolTip(t["carrier_tol_spin_tt"])

    def apply_dark_theme(self):
        dark = getattr(self.window(), "theme_mode", "dark") == "dark"
        fg = "#A9ADB5" if dark else "#1F2937"
        spine = "#2A2D32" if dark else "#CBD5E1"
        grid = "#25282D" if dark else "#E2E8F0"
        face = "#101214" if dark else "#FFFFFF"
        # Fundo da figura transparente para que as bordas arredondadas da mini janela nunca sejam cortadas
        self.figure.set_facecolor("none")
        self.figure.patch.set_alpha(0.0)
        self.ax.set_facecolor(face)
        self.ax.patch.set_alpha(1.0)
        self.ax.tick_params(colors=fg, labelsize=7.5, length=2.5, width=0.8, pad=2)
        for sp in self.ax.spines.values():
            sp.set_color(spine)
            sp.set_linewidth(0.8)
        self.ax.xaxis.label.set_color(fg)
        self.ax.yaxis.label.set_color(fg)
        self.ax.grid(color=grid, linewidth=0.6, alpha=0.65)
        
        # Atualiza cor dos ícones das ferramentas para alto contraste em ambos os temas
        icon_color = "#D7DCE2" if dark else "#334155"
        self.btn_pulse_edit.setIcon(make_ui_icon("pencil", color=icon_color, size=14))
        self.btn_expand.setIcon(make_ui_icon("maximize", color=icon_color, size=14))
        if hasattr(self, "btn_close"):
            self.btn_close.setStyleSheet("")
        if hasattr(self, "canvas"):
            self.canvas.draw_idle()
        
        # Estilização do eixo secundário do histograma (twinx - duração média)
        ax2 = getattr(self, "_ax2", None)
        if ax2 is not None:
            dur_color = '#FF6B6B' if dark else '#DC2626'
            ax2.tick_params(axis='y', labelsize=7, colors=dur_color, length=2)
            ax2.yaxis.label.set_color(dur_color)
            for sp in ax2.spines.values():
                sp.set_visible(False)
            ax2.spines['right'].set_visible(True)
            ax2.spines['right'].set_color(dur_color)
            ax2.spines['right'].set_linewidth(0.8)
            ax2.spines['right'].set_alpha(0.5)
            ax2.set_facecolor('none')

        if hasattr(self, "spec_ctrl_bar"):
            self.spec_ctrl_bar.setStyleSheet(self._ctrl_bar_style(dark))
        if hasattr(self, "freq_ctrl_bar"):
            self.freq_ctrl_bar.setStyleSheet(self._ctrl_bar_style(dark))
        if hasattr(self, "btn_toggle_raw"):
            self._apply_chip_style(self.btn_toggle_raw, "#94A3B8", self.btn_toggle_raw.isChecked())
            self._apply_chip_style(self.btn_toggle_env, "#0284C7", self.btn_toggle_env.isChecked())
            self._apply_chip_style(self.btn_toggle_lod, "#F97316", self.btn_toggle_lod.isChecked())
            self._apply_chip_style(self.btn_toggle_peaks, "#10B981", self.btn_toggle_peaks.isChecked())

    def _on_close_clicked(self):
        """Notifica a janela principal para fechar/ocultar este painel."""
        win = self.window()
        if hasattr(win, "close_plot_panel"):
            win.close_plot_panel(self)
        else:
            self.hide()

    @staticmethod
    def _make_vsep():
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.NoFrame)
        sep.setFixedWidth(1)
        sep.setStyleSheet("background-color: rgba(150, 150, 150, 0.2); border: none; margin: 3px 2px;")
        return sep

    def _set_active_preset(self, active_btn):
        for btn in (getattr(self, "btn_spec_preset_10k", None),
                    getattr(self, "btn_spec_preset_focal", None),
                    getattr(self, "btn_spec_preset_full", None)):
            if btn is not None:
                is_active = (btn is active_btn)
                btn.setProperty("active", "true" if is_active else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    def _apply_preset(self, preset_name):
        btn_map = {
            "10k": getattr(self, "btn_spec_preset_10k", None),
            "focal": getattr(self, "btn_spec_preset_focal", None),
            "full": getattr(self, "btn_spec_preset_full", None),
        }
        btn = btn_map.get(preset_name)
        if btn is not None and btn.property("active") == "true":
            self._set_active_preset(None)
            self._y_locked = False
            return

        self._is_applying_preset = True
        try:
            if preset_name in ("10k", "focal", "full"):
                self._y_locked = True
            else:
                self._y_locked = False

            if preset_name == "10k":
                self._set_active_preset(self.btn_spec_preset_10k)
                self.set_spec_limits(0.0, 10.0, unit="kHz")
            elif preset_name == "focal":
                self._set_active_preset(self.btn_spec_preset_focal)
                self._preset_focal_band()
            elif preset_name == "full":
                self._set_active_preset(self.btn_spec_preset_full)
                self._preset_full_nyquist()
        finally:
            self._is_applying_preset = False

    def _sync_y_slider_from_ymax(self, ymax):
        if hasattr(self, "slider_spec_y") and not getattr(self, "_is_syncing_y_slider", False):
            self._is_syncing_y_slider = True
            try:
                hz_val = int(ymax * 1000.0) if getattr(self, "spec_unit", "kHz") == "kHz" else int(ymax)
                if hz_val > self.slider_spec_y.maximum():
                    self.slider_spec_y.setMaximum(max(hz_val, 50000))
                if hz_val < self.slider_spec_y.minimum():
                    self.slider_spec_y.setMinimum(min(hz_val, 500))
                self.slider_spec_y.blockSignals(True)
                self.slider_spec_y.setValue(hz_val)
                self.slider_spec_y.blockSignals(False)
            finally:
                self._is_syncing_y_slider = False

    def _on_spec_y_slider_changed(self, val):
        if not hasattr(self, "spin_spec_ymax") or getattr(self, "_is_syncing_y_slider", False):
            return
        self._is_syncing_y_slider = True
        try:
            if getattr(self, "spec_unit", "kHz") == "kHz":
                target_val = round(val / 1000.0, 1)
            else:
                target_val = float(val)
            self.spin_spec_ymax.setValue(target_val)
        finally:
            self._is_syncing_y_slider = False

    def _on_spec_limits_changed(self):
        if not hasattr(self, "spin_spec_ymin") or not hasattr(self, "spin_spec_ymax"):
            return
        if not getattr(self, "_is_applying_preset", False):
            self._set_active_preset(None)
            self._y_locked = False
        ymin = self.spin_spec_ymin.value()
        ymax = self.spin_spec_ymax.value()
        step = self.spin_spec_ymin.singleStep()
        if ymin >= ymax:
            if self.sender() == self.spin_spec_ymin:
                ymax = ymin + step
                self.spin_spec_ymax.blockSignals(True)
                self.spin_spec_ymax.setValue(ymax)
                self.spin_spec_ymax.blockSignals(False)
            else:
                ymin = max(self.spin_spec_ymin.minimum(), ymax - step)
                self.spin_spec_ymin.blockSignals(True)
                self.spin_spec_ymin.setValue(ymin)
                self.spin_spec_ymin.blockSignals(False)

        self._sync_y_slider_from_ymax(ymax)

        self.spectrogram_y_limits_changed.emit(ymin, ymax, getattr(self, "spec_unit", "kHz"))

    def _on_spec_unit_combo_changed(self, new_unit):
        if not hasattr(self, "spin_spec_ymin") or not hasattr(self, "spin_spec_ymax"):
            return
        old_unit = getattr(self, "spec_unit", "kHz")
        if new_unit == old_unit:
            return
        ymin = self.spin_spec_ymin.value()
        ymax = self.spin_spec_ymax.value()
        self.spec_unit = new_unit
        self.spin_spec_ymin.blockSignals(True)
        self.spin_spec_ymax.blockSignals(True)
        if new_unit == "Hz":
            self.spin_spec_ymin.setRange(0.0, 30000.0)
            self.spin_spec_ymin.setSingleStep(500.0)
            self.spin_spec_ymin.setDecimals(0)
            self.spin_spec_ymin.setValue(ymin * 1000.0)
            self.spin_spec_ymax.setRange(500.0, 50000.0)
            self.spin_spec_ymax.setSingleStep(500.0)
            self.spin_spec_ymax.setDecimals(0)
            self.spin_spec_ymax.setValue(ymax * 1000.0)
        else:
            self.spin_spec_ymin.setRange(0.0, 30.0)
            self.spin_spec_ymin.setSingleStep(0.5)
            self.spin_spec_ymin.setDecimals(1)
            self.spin_spec_ymin.setValue(ymin / 1000.0)
            self.spin_spec_ymax.setRange(0.5, 50.0)
            self.spin_spec_ymax.setSingleStep(0.5)
            self.spin_spec_ymax.setDecimals(1)
            self.spin_spec_ymax.setValue(ymax / 1000.0)
        self.spin_spec_ymin.blockSignals(False)
        self.spin_spec_ymax.blockSignals(False)
        self._update_carrier_badge()
        self._on_spec_limits_changed()

    def _toggle_spec_unit(self):
        target = "Hz" if getattr(self, "spec_unit", "kHz") == "kHz" else "kHz"
        if hasattr(self, "combo_spec_unit"):
            self.combo_spec_unit.setCurrentText(target)
        else:
            self._on_spec_unit_combo_changed(target)

    def set_spec_limits(self, ymin, ymax, unit="kHz"):
        if not hasattr(self, "spin_spec_ymin"):
            return
        if getattr(self, "spec_unit", "kHz") != unit:
            self.spec_unit = unit
            if hasattr(self, "combo_spec_unit"):
                self.combo_spec_unit.blockSignals(True)
                self.combo_spec_unit.setCurrentText(unit)
                self.combo_spec_unit.blockSignals(False)
            self.spin_spec_ymin.blockSignals(True)
            self.spin_spec_ymax.blockSignals(True)
            if unit == "kHz":
                self.spin_spec_ymin.setRange(0.0, 30.0)
                self.spin_spec_ymin.setSingleStep(0.5)
                self.spin_spec_ymin.setDecimals(1)
                self.spin_spec_ymax.setRange(0.5, 50.0)
                self.spin_spec_ymax.setSingleStep(0.5)
                self.spin_spec_ymax.setDecimals(1)
            else:
                self.spin_spec_ymin.setRange(0.0, 30000.0)
                self.spin_spec_ymin.setSingleStep(500.0)
                self.spin_spec_ymin.setDecimals(0)
                self.spin_spec_ymax.setRange(500.0, 50000.0)
                self.spin_spec_ymax.setSingleStep(500.0)
                self.spin_spec_ymax.setDecimals(0)
            self.spin_spec_ymin.blockSignals(False)
            self.spin_spec_ymax.blockSignals(False)
            self._update_carrier_badge()
        self.spin_spec_ymin.setValue(ymin)
        self.spin_spec_ymax.setValue(ymax)
        self._sync_y_slider_from_ymax(ymax)

    def _preset_focal_band(self):
        carrier = getattr(self, "_carrier_freq", 0.0)
        tol = getattr(self, "spin_carrier_tol", None)
        tol_val = tol.value() if tol else 700.0
        
        if carrier > 0:
            y_min = max(0.0, carrier - tol_val)
            y_max = carrier + tol_val
            if getattr(self, "spec_unit", "kHz") == "kHz":
                self.set_spec_limits(round(y_min / 1000.0, 2), round(y_max / 1000.0, 2), unit="kHz")
            else:
                self.set_spec_limits(y_min, y_max, unit="Hz")
        else:
            win = self.window()
            p = (getattr(win.ctx, "active_heavy_data", {}) if getattr(win, "ctx", None) else {}).get("params", {})
            b1_min = float(p.get("b1_min", 3200))
            b1_max = float(p.get("b1_max", 6000))
            if getattr(self, "spec_unit", "kHz") == "kHz":
                self.set_spec_limits(round(b1_min / 1000.0, 2), round(b1_max / 1000.0, 2), unit="kHz")
            else:
                self.set_spec_limits(b1_min, b1_max, unit="Hz")

    def _preset_full_nyquist(self):
        win = self.window()
        rate = float((getattr(win.ctx, "active_heavy_data", {}) if getattr(win, "ctx", None) else {}).get("rate", 44100.0))
        nyq = rate / 2.0
        if getattr(self, "spec_unit", "kHz") == "kHz":
            self.set_spec_limits(0.0, round(nyq / 1000.0, 1), unit="kHz")
        else:
            self.set_spec_limits(0.0, round(nyq, 0), unit="Hz")

    @staticmethod
    def _ctrl_bar_style(dark=True):
        if dark:
            return """
                QFrame#specCtrlBar, QFrame#freqCtrlBar {
                    background-color: #16181B;
                    border-top: 1px solid #20242B;
                    border-bottom: 1px solid #23272E;
                    padding: 2px 6px;
                }
                QLabel.specCtrlLabel {
                    color: #8E949D;
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                }
                QLabel.specCtrlMuted {
                    color: #7A828E;
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                }
                QLabel.specCtrlSep {
                    color: #555E6B;
                    font-size: 11px;
                    background: transparent;
                    border: none;
                }

                /* Bloco de Escala Y Unificado */
                QFrame#yScaleBox {
                    background-color: #14171A;
                    border: 1px solid #23272F;
                    border-radius: 5px;
                }
                QFrame#yScaleBox:hover {
                    border-color: #38BDF8;
                }
                QFrame#yScaleBox QLabel {
                    background: transparent;
                    border: none;
                }
                QFrame#yScaleBox QDoubleSpinBox, QFrame#yScaleBox QLineEdit {
                    background: transparent;
                    border: none;
                    color: #F0F2F5;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0px;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                }
                QFrame#yScaleBox QDoubleSpinBox:hover, QFrame#yScaleBox QDoubleSpinBox:focus,
                QFrame#yScaleBox QLineEdit:hover, QFrame#yScaleBox QLineEdit:focus {
                    color: #FFFFFF;
                }
                QFrame#yScaleBox QDoubleSpinBox::up-button, QFrame#yScaleBox QDoubleSpinBox::down-button {
                    width: 0px;
                    height: 0px;
                    background: transparent;
                    border: none;
                }
                QComboBox#specUnitCombo, QComboBox.specUnitCombo {
                    background-color: #1C2026;
                    color: #38BDF8;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid #2B323C;
                    border-radius: 3px;
                    padding: 1px 11px 1px 4px;
                    margin: 0px;
                }
                QComboBox#specUnitCombo:hover, QComboBox.specUnitCombo:hover {
                    border-color: #38BDF8;
                    background-color: #232933;
                }
                QComboBox#specUnitCombo::drop-down, QComboBox.specUnitCombo::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: center right;
                    border: none;
                    width: 10px;
                }
                QComboBox#specUnitCombo::down-arrow, QComboBox.specUnitCombo::down-arrow {
                    subcontrol-origin: padding;
                    subcontrol-position: center;
                    image: none;
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid #38BDF8;
                    width: 0;
                    height: 0;
                    margin-right: 2px;
                }
                QComboBox#specUnitCombo QAbstractItemView, QComboBox.specUnitCombo QAbstractItemView {
                    background-color: #16181B;
                    border: 1px solid #282D35;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    color: #E2E8F0;
                    font-size: 10.5px;
                }

                /* Grupo de Presets Segmented Control */
                QFrame#presetGroupBox {
                    background-color: #121519;
                    border: 1px solid #2D333B;
                    border-radius: 5px;
                    padding: 2px;
                }
                QPushButton.segBtn {
                    background-color: #1E232A;
                    color: #CBD5E1;
                    font-size: 10.5px;
                    font-weight: 600;
                    border: 1px solid #333B47;
                    border-radius: 4px;
                    padding: 2px 5px;
                    height: 19px;
                }
                QPushButton.segBtn:hover {
                    background-color: #28303C;
                    border-color: #38BDF8;
                    color: #FFFFFF;
                }
                QPushButton.segBtn[active="true"] {
                    background-color: #2563EB;
                    border: 1px solid #1D4ED8;
                    color: #FFFFFF;
                    font-weight: 700;
                }

                /* Badge da Portadora */
                QLabel.carrierBadge {
                    background-color: rgba(14, 165, 233, 0.12);
                    border: 1px solid rgba(56, 189, 248, 0.28);
                    color: #38BDF8;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: 700;
                }

                /* Tolerância: Valor Monoespaçado */
                QSpinBox.specMonoSpin {
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 3px;
                    color: #F1F5F9;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 1px 2px;
                    min-width: 58px;
                    max-width: 66px;
                }
                QSpinBox.specMonoSpin:hover {
                    background-color: #1A1F26;
                    border: 1px solid #282D35;
                }
                QSpinBox.specMonoSpin:focus {
                    background-color: #1A1F26;
                    border: 1px solid #2563EB;
                }
                QSpinBox.specMonoSpin::up-button, QSpinBox.specMonoSpin::down-button {
                    width: 0px;
                    height: 0px;
                    border: none;
                }

                /* Slider Horizontal */
                QSlider.specSlider {
                    background: transparent;
                    border: none;
                    height: 20px;
                }
                QSlider.specSlider::groove:horizontal {
                    height: 3px;
                    background: rgba(255, 255, 255, 0.12);
                    border: none;
                    border-radius: 1.5px;
                }
                QSlider.specSlider::sub-page:horizontal {
                    background: #2563EB;
                    border-radius: 1.5px;
                }
                QSlider.specSlider::handle:horizontal {
                    background: #38BDF8;
                    border: 1px solid #0284C7;
                    width: 10px;
                    height: 10px;
                    margin: -3.5px 0;
                    border-radius: 5px;
                }
                QSlider.specSlider::handle:horizontal:hover {
                    background: #7DD3FC;
                    border: 1px solid #38BDF8;
                }

                /* Ghost Chips de Atalhos */
                QFrame#chipBox {
                    background: transparent;
                    border: none;
                }
                QPushButton.ghostChip {
                    background-color: #1E232A;
                    color: #F1F5F9;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid #384252;
                    border-radius: 4px;
                    padding: 1px 4px;
                    height: 19px;
                    min-width: 28px;
                }
                QPushButton.ghostChip:hover {
                    background-color: #28303C;
                    border-color: #38BDF8;
                    color: #FFFFFF;
                }
                QPushButton.ghostChip:pressed {
                    background-color: #2563EB;
                    border-color: #1D4ED8;
                    color: #FFFFFF;
                }

                /* Slider Vertical do Eixo Y */
                QSlider#specYSlider {
                    background: transparent;
                    border: none;
                    width: 16px;
                    margin: 4px 0px;
                }
                QSlider#specYSlider::groove:vertical {
                    width: 3px;
                    background: rgba(255, 255, 255, 0.12);
                    border: none;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::sub-page:vertical {
                    background: rgba(255, 255, 255, 0.12);
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::add-page:vertical {
                    background: #2563EB;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::handle:vertical {
                    background: #38BDF8;
                    border: 1px solid #0284C7;
                    width: 10px;
                    height: 10px;
                    margin: 0 -3.5px;
                    border-radius: 5px;
                }
                QSlider#specYSlider::handle:vertical:hover {
                    background: #7DD3FC;
                    border: 1px solid #38BDF8;
                }
            """
        else:
            return """
                QFrame#specCtrlBar, QFrame#freqCtrlBar {
                    background-color: #F8FAFC;
                    border-top: 1px solid #E2E8F0;
                    border-bottom: 1px solid #E2E8F0;
                    padding: 2px 6px;
                }
                QLabel.specCtrlLabel {
                    color: #334155;
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                }
                QLabel.specCtrlMuted {
                    color: #64748B;
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                }
                QLabel.specCtrlSep {
                    color: #CBD5E1;
                    font-size: 11px;
                    background: transparent;
                    border: none;
                }

                /* Bloco de Escala Y Unificado */
                QFrame#yScaleBox {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 5px;
                }
                QFrame#yScaleBox:hover {
                    border-color: #0284C7;
                }
                QFrame#yScaleBox QLabel {
                    background: transparent;
                    border: none;
                }
                QFrame#yScaleBox QDoubleSpinBox, QFrame#yScaleBox QLineEdit {
                    background: transparent;
                    border: none;
                    color: #0F172A;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 0px;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                }
                QFrame#yScaleBox QDoubleSpinBox:hover, QFrame#yScaleBox QDoubleSpinBox:focus,
                QFrame#yScaleBox QLineEdit:hover, QFrame#yScaleBox QLineEdit:focus {
                    color: #0284C7;
                }
                QFrame#yScaleBox QDoubleSpinBox::up-button, QFrame#yScaleBox QDoubleSpinBox::down-button {
                    width: 0px;
                    height: 0px;
                    background: transparent;
                    border: none;
                }
                QComboBox#specUnitCombo, QComboBox.specUnitCombo {
                    background-color: #F1F5F9;
                    color: #0284C7;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid #CBD5E1;
                    border-radius: 3px;
                    padding: 1px 11px 1px 4px;
                    margin: 0px;
                }
                QComboBox#specUnitCombo:hover, QComboBox.specUnitCombo:hover {
                    border-color: #0284C7;
                    background-color: #E2E8F0;
                }
                QComboBox#specUnitCombo::drop-down, QComboBox.specUnitCombo::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: center right;
                    border: none;
                    width: 10px;
                }
                QComboBox#specUnitCombo::down-arrow, QComboBox.specUnitCombo::down-arrow {
                    subcontrol-origin: padding;
                    subcontrol-position: center;
                    image: none;
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid #0284C7;
                    width: 0;
                    height: 0;
                    margin-right: 2px;
                }
                QComboBox#specUnitCombo QAbstractItemView, QComboBox.specUnitCombo QAbstractItemView {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    selection-background-color: #2563EB;
                    selection-color: #FFFFFF;
                    color: #0F172A;
                    font-size: 10.5px;
                }

                /* Grupo de Presets Segmented Control */
                QFrame#presetGroupBox {
                    background-color: #E2E8F0;
                    border: 1px solid #CBD5E1;
                    border-radius: 5px;
                    padding: 2px;
                }
                QPushButton.segBtn {
                    background-color: #FFFFFF;
                    color: #1E293B;
                    font-size: 10.5px;
                    font-weight: 600;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    padding: 2px 5px;
                    height: 19px;
                }
                QPushButton.segBtn:hover {
                    background-color: #F8FAFC;
                    border-color: #0284C7;
                    color: #0284C7;
                }
                QPushButton.segBtn[active="true"] {
                    background-color: #2563EB;
                    border: 1px solid #1D4ED8;
                    color: #FFFFFF;
                    font-weight: 700;
                }

                /* Badge da Portadora */
                QLabel.carrierBadge {
                    background-color: rgba(14, 165, 233, 0.10);
                    border: 1px solid rgba(2, 132, 199, 0.35);
                    color: #0284C7;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: 700;
                }

                /* Tolerância: Valor Monoespaçado */
                QSpinBox.specMonoSpin {
                    background: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 3px;
                    color: #0F172A;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 1px 2px;
                    min-width: 58px;
                    max-width: 66px;
                }
                QSpinBox.specMonoSpin:hover {
                    background-color: #F8FAFC;
                    border: 1px solid #94A3B8;
                }
                QSpinBox.specMonoSpin:focus {
                    background-color: #FFFFFF;
                    border: 1px solid #2563EB;
                }
                QSpinBox.specMonoSpin::up-button, QSpinBox.specMonoSpin::down-button {
                    width: 0px;
                    height: 0px;
                    border: none;
                }

                /* Slider Horizontal */
                QSlider.specSlider {
                    background: transparent;
                    border: none;
                    height: 20px;
                }
                QSlider.specSlider::groove:horizontal {
                    height: 3px;
                    background: rgba(0, 0, 0, 0.12);
                    border: none;
                    border-radius: 1.5px;
                }
                QSlider.specSlider::sub-page:horizontal {
                    background: #2563EB;
                    border-radius: 1.5px;
                }
                QSlider.specSlider::handle:horizontal {
                    background: #0284C7;
                    border: 1px solid #0369A1;
                    width: 10px;
                    height: 10px;
                    margin: -3.5px 0;
                    border-radius: 5px;
                }
                QSlider.specSlider::handle:horizontal:hover {
                    background: #38BDF8;
                }

                /* Ghost Chips de Atalhos */
                QFrame#chipBox {
                    background: transparent;
                    border: none;
                }
                QPushButton.ghostChip {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid #94A3B8;
                    border-radius: 4px;
                    padding: 1px 4px;
                    height: 19px;
                    min-width: 28px;
                }
                QPushButton.ghostChip:hover {
                    background-color: #F1F5F9;
                    border-color: #0284C7;
                    color: #0284C7;
                }
                QPushButton.ghostChip:pressed {
                    background-color: #2563EB;
                    border-color: #1D4ED8;
                    color: #FFFFFF;
                }

                /* Slider Vertical do Eixo Y */
                QSlider#specYSlider {
                    background: transparent;
                    border: none;
                    width: 16px;
                    margin: 4px 0px;
                }
                QSlider#specYSlider::groove:vertical {
                    width: 3px;
                    background: rgba(0, 0, 0, 0.12);
                    border: none;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::sub-page:vertical {
                    background: rgba(0, 0, 0, 0.12);
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::add-page:vertical {
                    background: #2563EB;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::handle:vertical {
                    background: #0284C7;
                    border: 1px solid #0369A1;
                    width: 10px;
                    height: 10px;
                    margin: 0 -3.5px;
                    border-radius: 5px;
                }
                QSlider#specYSlider::handle:vertical:hover {
                    background: #38BDF8;
                }
            """

    def _build_carrier_controls(self, layout):
        self.lbl_carrier_info = QLabel("FP: —")
        self.lbl_carrier_info.setProperty("class", "carrierBadge")
        self.lbl_carrier_info.setToolTip("Frequência Portadora (FP) detectada por densidade modal de chilreios")
        layout.addWidget(self.lbl_carrier_info)

        # Divisor vertical sutil
        layout.addWidget(self._make_vsep())

        self.lbl_tol_ref = QLabel(I18N[self.lang]["filter"] if hasattr(self, "lang") else "Filtro:")
        self.lbl_tol_ref.setProperty("class", "specCtrlMuted")
        layout.addWidget(self.lbl_tol_ref)

        self.slider_carrier_tol = QSlider(Qt.Orientation.Horizontal)
        self.slider_carrier_tol.setProperty("class", "specSlider")
        self.slider_carrier_tol.setRange(25, 1500)
        self.slider_carrier_tol.setSingleStep(25)
        self.slider_carrier_tol.setValue(700)
        self.slider_carrier_tol.setFixedWidth(50)
        self.slider_carrier_tol.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_carrier_tol.setToolTip("Arraste para regular a tolerância espectral em tempo real")
        self.slider_carrier_tol.valueChanged.connect(self._on_carrier_tol_slider_changed)
        layout.addWidget(self.slider_carrier_tol)

        self.spin_carrier_tol = QSpinBox()
        self.spin_carrier_tol.setProperty("class", "specMonoSpin")
        self.spin_carrier_tol.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.spin_carrier_tol.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_carrier_tol.setRange(25, 2000)
        self.spin_carrier_tol.setSingleStep(25)
        self.spin_carrier_tol.setValue(700)
        self.spin_carrier_tol.setPrefix("±")
        self.spin_carrier_tol.setSuffix(" Hz")
        self.spin_carrier_tol.setFixedWidth(54)
        self.spin_carrier_tol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_carrier_tol.setToolTip("Tolerância espectral em torno da frequência portadora (tempo real)")
        self.spin_carrier_tol.valueChanged.connect(self._on_carrier_tol_spin_changed)
        layout.addWidget(self.spin_carrier_tol)

        self.chip_box = QFrame()
        self.chip_box.setObjectName("chipBox")
        self.chip_box.setStyleSheet("background: transparent; border: none;")
        chip_layout = QHBoxLayout(self.chip_box)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(2)

        for tol_val in (300, 500, 700, 1000):
            btn_chip = QPushButton(f"±{tol_val}")
            btn_chip.setProperty("class", "ghostChip")
            btn_chip.setFixedHeight(20)
            btn_chip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_chip.setToolTip(f"Ajustar tolerância para ±{tol_val} Hz")
            btn_chip.clicked.connect(lambda checked=False, v=tol_val: self.set_carrier_tolerance(v))
            chip_layout.addWidget(btn_chip)

        layout.addWidget(self.chip_box)

    def _on_carrier_tol_spin_changed(self, val):
        if hasattr(self, "slider_carrier_tol") and self.slider_carrier_tol.value() != val:
            self.slider_carrier_tol.blockSignals(True)
            self.slider_carrier_tol.setValue(val)
            self.slider_carrier_tol.blockSignals(False)
        self._notify_carrier_tol_changed(val)

    def _on_carrier_tol_slider_changed(self, val):
        if hasattr(self, "spin_carrier_tol") and self.spin_carrier_tol.value() != val:
            self.spin_carrier_tol.blockSignals(True)
            self.spin_carrier_tol.setValue(val)
            self.spin_carrier_tol.blockSignals(False)
        self._notify_carrier_tol_changed(val)

    def _notify_carrier_tol_changed(self, val):
        self.freq_tolerance_changed.emit(val, self)

    def set_carrier_info(self, carrier_freq, tol_hz=None):
        self._carrier_freq = float(carrier_freq) if carrier_freq else 0.0
        self._update_carrier_badge()
        if tol_hz is not None:
            self.set_carrier_tolerance(int(tol_hz), notify=False)
            
            if self._carrier_freq > 0.0 and hasattr(self, "spin_spec_ymin") and hasattr(self, "spin_spec_ymax"):
                unit = getattr(self, "spec_unit", "kHz")
                ymin = max(0.0, self._carrier_freq - tol_hz)
                ymax = self._carrier_freq + tol_hz
                if unit == "kHz":
                    ymin /= 1000.0
                    ymax /= 1000.0
                
                self.spin_spec_ymin.blockSignals(True)
                self.spin_spec_ymax.blockSignals(True)
                self.spin_spec_ymin.setValue(ymin)
                self.spin_spec_ymax.setValue(ymax)
                self.spin_spec_ymin.blockSignals(False)
                self.spin_spec_ymax.blockSignals(False)

    def _update_carrier_badge(self):
        if not hasattr(self, "lbl_carrier_info"):
            return
        fc = getattr(self, "_carrier_freq", 0.0)
        unit = getattr(self, "spec_unit", "kHz")
        t = I18N[getattr(self, "lang", "pt")]
        if fc and fc > 0:
            if unit == "kHz":
                self.lbl_carrier_info.setText(f"FP: {fc / 1000.0:.2f} kHz")
            else:
                self.lbl_carrier_info.setText(f"FP: {fc:.0f} Hz")
            self.lbl_carrier_info.setToolTip(t["carrier_info_tt_detected"].format(fc=fc))
        else:
            self.lbl_carrier_info.setText("FP: —")
            self.lbl_carrier_info.setToolTip(t["carrier_info_tt_none"])

    def set_carrier_tolerance(self, val, notify=True):
        val = int(val)
        if hasattr(self, "spin_carrier_tol"):
            self.spin_carrier_tol.blockSignals(True)
            self.spin_carrier_tol.setValue(val)
            self.spin_carrier_tol.blockSignals(False)
        if hasattr(self, "slider_carrier_tol"):
            self.slider_carrier_tol.blockSignals(True)
            self.slider_carrier_tol.setValue(val)
            self.slider_carrier_tol.blockSignals(False)
        if notify:
            self._notify_carrier_tol_changed(val)




class TimelineWidget(QWidget):
    """Régua de reprodução/inspeção com ticks, timestamps e flags de chilreios."""
    def __init__(self, position_callback, parent=None):
        super().__init__(parent)
        self.position_callback = position_callback
        self.duration = 0.0
        self.position = 0.0
        self.markers = []
        self.is_dragging = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(92)
        self.setMaximumHeight(104)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def set_data(self, duration, markers):
        self.duration = max(0.0, float(duration or 0.0))
        self.markers = list(markers or [])
        self.update()

    def set_position(self, seconds):
        if not self.is_dragging:
            self.position = max(0.0, min(float(seconds), self.duration or 0.0))
            self.update()

    def _x_for(self, seconds, left, right):
        if self.duration <= 0:
            return left
        return left + (right - left) * (seconds / self.duration)

    def _seconds_from_event(self, event):
        left, right = 18, max(19, self.width() - 18)
        if hasattr(event, "pos"):
            ex = float(event.pos().x())
        elif hasattr(event, "position"):
            ex = float(event.position().x())
        else:
            ex = float(getattr(event, "x", lambda: 0)())

        ratio = max(0.0, min(1.0, (ex - left) / max(1.0, float(right - left))))
        return ratio * self.duration

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.duration > 0:
            self.is_dragging = True
            sec = self._seconds_from_event(event)
            self.position = sec
            self.update()
            if self.position_callback:
                self.position_callback(sec * 1000.0, is_final=False)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.duration > 0:
            sec = self._seconds_from_event(event)
            self.position = sec
            self.update()
            if self.position_callback:
                self.position_callback(sec * 1000.0, is_final=False)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging and self.duration > 0:
                sec = self._seconds_from_event(event)
                self.position = sec
                self.update()
                if self.position_callback:
                    self.position_callback(sec * 1000.0, is_final=True)
            self.is_dragging = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        dark = getattr(self.window(), "theme_mode", "dark") == "dark"
        bg = QColor("#111214") if dark else QColor("#F7F9FB")
        rail = QColor("#363A41") if dark else QColor("#C9D0D7")
        major = QColor("#A0A5AE") if dark else QColor("#64707C")
        minor = QColor("#353940") if dark else QColor("#D8DEE4")
        text = QColor("#8F949D") if dark else QColor("#65707A")
        left, right = 18, max(19, self.width() - 18)
        ruler_y = 45

        # trilho principal
        p.setPen(rail)
        p.drawLine(left, ruler_y, right, ruler_y)

        if self.duration <= 0:
            p.setPen(text)
            p.drawText(18, 20, "0.00")
            p.end()
            return

        # ticks finos a cada 1s e ticks principais a cada 10s
        major_step = 10.0
        if self.duration < 30:
            major_step = 5.0
        elif self.duration > 180:
            major_step = 20.0

        sec = 0.0
        while sec <= self.duration + 1e-6:
            x = self._x_for(sec, left, right)
            is_major = abs((sec / major_step) - round(sec / major_step)) < 1e-5
            tick_h = 11 if is_major else 5
            p.setPen(major if is_major else minor)
            p.drawLine(int(x), ruler_y-tick_h, int(x), ruler_y+2)
            if is_major:
                p.setPen(major)
                label = self._format_time(sec)
                p.drawText(int(x)-28, 72, 56, 14, Qt.AlignmentFlag.AlignCenter, label)
            sec += 1.0

        # faixa discreta de progresso
        progress_x = self._x_for(self.position, left, right)
        p.setPen(QColor("#3B8EDB"))
        p.drawLine(left, ruler_y, int(progress_x), ruler_y)

        # flags dos eventos analisados
        for idx, marker in enumerate(self.markers):
            t = marker.get("time", 0.0) if isinstance(marker, dict) else float(marker)
            color = marker.get("color", "#F0A54A") if isinstance(marker, dict) else ("#F0A54A" if idx % 2 == 0 else "#4D9DE0")
            x = int(self._x_for(t, left, right))
            p.setPen(QColor(color))
            p.setBrush(QColor(color))
            p.drawLine(x, 15, x, ruler_y)
            pts = QPolygonF([QPointF(x, 14), QPointF(x+9, 18), QPointF(x+9, 27), QPointF(x, 31)])
            p.drawPolygon(pts)

        # Cursor de reprodução com contorno de alto contraste (visível mesmo sob alta densidade de marcadores)
        cursor_x = float(progress_x)

        # 1. Halo de contraste escuro para separar o cursor de qualquer fundo ou marcação alaranjada
        pen_halo = QPen(QColor(15, 23, 42, 230), 4.0)
        pen_halo.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_halo)
        p.drawLine(QPointF(cursor_x, 4), QPointF(cursor_x, 80))

        # Contorno escuro para o cabeçote superior
        head_halo = QPolygonF([
            QPointF(cursor_x - 6.5, 2.0),
            QPointF(cursor_x + 6.5, 2.0),
            QPointF(cursor_x + 6.5, 10.0),
            QPointF(cursor_x, 16.5),
            QPointF(cursor_x - 6.5, 10.0)
        ])
        p.setBrush(QColor(15, 23, 42, 230))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(head_halo)

        # Contorno escuro para o pé/base inferior
        base_halo = QPolygonF([
            QPointF(cursor_x, 70.5),
            QPointF(cursor_x + 5.5, 79.5),
            QPointF(cursor_x - 5.5, 79.5)
        ])
        p.drawPolygon(base_halo)

        # 2. Agulha central em branco puro com 2.0px de espessura
        pen_core = QPen(QColor("#FFFFFF"), 2.0)
        pen_core.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_core)
        p.drawLine(QPointF(cursor_x, 5), QPointF(cursor_x, 79))

        # 3. Cabeçote superior preenchido em azul ciano vibrante (#38BDF8) com borda branca
        head_core = QPolygonF([
            QPointF(cursor_x - 5.0, 3.5),
            QPointF(cursor_x + 5.0, 3.5),
            QPointF(cursor_x + 5.0, 9.5),
            QPointF(cursor_x, 15.0),
            QPointF(cursor_x - 5.0, 9.5)
        ])
        p.setBrush(QColor("#38BDF8"))
        p.setPen(QPen(QColor("#FFFFFF"), 1.2))
        p.drawPolygon(head_core)

        # Ponto focal interno branco no cabeçote
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cursor_x, 7.0), 1.8, 1.8)

        # 4. Marcador inferior (base) com borda branca
        base_core = QPolygonF([
            QPointF(cursor_x, 72.5),
            QPointF(cursor_x + 4.0, 78.0),
            QPointF(cursor_x - 4.0, 78.0)
        ])
        p.setBrush(QColor("#38BDF8"))
        p.setPen(QPen(QColor("#FFFFFF"), 1.0))
        p.drawPolygon(base_core)

        p.setPen(text)
        # Tempo corrente e duração ficam na faixa inferior, separados das flags.
        p.setPen(text)
        p.drawText(18, 88, 74, 14, Qt.AlignmentFlag.AlignLeft, self._format_time(self.position) )
        p.drawText(right-74, 88, 74, 14, Qt.AlignmentFlag.AlignRight, self._format_time(self.duration) )
        p.end()

    @staticmethod
    def _format_time(seconds):
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        secs = seconds - minutes * 60
        return f"{minutes:02d}:{secs:05.2f}"




class AudioTransportPanel(QFrame):
    """Painel de controles de transporte de áudio (Play, Velocidade, Volume e Timeline). FASE 6."""
    
    play_toggled = pyqtSignal()
    speed_cycled = pyqtSignal()
    volume_changed = pyqtSignal(int)
    position_seeked = pyqtSignal(float, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transportTimelineCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(2)
        
        # CONTROLES DE REPRODUÇÃO
        self.playback_card = QFrame()
        self.playback_card.setObjectName("playbackCard")
        self.playback_card.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        root_play = QVBoxLayout(self.playback_card)
        root_play.setContentsMargins(14, 5, 14, 5)
        root_play.setSpacing(0)
        
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addStretch(2)

        self.btn_speed = self._transport_button("1×", "Reduzir velocidade de reprodução")
        self.btn_speed.setObjectName("speedButton")
        self.btn_speed.setFixedSize(50, 38)
        self.btn_speed.clicked.connect(self.speed_cycled.emit)
        row.addWidget(self.btn_speed, 0, Qt.AlignmentFlag.AlignVCenter)

        center = QWidget()
        center.setObjectName("playCenter")
        center.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(0, 0, 0, 0)
        center_l.setSpacing(0)
        center_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_play = self._transport_button("", "Reproduzir", play=True)
        self.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_play.setAutoDefault(False)
        self.btn_play.setDefault(False)
        self.btn_play.setFlat(True)
        self.btn_play.setFixedSize(46, 46)
        self.btn_play.setIconSize(QSize(19, 19))
        self.btn_play.setIcon(make_ui_icon("play", color="#FFFFFF", size=19))
        self.btn_play.clicked.connect(self.play_toggled.emit)
        center_l.addWidget(self.btn_play, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_elapsed = QLabel("00:00.00 / 00:00.00")
        self.lbl_elapsed.setObjectName("elapsedLabel")
        self.lbl_elapsed.setFixedWidth(138)
        self.lbl_elapsed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_l.addWidget(self.lbl_elapsed, 0, Qt.AlignmentFlag.AlignCenter)
        
        row.addWidget(center, 0, Qt.AlignmentFlag.AlignVCenter)

        self.volume_cluster = QWidget()
        self.volume_cluster.setObjectName("volumeCluster")
        self.volume_cluster.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        vol_l = QHBoxLayout(self.volume_cluster)
        vol_l.setContentsMargins(0, 0, 0, 0)
        vol_l.setSpacing(6)
        
        self.lbl_volume = QLabel()
        self.lbl_volume.setObjectName("volumeLabel")
        self.lbl_volume.setPixmap(make_ui_icon("volume", size=16).pixmap(16, 16))
        self.lbl_volume.setFixedSize(18, 18)
        vol_l.addWidget(self.lbl_volume)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        vol_l.addWidget(self.volume_slider)
        
        row.addWidget(self.volume_cluster, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(2)
        root_play.addLayout(row)

        self.layout.addWidget(self.playback_card)
        
        self.timeline = TimelineWidget(self._on_timeline_seek)
        self.layout.addWidget(self.timeline)

    def _transport_button(self, text, tooltip, play=False, checkable=False):
        b = QPushButton(text)
        b.setObjectName("playButton" if play else "transport")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tooltip)
        if checkable:
            b.setCheckable(True)
        if not play:
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return b
        
    def _on_timeline_seek(self, position_ms, is_final=False):
        self.position_seeked.emit(position_ms, is_final)
        
    def set_play_icon(self, icon_name, icon_color):
        self.btn_play.setIcon(make_ui_icon(icon_name, color=icon_color, size=19))
        self.btn_play.setToolTip("Pausar" if icon_name == "pause" else "Reproduzir")
        
    def set_speed_text(self, text, tooltip):
        self.btn_speed.setText(text)
        self.btn_speed.setToolTip(tooltip)
        
    def set_elapsed_text(self, text):
        self.lbl_elapsed.setText(text)
        
    def set_play_enabled(self, enabled):
        self.btn_play.setEnabled(enabled)
