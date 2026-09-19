"""
Crinômetro - Constantes Globais e Parâmetros de Configuração.
"""

APP_VERSION = "4.4.0"
CONFIG_FILE = "crinometro_config.json"

DEFAULT_ALGO_PARAMS = {
    "amp_min": 0.08, "amp_max": 1.00, "amp_var": 0.40,
    "dur_min": 14.0, "dur_max": 80.0,
    "gap_min": 25.0, "gap_max": 35.0,
    "min_p": 3, "max_p": 10, "b1_min": 3200, "b1_max": 6000,
    "prominence": 0.02, "width_min_ms": 0.0, "width_max_ms": 0.0,
    "smooth_window_ms": 15.0, "noise_floor": 1.00,
    "adaptation_rate": 0.10,
    "focal_sensitivity": 0.60,
    "freq_tolerance_hz": 300.0,
}

# Resumo simplificado e objetivo para exibição interna no diálogo Sobre / Notas de Atualização
CHANGELOG_SUMMARY = {
    "4.4.0": [
        "Histograma Bivariado com Eixo Duplo: contagem de chilreios e linha de tendência com duração média em ms no mesmo gráfico.",
        "Espectro de Potência (PSD): novo gráfico via método de Welch com anotação automática da portadora e foco acústico (0–15 kHz).",
        "Controle Rigoroso de Pulsos: bloqueio absoluto de falsos chilreios curtos (< 3 pulsos) e imposição fisiológica de min_p.",
        "Modo DSP Padrão e Reset de IA: inicialização nativa em DSP puro, diálogo instrutivo de IA e botão para resetar o classificador.",
        "Navegação com Limites Inteligentes: delimitação de área útil em todos os gráficos e zoom focal estrito em FP ± tolerância."
    ],
    "4.3.2": [
        "Desempenho Ultra-Fluido: eliminação de travamentos no redimensionamento dos gráficos e na navegação de zoom e pan.",
        "Espectrograma Adaptativo: contração livre sem bloqueios de largura mínima e ocultação contextual de controles em telas compactas.",
        "Cancelamento Cooperativo: novo botão '✕ Abortar' para interromper análises individuais ou em lote a qualquer momento.",
        "Ergonomia e Alto Contraste: cabeçalho reorganizado, botões de controle com affordance clicável sólida e mini-menus com fechamento por toggle."
    ],
    "4.3.0": [
        "Frequência Portadora Automática (FP): identificação instantânea da banda focal e filtro espectral de ±300 Hz contra ruídos.",
        "Controles Interativos no Espectrograma: ajuste de escala Y via slider vertical até 50 kHz, alternância kHz/Hz e presets '10k', 'Focal' e 'Total'.",
        "Navegação Direta: zoom fluido na roda do mouse (sem Ctrl) e pan rápido com o botão direito.",
        "Relatórios Agrupados: exportação em PDF consolidada por espécime com diagnóstico bioacústico."
    ],
    "4.2.2": [
        "Cursor de Alta Visibilidade: linha de reprodução com contorno protetor na timeline.",
        "Controle Manual de Reanálise: reanálise por IA acionada exclusivamente sob demanda."
    ],
    "4.2.0": [
        "Auto-Updater Integrado: verificação e download de atualizações diretamente no aplicativo.",
        "Manuais Técnicos e Didáticos: documentação científica completa em PDF."
    ],
    "4.1.2": [
        "Reorganização Livre de Gráficos: suporte a arrastar e soltar (drag & drop) para trocar e maximizar gráficos.",
        "Relatório Simplificado: síntese bioacústica compacta para múltiplos áudios."
    ],
    "4.1.0": [
        "Filtro ICI Gate: expurgo automático de falsos positivos durante o período refratário fisiológico.",
        "Edição Precisa de Pulsos: snapping inteligente de marcadores e exportação de relatórios completos para publicação."
    ],
    "4.0.0": [
        "Segregação Bioacústica Avançada: separação inteligente de grilos focais vs. coro distante de fundo.",
        "Classificador Supervisionado: aprendizado de máquina em tempo real com árvore de decisão de alta velocidade."
    ],
    "3.5.0": [
        "Novo Launcher Animado: inicialização temática com mascote vetorial.",
        "Normalização Robusta: proteção DSP contra impactos e ruídos de baixa frequência."
    ],
    "3.4.0": [
        "Processamento Assíncrono: tarefas pesadas em background com loading spinner animado.",
        "Paleta Cromática de Pulsos: diferenciação visual de chilreios por contagem de pulsos."
    ]
}

