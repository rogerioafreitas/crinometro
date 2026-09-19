"""
Crinômetro - Gerador de Relatórios Bioacústicos em PDF de Alta Qualidade.
"""
import os
import sys
import datetime
import numpy as np
import scipy.stats

from utils.constants import APP_VERSION

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


if REPORTLAB_AVAILABLE:
    class NumberedCanvas(canvas.Canvas):
        """Canvas com rodapé automático contendo numeração dinâmica de páginas (Página X de Y)."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_page_decorations(self, total_pages):
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            
            # Linha fina de rodapé
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.6)
            self.line(36, 38, 559, 38)

            # Texto do rodapé
            now_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
            self.drawString(36, 26, f"Crinômetro v{APP_VERSION} • Bioacústica Computacional • Emitido em {now_str}")
            self.drawRightString(559, 26, f"Página {self._pageNumber} de {total_pages}")
            self.restoreState()
else:
    NumberedCanvas = None


def format_timestamp_ms(time_sec):
    """Converte segundos em mm:ss.cc (minutos:segundos.centésimos)."""
    minutes = int(time_sec // 60)
    seconds = int(time_sec % 60)
    centis = int(round((time_sec - int(time_sec)) * 100))
    if centis >= 100:
        seconds += 1
        centis = 0
    return f"{minutes:02d}:{seconds:02d}.{centis:02d}"


def extract_specimen_id(filename: str) -> str:
    """Extrai o identificador do espécime/macho a partir do nome do arquivo.
    Regra: identifica o identificador do macho/espécime antes do separador underscore '_'
    (ex.: em 'm015_grav3.wav' -> 'm015', 'macho 15__0468.wav' -> 'macho 15', 'macho 27_0484.wav' -> 'macho 27').
    Caso não possua underscore, utiliza o nome base sem extensão.
    """
    base = os.path.basename(filename)
    name_no_ext, _ = os.path.splitext(base)
    if "_" in name_no_ext:
        specimen = name_no_ext.split("_")[0].strip()
        if specimen:
            return specimen
    return name_no_ext.strip()


def safe_mode(values):
    """Calcula a moda estatística de uma lista de valores com fallback seguro."""
    if not values:
        return 0
    try:
        import statistics
        return int(statistics.mode(values))
    except Exception:
        vals, counts = np.unique(values, return_counts=True)
        return int(vals[np.argmax(counts)])


def analyze_rhythmic_cadence(chirp_peaks_list, rate):
    """Avalia a cadência rítmica temporal entre chilreios consecutivos (ICI).
    
    Isola pausas fisiológicas naturais e ruídos transitórios (outliers) do ritmo
    contínuo antes de inferir aceleração ou desaceleração rítmica.
    Retorna diagnóstico textual, inclinação da regressão, mediana de ICI e CV.
    """
    if not chirp_peaks_list or len(chirp_peaks_list) < 3:
        return {
            "diagnosis": "Amostragem Insuficiente",
            "explanation": "São necessários ao menos 3 chilreios consecutivos para computar a cadência rítmica.",
            "slope": 0.0,
            "ici_median_ms": 0.0,
            "cv_percent": 0.0,
        }

    ici_times_s = []
    ici_intervals_ms = []
    
    for i in range(len(chirp_peaks_list) - 1):
        t_end_cur = chirp_peaks_list[i][-1] / float(rate)
        t_start_next = chirp_peaks_list[i + 1][0] / float(rate)
        dt_ici_s = t_start_next - t_end_cur
        if dt_ici_s > 0.010: # maior que o gap mínimo fisiológico
            ici_times_s.append(t_start_next)
            ici_intervals_ms.append(dt_ici_s * 1000.0)

    if len(ici_intervals_ms) < 2:
        return {
            "diagnosis": "Cadência Regular Estável",
            "explanation": "Intervalos regulares sem dispersão temporal significativa.",
            "slope": 0.0,
            "ici_median_ms": float(np.median(ici_intervals_ms)) if ici_intervals_ms else 0.0,
            "cv_percent": 0.0,
        }

    raw_y = np.asarray(ici_intervals_ms, dtype=float)
    raw_x = np.asarray(ici_times_s, dtype=float)

    # 1. Filtro robusto de pausas fisiológicas e ruídos transitórios
    median_raw_ici = float(np.median(raw_y))
    q25 = float(np.percentile(raw_y, 25))
    q75 = float(np.percentile(raw_y, 75))
    iqr = max(20.0, q75 - q25)
    
    # Limite superior para ritmo contínuo intrínseco:
    # intervalos que excedam 2.8x a mediana ou Q75 + 2.5*IQR ou 2000 ms são pausas fisiológicas/ruídos
    pause_cutoff_ms = min(2000.0, max(median_raw_ici * 2.8, q75 + 2.5 * iqr))
    continuous_mask = (raw_y >= 20.0) & (raw_y <= pause_cutoff_ms)
    
    if np.sum(continuous_mask) >= 3:
        x = raw_x[continuous_mask]
        y = raw_y[continuous_mask]
    else:
        x = raw_x
        y = raw_y

    # Regressão linear sobre os intervalos rítmicos contínuos
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x, y)
    
    median_ici = float(np.median(y))
    mean_ici = float(np.mean(y))
    std_ici = float(np.std(y))
    cv = (std_ici / mean_ici * 100.0) if mean_ici > 0 else 0.0

    # Classificação rigorosa: exige significância estatística (p < 0.05) e inclinação relevante (|slope| > 0.15 ms/s)
    if p_value < 0.05 and slope < -0.15:
        diag = "Aceleração Rítmica"
        desc = (f"Os intervalos inter-chilreios (ICI) contínuos apresentaram tendência temporal negativa "
                f"({slope:.2f} ms/s, p={p_value:.3f}), indicando aceleração estatisticamente significativa do ritmo estridulatório.")
    elif p_value < 0.05 and slope > +0.15:
        diag = "Desaceleração Rítmica"
        desc = (f"Os intervalos inter-chilreios (ICI) contínuos apresentaram tendência temporal positiva "
                f"(+{slope:.2f} ms/s, p={p_value:.3f}), indicando espaçamento progressivo dos chilreios e perda de cadência rápida.")
    else:
        diag = "Cadência Estável"
        desc = (f"A cadência temporal contínua entre chilreios manteve-se metronômica e consistente "
                f"(inclinação de {slope:+.3f} ms/s, p={p_value:.3f}), com ritmo fisiológico regular.")

    return {
        "diagnosis": diag,
        "explanation": desc,
        "slope": slope,
        "ici_median_ms": median_ici,
        "cv_percent": cv,
    }


def generate_pdf_report(output_filepath, report_params, selected_cache, algo_params=None, include_chirp_list=True):
    """Gera o relatório estruturado em PDF (Completo ou Simplificado) para os áudios selecionados."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("A biblioteca 'reportlab' não está instalada no ambiente Python.")

    doc = SimpleDocTemplate(
        output_filepath,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Estilos tipográficos customizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0284C7"),
        spaceAfter=12
    )
    section_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    bold_style = ParagraphStyle(
        'DocBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A")
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # 1. TÍTULO E CABEÇALHO DO DOCUMENTO
    report_tag = "COMPLETO" if include_chirp_list else "SIMPLIFICADO"
    story.append(Paragraph(f"🦗 CRINÔMETRO — RELATÓRIO BIOACÚSTICO ({report_tag})", title_style))
    story.append(Paragraph(f"Bioacústica Computacional e Análise Estridulatória Automatizada (v{APP_VERSION})", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=10))

    # 2. METADADOS INSTITUCIONAIS E DA PESQUISA
    inst = report_params.get('institution', '').strip() or "Laboratório / Instituição não informada"
    name = report_params.get('researcher_name', '').strip() or "Pesquisador não informado"
    role = report_params.get('role', '').strip() or "Não especificado"
    level = report_params.get('level', '').strip() or "Não especificado"
    now_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    meta_data = [
        [Paragraph("<b>Instituição:</b>", body_style), Paragraph(inst.upper(), bold_style),
         Paragraph("<b>Pesquisador(a):</b>", body_style), Paragraph(name, bold_style)],
        [Paragraph("<b>Função:</b>", body_style), Paragraph(role, body_style),
         Paragraph("<b>Grau Acadêmico:</b>", body_style), Paragraph(level, body_style)],
        [Paragraph("<b>Data da Análise:</b>", body_style), Paragraph(now_str, body_style),
         Paragraph("<b>Áudios Compilados:</b>", body_style), Paragraph(f"{len(selected_cache)} arquivo(s)", bold_style)],
    ]
    meta_table = Table(meta_data, colWidths=[90, 170, 95, 168])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#64748B")),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. TABELA COMPARATIVA GERAL (Quando houver mais de 1 áudio, agrupado por espécime)
    if len(selected_cache) > 1:
        story.append(Paragraph("<b>Síntese Bioacústica Comparativa entre Espécimes</b>", section_h1))
        comp_headers = [
            Paragraph("<b>Espécime</b>", table_header),
            Paragraph("<b>Duração</b>", table_header),
            Paragraph("<b>Chilreios</b>", table_header),
            Paragraph("<b>Moda</b>", table_header),
            Paragraph("<b>Média ± Desv</b>", table_header),
            Paragraph("<b>Dens. (chilr/s)</b>", table_header),
            Paragraph("<b>ICI Mediano</b>", table_header),
            Paragraph("<b>Frequência Portadora</b>", table_header),
        ]
        comp_rows = [comp_headers]

        # Agrupamento de gravações pertencentes ao mesmo espécime
        specimens_dict = {}
        for fname, d in selected_cache.items():
            spec_id = extract_specimen_id(fname)
            if spec_id not in specimens_dict:
                specimens_dict[spec_id] = []
            specimens_dict[spec_id].append((fname, d))

        for spec_id, audio_list in specimens_dict.items():
            n_audios = len(audio_list)
            if n_audios > 1:
                spec_label = f"<b>{spec_id}</b><br/><font size='6.5' color='#64748B'>({n_audios} gravações)</font>"
            else:
                spec_label = f"<b>{spec_id}</b>"

            total_dur = sum(float(d.get("duration", 0.0)) for _, d in audio_list)
            
            # Concatenação de métricas brutas de todos os chilreios do espécime
            combined_chirps = []
            all_icis_ms = []
            carrier_vals = []
            carrier_weights = []

            for _, d in audio_list:
                ch = list(d.get("chirps", []))
                combined_chirps.extend(ch)
                ch_list = list(d.get("chirp_peaks_list", d.get("chirp_peaks", [])))
                r = float(d.get("rate", 48000.0))
                for i in range(len(ch_list) - 1):
                    dt = (ch_list[i + 1][0] - ch_list[i][-1]) / float(r)
                    if 0.010 <= dt <= 2.0:
                        all_icis_ms.append(dt * 1000.0)
                
                c_freq = d.get("carrier_freq")
                if c_freq is None:
                    dom_f = d.get("dom_freqs")
                    c_freq = float(np.median(dom_f)) if dom_f is not None and len(dom_f) > 0 else 5000.0
                carrier_vals.append(float(c_freq))
                carrier_weights.append(max(1, len(ch)))

            tot_ch = len(combined_chirps)
            m_val = safe_mode(combined_chirps) if combined_chirps else 0
            med_val = float(np.mean(combined_chirps)) if combined_chirps else 0.0
            std_val = float(np.std(combined_chirps)) if combined_chirps else 0.0
            dens_c = (tot_ch / total_dur) if total_dur > 0 else 0.0
            ici_m = float(np.median(all_icis_ms)) if all_icis_ms else 0.0

            # Frequência portadora consolidada (média ponderada pelo volume de chilreios)
            if carrier_vals:
                cons_carrier = float(np.average(carrier_vals, weights=carrier_weights))
            else:
                cons_carrier = 5000.0

            carrier_str = f"{cons_carrier / 1000.0:.2f} kHz" if cons_carrier >= 1000.0 else f"{cons_carrier:.0f} Hz"

            comp_rows.append([
                Paragraph(spec_label, table_cell_bold),
                Paragraph(f"{total_dur:.1f}s", table_cell),
                Paragraph(f"<b>{tot_ch}</b>", table_cell_bold),
                Paragraph(f"{m_val}", table_cell),
                Paragraph(f"{med_val:.1f} ± {std_val:.1f}", table_cell),
                Paragraph(f"{dens_c:.2f}", table_cell),
                Paragraph(f"{ici_m:.1f} ms" if ici_m > 0 else "-", table_cell),
                Paragraph(f"<font color='#0284C7'><b>{carrier_str}</b></font>", table_cell_bold),
            ])

        comp_table = Table(comp_rows, colWidths=[120, 48, 52, 40, 72, 60, 58, 73], repeatRows=1)
        c_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#64748B")),
            ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        for r_i in range(1, len(comp_rows)):
            if r_i % 2 == 0:
                c_style.append(('BACKGROUND', (0, r_i), (-1, r_i), colors.HexColor("#F8FAFC")))
            else:
                c_style.append(('BACKGROUND', (0, r_i), (-1, r_i), colors.white))
        comp_table.setStyle(TableStyle(c_style))
        story.append(comp_table)
        story.append(Spacer(1, 14))

    # 4. RELATÓRIO DETALHADO POR ÁUDIO
    for audio_idx, (fname, d) in enumerate(selected_cache.items()):
        # No relatório completo, cada áudio inicia em uma nova página.
        # No relatório simplificado, agrupamos para economizar espaço e colocar múltiplos por página.
        if audio_idx > 0 and include_chirp_list:
            story.append(PageBreak())

        audio_elements = []

        duration = float(d.get("duration", 0.0))
        chirps = list(d.get("chirps", []))
        chirp_peaks_list = list(d.get("chirp_peaks_list", d.get("chirp_peaks", [])))
        total_chirps = len(chirps)
        rate = float(d.get("rate", 48000.0))
        dom_f = d.get("dom_freqs")
        carrier = d.get("carrier_freq") or (float(np.median(dom_f)) if dom_f is not None and len(dom_f) > 0 else None)

        moda = d.get("moda", 0)
        media = float(d.get("media", 0.0))
        mediana = float(np.median(chirps)) if chirps else 0.0
        total_pulses = sum(chirps)
        
        # Densidade estridulatória
        dens_chirps = (total_chirps / duration) if duration > 0 else 0.0
        dens_pulses = (total_pulses / duration) if duration > 0 else 0.0

        audio_elements.append(Paragraph(f"<b>Arquivo:</b> {fname}", section_h1))
        audio_elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=6))

        # Tabela de Métricas Globais
        carrier_text = f"{carrier:.1f} Hz" if carrier else "N/A"
        metrics_data = [
            [
                Paragraph("<b>Chilreios Totais</b>", table_header),
                Paragraph("<b>Média Pulsos/Chilreio</b>", table_header),
                Paragraph("<b>Moda de Pulsos</b>", table_header),
                Paragraph("<b>Mediana de Pulsos</b>", table_header),
                Paragraph("<b>Freq. Portadora</b>", table_header),
                Paragraph("<b>Duração Total</b>", table_header),
            ],
            [
                Paragraph(f"<font size=11><b>{total_chirps}</b></font>", table_cell_bold),
                Paragraph(f"<font size=11><b>{media:.2f}</b></font>", table_cell_bold),
                Paragraph(f"<font size=11><b>{moda}</b></font>", table_cell_bold),
                Paragraph(f"<font size=11><b>{mediana:.1f}</b></font>", table_cell_bold),
                Paragraph(f"<font size=10><b>{carrier_text}</b></font>", table_cell),
                Paragraph(f"<font size=10><b>{duration:.2f} s</b></font>", table_cell),
            ],
            [
                Paragraph(f"Densidade: <b>{dens_chirps:.2f} chilr/s</b>", table_cell),
                Paragraph(f"Pulsos Totais: <b>{total_pulses}</b>", table_cell),
                Paragraph(f"Densidade: <b>{dens_pulses:.1f} pul/s</b>", table_cell),
                Paragraph(f"Taxa: <b>{int(rate)} Hz</b>", table_cell),
                Paragraph("Classificador: <b>Bioacústico</b>", table_cell),
                Paragraph(f"Tempo: <b>{format_timestamp_ms(duration)}</b>", table_cell),
            ]
        ]
        metrics_table = Table(metrics_data, colWidths=[87, 95, 80, 85, 88, 88])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F1F5F9")),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#F8FAFC")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#64748B")),
            ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        audio_elements.append(metrics_table)
        audio_elements.append(Spacer(1, 6))

        # Diagnóstico de Cadência Rítmica
        cadence = analyze_rhythmic_cadence(chirp_peaks_list, rate)
        diag_title = cadence["diagnosis"]
        
        # Cor do badge de diagnóstico
        if diag_title == "Cadência Estável":
            badge_color = "#059669" # Emerald
        elif diag_title == "Aceleração Rítmica":
            badge_color = "#2563EB" # Blue
        elif diag_title == "Desaceleração Rítmica":
            badge_color = "#D97706" # Amber
        else:
            badge_color = "#64748B"

        cadence_data = [
            [
                Paragraph(f"<b>Diagnóstico Rítmico Fisiológico:</b> "
                          f"<font color='{badge_color}'><b>{diag_title.upper()}</b></font>", body_style),
                Paragraph(f"<b>ICI Mediano:</b> {cadence['ici_median_ms']:.1f} ms  |  "
                          f"<b>Coef. Variação (CV):</b> {cadence['cv_percent']:.1f}%", body_style),
            ],
            [
                Paragraph(f"<i>{cadence['explanation']}</i>", body_style),
                Paragraph(f"Tendência Linear: <b>{cadence['slope']:+.3f} ms/s</b>", body_style),
            ]
        ]
        cadence_table = Table(cadence_data, colWidths=[310, 213])
        cadence_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor(badge_color)),
            ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        audio_elements.append(cadence_table)
        audio_elements.append(Spacer(1, 10))

        # No relatório simplificado, mantemos o bloco do áudio coeso via KeepTogether
        if not include_chirp_list:
            story.append(KeepTogether(audio_elements))
        else:
            story.extend(audio_elements)

        # 5. TABELA ESTRUTURADA DE CHILREIOS (inclusa no Relatório Completo; omitida no Simplificado)
        if include_chirp_list:
            story.append(Paragraph("<b>Listagem Sequencial de Chilreios Detectados</b>", section_h1))
            
            table_rows = [
                [
                    Paragraph("<b>Chilreio</b>", table_header),
                    Paragraph("<b>Pulsos</b>", table_header),
                    Paragraph("<b>Início</b>", table_header),
                    Paragraph("<b>Fim</b>", table_header),
                    Paragraph("<b>Duração (ms)</b>", table_header),
                    Paragraph("<b>Gap Médio (ms)</b>", table_header),
                ]
            ]

            for c_idx, cp in enumerate(chirp_peaks_list):
                num_p = len(cp)
                t_start_s = cp[0] / rate
                t_end_s = cp[-1] / rate
                dur_ms = (t_end_s - t_start_s) * 1000.0
                
                if num_p > 1:
                    gaps = [(cp[k] - cp[k-1]) / rate * 1000.0 for k in range(1, num_p)]
                    gap_mean_ms = float(np.mean(gaps))
                else:
                    gap_mean_ms = 0.0

                # Formatação textual: 01º Chilreio — 4 Pulsos | Início: 00:01.24 | Fim: 00:01.35 | Gap Médio: 27.5 ms
                row = [
                    Paragraph(f"<b>{c_idx + 1:02d}º Chilreio</b>", table_cell_bold),
                    Paragraph(f"<b>{num_p}</b>", table_cell_bold),
                    Paragraph(format_timestamp_ms(t_start_s), table_cell),
                    Paragraph(format_timestamp_ms(t_end_s), table_cell),
                    Paragraph(f"{dur_ms:.1f}", table_cell),
                    Paragraph(f"{gap_mean_ms:.1f}", table_cell),
                ]
                table_rows.append(row)

            chirp_table = Table(table_rows, colWidths=[90, 60, 95, 95, 90, 93], repeatRows=1)
            
            t_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#64748B")),
                ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
                ('TOPPADDING', (0, 0), (-1, -1), 3.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ]
            # Alternância de cores nas linhas
            for r_idx in range(1, len(table_rows)):
                if r_idx % 2 == 0:
                    t_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor("#F8FAFC")))
                else:
                    t_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.white))

            chirp_table.setStyle(TableStyle(t_style))
            story.append(chirp_table)

    # Constrói o documento com numeração de páginas
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_filepath
