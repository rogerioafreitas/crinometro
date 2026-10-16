# DOCUMENTO 2: DOCUMENTAÇÃO TÉCNICA, MATEMÁTICA E BIOACÚSTICA — CRINÔMETRO v4.5.0

**Título Acadêmico:** Arquitetura Computacional, Processamento Digital de Sinais (DSP), Aprendizado Ativo e Metrologia Bioacústica de Alta Precisão para Sistemática e Descoberta Taxonômica em Orthoptera (Ensifera: Grylloidea)  
**Versão do Sistema:** Crinômetro v4.5.0 (Versão de Produção)  
**Padrão Terminológico Internacional:** Ragge & Reynolds (1998), Bennet-Clark (1999), Márquez et al. (2001), Baker & Chesmore (2020)

> **Axioma Metrológico da Versão 4.5.0:** O Crinômetro v4.5.0 é estritamente uma plataforma metrológica destinada à prospecção, diagnose e descrição formal de **novas espécies e táxons não descritos**. Toda e qualquer inferência ecológica indireta fundamentada em calibrações espécie-específicas pré-fixadas — notadamente a regressão linear termo-acústica de Dolbear (1897) — foi **erradicada da arquitetura v4.5.0**. Como a relação entre taxa de repetição de sílabas e temperatura ambiente depende de coeficientes metabólicos, massa torácica e cinética enzimática exclusivos de cada espécie, aplicar equações pré-calibradas de *Oecanthus fultoni* ou *Gryllus campestris* a táxons neotropicais inéditos violaria a independência taxonômica do instrumento.

---

## SUMÁRIO COMPLETO

- **1.0. Módulo I — Condicionamento de Sinal, Acústica Física e Pré-Filtragem Digital**
  - 1.1. Bloco A: Fundamentos Físicos e Bioacústicos (Biofísica da Estridulação, SNR, Microfonia e Critério de Nyquist-Shannon)
  - 1.2. Bloco B: Formulação Matemática e DSP (Seleção de Canal por RMS, Filtro Passa-Altas Anti-Vento e Passa-Faixa Butterworth de Fase Zero via SOS)
  - 1.3. Bloco C: Arquitetura de Software, Concorrência e Código (`CricketAnalyzer.analyze` em `core/analyzer.py`)
- **2.0. Módulo II — Análise Espectral, STFT, Método de Welch e Rastreamento Sub-Bin da Portadora**
  - 2.1. Bloco A: Fundamentos Físicos e Bioacústicos (Ressonância da Harpa/Espelho, Portadora vs. Modulação AM e Coros Simpátricos)
  - 2.2. Bloco B: Formulação Matemática e DSP (STFT de Gabor-Heisenberg, Interpolação Parabólica Sub-Bin de Smith e PSD de Welch)
  - 2.3. Bloco C: Arquitetura de Software, Concorrência e Código (Vetorização Sub-Bin, `compute_psd` e Real-Time Tolerance Filtering)
- **3.0. Módulo III — Envoltória Analítica de Hilbert, Morfologia de Pulsos e Sintaxe Temporal de Chilreios**
  - 3.1. Bloco A: Fundamentos Físicos e Bioacústicos (Plectrum, Pars Stridens, Pulsos, Sílabas, Chilreios/Echemas e Gerador Central de Padrões — CPG)
  - 3.2. Bloco B: Formulação Matemática e DSP (Transformada de Hilbert, Métricas a $-3\text{ dB}$ e $-6\text{ dB}$, IPI, ICI, PRR, Duty Cycle, Assimetria e Regressão Rítmica)
  - 3.3. Bloco C: Arquitetura de Software, Concorrência e Código (`regroup_chirps`, Filtro de Coerência Rítmica $O(N)$ e `analyze_rhythmic_cadence`)
- **4.0. Módulo IV — Aprendizado de Máquina Híbrido, Engenharia de Atributos e Serialização Segura (`skops`)**
  - 4.1. Bloco A: Fundamentos Físicos e Bioacústicos (Segregação de Indivíduo Focal vs. Coro Polifônico e invariância a ganho)
  - 4.2. Bloco B: Formulação Matemática e DSP (Vetor de 20 Atributos Bioacústicos, GMM Bimodal, HistGradientBoosting, Score Híbrido e Poda Contrastiva)
  - 4.3. Bloco C: Arquitetura de Software, Concorrência e Código (`PulseLearner`, Auditoria de AST com `skops`, Desacoplamento de Locks e Fallback Resiliente)
- **5.0. Módulo V — Computação Gráfica de Alta Performance (Min-Max LoD, Raster Blitting e Poda Espacial)**
  - 5.1. Bloco A: Fundamentos Físicos e Bioacústicos (Preservação Visual de Transientes Rápidos e Percepção Multiescala)
  - 5.2. Bloco B: Formulação Matemática e DSP (Teorema de Preservação de Extremos Min-Max LoD, Stride Slicing 2D e Busca Binária de Hover)
  - 5.3. Bloco C: Arquitetura de Software, Concorrência e Código (`HighPerfLineEngine`, `HighPerfSpectrogramEngine`, `NavigationController` e `FigureFactory`)
- **6.0. Módulo VI — Arquitetura Desacoplada v4.5.0, Concorrência Qt e Persistência Transacional Atômica**
  - 6.1. Bloco A: Fundamentos Físicos e Bioacústicos (Rastreabilidade Metrológica e Reprodutibilidade Experimental em Lote)
  - 6.2. Bloco B: Formulação Matemática e Modelo Formal de Concorrência (Grafo Acíclico de Locks, Deadline Monotônico e Atomicidade POSIX/NTFS)
  - 6.3. Bloco C: Arquitetura de Software, Concorrência e Código (`SessionContext`, Mediadores `ui/controllers/*`, `WorkerRegistry` e `utils/persistence.py`)
- **7.0. Seção Modelo "Materiais e Métodos" para Publicação Científica**
- **8.0. Índice Remissivo de Referências Cruzadas (Fórmulas $\leftrightarrow$ Classes $\leftrightarrow$ Seções)**

---

## 1.0. Módulo I — Condicionamento de Sinal, Acústica Física e Pré-Filtragem Digital

> ┌──────────────────────────────────────────────────────────────────────────────────────────┐
> │ GLOSSÁRIO TÉCNICO & BIOACÚSTICO DA PÁGINA                                                │
> │ • Aparelho Estridulatório [Ref: §1.1]: Complexo mecanorressonante nas tégminas de        │
> │   Ensifera composto pela lima quitinosa (pars stridens) e pelo plectro (plectrum).       │
> │ • Critério de Nyquist-Shannon [Ref: §1.1]: Teorema que exige taxa de amostragem          │
> │   $f_s > 2 f_{\max}$ para reconstrução exata sem dobramento espectral (aliasing).        │
> │ • Comb Filtering (Filtro Pente) [Ref: §1.2]: Cancelamento destrutivo periódico causado   │
> │   pela soma de sinais defasados provenientes de múltiplos transdutores acústicos.        │
> │ • SOS (Second-Order Sections) [Ref: §1.2]: Decomposição matricial em cascata de filtros  │
> │   biquadráticos de 2ª ordem que previne overflow de coeficientes em ordens elevadas.     │
> │ • Filtragem Zero-Phase (sosfiltfilt) [Ref: §1.2]: Aplicação bidirecional (direta e       │
> │   reversa) de um filtro IIR, anulando o atraso de grupo ($\tau_g(\omega) = 0$).          │
> └──────────────────────────────────────────────────────────────────────────────────────────┘

---

### 1.1. BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS

#### 1.1.1. Biofísica da Estridulação Tegminal
Nos ortópteros da subordem Ensifera (superfamília Grylloidea), a emissão acústica resulta de um processo de excitação mecânica por fricção intermitente (*stick-slip friction*) entre as duas asas anteriores coriáceas modificadas (**tégminas**). Na face ventral da veia cubital anterior ($\text{CuA}$) da tégmina superior (tipicamente a direita em Gryllidae), encontra-se a **lima estridulatória** (*pars stridens* ou *file*), constituída por uma série linear de $N_d \in [40, 350]$ lamelas ou dentes quitinosos microscopicamente espaçados. Na margem anal interna da tégmina oposta situa-se uma nervura fortemente esclerotizada em forma de cunha, o **plectro** (*plectrum* ou *scraper*).

Durante a fase ativa do canto (normalmente a adução ou fechamento tegminal), a contração dos músculos tergocoxais e basilares desloca o plectro ao longo da *pars stridens* com velocidade tangencial $v_p(t)$. Se o espaçamento interdental no ponto de contato é $d_z$, a taxa de impacto dentário (*tooth-strike rate*) impõe uma força impulsiva periódica de frequência fundamental:

$$f_c(t) = \frac{v_p(t)}{d_z}$$

Para que o pulso não se dissipe como uma sucessão ineficiente de estalos de banda larga, os grilos desenvolveram um mecanismo de **escape com trava de fase (*clockwork escapement*)** (Bennet-Clark, 1999): a taxa de impacto dentário $f_c$ acopla-se ao modo fundamental de vibração das células membranosas especializadas da tégmina — a **harpa** (*harp*, delimitada pelas veias $\text{CuA}_1$ e $\text{CuA}_2$) e o **espelho** (*mirror*). Essas células funcionam como dipolos acústicos suspensos com elevado fator de qualidade mecânica ($Q \in [15, 35]$), radiando uma onda sonora quase-senoidal de alta pureza espectral.

#### 1.1.2. Relação Sinal-Ruído (SNR) em Campo e Interferências Ambientais
Em levantamentos bioacústicos de campo destinados à descrição de novas espécies, a pressão sonora captada pelo microfone $x(t)$ é a superposição linear do sinal do espécime focal $s(t)$ e de três classes de perturbações estocásticas e determinísticas:

$$x(t) = s(t) + n_{\text{aero}}(t) + \sum_{m=1}^{M} c_m(t) + n_{\text{ant}}(t) + n_{\text{term}}(t)$$

1. **Turbulência Aerodinâmica e Vibração Mecânica ($n_{\text{aero}}$):** Rajadas de vento sobre a cápsula do microfone e vibrações do suporte geram energia infrassônica e de baixa frequência ($< 150\text{ Hz}$) com densidade espectral proporcional a $1/f^{\alpha}$ ($\alpha \in [2, 4]$), cuja amplitude pode exceder em $+40\text{ dB}$ a pressão sonora do inseto.
2. **Coros Heteroespecíficos e Coespecíficos Simpátricos ($\sum c_m(t)$):** Outros ortópteros, anuros e cicadídeos vocalizando simultaneamente no mesmo estrato vegetacional.
3. **Ruído Antropogênico e Harmônicos de Rede ($n_{\text{ant}}$):** Tráfego rodoviário ($50\text{–}1000\text{ Hz}$) e indução eletromagnética de linhas de transmissão ($50/60\text{ Hz}$ e seus harmônicos ímpares).
4. **Ruído Térmico de Pré-Amplificação ($n_{\text{term}}$):** Ruído branco gaussiano intrínseco aos transistores do pré-amplificador e conversor A/D.

#### 1.1.3. Limitações de Transdutores, Taxa de Amostragem ($f_s$) e Critério de Nyquist-Shannon
Pelo **Teorema da Amostragem de Nyquist-Shannon**, um sinal contínuo de banda limitada com frequência máxima $f_{\max}$ é univocamente representado por suas amostras discretas $x[n] = x(n / f_s)$ se e somente se a frequência de Nyquist $f_{\text{Nyq}} = f_s / 2$ satisfizer:

$$f_{\text{Nyq}} = \frac{f_s}{2} > f_{\max}$$

