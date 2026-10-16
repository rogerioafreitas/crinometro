# -*- coding: utf-8 -*-
"""
Script de captura metrológica e automatizada dos prints reais da interface do Crinômetro v4.5.0.
Gera imagens reais em alta definição com anotações gráficas perfeitamente alinhadas (esquadro matemático)
e tipografia TrueType completa (sem caracteres tofu/quadrados) em docs/figures/ para o Manual do Usuário em PDF.
"""
import os
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontDatabase, QPixmap

from ui.main_window import MainWindow
from ui.dialogs import AlgoSettingsDialog, AdvancedAlgoSettingsDialog, AIParamsDialog
from ui.dialogs.export_graph_dialog import ExportGraphDialog
from ui.dialogs.export_report_dialog import ExportReportDialog
from core.analyzer import CricketAnalyzer
from utils.constants import DEFAULT_ALGO_PARAMS


def register_system_fonts():
    """Carrega fontes TrueType essenciais para o subsistema offscreen do Qt."""
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/segoeuii.ttf",
        "C:/Windows/Fonts/segoeuiz.ttf",
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/seguisym.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            QFontDatabase.addApplicationFont(p)


def get_ttf_font(size=13, bold=True):
    """Retorna uma fonte TrueType com suporte completo a caracteres em língua portuguesa."""
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_annotation_box(img, x, y, w, h, label="", tag="", box_color=(239, 68, 68, 255), lw=2, badge_pos="auto"):
    """
    Desenha uma caixa vermelha milimetricamente ajustada ao redor do elemento.
    Adiciona um badge de identificação com tipografia TrueType legível.
    badge_pos: 'auto', 'top_outside', 'top_inside', 'bottom_outside'
    """
    draw = ImageDraw.Draw(img, "RGBA")
    img_w, img_h = img.size

    # Clamping de segurança
    x = max(2, min(int(x), img_w - 4))
    y = max(2, min(int(y), img_h - 4))
    w = max(4, min(int(w), img_w - x - 2))
    h = max(4, min(int(h), img_h - y - 2))

    # Retângulo de contorno com espessura
    for i in range(lw):
        draw.rectangle([x - i, y - i, x + w + i, y + h + i], outline=box_color)

    font_lbl = get_ttf_font(size=12, bold=True)
    font_tag = get_ttf_font(size=12, bold=True)

    # Se houver tag numérica [1], [2], desenha círculo no canto superior esquerdo
    if tag:
        r = 11
        cx, cy = x + r, y + r
        if y < 15:
            cy = y + h - r
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 38, 38, 245), outline=(255, 255, 255, 255), width=2)
        bbox = font_tag.getbbox(str(tag))
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 - 1), str(tag), fill=(255, 255, 255, 255), font=font_tag)

    if label:
        bbox = font_lbl.getbbox(label)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x = 6
        pad_y = 3
        badge_w = tw + pad_x * 2
        badge_h = th + pad_y * 2

        badge_x = x + (26 if tag else 4)
        badge_x = max(4, min(badge_x, img_w - badge_w - 4))

        if badge_pos == "top_inside":
            badge_y = y + 3
        elif badge_pos == "top_outside":
            badge_y = max(2, y - badge_h - 2)
        elif badge_pos == "bottom_outside":
            badge_y = min(img_h - badge_h - 2, y + h + 2)
        else:  # auto
            if y >= badge_h + 3:
                badge_y = y - badge_h
            else:
                badge_y = y + 3

        draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill=(220, 38, 38, 235), outline=(255, 255, 255, 200), width=1)
        draw.text((badge_x + pad_x, badge_y + pad_y - 1), label, fill=(255, 255, 255, 255), font=font_lbl)

    return img


def draw_annotation_arrow(img, x_target, y_target, x_origin, y_origin, tag="1", arrow_color=(239, 68, 68, 255)):
    """
    Desenha uma seta indicativa com círculo numerado na origem apontando com precisão
    milimétrica para o alvo (x_target, y_target).
    """
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Círculo na origem com número
    r = 13
    draw.ellipse([x_origin - r, y_origin - r, x_origin + r, y_origin + r],
                 fill=(220, 38, 38, 245), outline=(255, 255, 255, 255), width=2)
    font_num = get_ttf_font(size=13, bold=True)
    bbox = font_num.getbbox(str(tag))
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x_origin - tw // 2, y_origin - th // 2 - 1), str(tag), fill=(255, 255, 255, 255), font=font_num)

    # Vetor unitário
    dx = float(x_target - x_origin)
    dy = float(y_target - y_origin)
    dist = np.hypot(dx, dy)
    if dist < 1.0:
        return img

    ux = dx / dist
    uy = dy / dist

    # Inicia a linha logo após a borda do círculo da origem
    start_x = x_origin + ux * (r + 1)
    start_y = y_origin + uy * (r + 1)
    draw.line([start_x, start_y, x_target, y_target], fill=arrow_color, width=3)

    # Ponta da seta (triângulo equilátero)
    angle = np.arctan2(dy, dx)
    arrow_len = 13.0
    arrow_angle = np.pi / 6.0

    p1_x = x_target - arrow_len * np.cos(angle - arrow_angle)
    p1_y = y_target - arrow_len * np.sin(angle - arrow_angle)
    p2_x = x_target - arrow_len * np.cos(angle + arrow_angle)
    p2_y = y_target - arrow_len * np.sin(angle + arrow_angle)

    draw.polygon([(x_target, y_target), (int(p1_x), int(p1_y)), (int(p2_x), int(p2_y))], fill=arrow_color)
    return img


