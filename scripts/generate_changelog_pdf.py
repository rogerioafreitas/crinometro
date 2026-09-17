#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador automatizado de CHANGELOG.pdf para o software Crinômetro.
Compila todo o histórico técnico detalhado de versões em documento PDF formatado.
"""

import os
import sys

# Garante que o diretório raiz do projeto esteja no sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from utils.constants import APP_VERSION, CHANGELOG_FULL

DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)
PDF_OUTPUT_PATH = os.path.join(DOCS_DIR, "CHANGELOG.pdf")

# ----------------------------------------------------------------------
# Configuração de Fontes TrueType
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
            break
        except Exception:
            pass


class NumberedCanvas(canvas.Canvas):
    """Canvas com cálculo dinâmico do número total de páginas e rodapé institucional."""
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
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont(FONT_REGULAR, 8.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Linha divisória de rodapé
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 38, 555, 38)

        text_left = f"Crinômetro v{APP_VERSION} — Histórico Completo de Mudanças (CHANGELOG)"
        text_right = f"Página {self._pageNumber} de {page_count}"

        self.drawString(40, 26, text_left)
        self.drawRightString(555, 26, text_right)
        self.restoreState()


def generate_changelog_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    title_style = ParagraphStyle(
        "ChangelogTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "ChangelogSubtitle",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14
    )

    version_header_style = ParagraphStyle(
        "VersionHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=4
    )

    version_badge_current = ParagraphStyle(
        "VersionBadgeCurrent",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=8,
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        "ChangelogBullet",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=9.2,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    intro_box_style = ParagraphStyle(
        "IntroBox",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B")
    )

    story = []

    # Cabeçalho Principal
    story.append(Paragraph("🦗 Crinômetro — Histórico de Atualizações", title_style))
    story.append(Paragraph(
        f"Documentação técnica e descritiva de todas as versões | Versão Atual: <b>v{APP_VERSION}</b> | Desenvolvido por <b>Rogério de Araújo Freitas</b>",
        subtitle_style
    ))

    # Box de introdução
    intro_table = Table(
        [[Paragraph(
            "<b>Nota de Referência:</b> Este documento consolida todo o registro de engenharia, melhorias de bioacústica, "
            "otimizações de processamento digital de sinais (DSP), correções de estabilidade e aprimoramentos de interface "
            "implementados desde a versão 3.0.0 até a versão atual. O código-fonte e o histórico Git correspondente "
            "podem ser consultados no repositório oficial: <i>github.com/rogerioafreitas/crinometro</i>.",
            intro_box_style
        )]],
        colWidths=[515]
    )
    intro_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(intro_table)
    story.append(Spacer(1, 10))

    # Itera sobre todas as versões em CHANGELOG_FULL
    for ver, items in CHANGELOG_FULL.items():
        v_elements = []
        is_current = (ver == APP_VERSION)

        # Divisor e Título da Versão
        v_elements.append(HRFlowable(
            width="100%",
            thickness=1 if not is_current else 1.5,
            color=colors.HexColor("#CBD5E1") if not is_current else colors.HexColor("#3B82F6"),
            spaceBefore=8,
            spaceAfter=4
        ))

        title_text = f"Versão {ver} (Atual)" if is_current else f"Versão {ver}"
        v_elements.append(Paragraph(
            f"<b>{title_text}</b>",
            version_badge_current if is_current else version_header_style
        ))
        v_elements.append(Spacer(1, 2))

        for item in items:
            bullet_text = f"• {item}"
            v_elements.append(Paragraph(bullet_text, bullet_style))

        # Adiciona a versão ao story mantendo os primeiros itens juntos se viável
        story.append(KeepTogether(v_elements[:3]) if len(v_elements) >= 3 else v_elements[0])
        for remaining in v_elements[3:]:
            story.append(remaining)
        story.append(Spacer(1, 4))

    # Constrói o PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[✓] CHANGELOG.pdf gerado com sucesso em: {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    generate_changelog_pdf()
