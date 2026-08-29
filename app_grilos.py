import sys
import os
import time
import numpy as np
import statistics
import datetime
import json
from scipy.io import wavfile
from scipy.signal import hilbert, find_peaks, butter, sosfiltfilt, peak_widths, spectrogram

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QLabel, QSplitter, QMessageBox, 
                             QPushButton, QSlider, QSpinBox, QDoubleSpinBox, QFormLayout, 
                             QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QLineEdit,
                             QComboBox)
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize
from PyQt6.QtGui import QFont, QAction, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ==========================================
# CONSTANTES E INTERNACIONALIZAÇÃO (i18n)
# ==========================================
CONFIG_FILE = "crinometro_config.json"

I18N = {
    "pt": {
        "app_title": "Crinômetro - Beta 1.11",
        "file": "Arquivo",
        "load": "Carregar .wav",
        "export": "Exportar Relatório (.txt)",
        "settings": "Configurações",
        "algo_settings": "Parâmetros do Algoritmo...",
        "gen_settings": "Preferências Gerais...",
        "save_settings": "Salvar Configurações Atuais",
        "help": "Ajuda",
        "about": "Sobre...",
        "files": "🎧 Arquivos",
        "reanalyze": "🔄 Reanalisar",
        "remove": "🗑️",
        "sync": "🔗 Sincronizar (X)",
        "wave": "Onda Acústica",
        "hist": "Histograma de Pulsos",
        "freq": "Freq. Dominante vs Tempo",
        "spec": "Espectrograma",
        "welcome": "Vá em Arquivo > Carregar .wav ou arraste um arquivo para iniciar.",
        "success": "Sucesso",
        "config_saved": "Configurações salvas para a próxima inicialização.",
        "error": "Erro",
        "inst": "Instituição:",
        "researcher": "Pesquisador:",
        "role": "Função:",
        "level": "Grau Acadêmico:",
        "lang": "Idioma:",
        "toggle_panel": "Ocultar/Mostrar Painel de Arquivos"
    },
    "en": {
        "app_title": "Crinômetro - Beta 1.11",
        "file": "File",
        "load": "Load .wav",
        "export": "Export Report (.txt)",
        "settings": "Settings",
        "algo_settings": "Algorithm Parameters...",
        "gen_settings": "General Preferences...",
        "save_settings": "Save Current Settings",
        "help": "Help",
        "about": "About...",
        "files": "🎧 Files",
        "reanalyze": "🔄 Reanalyze",
        "remove": "🗑️",
        "sync": "🔗 Sync Time (X)",
        "wave": "Acoustic Wave",
        "hist": "Pulse Histogram",
        "freq": "Dominant Freq. vs Time",
        "spec": "Spectrogram",
        "welcome": "Go to File > Load .wav or drag a file here to start.",
        "success": "Success",
        "config_saved": "Settings saved for next startup.",
        "error": "Error",
        "inst": "Institution:",
        "researcher": "Researcher:",
        "role": "Role:",
        "level": "Academic Level:",
        "lang": "Language:",
        "toggle_panel": "Toggle File Panel"
    }
}

def get_app_icon():
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setFont(QFont("Segoe UI Emoji", 72))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🦗")
    painter.end()
    return QIcon(pixmap)

# ==========================================
# 1. MOTOR GRÁFICO PARA SINAIS 1D (ONDA ACÚSTICA)
# ==========================================
class HighPerfLineEngine:
    def __init__(self, ax, time_sec, data, base_color='#424242', update_bg_callback=None):
        self.ax = ax
        self.time_sec = time_sec
        self.data = data
        self.base_color = base_color
        self.update_bg_callback = update_bg_callback
        self.line = None
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.render_high_detail)

    def get_viewport_slice(self, xmin, xmax):
        t_idx_min = max(0, np.searchsorted(self.time_sec, xmin) - 1)
        t_idx_max = min(len(self.time_sec), np.searchsorted(self.time_sec, xmax) + 1)
        if t_idx_max <= t_idx_min: t_idx_max = t_idx_min + 2
        return t_idx_min, t_idx_max

    def _get_envelope(self, t, y, max_points=4000):
        if len(y) <= max_points:
            return t, y
            
        num_blocks = max_points // 2
        block_size = len(y) // num_blocks
        
        y_trunc = y[:block_size * num_blocks].reshape(num_blocks, block_size)
        t_trunc = t[:block_size * num_blocks:block_size]
        
        y_min = y_trunc.min(axis=1)
        y_max = y_trunc.max(axis=1)
        
        t_env = np.empty(num_blocks * 2, dtype=t.dtype)
        y_env = np.empty(num_blocks * 2, dtype=y.dtype)
        
        t_env[0::2] = t_trunc
        t_env[1::2] = t_trunc
        y_env[0::2] = y_min
        y_env[1::2] = y_max
        
        return t_env, y_env

    def render_interactive(self, xmin, xmax, is_sync=False):
        self.debounce_timer.stop()
        t0, t1 = self.get_viewport_slice(xmin, xmax)
        
        pts = 400 if is_sync else 1000 
        t_env, y_env = self._get_envelope(self.time_sec[t0:t1], self.data[t0:t1], max_points=pts)
        self._update_plot(t_env, y_env)
        
        self.debounce_timer.start(200 if is_sync else 150)

    def render_high_detail(self):
        xmin, xmax = self.ax.get_xlim()
        t0, t1 = self.get_viewport_slice(xmin, xmax)
        
        t_env, y_env = self._get_envelope(self.time_sec[t0:t1], self.data[t0:t1], max_points=4000)
        self._update_plot(t_env, y_env)
        
        if self.update_bg_callback:
            QTimer.singleShot(50, self.update_bg_callback)

    def _update_plot(self, t, y):
        if self.line is None:
            self.line, = self.ax.plot(t, y, color=self.base_color, zorder=1, antialiased=False)
        else:
            self.line.set_data(t, y)
        self.ax.figure.canvas.draw_idle()

