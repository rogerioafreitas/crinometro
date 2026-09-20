# -*- coding: utf-8 -*-
"""
Crinômetro v4.4.1 - Gerador Oficial de Manuais Técnicos e Didáticos em PDF
Gera:
  1. docs/Crinometro_Guia_Pratico_Didatico.pdf
  2. docs/Crinometro_Manual_Tecnico_Cientifico.pdf

Utiliza ReportLab com fontes TrueType nativas do Windows (Segoe UI / Arial),
paleta canônica de cores com amostras visuais e inserção de figuras reais
do sinal acústico em alta resolução (300 DPI).
"""

import os
import sys
import datetime
from PIL import Image as PILImage

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def _find_project_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d and os.path.dirname(d) != d:
        if os.path.exists(os.path.join(d, "core", "analyzer.py")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PROJECT_ROOT = _find_project_root()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
FIG_DIR = os.path.join(DOCS_DIR, "figures")
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

APP_VERSION = "4.4.1"

# ----------------------------------------------------------------------
# Configuração de Fontes TrueType com Suporte UTF-8 Completo
# ----------------------------------------------------------------------
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

font_candidates = [
    ("SegoeUI", "C:/Windows/Fonts/segoeui.ttf", "SegoeUI-Bold", "C:/Windows/Fonts/segoeuib.ttf", "SegoeUI-Italic", "C:/Windows/Fonts/segoeuii.ttf"),
    ("Arial", "C:/Windows/Fonts/arial.ttf", "Arial-Bold", "C:/Windows/Fonts/arialbd.ttf", "Arial-Italic", "C:/Windows/Fonts/ariali.ttf"),
]

for item in font_candidates:
    name_reg, path_reg, name_bld, path_bld, name_ita, path_ita = item
    if os.path.exists(path_reg) and os.path.exists(path_bld):
        try:
            pdfmetrics.registerFont(TTFont(name_reg, path_reg))
            pdfmetrics.registerFont(TTFont(name_bld, path_bld))
            if os.path.exists(path_ita):
                pdfmetrics.registerFont(TTFont(name_ita, path_ita))
                FONT_ITALIC = name_ita
            FONT_REGULAR = name_reg
            FONT_BOLD = name_bld
            break
        except Exception:
            pass

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
# Canvas com Numeração Dinâmica de Páginas e Rodapé
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
        footer_left = f"Crinômetro v{APP_VERSION} • Bioacústica Computacional & DSP • {now_str}"
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
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=3,
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=9.8,
        leading=13.5,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=8,
        alignment=0
    )
    
    h1_style = ParagraphStyle(
        "DocH1",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=11,
        leading=14.5,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=8,
        spaceAfter=3.5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=9.2,
        leading=12.5,
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=5,
        spaceAfter=2.5,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=3.5,
        alignment=4 # Justified
    )

    bullet_style = ParagraphStyle(
        "DocBullet",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=8.0,
        leading=11.2,
        textColor=colors.HexColor("#334155"),
        leftIndent=9,
        spaceAfter=2
    )

    caption_style = ParagraphStyle(
        "DocCaption",
        parent=styles["Normal"],
        fontName=FONT_ITALIC,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1, # Centered
        spaceAfter=4
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=7.6,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=7.6,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=8.0,
        leading=10.5,
        textColor=colors.HexColor("#FFFFFF")
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "h1": h1_style,
        "h2": h2_style,
        "body": body_style,
        "bullet": bullet_style,
        "caption": caption_style,
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
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]

    for idx in range(5):
        row = idx + 1
        _, hex1, _ = COLOR_PALETTE[idx]
        _, hex2, _ = COLOR_PALETTE[idx + 5]
        style_list.append(('BACKGROUND', (0, row), (0, row), colors.HexColor(hex1)))
        style_list.append(('BACKGROUND', (3, row), (3, row), colors.HexColor(hex2)))

    t_cores.setStyle(TableStyle(style_list))
    return t_cores


def make_captioned_image(img_path, caption_text, s, target_width=475):
    """Cria elemento visual com imagem ajustada à largura útil e legenda explicativa."""
    if not os.path.exists(img_path):
        return Spacer(1, 1)
    try:
        with PILImage.open(img_path) as im:
            orig_w, orig_h = im.size
        aspect = orig_h / orig_w
        target_height = target_width * aspect
        img = Image(img_path, width=target_width, height=target_height)
        img.hAlign = 'CENTER'
        cap = Paragraph(f"<b>Figura:</b> {caption_text}", s["caption"])
        return KeepTogether([img, Spacer(1, 2), cap, Spacer(1, 4)])
    except Exception as e:
        print(f"[!] Erro ao inserir imagem {img_path}: {e}")
        return Spacer(1, 1)


