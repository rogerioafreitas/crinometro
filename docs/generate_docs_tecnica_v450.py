# -*- coding: utf-8 -*-
"""
Gerador Principal da Documentação Técnica, Teórica e Metodológica do Crinômetro v4.5.0 em PDF.
Documento Científico de Alta Fidelidade para Defesa Acadêmica e Publicação Internacional.
Cobre 100% dos fundamentos de DSP, Modelagem Mecanobiológica de Orthoptera (Grylloidea),
Aprendizado Ativo, Engenharia de Software MVC/SessionContext e Métricas Taxonômicas.
TOTALMENTE ISENTO DA LEI DE DOLBEAR (Proscrição Metrológica da v4.5.0).
Zero caracteres tofu/quadrados: utiliza fontes TrueType registradas (Arial e Consolas).
"""

import os
import sys

# Garante que a raiz do projeto esteja no sys.path
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
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate

from docs.sections.common import (
    AcademicCanvas, build_academic_styles, DOC_OUTPUT_PATH
)
from docs.sections.cover_and_toc import build_cover_and_toc
from docs.sections.chapter1 import build_chapter1
from docs.sections.chapter2 import build_chapter2
from docs.sections.chapter3 import build_chapter3
from docs.sections.chapter4 import build_chapter4
from docs.sections.chapter5 import build_chapter5
from docs.sections.chapter6 import build_chapter6


def generate_pdf():
    os.makedirs(os.path.dirname(DOC_OUTPUT_PATH), exist_ok=True)
    doc = SimpleDocTemplate(
        DOC_OUTPUT_PATH,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm
    )

    S = build_academic_styles()
    story = []

    print("[*] Montando Capa e Sumário...")
    story.extend(build_cover_and_toc(S))

    print("[*] Montando Capítulo 1 (Arquitetura, Concorrência e Pipeline)...")
    story.extend(build_chapter1(S))

    print("[*] Montando Capítulo 2 (DSP e Engenharia Espectral)...")
    story.extend(build_chapter2(S))

    print("[*] Montando Capítulo 3 (Morfologia Temporal e Sintaxe de Chilreios)...")
    story.extend(build_chapter3(S))

    print("[*] Montando Capítulo 4 (Aprendizado de Máquina Híbrido e skops)...")
    story.extend(build_chapter4(S))

    print("[*] Montando Capítulo 5 (Computação Gráfica e Aceleração LoD)...")
    story.extend(build_chapter5(S))

    print("[*] Montando Capítulo 6 (Protocolos, Tabela Sintética e Índice Remissivo)...")
    story.extend(build_chapter6(S))

    print(f"[*] Compilando documentação técnica acadêmica em: {DOC_OUTPUT_PATH}...")
    doc.build(story, canvasmaker=AcademicCanvas)
    file_size = os.path.getsize(DOC_OUTPUT_PATH)
    print(f"[OK] Documentação técnica gerada com sucesso! Tamanho: {file_size:,} bytes")

    # Contagem de páginas via QPdfDocument
    try:
        from PyQt6.QtPdf import QPdfDocument
        qdoc = QPdfDocument(None)
        qdoc.load(DOC_OUTPUT_PATH)
        total_pages = qdoc.pageCount()
        print(f"[INFO] Total de páginas geradas no PDF: {total_pages}")
    except Exception as e:
        print(f"[WARN] Não foi possível obter contagem via QPdfDocument: {e}")


if __name__ == "__main__":
    generate_pdf()