Na bioacústica de Grylloidea:
- Espécies das subfamílias Gryllinae, Nemobiinae e Oecanthinae exibem frequências portadoras fundamentais entre $2,0\text{ kHz}$ e $8,5\text{ kHz}$, mas possuem transientes de ataque e harmônicos superiores ($2f_c, 3f_c$) que se estendem até $20\text{ kHz}$, exigindo no mínimo $f_s = 44,1\text{ kHz}$ ou $48,0\text{ kHz}$.
- Espécies neotropicais de Eneopterinae (tribos Lebinthini e Xenogryllini), Phalangopsidae e Trigonidiidae frequentemente evoluíram portadoras de alta frequência ou **ultrassônicas** ($f_c \in [12\text{ kHz}, 35\text{ kHz}]$). Para tais táxons, gravações a $44,1\text{ kHz}$ ($f_{\text{Nyq}} = 22,05\text{ kHz}$) sofrem dobramento espectral (*aliasing*) ou rejeição pelo filtro anti-aliasing do hardware. O Crinômetro v4.5.0 adapta dinamicamente todos os seus filtros digitais à frequência de Nyquist real do arquivo ($f_{\text{Nyq}} = 0,5 \cdot \text{rate}$), suportando gravações ultrassônicas de até $384\text{ kHz}$ e emitindo exceção explícita (`ValueError`) caso $f_{\text{Nyq}}$ seja incompatível com a banda paramétrica configurada.

---

### 1.2. BLOCO B: FORMULAÇÃO MATEMÁTICA E DSP

#### 1.2.1. Seleção de Canal Estéreo por Máxima Energia RMS (Prevenção de *Comb Filtering*)
Seja uma gravação multicanal $\mathbf{X} \in \mathbb{R}^{N \times C}$ com $N$ amostras e $C \ge 2$ canais. Se dois microfones espaçados por uma distância $d$ captam uma onda plana de frequência $f_c$ incidente sob ângulo $\theta$, a diferença de caminho acústico $\Delta r = d \sin\theta$ introduz um atraso interaural $\Delta t = \Delta r / c_{\text{som}}$ ($c_{\text{som}} \approx 343\text{ m/s}$). A soma aritmética ingênua dos dois canais produz uma função de transferência com zeros periódicos:

$$\left| H_{\text{soma}}(f) \right| = \left| \cos\left( \frac{\pi f d \sin\theta}{c_{\text{som}}} \right) \right|$$

Para $f_c = 5000\text{ Hz}$ ($\lambda = 6,86\text{ cm}$), uma diferença de percurso de apenas $\lambda / 2 = 3,43\text{ cm}$ anula completamente a portadora ($\left| H_{\text{soma}}(f_c) \right| = 0$). Para erradicar esse defeito, o Crinômetro v4.5.0 calcula o valor eficaz (**RMS — Root Mean Square**) de cada canal $c \in \{0, \dots, C-1\}$ e seleciona o canal de maior energia:

$$\text{RMS}_c = \sqrt{\frac{1}{N} \sum_{n=0}^{N-1} X_{n, c}^2}, \qquad c^* = \arg\max_{c \in \{0, \dots, C-1\}} \text{RMS}_c, \qquad x_0[n] = X_{n, c^*}$$

Em seguida, o componente de corrente contínua (*DC offset*) é removido por centralização na média amostral:

$$x_{\text{DC}}[n] = x_0[n] - \frac{1}{N} \sum_{k=0}^{N-1} x_0[k]$$

#### 1.2.2. Pré-Filtragem Passa-Altas e Passa-Faixa Butterworth de Fase Zero (SOS)
Um filtro analógico Butterworth passa-baixas normalizado de ordem $n$ possui função de transferência no plano complexo de Laplace $s = \sigma + j\omega$ dada por:

$$H(s) = \frac{1}{\prod_{k=1}^{n/2} \left( s^2 - 2s \cos\left(\frac{2k + n - 1}{2n}\pi\right) + 1 \right)}$$

cuja resposta em magnitude quadrática é maximamente plana na origem ($\frac{d^m |H(j\omega)|}{d\omega^m}\big|_{\omega=0} = 0$ para $m = 1, \dots, 2n-1$), garantindo **ausência absoluta de ondulações (*ripple*) na banda passante** que poderiam deformar o envelope temporal dos pulsos:

$$\left| H(j\omega) \right|^2 = \frac{1}{1 + \left(\frac{\omega}{\omega_c}\right)^{2n}}$$

Para transformar o protótipo analógico em um filtro passa-faixa digital com frequências de corte físicas $[f_{\text{low}}, f_{\text{high}}] = [\text{b1\_min}, \text{b1\_max}]$, aplica-se a transformação de frequência passa-baixas para passa-faixa seguida da **Transformação Bilinear** com pré-deformação (*pre-warping*) de frequência ($\Omega = \frac{2}{T_s} \tan\left(\frac{\omega T_s}{2}\right)$).

Como polinômios de ordem elevada na forma direta $(b, a)$ sofrem severa instabilidade numérica de quantização de polos quando $f_c \ll f_s$ (típico em gravações de alta taxa de amostragem), o Crinômetro fatora a função de transferência digital $H(z)$ em $K$ **Seções de Segunda Ordem (SOS — Biquads)**:

$$H(z) = \prod_{k=1}^{K} H_k(z) = \prod_{k=1}^{K} \frac{b_{0,k} + b_{1,k} z^{-1} + b_{2,k} z^{-2}}{1 + a_{1,k} z^{-1} + a_{2,k} z^{-2}}$$

Mais ainda, em vez da filtragem causal unidirecional (`sosfilt`), que introduz distorção de fase não-linear, o Crinômetro v4.5.0 aplica **filtragem bidirecional de fase zero (`sosfiltfilt`)**: o sinal é filtrado na direção temporal direta e o resultado revertido é filtrado novamente na direção reversa. No domínio $z$, a operação equivale a:

$$Y(z) = H(z) \cdot H(z^{-1}) \cdot X(z) = \left| H\left(e^{j\omega}\right) \right|^2 X\left(e^{j\omega}\right)$$

1. **Consequência Metrológica 1 (Fase Zero):** A fase líquida do filtro é identicamente nula ($\angle \left|H(e^{j\omega})\right|^2 \equiv 0$, atraso de grupo $\tau_g(\omega) = 0$). Os instantes de início (*onset*), pico (*peak*) e fim (*offset*) de cada pulso permanecem cravados no milissegundo real da gravação.
2. **Consequência Metrológica 2 (Duplicação da Ordem Efetiva):** O filtro passa-altas anti-vento de $2^{\text{a}}$ ordem ($f_c = 50\text{ Hz}$) opera com ordem efetiva $2n = 4$ ($24\text{ dB/oitava}$), e o filtro passa-faixa de $4^{\text{a}}$ ordem ($[\text{b1\_min}, \text{b1\_max}]$) opera com ordem efetiva $2n = 8$ ($48\text{ dB/oitava}$ de rejeição fora da banda).

---

### 1.3. BLOCO C: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E CÓDIGO

A implementação canônica encontra-se em [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L39-L105) no módulo [`core/analyzer.py`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py):

```python
# Trecho real de core/analyzer.py (CricketAnalyzer.analyze)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", WavFileWarning)
    rate, raw = wavfile.read(file_path)
if rate <= 0:
    raise ValueError(f"Taxa de amostragem inválida: {rate}")
raw = np.asarray(raw)
if raw.size == 0:
    raise ValueError("O arquivo de áudio está vazio.")
if raw.ndim > 1:
    data = raw.astype(np.float64)
    if not np.isfinite(data).all():
        raise ValueError("O arquivo contém valores NaN/Inf.")
    # Seleção do canal de maior energia RMS (previne comb filtering em estéreo)
    rms = np.sqrt(np.mean(data ** 2, axis=0))
    data = data[:, int(np.argmax(rms))]
else:
    data = raw.astype(np.float64)
if not np.isfinite(data).all():
    raise ValueError("O arquivo contém valores NaN/Inf.")

# Remove offset DC e ruídos de baixa frequência / vento (< 50 Hz) com Fase Zero
data = data - np.mean(data)
nyq = 0.5 * rate
if rate > 120.0 and nyq > 50.0:
    sos_dc = butter(2, 50.0 / nyq, btype='high', output='sos')
    data = sosfiltfilt(sos_dc, data)

# Filtragem passa-faixa Butterworth IIR de 4ª ordem (8ª ordem efetiva zero-phase)
b1_max = min(nyq - 20.0, float(params.get("b1_max", 6000)))
b1_min = max(20.0, float(params.get("b1_min", 3200)))
if b1_max - b1_min < 100.0:
    raise ValueError(
        f"Taxa de amostragem de {rate} Hz incompatível com a banda configurada "
        f"({b1_min:.0f}–{float(params.get('b1_max', 6000)):.0f} Hz; Nyquist = {nyq:.0f} Hz)."
    )
sos_b1 = butter(4, [b1_min / nyq, b1_max / nyq], btype='band', output='sos')
data_b1 = sosfiltfilt(sos_b1, data)
```

---

## 2.0. Módulo II — Análise Espectral, STFT, Método de Welch e Rastreamento Sub-Bin da Portadora

> ┌──────────────────────────────────────────────────────────────────────────────────────────┐
> │ GLOSSÁRIO TÉCNICO & BIOACÚSTICO DA PÁGINA                                                │
> │ • Frequência Portadora ($f_c$) [Ref: §2.1]: Frequência fundamental de maior densidade    │
> │   energética emitida pelo ressonador alar durante a estridulação.                        │
> │ • Princípio da Incerteza de Gabor-Heisenberg [Ref: §2.2]: Limite fundamental             │
> │   $\sigma_t \cdot \sigma_f \ge \frac{1}{4\pi}$ entre localização temporal e frequencial. │
> │ • Interpolação Parabólica Sub-Bin [Ref: §2.2]: Ajuste quadrático de 3 bins espectrais    │
> │   adjacentes em dB para estimar o ápice contínuo da frequência com erro $<\Delta f / 10$.│
> │ • Método de Welch (PSD) [Ref: §2.2]: Estimador de densidade espectral de potência de     │
> │   variância reduzida obtido pela média de periodogramas modificados janelados.           │
> └──────────────────────────────────────────────────────────────────────────────────────────┘

---

### 2.1. BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS

#### 2.1.1. Frequência Portadora (*Carrier Frequency*) vs. Modulação de Amplitude (AM)
O sinal estridulatório $s(t)$ de um grilo pode ser modelado fisicamente como uma portadora quase-harmônica $\cos(2\pi f_c(t) t + \phi_0)$ modulada em amplitude por um trem de pulsos $A(t) \ge 0$ gerado pelo fechamento cíclico das tégminas:

$$s(t) = A(t) \cdot \cos\left( 2\pi \int_{0}^{t} f_c(\tau)\, d\tau + \phi_0 \right)$$

Em muitos gêneros de Grylloidea (como *Oecanthus*, *Gryllus*, *Anurogryllus* e *Eneoptera*), a velocidade do plectro desacelera ligeiramente no terço final de cada dente da *pars stridens*, gerando uma sutil modulação de frequência intra-pulso (*downward frequency modulation* ou *chirp gliding* de $50\text{ a }250\text{ Hz}$). Além disso, em habitats neotropicais megadiversos, é comum que $3\text{ a }6$ espécies de ortópteros ocupem nichos acústicos adjacentes (*Acoustic Niche Hypothesis* — Krause, 1993), particionando o espectro de frequências em bandas separadas por apenas $400\text{ a }800\text{ Hz}$.