def make_side_by_side_images(img1_path, cap1_text, img2_path, cap2_text, s, target_width=234):
    """Cria tabela com duas imagens lado a lado com legendas individuais."""
    has1 = os.path.exists(img1_path)
    has2 = os.path.exists(img2_path)
    if not has1 or not has2:
        return Spacer(1, 1)
    
    with PILImage.open(img1_path) as im1:
        w1, h1 = im1.size
    with PILImage.open(img2_path) as im2:
        w2, h2 = im2.size
    
    h_target1 = target_width * (h1 / w1)
    h_target2 = target_width * (h2 / w2)
    
    im_obj1 = Image(img1_path, width=target_width, height=h_target1)
    im_obj2 = Image(img2_path, width=target_width, height=h_target2)
    
    cap_obj1 = Paragraph(f"<b>Figura A:</b> {cap1_text}", s["caption"])
    cap_obj2 = Paragraph(f"<b>Figura B:</b> {cap2_text}", s["caption"])
    
    table_data = [
        [im_obj1, im_obj2],
        [cap_obj1, cap_obj2]
    ]
    t = Table(table_data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return KeepTogether([t, Spacer(1, 4)])


# ======================================================================
# 1. GERADOR DO GUIA PRÁTICO E DIDÁTICO (v4.4.1)
# ======================================================================
def build_guia_pratico(output_path):
    print(f"[*] Gerando Guia Prático em: {output_path}...")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=32,
        bottomMargin=40
    )
    s = get_custom_styles()
    story = []

    fig_dash = os.path.join(FIG_DIR, "fig1_dashboard_m017.png")
    fig_wave = os.path.join(FIG_DIR, "fig2_waveform_lod_m017.png")
    fig_spec = os.path.join(FIG_DIR, "fig3_spectrogram_hd_m017.png")
    fig_psd = os.path.join(FIG_DIR, "fig4_psd_welch_m017.png")
    fig_hist = os.path.join(FIG_DIR, "fig5_hist_bivariado_m017.png")

    # ==================== PÁGINA 1 ====================
    story.append(Paragraph("GUIA PRÁTICO E DIDÁTICO", s["title"]))
    story.append(Paragraph(f"CRINÔMETRO v{APP_VERSION} — Descubra a Bioacústica dos Grilos com Precisão e Facilidade!", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=6))

    story.append(Paragraph(
        f"Bem-vindo ao <b>Crinômetro v{APP_VERSION}</b>! Desenvolvido para biólogos, entomólogos, estudantes e pesquisadores de campo, "
        "o Crinômetro é uma estação integrada para identificação rápida, quantificação física e análise bioacústica de cantos de grilos "
        "(Orthoptera: Grylloidea). O programa combina processamento digital determinístico de sinais com filtros de fase zero, demodulação de "
        "Hilbert e inteligência artificial supervisionada com aprendizado ativo, tudo empacotado em uma interface visual fluida e intuitiva.",
        s["body"]
    ))

    story.append(Paragraph("1. Como os Grilos Cantam? A Bioacústica da Estridulação", s["h1"]))
    story.append(Paragraph(
        "O canto dos grilos machos (estridulação) ocorre pela fricção rítmica das asas anteriores (tegminas): uma fileira de dentes microscópicos "
        "(a <i>fileira estridulatória</i> ou <i>pérspe</i>) raspa contra uma lâmina endurecida (o <i>pécten</i>). Cada impacto isolado gera um "
        "<b>pulso acústico</b> (batida de asa). A sequência de pulsos emitida em rápida sucessão forma um <b>chilreio</b> (ou <i>chirp</i>). "
        "Entre chilreios, ocorre uma pausa muscular de relaxamento denominada <b>Intervalo Inter-Chilreio (ICI)</b>. Como os grilos são "
        "animais ectotérmicos, sua taxa de estridulação varia com a temperatura ambiente segundo a famosa <b>Lei de Dolbear</b> "
        "(<i>T(°C) = (Chilreios/min - 40)/4 + 10</i>), transformando o animal em um termômetro natural!",
        s["body"]
    ))

    story.append(Paragraph("2. A Interface em 4 Painéis Sincronizados", s["h1"]))
    story.append(Paragraph(
        "Ao carregar um áudio, o Crinômetro analisa o sinal e organiza a visualização em quatro perspectivas interconectadas:",
        s["body"]
    ))

    if os.path.exists(fig_dash):
        story.append(make_captioned_image(
            fig_dash,
            f"Visão geral da interface do Crinômetro v{APP_VERSION} com o áudio analítico <i>m017_0376.wav</i>: Forma de Onda (superior esq.), "
            "Histograma Bivariado twinx (superior dir.), Densidade Espectral PSD Welch (inferior esq.) e Espectrograma HD (inferior dir.).",
            s, target_width=475
        ))

    paineis_info = [
        ("Painel 1 — Forma de Onda & Envoltória (Superior Esquerdo):",
         "Onda sonora filtrada e envoltória contínua pela Transformada de Hilbert. Pulsos identificados recebem marcadores 'X' com cor codificada por pulsos/chamado."),
        ("Painel 2 — Histograma Bivariado [twinx] (Superior Direito):",
         "<b>Inovação v4.4.x:</b> Contagem de chilreios no eixo Y primário (barras) e linha de duração média em milissegundos (ms) no eixo secundário (twinx)."),
        ("Painel 3 — Densidade Espectral de Potência [PSD Welch] (Inferior Esquerdo):",
         "<b>Inovação v4.4.x:</b> Assinatura contínua de energia (dB/Hz) via método de Welch (4096 amostras), foco biológico de 0 a 15 kHz e portadora destacada."),
        ("Painel 4 — Espectrograma STFT Multirresolução (Inferior Direito):",
         "Mapa tempo-frequência em dB com presets de navegação 'Total' e 'Focal' e limites inteligentes de pan e zoom que previnem áreas vazias.")
    ]
    for tit, desc in paineis_info:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    # Quebra explícita para a Página 2
    story.append(PageBreak())

    # ==================== PÁGINA 2 ====================
    story.append(Paragraph("3. Passo a Passo em 5 Minutos: Do Áudio ao Relatório Científico", s["h1"]))

    passo_data = [
        [
            Paragraph("Etapa", s["header"]),
            Paragraph("Ação do Usuário", s["header"]),
            Paragraph("O que o Crinômetro v4.4.1 Faz", s["header"])
        ],
        [
            Paragraph("<b>1. Carregar Áudios</b>", s["cell_bold"]),
            Paragraph("Clique em <b>'Abrir Áudio'</b> ou arraste múltiplos arquivos <i>.wav</i> para a lista lateral.", s["cell"]),
            Paragraph("Decodifica os arquivos em alta resolução com economia de 50% de RAM em <code>float32</code>.", s["cell"])
        ],
        [
            Paragraph("<b>2. Análise & Modo DSP</b>", s["cell_bold"]),
            Paragraph("A análise é imediata ao selecionar o arquivo. O software inicia no <b>Modo DSP puro</b> nativo.", s["cell"]),
            Paragraph("Executa filtros de fase zero, envoltória de Hilbert e agrupamento fisiológico com mínimo de 3 pulsos.", s["cell"])
        ],
        [
            Paragraph("<b>3. Sincronizar (X)</b>", s["cell_bold"]),
            Paragraph("Pressione a tecla <b>X</b> ou clique no botão <b>⇋ Sync</b> no cabeçalho.", s["cell"]),
            Paragraph("Alinha perfeitamente a linha temporal do cursor entre a Forma de Onda e o Espectrograma.", s["cell"])
        ],
        [
            Paragraph("<b>4. Abortar se Necessário</b>", s["cell_bold"]),
            Paragraph("Clique no botão <b>'✕ Abortar'</b> visível dinamicamente durante processamentos pesados.", s["cell"]),
            Paragraph("Interrompe de forma cooperativa e multithread a análise individual ou em lote sem travar a interface.", s["cell"])
        ],
        [
            Paragraph("<b>5. Auditoria & Reset</b>", s["cell_bold"]),
            Paragraph("Ajuste pulsos com a ferramenta de lápis. Se desejar restaurar o estado base, clique em <b>'Resetar IA'</b>.", s["cell"]),
            Paragraph("O sistema aprende correções ativas ou limpa o cache de persistência para reiniciar do zero sem resíduos.", s["cell"])
        ],
        [
            Paragraph("<b>6. Exportar Resultados</b>", s["cell_bold"]),
            Paragraph("Menu <b>'Exportar ▾'</b>: escolha <i>Relatório Completo</i>, <i>Simplificado</i> ou <i>Matriz TXT</i>.", s["cell"]),
            Paragraph("Gera relatórios diagramados em PDF para publicação e tabelas tabulares para R, Python e PAST.", s["cell"])
        ],
    ]

    t_passos = Table(passo_data, colWidths=[80, 210, 225])
    t_passos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#FFFFFF")]),
    ]))
    story.append(t_passos)
    story.append(Spacer(1, 5))

    story.append(Paragraph("4. Destaques Analíticos: Histograma Bivariado e Densidade Espectral (PSD)", s["h1"]))
    story.append(Paragraph(
        "As duas novas ferramentas analíticas do Crinômetro v4.4.1 oferecem diagnósticos instantâneos da biometria acústica e do perfil mecânico:",
        s["body"]
    ))

    if os.path.exists(fig_hist) and os.path.exists(fig_psd):
        story.append(make_side_by_side_images(
            fig_hist,
            "Histograma Bivariado: Contagem de cantos (barras) e duração média em ms (linha vermelha twinx).",
            fig_psd,
            "Densidade Espectral de Potência (PSD Welch): Foco 0–15 kHz com portadora dominante anotada em 5.81 kHz.",
            s, target_width=235
        ))

    story.append(Paragraph(
        "• <b>Como Interpretar o Histograma Bivariado:</b> Permite discernir se chilreios com mais pulsos mantêm proporcionalidade linear de tempo ou "
        "se sofrem compressão temporal por aceleração do movimento tegminal.<br/>"
        "• <b>Como Interpretar a Densidade Espectral (PSD):</b> A frequência portadora modal (pico em dB) representa a assinatura ressonante das asas. "
        "Desvios no espectro permitem identificar espécimes competidores ou sub-harmônicos de ressonância no habitat.",
        s["body"]
    ))

    # Quebra explícita para a Página 3
    story.append(PageBreak())

    # ==================== PÁGINA 3 ====================
    story.append(Paragraph("5. Guia Visual das Cores por Contagem de Pulsos", s["h1"]))
    story.append(Paragraph(
        "O Crinômetro adota uma correspondência unívoca de cores padronizadas em todos os gráficos (Onda, Histograma e Espectrograma):",
        s["body"]
    ))
    story.append(make_color_table(s))
    story.append(Spacer(1, 5))

    story.append(Paragraph("6. Atualização Automática Transparente no Launcher (v4.4.1)", s["h1"]))
    story.append(Paragraph(
        "A versão 4.4.1 consolida a arquitetura definitiva do atualizador automático integrado ao Launcher:<br/>"
        "• <b>Script Nativo PowerShell com UTF-8-BOM:</b> Substituiu arquivos em lote frágeis por rotina em PowerShell (<code>apply_update.ps1</code>), "
        "garantindo execução silenciosa e imune a conflitos de caracteres acentuados no Windows.<br/>"
        "• <b>Padronização de Diretório sem Acento:</b> A pasta de instalação em <i>Program Files</i> foi normalizada para <b>Crinometro</b>, "
        "eliminando erros de codepage de versões legadas e preservando o nome de exibição 'Crinômetro'.<br/>"
        "• <b>Migração e Desligamento Determinístico:</b> Migra automaticamente as preferências do pesquisador (<code>crinometro_config.json</code>), "
        "remove pastas corrompidas antigas e encerra os processos em memória com <code>os._exit(0)</code> para troca instantânea de binários.",
        s["body"]
    ))

    story.append(Paragraph("7. Recomendações de Campo e Boas Práticas Bioacústicas", s["h1"]))
    dicas = [
        ("Taxa de Amostragem sem Compressão:", "Grave arquivos WAV a 44.1 kHz ou 48 kHz (16/24 bits). Evite MP3 ou formatos comprimidos que degradam harmônicos."),
        ("Posicionamento Estratégico do Microfone:", "Mantenha o microfone entre 30 cm e 1 metro do indivíduo focal para obter alta relação sinal-ruído (SNR) e minimizar reverberações."),
        ("Registro Obrigatório da Temperatura Corporal/Ambiente:", "Como a cadência de estridulação é termossensível (Lei de Dolbear), anote sempre a temperatura em °C no momento da gravação."),
        ("Diagnóstico Rítmico de Cadência:", "Verifique no relatório se o canto apresenta aceleração ou fadiga muscular com base na inclinação estatisticamente significativa do ICI (|β₁| > 0.15 ms/s e p < 0.05).")
    ]
    for tit, desc in dicas:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("8. Síntese Metodológica & Exportação para Softwares Estatísticos", s["h1"]))
    story.append(Paragraph(
        "As matrizes tabulares em formato <i>.txt</i> exportadas pelo Crinômetro possuem separadores tabulados padronizados, incluindo cabeçalhos "
        "de tempo inicial (s), tempo final (s), duração (ms), intervalo inter-chilreio (ms), contagem de pulsos e frequência dominante (Hz). "
        "Podem ser importadas diretamente com comandos convencionais como <code>read.table()</code> no <b>R</b>, "
        "<code>pandas.read_csv(..., sep='\\t')</code> no <b>Python</b>, ou abertas nativamente no <b>PAST</b> e <b>JASP</b>.",
        s["body"]
    ))

    doc.build(story, canvasmaker=NumberedDocCanvas)
    print(f"[OK] Guia Prático gerado com sucesso em: {output_path}")