# Histórico técnico completo preservado para exportação em CHANGELOG.md e CHANGELOG.pdf
CHANGELOG_FULL = {
    "4.4.0": [
        "Implementação do Histograma Bivariado de Pulsos com Eixo Duplo (twinx): barras de contagem absoluta no eixo Y primário (esquerdo) e linha de tendência com marcadores discretos conectando a duração média dos chilreios em milissegundos (ms) no eixo Y secundário (direito).",
        "Substituição do gráfico de frequência instantânea pelo Espectro de Potência Médio (PSD) calculado via método de Welch no analyzer (janela de 4096 amostras), com faixa inicial focada em 0–15 kHz, pan delimitado até a frequência de Nyquist e anotação direta do pico da portadora.",
        "Enforcement absoluto do parâmetro de pulsos mínimos (min_p) no pipeline de agrupamento de chilreios, descartando eventos espúrios isolados (< min_p) e eliminando falsos chilreios curtos de 1 ou 2 pulsos mesmo na presença de ruídos residuais.",
        "Resolução definitiva do conflito de cache de correções: remoção da injeção cega de picos do DSP (validate_all), impedindo que o histórico gerasse centenas de falsas alterações e distorcesse o treinamento do modelo.",
        "Modo DSP puro como padrão de inicialização: o Crinômetro inicia sempre com a IA desativada. Ativar a IA exibe diálogo instrutivo com recomendações e salvaguardas.",
        "Novo comando 'Resetar Aprendizado da IA' no menu Configurações: restaura o estado original do DSP, expurga dados de treinamento persistidos (.crntrain) e reinicia a memória do classificador.",
        "Delimitação rigorosa de limites de navegação (clamp de pan e zoom) em todos os eixos, garantindo que a visualização permaneça estritamente dentro da área de dados acústicos úteis.",
        "Correção do preset 'Focal' no espectrograma para centralizar na banda da frequência portadora (FP ± tolerância) sem limites fixos legados, e padronização do zoom inicial sempre como 'Total' (0 a Nyquist).",
        "Unificação do status do modelo (lbl_model_status) com indicação precisa do modo ativo (Modo DSP puro, IA Não-Supervisionada ou IA Supervisionada), adaptado aos temas Claro e Escuro."
    ],
    "4.3.2": [
        "Desempenho Ultra-Fluido: eliminação de travamentos no redimensionamento dos gráficos e na navegação de zoom e pan.",
        "Espectrograma Adaptativo: contração livre sem bloqueios de largura mínima e ocultação contextual de controles em telas compactas.",
        "Cancelamento Cooperativo: novo botão '✕ Abortar' para interromper análises individuais ou em lote a qualquer momento.",
        "Ergonomia e Alto Contraste: cabeçalho reorganizado, botões de controle com affordance clicável sólida e mini-menus com fechamento por toggle."
    ],
    "4.3.0": [
        "Frequência Portadora Automática (FP): identificação instantânea da banda focal e filtro espectral de ±300 Hz contra ruídos.",
        "Controles Interativos no Espectrograma: ajuste de escala Y via slider vertical até 50 kHz, alternância kHz/Hz e presets '10k', 'Focal' e 'Total'.",
        "Navegação Direta: zoom fluido na roda do mouse (sem Ctrl) e pan rápido com o botão direito.",
        "Relatórios Agrupados: exportação em PDF consolidada por espécime com diagnóstico bioacústico."
    ],
    "4.2.2": [
        "Cursor de Alta Visibilidade: linha de reprodução com contorno protetor na timeline.",
        "Controle Manual de Reanálise: reanálise por IA acionada exclusivamente sob demanda."
    ],
    "4.2.0": [
        "Auto-Updater Integrado: verificação e download de atualizações diretamente no aplicativo.",
        "Manuais Técnicos e Didáticos: documentação científica completa em PDF."
    ],
    "4.1.2": [
        "Reorganização Livre de Gráficos: suporte a arrastar e soltar (drag & drop) para trocar e maximizar gráficos.",
        "Relatório Simplificado: síntese bioacústica compacta para múltiplos áudios."
    ],
    "4.1.0": [
        "Filtro ICI Gate: expurgo automático de falsos positivos durante o período refratário fisiológico.",
        "Edição Precisa de Pulsos: snapping inteligente de marcadores e exportação de relatórios completos para publicação."
    ],
    "4.0.0": [
        "Segregação Bioacústica Avançada: separação inteligente de grilos focais vs. coro distante de fundo.",
        "Classificador Supervisionado: aprendizado de máquina em tempo real com árvore de decisão de alta velocidade."
    ],
    "3.5.0": [
        "Novo Launcher Animado: inicialização temática com mascote vetorial.",
        "Normalização Robusta: proteção DSP contra impactos e ruídos de baixa frequência."
    ],
    "3.4.0": [
        "Processamento Assíncrono: tarefas pesadas em background com loading spinner animado.",
        "Paleta Cromática de Pulsos: diferenciação visual de chilreios por contagem de pulsos."
    ]
}

