import sys
import os
import math
import random
import tempfile
import subprocess
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
from PyQt5.QtWidgets import QWidget, QApplication

class ZParticle:
    """Partícula do Zzz: surge perto da cabeça, sobe, cresce e desvanece."""
    def __init__(self, start_x, start_y):
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.progress = 0.0
        self.lifetime = random.uniform(1.8, 2.3)
        self.wobble_seed = random.uniform(0, 2 * math.pi)
        self.base_char = random.choice(["z", "Z"])
        self.max_size = random.uniform(16, 24)

    def update(self, dt):
        self.progress += dt / self.lifetime
        self.y = self.start_y - (self.progress * 115)
        self.x = self.start_x + math.sin(self.progress * 6.5 + self.wobble_seed) * 12

    @property
    def is_dead(self):
        return self.progress >= 1.0

    @property
    def current_size(self):
        return 7 + (self.max_size - 7) * math.sin(self.progress * math.pi * 0.7)

    @property
    def opacity(self):
        if self.progress < 0.25:
            return self.progress / 0.25
        elif self.progress > 0.65:
            return max(0.0, 1.0 - (self.progress - 0.65) / 0.35)
        return 1.0


class LauncherLoadingScreen(QWidget):
    APP_VERSION = "v3.5.0"

    MEME_PHRASES = [
        "Intankável o grilo às 3 da manhã mandando áudio sem fone...",
        "POV: Você é um grilo e esqueceu que virou CLT.",
        "O grilo meteu o shape ou é só distorção harmônica?",
        "Calvo de estridular: perdendo frequência capilar ao vivo.",
        "Real ou feiki? Esse pico de áudio tá parecendo golpe do Pix.",
        "Nem Freud explica esse grilo emocionado cantando no vácuo.",
        "Grilo beta pedindo atenção vs Grilo sigma focado no grind.",
        "Esse chirp aí foi puro loss, gain zero na bioacústica.",
        "Totalmente delulu achando que o grilo tá cantando pra você.",
        "Macetando o FFT porque o algoritmo não é obrigado a nada.",
        "Grilo de cria mandando estridulação no passinho dos 5 kHz.",
        "Que Xou da Xuxa é esse? O grilo nem afinou antes do show.",
        "Simplesmente o grilo mais redpill da mata atlântica.",
        "Grilo com ansiedade social tentando cantar em mute.",
        "Aura -10.000 pro grilo que errou o compasso do chilreio.",
        "Isso aqui não é um chilreio, é uma thread de desabafo no X.",
        "Literalmente eu: fingindo que entendi a transformada de Fourier.",
        "O grilo tá fazendo gaslighting acústico com o microfone.",
        "NPC de folhagem detectado: repetindo o mesmo chirp há 2 horas.",
        "Grilo mandou a braba em 4 kHz e foi de mimi logo em seguida.",
        "Intankável o bostil bioacústico, só tem cigarra querendo aparecer.",
        "Era só um chirp limpo e um café, e eu não estaria aqui debugando.",
        "Avaliando se o inseto tá flertando ou só xingando o algoritmo.",
        "Grilo emocionado: mandou 4 chilreios seguidos e tomou ghosting.",
        "Plot twist: o grilo nem existe, era a geladeira fazendo barulho.",
        "O algoritmo tá tipo: 'deixa os garoto estridular em paz'.",
        "Farmando XP de bioacústica enquanto o modelo não dá overfitting.",
        "Grilo low profile: canta uma vez por ano e some da timeline.",
        "Não ironicamente decodificando a fofoca dos ortópteros.",
        "O grilo meteu um 'é sobre isso e tá tudo bem' em alta frequência."
    ]

    def __init__(self, ready_file, release_file, shown_file, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.ready_file = ready_file
        self.release_file = release_file
        self.shown_file = shown_file

        self.resize(760, 460)
        self._center_on_screen()

        # Estados: "sleeping" -> "waking" -> "awake" -> "expanding"
        self.anim_state = "sleeping"
        self.time_elapsed = 0.0
        self.wake_progress = 0.0
        self.awake_hold_time = 0.0
        self.scale_factor = 1.0
        self.fade_alpha = 255

        # Spinner giratório
        self.spinner_angle = 0.0

        # Partículas Zzz
        self.z_particles = []
        self.last_particle_time = 0.0

        # Sorteio aleatório da frase inicial
        self.current_phrase = random.choice(self.MEME_PHRASES)
        self.phrase_timer = QTimer(self)
        self.phrase_timer.timeout.connect(self._pick_random_phrase)
        self.phrase_timer.start(3400)

        # Loop principal (60 FPS)
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._update_animation)
        self.fps_timer.start(16)

        # Monitoramento do processo principal (IPC)
        self.ipc_timer = QTimer(self)
        self.ipc_timer.setInterval(30)
        self.ipc_timer.timeout.connect(self._check_app_ready)
        self.ipc_timer.start()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = self.geometry()
            geo.moveCenter(screen.availableGeometry().center())
            self.setGeometry(geo)

    def _pick_random_phrase(self):
        candidates = [p for p in self.MEME_PHRASES if p != self.current_phrase]
        self.current_phrase = random.choice(candidates)

    def _check_app_ready(self):
        if self.anim_state == "sleeping" and os.path.exists(self.ready_file):
            self.ipc_timer.stop()
            self.anim_state = "waking"

    def _update_animation(self):
        dt = 0.016
        self.time_elapsed += dt
        self.spinner_angle = (self.spinner_angle + 270 * dt) % 360

        if self.anim_state == "sleeping":
            if self.time_elapsed - self.last_particle_time > 0.42:
                self.z_particles.append(ZParticle(start_x=26, start_y=-16))
                self.last_particle_time = self.time_elapsed

            for p in self.z_particles:
                p.update(dt)
            self.z_particles = [p for p in self.z_particles if not p.is_dead]

        elif self.anim_state == "waking":
            self.wake_progress = min(1.0, self.wake_progress + dt * 2.8)
            if self.wake_progress >= 1.0:
                self.anim_state = "awake"

        elif self.anim_state == "awake":
            self.awake_hold_time += dt
            if self.awake_hold_time >= 0.25:
                self.anim_state = "expanding"

        elif self.anim_state == "expanding":
            # Expansão suave até a saída
            self.scale_factor += dt * 5.0
            if self.scale_factor >= 3.8:
                self.fps_timer.stop()
                self.phrase_timer.stop()
                try:
                    with open(self.release_file, "w", encoding="utf-8") as f:
                        f.write("release")
                except Exception as e:
                    print(f"Aviso launcher release: {e}")
                self.close()
                QApplication.quit()
                return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w, h = self.width(), self.height()
        center_x = w / 2.0

        # Transição de pivô para o centro exato no momento da explosão
        if self.anim_state == "expanding":
            t = min(1.0, (self.scale_factor - 1.0) / 0.9)
            t_smooth = math.sin(t * math.pi / 2.0)
            center_y = (h * 0.35) + ((h * 0.50) - (h * 0.35)) * t_smooth
        else:
            center_y = h * 0.35

        # Fundo Dark 100% sólido (garante que nunca pisque branco)
        painter.fillRect(self.rect(), QColor(14, 11, 20))

        # Versão no canto inferior esquerdo
        painter.setPen(QColor(115, 105, 130, 160))
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        painter.drawText(QRectF(22, h - 28, 120, 18), Qt.AlignLeft | Qt.AlignVCenter, self.APP_VERSION)

        # Textos e spinner somem imediatamente na expansão
        if self.anim_state != "expanding":
            painter.setPen(QColor(253, 242, 248))
            painter.setFont(QFont("Segoe UI", 21, QFont.Bold))
            painter.drawText(QRectF(0, h * 0.58, w, 32), Qt.AlignCenter, "Crinômetro")

            painter.setPen(QColor(244, 114, 182))
            painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
            painter.drawText(QRectF(0, h * 0.65, w, 18), Qt.AlignCenter, "MODO DETETIVE DE VÁCUO ATIVADO")

            spinner_size = 30
            spinner_rect = QRectF(w / 2.0 - (spinner_size / 2.0), h * 0.72, spinner_size, spinner_size)
            painter.setPen(QPen(QColor(46, 32, 60), 2.5))
            painter.drawEllipse(spinner_rect)

            pen_spinner = QPen(QColor(244, 114, 182), 2.5)
            pen_spinner.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_spinner)
            painter.drawArc(spinner_rect, int(-self.spinner_angle * 16), int(105 * 16))

            painter.setPen(QColor(233, 213, 255, 210))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(QRectF(40, h * 0.83, w - 80, 26), Qt.AlignCenter, self.current_phrase)

        # Renderização do Mascote
        painter.save()
        painter.translate(center_x, center_y)
        painter.scale(self.scale_factor, self.scale_factor)

        # Desvanece apenas o grilo contra o fundo escuro estático
        if self.anim_state == "expanding":
            cricket_opacity = max(0.0, 1.0 - (self.scale_factor - 1.0) / 2.6)
            painter.setOpacity(cricket_opacity)

        # Balanço suave enquanto dorme
        if self.anim_state == "sleeping":
            rocking_angle = math.sin(self.time_elapsed * 2.8) * 4.5
            sway_y = math.sin(self.time_elapsed * 5.6) * 3.0
            painter.rotate(rocking_angle)
            painter.translate(0, sway_y)

        # Círculo base / Berço
        painter.setPen(QPen(QColor(46, 32, 60), 2))
        painter.setBrush(QBrush(QColor(36, 27, 47)))
        painter.drawEllipse(QPointF(0, 0), 58, 58)

        # Corpo
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(74, 222, 128)))
        painter.drawEllipse(QPointF(0, 9), 28, 22)

        # Cabeça
        painter.setBrush(QBrush(QColor(134, 239, 172)))
        painter.drawEllipse(QPointF(0, -9), 20, 16)

        # Bochechas rosadas
        painter.setBrush(QBrush(QColor(244, 114, 182, 190)))
        painter.drawEllipse(QPointF(-13, -3), 4.5, 4.5)
        painter.drawEllipse(QPointF(13, -3), 4.5, 4.5)

        # Antenas
        pen_ant = QPen(QColor(74, 222, 128), 2.2)
        pen_ant.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_ant)
        painter.setBrush(Qt.NoBrush)

        path_ant_l = QPainterPath()
        path_ant_l.moveTo(-5, -24)
        path_ant_l.quadTo(-15, -39, -22, -35)
        painter.drawPath(path_ant_l)

        path_ant_r = QPainterPath()
        path_ant_r.moveTo(5, -24)
        path_ant_r.quadTo(15, -39, 22, -35)
        painter.drawPath(path_ant_r)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(253, 224, 71)))
        painter.drawEllipse(QPointF(-22, -35), 3.0, 3.0)
        painter.drawEllipse(QPointF(22, -35), 3.0, 3.0)

        # Fones de Ouvido
        pen_phone = QPen(QColor(244, 114, 182), 4.0)
        pen_phone.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_phone)
        painter.setBrush(Qt.NoBrush)

        path_phone = QPainterPath()
        path_phone.moveTo(-25, -10)
        path_phone.cubicTo(-25, -38, 25, -38, 25, -10)
        painter.drawPath(path_phone)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(251, 113, 133)))
        painter.drawRoundedRect(QRectF(-32, -18, 9, 18), 4, 4)
        painter.drawRoundedRect(QRectF(23, -18, 9, 18), 4, 4)

        # Olhos
        if self.anim_state == "sleeping":
            pen_eye = QPen(QColor(20, 83, 45), 2.2)
            pen_eye.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_eye)
            painter.setBrush(Qt.NoBrush)

            eye_l = QPainterPath()
            eye_l.moveTo(-11, -10)
            eye_l.quadTo(-7, -14, -3, -10)
            painter.drawPath(eye_l)

            eye_r = QPainterPath()
            eye_r.moveTo(3, -10)
            eye_r.quadTo(7, -14, 11, -10)
            painter.drawPath(eye_r)
        else:
            eye_size = 4.5 + 3.8 * self.wake_progress
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QPointF(-7, -10), eye_size, eye_size)
            painter.drawEllipse(QPointF(7, -10), eye_size, eye_size)

            painter.setBrush(QBrush(QColor(15, 23, 42)))
            painter.drawEllipse(QPointF(-7, -10), eye_size * 0.55, eye_size * 0.55)
            painter.drawEllipse(QPointF(7, -10), eye_size * 0.55, eye_size * 0.55)

            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QPointF(-9, -12), eye_size * 0.22, eye_size * 0.22)
            painter.drawEllipse(QPointF(5, -12), eye_size * 0.22, eye_size * 0.22)

        # Partículas Zzz
        if self.anim_state == "sleeping":
            for p in self.z_particles:
                painter.setPen(QColor(253, 224, 71, int(255 * p.opacity)))
                painter.setFont(QFont("Comic Sans MS", int(p.current_size), QFont.Bold))
                painter.drawText(QPointF(p.x, p.y), p.base_char)

        painter.restore()

