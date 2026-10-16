# -*- coding: utf-8 -*-
"""
Gerador do Manual do Usuário e Guia de Operação Prática Completo — Crinômetro v4.5.0
Edição Científica e Metrológica Definitiva (Seções 1.0 a 7.0 Unificadas):
- 100% de fontes TrueType (Arial) registradas para eliminação total de caracteres de tofu (quadrados)
- Zero vazamentos de código LaTeX (todas as fórmulas renderizadas em tipografia HTML compatível)
- 13 Capturas de tela reais com marcações vetoriais milimetricamente no esquadro
- Enquadramento perfeito de todos os 4 gráficos da Seção 2.0 (sem cortes ou estouros de margem)
- Tabelas técnicas exaustivas, caixas de glossário por seção e texto de Materiais e Métodos pronto para publicação
- Banimento terminante de Dolbear (instrumento metrológico estrito para novas espécies e espécimes)
"""

import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

APP_VERSION = "4.5.0"

# Registro de Fontes TrueType com suporte Unicode total
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Italic', 'C:/Windows/Fonts/ariali.ttf'))
pdfmetrics.registerFont(TTFont('Arial-BoldItalic', 'C:/Windows/Fonts/arialbi.ttf'))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic', boldItalic='Arial-BoldItalic')


class DocCanvas(Canvas):
    """Canvas de duas passagens com cabeçalho e rodapé numerados dinamicamente em Arial."""
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
            return  # Capa limpa

        self.saveState()
        w, h = A4

        # Cabeçalho superior
        self.setFont("Arial-Bold", 8)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(1.8 * cm, h - 1.1 * cm, "CRINÔMETRO v4.5.0")
        self.setFont("Arial", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(4.8 * cm, h - 1.1 * cm, "|   Manual do Usuário e Guia de Operação Prática")
        self.drawRightString(w - 1.8 * cm, h - 1.1 * cm, "Taxonomia Integrativa & Bioacústica")

        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(1.8 * cm, h - 1.3 * cm, w - 1.8 * cm, h - 1.3 * cm)

        # Rodapé inferior
        self.setFont("Arial", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(1.8 * cm, 1.1 * cm, "Instrumento Metrológico para Espécimes e Novas Espécies - DSP & Active Learning")
        self.drawRightString(w - 1.8 * cm, 1.1 * cm, f"Página {page_num} de {total_pages}")

        self.line(1.8 * cm, 1.4 * cm, w - 1.8 * cm, 1.4 * cm)
        self.restoreState()


def build_styles():
    ss = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "DocTitle", parent=ss["Title"],
        fontSize=24, leading=29, textColor=colors.HexColor("#0F172A"),
        fontName="Arial-Bold", spaceAfter=6, alignment=TA_CENTER
    )
    styles["subtitle"] = ParagraphStyle(
        "DocSubtitle", parent=ss["Normal"],
        fontSize=11.5, leading=16, textColor=colors.HexColor("#334155"),
        fontName="Arial", spaceAfter=10, alignment=TA_CENTER
    )
    styles["version_badge"] = ParagraphStyle(
        "DocVersionBadge", parent=ss["Normal"],
        fontSize=9.5, leading=14, textColor=colors.HexColor("#0284C7"),
        fontName="Arial-Bold", spaceAfter=12, alignment=TA_CENTER
    )
    styles["h1"] = ParagraphStyle(
        "DocH1", parent=ss["Heading1"],
        fontSize=13.5, leading=17.5, textColor=colors.HexColor("#0F172A"),
        fontName="Arial-Bold", spaceBefore=12, spaceAfter=6,
        keepWithNext=True
    )
    styles["h2"] = ParagraphStyle(
        "DocH2", parent=ss["Heading2"],
        fontSize=11.0, leading=14.5, textColor=colors.HexColor("#1E3A8A"),
        fontName="Arial-Bold", spaceBefore=9, spaceAfter=5,
        keepWithNext=True
    )
    styles["h3"] = ParagraphStyle(
        "DocH3", parent=ss["Heading3"],
        fontSize=9.5, leading=13.0, textColor=colors.HexColor("#0369A1"),
        fontName="Arial-Bold", spaceBefore=7, spaceAfter=4,
        keepWithNext=True
    )
    styles["body"] = ParagraphStyle(
        "DocBody", parent=ss["BodyText"],
        fontSize=8.6, leading=12.4, textColor=colors.HexColor("#1E293B"),
        fontName="Arial", spaceAfter=5, alignment=TA_JUSTIFY
    )
    styles["body_bold"] = ParagraphStyle(
        "DocBodyBold", parent=styles["body"],
        fontName="Arial-Bold"
    )
    styles["bullet"] = ParagraphStyle(
        "DocBullet", parent=styles["body"],
        leftIndent=12, firstLineIndent=-8, spaceAfter=3, alignment=TA_LEFT
    )
    styles["caption"] = ParagraphStyle(
        "DocCaption", parent=ss["Normal"],
        fontSize=7.8, leading=10.5, textColor=colors.HexColor("#475569"),
        fontName="Arial-Italic", spaceBefore=3, spaceAfter=6, alignment=TA_CENTER
    )
    styles["table_header"] = ParagraphStyle(
        "DocTableHeader", parent=ss["Normal"],
        fontSize=8.0, leading=10.5, textColor=colors.HexColor("#FFFFFF"),
        fontName="Arial-Bold", alignment=TA_CENTER
    )
    styles["table_cell"] = ParagraphStyle(
        "DocTableCell", parent=ss["Normal"],
        fontSize=7.8, leading=10.2, textColor=colors.HexColor("#1E293B"),
        fontName="Arial", alignment=TA_LEFT
    )
    styles["table_cell_bold"] = ParagraphStyle(
        "DocTableCellBold", parent=styles["table_cell"],
        fontName="Arial-Bold"
    )
    styles["table_cell_code"] = ParagraphStyle(
        "DocTableCellCode", parent=styles["table_cell"],
        fontName="Courier", fontSize=7.5, textColor=colors.HexColor("#0284C7")
    )
    styles["code_block"] = ParagraphStyle(
        "DocCodeBlock", parent=ss["Normal"],
        fontSize=7.5, leading=10.0, textColor=colors.HexColor("#0F172A"),
        fontName="Courier", spaceAfter=4, alignment=TA_LEFT
    )
    return styles


def make_callout(text, title="DIRETRIZ DE DOMÍNIO CRÍTICA (v4.5.0)", bg="#FEF2F2", border="#EF4444", text_color="#991B1B"):
    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle('CalloutT', fontName="Arial-Bold", fontSize=9.0, leading=12, textColor=colors.HexColor(text_color), spaceAfter=3))
    p_body = Paragraph(text, ParagraphStyle('CalloutB', fontName="Arial", fontSize=8.2, leading=11.5, textColor=colors.HexColor("#334155"), alignment=TA_JUSTIFY))
    tbl = Table([[p_title], [p_body]], colWidths=[17.4 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg)),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor(border)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return tbl


