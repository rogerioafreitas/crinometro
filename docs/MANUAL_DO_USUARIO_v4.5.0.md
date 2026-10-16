# DOCUMENTO 1: MANUAL DO USUÁRIO E GUIA DE OPERAÇÃO PRÁTICA — CRINÔMETRO v4.5.0

**Versão de Produção:** 4.5.0  
**Domínio Científico:** Bioacústica Computacional, Taxonomia Integrativa e Metrologia Acústica de Orthoptera (Ensifera: Grylloidea)  
**Arquitetura Gráfica:** PyQt6 + Matplotlib (Engines de Renderização Adaptativa LoD e Raster Blitting)

> **Declaração Metrológica de Domínio (v4.5.0):** O **Crinômetro v4.5.0** é um instrumento metrológico de precisão concebido para a descoberta, diagnose taxonômica, descrição formal e caracterização bioacústica de **novas espécies e espécimes não documentados**. Em conformidade estrita com os padrões internacionais de bioacústica sistemática (Ragge & Reynolds, 1998; Bennet-Clark, 1999; Márquez et al., 2001), todas as antigas estimativas ecológicas baseadas em espécies pré-fixadas — incluindo a aproximação linear termo-acústica de Dolbear (*termômetro de grilos*) — foram **integralmente abolidas** na versão 4.5.0. O software opera exclusivamente sobre grandezas físico-acústicas puras, auditáveis e livres de extrapolações alométricas ou fisiológicas espécie-dependentes.

---

## SUMÁRIO DO DOCUMENTO 1

- **1.0. Visão Geral da Interface e Carregamento de Arquivos**
  - 1.1. Anatomia da Janela Principal (`MainWindow`)
  - 1.2. Abertura de Arquivos WAV Individuais e Processamento em Lote (*Batch*)
  - 1.3. Monitoramento da Fila de Processamento, Status de Leitura e Cancelamento Cooperativo
- **2.0. Dashboard de Visualização e Compreensão Gráfica**
  - 2.1. Painel 1 — Forma de Onda (Oscilograma) e Envoltória Analítica de Hilbert
  - 2.2. Sistema de Nível de Detalhe (*Level of Detail* — Min-Max LoD)
  - 2.3. Painel 2 — Densidade Espectral de Potência (PSD via Método de Welch)
  - 2.4. Painel 3 — Espectrograma de Curto Tempo (STFT) e Filtro de Tolerância da Portadora
  - 2.5. Painel 4 — Histograma Bivariado de Sintaxe de Pulsos e Duração Média (`twinx`)
- **3.0. Mesa de Edição Interativa e Aprendizado Supervisionado (*Active Learning*)**
  - 3.1. Inspeção de Pulsos e *Hit-Testing* Bidimensional
  - 3.2. Adição Manual de Pulsos Omitidos (Falsos Negativos) e Remoção de Ruídos (Falsos Positivos)
  - 3.3. O Ciclo de Feedback Supervisionado: Botão *"Aprender com Correções"*
  - 3.4. Tabela Completa de Atalhos de Teclado e Mouse
- **4.0. Painel de Exportação Científica (Gráficos e Relatórios)**
  - 4.1. Exportação Modular de Gráficos (`ExportGraphDialog` — PNG 300/600 DPI e PDF Vetorial)
  - 4.2. Exportação do Relatório Sintético e Laudo Técnico (`ExportReportDialog`)
  - 4.3. Exportação de Matrizes Tabulares (`.CSV` Brasileiro/Universal e `.TXT`) para R, Python e PAST
- **5.0. Painel de Transporte e Diagnóstico de Áudio (`AudioTransportPanel`)**
  - 5.1. Reprodução Sincronizada a 60 FPS e Controle de Velocidade Bioacústica
  - 5.2. Diagnóstico de Integridade do Sinal: Indicador de Clipping, SNR Local e Piso de Ruído
- **6.0. Manutenção, Reset e Recuperação de Falhas**
  - 6.1. Restauração dos Parâmetros Algorítmicos de Fábrica (`crinometro_config.json`)
  - 6.2. Diagnóstico e Recuperação Automática do Modelo de Machine Learning (`.skops`)

---

## 1.0. Visão Geral da Interface e Carregamento de Arquivos

### 1.1. Anatomia da Janela Principal (`MainWindow`)

A interface do Crinômetro v4.5.0 foi projetada sob arquitetura de alta densidade informacional com suporte nativo aos temas **Escuro Profundo (Dark Slate — `#101214`)** e **Claro Laboratorial (Light Paper — `#F8FAFC`)**. A janela divide-se em cinco zonas funcionais:

1. **Barra de Ferramentas e Menu Superior (*Header Bar*):** Contém os seletores de ingestão de áudio, acesso aos diálogos de parâmetros matemáticos (`AlgorithmSettingsDialog`), configurações gerais (`GeneralSettingsDialog`), controle do modo de Inteligência Artificial (DSP Puro vs. Classificador Híbrido) e menu de exportação científica.
2. **Painel Lateral Esquerdo — Fila de Arquivos e Sumário Metrológico:** Exibe a lista de gravações `.WAV` carregadas, os cartões de métricas instantâneas (*Total de Chilreios*, *Média de Pulsos/Chilreio* e *Variância*), metadados técnicos do arquivo ativo (duração em segundos e faixa paramétrica ativa) e os botões de ação do ciclo de aprendizado ativo.
3. **Área Central — Host Principal de Visualização (`main_host`):** Exibe em destaque o gráfico maximizado pelo pesquisador (por padrão, o Oscilograma ou o Espectrograma).
4. **Pilha Lateral Direita (`stack_panels`):** Agrupa os três cartões gráficos complementares em visualização sincronizada. Qualquer gráfico da pilha lateral pode ser arrastado pela sua barra de título (`PlotTitleBar`) ou promovido ao painel principal com um clique no botão **Maximizar**.
5. **Rodapé — Painel de Transporte e Timeline Interativa (`AudioTransportPanel`):** Abriga a régua temporal com marcações cromáticas de chilreios (`TimelineWidget`), controles de reprodução de áudio, seletor de taxa de velocidade e barra de progresso com botão de interrupção cooperativa (**✕ Abortar**).

