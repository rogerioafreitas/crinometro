import os
import sys
from PyQt5.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QVideoWidget

RATE = 1.15


def asset_path(filename: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def center(widget: QWidget, width=900, height=506):
    screen = QApplication.primaryScreen()
    if not screen:
        widget.resize(width, height)
        return
    area = screen.availableGeometry()
    w = min(width, area.width())
    h = min(height, area.height())
    widget.resize(w, h)
    geo = widget.geometry()
    geo.moveCenter(area.center())
    widget.setGeometry(geo)


class CoreLoaderThread(QThread):
    loaded = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            import scipy.special
            import scipy.integrate
            import crinometro
            self.loaded.emit()
        except Exception as e:
            import traceback
            self.error.emit(traceback.format_exc())


class Launcher(QWidget):
    SAFETY_TIMEOUT_MS = 120_000

    def __init__(self):
        super().__init__()

        self.core_ready = False
        self.loaded_playing = False
        self.finished = False
        self.main_window = None

        self.setObjectName("Launcher")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setStyleSheet("""
            QWidget#Launcher {
                background: #FFFFFF;
                border: 1px solid #D7DCE1;
                border-radius: 10px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        host = QWidget(self)
        host.setStyleSheet("background:#FFFFFF; border:0;")
        root.addWidget(host)
        self.host = host

        self.loading_video = QVideoWidget(host)
        self.loaded_video = QVideoWidget(host)

        for video in (self.loading_video, self.loaded_video):
            video.setStyleSheet("background:#FFFFFF; border:0;")
            video.setAspectRatioMode(Qt.KeepAspectRatio)

        self.loaded_video.hide()
        self.loading_video.show()

        # Loading Player
        self.loading_player = QMediaPlayer(self)
        self.loading_player.setVolume(0)
        self.loading_player.setVideoOutput(self.loading_video)
        self.loading_player.setPlaybackRate(RATE)

        # Loaded Player
        self.loaded_player = QMediaPlayer(self)
        self.loaded_player.setVolume(100)
        self.loaded_player.setVideoOutput(self.loaded_video)
        self.loaded_player.setPlaybackRate(RATE)
        self.loaded_player.mediaStatusChanged.connect(self._on_loaded_media_status)
        self.loaded_player.positionChanged.connect(self._on_loaded_position_changed)

        self.safety_timer = QTimer(self)
        self.safety_timer.setSingleShot(True)
        self.safety_timer.timeout.connect(self._safety_timeout)

        center(self)
        self._resize_videos()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_videos()

    def _resize_videos(self):
        if not hasattr(self, "host"):
            return
        self.host.setGeometry(1, 1, self.width() - 2, self.height() - 2)
        rect = self.host.rect()
        self.loading_video.setGeometry(rect)
        self.loaded_video.setGeometry(rect)

    def start(self):
        loading = asset_path("loading.mp4")
        loaded = asset_path("loaded.mp4")

        if not os.path.isfile(loading):
            raise FileNotFoundError(f"loading.mp4 não encontrado: {loading}")
        if not os.path.isfile(loaded):
            raise FileNotFoundError(f"loaded.mp4 não encontrado: {loaded}")

        self.loaded_path = loaded

        # Inicia reprodução do loading em loop
        self.loading_playlist = QMediaPlaylist(self)
        self.loading_playlist.addMedia(QMediaContent(QUrl.fromLocalFile(loading)))
        self.loading_playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.loading_player.setPlaylist(self.loading_playlist)
        self.loading_player.setVolume(0)
        self.loading_player.play()

        # Inicia thread de carregamento dos módulos
        self.loader_thread = CoreLoaderThread()
        self.loader_thread.loaded.connect(self._on_core_loaded)
        self.loader_thread.error.connect(self._on_core_error)
        self.loader_thread.start()

        self.safety_timer.start(self.SAFETY_TIMEOUT_MS)

    def _on_core_loaded(self):
        if self.finished:
            return
        try:
            import crinometro
            self.main_window = crinometro.MainWindow()
            self.core_ready = True
            self._switch_to_loaded()
        except Exception as e:
            import traceback
            self._on_core_error(traceback.format_exc())

    def _on_core_error(self, err_trace: str):
        print(f"Erro ao carregar Crinômetro:\n{err_trace}")
        self.finished = True
        try:
            self.loading_player.stop()
            self.loaded_player.stop()
        except Exception:
            pass
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Erro de Inicialização - Crinômetro")
        msg.setText("Ocorreu um erro ao carregar o aplicativo:")
        msg.setDetailedText(err_trace)
        msg.exec_()
        self.close()
        QApplication.quit()

    def _switch_to_loaded(self):
        if self.loaded_playing or self.finished:
            return
        self.loaded_playing = True

        try:
            self.loading_player.stop()
        except Exception:
            pass

        self.loading_video.hide()
        self.loaded_video.show()
        self.loaded_video.raise_()

        self.loaded_player.setMedia(QMediaContent(QUrl.fromLocalFile(self.loaded_path)))
        self.loaded_player.setVolume(100)
        self.loaded_player.play()

    def _on_loaded_media_status(self, status):
        if not self.loaded_playing or self.finished:
            return
        if status == QMediaPlayer.EndOfMedia:
            self._show_main_window_and_finish()

    def _on_loaded_position_changed(self, position):
        if not self.loaded_playing or self.finished:
            return
        duration = self.loaded_player.duration()
        if duration > 0 and position >= duration - 60:
            self._show_main_window_and_finish()

    def _show_main_window_and_finish(self):
        if self.finished:
            return
        self.finished = True
        if self.safety_timer:
            self.safety_timer.stop()

        if self.main_window is not None:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

        try:
            self.loading_player.stop()
            self.loaded_player.stop()
        except Exception:
            pass

        QTimer.singleShot(150, self.close)

    def _safety_timeout(self):
        if self.finished:
            return
        self._show_main_window_and_finish()

    def closeEvent(self, event):
        if self.safety_timer:
            self.safety_timer.stop()
        # Restaura comportamento de fechar app quando MainWindow fechar
        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(True)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    icon_file = asset_path("grilinho.ico")
    if os.path.isfile(icon_file):
        app.setWindowIcon(QIcon(icon_file))

    splash = Launcher()
    splash.show()
    QApplication.processEvents()
    splash.start()

    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