Portanto, um sistema metrológico deve cumprir duas tarefas espectrais distintas:
1. **Alta Resolução Temporal (STFT + Interpolação Sub-Bin):** Medir a frequência dominante instantânea $f_{\text{dom}}(t_i)$ exatamente no milissegundo em que cada pulso $i$ atinge seu ápice, permitindo segregar pulsos do indivíduo focal daqueles emitidos por indivíduos de outras espécies.
2. **Alta Resolução Espectral Estacionária (PSD de Welch):** Estimar a assinatura energética global em $\text{dB/Hz}$ com variância estatística mínima para caracterização taxonômica da frequência portadora e de seus harmônicos.

---

### 2.2. BLOCO B: FORMULAÇÃO MATEMÁTICA E DSP

#### 2.2.1. Transformada de Fourier de Tempo Curto (STFT) e Limite de Gabor-Heisenberg
Para um sinal discreto $x[n]$ amostrado a $f_s$, a **Transformada de Fourier de Tempo Curto (STFT)** com janela deslizante $w[m]$ de comprimento $N_w = 1024$ amostras e passo de avanço (*hop size*) $H = N_w - N_{\text{overlap}} = 1024 - 768 = 256$ amostras ($75\%$ de sobreposição) é definida no quadro temporal $m$ e bin de frequência $k \in \{0, 1, \dots, N_w/2\}$ por:

$$X[k, m] = \sum_{n=0}^{N_w - 1} x[n + mH]\, w[n]\, e^{-j \frac{2\pi k n}{N_w}}$$

onde $w[n]$ é a **janela de Hann** (cosseno elevado), escolhida por apresentar atenuação de lóbulos laterais de $-31,5\text{ dB}$ e decaimento assintótico de $-18\text{ dB/oitava}$, suprimindo o vazamento espectral (*spectral leakage*):

$$w[n] = 0,5 \left[ 1 - \cos\left( \frac{2\pi n}{N_w - 1} \right) \right], \qquad n = 0, 1, \dots, N_w - 1$$

Pelo **Princípio da Incerteza de Gabor-Heisenberg**, os desvios padrões temporal ($\sigma_t$) e frequencial ($\sigma_f$) de qualquer átomo tempo-frequência satisfazem:

$$\sigma_t \cdot \sigma_f \ge \frac{1}{4\pi}$$

Com $N_w = 1024$ e $H = 256$, para $f_s = 48.000\text{ Hz}$, obtemos espaçamento entre quadros $\Delta t = H / f_s = 5,33\text{ ms}$ e largura de bin $\Delta f = f_s / N_w = 46,875\text{ Hz}$ (para $f_s = 44.100\text{ Hz}$, $\Delta t = 5,80\text{ ms}$ e $\Delta f = 43,07\text{ Hz}$). O espectrograma de potência unilateral é convertido para escala logarítmica com piso numérico estabilizador $\epsilon_{\text{spec}} = 10^{-10}$ ($-100\text{ dB}$):

$$S_{\text{dB}}[k, m] = 10 \log_{10}\left( S_{xx}[k, m] + 10^{-10} \right)$$

#### 2.2.2. Refinamento Sub-Bin Parabólico de Frequência (Método de Smith-Serra)
Como a grade discreta $\Delta f \approx 43\text{–}47\text{ Hz}$ é grosseira demais para aferir microvariações da portadora, para cada coluna temporal $m$, localiza-se o índice de pico $k^*_m = \arg\max_{k \in \mathcal{B}_1} S_{xx}[k, m]$ dentro da banda estridulatória $\mathcal{B}_1 = [\text{b1\_min}, \text{b1\_max}]$. Como a transformada de Fourier de uma janela de Hann aproximada em escala logarítmica ao redor do lóbulo principal segue um perfil gaussiano/parabólico, ajustamos uma parábola aos três bins adjacentes em decibéis:

$$\alpha_m = 10 \log_{10}\left(S_{xx}[k^*_m - 1, m] + 10^{-12}\right), \quad \beta_m = 10 \log_{10}\left(S_{xx}[k^*_m, m] + 10^{-12}\right), \quad \gamma_m = 10 \log_{10}\left(S_{xx}[k^*_m + 1, m] + 10^{-12}\right)$$

O deslocamento fracionário do vértice da parábola $p_m \in [-0,5, +0,5]$ e a frequência dominante contínua refinada $f_{\text{dom}}(t_m)$ são dados analiticamente por:

$$p_m = \frac{1}{2} \frac{\alpha_m - \gamma_m}{\alpha_m - 2\beta_m + \gamma_m}, \qquad f_{\text{dom}}(t_m) = f[k^*_m] + p_m \cdot \Delta f$$

reduzindo o erro máximo de quantização espectral em uma ordem de grandeza (para $\sim \pm 2\text{ a }4\text{ Hz}$).

#### 2.2.3. Estimação de Densidade Espectral de Potência pelo Método de Welch
Para estimar a densidade espectral de potência estacionária $P_{xx}(f)$ ($\text{W/Hz}$ convertida em $\text{dB/Hz}$), o sinal condicionado de comprimento $N$ é particionado em $L$ segmentos sobrepostos em $50\%$ de comprimento $M_{\text{psd}} = \min\left(N, \lfloor 0,05 \cdot f_s \rfloor\right)$ (janela de $50\text{ ms}$, fornecendo resolução espectral exata $\Delta f_{\text{PSD}} = 20\text{ Hz}$ independentemente da taxa de amostragem $f_s$). O periodograma modificado do $l$-ésimo segmento com janela de Hann $w[n]$ e fator de normalização de potência $U = \frac{1}{M_{\text{psd}}} \sum_{n=0}^{M_{\text{psd}}-1} w^2[n]$ é:

$$\hat{P}_l(f_k) = \frac{1}{f_s M_{\text{psd}} U} \left| \sum_{n=0}^{M_{\text{psd}}-1} x\left[n + l \frac{M_{\text{psd}}}{2}\right] w[n]\, e^{-j \frac{2\pi k n}{M_{\text{psd}}}} \right|^2$$

A estimativa de Welch $S_{xx}(f_k)$ é a média aritmética sobre os $L$ segmentos (reduzindo a variância do estimador por um fator proporcional a $9L/11$), seguida da conversão logarítmica com piso numérico estrito $\epsilon = 10^{-12}$ ($-120\text{ dB/Hz}$):

$$S_{xx}(f_k) = \frac{1}{L} \sum_{l=0}^{L-1} \hat{P}_l(f_k), \qquad P_{xx}(f_k) = 10 \log_{10}\left( \max\left(S_{xx}(f_k), 10^{-12}\right) \right)$$

#### 2.2.4. Estimador Ponderado de Frequência Portadora Modal ($f_c$)
Seja $\mathcal{P}_{\text{prelim}}$ o conjunto de pulsos pertencentes aos chilreios preliminares (ou, na ausência destes, os $35\%$ pulsos de maior amplitude da gravação). Para cada pulso $i \in \mathcal{P}_{\text{prelim}}$ no instante $t_i = \text{idx}_i / f_s$, obtém-se sua frequência instantânea por interpolação linear $f_i = \text{interp}(t_i, \mathbf{t}_{\text{spec}}, \mathbf{f}_{\text{dom}})$ e sua amplitude de envelope $a_i = E[\text{idx}_i]$.

Constrói-se um histograma espectral ponderado pelas amplitudes $a_i$ com largura de classe $\Delta_{\text{bin}} = 50\text{ Hz}$. Seja $b^* = \arg\max_b \sum_{i \in \text{Bin}_b} a_i$ o bin modal de maior peso energético. A frequência portadora $f_c$ do espécime é calculada pela **média ponderada por amplitude na vizinhança de $\pm 150\text{ Hz}$ ao redor do centro do bin modal** $f_{\text{center}}(b^*)$:

$$\mathcal{V} = \left\{ i \in \mathcal{P}_{\text{prelim}} \;\middle|\; \left| f_i - f_{\text{center}}(b^*) \right| \le 150\text{ Hz} \right\}, \qquad f_c = \frac{\sum_{i \in \mathcal{V}} a_i f_i}{\sum_{i \in \mathcal{V}} a_i}$$

---

### 2.3. BLOCO C: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E CÓDIGO

Abaixo apresenta-se a implementação exata da estimação de Welch (`compute_psd`), do refinamento parabólico sub-bin vetorizado e da estimação da portadora modal em [`core/analyzer.py`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L25-L37):

```python
# Trecho real de core/analyzer.py: Método de Welch e Refinamento Sub-Bin Vetorizado
@staticmethod
def compute_psd(data, sr):
    """Calcula o Espectro de Potência Médio (PSD) usando o método de Welch com janela Hann."""
    nperseg = min(len(data), int(sr * 0.05))  # Janela de 50ms para boa resolução espectral (20 Hz)
    f, Pxx = welch(data, sr, window='hann', nperseg=nperseg, scaling='density')
    with np.errstate(divide='ignore', invalid='ignore'):
        Pxx_db = 10 * np.log10(np.clip(Pxx, 1e-12, None))
    # Remove a componente DC (f=0) para evitar artefato vertical na origem
    return f[1:], Pxx_db[1:]
```

```python
# Refinamento parabólico sub-bin contínuo da frequência dominante (vetorizado em core/analyzer.py)
df = float(f_spec[1] - f_spec[0]) if len(f_spec) > 1 else 1.0
valid_k = (dom_freq_idx > 0) & (dom_freq_idx < Sxx.shape[0] - 1)
valid_cols = np.where(valid_k)[0]
if len(valid_cols) > 0:
    k_v = dom_freq_idx[valid_cols]
    s_prev = 10.0 * np.log10(Sxx[k_v - 1, valid_cols] + 1e-12)
    s_curr = 10.0 * np.log10(Sxx[k_v, valid_cols] + 1e-12)
    s_next = 10.0 * np.log10(Sxx[k_v + 1, valid_cols] + 1e-12)
    denom = s_prev - 2.0 * s_curr + s_next
    nonzero = np.abs(denom) > 1e-9
    delta = np.zeros_like(denom, dtype=np.float64)
    delta[nonzero] = 0.5 * (s_prev[nonzero] - s_next[nonzero]) / denom[nonzero]
    delta = np.clip(delta, -0.5, 0.5)
    dom_freqs[valid_cols] = f_spec[k_v] + delta * df
```