`[PRINT DE TELA: Visão panorâmica da janela principal do Crinômetro v4.5.0 no tema escuro em resolução recomendada de 1920x1080 pixels. Exibir o arquivo "m017_0376.wav" carregado. Destacar com CAIXAS VERMELHAS: (A) Barra Superior de Ações e Configuração; (B) Lista Lateral de Arquivos e Card de Sumário Metrológico à esquerda; (C) Painel Gráfico Principal maximizado ao centro exibindo a Forma de Onda; (D) Pilha vertical direita com os mini-painéis de Espectrograma, PSD de Welch e Histograma Bivariado; (E) Barra de Transporte e Timeline de Áudio no rodapé. Incluir SETAS NUMERADAS: Seta [1] apontando para o botão "+ Adicionar Áudio(s)" no topo esquerdo; Seta [2] apontando para a lista de arquivos carregados; Seta [3] apontando para o indicador de Total de Chilreios e Média/Variância; Seta [4] apontando para o botão de ativação da IA.]`

---

### 1.2. Abertura de Arquivos WAV Individuais e Processamento em Lote (*Batch*)

O Crinômetro processa gravações digitais não comprimidas no formato **RIFF WAVE (`.wav`)** em resoluções de 16 bits, 24 bits, 32 bits PCM ou 32 bits IEEE Float, com taxas de amostragem desde $8\text{ kHz}$ até gravações ultrassônicas de $192\text{ kHz}$ ou $384\text{ kHz}$ (com duração máxima de segurança de 20 minutos por arquivo).

#### Passo a Passo para Carregamento e Análise:

1. **Abertura de Arquivo Único ou Múltiplos Arquivos:**
   - Clique no botão **`+ Adicionar Áudio(s)`** localizado no topo do painel esquerdo (ou utilize o menu **`Arquivo → Abrir Áudio(s) WAV...`**).
   - Na caixa de diálogo do sistema operacional, selecione um ou dezenas de arquivos `.wav` simultaneamente mantendo as teclas `Shift` ou `Ctrl` pressionadas e clique em **Abrir**.
2. **Seleção e Disparo da Análise:**
   - Se apenas um arquivo for adicionado, o `PipelineOrchestrator` inicia imediatamente a análise bioacústica em uma thread secundária (`GenericWorker`) e renderiza os quatro painéis ao término.
   - Se múltiplos arquivos forem carregados para processamento em lote (*Batch Analysis*), clique no botão **`Analisar Todos (Lote)`** no painel lateral esquerdo.
3. **Condicionamento Automático de Canais Estéreo:**
   - Caso a gravação de campo seja estéreo (2 canais), o Crinômetro **não realiza média aritmética cega** entre os canais (evitando cancelamento destrutivo de fase / *comb filtering*). O motor seleciona automaticamente o canal com maior energia eficaz ($\text{RMS}$), garantindo fidelidade de fase da portadora.

---

### 1.3. Monitoramento da Fila de Processamento, Status de Leitura e Cancelamento Cooperativo

Durante o processamento individual ou em lote:
- Cada item na lista de arquivos exibe um ícone de status: **Pendente** (relógio cinza), **Processando** (indicador ativo) ou **Concluído** (marcador verde com a contagem de chilreios detectados).
- Na parte inferior da janela, a barra de progresso detalha o estágio exato do pipeline (*"Lendo WAV..."*, *"Filtrando banda estridulatória..."*, *"Calculando STFT e PSD..."*, *"Agrupando chilreios..."*) e o contador de lote (`[Arquivo k de N]`).
- **Interrupção Segura:** Para cancelar uma análise longa ou um lote inteiro a qualquer instante, clique no botão **`✕ Abortar`** ao lado da barra de progresso. O `WorkerRegistry` sinaliza o evento atômico de parada (`AnalysisAborted`), interrompendo o processamento em menos de $50\text{ ms}$ sem corromper o cache das análises já concluídas.

`[PRINT DE TELA: Recorte focado no Painel Lateral Esquerdo e na Barra de Progresso Inferior (dimensões recomendadas: 850x600 pixels). Exibir uma fila de 8 arquivos WAV em processamento em lote, com os 4 primeiros marcados como concluídos (ícone verde) e o 5º arquivo destacado em azul como ativo. Destacar com CAIXA VERMELHA a barra de progresso inferior mostrando "Analisando lote (5/8): m017_0376.wav (65%)" e o botão vermelho "✕ Abortar". Incluir SETAS NUMERADAS: Seta [1] no botão "Analisar Todos"; Seta [2] no indicador de status do arquivo na fila; Seta [3] no botão "✕ Abortar".]`

---

## 2.0. Dashboard de Visualização e Compreensão Gráfica

O Dashboard do Crinômetro v4.5.0 é composto por **quatro painéis científicos interconectados**, gerenciados pelo controlador `PlotRenderers` e sincronizados temporalmente pelo `NavigationController`.

---

### 2.1. Painel 1 — Forma de Onda (Oscilograma) e Envoltória Analítica de Hilbert

