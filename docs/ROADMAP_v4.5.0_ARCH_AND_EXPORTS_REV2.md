# Roadmap de Implementação — Arquitetura e Exportação Científica (Crinômetro)

**Documento de Planejamento Arquitetural e Execução Passo a Passo**  
**Versão Alvo:** v4.5.0  
**Documento revisado:** Revisão 2  
**Base:** `ui/main_window.py` atual + roadmap arquitetural anterior + componentes existentes do projeto  
**Objetivo:** refatorar a janela principal sem regressão funcional e ampliar a exportação científica de forma modular.

---

## 0. Princípios de Execução

Este roadmap não trata a refatoração como uma simples divisão de um arquivo de 4.000+ linhas. A meta é **mudar a propriedade das responsabilidades sem mudar o comportamento observado do aplicativo**, salvo quando uma mudança funcional estiver explicitamente prevista neste documento.

A `MainWindow` atual concentra estado analítico, cache, dados pesados, parâmetros, ML, reprodução de áudio, painéis, interação com Matplotlib, edição de pulsos e menus. Por isso, a migração deverá ser feita de forma incremental, com um proprietário único para cada estado e com validação após cada etapa. A arquitetura atual já possui módulos especializados em DSP, ML, engines gráficas e worker assíncrono; a refatoração deve preservar essas fronteiras e retirar da `MainWindow` apenas o que pertence às responsabilidades de coordenação e apresentação.

### Regras obrigatórias da migração

1. **Uma fonte de verdade por estado.** Durante a etapa de migração, uma variável pode permanecer temporariamente em `MainWindow`, mas não poderá existir uma segunda cópia autoritativa no `SessionContext`.
2. **Nenhuma mudança silenciosa de comportamento.** Thresholds, parâmetros DSP, regras de agrupamento, sincronização de eixos, edição de pulsos, fluxo de áudio e formatos de relatório devem permanecer semanticamente equivalentes até que uma alteração seja especificada como funcional.
3. **Sinais substituem acoplamento direto entre controladores.** Um controlador não deve manipular métodos internos de outro controlador como caminho normal de comunicação.
4. **UI não executa trabalho pesado.** DSP, treinamento, compilação de relatórios e renderizações off-screen deverão continuar em workers ou em rotinas apropriadas fora do ciclo de pintura da GUI.
5. **Cada fase precisa ser reversível.** O código deve permanecer executável depois de cada migração intermediária.
6. **Documentação acompanha a implementação.** Diagramas e documentação técnica só passam a declarar um componente como implementado depois que o código-fonte correspondente existir e estiver integrado.

---

# FASE 0 — BASELINE, TESTES DE CARACTERIZAÇÃO E CONTRATOS

## 0.1. Congelamento comportamental

Antes de remover métodos da `MainWindow`, registrar o comportamento atual de:

- carregamento, seleção e troca de arquivos;
- análise normal, reanálise e análise em lote;
- cancelamento cooperativo;
- cache de resultados;
- sincronização do eixo X;
- pan, zoom e hover;
- troca do gráfico principal e reorganização dos painéis;
- edição, desfazer e reaplicação de pulsos;
- aprendizado a partir das correções;
- exportação TXT/PDF;
- reprodução, timeline, volume e velocidade;
- tema claro/escuro;
- menus, configurações e atualização.

O objetivo desta fase é produzir uma referência objetiva para detectar regressões, e não alterar o comportamento do programa.

## 0.2. Testes de caracterização

Criar testes mínimos para os fluxos críticos antes da extração dos controladores. A cobertura inicial deve priorizar:

| Área | Teste mínimo |
| :--- | :--- |
| Pipeline | análise de um WAV conhecido produz estrutura esperada |
| Cache | reabrir/reselecionar arquivo reutiliza resultado quando aplicável |
| Cancelamento | análise interrompida encerra worker sem deixar estado inconsistente |
| Navegação | pan/zoom altera somente viewport esperado |
| Sincronização | alteração do eixo X propaga aos painéis previstos |
| Edição | adicionar/remover/restaurar pulso atualiza marcadores e agrupamento |
| ML | correções podem alimentar o learner sem quebrar o estado da sessão |
| Exportação | TXT/PDF continuam produzindo arquivos válidos |
| Áudio | play/pause, posição, duração e velocidade permanecem funcionais |

## 0.3. Contratos de estado

