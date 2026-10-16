# -*- coding: utf-8 -*-
"""
Capítulo 6: Protocolos Experimentais, Consolidação Paramétrica e Índice Remissivo do Crinômetro v4.5.0.
"""

from reportlab.platypus import Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from docs.sections.common import make_academic_table, BASE_FONT

def build_chapter6(S):
    story = []

    # =========================================================================
    # CAPÍTULO 6: MATERIAIS E MÉTODOS, TABELA SINTÉTICA E ÍNDICE REMISSIVO
    # =========================================================================
    story.append(Paragraph("6.0. CAPÍTULO 6: PROTOCOLOS EXPERIMENTAIS, CONSOLIDAÇÃO E ÍNDICE REMISSIVO", S["h1"]))
    story.append(Paragraph(
        "Este capítulo consolida as diretrizes para replicação experimental rigorosa, fornecendo uma seção padronizada "
        "de 'Materiais e Métodos' pronta para inclusão direta em artigos científicos de alto impacto taxonômico, a Tabela "
        "Paramétrica Sintética integral do sistema e o Índice Remissivo Consolidado de todas as formulações e conceitos abordados.",
        S["body"]
    ))

    # 6.1
    story.append(Paragraph("6.1. Seção Padronizada 'Materiais e Métodos' para Publicações Científicas", S["h2"]))
    story.append(Paragraph(
        "O texto a seguir foi estruturado de acordo com as exigências metodológicas e terminológicas de periódicos internacionais "
        "de referência em entomologia e bioacústica sistemática (e.g., <i>Zootaxa</i>, <i>Systematic Entomology</i>, <i>Bioacoustics</i>, "
        "<i>Journal of Orthoptera Research</i>), permitindo sua transcrição direta para manuscritos acadêmicos:",
        S["body"]
    ))

    mat_text = (
        "<i>\"As gravações bioacústicas de estridulação foram adquiridas em formato WAV não comprimido (taxas de amostragem de 44,1 kHz a 96,0 kHz; "
        "quantização de 16 ou 24 bits) e analisadas através da plataforma metrológica <b>Crinômetro (v4.5.0)</b>. "
        "Para gravações multicanal, o sistema selecionou automaticamente o canal com maior potência eficaz (RMS), prevenindo distorções "
        "por interferência destrutiva espacial (comb filtering). O sinal foi centralizado para remoção de offset DC e submetido a um "
        "filtro passa-altas Butterworth de 2ª ordem com corte em 50 Hz para atenuação de ruídos de vento aerodinâmico, seguido de "
        "filtro passa-faixa Butterworth de 4ª ordem sintonizado na banda estridulatória do táxon (3200–6000 Hz). "
        "Ambos os filtros foram computados em Seções de Segunda Ordem (SOS / Biquads) bidirecionais de fase zero (sosfiltfilt; ordem efetiva 8; "
        "atenuação de -48 dB/oitava; atraso de grupo identicamente nulo), garantindo a preservação absoluta da geometria temporal dos pulsos.<br/><br/>"
        "A análise tempo-frequência foi calculada via Transformada de Fourier de Tempo Curto (STFT) com janelas de Hann de 1024 amostras "
        "e sobreposição temporal de 75% (hop size de 256 amostras; resolução temporal Δt ≈ 5,3 a 5,8 ms; resolução frequencial Δf ≈ 43 a 47 Hz). "
        "A frequência dominante instantânea foi refinada por interpolação parabólica contínua sub-bin de Smith-Serra. "
        "A Densidade Espectral de Potência (PSD) média foi estimada pelo método de Welch utilizando janelas de 50 ms sobrepostas em 50%, "
        "impondo uma resolução frequencial invariante de exatamente 20,0 Hz.<br/><br/>"
        "A envoltória instantânea de modulação de amplitude (AM) foi extraída através do módulo da Transformada de Hilbert, expandida "
        "para o próximo inteiro 5-suave (next_fast_len), normalizada pelo percentil 99.85 da distribuição de amplitude e suavizada "
        "por convolução com janela de Hann de 2,0 ms. Os pulsos estridulatórios foram detectados por limiar adaptativo baseado no 25º "
        "percentil do envelope (P25 × 2.5) e validados morfologicamente pela largura a meia altura (-6 dB / FWHM). "
        "O agrupamento sintático em chilreios (chirps/echemas) operou através de um pipeline hierárquico em 5 camadas, compreendendo "
        "janelamento por Intervalo Inter-Pulso (IPI), fusão de colisões sub-refratárias (< 0.80 gap_min), coerência de amplitude "
        "fisiológica, portão refratário inter-chilreio (ICI Gate adaptativo a 70% da mediana) e filtro de coerência rítmica linear O(N) "
        "que expurga transientes que violem a cadência neuromotora por mais de ±30%.<br/><br/>"
        "A estabilidade do ritmo do Gerador Central de Padrões (CPG) ao longo da emissão foi inferida por regressão linear ordinária (OLS) "
        "dos intervalos inter-chilreios contínuos e testada estatisticamente via distribuição t de Student (α = 0,05), após a segregação "
        "estrita de pausas fisiológicas espontâneas (ICIs > 3× a mediana). "
        "Todas as grandezas biométricas reportadas representam medições físicas diretas (frequências em Hz, intervalos e durações em ms), "
        "estando a análise totalmente isenta de estimativas térmicas empíricas derivadas da Lei de Dolbear, resguardando a independência "
        "metrológica indispensável para a diagnose e descrição formal de novas espécies.\"</i>"
    )
    story.append(Paragraph(mat_text, ParagraphStyle(
        "MatBody", parent=S["body"],
        fontName=f"{BASE_FONT}-Italic" if BASE_FONT == "Arial" else "Helvetica-Oblique",
        backColor=colors.HexColor("#F8FAFC"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5, borderPadding=8
    )))
    story.append(Spacer(1, 8))

    # 6.2
    story.append(Paragraph("6.2. Tabela Paramétrica Sintética Completa do Crinômetro v4.5.0", S["h2"]))
    story.append(Paragraph(
        "A Tabela 6.1 consolida os 16 parâmetros internos da plataforma, detalhando seus valores padrão, faixas "
        "operacionais permitidas e justificativas metrológicas:",
        S["body"]
    ))

    param_headers = ["Parâmetro Interno", "Valor Padrão", "Faixa Operacional", "Unidade", "Descrição Metrológica"]
    param_rows = [
        ["b1_min", "3200.0", "20.0 a (Nyq - 100)", "Hz", "Frequência de corte inferior do filtro passa-faixa estridulatório."],
        ["b1_max", "6000.0", "120.0 a (Nyq - 20)", "Hz", "Frequência de corte superior do filtro passa-faixa (clampeada em Nyquist)."],
        ["freq_tolerance_hz", "700.0", "100.0 a 2000.0", "Hz", "Semilargura da janela de tolerância espectral em torno de fc."],
        ["amp_min", "0.08", "0.01 a 0.50", "Norm [0-1]", "Limiar primário de amplitude relativa da envoltória normalizada."],
        ["noise_floor", "1.00", "0.20 a 3.00", "Fator", "Escalador de sensibilidade de ruído multiplicado pelo 25º percentil."],
        ["smooth_window_ms", "2.0", "0.5 a 10.0", "ms", "Largura temporal do kernel de Hann para suavização da envoltória."],
        ["prominence", "0.015", "0.005 a 0.10", "Norm [0-1]", "Proeminência topográfica mínima para validação de cristas de sílabas."],
        ["gap_min", "25.0", "5.0 a 80.0", "ms", "Intervalo inter-pulso (IPI) mínimo para continuidade intra-chilreio."],
        ["gap_max", "35.0", "15.0 a 150.0", "ms", "Intervalo inter-pulso (IPI) máximo admitido dentro do mesmo chilreio."],
        ["dur_min", "14.0", "2.0 a 40.0", "ms", "Duração temporal mínima admitida para uma sílaba a -6 dB (FWHM)."],
        ["dur_max", "80.0", "30.0 a 250.0", "ms", "Duração temporal máxima admitida para uma sílaba a -6 dB."],
        ["min_p", "2", "1 a 20", "pulsos", "Número mínimo de pulsos validados para consolidação de um chilreio."],
        ["max_p", "8", "2 a 50", "pulsos", "Número máximo de pulsos admitidos por chilreio sintático."],
        ["ici_min", "200.0", "50.0 a 1000.0", "ms", "Intervalo inter-chilreio de referência para o portão refratário adaptativo."],
        ["focal_sensitivity", "0.60", "0.30 a 0.90", "Norm [0-1]", "Sensibilidade do classificador híbrido ML para resgate contextual."],
        ["psd_window_ms", "50.0", "20.0 a 200.0", "ms", "Janela de Welch para fixação da resolução espectral invariante em 20 Hz."]
    ]
    story.append(make_academic_table(param_headers, param_rows, S, col_widths=[3.2*cm, 2.0*cm, 2.8*cm, 1.8*cm, 7.2*cm]))
    story.append(Spacer(1, 8))

    # 6.3
    story.append(Paragraph("6.3. Índice Remissivo Consolidado de Fórmulas, Classes, Métodos e Glossário ([G-01] a [G-30])", S["h2"]))
    story.append(Paragraph(
        "A Tabela 6.2 apresenta o mapeamento cruzado entre os conceitos teóricos, as formulações matemáticas, "
        "os arquivos-fonte da versão 4.5.0 e os códigos remissivos do glossário:",
        S["body"]
    ))

    idx_headers = ["Cód.", "Conceito / Símbolo", "Expressão / Função Principal", "Módulo / Classe no Código v4.5.0", "Seção"]
    idx_rows = [
        ["G-01", "SSOT", "SessionContext.state_changed", "core/session_context.py (SessionContext)", "§1.1, §1.2"],
        ["G-02", "Batch Atômico", "with ctx.batch_update():", "core/session_context.py (batch_update)", "§1.2"],
        ["G-03", "Abort Cooperativo", "GenericWorker._abort_event.set()", "core/worker.py (GenericWorker)", "§1.3"],
        ["G-04", "Deadline Monotônico", "deadline = time.monotonic() + T", "core/worker.py (WorkerRegistry)", "§1.3"],
        ["G-05", "Atomic Replace", "os.replace(temp_path, path)", "utils/persistence.py (atomic_write)", "§1.4"],
        ["G-06", "Seleção RMS Estéreo", "c* = argmax_c √(mean(X_c²))", "core/analyzer.py (CricketAnalyzer.analyze)", "§2.1"],
        ["G-07", "Filtro SOS Anti-Vento", "butter(2, 50/nyq, 'high', output='sos')", "core/analyzer.py (CricketAnalyzer.analyze)", "§2.1"],
        ["G-08", "Passa-Faixa Zero-Phase", "sosfiltfilt(sos_b1, data)", "core/analyzer.py (CricketAnalyzer.analyze)", "§2.2"],
        ["G-09", "STFT Gabor-Heisenberg", "spectrogram(window='hann', N=1024)", "core/analyzer.py (CricketAnalyzer.analyze)", "§2.3"],
        ["G-10", "Refinamento Sub-Bin", "p = 0.5 (α-γ)/(α-2β+γ)", "core/analyzer.py (CricketAnalyzer.analyze)", "§2.4"],
        ["G-11", "PSD Welch Invariante", "welch(nperseg=sr*0.05)", "core/analyzer.py (compute_psd)", "§2.5"],
        ["G-12", "Portadora Modal fc", "Média ponderada no bin modal", "core/analyzer.py (CricketAnalyzer.analyze)", "§2.5, §3.4"],
        ["G-13", "Sintaxe CPG", "Pulsos -> IPI -> Chilreios -> ICI", "core/analyzer.py (regroup_chirps)", "§3.1"],
        ["G-14", "Envoltória de Hilbert", "E = √(x² + H{x}²)", "core/analyzer.py (CricketAnalyzer.analyze)", "§3.2"],
        ["G-15", "Duração FWHM (-6 dB)", "d = t_right,0.5 - t_left,0.5", "core/analyzer.py & core/learner.py", "§3.3"],
        ["G-16", "Duty Cycle", "DC = (d_p / IPI) × 100%", "utils/report_generator.py", "§3.3, §3.8"],
        ["G-17", "Coerência Rítmica O(N)", "Poda periférica por mediana de IPI", "core/analyzer.py (regroup_chirps)", "§3.5"],
        ["G-18", "Portão ICI (ICI Gate)", "Fusão se ICI < 0.70 med(ICI)", "core/analyzer.py (regroup_chirps)", "§3.5, §3.6"],
        ["G-19", "Vetor 20 Atributos", "f(p_i) em R²⁰ normalizado", "core/learner.py (extract_features_for_peak)", "§4.1, §4.2"],
        ["G-20", "GMM Bimodal", "EM com covariâncias completas", "core/learner.py (PulseLearner)", "§4.3"],
        ["G-21", "HistGradientBoosting", "Loss log-loss com L2 = 2.0", "core/learner.py (PulseLearner)", "§4.4"],
        ["G-22", "Contextual Gating", "Resgate por IPI pareado", "core/learner.py (filter_peaks)", "§4.6"],
        ["G-23", "Auditoria skops", "Validação AST de tipos seguros", "core/learner.py (load_persisted_training)", "§4.8"],
        ["G-24", "Locks Desacoplados", "_model_lock isolado de CONFIG_LOCK", "core/learner.py (save_to_config)", "§4.8"],
        ["G-25", "Min-Max LoD", "Redução de N para 2B vértices", "core/engines.py (HighPerfLineEngine)", "§5.1"],
        ["G-26", "Engines Vetorizadas", "reshape(n_buckets, bucket_size)", "core/engines.py (HighPerfLineEngine)", "§5.2"],
        ["G-27", "Raster Blitting", "copy_from_bbox / restore_region", "ui/controllers/navigation_controller.py", "§5.3"],
        ["G-28", "Poda Hover O(log M)", "np.searchsorted em ±30 pixels", "ui/controllers/navigation_controller.py", "§5.3, §5.4"],
        ["G-29", "Debounce Espectral", "QTimer 25 ms na portadora", "ui/controllers/pipeline_orchestrator.py", "§5.5"],
        ["G-30", "FigureFactory Pura", "FigureCanvasAgg sem pyplot global", "ui/figure_factory.py (ExportConfig)", "§5.6"]
    ]
    story.append(make_academic_table(idx_headers, idx_rows, S, col_widths=[1.2*cm, 3.8*cm, 4.3*cm, 5.9*cm, 1.8*cm]))

    return story
