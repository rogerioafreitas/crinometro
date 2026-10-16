# -*- coding: utf-8 -*-
"""
Capítulo 4: Aprendizado de Máquina Híbrido, Engenharia de Atributos e skops do Crinômetro v4.5.0.
"""

from reportlab.platypus import Paragraph, Spacer, PageBreak, Preformatted
from reportlab.lib.units import cm
from docs.sections.common import make_academic_table, make_glossary_box

def build_chapter4(S):
    story = []

    # =========================================================================
    # CAPÍTULO 4: APRENDIZADO DE MÁQUINA HÍBRIDO E SKOPS
    # =========================================================================
    story.append(Paragraph("4.0. CAPÍTULO 4: APRENDIZADO DE MÁQUINA HÍBRIDO E ENGENHARIA DE ATRIBUTOS", S["h1"]))
    story.append(Paragraph(
        "A bioacústica de campo frequentemente enfrenta cenários de polifonia complexa, onde múltiplos insetos "
        "cantam simultaneamente em planos acústicos distintos. O módulo de Inteligência Artificial do Crinômetro "
        "(<code>PulseLearner</code>) combina modelagem probabilística não-supervisionada, classificação supervisionada "
        "por gradiente impulsionado, indução de regras contrastivas e aprendizado ativo com feedback humano incremental.",
        S["body"]
    ))

    # 4.1
    story.append(Paragraph("4.1. Acústica Ecológica: Segregação do Canto Focal em Coros Polifônicos e Invariância a Ganho", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Em ecossistemas tropicais, machos de grilos cantam em agregados espaciais densos. O microfone capta o macho focal "
        "(a poucos centímetros) sobreposto a dezenas de machos conspecíficos e heterospecíficos a distâncias variadas (1 a 20 metros). "
        "A propagação da onda sonora sofre duas atenuações fundamentais: "
        "<i>(1)</i> <b>Divergência geométrica esférica:</b> a pressão acústica decai com o inverso da distância (p ~ 1/r); "
        "<i>(2)</i> <b>Absorção atmosférica molecular:</b> dissipação viscosa e relaxação molecular do ar que atenuam exponencialmente "
        "as altas frequências em função da umidade relativa e temperatura. "
        "Ademais, gravações de campo feitas por diferentes pesquisadores exibem ganhos analógicos arbitrários. "
        "Qualquer classificador que utilize amplitude absoluta é inútil em ecologia bioacústica.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "Para garantir transferibilidade inter-gravações, o Crinômetro formula seus descritores com <b>invariância estrita a ganho linear</b>. "
        "Para qualquer fator multiplicativo de ganho k > 0 aplicado ao sinal bruto x'(t) = k · x(t), os atributos baseados em razões "
        "de amplitude local ou relações de energia satisfazem:",
        S["body"]
    ))
    story.append(Paragraph(
        "f<sub>i</sub>(k · x) = [ k · Ê[p] ] / [ med(k · Ê<sub>local</sub>) ] = Ê[p] / med(Ê<sub>local</sub>) = f<sub>i</sub>(x)",
        S["formula"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_41 = (
        "# Normalização local com invariância a ganho em core/learner.py\n"
        "peak_amp = float(env_signal[peak_idx])\n"
        "med_amp = float(np.median(env_segment)) + 1e-6\n"
        "peak_amp_rel = peak_amp / med_amp  # Invariante a qualquer ganho k\n"
        "local_mad = float(np.median(np.abs(border_env - np.median(border_env)))) + 1e-6\n"
        "local_snr_db = float(20.0 * np.log10(peak_amp / (1.4826 * local_mad)))"
    )
    story.append(Preformatted(code_41, S["code"]))
    story.append(Spacer(1, 4))

    # 4.2
    story.append(Paragraph("4.2. O Espaço Vetorial de 20 Descritores Bioacústicos Normalizados", S["h2"]))
    story.append(Paragraph(
        "Para cada pulso candidato, o <code>PulseLearner</code> constrói um vetor de características f(p<sub>i</sub>) "
        "projetado no espaço vetorial <b>R</b><sup>20</sup>, extraído em janelas centradas no ápice do envelope (Tabela 4.1):",
        S["body"]
    ))

    feat_headers = ["ID", "Nome do Atributo", "Formulação Matemática Rigorosa", "Interpretação Bioacústica Mecânica"]
    feat_rows = [
        ["1", "peak_amp_rel", "Ê[p] / (mediana(Ê_±30ms) + 1e-6)", "Razão de emergência do pulso focal sobre o ruído da vizinhança local."],
        ["2", "peak_width_s", "w_0.50 / rate", "Duração FWHM a -6 dB em segundos (caractere biomecânico diagnóstico)."],
        ["3", "peak_width_75_s", "w_0.25 / rate", "Largura do topo do pulso a 75% da altura (agudeza do impacto tegminal)."],
        ["4", "local_snr_db", "20 log10( Ê[p] / (1.4826 MAD(borda) + 1e-6) )", "Relação Sinal-Ruído local robusta imune a outliers na vizinhança."],
        ["5", "energy_rel", "mean(Ê_±30ms²) / (Ê[p]² + 1e-9)", "Concentração relativa da densidade de energia acústica da janela."],
        ["6", "std_amp_rel", "std(Ê_±30ms) / (Ê[p] + 1e-6)", "Grau de variabilidade estocástica da amplitude ao redor do pulso."],
        ["7", "prominence_ratio", "(Ê[p] - min(vales)) / (Ê[p] + 1e-6)", "Proeminência topográfica sobre vales adjacentes (isolamento da crista)."],
        ["8", "peak_sharpness_rel", "(2Ê[p] - Ê[p-δ] - Ê[p+δ]) / (Ê[p] + 1e-6)", "Curvatura de 2ª ordem no ápice (taxa de impacto dente-a-dente)."],
        ["9", "crest_factor", "Ê[p] / (RMS_±30ms + 1e-6)", "Fator de crista temporal (discrimina cliques de transientes suaves)."],
        ["10", "skewness_local", "(mean(esq) - mean(dir)) / (Ê[p] + 1e-6)", "Assimetria temporal do envelope (ataque tegminal vs decaimento ressonante)."],
        ["11", "local_density_rel", "mean(Ê_±10ms) / (mean(Ê_±30ms) + 1e-6)", "Taxa de confinamento de energia no núcleo temporal de 10 ms."],
        ["12", "autocorr_1ms", "∑ e[m] e[m-τ] / (∑ e[m]² + 1e-9)", "Coeficiente de autocorrelação com atraso de 1 ms (periodicidade residual)."],
        ["13", "band_energy_ratio", "E_±10ms / (E_±30ms + 1e-9)", "Foco energético da sílaba focal em relação ao contexto temporal largo."],
        ["14", "rise_slope_rel", "(Ê[p] - min(esq)) / (Δt_subida · Ê[p])", "Velocidade mecânica de fechamento tegminal durante o ataque sonoro."],
        ["15", "spectral_centroid", "∑ f |X[f]| / (∑ |X[f]| + 1e-9)", "Centro de gravidade espectral (Hz); detecta atenuação por distância."],
        ["16", "spectral_rolloff_85", "Frequência onde energia atinge 85%", "Limite superior da irradiação acústica da harpa/espelho (Hz)."],
        ["17", "attack_time_10_90_ms", "(t_90% - t_10%) × 1000", "Tempo de subida entre 10% e 90% da altura via interpolação linear (ms)."],
        ["18", "local_hnr_db", "10 log10( E_portadora / (E_fora + 1e-9) )", "Razão Harmônico-Ruído local na janela de ±150 Hz em torno de fc."],
        ["19", "multiscale_energy", "RMS_15ms / (RMS_80ms + 1e-9)", "Densidade de potência multiescala (pulso isolado vs coro polifônico)."],
        ["20", "prior_p_focal", "P(Cluster Focal | GMM Bimodal)", "Probabilidade posterior não-supervisionada gerada pelo modelo GMM."]
    ]
    story.append(make_academic_table(feat_headers, feat_rows, S, col_widths=[1.0*cm, 3.8*cm, 5.7*cm, 6.5*cm]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_42 = (
        "# Trecho de core/learner.py (PulseLearner.extract_features_for_peak)\n"
        "feat = np.asarray([\n"
        "    peak_amp_rel, peak_width_s, peak_width_75_s, local_snr_db, energy_rel,\n"
        "    std_amp_rel, prominence_ratio, peak_sharpness_rel, crest_factor, skewness_local,\n"
        "    local_density_rel, autocorr_1ms, band_energy_ratio, rise_slope_rel,\n"
        "    spectral_centroid, spectral_rolloff_85, attack_time_10_90_ms, local_hnr_db,\n"
        "    multiscale_energy_ratio\n"
        "], dtype=float)\n"
        "return np.nan_to_num(feat, nan=0.0, posinf=10000.0, neginf=-10000.0)"
    )
    story.append(Preformatted(code_42, S["code"]))
    story.append(Spacer(1, 4))

    # 4.3
    story.append(Paragraph("4.3. Classificador Não-Supervisionado: Modelo de Mistura de Gaussianas (GMM Bimodal)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Antes que o taxonomista realize qualquer anotação manual, o sistema precisa fornecer uma primeira estimativa confiável "
        "de quais pulsos pertencem ao espécime focal mais próximo e quais decorrem de insetos distantes ou ruídos. "
        "O Modelo de Mistura de Gaussianas (GMM) modela essa partição bimodal intrínseca de forma puramente não-supervisionada.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O GMM opera em um subespaço bidimensional padronizado Z-score: z = [log(amplitude), centroide_espectral]. "
        "Ajustam-se duas componentes gaussianas multivariadas via algoritmo de Expectation-Maximization (EM):",
        S["body"]
    ))
    story.append(Paragraph(
        "P(z) = ∑<sub>k=1</sub><sup>2</sup> π<sub>k</sub> N(z | μ<sub>k</sub>, Σ<sub>k</sub>), "
        "&nbsp;&nbsp;&nbsp;&nbsp; c<sub>focal</sub> = argmax<sub>k</sub> ( μ<sub>k, amp</sub> + 0.5 μ<sub>k, centroide</sub> )",
        S["formula"]
    ))
    story.append(Paragraph(
        "O cluster focal é eleito pela soma ponderada de sua média de amplitude e centroide espectral (pulsos próximos sofrem menos "
        "atenuação atmosférica e possuem centroide mais alto). Instancia-se com <code>n_components=2</code>, matriz de covariância "
        "<code>covariance_type='diag'</code> ou <code>'full'</code> e <code>n_init=5</code> inicializações. "
        "Salvaguarda: se o áudio contiver N < 10 pulsos, o algoritmo assume ausência de coro e atribui P(focal) ≡ 1.0.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_43 = (
        "# Trecho de core/learner.py (PulseLearner.compute_unsupervised_focal_priors)\n"
        "if n < 10 or GaussianMixture is None:\n"
        "    return np.ones(n, dtype=float)  # Salvaguarda para amostras escassas\n"
        "F_norm = (F - np.mean(F, axis=0)) / (np.std(F, axis=0) + 1e-6)\n"
        "gmm = GaussianMixture(n_components=2, covariance_type='diag', random_state=42, max_iter=100)\n"
        "gmm.fit(F_norm)\n"
        "c_focal = int(np.argmax(gmm.means_[:, 0] + 0.5 * gmm.means_[:, 1]))\n"
        "probs = gmm.predict_proba(F_norm)[:, c_focal]\n"
        "return np.clip(probs, 0.0, 1.0)"
    )
    story.append(Preformatted(code_43, S["code"]))
    story.append(Spacer(1, 4))

    # 4.4
    story.append(Paragraph("4.4. Classificador Supervisionado (HistGradientBoosting) e Fallback para RandomForest", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Quando o taxonomista interage com a interface (adicionando sílabas perdidas ou excluindo ruídos), o sistema "
        "assimila esse conhecimento biológico humano e calibra um ensemble supervisionado de alta velocidade para "
        "propagar a diagnose correta ao restante da gravação.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O classificador primário é o <b>HistGradientBoostingClassifier</b> do scikit-learn. Sua principal vantagem matemática "
        "é a discretização dos atributos contínuos em histogramas inteiros de 256 bins inteiros de 8 bits (uint8). "
        "Isso reduz a complexidade de ordenação de divisões de nós de <b>O(N log N)</b> (GBDT clássico) para <b>O(N)</b>, "
        "permitindo o retreinamento do modelo em menos de 100 ms durante o clique do usuário.<br/>"
        "Hiperparâmetros configurados:<br/>"
        "• <i>Poucas amostras (N < 30):</i> max_iter=50, max_depth=3, min_samples_leaf=2, learning_rate=0.08, l2_regularization=2.0 (regularização forte contra overfitting);<br/>"
        "• <i>Amostras abundantes (N ≥ 30):</i> max_iter=80, max_depth=4, min_samples_leaf=5, learning_rate=0.08, l2_regularization=1.0, class_weight='balanced'.<br/>"
        "Caso o ambiente Python não possua os módulos C do histogram boosting, o sistema ativa fallback transparente para "
        "<code>RandomForestClassifier(n_estimators=80, max_depth=5, min_samples_split=6, class_weight='balanced', n_jobs=-1)</code>.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_44 = (
        "# Trecho de core/learner.py (PulseLearner._build_model)\n"
        "if HistGradientBoostingClassifier is not None:\n"
        "    if n_samples > 0 and n_samples < 30:\n"
        "        return HistGradientBoostingClassifier(\n"
        "            max_iter=50, max_depth=3, min_samples_leaf=2,\n"
        "            learning_rate=0.08, l2_regularization=2.0,\n"
        "            random_state=42, class_weight='balanced'\n"
        "        )\n"
        "    return HistGradientBoostingClassifier(\n"
        "        max_iter=80, max_depth=4, min_samples_leaf=5,\n"
        "        learning_rate=0.08, l2_regularization=1.0,\n"
        "        random_state=42, class_weight='balanced'\n"
        "    )\n"
        "elif RandomForestClassifier is not None:\n"
        "    return RandomForestClassifier(n_estimators=80, max_depth=5, class_weight='balanced', n_jobs=-1)"
    )
    story.append(Preformatted(code_44, S["code"]))
    story.append(Spacer(1, 4))

    # 4.5
    story.append(Paragraph("4.5. Mineração de Negativos Difíceis (Hard Negative Mining) e Poda Contrastiva", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Sons transientes espúrios como gotas de orvalho caindo no microfone ou cliques de insetos predadores podem exibir "
        "alta amplitude e enganar classificadores estatísticos convencionais. Quando o pesquisador clica para remover um falso "
        "positivo, o Crinômetro analisa o vetor de atributos desse negativo específico e induz regras determinísticas rígidas.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "Para métricas taxonômicas críticas (centroide, fator de crista, largura FWHM, tempo de subida 10-90%, roll-off e HNR), "
        "o algoritmo compara a distribuição dos pulsos confirmados (Válidos) contra os falsos positivos explícitos (FP). "
        "Se houver separação perfeita com gap positivo g > 0:<br/>"
        "• Caso 1 (min(V) > max(FP)): Threshold = max(FP) + 0.30 × g (regra: descartar se f<sub>i</sub> < Threshold);<br/>"
        "• Caso 2 (max(V) < min(FP)): Threshold = min(FP) - 0.30 × g (regra: descartar se f<sub>i</sub> > Threshold).<br/>"
        "A margem de 30% evita descartes de sílabas limítrofes. As regras atuam como um filtro prévio determinístico em tempo <b>O(1)</b>. "
        "Salvaguarda: se as regras podarem mais de 75% dos candidatos de uma nova gravação, a poda rígida é suspensa, "
        "restringindo-se apenas aos pulsos de baixíssima confiança.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_45 = (
        "# Trecho de core/learner.py (PulseLearner.induce_pruning_rules)\n"
        "min_val, max_val = float(np.min(v_val)), float(np.max(v_val))\n"
        "min_fp, max_fp = float(np.min(v_fp)), float(np.max(v_fp))\n"
        "if min_val > max_fp:\n"
        "    gap = min_val - max_fp\n"
        "    threshold = max_fp + 0.30 * gap  # Margem de segurança de 30%\n"
        "    new_rules.append({'feature': feat_name, 'op': '<', 'threshold': float(threshold)})\n"
        "elif max_val < min_fp:\n"
        "    gap = min_fp - max_val\n"
        "    threshold = min_fp - 0.30 * gap\n"
        "    new_rules.append({'feature': feat_name, 'op': '>', 'threshold': float(threshold)})"
    )
    story.append(Preformatted(code_45, S["code"]))
    story.append(Spacer(1, 4))

    # 4.6
    story.append(Paragraph("4.6. Pontuação Híbrida Ponderada e Resgate Contextual (Contextual Gating)", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A primeira e a última sílaba de um chilreio frequentemente possuem energia significativamente inferior às sílabas centrais "
        "devido à inércia do movimento de fechamento da asa. Um classificador estático descartaria essas sílabas de borda. "
        "O mecanismo de Resgate Contextual recupera esses pulsos periféricos se eles exibirem coerência sintática com o ritmo do chilreio.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "A decisão final combina a probabilidade a posteriori do ensemble supervisionado (peso 65%, refletindo a curadoria humana) "
        "com o prior não-supervisionado do GMM (peso 35%):",
        S["body"]
    ))
    story.append(Paragraph(
        "Score(p<sub>i</sub>) = 0,65 · P<sub>sup</sub>(y=1 | f<sub>i</sub>) + 0,35 · P<sub>GMM</sub>(Focal | z<sub>i</sub>)",
        S["formula"]
    ))
    story.append(Paragraph(
        "Pulsos com Score ≥ focal_sensitivity (padrão 0.60) são aprovados diretamente. Em seguida, executa-se o "
        "<b>Contextual Gating</b> iterativo (até 5 passagens de propagação temporal): qualquer pulso inicialmente descartado "
        "que esteja pareado com um pulso vizinho aprovado por intervalo biológico gap_min · 0.85 ≤ Δt ≤ gap_max · 1.15 "
        "e cuja amplitude atinja pelo menos 20% do vizinho é resgatado e reintegrado ao conjunto focal.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_46 = (
        "# Trecho de core/learner.py (PulseLearner.filter_peaks - Score Híbrido & Gating)\n"
        "combined_score = 0.65 * sup_probs + 0.35 * focal_priors\n"
        "kept_mask = (combined_score >= focal_sensitivity) & (amps >= 0.04)\n\n"
        "# Resgate Contextual iterativo por coerência de IPI fisiológico\n"
        "for _ in range(5):\n"
        "    changed = False\n"
        "    for i in range(n):\n"
        "        if not kept_mask[i] and combined_score[i] >= 0.35:\n"
        "            has_match = (i > 0 and kept_mask[i-1] and gap_min_s*0.85 <= (t[i]-t[i-1]) <= gap_max_s*1.15)\n"
        "            if has_match:\n"
        "                kept_mask[i] = True\n"
        "                changed = True\n"
        "    if not changed:\n"
        "        break"
    )
    story.append(Preformatted(code_46, S["code"]))
    story.append(Spacer(1, 4))

    # 4.7
    story.append(Paragraph("4.7. Ciclo de Feedback do Aprendizado Ativo em 5 Passos (subpassos a até g)", S["h2"]))
    story.append(Paragraph(
        "O aprendizado ativo do Crinômetro segue o paradigma de pool-based active learning em 5 passos formais:<br/>"
        "<b>Passo 1: Detecção Inicial DSP:</b> O pipeline processa o áudio bruto e gera candidatos preliminares baseados nas heurísticas de Hilbert e limiares adaptativos.<br/>"
        "<b>Passo 2: Classificação Automática:</b> O PulseLearner aplica o GMM e o classificador treinado, segregando cantos focais de ruídos.<br/>"
        "<b>Passo 3: Revisão Humana Interativa:</b> O taxonomista inspeciona o oscilograma/espectrograma. Marcadores incorretos são removidos (clique direito); sílabas omitidas são adicionadas (clique esquerdo).<br/>"
        "<b>Passo 4: Salvamento e Atualização Transacional com 7 Subpassos Obrigatórios:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>a)</i> Extração de 20 features de todos os pulsos validados (labels positivas y=1);<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>b)</i> Extração de features dos pulsos explicitamente removidos pelo usuário (labels negativas y=0);<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>c)</i> Mineração automática de negativos adicionais (silêncios e vales de baixa energia na gravação);<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>d)</i> Indução de regras de poda contrastivas (Hard Negatives) com margem de 30%;<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>e)</i> Acumulação no buffer circular histórico limitado a <b>5000 amostras</b> (preservando generalização);<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>f)</i> Retreinamento do classificador com o dataset balanceado e regularização L2;<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>g)</i> Serialização atômica segura via <code>skops.io</code> em <code>modelo_treinado.skops</code>.<br/>"
        "<b>Passo 5: Adaptação Paramétrica:</b> Calibração automática dos limiares de DSP (proeminência e tolerância) às características estatísticas da espécie anotada.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_47 = (
        "# Trecho de core/learner.py (PulseLearner.update_from_corrections)\n"
        "stacked = np.column_stack((X, y))\n"
        "_, first_idx = np.unique(stacked, axis=0, return_index=True)\n"
        "stacked = stacked[np.sort(first_idx)]\n"
        "self.training_features = stacked[:, :-1]\n"
        "self.training_labels = stacked[:, -1].astype(int)\n\n"
        "# Limite do buffer circular histórico de 5000 amostras\n"
        "_MAX_SAMPLES = 5000\n"
        "if len(self.training_features) > _MAX_SAMPLES:\n"
        "    self.training_features = self.training_features[-_MAX_SAMPLES:]\n"
        "    self.training_labels = self.training_labels[-_MAX_SAMPLES:]"
    )
    story.append(Preformatted(code_47, S["code"]))
    story.append(Spacer(1, 4))

    # 4.8
    story.append(Paragraph("4.8. Serialização Segura via `skops` e Desacoplamento de Locks de Concorrência", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A colaboração científica entre instituições e herbários/museus exige o compartilhamento de arquivos de modelos bioacústicos "
        "treinados para identificação de espécies crípticas. O formato clássico <code>.pkl</code> (Pickle) executa bytecode arbitrário "
        "durante o carregamento, representando uma grave vulnerabilidade de cibersegurança (RCE - Remote Code Execution). "
        "O Crinômetro v4.5.0 aboliu totalmente o pickle em prol do formato <code>skops</code> auditado.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O protocolo <code>skops.io</code> armazena a estrutura do modelo em árvore sintática tipada (AST) sem permitir instruções "
        "executáveis de baixo nível. Durante o carregamento, aplica-se uma lista branca estrita de tipos confiáveis: "
        "<code>HistGradientBoostingClassifier</code>, <code>RandomForestClassifier</code>, <code>np.ndarray</code>, "
        "<code>TreePredictor</code> e <code>Tree</code>. Qualquer objeto fora da lista branca aborta a leitura imediatamente.<br/>"
        "<b>Desacoplamento de Concorrência:</b> Para eliminar deadlocks clássicos do tipo AB-BA (onde duas threads competem "
        "pelo Lock do modelo ML e pelo Lock de gravação do JSON de configuração em ordens opostas), os locks <code>_model_lock</code> "
        "e <code>CONFIG_LOCK</code> jamais são aninhados; a serialização em memória ocorre sob o lock do modelo, liberando-o "
        "antes da aquisição do lock de gravação em disco.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_48 = (
        "# Trecho de core/learner.py (Serialização skops e Desacoplamento de Locks)\n"
        "def save_to_config(self):\n"
        "    with self._model_lock:\n"
        "        if self.model is None:\n"
        "            return False\n"
        "        serialized = self.serialize()  # Serializa sob _model_lock\n"
        "        rules = list(getattr(self, 'pruning_rules', []))\n"
        "    # _model_lock LIBERADO antes de adquirir CONFIG_LOCK (Evita Deadlock AB-BA)\n"
        "    with CONFIG_LOCK:\n"
        "        config['pulse_learner'] = serialized\n"
        "        atomic_write_json(self.config_path, config)\n\n"
        "# Carregamento auditado com lista branca em skops.io\n"
        "with open(target_path, 'rb') as f:\n"
        "    payload = skio.load(f, trusted=[\n"
        "        HistGradientBoostingClassifier, RandomForestClassifier,\n"
        "        np.ndarray, np.dtype, 'sklearn.tree._tree.Tree'\n"
        "    ])"
    )
    story.append(Preformatted(code_48, S["code"]))
    story.append(Spacer(1, 4))

    # Glossário Seção 4
    g4_items = [
        ("G-19", "Invariância a Ganho Linear", "Propriedade de descritores normalizados que mantêm seus valores idênticos mesmo se o ganho de captação for alterado."),
        ("G-20", "Gaussian Mixture Model (GMM)", "Modelo probabilístico generativo que ajusta componentes gaussianas multivariadas para identificar subpopulações de pulsos."),
        ("G-21", "HistGradientBoosting", "Ensemble de árvores de decisão impulsionadas por gradiente com discretização de atributos em histogramas de tempo O(N)."),
        ("G-22", "Contextual Gating", "Mecanismo bioacústico iterativo que resgata sílabas periféricas débeis desde que alinhadas ao ritmo estrito do chilreio."),
        ("G-23", "Serialização skops", "Formato seguro de armazenamento de modelos scikit-learn baseado em árvore de tipos, imune a injeções de bytecode executável."),
        ("G-24", "Desacoplamento de Locks AB-BA", "Padrão de concorrência que impede que duas threads tentem adquirir travas mútuas em ordem invertida, erradicando travamentos.")
    ]
    story.append(make_glossary_box("§4.0 - §4.8", g4_items, S))
    story.append(PageBreak())

    return story
