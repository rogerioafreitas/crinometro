# -*- coding: utf-8 -*-
"""
Crinômetro v4.2.0 - Gerador Oficial de Manuais Técnicos e Didáticos em PDF
Gera:
  1. docs/Crinometro_Guia_Pratico_Didatico.pdf
  2. docs/Crinometro_Manual_Tecnico_Cientifico.pdf

Utiliza ReportLab com fontes TrueType nativas do Windows (Segoe UI / Arial)
para suporte tipográfico completo a caracteres acentuados da língua portuguesa.
"""
import os
import sys
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PROJECT_ROOT = r"M:\Documentos\Faculdade\Biologia"
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

# ----------------------------------------------------------------------
# Configuração de Fontes TrueType com Suporte UTF-8 Completo
# ----------------------------------------------------------------------
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

font_candidates = [
    ("SegoeUI", "C:/Windows/Fonts/segoeui.ttf", "SegoeUI-Bold", "C:/Windows/Fonts/segoeuib.ttf"),
    ("Arial", "C:/Windows/Fonts/arial.ttf", "Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"),
]

for name_reg, path_reg, name_bld, path_bld in font_candidates:
    if os.path.exists(path_reg) and os.path.exists(path_bld):
        try:
            pdfmetrics.registerFont(TTFont(name_reg, path_reg))
            pdfmetrics.registerFont(TTFont(name_bld, path_bld))
            FONT_REGULAR = name_reg
            FONT_BOLD = name_bld
            print(f"[+] Fontes registradas com sucesso: {name_reg} / {name_bld}")
            break
        except Exception as e:
            print(f"[!] Falha ao registrar fonte {name_reg}: {e}")

# ----------------------------------------------------------------------
# Paleta Canônica de Cores do Crinômetro
# ----------------------------------------------------------------------
COLOR_PALETTE = [
    (2, "#2563EB", "Azul Royal"),
    (3, "#8B5CF6", "Roxo / Violeta"),
    (4, "#F97316", "Laranja Coral"),
    (5, "#10B981", "Verde Esmeralda"),
    (6, "#EC4899", "Rosa Magenta"),
    (7, "#06B6D4", "Ciano Turquesa"),
    (8, "#EAB308", "Amarelo Ouro"),
    (9, "#6366F1", "Índigo"),
    (10, "#14B8A6", "Teal Menta"),
    ("> 10", "#F43F5E", "Vermelho Rubi (Extra)"),
]

# ----------------------------------------------------------------------
# Canvas com Numeração Dinâmica de Páginas
# ----------------------------------------------------------------------
class NumberedDocCanvas(canvas.Canvas):
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
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages):
        self.saveState()
        self.setFont(FONT_REGULAR, 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Linha de rodapé
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(40, 36, 555, 36)

        # Textos de rodapé
        now_str = datetime.datetime.now().strftime("%d/%m/%Y")
        footer_left = f"Crinômetro v4.2.0 • Bioacústica Computacional • {now_str}"
        footer_right = f"Página {self._pageNumber} de {total_pages}"
        self.drawString(40, 24, footer_left)
        self.drawRightString(555, 24, footer_right)
        self.restoreState()


def get_custom_styles():
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=4,
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=14,
        alignment=0
    )
    
    h1_style = ParagraphStyle(
        "DocH1",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=12.5,
        leading=16.5,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=11,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=10,
        leading=13.5,
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8.8,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5,
        alignment=4 # Justified
    )

    bullet_style = ParagraphStyle(
        "DocBullet",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
        spaceAfter=3
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#FFFFFF")
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "h1": h1_style,
        "h2": h2_style,
        "body": body_style,
        "bullet": bullet_style,
        "cell": table_cell,
        "cell_bold": table_cell_bold,
        "header": table_header
    }


