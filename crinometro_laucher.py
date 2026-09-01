import os
import sys
import time
import winsound
from PyQt5.QtCore import Qt, QTimer, QThread, QRectF, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QColor

TARGET_FPS = 30.0  # 1.25x de velocidade em relação aos 24 fps originais
TICK_INTERVAL_MS = 16  # Loop do timer em ~60 Hz para máxima fluidez


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
            import sklearn
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
        self.mode = "loading"  # "loading" or "loaded"
        self.frame_idx = 0
        self.finished = False
        self.main_window = None
        self.spinner_angle = 0
        self.loading_start_time = time.time()
        self.loaded_start_time = None

        self.setObjectName("Launcher")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setStyleSheet("""
            QWidget#Launcher {
                background: #FFFFFF;
                border: 1px solid #D7DCE1;
                border-radius: 10px;
            }
        """)

        center(self)

        # Carrega os frames da animação pré-escalados para a resolução da janela
        self.loading_frames = []
        self.loaded_frames = []
        self._load_frames()

        # Timer de renderização em tempo real (baseado no relógio do sistema)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(TICK_INTERVAL_MS)
        self.anim_timer.timeout.connect(self._next_frame)

        self.safety_timer = QTimer(self)
        self.safety_timer.setSingleShot(True)
        self.safety_timer.timeout.connect(self._safety_timeout)

    def _load_frames(self):
        loading_dir = asset_path("launcher_assets/loading")
        loaded_dir = asset_path("launcher_assets/loaded")
        target_w, target_h = self.width(), self.height()

        if os.path.isdir(loading_dir):
            files = sorted([f for f in os.listdir(loading_dir) if f.endswith(".jpg") or f.endswith(".png")])
            for f in files:
                pix = QPixmap(os.path.join(loading_dir, f))
                if not pix.isNull():
                    if pix.size() != self.size():
                        pix = pix.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    self.loading_frames.append(pix)

        if os.path.isdir(loaded_dir):
            files = sorted([f for f in os.listdir(loaded_dir) if f.endswith(".jpg") or f.endswith(".png")])
            for f in files:
                pix = QPixmap(os.path.join(loaded_dir, f))
                if not pix.isNull():
                    if pix.size() != self.size():
                        pix = pix.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    self.loaded_frames.append(pix)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Desenha o quadro atual do vídeo
        frames = self.loading_frames if self.mode == "loading" else self.loaded_frames
        if frames and 0 <= self.frame_idx < len(frames):
            current_pix = frames[self.frame_idx]
            painter.drawPixmap(0, 0, current_pix)
        else:
            painter.fillRect(self.rect(), Qt.white)

        # 2. SPINNER ROTATIVO NO TOPO (Prioridade Visual / Z-Index Máximo)
        if self.mode == "loading":
            spinner_size = 28
            margin_right = 24
            margin_bottom = 24
            sx = self.width() - spinner_size - margin_right
            sy = self.height() - spinner_size - margin_bottom

            pen = QPen(QColor(30, 35, 42, 220), 3.0)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            spinner_rect = QRectF(sx, sy, spinner_size, spinner_size)
            painter.drawArc(spinner_rect, int(self.spinner_angle * 16), int(270 * 16))

        painter.end()

    def start(self):
        self.loading_start_time = time.time()
        self.anim_timer.start()

        # Inicia thread de carregamento dos módulos
        self.loader_thread = CoreLoaderThread()
        self.loader_thread.loaded.connect(self._on_core_loaded)
        self.loader_thread.error.connect(self._on_core_error)
        self.loader_thread.start()

        self.safety_timer.start(self.SAFETY_TIMEOUT_MS)

    def _next_frame(self):
        if self.finished:
            return

        now = time.time()

        if self.mode == "loading":
            elapsed = now - self.loading_start_time
            # Spinner gira a ~1.5 rotações por segundo em tempo real
            self.spinner_angle = int(elapsed * 360 * 1.5) % 360

            if self.loading_frames:
                total_loading_sec = len(self.loading_frames) / TARGET_FPS
                loop_sec = elapsed % total_loading_sec
                self.frame_idx = min(len(self.loading_frames) - 1, int(loop_sec * TARGET_FPS))

                if self.core_ready and elapsed >= total_loading_sec:
                    self._switch_to_loaded()
            self.update()

        elif self.mode == "loaded":
            if not self.loaded_start_time:
                self.loaded_start_time = now
            elapsed = now - self.loaded_start_time

            if not self.loaded_frames:
                self._show_main_window_and_finish()
                return

            total_loaded_sec = len(self.loaded_frames) / TARGET_FPS
            self.frame_idx = int(elapsed * TARGET_FPS)

            if self.frame_idx >= len(self.loaded_frames) or elapsed >= total_loaded_sec:
                self._show_main_window_and_finish()
            else:
                self.update()

    def _switch_to_loaded(self):
        if self.mode == "loaded" or self.finished:
            return
        self.mode = "loaded"
        self.loaded_start_time = time.time()
        self.frame_idx = 0

        # Áudio sincronizado em tempo real
        for audio_name in ("loaded_fast.wav", "loaded.wav"):
            audio_path = asset_path(audio_name)
            if os.path.isfile(audio_path):
                try:
                    winsound.PlaySound(audio_path, winsound.SND_ASYNC | winsound.SND_FILENAME)
                    break
                except Exception as e:
                    print(f"Aviso de áudio: {e}")
        self.update()

    def _on_core_loaded(self):
        if self.finished:
            return
        try:
            import crinometro
            self.main_window = crinometro.MainWindow()
            self.core_ready = True
            if self.mode == "loading":
                self._switch_to_loaded()
        except Exception as e:
            import traceback
            self._on_core_error(traceback.format_exc())

    def _on_core_error(self, err_trace: str):
        print(f"Erro ao carregar Crinômetro:\n{err_trace}")
        self.finished = True
        self.anim_timer.stop()
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
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

    def _show_main_window_and_finish(self):
        if self.finished:
            return
        self.finished = True
        self.anim_timer.stop()
        if self.safety_timer:
            self.safety_timer.stop()

        if self.main_window is not None:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

        QTimer.singleShot(150, self.close)

    def _safety_timeout(self):
        if self.finished:
            return
        self._show_main_window_and_finish()

    def closeEvent(self, event):
        if self.anim_timer:
            self.anim_timer.stop()
        if self.safety_timer:
            self.safety_timer.stop()
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
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
