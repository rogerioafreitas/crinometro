# -*- coding: utf-8 -*-
"""
Script de montagem da Documentação Técnica Acadêmica Exaustiva (v4.5.0).
Gera docs/generate_docs_tecnica_v450.py cobrindo 100% dos fundamentos de DSP,
Bioacústica de Orthoptera, Aprendizado Ativo, Engenharia de Software MVC e Métricas Taxonômicas.
Alvo de páginas: 22 a 30 páginas, sem Dolbear, zero tofu/quadrados pretos, fontes TrueType nativas.
"""

import os
import sys

def build_full_generator():
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_docs_tecnica_v450.py")
    print(f"[*] Gerando script completo em: {out_path}...")

    # Vamos escrever o arquivo generate_docs_tecnica_v450.py em blocos modulares
    with open(out_path, "w", encoding="utf-8") as f:
        # 1. Cabeçalho e Importações
        f.write('''# -*- coding: utf-8 -*-
"""
Gerador da Documentação Técnica, Teórica e Metodológica do Crinômetro v4.5.0 em PDF.
Documento Científico de Alta Fidelidade para Defesa Acadêmica e Publicação Internacional.
Cobre 100% dos fundamentos de DSP, Modelagem Mecanobiológica de Orthoptera (Grylloidea),
Aprendizado Ativo, Engenharia de Software MVC/SessionContext e Métricas Taxonômicas.
TOTALMENTE ISENTO DA LEI DE DOLBEAR (Proscrição Metrológica da v4.5.0).
Zero caracteres tofu/quadrados: utiliza fontes TrueType registradas (Arial e Consolas).
"""

import os
import sys
from datetime import datetime

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

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Image, Preformatted
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

APP_VERSION = "4.5.0"
DOC_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", f"Crinometro_Documentacao_Tecnica_Cientifica_v{APP_VERSION}.pdf")
FIG_DIR = os.path.join(PROJECT_ROOT, "docs", "figures")


def setup_fonts():
    font_dir = "C:/Windows/Fonts"
    arial_regular = os.path.join(font_dir, "arial.ttf")
    arial_bold = os.path.join(font_dir, "arialbd.ttf")
    arial_italic = os.path.join(font_dir, "ariali.ttf")
    arial_bold_italic = os.path.join(font_dir, "arialbi.ttf")
    consolas = os.path.join(font_dir, "consola.ttf")

    if os.path.exists(arial_regular):
        pdfmetrics.registerFont(TTFont("Arial", arial_regular))
        pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bold if os.path.exists(arial_bold) else arial_regular))
        pdfmetrics.registerFont(TTFont("Arial-Italic", arial_italic if os.path.exists(arial_italic) else arial_regular))
        pdfmetrics.registerFont(TTFont("Arial-BoldItalic", arial_bold_italic if os.path.exists(arial_bold_italic) else arial_regular))
        pdfmetrics.registerFontFamily(
            "Arial",
            normal="Arial",
            bold="Arial-Bold",
            italic="Arial-Italic",
            boldItalic="Arial-BoldItalic"
        )
        base_font = "Arial"
    else:
        base_font = "Helvetica"

    if os.path.exists(consolas):
        pdfmetrics.registerFont(TTFont("Consolas", consolas))
        code_font = "Consolas"
    else:
        code_font = "Courier"

    return base_font, code_font


BASE_FONT, CODE_FONT = setup_fonts()


class AcademicCanvas(Canvas):
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
            return  # Capa limpa sem cabeçalho/rodapé

        self.saveState()
        w, h = A4

        # Cabeçalho Superior
        self.setFont(f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(2.0 * cm, h - 1.2 * cm, "CRINÔMETRO v4.5.0")
        self.setFont(BASE_FONT, 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(5.0 * cm, h - 1.2 * cm, "|  Documentação Técnica, Teórica e Metodológica")
        self.drawRightString(w - 2.0 * cm, h - 1.2 * cm, "Bioacústica Computacional & DSP")

        # Linha divisória do cabeçalho
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(2.0 * cm, h - 1.35 * cm, w - 2.0 * cm, h - 1.35 * cm)

        # Rodapé Inferior
        self.setFont(BASE_FONT, 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(2.0 * cm, 1.1 * cm, "Plataforma Metrológica de Precisão para Orthoptera (Ensifera: Grylloidea)")
        self.drawRightString(w - 2.0 * cm, 1.1 * cm, f"Página {page_num} de {total_pages}")

        # Linha divisória do rodapé
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(2.0 * cm, 1.45 * cm, w - 2.0 * cm, 1.45 * cm)

        self.restoreState()


def build_academic_styles():
    ss = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "DocTitle", parent=ss["Title"],
        fontSize=20, leading=25, textColor=colors.HexColor("#0F172A"),
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        spaceAfter=6, alignment=TA_CENTER
    )
    styles["subtitle"] = ParagraphStyle(
        "DocSubtitle", parent=ss["Normal"],
        fontSize=10, leading=14.5, textColor=colors.HexColor("#334155"),
        fontName=BASE_FONT, spaceAfter=12, alignment=TA_CENTER
    )
    styles["meta"] = ParagraphStyle(
        "DocMeta", parent=ss["Normal"],
        fontSize=8.5, leading=12.5, textColor=colors.HexColor("#475569"),
        fontName=BASE_FONT, alignment=TA_CENTER, spaceAfter=15
    )
    styles["h1"] = ParagraphStyle(
        "H1", parent=ss["Heading1"],
        fontSize=12.5, leading=16.5, textColor=colors.HexColor("#0F172A"),
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        spaceBefore=14, spaceAfter=6, keepWithNext=True
    )
    styles["h2"] = ParagraphStyle(
        "H2", parent=ss["Heading2"],
        fontSize=10.2, leading=14, textColor=colors.HexColor("#1E293B"),
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        spaceBefore=11, spaceAfter=5, keepWithNext=True
    )
    styles["h3"] = ParagraphStyle(
        "H3", parent=ss["Heading3"],
        fontSize=9.2, leading=13, textColor=colors.HexColor("#0284C7"),
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        spaceBefore=8, spaceAfter=4, keepWithNext=True
    )
    styles["body"] = ParagraphStyle(
        "DocBody", parent=ss["Normal"],
        fontSize=8.5, leading=12.5, textColor=colors.HexColor("#1E293B"),
        fontName=BASE_FONT, spaceAfter=5, alignment=TA_JUSTIFY
    )
    styles["bullet"] = ParagraphStyle(
        "DocBullet", parent=styles["body"],
        leftIndent=12, firstLineIndent=-8, spaceAfter=3
    )
    styles["formula"] = ParagraphStyle(
        "FormulaBox", parent=ss["Normal"],
        fontSize=8.5, leading=12, textColor=colors.HexColor("#0F172A"),
        alignment=TA_CENTER, spaceBefore=4, spaceAfter=6,
        fontName=f"{BASE_FONT}-Italic" if BASE_FONT == "Arial" else "Helvetica-Oblique",
        backColor=colors.HexColor("#F8FAFC"),
        borderColor=colors.HexColor("#E2E8F0"), borderWidth=0.5,
        borderPadding=5
    )
    styles["code"] = ParagraphStyle(
        "DocCode", parent=ss["Code"],
        fontSize=7.0, leading=9.2, textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5, borderPadding=5,
        spaceBefore=4, spaceAfter=6,
        fontName=CODE_FONT
    )
    styles["caption"] = ParagraphStyle(
        "Caption", parent=ss["Normal"],
        fontSize=7.5, leading=10.5, textColor=colors.HexColor("#475569"),
        spaceBefore=3, spaceAfter=8, alignment=TA_CENTER,
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold"
    )
    styles["glossary_title"] = ParagraphStyle(
        "GlossaryTitle", parent=ss["Normal"],
        fontSize=8.0, leading=11, textColor=colors.HexColor("#0F172A"),
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        spaceAfter=2
    )
    styles["glossary_term"] = ParagraphStyle(
        "GlossaryTerm", parent=ss["Normal"],
        fontSize=7.5, leading=10.5, textColor=colors.HexColor("#1E293B"),
        fontName=BASE_FONT, spaceAfter=2, leftIndent=6
    )
    styles["table_header"] = ParagraphStyle(
        "THeader", parent=ss["Normal"],
        fontSize=7.5, leading=10, textColor=colors.white,
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        alignment=TA_CENTER
    )
    styles["table_cell"] = ParagraphStyle(
        "TCell", parent=ss["Normal"],
        fontSize=7.2, leading=9.5, textColor=colors.HexColor("#1E293B"),
        fontName=BASE_FONT, alignment=TA_LEFT
    )
    styles["table_cell_center"] = ParagraphStyle(
        "TCellCenter", parent=styles["table_cell"],
        alignment=TA_CENTER
    )
    styles["toc_item"] = ParagraphStyle(
        "TOCItem", parent=ss["Normal"],
        fontSize=8.2, leading=11.5, textColor=colors.HexColor("#0F172A"),
        fontName=f"{BASE_FONT}-Bold" if BASE_FONT == "Arial" else "Helvetica-Bold",
        spaceBefore=3, spaceAfter=1
    )
    styles["toc_subitem"] = ParagraphStyle(
        "TOCSubItem", parent=styles["toc_item"],
        fontSize=7.4, leading=10, textColor=colors.HexColor("#475569"),
        fontName=BASE_FONT, leftIndent=12, spaceAfter=1
    )
    return styles


def make_callout(title, text, S, box_type="info"):
    color_map = {
        "axiom":   (colors.HexColor("#FFF7ED"), colors.HexColor("#EA580C"), colors.HexColor("#FED7AA")),
        "bio":     (colors.HexColor("#F0FDF4"), colors.HexColor("#059669"), colors.HexColor("#BBF7D0")),
        "math":    (colors.HexColor("#EFF6FF"), colors.HexColor("#2563EB"), colors.HexColor("#BFDBFE")),
        "code":    (colors.HexColor("#F8FAFC"), colors.HexColor("#475569"), colors.HexColor("#CBD5E1")),
        "warning": (colors.HexColor("#FEF2F2"), colors.HexColor("#DC2626"), colors.HexColor("#FECACA")),
    }
    bg_color, bar_color, border_color = color_map.get(box_type, color_map["math"])

    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle(
        "CTitle", parent=S["glossary_title"], textColor=bar_color, fontSize=8.5, leading=11
    ))
    p_body = Paragraph(text, ParagraphStyle(
        "CBody", parent=S["body"], fontSize=8.0, leading=11.5, textColor=colors.HexColor("#334155")
    ))

    t = Table([[ [p_title, Spacer(1, 2), p_body] ]], colWidths=[17.0 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('LINELEFT', (0, 0), (0, -1), 3.0, bar_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def make_glossary_box(section_ref, items, S):
    content = [
        Paragraph(f"<b>[GLOSSÁRIO TÉCNICO E CIENTÍFICO DA SEÇÃO {section_ref}]</b>", S["glossary_title"]),
        Spacer(1, 3)
    ]
    for code, term, desc in items:
        p = Paragraph(f"• <b>[{code}] {term}:</b> {desc}", S["glossary_term"])
        content.append(p)

    t = Table([[ content ]], colWidths=[17.0 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('LINELEFT', (0, 0), (0, -1), 2.5, colors.HexColor("#0284C7")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def make_academic_table(header, rows, S, col_widths=None):
    wrapped_data = []
    header_row = [Paragraph(h, S["table_header"]) for h in header]
    wrapped_data.append(header_row)

    for r in rows:
        row_cells = []
        for idx, cell in enumerate(r):
            if isinstance(cell, str):
                row_cells.append(Paragraph(cell, S["table_cell"]))
            else:
                row_cells.append(cell)
        wrapped_data.append(row_cells)

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#64748B')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]
    t = Table(wrapped_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return t
''')
    print("[*] Cabeçalho e helpers escritos com sucesso!")

if __name__ == "__main__":
    build_full_generator()