Documentar, antes da criação do `SessionContext`, quais atributos são:

- **estado de domínio/analítico**;
- **estado de seleção/navegação**;
- **estado de edição/ML**;
- **estado de relatório/exportação**;
- **estado puramente visual da UI**;
- **estado transitório de infraestrutura**.

Este inventário será a referência para decidir o que sai da `MainWindow` e para impedir duplicação de estado.

---

# FASE 1 — `SessionContext`: ESTADO COMPARTILHADO COM PROPRIETÁRIO ÚNICO

## 1.1. Criação de `core/session_context.py`

Criar o `SessionContext` como contêiner explícito do estado compartilhado entre controladores. A primeira versão deve encapsular:

- `active_heavy_data`;
- `analysis_cache`;
- `loaded_files`;
- `peaks_detected`;
- `peaks_user_verified`;
- `corrections_by_file`;
- `algo_params`;
- `_adaptive_overrides`;
- `report_params`;
- referência ao `pulse_learner`.

O contexto poderá ser organizado internamente por blocos lógicos (`analysis`, `editing`, `ml`, `report`) sem obrigar a criação imediata de várias classes adicionais.

## 1.2. Sinais do contexto

Utilizar sinais Qt para notificar mudanças relevantes, por exemplo:

```python
state_changed.emit("active_heavy_data")
state_changed.emit("selection")
state_changed.emit("editing")
state_changed.emit("report")
```

Os sinais devem comunicar fatos sobre o estado, não impor a ordem interna de execução de outros controladores.

## 1.3. Regra de propriedade

Depois de migrado um atributo, a `MainWindow` deixa de ser sua fonte autoritativa. Referências temporárias de compatibilidade podem existir durante a transição, mas não devem ser atualizadas por dois lugares diferentes.

**Dívida arquitetural / Nota de transição:** Atualmente, a atribuição completa de estado (`self.active_heavy_data = novo_dict`) dispara `state_changed`, mas a **mutação interna** de dicionários e listas (ex: `self.analysis_cache[filename] = ...`) **não** dispara notificação. Esta é uma pendência aceita na FASE 1 e será resolvida durante a implementação dos controladores (FASE 2 a 5), não devendo ser usada como mecanismo definitivo de notificação quando os controladores passarem a depender do `SessionContext`.

---

# FASE 2 — `ui/controllers/pipeline_orchestrator.py`

## 2.1. Responsabilidade

Concentrar a execução assíncrona da análise, o ciclo de vida do `GenericWorker`, cancelamento cooperativo, reanálise e atualização de parâmetros derivados do pipeline.

## 2.2. Métodos-alvo

Migrar progressivamente:

- `force_reanalyze(self)`;
- `run_analysis(self, filename, params, render, validate_all)`;
- `_apply_analysis_results(self, ...)`;
- `apply_realtime_freq_tolerance(self, new_tol, source_panel)`;
- `_execute_realtime_freq_tolerance(self)`.

## 2.3. Contrato

O orquestrador **não desenha diretamente os painéis**. Ao concluir uma análise, atualiza o `SessionContext` e emite sinais como:

```text
analysis_started(filename)
analysis_progress(...)
analysis_completed(filename)
analysis_failed(error)
analysis_cancelled(filename)
```

O renderizador decide como refletir `analysis_completed` na interface.

## 2.4. Sinais formais e propriedade do worker no processamento em lote

O `PipelineOrchestrator` é o proprietário exclusivo dos workers assíncronos (`GenericWorker`). Nenhum sinal de worker de baixo nível (`finished_signal`, `result_ready_signal`) é exposto diretamente à `MainWindow`. O orquestrador gerencia internamente o ciclo de vida do worker e expõe sinais semânticos de alto nível:

```text
batch_started(total_files)
batch_item_completed(filename)
batch_progress(current, total)
batch_completed(success_count, errors)
batch_failed(error_message)
batch_cancelled()
```

A interface conecta-se exclusivamente a esses sinais, eliminando condições de corrida de conexão e garantindo autoridade única de renderização.

**Dívida arquitetural / Nota de transição (run_analysis síncrono):**  
A reanálise (`force_reanalyze`) e o lote (`run_batch_analysis`) executam estritamente em segundo plano via worker. No entanto, o método utilitário `run_analysis()` permanece temporariamente síncrono para atender chamadas diretas preexistentes na GUI (como resets de parâmetros e preparação de relatórios antes de sua modularização nas Fases 8 e 9). Essa pendência de transição é registrada e será convertida em rotinas assíncronas dedicadas quando os consumidores correspondentes forem refatorados.

