"""
Crinômetro - Painéis Gráficos e Timeline Interativa.
"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QPointF
from PyQt6.QtGui import QPainter, QColor, QPolygonF, QPen
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.i18n import I18N
from utils.icons import make_ui_icon


class PlotTitleBar(QWidget):
    """Barra de título da mini janela com suporte a arrastar e soltar (drag to reorder)."""
    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.panel = panel
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            dy = event.pos().y() - self._drag_start_pos.y()
            if dy > 35:  # Arrastou para baixo
                self._drag_start_pos = event.pos()
                win = self.window()
                if hasattr(win, "move_stack_panel"):
                    win.move_stack_panel(self.panel, 1)
            elif dy < -35:  # Arrastou para cima
                self._drag_start_pos = event.pos()
                win = self.window()
                if hasattr(win, "move_stack_panel"):
                    win.move_stack_panel(self.panel, -1)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)


class PlotPanel(QFrame):
    """Mini janela / Card de gráfico com cantos arredondados e suporte a reordenação."""
    def __init__(self, title_key, lang, expand_callback, main=False):
        super().__init__()
        self.title_key = title_key
        self.expand_callback = expand_callback
        self.pulse_edit_mode = False

        self.setObjectName("plotCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 4)
        self.layout.setSpacing(0)

        self.title_bar = PlotTitleBar(self)
        self.title_bar.setObjectName("plotTitleBar")
        self.title_bar.setCursor(Qt.CursorShape.OpenHandCursor)
        self.title_bar.setToolTip("Arraste esta barra para reordenar as mini janelas ou use os botões ▲ e ▼")
        bar = QHBoxLayout(self.title_bar)
        bar.setContentsMargins(12, 6, 8, 6)
        bar.setSpacing(4)

        self.lbl_title = QLabel(I18N[lang][title_key])
        self.lbl_title.setObjectName("plotTitle")
        bar.addWidget(self.lbl_title)
        bar.addStretch()

        # Botões para reordenar / trocar a posição da mini janela na pilha lateral
        self.btn_move_up = self._tool_button("▲", "Mover esta mini janela para cima")
        self.btn_move_up.setObjectName("plotTool")
        self.btn_move_up.clicked.connect(lambda: self._on_move_clicked(-1))
        bar.addWidget(self.btn_move_up)

        self.btn_move_down = self._tool_button("▼", "Mover esta mini janela para baixo")
        self.btn_move_down.setObjectName("plotTool")
        self.btn_move_down.clicked.connect(lambda: self._on_move_clicked(1))
        bar.addWidget(self.btn_move_down)

        # Botão de edição de pulsos (ativa/desativa modo de seleção)
        self.btn_pulse_edit = self._tool_button("", "Ativar modo de edição de pulsos (clique para adicionar/remover)")
        self.btn_pulse_edit.setObjectName("plotTool")
        self.btn_pulse_edit.setIcon(make_ui_icon("pencil", color="#D7DCE2", size=15))
        self.btn_pulse_edit.setIconSize(QSize(14, 14))
        self.btn_pulse_edit.setCheckable(True)
        self.btn_pulse_edit.toggled.connect(self._toggle_pulse_edit_mode)
        bar.addWidget(self.btn_pulse_edit)

        self.btn_pulse_undo = self._tool_button("↶", "Desfazer última edição de pulso")
        self.btn_pulse_undo.setEnabled(False)
        self.btn_pulse_undo.clicked.connect(
            lambda: self.window()._undo_pulse_edit()
            if hasattr(self.window(), "_undo_pulse_edit") else None
        )
        bar.addWidget(self.btn_pulse_undo)

        # Ações do gráfico: somente maximizar/restaurar, que possui comportamento real.
        self.btn_expand = self._tool_button("", "Colocar este gráfico na posição principal")
        self.btn_expand.setObjectName("plotMaximize")
        self.btn_expand.setIcon(make_ui_icon("maximize", color="#D7DCE2", size=15))
        self.btn_expand.setIconSize(QSize(14, 14))
        self.btn_expand.clicked.connect(lambda: self.expand_callback(self))
        bar.addWidget(self.btn_expand)

        self.figure = Figure(facecolor="none")
        self.figure.patch.set_alpha(0.0)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setStyleSheet("background: transparent; border: 0; padding: 0; margin: 0;")
        self.ax = self.figure.add_subplot(111, facecolor="#101214")
        self.apply_dark_theme()

        self.layout.addWidget(self.title_bar)
        self.layout.addWidget(self.canvas, 1)

        self._set_main_visual(main)

    def _tool_button(self, glyph, tooltip):
        b = QPushButton(glyph)
        b.setFlat(True)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setToolTip(tooltip)
        b.setFixedSize(28, 26)
        b.setObjectName("plotTool")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _toggle_pulse_edit_mode(self, checked):
        """Ativa/desativa o modo de edição de pulsos para este painel."""
        self.pulse_edit_mode = checked
        parent = self.window()
        if hasattr(parent, '_update_pulse_edit_buttons'):
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

    def set_main(self, main):
        self._set_main_visual(main)
        self.btn_expand.setToolTip(
            "Restaurar posição" if main else "Colocar este gráfico na posição principal"
        )
        if hasattr(self, "btn_move_up"):
            self.btn_move_up.setVisible(not main)
        if hasattr(self, "btn_move_down"):
            self.btn_move_down.setVisible(not main)

    def update_lang(self, lang):
        self.lbl_title.setText(I18N[lang][self.title_key])

    def apply_dark_theme(self):
        dark = getattr(self.window(), "theme_mode", "dark") == "dark"
        fg = "#A9ADB5" if dark else "#59616B"
        spine = "#2A2D32" if dark else "#D7DDE3"
        grid = "#25282D" if dark else "#DDE2E7"
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
        self.btn_pulse_edit.setIcon(make_ui_icon("pencil", color=icon_color, size=15))
        self.btn_expand.setIcon(make_ui_icon("maximize", color=icon_color, size=15))
        if hasattr(self, "btn_move_up"):
            self.btn_move_up.setStyleSheet(f"QPushButton {{ color: {icon_color}; background: transparent; border: 0; font-size: 11px; font-weight: bold; padding: 0; }} QPushButton:hover {{ background: rgba(255,255,255,0.12); border-radius: 4px; }}")
        if hasattr(self, "btn_move_down"):
            self.btn_move_down.setStyleSheet(f"QPushButton {{ color: {icon_color}; background: transparent; border: 0; font-size: 11px; font-weight: bold; padding: 0; }} QPushButton:hover {{ background: rgba(255,255,255,0.12); border-radius: 4px; }}")



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

        # cursor branco
        cursor_x = int(progress_x)
        p.setPen(QColor("#F2F3F5"))
        p.drawLine(cursor_x, 7, cursor_x, 78)
        p.setBrush(QColor("#F2F3F5"))
        p.drawRoundedRect(cursor_x-4, 5, 8, 7, 2, 2)

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