O painel **Forma de Onda** exibe a evolução da amplitude acústica normalizada em função do tempo ($t$, em segundos). Na barra superior deste cartão gráfico, quatro seletores em estilo *chip* permitem ligar ou desligar camadas independentes:

1. **Chip `Sinal Bruto` (Cinza Azulado `#94A3B8`):** Representa o sinal acústico condicionado na banda estridulatória. Permite observar as oscilações rápidas da onda sonora e verificar a simetria física da pressão acústica.
2. **Chip `Envoltória` (Azul Ciano `#0284C7`):** Traça a curva da **Envoltória Analítica de Hilbert** suavizada por janela de Hann e normalizada pelo percentil $99,85$. Esta curva contorna a energia instantânea de cada pulso, permitindo inspecionar:
   - **Transiente de Ataque (*Onset*):** A inclinação de subida rápida quando o *plectrum* inicia o impacto contra os dentes da *pars stridens*.
   - **Ápice do Pulso (*Peak*):** O ponto de máxima transferência de energia mecânica para a harpa alar.
   - **Taxa de Decaimento (*Offset*):** O amortecimento exponencial da membrana alar após o término do fechamento tegminal.
3. **Chip `Min-Max LOD` (Laranja `#F97316`):** Exibe a camada do motor de renderização adaptativa de alta velocidade (`HighPerfLineEngine`).
4. **Chip `Pulsos` (Verde Esmeralda `#10B981`):** Exibe ou oculta os marcadores cromáticos sobre o ápice de cada pulso detectado e agrupado em chilreios, codificados por cor conforme o número de pulsos do chilreio (ex.: Azul Royal para 2 pulsos, Roxo para 3 pulsos, Laranja para 4 pulsos, Verde Esmeralda para 5 pulsos). Pulsos isolados ou rejeitados pelo filtro de portadora aparecem em cinza translúcido (`distant_peaks`).

---

### 2.2. Sistema de Nível de Detalhe (*Level of Detail* — Min-Max LoD)

Em gravações longas (por exemplo, $60\text{ s}$ a $48\text{ kHz} = 2.880.000\text{ amostras}$), um monitor de computador possui apenas cerca de $1.920\text{ pixels}$ horizontais. Se um software comum aplicasse amostragem simples pulando pontos (*stride slicing*), pulsos estreitos de $3\text{ a }15\text{ ms}$ cairiam entre os pontos amostrados e **desapareceriam visualmente** no zoom afastado.

O motor **`HighPerfLineEngine`** do Crinômetro v4.5.0 resolve esse problema através da **Decimação em Blocos Min-Max**:
- O intervalo de tempo visível na tela é particionado em blocos contíguos (*buckets*).
- Dentro de cada bloco, o algoritmo extrai matematicamente o valor mínimo ($y_{\min}$) e o valor máximo ($y_{\max}$) exatos e desenha um par vertical $[y_{\min}, y_{\max}]$.
- **Resultado Prático:** Nenhum pico real de pulso jamais desaparece, independentemente do nível de zoom. Durante o movimento de arraste (*pan*) ou rolagem de zoom, o motor renderiza instantaneamente $300$ blocos a $60\text{ FPS}$ e, $120\text{ ms}$ após o mouse parar (*debounce*), refina o traçado para $4.000$ pontos de altíssima definição.

`[PRINT DE TELA: Painel "Forma de Onda" maximizado (dimensões recomendadas: 1400x550 pixels) exibindo um segmento de 2,0 segundos com quatro chilreios de 5 pulsos cada. Destacar com CAIXAS VERMELHAS: (A) Os quatro chips seletores no cabeçalho do cartão ("Sinal Bruto", "Envoltória", "Min-Max LOD", "Pulsos"); (B) A curva azul contínua da Envoltória de Hilbert contornando o sinal oscilatório cinza; (C) Os marcadores em "X" verdes no topo de cada pulso validado e um marcador "X" cinza em um ruído rejeitado. Incluir SETAS NUMERADAS: Seta [1] apontando para o chip "Envoltória"; Seta [2] apontando para o botão de Lápis (Modo de Edição de Pulsos); Seta [3] apontando para o botão Desfazer "↶"; Seta [4] apontando para o ápice de um pulso com o tooltip flutuante ativo mostrando "Pulso #14 | t = 3.142 s | Amp = 0.84 | f = 5812 Hz".]`

---

### 2.3. Painel 2 — Densidade Espectral de Potência (PSD via Método de Welch)

O painel **Espectro de Potência (PSD)** apresenta a distribuição média de potência acústica por unidade de frequência ($\text{dB/Hz}$ versus $\text{kHz}$ ou $\text{Hz}$), calculada pelo **Método dos Periodogramas Modificados de Welch** (`CricketAnalyzer.compute_psd`).

- **Identificação da Frequência Portadora ($f_c$):** O pico principal mais elevado na banda estridulatória (destacado por um marcador circular vermelho e anotação automática em $\text{kHz}$ e $\text{dB/Hz}$) indica a frequência fundamental de ressonância das tégminas do espécime.
- **Picos Secundários e Harmônicos:** Picos menores em múltiplos inteiros da portadora ($2 f_c, 3 f_c$) revelam os harmônicos naturais da estrutura quitinosa, enquanto picos secundários fora da relação harmônica alertam o pesquisador para a presença de espécies simpátricas cantando no fundo da gravação.
- **Faixa de Tolerância Espectral:** A banda vertical sombreada ao redor da portadora ilustra visualmente a janela de aceitação do filtro de rejeição de banda estreita ($\pm \Delta f_{\text{tol}}$).

