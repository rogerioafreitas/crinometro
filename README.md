# 🦗 Crinômetro v4.2.2

> **Software Especializado em Bioacústica, Processamento Digital de Sinais (DSP) e Aprendizado Ativo em Grylloidea**

---

## 📥 Download do Aplicativo Instalável (.exe)

O instalador oficial com assistente de instalação e atualizador automático integrado está disponível para download:

🔗 **[Baixar Instalador Oficial no Google Drive](https://drive.google.com/drive/folders/1CSjbYE-mql_Sg9qmV-argU05RjpwnmpT?usp=sharing)**

- **Nome do Instalador:** Crinometro_setup__v4.2.2.exe
- **Tipo:** Instalador moderno (Inno Setup) com suporte a atalhos na Área de Trabalho e inicialização do aplicativo.
- **Atualização Automática:** Notifica diretamente no Launcher sobre novas versões e realiza o download e a instalação de forma integrada e silenciosa.

---

## 📌 Regra de Versionamento (vX.Y.Z)

O projeto adota o padrão semântico de versionamento estruturado em três níveis:

- **Major (X):** Grandes saltos arquiteturais e reestruturações completas de escopo sob comando explícito (ex:  4.0.x introduzindo a segregação acústica focal vs. coro distante).
- **Minor (Y):** Qualquer mudança funcional, nova complexidade algorítmica, inclusão de recursos ou modificação visual significativa na interface que **demande registro ou alteração na documentação técnica** (ex: v4.0.x → v4.1.0 → v4.2.0). Desenvolvido em branches separadas.
- **Patch / Correções (Z):** Correções pontuais de bugs internos, pequenos ajustes cosméticos ou melhorias de estabilidade que **não alteram as diretrizes nem exigem atualização no relatório técnico**. Alterações diretas na branch main.

---

## 📚 Manuais e Documentações em PDF

Documentações completas e diagramadas estão disponíveis na pasta [docs/](docs/):

1. 📄 **[Manual Técnico e Científico](docs/Crinometro_Manual_Tecnico_Cientifico.pdf):** Formulação matemática dos filtros Butterworth, demodulação de Hilbert, segregação focal via GMM e arquitetura do classificador supervisionado.
2. 📘 **[Guia Prático e Didático](docs/Crinometro_Guia_Pratico_Didatico.pdf):** Explicação didática passo a passo, guia visual das cores por contagem de pulsos e dicas práticas de gravação em campo.

---

## ✨ Funcionalidades em Destaque

- 🔄 **Auto-Updater Integrado no Launcher:** Checagem assíncrona no GitHub Releases, download direto no Launcher com barra de progresso em tempo real e substituição automática via Inno Setup.
- 🎧 **Análise Bioacústica Avançada (DSP):** Envoltória de Hilbert, filtro Butterworth passa-faixa IIR de fase zero e identificação automática de picos, pulsos e chilreios.
- 🎨 **Paleta Canônica de Cores:** Identificação visual unificada de pulsos por chilreio em todos os gráficos (Onda, Histograma, Frequência e Espectrograma).
- 🪟 **Interface Modular e Fluida:** Mini painéis arredondados com suporte a arrastar e soltar (Drag & Drop), previsão de encaixe e troca rápida com o gráfico principal.
- 🧠 **Aprendizado Ativo (PulseLearner):** Mineração de regras rígidas a partir de correções manuais do usuário (*Hard Negative Rule Induction*) e filtro temporal fisiológico (*ICI Gate*).
- 📑 **Exportação Científica:** Relatório Completo detalhado e Relatório Simplificado multiáudio em PDF (ReportLab), além de tabelas em TXT para exportação direta ao R/Python.

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
