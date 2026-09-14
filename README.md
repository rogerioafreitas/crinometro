# 🦗 Crinômetro v4.1.2

> **Software Avançado para Bioacústica, Processamento Digital de Sinais (DSP) e Aprendizado Ativo em Grylloidea**

---

## 🤖 Declaração de Assistência por Inteligência Artificial
> [!NOTE]
> **Aviso de Desenvolvimento com IA:**
> Este projeto foi desenvolvido, refatorado e otimizado com o auxílio de **Inteligência Artificial (Google DeepMind / Antigravity / Gemini)** em colaboração com o autor, incluindo o design modular, algoritmos bioacústicos avançados, plasticidade ativa com HistGradientBoosting, regras rígidas de poda contrastiva, interface moderna em PyQt6 e automação de empacotamento.

---

## 📥 Download das Versões Compiladas (.exe)

Você pode baixar os executáveis prontos para uso diretamente no Google Drive oficial do projeto:

🔗 **[Acessar Pasta de Downloads no Google Drive](https://drive.google.com/drive/folders/1CSjbYE-mql_Sg9qmV-argU05RjpwnmpT?usp=sharing)**

### 💡 Qual formato devo baixar? (Guia Descomplicado)

| Formato | Como funciona? | Para quem é recomendado? |
| :--- | :--- | :--- |
| **Versão Onedir (Pasta `Crinometro_v4.1.2` / `.zip`)** | O executável vem acompanhado de suas pastas e bibliotecas já pré-extraídas. Basta descompactar o `.zip` e abrir o `Crinometro_v4.1.2.exe` ou `Crinometro.exe`. | **Recomendado:** abertura instantânea, altíssimo desempenho e eliminação de falsos positivos de antivírus. |
| **Versão Onefile (Arquivo Único)** | Um arquivo `.exe` individual e portátil. Pronto para rodar diretamente com dois cliques, sem precisar instalar ou extrair nada no seu computador. | Ideal para quem busca **praticidade e portabilidade**, podendo levar o programa direto em um pendrive. |

---

## 📌 Regra de Versionamento (`vX.Y.Z`)

O projeto adota o padrão semântico de versionamento estruturado em três níveis:

- **Major ($X$):** Grandes saltos arquiteturais e reestruturações completas de escopo sob comando explícito (ex: `v4.0.x` introduzindo a segregação acústica focal vs. coro distante).
- **Minor ($Y$):** Qualquer mudança funcional, nova complexidade algorítmica, inclusão de recursos ou modificação visual significativa na interface que **demande registro ou alteração na documentação técnica** (ex: `v4.0.x` $\rightarrow$ `v4.1.0` $\rightarrow$ `v4.1.2`).
- **Patch / Correções ($Z$):** Correções pontuais de bugs internos, pequenos ajustes cosméticos ou melhorias de estabilidade que **não alteram as diretrizes nem exigem atualização no relatório técnico**.

---

## 📚 Manuais e Documentações em PDF

Documentações completas e diagramadas estão disponíveis na pasta [`docs/`](docs/):

1. 📄 **[Manual Técnico e Científico](docs/Crinometro_Manual_Tecnico_Cientifico.pdf):** Destinado a pesquisadores, biólogos e ecólogos. Detalha a formulação matemática de filtros Butterworth, demodulação de Hilbert, arquitetura do classificador supervisionado e segregação focal via GMM.
2. 📘 **[Guia Prático e Descomplicado](docs/Crinometro_Guia_Pratico_Didatico.pdf):** Destinado a estudantes, leigos e entusiastas. Explicação didática passo a passo, guia visual das 10 cores e dicas práticas de gravação em campo.

---

## ✨ Funcionalidades Principais

- 🎧 **Carregamento & Gerenciamento de Áudios:** Suporte a arquivos `.wav` mono e estéreo com reprodução interativa, seleção individual por caixas de marcação e limpeza seletiva.
- ⚡ **Processamento em Lote:** Seleção múltipla com botão *"⚡ Analisar Selecionados"* e *"Selecionar tudo"* para cálculo bioacústico automático em massa.
- 🎨 **Paleta Canônica de 10 Cores:** Mapeamento de 2 a 10 pulsos (mais cor extra para escopos amplos) compartilhado de forma unívoca entre Onda, Histograma, Frequência e Espectrograma.
- 🌊 **Análise de Onda Acústica (DSP):**
  - Envoltória analítica contínua via Transformada de Hilbert.
  - Filtro digital Butterworth passa-faixa IIR de fase zero (`sosfiltfilt`).
  - Detecção adaptativa de picos e pulsos, com limiar mínimo padrão de 3 pulsos por chilreio (`min_p = 3`).
- 🪟 **Mini Janelinhas Arredondadas & Arraste Fluido com Previsão Visual (Drag & Drop):**
  - Gráficos laterais desenhados com cartões de cantos arredondados (`14px`) nativos em Qt (`QFrame`) e transparência de canvas (`patch.set_alpha(0.0)`).
  - Enquadramento pixel-exact adaptativo que impede cortes de rótulos dos eixos ("seconds", "Hz", "Amplitude") com e sem áudio carregado.
  - **Arraste e Solte com Previsão Visual:** Sistema fluido de reordenação com moldura indicadora translúcida (*drop indicator*). A reorganização visual só é aplicada no momento em que o mouse é solto, eliminando piscamentos e redraws intermediários.
  - **Troca Rápida com Gráfico Principal:** Soltar qualquer mini janela em cima da área principal realiza o swap imediato com o painel maximizado.
- 🧠 **Bioacústica Avançada & Plasticidade Ativa (PulseLearner):**
  - **Modo Padrão DSP Puro:** O software inicializa em modo estritamente acústico, permitindo ativar o módulo de IA sob demanda.
  - **Hard Negative Rule Induction:** Indução automática de regras rígidas de poda com margem de segurança de 30% a partir dos falsos positivos removidos manualmente pelo usuário.
  - **Filtro Fisiológico Inter-Chilreio (ICI Gate):** Expulga ecos e candidatos espúrios que violem o período refratário natural ($0.7 \times \text{ICI}_{mediano}$).
  - **Segregação Focal vs. Coro Distante via GMM Bimodal:** Modelação física de atenuação atmosférica e amplitude relativa.
  - **Classificador Supervisionado Leve e Ultrarrápido:** Treinamento em menos de 100 ms com `HistGradientBoostingClassifier`.
  - **Edição Manual com Hit-box Snapping Adaptativo:** Tolerância de 15px e teto de 20ms para confirmar ou remover pulsos com máxima precisão ergonômica.
- 🔗 **Sincronização Temporal Compacta (`btn_sync`):**
  - Botão quadrado compacto (32x32px) posicionado estrategicamente ao lado de *"Reanalisar"*.
  - Trava e sincroniza zoom e pan no eixo X com precisão de milissegundos.
  - Tooltips detalhados ao passar o mouse em todos os botões de ação.
- 🚀 **Desempenho Otimizado a 60 FPS & Barra Lateral Estável:**
  - Motor gráfico com decimação adaptativa de pontos e limitador de taxa de renderização (18 ms) para pan sem engasgos.
  - Barra lateral de arquivos com largura estável e trava mecânica mínima de 220px, impedindo que análises subsequentes encolham a barra.
  - Eliminação total de barras de rolagem redundantes e elisão dinâmica de nomes longos.
- 📑 **Exportação de Relatórios de Publicação (PDF e TXT):**
  - **Relatório Completo em PDF (ReportLab):** Cabeçalho institucional, parâmetros de detecção, métricas globais consolidadas, diagnóstico rítmico fisiológico automatizado (regressão linear do ICI e coeficiente de variação), tabela sequencial detalhada de chilreios com timestamps em centésimos (`mm:ss.cc`) e numeração "Página X de Y".
  - **Relatório Simplificado Multiaudio Compacto em PDF:** Síntese bioacústica comparativa consolidada, agrupando múltiplos áudios de forma contínua por página sem desperdício de espaço, omitindo apenas a listagem sequencial de chilreios.
  - **Tabela Estruturada em TXT:** Formatação amigável para importação direta no R, Python, PAST e JASP.
- 🎭 **Launcher Interativo Vetorial & Tela de Inicialização Elegante:**
  - Mascote animado com estados dinâmicos (dormindo, acordando, expandindo), partículas Zzz e frases de bioacústica com humor inteligente.
  - Janela translúcida com cantos arredondados, borda acetinada e efeito de sombra suave multicamadas (*drop shadow*) projetada sobre o desktop.
  - Totalmente integrado como ponto de entrada oficial do aplicativo e das compilações executáveis (`.exe`).


---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Interface Gráfica:** PyQt6 / QtMultimedia
- **Processamento Numérico e Sinais:** NumPy, SciPy (Signal, Integrate, Special, IO)
- **Machine Learning:** Scikit-Learn (HistGradientBoostingClassifier, RandomForestClassifier, GaussianMixture)
- **Visualização Científica:** Matplotlib
- **Geração de Documentos:** ReportLab, Pillow
- **Empacotamento e Distribuição:** PyInstaller

---

## 🚀 Como Executar pelo Código-Fonte

### 1. Clonar o repositório
```bash
git clone https://github.com/rogerioafreitas/crinometro.git
cd crinometro
```

### 2. Criar e ativar o ambiente virtual
```bash
python -m venv .venv
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Linux/macOS:
source .venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install PyQt6 numpy scipy scikit-learn matplotlib reportlab pillow pyinstaller
```

### 4. Executar a aplicação
```bash
python crinometro__laucher.py
```

---

## 📬 Feedbacks, Dúvidas e Sugestões

Para enviar dúvidas, relatar problemas ou sugerir novas melhorias para o aplicativo, entre em contato diretamente pelo e-mail:

📧 **rda.freitas.2002@gmail.com**  
*(Por favor, envie sua mensagem com o assunto **"Crinômetro"**).*

---

## 👤 Autor
- **rogerioafreitas**