---

### 2.4. Painel 3 — Espectrograma de Curto Tempo (STFT) e Filtro de Tolerância da Portadora

O painel **Espectrograma** exibe a evolução temporal-frequencial do áudio como um mapa de calor bidimensional (Tempo no eixo $X$, Frequência no eixo $Y$, e Densidade de Energia em $\text{dB}$ codificada pela paleta de cores *Viridis* ou *Magma*).

#### Controles Exclusivos da Barra do Espectrograma (`specCtrlBar`):
1. **Bloco de Escala Y (`Y: min – max` e Unidade `kHz`/`Hz`):** Permite digitar diretamente os limites inferior e superior de frequência ou alternar a escala entre $\text{kHz}$ e $\text{Hz}$ em tempo real.
2. **Slider Vertical de Eixo Y (`specYSlider`):** Posicionado à esquerda do gráfico, permite comprimir ou expandir o teto de frequência (até $50\text{ kHz}$ em gravações ultrassônicas) com um simples arrastar vertical.
3. **Presets de Enquadramento Rápido (*Segmented Control*):**
   - **`10k`:** Enquadra a janela clássica de $0\text{ a }10\text{ kHz}$.
   - **`Focal`:** Aplica zoom automático estrito na banda da frequência portadora detectada ($f_c \pm \text{tolerância}$).
   - **`Total`:** Expande o eixo $Y$ até a frequência máxima de Nyquist ($f_s / 2$) do arquivo WAV.
4. **Badge da Portadora (`FP: X.XX kHz`) e Controle de Tolerância em Tempo Real:**
   - Exibe a Frequência Portadora modal calculada.
   - O **Slider Horizontal de Filtro** (`25 Hz` a `1500 Hz`), a caixa numérica (`±700 Hz`) e os botões de atalho rápido (**`±300`**, **`±500`**, **`±700`**, **`±1000`**) ajustam em tempo real a largura da faixa espectral aceita. Qualquer pulso cuja frequência instantânea caia fora de $[f_c - \text{tol}, f_c + \text{tol}]$ é imediatamente reclassificado como ruído externo (`distant_peaks`), atualizando os chilreios e métricas em menos de $25\text{ ms}$ sem precisar recalcular a FFT!

`[PRINT DE TELA: Painel "Espectrograma" maximizado (dimensões recomendadas: 1400x600 pixels). Destacar com CAIXAS VERMELHAS: (A) O bloco de escala Y ("Y: 0.0 – 10.0 kHz") à esquerda da barra de controles; (B) O grupo de botões de Preset ("10k", "Focal", "Total"); (C) O Badge azul "FP: 5.81 kHz", o slider horizontal de tolerância, o spinbox "±700 Hz" e os chips rápidos "±300 | ±500 | ±700 | ±1000"; (D) O slider vertical à esquerda do eixo Y. Incluir SETAS NUMERADAS: Seta [1] no botão "Focal"; Seta [2] no slider de tolerância da portadora; Seta [3] apontando para as manchas brilhantes dos pulsos alinhadas sobre a frequência portadora no mapa de calor.]`

---

### 2.5. Painel 4 — Histograma Bivariado de Sintaxe de Pulsos e Duração Média (`twinx`)

O painel **Histograma de Pulsos por Chilreio** sintetiza a assinatura estatística e sintática do canto através de um gráfico de eixo duplo (`twinx`):
- **Eixo Y Esquerdo (Barras Verticais Coloridas):** Exibe a contagem absoluta de chilreios agrupados pela quantidade de pulsos por chilreio (ex.: quantos chilreios possuem 4 pulsos, 5 pulsos, 6 pulsos). Permite identificar imediatamente a **Moda Sintática** da espécie e verificar se há **multimodalidade acústica** (espécies com repertório composto ou dois indivíduos distintos na gravação).
- **Eixo Y Direito (Linha Tracejada Vermelha com Marcadores Circulares):** Exibe a **Duração Média do Chilreio (em $\text{ms}$)** para cada classe de contagem de pulsos. Em estridulações legítimas governadas por um Gerador Central de Padrões (CPG) neuromotor estável, a linha vermelha apresenta crescimento monotônico quase linear conforme o número de pulsos aumenta. Quebras abruptas nessa linha alertam o pesquisador para falsos positivos ou fusões indevidas de chilreios.

`[PRINT DE TELA: Painel "Histograma Bivariado" em detalhe (dimensões recomendadas: 900x500 pixels). Exibir barras para 4 pulsos (laranja), 5 pulsos (verde esmeralda, barra dominante com 60 ocorrências) e 6 pulsos (rosa magenta). Destacar com CAIXAS VERMELHAS: (A) Eixo Y esquerdo ("Contagem de Chilreios"); (B) Eixo Y direito em vermelho ("Duração Média (ms)"); (C) A linha tracejada vermelha ascendente conectando as durações médias sobre as barras; (D) A legenda inferior unificada. Incluir SETAS NUMERADAS: Seta [1] na barra modal de 5 pulsos; Seta [2] no ponto da curva vermelha indicando a duração média em milissegundos.]`

---

## 3.0. Mesa de Edição Interativa e Aprendizado Supervisionado (*Active Learning*)

Gravações de campo em ambientes tropicais frequentemente apresentam baixa relação sinal-ruído (SNR), reverberação em folhagem e sobreposição de coros polifônicos. Para garantir precisão metrológica absoluta antes da publicação de uma nova espécie, o Crinômetro v4.5.0 oferece uma **Mesa de Edição Interativa Bidimensional** acoplada ao controlador `EditorController`.

