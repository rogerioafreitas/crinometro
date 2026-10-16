# -*- coding: utf-8 -*-
"""
Capa Acadêmica e Sumário Estruturado Completo da Documentação Técnica v4.5.0.
"""

from datetime import datetime
from reportlab.platypus import Paragraph, Spacer, PageBreak
from docs.sections.common import make_callout, APP_VERSION

def build_cover_and_toc(S):
    story = []

    # =========================================================================
    # PÁGINA 1: CAPA ACADÊMICA
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("CRINÔMETRO v4.5.0", S["title"]))
    story.append(Paragraph(
        "DOCUMENTAÇÃO TÉCNICA, TEÓRICA E METODOLÓGICA<br/>"
        "<b>Arquitetura Computacional, Processamento Digital de Sinais (DSP), Aprendizado Ativo<br/>"
        "e Metrologia Bioacústica de Alta Precisão para Sistemática e Descoberta Taxonômica em Orthoptera</b>",
        S["subtitle"]
    ))
    story.append(Spacer(1, 10))

    meta_text = (
        "<b>Autor Técnico:</b> Engenharia de Processamento Digital de Sinais, Arquitetura Python/Qt & Bioacústica Computacional<br/>"
        "<b>Classificação do Instrumento:</b> Metrologia Pura para Diagnose e Caracterização Acústica de Novas Espécies<br/>"
        "<b>Padrão Terminológico Internacional:</b> Ragge & Reynolds (1998), Bennet-Clark (1999), Márquez et al. (2001), Baker & Chesmore (2020)<br/>"
        f"<b>Versão de Produção:</b> v{APP_VERSION} (Data de Emissão: {datetime.now().strftime('%d/%m/%Y')})"
    )
    story.append(Paragraph(meta_text, S["meta"]))
    story.append(Spacer(1, 15))

    axiom_box = (
        "<b>Axioma de Independência Taxonômica da Versão 4.5.0 (Proscrição da Lei de Dolbear):</b><br/>"
        "O Crinômetro v4.5.0 é expressamente um instrumento de metrologia bioacústica de alta precisão "
        "voltado à caracterização, diagnose e descrição formal de <b>espécies novas e espécimes não documentados</b>. "
        "Nas versões anteriores (v4.3.2/v4.4.1), mantinha-se a regressão linear termo-acústica de Dolbear (1897), "
        "calibrada no século XIX unicamente para <i>Oecanthus fultoni</i> na América do Norte. "
        "<b>Na arquitetura v4.5.0, qualquer estimativa térmica indireta por equações empíricas fixas foi banida e erradicada.</b><br/><br/>"
        "<i>Justificativa Científica:</i> A cinética do Gerador Central de Padrões (CPG) e os coeficientes térmicos (Q10) "
        "são caracteres espécie-específicos que variam com a massa torácica, fisiologia e microclima. "
        "Aplicar fórmulas pré-calibradas a táxons desconhecidos introduz viés sistemático inaceitável em taxonomia integrativa. "
        "O Crinômetro reporta exclusivamente grandezas físicas diretas: frequências em Hz, tempos em ms e densidades espectrais em dB/Hz."
    )
    story.append(make_callout("[DIRETRIZ DE DOMÍNIO CRÍTICA]", axiom_box, S, box_type="axiom"))
    story.append(Spacer(1, 20))
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 2: SUMÁRIO ESTRUTURADO COMPLETO
    # =========================================================================
    story.append(Paragraph("<b>SUMÁRIO ESTRUTURADO DA OBRA</b>", S["h1"]))
    story.append(Spacer(1, 4))
    toc_items = [
        ("1.0. CAPÍTULO 1: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E PIPELINE DE DADOS", [
            "1.1. Topologia de Fluxo de Dados (Dataflow) e Pipeline de Processamento Reativo",
            "1.2. Refatoração Arquitetural: Transição Monolito -> MVC Desacoplado (SessionContext e Mediadores)",
            "1.3. Concorrência Assíncrona: GenericWorker, Cancelamento Cooperativo e WorkerRegistry Monotônico",
            "1.4. Persistência Transacional Atômica: Write-Ahead, Fsync e Prevenção de Corrupção em Disco",
            "Glossário Técnico e Científico da Seção 1 ([G-01] a [G-05])"
        ]),
        ("2.0. CAPÍTULO 2: PROCESSAMENTO DIGITAL DE SINAIS (DSP) E ENGENHARIA ESPECTRAL", [
            "2.1. Condicionamento Primário: Seleção RMS Estéreo, Centralização DC e Filtro Anti-Vento (50 Hz)",
            "2.2. Filtragem Passa-Faixa Butterworth de Fase Zero via Seções de Segunda Ordem (SOS)",
            "2.3. Transformada de Fourier de Tempo Curto (STFT) e o Limite de Gabor-Heisenberg",
            "2.4. Refinamento Parabólico Sub-Bin da Frequência Portadora (Método de Smith-Serra)",
            "2.5. Densidade Espectral de Potência (Método de Welch) e Otimização Gráfica",
            "Glossário Técnico e Científico da Seção 2 ([G-06] a [G-12])"
        ]),
        ("3.0. CAPÍTULO 3: MORFOLOGIA TEMPORAL, ENVOLTÓRIA ANALÍTICA E SINTAXE DE CHILREIOS", [
            "3.1. Biofísica Tegminal: Plectro, Lima Estridulatória e Dinâmica do Gerador Central de Padrões (CPG)",
            "3.2. Envoltória Analítica via Transformada de Hilbert e Kernel de Suavização de Hann",
            "3.3. Algoritmo de Detecção de Pulsos em 3 Fases e Metrologia Fina de Sílabas",
            "3.4. Identificação da Frequência Portadora Modal e Filtragem de Rejeição de Banda Estreita",
            "3.5. Agrupamento Hierárquico em 5 Camadas e Filtro de Coerência Rítmica Linear O(N)",
            "3.6. Tratamento de Ruído e Diferenciação de Pausa Fisiológica vs. Ruído Transitório",
            "3.7. Diagnóstico de Cadência Rítmica por Regressão Linear Ordinária e Inferência por Teste t",
            "3.8. Tabela Formal das 15 Métricas Biométricas de Estridulação (Offset-to-Onset)",
            "Glossário Técnico e Científico da Seção 3 ([G-13] a [G-18])"
        ]),
        ("4.0. CAPÍTULO 4: APRENDIZADO DE MÁQUINA HÍBRIDO E ENGENHARIA DE ATRIBUTOS", [
            "4.1. Acústica Ecológica: Segregação do Canto Focal em Coros Polifônicos e Invariância a Ganho",
            "4.2. O Espaço Vetorial de 20 Descritores Bioacústicos Normalizados",
            "4.3. Classificador Não-Supervisionado: Modelo de Mistura de Gaussianas (GMM Bimodal)",
            "4.4. Classificador Supervisionado (HistGradientBoosting) e Fallback para RandomForest",
            "4.5. Mineração de Negativos Difíceis (Hard Negative Mining) e Poda Contrastiva",
            "4.6. Pontuação Híbrida Ponderada e Resgate Contextual (Contextual Gating)",
            "4.7. Ciclo de Feedback do Aprendizado Ativo em 5 Passos (subpassos a até g)",
            "4.8. Serialização Segura de Modelos via skops e Desacoplamento de Locks de Concorrência",
            "Glossário Técnico e Científico da Seção 4 ([G-19] a [G-24])"
        ]),
        ("5.0. CAPÍTULO 5: COMPUTAÇÃO GRÁFICA, ACELERAÇÃO LOD E INTERFACE REATIVA", [
            "5.1. Teorema de Preservação de Transientes por Decimação Min-Max LoD",
            "5.2. Arquitetura das Engines Vetorizadas: HighPerfLineEngine e HighPerfSpectrogramEngine",
            "5.3. Interatividade a 60 FPS: Background Blitting Coalescente e Poda Espacial O(log M) no Hover",
            "5.4. Controle Transacional de Visualização e Renderização Isolada de Eixos (NavigationController)",
            "5.5. Reavaliação Espectral em Tempo Real com Debounce de 25 ms",
            "5.6. Geração Pura de Figuras Científicas Vetoriais e Raster HD (FigureFactory)",
            "Glossário Técnico e Científico da Seção 5 ([G-25] a [G-30])"
        ]),
        ("6.0. CAPÍTULO 6: PROTOCOLOS EXPERIMENTAIS, CONSOLIDAÇÃO E ÍNDICE REMISSIVO", [
            "6.1. Seção Padronizada 'Materiais e Métodos' para Publicação em Periódicos de Alto Impacto",
            "6.2. Tabela Paramétrica Sintética Completa do Crinômetro v4.5.0",
            "6.3. Índice Remissivo Geral de Fórmulas, Classes, Métodos e Referências Cruzadas ([G-01] a [G-30])"
        ]),
    ]
    for cap_title, subitems in toc_items:
        story.append(Paragraph(f"<b>{cap_title}</b>", S["toc_item"]))
        for sub in subitems:
            story.append(Paragraph(f"• {sub}", S["toc_subitem"]))
        story.append(Spacer(1, 1))

    story.append(PageBreak())
    return story
