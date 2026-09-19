# Roadmap de Implementação — Arquitetura e Exportação Científica (Crinômetro)

**Documento de Planejamento Arquitetural e Execução Passo a Passo**
**Versão Alvo:** v4.4.0 / v4.5.0 (Refatoração Estrutural e Ferramentas de Exportação)
**Autor:** Antigravity (Arquiteto de Software e DSP)

Este documento detalha o plano de execução exaustivo para o desacoplamento da `main_window.py` (God Class com mais de 4.000 linhas) e a implementação de novos fluxos de exportação científica de alto nível. O planejamento é estritamente baseado no levantamento arquitetural profundo realizado sobre o código-fonte atual.

---

## 1. Visão Geral da Arquitetura Alvo (Desacoplamento)

Para resolver o anti-pattern de *God Class* da `MainWindow`, migraremos de um design monolítico para um padrão baseado em **Módulos Controladores Específicos** injetados via composição. O estado global mutável será extraído para um padrão *Mediator* ou *State Store* (Contexto de Sessão), eliminando dependências circulares.

```mermaid
graph TD
    MW[ui/main_window.py\n(Apenas UI Layout e Injeção)] --> SS[core/session_context.py\n(Estado Compartilhado)]
    MW --> C1[ui/controllers/pipeline_orchestrator.py]
    MW --> C2[ui/controllers/plot_renderers.py]
    MW --> C3[ui/controllers/navigation_controller.py]
    MW --> C4[ui/controllers/editor_controller.py]
    
    C1 -. Lê/Grava .-> SS
    C2 -. Lê .-> SS
    C3 -. Lê/Grava .-> SS
    C4 -. Grava .-> SS
    
    C1 --> DSP[core/analyzer.py]
    C4 --> ML[core/learner.py]
```

---

## BLOCO 1: REFATORAÇÃO E DESACOPLAMENTO DA MAIN WINDOW

### 1.1. Extração do Estado Compartilhado (`core/session_context.py`)
A `MainWindow` atualmente armazena centenas de variáveis de estado que misturam lógica de negócio, dados DSP e metadados de UI. 
- **Ação:** Criar a classe `SessionContext` para encapsular:
  - `active_heavy_data`, `analysis_cache`, `loaded_files`
  - `peaks_detected`, `peaks_user_verified`, `corrections_by_file`
  - `algo_params`, `_adaptive_overrides`, `report_params`
  - `pulse_learner` (Instância do ML)
- **Desacoplamento:** Controladores receberão a instância de `SessionContext` no `__init__`. Alterações no estado dispararão sinais Qt (`pyqtSignal`) nativos do contexto (ex: `state_changed.emit("active_heavy_data")`), que a UI assinará para atualizar rótulos e painéis de forma reativa.

### 1.2. Módulo: `ui/controllers/pipeline_orchestrator.py`
Responsável pela execução assíncrona, controle do `GenericWorker` e atualização de limites do DSP.
- **Métodos a migrar da MainWindow:**
  - `force_reanalyze(self)`
  - `run_analysis(self, filename, params, render, validate_all)`
  - `_apply_analysis_results(self, ...)` 
  - `apply_realtime_freq_tolerance(self, new_tol, source_panel)`
  - `_execute_realtime_freq_tolerance(self)`
- **Estratégia:** O orquestrador não desenhará na tela. Após o `_apply_analysis_results` popular o `SessionContext`, o orquestrador emitirá o sinal `analysis_completed(filename)`. A `MainWindow` assinará esse sinal para chamar o `PlotRenderers.render_dashboard()`.

### 1.3. Módulo: `ui/controllers/plot_renderers.py`
Responsável exclusivamente por coordenar as *engines* de alta performance e sobrepor marcadores nos eixos do Matplotlib.
- **Métodos a migrar:**
  - `render_dashboard(self, filename)`
  - `_refresh_histogram(self)`
  - `_refresh_user_peak_markers(self)`
  - `apply_spectrogram_y_limits(self, ymin, ymax, unit)`
- **Estratégia:** Receberá referências fracas (`weakref`) ou diretas aos painéis (`panel_wave`, `panel_spec`, etc.) durante a inicialização. Utilizará os dados do `SessionContext` para atualizar a tela.

### 1.4. Módulo: `ui/controllers/navigation_controller.py`
Concentrará toda a complexidade de eventos de mouse, manipulação de viewport (Pan/Zoom) e otimização por *blitting*.
- **Métodos a migrar:**
  - `on_press(self, event)`, `on_release(self, event)`, `on_motion(self, event)`, `zoom_graph(self, event)`
  - `_sync_render(self, ...)`, `_clamp_bounds(self, ...)`
  - `_refresh_synced_views(self)`
  - `capture_backgrounds(self)` e gestão de `self.backgrounds`, `self.cursor_lines`, `self.bg_cache_valid`.
- **Estratégia:** O controlador se registrará aos eventos do canvas via `mpl_connect`. O Pan e Zoom atualizarão limites e acionarão o `_sync_render` internamente, sem tocar no escopo geral da UI.

### 1.5. Módulo: `ui/controllers/editor_controller.py`
Controlará a lógica de edição bidimensional (Tempo/Amplitude e Tempo/Frequência) e a submissão de correções ao Machine Learning.
- **Métodos a migrar:**
  - `_toggle_peak_marker(self, time_sec, panel, event, f_click, amp_click)`
  - `_find_nearest_user_peak(self, time_sec, tolerance)`
  - `learn_from_corrections(self)`
  - `_undo_pulse_edit(self)`, `_save_corrections_state(self)`
