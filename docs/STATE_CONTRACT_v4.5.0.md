# Contrato de Estado (State Contract) - v4.5.0

Este documento inventaria o estado atual contido na `MainWindow` e define como ele será migrado para o `SessionContext` ou controladores específicos, garantindo uma única fonte de verdade.

## 1. Estado de Domínio / Analítico (Vai para `SessionContext`)
- `active_heavy_data`: (dict) Contém sinais de áudio brutos, arrays numpy (t, envelope), STFT, etc.
- `analysis_cache`: (dict) Cache de arquivos já analisados para reutilização rápida.
- `algo_params` / `_adaptive_overrides`: (dict) Parâmetros do algoritmo e heurísticas.
- `peaks_detected`: (list) Pulsos autodetectados.
- `peaks_user_verified`: (list) Pulsos finais após edição humana.
- `corrections_by_file`: (dict) Persistência temporária das correções em memória.

## 2. Estado de Edição / ML (Vai para `EditorController` ou `SessionContext`)
- `_pulse_edit_history`: (list) Histórico de ações (undo).
- `pulse_learner`: Instância de ML/classificação.

## 3. Estado de Seleção / Navegação (Vai para `NavigationController`)
- `active_filename`: Arquivo selecionado no momento.
- `loaded_files`: Lista (opcional, pode ser de um painel de arquivos).
- `bg_cache_valid` / `backgrounds`: Caches de blitting do Matplotlib.
- Limites de visualização (xlim/ylim atuais dos gráficos).

## 4. Estado de Relatório / Exportação (Vai para `SessionContext` e `ExportDialogs`)
- `report_params`: Configurações como espécie, pesquisador, metadados gerais.
- Preferências de plotagem.

## 5. Estado puramente visual da UI (Permanece em `MainWindow` ou `PlotRenderers`)
- Instâncias dos widgets (QSplitter, PlotPanels).
- `theme_mode` e `lang` (Internacionalização).
- Configurações do Player de Áudio (posição da timeline).

