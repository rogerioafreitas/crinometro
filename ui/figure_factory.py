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

import io
import contextlib
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

    # 1. Sinal bruto filtrado
    dec_raw = max(1, len(data) // 20000)
    line_raw, = ax.plot(
        time_sec[::dec_raw], data[::dec_raw],
        color='#94A3B8', alpha=0.45, linewidth=0.7, zorder=1,
        label="Sinal Bruto Filtrado",
    )
    line_raw.set_visible(bool(cfg.show_raw))
    wave_lines['raw'] = line_raw

    # 2. Envoltória de Hilbert suavizada
    if env is not None:
        dec_env = max(1, len(env) // 8000)
        line_env, = ax.plot(
            time_sec[::dec_env], env[::dec_env],
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
    ax.set_xlim(time_sec[0], time_sec[-1])
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
    ax.set_xlim(t_spec[0], t_spec[-1])
    ax.set_ylim(cfg.spec_ymin, cfg.spec_ymax)
    ax.tick_params(colors=cfg.ax_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(cfg.ax_color)

    if interactive and spectro_engine is not None:
        spectro_engine.render_high_detail()
    else:
        # Exportação de alta fidelidade: sem decimação restritiva
        # rasterized=True evita que PDFs fiquem gigantes e lentos, mantendo os eixos vetoriais em alta resolução
        ax.pcolormesh(t_spec, f_spec / scale, Sxx_db, shading='gouraud', cmap='magma', rasterized=True)


def draw_histogram(
    ax,
    chirp_peaks_list: List,
    rate: float,
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

    if not chirp_peaks_list:
        return

    from collections import Counter
    counts = Counter(len(cp) for cp in chirp_peaks_list)
    if not counts:
        return

    ks = sorted(counts.keys())
    vs = [counts[k] for k in ks]
    bar_colors = {
        1: '#F59E0B', 2: '#EC4899', 3: '#8B5CF6', 4: '#3B82F6',
        5: '#10B981', 6: '#EF4444', 7: '#F97316', 8: '#06B6D4',
        9: '#84CC16', 10: '#14B8A6',
    }
    extra = '#F43F5E'
    colors_list = [bar_colors.get(k, extra) for k in ks]

    bars = ax.bar(ks, vs, color=colors_list, edgecolor='none', zorder=2)
    ax.set_xticks(ks)
    
    # Anotações de contagem exata no topo das barras
    max_v = max(vs) if vs else 1
    for k, v in zip(ks, vs):
        ax.text(k, v + max_v * 0.015, str(v), ha='center', va='bottom', 
                color=cfg.text_color, fontsize=10, fontweight='bold', zorder=4)

    # Duração média (eixo secundário)
    ax2 = ax.twinx()
    ax2.tick_params(colors=cfg.ax_color)
    dur_ms = []
    for k in ks:
        peaks_k = [cp for cp in chirp_peaks_list if len(cp) == k]
        if len(peaks_k) >= 2:
            spans = [(max(cp) - min(cp)) / rate * 1000 for cp in peaks_k]
            dur_ms.append(float(np.mean(spans)))
        else:
            dur_ms.append(0.0)
            
    ax2.plot(ks, dur_ms, 'o--', color='#F97316', linewidth=1.4,
             markersize=5, zorder=3, label="Dur. média (ms)")
             
    # Anotações de duração em ms
    max_d = max(dur_ms) if any(dur_ms) else 1
    for k, d in zip(ks, dur_ms):
        if d > 0:
            ax2.text(k, d + max_d * 0.02, f"{d:.1f} ms", ha='center', va='bottom', 
                     color='#EA580C', fontsize=9, fontweight='bold', zorder=4)
    ax2.set_ylabel("Duração Média (ms)", color='#F97316')
    ax2.tick_params(axis='y', colors='#F97316')

    if cfg.grid:
        ax.grid(True, linestyle="--", alpha=0.4, color=cfg.ax_color)


# ---------------------------------------------------------------------------
# Funções de alto nível: create_*_figure → (Figure, ax)
# ---------------------------------------------------------------------------

def _new_fig(cfg: ExportConfig, height: float = 3.5) -> tuple:
    """Cria Figure + Canvas (sem pyplot) com configurações de tema."""
    fig = Figure(figsize=(cfg.fig_width, height), dpi=cfg.dpi)
    fig.patch.set_facecolor(cfg.bg_color)
    canvas = FigureCanvasAgg(fig)  # necessário para tight_layout funcionar
    ax = fig.add_subplot(111)
    ax.set_facecolor(cfg.bg_color)
    return fig, ax


def create_waveform_figure(ctx, cfg: Optional[ExportConfig] = None) -> tuple:
    """Retorna (Figure, ax) com o oscilograma pronto para exportar."""
    if cfg is None:
        cfg = ExportConfig()

    fig, ax = _new_fig(cfg, height=3.5)
    d = ctx.active_heavy_data
    if not d:
        return fig, ax

    draw_waveform(
        ax, d["data"], d["rate"],
        env=d.get("env"),
        chirp_peaks_list=d.get("chirp_peaks_list", []),
        cfg=cfg,
        interactive=False,
    )
    fig.tight_layout()
    return fig, ax


def create_psd_figure(ctx, cfg: Optional[ExportConfig] = None) -> tuple:
    """Retorna (Figure, ax) com o espectro de potência pronto para exportar."""
    if cfg is None:
        cfg = ExportConfig()

    fig, ax = _new_fig(cfg, height=3.5)
    d = ctx.active_heavy_data
    if not d:
        return fig, ax

    draw_psd(
        ax,
        np.asarray(d.get("f_psd", [])),
        np.asarray(d.get("Pxx_db", [])),
        rate=float(d.get("rate", 44100)),
        carrier_freq_hz=float(d.get("carrier_freq", 0.0)),
        cfg=cfg,
    )
    fig.tight_layout()
    return fig, ax


def create_spectrogram_figure(ctx, cfg: Optional[ExportConfig] = None) -> tuple:
    """Retorna (Figure, ax) com o espectrograma pronto para exportar."""
    if cfg is None:
        cfg = ExportConfig()

    fig, ax = _new_fig(cfg, height=4.0)
    d = ctx.active_heavy_data
    if not d:
        return fig, ax

    draw_spectrogram(
        ax,
        d["Sxx_db"], d["t_spec"], d["f_spec"],
        cfg=cfg,
        interactive=False,
    )
    fig.tight_layout()
    return fig, ax


def create_histogram_figure(ctx, cfg: Optional[ExportConfig] = None) -> tuple:
    """Retorna (Figure, ax) com o histograma pronto para exportar."""
    if cfg is None:
        cfg = ExportConfig()

    fig, ax = _new_fig(cfg, height=3.5)
    d = ctx.active_heavy_data
    if not d:
        return fig, ax

    draw_histogram(
        ax,
        d.get("chirp_peaks_list", []),
        float(d.get("rate", 44100)),
        cfg=cfg,
    )
    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Exportadores de alto nível
# ---------------------------------------------------------------------------

_PANEL_FACTORIES = {
    "waveform":     create_waveform_figure,
    "psd":          create_psd_figure,
    "spectrogram":  create_spectrogram_figure,
    "histogram":    create_histogram_figure,
}

_PANEL_TITLES = {
    "waveform":    "Oscilograma",
    "psd":         "Espectro de Potência (PSD)",
    "spectrogram": "Espectrograma",
    "histogram":   "Histograma de Chilreios",
}


def export_figures_png(ctx, path: str, cfg: Optional[ExportConfig] = None) -> List[str]:
    """
    Exporta cada painel selecionado em cfg.panels como arquivo PNG separado.

    Nomes gerados: <base>_waveform.png, <base>_psd.png, etc.
    Retorna lista dos caminhos escritos.
    """
    if cfg is None:
        cfg = ExportConfig(fmt="png")

    import os
    base, _ = os.path.splitext(path)
    written = []

    for panel in cfg.panels:
        factory = _PANEL_FACTORIES.get(panel)
        if factory is None:
            continue
        fig, _ = factory(ctx, cfg)
        try:
            out = f"{base}_{panel}.png"
            fig.savefig(out, dpi=cfg.dpi, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            written.append(out)
        finally:
            import matplotlib
            matplotlib.pyplot.close(fig) if hasattr(matplotlib, 'pyplot') else fig.clf()

    return written


def export_figures_pdf(ctx, path: str, cfg: Optional[ExportConfig] = None) -> str:
    """
    Exporta todos os painéis selecionados em um único PDF multipágina.

    Cada painel é uma página. Retorna o caminho do arquivo escrito.
    """
    if cfg is None:
        cfg = ExportConfig(fmt="pdf")

    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(path) as pdf:
        for panel in cfg.panels:
            factory = _PANEL_FACTORIES.get(panel)
            if factory is None:
                continue
            fig, ax = factory(ctx, cfg)
            try:
                ax.set_title(_PANEL_TITLES.get(panel, panel),
                             color=cfg.text_color, pad=8, fontsize=11)
                pdf.savefig(fig, bbox_inches="tight",
                            facecolor=fig.get_facecolor())
            finally:
                fig.clf()
                del fig

    return path
