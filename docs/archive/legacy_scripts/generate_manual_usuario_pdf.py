# -*- coding: utf-8 -*-
"""
Gerador do Manual do Usuário e Guia de Operação Prática em PDF — Crinômetro v4.5.0 (Parte 1)
Domínio: Taxonomia Integrativa, Bioacústica Computacional e Metrologia Acústica de Orthoptera.
Diretriz Crítica: Foco 100% em grandezas físicas puras (Dolbear banido/removido na v4.5.0).
Incorpora as capturas de tela reais com destaques gráficos e legendas padronizadas.
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

APP_VERSION = "4.5.0"


class DocCanvas(Canvas):
    """Canvas de duas passagens com cabeçalho e rodapé numerados dinamicamente."""
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
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(1.8 * cm, h - 1.1 * cm, "CRINÔMETRO v4.5.0")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(4.8 * cm, h - 1.1 * cm, "|   Manual do Usuário e Guia de Operação Prática")
        self.drawRightString(w - 1.8 * cm, h - 1.1 * cm, "Taxonomia Integrativa & Bioacústica")

        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(1.8 * cm, h - 1.3 * cm, w - 1.8 * cm, h - 1.3 * cm)

        # Rodapé inferior
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(1.8 * cm, 1.1 * cm, "Instrumento Metrológico para Espécimes e Novas Espécies  •  DSP & Active Learning")
        self.drawRightString(w - 1.8 * cm, 1.1 * cm, f"Página {page_num} de {total_pages}")

        self.line(1.8 * cm, 1.4 * cm, w - 1.8 * cm, 1.4 * cm)
        self.restoreState()


def build_styles():
    ss = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "DocTitle", parent=ss["Title"],
        fontSize=24, leading=29, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER
    )
    styles["subtitle"] = ParagraphStyle(
        "DocSubtitle", parent=ss["Normal"],
        fontSize=11.5, leading=16, textColor=colors.HexColor("#334155"),
        spaceAfter=12, alignment=TA_CENTER
    )
    styles["version_badge"] = ParagraphStyle(
        "DocVersionBadge", parent=ss["Normal"],
        fontSize=10, leading=14, textColor=colors.HexColor("#0284C7"),
        fontName="Helvetica-Bold", spaceAfter=14, alignment=TA_CENTER
    )
    styles["h1"] = ParagraphStyle(
        "DocH1", parent=ss["Heading1"],
        fontSize=15, leading=19, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=8,
        keepWithNext=True
    )
    styles["h2"] = ParagraphStyle(
        "DocH2", parent=ss["Heading2"],
        fontSize=12.5, leading=16, textColor=colors.HexColor("#1E3A8A"),
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6,
        keepWithNext=True
    )
    styles["h3"] = ParagraphStyle(
        "DocH3", parent=ss["Heading3"],
        fontSize=10.5, leading=14, textColor=colors.HexColor("#0369A1"),
        fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4,
        keepWithNext=True
    )
    styles["body"] = ParagraphStyle(
        "DocBody", parent=ss["BodyText"],
        fontSize=9.2, leading=13.5, textColor=colors.HexColor("#1E293B"),
        fontName="Helvetica", spaceAfter=6, alignment=TA_JUSTIFY
    )
    styles["body_bold"] = ParagraphStyle(
        "DocBodyBold", parent=styles["body"],
        fontName="Helvetica-Bold"
    )
    styles["bullet"] = ParagraphStyle(
        "DocBullet", parent=styles["body"],
        leftIndent=15, firstLineIndent=-8, spaceAfter=4, alignment=TA_LEFT
    )
    styles["caption"] = ParagraphStyle(
        "DocCaption", parent=ss["Normal"],
        fontSize=8, leading=11, textColor=colors.HexColor("#475569"),
        fontName="Helvetica-Oblique", spaceBefore=3, spaceAfter=8, alignment=TA_CENTER
    )
    styles["table_header"] = ParagraphStyle(
        "DocTableHeader", parent=ss["Normal"],
        fontSize=8.5, leading=11, textColor=colors.HexColor("#FFFFFF"),
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    styles["table_cell"] = ParagraphStyle(
        "DocTableCell", parent=ss["Normal"],
        fontSize=8.2, leading=10.8, textColor=colors.HexColor("#1E293B"),
        fontName="Helvetica", alignment=TA_LEFT
    )
    styles["table_cell_bold"] = ParagraphStyle(
        "DocTableCellBold", parent=styles["table_cell"],
        fontName="Helvetica-Bold"
    )
    styles["table_cell_code"] = ParagraphStyle(
        "DocTableCellCode", parent=styles["table_cell"],
        fontName="Courier-Bold", fontSize=8, textColor=colors.HexColor("#0284C7")
    )
    styles["glossary_title"] = ParagraphStyle(
        "DocGlossaryTitle", parent=ss["Normal"],
        fontSize=9.5, leading=12, textColor=colors.HexColor("#1E3A8A"),
        fontName="Helvetica-Bold", spaceAfter=4
    )
    styles["glossary_item"] = ParagraphStyle(
        "DocGlossaryItem", parent=ss["Normal"],
        fontSize=8.2, leading=11, textColor=colors.HexColor("#334155"),
        spaceAfter=3, alignment=TA_LEFT
    )
    return styles


def make_callout(text, title="DIRETRIZ DE DOMÍNIO CRÍTICA (v4.5.0)", bg="#FEF2F2", border="#EF4444", text_color="#991B1B"):
    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle('CalloutT', fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=colors.HexColor(text_color), spaceAfter=4))
    p_body = Paragraph(text, ParagraphStyle('CalloutB', fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"), alignment=TA_JUSTIFY))
    tbl = Table([[p_title], [p_body]], colWidths=[17.4 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg)),
        ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor(border)),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return tbl


def make_glossary_box(items_dict, section_name):
    flow = []
    p_title = Paragraph(f"📖 <b>Glossário Prático — {section_name}</b>", ParagraphStyle('GTitle', fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#0F172A"), spaceAfter=5))
    flow.append(p_title)
    for term, desc in items_dict.items():
        flow.append(Paragraph(f"• <b>{term}:</b> {desc}", ParagraphStyle('GItem', fontName="Helvetica", fontSize=8, leading=10.8, textColor=colors.HexColor("#334155"), spaceAfter=2.5)))
    tbl = Table([[flow]], colWidths=[17.4 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return tbl


def make_print_card(img_path, print_num, title, target_w=17.2*cm, target_h=None, description=""):
    """Insere o print real com bloco de metadados padronizado."""
    flow = []
    if os.path.exists(img_path):
        from PIL import Image as PILImage
        with PILImage.open(img_path) as im:
            orig_w, orig_h = im.size
        aspect = orig_h / float(orig_w)
        if target_h is None:
            calc_h = target_w * aspect
            # Limita altura máxima para não estourar a página
            if calc_h > 10.5 * cm:
                calc_h = 10.5 * cm
                target_w = calc_h / aspect
        else:
            calc_h = target_h
        flow.append(Image(img_path, width=target_w, height=calc_h))
    
    cap_text = f"<b>📸 [PRINT DE TELA #{print_num:02d} — {title}]</b>"
    if description:
        cap_text += f"<br/><font color='#64748B'>{description}</font>"
    p_cap = Paragraph(cap_text, ParagraphStyle('CapP', fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER, spaceBefore=4))
    flow.append(p_cap)

    tbl = Table([[flow]], colWidths=[17.4 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tbl


def generate_manual_pdf(out_pdf_path):
    print(f"[*] Compilando Manual do Usuário v{APP_VERSION} (Parte 1) em PDF...")
    doc = SimpleDocTemplate(
        out_pdf_path,
        pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm
    )

    styles = build_styles()
    story = []
    fig_dir = os.path.join(PROJECT_ROOT, "docs", "figures")

    # ═════════════════════════════════════════════════════════════
    # CAPA DO DOCUMENTO
    # ═════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph("🦗 CRINÔMETRO", styles["title"]))
    story.append(Paragraph("Manual do Usuário e Guia de Operação Prática Completo", styles["subtitle"]))
    story.append(Paragraph(f"Versão de Produção {APP_VERSION}  •  Edição Científica de Referência", styles["version_badge"]))
    story.append(Spacer(1, 0.4 * cm))

    callout_dolbear = (
        "O <b>Crinômetro v4.5.0</b> é um instrumento metrológico computacional desenvolvido estritamente para a "
        "<b>descoberta, caracterização acústica, diagnose taxonômica e descrição formal de novas espécies e espécimes não documentados</b>. "
        "Em conformidade estrita com os padrões bioacústicos internacionais (<i>Ragge & Reynolds, 1998; Bennet-Clark, 1999</i>), "
        "<b>todas as estimativas térmicas baseadas na Lei de Dolbear (presentes na v4.3.2) foram terminantemente banidas e removidas</b>. "
        "A correlação de Dolbear é uma propriedade restrita a machos de <i>Oecanthus</i> e sua inclusão induzia extrapolações ecológicas espúrias. "
        "A versão 4.5.0 opera exclusivamente sobre grandezas físico-acústicas diretas, morfologia de envoltória, microssegundos e pureza espectral."
    )
    story.append(make_callout(callout_dolbear))
    story.append(Spacer(1, 0.6 * cm))

    # Tabela de Metadados
    meta_table_data = [
        [Paragraph("<b>Domínio de Aplicação:</b>", styles["table_cell_bold"]), Paragraph("Taxonomia Integrativa, Bioacústica Computacional e Metrologia de Orthoptera", styles["table_cell"])],
        [Paragraph("<b>Mecanismos de Análise:</b>", styles["table_cell_bold"]), Paragraph("Filtro Butterworth IIR Fase Zero, Hilbert, STFT HD, Welch PSD, GMM Bimodal e HistGradientBoosting", styles["table_cell"])],
        [Paragraph("<b>Interface & Gráficos:</b>", styles["table_cell_bold"]), Paragraph("PyQt6 + Matplotlib com Motores Adaptativos LoD Min-Max e Blitting Raster a 60 FPS", styles["table_cell"])],
        [Paragraph("<b>Público-Alvo:</b>", styles["table_cell_bold"]), Paragraph("Biólogos, Entomologistas, Taxonomistas, Bioacústicos e Pesquisadores de Biodiversidade", styles["table_cell"])],
        [Paragraph("<b>Data da Compilação:</b>", styles["table_cell_bold"]), Paragraph(f"{datetime.now().strftime('%d/%m/%Y')} — Distribuição Oficial", styles["table_cell"])]
    ]
    t_meta = Table(meta_table_data, colWidths=[4.2 * cm, 13.2 * cm])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 0.8 * cm))

    # Sumário Geral
    story.append(Paragraph("<b>SUMÁRIO GERAL DO MANUAL</b>", styles["h2"]))
    toc_data = [
        [Paragraph("<b>PARTE 1: OPERAÇÃO FUNDAMENTAL, LEITURA E CURADORIA (Neste Volume)</b>", styles["table_cell_bold"]), Paragraph("<b>Pág.</b>", styles["table_header"])],
        [Paragraph("<b>1.0. Visão Geral, Instalação e Fluxo de Trabalho Rápido (Quickstart)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;1.1. Propósito na Taxonomia Integrativa • 1.2. Instalação • 1.3. Anatomia da Janela Principal<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;1.4. Ingestão de Áudio (Individual vs. Lote) • 1.5. Fila Assíncrona e Cancelamento (✕ Abortar)", styles["table_cell"]), Paragraph("2", styles["table_cell_bold"])],
        [Paragraph("<b>2.0. Guia de Leitura dos Gráficos (Interpretação Bioacústica dos Painéis)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;2.1. Arquitetura Modular e Drag & Drop • 2.2. Oscilograma e Envoltória de Hilbert • 2.3. Motor LoD<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;2.4. Espectrograma STFT HD • 2.5. PSD de Welch e Portadora • 2.6. Histograma Bivariado (twinx)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;2.7. Intervalos IPI, ICI e Diagnóstico de Cadência Rítmica", styles["table_cell"]), Paragraph("4", styles["table_cell_bold"])],
        [Paragraph("<b>3.0. Parametrização Fina: Calibração de Cada Controle</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;3.1. Diálogo Básico (AlgoSettingsDialog) • 3.2. Diálogo Avançado • 3.3. Tabela Comparativa<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;3.4. Cenários Acústicos e Ecológicos Típicos de Campo", styles["table_cell"]), Paragraph("7", styles["table_cell_bold"])],
        [Paragraph("<b>4.0. Mesa de Edição Interativa e Aprendizado Ativo (IA / PulseLearner)</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;4.1. Navegação Temporal Sincronizada • 4.2. Escuta Desacelerada (Time-Stretch vs. Heteródino)<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;4.3. Protocolo de Curadoria Manual • 4.4. Tabela de Atalhos • 4.5. Treinamento da IA<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;4.6. Extração das 20 Features, Hard Negative Mining e Serialização Segura .skops", styles["table_cell"]), Paragraph("9", styles["table_cell_bold"])],
        [Paragraph("<b>PARTE 2: EXPORTAÇÃO CIENTÍFICA, VALIDAÇÃO METROLÓGICA E TROUBLESHOOTING</b><br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;5.0. Guia de Exportação (Figuras PNG/PDF, Relatórios PDF, CSV/TXT) • 6.0. Confiabilidade e Interpretação<br/>"
                   "&nbsp;&nbsp;&nbsp;&nbsp;7.0. Manutenção, Reset de Fábrica e Recuperação Determinística", styles["table_cell"]), Paragraph("Volume 2", styles["table_cell_code"])],
    ]
    t_toc = Table(toc_data, colWidths=[15.8 * cm, 1.6 * cm])
    t_toc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(t_toc)

    # ═════════════════════════════════════════════════════════════
    # SEÇÃO 1: VISÃO GERAL, INSTALAÇÃO E QUICKSTART
    # ═════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("1.0. Visão Geral, Instalação e Fluxo de Trabalho Rápido (Quickstart)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=8))

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
        "• <b>Instalador Oficial Windows (Inno Setup):</b> Baixe <code>Crinometro_setup__v4.5.0.exe</code> e execute o assistente. O programa cria os atalhos e integra o atualizador seguro em PowerShell (<code>updater.ps1</code>), imune a problemas com pastas acentuadas.<br/>"
        "• <b>Execução a Partir do Código-Fonte:</b> Requer Python 3.10+ e os pacotes: <code>PyQt6, numpy, scipy, scikit-learn, skops, matplotlib, reportlab, pillow</code>. "
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
        "<b>(5) Barra de Transporte e Timeline:</b> Régua contínua com bandeiras de chilreios, controle de velocidade e botão de interrupção <code>✕ Abortar</code>.",
        styles["body"]
    ))

    p1_img = os.path.join(fig_dir, "ui_print01_main_window.png")
    story.append(make_print_card(
        p1_img, 1, "Visão Geral Panorâmica da Interface Principal (Tema Escuro)",
        description="Destaques: [1] Barra superior e botão '+ Adicionar Áudio(s)'; [2] Painel lateral com lista e métricas rápidas; [3] Forma de Onda central; [4] Pilha lateral com Espectrograma, PSD e Histograma; [5] Barra de transporte inferior."
    ))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("1.4. Ingestão de Áudio WAV: Arquivo Único vs. Processamento em Lote", styles["h2"]))
    story.append(Paragraph(
        "O Crinômetro suporta arquivos <b>RIFF WAVE (.wav)</b> de 16, 24 e 32 bits (PCM ou float) com taxas de amostragem de 8 kHz até 384 kHz (ultrassom). "
        "Caso a gravação de campo seja estéreo, o motor calcula automaticamente a energia eficaz (RMS) de cada canal e <b>seleciona o canal de maior relação sinal-ruído</b>, "
        "evitando o cancelamento destrutivo de fase (<i>comb filtering</i>) decorrente de médias aritméticas cegas.",
        styles["body"]
    ))
    story.append(Paragraph(
        "• <b>Arquivo Único:</b> Clique em <code>+ Adicionar Áudio(s)</code> e selecione o WAV. A análise dispara instantaneamente e plota os 4 gráficos em menos de 1 segundo.<br/>"
        "• <b>Processamento em Lote (Batch):</b> Selecione dezenas de arquivos com <code>Shift/Ctrl</code>. Clique na caixa <code>Selecionar tudo</code> e acione o botão <code>⚡ Analisar Selecionados</code>. O sistema processa a fila de forma assíncrona.",
        styles["body"]
    ))

    p2_img = os.path.join(fig_dir, "ui_print02_batch_queue.png")
    story.append(make_print_card(
        p2_img, 2, "Painel Lateral Esquerdo e Fila de Lotes em Execução",
        target_w=14.0 * cm,
        description="Destaques: [1] Controle 'Selecionar tudo'; [2] Lista com status de processamento por ícones; [3] Botão de disparo '⚡ Analisar Selecionados'."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("1.5. Fila Assíncrona e Cancelamento Cooperativo (✕ Abortar)", styles["h2"]))
    story.append(Paragraph(
        "O processamento ocorre via <code>GenericWorker</code> em thread secundária, impedindo que a interface congele. "
        "Caso o pesquisador queira interromper uma análise de arquivo muito longo ou cancelar um lote de dezenas de arquivos, "
        "basta clicar no botão vermelho <b><code>✕ Abortar</code></b> na barra inferior. O <code>WorkerRegistry</code> sinaliza o evento atômico e interrompe o cálculo em menos de 50 ms sem corromper as análises já salvas no cache.",
        styles["body"]
    ))

    # Glossário Seção 1
    g1 = {
        "Calling Song (Canto de Chamado)": "Emissão acústica estereotipada produzida por machos para atração reprodutiva coespecífica de fêmeas a longas distâncias.",
        "Chilreio (Echema / Chirp)": "Unidade sintática acústica de primeira ordem, formada por um agrupamento discreto de pulsos separados por intervalos regulares.",
        "Pulso (Sílaba)": "Som elementar indivisível produzido pelo fechamento tegminal único (atrito do plectrum na pars stridens).",
        "Comb Filtering (Filtragem em Pente)": "Artefato destrutivo de fase gerado ao fundir canais estéreo com defasagem, gerando cancelamento periódico de frequências.",
        "RMS (Root Mean Square)": "Valor eficaz da amplitude do sinal sonoro, representando a potência acústica média real transportada pela onda."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g1, "Seção 1 (Visão Geral e Quickstart)"))

    # ═════════════════════════════════════════════════════════════
    # SEÇÃO 2: GUIA DE LEITURA DOS GRÁFICOS
    # ═════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("2.0. Guia de Leitura dos Gráficos (Interpretação Bioacústica dos Painéis)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=8))

    story.append(Paragraph("2.1. Arquitetura Modular de Exibição e Drag & Drop", styles["h2"]))
    story.append(Paragraph(
        "Os 4 cartões gráficos do Crinômetro operam sob sincronismo temporal bidirecional via <code>NavigationController</code>. "
        "Qualquer mini-painel da pilha lateral pode ser arrastado pela sua barra de título para trocar de posição ou maximizado no quadrante central com o botão <code>⛶</code>. "
        "Para restabelecer o arranjo original de fábrica, use o menu <b><code>Gráficos 📊 → 🔄 Restaurar Layout Padrão</code></b>.",
        styles["body"]
    ))

    story.append(Paragraph("2.2. Painel 1 — Forma de Onda (Oscilograma) e Envoltória Analítica de Hilbert", styles["h2"]))
    story.append(Paragraph(
        "Exibe a evolução da amplitude acústica normalizada ($Y \in [-1.0, +1.0]$) versus o tempo físico em segundos ($X$). "
        "Quatro seletores (chips) no topo do painel controlam a visibilidade das camadas:<br/>"
        "• <b>Sinal Bruto (#94A3B8 - Cinza):</b> Onda acústica oscilatória condicionada pelo filtro passa-faixa Butterworth IIR de fase zero;<br/>"
        "• <b>Envoltória (#0284C7 - Azul Ciano):</b> Envoltória analítica calculada via Transformada de Hilbert ($E(t) = \\sqrt{x^2(t) + \\mathcal{H}\\{x(t)\\}^2}$), suavizada por janela de Hann (15 ms) e normalizada pelo percentil 99,85. Permite inspecionar o <i>Onset</i> (ataque), <i>Peak</i> (ápice) e <i>Offset</i> (decaimento);<br/>"
        "• <b>Min-Max LOD (#F97316 - Laranja):</b> Feixes do motor adaptativo de alta performance;<br/>"
        "• <b>Pulsos (#10B981 - Verde Esmeralda):</b> Marcadores sobre os ápices validados, codificados por cores conforme o número de pulsos por chamado (2p = Azul Royal, 3p = Roxo, 4p = Laranja, 5p = Verde Esmeralda, 6p = Magenta). Pulsos isolados ou rejeitados pela tolerância de portadora aparecem em cinza translúcido.",
        styles["body"]
    ))

    p3_img = os.path.join(fig_dir, "ui_print03_waveform.png")
    story.append(make_print_card(
        p3_img, 3, "Forma de Onda (Oscilograma) e Envoltória de Hilbert em Zoom Fino",
        target_w=16.8 * cm,
        description="Destaques: [1] Chips de controle de camadas (Sinal Bruto, Envoltória, Min-Max LOD, Pulsos); [2] Ferramentas de Lápis (✎) e Desfazer (↶); [3] Chilreio legítimo de 5 pulsos com marcadores verdes esmeralda."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.3. Motor de Nível de Detalhe Adaptativo (Min-Max LoD Engine)", styles["h2"]))
    story.append(Paragraph(
        "Em gravações extensas (ex.: 60 segundos a 96 kHz = 5,76 milhões de amostras) exibidas em telas comuns (~1.400 pixels úteis), "
        "algoritmos normais usam subamostragem por passo (<i>stride slicing</i>), fazendo com que pulsos estreitos (4 a 15 ms) caiam nos vazios amostrais e desapareçam da tela quando o zoom está afastado. "
        "O motor <b><code>HighPerfLineEngine</code></b> particiona a tela em caixas (<i>buckets</i>) e extrai o valor mínimo real ($y_{\\min}$) e máximo real ($y_{\\max}$) exatos de cada coluna. "
        "<b>Nenhum pulso bioacústico jamais é omitido</b> em qualquer nível de zoom, mantendo resposta interativa a 60 FPS durante o arraste e refinando para 4.000 pontos em repouso.",
        styles["body"]
    ))

    story.append(Paragraph("2.4. Painel 2 — Espectrograma de Curto Tempo (STFT HD)", styles["h2"]))
    story.append(Paragraph(
        "Mapeia a matriz bidimensional de Tempo ($X$, em segundos), Frequência ($Y$, em kHz/Hz) e Potência em decibéis ($Z$, escala cromática Viridis/Magma). "
        "Possui controles analíticos exclusivos na barra <code>specCtrlBar</code>:<br/>"
        "• <b>Escala Y e Unidade:</b> Caixas numéricas de teto e piso e botão de alternância instantânea entre <code>kHz</code> e <code>Hz</code>;<br/>"
        "• <b>Presets Rápidos:</b> Botão <code>10k</code> (enquadra 0 a 10 kHz), <code>Focal</code> (centraliza na banda da portadora $f_c \\pm \\text{tol}$) e <code>Total</code> (expande até a frequência de Nyquist $f_s/2$);<br/>"
        "• <b>Slider Vertical Y:</b> Localizado à esquerda do gráfico, permite comprimir ou estender o teto de frequência em até 50 kHz;<br/>"
        "• <b>Interpolação Parabólica Sub-Bin:</b> Rastreia o pico com precisão submétrica (resolução de $\\pm 2\\text{ a }5\\text{ Hz}$) ajustando uma parábola sobre os bins vizinhos da FFT.",
        styles["body"]
    ))

    p4_img = os.path.join(fig_dir, "ui_print04_spectrogram.png")
    story.append(make_print_card(
        p4_img, 4, "Espectrograma STFT de Alta Definição com Barra de Controles Espectrais",
        target_w=16.8 * cm,
        description="Destaques: [1] Grupo de Presets rápidos (10k, Focal, Total); [2] Ajuste de escala Y e unidade kHz/Hz; [3] Badge da portadora modal (FP: 5.81 kHz) com slider horizontal de tolerância espectral em tempo real."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.5. Painel 3 — Espectro de Potência Média (PSD Welch) e Tolerância da Portadora", styles["h2"]))
    story.append(Paragraph(
        "Calculado via Método dos Periodogramas Modificados de Welch (janela de 4.096 amostras janelada por Hann com 50% de overlap), "
        "este gráfico apresenta a densidade espectral de potência média em $\\text{dB/Hz}$ vs. frequência (0 a Nyquist):<br/>"
        "• <b>Marcador Circular Vermelho:</b> Identifica o ápice da Frequência Portadora ($f_c$), anotando o valor em kHz e magnitude em dB/Hz;<br/>"
        "• <b>Faixa Sombreada de Tolerância (±300 a ±1000 Hz):</b> Faixa vertical sombreada delimitando $[f_c - \\Delta f_{\\text{tol}}, f_c + \\Delta f_{\\text{tol}}]$. "
        "Ao regular o slider ou clicar nos chips rápidos (<code>±300</code>, <code>±500</code>, <code>±700</code>, <code>±1000</code>), qualquer pulso cuja frequência instantânea desvie da janela é reclassificado como ruído em menos de 25 ms sem precisar recalcular a FFT!",
        styles["body"]
    ))

    p5_img = os.path.join(fig_dir, "ui_print05_psd_welch.png")
    p6_img = os.path.join(fig_dir, "ui_print06_hist_bivariado.png")

    t_p5_p6 = Table([
        [make_print_card(p5_img, 5, "PSD de Welch e Portadora Modal", target_w=8.4*cm),
         make_print_card(p6_img, 6, "Histograma Bivariado (twinx)", target_w=8.4*cm)]
    ], colWidths=[8.6*cm, 8.6*cm])
    t_p5_p6.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(t_p5_p6)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("2.6. Painel 4 — Histograma Bivariado de Sintaxe e Duração Média (twinx)", styles["h2"]))
    story.append(Paragraph(
        "Acopla variáveis discretas e contínuas em um gráfico de eixo duplo:<br/>"
        "• <b>Eixo Y1 Primário (Esquerdo - Barras Coloridas):</b> Contagem absoluta de chilreios agrupados pelo número de pulsos por chamado. Revela a <b>Moda Sintática</b> da espécie e diagnostica multimodalidade (dois machos ou frases complexas);<br/>"
        "• <b>Eixo Y2 Secundário (Direito - Linha Vermelha):</b> Duração média do chilreio em milissegundos (ms) para cada classe de pulso. "
        "Em chamados normais governados pelo CPG neuromuscular, a linha vermelha exibe crescimento monotônico quase linear. Quebras bruscas alertam sobre falsos positivos ou fusões indevidas.",
        styles["body"]
    ))

    story.append(Paragraph("2.7. Intervalos IPI, ICI e Diagnóstico de Cadência Rítmica", styles["h2"]))
    story.append(Paragraph(
        "• <b>IPI (Inter-Pulse Interval):</b> Intervalo de silêncio medido do <i>Offset</i> de um pulso ao <i>Onset</i> do pulso seguinte no mesmo chilreio;<br/>"
        "• <b>ICI (Inter-Chirp Interval):</b> Período de repouso neuromuscular medido do <i>Offset</i> do último pulso de um chilreio ao <i>Onset</i> do primeiro pulso do chilreio seguinte;<br/>"
        "• <b>Filtro de Pausas Fisiológicas:</b> Intervalos anômalos que excedam $\\min(2000\\text{ ms}, \\max(2.8 \\times \\text{Mediana}, Q_{75} + 2.5 \\times \\text{IQR}))$ são expurgados do cálculo contínuo de cadência;<br/>"
        "• <b>Regressão Linear e Teste t:</b> Ajusta-se uma reta $y = ax + b$ sobre os ICIs válidos. Se $p < 0.05$ e $slope < -0.15\\text{ ms/s}$, classifica-se como <b>Aceleração Rítmica</b>; se $p < 0.05$ e $slope > +0.15\\text{ ms/s}$, como <b>Desaceleração Rítmica</b>; caso contrário, como <b>Cadência Regular Estável</b>.",
        styles["body"]
    ))

    # Glossário Seção 2
    g2 = {
        "Frequência Portadora (fc)": "Frequência fundamental de ressonância mecânica da harpa tegminal durante o fechamento das asas.",
        "STFT (Short-Time Fourier Transform)": "Transformada que divide o sinal em blocos curtos janelados para revelar o conteúdo espectral em função do tempo.",
        "Decimação Min-Max": "Técnica de amostragem gráfica que calcula o mínimo e máximo reais por coluna de pixel, impedindo a perda visual de pulsos estreitos.",
        "twinx": "Mecanismo gráfico que compartilha o mesmo eixo horizontal (X) vinculando dois eixos verticais (Y1 e Y2) com escalas e unidades distintas.",
        "IPI e ICI Offset-to-Onset": "Medição biométrica estrita que afere o silêncio inter-evento real, descartando a largura do pulso antecedente."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g2, "Seção 2 (Leitura dos Gráficos e Diagnóstico)"))

    # ═════════════════════════════════════════════════════════════
    # SEÇÃO 3: PARAMETRIZAÇÃO FINA
    # ═════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("3.0. Parametrização Fina: Calibração de Cada Controle", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=8))

    story.append(Paragraph("3.1. Diálogo de Parâmetros Básicos (AlgoSettingsDialog)", styles["h2"]))
    story.append(Paragraph(
        "Acessado via <b><code>Configurações → Parâmetros do Algoritmo...</code></b>. Controla as restrições mecânicas fundamentais do agrupamento de chamados: "
        "<code>min_p</code> (mínimo de pulsos por chilreio, padrão = 3), <code>max_p</code> (máximo de pulsos, padrão = 10), <code>amp_min</code> (limiar mínimo de amplitude do envelope, padrão = 0.30) e "
        "<code>gap_min</code> (distância temporal mínima entre pulsos para evitar duplicações, padrão = 25.0 ms).",
        styles["body"]
    ))

    story.append(Paragraph("3.2. Diálogo de Parâmetros Avançados (AdvancedAlgoSettingsDialog)", styles["h2"]))
    story.append(Paragraph(
        "Clicando em <code>⚙️ Configurações Avançadas...</code>, o pesquisador ajusta os filtros DSP e as constantes de segregação de coro: "
        "banda do filtro Butterworth (<code>b1_min = 3200 Hz</code>, <code>b1_max = 6000 Hz</code>), <code>smooth_window_ms = 15.0 ms</code>, <code>prominence = 0.020</code>, "
        "<code>focal_sensitivity = 0.60</code> (sensibilidade GMM para eliminar grilos distantes) e <code>freq_tolerance_hz = 700.0 Hz</code>.",
        styles["body"]
    ))

    p7_img = os.path.join(fig_dir, "ui_print07_algo_settings.png")
    p8_img = os.path.join(fig_dir, "ui_print08_advanced_settings.png")

    t_p7_p8 = Table([
        [make_print_card(p7_img, 7, "Parâmetros Básicos do Algoritmo", target_w=8.4*cm),
         make_print_card(p8_img, 8, "Configurações Avançadas e Filtros", target_w=8.4*cm)]
    ], colWidths=[8.6*cm, 8.6*cm])
    t_p7_p8.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(t_p7_p8)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("3.3. Tabela Comparativa de Parâmetros e Diretrizes de Ajuste", styles["h2"]))
    param_table_data = [
        [Paragraph("<b>Parâmetro</b>", styles["table_header"]), Paragraph("<b>Padrão</b>", styles["table_header"]), Paragraph("<b>Faixa</b>", styles["table_header"]), Paragraph("<b>Unid.</b>", styles["table_header"]), Paragraph("<b>Diretriz de Calibração e Função Físico-Biológica</b>", styles["table_header"])],
        [Paragraph("min_p", styles["table_cell_code"]), Paragraph("3", styles["table_cell_bold"]), Paragraph("1 – 50", styles["table_cell"]), Paragraph("pulsos", styles["table_cell"]), Paragraph("Mínimo de pulsos para validar um chilreio. Bloqueia estalidos isolados e ruídos espúrios. Reduza para 2 em espécies de díades.", styles["table_cell"])],
        [Paragraph("max_p", styles["table_cell_code"]), Paragraph("10", styles["table_cell_bold"]), Paragraph("1 – 100", styles["table_cell"]), Paragraph("pulsos", styles["table_cell"]), Paragraph("Teto superior de pulsos. Impede que ruídos longos fundam dezenas de eventos num falso chilreio. Aumente para 80 em trinados.", styles["table_cell"])],
        [Paragraph("amp_min", styles["table_cell_code"]), Paragraph("0.30", styles["table_cell_bold"]), Paragraph("0.01 – 2.0", styles["table_cell"]), Paragraph("adim.", styles["table_cell"]), Paragraph("Fração da amplitude normalizada máxima (p99.85). Reduza para 0.15 em cantos fracos; suba para 0.45 em gravações com eco.", styles["table_cell"])],
        [Paragraph("gap_min", styles["table_cell_code"]), Paragraph("25.0", styles["table_cell_bold"]), Paragraph("1 – 500", styles["table_cell"]), Paragraph("ms", styles["table_cell"]), Paragraph("Distância mínima entre pulsos consecutivos (período refratário neuromuscular). Picos mais próximos são unificados.", styles["table_cell"])],
        [Paragraph("b1_min", styles["table_cell_code"]), Paragraph("3200", styles["table_cell_bold"]), Paragraph("100 – 24k", styles["table_cell"]), Paragraph("Hz", styles["table_cell"]), Paragraph("Corte inferior do filtro Butterworth passa-faixa. Bloqueia ruídos de tráfego e passos. Ajuste ~1000 Hz abaixo da portadora.", styles["table_cell"])],
        [Paragraph("b1_max", styles["table_cell_code"]), Paragraph("6000", styles["table_cell_bold"]), Paragraph("100 – 24k", styles["table_cell"]), Paragraph("Hz", styles["table_cell"]), Paragraph("Corte superior do filtro passa-faixa. Bloqueia ruídos ultrassônicos e atrito de folhas. Expanda para espécies de alta frequência.", styles["table_cell"])],
        [Paragraph("smooth_window", styles["table_cell_code"]), Paragraph("15.0", styles["table_cell_bold"]), Paragraph("1 – 500", styles["table_cell"]), Paragraph("ms", styles["table_cell"]), Paragraph("Largura do kernel de Hann de suavização da envoltória analítica. Use 5–8 ms em cantos muito rápidos; 20–30 ms em cantos lentos.", styles["table_cell"])],
        [Paragraph("focal_sensitivity", styles["table_cell_code"]), Paragraph("0.60", styles["table_cell_bold"]), Paragraph("0.0 – 1.0", styles["table_cell"]), Paragraph("adim.", styles["table_cell"]), Paragraph("Sensibilidade do GMM bimodal de energia. Suba para 0.85 para isolar com rigor um único macho cantando dentro de coro denso.", styles["table_cell"])],
        [Paragraph("freq_tolerance", styles["table_cell_code"]), Paragraph("700.0", styles["table_cell_bold"]), Paragraph("50 – 2000", styles["table_cell"]), Paragraph("Hz", styles["table_cell"]), Paragraph("Tolerância espectral em torno da portadora ($f_c \\pm \\Delta f$). Exclui cantos simpátricos de outras espécies presentes no mesmo áudio.", styles["table_cell"])],
    ]
    t_params = Table(param_table_data, colWidths=[2.3*cm, 1.2*cm, 1.6*cm, 1.2*cm, 11.1*cm])
    t_params.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (1, 0), (3, -1), 'CENTER'),
    ]))
    story.append(t_params)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("3.4. Cenários Acústicos e Ecológicos Típicos de Campo", styles["h2"]))
    story.append(Paragraph(
        "• <b>Espécies de Alta Frequência / Ultrassom (> 10 kHz):</b> Ajuste <code>b1_min = 9000 Hz</code>, <code>b1_max = 28000 Hz</code> e reduza <code>smooth_window_ms = 5.0 ms</code> para capturar pulsos estreitos;<br/>"
        "• <b>Gravações com Ruído de Riacho ou Vento Constante:</b> Eleve <code>prominence = 0.045</code>, <code>noise_floor = 1.30</code> e restrinja a tolerância de portadora para <code>freq_tolerance_hz = 300 Hz</code>;<br/>"
        "• <b>Coro Polifônico Denso (Vários Machos Concorrentes):</b> Eleve <code>focal_sensitivity = 0.85</code> e <code>amp_min = 0.45</code> para forçar o GMM a selecionar apenas o indivíduo em primeiro plano;<br/>"
        "• <b>Trinados Contínuos (Trills):</b> Eleve <code>max_p = 100</code> e aumente <code>gap_max = 50.0 ms</code>.",
        styles["body"]
    ))

    # Glossário Seção 3
    g3 = {
        "Filtro Butterworth IIR": "Filtro com resposta em frequência maximally flat na banda passante, sem ondulações (ripple). Aplicado em modo bidirecional (fase zero).",
        "Proeminência Relativa": "Altitude vertical mínima que o pico se eleva em relação aos vales laterais mais profundos da curva de energia.",
        "Piso de Ruído Dinâmico": "Estimativa estatística adaptativa da energia de fundo em trechos sem estridulação, utilizada para ponderar o limiar.",
        "Segregação GMM": "Agrupamento estatístico em duas gaussianas (focal vs. coro) que classifica cada pulso pela sua probabilidade de pertencer ao macho primário."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g3, "Seção 3 (Parametrização Fina e Calibração)"))

    # ═════════════════════════════════════════════════════════════
    # SEÇÃO 4: MESA DE EDIÇÃO E APRENDIZADO ATIVO
    # ═════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("4.0. Mesa de Edição Interativa e Aprendizado Ativo (IA / PulseLearner)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284C7"), spaceAfter=8))

    story.append(Paragraph("4.1. Navegação Temporal Sincronizada e AudioTransportPanel", styles["h2"]))
    story.append(Paragraph(
        "• <b>Zoom Horizontal:</b> Roda do mouse (*scroll*) sobre a Forma de Onda ou Espectrograma aplica zoom simétrico em ambos os gráficos, mantendo o ponto sob o ponteiro rigidamente ancorado;<br/>"
        "• <b>Pan / Arraste Fluido (60 FPS):</b> Pressione o <b>Botão Direito do Mouse</b> e arraste horizontalmente para transladar a linha do tempo com limites travados entre $0.0\\text{ s}$ e a duração final;<br/>"
        "• <b>Alinhamento de Reprodução:</b> Um <b>Clique Esquerdo Simples</b> (com o lápis desligado) move a agulha vertical de áudio diretamente para o instante clicado.",
        styles["body"]
    ))

    p13_img = os.path.join(fig_dir, "ui_print13_transport_panel.png")
    story.append(make_print_card(
        p13_img, 13, "Painel Inferior de Transporte e Timeline Interativa",
        target_w=16.8 * cm,
        description="Destaques: [1] Controles multimídia com botão de velocidade (0.25x a 2.0x); [2] Régua da timeline exibindo as bandeiras coloridas de cada chilreio detectado ao longo do áudio."
    ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("4.2. Inspeção Auditiva Desacelerada: Time-Stretch vs. Rebaixamento Heteródino", styles["h2"]))
    story.append(Paragraph(
        "Como os pulsos de Grylloidea sucedem-se a intervalos de 15 a 35 ms, o ouvido humano funde os eventos sonoros (janela de integração de ~50 ms). "
        "Ao definir a taxa de velocidade para <b><code>0.25x</code></b> ou <b><code>0.5x</code></b> no rodapé, o Crinômetro desacelera o áudio em perfeita sincronia com o cursor gráfico. "
        "O pesquisador passa a ouvir distintamente <b>cada impacto mecânico individual dos dentes da lima tegminal</b> (<i>tooth strikes</i>), permitindo auditar acusticamente se um chilreio tem 4, 5 ou 6 pulsos. "
        "Em gravações ultrassônicas (> 20 kHz), a desaceleração atua como rebaixamento espectral heteródino, trazendo a energia do canto para a faixa audível humana (3 a 6 kHz).",
        styles["body"]
    ))

    story.append(Paragraph("4.3. Protocolo de Curadoria Manual de Pulsos (Modo Lápis ✎)", styles["h2"]))
    story.append(Paragraph(
        "1. <b>Ativar Modo de Edição:</b> Clique no ícone de <b>Lápis (<code>✎</code>)</b> no topo do Oscilograma ou Espectrograma. O botão se destaca em azul brilhante;<br/>"
        "2. <b>Remover Falso Positivo (Ruído):</b> Dê um <b>Clique Esquerdo</b> sobre o marcador de pulso indevido. O pulso ganha uma cruz vermelha <b><code>×</code></b> indicando exclusão, e o Crinômetro recalcula instantaneamente os chilreios, médias e histograma;<br/>"
        "3. <b>Adicionar Falso Negativo (Pulso Omitido):</b> Dê um <b>Clique Esquerdo</b> sobre o ápice do pulso na envoltória ou no espectrograma. Se houver um candidato previamente descartado pelo filtro de tolerância em $\\pm 15\\text{ ms}$, o cursor faz <i>snapping magnético</i> no ápice real e resgata seus metadados. Caso contrário, insere um marcador triangular azul <b><code>^</code></b>;<br/>"
        "4. <b>Desfazer Transacional (Undo):</b> Pressione <b><code>Ctrl + Z</code></b> ou clique no botão <b><code>↶</code></b> para reverter as últimas 50 edições de forma atômica.",
        styles["body"]
    ))

    p9_img = os.path.join(fig_dir, "ui_print09_pulse_editor.png")
    p10_img = os.path.join(fig_dir, "ui_print10_ai_params.png")

    t_p9_p10 = Table([
        [make_print_card(p9_img, 9, "Mesa de Edição com Lápis Ativo", target_w=8.4*cm),
         make_print_card(p10_img, 10, "Status e Gestão da IA (.skops)", target_w=8.4*cm)]
    ], colWidths=[8.6*cm, 8.6*cm])
    t_p9_p10.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(t_p9_p10)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("4.4. Tabela Completa de Atalhos de Teclado e Mouse", styles["h2"]))
    shortcuts_data = [
        [Paragraph("<b>Comando / Ação</b>", styles["table_header"]), Paragraph("<b>Atalho / Interação</b>", styles["table_header"]), Paragraph("<b>Comportamento na Interface v4.5.0</b>", styles["table_header"])],
        [Paragraph("Play / Pause Áudio", styles["table_cell_bold"]), Paragraph("Espaço (Barra de Espaço)", styles["table_cell_code"]), Paragraph("Inicia ou pausa a reprodução contínua a partir da posição atual do cursor na timeline.", styles["table_cell"])],
        [Paragraph("Desfazer Edição (Undo)", styles["table_cell_bold"]), Paragraph("Ctrl + Z", styles["table_cell_code"]), Paragraph("Reverte de forma transacional a última adição ou remoção de pulso (até 50 passos).", styles["table_cell"])],
        [Paragraph("Restaurar Painel", styles["table_cell_bold"]), Paragraph("Esc (Escape)", styles["table_cell_code"]), Paragraph("Fecha o gráfico maximizado e restaura a disposição dos mini-painéis na pilha lateral.", styles["table_cell"])],
        [Paragraph("Zoom Sincronizado", styles["table_cell_bold"]), Paragraph("Roda do Mouse (Scroll)", styles["table_cell_code"]), Paragraph("Aplica zoom horizontal mantendo o ponto sob o cursor perfeitamente ancorado no tempo.", styles["table_cell"])],
        [Paragraph("Pan / Arraste Temporal", styles["table_cell_bold"]), Paragraph("Botão Direito + Arrastar", styles["table_cell_code"]), Paragraph("Desloca a janela de visualização em 60 FPS com limites travados entre 0 e a duração total.", styles["table_cell"])],
        [Paragraph("Posicionar Cursor de Áudio", styles["table_cell_bold"]), Paragraph("Clique Esquerdo (Lápis Off)", styles["table_cell_code"]), Paragraph("Move a agulha de reprodução para o instante t exato sem alterar a lista de pulsos.", styles["table_cell"])],
        [Paragraph("Adicionar / Remover Pulso", styles["table_cell_bold"]), Paragraph("Clique Esquerdo (Lápis On ✎)", styles["table_cell_code"]), Paragraph("Alterna estado do pulso sob o cursor (remove pulso existente ou insere novo com snapping).", styles["table_cell"])],
        [Paragraph("Tooltip de Metadados", styles["table_cell_bold"]), Paragraph("Hover do Mouse", styles["table_cell_code"]), Paragraph("Exibe caixa flutuante com tempo, amplitude, frequência e motivo de descarte acústico.", styles["table_cell"])],
    ]
    t_short = Table(shortcuts_data, colWidths=[3.5*cm, 4.2*cm, 9.7*cm])
    t_short.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284C7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
    ]))
    story.append(t_short)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("4.5. Aprendizado Supervisionado: O Botão 'Salvar Correções'", styles["h2"]))
    story.append(Paragraph(
        "Após revisar manualmente alguns chilreios de uma gravação complexa, clique no botão <b><code>Salvar Correções</code></b> (ou <code>Aprender com Correções</code>) no painel esquerdo. "
        "O classificador <code>PulseLearner</code> é acionado em segundo plano via <code>GenericWorker</code> e, em menos de 150 ms, treina novas árvores de decisão. "
        "O rótulo superior atualiza para <b><code>🤖 IA: Ativada (Modelo Supervisionado)</code></b>, aplicando o aprendizado aos demais chilreios do arquivo e do lote.",
        styles["body"]
    ))

    story.append(Paragraph("4.6. Extração das 20 Features, Hard Negative Mining e Serialização Segura .skops", styles["h2"]))
    story.append(Paragraph(
        "O modelo supervisionado opera sobre um vetor de <b>20 descritores físicos invariantes a ganho</b>:<br/>"
        "• <b>Morfologia Temporal:</b> Duração FWHM a -6 dB (<code>peak_width_s</code>), duração a -3 dB, assimetria ataque/decaimento, fator de forma do envelope, curtose temporal, fator de crista, agudeza do ápice e profundidade de vales laterais;<br/>"
        "• <b>Energia & SNR:</b> Relação sinal-ruído local em decibéis ($20 \\log_{10}(A/\\sigma)$), energia normalizada e delta para o piso de ruído;<br/>"
        "• <b>Espectro & Frequência:</b> Desvio da portadora modal ($|f_i - f_c|$), centróide espectral, largura de banda, razão na banda estridulatória e taxa de cruzamento por zero;<br/>"
        "• <b>Contexto Sintático:</b> Distâncias temporal anterior e posterior e coerência com o IPI mediano local.<br/>"
        "<b>Hard Negative Mining:</b> Minera ruídos e estalidos em trechos de silêncio, criando regras rígidas de poda contrastiva com 30% de margem. "
        "Os pesos são serializados de forma criptograficamente segura no arquivo <b><code>modelo_treinado.skops</code></b>, eliminando vulnerabilidades e incompatibilidades dos arquivos <code>.pickle</code> legados.",
        styles["body"]
    ))

    # Glossário Seção 4
    g4 = {
        "FWHM (-6 dB)": "Full Width at Half Maximum. Largura do pulso a 50% da amplitude linear de pico. Métrica morfológica padrão em taxonomia.",
        "Hard Negative Mining": "Técnica que seleciona os ruídos mais difíceis (que mais se assemelham a pulsos verdadeiros) para treinar as fronteiras do classificador.",
        "Tooth Strike": "Impacto mecânico individual de um único dente da lima estridulatória tegminal contra o plectrum.",
        "Skops (.skops)": "Formato seguro de serialização de modelos estatísticos do scikit-learn, auditado contra execução de código malicioso.",
        "Fator de Crista": "Razão entre o valor de pico instantâneo do pulso e seu valor eficaz RMS local, medindo a impulsividade do evento sonoro."
    }
    story.append(Spacer(1, 0.2 * cm))
    story.append(make_glossary_box(g4, "Seção 4 (Mesa de Edição e Aprendizado Ativo)"))

    print("[*] Gravando documento PDF em disco...")
    doc.build(story, canvasmaker=DocCanvas)
    print(f"[OK] Manual em PDF gerado com sucesso: {out_pdf_path}")
    return out_pdf_path


if __name__ == "__main__":
    out_pdf = os.path.join(PROJECT_ROOT, "docs", "Crinometro_Manual_do_Usuario_v4.5.0_Parte1.pdf")
    generate_manual_pdf(out_pdf)
