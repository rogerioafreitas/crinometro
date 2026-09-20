import weakref
import numpy as np
from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine, HighPerfFreqEngine

class PlotRenderers:
    def update_wave_visibility(self, show_raw, show_env, show_lod):
        if not hasattr(self, 'wave_lines'): return
        if 'raw' in self.wave_lines: self.wave_lines['raw'].set_visible(show_raw)
        if 'env' in self.wave_lines: self.wave_lines['env'].set_visible(show_env)
        if 'lod' in self.wave_lines: self.wave_lines['lod'].set_visible(show_lod)
        if getattr(self, 'line_engine', None) and self.line_engine.line:
            self.line_engine.line.set_visible(show_lod)
        
        self.panel_wave.canvas.draw_idle()

    def __init__(self, session_context, main_window=None, panel_wave=None, panel_spec=None, panel_hist=None, panel_psd=None, panel_freq=None):
        self.main_window = weakref.ref(main_window) if main_window else lambda: None
        self.session_context = session_context
        self._panel_wave = weakref.ref(panel_wave) if panel_wave else lambda: None
        self._panel_spec = weakref.ref(panel_spec) if panel_spec else lambda: None
        self._panel_hist = weakref.ref(panel_hist) if panel_hist else lambda: None
        self._panel_psd = weakref.ref(panel_psd) if panel_psd else lambda: None
        self._panel_freq = weakref.ref(panel_freq) if panel_freq else lambda: None
        self._wave_user_markers = []
        self._pulse_hover_data = []

    @property
    def panel_wave(self): return self._panel_wave()
    @property
    def panel_spec(self): return self._panel_spec()
    @property
    def panel_hist(self): return self._panel_hist()
    @property
    def panel_psd(self): return self._panel_psd()
    @property
    def panel_freq(self): return self._panel_freq()

    @property
    def all_panels(self):
        return [p for p in (self.panel_wave, self.panel_spec, self.panel_hist, self.panel_psd, self.panel_freq) if p]

    def render_dashboard(self, filename):
            cur_splitter_sizes = self.main_window().splitter.sizes() if hasattr(self.main_window(), "splitter") else None
            # Limpa referências a linhas de alinhamento do clique em eixos que serão
            # destruídos/recriados nesta renderização. Mantê-las causaria RuntimeError
            # ao chamar line.remove() na próxima chamada de _align_click_marker().
            self._click_alignment_lines = []
            d = self.session_context.active_heavy_data
            p = d.get("params") or {}
            rate = d["rate"]
            data = d["data"]
            env = d["env"]
            chirp_peaks_list = d["chirp_peaks_list"]
            chirps = d["chirps"]
            f_spec = d["f_spec"]
            t_spec = d["t_spec"]
            Sxx_db = d["Sxx_db"]
            dom_freqs = d["dom_freqs"]
    
            p_txt = f"[Pulsos: {p['min_p']}-{p['max_p']} | Amp: {p['amp_min']:.2f}-{p['amp_max']:.2f} | Freq: {int(p['b1_min'])}-{int(p['b1_max'])} Hz]"
            meta_str = f"Duração: {d['duration']:.2f}s   |   Parâmetros: {p_txt}"
            paleta_cores = ['#03A9F4', '#4CAF50', '#FF5252', '#E040FB', '#FFAB40', '#00E676', '#FF4081', '#FFEA00']
            # Visual solicitado: verde/orange/magenta como categorias dominantes.
            # Paleta canônica por quantidade de pulsos (2 a 10 + 1 extra para escopos maiores).
            # A mesma cor é usada no histograma, nos X da onda, frequência e espectrograma.
            pulse_colors = {
                2: '#2563EB',   # Azul Royal
                3: '#8B5CF6',   # Roxo / Violeta
                4: '#F97316',   # Laranja
                5: '#10B981',   # Verde Esmeralda
                6: '#EC4899',   # Rosa Magenta
                7: '#06B6D4',   # Ciano Turquesa
                8: '#EAB308',   # Amarelo Dourado
                9: '#6366F1',   # Índigo
                10: '#14B8A6',  # Teal Menta
            }
            extra_pulse_color = '#F43F5E'  # Vermelho Rubi (cor extra para > 10 pulsos ou outros escopos)
            marker_colors = pulse_colors
    
            picos_por_contagem = {}
            for cp in chirp_peaks_list:
                qnt = len(cp)
                picos_por_contagem.setdefault(qnt, []).extend(cp)
            time_sec = np.arange(len(data)) / rate
    
            # WAVE
            ax1 = self.panel_wave.ax
            ax1.clear()
            self.line_engine = HighPerfLineEngine(ax1, time_sec, data, base_color='#21A8D8', update_bg_callback=None)
            self.line_engine.render_high_detail()
            decimation = max(1, len(env) // 5000)
            ax1.plot(time_sec[::decimation], env[::decimation], color='#6E747C', alpha=0.55, linewidth=0.8, zorder=2)
    
            ax1.set_xlabel("seconds")
            ax1.set_ylabel("Amplitude")
            ax1.set_ylim(-1.05, 1.05)
    
            # HIST — fixo, sem drag/zoom, com índice de cores/pulsos no rodapé
            self._refresh_histogram()
    
            # FREQ (PSD)
            ax3 = self.panel_freq.ax
            ax3.clear()
            
            f_psd = self.session_context.active_heavy_data.get("f_psd", [])
            Pxx_db = self.session_context.active_heavy_data.get("Pxx_db", [])
            unit = getattr(self.panel_spec, "spec_unit", "kHz")
            scale = 1000.0 if unit == "kHz" else 1.0
            
            ax3.set_ylabel("Power (dB/Hz)")
            ax3.set_xlabel(f"Frequency ({unit})")
            
            if len(f_psd) > 0 and len(Pxx_db) > 0:
                ax3.plot(f_psd / scale, Pxx_db, color='#8B5CF6', linewidth=1.5, zorder=2)
                
                # Highlight carrier peak
                carrier_freq_hz = self.session_context.active_heavy_data.get("carrier_freq", 0.0)
                if carrier_freq_hz > 0:
                    # Encontra o índice no PSD mais próximo à portadora
                    idx_c = np.argmin(np.abs(f_psd - carrier_freq_hz))
                    carrier_x = f_psd[idx_c] / scale
                    carrier_y = Pxx_db[idx_c]
                else:
                    idx_max = np.argmax(Pxx_db)
                    carrier_x = f_psd[idx_max] / scale
                    carrier_y = Pxx_db[idx_max]
                    
                ax3.plot(carrier_x, carrier_y, 'ro', markersize=6, zorder=3)
                ax3.annotate(f"{carrier_x:.2f} {unit}", 
                             xy=(carrier_x, carrier_y), xytext=(5, 5),
                             textcoords='offset points', color='white',
                             fontsize=9, zorder=4)
                             
                # Limite superior para focar na banda acústica relevante de insetos (ou Nyquist)
                rate = self.session_context.active_heavy_data.get("rate", 44100)
                max_khz = min(15.0, rate / 2000.0)
                ax3.set_xlim(0.0, max_khz if unit == "kHz" else max_khz * 1000.0)
                
                y_range = np.ptp(Pxx_db) if len(Pxx_db) > 0 else 10
                ax3.set_ylim(np.min(Pxx_db) - y_range*0.1, np.max(Pxx_db) + y_range*0.1)
    
            self.freq_engine = None
    
            # SPEC
            ax4 = self.panel_spec.ax
            ax4.clear()
            unit = getattr(self.panel_spec, "spec_unit", "kHz")
            scale = 1000.0 if unit == "kHz" else 1.0
            ymin = self.panel_spec.spin_spec_ymin.value() if hasattr(self.panel_spec, "spin_spec_ymin") else 0.0
            ymax = self.panel_spec.spin_spec_ymax.value() if hasattr(self.panel_spec, "spin_spec_ymax") else (10.0 if unit == "kHz" else 10000.0)
            ax4.set_ylabel(unit)
            ax4.set_xlabel("seconds")
            ax4.set_xlim(t_spec[0], t_spec[-1])
            ax4.set_ylim(ymin, ymax)
            self.spectro_engine = HighPerfSpectrogramEngine(ax4, Sxx_db, t_spec, f_spec, update_bg_callback=None, unit=unit)
            self.spectro_engine.render_high_detail()
    
            # Atualiza mapa de eixos independente da posição atual.
            self.main_window().cursor_lines = []
            for panel in [self.panel_wave, self.panel_spec]:
                self.main_window().cursor_lines.append(panel.ax.axvline(x=0, color="#E5E8EB", linewidth=1.2, linestyle="-", zorder=9))
    
            for panel in self.all_panels:
                panel.apply_dark_theme()
            # Desenho inicial explícito: o histograma não participa do cache do cursor,
            # então precisa receber seu primeiro draw aqui para aparecer imediatamente.
            try:
                for panel in self.all_panels:
                    panel.canvas.draw()
            finally:
                pass
            markers = []
            for idx, cp in enumerate(chirp_peaks_list):
                if not cp:
                    continue
                t = float(cp[0] / rate)
                markers.append({"time": t, "color": "#F0A84B" if idx % 2 == 0 else "#3F94D5"})
            self._refresh_user_peak_markers()
            if cur_splitter_sizes and len(cur_splitter_sizes) >= 2 and cur_splitter_sizes[0] >= 50:
                self.main_window().splitter.setSizes(cur_splitter_sizes)
    
    def apply_spectrogram_y_limits(self, ymin, ymax, unit="kHz"):
            """Atualiza dinamicamente a escala, limites e unidade do eixo Y do espectrograma."""
            if not hasattr(self, "panel_spec"):
                return
            ax4 = self.panel_spec.ax
            unit_changed = (getattr(self, "_last_applied_spec_unit", None) != unit)
            self._last_applied_spec_unit = unit
    
            ax4.set_ylabel(unit)
            ax4.set_ylim(ymin, ymax)
            if hasattr(self, "spectro_engine") and self.spectro_engine:
                if unit_changed:
                    self.spectro_engine.set_unit(unit)
                self.spectro_engine.render_high_detail()
    
            if unit_changed and self.session_context.active_heavy_data:
                scale = 1000.0 if unit == "kHz" else 1.0
                rate = float(self.session_context.active_heavy_data.get("rate", 1.0))
                t_spec = self.session_context.active_heavy_data.get("t_spec")
                dom_freqs = self.session_context.active_heavy_data.get("dom_freqs")
                chirp_peaks_list = self.session_context.active_heavy_data.get("chirp_peaks_list", [])
                distant_pks = self.session_context.active_heavy_data.get("distant_peaks", [])
                env = self.session_context.active_heavy_data.get("env")
                marker_colors = {
                    1: '#F59E0B', 2: '#EC4899', 3: '#8B5CF6', 4: '#3B82F6',
                    5: '#10B981', 6: '#F97316', 7: '#06B6D4', 8: '#84CC16',
                    9: '#EAB308', 10: '#A855F7', 11: '#14B8A6', 12: '#6366F1'
                }
                lines_to_keep = set(getattr(self.main_window(), "cursor_lines", []) + getattr(self.main_window(), "_click_alignment_lines", []))
                lines_to_remove = [line for line in ax4.lines if line not in lines_to_keep]
                for line in lines_to_remove:
                    try:
                        line.remove()
                    except Exception:
                        pass
    
                picos_por_contagem = {}
                for cp in chirp_peaks_list:
                    qnt = len(cp)
                    picos_por_contagem.setdefault(qnt, []).extend(cp)
    
                if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
                    for qnt, pks in sorted(picos_por_contagem.items()):
                        pks_t = np.array(pks) / rate
                        freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs) / scale
                        ax4.plot(pks_t, freqs_at_pks, 'x', color=marker_colors.get(int(qnt), '#5F9ED1'), markersize=7, markeredgewidth=1.5, zorder=7)
                    if distant_pks:
                        valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                        if valid_d:
                            d_times = np.array(valid_d) / rate
                            d_freqs = np.interp(d_times, t_spec, dom_freqs) / scale
                            ax4.plot(d_times, d_freqs, 'x', color='#9CA3AF', markersize=4.5, markeredgewidth=1.0, alpha=0.6, zorder=6)
    
            self.panel_spec.canvas.draw_idle()
    
    def _refresh_histogram(self):
            """Redesenha o histograma bivariado: barras de contagem (eixo Y esquerdo)
            e linha de tendência de duração média do chilreio em ms (eixo Y direito)."""
            if not hasattr(self, 'panel_hist') or not self.session_context.active_heavy_data:
                return
            chirps = self.session_context.active_heavy_data.get('chirps', [])
            chirp_peaks_list = self.session_context.active_heavy_data.get('chirp_peaks_list', [])
            rate = float(self.session_context.active_heavy_data.get('rate', 1.0))
            pulse_colors = {
                2: '#2563EB',   # Azul Royal
                3: '#8B5CF6',   # Roxo / Violeta
                4: '#F97316',   # Laranja
                5: '#10B981',   # Verde Esmeralda
                6: '#EC4899',   # Rosa Magenta
                7: '#06B6D4',   # Ciano Turquesa
                8: '#EAB308',   # Amarelo Ouro
                9: '#84CC16',   # Verde Lima
                10: '#A855F7',  # Púrpura Forte
                1: '#94A3B8'    # Cinza ardósia
            }
            extra_pulse_color = '#F43F5E'
            hist_palette = pulse_colors
            
            ax_hist = self.panel_hist.ax
            ax_hist.clear()
            
            # Remove eixos secundários antigos para evitar acúmulo
            for child_ax in self.panel_hist.figure.get_axes():
                if child_ax is not ax_hist:
                    self.panel_hist.figure.delaxes(child_ax)
            
            if len(chirps) == 0:
                self.panel_hist.canvas.draw_idle()
                return
            
            unique_pulses, counts = np.unique(chirps, return_counts=True)
            bars = ax_hist.bar(
                unique_pulses, counts,
                color=[hist_palette.get(int(x), extra_pulse_color) for x in unique_pulses],
                edgecolor='none', linewidth=0, width=0.68, zorder=3
            )
            
            is_dark = getattr(self.main_window(), "theme_mode", "dark") == 'dark'
            ax_hist.grid(axis='y', color='#292D32' if is_dark else '#E2E8F0', linewidth=0.6, alpha=0.8, zorder=0)
            max_count = int(max(counts)) if len(counts) else 1
            hist_text_color = '#DDE1E5' if is_dark else '#1F2937'
            hist_tick_color = '#A9ADB5' if is_dark else '#1F2937'
            for bar in bars:
                ax_hist.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max_count*0.025, str(int(bar.get_height())),
                         ha='center', va='bottom', color=hist_text_color, fontsize=8.5, fontweight='bold')
            ax_hist.set_xticks(unique_pulses)
            ax_hist.set_xlabel("")
            ax_hist.set_ylabel("")
            ax_hist.tick_params(axis='x', labelsize=8.5, colors=hist_tick_color, length=0)
            ax_hist.tick_params(axis='y', labelsize=8, colors=hist_tick_color)
            ax_hist.set_ylim(0, max_count * 1.20)
            
            # ——— Eixo Y secundário: Duração média do chilreio (ms) ———
            dur_color = '#FF6B6B' if is_dark else '#DC2626'
            
            # Calcular duração média por classe de pulsos
            duration_by_class = {}
            for cp in chirp_peaks_list:
                n_pulses = len(cp)
                if n_pulses >= 1 and rate > 0:
                    dur_ms = (cp[-1] - cp[0]) / rate * 1000.0
                    duration_by_class.setdefault(n_pulses, []).append(dur_ms)
            
            avg_durations = {}
            for n_p, durs in duration_by_class.items():
                avg_durations[n_p] = float(np.mean(durs))
            
            if len(avg_durations) >= 2:
                ax2 = ax_hist.twinx()
                # Armazenar referência para o tema poder estilizar
                self.panel_hist._ax2 = ax2
                
                sorted_classes = sorted(avg_durations.keys())
                x_pts = np.array(sorted_classes, dtype=float)
                y_pts = np.array([avg_durations[k] for k in sorted_classes], dtype=float)
                
                ax2.plot(x_pts, y_pts, color=dur_color, linewidth=1.5, linestyle='--',
                         marker='o', markersize=5, markerfacecolor=dur_color,
                         markeredgecolor='white' if is_dark else '#1F2937',
                         markeredgewidth=0.8, zorder=5, alpha=0.9)
                
                # Anotações discretas de duração sobre cada marcador
                for xv, yv in zip(x_pts, y_pts):
                    ax2.annotate(f'{yv:.0f}', (xv, yv), textcoords='offset points',
                                 xytext=(0, 7), ha='center', fontsize=6.5,
                                 color=dur_color, fontweight='bold')
                
                dur_label_color = dur_color
                ax2.set_ylabel("Duração (ms)", fontsize=7.5, color=dur_label_color)
                ax2.tick_params(axis='y', labelsize=7, colors=dur_label_color, length=2)
                for sp in ax2.spines.values():
                    sp.set_visible(False)
                ax2.spines['right'].set_visible(True)
                ax2.spines['right'].set_color(dur_color)
                ax2.spines['right'].set_linewidth(0.8)
                ax2.spines['right'].set_alpha(0.5)
                ax2.grid(False)
                
                # Margem vertical para não colar nos limites
                y_min_d = min(y_pts) * 0.85 if min(y_pts) > 0 else 0
                y_max_d = max(y_pts) * 1.20
                ax2.set_ylim(y_min_d, y_max_d)
                ax2.set_facecolor('none')
            else:
                self.panel_hist._ax2 = None
            
            # ——— Legenda unificada ———
            from matplotlib.patches import Patch
            from matplotlib.lines import Line2D
            legend_handles = [Patch(facecolor=hist_palette.get(int(x), extra_pulse_color), edgecolor='none', label=f'{int(x)} pulsos')
                              for x in unique_pulses]
            if len(avg_durations) >= 2:
                legend_handles.append(Line2D([0], [0], color=dur_color, linewidth=1.5, linestyle='--',
                                             marker='o', markersize=4, label='Duração (ms)'))
            if legend_handles:
                hist_w = self.panel_hist.width()
                leg_ncol = min(3 if hist_w < 340 else 4, len(legend_handles))
                leg_fs = 7.0 if hist_w < 280 else (7.5 if hist_w < 340 else 8.0)
                leg = ax_hist.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.11),
                                 ncol=leg_ncol, frameon=False, fontsize=leg_fs, handlelength=0.9,
                                 columnspacing=0.5, borderaxespad=0.0)
                leg.get_frame().set_facecolor((0, 0, 0, 0))
                leg.get_frame().set_alpha(0.0)
                leg.get_frame().set_edgecolor((0, 0, 0, 0))
                leg.get_frame().set_linewidth(0)
                for text in leg.get_texts():
                    text.set_color(hist_tick_color)
            
            self.panel_hist.canvas.draw_idle()
    
    def _refresh_user_peak_markers(self):
            """Renderiza marcadores de picos do usuário em todos os gráficos relevantes (onda, freq, spec)."""
            if not hasattr(self, 'panel_wave'):
                return
            
            # Limpa marcadores antigos de todos os painéis
            for artist in getattr(self, '_wave_user_markers', []):
                try:
                    artist.remove()
                except Exception:
                    pass
            self._wave_user_markers = []
    
            if not self.session_context.active_heavy_data:
                return
    
            rate = float(self.session_context.active_heavy_data.get('rate', 1.0))
            t_spec = self.session_context.active_heavy_data.get('t_spec', [])
            dom_freqs = self.session_context.active_heavy_data.get('dom_freqs', [])
            env = self.session_context.active_heavy_data.get('env')
            
            # 1. Desenhar marcadores de chirps classificados
            chirp_peaks_list = self.session_context.active_heavy_data.get('chirp_peaks_list', [])
            picos_por_contagem = {}
            for cp in chirp_peaks_list:
                qnt = len(cp)
                picos_por_contagem.setdefault(qnt, []).extend(cp)
                
            pulse_colors = {
                2: '#2563EB',   # Azul Royal
                3: '#8B5CF6',   # Roxo / Violeta
                4: '#F97316',   # Laranja
                5: '#10B981',   # Verde Esmeralda
                6: '#EC4899',   # Rosa Magenta
                7: '#06B6D4',   # Ciano Turquesa
                8: '#EAB308',   # Amarelo Ouro
                9: '#84CC16',   # Verde Lima
                10: '#A855F7',  # Púrpura Forte
                1: '#94A3B8'    # Cinza ardósia
            }
            extra_pulse_color = '#F43F5E'
            
            # 2. Distant Peaks
            distant_pks = self.session_context.active_heavy_data.get('distant_peaks', [])
            
            ax1 = getattr(self.panel_wave, 'ax', None)
            ax3 = getattr(self.panel_freq, 'ax', None)
            ax4 = getattr(self.panel_spec, 'ax', None)
            
            if ax1 and env is not None:
                for qnt, pks in sorted(picos_por_contagem.items()):
                    pks_t = np.array(pks) / rate
                    lines = ax1.plot(pks_t, env[pks], 'x', color=pulse_colors.get(int(qnt), extra_pulse_color), markersize=7, markeredgewidth=1.7, zorder=7)
                    self._wave_user_markers.extend(lines)
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if 0 <= dp < len(env)]
                    if valid_d:
                        lines = ax1.plot(np.array(valid_d) / rate, env[valid_d], 'x', color='#64748B', markersize=5.5, markeredgewidth=1.1, alpha=0.55, zorder=5)
                        self._wave_user_markers.extend(lines)
    
            if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
                pulse_meta = self.session_context.pulse_metadata
                
                def get_freqs_for_peaks(pks):
                    pks_t = np.array(pks) / rate
                    f = np.interp(pks_t, t_spec, dom_freqs)
                    for i, p in enumerate(pks):
                        if p in pulse_meta and "freq" in pulse_meta[p]:
                            f[i] = pulse_meta[p]["freq"]
                    return pks_t, f
    
                if ax3:
                    for qnt, pks in sorted(picos_por_contagem.items()):
                        pks_t, freqs_at_pks = get_freqs_for_peaks(pks)
                        lines = ax3.plot(pks_t, freqs_at_pks, 'x', color=pulse_colors.get(int(qnt), '#5F9ED1'), markersize=6, markeredgewidth=1.4, zorder=7)
                        self._wave_user_markers.extend(lines)
                    if distant_pks:
                        valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                        if valid_d:
                            d_times, d_freqs = get_freqs_for_peaks(valid_d)
                            lines = ax3.plot(d_times, d_freqs, 'x', color='#64748B', markersize=5, markeredgewidth=1.1, alpha=0.55, zorder=5)
                            self._wave_user_markers.extend(lines)
    
                if ax4:
                    unit = getattr(self.panel_spec, "spec_unit", "kHz")
                    scale = 1000.0 if unit == "kHz" else 1.0
                    for qnt, pks in sorted(picos_por_contagem.items()):
                        pks_t, freqs_at_pks = get_freqs_for_peaks(pks)
                        lines = ax4.plot(pks_t, freqs_at_pks / scale, 'x', color=pulse_colors.get(int(qnt), '#5F9ED1'), markersize=7, markeredgewidth=1.5, zorder=7)
                        self._wave_user_markers.extend(lines)
                    if distant_pks:
                        valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                        if valid_d:
                            d_times, d_freqs = get_freqs_for_peaks(valid_d)
                            lines = ax4.plot(d_times, d_freqs / scale, 'x', color='#94A3B8', markersize=5, markeredgewidth=1.0, alpha=0.5, zorder=5)
                            self._wave_user_markers.extend(lines)
    
            # 3. Marcadores do Usuário (Adicionados, Confirmados, Removidos)
            if self.session_context.peaks_user_verified and self.session_context.peaks_detected:
                peaks_detected_set = set(int(p) for p in self.session_context.peaks_detected)
                peaks_verified_set = set(int(p) for p in self.session_context.peaks_user_verified)
    
                peaks_confirmed = sorted(peaks_verified_set & peaks_detected_set)
                peaks_added = sorted(peaks_verified_set - peaks_detected_set)
                peaks_removed = sorted(peaks_detected_set - peaks_verified_set)
    
                if ax1:
                    if peaks_confirmed:
                        xdata = np.asarray(peaks_confirmed, dtype=float) / rate
                        scatter = ax1.scatter(xdata, np.zeros_like(xdata), s=60, marker='o', 
                                             color='#10B981', edgecolors='#047857', linewidths=1.5, zorder=4)
                        self._wave_user_markers.append(scatter)
    
                    if peaks_added:
                        xdata = np.asarray(peaks_added, dtype=float) / rate
                        scatter = ax1.scatter(xdata, np.zeros_like(xdata), s=60, marker='^', 
                                             color='#3B82F6', edgecolors='#1E40AF', linewidths=1.5, zorder=4)
                        self._wave_user_markers.append(scatter)
    
                    if peaks_removed:
                        xdata = np.asarray(peaks_removed, dtype=float) / rate
                        scatter = ax1.scatter(xdata, np.zeros_like(xdata), s=80, marker='x', 
                                             color='#EF4444', linewidths=2.0, zorder=4)
                        self._wave_user_markers.append(scatter)
    
                if t_spec is not None and len(t_spec) > 0 and dom_freqs is not None and len(dom_freqs) > 0:
                    for peaks, color, marker in [
                        (peaks_confirmed, '#10B981', 'o'),
                        (peaks_added, '#3B82F6', '^'),
                        (peaks_removed, '#EF4444', 'x'),
                    ]:
                        if peaks:
                            pks_t = np.asarray(peaks, dtype=float) / rate
                            freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs)
                            
                            # Usa a frequência manual exata caso o usuário tenha clicado no espectrograma
                            pulse_meta = self.session_context.pulse_metadata
                            for i, p in enumerate(peaks):
                                if p in pulse_meta and "freq" in pulse_meta[p]:
                                    freqs_at_pks[i] = pulse_meta[p]["freq"]
                            
                            if ax3:
                                lines = ax3.plot(pks_t, freqs_at_pks, marker=marker, linestyle='none',
                                                color=color, markersize=8, markeredgewidth=1.2, zorder=4)
                                self._wave_user_markers.extend(lines)
                                
                            if ax4:
                                unit = getattr(self.panel_spec, "spec_unit", "kHz")
                                scale = 1000.0 if unit == "kHz" else 1.0
                                freqs_at_pks_spec = freqs_at_pks / scale
                                lines = ax4.plot(pks_t, freqs_at_pks_spec, marker=marker, linestyle='none',
                                                color=color, markersize=8, markeredgewidth=1.2, zorder=4)
                                self._wave_user_markers.extend(lines)
            for panel in self.all_panels:
                try:
                    panel.canvas.draw_idle()
                except Exception:
                    pass