---

# FASE 3 — `ui/controllers/plot_renderers.py`

> [!NOTE]
> **Status da FASE 3: CONCLUÍDA E VALIDADA.**  
> O controller `ui/controllers/plot_renderers.py` foi plenamente integrado à `MainWindow` (`self.plot_renderers`). Os métodos gráficos foram migrados mantendo compatibilidade e fidelidade comportamental.
> 
> **Decisões arquiteturais e registro de auditoria:**
> 1. **Eliminação de Dual Ownership (Solução A):** A `MainWindow` expõe `@property` e setters para `line_engine`, `spectro_engine`, `freq_engine`, `wave_lines` e `_wave_user_markers`, delegando diretamente ao `self.plot_renderers`. Não há cópia paralela nem dualidade de estado gráfico fora do controller.
> 2. **Sincronização de FP (Frequência Portadora):** Sincronização explícita do valor modal da portadora e da tolerância nos badges `lbl_carrier_info` dos painéis de espectrograma e frequência via `set_carrier_info`, corrigindo a exibição indevida de "FP: —".
> 3. **Extensão controlada de escopo:** O método `update_wave_visibility` foi migrado para `PlotRenderers`, consolidando o controle de visibilidade das camadas da forma de onda junto ao subsistema de renderização.
> 4. **Dívida explícita transitória:** Métodos de hover e blitting (`win.capture_backgrounds`, `win._update_pulse_hover_data`, `win.cursor_lines`, etc.) são chamados transitoriamente via `weakref` e serão formalmente isolados na FASE 4 (`NavigationController`).
> 5. **Testes dedicados:** Adicionados `test_13_plot_renderers_integration_and_engine_aliasing` e `test_14_plot_renderers_semantic_api` na suíte de caracterização.

## 3.1. Responsabilidade

Coordenar as engines gráficas existentes e concentrar a renderização dos quatro painéis sem assumir a lógica de navegação do mouse.

## 3.2. Métodos-alvo

Migrados:

- `render_dashboard(self, filename)` (e `render_file(filename)`);
- `_refresh_histogram(self)` (e `refresh_histogram()`);
- `_refresh_user_peak_markers(self)` (e `refresh_markers()`);
- `apply_spectrogram_y_limits(self, ymin, ymax, unit)`;
- `update_wave_visibility(self, show_raw, show_env, show_lod, show_peaks)`.

## 3.3. Contrato

O `PlotRenderers` lê o `SessionContext` e recebe referências controladas aos `PlotPanel`s via `weakref`. Expõe operações semânticas:

```text
render_file(filename)
refresh_histogram()
refresh_markers()
refresh_all()
update_wave_visibility(show_raw, show_env, show_lod, show_peaks)
apply_spectrogram_y_limits(ymin, ymax, unit)
```

A navegação interativa na FASE 4 consumirá os engines através do controller sem dualidade.

---

# FASE 4 — `ui/controllers/navigation_controller.py`

## 4.1. Responsabilidade

Isolar eventos de mouse, viewport, pan, zoom, sincronização horizontal, hover e manutenção do cache necessário ao blitting.

## 4.2. Métodos-alvo

Migrar progressivamente:

- `on_press(self, event)`;
- `on_release(self, event)`;
- `on_motion(self, event)`;
- `zoom_graph(self, event)`;
- `_sync_render(self, ...)`;
- `_clamp_bounds(self, ...)`;
- `_refresh_synced_views(self)`;
- `capture_backgrounds(self)`;
- gestão de `backgrounds`, `cursor_lines` e `bg_cache_valid`.

## 4.3. Regra de comunicação

O controlador emite algo equivalente a:

```text
viewport_changed(xmin, xmax)
hover_changed(payload)
pan_started()
pan_finished()
```

Não deve chamar métodos internos do `PlotRenderers` como mecanismo obrigatório de coordenação.

## 4.4. Hover

Preservar o comportamento atual de busca local e throttle. Qualquer otimização adicional deverá ser medida antes de ser descrita como melhoria de complexidade ou desempenho.

---

# FASE 5 — `ui/controllers/editor_controller.py`

## 5.1. Responsabilidade