def main():
    if "--launcher-managed" in sys.argv:
        import crinometro
        return crinometro.main()

    app = QApplication(sys.argv)

    temp_dir = tempfile.gettempdir()
    session_id = f"crino_{os.getpid()}"
    ready_file = os.path.join(temp_dir, f"{session_id}_ready.sig")
    release_file = os.path.join(temp_dir, f"{session_id}_release.sig")
    shown_file = os.path.join(temp_dir, f"{session_id}_shown.sig")

    for sig in [ready_file, release_file, shown_file]:
        if os.path.exists(sig):
            try:
                os.remove(sig)
            except OSError:
                pass

    splash = LauncherLoadingScreen(ready_file, release_file, shown_file)
    splash.show()

    if getattr(sys, 'frozen', False):
        cmd = [
            sys.executable,
            "--launcher-managed",
            f"--ready-file={ready_file}",
            f"--release-file={release_file}",
            f"--shown-file={shown_file}"
        ]
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = ["crinometro.py", "crinometro_3.py", "crinometro_2.py", "app_grilos.py"]
        target_script = None
        for cand in candidates:
            full_path = os.path.join(base_dir, cand)
            if os.path.exists(full_path):
                target_script = full_path
                break

        if not target_script:
            target_script = os.path.join(base_dir, "crinometro.py")

        cmd = [
            sys.executable,
            target_script,
            "--launcher-managed",
            f"--ready-file={ready_file}",
            f"--release-file={release_file}",
            f"--shown-file={shown_file}"
        ]

    subprocess.Popen(cmd)

    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())