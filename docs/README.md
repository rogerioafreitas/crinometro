# Central de Documentação do Crinômetro (v4.5.0)

Bem-vindo à pasta de documentação do **Crinômetro v4.5.0**, instrumento metrológico de alta precisão para bioacústica computacional, caracterização morfológica de estridulação e diagnose taxonômica de novas espécies de Orthoptera (Ensifera: Grylloidea).

---

## 📚 Documentos Oficiais em Destaque (v4.5.0)

### 1. Documentação Técnica, Teórica e Metodológica (PDF)
* **Arquivo:** [`Crinometro_Documentacao_Tecnica_Cientifica_v4.5.0.pdf`](./Crinometro_Documentacao_Tecnica_Cientifica_v4.5.0.pdf)
* **Páginas:** 30 páginas (Formato acadêmico com rigor biofísico, equações, tabelas e código Python da v4.5.0).
* **Escopo:** Fundamentação de sinal (DSP, Butterworth SOS fase zero, STFT, Welch), neurofisiologia tegminal (CPG, Hilbert, FWHM), agrupamento hierárquico em 5 camadas, aprendizado de máquina híbrido (`PulseLearner`, GMM, `HistGradientBoosting`, serialização `.skops`), computação gráfica Min-Max LoD e 60 FPS com Blitting.

### 2. Manual do Usuário e Guia de Operação Prática (PDF)
* **Arquivo:** [`Crinometro_Manual_do_Usuario_v4.5.0_Completo.pdf`](./Crinometro_Manual_do_Usuario_v4.5.0_Completo.pdf)
* **Páginas:** Manual prático completo com sumário navegável, 13 prints oficiais da interface anotados com caixas e tags numeradas, fluxos de trabalho passo a passo, diagnose de erros e glossários de interface.

### 3. Especificações em Markdown
* [`DOCUMENTACAO_TECNICA_CIENTIFICA_v4.5.0.md`](./DOCUMENTACAO_TECNICA_CIENTIFICA_v4.5.0.md) — Texto integral da documentação científica.
* [`MANUAL_DO_USUARIO_v4.5.0.md`](./MANUAL_DO_USUARIO_v4.5.0.md) — Guia prático de operação e UX para pesquisadores.
* [`STATE_CONTRACT_v4.5.0.md`](./STATE_CONTRACT_v4.5.0.md) — Contrato formal de arquitetura MVC desacoplada e estado reativo (`SessionContext`).
* [`CHANGELOG.md`](./CHANGELOG.md) — Histórico detalhado de lançamentos, correções e versões.
* [`AUTO_UPDATER.md`](./AUTO_UPDATER.md) — Especificação do módulo de verificação e atualização automática.

---

## 🗂️ Estrutura Organizacional de Pastas

```text
docs/
├── Crinometro_Documentacao_Tecnica_Cientifica_v4.5.0.pdf  # [PDF Oficial] Doc. Técnica Científica (30 págs)
├── Crinometro_Manual_do_Usuario_v4.5.0_Completo.pdf      # [PDF Oficial] Manual do Usuário Completo
├── DOCUMENTACAO_TECNICA_CIENTIFICA_v4.5.0.md             # [MD Oficial] Especificação Técnica
├── MANUAL_DO_USUARIO_v4.5.0.md                           # [MD Oficial] Manual de Operação
├── STATE_CONTRACT_v4.5.0.md                              # [MD Oficial] Contrato de Estado MVC
├── CHANGELOG.md                                          # Histórico de Versões
├── AUTO_UPDATER.md                                       # Arquitetura do Atualizador
├── README.md                                             # Este guia de navegação
│
├── generate_docs_tecnica_v450.py                         # Compilador Mestre do PDF Técnico
├── generate_manual_usuario_completo_pdf.py               # Compilador Mestre do Manual em PDF
│
├── sections/                                             # Módulos Python da Doc. Técnica (Cap. 1 a 6)
│   ├── common.py                                         # Canvas de 2 passadas, estilos e fontes TrueType
│   ├── cover_and_toc.py                                  # Capa acadêmica e Sumário Estruturado
│   ├── chapter1.py                                       # Cap. 1: Arquitetura, Concorrência e Pipeline
│   ├── chapter2.py                                       # Cap. 2: DSP e Engenharia Espectral
│   ├── chapter3.py                                       # Cap. 3: Morfologia Temporal e Sintaxe de Chilreios
│   ├── chapter4.py                                       # Cap. 4: Aprendizado de Máquina Híbrido e skops
│   ├── chapter5.py                                       # Cap. 5: Computação Gráfica, LoD e Interface
│   └── chapter6.py                                       # Cap. 6: Protocolos, Tabela Sintética e Índice
│
├── figures/                                              # Recursos Gráficos e Imagens Oficiais
│   ├── fig1_dashboard_m017.png ... fig5_*.png            # Gráficos científicos do espécime m017
│   ├── ui_print01_main_window.png ... ui_print13_*.png   # 13 Capturas oficiais da UI com anotações
│   ├── pdf_review/                                       # Renderizações PNG de auditoria do Manual
│   ├── pdf_review_v450/                                  # Renderizações PNG de auditoria do Doc Técnico
│   └── archive_tests/                                    # Arquivo de imagens de teste e rascunhos
│
├── Reports/                                              # Relatórios de Engenharia, QA e Auditorias
│   ├── auditorias/                                       # Auditorias formais de código (betas 39 a 43)
│   ├── roadmaps/                                         # Roadmaps de arquitetura v4.5.0
│   ├── fases/                                            # Relatórios das Fases 6, 7 e 8
│   └── baselines/                                        # Protocolos de validação, fumaça e testes
│
└── archive/                                              # Arquivo Histórico e Versões Anteriores
    ├── v432/                                             # Documentação e extrações da versão 4.3.2
    │   ├── Crinometro_Documentacao_Tecnica_Cientifica_v432.pdf
    │   ├── Crinometro_Guia_Pratico_Didatico.pdf
    │   ├── Crinometro_Manual_Tecnico_Cientifico.pdf
    │   ├── CHANGELOG.pdf
    │   └── v432_extracted/                               # Textos de referência extraídos da v4.3.2
    ├── drafts/                                           # Rascunhos intermediários arquivados
    └── legacy_scripts/                                   # Scripts antigos de geração de PDFs
```

---

## ⚙️ Como Compilar as Documentações em PDF

A partir da raiz do repositório, execute com o interpretador Python do projeto:

```powershell
# 1. Compilar a Documentação Técnica, Teórica e Metodológica (30 páginas)
python docs/generate_docs_tecnica_v450.py

# 2. Compilar o Manual do Usuário e Guia de Operação Prática
python docs/generate_manual_usuario_completo_pdf.py

# 3. (Opcional) Re-capturar todos os 13 prints da interface com caixas anotadas
python scripts/capture_ui_screenshots.py
```