Concentrar a edição de pulsos, histórico de alterações e integração das correções com o `PulseLearner`.

## 5.2. Métodos-alvo

Migrar progressivamente:

- `_toggle_peak_marker(self, time_sec, panel, event, f_click, amp_click)`;
- `_find_nearest_user_peak(self, time_sec, tolerance)`;
- `learn_from_corrections(self)`;
- `_undo_pulse_edit(self)`;
- `_save_corrections_state(self)`.

## 5.3. Contrato

O `EditorController` atualiza o estado de edição e emite sinais sem redesenhar diretamente mais do que o estritamente necessário. A atualização visual deve seguir pelo `PlotRenderers`.

A operação de agrupamento (`CricketAnalyzer.regroup_chirps()`) continua pertencendo ao motor analítico; o controller apenas coordena sua utilização.

---

# FASE 6 — RESPONSABILIDADES QUE PERMANECEM NA `MainWindow`

A `MainWindow` não deverá virar outro ponto de concentração de lógica apenas para compensar a extração dos quatro controladores.

## 6.1. Permanecem na `MainWindow`

- composição e criação dos widgets;
- `setup_ui`;
- `setup_menu` e roteamento simples das ações;
- aplicação de tema e ciclo de vida visual;
- criação/injeção dos controladores;
- conexão dos sinais de alto nível;
- layouts, `QSplitter` e organização dos painéis;
- barra de transporte enquanto sua lógica continuar estritamente ligada à janela e ao `QMediaPlayer`.

## 6.2. Áudio: preparação para futura extração

A reprodução atualmente envolve `QMediaPlayer`, `QAudioOutput`, timer de 10 ms, timeline, volume e velocidade. Essa responsabilidade **não será extraída na primeira rodada** para evitar ampliar desnecessariamente o escopo da refatoração.

Entretanto, a interface deve ser organizada de forma que uma futura extração para `AudioController` seja possível sem reescrever a camada visual.

---

# FASE 7 — Limpeza Definitiva da `MainWindow`

Somente depois que os quatro controladores estiverem operacionais:

1. remover métodos já migrados;
2. remover estado duplicado;
3. remover aliases temporários;
4. remover dependências que ficaram obsoletas;
5. revisar imports;
6. verificar sinais/conexões duplicados;
7. medir novamente o tamanho e a distribuição de responsabilidades.

### Critério de sucesso

Não usar apenas "800–1000 linhas" como métrica. O critério principal é que a `MainWindow` não contenha lógica de domínio que pertença aos controllers, às engines ou aos módulos `core`.

A redução de linhas será um **indicador secundário**, não uma meta funcional.

---

# FASE 8 — EXPORTAÇÃO GRÁFICA PARA PUBLICAÇÃO CIENTÍFICA

Esta fase começa somente após a estabilização da arquitetura de renderização.

## 8.1. `ui/dialogs/export_graph_dialog.py`

### Interface

- seleção dos painéis:
  - Oscilograma;
  - Histograma;
  - PSD;
  - Espectrograma focal;
- opção de incluir/excluir:
  - eixos;
  - grade;
  - rótulos;
  - marcadores do usuário;
- formato:
  - PDF vetorial multipágina;
  - PNG individual;
- DPI para PNG:
  - 150;
  - 300;
  - 600.

## 8.2. Pipeline off-screen

A exportação não deve depender da geometria atual da janela.

O exportador deve criar `Figure`s independentes, utilizar backend não interativo apropriado e sempre liberar os objetos gráficos após a gravação.

O pipeline deverá ter um ciclo de vida equivalente a:

```text
SessionContext
    ↓
ExportConfig
    ↓
FigureFactory / Renderer de exportação
    ↓
fig.savefig(...)
    ↓
close/finalização garantida
```

A implementação deve evitar modificar os `FigureCanvas` visíveis do usuário durante a exportação.

---

# FASE 9 — EXPORTAÇÃO UNIFICADA DE RELATÓRIO PDF

## 9.1. `ui/dialogs/export_report_dialog.py`

O menu de exportação será reorganizado somente depois que o novo fluxo puder produzir os mesmos resultados funcionais dos formatos existentes.

### Metadados

Campos planejados:

- espécie;
- código do espécime;
- localidade;
- temperatura;
- equipamento;
- nome do gravador.

### Seções modulares