def get_widget_rect(child, container):
    """Mapeia a geometria exata de um widget filho nas coordenadas do container pai."""
    pt = child.mapTo(container, QPoint(0, 0))
    return (pt.x(), pt.y(), child.width(), child.height())


def data_to_panel_pixel(panel, data_x, data_y):
    """Mapeia um ponto de dados do gráfico (tempo, amplitude/frequência) para pixels no PlotPanel."""
    disp_x, disp_y = panel.ax.transData.transform((data_x, data_y))
    canvas_pt = panel.canvas.mapTo(panel, QPoint(0, 0))
    px = canvas_pt.x() + int(disp_x)
    py = canvas_pt.y() + panel.canvas.height() - int(disp_y)
    return (px, py)


def get_axes_rect(panel):
    """Retorna o retângulo de recorte dos eixos do Matplotlib no PlotPanel."""
    bbox = panel.ax.get_window_extent(panel.canvas.renderer)
    canvas_pt = panel.canvas.mapTo(panel, QPoint(0, 0))
    x = canvas_pt.x() + int(bbox.x0)
    y = canvas_pt.y() + panel.canvas.height() - int(bbox.y1)
    w = int(bbox.width)
    h = int(bbox.height)
    return (x, y, w, h)


def capture_widget(widget, out_path):
    """Renderiza um QWidget ativo para PNG e retorna como Image do Pillow em RGBA."""
    widget.updateGeometry()
    QApplication.processEvents()
    QApplication.processEvents()
    pixmap = widget.grab()
    pixmap.save(out_path, "PNG")
    return Image.open(out_path).convert("RGBA")


