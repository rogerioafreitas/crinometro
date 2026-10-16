"""
Crinômetro - Constantes Globais e Parâmetros de Configuração.
"""

APP_VERSION = "4.5.0"          # versão numérica pura — usada por parse_version_tuple, updater e learner
APP_VERSION_LABEL = "4.5.0"       # rótulo de exibição — usado pela UI, título de janela e relatórios
import os, shutil

def _user_config_dir():
    override = os.environ.get("CRINOMETRO_CONFIG_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "Crinometro")
    os.makedirs(d, exist_ok=True)
    return d

CONFIG_FILE = os.path.join(_user_config_dir(), "crinometro_config.json")

_legacy = os.path.abspath("crinometro_config.json")
if not os.path.exists(CONFIG_FILE) and os.path.exists(_legacy):
    try:
        shutil.copy2(_legacy, CONFIG_FILE)
    except OSError:
        pass

import threading
CONFIG_LOCK = threading.RLock()

DEFAULT_ALGO_PARAMS = {
    "amp_min": 0.30, "amp_max": 1.00, "amp_var": 0.40,
    "dur_min": 14.0, "dur_max": 80.0,
    "gap_min": 25.0, "gap_max": 35.0,
    "min_p": 3, "max_p": 10, "b1_min": 3200, "b1_max": 6000,
    "prominence": 0.02, "width_min_ms": 0.0, "width_max_ms": 0.0,
    "smooth_window_ms": 15.0, "noise_floor": 1.00,
    "adaptation_rate": 0.10,
    "focal_sensitivity": 0.60,
    "freq_tolerance_hz": 700.0,
}

# Resumo simplificado e objetivo para exibição interna no diálogo Sobre / Notas de Atualização
CHANGELOG_SUMMARY = {
    "4.5.0": [
        "Arquitetura 4.5: extração de PlotRenderers, NavigationController, EditorController e AudioTransportPanel da MainWindow (Fases 3–7).",
        "FigureFactory: exportação de gráficos independente da janela em PNG e PDF multipágina (Fase 8).",
        "Diálogo de Exportação de Gráficos: escolha de painel, grade, marcadores, DPI e formato.",
        "Sinais PyQt desacoplados: UI comunica com controllers via sinais, eliminando chamadas diretas a métodos privados.",
        "Correção do ícone Play: inicialização garantida na criação do botão e atualização correta ao mudar tema.",
    ],
    "4.4.1": [
        "Correção Crítica do Auto-Updater: eliminação definitiva de travamento na mensagem 'Instalando'.",
        "Script em PowerShell Nativo: suporte completo a caminhos Unicode com acentuação e UTF-8 com BOM.",
        "Limpeza de Diretórios Legados: remoção automática de pastas corrompidas por versões anteriores.",
        "Fechamento Determinístico: liberação imediata de travas de arquivo para substituição limpa do executável."
    ],
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
    "4.5.0": [
        "Versão 4.5.0."
    ],
    "4.4.1": [
        "Correção Crítica de Emergência no Auto-Updater: eliminação definitiva do travamento da janela do Launcher na mensagem 'Instalando arquivos...'.",
        "Migração Completa do Atualizador para PowerShell: substituição do lote legada em cmd.exe (.bat) por script PowerShell (.ps1) nativo em UTF-8 com BOM (utf-8-sig), resolvendo de ponta a ponta erros de codificação com o nome 'Crinômetro'.",
        "Tratamento de Exceções e Resiliência na UI: inclusão de bloco try/except robusto no acionamento do instalador pelo launcher, impedindo que falhas silenciosas travem a interface gráfica.",
        "Normalização e Limpeza Automática: identificação e correção de diretórios corrompidos com caractere \ufffd criados por versões anteriores e expurgo automático da pasta legada após a instalação.",
        "Encerramento Determinístico com os._exit(0): finalização do processo pai para liberação imediata de todas as travas de arquivo no Windows, garantindo que o Inno Setup substitua o executável sem conflitos."
    ],
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
        "Filtro ICI Gate: expurgo automático de falsos positivos durante o período refratário fisiológico.",
        "Edição Precisa de Pulsos: snapping inteligente de marcadores e exportação de relatórios completos para publicação."
    ],
    "4.0.0": [
        "Segregação Bioacústica Avançada: separação inteligente de grilos focais vs. coro distante de fundo.",
        "Classificador Supervisionado: aprendizado de máquina em tempo real com árvore de decisão de alta velocidade."
    ],
    "3.5.1": [
        "Aprimoramento abrangente da árvore de aprendizado com conjunto de 14 descritores físicos invariantes a ganho.",
        "Mineração automática de amostras de ruído de fundo (negative background mining) e regularização do ensemble para eliminar desbalanceamentos.",
        "Filtro probabilístico e contextual de pulsos (Chirp-Aware Contextual Gating), garantindo que pulsos rítmicos nunca fragmentem chilreios.",
        "Normalização robusta de sinal em banda no pipeline DSP, imune a ruídos e impactos de baixa frequência (<100 Hz)."
    ],
    "3.5.0": [
        "Novo Launcher Animado: inicialização temática com mascote vetorial.",
        "Normalização Robusta: proteção DSP contra impactos e ruídos de baixa frequência."
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
        "Processamento Assíncrono: tarefas pesadas em background com loading spinner animado.",
        "Paleta Cromática de Pulsos: diferenciação visual de chilreios por contagem de pulsos."
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
