import os
import sys
import tempfile
from PyQt5.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
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
            import crinometro
            self.loaded.emit()
        except Exception as e:
            self.error.emit(str(e))


class Launcher(QWidget):
    SAFETY_TIMEOUT_MS = 120_000

    def __init__(self):
        super().__init__()

        self.core_ready = False
        self.loaded_ready = False
        self.switch_armed = False
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

        # Dois vídeos permanentemente montados. O loaded fica por baixo.
        self.loaded_video = QVideoWidget(host)
        self.loading_video = QVideoWidget(host)

        for video in (self.loaded_video, self.loading_video):
            video.setStyleSheet("background:#FFFFFF; border:0;")
            video.setAspectRatioMode(Qt.KeepAspectRatio)

        self.loaded_video.lower()
        self.loading_video.raise_()

        # Loading Player
        self.loading_player = QMediaPlayer(self)
        self.loading_player.setVolume(0)
        self.loading_player.setVideoOutput(self.loading_video)
        self.loading_player.setPlaybackRate(RATE)
        self.loading_player.durationChanged.connect(self._loading_duration_changed)
        self.loading_player.mediaStatusChanged.connect(self._loading_media_status)
        if hasattr(self.loading_player, "errorOccurred"):
            self.loading_player.errorOccurred.connect(self._loading_error)
        elif hasattr(self.loading_player, "error"):
            self.loading_player.error.connect(self._loading_error)

        # Loaded Player
        self.loaded_player = QMediaPlayer(self)
        self.loaded_player.setVolume(0)
        self.loaded_player.setVideoOutput(self.loaded_video)
        self.loaded_player.setPlaybackRate(RATE)
        self.loaded_player.mediaStatusChanged.connect(self._loaded_media_status)
        self.loaded_player.stateChanged.connect(self._loaded_playback_state)
        self.loaded_player.positionChanged.connect(self._loaded_position_changed)
        if hasattr(self.loaded_player, "errorOccurred"):
            self.loaded_player.errorOccurred.connect(self._loaded_error)
        elif hasattr(self.loaded_player, "error"):
            self.loaded_player.error.connect(self._loaded_error)

        self.loading_duration = 0
        self.loading_media_ok = False
        self.loaded_media_ok = False

        self.loaded_prewarm_timer = QTimer(self)
        self.loaded_prewarm_timer.setSingleShot(True)
        self.loaded_prewarm_timer.timeout.connect(self._finish_loaded_prewarm)

        self.transition_check_timer = QTimer(self)
        self.transition_check_timer.setInterval(8)
        self.transition_check_timer.timeout.connect(self._check_transition_boundary)

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

        # Playlist para reproduzir loading em loop
        self.loading_playlist = QMediaPlaylist(self)
        self.loading_playlist.addMedia(QMediaContent(QUrl.fromLocalFile(loading)))
        self.loading_playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.loading_player.setPlaylist(self.loading_playlist)
        self.loading_player.setVolume(0)
        self.loading_player.play()

        self.loaded_player.setMedia(QMediaContent(QUrl.fromLocalFile(loaded)))

        # Inicia importação e preparação dos módulos em segundo plano
        self.loader_thread = CoreLoaderThread()
        self.loader_thread.loaded.connect(self._on_core_loaded)
        self.loader_thread.error.connect(self._on_core_error)
        self.loader_thread.start()

        self.safety_timer.start(self.SAFETY_TIMEOUT_MS)

    # ---------- loading ----------
    def _loading_duration_changed(self, duration):
        if duration > 0:
            self.loading_duration = int(duration)

    def _loading_media_status(self, status):
        if status in (
            QMediaPlayer.LoadedMedia,
            QMediaPlayer.BufferedMedia,
        ):
            self.loading_media_ok = True

    def _loading_error(self, *args):
        if self.finished:
            return
        QTimer.singleShot(50, self.loading_player.play)

    # ---------- carregamento do core ----------
    def _on_core_loaded(self):
        if self.finished:
            return
        try:
            import crinometro
            self.main_window = crinometro.MainWindow()
            self.core_ready = True
            self._prepare_loaded()
            self.transition_check_timer.start()
        except Exception as e:
            self._on_core_error(str(e))

    def _on_core_error(self, error_msg: str):
        print(f"Erro ao carregar Crinômetro: {error_msg}")
        self._safety_timeout()

    # ---------- loaded prewarm ----------
    def _prepare_loaded(self):
        if self.loaded_ready or self.finished:
            return

        self.loaded_ready = True
        self.loaded_player.setVolume(0)
        self.loaded_player.setPosition(0)
        self.loaded_player.play()

        self.loaded_prewarm_timer.start(220)

    def _finish_loaded_prewarm(self):
        if self.finished or self.loaded_playing:
            return

        try:
            self.loaded_player.pause()
            self.loaded_player.setPosition(0)
        except Exception:
            pass

    def _loaded_media_status(self, status):
        if status in (
            QMediaPlayer.LoadedMedia,
            QMediaPlayer.BufferedMedia,
        ):
            self.loaded_media_ok = True
        elif status == QMediaPlayer.EndOfMedia:
            if self.loaded_playing:
                self._on_loaded_finished()

    def _loaded_playback_state(self, state):
        if self.loaded_playing and state == QMediaPlayer.StoppedState:
            self._on_loaded_finished()

    def _loaded_position_changed(self, position):
        if self.loaded_playing and not self.finished:
            duration = self.loaded_player.duration()
            if duration > 0 and position >= duration - 50:
                self._on_loaded_finished()

    def _loaded_error(self, *args):
        if self.finished:
            return

    # ---------- troca sincronizada ----------
    def _check_transition_boundary(self):
        if self.finished or not self.core_ready or not self.loaded_ready:
            return
        if self.switch_armed:
            return

        duration = self.loading_duration
        position = self.loading_player.position()

        if duration <= 0:
            return

        remaining = duration - position

        if remaining <= 85:
            self._switch_to_loaded()

    def _switch_to_loaded(self):
        if self.switch_armed or self.finished:
            return

        self.switch_armed = True
        self.transition_check_timer.stop()
        self.loaded_playing = True

        self.loaded_player.setVolume(100)
        self.loaded_video.show()
        self.loaded_video.raise_()

        self.loaded_player.setPosition(0)
        self.loaded_player.play()

        self.loading_player.pause()
        self.loading_video.hide()

    # ---------- finalização e exibição ----------
    def _on_loaded_finished(self):
        if self.finished:
            return

        self.finished = True
        self._cleanup_timers()

        if self.main_window is not None:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

        try:
            self.loading_player.stop()
            self.loaded_player.stop()
            self.loading_player.setVideoOutput(None)
            self.loaded_player.setVideoOutput(None)
        except Exception:
            pass

        self.close()

    def _cleanup_timers(self):
        for timer in (
            self.transition_check_timer,
            self.loaded_prewarm_timer,
            self.safety_timer,
        ):
            if timer is not None:
                try:
                    timer.stop()
                except Exception:
                    pass

    def _safety_timeout(self):
        if self.finished:
            return
        self.finished = True
        self._cleanup_timers()

        if self.main_window is not None:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        else:
            QApplication.quit()

        self.close()

    def closeEvent(self, event):
        if not self.finished and self.main_window is None:
            self._cleanup_timers()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
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