- [x] Resumo Executivo e Tabela de Arquivos
- [x] Métricas Temporais Consolidadas
- [x] Diagnóstico de Cadência Rítmica
- [x] Estimativa de Temperatura (Dolbear)
- [x] Gráficos selecionados
- [ ] Listagem exaustiva de chilreios e pulsos

Esses padrões são defaults de interface e não devem substituir escolhas explícitas do usuário quando o relatório permitir configuração.

## 9.2. `utils/report_generator.py`

A função de geração deverá aceitar um objeto de configuração estruturado, por exemplo:

```python
ReportConfig(
    metadata=...,
    section_flags=...,
    graph_config=...,
)
```

A construção do PDF deverá poder rodar em `GenericWorker` para evitar bloquear a GUI.

### Compatibilidade

Antes de remover as ações legadas de relatório completo/resumido, validar que o novo diálogo cobre suas funções. Durante a transição, manter um caminho de compatibilidade até os testes confirmarem equivalência.

---

# FASE 10 — ARQUITETURA DE EXPORTAÇÃO E RESPONSABILIDADE DOS MENUS

A `MainWindow` ficará responsável apenas pelo **roteamento** das ações de menu.

Exemplo:

```text
Menu Exportar
   ├── Exportar dados TXT      → fluxo TXT existente
   ├── Relatório Científico    → ExportReportDialog
   └── Exportar Gráficos       → ExportGraphDialog
```

A lógica de montagem do relatório, desenho off-screen e preparação dos artefatos não deve permanecer na `MainWindow`.

---

# FASE 11 — SEGURANÇA E PERSISTÊNCIA DO MODELO

A persistência atual do classificador utiliza `pickle`. A migração para formatos interoperáveis/safe-by-default pode ser tratada como uma frente separada da refatoração de UI.

### Plano

1. documentar claramente a confiança exigida para `modelo_treinado.pkl`;
2. avaliar formato de persistência adequado ao classificador realmente utilizado;
3. somente então definir se ONNX, pesos numéricos ou outro formato atende aos requisitos;
4. criar teste de carga/compatibilidade antes de remover o `pickle`.

Não assumir antecipadamente que um formato alternativo é intercambiável com o modelo atual sem validar treinamento, inferência e preservação das features.

---

# MATRIZ DE DEPENDÊNCIAS ENTRE AS FASES

| Fase | Depende de | Entrega principal |
| :--- | :--- | :--- |
| 0 | — | Baseline + testes de caracterização |
| 1 | 0 | `SessionContext` + contrato de estado |
| 2 | 1 | Pipeline desacoplado |
| 3 | 1 | Renderização desacoplada |
| 4 | 1 + 3 | Navegação/viewport desacoplados |
| 5 | 1 + 3 | Edição/ML desacoplados |
| 6 | 2–5 | `MainWindow` reduzida a composição/UI |
| 7 | 6 | Limpeza e remoção de duplicidades |
| 8 | 3 + 7 | Exportação gráfica off-screen |
| 9 | 8 + 7 | Relatório PDF modular |
| 10 | 8 + 9 | Menus de exportação unificados |
| 11 | independente | Persistência de modelo avaliada com segurança |

---

# MATRIZ DE RISCOS DA MIGRAÇÃO

| Componente | Risco | Mitigação |
| :--- | :--- | :--- |
| **Regressão funcional** | A refatoração pode mudar comportamento sem erro sintático. | Testes de caracterização antes de cada extração e comparação pós-migração. |
| **Estado duplicado** | `MainWindow` e `SessionContext` podem divergir. | Proprietário único por atributo e remoção de aliases assim que a migração estabilizar. |
| **Sinais Qt duplicados** | Dois caminhos podem disparar o mesmo refresh ou análise. | Inventário de conexões + testes de emissão única. |
| **Dependência circular entre controllers** | Navigation, Render e Pipeline podem passar a depender uns dos outros diretamente. | Sinais semânticos e injeção de dependência unidirecional. |
| **Mouse Hover (`on_motion`)** | Quebra de responsividade por cálculos repetidos. | Preservar throttle/cache existentes e medir antes/depois. |
| **Sincronização de viewport** | Um controller pode assumir propriedade da lógica de outro. | `viewport_changed(xmin, xmax)` e responsabilidade clara de cada camada. |
| **Background Blitting** | Traços fantasmas/corrupção visual durante pan rápido. | Centralizar ciclo de captura/restauração e invalidar cache em mudanças de geometria/tema. |
| **Reparenting dos painéis** | Troca de gráficos pode disparar renders/reentrância. | Manter guardas de troca e debounce existentes até a nova arquitetura reproduzir o comportamento. |
| **Memória no Matplotlib** | Exportações off-screen podem acumular `Figure`s. | `try/finally`, fechamento explícito de figuras e teste com lotes repetidos. |
| **PDF em background** | Worker pode acessar objetos Qt ou estado mutável da GUI de forma insegura. | Worker recebe dados/configuração imutáveis e retorna apenas resultado/erro via sinais. |
| **Áudio** | Extração prematura pode quebrar timeline e sincronização. | Manter áudio na `MainWindow` na primeira rodada e apenas desacoplar interfaces gradualmente. |
| **ML** | Alteração do estado do learner pode afetar aprendizado por correções. | Testes de regressão com conjunto de correções conhecido. |
| **Persistência do modelo** | Troca de formato pode quebrar compatibilidade. | Tratar como frente independente e validar inferência antes da migração. |

