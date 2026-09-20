# 🦗 Crinômetro v4.4.1

> **Software Especializado em Bioacústica, Processamento Digital de Sinais (DSP) e Aprendizado Ativo em Grylloidea**

---

## 📥 Download do Aplicativo Instalável (.exe)

O instalador oficial com assistente de instalação e atualizador automático integrado está disponível para download:

🔗 **[Baixar Instalador Oficial no Google Drive](https://drive.google.com/drive/folders/1CSjbYE-mql_Sg9qmV-argU05RjpwnmpT?usp=sharing)**

- **Nome do Instalador:** Crinometro_setup__v4.4.1.exe
- **Tipo:** Instalador moderno (Inno Setup) com suporte a escolha de diretório de instalação, atalhos na Área de Trabalho e inicialização do aplicativo.
- **Atualização Automática:** Notifica diretamente no Launcher sobre novas versões e realiza o download e a instalação de forma integrada e silenciosa.

---

## 📌 Regra de Versionamento (vX.Y.Z)

O projeto adota o padrão semântico de versionamento estruturado em três níveis:

- **Major (X):** Grandes saltos arquiteturais e reestruturações completas de escopo sob comando explícito (ex:  4.0.x introduzindo a segregação acústica focal vs. coro distante).
- **Minor (Y):** Qualquer mudança funcional, nova complexidade algorítmica, inclusão de recursos ou modificação visual significativa na interface que **demande registro ou alteração na documentação técnica** (ex: v4.0.x → v4.1.0 → v4.2.0 → v4.3.0). Desenvolvido em branches separadas.
- **Patch / Correções (Z):** Correções pontuais de bugs internos, pequenos ajustes cosméticos ou melhorias de estabilidade que **não alteram as diretrizes nem exigem atualização no relatório técnico**. Alterações diretas na branch main.

---

## 📚 Manuais e Documentações em PDF

Documentações completas e diagramadas estão disponíveis na pasta [docs/](docs/) e na raiz:

1. 📄 **[Manual Técnico e Científico](docs/Crinometro_Manual_Tecnico_Cientifico.pdf):** Formulação matemática dos filtros Butterworth, demodulação de Hilbert, segregação focal via GMM e arquitetura do classificador supervisionado.
2. 📘 **[Guia Prático e Didático](docs/Crinometro_Guia_Pratico_Didatico.pdf):** Explicação didática passo a passo, guia visual das cores por contagem de pulsos e dicas práticas de gravação em campo.
3. 📋 **[Histórico Completo de Mudanças (CHANGELOG)](CHANGELOG.md)** | **[PDF](docs/CHANGELOG.pdf):** Registro exaustivo e cronológico de todas as atualizações desde a v3.0.0 até a versão atual.

---

## ✨ Funcionalidades em Destaque

- 📊 **Histograma Bivariado de Pulsos (twinx):** Visualização integrada com contagem de chilreios no eixo Y primário e curva de duração média em milissegundos (ms) no eixo Y secundário com legenda sincronizada.
- 🔊 **Densidade Espectral de Potência (PSD Welch):** Assinatura espectral média de 0 a 15 kHz calculada com 4096 amostras, anotação automática da Frequência Portadora ($f_p$) e delimitação até Nyquist.
- ⚡ **Modo DSP Nativo como Padrão e Reset de IA:** Inicialização segura e determinística com Inteligência Artificial desligada por padrão e botão de redefinição de fábrica do classificador.
- 📊 **Espectrograma Interativo com Presets:** Presets rápidos "Total" e "Focal", travas de pan/zoom limitadas à extensão temporal do áudio e alternância instantânea de unidade (Hz ⇋ kHz).
- 🔄 **Auto-Updater Robusto em PowerShell (v4.4.1):** Atualização transparente com script nativo PowerShell UTF-8-BOM, normalização de diretório desacentuado (`Crinometro`) e migração de configurações sem conflitos de concorrência.
- ⚡ **Navegação Ultra-Fluida e Cancelamento Seguro:** Redução de 50% de RAM em `float32`, redesenho assíncrono via `canvas.draw_idle()` e botão dinâmico "✕ Abortar" para interromper análises em tempo real.
- 🦗 **Agrupamento por Espécime e Frequência Portadora:** Síntese comparativa por espécime com frequência dominante intrínseca e diagnóstico rítmico de cadência com filtragem robusta de pausas no Relatório PDF.
- 🎧 **Cadeia Bioacústica Avançada (DSP):** Envoltória de Hilbert, filtro Butterworth passa-faixa IIR de fase zero e critério rigoroso de mínimo de 3 pulsos por chilreio ($min\_p \ge 3$).
- 🎨 **Paleta Canônica de Cores:** Identificação visual unificada de pulsos por chamado em todos os gráficos (Onda, Histograma e Espectrograma).
- 🧠 **Aprendizado Ativo (PulseLearner):** Mineração de regras rígidas (*Hard Negative Rule Induction*), filtro fisiológico *ICI Gate* e segregação focal vs. coro via Mistura de Gaussianas (GMM).
- 📑 **Exportação Científica Completa:** Relatórios diagramados em PDF (Completo e Simplificado) e tabelas estruturadas em TXT para exportação direta ao R, Python, PAST e JASP.

---

## 🚀 Executando pelo Código-Fonte

```bash
# 1. Clonar o repositório
git clone https://github.com/rogerioafreitas/crinometro.git
cd crinometro

# 2. Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependências
pip install PyQt6 numpy scipy scikit-learn matplotlib reportlab pillow pyinstaller

# 4. Iniciar o programa
python crinometro__laucher.py
```

---

## 📬 Contato e Suporte

- **Autor:** Rogério Freitas (@rogerioafreitas)
- **E-mail:** [rda.freitas.2002@gmail.com](mailto:rda.freitas.2002@gmail.com) *(Assunto: "Crinômetro")*
