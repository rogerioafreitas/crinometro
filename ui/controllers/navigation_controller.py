"""
ui/controllers/navigation_controller.py
--------------------------------------
FASE 4 — Navegação, viewport, pan, zoom, hover e background blitting.

Responsabilidade: Isolar eventos de mouse (on_press, on_release, on_motion,
zoom_graph, on_axes_leave), controle de viewport, pan interativo, zoom centrado,
sincronização horizontal, hover de metadados de pulsos e gestão do cache
necessário ao background blitting (cursor_lines, backgrounds, bg_cache_valid).

Comunicação semântica via sinais Qt:
  - viewport_changed(xmin, xmax)
  - hover_changed(payload)
  - pan_started()
  - pan_finished()

Consome PlotRenderers e SessionContext sem acoplamento reverso.
"""

import time
import weakref
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QToolTip


class NavigationController(QObject):
    """Controlador de navegação e interações de mouse do Crinômetro.

    Gerencia o estado e ciclo de vida de viewport, pan, zoom, sincronização
    temporal e cursor blitting para os painéis gráficos.
    """

    # Sinais semânticos (contrato FASE 4 §4.3)
    viewport_changed = pyqtSignal(float, float)
    hover_changed = pyqtSignal(object)
    pan_started = pyqtSignal()
    pan_finished = pyqtSignal()

    def __init__(
        self,
        session_context,
        plot_renderers=None,
        main_window=None,
        panel_wave=None,
        panel_spec=None,
        panel_hist=None,
        panel_psd=None,
        panel_freq=None,
        parent=None,
    ):
        super().__init__(parent)
        self.session_context = session_context
        self._plot_renderers = weakref.ref(plot_renderers) if plot_renderers is not None else lambda: None
        self._main_window = weakref.ref(main_window) if main_window is not None else lambda: None
        self._panel_wave = weakref.ref(panel_wave) if panel_wave is not None else lambda: None
        self._panel_spec = weakref.ref(panel_spec) if panel_spec is not None else lambda: None
        self._panel_hist = weakref.ref(panel_hist) if panel_hist is not None else lambda: None
        self._panel_psd = weakref.ref(panel_psd) if panel_psd is not None else lambda: None
        self._panel_freq = weakref.ref(panel_freq) if panel_freq is not None else lambda: None

        # Estado autoritativo de navegação e blitting (propriedade única de NavigationController)
        self.cursor_lines: list = []
        self.backgrounds: list = []
        self.bg_cache_valid: bool = False
        self.panning: bool = False
        self.active_ax = None
        self.start_xlim: tuple = (0.0, 1.0)
        self.start_ylim: tuple = (0.0, 1.0)
        self.start_x: float = 0.0
        self.start_y: float = 0.0
        self._last_pan_time: float = 0.0
        self.sync_throttle_time: float = 0.0
        self.last_draw_time: float = 0.0
        self._click_alignment_lines: list = []
        self.pulse_hover_data: list = []

        # Hook para edição de pulsos (FASE 5 / MainWindow)
        self.pulse_edit_handler = None

    # ------------------------------------------------------------------
    # Propriedades de acesso a componentes externos via weakref
    # ------------------------------------------------------------------

    @property
    def main_window(self):
        return self._main_window()

    @property
    def plot_renderers(self):
        return self._plot_renderers()

    def set_plot_renderers(self, plot_renderers):
        self._plot_renderers = weakref.ref(plot_renderers) if plot_renderers is not None else lambda: None

    @property
    def panel_wave(self):
        return self._panel_wave()

    @property
    def panel_spec(self):
        return self._panel_spec()

    @property
    def panel_hist(self):
        return self._panel_hist()

    @property
    def panel_psd(self):
        return self._panel_psd()

    @property
    def panel_freq(self):
        return self._panel_freq()

    @property
    def all_panels(self):
        return [
            p for p in (
                self.panel_wave,
                self.panel_spec,
                self.panel_hist,
                self.panel_psd,
                self.panel_freq,
            )
            if p is not None
        ]

    # ------------------------------------------------------------------
    # Background Blitting & Cursor Management
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reseta o estado de navegação, cursores e cache de background."""
        self.cursor_lines = []
        self.backgrounds = []
        self.bg_cache_valid = False
        self.panning = False
        self.active_ax = None
        self.start_xlim = (0.0, 1.0)
        self.start_ylim = (0.0, 1.0)
        self.start_x = 0.0
        self.start_y = 0.0
        self._last_pan_time = 0.0
        self.sync_throttle_time = 0.0
        self.last_draw_time = 0.0
        self._click_alignment_lines = []
        self.pulse_hover_data = []

    def setup_cursor_lines(self) -> list:
        """Cria e registra as linhas verticais de cursor nos eixos temporais (wave e spec)."""
        self.cursor_lines = []
        self.backgrounds = []
        self.bg_cache_valid = False
        for panel in [self.panel_wave, self.panel_spec]:
            if panel is not None and hasattr(panel, 'ax'):
                line = panel.ax.axvline(x=0, color='#E5E8EB', linewidth=1.2, linestyle='-', zorder=9)
                self.cursor_lines.append(line)
        return self.cursor_lines

    def capture_backgrounds(self) -> None:
        """Captura os bitmaps dos eixos temporais sem o cursor para blitting ultra-rápido."""
        if not self.cursor_lines:
            return
        for line in self.cursor_lines:
            line.set_animated(False)
            line.set_visible(False)
        active_panels = [p for p in (self.panel_wave, self.panel_spec) if p is not None]
        self.backgrounds = []
        for panel in active_panels:
            panel.canvas.draw()
            self.backgrounds.append(panel.canvas.copy_from_bbox(panel.ax.bbox))
        for line in self.cursor_lines:
            line.set_visible(True)
            line.set_animated(True)
        self.bg_cache_valid = True

    def update_playback_cursor(self, position_sec: float) -> None:
        """Atualiza a posição das linhas de cursor e realiza o blit nos eixos ativos."""
        for line in self.cursor_lines:
            try:
                line.set_xdata([position_sec, position_sec])
            except Exception:
                pass

        if not self.bg_cache_valid or self.panning:
            current_time = time.time()
            if current_time - self.last_draw_time > 0.01:
                for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
                    if panel is not None:
                        try:
                            panel.canvas.draw_idle()
                        except Exception:
                            pass
                self.last_draw_time = current_time
            return

        if not self.backgrounds:
            return

        try:
            active_panels = [p for p in (self.panel_wave, self.panel_spec) if p is not None]
            for panel, bg, line in zip(active_panels, self.backgrounds, self.cursor_lines):
                if bg is not None and hasattr(panel, 'ax') and panel.ax.bbox.width > 0 and panel.ax.bbox.height > 0:
                    panel.canvas.restore_region(bg)
                    panel.ax.draw_artist(line)
                    panel.canvas.blit(panel.ax.bbox)
        except Exception:
            self.bg_cache_valid = False
            for panel in [self.panel_wave, self.panel_freq, self.panel_spec]:
                if panel is not None:
                    try:
                        panel.canvas.draw_idle()
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Marcação de Clique & Alinhamento Temporal
    # ------------------------------------------------------------------

    def _align_click_marker(self, time_sec: float) -> None:
        """Desenha a referência vertical do clique em todos os eixos temporais."""
        for line in self._click_alignment_lines:
            try:
                line.remove()
            except Exception:
                pass
        self._click_alignment_lines = []
        for panel in (self.panel_wave, self.panel_freq, self.panel_spec):
            if panel is not None and hasattr(panel, 'figure'):
                for ax in panel.figure.axes:
                    self._click_alignment_lines.append(
                        ax.axvline(
                            x=time_sec, color="#FACC15", linewidth=1.0,
                            linestyle="--", alpha=0.75, zorder=8
                        )
                    )
                panel.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Limites e Clamping de Viewport
    # ------------------------------------------------------------------

    def _clamp_bounds(self, ax, xmin: float, xmax: float, ymin: float, ymax: float) -> tuple:
        """Restringe as coordenadas da viewport aos limites físicos do áudio e parâmetros."""
        if xmin > xmax:
            xmin, xmax = xmax, xmin
        if ymin > ymax:
            ymin, ymax = ymax, ymin
        d = self.session_context.active_heavy_data
        if not d:
            return xmin, xmax, ymin, ymax
        dur = float(d.get("duration", 0.0))
        rate = float(d.get("rate", 44100))
        nyq = rate / 2.0

        c_xmin, c_xmax, c_ymin, c_ymax = None, None, None, None

        if self.panel_wave is not None and ax == self.panel_wave.ax:
            c_xmin, c_xmax = 0.0, dur
            c_ymin, c_ymax = -1.05, 1.05
        elif self.panel_freq is not None and ax == self.panel_freq.ax:
            unit = getattr(self.panel_spec, "spec_unit", "kHz") if self.panel_spec is not None else "kHz"
            max_x = nyq / 1000.0 if unit == "kHz" else nyq
            c_xmin, c_xmax = 0.0, max_x

            Pxx_db = d.get("Pxx_db", [])
            if len(Pxx_db) > 0:
                yr = np.ptp(Pxx_db)
                c_ymin, c_ymax = np.min(Pxx_db) - yr * 0.1, np.max(Pxx_db) + yr * 0.1
        elif self.panel_spec is not None and ax == self.panel_spec.ax:
            c_xmin, c_xmax = 0.0, dur
            unit = getattr(self.panel_spec, "spec_unit", "kHz")
            c_ymin, c_ymax = 0.0, nyq / 1000.0 if unit == "kHz" else nyq
        elif self.panel_hist is not None and ax == self.panel_hist.ax:
            chirps = np.asarray(d.get("chirps", []))
            if chirps.size > 0:
                c_xmin, c_xmax = float(chirps.min()) - 0.65, float(chirps.min()) + 0.65
                ym = max(1, int(np.bincount(chirps.astype(int)).max()))
                c_ymin, c_ymax = 0, ym * 1.20

        # Clamping horizontal
        if c_xmin is not None and c_xmax is not None:
            if (xmax - xmin) > (c_xmax - c_xmin):
                xmin, xmax = c_xmin, c_xmax
            else:
                if xmin < c_xmin:
                    xmax += (c_xmin - xmin)
                    xmin = c_xmin
                if xmax > c_xmax:
                    xmin -= (xmax - c_xmax)
                    xmax = c_xmax

        # Clamping vertical
        if c_ymin is not None and c_ymax is not None:
            if (ymax - ymin) > (c_ymax - c_ymin):
                ymin, ymax = c_ymin, c_ymax
            else:
                if ymin < c_ymin:
                    ymax += (c_ymin - ymin)
                    ymin = c_ymin
                if ymax > c_ymax:
                    ymin -= (ymax - c_ymax)
                    ymax = c_ymax

        return xmin, xmax, ymin, ymax

    def is_sync_enabled(self) -> bool:
        """Informa se a sincronização horizontal entre eixos está ativa."""
        win = self.main_window
        if win is not None and hasattr(win, "btn_sync"):
            return bool(win.btn_sync.isChecked())
        return False

    # ------------------------------------------------------------------
    # Sincronização e Renderização Interativa
    # ------------------------------------------------------------------

    def _sync_render(self, target_panels, xmin: float, xmax: float) -> None:
        """Renderiza interativamente os painéis durante navegação e emite viewport_changed."""
        win = self.main_window
        if win is not None and getattr(win, "_swapping_panels", False):
            return
        current_time = time.time()
        if current_time - self.sync_throttle_time < 0.025:
            return

        pr = self.plot_renderers
        spectro_engine = pr.spectro_engine if pr is not None else getattr(win, "spectro_engine", None)
        line_engine = pr.line_engine if pr is not None else getattr(win, "line_engine", None)
        freq_engine = pr.freq_engine if pr is not None else getattr(win, "freq_engine", None)

        for panel in target_panels:
            if panel is None or not panel.isVisible():
                continue
            ymin, ymax = panel.ax.get_ylim()
            if spectro_engine and panel == self.panel_spec:
                spectro_engine.render_interactive(xmin, xmax, ymin, ymax, is_sync=True)
            elif line_engine and panel == self.panel_wave:
                line_engine.render_interactive(xmin, xmax, is_sync=True)
            elif freq_engine and panel == self.panel_freq:
                freq_engine.render_interactive(xmin, xmax, is_sync=True)
            else:
                panel.canvas.draw_idle()

        self.sync_throttle_time = current_time
        self.viewport_changed.emit(xmin, xmax)

    def _refresh_synced_views(self) -> None:
        """Redesenha os painéis depois que o Qt estabiliza as geometrias.
        Usa renderização de alta definição para evitar tiles/viewport cortados.
        """
        d = self.session_context.active_heavy_data
        if not d:
            return
        QApplication.processEvents()
        self.bg_cache_valid = False
        for line in self.cursor_lines:
            line.set_animated(False)
            line.set_visible(False)

        duration = float(d.get("duration", 0.0))
        p = d.get("params", {})
        if self.panel_wave is not None:
            self.panel_wave.ax.set_xlim(0.0, duration)
            self.panel_wave.ax.set_ylim(-1.05, 1.05)

        if self.panel_spec is not None:
            t_spec = d.get("t_spec", [])
            sx0 = float(t_spec[0]) if len(t_spec) else 0.0
            sx1 = float(t_spec[-1]) if len(t_spec) else duration
            self.panel_spec.ax.set_xlim(sx0, sx1)

            if hasattr(self.panel_spec, "spin_spec_ymin"):
                self.panel_spec.ax.set_ylim(
                    self.panel_spec.spin_spec_ymin.value(),
                    self.panel_spec.spin_spec_ymax.value(),
                )
            elif p:
                rate = float(d.get("rate", 44100.0))
                nyq = rate / 2.0
                unit = getattr(self.panel_spec, "spec_unit", "kHz")
                if unit == "kHz":
                    self.panel_spec.ax.set_ylim(0.0, nyq / 1000.0)
                else:
                    self.panel_spec.ax.set_ylim(0.0, nyq)

        pr = self.plot_renderers
        win = self.main_window
        spectro_engine = pr.spectro_engine if pr is not None else getattr(win, "spectro_engine", None)
        line_engine = pr.line_engine if pr is not None else getattr(win, "line_engine", None)
        freq_engine = pr.freq_engine if pr is not None else getattr(win, "freq_engine", None)

        if spectro_engine:
            spectro_engine.render_high_detail()
        if line_engine:
            line_engine.render_high_detail()
        if freq_engine:
            freq_engine.render_high_detail()

        for panel in self.all_panels:
            panel.canvas.draw()

        for line in self.cursor_lines:
            line.set_visible(True)
            line.set_animated(True)
        QTimer.singleShot(40, self.capture_backgrounds)

    def on_sync_toggled(self, enabled: bool) -> None:
        """Reestabelece uma geometria consistente nos eixos temporais ao alternar sincronização."""
        win = self.main_window
        if win is not None and getattr(win, "_swapping_panels", False):
            return
        self.bg_cache_valid = False
        for line in self.cursor_lines:
            line.set_animated(False)
        d = self.session_context.active_heavy_data
        if not d:
            return

        duration = float(d.get("duration", 0.0))
        if duration <= 0:
            return

        axes = [p.ax for p in (self.panel_wave, self.panel_spec) if p is not None]
        for ax in axes:
            ax.set_xlim(0.0, duration)
        if self.panel_wave is not None:
            self.panel_wave.ax.set_ylim(-1.05, 1.05)

        p = d.get("params", {})
        if self.panel_spec is not None and hasattr(self.panel_spec, "spin_spec_ymin"):
            self.panel_spec.ax.set_ylim(
                self.panel_spec.spin_spec_ymin.value(),
                self.panel_spec.spin_spec_ymax.value(),
            )
        elif p and self.panel_spec is not None:
            rate = float(d.get("rate", 44100.0))
            nyq = rate / 2.0
            unit = getattr(self.panel_spec, "spec_unit", "kHz")
            if unit == "kHz":
                self.panel_spec.ax.set_ylim(0.0, nyq / 1000.0)
            else:
                self.panel_spec.ax.set_ylim(0.0, nyq)

        QApplication.processEvents()
        self._refresh_synced_views()

    # ------------------------------------------------------------------
    # Tratamento de Eventos de Mouse (Press, Release, Motion, Zoom, Leave)
    # ------------------------------------------------------------------

    def on_press(self, event) -> None:
        """Gerencia cliques em painéis: alinhamento, edição de pulsos e início de pan."""
        # Alinha marcador vertical com botão esquerdo (button == 1)
        if event.button == 1 and event.xdata is not None:
            self._align_click_marker(float(event.xdata))

        # Determina qual painel foi clicado
        clicked_panel = None
        for panel in self.all_panels:
            if event.inaxes == panel.ax:
                clicked_panel = panel
                break

        # Se modo de edição está ativo e clicou com botão esquerdo em painel editável
        if (
            event.button == 1
            and clicked_panel
            and getattr(clicked_panel, 'pulse_edit_mode', False)
            and event.xdata is not None
        ):
            d = self.session_context.active_heavy_data
            if d:
                time_sec = float(event.xdata)
                kwargs = {"panel": clicked_panel, "event": event}
                if event.ydata is not None:
                    if clicked_panel == self.panel_spec:
                        unit = getattr(self.panel_spec, "spec_unit", "kHz")
                        kwargs["f_click"] = float(event.ydata) * (1000.0 if unit == "kHz" else 1.0)
                    elif clicked_panel == self.panel_wave:
                        kwargs["amp_click"] = float(event.ydata)

                # Delega ao handler de edição configurado ou à MainWindow
                if callable(self.pulse_edit_handler):
                    self.pulse_edit_handler(time_sec, **kwargs)
                    return
                win = self.main_window
                if win is not None and hasattr(win, "_toggle_peak_marker"):
                    win._toggle_peak_marker(time_sec, **kwargs)
                    return

        # Início de Arrastar / Pan com botão direito (button == 3)
        if clicked_panel and clicked_panel != self.panel_hist and event.button == 3:
            self.panning = True
            self.active_ax = event.inaxes
            self.start_xlim = self.active_ax.get_xlim()
            self.start_ylim = self.active_ax.get_ylim()
            self.start_x, self.start_y = event.x, event.y
            self.bg_cache_valid = False
            for line in self.cursor_lines:
                line.set_animated(False)
            self.pan_started.emit()

    def on_release(self, event) -> None:
        """Finaliza a operação de pan e agenda reconstrução do background blitting."""
        if event.button == 3:
            was_panning = self.panning
            self.panning = False
            self.active_ax = None
            for panel in self.all_panels:
                panel.canvas.draw_idle()

            QTimer.singleShot(350, self.capture_backgrounds)
            if was_panning:
                self.pan_finished.emit()

    def on_axes_leave(self, event) -> None:
        """Oculta o label de coordenadas e tooltip quando o cursor sai do eixo."""
        QToolTip.hideText()
        for panel in self.all_panels:
            if hasattr(panel, "coord_label") and event.inaxes == panel.ax:
                panel.coord_label.setVisible(False)

    def on_motion(self, event) -> None:
        """Manipula movimento do cursor: pan dinâmico, coordenadas e tooltip de hover."""
        # 1. Modo Pan ativo
        if self.panning and self.active_ax is not None and event.inaxes == self.active_ax:
            now_t = time.time()
            if now_t - self._last_pan_time < 0.018:
                return
            self._last_pan_time = now_t
            dx, dy = event.x - self.start_x, event.y - self.start_y
            x0, x1 = self.start_xlim
            y0, y1 = self.start_ylim
            bbox = self.active_ax.get_window_extent()
            if bbox.width == 0 or bbox.height == 0:
                return
            new_xmin = x0 - dx * (x1 - x0) / bbox.width
            new_xmax = x1 - dx * (x1 - x0) / bbox.width
            new_ymin = y0 - dy * (y1 - y0) / bbox.height
            new_ymax = y1 - dy * (y1 - y0) / bbox.height

            new_xmin, new_xmax, new_ymin, new_ymax = self._clamp_bounds(
                self.active_ax, new_xmin, new_xmax, new_ymin, new_ymax
            )

            time_axes = [p.ax for p in (self.panel_wave, self.panel_spec) if p is not None]
            if self.is_sync_enabled() and self.active_ax in time_axes:
                for panel in [self.panel_wave, self.panel_spec]:
                    if panel is not None:
                        panel.ax.set_xlim(new_xmin, new_xmax)
                        if panel.ax == self.active_ax:
                            if not (panel == self.panel_spec and getattr(self.panel_spec, "_y_locked", False)):
                                panel.ax.set_ylim(new_ymin, new_ymax)
                active_time_panels = [p for p in (self.panel_wave, self.panel_spec) if p is not None]
                self._sync_render(active_time_panels, new_xmin, new_xmax)
            else:
                self.active_ax.set_xlim(new_xmin, new_xmax)
                if not (self.panel_spec is not None and self.active_ax == self.panel_spec.ax and getattr(self.panel_spec, "_y_locked", False)):
                    self.active_ax.set_ylim(new_ymin, new_ymax)
                mapping = {p.ax: p for p in self.all_panels}
                if self.active_ax in mapping:
                    self._sync_render([mapping[self.active_ax]], new_xmin, new_xmax)

            if (
                self.panel_spec is not None
                and self.active_ax == self.panel_spec.ax
                and hasattr(self.panel_spec, "spin_spec_ymin")
            ):
                if not getattr(self.panel_spec, "_y_locked", False):
                    self.panel_spec.spin_spec_ymin.blockSignals(True)
                    self.panel_spec.spin_spec_ymax.blockSignals(True)
                    self.panel_spec.spin_spec_ymin.setValue(max(self.panel_spec.spin_spec_ymin.minimum(), new_ymin))
                    self.panel_spec.spin_spec_ymax.setValue(min(self.panel_spec.spin_spec_ymax.maximum(), new_ymax))
                    self.panel_spec.spin_spec_ymin.blockSignals(False)
                    self.panel_spec.spin_spec_ymax.blockSignals(False)
            return

        # 2. Tooltip de coordenadas em tempo real (quando não está em pan)
        if not self.panning:
            for panel in self.all_panels:
                if hasattr(panel, "coord_label"):
                    if event.inaxes == panel.ax and event.xdata is not None and event.ydata is not None:
                        if panel == self.panel_spec:
                            unit = getattr(self.panel_spec, "spec_unit", "kHz")
                            f_val = event.ydata if unit == "kHz" else event.ydata / 1000.0
                            panel.coord_label.setText(f"[ t: {event.xdata:.3f} s | f: {f_val:.2f} kHz ]")
                        elif panel == self.panel_wave:
                            panel.coord_label.setText(f"[ t: {event.xdata:.3f} s | amp: {event.ydata:+.4f} ]")
                        elif panel == self.panel_freq:
                            unit = getattr(self.panel_spec, "spec_unit", "kHz") if self.panel_spec is not None else "kHz"
                            panel.coord_label.setText(f"[ f: {event.xdata:.2f} {unit} | pot: {event.ydata:.1f} dB ]")
                        elif panel == self.panel_hist:
                            panel.coord_label.setText(f"[ pulsos: {int(event.xdata)} | contagem: {int(event.ydata)} ]")
                        else:
                            panel.coord_label.setText(f"[ x: {event.xdata:.3f} | y: {event.ydata:.3f} ]")
                        panel.coord_label.adjustSize()
                        panel.coord_label.setVisible(True)
                    else:
                        panel.coord_label.setVisible(False)

        # 3. Hover interativo em cima dos marcadores de pulsos
        if not self.panning and event.inaxes and event.xdata is not None and self.pulse_hover_data:
            ax = event.inaxes
            target_panel = None
            is_wave = (self.panel_wave is not None and ax == self.panel_wave.ax)
            is_freq = (self.panel_freq is not None and ax == self.panel_freq.ax)
            is_spec = (self.panel_spec is not None and ax == self.panel_spec.ax)

            if is_wave:
                target_panel = self.panel_wave
            elif is_freq:
                target_panel = self.panel_freq
            elif is_spec:
                target_panel = self.panel_spec

            if target_panel is not None:
                best_match = None
                min_pixel_dist = 20.0

                xlim = ax.get_xlim()
                bbox = ax.get_window_extent()
                px_per_sec = bbox.width / max(1e-6, (xlim[1] - xlim[0]))
                dt_max = max(0.04, 30.0 / max(1.0, px_per_sec))
                t_mouse = event.xdata

                unit = getattr(self.panel_spec, "spec_unit", "kHz") if self.panel_spec is not None else "kHz"
                spec_scale = 1000.0 if unit == "kHz" else 1.0

                for item in self.pulse_hover_data:
                    if abs(item["time"] - t_mouse) > dt_max:
                        continue

                    if is_wave:
                        y_val = item["env_y"]
                    elif is_spec:
                        y_val = item["freq_y"] / spec_scale
                    else:
                        y_val = item["freq_y"]

                    try:
                        pt_disp = ax.transData.transform((item["time"], y_val))
                        dx_pix = abs(pt_disp[0] - event.x)
                        dy_pix = abs(pt_disp[1] - event.y)
                        dist_pix = np.hypot(dx_pix, dy_pix)

                        if is_wave:
                            pt_zero = ax.transData.transform((item["time"], 0.0))
                            dist_zero = np.hypot(abs(pt_zero[0] - event.x), abs(pt_zero[1] - event.y))
                            dist_pix = min(dist_pix, dist_zero)

                        if dist_pix < min_pixel_dist:
                            min_pixel_dist = dist_pix
                            best_match = item
                    except Exception:
                        continue

                if best_match is not None:
                    if best_match.get("status") == "discarded":
                        t_val = best_match["time"]
                        f_val = best_match.get("freq_y", 0.0)
                        c_freq = best_match.get("carrier_freq", 0.0)
                        reason = best_match.get("reason", "Pulso descartado pelo filtro acústico")

                        freq_line = ""
                        if f_val > 0:
                            if c_freq > 0:
                                diff = f_val - c_freq
                                freq_line = f"<b>Frequência:</b> {f_val:.0f} Hz (Portadora: {c_freq:.0f} Hz | Desvio: {diff:+.0f} Hz)<br>"
                            else:
                                freq_line = f"<b>Frequência:</b> {f_val:.0f} Hz<br>"

                        msg = (
                            f"<div style='font-family: sans-serif; line-height: 1.35;'>"
                            f"<span style='color: #F87171; font-weight: 700;'>✖ Pulso Descartado</span><br>"
                            f"<b>Tempo:</b> {t_val:.3f} s<br>"
                            f"{freq_line}"
                            f"<b>Motivo:</b> <span style='color: #E2E8F0;'>{reason}</span>"
                            f"</div>"
                        )
                    else:
                        qnt = best_match["chirp_pulses"]
                        p_num = best_match["pulse_num"]
                        t_val = best_match["time"]
                        c_idx = best_match["chirp_idx"]
                        f_val = best_match.get("freq_y", 0.0)
                        freq_line = f"<br><b>Frequência:</b> {f_val:.0f} Hz" if f_val > 0 else ""
                        msg = (
                            f"<div style='font-family: sans-serif; line-height: 1.35;'>"
                            f"<b style='color: #38BDF8;'>Chilreio #{c_idx}: {qnt} pulsos</b><br>"
                            f"<b>Pulso:</b> {p_num} de {qnt}<br>"
                            f"<b>Tempo:</b> {t_val:.3f} s"
                            f"{freq_line}"
                            f"</div>"
                        )
                    QToolTip.showText(QCursor.pos(), msg, target_panel.canvas)
                    self.hover_changed.emit(best_match)
                    return
                else:
                    QToolTip.hideText()
                    self.hover_changed.emit(None)

    def zoom_graph(self, event) -> None:
        """Executa zoom focal centrado na coordenada do ponteiro do mouse."""
        if not event.inaxes:
            return
        self.bg_cache_valid = False
        for line in self.cursor_lines:
            line.set_animated(False)
        base_scale = 1.2
        scale = 1 / base_scale if event.button == 'up' else base_scale if event.button == 'down' else None
        if not scale or event.xdata is None or event.ydata is None:
            return
        ax = event.inaxes
        if self.panel_hist is not None and ax is self.panel_hist.ax:
            return

        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        dx = xmax - xmin
        dy = ymax - ymin
        if abs(dx) < 1e-9 or abs(dy) < 1e-9:
            return
        new_xw = dx * scale
        rel_x = (event.xdata - xmin) / dx
        new_xmin = event.xdata - new_xw * rel_x
        new_xmax = event.xdata + new_xw * (1 - rel_x)
        new_yw = dy * scale
        rel_y = (event.ydata - ymin) / dy
        new_ymin = event.ydata - new_yw * rel_y
        new_ymax = event.ydata + new_yw * (1 - rel_y)

        new_xmin, new_xmax, new_ymin, new_ymax = self._clamp_bounds(ax, new_xmin, new_xmax, new_ymin, new_ymax)

        time_axes = [p.ax for p in (self.panel_wave, self.panel_spec) if p is not None]
        if self.is_sync_enabled() and ax in time_axes:
            for panel in [self.panel_wave, self.panel_spec]:
                if panel is not None:
                    panel.ax.set_xlim(new_xmin, new_xmax)
                    if panel.ax == ax:
                        if not (panel == self.panel_spec and getattr(self.panel_spec, "_y_locked", False)):
                            panel.ax.set_ylim(new_ymin, new_ymax)
            active_time_panels = [p for p in (self.panel_wave, self.panel_spec) if p is not None]
            self._sync_render(active_time_panels, new_xmin, new_xmax)
        else:
            ax.set_xlim(new_xmin, new_xmax)
            if not (self.panel_spec is not None and ax == self.panel_spec.ax and getattr(self.panel_spec, "_y_locked", False)):
                ax.set_ylim(new_ymin, new_ymax)
            mapping = {p.ax: p for p in self.all_panels}
            if ax in mapping:
                self._sync_render([mapping[ax]], new_xmin, new_xmax)

        if (
            self.panel_spec is not None
            and ax == self.panel_spec.ax
            and hasattr(self.panel_spec, "spin_spec_ymin")
        ):
            if not getattr(self.panel_spec, "_y_locked", False):
                self.panel_spec.spin_spec_ymin.blockSignals(True)
                self.panel_spec.spin_spec_ymax.blockSignals(True)
                self.panel_spec.spin_spec_ymin.setValue(max(self.panel_spec.spin_spec_ymin.minimum(), new_ymin))
                self.panel_spec.spin_spec_ymax.setValue(min(self.panel_spec.spin_spec_ymax.maximum(), new_ymax))
                self.panel_spec.spin_spec_ymin.blockSignals(False)
                self.panel_spec.spin_spec_ymax.blockSignals(False)

    # ------------------------------------------------------------------
    # Atualização de Metadados de Hover
    # ------------------------------------------------------------------

    def update_hover_data(self, heavy_data=None) -> None:
        """Atualiza a tabela interna de metadados de pulsos para exibição nos tooltips de hover."""
        self.pulse_hover_data = []
        d = heavy_data if heavy_data is not None else self.session_context.active_heavy_data
        if not d:
            return
        rate = float(d.get("rate", 44100) or 44100)
        env = d.get("env1_smooth") if d.get("env1_smooth") is not None else d.get("env")
        if env is None:
            env = np.array([])
        chirp_peaks_list = d.get("chirp_peaks_list") or []
        dom_freqs = d.get("dom_freqs") if d.get("dom_freqs") is not None else np.array([])
        t_spec = d.get("t_spec") if d.get("t_spec") is not None else np.array([])
        carrier_freq = float(d.get("carrier_freq", 0.0) or 0.0)
        params = d.get("params") or {}
        freq_tol = float(params.get("freq_tolerance_hz", 700.0) or 700.0)

        # 1. Pulsos válidos agrupados em chilreios
        seen_samples = set()
        for c_idx, cp in enumerate(chirp_peaks_list):
            if cp is None:
                continue
            qnt = len(cp)
            for p_idx, pk in enumerate(cp):
                pk = int(pk)
                seen_samples.add(pk)
                t_val = float(pk) / rate
                y_env = float(env[pk]) if (env is not None and len(env) > pk) else 0.0
                if len(t_spec) > 0 and len(dom_freqs) > 0:
                    y_freq = float(np.interp(t_val, t_spec, dom_freqs))
                else:
                    y_freq = 0.0
                self.pulse_hover_data.append({
                    "sample": pk,
                    "time": t_val,
                    "env_y": y_env,
                    "freq_y": y_freq,
                    "chirp_pulses": qnt,
                    "chirp_idx": c_idx + 1,
                    "pulse_num": p_idx + 1,
                    "status": "valid",
                    "carrier_freq": carrier_freq,
                })

        # 2. Pulsos descartados
        distant_pks = d.get("distant_peaks") or []
        discarded_reasons = d.get("discarded_peaks_reasons") or {}

        for pk in distant_pks:
            pk = int(pk)
            if pk in seen_samples:
                continue
            t_val = float(pk) / rate
            y_env = float(env[pk]) if (env is not None and len(env) > pk) else 0.0
            if len(t_spec) > 0 and len(dom_freqs) > 0:
                y_freq = float(np.interp(t_val, t_spec, dom_freqs))
            else:
                y_freq = 0.0

            reason = discarded_reasons.get(pk)
            if not reason:
                if carrier_freq > 0 and abs(y_freq - carrier_freq) > freq_tol:
                    diff = y_freq - carrier_freq
                    reason = (
                        f"Frequência fora da tolerância da portadora "
                        f"({y_freq:.0f} Hz; desvio de {diff:+.0f} Hz da portadora {carrier_freq:.0f} Hz; limite ±{freq_tol:.0f} Hz)"
                    )
                else:
                    reason = "Pulso isolado / ruído fora do padrão rítmico focal"

            self.pulse_hover_data.append({
                "sample": pk,
                "time": t_val,
                "env_y": y_env,
                "freq_y": y_freq,
                "status": "discarded",
                "reason": reason,
                "carrier_freq": carrier_freq,
            })
