"""
Crinômetro - Widgets Visuais Customizados.
"""
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from utils.icons import make_ui_icon, make_spinner_icon

class ButtonSpinner:
    """Controlador de animação de carregamento e spinner diretamente dentro de um QPushButton."""
    def __init__(self, button, active_text=None):
        self.button = button
        self.active_text = active_text
        self.original_text = button.text()
        self.original_icon = button.icon()
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate)

    def start(self, text=None):
        self.original_text = self.button.text()
        self.original_icon = self.button.icon()
        if text:
            self.button.setText(text)
        elif self.active_text:
            self.button.setText(self.active_text)
        self.button.setEnabled(False)
        self.angle = 0
        self.timer.start(50)
        self._rotate()

    def _rotate(self):
        self.angle = (self.angle - 30) % 360
        self.button.setIcon(make_spinner_icon(self.angle, color="#FFFFFF", size=17))

    def stop(self, restore_icon=None, restore_text=None):
        self.timer.stop()
        self.button.setText(restore_text if restore_text is not None else self.original_text)
        if restore_icon is not None:
            self.button.setIcon(restore_icon)
        else:
            self.button.setIcon(self.original_icon)
        self.button.setEnabled(True)



class ThemeToggle(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setChecked(False)
        self.setStyleSheet("QCheckBox{background:transparent;border:0;} QCheckBox::indicator{width:44px;height:22px;border:0;background:transparent;}" )
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        dark=getattr(self.window(),'theme_mode','dark')=='dark'
        track=QColor('#2A2E33' if dark else '#D6DDE4'); active=QColor('#2E8ED8'); border=QColor('#444A52' if dark else '#B8C1CA')
        p.setPen(QPen(border,1)); p.setBrush(active if self.isChecked() else track); p.drawRoundedRect(QRectF(1,1,44,22),11,11)
        x=33 if self.isChecked() else 13
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#FFFFFF')); p.drawEllipse(QRectF(x-8,4,16,16)); p.end()



class LoadingScreen(QWidget):
    """Tela inicial sem moldura que reproduz loading.mp4 antes da janela principal."""
    def __init__(self, parent=None, finish_callback=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.finish_callback = finish_callback
        self.setStyleSheet("background: #0D0F11;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video = QVideoWidget(self)
        self.video.setStyleSheet("background: transparent; border: 0;")
        layout.addWidget(self.video)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.setVideoOutput(self.video)

        self.player.mediaStatusChanged.connect(self._on_media_status)
        if hasattr(self.player, "errorOccurred"):
            self.player.errorOccurred.connect(self._on_error)
        elif hasattr(self.player, "error"):
            self.player.error.connect(self._on_error)

        self._fallback = QTimer(self)
        self._fallback.setSingleShot(True)
        self._fallback.timeout.connect(self.finish)

        self._finished = False

        # Loading Spinner discreto no canto inferior direito (fundo branco do vídeo com spinner preto ~90% opaco)
        self.lbl_spinner = QLabel(self)
        self.lbl_spinner.setFixedSize(32, 32)
        self.lbl_spinner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.lbl_spinner.setStyleSheet("background: transparent; border: none;")
        self.spinner_angle = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._rotate_launcher_spinner)
        self.spinner_timer.start(40)

        video_path = self._asset_path("loading.mp4")
        if os.path.exists(video_path):
            self.player.setSource(QUrl.fromLocalFile(video_path))
            self.player.play()
            self._fallback.start(15000)
        else:
            self.finish()

        self._center_on_screen()

    @staticmethod
    def _asset_path(filename):
        # PyInstaller --onefile extrai --add-data para _MEIPASS.
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, filename)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(640, 360)
            return
        available = screen.availableGeometry()
        # 16:9, ocupando no máximo ~70% da tela para manter aspecto de splash.
        w = min(900, int(available.width() * 0.70))
        h = int(w * 9 / 16)
        if h > int(available.height() * 0.70):
            h = int(available.height() * 0.70)
            w = int(h * 16 / 9)
        self.resize(max(480, w), max(270, h))
        geo = self.geometry()
        geo.moveCenter(available.center())
        self.setGeometry(geo)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "lbl_spinner"):
            margin = 16
            self.lbl_spinner.move(self.width() - self.lbl_spinner.width() - margin,
                                  self.height() - self.lbl_spinner.height() - margin)
            self.lbl_spinner.raise_()

    def _rotate_launcher_spinner(self):
        self.spinner_angle = (self.spinner_angle - 25) % 360
        icon = make_spinner_icon(self.spinner_angle, color="#000000E6", size=22)
        self.lbl_spinner.setPixmap(icon.pixmap(22, 22))

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.finish()

    def _on_error(self, *args):
        self.finish()

    def finish(self):
        if self._finished:
            return
        self._finished = True
        if hasattr(self, "spinner_timer"):
            self.spinner_timer.stop()
        self._fallback.stop()
        self.player.stop()
        callback = self.finish_callback
        self.finish_callback = None
        self.close()
        if callback:
            QTimer.singleShot(0, callback)



