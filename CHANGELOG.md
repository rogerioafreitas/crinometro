# 🦗 CHANGELOG - Crinômetro

Histórico completo, técnico e detalhado de todas as atualizações, correções e melhorias implementadas no software **Crinômetro**.

Para uma visão resumida direcionada ao uso diário, consulte a janela **Sobre** dentro do próprio aplicativo.

---

## [4.3.2] - 2026-09-17

### Performance & Renderização Assíncrona
- **Otimização de Redesenho Não-Bloqueante:** Substituição de repaints síncronos por agendamento assíncrono via `canvas.draw_idle()`, eliminando congelamentos e travamentos durante o redimensionamento de janelas e arrasto de divisores (*splitters*).
- **Contração Fluida do Painel de Espectrograma:** Implementação da classe `CompactCtrlBar(QFrame)` com `minimumSizeHint() == QSize(0, 0)`, removendo bloqueios mecânicos que impediam o colapso e encolhimento vertical do painel.
- **Compressão Contextual Dinâmica:** Redução automática de botões de controle de escala no espectrograma quando a largura do card for inferior a 520px, mantendo visíveis apenas as informações essenciais de Frequência Portadora e Filtro.
- **Debounce de Redimensionamento:** Temporizador adaptativo de 100 ms para recálculo de layouts, evitando tempestades de eventos (*event spam*) no Matplotlib.

### Interrupção & Controle de Fluxo
- **Cancelamento Cooperativo de Análises:** Implementação de cancelamento multithread seguro via `GenericWorker.abort()`.
- **Botão "✕ Abortar" no Cabeçalho:** Visível dinamicamente ao lado do botão "Reanalisar" exclusivamente enquanto a análise do áudio atual estiver em execução.
- **Botão "✕ Abortar" na Barra Lateral:** Visível dinamicamente ao lado de "⚡ Analisar Selecionados" durante análises em lote, permitindo pausar ou interromper o processamento em qualquer momento.

### Interface do Usuário (UI/UX)
- **Correção de Toggle nos Menus Dropdown:** Implementação de guarda temporal com *timestamp* (`last_close_time`) para os menus "Gráficos ▾" e "Exportar ▾". Clicar no botão do menu com ele aberto agora o fecha imediatamente em vez de reabri-lo.
- **Reorganização Ergonômica do Cabeçalho:**
  - Lado esquerdo: Botão "Reanalisar" isolado com o botão "✕ Abortar" adjacente.
  - Lado direito (da direita para a esquerda): "Gráficos ▾", "Exportar ▾", "⇋ Sync", "💾 Salvar Correções" e "🧠 IA: Ativada/Desativada".
- **Affordance e Contraste dos Botões de Controle:**
  - Presets de espectrograma (`segBtn`): Fundo sólido preenchido, bordas contrastantes e realce vívido em hover/ativo para temas escuro e claro.
  - Chips de tolerância (`ghostChip`): Estilização sólida com texto de alto contraste em negrito (`#F1F5F9` no escuro e `#0F172A` no claro).
  - Ferramentas dos cards (`plotTool`): Adição de borda sutil e background de interação para clarificar a clicabilidade.
- **Proporção Padrão dos Gráficos:** Aumento de 10% na largura padrão do Histograma de Intervalos (proporção 68% / 32%), prevenindo sobreposição na legenda de contagem de pulsos.
- **Linha Divisória de Título:** Adição de linha separadora suave de 1px (`#2D333B` / `#CBD5E1`) entre a barra de título e a área de plotagem em todos os cards.

### Documentação & Sobre
- **Simplificação das Notas no App:** Diálogo "Sobre" agora exibe resumo objetivo (`CHANGELOG_SUMMARY`), facilitando a compreensão rápida.
- **Documentação Completa Externa:** Criação deste documento `CHANGELOG.md` e do documento compilado `docs/CHANGELOG.pdf`, acessíveis pelo novo botão **"📄 Mais detalhes no GitHub"**.