def make_color_table(s):
    cores_data = [
        [
            Paragraph("Cor", s["header"]),
            Paragraph("Pulsos", s["header"]),
            Paragraph("Nome Canônico", s["header"]),
            Paragraph("Cor", s["header"]),
            Paragraph("Pulsos", s["header"]),
            Paragraph("Nome Canônico", s["header"]),
        ]
    ]

    for idx in range(5):
        p1, hex1, nome1 = COLOR_PALETTE[idx]
        p2, hex2, nome2 = COLOR_PALETTE[idx + 5]
        cores_data.append([
            "",
            Paragraph(f"<b>{p1} pulsos</b>", s["cell"]),
            Paragraph(nome1, s["cell"]),
            "",
            Paragraph(f"<b>{p2} pulsos</b>", s["cell"]),
            Paragraph(nome2, s["cell"]),
        ])

    t_cores = Table(cores_data, colWidths=[24, 65, 168, 24, 65, 169])
    style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]

    for idx in range(5):
        row = idx + 1
        _, hex1, _ = COLOR_PALETTE[idx]
        _, hex2, _ = COLOR_PALETTE[idx + 5]
        style_list.append(('BACKGROUND', (0, row), (0, row), colors.HexColor(hex1)))
        style_list.append(('BACKGROUND', (3, row), (3, row), colors.HexColor(hex2)))

    t_cores.setStyle(TableStyle(style_list))
    return t_cores