class AudioListItemWidget(QWidget):
    """Widget para item da lista de áudios contendo:
    - Um card clicável com o nome do áudio (com efeito hover e seleção ativa).
    - Fora do card, no canto direito: a caixinha de seleção (azul quando marcada) e o botão de lixeira.
    """
    def __init__(self, filename, is_checked=False, is_active=False, on_toggle=None, on_delete=None, on_select=None, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.on_delete = on_delete
        self.on_toggle = on_toggle
        self.on_select = on_select

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(6)

        # 1. Card de clique / hover do áudio (exclusivo para o nome do arquivo)
        self.card = QFrame()
        self.card.setObjectName("audioFileCard")
        self.card.setProperty("active", is_active)
        self.card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(8, 4, 8, 4)
        card_layout.setSpacing(6)

        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(make_ui_icon("play", color="#8B949E", size=10).pixmap(10, 10))
        self.lbl_icon.setStyleSheet("background: transparent; border: 0;")
        card_layout.addWidget(self.lbl_icon)

        self.lbl_name = QLabel(filename)
        self.lbl_name.setObjectName("audioFileName")
        self.lbl_name.setToolTip(filename)
        self.lbl_name.setStyleSheet("background: transparent; border: 0;")
        card_layout.addWidget(self.lbl_name, 1)

        main_layout.addWidget(self.card, 1)

        # 2. Área no canto direito (FORA do card de clique/hover do áudio)
        self.actions_widget = QWidget()
        self.actions_widget.setStyleSheet("background: transparent; border: 0;")
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)

        # Caixinha de marcar (fica azul quando selecionada)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_checked)
        self.checkbox.setToolTip("Marcar para análise em lote e relatório")
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.stateChanged.connect(self._on_check_changed)
        actions_layout.addWidget(self.checkbox)

        # Botão com ícone de lixeira para remover o áudio
        self.btn_trash = QPushButton()
        self.btn_trash.setFixedSize(22, 22)
        self.btn_trash.setFlat(True)
        self.btn_trash.setIcon(make_ui_icon("trash", color="#8B949E", size=14))
        self.btn_trash.setToolTip(f"Remover {filename} da lista")
        self.btn_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trash.setStyleSheet("""
            QPushButton { background: transparent; border: 0; border-radius: 4px; padding: 2px; }
            QPushButton:hover { background: rgba(239, 68, 68, 0.25); }
        """)
        self.btn_trash.clicked.connect(self._on_delete_clicked)
        actions_layout.addWidget(self.btn_trash)

        main_layout.addWidget(self.actions_widget, 0)

        # Evento de clique no card para selecionar o áudio
        self.card.mousePressEvent = self._on_card_clicked

    def set_loading(self, is_loading):
        """Ativa ou desativa a animação de spinner no ícone do arquivo na lista."""
        if is_loading:
            if not hasattr(self, '_loading_timer'):
                self._loading_timer = QTimer(self)
                self._loading_timer.timeout.connect(self._rotate_item_spinner)
                self._loading_angle = 0
            self._loading_timer.start(50)
            self._rotate_item_spinner()
        else:
            if hasattr(self, '_loading_timer'):
                self._loading_timer.stop()
            self.lbl_icon.setPixmap(make_ui_icon("play", color="#8B949E", size=10).pixmap(10, 10))

    def _rotate_item_spinner(self):
        self._loading_angle = (self._loading_angle - 30) % 360
        self.lbl_icon.setPixmap(make_spinner_icon(self._loading_angle, color="#3B82F6", size=11).pixmap(11, 11))

    def _on_card_clicked(self, event):
        if self.on_select:
            self.on_select(self.filename)

    def set_active(self, active):
        self.card.setProperty("active", bool(active))
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)
        self.lbl_name.style().unpolish(self.lbl_name)
        self.lbl_name.style().polish(self.lbl_name)

    def is_checked(self):
        return self.checkbox.isChecked()

    def set_checked(self, checked):
        self.checkbox.setChecked(checked)

    def _on_check_changed(self, state):
        if self.on_toggle:
            self.on_toggle(self.filename, state == Qt.CheckState.Checked.value or state == 2 or state is True)

    def _on_delete_clicked(self):
        if self.on_delete:
            self.on_delete(self.filename)



