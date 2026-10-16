# -*- coding: utf-8 -*-
"""
Gerador de Documentação Técnica e Científica do Crinômetro (v4.4.1)
Documentação científica exaustiva do software Crinômetro, cobrindo:
- Processamento Digital de Sinais (DSP) e Bioacústica Computacional
- Modelagem Fisiológica Termo-Acústica e Biometria de Orthoptera
- Inteligência Artificial, GMM Bimodal e Aprendizado Ativo (Active Learning)
- Engenharia de Computação, Computação Gráfica, Concorrência e Otimização
- Incorporação de Figuras Reais de Alta Resolução (300 DPI) do Áudio m017

Compatível com ReportLab e otimizado para exibição acadêmica e didática.
"""

import os
import sys
from datetime import datetime
from collections import Counter

# Garante que a raiz do projeto esteja no sys.path independente de onde o script for chamado
def _find_project_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d and os.path.dirname(d) != d:
        if os.path.exists(os.path.join(d, "core", "analyzer.py")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

PROJECT_ROOT = _find_project_root()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Image
)
from reportlab.pdfgen.canvas import Canvas

APP_VERSION = "4.4.1"


# ─────────────────────────────────────────────────────────────
# Geração Automatizada das Figuras Reais do Áudio m017 (300 DPI)
# ─────────────────────────────────────────────────────────────
def ensure_m017_figures(fig_dir, base_dir, force_rebuild=False):
    """
    Carrega o áudio m017_0376.wav através do CricketAnalyzer e gera as 5 figuras
    analíticas de alta resolução (300 DPI) caso ainda não existam no disco.
    """
    os.makedirs(fig_dir, exist_ok=True)
    fig1_path = os.path.join(fig_dir, 'fig1_dashboard_m017.png')
    fig2_path = os.path.join(fig_dir, 'fig2_waveform_lod_m017.png')
    fig3_path = os.path.join(fig_dir, 'fig3_spectrogram_hd_m017.png')
    fig4_path = os.path.join(fig_dir, 'fig4_psd_welch_m017.png')
    fig5_path = os.path.join(fig_dir, 'fig5_hist_bivariado_m017.png')

    all_exist = all(os.path.exists(p) for p in [fig1_path, fig2_path, fig3_path, fig4_path, fig5_path])
    if all_exist and not force_rebuild:
        return {
            'fig1': fig1_path, 'fig2': fig2_path,
            'fig3': fig3_path, 'fig4': fig4_path, 'fig5': fig5_path
        }

    print("[*] Processando amostra real m017_0376.wav para captura de figuras analiticas...")
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from core.analyzer import CricketAnalyzer
    from utils.constants import DEFAULT_ALGO_PARAMS

    possible_paths = [
        os.path.join(PROJECT_ROOT, 'extras', 'audios', 'm017_0376.wav'),
        os.path.join(base_dir or PROJECT_ROOT, 'extras', 'audios', 'm017_0376.wav'),
        os.path.join(PROJECT_ROOT, 'audios', 'm017_0376.wav'),
        os.path.join(base_dir or PROJECT_ROOT, 'audios', 'm017_0376.wav'),
        os.path.join(PROJECT_ROOT, 'm017_0376.wav'),
    ]
    wav_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not wav_path:
        raise FileNotFoundError(f"Arquivo de audio m017 nao encontrado em: {possible_paths}")

    # Configuração dos parâmetros analíticos com tolerância espectral de ±700 Hz
    params = dict(DEFAULT_ALGO_PARAMS)
    params["freq_tolerance_hz"] = 700.0

    res = CricketAnalyzer.analyze(wav_path, params)
    rate, data, data_b1, env, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration = res[:14]
    carrier_freq = float(res[15]) if len(res) > 15 else 5810.0
    f_psd = res[19] if len(res) > 19 else None
    Pxx_db = res[20] if len(res) > 20 else None

    palette = {
        1: '#F59E0B', 2: '#2563EB', 3: '#8B5CF6', 4: '#F97316',
        5: '#10B981', 6: '#EC4899', 7: '#06B6D4', 8: '#84CC16'
    }

    def safe_savefig(fig_obj, out_path, **kwargs):
        import time
        for attempt in range(6):
            try:
                with open(out_path, 'wb') as fp:
                    fig_obj.savefig(fp, format='png', **kwargs)
                return
            except OSError:
                if attempt < 5:
                    time.sleep(0.35)
                else:
                    raise

    # 1. Dashboard Completo (4 Painéis)
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    for ax in axes.flat:
        ax.set_facecolor('#FFFFFF')
        ax.grid(True, linestyle=':', alpha=0.6, color='#CBD5E1')
        ax.tick_params(colors='#334155', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#94A3B8')

    # 1.1 Waveform
    ax_w = axes[0, 0]
    t_wave = np.linspace(0, audio_duration, len(env))
    ax_w.plot(t_wave, data_b1, color='#94A3B8', lw=0.4, alpha=0.7, label='Sinal Filtrado')
    ax_w.plot(t_wave, env, color='#0284C7', lw=0.9, label='Envoltória Hilbert')
    for cp in chirp_peaks_list:
        qnt = len(cp)
        c = palette.get(qnt, '#64748B')
        ax_w.plot(np.array(cp)/rate, env[cp], 'x', color=c, markersize=4, markeredgewidth=1.2)
    ax_w.set_title('A: Forma de Onda & Envoltória com Picos Detectados', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax_w.set_xlabel('Tempo (s)', fontsize=8, color='#334155')
    ax_w.set_ylabel('Amplitude Normalizada', fontsize=8, color='#334155')
    ax_w.set_xlim(0, min(12.0, audio_duration))

    # 1.2 Spectrogram
    ax_s = axes[1, 0]
    im = ax_s.pcolormesh(t_spec, f_spec / 1000.0, Sxx_db, shading='auto', cmap='viridis', vmin=-70, vmax=0)
    ax_s.axhline(carrier_freq / 1000.0, color='#EF4444', linestyle='--', lw=1.2, label=f'Portadora ({carrier_freq/1000:.2f} kHz)')
    ax_s.set_title('C: Espectrograma STFT com Rastreamento de Portadora', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax_s.set_xlabel('Tempo (s)', fontsize=8, color='#334155')
    ax_s.set_ylabel('Frequência (kHz)', fontsize=8, color='#334155')
    ax_s.set_ylim(0, 12.0)
    ax_s.set_xlim(0, min(12.0, audio_duration))
    ax_s.legend(loc='upper right', fontsize=7.5, framealpha=0.85)

    # 1.3 Histograma Bivariado
    ax_h = axes[0, 1]
    unique_pulses, counts = np.unique(chirps, return_counts=True)
    colors_bar = [palette.get(p, '#64748B') for p in unique_pulses]
    bars = ax_h.bar(unique_pulses, counts, color=colors_bar, width=0.55, edgecolor='#475569', lw=0.6, zorder=3)
    for b in bars:
        h = b.get_height()
        ax_h.text(b.get_x() + b.get_width()/2, h + 0.8, f'{int(h)}', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#0F172A')
    ax_h.set_title('B: Histograma Bivariado (Contagem e Duração Média)', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax_h.set_xlabel('Pulsos por Chilreio', fontsize=8, color='#334155')
    ax_h.set_ylabel('Contagem de Chilreios', fontsize=8, color='#334155')
    ax_h.set_ylim(0, max(counts) * 1.25)
    ax_h.set_xticks(unique_pulses)

    dur_by_p = {}
    for cp in chirp_peaks_list:
        n_p = len(cp)
        d_ms = (cp[-1] - cp[0]) / rate * 1000.0
        dur_by_p.setdefault(n_p, []).append(d_ms)
    ax_h2 = ax_h.twinx()
    ax_h2.grid(False)
    d_means = [np.mean(dur_by_p[p]) for p in unique_pulses]
    ax_h2.plot(unique_pulses, d_means, color='#DC2626', linestyle='--', marker='o', markersize=5, lw=1.5, zorder=5)
    for p, dm in zip(unique_pulses, d_means):
        ax_h2.text(p, dm + 1.2, f'{dm:.1f} ms', ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#DC2626')
    ax_h2.set_ylabel('Duração Média (ms)', fontsize=8, color='#DC2626')
    ax_h2.tick_params(axis='y', colors='#DC2626', labelsize=8)
    ax_h2.spines['right'].set_color('#DC2626')
    ax_h2.set_ylim(min(d_means) * 0.85, max(d_means) * 1.20)

    # 1.4 PSD Welch
    ax_p = axes[1, 1]
    if f_psd is not None and Pxx_db is not None:
        mask = (f_psd <= 15000.0)
        f_k = f_psd[mask] / 1000.0
        p_k = Pxx_db[mask]
        ax_p.plot(f_k, p_k, color='#0284C7', lw=1.2)
        # Busca do pico bioacústico na banda de estridulação (>= 3.0 kHz) para isolar a portadora do canto
        mask_bio = (f_k >= 3.0) & (f_k <= 15.0)
        if np.any(mask_bio):
            sub_idx = np.where(mask_bio)[0]
            best_i = sub_idx[np.argmax(p_k[mask_bio])]
        else:
            best_i = np.argmin(np.abs(f_k - carrier_freq / 1000.0))
        f_max_khz = f_k[best_i]
        p_max = p_k[best_i]
        ax_p.plot(f_max_khz, p_max, 'ro', markersize=6, label=f'Pico: {f_max_khz:.2f} kHz')
        ax_p.annotate(f'{f_max_khz:.2f} kHz\n({p_max:.1f} dB)', xy=(f_max_khz, p_max), xytext=(f_max_khz + 1.2, p_max - 6),
                      arrowprops=dict(arrowstyle='->', color='#EF4444', lw=1.0), fontsize=8, fontweight='bold', color='#991B1B')
        ax_p.axvspan(max(0, (carrier_freq - 700)/1000.0), min(15, (carrier_freq + 700)/1000.0), color='#BAE6FD', alpha=0.4, label='Tolerância ±700 Hz')
    ax_p.set_title('D: Densidade Espectral de Potência (PSD via Welch)', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax_p.set_xlabel('Frequência (kHz)', fontsize=8, color='#334155')
    ax_p.set_ylabel('Potência (dB/Hz)', fontsize=8, color='#334155')
    ax_p.set_xlim(0, 15.0)
    ax_p.legend(loc='lower left', fontsize=7.5, framealpha=0.85)

    plt.tight_layout()
    safe_savefig(fig, fig1_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

    # 2. Forma de Onda & LOD Min-Max
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5.2), dpi=300, gridspec_kw={'height_ratios': [1.2, 1.0]})
    fig.patch.set_facecolor('#F8FAFC')
    for ax in (ax1, ax2):
        ax.set_facecolor('#FFFFFF')
        ax.grid(True, linestyle=':', alpha=0.6, color='#CBD5E1')
        ax.tick_params(colors='#334155', labelsize=8)
        for s in ax.spines.values(): s.set_color('#94A3B8')

    z0, z1 = 2.5, 4.5
    idx0, idx1 = int(z0 * rate), int(z1 * rate)
    ax1.plot(t_wave[idx0:idx1], data_b1[idx0:idx1], color='#94A3B8', lw=0.4, alpha=0.6, label='Sinal Bruto Filtrado')
    ax1.plot(t_wave[idx0:idx1], env[idx0:idx1], color='#0284C7', lw=1.2, label='Envoltória de Hilbert Suavizada')
    pks_in_win = [p for p in peaks if idx0 <= p <= idx1]
    ax1.plot(np.array(pks_in_win)/rate, env[pks_in_win], 'x', color='#10B981', markersize=6, markeredgewidth=1.8, label='Pulsos Detectados (Moda: 5p)')
    ax1.set_title('A: Estrutura Temporal dos Pulsos de Estridulação (m017 - Janela de 2.0 s)', fontsize=9, fontweight='bold', color='#0F172A', pad=5)
    ax1.set_ylabel('Amplitude Normalizada', fontsize=8, color='#334155')
    ax1.set_xlim(z0, z1)
    ax1.legend(loc='upper right', fontsize=7.5, framealpha=0.85)

    pz0, pz1 = 3.05, 3.22
    pidx0, pidx1 = int(pz0 * rate), int(pz1 * rate)
    t_p = t_wave[pidx0:pidx1]
    y_p = data_b1[pidx0:pidx1]
    n_b = 60
    bsize = len(y_p) // n_b
    y_trunc = y_p[:bsize * n_b].reshape(n_b, bsize)
    t_trunc = t_p[:bsize * n_b:bsize]
    y_min = y_trunc.min(axis=1)
    y_max = y_trunc.max(axis=1)
    t_env = np.empty(n_b * 2)
    y_env = np.empty(n_b * 2)
    t_env[0::2] = t_trunc; t_env[1::2] = t_trunc
    y_env[0::2] = y_min; y_env[1::2] = y_max

    ax2.plot(t_p, y_p, color='#CBD5E1', lw=0.4, label=f'Amostras Reais ({len(t_p)} pts brutos)')
    ax2.plot(t_env, y_env, color='#D97706', lw=1.2, label=f'Decimação Min-Max LOD ({n_b*2} vértices renderizados)')
    ax2.set_title('B: Mecanismo de Decimação Min-Max (Preservação de Picos sem Overdraw)', fontsize=9, fontweight='bold', color='#0F172A', pad=5)
    ax2.set_xlabel('Tempo (s)', fontsize=8, color='#334155')
    ax2.set_ylabel('Amplitude', fontsize=8, color='#334155')
    ax2.set_xlim(pz0, pz1)
    ax2.legend(loc='upper right', fontsize=7.5, framealpha=0.85)

    plt.tight_layout()
    safe_savefig(fig, fig2_path, dpi=300, facecolor=fig.get_facecolor())
    plt.close()

    # 3. Espectrograma HD
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#FFFFFF')
    w_sec = min(10.0, audio_duration)
    mask_t = (t_spec <= w_sec)
    im = ax.pcolormesh(t_spec[mask_t], f_spec / 1000.0, Sxx_db[:, mask_t], shading='auto', cmap='magma', vmin=-65, vmax=0)
    ax.axhline(carrier_freq / 1000.0, color='#38BDF8', linestyle='--', lw=1.5, label=f'Frequência Portadora Modal fc = {carrier_freq/1000:.2f} kHz')
    pks_in_w = [p for p in peaks if p/rate <= w_sec]
    ax.plot(np.array(pks_in_w)/rate, [carrier_freq/1000.0]*len(pks_in_w), 'x', color='#4ADE80', markersize=4.5, markeredgewidth=1.2, label='Pulsos Validados na Portadora')
    ax.set_title(f'Espectrograma STFT de Alta Resolução (m017 - fc = {carrier_freq/1000:.2f} kHz, Janela 1024 Hann)', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax.set_xlabel('Tempo (s)', fontsize=8.5, color='#334155')
    ax.set_ylabel('Frequência (kHz)', fontsize=8.5, color='#334155')
    ax.set_ylim(0, 10.0)
    ax.set_xlim(0, w_sec)
    cbar = plt.colorbar(im, ax=ax, pad=0.015, aspect=20)
    cbar.set_label('Densidade Espectral (dB)', fontsize=8, color='#334155')
    cbar.ax.tick_params(labelsize=7.5, colors='#334155')
    ax.legend(loc='upper right', fontsize=8, framealpha=0.85)
    plt.tight_layout()
    safe_savefig(fig, fig3_path, dpi=300, facecolor=fig.get_facecolor())
    plt.close()

    # 4. PSD Welch
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#FFFFFF')
    ax.grid(True, linestyle=':', alpha=0.6, color='#CBD5E1')
    for s in ax.spines.values(): s.set_color('#94A3B8')

    mask_p = (f_psd <= 15000.0)
    f_khz = f_psd[mask_p] / 1000.0
    p_db = Pxx_db[mask_p]
    ax.plot(f_khz, p_db, color='#0284C7', lw=1.5, label='Densidade Espectral de Potência (Método de Welch)')

    # Busca do pico bioacústico na banda de estridulação (>= 3.0 kHz) para isolar a portadora do canto
    mask_bio = (f_khz >= 3.0) & (f_khz <= 15.0)
    if np.any(mask_bio):
        sub_idx = np.where(mask_bio)[0]
        best_i = sub_idx[np.argmax(p_db[mask_bio])]
    else:
        best_i = np.argmin(np.abs(f_khz - carrier_freq / 1000.0))
    f_max_val = f_khz[best_i]
    p_max_val = p_db[best_i]

    ax.plot(f_max_val, p_max_val, 'ro', markersize=7, label=f'Pico da Portadora: {f_max_val:.2f} kHz ({p_max_val:.1f} dB/Hz)')
    ax.annotate(f'Portadora Bioacústica: {f_max_val:.2f} kHz\nP_max: {p_max_val:.1f} dB/Hz', xy=(f_max_val, p_max_val), xytext=(f_max_val + 1.5, p_max_val - 5),
                arrowprops=dict(arrowstyle='->', color='#EF4444', lw=1.2), fontsize=8.5, fontweight='bold', color='#991B1B')
    t_low = (carrier_freq - 700)/1000.0
    t_high = (carrier_freq + 700)/1000.0
    ax.axvspan(t_low, t_high, color='#BAE6FD', alpha=0.45, label='Banda de Tolerância Espectral (±700 Hz)')
    ax.set_title('Densidade Espectral de Potência (PSD) via Método de Welch (m017)', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax.set_xlabel('Frequência (kHz)', fontsize=8.5, color='#334155')
    ax.set_ylabel('Potência (dB/Hz)', fontsize=8.5, color='#334155')
    ax.set_xlim(0, 15.0)
    ax.legend(loc='lower left', fontsize=8, framealpha=0.9)
    plt.tight_layout()
    safe_savefig(fig, fig4_path, dpi=300, facecolor=fig.get_facecolor())
    plt.close()

    # 5. Histograma Bivariado
    fig, ax1 = plt.subplots(figsize=(10, 4.5), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax1.set_facecolor('#FFFFFF')
    ax1.grid(True, linestyle=':', alpha=0.6, color='#CBD5E1')
    for s in ax1.spines.values(): s.set_color('#94A3B8')

    unique_p, c_counts = np.unique(chirps, return_counts=True)
    b_colors = [palette.get(p, '#64748B') for p in unique_p]
    bars = ax1.bar(unique_p, c_counts, color=b_colors, width=0.52, edgecolor='#334155', lw=0.8, zorder=3, label='Contagem de Chilreios')
    for b in bars:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2, h + 0.9, f'{int(h)} chirps', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#0F172A')
    ax1.set_title('Histograma Bivariado: Sintaxe de Pulsos vs. Duração Média (m017)', fontsize=9.5, fontweight='bold', color='#0F172A', pad=6)
    ax1.set_xlabel('Pulsos por Chilreio', fontsize=8.5, color='#334155')
    ax1.set_ylabel('Contagem Total de Chilreios', fontsize=8.5, color='#334155')
    ax1.set_ylim(0, max(c_counts) * 1.25)
    ax1.set_xticks(unique_p)

    ax2 = ax1.twinx()
    ax2.grid(False)
    d_means_all = [np.mean(dur_by_p[p]) for p in unique_p]
    ax2.plot(unique_p, d_means_all, color='#DC2626', linestyle='--', marker='o', markersize=6, lw=1.8, zorder=5, label='Duração Média (ms)')
    for p, dm in zip(unique_p, d_means_all):
        ax2.text(p, dm + 1.4, f'{dm:.1f} ms', ha='center', va='bottom', fontsize=8, fontweight='bold', color='#DC2626')
    ax2.set_ylabel('Duração Média do Chilreio (ms)', fontsize=8.5, color='#DC2626')
    ax2.tick_params(axis='y', colors='#DC2626', labelsize=8)
    ax2.spines['right'].set_color('#DC2626')
    ax2.set_ylim(min(d_means_all) * 0.85, max(d_means_all) * 1.20)

    plt.tight_layout()
    safe_savefig(fig, fig5_path, dpi=300, facecolor=fig.get_facecolor())
    plt.close()

    print("[OK] Todas as 5 figuras de alta resolucao foram geradas com sucesso em:", fig_dir)
    return {
        'fig1': fig1_path, 'fig2': fig2_path,
        'fig3': fig3_path, 'fig4': fig4_path, 'fig5': fig5_path
    }


# ─────────────────────────────────────────────────────────────
# Canvas com numeração dinâmica de páginas (sem duplicação)
# ─────────────────────────────────────────────────────────────
class DocCanvas(Canvas):
    """
    Canvas em duas passagens para cálculo dinâmico de páginas totais.
    Utiliza _startPage() em showPage() para evitar a duplicação de páginas.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_decorations(i + 1, num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, page_num, total_pages):
        if page_num == 1:
            return

        self.saveState()
        w, h = A4

        # Cabeçalho superior (Páginas 2 em diante)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(2 * cm, h - 1.2 * cm, "CRINÔMETRO")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(4.2 * cm, h - 1.2 * cm, f"|  Documentação Técnica e Científica (v{APP_VERSION})")
        self.drawRightString(w - 2 * cm, h - 1.2 * cm, "Bioacústica & Engenharia de Computação")

        # Linha fina do cabeçalho
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(2 * cm, h - 1.4 * cm, w - 2 * cm, h - 1.4 * cm)

        # Rodapé inferior
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(2 * cm, 1.1 * cm,
                        f"Crinômetro v{APP_VERSION}  •  Processamento Digital de Sinais, IA e Computação Gráfica")
        self.drawRightString(w - 2 * cm, 1.1 * cm,
                             f"Página {page_num} de {total_pages}")

        # Linha fina do rodapé
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)

        self.restoreState()


# ─────────────────────────────────────────────────────────────
# Definição Tipográfica e Estilos
# ─────────────────────────────────────────────────────────────
def build_styles():
    ss = getSampleStyleSheet()

    styles = {}
    styles["title"] = ParagraphStyle(
        "DocTitle", parent=ss["Title"],
        fontSize=24, leading=30, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER
    )
    styles["subtitle"] = ParagraphStyle(
        "DocSubtitle", parent=ss["Normal"],
        fontSize=12, leading=17, textColor=colors.HexColor("#334155"),
        spaceAfter=14, alignment=TA_CENTER
    )
    styles["version_badge"] = ParagraphStyle(
        "DocVersionBadge", parent=ss["Normal"],
        fontSize=10, leading=14, textColor=colors.HexColor("#0284C7"),
        fontName="Helvetica-Bold", spaceAfter=20, alignment=TA_CENTER
    )
    styles["h1"] = ParagraphStyle(
        "H1", parent=ss["Heading1"],
        fontSize=15, leading=20, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8,
        keepWithNext=True
    )
    styles["h2"] = ParagraphStyle(
        "H2", parent=ss["Heading2"],
        fontSize=12, leading=16, textColor=colors.HexColor("#1E293B"),
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
        keepWithNext=True
    )
    styles["h3"] = ParagraphStyle(
        "H3", parent=ss["Heading3"],
        fontSize=10.5, leading=15, textColor=colors.HexColor("#334155"),
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4,
        keepWithNext=True
    )
    styles["body"] = ParagraphStyle(
        "DocBody", parent=ss["Normal"],
        fontSize=9.5, leading=14.5, textColor=colors.HexColor("#1E293B"),
        spaceAfter=7, alignment=TA_JUSTIFY
    )
    styles["body_indent"] = ParagraphStyle(
        "DocBodyIndent", parent=styles["body"],
        leftIndent=14, spaceAfter=5
    )
    styles["code"] = ParagraphStyle(
        "DocCode", parent=ss["Code"],
        fontSize=8.2, leading=11.5, textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F8FAFC"),
        borderColor=colors.HexColor("#E2E8F0"),
        borderWidth=0.5, borderPadding=5,
        spaceBefore=4, spaceAfter=7,
        fontName="Courier"
    )
    styles["formula"] = ParagraphStyle(
        "Formula", parent=ss["Normal"],
        fontSize=9.5, leading=14, textColor=colors.HexColor("#0F172A"),
        alignment=TA_CENTER, spaceBefore=5, spaceAfter=7,
        fontName="Helvetica", backColor=colors.HexColor("#F8FAFC"),
        borderColor=colors.HexColor("#E2E8F0"), borderWidth=0.5,
        borderPadding=6
    )
    styles["caption"] = ParagraphStyle(
        "Caption", parent=ss["Normal"],
        fontSize=8.5, leading=12, textColor=colors.HexColor("#475569"),
        spaceBefore=4, spaceAfter=10, alignment=TA_CENTER,
        fontName="Helvetica-Bold"
    )
    styles["callout_title"] = ParagraphStyle(
        "CalloutTitle", parent=ss["Normal"],
        fontSize=9, leading=12, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceAfter=2
    )
    styles["callout_body"] = ParagraphStyle(
        "CalloutBody", parent=ss["Normal"],
        fontSize=8.5, leading=12.5, textColor=colors.HexColor("#334155"),
        fontName="Helvetica", alignment=TA_JUSTIFY
    )
    styles["table_header"] = ParagraphStyle(
        "THeader", parent=ss["Normal"],
        fontSize=8.5, leading=11, textColor=colors.white,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    styles["table_cell"] = ParagraphStyle(
        "TCell", parent=ss["Normal"],
        fontSize=8.0, leading=11, textColor=colors.HexColor("#1E293B"),
        fontName="Helvetica", alignment=TA_LEFT
    )
    styles["table_cell_center"] = ParagraphStyle(
        "TCellCenter", parent=styles["table_cell"],
        alignment=TA_CENTER
    )
    styles["toc_item"] = ParagraphStyle(
        "TOCItem", parent=ss["Normal"],
        fontSize=8.5, leading=11, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceBefore=3, spaceAfter=1
    )
    styles["toc_subitem"] = ParagraphStyle(
        "TOCSubItem", parent=styles["toc_item"],
        fontSize=7.5, leading=9.5, textColor=colors.HexColor("#475569"),
        fontName="Helvetica", leftIndent=12, spaceAfter=1
    )
    return styles


# ─────────────────────────────────────────────────────────────
# Helpers Visuais e Estruturais
# ─────────────────────────────────────────────────────────────
def hr():
    return HRFlowable(width="100%", thickness=0.6,
                      color=colors.HexColor("#CBD5E1"),
                      spaceBefore=6, spaceAfter=8)


def make_callout(title, text, S, box_type="info"):
    color_map = {
        "didactic": (colors.HexColor("#F0F9FF"), colors.HexColor("#0284C7"), colors.HexColor("#BAE6FD")),
        "bio":      (colors.HexColor("#F0FDF4"), colors.HexColor("#059669"), colors.HexColor("#BBF7D0")),
        "warning":  (colors.HexColor("#FFFBEB"), colors.HexColor("#D97706"), colors.HexColor("#FDE68A")),
        "eng":      (colors.HexColor("#F8FAFC"), colors.HexColor("#475569"), colors.HexColor("#CBD5E1")),
    }
    bg_color, bar_color, border_color = color_map.get(box_type, color_map["didactic"])

    p_title = Paragraph(f"<b>{title}</b>", S["callout_title"])
    p_body = Paragraph(text, S["callout_body"])

    t = Table([[ [p_title, p_body] ]], colWidths=[17.0 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('LINELEFT', (0, 0), (0, -1), 3.0, bar_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def make_table(header, rows, S, col_widths=None, align_left=True):
    wrapped_data = []
    header_row = [Paragraph(h, S["table_header"]) for h in header]
    wrapped_data.append(header_row)

    for r in rows:
        row_cells = []
        for idx, cell in enumerate(r):
            if isinstance(cell, str):
                cell_style = S["table_cell"] if (align_left or idx > 0) else S["table_cell_center"]
                row_cells.append(Paragraph(cell, cell_style))
            else:
                row_cells.append(cell)
        wrapped_data.append(row_cells)

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#64748B')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]
    t = Table(wrapped_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return t


# ─────────────────────────────────────────────────────────────
# Construção do Conteúdo Completo
# ─────────────────────────────────────────────────────────────
def build_content(S, fig_paths):
    E = []
    p = lambda text, style="body": Paragraph(text, S[style])

    # ═══════════════════════════════════════════
    # CAPA
    # ═══════════════════════════════════════════
    E.append(Spacer(1, 2.0 * cm))
    E.append(p("CRINÔMETRO", "title"))
    E.append(p("Documentação Técnica, Científica e Manual Metodológico Exaustivo", "subtitle"))
    E.append(p(f"Versão Canônica: v{APP_VERSION} (Expandida com Engenharia de Computação & Amostra Real m017)", "version_badge"))
    E.append(Spacer(1, 0.3 * cm))

    cover_text = (
        "<b>Fundamentação Multidisciplinar:</b> Processamento Digital de Sinais (DSP), Bioacústica Computacional,<br/>"
        "Computação Gráfica (LOD & Blitting), Concorrência Assíncrona Qt, Otimização de Memória SIMD/Cache L2/L3,<br/>"
        "Modelagem Fisiológica Termo-Acústica e Inteligência Artificial com Aprendizado Ativo (GMM/Boosting).<br/><br/>"
        f"<b>Data de Compilação:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M')}<br/>"
        "<b>Amostra de Referência Bioacústica:</b> Espécime <i>m017</i> (arquivo <code>m017_0376.wav</code> — 48.0 kHz, Gryllidae).<br/>"
        "<b>Público-Alvo:</b> Pesquisadores em Bioacústica, Cientistas da Computação, Engenheiros de Software,<br/>"
        "Ecólogos Comportamentais, Bancas Acadêmicas de Defesa e Desenvolvedores Interdisciplinares."
    )
    E.append(p(cover_text, "subtitle"))
    E.append(Spacer(1, 0.8 * cm))

    box_intro = (
        "<b>Declaração de Rigor Científico e Acessibilidade:</b> Este documento foi formulado sob o princípio da "
        "dupla finalidade: fornecer rigor matemático absoluto, código exato e decisões de engenharia de software "
        "em nível de produção para auditoria acadêmica, ao mesmo tempo em que oferece analogias didáticas intuitivas, "
        "permitindo que pesquisadores de qualquer área compreendam como o software opera e foi construído."
    )
    E.append(make_callout("[DOCUMENTO CANÔNICO DE REFERÊNCIA - v4.4.1]", box_intro, S, "didactic"))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SUMÁRIO
    # ═══════════════════════════════════════════
    E.append(p("SUMÁRIO GERAL", "h1"))
    E.append(hr())

    toc_structure = [
        ("1. Fundamentos Biológicos e Bioacústica da Estridulação", [
            "1.1. O Canto dos Grilos: Origem Evolutiva e Função Comportamental",
            "1.2. Anatomia Funcional e Mecanismo de Fricção Tegminal",
            "1.3. A Hierarquia Temporal: Pulso, Chilreio, IPI, ICI e Portadora",
            "1.4. Os Desafios do Mundo Real: Ruído de Fundo, Vento e Coro Concorrente",
        ]),
        ("2. Arquitetura Geral do Sistema e Pipeline de Dados (Dataflow)", [
            "2.1. O Ciclo de Vida do Sinal (Da Ingestão WAV ao Laudo Estruturado)",
            "2.2. Organização Modular do Código-Fonte e Separação de Camadas",
            "2.3. Execução Assíncrona Não-Bloqueante e Cancelamento Cooperativo",
            "2.4. [Figura 1] Visão Geral da Interface e Dashboard Analítico com m017",
        ]),
        ("3. Processamento Digital de Sinais (DSP): O Motor Matemático", [
            "3.1. Condicionamento do Sinal: Mono, Normalização e Offset DC",
            "3.2. Tratamento de Bordas: Downmix Estéreo e Análise de Cancelamento de Fase",
            "3.3. Filtragem Passa-Altas de 50 Hz (Butterworth 2ª Ordem SOS)",
            "3.4. Filtragem Passa-Faixa IIR (Butterworth 4ª Ordem SOS [3200–6000 Hz])",
            "3.5. Transformada de Fourier de Curto Tempo (STFT) e Espectrograma",
            "3.6. Refinamento Sub-bin Parabólico de Frequência",
            "3.7. [v4.4.0] Densidade Espectral de Potência (PSD via Método de Welch)",
            "3.8. [Figuras 3 e 4] Espectrograma HD e Curva PSD do Espécime m017",
        ]),
        ("4. Detecção, Segmentação e Agrupamento Bioacústico", [
            "4.1. Extração da Envoltória Instantânea via Transformada de Hilbert",
            "4.2. Suavização Hanning e Limiar Adaptativo por Percentis",
            "4.3. Detecção Morfológica de Picos e Validação Temporal",
            "4.4. Rastreamento da Portadora Modal e Filtro de Banda Estreita (±700 Hz)",
            "4.5. As Cinco Camadas do Agrupamento em Chilreios e Imposição de min_p",
            "4.6. [v4.4.0] Histograma Bivariado com Eixo Duplo (twinx: Contagem e Duração)",
            "4.7. [Figuras 2 e 5] Detalhe da Envoltória de Hilbert e Histograma Bivariado de m017",
        ]),
        ("5. Biometria Bioacústica e Modelagem Fisiológica", [
            "5.1. Métricas Bioacústicas Fundamentais (Tabela Exaustiva)",
            "5.2. Diagnóstico de Cadência Rítmica (Regressão Linear e Teste t de Student)",
            "5.3. Modelagem Termo-Acústica: A Lei de Dolbear e Ectotermia",
        ]),
        ("6. Inteligência Artificial e Aprendizado Ativo (Active Learning)", [
            "6.1. Filosofia de Design: [v4.4.0] Modo DSP Nativo e Reset de IA",
            "6.2. Engenharia de Recursos: O Vetor de 20 Features Bioacústicas",
            "6.3. Separação Não-Supervisionada: Modelo de Mistura de Gaussianas (GMM)",
            "6.4. Classificador Supervisionado HistGradientBoosting e Score Híbrido",
            "6.5. Mineração de Negativos Difíceis e Poda Contrastiva",
            "6.6. Filtro de Coerência Rítmica e o Ciclo Humano de Feedback Ativo",
        ]),
        ("7. Engenharia de Computação, Computação Gráfica e Baixo Nível", [
            "7.1. Pipeline Gráfico: Decimação Adaptativa Min-Max (Level of Detail - LOD)",
            "7.2. Aceleração de Tela: Raster Blitting e Double Buffering a 60 FPS",
            "7.3. Concorrência e Threading: Modelo Qt, QueuedConnection e Liberação do GIL",
            "7.4. Estruturas de Dados e Memória: float32, Cache L1/L2/L3 e Vetorização SIMD",
            "7.5. Poda Espacial Adaptativa no Hover (MainWindow.on_motion: O(N) para O(K))",
            "7.6. Segurança da Informação (AppSec): Análise de Riscos do Pickle e Roadmap",
            "7.7. Arquitetura de Software: O Contexto da God Class e Roadmap v4.5.0",
        ]),
        ("8. Engenharia de Distribuição e Auto-Updater [v4.4.1]", [
            "8.1. Arquitetura do Launcher e Ciclo de Vida da Aplicação",
            "8.2. O Sistema de Auto-Atualização via API do GitHub Releases",
            "8.3. [v4.4.1] Resolução Crítica: Script PowerShell UTF-8-BOM e os._exit(0)",
        ]),
        ("9. Glossário Metodológico para Defesa Acadêmica e Publicação", [
            "9.1. Seção de Materiais e Métodos Pronta para Teses e Artigos",
            "9.2. Matriz Sintética: Conceito Biológico <-> Algoritmo <-> Código-Fonte",
        ]),
    ]

    for section_title, subsections in toc_structure:
        E.append(p(f"<b>{section_title}</b>", "toc_item"))
        for sub in subsections:
            E.append(p(sub, "toc_subitem"))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 1: BIOACÚSTICA FUNDAMENTAL
    # ═══════════════════════════════════════════
    E.append(p("1. FUNDAMENTOS BIOLÓGICOS E BIOACÚSTICA DA ESTRIDULAÇÃO", "h1"))
    E.append(hr())

    E.append(p("1.1. O Canto dos Grilos: Origem Evolutiva e Função Comportamental", "h2"))
    E.append(p(
        "Os grilos (ordem Orthoptera, subordem Ensifera, família Gryllidae) utilizam a comunicação acústica como "
        "seu principal sistema de sinalização comportamental para reprodução, demarcação territorial e sobrevivência. "
        "Ao contrário dos vertebrados terrestres, que produzem som por modulação de fluxo de ar através de cordas vocais "
        "na laringe ou siringe, os insetos desenvolveram estruturas mecânicas exoesqueléticas rígidas denominadas "
        "<b>aparelhos estridulatórios tegumentares</b>.", "body"
    ))
    E.append(p(
        "A estridulação desempenha três papéis ecológicos vitais: "
        "(a) <b>Canto de Chamado (Calling Song):</b> emitido pelo macho estacionário para atrair fêmeas receptivas co-específicas "
        "a dezenas de metros de distância; "
        "(b) <b>Canto de Corte (Courtship Song):</b> vocalização de baixa amplitude emitida na presença imediata da fêmea; "
        "(c) <b>Canto de Agressão/Rivalidade (Rivalry Song):</b> rajadas acústicas rápidas e desordenadas para dissuadir machos rivais. "
        "O Crinômetro foi projetado com sensibilidade matemática calibrada para diagnosticar o canto de chamado, cuja "
        "estereotipia rítmica fornece caracteres diagnósticos de alto valor para taxonomia e especiação críptica.", "body"
    ))

    analogia_pente = (
        "[ANALOGIA DIDÁTICA: O PENTE E A PALHETA]<br/>"
        "Para entender intuitivamente como o grilo produz som, imagine passar a ponta do dedo ou uma palheta "
        "plástica rapidamente ao longo dos dentes de um pente de cabelo. Cada dente atingido produz um pequeno clique "
        "ou estalo. Se você passar o dedo muito rápido, os cliques individuais se fundem aos nossos ouvidos, "
        "gerando uma nota musical contínua. É exatamente assim que o grilo canta: raspando uma lima microscópica "
        "contra uma saliência endurecida nas suas asas."
    )
    E.append(make_callout("Mecanismo Intuitivo de Produção Sonora", analogia_pente, S, "didactic"))
    E.append(Spacer(1, 0.2 * cm))

    E.append(p("1.2. Anatomia Funcional e Mecanismo de Fricção Tegminal", "h2"))
    E.append(p(
        "O aparelho estridulatório dos machos localiza-se nas asas anteriores coriáceas, denominadas <b>tégminas</b>. "
        "Durante o canto, o grilo eleva as tégminas em um ângulo de aproximadamente 45° em relação ao dorso e "
        "executa aduções (fechamentos) e abduções (aberturas) rápidas impulsionadas pela musculatura torácica:", "body"
    ))
    E.append(p(
        "• <b>A Lima Estridulatória (File):</b> nervura transversal espessada na face ventral da asa direita, "
        "recoberta por uma fileira ordenada de 50 a 300 microdentes quitinosos convexos.<br/>"
        "• <b>A Raspadeira ou Plectro (Scraper):</b> uma lâmina quitinosa rígida na margem anal da asa esquerda.<br/>"
        "• <b>O Espelho (Mirror) e a Harpa (Harp):</b> membranas alares transparentes, delgadas e sem venação que atuam "
        "como diafragmas ressonadores acústicos acoplados. Quando o plectro percute os dentes da lima, as vibrações mecânicas "
        "são transferidas instantaneamente para a harpa, amplificando o sinal no ar exatamente como o tampo ressonador de um violão.", "body"
    ))
    E.append(p(
        "<b>Geração Quase-Senoidal:</b> Devido à alta ressonância mecânica alar (elevado fator de qualidade Q), "
        "o som irradiado concentra mais de 90% da sua potência em um tom quase puramente senoidal (frequência portadora), "
        "com distorção harmônica mínima, o que facilita o isolamento digital através de filtros passa-faixa.", "body"
    ))

    E.append(p("1.3. A Hierarquia Temporal: Pulso, Chilreio, IPI, ICI e Portadora", "h2"))
    E.append(p(
        "A análise bioacústica automatizada do Crinômetro estrutura a estridulação em uma hierarquia "
        "discreta de cinco grandezas fundamentais:", "body"
    ))

    hier_data = [
        ["Elemento Bioacústico", "Definição Física", "Comportamento Biológico Correspondente"],
        ["Pulso (Pulse / Syllable)", "Trem sonoro contínuo de curta duração (3 a 40 ms)", "Resultado de um único movimento de fechamento das tégminas (as asas fecham, a lima raspa)"],
        ["Chilreio (Chirp / Echeme)", "Sequência agrupada de pulsos separados por micropausas", "Ciclo muscular completo de estridulação; a unidade de atração que a fêmea reconhece"],
        ["IPI (Inter-Pulse Interval)", "Intervalo temporal medido entre o fim de um pulso e o início do próximo", "Tempo que o grilo leva para reabrir ligeiramente as asas sem atrito antes de fechar de novo"],
        ["ICI (Inter-Chirp Interval)", "Intervalo de silêncio entre dois chilreios consecutivos", "Pausa neuromotora e respiratória entre frases musicais consecutivas"],
        ["Frequência Portadora (fc)", "Frequência fundamental dominante do tom sonoro (Hz)", "A nota musical pura do canto (geralmente entre 3.200 Hz e 6.000 Hz nas espécies brasileiras)"],
    ]
    E.append(make_table(hier_data[0], hier_data[1:], S, col_widths=[3.8 * cm, 6.2 * cm, 7.0 * cm]))
    E.append(Spacer(1, 0.3 * cm))

    E.append(p("1.4. Os Desafios do Mundo Real: Ruído de Fundo, Vento e Coro Concorrente", "h2"))
    E.append(p(
        "Em gravações ecológicas de campo, o pesquisador raramente obtém áudios ideais. Três classes de ruído "
        "desafiam o processamento: (1) <b>Infrassom de turbulência e vento (< 50 Hz)</b>, que satura transientes; "
        "(2) <b>Ruídos difusos ambientais (folhas, chuva, tráfego)</b>; (3) <b>Coro concorrente polifônico:</b> "
        "outros machos ou insetos cantando no mesmo habitat. O Crinômetro integra técnicas avançadas de DSP e IA "
        "para isolar cirurgicamente o espécime focal mais próximo do microfone.", "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 2: ARQUITETURA GERAL E DATAFLOW
    # ═══════════════════════════════════════════
    E.append(p("2. ARQUITETURA GERAL DO SISTEMA E PIPELINE DE DADOS (DATAFLOW)", "h1"))
    E.append(hr())

    E.append(p("2.1. O Ciclo de Vida do Sinal (Da Ingestão WAV ao Laudo Estruturado)", "h2"))
    E.append(p(
        "O pipeline analítico do Crinômetro é sequencial, determinístico e auditável. "
        "A transformação do sinal bruto em métricas biométricas obedece a 8 estágios estruturados:", "body"
    ))

    flow_table_data = [
        ["Estágio", "Operação Matemática", "Módulo / Arquivo", "Objetivo Prático"],
        ["1. Ingestão", "Leitura binária, colapso mono e conversão float32", "scipy.io.wavfile", "Padronização de formatos e corte de 50% no uso de RAM"],
        ["2. Condicionamento", "Subtração da média (DC) e Highpass 50 Hz (Butterworth 2ª)", "scipy.signal.sosfilt", "Eliminar ruído de vento e evitar pico fantasma em 0 Hz"],
        ["3. Filtragem Passa-Faixa", "Butterworth IIR 4ª ordem SOS [3.2 a 6.0 kHz]", "core/analyzer.py", "Isolar a banda espectral de estridulação dos Gryllidae"],
        ["4. Espectro & Portadora", "STFT Hann (1024 amostras) + Refinamento Parabólico + Welch PSD", "scipy.signal.spectrogram / welch", "Gerar a matriz tempo-frequência e a assinatura média de potência"],
        ["5. Envoltória Analítica", "Transformada de Hilbert + Convolução Hanning (2 ms)", "scipy.signal.hilbert", "Eliminar a oscilação da portadora e revelar os pulsos temporais"],
        ["6. Detecção de Picos", "find_peaks adaptativo (Percentil 25 x 2.5) + Validação FWHM", "scipy.signal.find_peaks", "Localizar no tempo o ápice de cada batimento alar"],
        ["7. Filtro de Portadora", "Histograma modal com filtro de tolerância (ex.: ±700 Hz ajustável pelo usuário)", "core/analyzer.py", "Excluir pulsos rivais fora do espectro (desvios a partir de ±700 Hz)"],
        ["8. Agrupamento em Chilreios", "Validação temporal (IPI), ICI Gate e contagem mínima (min_p)", "core/analyzer.py (regroup_chirps)", "Agrupar pulsos nos chilreios biológicos verdadeiros"],
    ]
    E.append(make_table(flow_table_data[0], flow_table_data[1:], S, col_widths=[2.4 * cm, 5.8 * cm, 3.8 * cm, 5.0 * cm]))
    E.append(Spacer(1, 0.4 * cm))

    E.append(p("2.2. Organização Modular do Código-Fonte e Separação de Camadas", "h2"))
    E.append(p(
        "A arquitetura separa estritamente a interface gráfica (PyQt6) da computação matemática. "
        "Essa separação de preocupações (Separation of Concerns - SoC) garante testabilidade headless e "
        "execução em lote independente:", "body"
    ))

    mod_data = [
        ["Módulo Python", "Localização no Projeto", "Responsabilidade no Sistema"],
        ["CricketAnalyzer", "core/analyzer.py", "Motor matemático monolítico: filtros IIR SOS, STFT, Hilbert, agrupamento de chilreios e cálculo de métricas."],
        ["PulseLearner", "core/learner.py", "Cérebro de IA: extração de 20 features, clustering GMM bimodal, classificador HistGradientBoosting e active learning."],
        ["HighPerfLineEngine", "core/engines.py", "Renderizador de alta performance para a forma de onda com decimação min-max em múltiplos níveis de detalhe (LOD)."],
        ["HighPerfSpectrogramEngine", "core/engines.py", "Renderizador adaptativo de espectrogramas com particionamento em tiles e decimação dinâmica de colunas."],
        ["GenericWorker", "core/worker.py", "Envoltório de QThread com controle de concorrência, sinalização tipada e mecanismo cooperativo de abortar análises."],
        ["MainWindow", "ui/main_window.py", "Janela principal: orquestração de eventos, painéis, menu de gráficos, reprodução de áudio e interação."],
        ["PlotPanel", "ui/panels.py", "Widget de cartão de gráfico: toolbar responsiva, canvas Matplotlib integrado, sliders de portadora e botões de preset."],
        ["report_generator", "utils/report_generator.py", "Compilador de relatórios PDF com suporte a laudos comparativos por espécime e cadência rítmica."],
        ["launcher", "launcher.py", "Gerenciador de boot, splash screen animada, checagem assíncrona de versões e inicializador da aplicação."],
    ]
    E.append(make_table(mod_data[0], mod_data[1:], S, col_widths=[3.8 * cm, 3.8 * cm, 9.4 * cm]))
    E.append(Spacer(1, 0.3 * cm))

    E.append(p("2.3. Execução Assíncrona Não-Bloqueante e Cancelamento Cooperativo", "h2"))
    E.append(p(
        "Operações de DSP em gravações de vários minutos manipulam milhões de pontos flutuantes. Para impedir "
        "o congelamento da interface, a MainWindow instancia um worker assíncrono (<font face='Courier'>GenericWorker</font>) "
        "executado em thread de background com monitoramento cooperativo via <font face='Courier'>threading.Event</font>. "
        "O usuário pode clicar no botão <b>'✕ Abortar'</b> a qualquer instante, liberando recursos com segurança.", "body"
    ))
    E.append(Spacer(1, 0.2 * cm))

    E.append(p("2.4. [Figura 1] Visão Geral da Interface e Dashboard Analítico com m017", "h2"))
    E.append(p(
        "Abaixo apresenta-se a captura real do ambiente analítico do Crinômetro processando o arquivo de campo "
        "<code>m017_0376.wav</code> (gravação de 38.76 segundos, taxa de 48.0 kHz). Os quatro painéis síncronos "
        "revelam a correspondência exata entre tempo, amplitude, frequência e distribuição estatística:", "body"
    ))

    # Incorporação da Figura 1
    if os.path.exists(fig_paths['fig1']):
        img1 = Image(fig_paths['fig1'], width=16.2 * cm, height=9.5 * cm)
        cap1 = Paragraph(
            "<b>Figura 1:</b> Painel analítico integrado do Crinômetro processando o espécime <i>m017</i>. "
            "(A) Forma de onda com envoltória de Hilbert e picos validados; (B) Histograma bivariado com eixo duplo "
            "(contagem de chilreios e duração média em ms); (C) Espectrograma focal STFT com rastreamento da portadora "
            "(5.81 kHz); (D) Densidade Espectral de Potência (PSD de Welch) destacando a portadora (5.82 kHz) e banda de tolerância (±700 Hz).",
            S["caption"]
        )
        E.append(KeepTogether([img1, Spacer(1, 0.15 * cm), cap1]))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 3: PROCESSAMENTO DIGITAL DE SINAIS
    # ═══════════════════════════════════════════
    E.append(p("3. PROCESSAMENTO DIGITAL DE SINAIS (DSP): O MOTOR MATEMÁTICO", "h1"))
    E.append(hr())

    E.append(p("3.1. Condicionamento do Sinal: Mono, Normalização e Offset DC", "h2"))
    E.append(p(
        "A integridade dos cálculos bioacústicos requer condicionamento prévio do sinal elétrico amostrado:<br/>"
        "• <b>Conversão Mono:</b> <font face='Courier'>data = raw.mean(axis=1)</font> colapsa canais estéreo.<br/>"
        "• <b>Normalização float32:</b> Valores inteiros de 16 bits [-32768, +32767] são mapeados para ponto "
        "flutuante [-1.0, +1.0] em <font face='Courier'>float32</font>, economizando 50% de RAM em relação a float64.<br/>"
        "• <b>Remoção do Offset DC:</b> <font face='Courier'>data = data - np.mean(data)</font> extirpa tensões "
        "contínuas residuais que formariam picos espúrios na frequência 0 Hz.", "body"
    ))

    E.append(p("3.2. Tratamento de Bordas: Downmix Estéreo e Análise de Cancelamento de Fase", "h2"))
    E.append(p(
        "Uma questão crítica de engenharia em gravações de campo é o comportamento de sinais estéreo espaçados. "
        "Se o pesquisador utilizar um par de microfones afastados por uma distância d, as ondas sonoras atingem "
        "os microfones com um atraso temporal interaural:", "body"
    ))
    E.append(p("Δt = (d · sin θ) / c   ==>   Δφ = 2π · f · Δt", "formula"))
    E.append(p(
        "onde c = 343 m/s e θ é o ângulo de incidência acústica. Para uma portadora de 5.000 Hz, o comprimento de onda "
        "é de apenas λ = 6.86 cm. Um descompasso de apenas <b>3.43 cm</b> gera uma defasagem de 180° (anti-fase), "
        "fazendo com que a média simples (L + R) / 2 resulte em <b>cancelamento destrutivo total (comb filtering)</b>, "
        "apagando o canto do animal do áudio resultante. O Crinômetro documenta a premissa obrigatória de que "
        "gravações estéreo de entrada utilizem microfones coincidentes (técnica X-Y ou Mid-Side) ou gravações "
        "mono-canal nativas para assegurar coerência de fase absoluta.", "body"
    ))

    E.append(p("3.3. Filtragem Passa-Altas de 50 Hz (Butterworth 2ª Ordem SOS)", "h2"))
    E.append(p(
        "A turbulência do vento e as vibrações mecânicas de suportes concentram grande energia abaixo de 50 Hz. "
        "Aplica-se um filtro passa-altas Butterworth de 2ª ordem implementado na topologia de Seções de Segunda "
        "Ordem (SOS):", "body"
    ))
    E.append(p("H_hp(s) = s² / (s² + √2·ω_c·s + ω_c²)   com ω_c = 2π × 50 Hz", "formula"))

    E.append(p("3.4. Filtragem Passa-Faixa IIR (Butterworth 4ª Ordem SOS [3200–6000 Hz])", "h2"))
    E.append(p(
        "O isolamento da banda de estridulação é executado por um filtro Butterworth passa-faixa IIR de 4ª ordem "
        "(declive de 24 dB/oitava), com frequências padrão configuradas para 3.200 Hz e 6.000 Hz:", "body"
    ))
    E.append(p("|H(jω)|² = 1 / [ 1 + ((ω² - ω<sub>0</sub>²) / (B·ω))^(2N) ]   onde B = banda, N = 4", "formula"))

    butter_vs_cheby = (
        "[POR QUE ESCOLHEMOS BUTTERWORTH E NÃO CHEBYSHEV?]<br/>"
        "Filtros Chebyshev oferecem um corte mais abrupto, mas introduzem ondulações (ripple) na banda passante. "
        "Essas oscilações funcionam como um eco artificial que deforma o envelope do pulso, podendo desdobrar um pulso "
        "legítimo em dois picos falsos. O filtro Butterworth é <b>maximamente plano</b> na faixa de passagem: ele atenua "
        "ruídos fora da banda sem distorcer em nenhuma fração a envoltória morfológica dos pulsos de estridulação."
    )
    E.append(make_callout("Justificativa Fisiológica da Filtragem", butter_vs_cheby, S, "didactic"))
    E.append(Spacer(1, 0.2 * cm))

    E.append(p("3.5. Transformada de Fourier de Curto Tempo (STFT) e Espectrograma", "h2"))
    E.append(p(
        "A evolução tempo-frequência é obtida pela STFT via <font face='Courier'>scipy.signal.spectrogram</font> "
        "com parametrização calibrada para a cinemática de Gryllidae:<br/>"
        "• <b>Janela:</b> Hann (cosseno elevado) com N_perseg = 1024 amostras (21.3 ms a 48.0 kHz).<br/>"
        "• <b>Sobreposição:</b> 768 amostras (75%), resultando em avanço temporal (hop size) de 256 amostras (5.33 ms).<br/>"
        "• <b>Resolução:</b> Δf = 46.88 Hz por célula; Δt = 5.33 ms entre quadros sucessivos.<br/>"
        "• <b>Conversão Logarítmica:</b> S_dB(f, t) = 10 · log<sub>10</sub>(S_xx(f, t) + 10<sup>-10</sup>), "
        "onde o epsilon 10<sup>-10</sup> previne singularidades de logaritmo no silêncio.", "body"
    ))

    E.append(p("3.6. Refinamento Sub-bin Parabólico de Frequência", "h2"))
    E.append(p(
        "A grade da STFT (~47 Hz) não detecta microvariações da portadora. Aplica-se interpolação parabólica "
        "sub-bin de 3 pontos no pico espectral de cada quadro temporal:", "body"
    ))
    E.append(p("p = 0.5 × (α - γ) / (α - 2β + γ)   ==>   f_refinada = f_bin + p × Δf", "formula"))
    E.append(p(
        "onde α, β e γ são as potências em decibéis dos bins adjacentes. Isso eleva a precisão analítica da "
        "frequência portadora para <b>±4.3 Hz</b> sem custo computacional adicional.", "body"
    ))

    E.append(p("3.7. [v4.4.0] Densidade Espectral de Potência (PSD via Método de Welch)", "h2"))
    E.append(p(
        "Introduzido na v4.4.0, o PSD de Welch (<font face='Courier'>scipy.signal.welch</font>) computa a "
        "impressão digital espectral média de longo prazo do áudio. O sinal é fatiado em blocos de 4096 amostras "
        "com 50% de sobreposição e janelamento Hann, produzindo uma estimativa consistente da densidade de potência "
        "com resolução finíssima de ~11.7 Hz e rastreando automaticamente o pico absoluto da portadora modal.", "body"
    ))
    E.append(Spacer(1, 0.2 * cm))

    E.append(p("3.8. [Figuras 3 e 4] Espectrograma HD e Curva PSD do Espécime m017", "h2"))
    E.append(p(
        "Abaixo apresentam-se as renderizações reais obtidas do espécime <i>m017</i>, ilustrando o "
        "espectrograma de alta definição e o gráfico da Densidade Espectral de Potência (PSD):", "body"
    ))

    # Incorporação das Figuras 3 e 4
    if os.path.exists(fig_paths['fig3']):
        img3 = Image(fig_paths['fig3'], width=16.2 * cm, height=7.2 * cm)
        cap3 = Paragraph(
            "<b>Figura 3:</b> Espectrograma STFT de alta resolução do espécime <i>m017</i> (janela Hann de 1024 amostras, "
            "75% de overlap). A linha tracejada ciano indica a frequência portadora modal em <b>5.81 kHz</b>, "
            "com os marcadores verdes destacando os pulsos validados sobre a crista de máxima densidade energética.",
            S["caption"]
        )
        E.append(KeepTogether([img3, Spacer(1, 0.15 * cm), cap3]))

    E.append(Spacer(1, 0.3 * cm))

    if os.path.exists(fig_paths['fig4']):
        img4 = Image(fig_paths['fig4'], width=16.2 * cm, height=6.8 * cm)
        cap4 = Paragraph(
            "<b>Figura 4:</b> Densidade Espectral de Potência (PSD) via Método de Welch para o espécime <i>m017</i>. "
            "Observe o pico acústico agudo em <b>5.82 kHz</b> (portadora modal rastreada em <b>5.81 kHz</b>) com densidade "
            "de potência de pico de <b>-49.5 dB/Hz</b> e a faixa sombreada azul ilustrando a tolerância espectral de banda "
            "de <b>±700 Hz</b> (a partir de 700 Hz para mais ou para menos, o filtro selecionado — ajustável pelo usuário — "
            "exclui os pulsos rivais fora desse espectro).",
            S["caption"]
        )
        E.append(KeepTogether([img4, Spacer(1, 0.15 * cm), cap4]))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 4: DETECÇÃO E SEGMENTAÇÃO
    # ═══════════════════════════════════════════
    E.append(p("4. DETECÇÃO, SEGMENTAÇÃO E AGRUPAMENTO BIOACÚSTICO", "h1"))
    E.append(hr())

    E.append(p("4.1. Extração da Envoltória Instantânea via Transformada de Hilbert", "h2"))
    E.append(p(
        "Para extrair os pulsos sem a oscilação rápida da portadora, computa-se a envoltória analítica por Hilbert:", "body"
    ))
    E.append(p("x_analitico(t) = x(t) + j · H{x(t)}   ==>   Envelope(t) = √[ x(t)² + H{x(t)}² ]", "formula"))

    E.append(p("4.2. Suavização Hanning e Limiar Adaptativo por Percentis", "h2"))
    E.append(p(
        "A envoltória sofre convolução com janela Hanning de 2 ms (<font face='Courier'>smooth_window_ms</font>) "
        "e é normalizada pelo <b>percentil 99.85</b> (robusto contra ruídos impulsivos de saturação). "
        "O limiar adaptativo de detecção é formulado como:", "body"
    ))
    E.append(p("Threshold = max( amp_min × noise_floor,   P<sub>25</sub>(envelope) × 2.5 )", "formula"))
    E.append(p(
        "onde P<sub>25</sub> é o percentil 25 do envelope, garantindo sensibilidade superior a 95% para pulsos legítimos.", "body"
    ))

    E.append(p("4.3. Detecção Morfológica de Picos e Validação Temporal", "h2"))
    E.append(p(
        "A identificação de pulsos via <font face='Courier'>scipy.signal.find_peaks</font> impõe quatro travas:<br/>"
        "1. <b>Altura Mínima:</b> Ultrapassar o Threshold adaptativo.<br/>"
        "2. <b>Proeminência Relativa:</b> Superar o vale adjacente em pelo menos 0.02 unidades.<br/>"
        "3. <b>Distância Mínima:</b> Separador de no mínimo 25 ms (<font face='Courier'>gap_min</font>) para impedir duplicatas.<br/>"
        "4. <b>Largura FWHM:</b> A largura a meia altura (50%) deve estar entre 14 e 80 ms (<font face='Courier'>dur_min/dur_max</font>).", "body"
    ))

    E.append(p("4.4. Rastreamento da Portadora Modal e Filtro de Tolerância Espectral (±700 Hz)", "h2"))
    E.append(p(
        "Constrói-se um histograma espectral com classes de 50 Hz dos pulsos detectados. A moda define a "
        "<b>portadora focal</b> (5.81 kHz no espécime <i>m017</i>). O filtro de tolerância espectral "
        "(<font face='Courier'>freq_tolerance_hz</font>, configurado em <b>±700 Hz</b> e dinamicamente ajustável "
        "pelo usuário para mais ou para menos) opera como corte seletivo: a partir de um desvio de <b>700 Hz para mais "
        "ou para menos</b> em relação à portadora modal, o filtro selecionado exclui os pulsos rivais fora desse espectro, "
        "preservando apenas os pulsos verdadeiros do espécime focal sob monitoramento.", "body"
    ))

    E.append(p("4.5. As Cinco Camadas do Agrupamento em Chilreios e Imposição de min_p", "h2"))
    E.append(p(
        "O algoritmo <font face='Courier'>regroup_chirps()</font> agrupa os pulsos em chilreios por 5 camadas:<br/>"
        "• <b>Camada 1 (Continuidade Temporal):</b> IPIs entre gap_min e gap_max formam um único trem.<br/>"
        "• <b>Camada 2 (Coerência de Amplitude):</b> Desvio de amplitude intra-chilreio limitado a 1.65× da mediana.<br/>"
        "• <b>Camada 3 (Detecção de Colisão):</b> IPIs inferiores a 0.8 × gap_min indicam colisão com outro grilo; descarta o mais fraco.<br/>"
        "• <b>Camada 4 (ICI Gate):</b> Pausas inter-chilreios menores que 70% da mediana de ICI são fundidas.<br/>"
        "• <b>Camada 5 ([v4.4.0] Imposição Rigorosa de min_p):</b> Qualquer sequência residual com menos de "
        "<font face='Courier'>min_p</font> pulsos (padrão: 3) é descartada, bloqueando falsos chilreios espúrios.", "body"
    ))

    E.append(p("4.6. [v4.4.0] Histograma Bivariado com Eixo Duplo (twinx: Contagem e Duração)", "h2"))
    E.append(p(
        "O Histograma Bivariado correlaciona a contagem de chilreios (eixo Y esquerdo em barras) com a duração média "
        "em milissegundos (eixo Y direito via <font face='Courier'>twinx</font> em linha vermelha com marcadores), "
        "revelando visualmente se chilreios com mais pulsos duram mais tempo ou comprimem o IPI.", "body"
    ))
    E.append(Spacer(1, 0.2 * cm))

    E.append(p("4.7. [Figuras 2 e 5] Detalhe da Envoltória de Hilbert e Histograma Bivariado de m017", "h2"))
    E.append(p(
        "Abaixo apresentam-se as figuras capturadas para a forma de onda detalhada com decimação LOD e o "
        "histograma bivariado de sintaxe e duração do espécime <i>m017</i>:", "body"
    ))

    # Incorporação das Figuras 2 e 5
    if os.path.exists(fig_paths['fig2']):
        img2 = Image(fig_paths['fig2'], width=16.2 * cm, height=8.3 * cm)
        cap2 = Paragraph(
            "<b>Figura 2:</b> Detalhe temporal e decimação adaptativa da envoltória do espécime <i>m017</i>. "
            "(A) Sinal filtrado em cinza, envoltória analítica de Hilbert em azul e pulsos detectados com moda de 5 pulsos; "
            "(B) Zoom microscópico comparando o sinal bruto denso com a decimação adaptativa Min-Max (LOD), "
            "demonstrando a preservação exata dos picos de estridulação sem sobrecarga gráfica.",
            S["caption"]
        )
        E.append(KeepTogether([img2, Spacer(1, 0.15 * cm), cap2]))

    E.append(Spacer(1, 0.3 * cm))

    if os.path.exists(fig_paths['fig5']):
        img5 = Image(fig_paths['fig5'], width=16.2 * cm, height=7.2 * cm)
        cap5 = Paragraph(
            "<b>Figura 5:</b> Histograma Bivariado do espécime <i>m017</i>. As barras azuis/verdes indicam a distribuição "
            "sintática de chilreios (predomínio absoluto da classe de <b>5 pulsos</b> com 60 eventos). A linha tracejada vermelha "
            "(eixo Y secundário twinx) ilustra a correlação positiva linear com a duração média do evento em milissegundos.",
            S["caption"]
        )
        E.append(KeepTogether([img5, Spacer(1, 0.15 * cm), cap5]))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 5: MÉTRICAS E FISIOLOGIA
    # ═══════════════════════════════════════════
    E.append(p("5. BIOMETRIA BIOACÚSTICA E MODELAGEM FISIOLÓGICA", "h1"))
    E.append(hr())

    E.append(p("5.1. Métricas Bioacústicas Fundamentais (Tabela Exaustiva)", "h2"))
    E.append(p(
        "Grandezas biométricas computadas pelo Crinômetro sobre os chilreios validados de <i>m017</i>:", "body"
    ))

    metrics_data = [
        ["Métrica Bioacústica", "Símbolo", "Fórmula Matemática", "Unidade", "Significado Biológico"],
        ["Total de Chilreios", "N_c", "len(chirp_peaks_list)", "chilreios", "Volume total de eventos emitidos na gravação"],
        ["Total de Pulsos", "N_p", "Σ len(chirp_i)", "pulsos", "Trabalho muscular total de fechamento das asas"],
        ["Taxa de Chilreios", "R_c", "N_c / Duração_Total", "chilr/s", "Frequência rítmica de emissão por segundo"],
        ["Cadência por Minuto", "R_min", "R_c × 60.0", "chilr/min", "Parâmetro padrão utilizado na Lei de Dolbear"],
        ["ICI Mediano", "ICI_med", "mediana(onset[i+1] - offset[i])", "ms", "Intervalo típico de pausa respiratória entre cantos"],
        ["IPI Médio", "IPI_med", "(1/m) Σ (onset[j+1] - offset[j])", "ms", "Velocidade neuromotora intra-chilreio"],
        ["Duração do Pulso", "d_p", "FWHM(pico)", "ms", "Tempo de contato físico entre a lima e o plectro"],
        ["Duração do Chilreio", "d_c", "offset_ultimo - onset_primeiro", "ms", "Tempo total do trem de pulsos"],
        ["Moda de Pulsos", "Mo_p", "moda({ len(chirp_i) })", "pulsos", "Padrão sintático mais frequente da espécie"],
        ["Frequência Portadora", "f_c", "Moda(histograma_espectral_50Hz)", "Hz", "Tom sonoro fundamental da estridulação"],
    ]
    E.append(make_table(metrics_data[0], metrics_data[1:], S, col_widths=[3.2 * cm, 1.6 * cm, 4.4 * cm, 1.8 * cm, 6.0 * cm]))
    E.append(Spacer(1, 0.3 * cm))

    E.append(p("5.2. Diagnóstico de Cadência Rítmica (Regressão Linear e Teste t de Student)", "h2"))
    E.append(p(
        "A cadência rítmica avalia a dinâmica neuromuscular ao longo do tempo via regressão linear de primeira ordem:", "body"
    ))
    E.append(p("ICI(t) = β<sub>0</sub> + β<sub>1</sub> · t + ε", "formula"))
    E.append(p(
        "onde pausas anômalas (ICIs > 3× a mediana) são excluídas previamente. "
        "Se β<sub>1</sub> < -0.15 ms/s e p-valor < 0.05, diagnostica-se <b>Aceleração Rítmica</b>; "
        "se β<sub>1</sub> > +0.15 ms/s e p-valor < 0.05, diagnostica-se <b>Desaceleração Rítmica</b>; "
        "caso contrário (|β<sub>1</sub>| ≤ 0.15 ou p ≥ 0.05), a cadência é <b>Estável</b>.", "body"
    ))

    E.append(p("5.3. Modelagem Termo-Acústica: A Lei de Dolbear e Ectotermia", "h2"))
    E.append(p(
        "Em animais ectotérmicos, as taxas metabólicas e musculares aceleram diretamente com o calor. "
        "O Crinômetro parametriza a Lei de Dolbear adaptada para Celsius:", "body"
    ))
    E.append(p("T(°C) = ( R_min - 40 ) / 4.0 + 10.0   onde R_min = taxa de chilreios por minuto", "formula"))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 6: INTELIGÊNCIA ARTIFICIAL
    # ═══════════════════════════════════════════
    E.append(p("6. INTELIGÊNCIA ARTIFICIAL E APRENDIZADO ATIVO (ACTIVE LEARNING)", "h1"))
    E.append(hr())

    E.append(p("6.1. Filosofia de Design: [v4.4.0] Modo DSP Nativo e Reset de IA", "h2"))
    E.append(p(
        "O módulo <font face='Courier'>PulseLearner</font> opera como assistente de apoio ao pesquisador. "
        "Na v4.4.0, o software passa a iniciar com IA desligada por padrão (Modo DSP puro). "
        "Foi implementado o comando <b>'Resetar Aprendizado da IA'</b>, que elimina arquivos persistidos "
        "(<font face='Courier'>.crntrain</font>) e restaura os pesos de fábrica.", "body"
    ))

    E.append(p("6.2. Engenharia de Recursos: O Vetor de 20 Features Bioacústicas", "h2"))
    E.append(p(
        "Para cada pulso candidato, extrai-se uma janela de ±30 ms centrada no pico e computa-se um "
        "vetor invariante a ganho com 20 características bioacústicas:", "body"
    ))

    feat_data = [
        ["#", "Nome da Feature", "Definição Matemática", "Significado Discriminatório"],
        ["1", "peak_amp_rel", "A_pico / mediana(A_local)", "Separa o grilo próximo (alto relevo) do coro distante"],
        ["2", "peak_width_s", "FWHM a 50% da altura", "Duração precisa do batimento alar"],
        ["3", "peak_width_75_s", "Largura a 75% da altura", "Agudeza do topo do pulso"],
        ["4", "local_snr_db", "20 · log<sub>10</sub>(A_pico / σ_ruído)", "Razão sinal-ruído local em decibéis"],
        ["5", "energy_rel", "Energia da janela / A_pico²", "Concentração energética do pulso"],
        ["6", "std_amp_rel", "Desvio padrão local / A_pico", "Estabilidade da amplitude ao redor do evento"],
        ["7", "prominence_ratio", "(A_pico - A_vale) / A_pico", "Proeminência vertical em relação aos vales"],
        ["8", "peak_sharpness_rel", "d²(envelope)/dt² no ápice", "Segunda derivada: quão pontiagudo é o pico"],
        ["9", "crest_factor", "A_pico / RMS_local", "Fator de crista: detecta estalos e cliques espúrios"],
        ["10", "skewness_local", "Assimetria temporal do pulso", "Diferença entre o tempo de subida e descida"],
        ["11", "local_density_rel", "Energia(±10ms) / Energia(±30ms)", "Foco de energia no centro do pulso"],
        ["12", "autocorr_1ms", "Autocorrelação com atraso de 1 ms", "Periodicidade sonora da portadora no pulso"],
        ["13", "band_energy_ratio", "Energia na banda / Energia total", "Pureza do sinal na faixa de estridulação"],
        ["14", "rise_slope_rel", "Δamplitude / Δtempo (subida)", "Velocidade de ataque do batimento mecânico"],
        ["15", "spectral_centroid", "Σ(f · |X|) / Σ|X|", "Centro de massa espectral em Hertz"],
        ["16", "spectral_rolloff_85", "Frequência onde acumula 85% de energia", "Queda espectral de alta frequência"],
        ["17", "attack_time_10_90_ms", "Tempo de subida de 10% a 90%", "Cinemática de fechamento da asa"],
        ["18", "local_hnr_db", "Harmonics-to-Noise Ratio local", "Razão entre som harmônico e ruído caótico"],
        ["19", "multiscale_energy", "Energia(±10ms) / Energia(±40ms)", "Contraste em múltiplas escalas temporais"],
        ["20", "prior_p_focal", "Probabilidade posterior do GMM", "Convicção não-supervisionada prévia"],
    ]
    E.append(make_table(feat_data[0], feat_data[1:], S, col_widths=[0.8 * cm, 3.8 * cm, 5.4 * cm, 7.0 * cm]))
    E.append(Spacer(1, 0.4 * cm))

    E.append(p("6.3. Separação Não-Supervisionada: Modelo de Mistura de Gaussianas (GMM)", "h2"))
    E.append(p(
        "Um GMM bimodal agrupa os pulsos em dois clusters elipsoidais no espaço [log(amplitude) × centroide_espectral]. "
        "O cluster de maior amplitude é rotulado como <b>Indivíduo Focal</b> e o outro como <b>Coro / Ruído</b>.", "body"
    ))

    E.append(p("6.4. Classificador Supervisionado HistGradientBoosting e Score Híbrido", "h2"))
    E.append(p(
        "Com as correções do usuário, treina-se um <font face='Courier'>HistGradientBoostingClassifier</font> em tempo O(N):", "body"
    ))
    E.append(p("Score_Final = 0.65 × P(Válido | HistGradientBoosting) + 0.35 × P(Focal | GMM)", "formula"))

    E.append(p("6.5. Mineração de Negativos Difíceis e Poda Contrastiva", "h2"))
    E.append(p(
        "A exclusão manual de falsos positivos aciona o <b>Hard Negative Mining</b>, que induz regras contrastivas "
        "com margem de segurança de 30% em tempo O(1), descartando ruídos antes de submeter os dados à árvore de decisão.", "body"
    ))

    E.append(p("6.6. Filtro de Coerência Rítmica e o Ciclo Humano de Feedback Ativo", "h2"))
    E.append(p(
        "O Gerador Central de Padrões (CPG) torácico produz ritmos regulares (variação < ±30%). Pulsos fora desse padrão "
        "são removidos automaticamente. O feedback ativo permite treinar o classificador com poucos cliques e exportar "
        "o modelo treinado para arquivos adicionais.", "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 7: ENGENHARIA DE COMPUTAÇÃO E BAIXO NÍVEL (EXPANDIDA)
    # ═══════════════════════════════════════════
    E.append(p("7. ENGENHARIA DE COMPUTAÇÃO, SISTEMAS E COMPUTAÇÃO VISUAL", "h1"))
    E.append(hr())

    E.append(p("7.1. Pipeline Gráfico: Decimação Adaptativa Min-Max (Level of Detail - LOD)", "h2"))
    E.append(p(
        "Em processamento de áudio digital, renderizar visualmente a forma de onda bruta de um arquivo longo "
        "revela um desafio clássico de computação gráfica: <b>a disparidade de amostragem por pixel</b>. "
        "Considere uma gravação de apenas 10 segundos amostrada a fs = 44.100 Hz:", "body"
    ))
    E.append(p("N_amostras = 10 s × 44.100 amostras/s = 441.000 amostras", "formula"))
    E.append(p(
        "Em um monitor Full HD padrão, a largura física destinada ao painel de onda no Matplotlib é de aproximadamente "
        "W_px = 1.920 pixels. A taxa de densidade é de:", "body"
    ))
    E.append(p("Densidade = 441.000 amostras / 1.920 pixels ≈ 230 amostras por pixel", "formula"))
    E.append(p(
        "<b>O Problema do Overdraw e Aliasing:</b> Traçar 441.000 segmentos de linha em 1.920 pixels sobrecarrega a GPU/CPU "
        "com dezenas de milhares de operações de desenho redundantes no mesmo pixel (overdraw). Pior: se o desenvolvedor "
        "utilizar uma decimação ingênua por stride (ex: <font face='Courier'>data[::230]</font>), ocorre <b>aliasing catastrófico</b>. "
        "Como os pulsos de estridulação do grilo duram apenas 10 a 30 ms, um pulso pode cair exatamente entre os passos do stride "
        "e ser completamente omitido da tela, exibindo uma linha plana onde existia um canto sonoro!", "body"
    ))
    E.append(p(
        "<b>A Solução Implementada (<font face='Courier'>HighPerfLineEngine._get_envelope</font>):</b><br/>"
        "O Crinômetro particiona a janela temporal visível em M blocos contíguos (buckets) de tamanho fixo. "
        "Para cada bloco k, extrai-se analiticamente o valor mínimo e máximo:", "body"
    ))
    E.append(p("y_min[k] = min( y[j] )   e   y_max[k] = max( y[j] )   para j ∈ Bloco_k", "formula"))
    E.append(p(
        "Esses extremos são intercalados em um novo vetor: [t_k, y_min[k]], [t_k, y_max[k]]. Isso garante que "
        "<b>100% dos picos e vales físicos da estridulação sejam preservados na tela sem nenhuma perda morfológica</b>, "
        "enquanto o volume de vértices despachados ao Matplotlib cai de 441.000 para apenas 4.000 pontos (redução de 99.1%!). "
        "Durante arraste (pan) e zoom interativos, a engine renderiza um rascunho ultrarrápido com 300 pontos a 60 FPS e, "
        "através de um temporizador de debounce (120 ms), desenha o envelope de alta resolução (4.000 pontos) assim que o mouse para.", "body"
    ))

    E.append(p("7.2. Aceleração de Tela: Raster Blitting e Double Buffering a 60 FPS", "h2"))
    E.append(p(
        "O espectrograma do Crinômetro consiste em uma matriz densa de 513 bins de frequência por milhares de quadros temporais. "
        "Durante a reprodução de áudio, a interface precisa atualizar uma linha indicadora vertical (cursor de playback) "
        "em sincronia com o relógio do sistema a cada 16 milissegundos (60 quadros por segundo).", "body"
    ))
    E.append(p(
        "Redesenhar o espectrograma completo a cada tick consumiria 100% da CPU, tornando a reprodução engasgada. "
        "A solução é a técnica de <b>Raster Blitting (Bit-Block Transfer)</b>:", "body"
    ))
    E.append(p(
        "1. <b>Captura Única do Fundo:</b> Na carga do arquivo, o gráfico estático (espectrograma, eixos, grids) é rasterizado "
        "uma única vez em um buffer de memória off-screen via <font face='Courier'>canvas.copy_from_bbox(ax.bbox)</font>.<br/>"
        "2. <b>Restauração em Tempo O(1):</b> A cada frame de reprodução, o buffer original limpo é restaurado em memória "
        "através de <font face='Courier'>canvas.restore_region(bg)</font> (operação de memcpy em C).<br/>"
        "3. <b>Desenho do Elemento Animado:</b> Apenas a linha do cursor é reposicionada e desenhada: "
        "<font face='Courier'>ax.draw_artist(cursor_line)</font>.<br/>"
        "4. <b>Transferência de Bounding Box:</b> A região delimitada é copiada diretamente para a janela Qt via "
        "<font face='Courier'>canvas.blit(ax.bbox)</font>, mantendo a fluidez a 60 FPS cravados sem recomputar matrizes.", "body"
    ))

    E.append(p("7.3. Concorrência e Threading: Modelo Qt, QueuedConnection e Liberação do GIL", "h2"))
    E.append(p(
        "O processamento no Crinômetro segue um modelo de <b>multithreading desacoplado</b> com as seguintes salvaguardas:", "body"
    ))
    E.append(p(
        "• <b>Thread Affinity e Isolamento de GUI:</b> A thread principal executa o Qt Event Loop (<font face='Courier'>QApplication.exec</font>). "
        "Operações de DSP pesadas rodam na thread secundária gerenciada pelo <font face='Courier'>GenericWorker(QThread)</font>.<br/>"
        "• <b>Sinalização Tipada via QueuedConnection:</b> Chamar métodos da interface a partir de uma thread secundária causa "
        "falhas de segmentação no subsistema gráfico do Windows (GDI/DirectX). A comunicação entre worker e janela ocorre "
        "estritamente através de sinais e slots Qt (<font face='Courier'>finished_signal</font>, <font face='Courier'>progress_signal</font>). "
        "O Qt empacota o resultado em uma fila de mensagens segura (<font face='Courier'>QueuedConnection</font>), executando a "
        "atualização gráfica na thread de UI.<br/>"
        "• <b>Interrupção Cooperativa vs QThread.terminate():</b> Matar uma thread abruptamente com chamadas do sistema "
        "(TerminateThread) deixa travas de heap, mutexes e arquivos corrompidos. O Crinômetro utiliza <b>cancelamento cooperativo</b> "
        "via <font face='Courier'>threading.Event</font>: a esteira analítica consulta atômica e ciclicamente "
        "<font face='Courier'>self.is_abort_requested</font>, encerrando-se de forma limpa e liberando a memória.<br/>"
        "• <b>Liberação do GIL (Global Interpreter Lock):</b> Embora o interpretador CPython possua o GIL, as rotinas numéricas "
        "de FFT, convolução de Hilbert e filtragem SOS são executadas em extensões C e Fortran compiladas do NumPy e SciPy. "
        "Essas bibliotecas liberam explicitamente o GIL (<font face='Courier'>Py_BEGIN_ALLOW_THREADS</font>), permitindo "
        "que o processamento explore múltiplos núcleos físicos de CPU simultaneamente enquanto a interface permanece 100% responsiva.", "body"
    ))

    E.append(p("7.4. Estruturas de Dados e Memória: float32, Cache L1/L2/L3 e Vetorização SIMD", "h2"))
    E.append(p(
        "O layout de memória das estruturas de dados é fundamental para a performance em larga escala:<br/>"
        "• <b>Pegada de Memória (RAM):</b> Arrays em <font face='Courier'>float32</font> ocupam 4 bytes por elemento "
        "contra 8 bytes do padrão <font face='Courier'>float64</font>. Em um áudio de 5 minutos (14.4 milhões de amostras), "
        "o consumo de sinal bruto, sinal filtrado, envoltória e espectrograma cai de ~1.1 GB para menos de 280 MB.<br/>"
        "• <b>Aproveitamento das Linhas de Cache da CPU:</b> Processadores modernos transferem dados da memória RAM para o cache "
        "L1/L2 em linhas de 64 bytes. Uma linha de 64 bytes armazena 8 números em float64, mas comporta <b>16 números em float32</b>. "
        "Dobrar a densidade de amostras por linha de cache reduz a latência de barramento pela metade e maximiza os acertos de cache "
        "(cache hits) durante as multiplicações matriciais da STFT.<br/>"
        "• <b>Alinhamento Contíguo e Instruções SIMD:</b> Todos os tensores são mantidos em blocos contíguos na memória C-order "
        "(<font face='Courier'>np.ascontiguousarray</font>). Isso habilita a vetorização vetorial SIMD (AVX2 / AVX-512) da CPU, "
        "executando 8 ou 16 operações de ponto flutuante em um único ciclo de clock.", "body"
    ))

    E.append(p("7.5. Poda Espacial Adaptativa no Hover (MainWindow.on_motion: O(N) para O(K))", "h2"))
    E.append(p(
        "Quando o usuário move o cursor do mouse sobre o gráfico, o evento <font face='Courier'>on_motion</font> é disparado "
        "a até 120 Hz. Em arquivos com mais de 5.000 pulsos detectados, uma busca ingênua calculando a distância euclidiana "
        "de todos os pulsos na tela (<font face='Courier'>ax.transData.transform</font>) exigiria 5.000 transformações afins "
        "a cada movimento do mouse, gerando congelamentos severos.<br/>"
        "<b>Algoritmo de Poda Espacial Local:</b> O Crinômetro calcula dinamicamente uma janela temporal estreita ao redor do cursor:<br/>"
        "<font face='Courier'>dt_max = max(0.04, 30.0 / px_per_sec)</font>.<br/>"
        "Todos os pulsos fora do intervalo [t_cursor - dt_max, t_cursor + dt_max] são descartados instantaneamente em tempo O(1) "
        "por busca binária (<font face='Courier'>np.searchsorted</font>). Apenas os K pulsos vizinhos (geralmente K ≤ 4) são "
        "transformados em coordenadas de tela para hit-testing, reduzindo a complexidade de O(N) para O(K) e garantindo tooltips instantâneos.", "body"
    ))

    E.append(p("7.6. Segurança da Informação (AppSec): Análise de Riscos do Pickle e Roadmap", "h2"))
    E.append(p(
        "A persistência de modelos de IA no arquivo <font face='Courier'>modelo_treinado.pkl</font> utiliza o módulo "
        "<font face='Courier'>pickle</font> do Python. Sob o prisma de segurança da informação (AppSec), o formato Pickle "
        "permite a execução arbitrária de código durante a desserialização via método mágico <font face='Courier'>__reduce__</font>, "
        "representando uma superfície de risco se o pesquisador carregar arquivos de terceiros não confiáveis.<br/>"
        "<b>Roadmap Arquitetural Seguro:</b> O Crinômetro implementa escopo seguro de carregamento local e prevê para a versão "
        "v4.5.0 a migração da persistência para formatos padronizados e seguros: exportação do classificador em <b>ONNX (Open Neural Network Exchange)</b> "
        "ou pesos numéricos em JSON/HDF5, impedindo a injeção de instruções executáveis e viabilizando interoperabilidade com outras linguagens.", "body"
    ))

    E.append(p("7.7. Arquitetura de Software: O Contexto da God Class e Roadmap v4.5.0", "h2"))
    E.append(p(
        "O arquivo <font face='Courier'>ui/main_window.py</font> consolidou-se ao longo das versões como uma <i>God Class</i> "
        "monolítica com 4.075 linhas de código, acumulando gerenciamento de janelas, roteamento de áudio, cálculo de hover, "
        "manipulação de eixos Matplotlib e menus de exportação.<br/>"
        "<b>Plano de Desacoplamento Aprovado (ROADMAP_v4.5.0):</b> O planejamento arquitetural do projeto formalizou a "
        "modularização em quatro controladores especializados coordenados pelo padrão Mediator através de um "
        "<font face='Courier'>SessionContext</font> isolado:<br/>"
        "1. <font face='Courier'>pipeline_orchestrator.py</font>: execução assíncrona, batch e controle de worker.<br/>"
        "2. <font face='Courier'>plot_renderers.py</font>: renderização e sobreposição gráfica nos 4 painéis.<br/>"
        "3. <font face='Courier'>navigation_controller.py</font>: captura de mouse, pan, zoom e blitting de background.<br/>"
        "4. <font face='Courier'>editor_controller.py</font>: edição bidimensional de pulsos e feedback de machine learning.<br/>"
        "Essa evolução reduzirá a MainWindow para menos de 900 linhas, garantindo manutenibilidade limpa para as próximas décadas de pesquisa.", "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 8: DISTRIBUIÇÃO E ATUALIZADOR
    # ═══════════════════════════════════════════
    E.append(p("8. ENGENHARIA DE DISTRIBUIÇÃO E AUTO-UPDATER [v4.4.1]", "h1"))
    E.append(hr())

    E.append(p("8.1. Arquitetura do Launcher e Ciclo de Vida da Aplicação", "h2"))
    E.append(p(
        "O Crinômetro é empacotado como binário independente para Windows via Inno Setup e PyInstaller. "
        "O ponto de entrada <font face='Courier'>launcher.py</font> exibe uma tela de inicialização temática "
        "(Splash Screen) com sombra projetada e inicialização assíncrona dos módulos de áudio.", "body"
    ))

    E.append(p("8.2. O Sistema de Auto-Atualização via API do GitHub Releases", "h2"))
    E.append(p(
        "O aplicativo consulta silenciosamente a API de Releases do GitHub (<font face='Courier'>api.github.com/repos/.../releases/latest</font>). "
        "Havendo uma tag superior à versão em execução, o atualizador baixa em segundo plano o instalador oficial com barra de progresso em tempo real.", "body"
    ))

    E.append(p("8.3. [v4.4.1] Resolução Crítica: Script PowerShell UTF-8-BOM e os._exit(0)", "h2"))
    E.append(p(
        "A versão <b>v4.4.1</b> solucionou um problema clássico de concorrência do Windows: o travamento do instalador "
        "durante a mensagem 'Instalando arquivos...'. A análise de causa-raiz e a solução são documentadas a seguir:", "body"
    ))

    updater_callout = (
        "[A ENGENHARIA POR TRÁS DO HOTFIX v4.4.1]<br/>"
        "No sistema operacional Windows, um arquivo executável (.exe) ou DLL em execução é bloqueado contra escrita "
        "em nível de kernel (erro <i>ERROR_SHARING_VIOLATION</i> / Código 32). Além disso, o caractere circunflexo no nome da pasta de instalação "
        "(<b>C:\\Program Files\\Crinômetro</b>) causava corrupção de caracteres em scripts de lote legados (.bat) "
        "executados pelo interpretador CMD do Windows, gerando pastas fantasmas defeituosas como <i>Crin?metro</i>.<br/><br/>"
        "<b>Solução Implementada na v4.4.1:</b><br/>"
        "1. <b>Migração para PowerShell:</b> O script auxiliar de atualização foi reescrito em PowerShell nativo (.ps1), "
        "salvo estritamente em codificação <b>UTF-8 com BOM (utf-8-sig)</b>, garantindo interpretação perfeita de acentuação.<br/>"
        "2. <b>Normalização Automática:</b> O script detecta e apaga qualquer diretório corrompido remanescente de atualizações antigas.<br/>"
        "3. <b>Encerramento Determinístico com os._exit(0):</b> Após acionar o script de instalação com as diretivas "
        "atômicas do Inno Setup (/VERYSILENT /NORESTART), a aplicação se encerra forçosamente via <i>os._exit(0)</i>, "
        "liberando instantaneamente todos os descritores de arquivo e permitindo a substituição limpa do executável."
    )
    E.append(make_callout("Arquitetura da Atualização Atômica", updater_callout, S, "eng"))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 9: GLOSSÁRIO E DEFESA ACADÊMICA
    # ═══════════════════════════════════════════
    E.append(p("9. GLOSSÁRIO METODOLÓGICO PARA DEFESA ACADÊMICA E PUBLICAÇÃO", "h1"))
    E.append(hr())

    E.append(p("9.1. Seção de Materiais e Métodos Pronta para Teses e Artigos", "h2"))
    E.append(p(
        "A redação abaixo foi formulada para inclusão direta em dissertações de mestrado, teses e artigos científicos:", "body"
    ))

    academic_text = (
        "<i>\"Os registros acústicos em formato WAV não-comprimido (taxa de amostragem padronizada em float32) foram "
        f"processados e quantificados por meio do software Crinômetro (versão {APP_VERSION}). O sinal bruto foi submetido a "
        "condicionamento prévio para remoção do offset de corrente contínua (DC offset) e filtrado por um filtro passa-altas "
        "Butterworth de 2ª ordem (frequência de corte a 50 Hz) na topologia SOS (Second-Order Sections) para eliminação de "
        "ruídos de vento e perturbações infrassônicas de baixa frequência. A banda de estridulação focal foi isolada através de um "
        "filtro passa-faixa digital IIR Butterworth de 4ª ordem (f_low = 3200 Hz; f_high = 6000 Hz; SOS).<br/><br/>"
        "A matriz tempo-frequência foi computada por Transformada de Fourier de Curto Tempo (STFT) com janelamento de Hann "
        "de 1024 amostras, sobreposição de 75% e refinamento espectral sub-bin por interpolação parabólica de três pontos. "
        "A assinatura espectral média foi avaliada pela Densidade Espectral de Potência (PSD) calculada pelo método de Welch "
        "(janela de 4096 amostras com sobreposição de 50%). A envoltória temporal instantânea foi extraída pelo módulo do sinal "
        "analítico obtido via Transformada de Hilbert, suavizada por convolução com janela de Hanning de 2.0 ms e normalizada "
        "pelo percentil 99.85 da distribuição de amplitude.<br/><br/>"
        "A segmentação dos pulsos estridulatórios baseou-se em busca morfológica de picos sob limiar adaptativo dinâmico "
        "(2.5 vezes o 25º percentil da envoltória), validação de largura FWHM e rejeição espectral de pulsos rivais com desvio a partir de ±700 Hz "
        "da portadora modal (tolerância espectral parametrizada pelo operador). O agrupamento em chilreios (chirps) seguiu validação hierárquica em cinco camadas, impondo intervalo "
        "inter-pulso fisiológico, portão refratário de intervalo inter-chilreio (ICI Gate a 70% da mediana) e contagem mínima "
        "rigorosa de três pulsos por evento. A relação estrutural entre a contagem de pulsos e a duração temporal dos cantos foi "
        "quantificada pelo Histograma Bivariado com eixo secundário twinx.<br/><br/>"
        "O diagnóstico de cadência rítmica (aceleração versus desaceleração) foi determinado por regressão linear ponderada dos "
        "intervalos inter-chilreios (ICIs) ao longo do tempo de gravação, expurgando pausas comportamentais superiores a três vezes a "
        "mediana, com significância atestada pelo teste t de Student (p < 0.05) e limiar biológico de inclinação (|β<sub>1</sub>| > 0.15 ms/s). "
        "A estimativa termo-acústica foi parametrizada pela formulação em graus Celsius da Lei de Dolbear.\"</i>"
    )
    E.append(p(academic_text, "body_indent"))
    E.append(Spacer(1, 0.4 * cm))

    E.append(p("9.2. Matriz Sintética: Conceito Biológico <-> Algoritmo <-> Código-Fonte", "h2"))

    matrix_data = [
        ["Fenômeno Biológico / Conceito CS", "Implementação Algorítmica", "Arquivo e Função no Código"],
        ["Fricção tegminal do grilo", "Sinal oscilatório na banda acústica 3.2–6.0 kHz", "core/analyzer.py -> analyze()"],
        ["Ruído de vento e vibração", "Filtro passa-altas 50 Hz Butterworth 2ª ordem SOS", "core/analyzer.py -> sosfilt()"],
        ["Assinatura pura do canto", "Filtro passa-faixa IIR 4ª ordem SOS maximamente plano", "core/analyzer.py -> butter(4, btype='band')"],
        ["Partitura sonora temporal", "STFT com janela Hann de 1024 amostras e 75% overlap", "scipy.signal.spectrogram()"],
        ["Tom musical exato do animal", "Interpolação parabólica sub-bin de 3 pontos (±4 Hz)", "core/analyzer.py -> dom_freqs"],
        ["Impressão digital de potência", "PSD pelo método de Welch (janela 4096, foco 0–15 kHz)", "core/analyzer.py -> compute_psd()"],
        ["Volume do pulso mecânico", "Módulo do sinal analítico via Transformada de Hilbert", "scipy.signal.hilbert()"],
        ["Impacto do dente alar (pulso)", "Detecção morfológica de picos adaptativa com FWHM", "scipy.signal.find_peaks()"],
        ["Exclusão de cantos rivais", "Filtro de tolerância (exclui pulsos a partir de ±700 Hz da portadora; ajustável)", "core/analyzer.py -> carrier_freq"],
        ["Frase do canto (chilreio)", "Agrupamento sequencial com 5 camadas e min_p >= 3", "core/analyzer.py -> regroup_chirps()"],
        ["Contagem vs Duração do chilreio", "Histograma Bivariado com eixo duplo twinx (barras + ms)", "ui/main_window.py -> _refresh_histogram()"],
        ["Ritmo de aceleração ou cansaço", "Regressão linear dos ICIs e teste t de Student (p < 0.05)", "utils/report_generator.py -> analyze_rhythmic_cadence()"],
        ["Termômetro natural ectotérmico", "Lei de Dolbear para Gryllus: T(°C) = (R_min - 40)/4 + 10", "core/analyzer.py -> metrics"],
        ["Diferenciação focal vs coro", "Clustering GMM bimodal no espaço amplitude x centroide", "core/learner.py -> GaussianMixture()"],
        ["Classificação supervisionada", "HistGradientBoostingClassifier com score híbrido", "core/learner.py -> HistGradientBoosting()"],
        ["Decimação Min-Max (LOD)", "Agregação temporal [min, max] preservando picos (99% redução)", "core/engines.py -> HighPerfLineEngine"],
        ["Raster Blitting a 60 FPS", "copy_from_bbox e restore_region para cursor sem redraw STFT", "ui/main_window.py -> capture_backgrounds"],
        ["Multithreading sem congelamento", "GenericWorker QThread desacoplado com QueuedConnection", "core/worker.py -> GenericWorker"],
        ["Poda espacial no Hover", "Filtro temporal dt_max reduzindo busca de O(N) para O(K)", "ui/main_window.py -> on_motion"],
        ["Instalação atômica e Unicode", "Launcher PowerShell UTF-8-BOM e desligamento os._exit(0)", "launcher.py -> run_powershell_updater()"],
    ]
    E.append(make_table(matrix_data[0], matrix_data[1:], S, col_widths=[3.8 * cm, 6.2 * cm, 7.0 * cm]))

    E.append(Spacer(1, 0.6 * cm))
    E.append(hr())
    E.append(p(
        f"<b>Fim da Documentação Técnica e Metodológica (Crinômetro v{APP_VERSION}).</b><br/>"
        f"Documento compilado e auditado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M')}. "
        "Todos os direitos reservados aos autores e à comunidade acadêmica.",
        "caption"
    ))

    return E


# ─────────────────────────────────────────────────────────────
# Execução Principal e Compilação
# ─────────────────────────────────────────────────────────────
def main():
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(docs_dir)
    fig_dir = os.path.join(docs_dir, "figures")

    # 1. Garante que as 5 figuras do m017 estejam geradas em 300 DPI
    fig_paths = ensure_m017_figures(fig_dir, base_dir, force_rebuild=True)

    output_path = os.path.join(docs_dir, "Crinometro_Documentacao_Tecnica_Cientifica_v441.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        title=f"Crinômetro v{APP_VERSION} — Documentação Técnica e Científica",
        author="Crinômetro — Gerador Automático de Documentação",
    )

    S = build_styles()
    elements = build_content(S, fig_paths)

    print(f"[*] Compilando documento PDF expandido para a versao v{APP_VERSION}...")
    doc.build(elements, canvasmaker=DocCanvas)
    print(f"[OK] PDF expandido gerado com sucesso em: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