# ======================================================================
# 1. GERADOR DO GUIA PRÁTICO E DIDÁTICO
# ======================================================================
def build_guia_pratico(output_path):
    print(f"[*] Gerando Guia Prático em: {output_path}...")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=44
    )
    s = get_custom_styles()
    story = []

    # Cabeçalho Principal
    story.append(Paragraph("GUIA PRÁTICO E DIDÁTICO", s["title"]))
    story.append(Paragraph("CRINÔMETRO v4.2.0 — Descubra a Bioacústica dos Grilos sem Complicação!", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=8))

    # Apresentação
    story.append(Paragraph(
        "Bem-vindo ao <b>Crinômetro v4.2.0</b>! Este aplicativo foi desenvolvido especialmente para estudantes, biólogos e "
        "pesquisadores de campo que necessitam analisar a estridulação de insetos de maneira rápida, visual e rigorosamente precisa. "
        "O programa processa arquivos de áudio, reconhece os padrões acústicos de fricção das asas e calcula automaticamente a "
        "frequência do canto, a taxa de chilreios e a quantidade de pulsos por chamado.",
        s["body"]
    ))

    # Seção 1: Como os Grilos Cantam
    story.append(Paragraph("1. Como os Grilos Cantam? A Mecânica da Estridulação", s["h1"]))
    story.append(Paragraph(
        "O canto dos grilos machos (estridulação) ocorre pela fricção rítmica de estruturas especializadas nas asas anteriores "
        "(tegminas): uma fileira de dentes microscópicos (a <i>pérspe</i> ou fileira estridulatória) raspa contra uma crista esclerotizada "
        "(o <i>pécten</i>). Cada passagem do raspador gera um <b>pulso acústico individual</b>. Uma sequência de pulsos emitida em rápida "
        "sucessão constitui um <b>chilreio</b> (ou <i>chirp</i>). Entre um chilreio e outro, ocorre uma pausa de repouso muscular conhecida "
        "como intervalo inter-chilreio (ICI). O Crinômetro identifica e quantifica cada uma dessas frações temporais automaticamente.",
        s["body"]
    ))

    # Seção 2: Passo a Passo em 5 Minutos
    story.append(Paragraph("2. Passo a Passo em 5 Minutos: Do Áudio ao Relatório", s["h1"]))

    passo_data = [
        [
            Paragraph("Etapa", s["header"]),
            Paragraph("Ação Recomendada", s["header"]),
            Paragraph("O que o Crinômetro Faz", s["header"])
        ],
        [
            Paragraph("<b>1. Carregar Áudios</b>", s["cell_bold"]),
            Paragraph("Clique em <b>'Abrir Áudio'</b> ou arraste arquivos <i>.wav</i> diretamente para a lista lateral.", s["cell"]),
            Paragraph("Carrega o sinal sonoro em memória e decodifica a forma de onda em alta fidelidade.", s["cell"])
        ],
        [
            Paragraph("<b>2. Análise Instantânea</b>", s["cell_bold"]),
            Paragraph("O programa executa a filtragem digital e a detecção de picos automaticamente ao selecionar o arquivo.", s["cell"]),
            Paragraph("Gera a envoltória de Hilbert, marca os pulsos com 'X' coloridos e desenha os 4 painéis analíticos.", s["cell"])
        ],
        [
            Paragraph("<b>3. Sincronização (X)</b>", s["cell_bold"]),
            Paragraph("Pressione a tecla <b>X</b> ou clique no botão de sincronização na barra de ferramentas.", s["cell"]),
            Paragraph("Alinha o cursor temporal entre Forma de Onda, Espectrograma e Frequência Dominante simultaneamente.", s["cell"])
        ],
        [
            Paragraph("<b>4. Ajuste & Treino</b>", s["cell_bold"]),
            Paragraph("Use a ferramenta de edição de pulsos e clique em <b>'Aprender com as Correções'</b>.", s["cell"]),
            Paragraph("A inteligência artificial treina com seu feedback (<150ms) e elimina falsos positivos nos próximos áudios.", s["cell"])
        ],
        [
            Paragraph("<b>5. Exportar Dados</b>", s["cell_bold"]),
            Paragraph("Clique em <b>'Exportar Relatório'</b> e selecione o modelo <i>Completo</i> ou <i>Simplificado</i>.", s["cell"]),
            Paragraph("Gera um PDF elegante e diagramado, além de tabelas <i>.txt</i> compatíveis com R, Python e PAST.", s["cell"])
        ],
    ]

    t_passos = Table(passo_data, colWidths=[90, 212, 213])
    t_passos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#FFFFFF")]),
    ]))
    story.append(t_passos)
    story.append(Spacer(1, 8))

    # Seção 3: Paleta Canônica de Cores
    story.append(Paragraph("3. Guia Visual das Cores dos Cantos por Número de Pulsos", s["h1"]))
    story.append(Paragraph(
        "Para facilitar o diagnóstico visual em tempo real, o Crinômetro atribui uma cor padronizada para cada chamado de acordo "
        "com o número de batidas de asa detectadas. A cor é idêntica na forma de onda, nos marcadores 'X', no espectrograma e no histograma:",
        s["body"]
    ))
    story.append(make_color_table(s))
    story.append(Spacer(1, 8))

    # Seção 4: Novidades da Versão 4.2.0
    story.append(Paragraph("4. Novidades e Atualizações da Versão 4.2.0", s["h1"]))
    novidades = [
        ("Sistema de Atualização Automática no Launcher:",
         "O Crinômetro verifica assincronamente na inicialização se há novas versões disponíveis no GitHub Releases, "
         "apresentando as opções 'Atualizar Agora' ou 'Lembrar Mais Tarde'."),
        ("Instalação com Launcher Aberto:",
         "O download exibe uma barra de progresso em tempo real. A instalação dos novos arquivos e bibliotecas ocorre "
         "enquanto o Launcher permanece ativo exibindo 'Instalando arquivos...', transicionando suavemente para "
         "'Reiniciando o programa...' antes de carregar a nova versão."),
        ("Relatório Simplificado Multi-Áudio em PDF:",
         "Consolidação compacta de múltiplos arquivos em páginas contínuas, ideal para publicação e triagem em lote."),
        ("Arraste e Solte Fluido de Painéis:",
         "Reorganize qualquer mini-janela gráfica ou troque-a com o painel central com pré-visualização translúcida fluida.")
    ]
    for titulo, desc in novidades:
        story.append(Paragraph(f"• <b>{titulo}</b> {desc}", s["bullet"]))

    story.append(Spacer(1, 6))

    # Seção 5: Dicas de Gravação
    story.append(Paragraph("5. Dicas de Gravação para Melhores Resultados Bioacústicos", s["h1"]))
    dicas = [
        "<b>Taxa de Amostragem Adequada:</b> Grave sempre a 44.1 kHz ou 48 kHz (16 ou 24 bits) em formato WAV sem compressão.",
        "<b>Distância do Microfone:</b> Posicione o microfone a uma distância entre 30 cm e 1 metro do grilo para capturar harmônicos nítidos.",
        "<b>Registro da Temperatura Ambiente:</b> A taxa de estridulação depende diretamente da temperatura corporal do inseto (Lei de Dolbear). Anote a temperatura em graus Celsius (°C) no início de cada sessão de campo.",
        "<b>Atenuação de Ruído de Fundo:</b> Use protetores de vento na cápsula do microfone e evite proximidade com fontes artificiais de ruído contínuo (geradores, tráfego pesado ou ar-condicionado)."
    ]
    for dica in dicas:
        story.append(Paragraph(f"• {dica}", s["bullet"]))

    doc.build(story, canvasmaker=NumberedDocCanvas)
    print(f"[OK] Guia Prático gerado com sucesso!")


