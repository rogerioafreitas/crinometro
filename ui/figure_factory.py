# coding: utf-8
"""
ui/figure_factory.py
--------------------
FASE 8 — Fábrica de Figuras Puras

Funções de desenho Matplotlib completamente desacopladas da janela Qt.
Recebem dados brutos (arrays NumPy) ou um SessionContext + ExportConfig,
e devolvem objetos Figure prontos para salvar em PNG, PDF ou exibir em
qualquer canvas sem tocar nos panels ao vivo.

Regras de ouro:
  • Sem import de PyQt6/PySide6 neste módulo.
  • Sem acesso a self.main_window, self.transport_panel, etc.
  • Sem pyplot; toda figure é criada com Figure() diretamente.
  • Parâmetros de tema (cores, labels) chegam via ExportConfig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


# ---------------------------------------------------------------------------
# ExportConfig — transporta todas as opções de exportação
# ---------------------------------------------------------------------------

@dataclass
class ExportConfig:
    """Configuração imutável para geração de figuras de exportação."""

    # Painéis a incluir
    panels: List[str] = field(default_factory=lambda: ["waveform", "histogram", "psd", "spectrogram"])

    # Camadas de onda
    show_raw: bool = True
    show_env: bool = True
    show_markers: bool = True   # marcadores de pulsos sobre a onda

    # Grade
    grid: bool = False

    # Espectrograma
    spec_unit: str = "kHz"      # "kHz" ou "Hz"
    spec_xmin: Optional[float] = None
    spec_xmax: Optional[float] = None
    spec_ymin: float = 0.0
    spec_ymax: float = 10.0

    # DPI e tamanho
    dpi: int = 300
    fig_width: float = 10.0     # polegadas

    # Tema de cores
    bg_color: str = "#FFFFFF"      # fundo da figura (branco para papel)
    ax_color: str = "#1E293B"      # cor dos eixos e ticks
    text_color: str = "#1E293B"    # rótulos, títulos
    annotation_color: str = "#1E293B"  # anotações (portadora PSD etc.)

    # Rótulos de eixos (None = usar padrão)
    xlabel_wave: Optional[str] = None
    ylabel_wave: Optional[str] = None
    xlabel_spec: Optional[str] = None

    # Formato de saída (usado por save_figures)
    fmt: str = "png"    # "png" ou "pdf"


# ---------------------------------------------------------------------------
# Primitivas de desenho (recebem ax + dados brutos, sem contexto Qt)
# ---------------------------------------------------------------------------

def draw_waveform(
    ax,
    data: np.ndarray,
    rate: float,
    env: Optional[np.ndarray] = None,
    chirp_peaks_list: Optional[List] = None,
    cfg: Optional[ExportConfig] = None,
    interactive: bool = False,
    line_engine=None,
) -> Dict[str, Any]:
    """
    Traça o oscilograma no eixo `ax`.

    Modo exportação (interactive=False): desenha sinal bruto + envoltória
    de forma estática, com marcadores de pulsos opcionais.

    Modo GUI (interactive=True): configura o HighPerfLineEngine e delega
    o LOD a ele.

    Retorna dict com artists criados.
    """
    if cfg is None:
        cfg = ExportConfig()

    wave_lines: Dict[str, Any] = {}
    time_sec = np.arange(len(data)) / rate

    # Subset dos dados se houver limite X (Apenas para exportação de Específico)
    if not interactive and cfg.spec_xmin is not None and cfg.spec_xmax is not None:
        idx_min = max(0, int(cfg.spec_xmin * rate))
        idx_max = min(len(data), int(cfg.spec_xmax * rate) + 1)
        plot_data = data[idx_min:idx_max]
        plot_env = env[idx_min:idx_max] if env is not None else None
        plot_time = time_sec[idx_min:idx_max]
    else:
        plot_data = data
        plot_env = env
        plot_time = time_sec

    # 1. Sinal bruto filtrado
    # Na exportação, usar min/max decimation para preservar picos reais
    num_points = 20000 if interactive else 100000
    if len(plot_data) > num_points * 2:
        block_size = len(plot_data) // num_points
        data_reshaped = plot_data[:block_size * num_points].reshape(-1, block_size)
        time_reshaped = plot_time[:block_size * num_points].reshape(-1, block_size)
        
        min_vals = data_reshaped.min(axis=1)
        max_vals = data_reshaped.max(axis=1)
        t_vals = time_reshaped[:, 0]
        
        plot_time_dec = np.empty(num_points * 2)
        plot_time_dec[0::2] = t_vals
        plot_time_dec[1::2] = t_vals
        
        plot_data_dec = np.empty(num_points * 2)
        plot_data_dec[0::2] = min_vals
        plot_data_dec[1::2] = max_vals
    else:
        plot_time_dec = plot_time
        plot_data_dec = plot_data

    line_raw, = ax.plot(
        plot_time_dec, plot_data_dec,
        color='#94A3B8', alpha=0.45, linewidth=0.7, zorder=1,
        label="Sinal Bruto Filtrado",
    )
    line_raw.set_visible(bool(cfg.show_raw))
    wave_lines['raw'] = line_raw

    # 2. Envoltória de Hilbert suavizada
    if plot_env is not None:
        num_env_points = 8000 if interactive else 50000
        if len(plot_env) > num_env_points * 2:
            block_size = len(plot_env) // num_env_points
            env_reshaped = plot_env[:block_size * num_env_points].reshape(-1, block_size)
            time_env_reshaped = plot_time[:block_size * num_env_points].reshape(-1, block_size)
            max_env_vals = env_reshaped.max(axis=1)
            plot_env_dec = max_env_vals
            plot_time_env_dec = time_env_reshaped[:, 0]
        else:
            plot_time_env_dec = plot_time
            plot_env_dec = plot_env
            
        line_env, = ax.plot(
            plot_time_env_dec, plot_env_dec,
            color='#0284C7', alpha=0.95, linewidth=1.6, zorder=3,
            label="Envoltória de Hilbert Suavizada",
        )
        line_env.set_visible(bool(cfg.show_env))
        wave_lines['env'] = line_env

    # 3. LOD interativo (somente modo GUI)
    if interactive and line_engine is not None:
        line_engine.render_high_detail()
        if line_engine.line:
            line_engine.line.set_zorder(2)
            line_engine.line.set_linewidth(1.1)
            wave_lines['lod'] = line_engine.line

    # 4. Marcadores de pulsos (exportação)
    if not interactive and cfg.show_markers and chirp_peaks_list:
        marker_colors = {
            1: '#F59E0B', 2: '#EC4899', 3: '#8B5CF6', 4: '#3B82F6',
            5: '#10B981', 6: '#EF4444', 7: '#F97316', 8: '#06B6D4',
            9: '#84CC16', 10: '#14B8A6',
        }
        extra_color = '#F43F5E'
        for cp in chirp_peaks_list:
            n = len(cp)
            c = marker_colors.get(n, extra_color)
            xs = [p / rate for p in cp]
            ys = [float(np.interp(x, time_sec, env if env is not None else data)) for x in xs]
            ax.scatter(xs, ys, color=c, s=18, zorder=5, linewidths=0)

    xlabel = cfg.xlabel_wave or "Tempo (s)"
    ylabel = cfg.ylabel_wave or "Amplitude"
    ax.set_xlabel(xlabel, color=cfg.text_color)
    ax.set_ylabel(ylabel, color=cfg.text_color)
    
    xmin = cfg.spec_xmin if cfg.spec_xmin is not None else time_sec[0]
    xmax = cfg.spec_xmax if cfg.spec_xmax is not None else time_sec[-1]
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(-1.05, 1.05)
    ax.tick_params(colors=cfg.ax_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(cfg.ax_color)

    if cfg.grid:
        ax.grid(True, linestyle="--", alpha=0.4, color=cfg.ax_color)

    return wave_lines


def draw_psd(
    ax,
    f_psd: np.ndarray,
    Pxx_db: np.ndarray,
    rate: float = 44100,
    carrier_freq_hz: float = 0.0,
    cfg: Optional[ExportConfig] = None,
) -> None:
    """Traça o espectro de potência (PSD) no eixo `ax`."""
    if cfg is None:
        cfg = ExportConfig()

    unit = cfg.spec_unit
    scale = 1000.0 if unit == "kHz" else 1.0

    ax.set_ylabel("Potência (dB/Hz)", color=cfg.text_color)
    ax.set_xlabel(f"Frequência ({unit})", color=cfg.text_color)
    ax.tick_params(colors=cfg.ax_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(cfg.ax_color)

    if len(f_psd) > 0 and len(Pxx_db) > 0:
        ax.plot(f_psd / scale, Pxx_db, color='#8B5CF6', linewidth=1.5, zorder=2)

        if carrier_freq_hz > 0:
            idx_c = int(np.argmin(np.abs(f_psd - carrier_freq_hz)))
            cx, cy = f_psd[idx_c] / scale, Pxx_db[idx_c]
        else:
            idx_max = int(np.argmax(Pxx_db))
            cx, cy = f_psd[idx_max] / scale, Pxx_db[idx_max]

        ax.plot(cx, cy, 'ro', markersize=6, zorder=3)
        ax.annotate(
            f"{cx:.2f} {unit}",
            xy=(cx, cy), xytext=(5, 5),
            textcoords='offset points',
            color=cfg.annotation_color,   # parametrizado — não hardcoded 'white'
            fontsize=9, zorder=4,
        )

        max_khz = min(15.0, rate / 2000.0)
        ax.set_xlim(0.0, max_khz if unit == "kHz" else max_khz * 1000.0)

        y_range = float(np.ptp(Pxx_db)) if len(Pxx_db) > 0 else 10.0
        ax.set_ylim(np.min(Pxx_db) - y_range * 0.1, np.max(Pxx_db) + y_range * 0.1)

    if cfg.grid:
        ax.grid(True, linestyle="--", alpha=0.4, color=cfg.ax_color)


def draw_spectrogram(
    ax,
    Sxx_db: np.ndarray,
    t_spec: np.ndarray,
    f_spec: np.ndarray,
    cfg: Optional[ExportConfig] = None,
    interactive: bool = False,
    spectro_engine=None,
) -> None:
    """
    Traça o espectrograma no eixo `ax`.

    Modo exportação: usa pcolormesh com decimação por fatores de 2 para
    evitar imagens gigantes em gravações longas.

    Modo GUI: delega ao HighPerfSpectrogramEngine.
    """
    if cfg is None:
        cfg = ExportConfig()

    unit = cfg.spec_unit
    scale = 1000.0 if unit == "kHz" else 1.0

    xlabel = cfg.xlabel_spec or "Tempo (s)"
    ax.set_ylabel(unit, color=cfg.text_color)
    ax.set_xlabel(xlabel, color=cfg.text_color)
    xmin = cfg.spec_xmin if cfg.spec_xmin is not None else t_spec[0]
    xmax = cfg.spec_xmax if cfg.spec_xmax is not None else t_spec[-1]
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(cfg.spec_ymin, cfg.spec_ymax)
    ax.tick_params(colors=cfg.ax_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(cfg.ax_color)

    if interactive and spectro_engine is not None:
        spectro_engine.render_high_detail()
    else:
        # Subset para Específico não renderizar matriz gigantesca fora da view
        if cfg.spec_xmin is not None and cfg.spec_xmax is not None:
            t_mask = (t_spec >= cfg.spec_xmin) & (t_spec <= cfg.spec_xmax)
            t_plot = t_spec[t_mask]
            S_plot = Sxx_db[:, t_mask]
        else:
            t_plot = t_spec
            S_plot = Sxx_db
            
        # Exportação de alta fidelidade: sem decimação restritiva temporal
        # rasterized=True evita que PDFs fiquem gigantes e lentos, mantendo os eixos vetoriais em alta resolução
        if len(t_plot) > 0:
            mesh = ax.pcolormesh(t_plot, f_spec / scale, S_plot, shading='auto', cmap='magma', rasterized=True)
            if not interactive:
                cbar = ax.figure.colorbar(mesh, ax=ax, pad=0.01)
                cbar.set_label('Potência (dB)', color=cfg.text_color)
                cbar.ax.yaxis.set_tick_params(color=cfg.ax_color, labelcolor=cfg.text_color)
                for spine in cbar.ax.spines.values():
                    spine.set_color(cfg.ax_color)


def draw_histogram(
    ax,
    chirps: List[Dict[str, Any]],
    cfg: Optional[ExportConfig] = None,
) -> None:
    """
    Traça o histograma bivariado de chirps (contagem × duração média).

    Replicação fiel da lógica de _refresh_histogram do PlotRenderers,
    porém sem dependência de widgets Qt.
    """
    if cfg is None:
        cfg = ExportConfig()

    ax.set_xlabel("Nº de Pulsos por Chilreio", color=cfg.text_color)
    ax.set_ylabel("Contagem de Chilreios", color=cfg.text_color)
    ax.tick_params(colors=cfg.ax_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(cfg.ax_color)

    if not chirps:
        return

    from collections import Counter
    import numpy as np
    
    counts = Counter(c['n_pulses'] for c in chirps)
    if not counts:
        return

    ks = sorted(counts.keys())
    vs = [counts[k] for k in ks]
    pulse_colors = {
        2: '#2563EB', 3: '#8B5CF6', 4: '#F97316', 5: '#10B981',
        6: '#EC4899', 7: '#06B6D4', 8: '#EAB308', 9: '#84CC16',
        10: '#A855F7', 1: '#94A3B8',
    }
    extra_pulse_color = '#F43F5E'
    colors_list = [pulse_colors.get(k, extra_pulse_color) for k in ks]

    bars = ax.bar(ks, vs, color=colors_list, edgecolor='none', zorder=2)
    ax.set_xticks(ks)
    
    max_v = max(vs) if vs else 1
    ax.set_ylim(0, max_v * 1.15) # Folga para o rótulo
    
    for k, v in zip(ks, vs):
        ax.text(k, v + max_v * 0.02, str(v), ha='center', va='bottom', 
                color=cfg.text_color, fontsize=10, fontweight='bold', zorder=4)

    ax2 = ax.twinx()
    ax2.tick_params(colors=cfg.ax_color)
    dur_ms = []
    
    for k in ks:
        spans = [(c['end_time'] - c['start_time']) * 1000.0 for c in chirps if c['n_pulses'] == k]
        if spans:
            dur_ms.append(float(np.mean(spans)))
        else:
            dur_ms.append(0.0)
            
    ax2.plot(ks, dur_ms, 'o--', color='#F97316', linewidth=1.4,
             markersize=5, zorder=3, label="Duração Média (ms)")
             
    max_d = max(dur_ms) if any(dur_ms) else 1
    ax2.set_ylim(0, max_d * 1.25) # Folga para o rótulo
    
    for k, d in zip(ks, dur_ms):
        if d > 0:
            ax2.text(k, d + max_d * 0.03, f"{d:.1f} ms", ha='center', va='bottom', 
                     color='#EA580C', fontsize=9, fontweight='bold', zorder=4)

    ax2.set_ylabel("Duração Média (ms)", color=cfg.text_color)
    
    for spine in ax2.spines.values():
        spine.set_edgecolor(cfg.ax_color)
        
    ax2.legend(loc='upper left')