---

## [4.3.0] - 2026-09-16

### Bioacústica & DSP
- **Identificação de Frequência Focal por Densidade:** Algoritmo de busca e rastreamento espectral que identifica a portadora dominante com maior densidade de chilreios.
- **Filtro de Rejeição de Banda Estreita (±300 Hz):** Expurgo rigoroso de pulsos e ecos espúrios distantes em frequência da portadora principal, eliminando falsos positivos de insetos e ruídos de fundo.
- **Espectrograma de Faixa Larga:** Renderização estendida até 10+ kHz com controle contínuo de faixa inferior e superior e alternância instantânea de unidades (Hz / kHz).
- **Prevenção de Falsos Diagnósticos de Cadência:** Rejeição de pausas fisiológicas longas e ruídos transitórios no cálculo de desaceleração rítmica do ICI, exigindo significância estatística ($p < 0.05$ e $|\text{slope}| > 0.15\text{ ms/s}$).

### Performance & Gerenciamento de Memória
- **Vetores Acústicos em `float32`:** Redução de 50% na alocação de memória RAM para matrizes de espectrograma (`Sxx_db`), forma de onda (`data`) e envoltória (`env`).
- **Otimização de Eventos de Mouse (Pan/Zoom):** Limitação de busca temporal por proximidade máxima (`dt_max`) e bloqueio de repintura em eixos ocultos.
- **Isolamento de Estado de Áudio:** Implementação de `reset_audio_state()` para evitar contaminação cruzada de picos residuais entre arquivos consecutivos.

### Relatórios em PDF
- **Agrupamento Comparativo por Espécime:** Consolidação automática de gravações do mesmo indivíduo com base no prefixo do nome do arquivo (`prefixo_*.wav`).
- **Tabelas Sintéticas de Espécimes:** Substituição de dados redundantes por agregações de Frequência Portadora, Taxa Média e Diagnóstico Global.

---

## [4.2.2] - 2026-09-14

### Correções & Estabilidade
- **Isolamento de Dependências no Instalador:** Empacotamento estrito de bibliotecas e DLLs dentro da subpasta `_internal`, prevenindo colisões no diretório raiz.
- **Cursor de Reprodução Reforçado:** Linha indicadora com espessura de 2px, contorno escuro protetor (*halo*) e marcadores triangulares nas extremidades para alta visibilidade sobre eventos densos.
- **Tipografia no Cabeçalho:** Ajuste fino de fontes para evitar quebra ou truncamento de parâmetros acústicos.
- **Controle Explícito de IA:** Remoção de reanálise automática ao alternar o botão de IA, mantendo o controle sob o clique do usuário em "Reanalisar".

---

## [4.2.0] - 2026-09-12

### Sistema de Atualização
- **Auto-Updater Integrado no Launcher:** Checagem automática e transparente de novos lançamentos no GitHub Releases com opção de atualização imediata.
- **Download em Background com Progresso:** Atualização fluida com barra de carregamento em tempo real sem encerrar a interface antes da substituição atômica.
- **Integração com Inno Setup:** Substituição segura de arquivos em execução via diretivas de reinicialização atômica do Windows.

---

## [4.1.2] - 2026-09-08

### Interface & Usabilidade
- **Launcher Integrado no Executável:** Exibição imediata da inicialização temática com o mascote animado em qualquer ambiente.
- **Efeito Drop Shadow Suave:** Renderização moderna de sombreamento na janela do Launcher.
- **Drag & Drop Livre entre Gráficos:** Mecanismo refinado para arrastar qualquer painel lateral secundário para a posição principal de foco.
- **Preservação de Layout da Barra Lateral:** Fixação de largura mínima para evitar recolhimento involuntário da lista de arquivos.

---

## [4.1.1] - 2026-09-04