---

### 3.1. Inspeção de Pulsos e *Hit-Testing* Bidimensional

Ao passar o cursor do mouse sobre qualquer ponto da **Forma de Onda** ou do **Espectrograma**, o algoritmo de poda espacial $O(K)$ identifica instantaneamente o pulso mais próximo em um raio de $30\text{ pixels}$ e exibe uma caixa informativa (*tooltip*) contendo:
- Status do pulso (**Pulso Validado** do chilreio ou **Pico Rejeitado / Fora da Banda** com o motivo exato do descarte em `discarded_peaks_reasons`);
- Instante temporal exato ($t$ em segundos e milissegundos);
- Amplitude normalizada do envelope e Frequência Dominante instantânea ($\text{Hz}$).

---

### 3.2. Adição Manual de Pulsos Omitidos (Falsos Negativos) e Remoção de Ruídos (Falsos Positivos)

Para iniciar a curadoria manual:

1. **Ativar o Modo de Edição de Pulsos:**
   - Clique no ícone de **Lápis (`✎`)** localizado no canto superior direito da barra de título do painel **Forma de Onda** ou do painel **Espectrograma**. O botão ficará destacado em azul brilhante (`#1F6FEB`), indicando que os cliques esquerdos naquele gráfico estão dedicados à edição de pulsos.
2. **Remover um Falso Positivo (Ruído Indevidamente Marcado):**
   - Clique com o **Botão Esquerdo do Mouse** diretamente sobre um marcador de pulso existente (`o` verde ou `^` azul).
   - O pulso é removido da lista de pulsos verificados (`peaks_user_verified`), recebe um marcador vermelho **`×`** (indicando exclusão explícita pelo pesquisador), e todos os chilreios, contagens, médias, variâncias e o Histograma Bivariado são recalculados instantaneamente via `EditorController.recalculate_metrics()`.
3. **Adicionar um Falso Negativo (Pulso Legítimo Omitido):**
   - Clique com o **Botão Esquerdo do Mouse** sobre o pico desejado na curva da envoltória (ou sobre a mancha energética do pulso no Espectrograma).
   - **Snapping Inteligente:** Se houver um candidato detectado ou um pico previamente descartado pelo filtro de portadora (`distant_peaks`) dentro da janela de tolerância de $\pm 15\text{ ms}$, o cursor faz *snap* automático para o ápice exato da amostra física e resgata o pulso! Caso contrário, insere um novo pulso no instante e frequência clicados, demarcado com um triângulo azul **`^`**.
4. **Desfazer Edições (`Undo` Transacional):**
   - Pressione **`Ctrl + Z`** no teclado ou clique no botão **`↶`** na barra do gráfico para reverter passo a passo até as últimas $50$ alterações manuais, restaurando integralmente os metadados espectrais e razões de descarte.

`[PRINT DE TELA: Comparativo lado a lado ou destaque da Mesa de Edição no painel Forma de Onda (dimensões recomendadas: 1400x550 pixels). Mostrar o botão de Lápis ativado em azul no topo direito. Na curva do oscilograma, destacar com CAIXAS VERMELHAS os três tipos de marcadores de curadoria: (A) Círculo Verde ("o") indicando pulso detectado e confirmado; (B) Triângulo Azul ("^") indicando pulso adicionado manualmente pelo pesquisador; (C) Cruz Vermelha ("x") indicando ruído/falso positivo removido manualmente. Incluir SETAS NUMERADAS: Seta [1] no botão Lápis ativo; Seta [2] no botão Desfazer "↶"; Seta [3] no botão "Aprender com Correções" no painel lateral esquerdo.]`

---

### 3.3. O Ciclo de Feedback Supervisionado: Botão *"Aprender com Correções"*

Após revisar e corrigir manualmente alguns chilreios de uma gravação desafiadora, o pesquisador pode transferir esse conhecimento para o motor de Inteligência Artificial clicando no botão **`Aprender com Correções`** (no painel lateral esquerdo):

1. **Extração de Vetores de 20 Atributos:** O `PulseLearner` analisa todos os pulsos confirmados/adicionados (classe positiva $y = 1$) e todos os falsos positivos removidos pelo usuário (classe negativa explícita $y = 0$), além de minerar negativos em regiões de silêncio e ruído de fundo.
2. **Indução de Regras de Poda Contrastiva (*Hard Negative Mining*):** O sistema identifica quais atributos físicos (ex.: largura FWHM, fator de crista, relação sinal-ruído local) separam os ruídos removidos dos pulsos verdadeiros, criando barreiras rápidas $O(1)$ com margem de segurança de $30\%$.
3. **Ajuste Local Seguro sem Corromper a Base Histórica:**
   - Os parâmetros adaptativos finos (`_adaptive_overrides`: proeminência e limites de largura) são ajustados na sessão atual (`SessionContext`) para refinar a detecção daquele arquivo e lote específico.
   - O conjunto histórico de treinamento é limitado por uma janela deslizante estratificada de até $5.000$ amostras e serializado de forma **atômica e criptograficamente segura via `skops`** (`modelo_treinado.skops`), impedindo que um único áudio atípico apague ou corrompa o aprendizado acumulado em sessões anteriores.

---

### 3.4. Tabela Completa de Atalhos de Teclado e Mouse