# ======================================================================
# 2. GERADOR DO MANUAL TÉCNICO E ESPECIFICAÇÃO CIENTÍFICA (v4.4.1)
# ======================================================================
def build_manual_tecnico(output_path):
    print(f"[*] Gerando Manual Técnico em: {output_path}...")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=32,
        bottomMargin=40
    )
    s = get_custom_styles()
    story = []

    fig_wave = os.path.join(FIG_DIR, "fig2_waveform_lod_m017.png")
    fig_psd = os.path.join(FIG_DIR, "fig4_psd_welch_m017.png")
    fig_hist = os.path.join(FIG_DIR, "fig5_hist_bivariado_m017.png")

    # ==================== PÁGINA 1 ====================
    story.append(Paragraph("MANUAL TÉCNICO E ESPECIFICAÇÃO CIENTÍFICA", s["title"]))
    story.append(Paragraph(f"CRINÔMETRO v{APP_VERSION} — Processamento Digital de Sinais (DSP), Bioacústica e Aprendizado Ativo", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=6))

    story.append(Paragraph("Apresentação e Escopo Científico", s["h1"]))
    story.append(Paragraph(
        f"O <b>Crinômetro v{APP_VERSION}</b> é uma estação computacional concebida para a extração paramétrica quantitativa, caracterização "
        "biofísica e análise reprodutível de sinais bioacústicos em insetos (ordem Orthoptera: subordens Ensifera, famílias Gryllidae e Tettigoniidae). "
        "A arquitetura combina processamento digital determinístico de sinais com demodulação analítica pela Transformada de Hilbert, filtros "
        "digitais de fase zero, espectro de densidade de potência de Welch, histograma bivariado com eixo secundário e aprendizado ativo supervisionado. "
        "Esta especificação técnica é o documento formal de referência para validação experimental e citação acadêmica da versão 4.4.1.",
        s["body"]
    ))

    story.append(Paragraph("1. Arquitetura da Cadeia de Processamento Digital de Sinais (DSP)", s["h1"]))
    story.append(Paragraph(
        "A cadeia de sinal opera em precisão de 64 bits (float64) durante filtragem e detecção, com matrizes de visualização otimizadas em float32:",
        s["body"]
    ))
    dsp_items = [
        ("Condicionamento e Pré-filtragem Passa-Altas:",
         "Aplicação de filtro Butterworth de 2ª ordem SOS em 50 Hz para cancelamento de componentes contínuas (DC offset) e ruídos subsônicos ambientais."),
        ("Filtragem Passa-Faixa IIR de Fase Zero:",
         "Implementado com <code>scipy.signal.sosfiltfilt</code> (Butterworth 4ª ordem em Seções de Segunda Ordem, banda típica de 3.200 a 6.000 Hz). "
         "A filtragem bidirecional garante distorção de fase estritamente nula, preservando a morfologia temporal dos pulsos estridulatórios."),
        ("Demodulação Analítica por Transformada de Hilbert:",
         "Cálculo do sinal analítico complexo <i>z(t) = s(t) + j·H{s(t)}</i>, derivando a envoltória contínua <i>A(t) = |z(t)|</i>. A envoltória é "
         "normalizada pelo percentil 99.85 da distribuição de amplitudes e suavizada por convolução com janela de Hanning de 2.0 ms."),
        ("Busca Topológica Adaptativa e Critério FWHM:",
         "Segmentação morfológica de picos sob limiar adaptativo dinâmico (2.5 vezes o 25º percentil da envoltória) combinado à validação de largura "
         "a meia altura (Full Width at Half Maximum — FWHM) e distância inter-pulso mínima de 8 ms."),
        ("Filtro Espectral de Portadora:",
         "Exclusão de pulsos cuja frequência instantânea desvie além da tolerância espectral ajustada (chips rápidos de ±300, ±500, ±700 ou ±1000 Hz) "
         "em relação à frequência portadora dominante da espécie."),
        ("Agrupamento Fisiológico em Chilreios (Chirps):",
         "Consolidação em 5 camadas: fusão temporal por critério de gap, portão refratário de intervalo inter-chilreio (ICI Gate a 70% da mediana) "
         "e <b>imposição estrita de min_p ≥ 3 pulsos</b>, rejeitando artefatos isolados de 1 ou 2 pulsos.")
    ]
    for tit, desc in dsp_items:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    if os.path.exists(fig_wave):
        story.append(make_captioned_image(
            fig_wave,
            "Forma de onda oscilatória (azul), curva envoltória contínua de Hilbert (laranja tracejado) e pulsos estridulatórios marcados ('X').",
            s, target_width=475
        ))

    # Quebra explícita para a Página 2
    story.append(PageBreak())

    # ==================== PÁGINA 2 ====================
    story.append(Paragraph("2. Métricas Bioacústicas Avançadas e Visualização Científica", s["h1"]))
    story.append(Paragraph(
        "A versão 4.4.1 incorpora instrumentos gráficos avançados para análise quantitativa aprofundada:",
        s["body"]
    ))

    if os.path.exists(fig_hist) and os.path.exists(fig_psd):
        story.append(make_side_by_side_images(
            fig_hist,
            "Histograma Bivariado [twinx]: Distribuição de chamados (eixo esquerdo) vs Duração média em ms (eixo direito).",
            fig_psd,
            "Densidade Espectral de Potência [PSD Welch]: Janela 4096, foco 0–15 kHz e pico da portadora anotado.",
            s, target_width=235
        ))

    metricas_info = [
        ("Densidade Espectral de Potência (PSD Welch):",
         "Calculada via método de Welch com janela Hann de 4096 amostras e 50% de sobreposição. Substitui a dispersão instantânea por uma curva "
         "contínua de energia espectral em dB/Hz, focada no intervalo de 0 a 15 kHz e anotando automaticamente a portadora fundamental "
         "(<i>f_p</i>) obtida por interpolação parabólica sub-bin de 3 pontos."),
        ("Histograma Bivariado de Pulsos (twinx):",
         "Integração em eixo secundário sincronizado: as barras representam a probabilidade e contagem de chilreios por classe de pulsos, enquanto "
         "a linha tracejada vermelha plota a duração média em milissegundos com pontos marcadores, quantificando a persistência muscular do animal."),
        ("Espectrograma STFT Multirresolução:",
         "Transformada de Fourier de Tempo Curto com janela Hann de 1024 pontos e 75% de sobreposição. Opera com vetores float32 e oferece navegação "
         "com presets 'Total' (0 a Nyquist) e 'Focal' (f_p ± tolerância), limitada à extensão física real do áudio."),
        ("Diagnóstico Estatístico de Cadência Rítmica:",
         "Regressão linear ponderada dos intervalos inter-chilreios: <i>ICI(t) = β₀ + β₁·t + ε</i>. Pausas comportamentais (> 3× mediana) são "
         "expurgadas. A tendência é atestada por teste t de Student (p < 0.05) com critério fisiológico mínimo de inclinação (|β₁| > 0.15 ms/s)."),
        ("Modelagem Termo-Acústica (Lei de Dolbear):",
         "Estimativa térmica para espécies do gênero <i>Gryllus</i>: <i>T(°C) = (R_min - 40)/4 + 10</i>, onde R_min representa a cadência de "
         "chilreios por minuto ajustada por interpolação linear robusta.")
    ]
    for tit, desc in metricas_info:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    story.append(Paragraph("3. Motor de Machine Learning & Plasticidade Ativa (PulseLearner)", s["h1"]))
    ml_items = [
        ("Modo DSP Nativo como Padrão:",
         "O software inicia estritamente no modo determinístico com IA desligada, assegurando reprodutibilidade absoluta dos dados. A IA é "
         "ativada sob demanda pelo pesquisador, exibindo diálogo explicativo sobre as salvaguardas de inferência."),
        ("Espaço Vetorial de 14 Descritores Acústicos:",
         "Cada pulso candidato é descrito por 14 atributos físicos invariantes a ganho: largura a meia altura (FWHM), proeminência relativa, "
         "energia RMS normalizada, assimetria de crista (skewness), tempo de subida 10%-90% (attack time), centroide espectral, roll-off 85% e HNR."),
        ("Indução de Regras Contrastivas de Poda (Hard Negative Mining):",
         "A exclusão manual de um falso pulso pelo pesquisador induz hiper-retângulos rígidos de rejeição com margem de 30% em torno dos descritores "
         "do falso positivo, eliminando instantaneamente ruídos e reflexões análogas em gravações subsequentes."),
        ("Segregação Não-Supervisionada Focal vs. Coro por GMM:",
         "Modelagem estocástica via Mistura de Gaussianas bimodal no espaço amplitude × centroide, derivando o prior contínuo P(focal) para isolar "
         "o indivíduo em primeiro plano de cantos distantes e reverberações do ambiente."),
        ("Classificador Supervisionado e Reset de Fábrica:",
         "Emprega <code>HistGradientBoostingClassifier</code> com fallback para Random Forest (300 árvores) e serialização compacta <code>.crntrain</code>. "
         "O novo comando <b>'Resetar Aprendizado da IA'</b> limpa o cache e restaura os pesos de fábrica sem contaminação cruzada.")
    ]
    for tit, desc in ml_items:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    story.append(Paragraph("4. Engenharia de Computação, Concorrência e Viewport", s["h1"]))
    comp_items = [
        ("Concorrência Cooperativa com Botão '✕ Abortar':",
         "Processamento desacoplado em <code>GenericWorker(QThread)</code> com emissão de sinais Qt em fila (QueuedConnection). O botão "
         "<b>'✕ Abortar'</b> permite interromper cooperativamente análises individuais ou lotes demorados sem corrupção de estado."),
        ("Renderização Gráfica Não-Bloqueante:",
         "Repaint assíncrono via <code>canvas.draw_idle()</code> e debouncing de 100 ms em redimensionamentos, eliminando lag de interface."),
        ("Painéis Flexíveis com CompactCtrlBar:",
         "Controles de barra com <code>minimumSizeHint() == QSize(0,0)</code>, permitindo colapso elástico dos divisores de tela sem travamentos.")
    ]
    for tit, desc in comp_items:
        story.append(Paragraph(f"• <b>{tit}</b> {desc}", s["bullet"]))

    # Quebra explícita para a Página 3
    story.append(PageBreak())

    # ==================== PÁGINA 3 ====================
    story.append(Paragraph("5. Subsistema de Atualização Automática e Instalador (v4.4.1)", s["h1"]))
    story.append(Paragraph(
        "A versão 4.4.1 soluciona definitivamente o ciclo de atualização contínua:<br/>"
        "• <b>PowerShell UTF-8 com BOM:</b> O atualizador gera e executa <code>apply_update.ps1</code> codificado em <code>utf-8-sig</code>, "
        "com total suporte a acentos no Windows PowerShell nativo e sem dependência do frágil <code>cmd.exe</code>.<br/>"
        "• <b>Diretório Padronizado sem Acentos:</b> Normalização do caminho de instalação para <code>C:\\Program Files\\Crinometro</code>, "
        "garantindo compatibilidade universal em subshells de sistema operacional.<br/>"
        "• <b>Migração Automática e Expurgo:</b> Preservação de configurações (<code>crinometro_config.json</code>) e remoção atômica de pastas "
        "residuais legadas (<code>Crin?metro</code> e <code>Crinômetro</code>).<br/>"
        "• <b>Desligamento Atômico com os._exit(0):</b> Finalização imediata do processo principal para liberação de descritores de DLL e executável, "
        "permitindo que o Inno Setup complete a instalação silenciosa sem violações de compartilhamento.",
        s["body"]
    ))

    story.append(Paragraph("6. Tabela Canônica de Parâmetros Bioacústicos", s["h1"]))
    param_data = [
        [Paragraph("Parâmetro", s["header"]), Paragraph("Valor Padrão", s["header"]), Paragraph("Significado Fisiológico / Acústico", s["header"])],
        [Paragraph("min_p / max_p", s["cell_bold"]), Paragraph("3 a 10 pulsos", s["cell"]), Paragraph("Mínimo rigoroso de 3 pulsos para rejeição de cliques e ruídos transitórios.", s["cell"])],
        [Paragraph("amp_min / amp_max", s["cell_bold"]), Paragraph("0.08 a 1.00", s["cell"]), Paragraph("Limiares normalizados de amplitude para rejeição de ruído de fundo.", s["cell"])],
        [Paragraph("dur_min / dur_max", s["cell_bold"]), Paragraph("14.0 a 80.0 ms", s["cell"]), Paragraph("Faixa de duração temporal compatível com a batida de asa da espécie.", s["cell"])],
        [Paragraph("gap_min / gap_max", s["cell_bold"]), Paragraph("25.0 a 35.0 ms", s["cell"]), Paragraph("Critério de silêncio inter-pulso para segmentação e quebra de chamados.", s["cell"])],
        [Paragraph("b1_min / b1_max", s["cell_bold"]), Paragraph("3200 a 6000 Hz", s["cell"]), Paragraph("Banda de passagem do filtro Butterworth para estridulação em Grylloidea.", s["cell"])],
        [Paragraph("freq_tolerance_hz", s["cell_bold"]), Paragraph("±700 Hz", s["cell"]), Paragraph("Tolerância espectral em torno da frequência portadora (chips rápidos de 300, 500, 700, 1000 Hz).", s["cell"])],
        [Paragraph("psd_nfft / overlap", s["cell_bold"]), Paragraph("4096 / 50%", s["cell"]), Paragraph("Resolução espectral do método de Welch para cálculo da densidade de potência.", s["cell"])],
        [Paragraph("focal_sensitivity", s["cell_bold"]), Paragraph("0.60", s["cell"]), Paragraph("Ponto de corte para probabilidade posterior P(focal) no modelo GMM.", s["cell"])],
    ]
    t_params = Table(param_data, colWidths=[105, 75, 335])
    t_params.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#FFFFFF")]),
    ]))
    story.append(t_params)
    story.append(Spacer(1, 4))

    story.append(Paragraph("7. Paleta Canônica de Cores por Classe de Chilreio", s["h1"]))
    story.append(make_color_table(s))
    story.append(Spacer(1, 4))

    story.append(Paragraph("8. Matriz Sintética: Bioacústica ⇋ Algoritmo ⇋ Código-Fonte", s["h1"]))
    matriz_data = [
        [Paragraph("Fenômeno / Conceito", s["header"]), Paragraph("Implementação Algorítmica", s["header"]), Paragraph("Módulo e Função", s["header"])],
        [Paragraph("Fricção das tegminas", s["cell_bold"]), Paragraph("Sinal oscilatório na banda 3.2–6.0 kHz", s["cell"]), Paragraph("<code>core/analyzer.py -> analyze()</code>", s["cell"])],
        [Paragraph("Assinatura pura do canto", s["cell_bold"]), Paragraph("Filtro Butterworth 4ª ordem SOS fase zero", s["cell"]), Paragraph("<code>scipy.signal.sosfiltfilt()</code>", s["cell"])],
        [Paragraph("Volume instantâneo", s["cell_bold"]), Paragraph("Demodulação analítica de Hilbert", s["cell"]), Paragraph("<code>scipy.signal.hilbert()</code>", s["cell"])],
        [Paragraph("Batida de asa (pulso)", s["cell_bold"]), Paragraph("Detecção morfológica adaptativa e FWHM", s["cell"]), Paragraph("<code>scipy.signal.find_peaks()</code>", s["cell"])],
        [Paragraph("Espectro de potência", s["cell_bold"]), Paragraph("PSD pelo método de Welch (4096 amostras)", s["cell"]), Paragraph("<code>scipy.signal.welch()</code>", s["cell"])],
        [Paragraph("Contagem vs Duração", s["cell_bold"]), Paragraph("Histograma Bivariado com eixo duplo twinx", s["cell"]), Paragraph("<code>ui/main_window.py -> histogram</code>", s["cell"])],
        [Paragraph("Termômetro natural", s["cell_bold"]), Paragraph("Lei de Dolbear: T(°C) = (R_min - 40)/4 + 10", s["cell"]), Paragraph("<code>core/analyzer.py -> metrics</code>", s["cell"])],
        [Paragraph("Segregação focal vs coro", s["cell_bold"]), Paragraph("Clustering GMM bimodal no espaço amplitude × centroide", s["cell"]), Paragraph("<code>core/learner.py -> GaussianMixture()</code>", s["cell"])],
        [Paragraph("Cancelamento seguro", s["cell_bold"]), Paragraph("GenericWorker QThread cooperativo com abort()", s["cell"]), Paragraph("<code>core/worker.py -> GenericWorker</code>", s["cell"])],
    ]
    t_matriz = Table(matriz_data, colWidths=[110, 205, 200])
    t_matriz.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#FFFFFF")]),
    ]))
    story.append(t_matriz)

    doc.build(story, canvasmaker=NumberedDocCanvas)
    print(f"[OK] Manual Técnico gerado com sucesso em: {output_path}")


def main():
    guia_path = os.path.join(DOCS_DIR, "Crinometro_Guia_Pratico_Didatico.pdf")
    manual_path = os.path.join(DOCS_DIR, "Crinometro_Manual_Tecnico_Cientifico.pdf")
    build_guia_pratico(guia_path)
    build_manual_tecnico(manual_path)
    print("=" * 60)
    print(f"[OK] Manuais v{APP_VERSION} compilados com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    main()