# Histórico técnico completo preservado para exportação em CHANGELOG.md e CHANGELOG.pdf
CHANGELOG_FULL = {
    "4.3.2": [
        "Otimização assíncrona de renderização com canvas.draw_idle(), eliminando repaints síncronos bloqueantes e travamentos durante o redimensionamento de janelas e drag do splitter.",
        "Criação da classe CompactCtrlBar(QFrame) com minimumSizeHint flexível (0, 0), permitindo contração total do espectrograma sem bloqueios mecânicos de layout.",
        "Compressão contextual adaptativa dos controles do espectrograma: ocultação automática de limites Y e presets quando a largura for < 520px, mantendo apenas FP e Filtro.",
        "Novo mecanismo de cancelamento cooperativo via GenericWorker.abort(), com botão '✕ Abortar' no cabeçalho e na barra lateral durante análises simples e em lote.",
        "Correção do comportamento toggle nos mini-menus 'Gráficos ▾' e 'Exportar ▾' com guarda de timestamp de fechamento para evitar reabertura imediata no segundo clique.",
        "Reestruturação visual do cabeçalho de ações: 'Reanalisar' isolado à esquerda com botão de abortar; demais ferramentas acumuladas da direita para a esquerda.",
        "Aprimoramento de affordance tátil e contraste dos botões de controle (segBtn, ghostChip e plotTool) com preenchimento sólido e bordas nítidas nos temas escuro e claro.",
        "Ajuste da proporção padrão do splitter horizontal para 68% / 32% (histograma ~10% mais largo) e linha divisória sutil de 1px nas barras de título dos cards."
    ],
    "4.3.0": [
        "Identificação de Frequência Focal por Densidade de Chilreios e Filtro de ±300 Hz: localização automática da frequência portadora com maior densidade de chilreios e expurgo sistemático de pulsos espúrios com mais de 300 Hz de desvio, eliminando falsos positivos e ruídos externos.",
        "Controles Interativos de Escala e Unidades no Espectrograma: manipulação vertical contínua com spinboxes dedicados para limites inferior e superior, alternância dinâmica de unidade entre Hz e kHz com conversão instantânea de rótulos/marcadores, atalhos de preset ('10k' e 'Focal') e espectrograma de banda ampla abrangendo todo o som do áudio até 10+ kHz.",
        "Otimização de Performance e Fluidez no Pan/Zoom: eliminação completa de lag e travamentos durante navegação com múltiplos áudios; redução de 50% no consumo de RAM via float32 nos arrays acústicos (data, env, Sxx_db), filtragem ultra-rápida de proximidade temporal (dt_max) no evento de hover e bloqueio de repintura em painéis invisíveis.",
        "Agrupamento Bioacústico por Espécime no Relatório Geral (PDF): consolidação comparativa agrupada por identificador de espécime (prefixo antes do sublinhado '_'), exibindo métricas globais agregadas e substituindo a coluna 'Diagnóstico Rítmico' por 'Frequência Portadora' consolidada.",
        "Robustez Estatística no Diagnóstico de Cadência Rítmica: rejeição automática de pausas fisiológicas longas e lacunas de ruído passageiro na análise de regressão do ICI, com exigência de significância estatística (p < 0.05 e |slope| > 0.15 ms/s) para evitar falsos positivos de desaceleração.",
        "Correção do Bug Crítico de Perda Global de Detecção: eliminação de contaminação cruzada de picos residuais entre áudios com método atômico de reinicialização de estado (reset_audio_state), garantindo que novos áudios longos mantenham detecção integral ao longo de toda a duração, além de salvaguardas contra poda excessiva no PulseLearner."
    ],
    "4.2.2": [
        "Correção do Instalador e Auto-Updater: isolamento rigoroso de dependências na subpasta '_internal', evitando descompactação indevida de DLLs na raiz, e garantia de reinicialização atômica do executável mais recente instalado.",
        "Ajuste de Tipografia e Layout no Cabeçalho de Metadados: redução para 10px e otimização dos espaçamentos para eliminar truncamentos de texto de parâmetros.",
        "Cursor de Reprodução de Alto Contraste na Timeline: linha reforçada de 2px com contorno escuro protetor (halo) e ponteiros estilizados no topo e na base, garantindo visibilidade total mesmo sob densas marcações de eventos.",
        "Controle Manual de Reanálise por IA: remoção da reanálise automática ao alternar o botão de IA, permitindo ao usuário reanalisar apenas quando desejar pelo botão específico 'Reanalisar'."
    ],
    "4.2.0": [
        "Sistema de Atualização Automática Integrado: verificação inteligente de releases no GitHub diretamente no Launcher, permitindo ao usuário escolher entre atualizar imediatamente ou lembrar mais tarde.",
        "Instalação Fluida em Segundo Plano: download com barra de progresso em tempo real e atualização dos arquivos com o Launcher aberto, sem encerramentos abruptos da interface.",
        "Integração Robusta com Inno Setup: substituição segura e atômica de executáveis via diretivas 'restartreplace uninsrestartdelete' e reinicialização automática do programa atualizado.",
        "Documentação Técnica e Didática em PDF Atualizada: manuais científicos revisados para v4.2.0 com diagramação aperfeiçoada e suporte tipográfico Unicode completo.",
        "README Reestruturado e Sintético: visão geral objetiva, regras estritas de versionamento semântico (SemVer) e instruções concisas de compilação e execução."
    ],
    "4.1.2": [
        "Launcher Integrado no Executável: inicialização direta exibindo o mascote animado e frases temáticas antes da tela principal, tanto no código-fonte quanto no executável (.exe).",
        "Efeito de Sombra Suave (Drop Shadow) no Launcher: janela frameless translúcida com renderização multicamadas de sombra suave e borda sutil para destaque no desktop.",
        "Relatório Simplificado em PDF compacto: consolidação de múltiplos áudios por página sem desperdício de espaço e síntese bioacústica comparativa integrada.",
        "Estabilidade da Barra Lateral: correção do encolhimento automático do divisor (splitter) após análise de áudio, com preservação de largura mínima de 220px.",
        "Arraste e Solte (Drag & Drop) Fluido de Painéis: previsão visual de drop (moldura com preview translúcido) sem piscadas ou reconstrução prematura, executando a reorganização somente ao soltar o mouse.",
        "Troca Rápida de Painel Principal: suporte completo a arrastar qualquer mini janela lateral para a posição do gráfico maximizado para substituí-lo instantaneamente.",
        "Ajuste visual refinado dos gráficos e eliminação de barras de rolagem redundantes."
    ],
    "4.1.1": [
        "Correção do bug no aprendizado ativo ('find_peaks' indefinido na mineração de negativos).",
        "Redesign dos botões de ação e reposicionamento ergonômico do botão de sincronização X (compacto, com legendas em hover).",
        "Modernização dos gráficos laterais em formato de 'mini janelinhas' com cantos arredondados, enquadramento aprimorado e reordenação instantânea.",
        "Redimensionamento suave e sem engasgos da lista de arquivos de áudio (elisão dinâmica do nome do arquivo com debounce).",
        "Reset completo de modelos prévios e inicialização estrita no modo DSP padrão, com treino ultra-rápido (<150ms) focado em correções manuais.",
        "Otimização da taxa de quadros (FPS) no pan e zoom dos gráficos de amplitude e espectrograma.",
        "Correção no gerador de relatórios PDF, restaurando o diagnóstico de cadência rítmica e a tabela sequencial completa de chilreios.",
        "Restauração do valor padrão mínimo de 3 pulsos por chilreio (min_p = 3)."
    ],
    "4.1.0": [
        "Aprendizado Contrastivo Baseado em Regras (Hard Negative Rule Induction): indução automática de regras rígidas de poda com margem de segurança de 30% a partir de correções manuais.",
        "Filtro Rítmico Fisiológico Inter-Chilreio (ICI Gate): descarte de detecções espúrias durante o período refratário fisiológico (Δt < 0.70 × ICI_mediano).",
        "Exportação de Relatórios Completos em PDF para publicação: cabeçalho institucional, diagnóstico de cadência rítmica (regressão linear do ICI) e tabela estruturada e paginada de chilreios.",
        "Otimização da interação nos gráficos: hit-box snapping em pixels de tela (~15px) para seleção/remoção de marcadores e preservação do timestamp exato em áreas limpas.",
        "Ajuste e hierarquia de Z-Order visual: marcadores de detecção e hover na camada superior (zorder=7) e marcadores de edição de usuário em camada inferior (zorder=4).",
        "Harmonização visual global e acessibilidade (UI/UX): cursor de mão em 100% dos botões, ícones, cards e checkboxes, além de padronização de altura mínima (32px), padding e cantos arredondados."
    ],
    "4.0.0": [
        "Nova arquitetura de bioacústica avançada: segregação de grilos focais (primeiro plano) vs. grilos distantes (coro de fundo e ecos).",
        "Extração de descritores físicos de atenuação acústica (Centroide espectral, Roll-off 85%, Attack Time 10-90%, HNR e Multi-scale energy).",
        "Segregação acústica não supervisionada via Mistura de Gaussianas (GMM bimodal) calculando prior contínuo P(focal) por gravação.",
        "Classificador supervisionado de alta velocidade baseado em HistGradientBoosting (com fallback resiliente para Random Forest).",
        "Filtro de coerência de trilha acústica em tempo linear O(N) para expurgar intrusos rítmicos sem fragmentar chilreios.",
        "Novo controle de Sensibilidade Focal / Rejeição de Grilos Distantes no menu de Configurações Avançadas.",
        "Botão dedicado na barra de ferramentas para ativar ou desativar a análise com IA (🧠 IA: Ativada / Desativada).",
        "Feedback visual sutil na forma de onda e espectrograma identificando picos classificados como coro distante."
    ],
    "3.5.1": [
        "Aprimoramento abrangente da árvore de aprendizado com conjunto de 14 descritores físicos invariantes a ganho.",
        "Mineração automática de amostras de ruído de fundo (negative background mining) e regularização do ensemble para eliminar desbalanceamentos.",
        "Filtro probabilístico e contextual de pulsos (Chirp-Aware Contextual Gating), garantindo que pulsos rítmicos nunca fragmentem chilreios.",
        "Normalização robusta de sinal em banda no pipeline DSP, imune a ruídos e impactos de baixa frequência (<100 Hz)."
    ],
    "3.5.0": [
        "Novo launcher temático e vetorial com animação interativa do mascote e frases dinâmicas.",
        "Sincronização refinada de abertura com transição suave para a tela principal após o carregamento.",
        "Disponibilização de manuais estruturados em PDF para pesquisadores e público geral."
    ],
    "3.4.5": [
        "Paleta expandida com 10 cores distintas e de alto contraste para chilreios de 2 a 10 pulsos (+ cor extra).",
        "Correção do estado visual do botão de edição manual, desativando o destaque azul ao acionar reanálise.",
        "Sincronização de áudio e aceleração a 1.2x na reprodução das animações de inicialização do launcher."
    ],
    "3.4.4": [
        "Abertura instantânea do Launcher com reprodução contínua de loading.mp4 em segundo plano.",
        "Transição sincronizada para loaded.mp4 assim que os módulos são carregados.",
        "Exibição fluida e encerramento automático do launcher sem piscamentos ou travamentos."
    ],
    "3.4.3": [
        "Padronização do cursor de clique (hand pointer) em todos os botões e ferramentas da interface.",
        "Remoção de tarjas e aplicação de transparência total no contêiner 'Selecionar tudo'."
    ],
    "3.4.2": [
        "Correção definitiva da seleção individual e em lote dos arquivos de áudio.",
        "Correção do comportamento e visibilidade dinâmica do controle 'Selecionar tudo'.",
        "Análise em lote de selecionados agora processa fielmente apenas os áudios marcados."
    ],
    "3.4.1": [
        "Correção do encerramento inesperado ao alternar entre áudios já analisados e reanalisados.",
        "Preservação integral do cache de dados e picos detectados na memória.",
        "Sistema global de captura de erros com pop-up modal detalhado (Crash Reporter) para diagnóstico imediato."
    ],
    "3.4.0": [
        "Tolerância e resiliência total na análise: arquivos com 0 chilreios são exibidos normalmente para edição manual.",
        "Parâmetro padrão de chilreios atualizado de fábrica para a faixa de 2 a 10 pulsos.",
        "Botão contextual dinâmico 'Analisar' / 'Reanalisar' com Loading Spinner animado e indicador na lista de arquivos.",
        "Desativação automática da ferramenta de edição manual ao acionar reanálise.",
        "Novo design de barras de rolagem (Scrollbar) com trilho e puxador arredondados em cinza suave.",
        "Loading Spinner discreto semi-transparente adicionado à tela de carregamento do launcher.",
        "Correção de encerramento inesperado ao abrir as preferências de algoritmo."
    ],
    "3.3.0": [
        "Eliminação de travamentos ao editar pulsos manualmente com resposta imediata em tempo real.",
        "Execução assíncrona em background para Reanálise, Aprendizado Ativo e Análise em Lote.",
        "Indicador visual dinâmico com Loading Spinner animado diretamente dentro dos botões acionados."
    ],
    "3.2.3": [
        "Compatibilidade retroativa com modelos anteriores (tolerância automática entre 7 e 12 features).",
        "Verificação de compatibilidade de versão ao importar arquivos de treinamento (.pkl).",
        "Notas de Atualização com scroll suave e tipografia refinada sem excesso de destaque no 'atual'.",
        "Menu hambúrguer com hover azul bem visível e consistente em ambos os temas.",
        "Botões de ação e ferramentas com hover em tons azulados e ícones de alto contraste no tema claro."
    ],
    "3.2.2": [
        "Ajuste visual de pop-ups removendo containers de fundo destoantes nas legendas.",
        "Novo design moderno para a barra de rolagem (scroll) com tom azulado e bordas arredondadas.",
        "Menu hambúrguer aprimorado com cantos arredondados e hover/clique azul vívido mais responsivo."
    ],
    "3.2.1": [
        "Correção e alinhamento visual dos submenus do menu hambúrguer no hover.",
        "Suporte completo ao tema claro para todas as janelas de diálogo e pop-ups.",
        "Caixa 'Selecionar tudo' na barra lateral agora é oculta por padrão e surge dinamicamente ao marcar áudios.",
        "Hiperlink clicável na versão da janela Sobre para exibir o histórico de mudanças."
    ],
    "3.2.0": [
        "Classificador Random Forest expandido para 500 árvores de decisão em paralelo.",
        "Extração bioacústica ampliada para 12 descritores morfológicos e espectrais.",
        "Funcionalidade de Exportar e Importar arquivos de treinamento (.pkl).",
        "Correção na resolução do nome de arquivos no botão Reanalisar e Aprendizado com Correções."
    ],
    "3.1.0": [
        "Taxa de atualização de áudio e timeline acelerada para 10 ms (100 Hz).",
        "Correção de instabilidades e crashes ao arrastar o cursor de reprodução na timeline.",
        "Otimização de eventos de reprodução e isolamento de rotinas gráficas."
    ],
    "3.0.0": [
        "Nova interface visual modernizada com temas Claro e Escuro.",
        "Sistema de seleção individual de áudios e exclusão rápida na barra lateral.",
        "Análise em lote e relatórios consolidados apenas para áudios selecionados.",
        "Tooltips e hover interativo nos marcadores de pulsos (X) com contagem de pulsos por chilreio."
    ]
}

# Alias canônico utilizado pela interface do usuário (resumido e limpo)
CHANGELOG = CHANGELOG_SUMMARY
