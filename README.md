# 🦗 Crinômetro 3.0

> **Software para Bioacústica e Análise de Pulsos de Grilos e Insetos Estriduladores**

---

## 🤖 Declaração de Assistência por Inteligência Artificial
> [!NOTE]
> **Aviso de Desenvolvimento com IA:**
> Este projeto foi desenvolvido, refatorado e otimizado com o auxílio de **Inteligência Artificial (Google DeepMind / Antigravity / Gemini)** em colaboração com o autor, incluindo o design do fluxo do launcher, algoritmos de bioacústica e empacotamento.

---

## 📋 Sobre o Projeto

O **Crinômetro 3.0** é uma aplicação científica interativa desenvolvida em Python e PyQt6 com foco em bioacústica. A ferramenta permite carregar arquivos de áudio (.wav), processar sinais sonoros, detectar e quantificar pulsos/estridulações de grilos, traçar espectrogramas, analisar frequências dominantes e gerar relatórios acadêmicos completos.

---

## ✨ Funcionalidades Principais

- 🎧 **Carregamento e Gerenciamento de Áudios:** Suporte a arquivos .wav mono e estéreo com visualização rápida, caixas de seleção independentes e lixeira para remoção instantânea.
- ⚡ **Análise em Lote:** Processamento bioacústico automático de múltiplos arquivos selecionados com feedback em tempo real.
- 🔍 **Hover Interativo:** Visualização instantânea de metadados dos chilreios e contagem de pulsos ao passar o mouse sobre os marcadores dos gráficos.
- 🌊 **Análise de Onda Acústica:**
  - Envoltória do sinal via Transformada de Hilbert.
  - Filtragem passa-faixa digital (Butterworth).
  - Detecção automática de picos, pulsos e taxas de estridulação com aprendizado adaptativo.
- 📊 **Histograma de Pulsos:** Distribuição temporal e contagem precisa de pulsos por chilreio.
- 📈 **Frequência Dominante vs. Tempo:** Identificação da evolução espectral ao longo da gravação.
- 🌈 **Espectrograma:** Transformada de Fourier em tempo curto (STFT) com mapa de calor configurável.
- 🔗 **Sincronização de Eixos:** Zoom e navegação síncrona entre gráficos de sinal e espectrograma.
- 📑 **Exportação de Relatórios Seletivos:** Geração automática de relatórios em .txt compilando métricas estatísticas dos arquivos selecionados.
- 🌐 **Internacionalização:** Interface multilíngue com suporte nativo a Português e Inglês.
- 🎬 **Launcher Integrado:** Abertura animada com reprodução de vídeos (loading.mp4 e loaded.mp4), transição contínua sem tela preta e carregamento em segundo plano.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **GUI:** PyQt6, PyQt6-QtMultimedia
- **Processamento Numérico e Sinal:** NumPy, SciPy (Signal, IO)
- **Visualização de Dados:** Matplotlib
- **Empacotamento:** PyInstaller

---

## 🚀 Como Executar

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
pip install PyQt6 PyQt6-QtMultimedia numpy scipy matplotlib pyinstaller
```

### 4. Executar a aplicação
Para abrir com a tela de carregamento animada:
```bash
python crinometro_laucher.py
```

Ou para abrir diretamente a janela principal:
```bash
python crinometro.py
```

---

## 📦 Como Compilar o Executável (.exe)

Para gerar o executável único com ícone personalizado e recursos embutidos:

```bash
pyinstaller --clean --noconfirm crinometro.spec
```

O arquivo compilado estará disponível na pasta dist/crinometro.exe.

---

## 👤 Autor
- **rogerioafreitas**