| Comando / Interação | Atalho / Ação | Escopo / Comportamento no Crinômetro v4.5.0 |
| :--- | :--- | :--- |
| **Reproduzir / Pausar Áudio** | `Espaço` (Barra de Espaço) | Alterna imediatamente entre Play e Pause a partir da posição atual do cursor. |
| **Desfazer Última Edição de Pulso** | `Ctrl + Z` | Reverte de forma transacional a última adição ou remoção manual de pulso (`EditorController.undo`). |
| **Zoom Horizontal Sincronizado** | `Roda do Mouse (Scroll)` | Amplia ou reduz o eixo temporal ($X$) simultaneamente na Forma de Onda e no Espectrograma, mantendo o ponto sob o cursor ancorado. |
| **Pan / Arraste Temporal** | `Botão Direito do Mouse + Arrastar` (ou `Botão Esquerdo` com Lápis inativo) | Desloca horizontalmente a janela de visualização sincronizada entre Oscilograma e Espectrograma a $60\text{ FPS}$. |
| **Alinhar Cursor de Áudio no Gráfico** | `Clique Esquerdo Simples` (com Lápis inativo) | Posiciona a linha vertical de reprodução exatamente no instante $t$ clicado e exibe marcador de alinhamento. |
| **Adicionar / Remover Pulso** | `Clique Esquerdo Simples` (com Lápis `✎` ativo) | Alterna o estado do pulso sob o cursor (remove se já validado; adiciona/resgata se ausente ou descartado). |
| **Reorganizar Painéis Gráficos** | `Arrastar Barra de Título do Gráfico` | Troca a posição do cartão gráfico na pilha lateral ou promove-o para a área principal (`swap_main_panel`). |
| **Maximizar / Restaurar Painel** | Clique no ícone `⛶` (`plotMaximize`) | Alterna o gráfico selecionado com o painel principal em destaque. |

---

## 4.0. Painel de Exportação Científica (Gráficos e Relatórios)

O Crinômetro v4.5.0 introduz uma arquitetura de exportação científica totalmente desacoplada da resolução do monitor através da fábrica pura `FigureFactory` (`ui/figure_factory.py`) e do controlador `ExportController`.

---

### 4.1. Exportação Modular de Gráficos (`ExportGraphDialog` — PNG 300/600 DPI e PDF Vetorial)

Para exportar figuras prontas para submissão a periódicos científicos internacionais (*Zootaxa*, *Journal of Orthoptera Research*, *Bioacoustics*):

1. **Onde Clicar:** Na barra superior da janela principal, clique no botão **`Exportar Gráfico(s)`** (ou acesse o menu **`Exportar → Exportar Gráficos de Alta Resolução...`**).
2. **Preenchimento do Diálogo (`ExportGraphDialog`):**
   - **Seleção de Painéis:** Marque individualmente quais gráficos deseja exportar (**Forma de Onda**, **Espectrograma STFT**, **Espectro de Potência PSD**, **Histograma Bivariado**) ou selecione a opção **Dashboard Combinado (Mosaico 2×2)**.
   - **Formato e Resolução Metrológica:**
     - **PNG Rasterizado:** Escolha a densidade de pontos por polegada em **`150 DPI`** (prévia rápida), **`300 DPI`** (padrão editorial) ou **`600 DPI`** (alta definição tipográfica para linhas finas).
     - **PDF / SVG Vetorial:** Exporta curvas e textos como primitivas matemáticas vetoriais escaláveis infinitamente sem perda de nitidez.
   - **Tema Visual de Publicação:**
     - **Claro (Publicação Científica):** Fundo branco puro (`#FFFFFF`), eixos em cinza ardósia escuro (`#334155`) e alto contraste para impressão em papel.
     - **Escuro (Apresentação / Slides):** Preserva a estética escura da interface.
   - **Faixa Temporal Exportada (*Time Range*):**
     - **Áudio Completo (*Total*):** Renderiza toda a extensão da gravação de $0\text{ s}$ até a duração final.
     - **Janela Atual (*Viewport Atual*):** Exporta exatamente o recorte temporal ($[t_{\min}, t_{\max}]$) em que você aplicou zoom na tela, ideal para ilustrar a morfologia fina de um único chilreio ou pulso!
   - **Camadas e Sobreposições:** Caixas de seleção permitem incluir ou ocultar grades de fundo (*Grid*), marcadores de pulsos validados, linha de frequência portadora e anotações de pico.
3. **Pré-visualização ao Vivo (*Live Preview*):** O painel direito do diálogo renderiza uma miniatura fiel da figura antes de salvar. Clique em **`Exportar`** para gravar os arquivos em disco.

`[PRINT DE TELA: Janela modal "Exportar Gráficos Científicos" (ExportGraphDialog, dimensões recomendadas: 1050x680 pixels). À esquerda, exibir os grupos de configuração: Checkboxes dos 4 painéis, seletor de Formato (PNG / PDF), seletor de Resolução (300 DPI / 600 DPI), seletor de Tema (Claro Publicação vs. Escuro) e Faixa Temporal (Áudio Completo vs. Recorte do Zoom Atual). À direita, exibir o canvas de Pré-visualização ao vivo com fundo branco de publicação. Destacar com CAIXAS VERMELHAS o seletor de DPI, a opção "Recorte do Zoom Atual" e o botão azul "Exportar". Incluir SETAS NUMERADAS: Seta [1] na seleção de painéis; Seta [2] na escolha de 600 DPI; Seta [3] na escolha do intervalo temporal; Seta [4] no botão "Exportar".]`

---

### 4.2. Exportação do Relatório Sintético e Laudo Técnico (`ExportReportDialog`)

Para gerar o laudo analítico consolidado em PDF (compilado pelo motor tipográfico `ReportLab` com rodapé numerado `NumberedCanvas`):

