"""
Crinômetro - Constantes Globais e Parâmetros de Configuração.
"""

APP_VERSION = "4.0.0"
CONFIG_FILE = "crinometro_config.json"

DEFAULT_ALGO_PARAMS = {
    "amp_min": 0.08, "amp_max": 1.00, "amp_var": 0.40,
    "dur_min": 14.0, "dur_max": 80.0,
    "gap_min": 25.0, "gap_max": 35.0,
    "min_p": 2, "max_p": 10, "b1_min": 3200, "b1_max": 6000,
    "prominence": 0.02, "width_min_ms": 0.0, "width_max_ms": 0.0,
    "smooth_window_ms": 15.0, "noise_floor": 1.00,
    "adaptation_rate": 0.10,
    "focal_sensitivity": 0.60,
}

CHANGELOG = {
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