### Correções
- **Correção em Aprendizado Ativo:** Resolução de dependência ausente de `find_peaks` na mineração de amostras negativas.
- **Ergonomia dos Controles:** Novo layout compacto com tooltips descritivos no botão de sincronização temporal.
- **Mini Janelas Laterais com Cantos Arredondados:** Enquadramento estético uniforme para os cards secundários.
- **Restauração do Padrão de 3 Pulsos:** Redefinição de fábrica do mínimo de pulsos por chilreio para $min\_p = 3$.

---

## [4.1.0] - 2026-09-03

### Aprendizado Ativo & Bioacústica
- **Indução de Regras Contrastivas de Poda (*Hard Negative Mining*):** Inferência de regras paramétricas a partir das exclusões manuais feitas pelo pesquisador.
- **Filtro Fisiológico Inter-Chilreio (*ICI Gate*):** Supressão de detecções espúrias durante o período refratário fisiológico natural ($\Delta t < 0.70 \times \text{ICI}_{\text{mediano}}$).
- **Exportação Acadêmica em PDF:** Relatórios diagramados para publicação contendo cabeçalho institucional, parâmetros e tabela detalhada de chilreios.
- **Snapping Magnético de Cursor:** Detecção inteligente de proximidade com tolerância de 15px para inserção e remoção ágil de pulsos.

---

## [4.0.0] - 2026-09-01

### Bioacústica Avançada & Inteligência Artificial
- **Segregação de Grilo Focal vs. Coro Distante:** Separação bioacústica de indivíduos em primeiro plano contra ruídos e cantos de fundo.
- **Conjunto de Descritores Físicos:** Extração de centroide espectral, *roll-off* 85%, tempo de ataque 10-90%, razão harmônico-ruído (HNR) e energia multiescala.
- **Mistura de Gaussianas (GMM Bimodal):** Classificação não supervisionada calculando a probabilidade contínua $P(\text{focal})$ por registro acústico.
- **Classificador Supervisionado:** Implementação de `HistGradientBoostingClassifier` com fallback para `RandomForestClassifier`.
- **Filtro de Coerência Rítmica $O(N)$:** Poda de pulsos intrusos sem quebra da cadência do chilreio.

---

## [3.5.1] - 2026-08-23
- Expansão para 14 descritores acústicos invariantes a ganho.
- Mineração regularizada de ruído de fundo para eliminação de desbalanceamento amostral.
- Portão contextual de chilreios (*Chirp-Aware Contextual Gating*).

---

## [3.5.0] - 2026-08-22
- Novo launcher interativo animado com mascote vetorial e mensagens de carregamento temáticas.
- Publicação dos primeiros manuais e guias científicos de operação em formato PDF.

---

## [3.4.0] - 2026-08-21
- Tolerância total para gravações sem chilreios (0 detecções permitidas para anotação manual).
- Execução assíncrona de tarefas demoradas com animação de indicador de atividade (*loading spinner*).
- Paleta cromática com 10 cores contrastantes para categorização visual de chilreios por quantidade de pulsos.

---

## [3.3.0] - 2026-08-20
- Edição manual instantânea com latência imperceptível em tempo real.
- Execução desacoplada de rotinas de aprendizado de máquina em threads dedicadas.

---

## [3.2.0] - 2026-08-19
- Exportação e importação de modelos treinados e correções acumuladas em arquivos compactos `.pkl`.
- Expansão do classificador Random Forest para 500 estimadores paralelos.

---

## [3.1.0] - 2026-08-16
- Atualização em alta frequência do cursor de áudio na timeline (100 Hz / 10 ms).
- Eliminação de falhas e travamentos durante o deslocamento contínuo da reprodução.

---

## [3.0.0] - 2026-08-15
- Lançamento da nova identidade visual com suporte integral a Temas Escuro e Claro.
- Sistema de análise em lote com marcação seletiva de arquivos.
- Dicas interativas (*tooltips*) em marcadores de eventos acústicos.