# ======================================================================
# 2. GERADOR DO MANUAL TÉCNICO E ESPECIFICAÇÃO CIENTÍFICA
# ======================================================================
def build_manual_tecnico(output_path):
    print(f"[*] Gerando Manual Técnico em: {output_path}...")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=44
    )
    s = get_custom_styles()
    story = []

    # Cabeçalho Principal
    story.append(Paragraph("MANUAL TÉCNICO E ESPECIFICAÇÃO CIENTÍFICA", s["title"]))
    story.append(Paragraph("CRINÔMETRO v4.2.0 — Processamento Digital de Sinais (DSP) e Aprendizado Ativo em Bioacústica", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=8))

    # Apresentação e Escopo
    story.append(Paragraph("Apresentação e Escopo Científico", s["h1"]))
    story.append(Paragraph(
        "O <b>Crinômetro v4.2.0</b> é uma estação de trabalho computacional concebida para a extração paramétrica, quantificação "
        "reprodutível e análise de alta resolução temporal de bioacústica em insetos (notadamente ordens Orthoptera: Grylloidea e Tettigoniidae). "
        "A ferramenta combina processamento determinístico de sinais com demodulação analítica pela Transformada de Hilbert, filtros "
        "digitais de fase zero e um motor híbrido de aprendizado de máquina supervisionado com realimentação ativa pelo taxonomista. "
        "Esta especificação técnica é o documento formal de referência para a arquitetura algorítmica da versão 4.2.0.",
        s["body"]
    ))

    # Diretriz de Versionamento SemVer
    story.append(Paragraph("Diretriz Estrita de Versionamento Semântico (SemVer: X.Y.Z)", s["h2"]))
    story.append(Paragraph(
        "O desenvolvimento do Crinômetro segue rigorosamente o padrão SemVer adaptado ao escopo acadêmico-científico:<br/>"
        "• <b>Major (X):</b> Grandes saltos estruturais, alterações profundas de pipeline ou reestruturação conceitual completa "
        "(ex: introdução da segregação acústica focal vs. coro distante na série v4.0.0). Requer branch dedicada e validação.<br/>"
        "• <b>Minor (Y):</b> Inclusão de novas ferramentas funcionais, enriquecimento algorítmico ou alterações na interface "
        "que demandem atualização formal neste manual técnico em PDF (ex: v4.1.2 ➜ v4.2.0 com sistema de atualização integrada).<br/>"
        "• <b>Patch (Z):</b> Correções pontuais de bugs internos, pequenos ajustes visuais ou estabilizações de código que "
        "não modificam as especificações matemáticas descritas neste manual.",
        s["body"]
    ))

    # 1. Arquitetura de DSP
    story.append(Paragraph("1. Arquitetura da Cadeia de Processamento Digital de Sinais (DSP)", s["h1"]))
    story.append(Paragraph(
        "A cadeia de sinal opera em taxa de amostragem nativa (fs até 192 kHz) com precisão de ponto flutuante de 64 bits (float64):",
        s["body"]
    ))
    dsp_steps = [
        ("Filtro Butterworth IIR Passa-Faixa de Fase Zero:",
         "Implementado via <code>scipy.signal.sosfiltfilt</code> (Seções de Segunda Ordem, 4ª ordem) para eliminar artefatos "
         "de fase e preservar com precisão micrométrica os instantes de subida e descida dos pulsos estridulatórios na banda de interesse (3,2 kHz a 6,0 kHz)."),
        ("Demodulação Analítica por Transformada de Hilbert:",
         "Cálculo do sinal analítico complexo z(t) = s(t) + j·H{s(t)}, derivando a envoltória instantânea de amplitude A(t) = |z(t)|, "
         "isenta de ondulações de alta frequência da portadora acústica."),
        ("Convolução Hanning & SNR Adaptativo:",
         "Suavização por janela de Hanning (15 ms) combinada ao rastreamento estocástico do piso de ruído ambiental (noise floor), "
         "estabelecendo limiar adaptativo de detecção de eventos."),
        ("Segmentação Topológica de Picos e Fusão Inter-Chilreio (ICI):",
         "Extração de picos de amplitude baseada em proeminência relativa e fusão de pulsos adjacentes com separação temporal "
         "menor que o critério fisiológico de gap (25 ms a 35 ms) para consolidação em chilreios completos.")
    ]
    for tit, desc in dsp_steps:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    story.append(Spacer(1, 6))

    # 2. Machine Learning e Plasticidade
    story.append(Paragraph("2. Motor de Machine Learning & Plasticidade Ativa (PulseLearner)", s["h1"]))
    story.append(Paragraph(
        "O motor de classificação supervisionada opera com base em <b>HistGradientBoostingClassifier</b> (com fallback dinâmico "
        "para Random Forest de 300 árvores), combinando velocidade de inferência ultrarrápida (<150 ms) com alta capacidade discriminativa:",
        s["body"]
    ))
    ml_features = [
        ("Conjunto de 14 Descritores Físicos Invariantes:",
         "Para cada candidato a pulso, são calculados atributos físicos incluindo largura de pico a meia altura (FWHM), "
         "proeminência relativa, densidade espectral local, energia RMS normalizada, assimetria de crista (skewness), "
         "tempo de subida 10%-90% (attack time), centroide espectral e razão harmônico-ruído (HNR)."),
        ("Aprendizado Contrastivo Baseado em Regras (Hard Negative Rule Induction):",
         "Ao remover um falso pulso na interface, o sistema induz automaticamente regras rígidas de poda com margem de "
         "segurança de 30% em torno dos descritores do falso positivo, garantindo imunidade imediata a ruídos semelhantes."),
        ("Filtro Rítmico Fisiológico Inter-Chilreio (ICI Gate):",
         "O algoritmo monitora a distribuição temporal dos chilreios. Detecções espúrias que ocorram dentro do período "
         "refratário fisiológico (Δt < 0.70 × ICI_mediano) são suprimidas preventivamente."),
        ("Segregação Bimodal Focal vs. Coro Distante (GMM):",
         "Mistura de Gaussianas bimodal que modela a distribuição de energia espectral para calcular o prior contínuo P(focal), "
         "segregando com precisão o espécime em primeiro plano dos cantos de fundo e ecos distantes.")
    ]
    for tit, desc in ml_features:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    story.append(Spacer(1, 6))

    # 3. Parametrização Fisiológica
    story.append(Paragraph("3. Parametrização Fisiológica e Acústica Padrão", s["h1"]))
    story.append(Paragraph(
        "A tabela abaixo resume os parâmetros padrão configurados no núcleo algorítmico do Crinômetro v4.2.0:",
        s["body"]
    ))

    param_data = [
        [
            Paragraph("Parâmetro", s["header"]),
            Paragraph("Valor Padrão", s["header"]),
            Paragraph("Significado Fisiológico / Acústico", s["header"])
        ],
        [Paragraph("min_p / max_p", s["cell_bold"]), Paragraph("3 a 10 pulsos", s["cell"]), Paragraph("Faixa esperada de pulsos por chamado estridulatório da espécie.", s["cell"])],
        [Paragraph("amp_min / amp_max", s["cell_bold"]), Paragraph("0.08 a 1.00", s["cell"]), Paragraph("Limiares normalizados de amplitude para rejeição de ruído de fundo.", s["cell"])],
        [Paragraph("dur_min / dur_max", s["cell_bold"]), Paragraph("14.0 a 80.0 ms", s["cell"]), Paragraph("Limites temporais fisiológicos de duração de um pulso individual.", s["cell"])],
        [Paragraph("gap_min / gap_max", s["cell_bold"]), Paragraph("25.0 a 35.0 ms", s["cell"]), Paragraph("Critério de silêncio para quebra e delimitação entre chamados adjacentes.", s["cell"])],
        [Paragraph("b1_min / b1_max", s["cell_bold"]), Paragraph("3200 a 6000 Hz", s["cell"]), Paragraph("Faixa de frequência fundamental típica de estridulação em Grylloidea.", s["cell"])],
        [Paragraph("prominence", s["cell_bold"]), Paragraph("0.02", s["cell"]), Paragraph("Proeminência topológica mínima para distinção entre pulso e ondulação.", s["cell"])],
        [Paragraph("focal_sensitivity", s["cell_bold"]), Paragraph("0.60", s["cell"]), Paragraph("Sensibilidade do corte de segregação focal via Mistura de Gaussianas (GMM).", s["cell"])],
    ]

    t_params = Table(param_data, colWidths=[105, 80, 330])
    t_params.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#FFFFFF")]),
    ]))
    story.append(t_params)
    story.append(Spacer(1, 8))

    # 4. Paleta Canônica de 10 Cores
    story.append(Paragraph("4. Paleta Canônica de Cores por Classe de Chilreio", s["h1"]))
    story.append(Paragraph(
        "A correspondência cromática estrita garante identificação visual unívoca nos gráficos de Forma de Onda, "
        "Frequência Dominante, Espectrograma e Histograma de Chilreios:",
        s["body"]
    ))
    story.append(make_color_table(s))
    story.append(Spacer(1, 8))

    # 5. Sistema de Atualização Automática e Arquitetura Inno Setup
    story.append(Paragraph("5. Sistema de Atualização Automática e Arquitetura Inno Setup", s["h1"]))
    story.append(Paragraph(
        "A versão 4.2.0 introduz o subsistema de atualização automática transparente com instalação em segundo plano:<br/>"
        "• <b>Comunicação com GitHub Releases:</b> O Launcher consulta a API oficial do GitHub em thread secundária protegida "
        "(<code>CoreLoaderThread</code>), checando se há versão mais recente disponível.<br/>"
        "• <b>Fluxo Transparente no Launcher:</b> O usuário decide se deseja atualizar ou prosseguir. Ao confirmar, o download "
        "executa em fluxo contínuo com barra de progresso horizontal moderna.<br/>"
        "• <b>Substituição Atômica com Inno Setup:</b> O instalador Inno Setup é acionado silenciosamente em segundo plano "
        "(<code>/SP- /SILENT /SUPPRESSMSGBOXES</code>) enquanto o Launcher exibe <i>'Instalando arquivos...'</i>. Com as diretivas "
        "<code>restartreplace uninsrestartdelete</code>, todas as bibliotecas e arquivos complementares são substituídos em disco. "
        "Ao transicionar para <i>'Reiniciando o programa...'</i>, o Launcher fecha-se suavemente para que o instalador substitua o "
        "executável principal liberado e inicialize o Crinômetro v4.2.0 atualizado.",
        s["body"]
    ))

    # 6. Protocolo Metodológico de Exportação
    story.append(Paragraph("6. Protocolo de Exportação Tabular e Relatórios Técnicos", s["h1"]))
    story.append(Paragraph(
        "O Crinômetro consolida os resultados analíticos em dois formatos complementares:<br/>"
        "1. <b>Relatórios em PDF de Alta Qualidade:</b> Renderizados via ReportLab com diagramação acadêmica, gráficos "
        "incorporados, diagnóstico de cadência rítmica por regressão linear do ICI e tabelas paginadas de chilreios.<br/>"
        "2. <b>Exportação Tabular Estruturada (.txt / .csv):</b> Matrizes de dados com timestamps exatos de início e fim "
        "de cada pulso, intervalo inter-chilreio, frequência dominante e energia RMS, prontas para importação direta em "
        "ambientes estatísticos como R, Python (pandas/scipy), PAST e JASP.",
        s["body"]
    ))

    doc.build(story, canvasmaker=NumberedDocCanvas)
    print(f"[OK] Manual Técnico gerado com sucesso!")


def main():
    guia_path = os.path.join(DOCS_DIR, "Crinometro_Guia_Pratico_Didatico.pdf")
    manual_path = os.path.join(DOCS_DIR, "Crinometro_Manual_Tecnico_Cientifico.pdf")
    build_guia_pratico(guia_path)
    build_manual_tecnico(manual_path)
    print("=" * 60)
    print("[OK] TODOS OS MANUAIS FORAM GERADOS COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    main()
