# 🦗 Crinômetro v3.5.0

> **Software Avançado para Bioacústica, Processamento Digital de Sinais (DSP) e Aprendizado Ativo em Grylloidea**

---

## 🤖 Declaração de Assistência por Inteligência Artificial
> [!NOTE]
> **Aviso de Desenvolvimento com IA:**
> Este projeto foi desenvolvido, refatorado e otimizado com o auxílio de **Inteligência Artificial (Google DeepMind / Antigravity / Gemini)** em colaboração com o autor, incluindo o design do fluxo do launcher, algoritmos de bioacústica, plasticidade ativa com Random Forest e empacotamento.

---

## 📥 Download das Versões Compiladas (.exe)

Você pode baixar os executáveis prontos para uso diretamente no Google Drive oficial do projeto:

🔗 **[Acessar Pasta de Downloads no Google Drive](https://drive.google.com/drive/folders/1CSjbYE-mql_Sg9qmV-argU05RjpwnmpT?usp=sharing)**

### 💡 Qual formato devo baixar? (Guia Descomplicado)

| Formato | Como funciona? | Para quem é recomendado? |
| :--- | :--- | :--- |
| **Versão Onefile (Arquivo Único)** | Um arquivo `.exe` individual e portátil. Pronto para rodar diretamente com dois cliques, sem precisar instalar ou extrair nada no seu computador. | Ideal para quem busca **praticidade e portabilidade**, podendo levar o programa direto em um pendrive. |
| **Versão Onedir (Pasta com Arquivos / .zip)** | O executável vem acompanhado de suas pastas e bibliotecas já pré-extraídas. Basta descompactar o `.zip` e abrir o executável dentro da pasta. | Recomendado para **abertura ultra rápida** e para **evitar falsos positivos** em alguns antivírus. |

---

## 📌 Regra de Versionamento (`vX.Y.Z`)

O projeto adota o padrão semântico de versionamento estructurado em três níveis:

- **Major ($X$):** Grandes saltos arquiteturais e reestruturações completas de escopo sob comando explícito.
- **Minor ($Y$):** Qualquer mudança funcional, nova complexidade algorítmica, inclusão de recursos ou modificação visual significativa na interface que **demande registro ou alteração na documentação técnica**. Obrigatoriamente incrementa $Y$ (ex: `v3.4.5` $\rightarrow$ `v3.5.0`).
- **Patch / Correções ($Z$):** Correções pontuais de bugs internos, pequenos ajustes cosméticos ou melhorias de estabilidade que **não alteram as diretrizes nem exigem atualização no relatório técnico**.

---

## 📚 Manuais e Documentações em PDF

Documentações completas e diagramadas estão disponíveis na pasta [`docs/`](docs/):

1. 📄 **[Manual Técnico e Científico](docs/Crinometro_Manual_Tecnico_Cientifico.pdf):** Destinado a pesquisadores, biólogos e ecólogos. Detalha a formulação matemática de filtros Butterworth, demodulação de Hilbert, arquitetura do classificador Random Forest (500 árvores) e descritores físicos.
2. 📘 **[Guia Prático e Descomplicado](docs/Crinometro_Guia_Pratico_Didatico.pdf):** Destinado a estudantes, leigos e entusiastas. Explicação didática passo a passo, guia visual das 10 cores e dicas práticas de gravação em campo.

---

## ✨ Funcionalidades Principais

- 🎧 **Carregamento & Gerenciamento de Áudios:** Suporte a arquivos `.wav` mono e estéreo com reprodução interativa, seleção individual por caixas de marcação e limpeza seletiva.
- ⚡ **Processamento em Lote:** Seleção múltipla com botão *"⚡ Analisar Selecionados"* e *"Selecionar tudo"* para cálculo bioacústico automático em massa.
- 🎨 **Paleta Canônica de 10 Cores:** Mapeamento de 2 a 10 pulsos (mais cor extra para escopos amplos) compartilhado de forma unívoca entre Onda, Histograma, Frequência e Espectrograma.
- 🌊 **Análise de Onda Acústica (DSP):**
  - Envoltória analítica contínua via Transformada de Hilbert.
  - Filtro digital Butterworth passa-faixa IIR de fase zero (`sosfiltfilt`).
  - Detecção adaptativa de picos, pulsos e agrupamento em chilreios.
- 🧠 **Machine Learning com Plasticidade Ativa (PulseLearner):**
  - Classificador *Random Forest* (500 árvores) treinado sobre 12 descritores físicos.
  - Aprendizado ativo contínuo: edições manuais na onda realimentam o modelo com o botão *"Aprender com as Correções"*.
  - Persistência e interoperabilidade de modelos via arquivos `.pkl`.
- 📊 **Histograma de Distribuição:** Contagem, média, moda e legenda individual por classe de pulso.
- 📈 **Frequência Dominante vs. Tempo:** Rastreamento espectral instante a instante com interpolação precisa.
- 🌈 **Espectrograma STFT Multirresolução:** Mapa tempo-frequência (dB) com engine adaptativa LOD.
- 🔗 **Sincronização Temporal (`🔗 Sincronizar (X)`):** Trava e sincroniza zoom e deslocamento entre os painéis com precisão de milissegundos.
- 📑 **Exportação de Relatórios:** Geração de arquivos estruturados em `.txt` para integração com R, Python, PAST e JASP.
- 🎭 **Launcher Interativo Vetorial:** Mascote animado com estados de repouso e despertar, partículas e frases dinâmicas sobre bioacústica.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Interface Gráfica:** PyQt5 / QtMultimedia
- **Processamento Numérico e Sinal:** NumPy, SciPy (Signal, Integrate, Special, IO)
- **Machine Learning:** Scikit-Learn (RandomForestClassifier)
- **Visualização de Dados:** Matplotlib
- **Geração de Documentos:** ReportLab, Pillow
- **Empacotamento:** PyInstaller

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
pip install PyQt5 numpy scipy scikit-learn matplotlib reportlab pillow pyinstaller
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