1. **Onde Clicar:** Clique no botão **`Exportar Relatório`** na barra superior.
2. **Metadados de Rastreabilidade Científica (`_collect_metadata`):**
   - **Pesquisador(a) / Operador:** Nome do responsável pela análise e curadoria.
   - **Instituição / Laboratório:** Universidade ou centro de pesquisa (impresso no cabeçalho institucional do laudo).
   - **Localização Geográfica / Coordenadas:** Município, unidade de conservação ou coordenadas GPS da coleta.
   - **Temperatura de Gravação (Medida em Campo):** Campo textual livre para registro da temperatura aferida por termohigrômetro no ato da coleta (sem qualquer inferência circular por software).
   - **Equipamento de Gravação:** Modelo do gravador digital e microfone utilizados (ex.: *Tascam DR-100mkIII + Sennheiser ME66*).
   - **Tabela por Arquivo / Espécime:** Para cada arquivo `.WAV` selecionado, preencha o **Código do Espécime (Voucher / Tombo)** e a **Identificação Taxonômica Preliminar (Espécie / Morfotipo)** (ex.: *Gryllus sp. nov. "Serra do Cipó"*). Campos deixados em branco são automaticamente omitidos do cabeçalho do PDF para manter a diagramação limpa.
3. **Ativação Modular de Seções Analíticas (`ReportSectionFlags`):**
   - Marque ou desmarque livremente as seções do documento:
     - `[x] Resumo Executivo e Consolidação por Espécime`
     - `[x] Tabela de Métricas Bioacústicas e Espectrais (IPI, ICI, Portadora, Duração)`
     - `[x] Diagnóstico Estatístico de Cadência Rítmica (Regressão Linear e Teste t de Student)`
     - `[x] Figuras e Gráficos Analíticos Incorporados`
     - `[x] Listagem Detalhada de Chilreios e Pulsos (Timestamps ms)`

`[PRINT DE TELA: Janela modal "Configuração e Exportação de Relatório" (ExportReportDialog, dimensões recomendadas: 920x650 pixels). Destacar com CAIXAS VERMELHAS: (A) Campos de metadados do pesquisador, instituição, equipamento e temperatura medida em campo; (B) Tabela editável vinculando cada arquivo WAV ao seu "Cód. Espécime" e "Espécie / Morfotipo"; (C) Checkboxes das 5 seções modulares do relatório; (D) Botões de formato de saída (PDF, CSV Brasileiro, CSV Universal, TXT). Incluir SETAS NUMERADAS: Seta [1] nos campos de metadados; Seta [2] na tabela de espécimes; Seta [3] nas caixas de seleção de seções; Seta [4] no botão "Gerar Relatório".]`

---

### 4.3. Exportação de Matrizes Tabulares (`.CSV` Brasileiro/Universal e `.TXT`) para R, Python e PAST

Além do laudo PDF, o Crinômetro exporta os dados brutos e sumarizados em formatos tabulares estruturados (`generate_csv_report` e `generate_txt_report`):

- **Modo CSV Brasileiro (`csv_mode="brazilian"`):** Codificado em `UTF-8 com BOM (utf-8-sig)`, utiliza ponto e vírgula (`;`) como delimitador de colunas e vírgula (`,`) como separador decimal. Abre diretamente no **Microsoft Excel em Português** com acentuação e colunas perfeitamente alinhadas.
- **Modo CSV Universal (`csv_mode="universal"`):** Codificado em `UTF-8 puro`, utiliza vírgula (`,`) como delimitador, ponto (`.`) como separador decimal e cabeçalhos padronizados em `snake_case` (`file_name`, `specimen_id`, `species`, `total_chirps`, `total_pulses`, `pulses_per_chirp_mean`, `pulses_per_chirp_mode`, `pulses_per_chirp_var`, `carrier_freq_hz`, `ici_mean_ms`, `ipi_mean_ms`, `pulse_dur_mean_ms`, `chirp_dur_mean_ms`). Pronto para ingestão imediata via `pandas.read_csv()` em **Python**, `read.csv()` no **R** ou importação direta no software morfométrico/estatístico **PAST**.

---

## 5.0. Painel de Transporte e Diagnóstico de Áudio (`AudioTransportPanel`)

### 5.1. Reprodução Sincronizada a 60 FPS e Controle de Velocidade Bioacústica

O painel inferior integra o reprodutor multimídia de baixa latência (`QMediaPlayer` + `QAudioOutput`) à régua gráfica `TimelineWidget`:
- **Marcadores de Chilreios na Timeline:** Cada chilreio validado é desenhado na régua inferior como uma bandeira vertical alternando entre âmbar (`#F0A84B`) e azul (`#3F94D5`), permitindo saltar diretamente para regiões de atividade vocal mesmo em arquivos longos com grandes períodos de silêncio.
- **Controle de Velocidade de Reprodução (`0.25x`, `0.5x`, `1.0x`, `1.5x`, `2.0x`):**
  - Na bioacústica de Orthoptera, os pulsos individuais sucedem-se a intervalos de apenas $15\text{ a }35\text{ ms}$ (velocidade superior à resolução temporal do ouvido humano, que funde eventos separados por menos de $\sim 50\text{ ms}$ em um único som contínuo).
  - Ao reduzir a velocidade para **`0.25x`** ou **`0.5x`**, o pesquisador consegue ouvir distintamente cada impacto individual dos dentes da lima estridulatória (*tooth strikes*), auditando acusticamente se um chilreio possui 4, 5 ou 6 pulsos enquanto acompanha o cursor luminoso atravessar cada marcador `×` na tela!
  - *Nota Técnica sobre Time-Stretch vs. Pitch-Shift:* Para inspeção de envelopes temporais em frequências audíveis ($3\text{–}8\text{ kHz}$), a desaceleração expande a escala temporal preservando o alinhamento exato do cursor com os timestamps reais no gráfico. Para gravações de espécies com portadoras ultrassônicas ($> 20\text{ kHz}$, inaudíveis ao ouvido humano), a redução da taxa efetiva de reprodução atua simultaneamente como rebaixamento heteródino/proporcional de frequência (*pitch-down*), trazendo a energia ultrassônica para dentro do espectro audível humano.

