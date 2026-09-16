"""
Crinômetro - Motores de Renderização Gráfica de Alta Performance (Matplotlib).
"""
import numpy as np
from PyQt6.QtCore import QTimer

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
        
        pts = 300 if is_sync else 500 
        t_env, y_env = self._get_envelope(self.time_sec[t0:t1], self.data[t0:t1], max_points=pts)
        self._update_plot(t_env, y_env)
        
        self.debounce_timer.start(150 if is_sync else 120)

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
    def __init__(self, ax, Sxx_db, t_spec, f_spec, update_bg_callback=None, unit="kHz"):
        self.ax = ax
        self.Sxx_db = Sxx_db
        self.t_spec = t_spec
        self.f_spec = f_spec
        self.update_bg_callback = update_bg_callback
        self.image = None
        self.unit = unit
        self.scale = 1000.0 if unit == "kHz" else 1.0
        
        self.tile_cache = {}
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.render_high_detail)

    def set_unit(self, unit):
        if self.unit != unit:
            self.unit = unit
            self.scale = 1000.0 if unit == "kHz" else 1.0
            self.tile_cache.clear()
            if self.image is not None:
                try:
                    self.image.remove()
                except Exception:
                    pass
                self.image = None
        
    def get_viewport_slice(self, xmin, xmax, ymin, ymax):
        ymin_hz = ymin * self.scale
        ymax_hz = ymax * self.scale
        t_idx_min = max(0, np.searchsorted(self.t_spec, xmin) - 1)
        t_idx_max = min(len(self.t_spec), np.searchsorted(self.t_spec, xmax) + 1)
        f_idx_min = max(0, np.searchsorted(self.f_spec, ymin_hz) - 1)
        f_idx_max = min(len(self.f_spec), np.searchsorted(self.f_spec, ymax_hz) + 1)
        
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
        y0 = float(self.f_spec[f0] / self.scale)
        y1 = float(self.f_spec[f1-1] / self.scale)
        self._update_imshow(sliced_data, float(self.t_spec[t0]), float(self.t_spec[t1-1]), y0, y1)
        
        self.debounce_timer.start(250 if is_sync else 200)
        
    def render_high_detail(self):
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        
        cache_key = (round(xmin, 1), round(xmax, 1), round(ymin, 2), round(ymax, 2), self.unit)
        
        if cache_key in self.tile_cache:
            high_res_data, extent = self.tile_cache[cache_key]
            self._update_imshow(high_res_data, *extent)
        else:
            t0, t1, f0, f1 = self.get_viewport_slice(xmin, xmax, ymin, ymax)
            high_res_data = self.Sxx_db[f0:f1, t0:t1]
            y0 = float(self.f_spec[f0] / self.scale)
            y1 = float(self.f_spec[f1-1] / self.scale)
            extent = (float(self.t_spec[t0]), float(self.t_spec[t1-1]), y0, y1)
            
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
# 3. ENGINE GRÁFICA DE ALTA PERFORMANCE (FREQUÊNCIA DOMINANTE)
# ==========================================
class HighPerfFreqEngine:
    def __init__(self, ax, t_spec, dom_freqs, base_color='#8B5CF6', update_bg_callback=None):
        self.ax = ax
        self.t_spec = t_spec
        self.dom_freqs = dom_freqs
        self.base_color = base_color
        self.update_bg_callback = update_bg_callback
        self.line = None
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.render_high_detail)

    def get_viewport_slice(self, xmin, xmax):
        t0 = max(0, int(np.searchsorted(self.t_spec, xmin)) - 1)
        t1 = min(len(self.t_spec), int(np.searchsorted(self.t_spec, xmax)) + 1)
        if t1 <= t0:
            t1 = t0 + 2
        return t0, t1

    def render_interactive(self, xmin, xmax, is_sync=False):
        self.debounce_timer.stop()
        t0, t1 = self.get_viewport_slice(xmin, xmax)
        length = t1 - t0
        step = max(1, length // (300 if is_sync else 500))
        t_sub = self.t_spec[t0:t1:step]
        y_sub = self.dom_freqs[t0:t1:step]
        self._update_plot(t_sub, y_sub)
        self.debounce_timer.start(150 if is_sync else 120)

    def render_high_detail(self):
        xmin, xmax = self.ax.get_xlim()
        t0, t1 = self.get_viewport_slice(xmin, xmax)
        length = t1 - t0
        step = max(1, length // 2500)
        t_sub = self.t_spec[t0:t1:step]
        y_sub = self.dom_freqs[t0:t1:step]
        self._update_plot(t_sub, y_sub)
        if self.update_bg_callback:
            QTimer.singleShot(50, self.update_bg_callback)

    def _update_plot(self, t, y):
        if self.line is None:
            self.line, = self.ax.plot(t, y, '.', color=self.base_color, markersize=2.2, alpha=0.72, zorder=2)
        else:
            self.line.set_data(t, y)
        self.ax.figure.canvas.draw_idle()