---

# CRITÉRIOS DE ACEITE DA v4.5.0

A refatoração será considerada concluída quando:

- a análise continuar produzindo resultados compatíveis com o baseline;
- o cancelamento continuar cooperativo e limpo;
- cache, seleção de arquivos e estado de sessão permanecerem consistentes;
- os quatro painéis continuarem funcionando com o mesmo comportamento esperado;
- pan, zoom, hover e sincronização não apresentarem regressões perceptíveis;
- edição de pulsos, desfazer e aprendizado pelas correções continuarem funcionais;
- reprodução, timeline, volume e velocidade continuarem funcionais;
- exportação TXT/PDF permanecer funcional durante a transição;
- nova exportação gráfica gerar arquivos válidos e independentes da geometria da janela;
- relatório PDF modular funcionar em segundo plano sem congelar a GUI;
- não existir estado autoritativo duplicado entre `MainWindow` e `SessionContext`;
- os novos módulos estarem efetivamente presentes no código-fonte e cobertos por testes correspondentes;
- a documentação técnica da v4.5.0 distinguir claramente **implementado**, **em migração** e **planejado**.

---

# ESTRUTURA-ALVO

```text
ui/
├── main_window.py
├── panels.py
├── widgets.py
├── dialogs.py
├── dialogs/
│   ├── export_graph_dialog.py
│   └── export_report_dialog.py
└── controllers/
    ├── pipeline_orchestrator.py
    ├── plot_renderers.py
    ├── navigation_controller.py
    └── editor_controller.py

core/
├── session_context.py
├── analyzer.py
├── learner.py
├── engines.py
├── worker.py
└── updater.py

utils/
└── report_generator.py
```

A existência desses arquivos na arquitetura-alvo **não significa que já estejam implementados na versão atual**. O status de cada módulo deverá ser atualizado somente depois da migração real.

---

# SEQUÊNCIA RECOMENDADA DE EXECUÇÃO

```text
FASE 0
Baseline + testes
        ↓
FASE 1
SessionContext
        ↓
FASE 2
PipelineOrchestrator
        ↓
FASE 3
PlotRenderers
        ↓
FASE 4
NavigationController
        ↓
FASE 5
EditorController
        ↓
FASE 6
Integração da MainWindow
        ↓
FASE 7
Limpeza + remoção de duplicidades
        ↓
FASE 8
Exportação gráfica
        ↓
FASE 9
Relatório PDF modular
        ↓
FASE 10
Unificação dos menus
        ↓
FASE 11
Persistência segura do modelo
```

---

## Status do Roadmap

**Status:** Plano revisado para execução da v4.5.0.  
**Base arquitetural:** `ui/main_window.py` atual e ROADMAP anterior.  
**Escopo central:** desacoplamento seguro da `MainWindow`, preservação de comportamento, exportação científica modular e critérios explícitos de validação.  
**Fases concluídas e validadas:** FASE 0, FASE 1, FASE 2, **FASE 3** (100% auditada: dual ownership eliminado via aliases, FP badge sincronizado, 15/15 testes de caracterização e 22/22 testes da suíte completa passando).  
**Próximo marco de implementação:** executar a **FASE 4 — NavigationController** (isolamento de pan/zoom, sincronização horizontal, hover, cursor blitting e `capture_backgrounds`).