---

### 5.2. Diagnóstico de Integridade do Sinal: Indicador de Clipping, SNR Local e Piso de Ruído

O Crinômetro monitora continuamente a qualidade metrológica do arquivo `.WAV`:
- **Proteção contra Clipping (Saturação A/D):** Quando o ganho do gravador de campo foi ajustado alto demais, o topo da onda sonora é ceifado no limite digital ($\pm 1,0$). O motor normaliza a envoltória pelo percentil $99,85$ (`scale_p99`) e avalia a curvatura no ápice (`peak_sharpness_rel`) e o fator de crista (`crest_factor`), evitando que o achatamento por saturação divida um pulso saturado em dois picos falsos nas bordas do platô.
- **Estimativa de SNR Local (`local_snr_db`) e Piso de Ruído (`noise_floor`):** Para cada pulso, a relação sinal-ruído é aferida em decibéis comparando a amplitude do pico com o desvio padrão do ruído de fundo circundante ($20 \log_{10}(A_{\text{peak}} / \sigma_{\text{local}})$), exibida detalhadamente nos relatórios e utilizada na ponderação de confiança.

`[PRINT DE TELA: Barra de Transporte Inferior e TimelineWidget em detalhe (dimensões recomendadas: 1400x160 pixels). Destacar com CAIXAS VERMELHAS: (A) Botão Play/Pause e contador de tempo em milissegundos ("00:03.14 / 00:38.76"); (B) Seletor de velocidade de reprodução ("0.25x | 0.5x | 1.0x"); (C) A régua TimelineWidget mostrando as bandeiras coloridas (âmbar e azul) de cada chilreio ao longo do tempo e a agulha vertical do cursor de reprodução. Incluir SETAS NUMERADAS: Seta [1] no botão Play; Seta [2] no seletor de desaceleração 0.25x; Seta [3] nas bandeiras de chilreio na régua de tempo.]`

---

## 6.0. Manutenção, Reset e Recuperação de Falhas

### 6.1. Restauração dos Parâmetros Algorítmicos de Fábrica (`crinometro_config.json`)

O arquivo de configuração persistente fica armazenado no diretório de dados do usuário (`%APPDATA%\Crinometro\crinometro_config.json` no Windows ou `~/.config/Crinometro/crinometro_config.json` no Linux/macOS).

Caso o pesquisador tenha alterado limites de filtro passa-faixa (`b1_min`, `b1_max`), janelas de IPI (`gap_min`, `gap_max`) ou limiares de amplitude e deseje retornar à calibração metrológica original:
1. Acesse o menu superior **`Configurações → Restaurar Padrões de Fábrica`** (ou clique no botão **`Restaurar Padrões`** dentro do diálogo de Parâmetros do Algoritmo).
2. Confirme na caixa de diálogo. O método `MainWindow.reset_to_defaults()` restaura imediatamente o dicionário `DEFAULT_ALGO_PARAMS`, limpa sobreposições adaptativas (`_adaptive_overrides`), grava o estado limpo de forma atômica sob trava `CONFIG_LOCK` e reanalisa o arquivo ativo do zero.

---

### 6.2. Diagnóstico e Recuperação Automática do Modelo de Machine Learning (`.skops`)

O Crinômetro v4.5.0 foi projetado sob o paradigma de **Tolerância a Falhas Determinística (*Graceful Degradation*)**:

1. **Inicialização em Modo DSP Puro:** Por padrão, o programa inicia com a filtragem por IA desativada, operando exclusivamente com equações determinísticas de Processamento Digital de Sinais (Butterworth + Hilbert + STFT + Portadora Modal).
2. **Auditoria de Segurança e Integridade do `.skops`:** Quando o modelo supervisionado (`%APPDATA%\Crinometro\modelo_treinado.skops`) é carregado, o `PulseLearner` inspeciona todos os tipos da árvore sintática via `skops.io.get_untrusted_types()`, permitindo exclusivamente classes matemáticas seguras (`sklearn.*`, `numpy.*`, `scipy.*`).
3. **Quarantena e Fallback Automático (`degraded = True`):**
   - Se o arquivo `.skops` ou o `crinometro_config.json` estiver corrompido (por exemplo, após queda brusca de energia em outro software ou incompatibilidade de versão do `scikit-learn`), o módulo `utils/persistence.py` move automaticamente o arquivo defeituoso para quarentena (`.corrupted` / `.corrupt-<timestamp>`), restaura o backup `.bak` se disponível, e ativa o sinalizador `PulseLearner.degraded = True`.
   - O sistema **jamais trava ou fecha abruptamente**: ele reverte transparentemente para o classificador físico não-supervisionado (GMM Bimodal + Heurística DSP) e exibe um aviso claro na interface.
4. **Reset Manual da IA:** A qualquer momento, o usuário pode clicar em **`Resetar Aprendizado da IA`** no menu superior. O método `PulseLearner.reset()` apaga o arquivo `modelo_treinado.skops` em disco, limpa as regras de poda contrastiva (`pruning_rules`) e reinicia o classificador limpo.
