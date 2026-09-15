import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import math
import random
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QIcon, QCursor
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QPushButton
from utils.icons import get_app_icon
from core.updater import UpdateCheckerThread, UpdateDownloaderThread, launch_windows_updater


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


class CoreLoaderThread(QThread):
    loaded = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            import scipy.special
            import scipy.integrate
            import scipy.signal
            import matplotlib
            import sklearn
            import crinometro
            self.loaded.emit()
        except Exception as e:
            import traceback
            self.error.emit(traceback.format_exc())


from utils.constants import APP_VERSION as CONST_APP_VERSION

class LauncherLoadingScreen(QWidget):
    APP_VERSION = f"v{CONST_APP_VERSION}"

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
        self.main_window = None
        self.core_ready = False

        # Margem para renderização da sombra suave projetada (drop shadow)
        self.shadow_margin = 20
        self.card_w = 760
        self.card_h = 460
        self.resize(self.card_w + 2 * self.shadow_margin, self.card_h + 2 * self.shadow_margin)
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

        # Atualizador Automático (Auto-updater)
        self.update_checker = None
        self.downloader = None
        self.update_info = None
        self.update_progress = 0
        self.update_status_text = ""

        # Botões de Atualização (inicialmente ocultos)
        btn_w, btn_h = 165, 38
        y_btns = int(self.shadow_margin + self.card_h * 0.77)
        c_x = int(self.shadow_margin + self.card_w / 2.0)
        gap = 14

        self.btn_update_now = QPushButton("⚡ Atualizar Agora", self)
        self.btn_update_now.setGeometry(c_x - btn_w - (gap // 2), y_btns, btn_w, btn_h)
        self.btn_update_now.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_update_now.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #db2777, stop:1 #ec4899);
                color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
                border-radius: 8px;
                border: 1px solid #f472b6;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ec4899, stop:1 #f472b6);
                border: 1px solid #fbcfe8;
            }
            QPushButton:pressed {
                background: #be185d;
            }
        """)
        self.btn_update_now.clicked.connect(self._on_update_now_clicked)
        self.btn_update_now.hide()

        self.btn_remind_later = QPushButton("Lembrar Mais Tarde", self)
        self.btn_remind_later.setGeometry(c_x + (gap // 2), y_btns, btn_w, btn_h)
        self.btn_remind_later.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_remind_later.setStyleSheet("""
            QPushButton {
                background-color: #261b33;
                color: #cbd5e1;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
                border-radius: 8px;
                border: 1px solid #47385d;
            }
            QPushButton:hover {
                background-color: #38284c;
                color: #f8fafc;
                border: 1px solid #7c5295;
            }
            QPushButton:pressed {
                background-color: #1e1529;
            }
        """)
        self.btn_remind_later.clicked.connect(self._on_remind_later_clicked)
        self.btn_remind_later.hide()

        # Loop principal (60 FPS)
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._update_animation)
        self.fps_timer.start(16)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = self.geometry()
            geo.moveCenter(screen.availableGeometry().center())
            self.setGeometry(geo)

    def _pick_random_phrase(self):
        candidates = [p for p in self.MEME_PHRASES if p != self.current_phrase]
        self.current_phrase = random.choice(candidates)

    def start_loader(self):
        # 1. Carregamento das bibliotecas e inicialização da janela principal
        self.loader_thread = CoreLoaderThread()
        self.loader_thread.loaded.connect(self._on_core_loaded)
        self.loader_thread.error.connect(self._on_core_error)
        self.loader_thread.start()

        # 2. Verificação assíncrona de atualização no GitHub
        self.update_checker = UpdateCheckerThread(self)
        self.update_checker.update_available.connect(self._on_update_detected)
        self.update_checker.no_update.connect(self._on_update_not_found)
        self.update_checker.error.connect(self._on_update_check_error)
        self.update_checker.start()

    def _on_core_loaded(self):
        try:
            import crinometro
            self.main_window = crinometro.MainWindow()
            self.core_ready = True
            # Se não estiver aguardando decisão ou baixando atualização, acorda o mascote e prossegue
            if self.anim_state == "sleeping":
                self.anim_state = "waking"
        except Exception as e:
            import traceback
            self._on_core_error(traceback.format_exc())

    def _on_update_detected(self, info: dict):
        """Quando uma nova versão é detectada no GitHub."""
        self.update_info = info
        # Para a troca periódica de memes e mantém o launcher parado
        self.phrase_timer.stop()
        self.anim_state = "update_prompt"
        self.btn_update_now.show()
        self.btn_remind_later.show()
        self.update()

    def _on_update_not_found(self, info: dict):
        """Nenhuma versão nova encontrada; segue o fluxo normal."""
        if self.core_ready and self.anim_state == "sleeping":
            self.anim_state = "waking"

    def _on_update_check_error(self, err_msg: str):
        """Em caso de falha de conexão com o GitHub, não impede o app de abrir."""
        print(f"[Auto-Updater] Verificação ignorada: {err_msg}")
        if self.core_ready and self.anim_state == "sleeping":
            self.anim_state = "waking"

    def _on_remind_later_clicked(self):
        """Usuário optou por ignorar no momento e usar a versão atual."""
        self.btn_update_now.hide()
        self.btn_remind_later.hide()
        if self.core_ready:
            self.anim_state = "waking"
        else:
            self.anim_state = "sleeping"
            self.phrase_timer.start(3400)
        self.update()

    def _on_update_now_clicked(self):
        """Usuário aceitou atualizar agora: esconde botões e inicia download."""
        self.btn_update_now.hide()
        self.btn_remind_later.hide()
        self.anim_state = "updating"
        self.update_progress = 0
        self.update_status_text = "Baixando atualização (0%)"
        self.update()

        download_url = self.update_info.get("download_url") if self.update_info else ""
        asset_name = self.update_info.get("asset_name", "") if self.update_info else ""

        if not download_url:
            # Fallback caso não haja executável direto: abre a página de releases e prossegue
            import webbrowser
            target_url = self.update_info.get("html_url", "https://github.com/rogerioafreitas/crinometro/releases")
            webbrowser.open(target_url)
            self._on_remind_later_clicked()
            return

        self.downloader = UpdateDownloaderThread(download_url, dest_filename=asset_name, parent=self)
        self.downloader.progress.connect(self._on_download_progress)
        self.downloader.finished.connect(self._on_download_finished)
        self.downloader.error.connect(self._on_download_error)
        self.downloader.start()

    def _on_download_progress(self, percent: int):
        self.update_progress = percent
        self.update_status_text = f"Baixando atualização ({percent}%)"
        self.update()

    def _on_download_finished(self, file_path: str):
        self.update_progress = 100
        self.update_status_text = "Verificando arquivos..."
        self.update()

        # Sequência suave de mensagens de transição antes de aplicar
        QTimer.singleShot(600, lambda: self._step_install_files(file_path))

    def _step_install_files(self, file_path: str):
        self.update_status_text = "Instalando arquivos..."
        self.update()
        QTimer.singleShot(700, lambda: self._step_restart_app(file_path))

    def _step_restart_app(self, file_path: str):
        self.update_status_text = "Reiniciando o programa..."
        self.update()
        QTimer.singleShot(800, lambda: launch_windows_updater(file_path))

    def _on_download_error(self, err_msg: str):
        print(f"[Auto-Updater] Erro no download: {err_msg}")
        self.update_status_text = "Erro no download. Iniciando versão atual..."
        self.update()
        QTimer.singleShot(1500, self._on_remind_later_clicked)

    def _on_core_error(self, err_trace: str):
        print(f"Erro ao carregar Crinômetro:\n{err_trace}")
        self.fps_timer.stop()
        self.phrase_timer.stop()
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Erro de Inicialização - Crinômetro")
        msg.setText("Ocorreu um erro ao carregar o aplicativo:")
        msg.setDetailedText(err_trace)
        msg.exec()
        self.close()
        QApplication.quit()

    def _update_animation(self):
        dt = 0.016
        self.time_elapsed += dt
        self.spinner_angle = (self.spinner_angle + 270 * dt) % 360

        if self.anim_state in ("sleeping", "update_prompt", "updating"):
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
                if self.main_window is not None:
                    self.main_window.show()
                    self.main_window.raise_()
                    self.main_window.activateWindow()
                self.close()
                return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        m = self.shadow_margin
        card_w, card_h = self.card_w, self.card_h
        card_rect = QRectF(m, m, card_w, card_h)

        # 1. Efeito de Sombra Suave por trás da janela (Drop Shadow)
        corner_r = 14.0
        for i in range(m, 0, -2):
            alpha = int(55 * (1.0 - (i / m)) ** 1.8)
            if alpha <= 0:
                continue
            shadow_rect = card_rect.adjusted(-i, -i + 3, i, i + 3)
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(shadow_rect, corner_r + i * 0.4, corner_r + i * 0.4)
            painter.fillPath(shadow_path, QColor(0, 0, 0, alpha))

        # 2. Fundo Dark da Janela (Card Arredondado com borda sutil)
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, corner_r, corner_r)
        painter.fillPath(card_path, QColor(14, 11, 20))

        # Borda sutil para dar acabamento premium e destacar do fundo
        pen_border = QPen(QColor(60, 48, 75, 160), 1.2)
        painter.setPen(pen_border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(card_rect, corner_r, corner_r)

        center_x = m + card_w / 2.0

        # Transição de pivô para o centro exato no momento da explosão
        if self.anim_state == "expanding":
            t = min(1.0, (self.scale_factor - 1.0) / 0.9)
            t_smooth = math.sin(t * math.pi / 2.0)
            center_y = m + (card_h * 0.35) + ((card_h * 0.50) - (card_h * 0.35)) * t_smooth
        else:
            center_y = m + (card_h * 0.35)

        # Versão no canto inferior esquerdo
        painter.setPen(QColor(115, 105, 130, 160))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(QRectF(m + 22, m + card_h - 28, 120, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.APP_VERSION)

        # Textos e status centrais (somem imediatamente na expansão)
        if self.anim_state != "expanding":
            painter.setPen(QColor(253, 242, 248))
            painter.setFont(QFont("Segoe UI", 21, QFont.Weight.Bold))
            painter.drawText(QRectF(m, m + card_h * 0.58, card_w, 32), Qt.AlignmentFlag.AlignCenter, "Crinômetro")

            if self.anim_state == "update_prompt":
                # Estado 1: Nova versão detectada, aguardando resposta do usuário
                remote_ver = self.update_info.get("tag", "") if self.update_info else ""
                tag_label = f"v{remote_ver}" if remote_ver and not remote_ver.startswith("v") else remote_ver
                painter.setPen(QColor(244, 114, 182))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
                painter.drawText(QRectF(m, m + card_h * 0.65, card_w, 18), Qt.AlignmentFlag.AlignCenter, f"NOVA ATUALIZAÇÃO DISPONÍVEL ({tag_label})")

                painter.setPen(QColor(233, 213, 255, 220))
                painter.setFont(QFont("Segoe UI", 9))
                painter.drawText(QRectF(m + 40, m + card_h * 0.70, card_w - 80, 24), Qt.AlignmentFlag.AlignCenter, "Deseja atualizar agora para obter as novidades e melhorias?")

            elif self.anim_state == "updating":
                # Estado 2: Atualização em andamento com barra de progresso
                painter.setPen(QColor(244, 114, 182))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
                painter.drawText(QRectF(m, m + card_h * 0.65, card_w, 18), Qt.AlignmentFlag.AlignCenter, "ATUALIZAÇÃO AUTOMÁTICA EM ANDAMENTO")

                # Barra de progresso moderna
                bar_w, bar_h = 360, 10
                bar_x = center_x - (bar_w / 2.0)
                bar_y = m + card_h * 0.72
                bar_rect = QRectF(bar_x, bar_y, bar_w, bar_h)

                # Trilho de fundo
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(36, 27, 47)))
                painter.drawRoundedRect(bar_rect, 5.0, 5.0)

                # Barra preenchida
                fill_w = max(0.0, (bar_w * (self.update_progress / 100.0)))
                if fill_w > 0:
                    fill_rect = QRectF(bar_x, bar_y, fill_w, bar_h)
                    painter.setBrush(QBrush(QColor(236, 72, 153)))
                    painter.drawRoundedRect(fill_rect, 5.0, 5.0)

                # Borda sutil na barra
                painter.setPen(QPen(QColor(60, 48, 75), 1.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(bar_rect, 5.0, 5.0)

                # Texto de status funcional ("Baixando...", "Instalando...", etc.)
                painter.setPen(QColor(233, 213, 255, 230))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                painter.drawText(QRectF(m + 40, m + card_h * 0.78, card_w - 80, 26), Qt.AlignmentFlag.AlignCenter, self.update_status_text)

            else:
                # Estado Normal: Spinner e memes rotativos
                painter.setPen(QColor(244, 114, 182))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
                painter.drawText(QRectF(m, m + card_h * 0.65, card_w, 18), Qt.AlignmentFlag.AlignCenter, "MODO DETETIVE DE VÁCUO ATIVADO")

                spinner_size = 30
                spinner_rect = QRectF(center_x - (spinner_size / 2.0), m + card_h * 0.72, spinner_size, spinner_size)
                painter.setPen(QPen(QColor(46, 32, 60), 2.5))
                painter.drawEllipse(spinner_rect)

                pen_spinner = QPen(QColor(244, 114, 182), 2.5)
                pen_spinner.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen_spinner)
                painter.drawArc(spinner_rect, int(-self.spinner_angle * 16), int(105 * 16))

                painter.setPen(QColor(233, 213, 255, 210))
                painter.setFont(QFont("Segoe UI", 9))
                painter.drawText(QRectF(m + 40, m + card_h * 0.83, card_w - 80, 26), Qt.AlignmentFlag.AlignCenter, self.current_phrase)

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
        painter.setPen(Qt.PenStyle.NoPen)
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
        pen_ant.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_ant)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        path_ant_l = QPainterPath()
        path_ant_l.moveTo(-5, -24)
        path_ant_l.quadTo(-15, -39, -22, -35)
        painter.drawPath(path_ant_l)

        path_ant_r = QPainterPath()
        path_ant_r.moveTo(5, -24)
        path_ant_r.quadTo(15, -39, 22, -35)
        painter.drawPath(path_ant_r)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(253, 224, 71)))
        painter.drawEllipse(QPointF(-22, -35), 3.0, 3.0)
        painter.drawEllipse(QPointF(22, -35), 3.0, 3.0)

        # Fones de Ouvido
        pen_phone = QPen(QColor(244, 114, 182), 4.0)
        pen_phone.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_phone)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        path_phone = QPainterPath()
        path_phone.moveTo(-25, -10)
        path_phone.cubicTo(-25, -38, 25, -38, 25, -10)
        painter.drawPath(path_phone)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(251, 113, 133)))
        painter.drawRoundedRect(QRectF(-32, -18, 9, 18), 4, 4)
        painter.drawRoundedRect(QRectF(23, -18, 9, 18), 4, 4)

        # Olhos
        if self.anim_state in ("sleeping", "update_prompt", "updating"):
            pen_eye = QPen(QColor(20, 83, 45), 2.2)
            pen_eye.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_eye)
            painter.setBrush(Qt.BrushStyle.NoBrush)

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
            painter.setPen(Qt.PenStyle.NoPen)
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
        if self.anim_state in ("sleeping", "update_prompt", "updating"):
            for p in self.z_particles:
                painter.setPen(QColor(253, 224, 71, int(255 * p.opacity)))
                painter.setFont(QFont("Comic Sans MS", int(p.current_size), QFont.Weight.Bold))
                painter.drawText(QPointF(p.x, p.y), p.base_char)

        painter.restore()

    def closeEvent(self, event):
        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(True)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    # Ícone do aplicativo
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_candidate = os.path.join(base_dir, "grilinho.ico")
    if os.path.isfile(icon_candidate):
        app.setWindowIcon(QIcon(icon_candidate))
    else:
        app.setWindowIcon(get_app_icon())

    splash = LauncherLoadingScreen()
    splash.show()
    app.processEvents()
    splash.start_loader()

    return app.exec()



if __name__ == "__main__":
    raise SystemExit(main())