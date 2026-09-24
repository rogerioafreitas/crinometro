# Contrato de Estado (State Contract) - v4.5.0

Este documento inventaria exaustivamente o estado da `MainWindow` e define a categorização e a propriedade de cada atributo na arquitetura modular da v4.5.0.

## 1. Estado de Domínio / Analítico (Fonte da Verdade: `SessionContext`)
- `active_heavy_data`: (dict) Contém dados pesados da análise do arquivo ativo (`rate`, `data`, `data_b1`, `env`, `peaks`, `chirps`, `chirp_peaks_list`, `chirp_peaks`, `media`, `moda`, `f_spec`, `t_spec`, `Sxx_db`, `dom_freqs`, `duration`, `params`, `peaks_detected`, `peaks_user_verified`, `distant_peaks`, `carrier_freq`, `discarded_peaks_reasons`, `valid_peaks_stage2`, `peak_dur_dict`, `f_psd`, `Pxx_db`).
- `analysis_cache`: (dict) Mapeamento `filename -> heavy_data` para evitar recomputações desnecessárias.
- `algo_params`: (dict) Parâmetros analíticos base do usuário (ex: `freq_tolerance_hz`, `min_p`, `max_dist_ms`, `b1_min`, `b1_max`, etc.).
- `_adaptive_overrides`: (dict) Sobreposições adaptativas calculadas por heurística ou IA (`prominence`, `noise_floor`, `width_min_ms`).
- `peaks_detected`: (list[int]) Índices amostrais de picos/pulsos detectados automaticamente pelo analisador DSP.
- `peaks_user_verified`: (list[int]) Índices amostrais de pulsos confirmados após intervenção humana ou carregamento de correções salvas.
- `corrections_by_file`: (dict[str, list]) Histórico de correções manuais persistidas em memória por arquivo de áudio.

## 2. Estado de Seleção / Navegação (Gerenciado pelo `NavigationController` a partir da Fase 4)
- `active_filename`: (str | None) Nome do arquivo de áudio atualmente selecionado e renderizado no dashboard. (Temporariamente em `SessionContext` para compatibilidade).
- `loaded_files`: (dict[str, str]) Mapeamento de nome de exibição para caminho absoluto no disco (`filename -> full_path`). (Temporariamente em `SessionContext` para compatibilidade).
- `last_audio_dir`: (str | None) Caminho do último diretório acessado pelo usuário para abertura de áudios.
- `_saved_viewport`: (dict | None) Dicionário preservando os limites de eixos (`wave_xlim`, `wave_ylim`, `freq_xlim`, `freq_ylim`, `spec_xlim`, `spec_ylim`) durante trocas de estado e reanálises.

## 3. Estado de Edição / ML (Gerenciado por `EditorController` e `PulseLearner`)
- `_pulse_edit_history`: (list) Pilha de estados anteriores de `peaks_user_verified` para suporte à operação de Desfazer (Undo).
- `pulse_learner`: (`PulseLearner` | None) Instância do modelo de aprendizado de máquina adaptativo baseado em correções do usuário.
- `use_machine_learning`: (bool) Flag mestre indicando se o modelo de aprendizado de máquina está ativado ou se o pipeline opera estritamente em modo DSP tradicional.
- `pulse_metadata`: (dict) Metadados complementares atribuídos manualmente a pulsos individuais (ex: anotações, flags de chirp).
- `_wave_user_markers`: (list) Marcadores manuais de pulso desenhados diretamente na forma de onda.
- `pulse_hover_data`: (list) Cache de coordenadas e raios de tolerância para detecção de hover e cliques no editor de pulsos.
- `_click_alignment_lines`: (list) Linhas guias visuais renderizadas durante o alinhamento de cliques interativos.

## 4. Estado de Relatório / Exportação (Compartilhado entre `SessionContext` e geradores de exportação)
- `report_params`: (dict) Parâmetros configurados para geração de relatórios técnicos (`lang`, `institution`, `researcher_name`, `role`, `level`).

## 5. Estado Visual e Estrutural da UI (Permanece em `MainWindow` e `PlotRenderers`)
- `main_panel`: (`PlotPanel`) Painel que ocupa a área visual focal/superior do dashboard.
- `stack_panels`: (list[`PlotPanel`]) Lista dos três painéis dispostos na pilha secundária.
- `all_panels`: (list[`PlotPanel`]) Lista contendo as 4 instâncias de painéis (`panel_wave`, `panel_hist`, `panel_freq`, `panel_spec`).
- `theme_mode`: (str) Tema atual da interface (`"dark"` ou `"light"`).
- `lang`: (str) Código de idioma ativo da interface (`"pt"` ou `"en"`).
- `_last_applied_spec_unit`: (str) Unidade espectral em vigor (`"db_rel"` ou `"db_full"`).
- `_plots_menu_open` / `_plots_menu_last_close_time`: Controle de debounce do dropdown de seleção de gráficos.
- `_export_menu_open` / `_export_menu_last_close_time`: Controle de debounce do dropdown de exportação de relatórios.
- Player de áudio: `playback_speed`, `cursor_lines` (linhas verticais indicadoras de progresso), instâncias de `player` e `timeline`.

## 6. Estado Transitório de Infraestrutura (Gerenciado por Controladores e Workers)
- Background Workers: `_reanalyze_worker` (`GenericWorker`), `_batch_worker` (`GenericWorker`), `_learn_worker` (`GenericWorker`), `_checker_thread` (`UpdateCheckerThread`).
- Spinners de feedback visual: `_reanalyze_spinner` (`ButtonSpinner`), `_batch_spinner` (`ButtonSpinner`).
- Timers de debounce: `_dashboard_splitter_debounce_timer`, `_resize_debounce_timer`, `_focus_debounce_timer`, `playback_timer`, `_carrier_tol_timer`.
- Otimização Matplotlib (Blitting): `bg_cache_valid`, `backgrounds`.
- Ferramentas de navegação interativa (Pan/Zoom): `panning`, `active_ax`, `start_xlim`, `start_ylim`, `start_x`, `start_y`, `last_draw_time`, `sync_throttle_time`, `_last_pan_time`.
- Flags de sincronização e transição de layout: `_swapping_panels`, `_refreshing_canvases`, `_has_shown_initial_layout`.
- Motores de desenho C/C++ vinculados: `line_engine` (`HighPerfLineEngine`), `spectro_engine` (`HighPerfSpectrogramEngine`), `freq_engine` (`HighPerfPSDViewer`).