- **Estratégia:** Lógica isolada que consome o `SessionContext`, executa `CricketAnalyzer.regroup_chirps()`, e emite sinais para o `PlotRenderers` redesenhar marcadores e histograma.

### 1.6. Limpeza Residual da `MainWindow`
- A `main_window.py` passará de 4075 linhas para cerca de 800-1000 linhas.
- Conterá estritamente: `setup_ui`, `setup_menu`, `apply_modern_styles`, instigação dos 4 controladores, roteamento de sinais base (ex: clique em botão aciona controlador), barra de transporte (`toggle_playback`, `update_playback_cursor`) e layouts estruturais (`QSplitter`).

---

## BLOCO 2: DIÁLOGO DE EXPORTAÇÃO GRÁFICA PARA PUBLICAÇÃO CIENTÍFICA

O fluxo atual exporta o PDF estruturado, mas faltam exportações vetoriais/raster em alta resolução diretas dos gráficos exibidos.

### 2.1. Novo Componente: `ui/dialogs/export_graph_dialog.py`
- **Interface Gráfica (`QDialog` modal):**
  - **Matriz de Seleção (Checkboxes):** Permitirá escolher quais painéis exportar (Oscilograma, Histograma, PSD, Espectrograma focal).
  - **Camada de Anotações:** Toggle para incluir/excluir eixos, grade, rótulos e marcadores de pulso do usuário.
  - **Formato:** Seletor (PDF multi-página paisagem vetorial vs. Arquivos PNG isolados).
  - **DPI (Para PNG):** 150 (Rascunho), 300 (Publicação), 600 (Alta Qualidade).
- **Pipeline Off-Screen (Renderização Segura):**
  - **Problema a evitar:** Congelamento da UI ou contaminação pelo tamanho atual da janela (viewport dependente de tela).
  - **Solução:** O controlador instanciará objetos `Figure` do Matplotlib independentes usando o backend não-interativo `Agg` (`matplotlib.use('Agg')` num escopo isolado).
  - Receberá o dicionário puro de dados do `SessionContext.active_heavy_data` e desenhará os gráficos limpos nas dimensões físicas corretas (ex: 7x5 polegadas), iterando e salvando via `fig.savefig(dpi=...)`.

---

## BLOCO 3: DIÁLOGO UNIFICADO DE RELATÓRIO PDF

O relatório PDF atual carece de validação de metadados antes da geração e opções para ligar/desligar seções de análise, além do problema de contraste visual identificado (cores excessivamente claras para linhas e grades).

### 3.1. Novo Componente: `ui/dialogs/export_report_dialog.py`
- **Interface Gráfica (`QDialog` modal):**
  - **Aba Metadados:** Campos validados para Espécie (Input texto), Código do Espécime, Localidade, Temperatura (°C), Equipamento e Nome do Gravador. (Avisa/Marca em vermelho se campos essenciais estiverem vazios antes da emissão).
  - **Aba Seções Modulares (Checkboxes):** 
    - [x] Resumo Executivo e Tabela de Arquivos
    - [x] Métricas Temporais Consolidadas
    - [x] Diagnóstico de Cadência Rítmica
    - [x] Estimativa de Temperatura (Dolbear)
    - [x] Gráficos de Espectrograma e PSD (Nova integração com o Bloco 2)
    - [ ] Listagem Exaustiva de Chilreios e Pulsos (Tabela longa)
  - Botão "Gerar Relatório em Segundo Plano".

### 3.2. Refatoração em `utils/report_generator.py`
- **Correção de UI Crítica:** Ajustar a cor `#E2E8F0` em todos os `INNERGRID` dos `TableStyle` (linhas 301, 397, 475, 514, 572). Substituir por `#CBD5E1` (Bordas internas) e `#94A3B8` (Bordas externas) para legibilidade em impressoras P&B e visores de alto brilho.
- **Adaptação Modular:** A função `generate_pdf_report` passará a aceitar um objeto `ReportConfig` que conterá os metadados ricos (passados do Dialog) e uma lista booleana ativando/desativando seções `section_flags = {'cadence': True, 'graphs': True, 'chirp_list': False, ...}`.
- **Processamento Assíncrono:** A compilação PDF (`doc.build()`) pode levar de 5 a 15 segundos para grandes lotes (centenas de chilreios longos). Será movida para `GenericWorker` com captura de exceções `_on_error` reportando à janela principal sem travar a thread de GUI.

---

## MATRIZ DE RISCOS DA MIGRAÇÃO

| Componente | Risco | Mitigação |
| :--- | :--- | :--- |
| **Mouse Hover (`on_motion`)** | Quebra de responsividade (Lag). O throttle crítico depende de cache rápido. | O `navigation_controller.py` deve assumir estritamente o `pulse_hover_data` e cálculos de proximidade em pixels. |
| **Sincronização de Viewport** | Dependência circular (Controller de Navegação precisa do Controller de Renderização para o `_sync_render`). | Uso rigoroso de injeção de dependências ou emissão de sinal explícito `viewport_changed(xmin, xmax)` capturado pelo Orchestrator. |
| **Background Blitting** | Corrupção gráfica / traços fantasma deixados na tela durante pans rápidos. | Centralizar as rotinas de `capture_backgrounds` num gerenciador de renderização atômico associado ao `navigation_controller`. |
| **Memory Leaks no Matplotlib** | Criação de gráficos off-screen no Bloco 2 estourando a memória RAM. | Assegurar chamadas mandatórias a `plt.close(fig)` em blocos `finally` no exportador `Agg`. |

---
**Status do Roadmap:** Elaborado com base no rastreamento de 4.075 linhas de código GUI e 590 linhas de geração de relatórios (Set/2026). Pronto para aprovação do desenvolvedor líder.