Quando o usuário move o slider de tolerância espectral na interface, [`PipelineOrchestrator._execute_realtime_freq_tolerance`](file:///m:/Documentos/Faculdade/Biologia/ui/controllers/pipeline_orchestrator.py#L519-L645) reaproveita a matriz STFT em cache (`t_spec`, `dom_freqs`) e reclassifica todos os pulsos em menos de $5\text{ ms}$, preservando de forma transacional quaisquer adições (`_manual_added`) ou exclusões (`_manual_removed`) feitas manualmente pelo pesquisador.

---

## 3.0. Módulo III — Envoltória Analítica de Hilbert, Morfologia de Pulsos e Sintaxe Temporal de Chilreios

> ┌──────────────────────────────────────────────────────────────────────────────────────────┐
> │ GLOSSÁRIO TÉCNICO & BIOACÚSTICO DA PÁGINA                                                │
> │ • Pulso / Sílaba (Pulse / Syllable) [Ref: §3.1]: Unidade acústica elementar produzida    │
> │   por um único movimento de abertura ou fechamento tegminal.                             │
> │ • Chilreio / Echema (Chirp / Echeme) [Ref: §3.1]: Agrupamento de primeira ordem de       │
> │   sílabas/pulsos separado por intervalos inter-chilreio (ICI).                           │
> │ • Transformada de Hilbert ($\mathcal{H}$) [Ref: §3.2]: Operador linear singular que      │
> │   desloca a fase das componentes de frequência positivas em $-\pi/2\text{ rad}$.         │
> │ • Duty Cycle (Ciclo de Trabalho) [Ref: §3.2]: Razão adimensional entre a duração ativa   │
> │   do pulso ($d_p$) e o período total do ciclo de repetição ($T_{\text{ciclo}}$).         │
> │ • Portão ICI (ICI Gate) [Ref: §3.2]: Filtro de período refratário neuromotor que funde   │
> │   sub-trens separados por pausas inferiores a $70\%$ do ICI mediano.                     │
> └──────────────────────────────────────────────────────────────────────────────────────────┘

---

### 3.1. BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS

#### 3.1.1. Hierarquia Temporal: Transientes, Pulsos, Sílabas, Trilos, Chilreios e Echemas
Segundo a nomenclatura bioacústica unificada para Orthoptera (Ragge & Reynolds, 1998; Baker & Chesmore, 2020):
1. **Transiente Dentário (*Tooth Impact Transient*):** Impulso individual sub-milissegundo gerado pela colisão do plectro contra um único dente da *pars stridens*.
2. **Pulso / Hemissílaba (*Pulse / Hemisyllable*):** Trem coerente de ondas amortecidas produzido por um único curso unidirecional das tégminas (tipicamente a adução/fechamento; a abdução/abertura é geralmente silenciosa ou produz uma hemissílaba de baixa amplitude).
3. **Chilreio / Echema (*Chirp / Echeme*):** Agrupamento discreto de $N_p \in [\text{min\_p}, \text{max\_p}]$ pulsos sucessivos separados por **Intervalos Inter-Pulso ($\text{IPI}$)** curtos ($15\text{–}45\text{ ms}$), sendo cada chilreio isolado do próximo por um **Intervalo Inter-Chilreio ($\text{ICI}$)** longo ($100\text{–}1500\text{ ms}$).
4. **Trilo (*Trill*):** Sequência contínua de dezenas ou centenas de pulsos emitidos sem pausas inter-chilreio discerníveis (comum em Oecanthinae e Trigonidiidae).

#### 3.1.2. Gerador Central de Padrões (CPG) e Ausência Deliberada de Inferência Térmica
O ritmo temporal da estridulação é comandado por uma rede de interneurônios nos gânglios mesotorácico e metatorácico denominada **Gerador Central de Padrões (CPG — *Central Pattern Generator*)**. Embora a cinética de despolarização neuronal do CPG em artrópodes ectotérmicos responda à temperatura ambiente segundo uma relação de Arrhenius, a inclinação e o intercepto dessa curva variam drasticamente entre gêneros, espécies crípticas e populações alopátricas (Walker, 1962).

Por essa razão científica fundamental, **o Crinômetro v4.5.0 não inclui nem executa estimativas de temperatura por equações pré-fixadas (como a Lei de Dolbear)**. A temperatura deve ser aferida em campo com termômetro calibrado no micro-habitat do inseto e registrada como metadado ambiental independente, permitindo que o pesquisador descubra e ajuste a curva termo-acústica real da nova espécie sem circularidade analítica.

---

### 3.2. BLOCO B: FORMULAÇÃO MATEMÁTICA E DSP

#### 3.2.1. Envoltória Analítica e Transformada de Hilbert
Dado o sinal real filtrado na banda estridulatória $x(t) = \text{data\_b1}(t)$, sua **Transformada de Hilbert** $\tilde{x}(t) = \mathcal{H}\{x(t)\}$ é definida pela integral de convolução no sentido do Valor Principal de Cauchy ($\text{p.v.}$):

$$\tilde{x}(t) = \mathcal{H}\{x(t)\} = \frac{1}{\pi}\, \text{p.v.} \int_{-\infty}^{\infty} \frac{x(\tau)}{t - \tau}\, d\tau, \qquad E(t) = \sqrt{x^2(t) + \tilde{x}^2(t)}$$

No domínio da frequência, $\mathcal{F}\{\tilde{x}(t)\} = -j \operatorname{sgn}(f) X(f)$, de modo que o **sinal analítico** $z(t) = x(t) + j\tilde{x}(t)$ contém exclusivamente frequências não-negativas. Computacionalmente, para evitar complexidade $O(N^2)$ quando o comprimento $N$ do áudio é um número primo grande, o Crinômetro expande o vetor até o próximo inteiro 5-suave $N_{\text{fast}} = \text{next\_fast\_len}(N) = 2^a 3^b 5^c \ge N$, computa a FFT em $O(N_{\text{fast}} \log N_{\text{fast}})$ e trunca de volta para $N$ amostras.

A envoltória bruta $E[n]$ é normalizada pelo percentil robusto $P_{99,85}(E)$ e suavizada por convolução discreta com um kernel de Hann $h[m]$ de duração configurável $\tau_{\text{smooth}} = \text{smooth\_window\_ms}$ (garantindo comprimento ímpar $M_h = 2\lfloor \tau_{\text{smooth}} f_s / 2000 \rfloor + 1$ para simetria de fase exata):

$$\hat{E}[n] = \frac{1}{P_{99,85}(E)} \sum_{m=-(M_h-1)/2}^{(M_h-1)/2} E[n - m]\, \frac{w_{\text{Hann}}[m]}{\sum_k w_{\text{Hann}}[k]}$$

#### 3.2.2. Limiar Adaptativo e Métricas Metrológicas dos Pulsos ($-3\text{ dB}$, $-6\text{ dB}$, IPI, PRR, Duty Cycle e Assimetria)
O limiar adaptativo de detecção de picos combina o parâmetro determinístico `amp_min` escalonado pelo `noise_floor` com o estimador estatístico do $25^{\circ}$ percentil do envelope suavizado:

$$\theta_{\text{peak}} = \max\left( 0,03,\; \min\left( \text{amp\_min} \cdot \text{noise\_floor},\; \max\left(P_{25}(\hat{E}) \cdot 2,5,\; 0,06\right) \right) \right)$$

Para cada pico candidato localizado na amostra $n_i$ (instante $t_{\text{peak}, i} = n_i / f_s$) com amplitude de ápice $A_i = \hat{E}[n_i]$ e proeminência topográfica $P_i$:

1. **Duração do Pulso a $-6\text{ dB}$ (Meia Amplitude Linear / FWHM — `rel_height = 0.50`):**
   Corresponde ao intervalo temporal em que a envoltória permanece acima de $50\%$ da altura do pico ($20 \log_{10}(0,50) \approx -6,02\text{ dB}$):
   $$d_{p, -6\text{dB}}(i) = t_{\text{right}, 0.50}(i) - t_{\text{left}, 0.50}(i)$$
2. **Duração do Pulso a $-3\text{ dB}$ (Meia Potência Energética — `rel_height` $\approx 1 - 1/\sqrt{2} \approx 0,293$ e a $25\%$ / `rel_height = 0.25`):**
   Corresponde à largura no topo energético onde a potência instantânea $E^2(t)$ cai pela metade ($A(t) = A_i / \sqrt{2} \approx 0,707 A_i$, ou a $75\%$ da altura em `peak_width_75_s`):
   $$d_{p, -3\text{dB}}(i) = t_{\text{right}, 1 - 1/\sqrt{2}}(i) - t_{\text{left}, 1 - 1/\sqrt{2}}(i)$$
3. **Intervalo Inter-Pulso ($\text{IPI}$) e Período Inter-Pulso ($T_p$):**
   O Crinômetro distingue rigorosamente o período centro-a-centro entre picos consecutivos ($\Delta t_{\text{peak}, i}$) e o período de silêncio *offset-to-onset* entre o término de um pulso e o início do subsequente:
   $$\text{IPI}_{\text{peak}, i} = t_{\text{peak}, i+1} - t_{\text{peak}, i}, \qquad \text{IPI}_{\text{silêncio}, i} = t_{\text{onset}, i+1} - t_{\text{offset}, i}$$
4. **Taxa de Repetição de Pulsos ($\text{PRR}$ — *Pulse Repetition Rate*):**
   $$\text{PRR}_i = \frac{1}{t_{\text{peak}, i+1} - t_{\text{peak}, i}} \quad [\text{pulsos/s ou Hz}]$$
5. **Ciclo de Trabalho (*Duty Cycle* — $\text{DC}_i$):**
   Expressa a fração de tempo em que o aparelho estridulatório permanece ativamente irradiando energia acústica dentro de cada ciclo silábico:
   $$\text{DC}_i = \frac{d_{p, -6\text{dB}}(i)}{t_{\text{peak}, i+1} - t_{\text{peak}, i}} \times 100\%$$
6. **Assimetria Temporal do Envelope (*Skewness Local* — $\mathcal{S}_i$) e Tempo de Ataque $10\text{–}90\%$:**
   Sejam $\mu_{\text{left}, i}$ e $\mu_{\text{right}, i}$ as médias de amplitude nas meias-janelas esquerda (ataque) e direita (decaimento) de $\pm 30\text{ ms}$ ao redor de $t_{\text{peak}, i}$:
   $$\mathcal{S}_i = \frac{\mu_{\text{left}, i} - \mu_{\text{right}, i}}{A_i + \epsilon}, \qquad t_{\text{attack}, 10\text{–}90\%}(i) = t_{0,90 A_i} - t_{0,10 A_i}$$
   Como o impacto mecânico inicial na harpa alar é abrupto e o decaimento é governado pelo amortecimento viscoso exponencial da membrana, pulsos biológicos verdadeiros exibem $t_{\text{attack}, 10\text{–}90\%}$ reduzido e assimetria característica.

#### 3.2.3. Agrupamento Hierárquico em 5 Camadas, Filtro de Coerência Rítmica $O(N)$ e Diagnóstico de Cadência
O método [`CricketAnalyzer.regroup_chirps`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L411-L553) agrupa a sequência ordenada de pulsos validados $\{n_1, n_2, \dots, n_M\}$ aplicando cinco invariantes biomecânicos:

1. **Camada 1 (Resolução de Colisão Sub-Refratária):** Se dois picos consecutivos distam menos que $0,8 \cdot \text{gap\_min}$, retém-se apenas o pulso de maior amplitude no envelope ($\max(\hat{E}[n_i], \hat{E}[n_{i+1}])$).
2. **Camada 2 (Continuidade Intra-Chilreio e Coerência de Amplitude):** Um pulso $n_{i+1}$ é anexado ao chilreio em construção $\mathcal{C}_k$ se e somente se:
   $$\text{gap\_min} \le \frac{n_{i+1} - n_i}{f_s} \le \text{gap\_max} \quad \wedge \quad \hat{E}[n_{i+1}] \ge 0,25 \cdot \operatorname{mediana}_{p \in \mathcal{C}_k}(\hat{E}[p])$$
3. **Camada 3 (Filtro de Coerência Rítmica $O(N)$):** Para cada chilreio candidato $\mathcal{C}_k$ com $|\mathcal{C}_k| \ge 4$, seja $\widetilde{\text{IPI}}_k = \operatorname{mediana}(\{\Delta t_j\}_{j \in \mathcal{C}_k})$. Pulsos periféricos na primeira ou última posição cujo intervalo viole a estabilidade do CPG ($\Delta t < 0,45 \cdot \widetilde{\text{IPI}}_k$ ou $\Delta t > 1,85 \cdot \widetilde{\text{IPI}}_k$ com amplitude inferior a $55\%$ da mediana do chilreio) são podados em tempo linear $O(N)$.
4. **Camada 4 (Portão Refratário ICI — *Inter-Chirp Interval Gate*):** Calculam-se os intervalos inter-chilreio $\text{ICI}_k = t_{\text{onset}}(\mathcal{C}_{k+1}) - t_{\text{offset}}(\mathcal{C}_k)$. Pares consecutivos com $\text{ICI}_k < \min(0,12\text{ s},\; 0,70 \cdot \operatorname{mediana}(\text{ICI}))$ cuja soma de pulsos não exceda $\text{max\_p}$ são fundidos.
5. **Camada 5 (Validação Sintática Estrita):** Apenas chilreios que satisfazem $\text{min\_p} \le |\mathcal{C}_k| \le \text{max\_p}$ são retidos na lista final `chirp_peaks_list`.

Para o **Diagnóstico Estatístico de Cadência Rítmica** ao longo da gravação (`analyze_rhythmic_cadence` em [`utils/report_generator.py`](file:///m:/Documentos/Faculdade/Biologia/utils/report_generator.py#L92-L204)), expurgam-se pausas comportamentais ($\text{ICI}_k > 3 \cdot \operatorname{mediana}(\text{ICI})$) e ajusta-se o modelo linear de mínimos quadrados ordinários (OLS) sobre os instantes temporais $t_k$:

$$\text{ICI}(t_k) = \beta_0 + \beta_1 t_k + \varepsilon_k$$

A hipótese nula $H_0: \beta_1 = 0$ é testada pela estatística $t$ de Student com $n - 2$ graus de liberdade a partir do coeficiente de correlação de Pearson $r$:

$$t_{\text{stat}} = r \sqrt{\frac{n - 2}{1 - r^2}}, \qquad p\text{-valor} = 2 \left( 1 - F_{t, n-2}\left(|t_{\text{stat}}|\right) \right)$$

- Se $\beta_1 < -0,15\text{ ms/s}$ e $p < 0,05$: **Aceleração Rítmica Significativa**;
- Se $\beta_1 > +0,15\text{ ms/s}$ e $p < 0,05$: **Desaceleração / Fadiga Neuromotora Significativa**;
- Caso contrário: **Cadência Estacionária Estável**.

---

### 3.3. BLOCO C: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E CÓDIGO

A implementação do agrupamento hierárquico e do filtro de coerência rítmica em [`core/analyzer.py`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L465-L535):

```python
# Trecho real de core/analyzer.py (CricketAnalyzer.regroup_chirps)
# Filtro de Coerência Rítmica intra-chilreio O(N) e ICI Gate
filtered_groups = []
for g in prelim_groups:
    if len(g) >= 4:
        ipis = np.diff(g) / float(rate)
        med_ipi = float(np.median(ipis))
        if med_ipi > 0 and env is not None:
            g_amps = env[g]
            med_amp = float(np.median(g_amps))
            # Poda nas extremidades se o pulso periférico quebrar o ritmo do CPG e for fraco
            if len(g) >= 4 and (ipis[-1] > 1.85 * med_ipi or ipis[-1] < 0.45 * med_ipi):
                if g_amps[-1] < 0.55 * med_amp:
                    g = g[:-1]
                    ipis = np.diff(g) / float(rate)
            if len(g) >= 4 and len(ipis) > 0 and (ipis[0] > 1.85 * med_ipi or ipis[0] < 0.45 * med_ipi):
                if g_amps[0] < 0.55 * med_amp:
                    g = g[1:]
    filtered_groups.append(g)

# Validação final estrita de contagem de pulsos [min_p, max_p]
chirp_peaks_list = [g for g in merged_groups if min_p <= len(g) <= max_p]
chirps = [len(g) for g in chirp_peaks_list]
media = float(np.mean(chirps)) if chirps else 0.0
moda = CricketAnalyzer._safe_mode(chirps) if chirps else 0
variancia = float(np.var(chirps, ddof=1)) if len(chirps) > 1 else 0.0
```

---

## 4.0. Módulo IV — Aprendizado de Máquina Híbrido, Engenharia de Atributos e Serialização Segura (`skops`)

> ┌──────────────────────────────────────────────────────────────────────────────────────────┐
> │ GLOSSÁRIO TÉCNICO & BIOACÚSTICO DA PÁGINA                                                │
> │ • GMM Bimodal (Gaussian Mixture Model) [Ref: §4.2]: Modelo probabilístico generativo que │
> │   decompõe a distribuição de pulsos em cluster focal vs. cluster de coro/ruído via EM.   │
> │ • HistGradientBoostingClassifier [Ref: §4.2]: Ensemble de árvores de decisão impulsionadas│
> │   por gradiente com discretização por histogramas em tempo $O(N_{\text{amostras}})$.     │
> │ • Hard Negative Mining [Ref: §4.2]: Indução determinística de hiperplanos de poda a      │
> │   partir de falsos positivos explicitamente rejeitados pelo especialista humano.         │
> │ • skops (Secure Scikit-Learn Serialization) [Ref: §4.3]: Protocolo de persistência que   │
> │   substitui o bytecode arbitrário do `pickle` por inspeção estrita de árvore de tipos.   │
> └──────────────────────────────────────────────────────────────────────────────────────────┘

---

### 4.1. BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS

Em gravações de florestas tropicais, a simples filtragem passa-faixa e de frequência portadora pode não ser suficiente quando dois ou mais machos coespecíficos (portanto, com a mesma frequência portadora $f_c$) cantam em alternância ou sobreposição a diferentes distâncias do microfone. Pela lei física da atenuação esférica e absorção atmosférica excessiva no habitat:
1. O **indivíduo focal** (mais próximo do transdutor) apresenta maior amplitude relativa (`peak_amp_rel`), maior relação sinal-ruído local (`local_snr_db`), flanco de subida mais íngreme (`rise_slope_rel` — menor dispersão por reverberação em folhagem) e maior razão harmônico-ruído (`local_hnr_db`).
2. Os **indivíduos de coro de fundo** sofrem espalhamento acústico (*multipath scattering*), que alarga a largura a $75\%$ do pico (`peak_width_75_s`), suaviza a segunda derivada no ápice (`peak_sharpness_rel`) e reduz o contraste energético multiescala (`multiscale_energy`).

Para capturar essa assinatura multidimensional independentemente do volume absoluto de gravação, todas as características extraídas pelo `PulseLearner` são **invariantes a ganho linear** (normalizadas pela amplitude ou energia local da janela).

---

### 4.2. BLOCO B: FORMULAÇÃO MATEMÁTICA E DSP

#### 4.2.1. O Vetor de 20 Atributos Bioacústicos ($\mathbf{f}(p_i) \in \mathbb{R}^{20}$)
Para cada candidato a pulso centrado na amostra $n_i$ sobre uma janela local $\mathcal{W}_{30\text{ms}} = [n_i - \lfloor 0,03 f_s \rfloor, n_i + \lfloor 0,03 f_s \rfloor]$:

| Índice | Identificador no Código (`feature_names`) | Formulação Matemática Exata | Interpretação Física e Bioacústica |
| :---: | :--- | :--- | :--- |
| **1** | `peak_amp_rel` | $\frac{\hat{E}[n_i]}{\operatorname{mediana}_{m \in \mathcal{W}}(\hat{E}[m]) + 10^{-6}}$ | Contraste de amplitude do pico contra o fundo local |
| **2** | `peak_width_s` | $\frac{w_{0,50}(n_i)}{f_s}$ | Duração FWHM a $-6\text{ dB}$ ($50\%$ de proeminência) em segundos |
| **3** | `peak_width_75_s` | $\frac{w_{0,25}(n_i)}{f_s}$ | Largura do topo agudo a $75\%$ da altura em segundos |
| **4** | `local_snr_db` | $20 \log_{10}\left( \frac{\hat{E}[n_i]}{1,4826 \cdot \operatorname{MAD}(\hat{E}_{\text{bordas}}) + 10^{-6}} \right)$ | Relação Sinal-Ruído robusta baseada no Desvio Absoluto Mediano |
| **5** | `energy_rel` | $\frac{\frac{1}{|\mathcal{W}|} \sum_{m \in \mathcal{W}} \hat{E}^2[m]}{\hat{E}^2[n_i] + 10^{-9}}$ | Energia normalizada da janela (compactação do pulso) |
| **6** | `std_amp_rel` | $\frac{\sigma(\hat{E}_{\mathcal{W}})}{\hat{E}[n_i] + 10^{-6}}$ | Dispersão relativa de amplitude na vizinhança |
| **7** | `prominence_ratio` | $\frac{\hat{E}[n_i] - \min(\hat{E}_{\text{esq}}, \hat{E}_{\text{dir}})}{\hat{E}[n_i] + 10^{-6}}$ | Proeminência topográfica normalizada sobre os vales laterais |
| **8** | `peak_sharpness_rel` | $\frac{2\hat{E}[n_i] - \hat{E}[n_i - \delta] - \hat{E}[n_i + \delta]}{\hat{E}[n_i] + 10^{-6}}$ | Curvatura discreta de $2^{\text{a}}$ ordem no ápice ($\delta \approx 1\text{ ms}$) |
| **9** | `crest_factor` | $\frac{\hat{E}[n_i]}{\sqrt{\frac{1}{|\mathcal{W}|}\sum_{m \in \mathcal{W}} \hat{E}^2[m]} + 10^{-6}}$ | Fator de crista local (discrimina cliques impulsivos de sílabas) |
| **10** | `skewness_local` | $\frac{\mu(\hat{E}_{\text{esq}}) - \mu(\hat{E}_{\text{dir}})}{\hat{E}[n_i] + 10^{-6}}$ | Assimetria temporal entre o flanco de ataque e o decaimento |
| **11** | `local_density_rel` | $\frac{\mu(\hat{E}_{\pm 10\text{ms}})}{\mu(\hat{E}_{\pm 30\text{ms}}) + 10^{-6}}$ | Concentração de amplitude no núcleo de $\pm 10\text{ ms}$ |
| **12** | `autocorr_1ms` | $\frac{\sum_m \tilde{e}[m]\tilde{e}[m - \tau_{1\text{ms}}]}{\sum_m \tilde{e}^2[m] + 10^{-9}}$ | Coerência de autocorrelação do envelope em atraso $\tau = 1\text{ ms}$ |
| **13** | `band_energy_ratio` | $\frac{\sum_{m \in \mathcal{W}_{10\text{ms}}} \hat{E}^2[m]}{\sum_{m \in \mathcal{W}_{30\text{ms}}} \hat{E}^2[m] + 10^{-9}}$ | Razão de confinamento energético na janela estreita vs. larga |
| **14** | `rise_slope_rel` | $\frac{\hat{E}[n_i] - \min(\hat{E}_{\text{esq}})}{\Delta t_{\text{subida}} \cdot (\hat{E}[n_i] + 10^{-6})}$ | Taxa normalizada de ataque mecânico ($\text{s}^{-1}$) |
| **15** | `spectral_centroid` | $\frac{\sum_k f_k |X_{\text{loc}}[k]|}{\sum_k |X_{\text{loc}}[k]| + 10^{-9}}$ | Centro de gravidade espectral de Fourier do pulso ($\text{Hz}$) |
| **16** | `spectral_rolloff_85` | $\min \left\{ f_K \;\middle|\; \sum_{k=0}^K |X_{\text{loc}}[k]|^2 \ge 0,85 \sum_k |X_{\text{loc}}[k]|^2 \right\}$ | Frequência de corte superior acumulando $85\%$ da energia ($\text{Hz}$) |
| **17** | `attack_time_10_90_ms` | $(t_{90\%} - t_{10\%}) \times 1000$ | Tempo de subida entre $10\%$ e $90\%$ da amplitude de pico ($\text{ms}$) |
| **18** | `local_hnr_db` | $10 \log_{10}\left( \frac{E_{|f - f_{\text{peak}}| \le 150\text{Hz}}}{E_{\text{fora}} + 10^{-9}} \right)$ | Razão Harmônico-Ruído local na banda estreita de $\pm 150\text{ Hz}$ |
| **19** | `multiscale_energy` | $\frac{\frac{1}{|\mathcal{W}_{10}|}\sum_{\mathcal{W}_{10}} \hat{E}^2}{\frac{1}{|\mathcal{W}_{40}|}\sum_{\mathcal{W}_{40}} \hat{E}^2 + 10^{-9}}$ | Densidade de potência multiescala ($\pm 10\text{ ms}$ vs. $\pm 40\text{ ms}$) |
| **20** | `prior_p_focal` | $P(\text{Cluster Focal} \mid \mathbf{z}_i, \Theta_{\text{GMM}})$ | Probabilidade posterior não-supervisionada do GMM Bimodal |

#### 4.2.2. Modelo de Mistura de Gaussianas (GMM Bimodal) e Score Híbrido Supervisionado
O módulo não-supervisionado projeta os candidatos no espaço padronizado $\mathbf{z}_i \in \mathbb{R}^2$ (log-amplitude e centroide espectral) e ajusta um **Modelo de Mistura de Gaussianas (`GaussianMixture`)** com $K = 2$ componentes e matrizes de covariância completas $\boldsymbol{\Sigma}_k$ via algoritmo Expectation-Maximization (EM):

$$p(\mathbf{z}_i \mid \Theta) = \sum_{k=1}^{2} \pi_k\, \mathcal{N}\left(\mathbf{z}_i \;\middle|\; \boldsymbol{\mu}_k, \boldsymbol{\Sigma}_k\right), \qquad P(\text{Focal} \mid \mathbf{z}_i) = \frac{\pi_{k^*} \mathcal{N}(\mathbf{z}_i \mid \boldsymbol{\mu}_{k^*}, \boldsymbol{\Sigma}_{k^*})}{\sum_{k=1}^{2} \pi_k \mathcal{N}(\mathbf{z}_i \mid \boldsymbol{\mu}_k, \boldsymbol{\Sigma}_k)}$$

Quando o pesquisador fornece exemplos rotulados e aciona o treinamento supervisionado, o Crinômetro ajusta um ensemble **`HistGradientBoostingClassifier`** (ou `RandomForestClassifier` como *fallback*), que minimiza a perda de entropia cruzada binária sobre árvores de decisão rasas ($\text{max\_depth} \in \{3, 4\}$) com regularização $L_2$ ($\lambda_{L2} = 2,0$ para amostras pequenas), prevenindo sobreajuste (*overfitting*).

A pontuação de decisão final para cada pulso $i$ combina convexamente a probabilidade supervisionada $P_{\text{sup}}(y_i = 1 \mid \mathbf{f}_i)$ e o prior físico do GMM $P_{\text{GMM}}(\text{Focal} \mid \mathbf{z}_i)$:

$$\text{Score}(i) = 0,65 \cdot P_{\text{sup}}(y_i = 1 \mid \mathbf{f}_i) + 0,35 \cdot P_{\text{GMM}}(\text{Focal} \mid \mathbf{z}_i)$$

Seguida pelo **Resgate Contextual Iterativo (*Contextual Gating*)**: pulsos de ataque ou decaimento nas bordas de um chilreio que apresentem $\text{Score}(i) \ge \theta_{\text{low}}$ ($0,42 + 0,20 \cdot \text{focal\_sensitivity}$) e estejam temporalmente pareados ($\text{IPI} \in [0,85 \cdot \text{gap\_min}, 1,15 \cdot \text{gap\_max}]$) a um pulso de alta confiança ($\text{Score} \ge 0,58 + 0,25 \cdot \text{focal\_sensitivity}$) são resgatados iterativamente (até $5$ passagens), preservando a integridade da contagem sintática do chilreio.

---

### 4.3. BLOCO C: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E CÓDIGO

#### 4.3.1. Segurança de Desserialização com `skops` e Prevenção de Execução Arbitrária de Código
Na versão 4.5.0, o antigo formato `.pkl` (`pickle`) foi substituído pela biblioteca **`skops.io`** (`modelo_treinado.skops`). Durante o carregamento (`load_persisted_training` e `import_model_file`), o Crinômetro executa auditoria estática de todos os tipos contidos no arquivo via `skio.get_untrusted_types()` e valida cada símbolo contra a lista branca estrita `_ALLOWED_SKOPS_PREFIXES`:

```python
# Trecho real de core/learner.py: Validação de segurança da árvore de tipos skops
_ALLOWED_SKOPS_PREFIXES = (
    "sklearn.", "numpy.", "scipy.", "builtins.", "collections."
)

def _validate_skops_types(untrusted_types):
    for t in untrusted_types:
        t_str = str(t)
        if not any(t_str.startswith(p) or t_str in ("int", "float", "str", "bool", "list", "dict", "tuple", "set", "bytes", "NoneType") for p in _ALLOWED_SKOPS_PREFIXES):
            raise ValueError(f"Tipo não confiável bloqueado na desserialização skops: {t_str}")
    return list(untrusted_types)
```

#### 4.3.2. Desacoplamento de Locks (`_model_lock` vs. `CONFIG_LOCK`) e Fallback Determinístico
Para eliminar qualquer possibilidade de *deadlock* do tipo AB-BA entre a thread principal da interface (que adquire `CONFIG_LOCK` ao salvar preferências) e o worker de treinamento (que adquire `self._model_lock`), os métodos `save_to_config`, `load_from_config`, `import_model_file` e `reset` em [`core/learner.py`](file:///m:/Documentos/Faculdade/Biologia/core/learner.py#L698-L785) jamais aninham os dois locks:

```python
# Trecho real de core/learner.py: Desacoplamento estrito entre _model_lock e CONFIG_LOCK
def save_to_config(self):
    with self._model_lock:
        if self.model is None:
            return False
        serialized = self.serialize()
        rules = list(getattr(self, "pruning_rules", []))
    try:
        with CONFIG_LOCK:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}
            if not isinstance(config, dict):
                config = {}
            config["pulse_learner"] = serialized
            config["pruning_rules"] = rules
            from utils.persistence import atomic_write_json
            atomic_write_json(self.config_path, config)
            return True
    except Exception as exc:
        logging.getLogger("crinometro").error(f"Erro ao persistir modelo de aprendizado: {exc}", exc_info=True)
        return False
```

Caso `self.model` lance qualquer exceção em tempo de execução ou o arquivo `.skops` esteja corrompido, a exceção interna `ModelUnavailable` é capturada, `self.degraded = True` é sinalizado e `filter_peaks` reverte imediatamente para o ramo determinístico não-supervisionado (`pos_probs is None`), garantindo continuidade operacional absoluta.

---

## 5.0. Módulo V — Computação Gráfica de Alta Performance (Min-Max LoD, Raster Blitting e Poda Espacial)

> ┌──────────────────────────────────────────────────────────────────────────────────────────┐
> │ GLOSSÁRIO TÉCNICO & BIOACÚSTICO DA PÁGINA                                                │
> │ • Aliasing Visual de Sub-Amostragem [Ref: §5.1]: Omissão gráfica de picos estreitos      │
> │   quando um sinal denso é sub-amostrado por passo fixo ($x[::k]$) na tela.               │
> │ • Decimação em Blocos Min-Max (LoD) [Ref: §5.2]: Particionamento do domínio visível em   │
> │   $B$ intervalos contíguos extraindo $[\min(x_b), \max(x_b)]$ para preservar extremos.   │
> │ • Raster Blitting (Bit-Block Transfer) [Ref: §5.3]: Restauração em tempo $O(1)$ de um    │
> │   buffer de pixels pré-renderizado na RAM para animar cursores a $60\text{ FPS}$.        │
> └──────────────────────────────────────────────────────────────────────────────────────────┘

---

### 5.1. BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS

Um pulso estridulatório de grilo dura tipicamente entre $3\text{ ms}$ e $30\text{ ms}$. Em uma gravação de campo de $5\text{ minutos}$ ($300\text{ s}$) amostrada a $f_s = 48.000\text{ Hz}$, o vetor de áudio contém $N = 14.400.000\text{ amostras}$, enquanto a área de plotagem de um monitor Full HD comporta apenas $W_{\text{px}} \approx 1.600\text{ pixels}$ horizontais (densidade de $9.000\text{ amostras por pixel}$).

Se o motor gráfico tentasse enviar $14,4\text{ milhões}$ de vértices para o rasterizador Agg do Matplotlib, cada operação de pan/zoom levaria vários segundos (*overdraw* massivo). Por outro lado, se aplicasse amostragem ingênua a cada $9.000$ amostras ($\Delta t_{\text{stride}} = 187,5\text{ ms}$), **pulsos inteiros de $15\text{ ms}$ cairiam nos vãos entre amostras e sumiriam completamente da tela**, induzindo o taxonomista ao erro grave de achar que a gravação está silenciosa.

---

### 5.2. BLOCO B: FORMULAÇÃO MATEMÁTICA E DSP

#### 5.2.1. Teorema de Preservação de Extremos por Decimação Min-Max (LoD)
Seja $[t_{\min}, t_{\max}]$ a janela temporal visível no eixo $X$, correspondente ao sub-intervalo de índices discretos $[i_0, i_1]$ de comprimento $N_{\text{vis}} = i_1 - i_0$. Dado um orçamento de resolução de $B$ blocos visuais ($B = 300$ durante interação rápida de arraste a $60\text{ FPS}$; $B = 2.000$ no modo de alta definição estacionária, gerando $2B = 4.000$ vértices), define-se o tamanho de bloco $L_b = \lfloor N_{\text{vis}} / B \rfloor$.

Para cada bloco contíguo $b \in \{0, 1, \dots, B-1\}$, seja o conjunto de índices $\mathcal{I}_b = \{i_0 + b L_b, \dots, i_0 + (b+1)L_b - 1\}$. O operador de redução **Min-Max LoD** projeta $\mathcal{I}_b$ no par ordenado de extremos locais:

$$y_{\min}[b] = \min_{n \in \mathcal{I}_b} y[n], \qquad y_{\max}[b] = \max_{n \in \mathcal{I}_b} y[n]$$

intercalados no vetor de saída $\mathbf{y}_{\text{LoD}} \in \mathbb{R}^{2B}$ tal que:

$$y_{\text{LoD}}[2b] = y_{\min}[b], \qquad y_{\text{LoD}}[2b + 1] = y_{\max}[b]$$

**Propriedade de Invariância Topológica de Picos:** Para qualquer pulso $p^*$ contido em $[i_0, i_1]$, existe um único bloco $b^*$ tal que $p^* \in \mathcal{I}_{b^*}$. Como $y_{\max}[b^*] \ge y[p^*]$, a envolvente vertical renderizada no pixel correspondente a $b^*$ **cobre matematicamente $100\%$ da excursão de pico de todos os pulsos da gravação**, reduzindo a complexidade de rasterização de $O(N_{\text{vis}})$ para $O(B)$ constante!

#### 5.2.2. Poda Espacial Logarítmica no Hover (`on_motion`: de $O(N)$ para $O(K)$)
Durante o movimento do mouse na posição $(x_{\text{mouse}}, y_{\text{mouse}})$ correspondente ao instante $t_c$, transformar todos os $M$ picos do áudio pelas matrizes afins do Matplotlib (`ax.transData.transform`) teria custo $O(M)$ por evento de $120\text{ Hz}$. O `NavigationController` restringe a busca a uma vizinhança temporal $\Delta t_{\max}$ equivalente a $30\text{ pixels}$ de tela:

$$\Delta t_{\max} = \max\left( 0,04\text{ s},\; \frac{30,0}{\text{px\_per\_sec}} \right)$$

Localizam-se as fronteiras do intervalo $[t_c - \Delta t_{\max}, t_c + \Delta t_{\max}]$ no vetor ordenado de tempos de pulso por **busca binária dicotômica (`np.searchsorted`)** em tempo $O(\log M)$, aplicando a transformação de coordenadas de tela exclusivamente aos $K \ll M$ candidatos internos à janela.

---

### 5.3. BLOCO C: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E CÓDIGO

#### 5.3.1. `HighPerfLineEngine` e `HighPerfSpectrogramEngine` (`core/engines.py`)
Em [`core/engines.py`](file:///m:/Documentos/Faculdade/Biologia/core/engines.py#L14-L115), a decimação Min-Max é vetorizada em C via `numpy.reshape` sem laços Python:

```python
# Trecho real de core/engines.py (HighPerfLineEngine._get_envelope)
def _get_envelope(self, x_min, x_max, n_buckets):
    i0 = max(0, int(np.searchsorted(self.x, x_min, side='left')) - 1)
    i1 = min(len(self.x), int(np.searchsorted(self.x, x_max, side='right')) + 1)
    sub_x = self.x[i0:i1]
    sub_y = self.y[i0:i1]
    n = len(sub_y)
    if n <= n_buckets * 2:
        return sub_x, sub_y

    bucket_size = n // n_buckets
    limit = bucket_size * n_buckets
    y_reshaped = sub_y[:limit].reshape(n_buckets, bucket_size)
    x_reshaped = sub_x[:limit].reshape(n_buckets, bucket_size)

    y_min = y_reshaped.min(axis=1)
    y_max = y_reshaped.max(axis=1)
    t_min = x_reshaped[:, 0]
    t_max = x_reshaped[:, -1]

    x_out = np.empty(n_buckets * 2, dtype=sub_x.dtype)
    y_out = np.empty(n_buckets * 2, dtype=sub_y.dtype)
    x_out[0::2] = t_min
    x_out[1::2] = t_max
    y_out[0::2] = y_min
    y_out[1::2] = y_max
    return x_out, y_out
```

#### 5.3.2. Coalescência de Background Blitting e Prevenção de Vazamento de Memória (`NavigationController` e `FigureFactory`)
- **Coalescência de Captura (`schedule_capture_backgrounds`):** Quando o usuário finaliza um zoom ou altera a tolerância da portadora, tanto o `HighPerfLineEngine` quanto o `HighPerfSpectrogramEngine` disparam callbacks de alta resolução. Em [`NavigationController`](file:///m:/Documentos/Faculdade/Biologia/ui/controllers/navigation_controller.py#L225-L275), um `QTimer` *single-shot* de $50\text{ ms}$ coalesce múltiplas solicitações em um único ciclo de `canvas.draw()` + `copy_from_bbox(panel.ax.bbox)`, e invalida/recaptura o cache imediatamente após edições de pulsos (`PlotRenderers._refresh_user_peak_markers`), garantindo que marcadores recém-adicionados nunca desapareçam durante o *blitting* do cursor de áudio.
- **Isolamento de Eixos Estáticos:** Eventos de *pan* e *release* em `NavigationController.on_release` redesenham exclusivamente `(self.panel_wave, self.panel_spec)`, poupando o painel estático de Histograma (`panel_hist`) e o PSD (`panel_freq`) de redesenhos desnecessários.
- **Prevenção de Vazamento de Memória no Matplotlib:** Na geração de figuras de exportação e relatórios PDF (`FigureFactory` em [`ui/figure_factory.py`](file:///m:/Documentos/Faculdade/Biologia/ui/figure_factory.py) e `utils/report_generator.py`), utiliza-se a API orientada a objetos (`matplotlib.figure.Figure` acoplada a `FigureCanvasAgg`) ou fechamento explícito `plt.close(fig)` em blocos `try...finally`, impedindo a retenção de referências globais no módulo `pyplot` que causariam exaustão de memória RAM em processamentos em lote.

---

## 6.0. Módulo VI — Arquitetura Desacoplada v4.5.0, Concorrência Qt e Persistência Transacional Atômica

> ┌──────────────────────────────────────────────────────────────────────────────────────────┐
> │ GLOSSÁRIO TÉCNICO & BIOACÚSTICO DA PÁGINA                                                │
> │ • SessionContext [Ref: §6.1]: Repositório reativo centralizado (Single Source of Truth)  │
> │   que encapsula o estado analítico, cache de arquivos e parâmetros com sinais PyQt6.     │
> │ • Imutabilidade por Snapshot Profundo [Ref: §6.2]: Cópia isolada de dicionários e arrays │
> │   mutáveis antes da passagem para `QThread`, eliminando condições de corrida (Data Race).│
> │ • Substituição Atômica (os.replace) [Ref: §6.3]: Operação de sistema de arquivos que     │
> │   substitui o ponteiro de diretório após `fsync`, prevenindo arquivos JSON truncados.    │
> └──────────────────────────────────────────────────────────────────────────────────────────┘

---

### 6.1. BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS

Na prática laboratorial de taxonomia integrativa, um pesquisador frequentemente analisa lotes de $50\text{ a }200$ gravações de diferentes parátipos, alternando rapidamente entre a audição de um arquivo, a edição manual de pulsos no oscilograma, o ajuste do filtro de portadora e a exportação de relatórios PDF em segundo plano. Se o estado interno da aplicação estivesse acoplado diretamente aos widgets visuais da janela principal (*God Class*), editar um pulso enquanto um relatório PDF é compilado em segundo plano corromperia as estatísticas impressas no laudo ou causaria falha de segmentação C++ no motor Qt.

---

### 6.2. BLOCO B: FORMULAÇÃO MATEMÁTICA E MODELO FORMAL DE CONCORRÊNCIA

#### 6.2.1. Grafo de Dependência de Componentes e Estado Reativo
Na arquitetura v4.5.0, o estado global da sessão $\Sigma$ reside exclusivamente em [`SessionContext`](file:///m:/Documentos/Faculdade/Biologia/core/session_context.py) (`core/session_context.py`), que atua como *Single Source of Truth* (SSOT) observável via sinal Qt `state_changed(str)`. Os seis subsistemas operam desacoplados sob o padrão *Mediator*:

```
                    ┌───────────────────────────────────┐
                    │      SessionContext (SSOT)        │
                    │  • analysis_cache / heavy_data    │
                    │  • peaks_user_verified / metadata │
                    │  • algo_params / report_params    │
                    └─────────────────┬─────────────────┘
                                      │ Sinais PyQt6 (state_changed)
       ┌──────────────┬───────────────┼───────────────┬──────────────┐
       ▼              ▼               ▼               ▼              ▼
┌─────────────┐ ┌────────────┐ ┌─────────────┐ ┌────────────┐ ┌─────────────┐
│  Pipeline   │ │   Editor   │ │    Plot     │ │ Navigation │ │   Export    │
│Orchestrator │ │ Controller │ │  Renderers  │ │ Controller │ │ Controller  │
└──────┬──────┘ └─────┬──────┘ └──────┬──────┘ └─────┬──────┘ └──────┬──────┘
       │              │               │              │               │
       └──────────────┴───────────────┴──────────────┴───────────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │   WorkerRegistry & GenericWorker  │
                    │   (QThread Pool + Lock + Abort)   │
                    └───────────────────────────────────┘
```

#### 6.2.2. Deadline Monotônico Global no Encerramento de Threads (`WorkerRegistry.wait_all`)
Seja $\mathcal{W} = \{w_1, w_2, \dots, w_k\}$ o conjunto de *workers* (`QThread`) ativos no instante do fechamento da aplicação e $T_{\max}$ o tempo limite global de espera (padrão: $3.000\text{ ms}$). Em vez de aguardar sequencialmente $T_{\max}$ para cada thread (o que bloquearia a UI por $k \cdot T_{\max}$), o `WorkerRegistry` define um *deadline* monotônico único $t_{\text{deadline}} = t_{\text{mono}}() + T_{\max}/1000$:

$$\Delta t_{\text{rem}}(w_i) = \max\left(0,\; \left\lfloor \left(t_{\text{deadline}} - t_{\text{mono}}()\right) \times 1000 \right\rfloor \right)$$

garantindo que o tempo total de sincronização satisfaça estritamente $\sum_{i=1}^{k} t_{\text{wait}}(w_i) \le T_{\max}$.

---

### 6.3. BLOCO C: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E CÓDIGO

#### 6.3.1. Isolamento Thread-Safe em `WorkerRegistry` e `GenericWorker` (`core/worker.py`)
Em [`core/worker.py`](file:///m:/Documentos/Faculdade/Biologia/core/worker.py#L140-L216), todas as mutações na lista de threads ativas são protegidas por `self._lock = threading.Lock()`, e o cancelamento é 100% cooperativo via `threading.Event` (`abort()`), erradicando o erro fatal do Qt `QThread: Destroyed while thread is still running`:

```python
# Trecho real de core/worker.py (WorkerRegistry)
class WorkerRegistry:
    def __init__(self):
        self._workers: list[GenericWorker] = []
        self._lock = threading.Lock()

    def retain(self, worker: GenericWorker) -> GenericWorker:
        with self._lock:
            if worker not in self._workers:
                self._workers.append(worker)
        worker.finished.connect(lambda _w=worker: self._remove(_w))
        return worker

    def abort_all(self) -> None:
        with self._lock:
            snapshot = list(self._workers)
        for w in snapshot:
            try:
                w.abort()
            except Exception:
                pass

    def wait_all(self, timeout_ms: int = 3000) -> bool:
        deadline = time.monotonic() + (max(0, int(timeout_ms)) / 1000.0)
        with self._lock:
            snapshot = list(self._workers)
        all_stopped = True
        for w in snapshot:
            try:
                if w.isRunning():
                    rem_ms = max(0, int((deadline - time.monotonic()) * 1000.0))
                    if not w.wait(rem_ms):
                        all_stopped = False
            except RuntimeError:
                pass
        return all_stopped
```

#### 6.3.2. Imutabilidade e Snapshot Profundo para Exportação Assíncrona (`ExportController` e `_SnapshotCtx`)
Para impedir condições de corrida (*Data Races*) quando o usuário edita pulsos na interface enquanto uma thread secundária renderiza gráficos ou compila o PDF, [`ExportController._generate_pdf_report_modular`](file:///m:/Documentos/Faculdade/Biologia/ui/controllers/export_controller.py#L514-L539) e [`_SnapshotCtx.__init__`](file:///m:/Documentos/Faculdade/Biologia/ui/dialogs/export_graph_dialog.py#L51-L82) constroem cópias profundas isoladas na thread principal antes de disparar o `GenericWorker`:

```python
# Trecho real de ui/controllers/export_controller.py: Snapshot profundo thread-safe
def _snapshot_entry(entry: dict) -> dict:
    snap = dict(entry)
    for k in ("params", "discarded_peaks_reasons", "pulse_metadata"):
        if isinstance(snap.get(k), dict):
            snap[k] = dict(snap[k])
    for k in ("chirps", "peaks", "peaks_detected", "peaks_user_verified", "distant_peaks"):
        if snap.get(k) is not None:
            snap[k] = list(snap[k])
    if snap.get("chirp_peaks_list") is not None:
        snap["chirp_peaks_list"] = [list(c) for c in snap["chirp_peaks_list"]]
    return snap
```

#### 6.3.3. Gravação Atômica de Estado e Configurações (`utils/persistence.py`)
Para proteger o arquivo `crinometro_config.json` contra corrupção por queda de energia ou encerramento abrupto do sistema operacional, [`utils/persistence.py`](file:///m:/Documentos/Faculdade/Biologia/utils/persistence.py#L8-L63) implementa o protocolo **Write-Ahead Tempfile + Flush + OS Fsync + Atomic Replace** com preservação de backup `.bak` e quarentena automática de arquivos corrompidos:

```python
# Trecho real de utils/persistence.py
def atomic_write(filepath: str, content: bytes):
    """Escreve num arquivo de forma atômica usando rename, mantendo backup antigo."""
    bak_path = filepath + ".bak"
    if os.path.exists(filepath):
        try:
            shutil.copy2(filepath, bak_path)
        except Exception as e:
            logger.warning(f"Nao foi possivel criar backup de {filepath}: {e}")
            
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="." + os.path.basename(filepath), suffix=".tmp")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, filepath)
    except Exception as e:
        logger.error(f"Erro na escrita atomica para {filepath}: {e}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
```

---

## 7.0. Seção Modelo "Materiais e Métodos" para Publicação Científica

O texto abaixo está formatado segundo as normas editoriais de periódicos de taxonomia e bioacústica (*Zootaxa*, *Systematic Entomology*, *Bioacoustics*), pronto para inclusão em artigos de descrição de novas espécies:

> *"As gravações digitais em formato WAV não comprimido foram analisadas no software **Crinômetro (v4.5.0)**. Para arquivos originalmente estéreos, selecionou-se automaticamente o canal de maior energia eficaz ($\text{RMS}$), prevenindo artefatos de cancelamento de fase inter-canal. O sinal foi centralizado para remoção de offset DC e submetido a um filtro passa-altas Butterworth de $2^{\text{a}}$ ordem ($f_c = 50\text{ Hz}$) seguido de um filtro passa-faixa Butterworth de $4^{\text{a}}$ ordem ($[3200, 6000]\text{ Hz}$, ajustado à banda focal do táxon), ambos decompostos em Seções de Segunda Ordem (SOS) e aplicados bidirecionalmente com fase zero (`sosfiltfilt`; ordem efetiva $8$), preservando os instantes exatos dos transientes temporais sem atraso de grupo.*
>
> *A representação tempo-frequência foi obtida via Transformada de Fourier de Tempo Curto (STFT) com janela de Hann de $1024$ amostras e sobreposição de $75\%$ ($H = 256$ amostras), refinando-se a frequência dominante quadro a quadro por interpolação parabólica sub-bin de três pontos sobre o espectro logarítmico. A Densidade Espectral de Potência (PSD) média foi estimada pelo método dos periodogramas modificados de Welch com janelas de Hann de $50\text{ ms}$ ($\Delta f = 20\text{ Hz}$) e sobreposição de $50\%$. A frequência portadora modal ($f_c$) foi determinada pela média ponderada por amplitude na vizinhança do bin modal ($50\text{ Hz}$) dos pulsos validados, aplicando-se rejeição de banda estreita parametrizável ($\pm 700\text{ Hz}$).*
>
> *A envoltória analítica instantânea foi extraída pelo módulo da Transformada de Hilbert ($E(t) = \sqrt{x^2(t) + \mathcal{H}\{x(t)\}^2}$), normalizada pelo percentil $99,85$ e suavizada por convolução com janela de Hann. A detecção de sílabas/pulsos empregou limiar adaptativo baseado no $25^{\circ}$ percentil do envelope, validação morfológica de largura a meia altura (FWHM, $-6\text{ dB}$) e agrupamento hierárquico em chilreios (echemas) com imposição de intervalo inter-pulso ($\text{IPI}$), filtro de coerência rítmica linear $O(N)$ e portão de período refratário inter-chilreio ($\text{ICI Gate}$ a $70\%$ do $\text{ICI}$ mediano). A estabilidade rítmica ao longo da emissão foi avaliada por regressão linear dos $\text{ICIs}$ aferida pelo teste $t$ de Student ($\alpha = 0,05$). Todas as métricas reportadas baseiam-se exclusivamente nos parâmetros físico-acústicos diretos do espécime, sem aplicação de extrapolações termo-acústicas interespecíficas pré-fixadas."*

---

## 8.0. Índice Remissivo de Referências Cruzadas (Fórmulas $\leftrightarrow$ Classes $\leftrightarrow$ Seções)

| Conceito / Grandeza Matemática | Equação / Símbolo Principal | Classe / Método / Arquivo no Crinômetro v4.5.0 | Seção de Referência |
| :--- | :--- | :--- | :---: |
| **Seleção Estéreo por Energia RMS** | $c^* = \arg\max_c \sqrt{\frac{1}{N}\sum_n X_{n,c}^2}$ | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L52-L58) (`core/analyzer.py`) | §1.2.1, §1.3 |
| **Filtro Passa-Altas Anti-Vento ($50\text{ Hz}$)** | $H_{\text{HP}}(z) H_{\text{HP}}(z^{-1})$ (2ª Ordem SOS Zero-Phase) | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L64-L69) (`core/analyzer.py`) | §1.2.2, §1.3 |
| **Filtro Passa-Faixa Butterworth SOS** | $\left\|H(j\omega)\right\|^2 = [1 + (\omega/\omega_c)^{2n}]^{-1}$ ($n=4$, Zero-Phase) | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L81-L87) (`core/analyzer.py`) | §1.2.2, §1.3 |
| **Espectrograma STFT (Gabor-Heisenberg)** | $S_{\text{dB}}[k,m] = 10\log_{10}(S_{xx}[k,m] + 10^{-10})$ | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L120-L125) (`core/analyzer.py`) | §2.2.1, §2.3 |
| **Interpolação Parabólica Sub-Bin** | $p_m = \frac{1}{2}\frac{\alpha_m - \gamma_m}{\alpha_m - 2\beta_m + \gamma_m}$ | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L136-L152) (`core/analyzer.py`) | §2.2.2, §2.3 |
| **Densidade Espectral de Potência (Welch)** | $P_{xx}(f) = 10\log_{10}(\max(S_{xx}(f), 10^{-12}))$ | [`CricketAnalyzer.compute_psd`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L25-L37) (`core/analyzer.py`) | §2.2.3, §2.3 |
| **Frequência Portadora Modal Ponderada** | $f_c = \frac{\sum_{i \in \mathcal{V}} a_i f_i}{\sum_{i \in \mathcal{V}} a_i}$ | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L215-L265) (`core/analyzer.py`) | §2.2.4, §2.3 |
| **Filtro de Tolerância Espectral Real-Time** | $\left\|f_i - f_c\right\| \le \Delta f_{\text{tol}}$ | [`PipelineOrchestrator._execute_realtime_freq_tolerance`](file:///m:/Documentos/Faculdade/Biologia/ui/controllers/pipeline_orchestrator.py#L519-L645) | §2.2.4, §2.3 |
| **Envoltória Analítica de Hilbert** | $E(t) = \sqrt{x^2(t) + \mathcal{H}\{x(t)\}^2}$ | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L88-L113) (`core/analyzer.py`) | §3.2.1, §3.3 |
| **Duração de Pulso FWHM ($-6\text{ dB}$ e $-3\text{ dB}$)** | $d_{p,-6\text{dB}} = w_{0,50}/f_s$, $w_{0,25}/f_s$ | [`CricketAnalyzer.analyze`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L180-L210) & [`PulseLearner.extract_features_for_peak`](file:///m:/Documentos/Faculdade/Biologia/core/learner.py#L112-L260) | §3.2.2, §4.2.1 |
| **Agrupamento em Chilreios e Coerência $O(N)$** | $\text{IPI} \in [\text{gap\_min}, \text{gap\_max}]$, $\text{ICI Gate } 0,70$ | [`CricketAnalyzer.regroup_chirps`](file:///m:/Documentos/Faculdade/Biologia/core/analyzer.py#L411-L553) (`core/analyzer.py`) | §3.2.3, §3.3 |
| **Diagnóstico de Cadência Rítmica (OLS + Teste $t$)** | $\text{ICI}(t) = \beta_0 + \beta_1 t$, $t = r\sqrt{\frac{n-2}{1-r^2}}$ | [`analyze_rhythmic_cadence`](file:///m:/Documentos/Faculdade/Biologia/utils/report_generator.py#L92-L204) (`utils/report_generator.py`) | §3.2.3, §3.3 |
| **Vetor de 20 Atributos Invariantes a Ganho** | $\mathbf{f}(p_i) \in \mathbb{R}^{20}$ | [`PulseLearner.extract_features_for_peak`](file:///m:/Documentos/Faculdade/Biologia/core/learner.py#L112-L260) (`core/learner.py`) | §4.1, §4.2.1 |
| **GMM Bimodal + HistGradientBoosting Híbrido** | $\text{Score} = 0,65 P_{\text{sup}} + 0,35 P_{\text{GMM}}$ | [`PulseLearner.filter_peaks`](file:///m:/Documentos/Faculdade/Biologia/core/learner.py#L645-L825) (`core/learner.py`) | §4.2.2, §4.3 |
| **Serialização Segura por Auditoria AST (`skops`)** | `skio.dumps` / `skio.get_untrusted_types` | [`PulseLearner.save_persisted_training`](file:///m:/Documentos/Faculdade/Biologia/core/learner.py#L861-L945) (`core/learner.py`) | §4.3.1, §4.3.2 |
| **Decimação Gráfica Adaptativa Min-Max (LoD)** | $y_{\min}[b] = \min_{\mathcal{I}_b} y, \; y_{\max}[b] = \max_{\mathcal{I}_b} y$ | [`HighPerfLineEngine._get_envelope`](file:///m:/Documentos/Faculdade/Biologia/core/engines.py#L56-L102) (`core/engines.py`) | §5.2.1, §5.3.1 |
| **Raster Blitting Coalescente a $60\text{ FPS}$** | `copy_from_bbox` / `restore_region` / `blit` | [`NavigationController.schedule_capture_backgrounds`](file:///m:/Documentos/Faculdade/Biologia/ui/controllers/navigation_controller.py#L242-L295) | §5.3.2 |
| **Poda Espacial Logarítmica de Hover $O(K)$** | $\Delta t_{\max} = \max(0,04,\; 30/\text{px\_per\_sec})$ | [`NavigationController.on_motion`](file:///m:/Documentos/Faculdade/Biologia/ui/controllers/navigation_controller.py#L460-L565) | §5.2.2, §5.3.2 |
| **Fábrica Pura de Figuras Científicas** | `draw_waveform`, `draw_spectrogram`, `draw_psd` | [`ui/figure_factory.py`](file:///m:/Documentos/Faculdade/Biologia/ui/figure_factory.py#L150-L420) (`ExportConfig`) | §5.3.2 |
| **Estado Reativo Centralizado (SSOT)** | `state_changed = pyqtSignal(str)` | [`SessionContext`](file:///m:/Documentos/Faculdade/Biologia/core/session_context.py#L15-L210) (`core/session_context.py`) | §6.2.1, §6.3 |
| **Pool de Threads e Deadline Monotônico** | $\Delta t_{\text{rem}} = \max(0, t_{\text{deadline}} - t_{\text{mono}})$ | [`WorkerRegistry`](file:///m:/Documentos/Faculdade/Biologia/core/worker.py#L140-L216) & [`GenericWorker`](file:///m:/Documentos/Faculdade/Biologia/core/worker.py#L20-L138) (`core/worker.py`) | §6.2.2, §6.3.1 |
| **Persistência Transacional Atômica** | `mkstemp` $\rightarrow$ `fsync` $\rightarrow$ `os.replace` | [`atomic_write`](file:///m:/Documentos/Faculdade/Biologia/utils/persistence.py#L8-L31) & [`atomic_write_json`](file:///m:/Documentos/Faculdade/Biologia/utils/persistence.py#L59-L63) (`utils/persistence.py`) | §6.3.3 |