def make_glossary_box(items_dict, section_name):
    flow = []
    p_title = Paragraph(f"<b>Glossário Técnico e Metrológico — {section_name}</b>", ParagraphStyle('GTitle', fontName="Arial-Bold", fontSize=8.5, leading=11.5, textColor=colors.HexColor("#0F172A"), spaceAfter=4))
    flow.append(p_title)
    for term, desc in items_dict.items():
        flow.append(Paragraph(f"&bull; <b>{term}:</b> {desc}", ParagraphStyle('GItem', fontName="Arial", fontSize=7.8, leading=10.5, textColor=colors.HexColor("#334155"), spaceAfter=2.0)))
    tbl = Table([[flow]], colWidths=[17.4 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return tbl


def make_print_card(img_path, print_num, title, target_w=17.0*cm, target_h=None, description=""):
    flow = []
    if os.path.exists(img_path):
        from PIL import Image as PILImage
        with PILImage.open(img_path) as im:
            orig_w, orig_h = im.size
        aspect = orig_h / float(orig_w)
        if target_h is None:
            calc_h = target_w * aspect
            max_h = 8.8 * cm
            if calc_h > max_h:
                calc_h = max_h
                target_w = calc_h / aspect
        else:
            calc_h = target_h
        img_flow = Image(img_path, width=target_w - 0.4*cm, height=calc_h)
        flow.append(img_flow)

    cap_text = f"<b>[CAPTURA DE TELA #{print_num:02d} — {title}]</b>"
    if description:
        cap_text += f"<br/><font color='#64748B'>{description}</font>"
    p_cap = Paragraph(cap_text, ParagraphStyle(
        f'CapP_{print_num}', fontName="Arial", fontSize=7.6, leading=10.0,
        textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER, spaceBefore=3
    ))
    flow.append(p_cap)

    tbl = Table([[flow]], colWidths=[target_w])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return tbl


def generate_full_manual_pdf(out_pdf_path):
    print(f"[*] Compilando Manual Completo em PDF (Edição Definitiva v{APP_VERSION})...")
    doc = SimpleDocTemplate(
        out_pdf_path,
        pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm
    )

    styles = build_styles()
    story = []
    fig_dir = os.path.join(PROJECT_ROOT, "docs", "figures")

    # =========================================================================
    # CAPA DO DOCUMENTO
    # =========================================================================
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("CRINÔMETRO", styles["title"]))
    story.append(Paragraph("Manual do Usuário e Guia de Operação Prática Completo", styles["subtitle"]))
    story.append(Paragraph(f"Versão de Produção {APP_VERSION}  &bull;  Edição Científica e Metrológica Integral", styles["version_badge"]))
    story.append(Spacer(1, 0.2 * cm))

    callout_dolbear = (
        "O <b>Crinômetro v4.5.0</b> é um instrumento metrológico computacional desenvolvido estritamente para a "
        "<b>descoberta, caracterização acústica, diagnose taxonômica e descrição formal de novas espécies e espécimes não documentados</b>. "
        "Em conformidade estrita com os padrões bioacústicos internacionais (<i>Ragge & Reynolds, 1998; Bennet-Clark, 1999</i>), "
        "<b>todas as estimativas térmicas baseadas na Lei de Dolbear (presentes na v4.3.2) foram terminantemente banidas e removidas</b>. "
        "A correlação de Dolbear é uma propriedade restrita a machos de <i>Oecanthus</i> e sua inclusão induzia extrapolações ecológicas espúrias. "
        "A versão 4.5.0 opera exclusivamente sobre grandezas físico-acústicas diretas, morfologia de envoltória, microssegundos e pureza espectral."
    )
    story.append(make_callout(callout_dolbear))
    story.append(Spacer(1, 0.4 * cm))

    # Tabela de Metadados
    meta_table_data = [
        [Paragraph("<b>Domínio de Aplicação:</b>", styles["table_cell_bold"]), Paragraph("Taxonomia Integrativa, Bioacústica Computacional e Metrologia de Orthoptera", styles["table_cell"])],
        [Paragraph("<b>Mecanismos de Análise:</b>", styles["table_cell_bold"]), Paragraph("Filtro Butterworth IIR Fase Zero, Hilbert, STFT HD, Welch PSD, GMM Bimodal e HistGradientBoosting", styles["table_cell"])],
        [Paragraph("<b>Interface & Gráficos:</b>", styles["table_cell_bold"]), Paragraph("PyQt6 + Matplotlib com Motores Adaptativos LoD Min-Max e Blitting Raster a 60 FPS", styles["table_cell"])],
        [Paragraph("<b>Público-Alvo:</b>", styles["table_cell_bold"]), Paragraph("Biólogos, Entomologistas, Taxonomistas, Bioacústicos e Pesquisadores de Biodiversidade", styles["table_cell"])],
        [Paragraph("<b>Data da Compilação:</b>", styles["table_cell_bold"]), Paragraph(f"{datetime.now().strftime('%d/%m/%Y')} — Distribuição Oficial Completa", styles["table_cell"])]
    ]
    t_meta = Table(meta_table_data, colWidths=[4.2 * cm, 13.2 * cm])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.0),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 0.4 * cm))

    # Sumário Geral
    story.append(Paragraph("<b>SUMÁRIO INTEGRAL DO MANUAL</b>", styles["h2"]))
    toc_data = [
        [Paragraph("<b>SEÇÃO / CAPÍTULO</b>", styles["table_header"]), Paragraph("<b>Pág.</b>", styles["table_header"])],
        [Paragraph("<b>1.0. Visão Geral, Instalação e Fluxo de Trabalho Rápido (Quickstart)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;1.1. Propósito na Taxonomia &bull; 1.2. Instalação &bull; 1.3. Anatomia da Janela Principal<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;1.4. Ingestão de Áudio (Individual vs. Lote) &bull; 1.5. Fila Assíncrona e Cancelamento", styles["table_cell"]), Paragraph("2", styles["table_cell_bold"])],
        [Paragraph("<b>2.0. Guia de Leitura dos Gráficos (Interpretação Bioacústica dos Painéis)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;2.1. Oscilograma e Hilbert &bull; 2.2. Espectrograma STFT HD &bull; 2.3. PSD Welch e Portadora<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;2.4. Histograma Bivariado (twinx) &bull; 2.5. Diagnóstico de Cadência Rítmica (Regressão)", styles["table_cell"]), Paragraph("4", styles["table_cell_bold"])],
        [Paragraph("<b>3.0. Parametrização Fina: Calibração de Cada Controle</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;3.1. Parâmetros Básicos &bull; 3.2. Parâmetros Avançados &bull; 3.3. Tabela Comparativa Exaustiva<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;3.4. Cenários Acústicos e Ecológicos Típicos de Campo", styles["table_cell"]), Paragraph("7", styles["table_cell_bold"])],
        [Paragraph("<b>4.0. Mesa de Edição Interativa e Aprendizado Ativo (IA / PulseLearner)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;4.1. Navegação Temporal Sincronizada &bull; 4.2. Escuta Desacelerada (Time-Stretch)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;4.3. Curadoria Manual de Pulsos (Modo Lápis) &bull; 4.4. Tabela de Atalhos &bull; 4.5. Treinamento IA (.skops)", styles["table_cell"]), Paragraph("9", styles["table_cell_bold"])],
        [Paragraph("<b>5.0. Guia Completo de Exportação (Gráficos, Tabelas e Laudos PDF)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;5.1. Exportação de Figuras Científicas (PNG 300/600 DPI e PDF Vetorial)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;5.2. Laudos Técnicos em PDF e Texto Pronto de 'Materiais e Métodos'<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;5.3. Matrizes Tabulares (.CSV Brasileiro, .CSV Universal e .TXT) para R/Python/PAST", styles["table_cell"]), Paragraph("11", styles["table_cell_bold"])],
        [Paragraph("<b>6.0. Guia de Confiabilidade dos Dados e Interpretação Biológica (CRÍTICO)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;6.1. Critérios de Qualidade (SNR &ge; 10 dB, clipping e amostragem)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;6.2. Validação Estatística Amostral (Nc e Np mínimos para diagnose taxonômica)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;6.3. Quando NÃO confiar no automático &bull; 6.4. Fundamentação IPI/ICI Offset-a-Onset", styles["table_cell"]), Paragraph("13", styles["table_cell_bold"])],
        [Paragraph("<b>7.0. Manutenção, Reset de Fábrica e Solução de Problemas (Troubleshooting)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;7.1. Restauração de Fábrica (crinometro_config.json) &bull; 7.2. Reset da IA (.skops)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;7.3. Tolerância a Falhas e Recuperação Determinística (DSP Fallback)", styles["table_cell"]), Paragraph("15", styles["table_cell_bold"])],
    ]
    t_toc = Table(toc_data, colWidths=[15.8 * cm, 1.6 * cm])
    t_toc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.0),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(t_toc)

    # =========================================================================
    # SEÇÃO 1: VISÃO GERAL, INSTALAÇÃO E QUICKSTART
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("1.0. Visão Geral, Instalação e Fluxo de Trabalho Rápido (Quickstart)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("1.1. Propósito na Taxonomia Integrativa e Bioacústica de Orthoptera", styles["h2"]))
    story.append(Paragraph(
        "A emissão sonora em Orthoptera (grilos e esperanças) constitui um dos caracteres fenotípicos de maior valor diagnóstico na biologia comparada. "
        "Muitas linhagens crípticas não apresentam diferenciação anatômica apreciável na genitália ou morfometria tradicional, porém divergem de forma estrita "
        "na sintaxe do canto de chamado (<i>calling song</i>). O <b>Crinômetro v4.5.0</b> atua como uma estação bioacústica automatizada e auditável, eliminando "
        "a subjetividade da medição manual de pulsos em editores generalistas de áudio.",
        styles["body"]
    ))

    story.append(Paragraph("1.2. Requisitos de Sistema e Instalação", styles["h2"]))
    story.append(Paragraph(
        "&bull; <b>Instalador Oficial Windows (Inno Setup):</b> Baixe <code>Crinometro_setup__v4.5.0.exe</code> e execute o assistente. O programa cria os atalhos e integra o atualizador seguro em PowerShell (<code>updater.ps1</code>), imune a problemas com pastas acentuadas.<br/>"
        "&bull; <b>Execução a Partir do Código-Fonte:</b> Requer Python 3.10+ e os pacotes: <code>PyQt6, numpy, scipy, scikit-learn, skops, matplotlib, reportlab, pillow</code>. "
        "Inicie pelo launcher temático: <code>python crinometro__laucher.py</code> ou direto pelo núcleo: <code>python main.py</code>.",
        styles["body"]
    ))

    story.append(Paragraph("1.3. Anatomia da Janela Principal (MainWindow)", styles["h2"]))
    story.append(Paragraph(
        "A interface gráfica da versão 4.5.0 divide-se em 5 regiões funcionais de alta densidade informativa: "
        "<b>(1) Barra Superior:</b> Acesso a arquivos, menus de exportação e controle do modo de IA (Modo DSP determinístico vs. Classificador Híbrido); "
        "<b>(2) Painel Lateral Esquerdo:</b> Fila de áudios carregados com caixas de seleção, contadores em tempo real de chilreios totais e média/variância de pulsos; "
        "<b>(3) Área Principal (Host Central):</b> Exibição maximizada de alta resolução da Forma de Onda ou Espectrograma; "
        "<b>(4) Pilha Lateral de Mini-Painéis:</b> Cartões gráficos complementares sincronizados temporalmente; "
        "<b>(5) Barra de Transporte e Timeline:</b> Régua contínua com bandeiras de chilreios, controle de velocidade e botão de interrupção <code>Abortar</code>.",
        styles["body"]
    ))

    p1_img = os.path.join(fig_dir, "ui_print01_main_window.png")
    story.append(make_print_card(
        p1_img, 1, "Visão Geral Panorâmica da Interface Principal",
        target_w=17.0 * cm,
        description="Destaques: [1] Fila lateral de áudios e métricas; [2] Painel central com forma de onda e detecção; [3] Pilha lateral com espectrograma, PSD e histograma; [4] Barra de transporte e timeline inferior."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("1.4. Ingestão de Áudio WAV: Arquivo Único vs. Processamento em Lote", styles["h2"]))
    story.append(Paragraph(
        "O Crinômetro suporta arquivos <b>RIFF WAVE (.wav)</b> de 16, 24 e 32 bits (PCM ou float) com taxas de amostragem de 8 kHz até 384 kHz (ultrassom). "
        "Caso a gravação de campo seja estéreo, o motor calcula automaticamente a energia eficaz (RMS) de cada canal e <b>seleciona o canal de maior relação sinal-ruído</b>, "
        "evitando o cancelamento destrutivo de fase (<i>comb filtering</i>) decorrente de médias aritméticas cegas.<br/>"
        "&bull; <b>Arquivo Único:</b> Clique em <code>+ Adicionar Áudio(s)</code> e selecione o WAV. A análise dispara instantaneamente e plota os 4 gráficos em menos de 1 segundo.<br/>"
        "&bull; <b>Processamento em Lote (Batch):</b> Selecione dezenas de arquivos com <code>Shift/Ctrl</code>. Clique na caixa <code>Selecionar tudo</code> e acione o botão <code>Analisar Selecionados</code>. O sistema processa a fila de forma assíncrona.",
        styles["body"]
    ))

    p2_img = os.path.join(fig_dir, "ui_print02_batch_queue.png")
    story.append(make_print_card(
        p2_img, 2, "Painel Lateral Esquerdo e Fila de Lotes em Execução",
        target_w=13.0 * cm,
        description="Destaques: [1] Controle 'Selecionar tudo'; [2] Lista com status de processamento por ícones; [3] Botão de disparo 'Analisar Selecionados'."
    ))
    story.append(Spacer(1, 0.2 * cm))

    # Glossário Seção 1
    g1 = {
        "Calling Song (Canto de Chamado)": "Emissão acústica estereotipada produzida por machos para atração reprodutiva coespecífica de fêmeas a longas distâncias.",
        "Chilreio (Echema / Chirp)": "Unidade sintática acústica de primeira ordem, formada por um agrupamento discreto de pulsos separados por intervalos regulares.",
        "Pulso (Sílaba)": "Som elementar indivisível produzido pelo fechamento tegminal único (atrito do plectrum na pars stridens).",
        "Comb Filtering (Filtragem em Pente)": "Artefato destrutivo de fase gerado ao fundir canais estéreo com defasagem, gerando cancelamento periódico de frequências.",
        "RMS (Root Mean Square)": "Valor eficaz da amplitude do sinal sonoro, representando a potência acústica média real transportada pela onda."
    }
    story.append(make_glossary_box(g1, "Seção 1 (Visão Geral e Quickstart)"))

    # =========================================================================
    # SEÇÃO 2: GUIA DE LEITURA DOS GRÁFICOS
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("2.0. Guia de Leitura dos Gráficos (Interpretação Bioacústica dos Painéis)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("2.1. Painel 1 — Forma de Onda (Oscilograma) e Envoltória de Hilbert", styles["h2"]))
    story.append(Paragraph(
        "Exibe a evolução da amplitude acústica normalizada (<i>Y</i> &isin; [-1.0, +1.0]) versus o tempo físico em segundos (<i>X</i>). "
        "Quatro seletores (chips) no topo do painel controlam a visibilidade das camadas:<br/>"
        "&bull; <b>Sinal Bruto (Cinza):</b> Onda acústica oscilatória condicionada pelo filtro passa-faixa Butterworth IIR de fase zero;<br/>"
        "&bull; <b>Envoltória (Azul Ciano):</b> Envoltória analítica calculada via Transformada de Hilbert, suavizada por janela móvel (15 ms) e normalizada pelo percentil 99,85. Permite inspecionar o <i>Onset</i> (início do ataque), <i>Peak</i> (pico máximo de energia) e <i>Offset</i> (decaimento);<br/>"
        "&bull; <b>Min-Max LOD (Laranja):</b> Feixes do motor adaptativo de alta performance que garantem visibilidade de pulsos estreitos mesmo em zoom afastado;<br/>"
        "&bull; <b>Pulsos (Verde Esmeralda):</b> Marcadores sobre os ápices validados, codificados por cores conforme o número de pulsos por chamado. Chilreios completos recebem colchetes horizontais superiores delimitando seu início e fim.",
        styles["body"]
    ))

    p3_img = os.path.join(fig_dir, "ui_print03_waveform.png")
    story.append(make_print_card(
        p3_img, 3, "Forma de Onda (Oscilograma) e Envoltória de Hilbert em Zoom Fino",
        target_w=17.0 * cm,
        description="Destaques: [1] Chips de controle de camadas (Sinal Bruto, Envoltória, Pulsos); [2] Chilreio legítimo de 5 pulsos com colchete delimitador; [3] Pulso individual com marcadores de Onset, Pico e Offset."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.2. Painel 2 — Espectrograma de Curto Tempo (STFT HD)", styles["h2"]))
    story.append(Paragraph(
        "Mapeia a matriz bidimensional de Tempo (<i>X</i>, em segundos), Frequência (<i>Y</i>, em kHz/Hz) e Potência em decibéis (<i>Z</i>, escala cromática contínua). "
        "Possui controles analíticos exclusivos na barra superior do painel:<br/>"
        "&bull; <b>Escala Y e Unidade:</b> Caixas numéricas de teto e piso e botão de alternância instantânea entre <code>kHz</code> e <code>Hz</code>;<br/>"
        "&bull; <b>Presets Rápidos:</b> Botão <code>10k</code> (enquadra 0 a 10 kHz), <code>Focal</code> (centraliza na banda da portadora <i>f</i><sub>carrier</sub> &plusmn; tolerância) e <code>Total</code> (expande até a frequência de Nyquist <i>f</i><sub>s</sub>/2);<br/>"
        "&bull; <b>Rastreamento Sub-bin:</b> Ajuste parabólico de 3 pontos no espectro STFT para determinar a frequência portadora instantânea com precisão sub-amostral superior à grade FFT.",
        styles["body"]
    ))

    p4_img = os.path.join(fig_dir, "ui_print04_spectrogram.png")
    story.append(make_print_card(
        p4_img, 4, "Espectrograma STFT HD com Portadora Modal e Filtro de Tolerância",
        target_w=17.0 * cm,
        description="Destaques: [1] Controles de escala Y e presets rápidos (10k, Focal, Total); [2] Frequência portadora modal contínua a ~5.81 kHz; [3] Harmônico secundário superior."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())
    story.append(Paragraph("2.3. Painel 3 — Espectro de Potência Média de Welch (PSD)", styles["h2"]))
    story.append(Paragraph(
        "Computa a Densidade Espectral de Potência média do sinal através do periodograma suavizado de Welch (janela de Hanning com 75% de sobreposição). "
        "Permite identificar instantaneamente:<br/>"
        "&bull; <b>Moda da Frequência Portadora (<i>f</i><sub>carrier</sub>):</b> Indicada por uma linha vertical tracejada vermelha no pico modal (ex.: 5,81 kHz);<br/>"
        "&bull; <b>Faixa Sombreada de Tolerância Dinâmica:</b> Região cinza translúcida configurável via controle numérico (+/- 700 Hz), dentro da qual pulsos acústicos são aceitos como foco bioacústico do espécime sob análise;<br/>"
        "&bull; <b>Largura de Banda a -3 dB e -10 dB:</b> Faixa de dispersão espectral que quantifica a pureza tonal da estridulação.",
        styles["body"]
    ))

    p5_img = os.path.join(fig_dir, "ui_print05_psd_welch.png")
    story.append(make_print_card(
        p5_img, 5, "Espectro de Potência Welch (PSD) com Portadora Modal e Tolerância",
        target_w=17.0 * cm,
        description="Destaques: [1] Barra de controle de tolerância dinâmica (+/- Hz); [2] Linha vertical e pico modal da portadora f_carrier (5.81 kHz); [3] Faixa de rejeição de ruído de baixa frequência."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.4. Painel 4 — Histograma Bivariado de Pulsos e Duração (twinx)", styles["h2"]))
    story.append(Paragraph(
        "Apresenta uma visão sintática integrada do repertório através de dois eixos verticais sincronizados:<br/>"
        "&bull; <b>Eixo Y1 (Esquerdo - Barras Azuis):</b> Contagem absoluta de ocorrências de chamados agrupados pelo número de pulsos por chilreio (PPC);<br/>"
        "&bull; <b>Eixo Y2 (Direito - Linha Laranja com Marcadores):</b> Duração média física do chilreio em milissegundos para cada classe de pulso;<br/>"
        "&bull; <b>Diagnóstico da Sintaxe Modal:</b> A barra mais alta revela imediatamente a moda estereotipada da espécie (ex.: chamado padrão com 5 pulsos e duração de 88 ms), permitindo segregar de relance variações anômalas.",
        styles["body"]
    ))

    p6_img = os.path.join(fig_dir, "ui_print06_hist_bivariado.png")
    story.append(make_print_card(
        p6_img, 6, "Histograma Bivariado de Pulsos por Chilreio e Duração Média",
        target_w=17.0 * cm,
        description="Destaques: [1] Eixo Y1 (Contagem de chamados); [2] Barra modal dominante (5 pulsos por chilreio); [3] Eixo Y2 (Duração física em milissegundos)."
    ))
    story.append(Spacer(1, 0.2 * cm))

    # Glossário Seção 2
    g2 = {
        "Envoltória de Hilbert": "Curva analítica que conecta as cristas instantâneas da onda sonora, eliminando a oscilação da portadora e preservando o contorno temporal de energia.",
        "STFT (Short-Time Fourier Transform)": "Transformada que divide o sinal em janelas temporais curtas e computa a FFT de cada bloco, gerando a matriz tempo-frequência.",
        "PSD Welch": "Método de cálculo espectral que calcula médias de FFTs segmentadas para reduzir ruído de variância estocástica.",
        "Twinx (Eixo Duplo)": "Disposição gráfica onde dois eixos verticais independentes compartilham o mesmo eixo horizontal de classes discretas."
    }
    story.append(make_glossary_box(g2, "Seção 2 (Leitura dos Gráficos)"))

    # =========================================================================
    # SEÇÃO 3: PARAMETRIZAÇÃO FINA
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("3.0. Parametrização Fina: Calibração de Cada Controle", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("3.1. Diálogo de Parâmetros Básicos (AlgoSettingsDialog)", styles["h2"]))
    story.append(Paragraph(
        "Acessível pelo menu <b><code>Configurações -> Parâmetros do Algoritmo...</code></b> ou pelo botão de engrenagem na barra superior. "
        "Define os limites fisiológicos fundamentais da espécie sob análise:<br/>"
        "&bull; <b>Mínimo / Máximo de Pulsos por Chamado (min_p / max_p):</b> Define a janela de aceitação da sintaxe tegminal. Rejeita ruídos isolados (1 pulso) ou sobreposições anômalas;<br/>"
        "&bull; <b>Limiar Mínimo de Amplitude (amp_min):</b> Teto relativo de sensibilidade da envoltória. Valores baixos (0.02) capturam chamados fracos; valores altos (0.15) silenciam o ruído de fundo ambiental;<br/>"
        "&bull; <b>Silêncio Mínimo entre Chilreios (gap_min):</b> Período refratário neuromuscular mínimo (em ms) para fechar o agrupamento de um chamado e iniciar a contagem do próximo.",
        styles["body"]
    ))

    p7_img = os.path.join(fig_dir, "ui_print07_algo_settings.png")
    story.append(make_print_card(
        p7_img, 7, "Diálogo de Parâmetros Básicos do Algoritmo",
        target_w=14.0 * cm,
        description="Destaques: [1] Controles de min_p, max_p, amp_min e gap_min; [2] Botão de acesso direto às configurações avançadas."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("3.2. Diálogo de Parâmetros Avançados (AdvancedAlgoSettingsDialog)", styles["h2"]))
    story.append(Paragraph(
        "Projetado para gravações com acústica desafiadora (reverberação de caverna, coros simpátricos de alta densidade e ruídos fluviais):<br/>"
        "&bull; <b>Filtro Passa-Faixa Butterworth 8ª Ordem (b1_min / b1_max):</b> Corta com altíssima inclinação (-48 dB/oitava) frequências fora da banda do espécime;<br/>"
        "&bull; <b>Janela de Suavização da Envoltória (smooth_window_ms):</b> Define a largura temporal do kernel de convolução. Janelas estreitas (2-5 ms) resolvem pulsos rápidos; janelas largas (15-20 ms) consolidam pulsos reverberantes;<br/>"
        "&bull; <b>Sensibilidade Focal e GMM (focal_sensitivity):</b> Ativa o classificador probabilístico de Mistura de Gaussianas para segregar machos distantes em segundo plano.",
        styles["body"]
    ))

    p8_img = os.path.join(fig_dir, "ui_print08_advanced_settings.png")
    story.append(make_print_card(
        p8_img, 8, "Diálogo de Configurações Avançadas e Filtros",
        target_w=14.0 * cm,
        description="Destaques: [1] Banda passa-faixa Butterworth IIR (b1_min/max); [2] Sensibilidade de segregação de coros simpátricos (focal_sensitivity)."
    ))
    story.append(Spacer(1, 0.2 * cm))

    # Tabela de Parâmetros
    param_table_data = [
        [Paragraph("<b>Parâmetro</b>", styles["table_header"]), Paragraph("<b>Padrão</b>", styles["table_header"]), Paragraph("<b>Faixa Útil</b>", styles["table_header"]), Paragraph("<b>Significado Biológico / Ação Recomendada</b>", styles["table_header"])],
        [Paragraph("min_p", styles["table_cell_code"]), Paragraph("2 pulsos", styles["table_cell"]), Paragraph("1 a 50", styles["table_cell"]), Paragraph("Rejeita transientes isolados (estalidos de galhos, gotas de chuva).", styles["table_cell"])],
        [Paragraph("max_p", styles["table_cell_code"]), Paragraph("10 pulsos", styles["table_cell"]), Paragraph("2 a 100", styles["table_cell"]), Paragraph("Teto de pulsos por chamado. Impede fusão de dois cantos contínuos.", styles["table_cell"])],
        [Paragraph("amp_min", styles["table_cell_code"]), Paragraph("0.05", styles["table_cell"]), Paragraph("0.01 a 0.50", styles["table_cell"]), Paragraph("Limiar mínimo de energia. Reduza em sinais fracos e aumente em áudios ruidosos.", styles["table_cell"])],
        [Paragraph("gap_min", styles["table_cell_code"]), Paragraph("60.0 ms", styles["table_cell"]), Paragraph("10 a 500 ms", styles["table_cell"]), Paragraph("Silêncio inter-chilreio mínimo. Define o limite refratário mecânico do inseto.", styles["table_cell"])],
        [Paragraph("b1_min / b1_max", styles["table_cell_code"]), Paragraph("3.2k / 6.0k Hz", styles["table_cell"]), Paragraph("100 a 48000 Hz", styles["table_cell"]), Paragraph("Corte passa-faixa Butterworth. Isole rigorosamente a portadora da espécie.", styles["table_cell"])],
        [Paragraph("focal_sensitivity", styles["table_cell_code"]), Paragraph("0.60", styles["table_cell"]), Paragraph("0.0 a 1.0", styles["table_cell"]), Paragraph("Sensibilidade do GMM para rejeitar cantos distantes em segundo plano.", styles["table_cell"])],
    ]
    t_params = Table(param_table_data, colWidths=[3.2*cm, 2.2*cm, 2.5*cm, 9.5*cm])
    t_params.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 2.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.8),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
    ]))
    story.append(t_params)

    # Glossário Seção 3
    g3 = {
        "Focal Sensitivity": "Parâmetro que pondera a distribuição bimodal de energia no GMM, atribuindo probabilidade zero a pulsos de cantores secundários de fundo.",
        "Butterworth IIR": "Filtro digital recursivo com resposta em frequência maximamente plana na banda passante, sem ondulações espúrias de ganho.",
        "Gate Refratário": "Intervalo temporal mínimo obrigatório de silêncio exigido para que dois grupos de pulsos sejam contabilizados como chamados independentes."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g3, "Seção 3 (Parametrização Fina)"))

    # =========================================================================
    # SEÇÃO 4: MESA DE EDIÇÃO E APRENDIZADO ATIVO (IA)
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("4.0. Mesa de Edição Interativa e Aprendizado Ativo (IA / PulseLearner)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("4.1. Navegação Sincronizada e Escuta Desacelerada (Time-Stretch)", styles["h2"]))
    story.append(Paragraph(
        "A inspeção detalhada de pulsos de altíssima velocidade (100 a 300 pulsos por segundo) é viabilizada por duas ferramentas integradas:<br/>"
        "&bull; <b>Sincronismo Bidirecional de Eixo X:</b> O botão <code>Sincronizar</code> na barra superior acopla o zoom e pan da Forma de Onda ao Espectrograma. Ao aproximar um pulso no oscilograma, o espectrograma acompanha o alinhamento temporal exato;<br/>"
        "&bull; <b>Reprodução com Pitch Preservado (Time-Stretch):</b> O botão de velocidade na barra de transporte permite ciclar entre <code>1x</code>, <code>0.5x</code> e <code>0.25x</code> sem transpor o tom para o grave, permitindo escutar claramente cada batimento alar individual.",
        styles["body"]
    ))

    p13_img = os.path.join(fig_dir, "ui_print13_transport_panel.png")
    story.append(make_print_card(
        p13_img, 13, "Painel de Transporte de Áudio e Timeline Interativa",
        target_w=17.0 * cm,
        description="Destaques: [1] Seletor de velocidade desacelerada (1x, 0.5x, 0.25x); [2] Timeline contínua com bandeiras de chilreios detectados."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("4.2. Curadoria Manual com Ferramenta Lápis e Atalhos de Teclado", styles["h2"]))
    story.append(Paragraph(
        "Para corrigir falsos positivos ou falsos negativos em trechos com ruído:<br/>"
        "1. Clique no botão <b>Lápis</b> (ou pressione <code>E</code>) na barra superior do oscilograma para ativar o modo de curadoria;<br/>"
        "2. <b>Inserir Pulso (Falso Negativo):</b> Clique com o <code>Botão Esquerdo</code> sobre a crista da envoltória. Um novo marcador será criado;<br/>"
        "3. <b>Remover Pulso (Falso Positivo):</b> Clique com o <code>Botão Direito</code> sobre o marcador indesejado;<br/>"
        "4. <b>Desfazer Ação:</b> Pressione <code>Ctrl+Z</code> ou clique no botão <code>Desfazer</code> na barra de título.",
        styles["body"]
    ))

    p9_img = os.path.join(fig_dir, "ui_print09_pulse_editor.png")
    story.append(make_print_card(
        p9_img, 9, "Mesa de Edição Interativa com Modo Lápis Ativado",
        target_w=17.0 * cm,
        description="Destaques: [1] Ferramenta Lápis ativa em azul; [2] Marcadores manuais sobrepostos à envoltória de Hilbert em zoom de alta resolução."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("4.3. Aprendizado Ativo: Ajuste do Classificador HistGradientBoosting (.skops)", styles["h2"]))
    story.append(Paragraph(
        "Após realizar as correções manuais na mesa de edição, o pesquisador não precisa reajustar dezenas de filtros manualmente. "
        "Basta clicar no botão <b><code>Aprender com Correções</code></b> na barra superior.<br/>"
        "&bull; <b>Extração das 20 Features Físicas:</b> O motor extrai para cada pulso anotado descritores como FWHM a -6 dB, fator de crista, energia RMS, derivada de ataque e proximidade espectral;<br/>"
        "&bull; <b>Mineração de Negativos Difíceis (Hard Negative Mining):</b> O modelo foca especificamente nos transientes ruidosos que enganaram o filtro inicial;<br/>"
        "&bull; <b>Serialização Segura (.skops):</b> O classificador treinado é gravado no formato seguro <code>.skops</code>, imune a vulnerabilidades de execução remota de código.",
        styles["body"]
    ))

    p10_img = os.path.join(fig_dir, "ui_print10_ai_params.png")
    story.append(make_print_card(
        p10_img, 10, "Diálogo de Gestão e Diagnóstico do Módulo de IA (AIParamsDialog)",
        target_w=14.0 * cm,
        description="Destaques: [1] Diagnóstico de status e árvores do classificador; [2] Botões para exportar/importar modelo treinado e reset de segurança."
    ))
    story.append(Spacer(1, 0.2 * cm))

    # Glossário Seção 4
    g4 = {
        "Time-Stretch": "Algoritmo de processamento digital de áudio que desacelera a velocidade de reprodução sem alterar as frequências (pitch).",
        "Hard Negative Mining": "Técnica de aprendizado supervisionado onde os exemplos negativos mais difíceis (ruídos que se assemelham a pulsos) recebem maior peso no retreinamento.",
        "Skops (.skops)": "Formato seguro de serialização de modelos estatísticos do ecossistema Scikit-Learn que elimina riscos de código malicioso de arquivos pickle legados.",
        "FWHM (-6 dB)": "Full Width at Half Maximum. Largura temporal do pulso medida exatamente no ponto onde a amplitude decai à metade (-6 dB) do pico máximo."
    }
    story.append(make_glossary_box(g4, "Seção 4 (Edição Interativa e IA)"))

    # =========================================================================
    # SEÇÃO 5: GUIA COMPLETO DE EXPORTAÇÃO
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("5.0. Guia Completo de Exportação e Publicação Científica", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("5.1. Exportação de Figuras Gráficas para Artigos (ExportGraphDialog)", styles["h2"]))
    story.append(Paragraph(
        "O Crinômetro v4.5.0 desacopla totalmente a renderização de exportação da resolução do monitor de vídeo através da fábrica pura "
        "<code>FigureFactory</code> e do controlador <code>ExportController</code>. "
        "Para acessar, clique no botão <b><code>Exportar Gráficos</code></b> na barra superior (ou use o menu <b><code>Exportar  -> Exportar Gráficos (PNG/PDF)...</code></b>).<br/>"
        "&bull; <b>Seleção de Painéis:</b> Marque individualmente quais gráficos deseja exportar (Oscilograma, Espectrograma, PSD Welch ou Histograma de Chilreios) usando os atalhos <code>Ctrl+A</code> (Marcar todos) e <code>Ctrl+D</code> (Limpar);<br/>"
        "&bull; <b>Resolução Metrológica (DPI):</b> Escolha entre <code>600 DPI</code> (Alta definição para linhas finas em periódicos como Zootaxa), <code>300 DPI</code> (Padrão editorial de publicação), <code>150 DPI</code> (Rascunho) ou <code>72 DPI</code> (Apresentação web);<br/>"
        "&bull; <b>Fundo / Tema:</b> Selecione <code>Branco (papel)</code> para impressão científica limpa ou <code>Tema atual da janela</code> para slides;<br/>"
        "&bull; <b>Formato de Saída:</b> <code>PDF multipágina (arquivo único)</code> consolidando todas as figuras ou <code>PNG individual por painel</code>.",
        styles["body"]
    ))

    p11_img = os.path.join(fig_dir, "ui_print11_export_graph.png")
    story.append(make_print_card(
        p11_img, 11, "Modal de Exportação de Gráficos Científicos de Alta Resolução",
        target_w=15.0 * cm,
        description="Destaques: [1] Seleção individual de painéis; [2] Configuração de DPI (300/600) e tema branco para impressão; [3] Confirmação de exportação."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("5.2. Geração de Laudos Técnicos em PDF e Metadados (ExportReportDialog)", styles["h2"]))
    story.append(Paragraph(
        "Para gerar o laudo técnico estruturado em PDF:<br/>"
        "1. Acesse o menu superior <b><code>Exportar  -> Exportar Relatório Modular...</code></b>;<br/>"
        "2. <b>Aba 'Metadados':</b> Preencha <code>Pesquisador(a)</code>, <code>Instituição</code>, <code>Localidade/Coordenadas</code>, <code>Equipamento de Gravação</code> e <code>Temperatura Medida em Campo (°C)</code> (anotada por termohigrômetro no ato da coleta, sem inferência computacional);<br/>"
        "3. <b>Tabela de Vouchers por Áudio:</b> Atribua a cada arquivo o seu <code>Cód. Espécime</code> (número de tombo/coleção) e a <code>Espécie / Morfotipo</code> preliminar;<br/>"
        "4. <b>Aba 'Conteúdo':</b> Selecione as seções modulares inclusas no laudo: Resumo Executivo, Métricas Consolidadas, Diagnóstico de Cadência Rítmica e Listagem Exaustiva de Chilreios e Pulsos.",
        styles["body"]
    ))

    p12_img = os.path.join(fig_dir, "ui_print12_export_report.png")
    story.append(make_print_card(
        p12_img, 12, "Configuração e Metadados do Laudo Técnico em PDF",
        target_w=17.0 * cm,
        description="Destaques: [1] Metadados da expedição e temperatura de campo; [2] Tabela vinculando arquivos a números de tombo/vouchers; [3] Disparo do laudo PDF."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Texto Pronto para a Seção de 'Materiais e Métodos' (Pronto para Manuscrito):", styles["h3"]))
    mat_methods_text = (
        "<i>\"As gravações bioacústicas foram analisadas com o software Crinômetro v4.5.0. "
        "Previamente à extração dos parâmetros, o sinal sonoro foi submetido a filtragem passa-faixa digital (Butterworth IIR de 8ª ordem) "
        "ajustada à banda espectral do espécime para eliminação de ruídos ambientais. A envoltória analítica foi extraída via Transformada Discreta "
        "de Hilbert e suavizada por média móvel adaptativa (15 ms). A delimitação de pulsos e chilreios foi executada por limiar adaptativo de energia "
        "relativo ao piso de ruído de fundo. A caracterização espectral empregou o método de Densidade Espectral de Potência de Welch (janela de Hanning, "
        "FFT de 2048 pontos, 75% de sobreposição) e interpolação parabólica sub-bin na STFT. As métricas temporais foram tabuladas por estatística "
        "paramétrica (média &plusmn; desvio padrão) e não-paramétrica (mediana e intervalo interquartil). Pausas fisiológicas atípicas (> 2.8x mediana) "
        "foram desconsideradas na reta de regressão do ritmo temporal. Para assegurar fidelidade na diagnose de táxons não descritos, todas as grandezas "
        "representam medidas físicas e acústicas empíricas diretas, sem aplicação de calibrações térmicas alométricas pré-fixadas.\"</i>"
    )
    story.append(Paragraph(mat_methods_text, styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph("5.3. Exportação de Matrizes Tabulares (.CSV Brasileiro, .CSV Universal e .TXT) para R/Python/PAST", styles["h2"]))
    story.append(Paragraph(
        "O Crinômetro exporta matrizes completas com todas as observações discretas prontas para ingestão em softwares estatísticos:<br/>"
        "&bull; <b>Padrão Brasileiro:</b> Codificado em <code>UTF-8 com BOM (utf-8-sig)</code>, separador ponto-e-vírgula (<code>;</code>) e decimal vírgula (<code>,</code>). Abre diretamente no <b>Microsoft Excel em Português</b> sem corrupção de acentos;<br/>"
        "&bull; <b>Padrão Universal:</b> Codificado em <code>UTF-8 puro</code>, separador vírgula (<code>,</code>) e decimal ponto (<code>.</code>). Formato canônico para importação imediata em <b>R</b> (<code>read.csv()</code>), <b>Python</b> (<code>pandas.read_csv()</code>) e <b>PAST</b> (análises multivariadas PCA, CVA e DFA).",
        styles["body"]
    ))

    # Tabela de Colunas do CSV
    csv_cols_data = [
        [Paragraph("<b>Coluna no CSV Universal</b>", styles["table_header"]), Paragraph("<b>Equivalente pt-BR</b>", styles["table_header"]), Paragraph("<b>Unidade</b>", styles["table_header"]), Paragraph("<b>Descrição Metrológica do Dado</b>", styles["table_header"])],
        [Paragraph("file_name", styles["table_cell_code"]), Paragraph("Arquivo de Áudio", styles["table_cell"]), Paragraph("texto", styles["table_cell"]), Paragraph("Nome do arquivo WAV de origem analisado.", styles["table_cell"])],
        [Paragraph("species", styles["table_cell_code"]), Paragraph("Espécie", styles["table_cell"]), Paragraph("texto", styles["table_cell"]), Paragraph("Identificação taxonômica do espécime (ou morfotipo).", styles["table_cell"])],
        [Paragraph("specimen_id", styles["table_cell_code"]), Paragraph("Cód. Espécime", styles["table_cell"]), Paragraph("texto", styles["table_cell"]), Paragraph("Código do voucher / número de tombo na coleção biológica.", styles["table_cell"])],
        [Paragraph("chirp_index", styles["table_cell_code"]), Paragraph("Nº do Chilreio", styles["table_cell"]), Paragraph("inteiro", styles["table_cell"]), Paragraph("Índice sequencial ordinal do chamado na gravação.", styles["table_cell"])],
        [Paragraph("start_time_s", styles["table_cell_code"]), Paragraph("Início (s)", styles["table_cell"]), Paragraph("s", styles["table_cell"]), Paragraph("Timestamp absoluto de Onset do primeiro pulso do chilreio.", styles["table_cell"])],
        [Paragraph("end_time_s", styles["table_cell_code"]), Paragraph("Fim (s)", styles["table_cell"]), Paragraph("s", styles["table_cell"]), Paragraph("Timestamp absoluto de Offset do último pulso do chamado.", styles["table_cell"])],
        [Paragraph("chirp_duration_ms", styles["table_cell_code"]), Paragraph("Duração (ms)", styles["table_cell"]), Paragraph("ms", styles["table_cell"]), Paragraph("Duração física total do chamado em milissegundos.", styles["table_cell"])],
        [Paragraph("pulses_per_chirp", styles["table_cell_code"]), Paragraph("Qtd. de Pulsos", styles["table_cell"]), Paragraph("pulsos", styles["table_cell"]), Paragraph("Número exato de pulsos constituintes do chamado (PPC).", styles["table_cell"])],
        [Paragraph("mean_ipi_ms", styles["table_cell_code"]), Paragraph("Média IPI (ms)", styles["table_cell"]), Paragraph("ms", styles["table_cell"]), Paragraph("Média dos intervalos inter-pulso (offset-a-onset) do chamado.", styles["table_cell"])],
        [Paragraph("ici_ms", styles["table_cell_code"]), Paragraph("Média ICI (ms)", styles["table_cell"]), Paragraph("ms", styles["table_cell"]), Paragraph("Intervalo inter-chilreio até o próximo chamado (NaN no último).", styles["table_cell"])],
    ]
    t_csv_cols = Table(csv_cols_data, colWidths=[3.2*cm, 2.8*cm, 1.2*cm, 10.2*cm])
    t_csv_cols.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
    ]))
    story.append(t_csv_cols)

    # Glossário Seção 5
    g5 = {
        "DPI (Dots Per Inch)": "Densidade de pontos por polegada. Define a resolução de impressão (300 DPI é o padrão da maioria dos periódicos; 600 DPI para linhas de alta definição).",
        "Voucher Specimen": "Espécime físico preservado em museu entomológico vinculado à gravação acústica para permitir revisões taxonômicas futuras.",
        "CSV Universal vs. Brasileiro": "Universal adota vírgula e ponto decimal (Python/R); Brasileiro adota ponto-e-vírgula e vírgula decimal com UTF-8-BOM (Excel).",
        "PAST": "Palaeontological Statistics, software amplamente utilizado em biometria, taxonomia e ecologia para análises de PCA, DFA e agrupamento multivariado."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g5, "Seção 5 (Exportação e Publicação)"))

    # =========================================================================
    # SEÇÃO 6: GUIA DE CONFIABILIDADE E INTERPRETAÇÃO BIOLÓGICA
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("6.0. Guia de Confiabilidade dos Dados e Interpretação Biológica (CRÍTICO)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("6.1. Critérios de Qualidade do Sinal Acústico e Relação Sinal-Ruído (SNR)", styles["h2"]))
    story.append(Paragraph(
        "Antes de publicar medições acústicas para diagnose de espécies novas, o taxonomista deve auditar a qualidade metrológica da gravação:<br/>"
        "&bull; <b>Relação Sinal-Ruído Local (SNR &ge; 10 dB Recomendado):</b> Gravações com <b>SNR &lt; 6 dB</b> apresentam flutuações randômicas que distorcem o ponto de Onset e Offset. Se o SNR estiver baixo, aplique tolerância espectral estreita (&plusmn; 300 Hz) ou descarte o trecho ruidoso;<br/>"
        "&bull; <b>Ausência de Clipping (Saturação A/D Digital):</b> Quando o ganho do microfone excede 0 dBFS (amplitude encostando em &plusmn; 1.0), o topo da onda é ceifado em forma de platô. O achatamento faz a segunda derivada (<code>peak_sharpness_rel</code>) desabar e pode induzir o algoritmo a dividir um pulso saturado em dois picos falsos nas bordas do platô. Sempre grave com margem de segurança (<i>headroom</i>) de pelo menos -6 dBFS a -12 dBFS;<br/>"
        "&bull; <b>Impacto da Taxa de Amostragem (44.1 kHz vs. 96 kHz+):</b> Em grilos com portadora em 5 kHz, 44.1 kHz é perfeitamente adequado. Contudo, espécies com pulsos ultrarrápidos (&lt; 5 ms) ou harmônicos ultrassônicos exigem 96 kHz ou 192 kHz para garantir resolução de sub-amostras no perfil da envoltória.",
        styles["body"]
    ))

    story.append(Paragraph("6.2. Validação Estatística Amostral para Taxonomia", styles["h2"]))
    story.append(Paragraph(
        "Na descrição formal de novos táxons, médias isoladas de 2 ou 3 chamados não possuem validade diagnóstica populacional:<br/>"
        "&bull; <b>Número Mínimo de Chilreios (<i>N</i><sub>c</sub> &ge; 15 a 30):</b> Imprescindível para estabilizar a estimativa da moda de pulsos por chamado (<b><i>Mo</i><sub>ppc</sub></b>) e o intervalo inter-chilreio mediano (<i>ICI</i>);<br/>"
        "&bull; <b>Número Mínimo de Pulsos (<i>N</i><sub>p</sub> &ge; 100):</b> Necessário para que a média e o desvio padrão da duração do pulso e do IPI tenham poder estatístico em análises discriminantes (DFA/PCA);<br/>"
        "&bull; <b>Significância do Diagnóstico Rítmico (<i>p</i> &lt; 0.05):</b> Uma inclinação de cadência só deve ser afirmada como aceleração ou desaceleração fisiológica se o teste <i>t</i> de Student rejeitar a hipótese nula com <i>p</i> &lt; 0.05. Caso contrário, reporta-se como cadência estável regular.",
        styles["body"]
    ))

    story.append(Paragraph("6.3. Quando NÃO Confiar no Automático (Artefatos de Campo)", styles["h2"]))
    story.append(Paragraph(
        "O pesquisador deve intervir manualmente com o Modo Lápis nas seguintes situações de campo:<br/>"
        "1. <b>Reverberação Severa em Mata Fechada / Cavernas:</b> As reflexões múltiplas em folhas largas e paredões rochosos preenchem o silêncio entre os pulsos, 'esticando' artificialmente a duração FWHM a -6 dB e fundindo pulsos consecutivos em uma única massa energética contínua;<br/>"
        "2. <b>Sobreposição de Dois Machos (Antifonia ou Canto Síncrono):</b> Quando dois indivíduos cantam na mesma folhagem, ocorre colisão de pulsos com intervalos inferiores a 0.8 &times; gap_min, gerando chilreios anômalos com 10 a 18 pulsos. Nesses casos, utilize a sensibilidade focal elevada (<code>focal_sensitivity = 0.85</code>) ou remova manualmente os pulsos fracos do macho secundário;<br/>"
        "3. <b>Estalidos de Gravetos e Chiado de Chuva:</b> Impulsos acústicos de banda larga que cruzam a portadora e geram pulsos fantasmas com fator de crista anômalo.",
        styles["body"]
    ))

    story.append(Paragraph("6.4. Fundamentação Biológica da Medição IPI e ICI de Offset-a-Onset", styles["h2"]))
    story.append(Paragraph(
        "Por que o Crinômetro mede IPI e ICI rigorosamente de <b>Offset-a-Onset</b> (do fim do pulso ao início do próximo), em vez do clássico Onset-a-Onset?<br/>"
        "&bull; <b>Fisiologia Neuromuscular do Gerador de Padrão (CPG):</b> O período de fechamento tegminal (duração do pulso) depende da velocidade de contração dos músculos alares subalar e basalar. Já o silêncio inter-pulso (IPI real) representa o <b>tempo de recuo passivo e abertura das asas</b> (período refratário mecânico);<br/>"
        "&bull; A medição Onset-a-Onset embute a duração do pulso anterior, mascarando variações sutis de fadiga neuromuscular. Ao segregar a duração do pulso do silêncio real (*Offset-to-Onset*), o Crinômetro fornece grandezas físicas ortogonais e independentes para a taxonomia comparativa.",
        styles["body"]
    ))

    # Glossário Seção 6
    g6 = {
        "Headroom (Margem de Ganho)": "Diferença entre o nível de pico máximo do sinal e o limite de saturação digital (0 dBFS). Recomenda-se manter pelo menos 6 dB de margem.",
        "Clipping Digital": "Ceifamento da forma de onda que ocorre quando a tensão elétrica excede a faixa de conversão analógico-digital, gerando distorção harmônica severa.",
        "Antifonia": "Comportamento comunicativo em que dois machos alternam seus chamados de forma coordenada para evitar sobreposição acústica mútua.",
        "Período Refratário Mecânico": "Intervalo mínimo de tempo necessário para que as asas do inseto se abram completamente antes de iniciar novo ciclo de estridulação."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g6, "Seção 6 (Confiabilidade Metrológica e Biologia)"))

    # =========================================================================
    # SEÇÃO 7: MANUTENÇÃO, RESET E SOLUÇÃO DE PROBLEMAS
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("7.0. Manutenção, Reset de Fábrica e Solução de Problemas (Troubleshooting)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=6))

    story.append(Paragraph("7.1. Restauração dos Padrões de Fábrica (crinometro_config.json)", styles["h2"]))
    story.append(Paragraph(
        "As preferências do Crinômetro são armazenadas no diretório de configuração do usuário:<br/>"
        "&bull; <b>Windows:</b> <code>%APPDATA%\\Crinometro\\crinometro_config.json</code>;<br/>"
        "&bull; <b>Linux/macOS:</b> <code>~/.config/Crinometro/crinometro_config.json</code>.<br/>"
        "Para resetar as configurações de volta aos padrões originais de laboratório:<br/>"
        "1. Acesse o menu superior <b><code>Configurações -> Resetar para Padrões (Desaprender)...</code></b>;<br/>"
        "2. Confirme a caixa de diálogo modal. O método <code>MainWindow.reset_to_defaults()</code> grava atomicamente o dicionário padrão <code>DEFAULT_ALGO_PARAMS</code> sob trava de concorrência <code>CONFIG_LOCK</code> e reanalisa o arquivo ativo do zero;<br/>"
        "3. <b>Reset Manual de Emergência:</b> Se o programa não abrir por corrupção de sistema operacional, feche o Crinômetro e apague manualmente o arquivo <code>crinometro_config.json</code>. Na próxima inicialização, um arquivo limpo será recriado automaticamente.",
        styles["body"]
    ))

    story.append(Paragraph("7.2. Como Limpar ou Resetar o Histórico de Aprendizado da IA (.skops)", styles["h2"]))
    story.append(Paragraph(
        "Caso o taxonomista tenha executado correções incorretas ou treinado a IA com áudios de outra família de insetos com características divergentes, o classificador pode ficar enviesado:<br/>"
        "1. Acesse o menu <b><code>Configurações -> Parâmetros de IA</code></b>;<br/>"
        "2. Na seção 'Gerenciamento de Aprendizado', clique no botão vermelho <b><code>Resetar Aprendizado</code></b>;<br/>"
        "3. O Crinômetro exclui o arquivo <code>modelo_treinado.skops</code>, limpa a memória de regras de poda e retorna imediatamente o motor ao modo <b>DSP determinístico puro</b>.",
        styles["body"]
    ))

    story.append(Paragraph("7.3. Tolerância a Falhas e Recuperação Graciosa Determinística (DSP Fallback)", styles["h2"]))
    story.append(Paragraph(
        "O Crinômetro v4.5.0 foi arquitetado sob o princípio da **Tolerância a Falhas Determinística (<i>Graceful Degradation</i>)**:<br/>"
        "&bull; <b>Auditoria de Segurança Criptográfica:</b> Antes de desserializar qualquer modelo <code>.skops</code>, a função <code>skops.io.get_untrusted_types()</code> inspeciona a árvore de tipos. Se houver classes não autorizadas ou incompatibilidade de versão de bibliotecas, o carregamento é bloqueado;<br/>"
        "&bull; <b>Quarentena Automática:</b> Arquivos de configuração ou modelos corrompidos por quedas de energia são automaticamente renomeados para <code>.corrupt-AAAAMMDD-HHMMSS</code> e colocados em quarentena;<br/>"
        "&bull; <b>Fallback Seguro:</b> O sistema <b>jamais fecha abruptamente ou trava</b>. Caso a IA falhe ou o arquivo de pesos esteja ausente, o sinalizador <code>PulseLearner.degraded = True</code> é ativado silenciosamente e o software continua operando com 100% de estabilidade sobre os filtros DSP determinísticos.",
        styles["body"]
    ))

    # Tabela de Troubleshooting
    tb_data = [
        [Paragraph("<b>Sintoma / Problema</b>", styles["table_header"]), Paragraph("<b>Causa Provável</b>", styles["table_header"]), Paragraph("<b>Solução Recomendada</b>", styles["table_header"])],
        [Paragraph("Nenhum pulso detectado no arquivo.", styles["table_cell_bold"]), Paragraph("A portadora do inseto está fora da banda padrão (3.2 a 6.0 kHz).", styles["table_cell"]), Paragraph("Abra Configurações Avançadas e ajuste b1_min e b1_max para a frequência real observada no PSD.", styles["table_cell"])],
        [Paragraph("Pulsos duplicados no mesmo pico.", styles["table_cell_bold"]), Paragraph("gap_min muito curto ou saturação digital (clipping).", styles["table_cell"]), Paragraph("Eleve gap_min de 25 ms para 35 ms ou aumente smooth_window para 20 ms.", styles["table_cell"])],
        [Paragraph("IA gerando marcações irregulares.", styles["table_cell_bold"]), Paragraph("Modelo enviesado por correções manuais conflitantes.", styles["table_cell"]), Paragraph("Acesse Configurações > Parâmetros de IA e clique em 'Resetar Aprendizado' para voltar ao DSP puro.", styles["table_cell"])],
        [Paragraph("Erro de reprodução no Play.", styles["table_cell_bold"]), Paragraph("Dispositivo de saída de áudio ocupado ou sem permissão.", styles["table_cell"]), Paragraph("Verifique se o fone de ouvido ou driver DirectSound está livre e reinicie o aplicativo.", styles["table_cell"])],
    ]
    t_tb = Table(tb_data, colWidths=[4.2*cm, 5.0*cm, 8.2*cm])
    t_tb.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_tb)

    # Glossário Seção 7
    g7 = {
        "Graceful Degradation": "Capacidade de um sistema de software continuar operando de forma estável, desativando recursos complexos em caso de falha sem travar.",
        "Quarentena de Arquivo": "Isolamento de um arquivo corrompido com extensão de data para evitar que o software tente lê-lo novamente e cause erro.",
        "CONFIG_LOCK": "Mecanismo de trava de sincronização (threading.RLock) que impede que duas operações de escrita acessem o arquivo de configuração simultaneamente.",
        "DSP Fallback": "Retorno automático e determinístico aos algoritmos matemáticos puros de sinal na ausência ou falha do classificador de machine learning."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g7, "Seção 7 (Manutenção e Troubleshooting)"))

    print("[*] Gravando documento PDF consolidado em disco...")
    doc.build(story, canvasmaker=DocCanvas)
    print(f"[OK] Manual Completo em PDF gerado com sucesso: {out_pdf_path}")
    return out_pdf_path


if __name__ == "__main__":
    out_pdf = os.path.join(PROJECT_ROOT, "docs", "Crinometro_Manual_do_Usuario_v4.5.0_Completo.pdf")
    generate_full_manual_pdf(out_pdf)