def main():
    print("[*] Inicializando subsistema gráfico Qt com suporte total a fontes TrueType...")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    register_system_fonts()
    app.setFont(QFont("Segoe UI", 9))

    out_dir = os.path.join(PROJECT_ROOT, "docs", "figures")
    os.makedirs(out_dir, exist_ok=True)

    wav_path = os.path.join(PROJECT_ROOT, "extras", "audios", "m017_0376.wav")
    if not os.path.exists(wav_path):
        wav_path = os.path.join(PROJECT_ROOT, "audios", "m017_0376.wav")

    print(f"[*] Áudio de referência: {wav_path}")

    # Inicialização da janela principal
    win = MainWindow()
    win.setMinimumSize(1560, 960)
    win.resize(1600, 1000)
    win.show()
    QApplication.processEvents()

    # Preenche a fila com gravações para demonstrar o ambiente real de lote
    demo_files = [
        "m004_grav2.wav", "m010_0385.wav", "m012_0379.wav",
        "m015_grav3.wav", "m017_0376.wav", "m027_0484.wav"
    ]
    for df in demo_files:
        p = os.path.join(PROJECT_ROOT, "extras", "audios", df)
        if os.path.exists(p):
            win.ctx.loaded_files[df] = p
            win._add_audio_file_item(df, is_checked=True)
            w = win._get_item_widget_by_name(df)
            if w and hasattr(w, "set_analyzed"):
                if df in ["m004_grav2.wav", "m010_0385.wav", "m012_0379.wav"]:
                    w.set_analyzed(True, 35)
                elif df == "m017_0376.wav":
                    w.set_analyzed(True, 48)

    win._update_select_all_visibility()

    # Processa e injeta análise completa do m017_0376.wav
    target_name = os.path.basename(wav_path)
    win.ctx.loaded_files[target_name] = wav_path
    params = dict(DEFAULT_ALGO_PARAMS)
    params["freq_tolerance_hz"] = 700.0

    print("[*] Computando análise DSP e segmentação de pulsos...")
    res = CricketAnalyzer.analyze(wav_path, params)
    win.pipeline._apply_analysis_results(target_name, res, params)
    win.select_file_by_name(target_name)
    QApplication.processEvents()

    # Configura layout inicial com Oscilograma como principal
    win.show_plot_panel(win.panel_wave)
    win.show_plot_panel(win.panel_spec)
    win.show_plot_panel(win.panel_freq)
    win.show_plot_panel(win.panel_hist)
    win.swap_main_panel(win.panel_wave)
    win.plot_renderers.render_file(target_name)
    win.panel_wave.ax.set_xlim(2.15, 3.45)
    if win.plot_renderers.line_engine:
        win.plot_renderers.line_engine.render_high_detail()
    win.panel_wave.canvas.draw()
    QApplication.processEvents()
    time.sleep(0.3)

    # =========================================================================
    # PRINT 01: Visão Geral da Interface Principal
    # =========================================================================
    print("[*] Gerando Print 01: Visão Geral Panorâmica...")
    p1_path = os.path.join(out_dir, "ui_print01_main_window.png")
    img1 = capture_widget(win, p1_path)

    # 1. Fila de Áudio (Painel Esquerdo)
    rx, ry, rw, rh = get_widget_rect(win.left_panel, win)
    img1 = draw_annotation_box(img1, rx, ry, rw, rh, "Fila de Áudio e Métricas Rápidas", tag="1", lw=3)
    img1 = draw_annotation_arrow(img1, rx + rw - 35, ry + 250, rx + 45, ry + 250, tag="1")

    # 2. Painel Central (Oscilograma e Detecção)
    rx2, ry2, rw2, rh2 = get_widget_rect(win.main_host, win)
    img1 = draw_annotation_box(img1, rx2, ry2, rw2, rh2, "Painel Principal (Oscilograma e Detecção)", tag="2", lw=3)
    peak_pt = data_to_panel_pixel(win.panel_wave, 2.36, 0.60)
    img1 = draw_annotation_arrow(img1, rx2 + peak_pt[0], ry2 + peak_pt[1], rx2 + peak_pt[0] - 80, ry2 + peak_pt[1] - 65, tag="2")

    # 3. Pilha Lateral de Mini-Painéis
    rx3, ry3, rw3, rh3 = get_widget_rect(win.stack_splitter, win)
    img1 = draw_annotation_box(img1, rx3, ry3, rw3, rh3, "Pilha Lateral de Análise Espectral", tag="3", lw=3)
    img1 = draw_annotation_arrow(img1, rx3 + 220, ry3 + 130, rx3 + 280, ry3 + 70, tag="3")

    # 4. Barra de Transporte Inferior
    rx4, ry4, rw4, rh4 = get_widget_rect(win.transport_panel, win)
    img1 = draw_annotation_box(img1, rx4, ry4, rw4, rh4, "Barra de Transporte & Timeline", tag="4", lw=3)
    img1 = draw_annotation_arrow(img1, rx4 + 400, ry4 + rh4 - 40, rx4 + 400, ry4 + 25, tag="4")

    img1.save(p1_path, "PNG")

    # =========================================================================
    # PRINT 02: Fila de Processamento em Lote (Painel Esquerdo)
    # =========================================================================
    print("[*] Gerando Print 02: Painel Esquerdo / Fila em Lote...")
    p2_path = os.path.join(out_dir, "ui_print02_batch_queue.png")
    img2 = capture_widget(win.left_panel, p2_path)
    lp_w = win.left_panel.width()
    lp_h = win.left_panel.height()

    # 1. Cabeçalho de seleção
    img2 = draw_annotation_box(img2, 6, 6, lp_w - 12, 38, "Seleção Múltipla & Cabeçalho", tag="1", lw=2, badge_pos="top_inside")
    rx_chk, ry_chk, rw_chk, rh_chk = get_widget_rect(win.chk_select_all, win.left_panel)
    img2 = draw_annotation_arrow(img2, rx_chk + 10, ry_chk + rh_chk // 2, rx_chk - 45, ry_chk + rh_chk // 2, tag="1")

    # 2. Lista de Arquivos com status
    img2 = draw_annotation_box(img2, 6, 48, lp_w - 12, lp_h - 108, "Gravações e Badges de Status", tag="2", lw=2, badge_pos="top_inside")
    img2 = draw_annotation_arrow(img2, lp_w - 28, 175, lp_w - 95, 225, tag="2")

    # 3. Botão Analisar em Lote
    img2 = draw_annotation_box(img2, 6, lp_h - 52, lp_w - 12, 46, "Disparo da Fila em Lote", tag="3", lw=2, badge_pos="top_outside")
    img2 = draw_annotation_arrow(img2, lp_w // 2, lp_h - 28, lp_w // 2, lp_h - 85, tag="3")

    img2.save(p2_path, "PNG")

    # =========================================================================
    # PRINT 03: Forma de Onda e Envoltória de Hilbert (Painel Waveform)
    # =========================================================================
    print("[*] Gerando Print 03: Painel da Forma de Onda...")
    p3_path = os.path.join(out_dir, "ui_print03_waveform.png")
    win.swap_main_panel(win.panel_wave)
    win.panel_wave.ax.set_xlim(2.15, 3.45)
    if win.plot_renderers.line_engine:
        win.plot_renderers.line_engine.render_high_detail()
    win.panel_wave.canvas.draw()
    QApplication.processEvents()
    time.sleep(0.2)

    img3 = capture_widget(win.panel_wave, p3_path)

    # 1. Chips de camadas na barra de título
    rx, ry, rw, rh = get_widget_rect(win.panel_wave.btn_toggle_raw, win.panel_wave)
    _, _, rw_p, _ = get_widget_rect(win.panel_wave.btn_toggle_peaks, win.panel_wave)
    total_chips_w = (win.panel_wave.btn_toggle_peaks.mapTo(win.panel_wave, QPoint(0, 0)).x() + rw_p) - rx
    img3 = draw_annotation_box(img3, rx - 4, ry - 3, total_chips_w + 8, rh + 6, "Chips de Camadas (Bruto / Envoltória / Pulsos)", tag="1", lw=2, badge_pos="top_outside")
    img3 = draw_annotation_arrow(img3, rx + 45, ry + rh // 2, rx + 45, ry + rh + 40, tag="1")

    # 2. Destaque em um chilreio inteiro com 5 pulsos (Chirp 1: 2.24s a 2.40s)
    c_p1 = data_to_panel_pixel(win.panel_wave, 2.23, 0.85)
    c_p2 = data_to_panel_pixel(win.panel_wave, 2.41, -0.85)
    bx = min(c_p1[0], c_p2[0])
    by = min(c_p1[1], c_p2[1])
    bw = abs(c_p2[0] - c_p1[0])
    bh = abs(c_p2[1] - c_p1[1])
    img3 = draw_annotation_box(img3, bx, by, bw, bh, "Chilreio de 5 Pulsos (Colchete & Envoltória)", tag="2", lw=2, badge_pos="top_inside")
    img3 = draw_annotation_arrow(img3, bx + bw // 2, by + 12, bx + bw + 50, by + 35, tag="2")

    # 3. Destaque em um pulso individual (Chirp 2: pulso central a 2.70s)
    p_pt = data_to_panel_pixel(win.panel_wave, 2.70, 0.58)
    img3 = draw_annotation_arrow(img3, p_pt[0], p_pt[1], p_pt[0] + 65, p_pt[1] - 50, tag="3")

    img3.save(p3_path, "PNG")

    # =========================================================================
    # PRINT 04: Espectrograma STFT HD (Painel Spectrogram)
    # =========================================================================
    print("[*] Gerando Print 04: Espectrograma STFT HD...")
    p4_path = os.path.join(out_dir, "ui_print04_spectrogram.png")
    win.show_plot_panel(win.panel_spec)
    win.swap_main_panel(win.panel_spec)
    win.main_host.updateGeometry()
    QApplication.processEvents()
    QApplication.processEvents()
    win.panel_spec.ax.set_xlim(2.15, 3.45)
    win.panel_spec.spin_spec_ymin.setValue(0.0)
    win.panel_spec.spin_spec_ymax.setValue(12.0)
    win.panel_spec.canvas.draw()
    QApplication.processEvents()
    time.sleep(0.2)

    img4 = capture_widget(win.panel_spec, p4_path)

    # 1. Controles de Escala Y e Presets
    rx, ry, rw, rh = get_widget_rect(win.panel_spec.spec_ctrl_bar, win.panel_spec)
    img4 = draw_annotation_box(img4, rx + 2, ry + 2, 420, rh - 4, "Escala Y & Presets Espectrais", tag="1", lw=2, badge_pos="top_outside")
    img4 = draw_annotation_arrow(img4, rx + 110, ry + rh // 2, rx + 110, ry + rh + 35, tag="1")

    # 2. Portadora modal (faixa em torno de 5.81 kHz)
    c_p1 = data_to_panel_pixel(win.panel_spec, 2.22, 6.30)
    c_p2 = data_to_panel_pixel(win.panel_spec, 3.40, 5.30)
    cb_x = min(c_p1[0], c_p2[0])
    cb_y = min(c_p1[1], c_p2[1])
    cb_w = abs(c_p2[0] - c_p1[0])
    cb_h = abs(c_p2[1] - c_p1[1])
    img4 = draw_annotation_box(img4, cb_x, cb_y, cb_w, cb_h, "Frequência Portadora Modal (5.81 kHz)", tag="2", lw=2, badge_pos="top_inside")
    pt_carrier = data_to_panel_pixel(win.panel_spec, 2.36, 5.81)
    img4 = draw_annotation_arrow(img4, pt_carrier[0], pt_carrier[1], pt_carrier[0], pt_carrier[1] + 55, tag="2")

    # 3. Harmônico secundário superior (~11.6 kHz)
    h_pt = data_to_panel_pixel(win.panel_spec, 2.70, 11.6)
    img4 = draw_annotation_arrow(img4, h_pt[0], h_pt[1], h_pt[0] + 65, h_pt[1] + 35, tag="3")

    img4.save(p4_path, "PNG")

    # =========================================================================
    # PRINT 05: Espectro de Potência Welch (PSD)
    # =========================================================================
    print("[*] Gerando Print 05: Espectro Welch (PSD)...")
    p5_path = os.path.join(out_dir, "ui_print05_psd_welch.png")
    win.show_plot_panel(win.panel_freq)
    win.swap_main_panel(win.panel_freq)
    win.main_host.updateGeometry()
    QApplication.processEvents()
    QApplication.processEvents()
    win.plot_renderers.render_file(target_name)
    win.panel_freq.canvas.draw()
    QApplication.processEvents()
    time.sleep(0.2)

    img5 = capture_widget(win.panel_freq, p5_path)

    # 1. Barra de Controles de Tolerância Espectral
    rx, ry, rw, rh = get_widget_rect(win.panel_freq.freq_ctrl_bar, win.panel_freq)
    img5 = draw_annotation_box(img5, rx + 2, ry + 2, 340, rh - 4, "Tolerância Espectral Dinâmica (± Hz)", tag="1", lw=2, badge_pos="top_outside")
    img5 = draw_annotation_arrow(img5, rx + 140, ry + rh // 2, rx + 140, ry + rh + 30, tag="1")

    # 2. Pico da Portadora (5.82 kHz, -50 dB/Hz)
    pt_peak = data_to_panel_pixel(win.panel_freq, 5.82, -50.0)
    p_box1 = data_to_panel_pixel(win.panel_freq, 4.80, -42.0)
    p_box2 = data_to_panel_pixel(win.panel_freq, 6.80, -82.0)
    bx = min(p_box1[0], p_box2[0])
    by = min(p_box1[1], p_box2[1])
    bw = abs(p_box2[0] - p_box1[0])
    bh = abs(p_box2[1] - p_box1[1])
    img5 = draw_annotation_box(img5, bx, by, bw, bh, "Portadora Modal f_carrier (5.82 kHz)", tag="2", lw=2, badge_pos="top_inside")
    img5 = draw_annotation_arrow(img5, pt_peak[0], pt_peak[1], pt_peak[0] + 85, pt_peak[1], tag="2")

    img5.save(p5_path, "PNG")

    # =========================================================================
    # PRINT 06: Histograma Bivariado (Pulsos por Chilreio & Duração)
    # =========================================================================
    print("[*] Gerando Print 06: Histograma Bivariado...")
    p6_path = os.path.join(out_dir, "ui_print06_hist_bivariado.png")
    win.show_plot_panel(win.panel_hist)
    win.swap_main_panel(win.panel_hist)
    win.main_host.updateGeometry()
    QApplication.processEvents()
    QApplication.processEvents()
    win.plot_renderers.render_file(target_name)
    win.panel_hist.canvas.draw()
    QApplication.processEvents()
    time.sleep(0.2)

    img6 = capture_widget(win.panel_hist, p6_path)
    ax_rect = get_axes_rect(win.panel_hist)

    # 1. Eixo Y1 (Esquerdo - Contagem)
    img6 = draw_annotation_box(img6, ax_rect[0] - 50, ax_rect[1], 48, ax_rect[3], "Eixo Y1: Contagem", tag="1", lw=2, badge_pos="top_inside")
    img6 = draw_annotation_arrow(img6, ax_rect[0] - 12, ax_rect[1] + 60, ax_rect[0] + 50, ax_rect[1] + 60, tag="1")

    # 2. Barra Modal (6 pulsos, 36 chilreios)
    m_p1 = data_to_panel_pixel(win.panel_hist, 5.60, 38.0)
    m_p2 = data_to_panel_pixel(win.panel_hist, 6.40, 0.0)
    mb_x = min(m_p1[0], m_p2[0])
    mb_y = min(m_p1[1], m_p2[1])
    mb_w = abs(m_p2[0] - m_p1[0])
    mb_h = abs(m_p2[1] - m_p1[1])
    img6 = draw_annotation_box(img6, mb_x, mb_y, mb_w, mb_h, "Moda: 6 Pulsos (36 Chilreios)", tag="2", lw=2, badge_pos="top_inside")
    m_pt = data_to_panel_pixel(win.panel_hist, 6.0, 36.5)
    img6 = draw_annotation_arrow(img6, m_pt[0], m_pt[1], m_pt[0] + 55, m_pt[1] - 45, tag="2")

    # 3. Eixo Y2 (Direito - Duração em ms)
    y2_x = ax_rect[0] + ax_rect[2] + 2
    img6 = draw_annotation_box(img6, y2_x, ax_rect[1], 52, ax_rect[3], "Eixo Y2: Duração (ms)", tag="3", lw=2, badge_pos="top_inside")
    img6 = draw_annotation_arrow(img6, y2_x + 12, ax_rect[1] + 120, y2_x - 45, ax_rect[1] + 120, tag="3")

    img6.save(p6_path, "PNG")

    # =========================================================================
    # PRINT 07: Diálogo de Parâmetros Básicos (AlgoSettingsDialog)
    # =========================================================================
    print("[*] Gerando Print 07: AlgoSettingsDialog...")
    p7_path = os.path.join(out_dir, "ui_print07_algo_settings.png")
    dlg_algo = AlgoSettingsDialog(win.ctx.algo_params, win.lang, win)
    dlg_algo.resize(580, 420)
    dlg_algo.show()
    QApplication.processEvents()

    img7 = capture_widget(dlg_algo, p7_path)

    # 1. Campos de entrada de parâmetros fisiológicos
    rx, ry, rw, rh = get_widget_rect(dlg_algo.inputs["min_p"], dlg_algo)
    _, _, _, rh_gap = get_widget_rect(dlg_algo.inputs["gap_min"], dlg_algo)
    gap_y = dlg_algo.inputs["gap_min"].mapTo(dlg_algo, QPoint(0, 0)).y()
    total_form_h = (gap_y + rh_gap) - ry
    img7 = draw_annotation_box(img7, 16, ry - 6, dlg_algo.width() - 32, total_form_h + 12, "Parâmetros Fisiológicos Fundamentais", tag="1", lw=2, badge_pos="top_outside")
    img7 = draw_annotation_arrow(img7, rx + 40, ry + rh // 2, rx + 140, ry + rh // 2, tag="1")

    # 2. Botão Avançado
    rx2, ry2, rw2, rh2 = get_widget_rect(dlg_algo.advanced_button, dlg_algo)
    img7 = draw_annotation_box(img7, rx2 - 4, ry2 - 4, rw2 + 8, rh2 + 8, "Acesso aos Controles Avançados", tag="2", lw=2, badge_pos="top_outside")
    img7 = draw_annotation_arrow(img7, rx2 + rw2 // 2, ry2 + rh2 // 2, rx2 + rw2 // 2, ry2 - 38, tag="2")

    img7.save(p7_path, "PNG")
    dlg_algo.close()

    # =========================================================================
    # PRINT 08: Diálogo de Configurações Avançadas (AdvancedAlgoSettingsDialog)
    # =========================================================================
    print("[*] Gerando Print 08: AdvancedAlgoSettingsDialog...")
    p8_path = os.path.join(out_dir, "ui_print08_advanced_settings.png")
    dlg_adv = AdvancedAlgoSettingsDialog(win.ctx.algo_params, win)
    dlg_adv.resize(620, 540)
    dlg_adv.show()
    QApplication.processEvents()

    img8 = capture_widget(dlg_adv, p8_path)

    # 1. Filtro Butterworth
    rx, ry, rw, rh = get_widget_rect(dlg_adv.inputs["b1_min"], dlg_adv)
    b1_max_y = dlg_adv.inputs["b1_max"].mapTo(dlg_adv, QPoint(0, 0)).y()
    _, _, _, b1_max_h = get_widget_rect(dlg_adv.inputs["b1_max"], dlg_adv)
    total_b1_h = (b1_max_y + b1_max_h) - ry
    img8 = draw_annotation_box(img8, 16, ry - 6, dlg_adv.width() - 32, total_b1_h + 12, "Filtro Passa-Faixa Butterworth 8ª Ordem", tag="1", lw=2, badge_pos="top_outside")
    img8 = draw_annotation_arrow(img8, rx + 40, ry + rh // 2, rx + 130, ry + rh // 2, tag="1")

    # 2. Segregação GMM Coro Distante
    rx2, ry2, rw2, rh2 = get_widget_rect(dlg_adv.inputs["focal_sensitivity"], dlg_adv)
    img8 = draw_annotation_box(img8, 16, ry2 - 6, dlg_adv.width() - 32, rh2 + 12, "Sensibilidade Focal & GMM", tag="2", lw=2, badge_pos="top_outside")
    img8 = draw_annotation_arrow(img8, rx2 + 40, ry2 + rh2 // 2, rx2 + 130, ry2 + rh2 // 2, tag="2")

    img8.save(p8_path, "PNG")
    dlg_adv.close()

    # =========================================================================
    # PRINT 09: Mesa de Edição Interativa (Modo Lápis Ativo)
    # =========================================================================
    print("[*] Gerando Print 09: Mesa de Edição de Pulsos...")
    p9_path = os.path.join(out_dir, "ui_print09_pulse_editor.png")
    win.swap_main_panel(win.panel_wave)
    win.panel_wave.btn_pulse_edit.setChecked(True)
    win.panel_wave.pulse_edit_mode = True
    win.panel_wave.ax.set_xlim(2.26, 2.50)
    if win.plot_renderers.line_engine:
        win.plot_renderers.line_engine.render_high_detail()
    win.panel_wave.canvas.draw()
    QApplication.processEvents()
    time.sleep(0.2)

    img9 = capture_widget(win.panel_wave, p9_path)

    # 1. Ferramenta Lápis ativa na barra superior
    rx, ry, rw, rh = get_widget_rect(win.panel_wave.btn_pulse_edit, win.panel_wave)
    img9 = draw_annotation_box(img9, rx - 3, ry - 3, rw + 6, rh + 6, "Modo Lápis (Edição Ativa)", tag="1", lw=2, badge_pos="bottom_outside")
    img9 = draw_annotation_arrow(img9, rx + rw // 2, ry + rh // 2, rx - 45, ry + rh // 2, tag="1")

    # 2. Pulso real em foco para curadoria (pulso central a 2.33s com onset, pico e offset)
    cur_p1 = data_to_panel_pixel(win.panel_wave, 2.305, 0.65)
    cur_p2 = data_to_panel_pixel(win.panel_wave, 2.355, -0.20)
    cbx = min(cur_p1[0], cur_p2[0])
    cby = min(cur_p1[1], cur_p2[1])
    cbw = abs(cur_p2[0] - cur_p1[0])
    cbh = abs(cur_p2[1] - cur_p1[1])
    img9 = draw_annotation_box(img9, cbx, cby, cbw, cbh, "Curadoria de Marcadores", tag="2", lw=2, badge_pos="top_inside")
    pt_cur_peak = data_to_panel_pixel(win.panel_wave, 2.33, 0.54)
    img9 = draw_annotation_arrow(img9, pt_cur_peak[0], pt_cur_peak[1], pt_cur_peak[0] - 60, pt_cur_peak[1] - 45, tag="2")

    img9.save(p9_path, "PNG")
    win.panel_wave.btn_pulse_edit.setChecked(False)
    win.panel_wave.pulse_edit_mode = False

    # =========================================================================
    # PRINT 10: Diálogo de Parâmetros de IA (AIParamsDialog)
    # =========================================================================
    print("[*] Gerando Print 10: AIParamsDialog...")
    p10_path = os.path.join(out_dir, "ui_print10_ai_params.png")
    dlg_ai = AIParamsDialog(win, win.lang, win)
    dlg_ai.resize(600, 360)
    dlg_ai.show()
    QApplication.processEvents()

    img10 = capture_widget(dlg_ai, p10_path)

    # 1. Diagnóstico de status
    status_widget = dlg_ai.findChild(QLabel, "lbl_status")
    if status_widget:
        rx, ry, rw, rh = get_widget_rect(status_widget, dlg_ai)
        img10 = draw_annotation_box(img10, 16, ry - 6, dlg_ai.width() - 32, rh + 12, "Status e Diagnóstico do Classificador", tag="1", lw=2, badge_pos="top_inside")
        img10 = draw_annotation_arrow(img10, rx + 75, ry + 25, rx + 160, ry + 25, tag="1")

    # 2. Ações de Gestão (.skops / Reset)
    rx2, ry2, rw2, rh2 = get_widget_rect(dlg_ai.btn_export, dlg_ai)
    rx_rst, _, rw_rst, _ = get_widget_rect(dlg_ai.btn_reset, dlg_ai)
    total_act_w = (rx_rst + rw_rst) - rx2
    img10 = draw_annotation_box(img10, rx2 - 6, ry2 - 6, total_act_w + 12, rh2 + 12, "Exportação (.skops) e Reset Seguro", tag="2", lw=2, badge_pos="top_outside")
    img10 = draw_annotation_arrow(img10, rx2 + 40, ry2 + rh2 // 2, rx2 + 40, ry2 - 35, tag="2")

    img10.save(p10_path, "PNG")
    dlg_ai.close()

    # =========================================================================
    # PRINT 11: Diálogo de Exportação Gráfica (ExportGraphDialog)
    # =========================================================================
    print("[*] Gerando Print 11: ExportGraphDialog...")
    p11_path = os.path.join(out_dir, "ui_print11_export_graph.png")
    dlg_eg = ExportGraphDialog(win.ctx, parent=win)
    dlg_eg.resize(640, 840)
    dlg_eg.show()
    QApplication.processEvents()

    img11 = capture_widget(dlg_eg, p11_path)

    # 1. Grupo de painéis
    img11 = draw_annotation_box(img11, 16, 16, dlg_eg.width() - 32, 240, "Seleção Individual e em Massa de Painéis", tag="1", lw=2, badge_pos="top_inside")
    img11 = draw_annotation_arrow(img11, 55, 75, 125, 75, tag="1")

    # 2. Resolução DPI
    rx2, ry2, rw2, rh2 = get_widget_rect(dlg_eg._cmb_dpi, dlg_eg)
    img11 = draw_annotation_box(img11, 16, ry2 - 25, dlg_eg.width() - 32, 140, "Resolução (300/600 DPI) e Fundo Branco", tag="2", lw=2, badge_pos="top_inside")
    img11 = draw_annotation_arrow(img11, rx2 + 40, ry2 + rh2 // 2, rx2 - 35, ry2 + rh2 // 2, tag="2")

    # 3. Botão Exportar
    rx3, ry3, rw3, rh3 = get_widget_rect(dlg_eg._btn_export, dlg_eg)
    img11 = draw_annotation_box(img11, rx3 - 4, ry3 - 4, rw3 + 8, rh3 + 8, "Confirmação de Exportação", tag="3", lw=2, badge_pos="top_outside")
    img11 = draw_annotation_arrow(img11, rx3 + rw3 // 2, ry3 + rh3 // 2, rx3 + rw3 // 2, ry3 - 35, tag="3")

    img11.save(p11_path, "PNG")
    dlg_eg.close()

    # =========================================================================
    # PRINT 12: Diálogo de Laudos Técnicos em PDF (ExportReportDialog)
    # =========================================================================
    print("[*] Gerando Print 12: ExportReportDialog...")
    p12_path = os.path.join(out_dir, "ui_print12_export_report.png")
    dlg_er = ExportReportDialog(win.ctx, checked_files=demo_files, parent=win)
    dlg_er.resize(900, 640)
    dlg_er.show()
    QApplication.processEvents()

    img12 = capture_widget(dlg_er, p12_path)

    # 1. Metadados do espécime e expedição
    rx, ry, rw, rh = get_widget_rect(dlg_er.txt_temp, dlg_er)
    img12 = draw_annotation_box(img12, 16, 45, dlg_er.width() - 32, 130, "Metadados do Espécime (Voucher, Coletor, Temp)", tag="1", lw=2, badge_pos="top_outside")
    img12 = draw_annotation_arrow(img12, rx + 40, ry + rh // 2, rx + 125, ry + rh // 2, tag="1")

    # 2. Tabela de arquivos com identificação taxonômica
    rx2, ry2, rw2, rh2 = get_widget_rect(dlg_er.table_files, dlg_er)
    img12 = draw_annotation_box(img12, rx2, ry2, rw2, rh2, "Associação Espécie / Espécime / Gravações", tag="2", lw=2, badge_pos="top_outside")
    img12 = draw_annotation_arrow(img12, rx2 + 120, ry2 + 50, rx2 + 200, ry2 + 50, tag="2")

    # 3. Botão Gerar Laudo PDF
    rx3, ry3, rw3, rh3 = get_widget_rect(dlg_er.btn_export, dlg_er)
    img12 = draw_annotation_box(img12, rx3 - 4, ry3 - 4, rw3 + 8, rh3 + 8, "Compilação do Laudo PDF", tag="3", lw=2, badge_pos="top_outside")
    img12 = draw_annotation_arrow(img12, rx3 + rw3 // 2, ry3 + rh3 // 2, rx3 + rw3 // 2, ry3 - 35, tag="3")

    img12.save(p12_path, "PNG")
    dlg_er.close()

    # =========================================================================
    # PRINT 13: Barra de Transporte de Áudio e Timeline
    # =========================================================================
    print("[*] Gerando Print 13: AudioTransportPanel...")
    p13_path = os.path.join(out_dir, "ui_print13_transport_panel.png")
    img13 = capture_widget(win.transport_panel, p13_path)

    # 1. Botão de velocidade (Time-stretch)
    rx, ry, rw, rh = get_widget_rect(win.transport_panel.btn_speed, win.transport_panel)
    img13 = draw_annotation_box(img13, rx - 3, ry - 3, rw + 6, rh + 6, "Velocidade / Pitch (1×, 0.5×, 0.25×)", tag="1", lw=2, badge_pos="top_outside")
    img13 = draw_annotation_arrow(img13, rx + rw // 2, ry + rh // 2, rx - 45, ry + rh // 2, tag="1")

    # 2. Timeline com bandeiras de chilreios
    rx2, ry2, rw2, rh2 = get_widget_rect(win.transport_panel.timeline, win.transport_panel)
    img13 = draw_annotation_box(img13, rx2, ry2, rw2, rh2, "Timeline Interativa com Marcadores de Chilreios", tag="2", lw=2, badge_pos="top_inside")
    img13 = draw_annotation_arrow(img13, rx2 + 450, ry2 + 18, rx2 + 450, ry2 - 25, tag="2")

    img13.save(p13_path, "PNG")

    print("[OK] Todas as 13 capturas de tela foram geradas com sucesso com precisão milimétrica e fontes TrueType!")
    win.close()


if __name__ == "__main__":
    main()
