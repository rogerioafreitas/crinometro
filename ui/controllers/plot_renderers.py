"""
ui/controllers/plot_renderers.py
---------------------------------
FASE 3 — Renderização desacoplada dos painéis.

Responsabilidade: coordenar as engines gráficas existentes e concentrar a
renderização dos quatro painéis sem assumir a lógica de navegação do mouse.

O PlotRenderers lê o SessionContext e recebe referências controladas aos
PlotPanels e à MainWindow via weakref.

Dívida técnica transitória (FASE 4): os callbacks de background update
(update_bg_callback=win.capture_backgrounds) passados aos engines HighPerf
mantêm referências bound à MainWindow até o isolamento completo da navegação,
hover e blitting no NavigationController (FASE 4).

A navegação (pan/zoom/hover/blit) permanece na MainWindow até a FASE 4.
"""

import weakref
import numpy as np
from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine


class PlotRenderers:
    """Controlador de renderização dos painéis gráficos do Crinômetro.

    Lê estado exclusivamente de ``session_context`` e via referências aos
    painéis. Nunca armazena cópia autoritativa de estado analítico.

    Operações semânticas públicas
    ─────────────────────────────
    render_file(filename)   — renderização completa de um arquivo analisado
    refresh_histogram()     — redesenha apenas o histograma bivariado
    refresh_markers()       — redesenha apenas os marcadores de picos/pulsos
    refresh_all()           — delega para render_file com o arquivo ativo

    Os métodos privados (_refresh_histogram, _refresh_user_peak_markers,
    apply_spectrogram_y_limits, update_wave_visibility) mantêm as assinaturas
    originais para compatibilidade com os stubs de delegação da MainWindow.
    """

    # ------------------------------------------------------------------
    # Construção e propriedades de painéis
    # ------------------------------------------------------------------

    def __init__(
        self,
        session_context,
        main_window=None,
        panel_wave=None,
        panel_spec=None,
        panel_hist=None,
        panel_psd=None,
        panel_freq=None,
    ):
        self.session_context = session_context
        self._main_window = weakref.ref(main_window) if main_window is not None else lambda: None
        self._panel_wave = weakref.ref(panel_wave) if panel_wave is not None else lambda: None
        self._panel_spec = weakref.ref(panel_spec) if panel_spec is not None else lambda: None
        self._panel_hist = weakref.ref(panel_hist) if panel_hist is not None else lambda: None
        self._panel_psd = weakref.ref(panel_psd) if panel_psd is not None else lambda: None
        self._panel_freq = weakref.ref(panel_freq) if panel_freq is not None else lambda: None

        # Estado interno de renderização (propriedade de PlotRenderers, não do SessionContext)
        self.wave_lines: dict = {}
        self._wave_user_markers: list = []
        self.line_engine = None
        self.spectro_engine = None
        self.freq_engine = None
        self._last_applied_spec_unit = None

    @property
    def main_window(self):
        return self._main_window()

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
    # Operações semânticas públicas (contrato FASE 3 §3.3)
    # ------------------------------------------------------------------

    def render_file(self, filename: str) -> None:
        """Renderização completa de um arquivo analisado.

        Delega para render_dashboard, que contém a implementação canônica
        extraída da MainWindow com fidelidade comportamental total.
        """
        self.render_dashboard(filename)

    def refresh_histogram(self) -> None:
        """Redesenha apenas o histograma bivariado."""
        self._refresh_histogram()

    def refresh_markers(self) -> None:
        """Redesenha apenas os marcadores de picos/pulsos do usuário."""
        self._refresh_user_peak_markers()

    def refresh_all(self) -> None:
        """Re-renderiza o arquivo ativo completo (se houver)."""
        ctx = self.session_context
        if ctx.active_filename:
            self.render_file(ctx.active_filename)

    # ------------------------------------------------------------------
    # render_dashboard — migrado de MainWindow (fidelidade comportamental)
    # ------------------------------------------------------------------

    def render_dashboard(self, filename: str) -> None:
        """Orquestra a renderização completa dos quatro painéis.

        Implementação extraída de MainWindow.render_dashboard com fidelidade
        de assinatura e comportamento. Referências a self.* na MainWindow
        que pertencem à responsabilidade de UI (labels, timeline, splitter,
        capture_backgrounds) são acessadas via self.main_window.
        """
        win = self.main_window
        if win is None:
            return

        # Preserva tamanho do splitter antes de redesenhar
        cur_splitter_sizes = win.splitter.sizes() if hasattr(win, "splitter") else None

        # Limpa referências a linhas de alinhamento do clique em eixos que serão
        # destruídos/recriados nesta renderização. Mantê-las causaria RuntimeError
        # ao chamar line.remove() na próxima chamada de _align_click_marker().
        win._click_alignment_lines = []

        # Para timers de debounce pendentes dos engines anteriores antes de recriá-los
        if self.line_engine is not None and hasattr(self.line_engine, "debounce_timer"):
            self.line_engine.debounce_timer.stop()
        if self.spectro_engine is not None and hasattr(self.spectro_engine, "debounce_timer"):
            self.spectro_engine.debounce_timer.stop()
        if self.freq_engine is not None and hasattr(self.freq_engine, "debounce_timer"):
            self.freq_engine.debounce_timer.stop()

        # Ativa atomicamente todo o estado analítico do arquivo no SessionContext
        ctx = self.session_context
        if filename:
            if filename in ctx.analysis_cache:
                ctx.activate_cached_file(filename)
            elif filename != ctx.active_filename:
                # Arquivo não analisado ou inexistente no cache: interrompe renderização
                # para evitar apresentar dados de outro arquivo com rótulo incorreto
                return
        d = ctx.active_heavy_data

        if not d:
            return

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

        # Atualiza labels de sumário na MainWindow (responsabilidade de UI)
        if hasattr(win, "lbl_summary_file"):
            win.lbl_summary_file.setText(filename)
        if hasattr(win, "lbl_summary_meta"):
            p_txt = (
                f"[Pulsos: {p['min_p']}-{p['max_p']} | "
                f"Amp: {p['amp_min']:.2f}-{p['amp_max']:.2f} | "
                f"Freq: {int(p['b1_min'])}-{int(p['b1_max'])} Hz]"
            )
            meta_str = f"Duração: {d['duration']:.2f}s   |   Parâmetros: {p_txt}"
            win.lbl_summary_meta.setText(meta_str)
            win.lbl_summary_meta.setToolTip(
                f"Duração: {d['duration']:.2f} segundos\nParâmetros: {p_txt}"
            )
        if hasattr(win, "lbl_total"):
            win.lbl_total.setText(str(len(chirps)))
        if hasattr(win, "lbl_metric_sub"):
            win.lbl_metric_sub.setText(f"Moda: {d['moda']}   |   Média: {d['media']:.2f}")
        if hasattr(win, "_update_ml_toggle_ui"):
            win._update_ml_toggle_ui()

        # Sincroniza informações da frequência portadora (FP) e tolerância nos painéis
        carrier_freq = float(d.get("carrier_freq", 0.0))
        tol_val = float(p.get("freq_tolerance_hz", 700.0))
        if self.panel_spec and hasattr(self.panel_spec, "set_carrier_info"):
            self.panel_spec.set_carrier_info(carrier_freq, tol_val)
        if self.panel_freq and hasattr(self.panel_freq, "set_carrier_info"):
            self.panel_freq.set_carrier_info(carrier_freq, tol_val)

        # Paleta canônica por quantidade de pulsos (2 a 10 + extra para outros escopos).
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
        extra_pulse_color = '#F43F5E'  # Vermelho Rubi

        picos_por_contagem = {}
        for cp in chirp_peaks_list:
            qnt = len(cp)
            picos_por_contagem.setdefault(qnt, []).extend(cp)
        time_sec = np.arange(len(data)) / rate

        # ── WAVE ──────────────────────────────────────────────────────────
        ax1 = self.panel_wave.ax
        ax1.clear()
        self._wave_user_markers = []
        self.wave_lines = {}

        # Lê os seletores configurados nos chips do cabeçalho
        show_raw = getattr(self.panel_wave, "show_raw", True)
        show_env = getattr(self.panel_wave, "show_env", True)
        show_lod = getattr(self.panel_wave, "show_lod", False)
        show_peaks = getattr(self.panel_wave, "show_peaks", True)

        # 1. Sinal Bruto Filtrado (Amostras Reais — Linha cinza em segundo plano)
        dec_raw = max(1, len(data) // 20000)
        line_raw, = ax1.plot(
            time_sec[::dec_raw], data[::dec_raw],
            color='#94A3B8', alpha=0.45, linewidth=0.7, zorder=1,
            label="Sinal Bruto Filtrado",
        )
        line_raw.set_visible(bool(show_raw))
        self.wave_lines['raw'] = line_raw

        # 2. Envoltória de Hilbert Suavizada (Curva azul nítida em destaque)
        dec_env = max(1, len(env) // 8000)
        line_env, = ax1.plot(
            time_sec[::dec_env], env[::dec_env],
            color='#0284C7', alpha=0.95, linewidth=1.6, zorder=3,
            label="Envoltória de Hilbert Suavizada",
        )
        line_env.set_visible(bool(show_env))
        self.wave_lines['env'] = line_env

        # 3. Decimação Min-Max LOD (Linha Laranja dinâmica com preservação de picos)
        self.line_engine = HighPerfLineEngine(
            ax1, time_sec, data, base_color='#F97316',
            update_bg_callback=win.capture_backgrounds if hasattr(win, "capture_backgrounds") else None,
        )
        self.line_engine.render_high_detail()
        if self.line_engine.line:
            self.line_engine.line.set_zorder(2)
            self.line_engine.line.set_linewidth(1.1)
            self.line_engine.line.set_visible(bool(show_lod))
            self.wave_lines['lod'] = self.line_engine.line

        ax1.set_xlabel("seconds")
        ax1.set_ylabel("Amplitude")
        ax1.set_xlim(time_sec[0], time_sec[-1])
        ax1.set_ylim(-1.05, 1.05)

        # ── HIST ──────────────────────────────────────────────────────────
        # Fixo, sem drag/zoom, com índice de cores/pulsos no rodapé
        self._refresh_histogram()

        # ── FREQ (PSD) ────────────────────────────────────────────────────
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
                idx_c = np.argmin(np.abs(f_psd - carrier_freq_hz))
                carrier_x = f_psd[idx_c] / scale
                carrier_y = Pxx_db[idx_c]
            else:
                idx_max = np.argmax(Pxx_db)
                carrier_x = f_psd[idx_max] / scale
                carrier_y = Pxx_db[idx_max]

            ax3.plot(carrier_x, carrier_y, 'ro', markersize=6, zorder=3)
            ax3.annotate(
                f"{carrier_x:.2f} {unit}",
                xy=(carrier_x, carrier_y), xytext=(5, 5),
                textcoords='offset points', color='white',
                fontsize=9, zorder=4,
            )

            # Limite superior para focar na banda acústica relevante de insetos (ou Nyquist)
            rate_psd = self.session_context.active_heavy_data.get("rate", 44100)
            max_khz = min(15.0, rate_psd / 2000.0)
            ax3.set_xlim(0.0, max_khz if unit == "kHz" else max_khz * 1000.0)

            y_range = np.ptp(Pxx_db) if len(Pxx_db) > 0 else 10
            ax3.set_ylim(np.min(Pxx_db) - y_range * 0.1, np.max(Pxx_db) + y_range * 0.1)

        # Nota histórica: HighPerfFreqEngine permanece não instanciado nesta fase;
        # freq_engine continua None, preservando estritamente o comportamento legado da MainWindow.
        self.freq_engine = None

        # ── SPEC ──────────────────────────────────────────────────────────
        ax4 = self.panel_spec.ax
        ax4.clear()
        unit = getattr(self.panel_spec, "spec_unit", "kHz")
        scale = 1000.0 if unit == "kHz" else 1.0
        ymin = (
            self.panel_spec.spin_spec_ymin.value()
            if hasattr(self.panel_spec, "spin_spec_ymin") else 0.0
        )
        ymax = (
            self.panel_spec.spin_spec_ymax.value()
            if hasattr(self.panel_spec, "spin_spec_ymax")
            else (10.0 if unit == "kHz" else 10000.0)
        )
        ax4.set_ylabel(unit)
        ax4.set_xlabel("seconds")
        ax4.set_xlim(t_spec[0], t_spec[-1])
        ax4.set_ylim(ymin, ymax)
        self.spectro_engine = HighPerfSpectrogramEngine(
            ax4, Sxx_db, t_spec, f_spec,
            update_bg_callback=win.capture_backgrounds if hasattr(win, "capture_backgrounds") else None,
            unit=unit,
        )
        self.spectro_engine.render_high_detail()

        # Atualiza mapa de eixos independente da posição atual.
        win.cursor_lines = []
        for panel in [self.panel_wave, self.panel_spec]:
            win.cursor_lines.append(
                panel.ax.axvline(x=0, color='#E5E8EB', linewidth=1.2, linestyle='-', zorder=9)
            )

        for panel in self.all_panels:
            panel.apply_dark_theme()
        if hasattr(win, "_apply_plot_geometry"):
            win._apply_plot_geometry()

        # Desenho inicial explícito: o histograma não participa do cache do cursor,
        # então precisa receber seu primeiro draw aqui para aparecer imediatamente.
        win.setUpdatesEnabled(False)
        try:
            for panel in self.all_panels:
                panel.canvas.draw()
        finally:
            win.setUpdatesEnabled(True)

        markers = []
        for idx, cp in enumerate(chirp_peaks_list):
            if not cp:
                continue
            t = float(cp[0] / rate)
            markers.append({"time": t, "color": "#F0A84B" if idx % 2 == 0 else "#3F94D5"})
        if hasattr(win, "timeline"):
            win.timeline.set_data(d["duration"], markers)
            win.timeline.set_position(win.player.position() / 1000.0)

        self._refresh_user_peak_markers()
        if hasattr(win, "_update_pulse_hover_data"):
            win._update_pulse_hover_data()
        if hasattr(win, "capture_backgrounds"):
            win.capture_backgrounds()

        if cur_splitter_sizes and len(cur_splitter_sizes) >= 2 and cur_splitter_sizes[0] >= 50:
            win.splitter.setSizes(cur_splitter_sizes)

    # ------------------------------------------------------------------
    # _refresh_histogram — migrado de MainWindow (fidelidade comportamental)
    # ------------------------------------------------------------------

    def _refresh_histogram(self) -> None:
        """Redesenha o histograma bivariado: barras de contagem (eixo Y esquerdo)
        e linha de tendência de duração média do chilreio em ms (eixo Y direito)."""
        if self.panel_hist is None or not self.session_context.active_heavy_data:
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
            1: '#94A3B8',   # Cinza ardósia
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
            edgecolor='none', linewidth=0, width=0.68, zorder=3,
        )

        win = self.main_window
        is_dark = (getattr(win, "theme_mode", "dark") == 'dark') if win is not None else True
        ax_hist.grid(
            axis='y',
            color='#292D32' if is_dark else '#E2E8F0',
            linewidth=0.6, alpha=0.8, zorder=0,
        )
        max_count = int(max(counts)) if len(counts) else 1
        hist_text_color = '#DDE1E5' if is_dark else '#1F2937'
        hist_tick_color = '#A9ADB5' if is_dark else '#1F2937'
        for bar in bars:
            ax_hist.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_count * 0.025,
                str(int(bar.get_height())),
                ha='center', va='bottom',
                color=hist_text_color, fontsize=8.5, fontweight='bold',
            )
        ax_hist.set_xticks(unique_pulses)
        ax_hist.set_xlabel("")
        ax_hist.set_ylabel("")
        ax_hist.tick_params(axis='x', labelsize=8.5, colors=hist_tick_color, length=0)
        ax_hist.tick_params(axis='y', labelsize=8, colors=hist_tick_color)
        ax_hist.set_ylim(0, max_count * 1.20)

        # ── Eixo Y secundário: Duração média do chilreio (ms) ────────────
        dur_color = '#FF6B6B' if is_dark else '#DC2626'

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

            ax2.plot(
                x_pts, y_pts,
                color=dur_color, linewidth=1.5, linestyle='--',
                marker='o', markersize=5, markerfacecolor=dur_color,
                markeredgecolor='white' if is_dark else '#1F2937',
                markeredgewidth=0.8, zorder=5, alpha=0.9,
            )

            # Anotações discretas de duração sobre cada marcador
            for xv, yv in zip(x_pts, y_pts):
                ax2.annotate(
                    f'{yv:.0f}', (xv, yv), textcoords='offset points',
                    xytext=(0, 7), ha='center', fontsize=6.5,
                    color=dur_color, fontweight='bold',
                )

            ax2.set_ylabel("Duração (ms)", fontsize=7.5, color=dur_color)
            ax2.tick_params(axis='y', labelsize=7, colors=dur_color, length=2)
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

        # ── Legenda unificada ─────────────────────────────────────────────
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        legend_handles = [
            Patch(
                facecolor=hist_palette.get(int(x), extra_pulse_color),
                edgecolor='none',
                label=f'{int(x)} pulsos',
            )
            for x in unique_pulses
        ]
        if len(avg_durations) >= 2:
            legend_handles.append(
                Line2D(
                    [0], [0], color=dur_color, linewidth=1.5, linestyle='--',
                    marker='o', markersize=4, label='Duração (ms)',
                )
            )
        if legend_handles:
            hist_w = self.panel_hist.width()
            leg_ncol = min(3 if hist_w < 340 else 4, len(legend_handles))
            leg_fs = 7.0 if hist_w < 280 else (7.5 if hist_w < 340 else 8.0)
            leg = ax_hist.legend(
                handles=legend_handles,
                loc='upper center', bbox_to_anchor=(0.5, -0.11),
                ncol=leg_ncol, frameon=False, fontsize=leg_fs,
                handlelength=0.9, columnspacing=0.5, borderaxespad=0.0,
            )
            leg.get_frame().set_facecolor((0, 0, 0, 0))
            leg.get_frame().set_alpha(0.0)
            leg.get_frame().set_edgecolor((0, 0, 0, 0))
            leg.get_frame().set_linewidth(0)
            for text in leg.get_texts():
                text.set_color(hist_tick_color)

        self.panel_hist.canvas.draw_idle()

    # ------------------------------------------------------------------
    # _refresh_user_peak_markers — migrado de MainWindow (fidelidade)
    # ------------------------------------------------------------------

    def _refresh_user_peak_markers(self) -> None:
        """Renderiza marcadores de picos do usuário em todos os gráficos
        relevantes (onda, freq, spec)."""
        if self.panel_wave is None:
            return

        # Limpa marcadores antigos de todos os painéis
        for artist in self._wave_user_markers:
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
            1: '#94A3B8',   # Cinza ardósia
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
                lines = ax1.plot(
                    pks_t, env[pks], 'x',
                    color=pulse_colors.get(int(qnt), extra_pulse_color),
                    markersize=7, markeredgewidth=1.7, zorder=7,
                )
                self._wave_user_markers.extend(lines)
            if distant_pks:
                valid_d = [dp for dp in distant_pks if 0 <= dp < len(env)]
                if valid_d:
                    lines = ax1.plot(
                        np.array(valid_d) / rate, env[valid_d], 'x',
                        color='#64748B', markersize=5.5, markeredgewidth=1.1,
                        alpha=0.55, zorder=5,
                    )
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
                    lines = ax3.plot(
                        pks_t, freqs_at_pks, 'x',
                        color=pulse_colors.get(int(qnt), '#5F9ED1'),
                        markersize=6, markeredgewidth=1.4, zorder=7,
                    )
                    self._wave_user_markers.extend(lines)
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                    if valid_d:
                        d_times, d_freqs = get_freqs_for_peaks(valid_d)
                        lines = ax3.plot(
                            d_times, d_freqs, 'x',
                            color='#64748B', markersize=5, markeredgewidth=1.1,
                            alpha=0.55, zorder=5,
                        )
                        self._wave_user_markers.extend(lines)

            if ax4:
                unit = getattr(self.panel_spec, "spec_unit", "kHz")
                scale = 1000.0 if unit == "kHz" else 1.0
                for qnt, pks in sorted(picos_por_contagem.items()):
                    pks_t, freqs_at_pks = get_freqs_for_peaks(pks)
                    lines = ax4.plot(
                        pks_t, freqs_at_pks / scale, 'x',
                        color=pulse_colors.get(int(qnt), '#5F9ED1'),
                        markersize=7, markeredgewidth=1.5, zorder=7,
                    )
                    self._wave_user_markers.extend(lines)
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                    if valid_d:
                        d_times, d_freqs = get_freqs_for_peaks(valid_d)
                        lines = ax4.plot(
                            d_times, d_freqs / scale, 'x',
                            color='#94A3B8', markersize=5, markeredgewidth=1.0,
                            alpha=0.5, zorder=5,
                        )
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
                    scatter = ax1.scatter(
                        xdata, np.zeros_like(xdata), s=60, marker='o',
                        color='#10B981', edgecolors='#047857', linewidths=1.5, zorder=4,
                    )
                    self._wave_user_markers.append(scatter)

                if peaks_added:
                    xdata = np.asarray(peaks_added, dtype=float) / rate
                    scatter = ax1.scatter(
                        xdata, np.zeros_like(xdata), s=60, marker='^',
                        color='#3B82F6', edgecolors='#1E40AF', linewidths=1.5, zorder=4,
                    )
                    self._wave_user_markers.append(scatter)

                if peaks_removed:
                    xdata = np.asarray(peaks_removed, dtype=float) / rate
                    scatter = ax1.scatter(
                        xdata, np.zeros_like(xdata), s=80, marker='x',
                        color='#EF4444', linewidths=2.0, zorder=4,
                    )
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
                            lines = ax3.plot(
                                pks_t, freqs_at_pks, marker=marker, linestyle='none',
                                color=color, markersize=8, markeredgewidth=1.2, zorder=4,
                            )
                            self._wave_user_markers.extend(lines)

                        if ax4:
                            unit = getattr(self.panel_spec, "spec_unit", "kHz")
                            scale = 1000.0 if unit == "kHz" else 1.0
                            freqs_at_pks_spec = freqs_at_pks / scale
                            lines = ax4.plot(
                                pks_t, freqs_at_pks_spec, marker=marker, linestyle='none',
                                color=color, markersize=8, markeredgewidth=1.2, zorder=4,
                            )
                            self._wave_user_markers.extend(lines)

        # Aplica a visibilidade configurada pelo usuário nos marcadores de pulsos
        show_peaks = getattr(self.panel_wave, "show_peaks", True)
        if not show_peaks:
            for m in self._wave_user_markers:
                try:
                    m.set_visible(False)
                except Exception:
                    pass

        # Atualiza dados de hover (responsabilidade da MainWindow enquanto não for FASE 4)
        win = self.main_window
        if win is not None and hasattr(win, "_update_pulse_hover_data"):
            win._update_pulse_hover_data()

        for panel in self.all_panels:
            try:
                panel.canvas.draw_idle()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # apply_spectrogram_y_limits — migrado de MainWindow (fidelidade)
    # ------------------------------------------------------------------

    def apply_spectrogram_y_limits(self, ymin, ymax, unit="kHz") -> None:
        """Atualiza dinamicamente a escala, limites e unidade do eixo Y do espectrograma."""
        if self.panel_spec is None:
            return

        ax4 = self.panel_spec.ax
        unit_changed = (self._last_applied_spec_unit != unit)
        self._last_applied_spec_unit = unit

        ax4.set_ylabel(unit)
        ax4.set_ylim(ymin, ymax)
        if self.spectro_engine is not None:
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
                9: '#EAB308', 10: '#A855F7', 11: '#14B8A6', 12: '#6366F1',
            }

            win = self.main_window
            cursor_lines = getattr(win, "cursor_lines", []) if win is not None else []
            alignment_lines = getattr(win, "_click_alignment_lines", []) if win is not None else []
            lines_to_keep = set(cursor_lines + alignment_lines)
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

            if (
                t_spec is not None and len(t_spec) > 0
                and dom_freqs is not None and len(dom_freqs) > 0
            ):
                for qnt, pks in sorted(picos_por_contagem.items()):
                    pks_t = np.array(pks) / rate
                    freqs_at_pks = np.interp(pks_t, t_spec, dom_freqs) / scale
                    ax4.plot(
                        pks_t, freqs_at_pks, 'x',
                        color=marker_colors.get(int(qnt), '#5F9ED1'),
                        markersize=7, markeredgewidth=1.5, zorder=7,
                    )
                if distant_pks:
                    valid_d = [dp for dp in distant_pks if env is not None and 0 <= dp < len(env)]
                    if valid_d:
                        d_times = np.array(valid_d) / rate
                        d_freqs = np.interp(d_times, t_spec, dom_freqs) / scale
                        ax4.plot(
                            d_times, d_freqs, 'x',
                            color='#9CA3AF', markersize=4.5, markeredgewidth=1.0,
                            alpha=0.6, zorder=6,
                        )

        self.panel_spec.canvas.draw_idle()

    # ------------------------------------------------------------------
    # update_wave_visibility — migrado de MainWindow (fidelidade)
    # ------------------------------------------------------------------

    def update_wave_visibility(self, show_raw, show_env, show_lod, show_peaks) -> None:
        """Controla a visibilidade das camadas do painel de onda."""
        if self.wave_lines:
            if 'raw' in self.wave_lines and self.wave_lines['raw']:
                self.wave_lines['raw'].set_visible(bool(show_raw))
            if 'env' in self.wave_lines and self.wave_lines['env']:
                self.wave_lines['env'].set_visible(bool(show_env))
            if 'lod' in self.wave_lines and self.wave_lines['lod']:
                self.wave_lines['lod'].set_visible(bool(show_lod))
        if self.line_engine is not None and getattr(self.line_engine, 'line', None):
            self.line_engine.line.set_visible(bool(show_lod))

        for m in self._wave_user_markers:
            try:
                m.set_visible(bool(show_peaks))
            except Exception:
                pass

        if self.panel_wave is not None and hasattr(self.panel_wave, 'canvas'):
            self.panel_wave.canvas.draw_idle()

        win = self.main_window
        if win is not None and hasattr(win, "capture_backgrounds"):
            win.bg_cache_valid = False
            win.capture_backgrounds()