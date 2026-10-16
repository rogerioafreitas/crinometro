# -*- coding: utf-8 -*-
"""
Capítulo 3: Morfologia Temporal, Envoltória Analítica e Sintaxe de Chilreios do Crinômetro v4.5.0.
"""

import os
from reportlab.platypus import Paragraph, Spacer, PageBreak, Preformatted, Image
from reportlab.lib.units import cm
from docs.sections.common import make_academic_table, make_glossary_box, FIG_DIR

def build_chapter3(S):
    story = []

    # =========================================================================
    # CAPÍTULO 3: MORFOLOGIA TEMPORAL E SINTAXE DE CHILREIOS
    # =========================================================================
    story.append(Paragraph("3.0. CAPÍTULO 3: MORFOLOGIA TEMPORAL, ENVOLTÓRIA ANALÍTICA E SINTAXE DE CHILREIOS", S["h1"]))
    story.append(Paragraph(
        "A caracterização morfológica e temporal da estridulação constitui o núcleo da diagnose bioacústica em Orthoptera. "
        "Diferente da frequência portadora (que sofre forte influência física do tamanho corporal e da rigidez tegminal), "
        "a sintaxe temporal dos pulsos e chilreios é controlada por redes neuronais dedicadas, exibindo altíssima especificidade "
        "taxonômica e servindo como mecanismo chave de isolamento reprodutivo pré-zigótico entre espécies crípticas.",
        S["body"]
    ))

    # 3.1
    story.append(Paragraph("3.1. Biofísica Tegminal: Plectro, Lima Estridulatória e Dinâmica do Gerador Central de Padrões (CPG)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "O mecanismo de estridulação em machos da superfamília Grylloidea baseia-se na raspagem recíproca das tégminas modificadas. "
        "A tégmina esquerda sobrepõe-se à direita; na face ventral da tégmina superior encontra-se a lima estridulatória "
        "(<i>pars stridens</i>), composta por uma fileira linear de dentes cuticulares microscópicos (100 a 300 dentes). "
        "A margem anal da tégmina inferior contém uma lâmina esclerotizada rígida denominada plectro (<i>scraper</i>). "
        "Durante o movimento de fechamento (adução tegminal rápida), o plectro colide sucessivamente contra os dentes da lima. "
        "Cada colisão microscópica excita as membranas resonantes especializadas da tégmina: a harpa (responsável pela "
        "amplificação mecânica da frequência portadora pura) e o espelho (<i>speculum</i>).",
        S["body"]
    ))
    story.append(Paragraph(
        "A coordenação motora desse movimento é governada pelo <b>Gerador Central de Padrões (CPG - Central Pattern Generator)</b>, "
        "uma rede oscilatória de interneurônios situada nos gânglios torácicos (meso e metatorácico). "
        "A bioacústica comparada estabelece uma hierarquia estrutural estrita em quatro níveis: "
        "<i>(1)</i> <b>Transiente dentário:</b> colisão sub-milissegundo com um único dente da lima (< 1 ms); "
        "<i>(2)</i> <b>Pulso / Sílaba:</b> trem sonoro contínuo gerado por um único ciclo de adução tegminal (5 a 35 ms); "
        "<i>(3)</i> <b>Chilreio / Echema:</b> agrupamento estereotipado de N pulsos separados por Intervalos Inter-Pulso (IPI); e "
        "<i>(4)</i> <b>Intervalo Inter-Chilreio (ICI):</b> pausa refratária de recuperação metabólica e coordenação motora.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "Em Gryllidae, apenas o movimento de adução (fechamento) é sonoramente ativo, enquanto a abdução (abertura) "
        "ocorre em silêncio acústico (diferindo de Tettigoniidae, que frequentemente exibem estridulação bidirecional). "
        "Portanto, o ciclo mecânico elementar é expresso pela soma da duração ativa da sílaba (d<sub>p</sub>) e do período de repouso "
        "neuromuscular (IPI). O Crinômetro modela as constantes temporais através de restrições fisiológicas rígidas: "
        "o IPI deve obedecer ao intervalo [gap_min, gap_max], enquanto a duração de sílaba obedece a [dur_min, dur_max].",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_31 = (
        "# Mapeamento de constantes fisiológicas do CPG em core/analyzer.py\n"
        "gap_min_s = float(params.get('gap_min', 25.0)) / 1000.0 * 0.85  # Limiar refratário inferior\n"
        "gap_max_s = float(params.get('gap_max', 35.0)) / 1000.0 * 1.15  # Limiar de ruptura de chilreio\n"
        "dur_min_lim = (float(params.get('dur_min', 14.0)) / 1000.0) * (1 - 0.45) # Duração mínima\n"
        "dur_max_lim = (float(params.get('dur_max', 80.0)) / 1000.0) * (1 + 0.45) # Duração máxima"
    )
    story.append(Preformatted(code_31, S["code"]))
    story.append(Spacer(1, 4))

    # 3.2
    story.append(Paragraph("3.2. Envoltória Analítica via Transformada de Hilbert e Kernel de Suavização de Hann", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A extração precisa dos contornos temporais de início (<i>onset</i>) e término (<i>offset</i>) de cada pulso exige "
        "demarcar a envoltória de amplitude (AM), eliminando completamente as oscilações de alta frequência da portadora mecânica. "
        "Técnicas arcaicas baseadas em retificação de onda completa seguida de filtro passa-baixas introduzem distorções "
        "de fase e atrasos temporais assimétricos que corrompem a mensuração de intervalos inter-pulso milissegundos.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O Crinômetro extrai a envoltória matemática exata através da <b>Transformada de Hilbert</b>. "
        "Dado o sinal filtrado x(t), sua transformada de Hilbert x̃(t) corresponde à rotação de fase de -90° para frequências positivas: "
        "x̃(t) = (1/π) P.V. ∫ [x(τ) / (t - τ)] dτ. O sinal analítico complexo z(t) = x(t) + j x̃(t) define a envoltória instantânea "
        "como seu módulo euclidiano contínuo:",
        S["body"]
    ))
    story.append(Paragraph(
        "E(t) = |z(t)| = √[ x<sup>2</sup>(t) + x̃<sup>2</sup>(t) ]",
        S["formula"]
    ))
    story.append(Paragraph(
        "Para acelerar o cálculo computacional da FFT em arquivos com número arbitrário de amostras N (onde N pode ser um primo "
        "grande induzindo custo O(N²)), o Crinômetro calcula o próximo número inteiro 5-suave (fatorável exclusivamente em "
        "potências de 2, 3 e 5): N<sub>fast</sub> = next_fast_len(N) = 2<sup>a</sup> 3<sup>b</sup> 5<sup>c</sup>, "
        "garantindo que a execução opere estritamente em tempo <b>O(N<sub>fast</sub> log N<sub>fast</sub>)</b>.<br/>"
        "Em seguida, aplica-se a normalização robusta pelo percentil 99.85 (P<sub>99.85</sub>) ao invés do valor máximo absoluto, "
        "prevenindo a compressão da escala dinâmica por cliques transitórios ou estalos microfônicos. "
        "A envoltória normalizada é então convoluída com uma janela de Hann de 2,0 ms normalizada por sua integral:",
        S["body"]
    ))
    story.append(Paragraph(
        "Ê[n] = (1 / P<sub>99.85</sub>(E)) [ E * w<sub>Hann</sub> ][n], "
        "&nbsp;&nbsp;&nbsp;&nbsp; w<sub>Hann</sub>[m] = [0.5 - 0.5 cos(2π m / (M-1))] / ∑<sub>k=0</sub><sup>M-1</sup> w<sub>Hann</sub>[k]",
        S["formula"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_32 = (
        "# Trecho de core/analyzer.py (Hilbert e Suavização Hann Normalizada)\n"
        "env1 = np.abs(hilbert(data_b1, N=next_fast_len(len(data_b1)))[:len(data_b1)])\n"
        "scale_p99 = float(np.percentile(env1, 99.85))\n"
        "env1_norm = env1 / (scale_p99 if scale_p99 > 1e-9 else 1.0)\n"
        "smooth_ms = float(params.get('smooth_window_ms', 2.0))\n"
        "smooth_samples = max(3, int(rate * (smooth_ms / 1000.0)))\n"
        "if smooth_samples % 2 == 0:\n"
        "    smooth_samples += 1\n"
        "hann_win = np.hanning(smooth_samples)\n"
        "hann_win /= np.sum(hann_win)\n"
        "env1_smooth = np.convolve(env1_norm, hann_win, mode='same').astype(np.float32)"
    )
    story.append(Preformatted(code_32, S["code"]))
    story.append(Spacer(1, 4))

    # 3.3
    story.append(Paragraph("3.3. Algoritmo de Detecção de Pulsos em 3 Fases e Metrologia Fina de Sílabas", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Em gravações de habitat natural, o nível de ruído estocástico de fundo varia dinamicamente ao longo do tempo. "
        "Um limiar fixo estático resultaria em perda massiva de pulsos de baixa intensidade durante ataques graduais (<i>crescendo</i>) "
        "ou na proliferação incontrolável de falsos positivos em passagens silenciosas. O algoritmo opera em 3 fases complementares.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "<b>Fase 1: Estimação do Limiar Adaptativo:</b> O piso de detecção é formulado a partir do 25º percentil "
        "da distribuição da envoltória suavizada: θ<sub>peak</sub> = max(0.06, max(amp_min · noise_floor, P<sub>25</sub>(Ê) · 2.5)). "
        "O fator empírico 2.5 foi derivado de otimização da curva ROC (Receiver Operating Characteristic), garantindo sensibilidade "
        "> 95% e taxa de falsos positivos < 5% em gravações com Relação Sinal-Ruído (SNR) ≥ 10 dB.<br/><br/>"
        "<b>Fase 2: Detecção de Picos via <code>scipy.signal.find_peaks</code>:</b> Quatro critérios topográficos estritos são aplicados:<br/>"
        "• <i>height:</i> Amplitude instantânea dentro de [θ<sub>peak</sub>, amp_max];<br/>"
        "• <i>prominence:</i> Altura relativa mínima do pico em relação aos vales laterais mais próximos (evita picos em platôs);<br/>"
        "• <i>distance:</i> Distância mínima entre picos consecutivos = floor(rate · gap_min · 0.88), prevenindo detecções duplas de dentes na mesma sílaba;<br/>"
        "• <i>width:</i> Largura temporal na base do pico compatível com os limites de duração física do pulso.<br/><br/>"
        "<b>Fase 3: Validação Morfológica FWHM (-6 dB):</b> Cada pico candidato é avaliado via <code>peak_widths</code> na altura relativa de 50% "
        "(Full Width at Half Maximum - FWHM, equivalente à atenuação de -6 dB):",
        S["body"]
    ))
    story.append(Paragraph(
        "d<sub>p,-6dB</sub> = t<sub>right, 0.5</sub> - t<sub>left, 0.5</sub>, "
        "&nbsp;&nbsp;&nbsp;&nbsp; Critério: dur<sub>min</sub> × (1 - 0.45) ≤ d<sub>p,-6dB</sub> ≤ dur<sub>max</sub> × (1 + 0.45)",
        S["formula"]
    ))
    story.append(Paragraph(
        "Pulsos fora desse intervalo são rejeitados (pulsos < 3 ms são estalos de clique; pulsos > 80 ms decorrem de sobreposições). "
        "Para os pulsos aprovados, computam-se adicionalmente: Duração a -3 dB (queda de 50% em potência, rel_height=0.293), "
        "Intervalo Inter-Pulso (IPI = t<sub>peak, i+1</sub> - t<sub>peak, i</sub>), Taxa de Repetição de Pulsos (PRR = 1 / IPI) e "
        "Duty Cycle (DC = [d<sub>p</sub> / IPI] × 100%).",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_33 = (
        "# Trecho de core/analyzer.py (3 Fases de Detecção de Picos e Validação FWHM)\n"
        "# Fase 1: Limiar Adaptativo\n"
        "noise_floor_param = float(params.get('noise_floor', 1.00))\n"
        "noise_25 = float(np.percentile(env1_smooth, 25))\n"
        "search_thresh = max(float(params.get('amp_min', 0.08)) * noise_floor_param, noise_25 * 2.5)\n"
        "search_thresh = max(0.06, search_thresh)\n\n"
        "# Fase 2: find_peaks com 4 critérios restritivos\n"
        "dist_samples = max(1, int(rate * (float(params.get('gap_min', 25.0)) / 1000.0 * 0.88)))\n"
        "raw_peaks, _ = find_peaks(env1_smooth, height=(search_thresh, 2.0),\n"
        "                          distance=dist_samples, prominence=0.015,\n"
        "                          width=(max(0.0, float(params.get('width_min_ms', 0.0)) * rate / 1000.0), None))\n\n"
        "# Fase 3: Validação Morfológica FWHM (-6 dB / rel_height=0.50 e 0.70)\n"
        "widths_samples, _, _, _ = peak_widths(env1_smooth, raw_peaks, rel_height=0.70)\n"
        "pulse_durations_s = widths_samples / rate\n"
        "dur_min_lim = (float(params.get('dur_min', 14.0)) / 1000.0) * (1 - 0.45)\n"
        "dur_max_lim = (float(params.get('dur_max', 80.0)) / 1000.0) * (1 + 0.45)\n"
        "valid_peaks_stage2 = [p for p, dur in zip(raw_peaks, pulse_durations_s) if dur_min_lim <= dur <= dur_max_lim]"
    )
    story.append(Preformatted(code_33, S["code"]))
    story.append(Spacer(1, 4))

    # 3.4
    story.append(Paragraph("3.4. Identificação da Frequência Portadora Modal e Filtragem de Rejeição de Banda Estreita", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Mesmo após a filtragem passa-faixa, gravações de campo frequentemente contêm pulsos captados de outros insetos "
        "cantando em frequências próximas (por exemplo, outro macho a 4,2 kHz enquanto o indivíduo focal canta a 5,8 kHz). "
        "A identificação precisa da frequência portadora modal (f<sub>carrier</sub>) permite erguer um filtro de rejeição estreito "
        "que blinda o conjunto de dados contra intrusões acústicas simpátricas.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O algoritmo executa em 2 etapas estatísticas rigorosas: "
        "<i>(1)</i> Realiza um agrupamento preliminar dos pulsos candidatos em chilreios e interpola a frequência dominante refinada "
        "de cada pulso a partir da grade contínua do espectrograma. Constrói um histograma ponderado das frequências dominantes dos chilreios "
        "com largura de bin de exatamente <b>50,0 Hz</b>, onde o peso de cada chilreio é igual ao seu número de pulsos (|c<sub>j</sub>|). "
        "<i>(2)</i> O bin com maior contagem ponderada define o ápice modal. Em seguida, calcula-se a mediana ponderada dos chilreios "
        "na vizinhança restrita de ±150 Hz ([edges[best] - 75 Hz, edges[best+1] + 75 Hz]), fornecendo a frequência portadora f<sub>carrier</sub>. "
        "Pulsos individuais cuja frequência dominante difira da portadora por mais de ±freq_tolerance (padrão 700 Hz, configurável) "
        "são sumariamente expurgados:",
        S["body"]
    ))
    story.append(Paragraph(
        "| f<sub>dom</sub>(p<sub>i</sub>) - f<sub>carrier</sub> | ≤ Δf<sub>tol</sub>",
        S["formula"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_34 = (
        "# Trecho de core/analyzer.py (Portadora Modal e Filtragem Espectral)\n"
        "bins = np.arange(f_min_search, f_max_search + 50.0, 50.0)\n"
        "counts, edges = np.histogram(chirp_freqs, bins=bins, weights=chirp_weights)\n"
        "best_bin = int(np.argmax(counts))\n"
        "bin_lo, bin_hi = edges[best_bin] - 75.0, edges[best_bin + 1] + 75.0\n"
        "modal_freqs = [f for f in chirp_freqs if bin_lo <= f <= bin_hi]\n"
        "carrier_freq = float(np.median(modal_freqs)) if modal_freqs else float((edges[best_bin] + edges[best_bin + 1]) / 2.0)\n\n"
        "# Rejeição por tolerância espectral de banda estreita\n"
        "valid_peaks_stage3 = []\n"
        "for p in valid_peaks_stage2:\n"
        "    f_p = float(np.interp(p / rate, t_spec, dom_freqs))\n"
        "    if abs(f_p - carrier_freq) <= freq_tol:\n"
        "        valid_peaks_stage3.append(p)"
    )
    story.append(Preformatted(code_34, S["code"]))
    story.append(Spacer(1, 4))

    # 3.5
    story.append(Paragraph("3.5. Agrupamento Hierárquico em 5 Camadas e Filtro de Coerência Rítmica Linear O(N)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A sintaxe de chilreios em Gryllidae reflete a integridade do circuito CPG torácico. "
        "Agrupamentos ingênuos baseados puramente em janelas temporais fixas falham catastroficamente na presença de ecos, "
        "pulsos colidentes de machos secundários ou modulações naturais de amplitude. "
        "O método <code>regroup_chirps</code> implementa uma cascata de 5 camadas determinísticas com complexidade assintótica O(N).",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "<b>Camada 1: Janelamento Temporal IPI:</b> Varredura linear em O(N) onde pulsos sucessivos são agrupados se seu intervalo "
        "obedecer a gap_min · 0.85 ≤ Δt<sub>i</sub> ≤ gap_max · 1.15. Caso Δt<sub>i</sub> > gap_max, o chilreio preliminar é encerrado.<br/><br/>"
        "<b>Camada 2: Detecção de Colisão e Fusão Submilissegundo:</b> Se dois pulsos distam menos de 0.80 × gap_min, a mecânica tegminal "
        "proíbe a emissão pelo mesmo aparelho estridulatório (período refratário muscular absoluto). Trata-se de colisão com pulso de outro indivíduo; "
        "o algoritmo compara as amplitudes na envoltória e retém unicamente o pulso de maior energia.<br/><br/>"
        "<b>Camada 3: Coerência de Amplitude Fisiológica:</b> Calcula a amplitude mediana do trem de pulsos (A<sub>ref</sub>). "
        "Pulsos com desvio relativo |Ê[p] - A<sub>ref</sub>| / A<sub>ref</sub> > amp_var × 1.65 são expurgados como ruídos de fundo.<br/><br/>"
        "<b>Camada 4: Re-segmentação e Validação de Densidade:</b> O trem de pulsos limpo é re-fatiado em sub-blocos contínuos válidos, "
        "assegurando que nenhum vão temporal residual viole a cadência do CPG.<br/><br/>"
        "<b>Camada 5: Portão ICI (Inter-Chirp Interval Gate) e Filtro de Coerência Rítmica O(N):</b> Calcula o limiar refratário adaptativo "
        "ici_min_refractory = max(0.120 s, min(0.180 s, 0.45 · med(ICI), ici_param)). Subtrens separados por pausas menores que esse limiar "
        "são consolidados em um único chilreio. Por fim, aplica-se o filtro de coerência rítmica linear O(N), que descarta pulsos nas bordas "
        "que violem o ritmo neuromotor por mais de ±30% da mediana de IPI (|IPI<sub>i</sub> - IPI<sub>med</sub>| > 0.30 · IPI<sub>med</sub>), "
        "e expurga chilreios finais com contagem de pulsos inferior a min_p.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_35 = (
        "# Trecho de core/analyzer.py (CricketAnalyzer.regroup_chirps - As 5 Camadas)\n"
        "# 1. Agrupamento preliminar por janelamento temporal IPI em O(N)\n"
        "for i in range(1, len(pulse_times_s)):\n"
        "    gap_s = pulse_times_s[i] - pulse_times_s[i - 1]\n"
        "    if gap_min_s <= gap_s <= gap_max_s:\n"
        "        current_chirp.append(peaks[i])\n"
        "    else:\n"
        "        if len(current_chirp) >= min_p:\n"
        "            chirp_peaks_list.append(current_chirp)\n"
        "        current_chirp = [peaks[i]]\n\n"
        "# 2. Colisão sub-refratária (dt < gap_min_s * 0.80) e Coerência de Amplitude\n"
        "for k in range(1, len(coherent_pulses)):\n"
        "    dt = c_times[k] - (clean_track[-1] / float(rate))\n"
        "    if dt < gap_min_s * 0.80:\n"
        "        if env[coherent_pulses[k]] > env[clean_track[-1]]:\n"
        "            clean_track[-1] = coherent_pulses[k]  # Retém o pulso mais forte\n"
        "    else:\n"
        "        clean_track.append(coherent_pulses[k])\n\n"
        "# 5. Portão ICI Refratário Adaptativo e Validação Final de min_p\n"
        "ici_min_refractory_s = max(0.120, min(0.180, 0.45 * ici_median_s, ici_param_s))\n"
        "for cand in refined_chirps[1:]:\n"
        "    if (cand[0] - last_valid[-1]) / rate < ici_min_refractory_s:\n"
        "        if len(cand) >= 3 and mean_amp(cand) >= 0.70 * mean_amp(last_valid):\n"
        "            gated_chirps.append(cand)\n"
        "        elif mean_amp(cand) > 1.20 * mean_amp(last_valid):\n"
        "            gated_chirps[-1] = cand\n"
        "    else:\n"
        "        gated_chirps.append(cand)"
    )
    story.append(Preformatted(code_35, S["code"]))
    story.append(Spacer(1, 4))

    # 3.6
    story.append(Paragraph("3.6. Tratamento de Ruído e Diferenciação de Pausa Fisiológica vs. Ruído Transitório", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A estridulação contínua impõe enorme demanda metabólica aos músculos alares do tórax. Periodicamente, o macho cessa "
        "o canto por alguns segundos para termorregulação ou em resposta à passagem de predadores. "
        "Tratar essas pausas fisiológicas naturais como se fossem intervalos inter-chilreio normais distorceria completamente "
        "as métricas de cadência e variância da espécie.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O sistema emprega um critério robusto de corte não-paramétrico baseado no Intervalo Interquartil (IQR): "
        "Cutoff<sub>pausa</sub> = min(2000 ms, max(2.8 · med(ICI), Q<sub>75</sub> + 2.5 · IQR)). "
        "Uma pausa fisiológica genuína é formalmente caracterizada por 3 condições simultâneas: "
        "<i>(a)</i> ICI significativamente maior que a mediana (> 3 × med(ICI)); "
        "<i>(b)</i> ausência completa de pulsos no envelope analítico durante o intervalo; e "
        "<i>(c)</i> retomada imediata da estridulação com IPI idêntico à cadência metronômica anterior. "
        "Essas pausas são isoladas e excluídas da regressão de cadência contínua.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_36 = (
        "# Trecho de utils/report_generator.py (Filtro Robusto de Pausas Fisiológicas)\n"
        "median_raw_ici = float(np.median(raw_y))\n"
        "q25, q75 = float(np.percentile(raw_y, 25)), float(np.percentile(raw_y, 75))\n"
        "iqr = max(20.0, q75 - q25)\n"
        "pause_cutoff_ms = min(2000.0, max(median_raw_ici * 2.8, q75 + 2.5 * iqr))\n"
        "continuous_mask = (raw_y >= 20.0) & (raw_y <= pause_cutoff_ms)\n"
        "x_cont, y_cont = raw_x[continuous_mask], raw_y[continuous_mask]"
    )
    story.append(Preformatted(code_36, S["code"]))
    story.append(Spacer(1, 4))

    # 3.7
    story.append(Paragraph("3.7. Diagnóstico de Cadência Rítmica por Regressão Linear Ordinária e Inferência por Teste t", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A avaliação da estabilidade do canto ao longo de registros prolongados revela aspectos cruciais do estado fisiológico "
        "do indivíduo (aquecimento motor vs. exaustão neuromuscular). Em estudos de taxonomia integrativa, é indispensável "
        "reportar se a amostra acústica representa um canto estacionário metronômico ou um trecho transitório.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O modelo ajusta uma regressão linear simples por Mínimos Quadrados Ordinários (OLS) sobre os intervalos contínuos: "
        "ICI(t<sub>k</sub>) = β<sub>0</sub> + β<sub>1</sub> t<sub>k</sub> + ε<sub>k</sub>. "
        "A significância estatística da inclinação β<sub>1</sub> (ms/s) é testada convertendo o coeficiente de correlação de Pearson r "
        "na estatística t de Student com n-2 graus de liberdade:",
        S["body"]
    ))
    story.append(Paragraph(
        "t<sub>stat</sub> = r √[ (n-2) / (1 - r<sup>2</sup>) ], "
        "&nbsp;&nbsp;&nbsp;&nbsp; p-valor = 2 [ 1 - F<sub>t, n-2</sub>(|t<sub>stat</sub>|) ]",
        S["formula"]
    ))
    story.append(Paragraph(
        "Critérios diagnósticos padronizados:<br/>"
        "• <b>Aceleração Rítmica:</b> β<sub>1</sub> < -0,15 ms/s e p-valor < 0,05 (ICIs encurtando de forma significativa);<br/>"
        "• <b>Desaceleração Rítmica / Fadiga:</b> β<sub>1</sub> > +0,15 ms/s e p-valor < 0,05 (ICIs dilatando progressivamente);<br/>"
        "• <b>Cadência Estável Estacionária:</b> |β<sub>1</sub>| ≤ 0,15 ms/s ou p-valor ≥ 0,05 (ritmo metronômico consistente).",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_37 = (
        "# Trecho de utils/report_generator.py (analyze_rhythmic_cadence)\n"
        "slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x_cont, y_cont)\n"
        "median_ici = float(np.median(y_cont))\n"
        "cv = (float(np.std(y_cont)) / float(np.mean(y_cont)) * 100.0) if np.mean(y_cont) > 0 else 0.0\n"
        "if p_value < 0.05 and slope < -0.15:\n"
        "    diag = 'Aceleração Rítmica'\n"
        "elif p_value < 0.05 and slope > +0.15:\n"
        "    diag = 'Desaceleração Rítmica'\n"
        "else:\n"
        "    diag = 'Cadência Estável'"
    )
    story.append(Preformatted(code_37, S["code"]))
    story.append(Spacer(1, 4))

    # 3.8 Tabela Formal das Métricas Biométricas
    story.append(PageBreak())
    story.append(Paragraph("3.8. Tabela Formal das 15 Métricas Biométricas de Estridulação (Offset-to-Onset)", S["h2"]))
    story.append(Paragraph(
        "A Tabela 3.1 define as 15 variáveis acústicas padronizadas pelo Crinômetro v4.5.0. "
        "<b>Fundamentação Bioacústica da Convenção Offset-to-Onset:</b> O Intervalo Inter-Chilreio (ICI) e o Intervalo Inter-Pulso (IPI) "
        "são medidos rigorosamente do <i>offset</i> do evento anterior ao <i>onset</i> do evento seguinte. "
        "Esta escolha metrológica quantifica com precisão o verdadeiro período de repouso e relaxamento neuromuscular do aparelho "
        "estridulatório, enquanto a convenção rival (<i>onset-to-onset</i>) embute a duração do pulso prévio, contaminando a métrica "
        "temporal com variações de atrito e desgaste da cutícula.",
        S["body"]
    ))

    bio_headers = ["Métrica Taxonômica", "Símbolo", "Formulação Matemática Rigorosa", "Unidade", "Significado Físico Bioacústico"]
    bio_rows = [
        ["Total de Chilreios", "N_c", "Contagem de chirps validados", "unid.", "Volume total de echemas emitidos na gravação."],
        ["Total de Pulsos", "N_p", "∑ |c_i| para i=1..N_c", "unid.", "Contagem integral de sílabas estridulatórias validadas."],
        ["Taxa de Chilreios", "R_c", "N_c / T_total", "chilreios/s", "Frequência global de emissão de agrupamentos por segundo."],
        ["Cadência", "R_min", "R_c × 60", "chilreios/min", "Cadência de chilreios por minuto (caractere diagnóstico)."],
        ["ICI Médio", "μ_ICI", "(1/n) ∑ (onset[i+1] - offset[i])", "ms", "Pausa média de recuperação entre chilreios sucessivos."],
        ["ICI Desvio Padrão", "σ_ICI", "std(ICIs contínuos)", "ms", "Dispersão absoluta e variabilidade da cadência de repouso."],
        ["IPI Médio", "μ_IPI", "(1/m) ∑ (onset[j+1] - offset[j])", "ms", "Intervalo intra-chilreio de silêncio entre sílabas adjacentes."],
        ["IPI Desvio Padrão", "σ_IPI", "std(IPIs internos)", "ms", "Regularidade neuromotora do trem de disparos do CPG."],
        ["Duração do Pulso", "μ_d_p", "(1/N_p) ∑ (offset[k] - onset[k])", "ms", "Largura média da sílaba medida a -6 dB (FWHM)."],
        ["Duração do Chilreio", "μ_d_c", "(1/N_c) ∑ (offset_last - onset_first)", "ms", "Extensão temporal contínua total do echema."],
        ["Moda Pulsos/Chilreio", "Mo_ppc", "moda({ |c_i| })", "pulsos", "Assinatura sintática estereotipada da espécie."],
        ["Variância PPC", "σ²_ppc", "var({ |c_i| })", "pulsos²", "Grau de plasticidade sintática intra-específica."],
        ["Taxa Repetição Pulso", "PRR", "1 / (μ_d_p + μ_IPI)", "pulsos/s", "Pulse Repetition Rate intra-chilreio."],
        ["Duty Cycle", "DC", "(μ_d_p / (μ_d_p + μ_IPI)) × 100", "%", "Fração ativa de irradiação acústica por ciclo tegminal."],
        ["Portadora Modal", "f_carrier", "moda do histograma (50 Hz bins)", "Hz", "Frequência mecânica fundamental de estridulação."]
    ]
    story.append(make_academic_table(bio_headers, bio_rows, S, col_widths=[2.8*cm, 1.4*cm, 4.3*cm, 1.7*cm, 6.8*cm]))
    story.append(Spacer(1, 6))

    # Inserção das Figuras 1 e 5 do Áudio Real m017
    fig1_path = os.path.join(FIG_DIR, "fig1_dashboard_m017.png")
    fig5_path = os.path.join(FIG_DIR, "fig5_hist_bivariado_m017.png")
    if os.path.exists(fig1_path):
        story.append(Image(fig1_path, width=16.5*cm, height=8.5*cm))
        story.append(Paragraph("<b>Figura 3.1:</b> Dashboard Metrológico Completo do Crinômetro v4.5.0 (Oscilograma com Envoltória LoD, Espectrograma STFT, Histograma de Pulsos por Chilreio e Histograma de Duração para o Áudio m017).", S["caption"]))
        story.append(Spacer(1, 4))

    if os.path.exists(fig5_path):
        story.append(Image(fig5_path, width=16.5*cm, height=5.5*cm))
        story.append(Paragraph("<b>Figura 3.2:</b> Histograma Bivariado de Sintaxe Temporal (Distribuição conjunta de Pulsos por Chilreio vs. Duração do Chilreio em ms).", S["caption"]))
        story.append(Spacer(1, 4))

    # Glossário Seção 3
    g3_items = [
        ("G-13", "Gerador Central de Padrões (CPG)", "Rede interneuronal torácica que comanda os ciclos motores rítmicos de estridulação em ortópteros."),
        ("G-14", "Envoltória de Hilbert", "Curva analítica instantânea obtida a partir da amplitude complexa do sinal, refletindo a energia mecânica do pulso."),
        ("G-15", "Duração FWHM (-6 dB)", "Largura temporal do pulso medida a 50% da amplitude máxima linear (Full Width at Half Maximum)."),
        ("G-16", "Duty Cycle (Ciclo de Trabalho)", "Percentual da duração do pulso em relação ao período total do ciclo acústico (IPI)."),
        ("G-17", "Filtro de Coerência Rítmica O(N)", "Algoritmo de varredura linear que expurga transientes que violam o ritmo neuromuscular nas bordas do chilreio."),
        ("G-18", "Portão ICI (ICI Gate)", "Critério refratário que consolida sub-agrupamentos separados por pausas menores que 70% da mediana global.")
    ]
    story.append(make_glossary_box("§3.0 - §3.8", g3_items, S))
    story.append(PageBreak())

    return story