# ==========================================
# 2. ENGINE GRÁFICA DE ALTA PERFORMANCE (ESPECTROGRAMA)
# ==========================================
class HighPerfSpectrogramEngine:
    def __init__(self, ax, Sxx_db, t_spec, f_spec, update_bg_callback=None):
        self.ax = ax
        self.Sxx_db = Sxx_db
        self.t_spec = t_spec
        self.f_spec = f_spec
        self.update_bg_callback = update_bg_callback
        self.image = None
        
        self.tile_cache = {}
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.render_high_detail)
        
    def get_viewport_slice(self, xmin, xmax, ymin, ymax):
        t_idx_min = max(0, np.searchsorted(self.t_spec, xmin) - 1)
        t_idx_max = min(len(self.t_spec), np.searchsorted(self.t_spec, xmax) + 1)
        f_idx_min = max(0, np.searchsorted(self.f_spec, ymin) - 1)
        f_idx_max = min(len(self.f_spec), np.searchsorted(self.f_spec, ymax) + 1)
        
        if t_idx_max <= t_idx_min: t_idx_max = t_idx_min + 2
        if f_idx_max <= f_idx_min: f_idx_max = f_idx_min + 2
            
        return t_idx_min, t_idx_max, f_idx_min, f_idx_max

    def render_interactive(self, xmin, xmax, ymin, ymax, is_sync=False):
        self.debounce_timer.stop() 
        t0, t1, f0, f1 = self.get_viewport_slice(xmin, xmax, ymin, ymax)
        
        viewport_width = t1 - t0
        divisor = 350 if is_sync else 200 
        lod_step = max(1, viewport_width // divisor) 
        
        sliced_data = self.Sxx_db[f0:f1:lod_step, t0:t1:lod_step]
        self._update_imshow(sliced_data, self.t_spec[t0], self.t_spec[t1-1], self.f_spec[f0], self.f_spec[f1-1])
        
        self.debounce_timer.start(250 if is_sync else 200)
        
    def render_high_detail(self):
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        
        cache_key = (round(xmin, 1), round(xmax, 1), round(ymin, 0), round(ymax, 0))
        
        if cache_key in self.tile_cache:
            high_res_data, extent = self.tile_cache[cache_key]
            self._update_imshow(high_res_data, *extent)
        else:
            t0, t1, f0, f1 = self.get_viewport_slice(xmin, xmax, ymin, ymax)
            high_res_data = self.Sxx_db[f0:f1, t0:t1]
            extent = (self.t_spec[t0], self.t_spec[t1-1], self.f_spec[f0], self.f_spec[f1-1])
            
            self._update_imshow(high_res_data, *extent)
            
            if len(self.tile_cache) > 10:
                self.tile_cache.pop(next(iter(self.tile_cache)))
            self.tile_cache[cache_key] = (high_res_data, extent)
            
        if self.update_bg_callback:
            QTimer.singleShot(50, self.update_bg_callback)

    def _update_imshow(self, data, x0, x1, y0, y1):
        if self.image is None:
            self.image = self.ax.imshow(data, aspect='auto', origin='lower', cmap='viridis', extent=[x0, x1, y0, y1], interpolation='bilinear', zorder=1)
        else:
            self.image.set_data(data)
            self.image.set_extent([x0, x1, y0, y1])
        self.ax.figure.canvas.draw_idle()

# ==========================================
# PAINEL DE GRÁFICO CUSTOMIZADO
# ==========================================
class PlotPanel(QWidget):
    def __init__(self, title_key, lang, expand_callback):
        super().__init__()
        self.title_key = title_key
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel(I18N[lang][title_key])
        self.lbl_title.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 13px;")
        
        self.btn_expand = QPushButton("⛶")
        self.btn_expand.setStyleSheet("""
            QPushButton { background-color: #333333; padding: 4px; font-size: 12px; border-radius: 4px; color: white;}
            QPushButton:hover { background-color: #555555; }
        """)
        self.btn_expand.setFixedSize(30, 24)
        self.btn_expand.clicked.connect(lambda: expand_callback(self))
        
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_expand)
        
        self.figure = Figure(facecolor='#1E1E1E')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, facecolor='#121212')
        self.apply_dark_theme()
        
        self.layout.addLayout(top_bar)
        self.layout.addWidget(self.canvas)
        
    def update_lang(self, lang):
        self.lbl_title.setText(I18N[lang][self.title_key])

    def apply_dark_theme(self):
        self.ax.tick_params(colors='#E0E0E0', labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color('#333333')
        self.ax.xaxis.label.set_color('#E0E0E0')
        self.ax.yaxis.label.set_color('#E0E0E0')


# ==========================================
# DIÁLOGOS DE CONFIGURAÇÃO E SOBRE
# ==========================================
class AlgoSettingsDialog(QDialog):
    def __init__(self, current_params, lang, parent=None):
        super().__init__(parent)
        self.setWindowTitle(I18N[lang]["algo_settings"])
        self.setMinimumWidth(380)
        self.apply_styles()
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)
        
        self.inputs = {}
        fields = [
            ("amp_min", "Amp. Mínima:", QDoubleSpinBox, 0.01, 2.00, 0.01),
            ("amp_max", "Amp. Máxima:", QDoubleSpinBox, 0.01, 2.00, 0.01),
            ("amp_var", "Var. Amplitude (%):", QDoubleSpinBox, 0.05, 1.00, 0.05),
            ("dur_min", "Dur. Mín. (ms):", QDoubleSpinBox, 1.0, 100.0, 0.5),
            ("dur_max", "Dur. Máx. (ms):", QDoubleSpinBox, 1.0, 100.0, 0.5),
            ("gap_min", "Espaço Mín (ms):", QDoubleSpinBox, 1.0, 500.0, 1.0),
            ("gap_max", "Espaço Máx (ms):", QDoubleSpinBox, 1.0, 500.0, 1.0),
            ("min_p", "Mín. Pulsos/Chilr.:", QSpinBox, 1, 50, 1),
            ("max_p", "Máx. Pulsos/Chilr.:", QSpinBox, 1, 100, 1),
            ("b1_min", "Banda 1 Min (Hz):", QSpinBox, 100, 24000, 100),
            ("b1_max", "Banda 1 Max (Hz):", QSpinBox, 100, 24000, 100)
        ]
        
        for key, label, WidgetClass, vmin, vmax, step in fields:
            widget = WidgetClass()
            widget.setRange(vmin, vmax)
            widget.setSingleStep(step)
            widget.setValue(current_params[key])
            self.inputs[key] = widget
            form.addRow(label, widget)
            
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #1E1E1E; color: white; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; font-size: 12px; }
            QSpinBox, QDoubleSpinBox { 
                background-color: #2D2D2D; color: #4CAF50; font-weight: bold; font-size: 13px;
                border: 1px solid #555; border-radius: 4px; padding: 4px;
            }
            QPushButton { background-color: #2196F3; color: white; padding: 8px; border-radius: 4px; font-weight: bold;}
            QPushButton:hover { background-color: #1E88E5; }
        """)
        
    def get_params(self):
        return {key: widget.value() for key, widget in self.inputs.items()}

class GeneralSettingsDialog(QDialog):
    def __init__(self, current_params, lang, parent=None):
        super().__init__(parent)
        self.setWindowTitle(I18N[lang]["gen_settings"])
        self.setMinimumWidth(400)
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
        self.setStyleSheet("""
            QDialog { background-color: #1E1E1E; color: white; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; font-size: 12px; }
            QLineEdit, QComboBox { 
                background-color: #2D2D2D; color: #4CAF50; font-weight: bold; font-size: 13px;
                border: 1px solid #555; border-radius: 4px; padding: 4px;
            }
            QComboBox::drop-down { border: 0px; }
            QPushButton { background-color: #2196F3; color: white; padding: 8px; border-radius: 4px; font-weight: bold;}
            QPushButton:hover { background-color: #1E88E5; }
        """)

    def get_params(self):
        return {
            "lang": self.lang_input.currentText(),
            "institution": self.inst_input.text().strip(),
            "researcher_name": self.name_input.text().strip(),
            "role": self.role_input.currentText(),
            "level": self.level_input.currentText()
        }

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Crinômetro")
        self.setFixedSize(450, 250)
        self.setStyleSheet("background-color: #1E1E1E; color: white; font-family: 'Segoe UI';")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("🦗 Crinômetro")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50; margin-bottom: 5px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_version = QLabel("Versão: Beta 1.11")
        lbl_version.setStyleSheet("font-size: 12px; color: #9E9E9E;")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_dev = QLabel("Criado por: <b>Rogério de Araújo Freitas</b><br><a href='https://github.com/rogerioafreitas' style='color:#4CAF50; text-decoration:none;'>github.com/rogerioafreitas</a>")
        lbl_dev.setOpenExternalLinks(True)
        lbl_dev.setStyleSheet("font-size: 14px; margin-top: 15px; margin-bottom: 10px;")
        lbl_dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_desc = QLabel(
            "Desenvolvido com a intenção de auxiliar em um projeto de pesquisa na <b>UNIFESP</b>.<br>"
            "Ferramenta de bioacústica focada em detecção, análise e geração de relatórios de chilreios e pulsos."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; text-align: justify; color: #E0E0E0;")
        
        btn_close = QPushButton("Fechar")
        btn_close.setStyleSheet("background-color: #333; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_close.clicked.connect(self.accept)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_version)
        layout.addWidget(lbl_dev)
        layout.addWidget(lbl_desc)
        layout.addStretch()
        layout.addWidget(btn_close)

# ==========================================
# MOTOR DE ANÁLISE BIOACÚSTICA
# ==========================================
class CricketAnalyzer:
    @staticmethod
    def _safe_mode(values):
        if not values: return 0
        try: return statistics.mode(values)
        except statistics.StatisticsError:
            modes = statistics.multimode(values)
            return min(modes) if modes else 0

    @staticmethod
    def analyze(file_path, params):
        rate, data = wavfile.read(file_path)
        if len(data.shape) > 1: data = data[:, 0]

        data = data.astype(np.float64)
        max_val = np.max(np.abs(data))
        if max_val == 0: raise ValueError("O arquivo de áudio está mudo.")
        data = data / max_val

        audio_duration_sec = len(data) / rate

        nyq = 0.5 * rate
        sos_b1 = butter(4, [params["b1_min"]/nyq, params["b1_max"]/nyq], btype='band', output='sos')
        data_b1 = sosfiltfilt(sos_b1, data)
        env1 = np.abs(hilbert(data_b1))

        smooth_window = max(9, int(rate * 0.015))
        kernel = np.ones(smooth_window) / smooth_window
        env1_smooth = np.convolve(env1, kernel, mode='same')

        f_spec, t_spec, Sxx = spectrogram(data_b1, rate, nperseg=1024, noverlap=768)
        Sxx_db = 10 * np.log10(Sxx + 1e-10) 
        
        freq_mask = (f_spec >= params["b1_min"]) & (f_spec <= params["b1_max"])
        Sxx_band = Sxx[freq_mask, :]
        band_ratio = np.sum(Sxx_band, axis=0) / (np.sum(Sxx, axis=0) + 1e-10)
        
        dom_freq_idx = np.argmax(Sxx, axis=0)
        dom_freqs = f_spec[dom_freq_idx]

        dist_samples = max(1, int(rate * (params["gap_min"] / 1000.0)))
        
        search_thresh = params["amp_min"] * 0.90
        prominence_val = search_thresh * 0.01 
            
        raw_peaks, _ = find_peaks(env1_smooth, height=(search_thresh, params["amp_max"]), 
                               distance=dist_samples, prominence=prominence_val)

        if len(raw_peaks) == 0: raise ValueError("Nenhum pico encontrado com a amplitude informada.")

        valid_peaks_stage1 = []
        for p in raw_peaks:
            p_time = p / rate
            spec_col_idx = np.argmin(np.abs(t_spec - p_time))
            br = band_ratio[spec_col_idx]
            if br > 0.35:
                valid_peaks_stage1.append(p)
                
        peaks_filtered = np.array(valid_peaks_stage1)
        if len(peaks_filtered) == 0: raise ValueError("Nenhum pulso validado no espectrograma.")

        widths_samples, _, _, _ = peak_widths(env1_smooth, peaks_filtered, rel_height=0.7)
        pulse_durations_s = widths_samples / rate
        peak_dur_dict = dict(zip(peaks_filtered, pulse_durations_s))
        
        dur_tol = 0.5

        valid_peaks_stage2 = []
        for p in peaks_filtered:
            dur = peak_dur_dict[p]
            if (params["dur_min"]/1000.0)*(1-dur_tol) <= dur <= (params["dur_max"]/1000.0)*(1+dur_tol):
                valid_peaks_stage2.append(p)
                
        peaks = np.array(valid_peaks_stage2)
        if len(peaks) == 0: raise ValueError("Nenhum pulso passou pelo filtro de duração.")

        pulse_times_s = peaks / rate
        chirp_peaks_list = []
        current_chirp = [peaks[0]]

        for i in range(1, len(pulse_times_s)):
            gap_s = pulse_times_s[i] - pulse_times_s[i - 1]
            expected_gap_min = params["gap_min"] / 1000.0
            expected_gap_max = params["gap_max"] / 1000.0
            
            if expected_gap_min <= gap_s <= expected_gap_max:
                current_chirp.append(peaks[i])
            else:
                if len(current_chirp) >= 2: chirp_peaks_list.append(current_chirp)
                current_chirp = [peaks[i]]

        if len(current_chirp) >= 2: chirp_peaks_list.append(current_chirp)

        refined_chirps = []
        for chirp in chirp_peaks_list:
            if len(chirp) <= 1: continue
            
            amps = env1_smooth[chirp]
            ref_amp = np.median(amps)
            valid_in_chirp = []
            allowed_var = params["amp_var"] * 1.2
            
            for i in range(len(chirp)):
                amp_deviation = abs(amps[i] - ref_amp) / (ref_amp + 1e-6)
                if amp_deviation <= allowed_var:
                    valid_in_chirp.append(chirp[i])
            
            if params["min_p"] <= len(valid_in_chirp) <= params["max_p"]:
                refined_chirps.append(valid_in_chirp)
                
        chirp_peaks_list = refined_chirps
        chirps = [len(cp) for cp in chirp_peaks_list]
        if len(chirps) == 0: raise ValueError("Nenhum chilreio validado após agrupamento.")

        media = statistics.mean(chirps)
        moda = CricketAnalyzer._safe_mode(chirps)

        return rate, data, data_b1, env1_smooth, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration_sec

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.algo_params = {
            "amp_min": 0.04, "amp_max": 1.00, "amp_var": 0.40,
            "dur_min": 14.0, "dur_max": 80.0,
            "gap_min": 25.0, "gap_max": 35.0,
            "min_p": 3, "max_p": 7,
            "b1_min": 3200, "b1_max": 6000
        }
        
        self.report_params = {
            "lang": "pt",
            "institution": "",
            "researcher_name": "",
            "role": "",
            "level": ""
        }
        
        self.load_settings()
        self.lang = self.report_params.get("lang", "pt")
        
        self.setWindowTitle(I18N[self.lang]["app_title"])
        self.setGeometry(100, 100, 1400, 850)
        self.setAcceptDrops(True)
        self.setWindowIcon(get_app_icon())
        
        # O Play agora usa transparência de fundo para não ficar torto e ter design clean.
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QWidget { color: #E0E0E0; font-family: 'Segoe UI'; }
            QSplitter::handle { background-color: #333; width: 4px; }
            QListWidget { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 5px; padding: 5px; outline: 0; }
            QListWidget::item { padding: 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #2196F3; color: white; font-weight: bold; }
            QListWidget::item:hover:!selected { background-color: #2A2A2A; }
            QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #1E88E5; }
            QPushButton:checked { background-color: #FF5252; }
            
            QPushButton#btn_play { 
                background-color: transparent; 
                color: #4CAF50; 
                font-size: 36px; 
                padding: 0px; 
                border: none; 
            }
            QPushButton#btn_play:hover { color: #66BB6A; }
            QPushButton#btn_play:pressed { color: #2E7D32; }
            QPushButton#btn_play:disabled { color: #424242; }
            
            QPushButton#btn_sidebar { background-color: transparent; font-size: 20px; color: #aaa; padding: 4px;}
            QPushButton#btn_sidebar:hover { color: white; background-color: #2D2D2D;}
            
            QSlider::groove:horizontal { border: 1px solid #333333; height: 6px; background: #2D2D2D; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #4CAF50; border-radius: 3px; }
            QSlider::handle:horizontal { background: white; border: 1px solid #4CAF50; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
            QLabel#lbl_resultados { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; padding: 15px; font-size: 13px; line-height: 1.5; }
        """)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.update_playback_cursor)
        self.player.durationChanged.connect(self.update_duration)
        
        self.loaded_files = {}
        self.cursor_lines = []
        self.backgrounds = [] 
        self.bg_cache_valid = False 
        
        self.panning = False
        self.active_ax = None
        self.expanded_panel = None
        self.spectro_engine = None
        self.line_engine = None
        
        self.last_draw_time = 0
        self.last_pan_time = 0
        self.sync_throttle_time = 0
        
        self.analysis_cache = {}
        self.active_heavy_data = {}
        
        self.setup_menu()
        self.setup_ui()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "algo_params" in data: self.algo_params.update(data["algo_params"])
                    if "report_params" in data: self.report_params.update(data["report_params"])
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}")

    def save_settings(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "algo_params": self.algo_params,
                    "report_params": self.report_params
                }, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, I18N[self.lang]["success"], I18N[self.lang]["config_saved"])
        except Exception as e:
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Failed to save:\n{e}")

    def setup_menu(self):
        self.menu_bar = self.menuBar()
        self.menu_bar.setStyleSheet("background-color: #1E1E1E; color: white; padding: 3px;")
        self.update_menu_text()

    def update_menu_text(self):
        self.menu_bar.clear()
        l = self.lang
        
        file_menu = self.menu_bar.addMenu(I18N[l]["file"])
        action_load = QAction(I18N[l]["load"], self)
        action_load.triggered.connect(self.action_load_wav)
        file_menu.addAction(action_load)
        
        action_save = QAction(I18N[l]["export"], self)
        action_save.triggered.connect(self.action_save_txt)
        file_menu.addAction(action_save)
        
        settings_menu = self.menu_bar.addMenu(I18N[l]["settings"])
        action_algo_config = QAction(I18N[l]["algo_settings"], self)
        action_algo_config.triggered.connect(self.open_algo_settings)
        settings_menu.addAction(action_algo_config)
        
        action_report_config = QAction(I18N[l]["gen_settings"], self)
        action_report_config.triggered.connect(self.open_report_settings)
        settings_menu.addAction(action_report_config)
        
        settings_menu.addSeparator()
        action_save_settings = QAction(I18N[l]["save_settings"], self)
        action_save_settings.triggered.connect(self.save_settings)
        settings_menu.addAction(action_save_settings)
        
        help_menu = self.menu_bar.addMenu(I18N[l]["help"])
        action_about = QAction(I18N[l]["about"], self)
        action_about.triggered.connect(self.open_about)
        help_menu.addAction(action_about)
        
        self.setWindowTitle(I18N[l]["app_title"])

    def setup_ui(self):
        l = self.lang
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # ---- PAINEL ESQUERDO ----
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        self.lbl_arquivos = QLabel(I18N[l]["files"])
        self.lbl_arquivos.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_file_selected)
        
        btn_layout = QHBoxLayout()
        self.btn_reanalisar = QPushButton(I18N[l]["reanalyze"])
        self.btn_reanalisar.clicked.connect(self.force_reanalyze)
        self.btn_remover = QPushButton(I18N[l]["remove"])
        self.btn_remover.setStyleSheet("background-color: #424242;")
        self.btn_remover.clicked.connect(self.remove_audio)
        
        btn_layout.addWidget(self.btn_reanalisar, stretch=3)
        btn_layout.addWidget(self.btn_remover, stretch=1)

        left_layout.addWidget(self.lbl_arquivos)
        left_layout.addWidget(self.list_widget)
        left_layout.addLayout(btn_layout)
        
        # ---- PAINEL DIREITO (PRINCIPAL) ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        top_right_layout = QHBoxLayout()
        
        # O botão de sidebar agora fica fixo na visualização principal para não sumir
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setObjectName("btn_sidebar")
        self.btn_toggle_sidebar.setFixedSize(36, 36)
        self.btn_toggle_sidebar.setToolTip(I18N[l]["toggle_panel"])
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        
        self.lbl_resultados = QLabel(I18N[l]["welcome"])
        self.lbl_resultados.setObjectName("lbl_resultados")
        self.lbl_resultados.setWordWrap(True)
        self.lbl_resultados.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.btn_sync = QPushButton(I18N[l]["sync"])
        self.btn_sync.setCheckable(True)
        self.btn_sync.setFixedWidth(200)
        
        top_right_layout.addWidget(self.btn_toggle_sidebar, alignment=Qt.AlignmentFlag.AlignTop)
        top_right_layout.addWidget(self.lbl_resultados, stretch=1)
        top_right_layout.addWidget(self.btn_sync, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        self.grid_graphs = QGridLayout()
        self.grid_graphs.setSpacing(10)
        
        self.panel1 = PlotPanel("wave", self.lang, self.toggle_expand)
        self.panel2 = PlotPanel("hist", self.lang, self.toggle_expand)
        self.panel3 = PlotPanel("freq", self.lang, self.toggle_expand)
        self.panel4 = PlotPanel("spec", self.lang, self.toggle_expand)
        
        self.grid_graphs.addWidget(self.panel1, 0, 0)
        self.grid_graphs.addWidget(self.panel2, 0, 1)
        self.grid_graphs.addWidget(self.panel3, 1, 0)
        self.grid_graphs.addWidget(self.panel4, 1, 1)
        
        self.all_panels = [self.panel1, self.panel2, self.panel3, self.panel4]
        for panel in self.all_panels:
            panel.canvas.mpl_connect("scroll_event", self.zoom_graph)
            panel.canvas.mpl_connect("button_press_event", self.on_press)
            panel.canvas.mpl_connect("button_release_event", self.on_release)
            panel.canvas.mpl_connect("motion_notify_event", self.on_motion)
            
        playback_layout = QHBoxLayout()
        playback_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("btn_play")
        self.btn_play.setFixedSize(50, 50)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_play.setEnabled(False)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)
        
        playback_layout.addWidget(self.btn_play)
        playback_layout.addWidget(self.slider)
        
        right_layout.addLayout(top_right_layout, stretch=1)
        right_layout.addLayout(self.grid_graphs, stretch=8)
        right_layout.addLayout(playback_layout, stretch=1)
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([250, 1150])
        
    def refresh_ui_texts(self):
        l = self.lang
        self.lbl_arquivos.setText(I18N[l]["files"])
        self.btn_reanalisar.setText(I18N[l]["reanalyze"])
        self.btn_remover.setText(I18N[l]["remove"])
        self.btn_sync.setText(I18N[l]["sync"])
        self.btn_toggle_sidebar.setToolTip(I18N[l]["toggle_panel"])
        if "carregar" in self.lbl_resultados.text().lower() or "load" in self.lbl_resultados.text().lower():
            self.lbl_resultados.setText(I18N[l]["welcome"])
        for p in self.all_panels:
            p.update_lang(l)
        self.update_menu_text()

    def toggle_sidebar(self):
        sizes = self.splitter.sizes()
        if sizes[0] == 0:
            self.splitter.setSizes([250, 1150])
        else:
            self.splitter.setSizes([0, 1400])

    def remove_audio(self):
        curr_item = self.list_widget.currentItem()
        if not curr_item: return
        fname = curr_item.text()
        
        if self.player.source().toLocalFile() == self.loaded_files.get(fname):
            self.player.stop()
            self.btn_play.setEnabled(False)
            self.btn_play.setText("▶")
            self.slider.setValue(0)
            
        if fname in self.loaded_files: del self.loaded_files[fname]
        if fname in self.analysis_cache: del self.analysis_cache[fname]
        
        self.list_widget.takeItem(self.list_widget.row(curr_item))
        
        if self.list_widget.count() == 0:
            for p in self.all_panels: p.ax.clear(); p.canvas.draw()
            self.lbl_resultados.setText(I18N[self.lang]["welcome"])

    def open_algo_settings(self):
        dialog = AlgoSettingsDialog(self.algo_params, self.lang, self)
        if dialog.exec():
            new_params = dialog.get_params()
            if new_params != self.algo_params:
                self.algo_params = new_params
                
                if self.analysis_cache:
                    reply = QMessageBox.question(self, "Reanalyze?", 
                        "Configurações alteradas! Deseja refazer as análises no cache?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        for fname in list(self.analysis_cache.keys()):
                            self.run_analysis(fname, self.algo_params, render=False)
                
                curr = self.list_widget.currentItem()
                if curr and curr.text() in self.analysis_cache:
                    self.render_dashboard(curr.text())

    def open_report_settings(self):
        dialog = GeneralSettingsDialog(self.report_params, self.lang, self)
        if dialog.exec():
            new_params = dialog.get_params()
            self.report_params = new_params
            if new_params["lang"] != self.lang:
                self.lang = new_params["lang"]
                self.refresh_ui_texts()

    def open_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def action_load_wav(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Load Audio Files", "", "WAV Files (*.wav)")
        for file_path in files:
            filename = os.path.basename(file_path)
            if filename not in self.loaded_files:
                self.loaded_files[filename] = file_path
                self.list_widget.addItem(filename)

    def action_save_txt(self):
        if not self.analysis_cache:
            QMessageBox.warning(self, "Aviso", "Cache vazio.")
            return
            
        now = datetime.datetime.now()
        default_name = f"Relatorio_Crinometro_{now.strftime('%d%m%Y_%M%H')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(self, I18N[self.lang]["export"], default_name, "Text Files (*.txt)")
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                inst = self.report_params.get('institution', '').strip()
                name = self.report_params.get('researcher_name', '').strip()
                role = self.report_params.get('role', '').strip()
                level = self.report_params.get('level', '').strip()
                
                header_lines = []
                if inst: header_lines.append(f"Instituição: {inst.upper()}")
                if name: header_lines.append(f"Pesquisador(a): {name}")
                if role: header_lines.append(f"Função: {role}")
                if level: header_lines.append(f"Grau Acadêmico: {level}")
                
                header_text = "\n".join(header_lines) + "\n\n" if header_lines else ""
                
                params_list = [d['params'] for d in self.analysis_cache.values()]
                all_same_params = all(p == params_list[0] for p in params_list)
                
                texto = (
                    f"RELATÓRIO MULTIPLEXADO DE ANÁLISE BIOACÚSTICA - CRINÔMETRO\n"
                    "==========================================================\n"
                    f"{header_text}"
                    f"Data da Geração: {now.strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"Total de Arquivos Compilados: {len(self.analysis_cache)}\n\n"
                )
                
                def get_pulse_distribution_text(chirps_list):
                    unique_p, counts_p = np.unique(chirps_list, return_counts=True)
                    dist_strs = [f"{int(cnt)} chilreiro(s) com {int(up)} pulso(s)" for up, cnt in zip(unique_p, counts_p)]
                    return "; ".join(dist_strs)

                if all_same_params:
                    p = params_list[0]
                    texto += (
                        "1. PARÂMETROS METODOLÓGICOS (CONFIGURAÇÕES GERAIS)\n"
                        "----------------------------------------------------------\n"
                        f"- Filtro de Amplitude: Mín={p['amp_min']} | Máx={p['amp_max']}\n"
                        f"- Limites de Duração de Pulso: {p['dur_min']}ms a {p['dur_max']}ms\n"
                        f"- Banda de Frequência Analisada: {p['b1_min']}Hz a {p['b1_max']}Hz\n\n"
                        "2. RESULTADOS POR ÁUDIO\n"
                        "----------------------------------------------------------\n\n"
                    )
                    
                    for fname, d in self.analysis_cache.items():
                        dist_text = get_pulse_distribution_text(d['chirps'])
                        texto += (
                            f"• ARQUIVO: {fname}\n"
                            f"  - Duração Total: {d['duration']:.2f} segundos\n"
                            f"  - Chilreios Validados: {len(d['chirps'])}\n"
                            f"  - Moda (Padrão): {d['moda']} pulsos/chilreio | Média: {d['media']:.2f}\n"
                            f"  - Distribuição: {dist_text}\n\n"
                        )
                else:
                    texto += "RESULTADOS DETALHADOS POR ÁUDIO\n"
                    for fname, d in self.analysis_cache.items():
                        texto += f"Arquivo: {fname} | Chilreios: {len(d['chirps'])}\n"
                        
                f.write(texto)
            QMessageBox.information(self, I18N[self.lang]["success"], "Relatório gerado.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.wav'):
                filename = os.path.basename(file_path)
                if filename not in self.loaded_files:
                    self.loaded_files[filename] = file_path
                    self.list_widget.addItem(filename)

    def force_reanalyze(self):
        curr_item = self.list_widget.currentItem()
        if not curr_item: return
        filename = curr_item.text()
        self.run_analysis(filename, self.algo_params, render=True)

    def on_file_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
            
        self.player.stop()
        self.btn_play.setText("▶")
        
        filename = selected_items[0].text()
        file_path = self.loaded_files[filename]
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.btn_play.setEnabled(True)
        
        if filename in self.analysis_cache:
            self.run_analysis(filename, self.analysis_cache[filename]["params"], render=True)
        else:
            self.run_analysis(filename, self.algo_params, render=True)
            
    def run_analysis(self, filename, params, render=True):
        file_path = self.loaded_files[filename]
        try:
            rate, data, data_b1, env, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration = CricketAnalyzer.analyze(file_path, params)
            
            self.analysis_cache[filename] = {
                "chirps": chirps, "media": media, "moda": moda, 
                "duration": audio_duration, "params": params.copy()
            }
            
            self.active_heavy_data = {
                "rate": rate, "data": data, "env": env, 
                "peaks": peaks, "chirps": chirps, "chirp_peaks_list": chirp_peaks_list, 
                "media": media, "moda": moda, "f_spec": f_spec, "t_spec": t_spec, 
                "Sxx_db": Sxx_db, "dom_freqs": dom_freqs, "duration": audio_duration,
                "params": params.copy()
            }
            
            if render:
                self.render_dashboard(filename)
                
        except Exception as e:
            QMessageBox.critical(self, I18N[self.lang]["error"], f"Falha no arquivo {filename}:\n{str(e)}")

    def render_dashboard(self, filename):
        d = self.active_heavy_data
        p = d["params"] 
        
        rate = d["rate"]
        data = d["data"]
        env = d["env"]
        chirp_peaks_list = d["chirp_peaks_list"]
        chirps = d["chirps"]
        f_spec = d["f_spec"]
        t_spec = d["t_spec"]
        Sxx_db = d["Sxx_db"]
        dom_freqs = d["dom_freqs"]

        p_txt = f"[Pulsos: {p['min_p']}-{p['max_p']} | Amp: {p['amp_min']}-{p['amp_max']} | Freq: {p['b1_min']}-{p['b1_max']}Hz]"
        
        res_text = (
            f"<h3 style='margin:0; color:#2196F3'>📄 {filename}</h3><hr style='border:1px solid #333'>"
            f"<b>Duração:</b> {d['duration']:.2f}s | <b>Parâmetros:</b> {p_txt}<br>"
            f"<b>Total:</b> {len(chirps)} chilreios. <b>Moda:</b> {d['moda']} | <b>Média:</b> {d['media']:.2f}.<br>"
        )
        self.lbl_resultados.setText(res_text)
        
        paleta_cores = ['#03A9F4', '#4CAF50', '#FF5252', '#E040FB', '#FFAB40', '#00E676', '#FF4081', '#FFEA00']
        
        picos_por_contagem = {}
        for cp in chirp_peaks_list:
            qnt = len(cp)
            if qnt not in picos_por_contagem: picos_por_contagem[qnt] = []
            picos_por_contagem[qnt].extend(cp)
            
        time_sec = np.arange(len(data)) / rate

        # -------------------------------------------------------------
        # AX1 (ONDA 1D - ENVELOPE)
        # -------------------------------------------------------------
        ax1 = self.panel1.ax
        ax1.clear()
        
        self.line_engine = HighPerfLineEngine(ax1, time_sec, data, update_bg_callback=self.capture_backgrounds)
        self.line_engine.render_high_detail()
        
        decimation_step_env = max(1, len(env) // 5000)
        ax1.plot(time_sec[::decimation_step_env], env[::decimation_step_env], color='#757575', alpha=0.5, zorder=2)
        
        for qnt, pks in sorted(picos_por_contagem.items()):
            cor = paleta_cores[qnt % len(paleta_cores)]
            pks_t = np.array(pks)/rate
            ax1.plot(pks_t, env[pks], "x", color=cor, markersize=8, markeredgewidth=2, zorder=3)

        # -------------------------------------------------------------
        # AX2 (HISTOGRAMA)
        # -------------------------------------------------------------
        ax2 = self.panel2.ax
        ax2.clear()
        unique_pulses, counts = np.unique(chirps, return_counts=True)
        cores_barras = [paleta_cores[x % len(paleta_cores)] for x in unique_pulses]
        bars = ax2.bar(unique_pulses, counts, color=cores_barras, edgecolor='#121212', linewidth=1.5)
        ax2.grid(axis='y', linestyle='--', color='#333333', alpha=0.6)
        for bar in bars:
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{int(bar.get_height())}', ha='center', va='bottom', color='#FFFFFF')
        ax2.set_xticks(unique_pulses)
        
        # -------------------------------------------------------------
        # AX3 (FREQ. DOMINANTE)
        # -------------------------------------------------------------
        ax3 = self.panel3.ax
        ax3.clear()
        ax3.scatter(t_spec, dom_freqs, c=dom_freqs, cmap='plasma', s=10, alpha=0.7, edgecolors='none')
        ax3.set_ylabel("Hz")
        for qnt, pks in sorted(picos_por_contagem.items()):
            cor = paleta_cores[qnt % len(paleta_cores)]
            pks_t = np.array(pks)/rate
            freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
            ax3.plot(pks_t, freqs_at_pks, "x", color=cor, markersize=8, markeredgewidth=2)

        # -------------------------------------------------------------
        # AX4 (ESPECTROGRAMA)
        # -------------------------------------------------------------
        ax4 = self.panel4.ax
        ax4.clear()
        ax4.set_ylabel("Hz")
        
        ax4.set_xlim(t_spec[0], t_spec[-1])
        ax4.set_ylim(p["b1_min"], p["b1_max"])
        
        self.spectro_engine = HighPerfSpectrogramEngine(ax4, Sxx_db, t_spec, f_spec, update_bg_callback=self.capture_backgrounds)
        self.spectro_engine.render_high_detail()
        
        for qnt, pks in sorted(picos_por_contagem.items()):
            cor = paleta_cores[qnt % len(paleta_cores)]
            pks_t = np.array(pks)/rate
            freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
            ax4.plot(pks_t, freqs_at_pks, "x", color=cor, markersize=7, markeredgewidth=1.5, zorder=2)
        
        self.cursor_lines = [
            ax1.axvline(x=0, color='#00E676', linewidth=2, linestyle='--', zorder=5),
            ax3.axvline(x=0, color='#00E676', linewidth=2, linestyle='--', zorder=5),
            ax4.axvline(x=0, color='#00E676', linewidth=2, linestyle='--', zorder=5)
        ]
        
        for panel in self.all_panels:
            panel.apply_dark_theme()
            panel.figure.tight_layout()
            
        self.capture_backgrounds()

    def capture_backgrounds(self):
        if not hasattr(self, 'cursor_lines') or not self.cursor_lines: return
        for line in self.cursor_lines:
            line.set_animated(False)
            line.set_visible(False)
        active_panels = [self.panel1, self.panel3, self.panel4]
        self.backgrounds = []
        for panel in active_panels:
            panel.canvas.draw()
            self.backgrounds.append(panel.canvas.copy_from_bbox(panel.ax.bbox))
        for line in self.cursor_lines:
            line.set_visible(True)
            line.set_animated(True)
        self.bg_cache_valid = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.expanded_panel is not None:
            self.toggle_expand(self.expanded_panel)
        else:
            super().keyPressEvent(event)

    def toggle_expand(self, panel):
        if self.expanded_panel is None:
            for p in self.all_panels:
                if p != panel: p.hide()
            panel.btn_expand.setText("🗗")
            self.expanded_panel = panel
        else:
            for p in self.all_panels: p.show()
            panel.btn_expand.setText("⛶")
            self.expanded_panel = None

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def update_duration(self, duration_ms):
        self.slider.setRange(0, duration_ms)

    def set_position(self, position_ms):
        self.player.setPosition(position_ms)
        self.update_playback_cursor(position_ms)

    def update_playback_cursor(self, position_ms):
        if not self.slider.isSliderDown(): 
            self.slider.setValue(position_ms)
        position_sec = position_ms / 1000.0
        for line in self.cursor_lines: 
            line.set_xdata([position_sec, position_sec])
            
        if not getattr(self, 'bg_cache_valid', False) or getattr(self, 'panning', False):
            current_time = time.time()
            if current_time - self.last_draw_time > 0.05:
                for panel in [self.panel1, self.panel3, self.panel4]: panel.canvas.draw_idle()
                self.last_draw_time = current_time
            return
        if not hasattr(self, 'backgrounds') or not self.backgrounds: return
        try:
            for i, panel in enumerate([self.panel1, self.panel3, self.panel4]):
                panel.canvas.restore_region(self.backgrounds[i])
                panel.ax.draw_artist(self.cursor_lines[i])
                panel.canvas.blit(panel.ax.bbox)
        except Exception: pass 

    def on_press(self, event):
        for panel in self.all_panels:
            if event.button == 1 and event.inaxes == panel.ax:
                self.panning, self.active_ax = True, event.inaxes
                self.start_xlim, self.start_ylim = self.active_ax.get_xlim(), self.active_ax.get_ylim()
                self.start_x, self.start_y = event.x, event.y
                self.bg_cache_valid = False
                for line in getattr(self, 'cursor_lines', []): line.set_animated(False)

    def on_release(self, event):
        if event.button == 1: 
            self.panning, self.active_ax = False, None
            if hasattr(self, 'expanded_panel') and self.expanded_panel:
                self.expanded_panel.canvas.draw_idle()
            else:
                for panel in self.all_panels: panel.canvas.draw_idle()
            QTimer.singleShot(150, self.capture_backgrounds)

    def _sync_render(self, target_panels, xmin, xmax):
        current_time = time.time()
        if current_time - self.sync_throttle_time < 0.042: return
        
        for panel in target_panels:
            ymin, ymax = panel.ax.get_ylim()
            if self.spectro_engine and panel == self.panel4:
                self.spectro_engine.render_interactive(xmin, xmax, ymin, ymax, is_sync=True)
            elif self.line_engine and panel == self.panel1:
                self.line_engine.render_interactive(xmin, xmax, is_sync=True)
            else:
                panel.canvas.draw_idle()
                
        self.sync_throttle_time = current_time

    def on_motion(self, event):
        if not self.panning or self.active_ax is None or event.inaxes != self.active_ax: return
        
        dx, dy = event.x - self.start_x, event.y - self.start_y
        x0, x1 = self.start_xlim
        y0, y1 = self.start_ylim
        bbox = self.active_ax.get_window_extent()
        if bbox.width == 0 or bbox.height == 0: return
        
        new_xmin = x0 - dx * (x1 - x0) / bbox.width
        new_xmax = x1 - dx * (x1 - x0) / bbox.width
        new_ymin = y0 - dy * (y1 - y0) / bbox.height
        new_ymax = y1 - dy * (y1 - y0) / bbox.height
        
        time_axes = [self.panel1.ax, self.panel3.ax, self.panel4.ax]
        is_time_axis = self.active_ax in time_axes
        
        if self.btn_sync.isChecked() and is_time_axis:
            for panel in [self.panel1, self.panel3, self.panel4]:
                panel.ax.set_xlim(new_xmin, new_xmax)
                if panel.ax == self.active_ax: panel.ax.set_ylim(new_ymin, new_ymax)
            self._sync_render([self.panel1, self.panel3, self.panel4], new_xmin, new_xmax)
        else:
            self.active_ax.set_xlim(new_xmin, new_xmax)
            self.active_ax.set_ylim(new_ymin, new_ymax)
            panel_mapping = {self.panel1.ax: self.panel1, self.panel2.ax: self.panel2, self.panel3.ax: self.panel3, self.panel4.ax: self.panel4}
            self._sync_render([panel_mapping[self.active_ax]], new_xmin, new_xmax)

    def zoom_graph(self, event):
        if not event.inaxes or QApplication.keyboardModifiers() != Qt.KeyboardModifier.ControlModifier: return
        
        self.bg_cache_valid = False
        for line in getattr(self, 'cursor_lines', []): line.set_animated(False)
            
        base_scale = 1.2
        scale = 1/base_scale if event.button == 'up' else base_scale if event.button == 'down' else None
        if not scale or event.xdata is None or event.ydata is None: return

        ax = event.inaxes
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        
        new_xw = (xmax - xmin) * scale
        rel_x = (event.xdata - xmin) / (xmax - xmin)
        new_xmin, new_xmax = event.xdata - new_xw * rel_x, event.xdata + new_xw * (1 - rel_x)
        
        new_yw = (ymax - ymin) * scale
        rel_y = (event.ydata - ymin) / (ymax - ymin)
        new_ymin, new_ymax = event.ydata - new_yw * rel_y, event.ydata + new_yw * (1 - rel_y)
        
        time_axes = [self.panel1.ax, self.panel3.ax, self.panel4.ax]
        is_time_axis = ax in time_axes
        
        if self.btn_sync.isChecked() and is_time_axis:
            for panel in [self.panel1, self.panel3, self.panel4]:
                panel.ax.set_xlim(new_xmin, new_xmax)
                if panel.ax == ax: panel.ax.set_ylim(new_ymin, new_ymax)
            self._sync_render([self.panel1, self.panel3, self.panel4], new_xmin, new_xmax)
        else:
            ax.set_xlim(new_xmin, new_xmax)
            ax.set_ylim(new_ymin, new_ymax)
            panel_mapping = {self.panel1.ax: self.panel1, self.panel2.ax: self.panel2, self.panel3.ax: self.panel3, self.panel4.ax: self.panel4}
            self._sync_render([panel_mapping[ax]], new_xmin, new_xmax)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())