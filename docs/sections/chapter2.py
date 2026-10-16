# -*- coding: utf-8 -*-
"""
Capítulo 2: Processamento Digital de Sinais (DSP) e Engenharia Espectral do Crinômetro v4.5.0.
"""

import os
from reportlab.platypus import Paragraph, Spacer, PageBreak, Preformatted, Image
from reportlab.lib.units import cm
from docs.sections.common import make_academic_table, make_glossary_box, FIG_DIR

def build_chapter2(S):
    story = []

    # =========================================================================
    # CAPÍTULO 2: PROCESSAMENTO DIGITAL DE SINAIS (DSP)
    # =========================================================================
    story.append(Paragraph("2.0. CAPÍTULO 2: PROCESSAMENTO DIGITAL DE SINAIS (DSP) E ENGENHARIA ESPECTRAL", S["h1"]))
    story.append(Paragraph(
        "O módulo de Processamento Digital de Sinais (DSP) do Crinômetro v4.5.0 constitui a base metrológica "
        "fundamental da plataforma. Sua finalidade é condicionar gravações acústicas de campo não-estacionárias, "
        "rejeitando ruídos de vento e perturbações ultrassônicas de artrópodes simpátricos sem introduzir "
        "distorções de fase ou dispersão temporal na morfologia das sílabas estridulatórias.",
        S["body"]
    ))

    # 2.1
    story.append(Paragraph("2.1. Condicionamento Primário: Seleção RMS Estéreo, Centralização DC e Filtro Anti-Vento (50 Hz)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A emissão sonora em Grylloidea decorre do impacto mecânico do plectro contra as lamelas da <i>pars stridens</i>, "
        "excitando a harpa e o espelho das tégminas. Gravações bioacústicas de campo sofrem contaminações severas: "
        "<i>(a)</i> turbulência aerodinâmica do vento sobre o diafragma do microfone (infrassons de alta energia concentrados abaixo de 100 Hz); "
        "<i>(b)</i> offset contínuo de tensão nos pré-amplificadores analógicos e conversores A/D; e "
        "<i>(c)</i> cancelamento por interferência destrutiva (filtro pente ou <i>comb filtering</i>) quando gravações estéreo "
        "são mixadas por soma aritmética ingênua.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "Para microfones espaçados por distância <i>d</i> e ângulo de incidência sonoro θ, a soma aritmética introduz zeros periódicos "
        "na magnitude espectral de acordo com a função de transferência do filtro pente: |H(f)| = 2 |cos(π f d sin(θ) / c)|, onde c ≈ 343 m/s. "
        "Para uma portadora típica de 5,0 kHz, uma defasagem espacial de apenas 3,43 cm anula completamente o sinal acústico útil. "
        "O Crinômetro calcula o valor eficaz (RMS) independente de cada canal e elege estritamente o canal com maior densidade de potência:",
        S["body"]
    ))
    story.append(Paragraph(
        "RMS<sub>c</sub> = √[ (1/N) ∑<sub>n=0</sub><sup>N-1</sup> X<sub>n,c</sub><sup>2</sup> ], "
        "&nbsp;&nbsp;&nbsp;&nbsp; c* = argmax<sub>c</sub> RMS<sub>c</sub>, "
        "&nbsp;&nbsp;&nbsp;&nbsp; x<sub>0</sub>[n] = X<sub>n, c*</sub> - (1/N) ∑<sub>k=0</sub><sup>N-1</sup> X<sub>k, c*</sub>",
        S["formula"]
    ))
    story.append(Paragraph(
        "Em seguida, aplica-se o filtro passa-altas Butterworth de 2ª ordem com frequência de corte em 50 Hz, implementado em "
        "Seções de Segunda Ordem (SOS) e processado bidirecionalmente (<code>sosfiltfilt</code>). "
        "A magnitude efetiva possui ordem 4 (atenuação estrita de -24 dB/oitava abaixo de 50 Hz) e fase identicamente nula "
        "(atraso de grupo τ<sub>g</sub>(ω) ≡ 0), preservando com exatidão micrométrica os transientes de subida de cada pulso.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_21 = (
        "# Trecho de core/analyzer.py (CricketAnalyzer.analyze - Condicionamento Primário)\n"
        "rms = np.sqrt(np.mean(data ** 2, axis=0))\n"
        "data = data[:, int(np.argmax(rms))]  # Seleção do canal de máxima energia RMS\n"
        "data = data - np.mean(data)          # Centralização amostral (Remoção de offset DC)\n"
        "nyq = 0.5 * rate\n"
        "if rate > 120.0 and nyq > 50.0:\n"
        "    sos_dc = butter(2, 50.0 / nyq, btype='high', output='sos')\n"
        "    data = sosfiltfilt(sos_dc, data)  # Fase Zero: preserva transientes de ataque"
    )
    story.append(Preformatted(code_21, S["code"]))
    story.append(Spacer(1, 4))

    # 2.2
    story.append(Paragraph("2.2. Filtragem Passa-Faixa Butterworth de Fase Zero via Seções de Segunda Ordem (SOS)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "O isolamento da banda bioacústica do táxon estudado ([b1_min, b1_max], padrão 3200 a 6000 Hz) exige rejeitar ruídos "
        "de ortópteros simpátricos (Tettigoniidae com estridulações ultrassônicas de 15 a 40 kHz) e anuros de baixa frequência. "
        "A filtragem não pode introduzir dispersão de fase não-linear, sob pena de deformar assimetricamente o perfil envoltório das sílabas.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O filtro Butterworth foi selecionado em detrimento de Chebyshev e Elíptico por 3 propriedades cruciais: "
        "<i>(1)</i> máxima planicidade na banda passante (ausência de ripple que falsearia a amplitude de sílabas); "
        "<i>(2)</i> decaimento monotônico suave na banda de rejeição; e "
        "<i>(3)</i> cancelamento exato de atraso de grupo via filtragem bidirecional de fase zero. "
        "A decomposição em Seções de Segunda Ordem (SOS / Biquads) previne instabilidade numérica e saturação de polos em float64:",
        S["body"]
    ))
    story.append(Paragraph(
        "H(z) = H<sub>1</sub>(z) · H<sub>2</sub>(z) = [ (b<sub>0,1</sub> + b<sub>1,1</sub> z<sup>-1</sup> + b<sub>2,1</sub> z<sup>-2</sup>) / (1 + a<sub>1,1</sub> z<sup>-1</sup> + a<sub>2,1</sub> z<sup>-2</sup>) ] · [ (b<sub>0,2</sub> + b<sub>1,2</sub> z<sup>-1</sup> + b<sub>2,2</sub> z<sup>-2</sup>) / (1 + a<sub>1,2</sub> z<sup>-1</sup> + a<sub>2,2</sub> z<sup>-2</sup>) ], "
        "&nbsp;&nbsp;&nbsp;&nbsp; |H<sub>eff</sub>(e<sup>jω</sup>)|<sup>2</sup> = |H(e<sup>jω</sup>)|<sup>2</sup> (Ordem Efetiva = 8, -48 dB/oitava)",
        S["formula"]
    ))
    story.append(Paragraph(
        "O Crinômetro impõe clampeamento automático em relação à frequência de Nyquist: b1_max ≤ f<sub>Nyq</sub> - 20 Hz e b1_min ≥ 20 Hz, "
        "exigindo uma largura passante mínima de 100 Hz para evitar divergências bilineares nos coeficientes do filtro.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_22 = (
        "# Trecho de core/analyzer.py (CricketAnalyzer.analyze - Filtragem Passa-Faixa SOS)\n"
        "b1_max = min(nyq - 20.0, float(params.get('b1_max', 6000)))\n"
        "b1_min = max(20.0, float(params.get('b1_min', 3200)))\n"
        "if b1_max - b1_min < 100.0:\n"
        "    raise ValueError(f'Banda passante inviável ({b1_min:.0f}-{b1_max:.0f} Hz) para Nyquist {nyq:.0f} Hz')\n"
        "sos_b1 = butter(4, [b1_min / nyq, b1_max / nyq], btype='band', output='sos')\n"
        "data_b1 = sosfiltfilt(sos_b1, data)  # Ordem 4 direta + reversa = 8ª ordem efetiva (-48 dB/oitava)"
    )
    story.append(Preformatted(code_22, S["code"]))
    story.append(Spacer(1, 4))

    # 2.3
    story.append(Paragraph("2.3. Transformada de Fourier de Tempo Curto (STFT) e o Limite de Gabor-Heisenberg", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Como os pulsos individuais de grilos duram tipicamente entre 3 e 35 ms e frequentemente exibem modulações sutis "
        "de frequência intra-pulso (<i>chirp gliding</i>), a análise exige uma representação conjunta tempo-frequência que capture "
        "a energia mecânica sem diluição temporal dos limites das sílabas.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "Pelo Princípio da Incerteza de Gabor-Heisenberg (σ<sub>t</sub> · σ<sub>f</sub> ≥ 1 / 4π), há uma troca fundamental "
        "entre resolução temporal e espectral. O Crinômetro parametriza janela de Hann com N<sub>w</sub> = 1024 amostras "
        "e sobreposição de 75% (hop size H = 256 amostras). A dedução matemática das grandezas operacionais revela:",
        S["body"]
    ))
    story.append(Paragraph(
        "• Para f<sub>s</sub> = 44.100 Hz: Δf = 44.100 / 1024 ≈ 43,07 Hz; &nbsp;&nbsp; Δt = 256 / 44.100 ≈ 5,80 ms.<br/>"
        "• Para f<sub>s</sub> = 48.000 Hz: Δf = 48.000 / 1024 = 46,88 Hz; &nbsp;&nbsp; Δt = 256 / 48.000 = 5,33 ms.",
        S["formula"]
    ))
    story.append(Paragraph(
        "Esta parametrização privilegia a resolução temporal em detrimento da espectral, garantindo precisão sub-milissegundo "
        "na demarcação dos limites de cada sílaba. A conversão logarítmica utiliza piso numérico estabilizador ε = 10<sup>-10</sup> (-100 dB):",
        S["body"]
    ))
    story.append(Paragraph(
        "S<sub>dB</sub>[k, m] = 10 log<sub>10</sub>( S<sub>xx</sub>[k, m] + 10<sup>-10</sup> )",
        S["formula"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_23 = (
        "# Trecho de core/analyzer.py (CricketAnalyzer.analyze - STFT Espectrograma)\n"
        "f_spec, t_spec, Sxx = scipy.signal.spectrogram(\n"
        "    data, rate, window='hann', nperseg=1024, noverlap=768, scaling='spectrum'\n"
        ")\n"
        "Sxx_db = (10.0 * np.log10(Sxx + 1e-10)).astype(np.float32)  # Piso logarítmico contra -inf"
    )
    story.append(Preformatted(code_23, S["code"]))
    story.append(Spacer(1, 4))

    # Tabela Formal da STFT (Restaurada da Seção 2.3 da v4.3.2)
    stft_headers = ["Parâmetro STFT", "Valor Padrão", "Tipo / Unidade", "Significado Físico Bioacústico"]
    stft_rows = [
        ["nperseg", "1024 amostras", "Inteiro (potência de 2)", "Tamanho da janela de Fourier (~23,2 ms a 44,1 kHz; ~21,3 ms a 48 kHz)."],
        ["window", "Hann", "Cosseno elevado", "Janela ponderadora que reduz o vazamento espectral (side-lobe suppression a -31 dB)."],
        ["noverlap", "768 amostras", "Inteiro (75% da janela)", "Sobreposição entre janelas consecutivas, assegurando continuidade temporal suave."],
        ["hop_size", "256 amostras", "Inteiro (= nperseg - noverlap)", "Deslocamento temporal entre colunas sucessivas do espectrograma (~5,3 a 5,8 ms)."],
        ["scaling", "'spectrum'", "Densidade / Espectro", "Retorna a densidade de potência quadrática por bin discreto de frequência (V²/bin)."]
    ]
    story.append(make_academic_table(stft_headers, stft_rows, S, col_widths=[3.0*cm, 3.0*cm, 3.5*cm, 7.5*cm]))
    story.append(Spacer(1, 6))

    # 2.4
    story.append(Paragraph("2.4. Refinamento Parabólico Sub-Bin da Frequência Portadora (Smith-Serra)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A grade discreta da FFT (~43-47 Hz) é insuficiente para discriminar espécies crípticas de Orthoptera cujos desvios "
        "diagnósticos de portadora são de apenas 15 a 30 Hz. O refinamento contínuo sub-bin eleva a precisão analítica para ±2 a 4 Hz.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "Aproximando o vértice espectral em decibéis por uma parábola quadrática de Taylor nos 3 bins adjacentes "
        "(α = S<sub>dB</sub>[k*-1], β = S<sub>dB</sub>[k*], γ = S<sub>dB</sub>[k*+1]), a derivada dP/dp = 0 "
        "fornece o deslocamento fracionário ótimo <i>p</i> no intervalo [-0.5, +0.5]:",
        S["body"]
    ))
    story.append(Paragraph(
        "p = 0.5 × [ (α - γ) / (α - 2β + γ) ], "
        "&nbsp;&nbsp;&nbsp;&nbsp; f<sub>dom</sub>(t<sub>m</sub>) = f<sub>spec</sub>[k*] + p · Δf",
        S["formula"]
    ))
    story.append(Paragraph(
        "Esse estimador reduz o erro assintótico de quantização de ±21,5 Hz (discreto) para menos de ±4,3 Hz (sub-bin contínuo), "
        "sem a sobrecarga computacional de zero-padding quádruplo.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_24 = (
        "# Refinamento parabólico sub-bin contínuo vetorizado (core/analyzer.py)\n"
        "valid_k = (dom_freq_idx > 0) & (dom_freq_idx < Sxx.shape[0] - 1)\n"
        "valid_cols = np.where(valid_k)[0]\n"
        "if len(valid_cols) > 0:\n"
        "    k = dom_freq_idx[valid_cols]\n"
        "    alpha = Sxx_db[k - 1, valid_cols]\n"
        "    beta = Sxx_db[k, valid_cols]\n"
        "    gamma = Sxx_db[k + 1, valid_cols]\n"
        "    denom = alpha - 2.0 * beta + gamma\n"
        "    non_zero = np.abs(denom) > 1e-6\n"
        "    p = np.zeros_like(denom, dtype=np.float32)\n"
        "    p[non_zero] = 0.5 * (alpha[non_zero] - gamma[non_zero]) / denom[non_zero]\n"
        "    p_valid = non_zero & (p >= -1.0) & (p <= 1.0)\n"
        "    dom_freqs[valid_cols[p_valid]] = f_spec[k[p_valid]] + p[p_valid] * df"
    )
    story.append(Preformatted(code_24, S["code"]))
    story.append(Spacer(1, 4))

    # 2.5
    story.append(Paragraph("2.5. Densidade Espectral de Potência (Método de Welch) e Otimização Gráfica", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A diagnose taxonômica da frequência mecânica fundamental (f<sub>c</sub>) e seus harmônicos secundários requer "
        "um estimador espectral de variância mínima, imune a transientes pontuais de ruído de insetos distantes.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O Crinômetro particiona o sinal em segmentos de 50 ms (M = min(N, floor(0.05 · f<sub>s</sub>))) sobrepostos em 50%. "
        "Isso impõe uma resolução frequencial invariante de exatamente <b>20,0 Hz</b> para qualquer taxa de amostragem. "
        "A média dos periodogramas modificados de Hann reduz a variância do estimador por um fator proporcional a 9L/11:",
        S["body"]
    ))
    story.append(Paragraph(
        "S<sub>xx</sub>(f<sub>k</sub>) = (1/L) ∑<sub>l=0</sub><sup>L-1</sup> P_welch<sub>l</sub>(f<sub>k</sub>), "
        "&nbsp;&nbsp;&nbsp;&nbsp; P<sub>xx,dB</sub>(f<sub>k</sub>) = 10 log<sub>10</sub>( max( S<sub>xx</sub>(f<sub>k</sub>), 10<sup>-12</sup> ) )",
        S["formula"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_25 = (
        "# Método de Welch estático em core/analyzer.py\n"
        "@staticmethod\n"
        "def compute_psd(data, sr):\n"
        "    nperseg = min(len(data), int(sr * 0.05))  # Janela de 50 ms -> 20,0 Hz exatos\n"
        "    f, Pxx = welch(data, sr, window='hann', nperseg=nperseg, scaling='density')\n"
        "    with np.errstate(divide='ignore', invalid='ignore'):\n"
        "        Pxx_db = 10 * np.log10(np.clip(Pxx, 1e-12, None))\n"
        "    return f[1:], Pxx_db[1:]  # Descarta o bin DC (f=0)"
    )
    story.append(Preformatted(code_25, S["code"]))
    story.append(Spacer(1, 4))

    # Inserção das Figuras 3 e 4 do Áudio Real m017
    fig3_path = os.path.join(FIG_DIR, "fig3_spectrogram_hd_m017.png")
    fig4_path = os.path.join(FIG_DIR, "fig4_psd_welch_m017.png")
    if os.path.exists(fig3_path):
        story.append(Image(fig3_path, width=16.5*cm, height=5.5*cm))
        story.append(Paragraph("<b>Figura 2.1:</b> Espectrograma STFT de Alta Resolução (Áudio m017_0376.wav, f<sub>c</sub> = 5,81 kHz, janela de Hann 1024 amostras, sobreposição de 75%).", S["caption"]))
        story.append(Spacer(1, 4))

    if os.path.exists(fig4_path):
        story.append(Image(fig4_path, width=16.5*cm, height=5.5*cm))
        story.append(Paragraph("<b>Figura 2.2:</b> Densidade Espectral de Potência (PSD) via Método de Welch com faixa de tolerância bioacústica de ±700 Hz.", S["caption"]))
        story.append(Spacer(1, 4))

    # Glossário Seção 2
    g2_items = [
        ("G-06", "Comb Filtering (Filtro Pente)", "Fenômeno acústico de cancelamento destrutivo periódico gerado pela soma de sinais idênticos defasados no tempo."),
        ("G-07", "Second-Order Sections (SOS)", "Decomposição matricial em cascata de filtros biquadráticos que previne instabilidade numérica e saturação de polos."),
        ("G-08", "Filtragem Bidirecional (Zero-Phase)", "Aplicação direta e reversa (sosfiltfilt) que duplica a ordem efetiva do filtro e anula integralmente o atraso de grupo."),
        ("G-09", "Limite de Gabor-Heisenberg", "Princípio físico da incerteza que define a fronteira teórica entre resolução temporal (Δt) e frequencial (Δf) em janelas de Fourier."),
        ("G-10", "Interpolação Parabólica Sub-Bin", "Ajuste quadrático contínuo de 3 pontos no espectro logarítmico que refina a frequência dominante com precisão sub-grade."),
        ("G-11", "Método de Welch (PSD)", "Estimador espectral baseado na média de periodogramas modificados sobrepostos, reduzindo a variância estocástica do sinal."),
        ("G-12", "Frequência Portadora Modal (fc)", "Frequência mecânica fundamental de maior potência emitida pela harpa/espelho durante a estridulação tegminal.")
    ]
    story.append(make_glossary_box("§2.0 - §2.5", g2_items, S))
    story.append(PageBreak())

    return story
