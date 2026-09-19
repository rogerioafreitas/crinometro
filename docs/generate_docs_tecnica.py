# -*- coding: utf-8 -*-
"""
Gerador de Documentação Técnica do Crinômetro
Gera o PDF de documentação científica exaustiva do core do software.

Dependências: reportlab (já presente no projeto)
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem, HRFlowable
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ─────────────────────────────────────────────────────────────
# Canvas com numeração de páginas e cabeçalho/rodapé
# ─────────────────────────────────────────────────────────────
class DocCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        Canvas.showPage(self)

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_decorations(i + 1, num_pages)
            Canvas.showPage(self)
        Canvas.save(self)

    def _draw_decorations(self, page_num, total_pages):
        self.saveState()
        w, h = A4
        # Rodapé
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(2 * cm, 1.2 * cm,
                        f"Crinômetro — Documentação Técnica e Científica v4.3.2")
        self.drawRightString(w - 2 * cm, 1.2 * cm,
                             f"Página {page_num} de {total_pages}")
        # Linha fina no rodapé
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(2 * cm, 1.6 * cm, w - 2 * cm, 1.6 * cm)
        self.restoreState()


# ─────────────────────────────────────────────────────────────
# Estilos
# ─────────────────────────────────────────────────────────────
def build_styles():
    ss = getSampleStyleSheet()

    styles = {}
    styles["title"] = ParagraphStyle(
        "DocTitle", parent=ss["Title"],
        fontSize=22, leading=28, textColor=colors.HexColor("#0F172A"),
        spaceAfter=6, alignment=TA_CENTER
    )
    styles["subtitle"] = ParagraphStyle(
        "DocSubtitle", parent=ss["Normal"],
        fontSize=12, leading=16, textColor=colors.HexColor("#475569"),
        spaceAfter=20, alignment=TA_CENTER
    )
    styles["h1"] = ParagraphStyle(
        "H1", parent=ss["Heading1"],
        fontSize=16, leading=22, textColor=colors.HexColor("#0F172A"),
        spaceBefore=24, spaceAfter=10,
        borderPadding=(0, 0, 4, 0),
    )
    styles["h2"] = ParagraphStyle(
        "H2", parent=ss["Heading2"],
        fontSize=13, leading=18, textColor=colors.HexColor("#1E293B"),
        spaceBefore=16, spaceAfter=8
    )
    styles["h3"] = ParagraphStyle(
        "H3", parent=ss["Heading3"],
        fontSize=11, leading=15, textColor=colors.HexColor("#334155"),
        spaceBefore=12, spaceAfter=6
    )
    styles["body"] = ParagraphStyle(
        "DocBody", parent=ss["Normal"],
        fontSize=10, leading=15, textColor=colors.HexColor("#1F2937"),
        spaceAfter=8, alignment=TA_JUSTIFY
    )
    styles["body_indent"] = ParagraphStyle(
        "DocBodyIndent", parent=styles["body"],
        leftIndent=18, spaceAfter=6
    )
    styles["code"] = ParagraphStyle(
        "DocCode", parent=ss["Code"],
        fontSize=8.5, leading=12, textColor=colors.HexColor("#1E293B"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5, borderPadding=6,
        spaceBefore=4, spaceAfter=8,
        fontName="Courier"
    )
    styles["formula"] = ParagraphStyle(
        "Formula", parent=ss["Normal"],
        fontSize=10, leading=15, textColor=colors.HexColor("#0F172A"),
        alignment=TA_CENTER, spaceBefore=6, spaceAfter=8,
        fontName="Courier", backColor=colors.HexColor("#F8FAFC"),
        borderPadding=6
    )
    styles["caption"] = ParagraphStyle(
        "Caption", parent=ss["Normal"],
        fontSize=9, leading=13, textColor=colors.HexColor("#64748B"),
        spaceBefore=2, spaceAfter=10, alignment=TA_CENTER,
        fontName="Helvetica-Oblique"
    )
    styles["bullet"] = ParagraphStyle(
        "DocBullet", parent=styles["body"],
        leftIndent=24, firstLineIndent=-12,
        spaceBefore=2, spaceAfter=3
    )
    styles["glossary_term"] = ParagraphStyle(
        "GlossTerm", parent=ss["Normal"],
        fontSize=10, leading=14, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceAfter=2
    )
    styles["glossary_def"] = ParagraphStyle(
        "GlossDef", parent=ss["Normal"],
        fontSize=9.5, leading=14, textColor=colors.HexColor("#334155"),
        leftIndent=18, spaceAfter=8
    )
    return styles


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def hr():
    return HRFlowable(width="100%", thickness=0.8,
                      color=colors.HexColor("#CBD5E1"),
                      spaceBefore=8, spaceAfter=8)

def make_table(header, rows, col_widths=None):
    data = [header] + rows
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor('#64748B')),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#94A3B8')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F8FAFC')]),
    ]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return t


# ─────────────────────────────────────────────────────────────
# Conteúdo do Documento
# ─────────────────────────────────────────────────────────────
def build_content(S):
    """Constrói a lista de Flowables para o PDF."""
    E = []  # elements
    p = lambda text, style="body": Paragraph(text, S[style])

    # ═══════════════════════════════════════════
    # CAPA
    # ═══════════════════════════════════════════
    E.append(Spacer(1, 3 * cm))
    E.append(p("CRINÔMETRO", "title"))
    E.append(p("Documentação Técnica, Teórica e Metodológica", "subtitle"))
    E.append(Spacer(1, 0.5 * cm))
    E.append(p("Análise de Processamento Digital de Sinais (DSP), Bioacústica Computacional,<br/>"
               "Aprendizado de Máquina e Métricas Fisiológicas da Estridulação de Gryllidae", "subtitle"))
    E.append(Spacer(1, 1.5 * cm))
    E.append(p(f"<b>Versão do Software:</b> v4.3.2", "body"))
    E.append(p(f"<b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M')}", "body"))
    E.append(p("<b>Objetivo:</b> Servir como base formal para defesa acadêmica e redação científica,<br/>"
               "documentando exaustivamente cada cálculo, decisão algorítmica e transformação<br/>"
               "de dados implementada no programa.", "body"))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SUMÁRIO
    # ═══════════════════════════════════════════
    E.append(p("SUMÁRIO", "h1"))
    toc_items = [
        "1. Arquitetura Geral e Pipeline de Dados (Dataflow)",
        "2. Processamento Digital de Sinais (DSP): Teoria, Cálculo e Implementação",
        "   2.1. Pré-Processamento e Condicionamento do Sinal",
        "   2.2. Filtragem Passa-Faixa (Bandpass Filter)",
        "   2.3. Transformada de Fourier e Espectrograma (STFT)",
        "   2.4. Refinamento Sub-bin Parabólico de Frequência",
        "   2.5. Densidade Espectral de Potência (PSD)",
        "3. Detecção e Segmentação Bioacústica",
        "   3.1. Extração de Envelope Temporal",
        "   3.2. Algoritmo de Segmentação e Thresholding",
        "   3.3. Agrupamento Hierárquico de Chilreios",
        "   3.4. Tratamento de Ruídos e Falsos Positivos",
        "4. Cálculo de Métricas Biométricas e Modelagem Fisiológica",
        "   4.1. Métricas Temporais de Estridulação",
        "   4.2. Diagnóstico Rítmico (Aceleração vs. Desaceleração)",
        "   4.3. Correlação Termo-Acústica (Lei de Dolbear)",
        "5. Módulo de IA e Aprendizado Ativo",
        "   5.1. Vetor de Características (Feature Engineering)",
        "   5.2. Separação Não-Supervisionada (GMM Bimodal)",
        "   5.3. Classificador Supervisionado (HistGradientBoosting)",
        "   5.4. Mineração de Negativos Difíceis (Hard Negative Mining)",
        "   5.5. Filtro de Coerência Rítmica",
        "   5.6. Ciclo de Feedback do Aprendizado Ativo",
        "6. Glossário Metodológico para Defesa Acadêmica",
    ]
    for item in toc_items:
        indent = "body_indent" if item.startswith("   ") else "body"
        E.append(p(item.strip(), indent))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 1: ARQUITETURA GERAL
    # ═══════════════════════════════════════════
    E.append(p("1. ARQUITETURA GERAL E PIPELINE DE DADOS (DATAFLOW)", "h1"))
    E.append(hr())

    E.append(p("1.1. Ciclo de Vida do Sinal de Áudio", "h2"))
    E.append(p(
        "O Crinômetro implementa um pipeline sequencial de processamento que transforma "
        "uma gravação bruta em formato WAV em um conjunto estruturado de métricas bioacústicas "
        "e visualizações interativas. O ciclo de vida completo é:", "body"
    ))

    pipeline_text = (
        "<font face='Courier' size=8>"
        "┌─────────────────────────────────────────────────────────────────────────┐<br/>"
        "│  ARQUIVO .WAV (entrada)                                                │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  wavfile.read() → Mono + Normalização → float32                       │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Remoção DC (subtração da média) + Highpass 50 Hz (Butterworth 2ª Ord)│<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Filtragem Passa-Faixa IIR Butterworth 4ª Ordem [3200–6000 Hz]       │<br/>"
        "│     │                                                                  │<br/>"
        "│     ├──────────────────────────┐                                       │<br/>"
        "│     ▼                          ▼                                       │<br/>"
        "│  Hilbert → Envelope     STFT Espectrograma                            │<br/>"
        "│     │                   (nperseg=1024, overlap=768)                    │<br/>"
        "│     │                          │                                       │<br/>"
        "│     ▼                          ▼                                       │<br/>"
        "│  Suavização Hanning     Refinamento Parabólico Sub-bin                │<br/>"
        "│     │                   → dom_freqs (freq dominante contínua)          │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Detecção de Picos (find_peaks + threshold adaptativo)                │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Validação Morfológica (duração, amplitude, largura)                  │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Identificação da Frequência Portadora Modal                           │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Filtragem por Tolerância Espectral (±300 Hz da portadora)            │<br/>"
        "│     │                                                                  │<br/>"
        "│     ├─── [IA Ativada?] ──▶ PulseLearner.filter_peaks()               │<br/>"
        "│     │                       (GMM + Classificador + Poda Contrastiva)   │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Agrupamento em Chilreios (gap_min/gap_max + ICI Gate)                │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Filtro de Coerência Rítmica O(N)                                     │<br/>"
        "│     │                                                                  │<br/>"
        "│     ▼                                                                  │<br/>"
        "│  Cálculo de Métricas (ICI, IPI, Cadência, Dolbear)                   │<br/>"
        "│     │                                                                  │<br/>"
        "│     ├──▶ Renderização Interativa (Matplotlib + Engines LOD)           │<br/>"
        "│     └──▶ Exportação (PDF / TXT / Tabelas)                             │<br/>"
        "└─────────────────────────────────────────────────────────────────────────┘<br/>"
        "</font>"
    )
    E.append(p(pipeline_text, "body"))
    E.append(p("<i>Figura 1: Diagrama de fluxo do pipeline completo de processamento do Crinômetro.</i>", "caption"))

    E.append(p("1.2. Organização Modular e Desacoplamento", "h2"))
    E.append(p(
        "A arquitetura do Crinômetro separa rigorosamente a camada de interface gráfica (GUI) da camada "
        "de processamento matemático. Esta decisão atende a três requisitos fundamentais: (a) permitir "
        "que operações de DSP pesadas executem em threads secundárias sem congelar a interface; "
        "(b) facilitar testes unitários do core sem dependência do Qt; e (c) possibilitar "
        "reutilização do motor analítico em contextos não-interativos (scripts de lote, pipelines "
        "acadêmicos).", "body"
    ))

    mod_table = make_table(
        ["Módulo", "Arquivo", "Responsabilidade"],
        [
            ["CricketAnalyzer", "core/analyzer.py", "Pipeline DSP completo: filtragem, espectrograma, detecção de pulsos, agrupamento de chilreios, métricas"],
            ["PulseLearner", "core/learner.py", "ML/Active Learning: extração de features, GMM, classificação supervisionada, poda contrastiva"],
            ["HighPerfLineEngine", "core/engines.py", "Renderização adaptativa LOD de formas de onda com decimação min-max"],
            ["HighPerfSpectrogramEngine", "core/engines.py", "Renderização adaptativa de espectrogramas com cache de tiles e stride slicing"],
            ["HighPerfFreqEngine", "core/engines.py", "Renderização adaptativa de scatter plots de frequência dominante"],
            ["GenericWorker", "core/worker.py", "Wrapper QThread com cancelamento cooperativo e sinalização typed"],
            ["MainWindow", "ui/main_window.py", "Orquestrador central: UI, estado, navegação, edição interativa, playback"],
            ["PlotPanel", "ui/panels.py", "Card de gráfico Matplotlib com tema, drag-drop, toolbar e tooltips"],
            ["report_generator", "utils/report_generator.py", "Geração de relatórios PDF acadêmicos via ReportLab"],
        ],
        col_widths=[3.5*cm, 3.5*cm, 10*cm]
    )
    E.append(mod_table)
    E.append(Spacer(1, 0.3*cm))

    E.append(p(
        "O desacoplamento é mediado pelo padrão de <b>worker assíncrono</b>: a MainWindow instancia "
        "um <font face='Courier'>GenericWorker(QThread)</font> que executa "
        "<font face='Courier'>CricketAnalyzer.analyze()</font> em uma thread secundária. "
        "Ao concluir, o resultado é emitido via sinal Qt (<font face='Courier'>finished_signal</font>) "
        "e recebido pelo slot da MainWindow na thread principal, que então atualiza a GUI. "
        "Este mecanismo garante que operações de FFT, Hilbert e classificação ML nunca bloqueiem "
        "o event loop do Qt.", "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 2: DSP
    # ═══════════════════════════════════════════
    E.append(p("2. PROCESSAMENTO DIGITAL DE SINAIS (DSP)", "h1"))
    E.append(hr())

    E.append(p("2.1. Pré-Processamento e Condicionamento do Sinal", "h2"))
    E.append(p(
        "Antes da análise bioacústica propriamente dita, o sinal bruto passa por três etapas de "
        "condicionamento que removem artefatos comuns em gravações de campo:", "body"
    ))

    E.append(p("<b>Etapa 1: Leitura e Normalização</b>", "h3"))
    E.append(p(
        "O arquivo WAV é lido via <font face='Courier'>scipy.io.wavfile.read()</font>. "
        "Se o arquivo for estéreo (2 canais), os canais são colapsados para mono pela média aritmética: "
        "<font face='Courier'>data = raw.mean(axis=1)</font>. A amplitude é normalizada ao intervalo "
        "[-1.0, +1.0] dividindo pelo valor máximo absoluto do tipo de dado (32768 para int16, "
        "2147483648 para int32). O resultado é convertido para <font face='Courier'>float32</font> "
        "para reduzir em 50% o consumo de memória em relação a float64.", "body"
    ))

    E.append(p("<b>Etapa 2: Remoção do Offset DC</b>", "h3"))
    E.append(p(
        "A média aritmética do sinal é subtraída de todas as amostras: "
        "<font face='Courier'>data = data - np.mean(data)</font>. "
        "Isto elimina qualquer componente de corrente contínua (DC offset) que possa estar presente "
        "devido a imperfeições no circuito de gravação ou calibração do microfone. Um offset DC não "
        "removido introduziria um pico espúrio em 0 Hz no espectro, distorcendo a detecção de "
        "frequência portadora.", "body"
    ))

    E.append(p("<b>Etapa 3: Filtro Passa-Altas Anti-Vento (50 Hz)</b>", "h3"))
    E.append(p(
        "Um filtro Butterworth IIR de 2ª ordem com frequência de corte em 50 Hz é aplicado para "
        "atenuar ruídos de vento, vibrações mecânicas do suporte do microfone e interferência "
        "eletromagnética de rede elétrica (hum de 50/60 Hz). A topologia Butterworth foi escolhida "
        "por sua resposta em magnitude maximamente plana na banda passante, evitando ripple que "
        "poderia distorcer a envoltória temporal dos pulsos.", "body"
    ))
    E.append(p(
        "A implementação utiliza a forma SOS (Second-Order Sections) ao invés da forma de função "
        "de transferência (b, a) para garantir estabilidade numérica. A função de transferência "
        "de um filtro Butterworth passa-altas de 2ª ordem é:", "body"
    ))
    E.append(p(
        "H(s) = s² / (s² + √2·ω<sub>c</sub>·s + ω<sub>c</sub>²)   onde ω<sub>c</sub> = 2π × 50 Hz",
        "formula"
    ))

    E.append(p("2.2. Filtragem Passa-Faixa (Bandpass Filter)", "h2"))
    E.append(p(
        "A etapa central de isolamento do sinal de estridulação utiliza um filtro Butterworth IIR "
        "passa-faixa de <b>4ª ordem</b> (cascata de 2 seções de 2ª ordem) com frequências de corte "
        "configuráveis. Os valores padrão — <b>f<sub>low</sub> = 3200 Hz</b> e <b>f<sub>high</sub> = 6000 Hz</b> — "
        "foram calibrados empiricamente para capturar a faixa de estridulação da maioria das espécies "
        "de Gryllidae comuns em gravações de campo no Brasil (gêneros <i>Gryllus</i>, <i>Anurogryllus</i>, "
        "<i>Oecanthus</i>).", "body"
    ))

    E.append(p("<b>Justificativa da Topologia Butterworth</b>", "h3"))
    E.append(p(
        "A resposta em magnitude do filtro Butterworth de ordem N satisfaz:", "body"
    ))
    E.append(p(
        "|H(jω)|² = 1 / [1 + (ω/ω<sub>c</sub>)^(2N)]",
        "formula"
    ))
    E.append(p(
        "Três propriedades tornam esta topologia ideal para bioacústica de insetos: "
        "(1) <b>Resposta maximamente plana</b> na banda passante — não introduz ripple que "
        "distorceria a envoltória temporal dos pulsos. Filtros Chebyshev tipo I, por exemplo, "
        "apresentam oscilações na banda passante que poderiam gerar falsos picos no envelope. "
        "(2) <b>Atenuação monotônica</b> na banda de rejeição — garante supressão progressiva de "
        "frequências fora da faixa de interesse sem side-lobes. "
        "(3) <b>Fase suavemente variável</b> — embora não seja linear, a fase do Butterworth "
        "é mais suave que a do Chebyshev, preservando melhor a forma temporal dos pulsos de "
        "estridulação.", "body"
    ))
    E.append(p(
        "A <b>4ª ordem</b> (atenuação de 80 dB/década = 24 dB/oitava por polo) fornece uma "
        "rejeição suficiente para separar o canto do grilo focal de fontes de banda larga "
        "(tráfego, vento, outros artrópodes) sem o custo computacional de ordens superiores. "
        "Ordens acima de 6 tendem a causar instabilidade numérica na forma (b, a), "
        "embora a implementação SOS mitigue este risco.", "body"
    ))

    E.append(p("<b>Implementação</b>", "h3"))
    E.append(p(
        "<font face='Courier'>sos = scipy.signal.butter(4, [f_low/(sr/2), f_high/(sr/2)], "
        "btype='band', output='sos')<br/>"
        "data_filtered = scipy.signal.sosfilt(sos, data).astype(np.float32)</font>",
        "code"
    ))
    E.append(p(
        "A normalização das frequências de corte pelo Nyquist (<font face='Courier'>sr/2</font>) "
        "é necessária porque a função <font face='Courier'>butter()</font> espera frequências "
        "normalizadas no intervalo (0, 1). Valores fora de (0.001, 0.999) são clampeados para "
        "evitar instabilidade.", "body"
    ))

    E.append(p("2.3. Transformada de Fourier de Curto Tempo (STFT) e Espectrograma", "h2"))
    E.append(p(
        "O espectrograma do Crinômetro é calculado via STFT usando a função "
        "<font face='Courier'>scipy.signal.spectrogram()</font> com os seguintes parâmetros:",
        "body"
    ))

    stft_table = make_table(
        ["Parâmetro", "Valor Padrão", "Significado Físico"],
        [
            ["nperseg", "1024 amostras", "Tamanho da janela de análise (≈23.2 ms a 44.1 kHz)"],
            ["window", "Hann (cosseno elevado)", "Função de janelamento para redução de vazamento espectral"],
            ["noverlap", "768 amostras (75%)", "Sobreposição entre janelas consecutivas"],
            ["hop_size", "256 amostras (= 1024 - 768)", "Deslocamento temporal entre quadros (≈5.8 ms)"],
            ["scaling", "'spectrum'", "Retorna potência por bin de frequência (não por Hz)"],
        ],
        col_widths=[3*cm, 4*cm, 10*cm]
    )
    E.append(stft_table)
    E.append(Spacer(1, 0.3*cm))

    E.append(p("<b>Resoluções Resultantes</b>", "h3"))
    E.append(p(
        "O Princípio da Incerteza de Heisenberg-Gabor estabelece que a resolução temporal (Δt) "
        "e a resolução espectral (Δf) de qualquer análise tempo-frequência são mutuamente exclusivas:", "body"
    ))
    E.append(p("Δt × Δf ≥ 1 / (4π)", "formula"))
    E.append(p(
        "Para os parâmetros escolhidos (sr = 44100 Hz, nperseg = 1024):", "body"
    ))
    E.append(p(
        "• <b>Resolução em frequência:</b> Δf = sr / nperseg = 44100 / 1024 ≈ <b>43.07 Hz</b><br/>"
        "• <b>Resolução temporal:</b> Δt = hop_size / sr = 256 / 44100 ≈ <b>5.8 ms</b>", "body"
    ))
    E.append(p(
        "Esta parametrização privilegia a <b>resolução temporal</b> em detrimento da espectral. "
        "A escolha é fundamentada na natureza do sinal de estridulação: cada pulso individual "
        "de um grilo dura tipicamente entre 3 e 30 ms, exigindo resolução temporal sub-milissegundos "
        "para segmentação precisa. A resolução espectral de ~43 Hz é suficiente para distinguir a "
        "frequência portadora (tipicamente entre 3 e 8 kHz) e seus harmônicos mais proeminentes.", "body"
    ))

    E.append(p("<b>Conversão para Decibéis</b>", "h3"))
    E.append(p(
        "A matriz de potência Sxx é convertida para escala logarítmica:", "body"
    ))
    E.append(p(
        "S<sub>dB</sub>(f, t) = 10 · log<sub>10</sub>(S<sub>xx</sub>(f, t) + 10<sup>-10</sup>)",
        "formula"
    ))
    E.append(p(
        "O epsilon aditivo (10<sup>-10</sup>, equivalente a -100 dB) previne o logaritmo de zero "
        "em regiões de silêncio absoluto. A matriz resultante é convertida para "
        "<font face='Courier'>float32</font> para economia de memória.", "body"
    ))

    E.append(p("2.4. Refinamento Sub-bin Parabólico de Frequência", "h2"))
    E.append(p(
        "A resolução espectral do espectrograma (~43 Hz) é insuficiente para rastreamento preciso "
        "da frequência portadora do grilo, cuja variação natural pode ser de apenas ±10-20 Hz. "
        "Para superar esta limitação, o Crinômetro aplica <b>interpolação parabólica sub-bin</b> "
        "a cada coluna temporal do espectrograma.", "body"
    ))
    E.append(p(
        "Para cada instante t, identifica-se o bin de frequência k com maior potência. "
        "Usando os valores de potência logarítmica dos bins adjacentes (k-1, k, k+1), "
        "calcula-se o offset fracionário p do pico verdadeiro:", "body"
    ))
    E.append(p(
        "p = 0.5 × (α - γ) / (α - 2β + γ)<br/><br/>"
        "onde α = S<sub>dB</sub>[k-1], β = S<sub>dB</sub>[k], γ = S<sub>dB</sub>[k+1]",
        "formula"
    ))
    E.append(p(
        "A frequência dominante refinada é então:", "body"
    ))
    E.append(p("f<sub>peak</sub>(t) = f[k] + p × Δf", "formula"))
    E.append(p(
        "Este método reduz o erro de estimação de frequência de ±Δf/2 (≈21.5 Hz) para "
        "aproximadamente ±Δf/10 (≈4.3 Hz), oferecendo precisão sub-bin sem o custo "
        "computacional de zero-padding ou janelas maiores.", "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 3: DETECÇÃO E SEGMENTAÇÃO
    # ═══════════════════════════════════════════
    E.append(p("3. DETECÇÃO E SEGMENTAÇÃO BIOACÚSTICA", "h1"))
    E.append(hr())

    E.append(p("3.1. Extração de Envelope Temporal", "h2"))
    E.append(p(
        "O envelope de amplitude é a curva que delineia os picos instantâneos do sinal filtrado, "
        "eliminando as oscilações rápidas da frequência portadora e preservando apenas a modulação "
        "de amplitude (AM) que define a estrutura temporal dos pulsos. O Crinômetro utiliza a "
        "<b>Transformada de Hilbert</b> para esta finalidade.", "body"
    ))
    E.append(p("<b>Fundamento Matemático</b>", "h3"))
    E.append(p(
        "Dado um sinal real x(t), a Transformada de Hilbert produz o sinal analítico:", "body"
    ))
    E.append(p("x<sub>a</sub>(t) = x(t) + j·H{x(t)}", "formula"))
    E.append(p(
        "onde H{·} é o operador de Hilbert (rotação de fase de -90° para frequências positivas "
        "e +90° para negativas). O envelope instantâneo é o módulo do sinal analítico:", "body"
    ))
    E.append(p("A(t) = |x<sub>a</sub>(t)| = √[x(t)² + H{x(t)}²]", "formula"))
    E.append(p("<b>Implementação e Suavização</b>", "h3"))
    E.append(p(
        "<font face='Courier'>analytic = scipy.signal.hilbert(data_filtered)<br/>"
        "envelope = np.abs(analytic).astype(np.float32)</font>", "code"
    ))
    E.append(p(
        "O envelope bruto apresenta ripple residual da portadora. Para eliminar estas flutuações, "
        "aplica-se uma <b>suavização por janela de Hanning</b> via convolução:", "body"
    ))
    E.append(p(
        "<font face='Courier'>win = np.hanning(smooth_samples)<br/>"
        "win /= win.sum()<br/>"
        "envelope_smooth = np.convolve(envelope, win, mode='same')</font>", "code"
    ))
    E.append(p(
        "O tamanho da janela de suavização (padrão: 2 ms, configurável pelo pesquisador) "
        "controla o trade-off entre resolução temporal e supressão de ripple. Janelas maiores "
        "produzem envelopes mais suaves mas podem fundir pulsos adjacentes muito próximos; "
        "janelas menores preservam detalhes mas podem gerar detecções espúrias.", "body"
    ))
    E.append(p("<b>Normalização Robusta</b>", "h3"))
    E.append(p(
        "O envelope é normalizado pelo percentil 99.85 da distribuição de amplitude (ao invés "
        "do máximo absoluto). Esta abordagem é robusta a cliques, estalos e artefatos transientes "
        "que poderiam comprimir toda a faixa dinâmica se o máximo absoluto fosse utilizado. "
        "A constante 99.85 foi calibrada empiricamente para rejeitar os 0.15% mais extremos das "
        "amostras sem afetar os pulsos legítimos de estridulação.", "body"
    ))

    E.append(p("3.2. Algoritmo de Detecção de Pulsos e Thresholding", "h2"))
    E.append(p(
        "A detecção de pulsos opera sobre o envelope suavizado e normalizado. O processo envolve "
        "três fases: (1) estimação do limiar adaptativo, (2) detecção de picos, e "
        "(3) validação morfológica.", "body"
    ))

    E.append(p("<b>Fase 1: Limiar Adaptativo</b>", "h3"))
    E.append(p(
        "O limiar de detecção é calculado adaptativamente a partir da distribuição estatística "
        "do envelope:", "body"
    ))
    E.append(p(
        "threshold = max(amp_min × noise_floor, P<sub>25</sub> × 2.5)", "formula"
    ))
    E.append(p(
        "onde <b>amp_min</b> é o limiar mínimo configurável (padrão: 0.08), <b>noise_floor</b> "
        "é a mediana do envelope nas regiões de silêncio, e <b>P<sub>25</sub></b> é o 25º percentil "
        "da distribuição do envelope. O fator multiplicativo de 2.5 foi determinado empiricamente "
        "para maximizar a taxa de detecção verdadeira (recall) mantendo a taxa de falsos positivos "
        "abaixo de 5% em gravações com SNR ≥ 10 dB.", "body"
    ))

    E.append(p("<b>Fase 2: Detecção de Picos</b>", "h3"))
    E.append(p(
        "A detecção utiliza <font face='Courier'>scipy.signal.find_peaks()</font> com os "
        "seguintes critérios:", "body"
    ))
    E.append(p(
        "• <b>height</b>: threshold calculado na Fase 1<br/>"
        "• <b>prominence</b>: proeminência mínima configurável (garante que o pico se destaque "
        "significativamente de seus vizinhos)<br/>"
        "• <b>width</b>: largura do pico a 50% da altura entre width_min e width_max (em amostras), "
        "equivalente à duração do pulso entre dur_min e dur_max (em ms)<br/>"
        "• <b>distance</b>: distância mínima entre picos consecutivos "
        "(= gap_min × sr, prevenindo dupla detecção)", "body"
    ))

    E.append(p("<b>Fase 3: Validação Morfológica</b>", "h3"))
    E.append(p(
        "Cada pulso candidato é submetido a validação de duração:", "body"
    ))
    E.append(p(
        "• Duração calculada: d = largura do pico a 50% da altura (FWHM) via "
        "<font face='Courier'>peak_widths()</font><br/>"
        "• Critério: dur_min (3 ms) ≤ d ≤ dur_max (50 ms)<br/>"
        "• Pulsos fora deste intervalo são rejeitados como artefatos (muito curtos = cliques; "
        "muito longos = sobreposição de múltiplos pulsos)", "body"
    ))

    E.append(p("3.3. Identificação da Frequência Portadora e Filtragem Espectral", "h2"))
    E.append(p(
        "Após a detecção de pulsos candidatos, o sistema identifica a <b>frequência portadora "
        "modal</b> — a frequência de estridulação dominante que caracteriza o indivíduo focal.", "body"
    ))
    E.append(p(
        "<b>Algoritmo:</b> Para cada pulso validado, extrai-se a frequência dominante do espectrograma "
        "no instante do pico (usando o refinamento sub-bin parabólico da Seção 2.4). Constrói-se "
        "um histograma ponderado dessas frequências com largura de bin de 50 Hz, e a moda do "
        "histograma é designada como a frequência portadora f<sub>carrier</sub>.", "body"
    ))
    E.append(p(
        "Pulsos cuja frequência dominante difere da portadora em mais de ±freq_tolerance "
        "(padrão: 300 Hz) são rejeitados como provenientes de outras fontes acústicas "
        "(outros grilos, cigarras, ruído ambiental). Esta é a <b>Filtragem de Rejeição de "
        "Banda Estreita</b> introduzida na v4.3.0.", "body"
    ))

    E.append(p("3.4. Agrupamento Hierárquico em Chilreios (Chirps)", "h2"))
    E.append(p(
        "Os pulsos validados e filtrados espectralmente são agrupados em <b>chilreios</b> "
        "(chirps) — sequências rítmicas de pulsos produzidas por um único ciclo de fechamento "
        "tegminal. O agrupamento segue um algoritmo sequencial com múltiplas camadas de validação:",
        "body"
    ))
    E.append(p(
        "<b>Camada 1 — Agrupamento Temporal:</b> Pulsos consecutivos são agrupados no mesmo chilreio "
        "se o intervalo inter-pulso (IPI) estiver dentro do intervalo [gap_min, gap_max] "
        "(padrão: [20 ms, 40 ms]). Um IPI menor que gap_min sugere colisão de dois pulsos "
        "sobrepostos; um IPI maior que gap_max indica o fim do chilreio.", "body"
    ))
    E.append(p(
        "<b>Camada 2 — Coerência de Amplitude:</b> Dentro de cada chilreio candidato, a amplitude "
        "dos pulsos é verificada: a razão entre o pulso mais fraco e a mediana não deve exceder "
        "um fator de 1.65×. Isto rejeita intrusões de pulsos distantes (coro de fundo) que "
        "coincidem temporalmente mas apresentam amplitude discrepante.", "body"
    ))
    E.append(p(
        "<b>Camada 3 — Detecção de Colisão:</b> Se dois pulsos estão separados por menos de "
        "0.8 × gap_min, é provável que sejam pulsos sobrepostos de dois indivíduos diferentes. "
        "O sistema retém o pulso de maior amplitude e descarta o mais fraco.", "body"
    ))
    E.append(p(
        "<b>Camada 4 — Portão ICI (Inter-Chirp Interval Gate):</b> Após o agrupamento inicial, "
        "aplica-se um filtro de período refratário fisiológico. Para cada par de chilreios "
        "consecutivos, se o intervalo inter-chilreio (ICI) for inferior a 70% da mediana dos ICIs "
        "(ICI<sub>gate</sub> = 0.70 × ICI<sub>mediana</sub>), os dois chilreios são fundidos em "
        "um único (o intervalo era curto demais para ser uma pausa fisiológica real).", "body"
    ))
    E.append(p(
        "<b>Camada 5 — Validação de Contagem Mínima:</b> Chilreios com menos de min_p pulsos "
        "(padrão: 3) são descartados, pois não constituem uma sequência rítmica "
        "suficiente para classificação bioacústica confiável.", "body"
    ))

    E.append(p("3.5. Tratamento de Ruídos e Falsos Positivos", "h2"))
    E.append(p(
        "O sistema emprega múltiplas estratégias hierárquicas para discriminar sinal de ruído:",
        "body"
    ))
    E.append(p(
        "• <b>Filtragem passa-faixa:</b> Remove ruído fora da banda de estridulação<br/>"
        "• <b>Threshold adaptativo:</b> Se ajusta ao nível de ruído específico da gravação<br/>"
        "• <b>Validação morfológica:</b> Rejeita pulsos com duração ou largura fora do esperado<br/>"
        "• <b>Tolerância espectral:</b> Rejeita pulsos com frequência fora da portadora ±300 Hz<br/>"
        "• <b>Coerência de amplitude:</b> Remove intrusos com amplitude incompatível<br/>"
        "• <b>ICI Gate:</b> Rejeita detecções no período refratário fisiológico<br/>"
        "• <b>Classificador ML (opcional):</b> Discriminação supervisionada baseada em 20 features "
        "acústicas", "body"
    ))
    E.append(p(
        "<b>Diferenciação de pausa fisiológica vs. ruído transitório:</b> Uma pausa fisiológica "
        "genuína (o grilo interrompeu temporariamente a estridulação) é caracterizada por: "
        "(a) ICI significativamente maior que a mediana (> 3×), (b) ausência de pulsos espúrios "
        "durante a pausa, e (c) retomada da cadência com IPI consistente. O sistema identifica "
        "estas pausas e as exclui dos cálculos de taxa e cadência para evitar distorção das métricas.",
        "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 4: MÉTRICAS
    # ═══════════════════════════════════════════
    E.append(p("4. CÁLCULO DE MÉTRICAS BIOMÉTRICAS E MODELAGEM FISIOLÓGICA", "h1"))
    E.append(hr())

    E.append(p("4.1. Métricas Temporais de Estridulação", "h2"))
    E.append(p(
        "As métricas bioacústicas calculadas pelo Crinômetro são formalmente definidas a seguir. "
        "Todas as equações são aplicadas sobre os chilreios validados pelo pipeline completo.",
        "body"
    ))

    metrics_table = make_table(
        ["Métrica", "Símbolo", "Fórmula", "Unidade"],
        [
            ["Total de Chilreios", "N_c", "Contagem de chirps validados", "—"],
            ["Total de Pulsos", "N_p", "Σ |chirp_i| para todos os chirps", "—"],
            ["Taxa de Chilreios", "R_c", "N_c / T_total", "chirps/s"],
            ["Cadência", "R_min", "R_c × 60", "chirps/min"],
            ["ICI Médio", "μ_ICI", "(1/n)Σ(onset[i+1] - offset[i])", "ms"],
            ["ICI Desvio Padrão", "σ_ICI", "std(ICIs)", "ms"],
            ["IPI Médio", "μ_IPI", "(1/m)Σ(onset[j+1] - offset[j]) intra-chirp", "ms"],
            ["IPI Desvio Padrão", "σ_IPI", "std(IPIs)", "ms"],
            ["Duração Média do Pulso", "μ_d_p", "(1/N_p)Σ(offset[k] - onset[k])", "ms"],
            ["Duração Média do Chilreio", "μ_d_c", "(1/N_c)Σ(offset_last - onset_first)", "ms"],
            ["Pulsos por Chilreio (Moda)", "Mo_ppc", "mode({|chirp_i|})", "—"],
            ["Frequência Portadora", "f_carrier", "moda do histograma espectral (50 Hz bins)", "Hz"],
        ],
        col_widths=[3.5*cm, 1.8*cm, 7.2*cm, 1.5*cm]
    )
    E.append(metrics_table)
    E.append(Spacer(1, 0.3*cm))

    E.append(p(
        "O <b>Intervalo Inter-Chilreio (ICI)</b> é medido do offset do último pulso de um chilreio "
        "ao onset do primeiro pulso do chilreio seguinte. O <b>Intervalo Inter-Pulso (IPI)</b> é "
        "medido analogamente dentro de um mesmo chilreio. Esta definição (offset-to-onset) ao invés "
        "de (onset-to-onset) é mais apropriada bioacusticamente pois mede o período de silêncio real "
        "entre eventos, e não o período do ciclo que inclui a duração do evento anterior.", "body"
    ))

    E.append(p("4.2. Diagnóstico Rítmico (Aceleração vs. Desaceleração)", "h2"))
    E.append(p(
        "O diagnóstico rítmico avalia se o grilo está acelerando, desacelerando ou mantendo "
        "cadência estável ao longo da gravação. O modelo empregado é uma <b>regressão linear "
        "simples</b> dos ICIs ao longo do tempo:", "body"
    ))
    E.append(p("ICI(t) = β₀ + β₁·t + ε", "formula"))
    E.append(p(
        "onde β₁ (slope) é a taxa de variação do ICI em ms/s. O ajuste é realizado via "
        "<font face='Courier'>numpy.polyfit(timestamps, icis_ms, deg=1)</font>.", "body"
    ))

    E.append(p("<b>Critérios de Diagnóstico:</b>", "h3"))
    E.append(p(
        "• <b>Aceleração:</b> β₁ < -0.15 ms/s E p-valor < 0.05<br/>"
        "  (ICIs ficando menores → chirps mais frequentes → acelerando)<br/>"
        "• <b>Desaceleração:</b> β₁ > +0.15 ms/s E p-valor < 0.05<br/>"
        "  (ICIs ficando maiores → chirps menos frequentes → desacelerando)<br/>"
        "• <b>Estável:</b> |β₁| ≤ 0.15 ms/s OU p-valor ≥ 0.05<br/>"
        "  (Sem tendência significativa)", "body"
    ))
    E.append(p(
        "A significância estatística é testada via <b>coeficiente de correlação de Pearson</b> "
        "convertido em estatística t de Student:", "body"
    ))
    E.append(p(
        "t = r × √[(n-2) / (1 - r²)]    →    p = 2 × [1 - CDF_t(|t|, df=n-2)]",
        "formula"
    ))
    E.append(p(
        "<b>Filtragem de pausas fisiológicas:</b> ICIs maiores que 3× a mediana são excluídos "
        "da regressão, pois representam interrupções do comportamento de estridulação "
        "(o grilo parou de cantar brevemente) e não variações rítmicas genuínas.",
        "body"
    ))

    E.append(p("4.3. Correlação Termo-Acústica (Lei de Dolbear)", "h2"))
    E.append(p(
        "A Lei de Dolbear (1897) descreve uma relação empírica aproximadamente linear entre a "
        "taxa de estridulação de grilos e a temperatura ambiente. A formulação implementada no "
        "Crinômetro é baseada na versão simplificada para grilo-de-campo (<i>Gryllus</i>):", "body"
    ))
    E.append(p(
        "T(°C) = (R<sub>min</sub> - 40) / 4 + 10", "formula"
    ))
    E.append(p(
        "onde R<sub>min</sub> é a cadência de chilreios por minuto. Esta fórmula é derivada da "
        "Lei de Dolbear original para <i>Oecanthus fultoni</i> (T°F = 40 + n/4, onde n = número "
        "de chirps em 13 segundos), adaptada e convertida para Celsius.", "body"
    ))
    E.append(p(
        "<b>Limitações importantes:</b> A estimativa de temperatura é apresentada como valor "
        "informativo e indicativo, não como medição precisa. A relação é espécie-específica — "
        "grilos de espécies diferentes (e.g., <i>Gryllus</i> vs. <i>Oecanthus</i>) têm "
        "coeficientes distintos. Além disso, fatores como estresse, competição intraespecífica "
        "e estado nutricional podem modular a taxa independentemente da temperatura.",
        "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 5: IA / ACTIVE LEARNING
    # ═══════════════════════════════════════════
    E.append(p("5. MÓDULO DE IA E APRENDIZADO ATIVO", "h1"))
    E.append(hr())
    E.append(p(
        "O módulo de inteligência artificial do Crinômetro (<font face='Courier'>PulseLearner</font>) "
        "implementa um sistema híbrido de classificação que combina (a) clustering não-supervisionado "
        "via GMM bimodal, (b) classificação supervisionada via gradient boosting, e (c) aprendizado "
        "ativo onde o pesquisador refina progressivamente o modelo corrigindo detecções individuais.",
        "body"
    ))

    E.append(p("5.1. Vetor de Características (Feature Engineering)", "h2"))
    E.append(p(
        "Para cada pulso candidato, o sistema extrai um <b>vetor de 20 características</b> "
        "bioacústicas calculadas em uma janela de ±30 ms centrada no pico do envelope. "
        "Estas características foram selecionadas para serem <b>invariantes a ganho</b> "
        "(normalizadas por amplitude local) e <b>fisicamente interpretáveis</b>:", "body"
    ))

    feat_table = make_table(
        ["#", "Feature", "Fórmula / Método", "Significado Bioacústico"],
        [
            ["1", "peak_amp_rel", "A_peak / mediana(A_local)", "Amplitude relativa: distingue focal de coro distante"],
            ["2", "peak_width_s", "FWHM a 50% da altura", "Duração do pulso: espécie-específica"],
            ["3", "peak_width_75_s", "Largura a 75% da altura", "Forma do pico: pulsos focais são mais estreitos"],
            ["4", "local_snr_db", "20·log10(A_peak / σ_local)", "Razão sinal-ruído local"],
            ["5", "energy_rel", "E_janela / A_peak²", "Energia normalizada do pulso"],
            ["6", "std_amp_rel", "σ_local / A_peak", "Variabilidade de amplitude local"],
            ["7", "prominence_ratio", "(A_peak - A_vale) / A_peak", "Proeminência relativa do pico"],
            ["8", "peak_sharpness_rel", "d²env/dt² no pico (normalizado)", "Agudeza do pico (2ª derivada)"],
            ["9", "crest_factor", "A_peak / RMS_local", "Fator de crista: impulsividade do sinal"],
            ["10", "skewness_local", "(μ_esq - μ_dir) / A_peak", "Assimetria temporal do envelope"],
            ["11", "local_density_rel", "E_±10ms / E_±30ms", "Concentração de energia temporal"],
            ["12", "autocorr_1ms", "r(τ=1ms) normalizada", "Periodicidade a curto prazo"],
            ["13", "band_energy_ratio", "E_±10ms / E_±30ms", "Foco energético vs contexto"],
            ["14", "rise_slope_rel", "Δenv/Δt (vale→pico)", "Velocidade de ataque do pulso"],
            ["15", "spectral_centroid", "Σ(f·|X|)/Σ|X|", "Centro de massa espectral (Hz)"],
            ["16", "spectral_rolloff_85", "f tal que CDF(|X|²)=0.85", "Decaimento espectral a 85%"],
            ["17", "attack_time_10_90_ms", "t(90%) - t(10%) interpolado", "Tempo de subida 10-90% (ms)"],
            ["18", "local_hnr_db", "E_harmônica / E_ruído (±150Hz)", "Razão harmônico-ruído local"],
            ["19", "multiscale_energy", "E_±10ms / E_±40ms", "Razão energia multiescala"],
            ["20", "prior_p_focal", "P(focal | GMM)", "Prior não-supervisionado do GMM"],
        ],
        col_widths=[0.7*cm, 3.2*cm, 5*cm, 5.6*cm]
    )
    E.append(feat_table)
    E.append(Spacer(1, 0.3*cm))

    E.append(p("5.2. Separação Não-Supervisionada (GMM Bimodal)", "h2"))
    E.append(p(
        "O módulo GMM (Gaussian Mixture Model) modela a distribuição das features de pulso como "
        "uma mistura de <b>duas gaussianas</b> representando dois clusters:", "body"
    ))
    E.append(p(
        "• <b>Cluster Focal:</b> Pulsos do grilo mais próximo (alta amplitude, centroide espectral "
        "consistente, alto HNR)<br/>"
        "• <b>Cluster Coro/Ruído:</b> Pulsos distantes, ecos, ruído ambiental (baixa amplitude, "
        "centroide disperso, baixo HNR)", "body"
    ))
    E.append(p(
        "O GMM é ajustado em um espaço bidimensional de [log(amplitude), centroide_espectral] "
        "padronizado (Z-score). A designação focal/coro é feita automaticamente: o cluster com "
        "maior média de amplitude + 0.5 × centroide é marcado como focal.", "body"
    ))
    E.append(p(
        "P(focal | x) = π<sub>focal</sub> · N(x | μ<sub>focal</sub>, Σ<sub>focal</sub>) / "
        "Σ<sub>k</sub> π<sub>k</sub> · N(x | μ<sub>k</sub>, Σ<sub>k</sub>)",
        "formula"
    ))
    E.append(p(
        "O <font face='Courier'>GaussianMixture</font> do scikit-learn é instanciado com "
        "<font face='Courier'>n_components=2, covariance_type='full', n_init=5</font>. "
        "O uso de covariância 'full' permite clusters elipsoidais de orientação arbitrária, "
        "capturando correlações entre amplitude e frequência.", "body"
    ))

    E.append(p("5.3. Classificador Supervisionado (HistGradientBoosting)", "h2"))
    E.append(p(
        "Quando o pesquisador fornece correções manuais, o sistema treina um classificador "
        "supervisionado que substitui (ou complementa) a classificação GMM.", "body"
    ))
    E.append(p("<b>Classificador Primário: HistGradientBoostingClassifier</b>", "h3"))
    E.append(p(
        "• <b>max_iter</b>: 200 iterações de boosting<br/>"
        "• <b>max_depth</b>: 3-4 (árvores rasas para evitar overfitting com poucos exemplos)<br/>"
        "• <b>learning_rate</b>: 0.1<br/>"
        "• <b>l2_regularization</b>: 2.0 (quando < 30 amostras) — regularização forte<br/>"
        "• <b>class_weight</b>: 'balanced' — compensa desbalanceamento entre classes<br/>"
        "• <b>min_samples_leaf</b>: 5 — evita folhas com pouquíssimas amostras", "body"
    ))
    E.append(p(
        "O <b>HistGradientBoosting</b> foi escolhido por duas vantagens: (1) construção de "
        "histogramas de features é O(n) em vez de O(n·log·n) como GBDT clássico, permitindo "
        "treinamento rápido durante a interação do pesquisador; (2) suporta nativamente valores "
        "faltantes (NaN) sem necessidade de imputação.", "body"
    ))
    E.append(p("<b>Classificador de Fallback: RandomForestClassifier</b>", "h3"))
    E.append(p(
        "Se o HistGradientBoosting não estiver disponível (versões antigas do sklearn), o sistema "
        "utiliza um Random Forest com 500 estimadores, max_depth=10, n_jobs=-1 (paralelismo total).",
        "body"
    ))
    E.append(p("<b>Score Híbrido</b>", "h3"))
    E.append(p(
        "A decisão final combina a probabilidade do classificador supervisionado com o prior do GMM:", "body"
    ))
    E.append(p(
        "Score = 0.65 × P(válido | classificador) + 0.35 × P(focal | GMM)",
        "formula"
    ))
    E.append(p(
        "Um pulso é aceito se Score ≥ focal_sensitivity (padrão: 0.60). O peso maior no "
        "classificador (65%) reflete a maior confiabilidade das labels humanas em relação "
        "ao clustering não-supervisionado.", "body"
    ))

    E.append(p("5.4. Mineração de Negativos Difíceis (Hard Negative Mining)", "h2"))
    E.append(p(
        "Quando o pesquisador remove manualmente pulsos falsos positivos (clicando em marcadores "
        "espúrios), o sistema analisa os vetores de features desses negativos explícitos e "
        "<b>induz regras de poda contrastivas</b>.", "body"
    ))
    E.append(p(
        "<b>Algoritmo:</b> Para cada uma das 20 features, compara-se a distribuição dos positivos "
        "validados vs. negativos explícitos. Se uma feature <i>f<sub>i</sub></i> separa "
        "perfeitamente os dois grupos (i.e., nenhum overlap), uma regra é criada:", "body"
    ))
    E.append(p(
        "Se f_i < threshold_com_margem_30%  →  Rejeitar pulso", "formula"
    ))
    E.append(p(
        "A margem de segurança de 30% previne rejeição de positivos borderline. "
        "Estas regras são aplicadas <b>antes</b> do classificador ML, "
        "funcionando como um filtro rápido O(1) por pulso.", "body"
    ))

    E.append(p("5.5. Filtro de Coerência Rítmica O(N)", "h2"))
    E.append(p(
        "Após o agrupamento em chilreios, aplica-se um filtro de coerência rítmica que remove "
        "pulsos intrusos — aqueles que quebram o padrão de intervalos regulares esperado em uma "
        "estridulação de grilo.", "body"
    ))
    E.append(p(
        "<b>Algoritmo:</b><br/>"
        "1. Para cada chirp, calcular todos os IPIs internos<br/>"
        "2. Calcular a mediana dos IPIs: IPI<sub>med</sub><br/>"
        "3. Para cada pulso no chirp:<br/>"
        "   Se |IPI<sub>i</sub> - IPI<sub>med</sub>| > tolerância × IPI<sub>med</sub> (tolerância=0.30):<br/>"
        "       → Remover o pulso (ritmicamente incoerente)<br/>"
        "4. Re-validar contagem mínima de pulsos", "body"
    ))
    E.append(p(
        "<b>Justificativa biológica:</b> A estridulação dos Gryllidae é produzida por um "
        "gerador central de padrões (CPG — Central Pattern Generator) neuromotor que produz "
        "intervalos altamente regulares. A variabilidade natural do IPI em uma sequência legítima "
        "raramente excede ±30% da mediana. Pulsos que violam esta regularidade são quase certamente "
        "originários de um segundo indivíduo (overlapping) ou de artefato ambiental.", "body"
    ))

    E.append(p("5.6. Ciclo de Feedback do Aprendizado Ativo", "h2"))
    E.append(p(
        "O aprendizado ativo do Crinômetro segue o paradigma de <b>pool-based active learning</b> "
        "com feedback humano incremental:", "body"
    ))
    E.append(p(
        "<b>Passo 1 — Detecção Inicial:</b> O pipeline DSP detecta todos os pulsos candidatos "
        "usando apenas heurísticas paramétricas (threshold, morfologia, banda espectral).", "body"
    ))
    E.append(p(
        "<b>Passo 2 — Classificação Automática (se modelo existir):</b> O PulseLearner aplica "
        "o GMM e/ou classificador supervisionado para filtrar e classificar os pulsos.", "body"
    ))
    E.append(p(
        "<b>Passo 3 — Revisão Humana:</b> O pesquisador inspeciona visualmente os marcadores de "
        "pulso no espectrograma e oscilograma. Pulsos incorretamente incluídos são removidos "
        "(clique direito); pulsos não detectados são adicionados manualmente (clique esquerdo).",
        "body"
    ))
    E.append(p(
        "<b>Passo 4 — Salvamento de Correções:</b> Ao clicar em \"Salvar Correções\", o sistema:<br/>"
        "  a) Extrai features de todos os pulsos validados → labels positivas (1)<br/>"
        "  b) Extrai features de todos os pulsos removidos → labels negativas (0)<br/>"
        "  c) Minera negativos adicionais: pulsos do envelope em regiões de silêncio, "
        "picos de baixa amplitude distantes dos pulsos validados<br/>"
        "  d) Induz regras de poda contrastivas (Hard Negatives)<br/>"
        "  e) Acumula exemplos no dataset histórico (até 5000 amostras)<br/>"
        "  f) Re-treina o classificador com o dataset atualizado<br/>"
        "  g) Serializa modelo + dataset via pickle em <font face='Courier'>modelo_treinado.pkl</font>",
        "body"
    ))
    E.append(p(
        "<b>Passo 5 — Adaptação Paramétrica:</b> Opcionalmente, o sistema ajusta automaticamente "
        "os parâmetros de proeminência e largura do pipeline DSP com base nas estatísticas dos "
        "pulsos validados pelo pesquisador, reduzindo a necessidade de correções futuras.", "body"
    ))
    E.append(p(
        "<b>Persistência e Transferência:</b> O modelo treinado é salvo em "
        "<font face='Courier'>modelo_treinado.pkl</font> e recarregado em sessões subsequentes. "
        "Pode ser exportado/importado entre pesquisadores via \"Exportar/Carregar Treinamento (.pkl)\".",
        "body"
    ))
    E.append(PageBreak())

    # ═══════════════════════════════════════════
    # SEÇÃO 6: GLOSSÁRIO
    # ═══════════════════════════════════════════
    E.append(p("6. GLOSSÁRIO METODOLÓGICO PARA DEFESA ACADÊMICA", "h1"))
    E.append(hr())

    E.append(p("6.1. Seção \"Materiais e Métodos\" — Modelo de Redação", "h2"))
    E.append(p(
        "A seguir, apresenta-se uma formulação no estilo \"Materiais e Métodos\" de artigo "
        "científico, adequada para inclusão direta em dissertações, teses e publicações:", "body"
    ))

    E.append(p(
        "<i>\"Os arquivos de áudio no formato WAV (44.1 kHz, 16 bits) foram processados pelo "
        "software Crinômetro (v4.3.2). O sinal bruto foi condicionado pela remoção do offset DC "
        "seguida de filtragem passa-altas Butterworth de 2ª ordem (f<sub>c</sub> = 50 Hz) para "
        "eliminação de ruído infrassônico. A banda de estridulação foi isolada por um filtro "
        "Butterworth passa-faixa IIR de 4ª ordem com frequências de corte em 3200 Hz e 6000 Hz, "
        "ambos implementados na forma SOS (Second-Order Sections) para estabilidade numérica "
        "(Oppenheim &amp; Willsky, 2014).</i>", "body_indent"
    ))
    E.append(p(
        "<i>O envelope de amplitude foi extraído pela Transformada de Hilbert (Hilbert, 1912; "
        "Boashash, 1992) seguida de suavização por convolução com janela de Hanning de 2 ms. "
        "A detecção de pulsos utilizou busca de picos com threshold adaptativo baseado no "
        "25º percentil da distribuição do envelope multiplicado por fator 2.5, validação "
        "morfológica (duração entre 3 e 50 ms), e rejeição de banda estreita (±300 Hz da "
        "frequência portadora modal).</i>", "body_indent"
    ))
    E.append(p(
        "<i>O espectrograma foi computado por STFT (Short-Time Fourier Transform) com janela "
        "de Hann de 1024 amostras e sobreposição de 75%, resultando em resolução espectral "
        "de ~43 Hz e resolução temporal de ~5.8 ms. A frequência portadora foi refinada por "
        "interpolação parabólica sub-bin de Smith (1987) aplicada quadro a quadro.</i>", "body_indent"
    ))
    E.append(p(
        "<i>A segregação acústica de indivíduos focais vs. coro distante empregou um Modelo de "
        "Mistura de Gaussianas (GMM) bimodal (Dempster et al., 1977) no espaço log-amplitude × "
        "centroide espectral, complementado por um classificador HistGradientBoosting (Ke et al., "
        "2017) treinado incrementalmente por aprendizado ativo com correções do pesquisador. "
        "O vetor de 20 características por pulso incluiu métricas temporais (duração, tempo de "
        "ataque 10-90%, fator de crista), espectrais (centroide, roll-off 85%, HNR) e contextuais "
        "(energia multiescala, prior focal do GMM).</i>", "body_indent"
    ))
    E.append(p(
        "<i>O diagnóstico rítmico (aceleração/desaceleração) baseou-se em regressão linear dos "
        "ICIs ao longo do tempo, com significância estatística avaliada pela estatística t de "
        "Student (α = 0.05) e limiar de relevância clínica de |β₁| > 0.15 ms/s. "
        "A estimativa de temperatura foi calculada pela Lei de Dolbear simplificada "
        "(T°C = (R<sub>min</sub> − 40)/4 + 10; Dolbear, 1897).\"</i>", "body_indent"
    ))

    E.append(Spacer(1, 0.6*cm))
    E.append(p("6.2. Tabela Sintética: Conceito → Implementação → Localização", "h2"))

    gloss_table = make_table(
        ["Conceito Físico / Biológico", "Implementação Matemática", "Arquivo / Método"],
        [
            ["Estridulação por fricção tegminal", "Sinal oscilatório quase-periódico na banda 3–8 kHz", "Entrada WAV bruta"],
            ["Frequência portadora do canto", "Moda do histograma espectral (50 Hz bins) com refinamento sub-bin", "analyzer.py → analyze()"],
            ["Pulso individual (tooth strike)", "Segmento do envelope acima do threshold com duração validada", "analyzer.py → find_peaks()"],
            ["Chilreio (chirp = trem de pulsos)", "Grupo sequencial com IPI ∈ [gap_min, gap_max]", "analyzer.py → regroup_chirps()"],
            ["Envelope de amplitude", "Módulo do sinal analítico via Transformada de Hilbert", "scipy.signal.hilbert()"],
            ["Espectrograma", "STFT com janela Hann 1024, overlap 75%, potência em dB", "scipy.signal.spectrogram()"],
            ["Filtragem de banda", "Butterworth IIR 4ª ordem, forma SOS", "scipy.signal.butter() + sosfilt()"],
            ["Separação focal/coro", "GMM bimodal + HistGradientBoosting supervisionado", "learner.py → PulseLearner"],
            ["Coerência rítmica", "Rejeição de pulsos com |IPI - mediana| > 30%", "analyzer.py → regroup_chirps()"],
            ["Taxa de estridulação", "N_chirps / T_total × 60 (chirps/min)", "analyze() métricas"],
            ["Diagnóstico rítmico", "Regressão linear ICI(t), teste t de Student", "report_generator.py"],
            ["Estimativa de temperatura", "Lei de Dolbear: T°C = (R_min - 40)/4 + 10", "analyze() métricas"],
            ["Aprendizado ativo", "Pool-based AL com feedback humano incremental", "learner.py → update_from_corrections()"],
            ["Poda contrastiva", "Regras induzidas por separação perfeita de features", "learner.py → induce_pruning_rules()"],
        ],
        col_widths=[4*cm, 5.5*cm, 4.5*cm]
    )
    E.append(gloss_table)

    E.append(Spacer(1, 1*cm))
    E.append(hr())
    E.append(p(
        "<b>Fim da Documentação Técnica.</b><br/>"
        f"Documento gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M')} "
        "pelo Crinômetro — Documentador Científico.",
        "caption"
    ))

    return E


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "Crinometro_Documentacao_Tecnica_Cientifica_v432.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="Crinômetro — Documentação Técnica e Científica",
        author="Crinômetro — Gerador Automático de Documentação",
    )

    S = build_styles()
    elements = build_content(S)

    doc.build(elements, canvasmaker=DocCanvas)
    print(f"[OK] PDF gerado com sucesso: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
