# -*- coding: utf-8 -*-
"""
Capítulo 1: Arquitetura de Software, Concorrência e Pipeline de Dados do Crinômetro v4.5.0.
"""

from reportlab.platypus import Paragraph, Spacer, PageBreak, Preformatted
from reportlab.lib.units import cm
from docs.sections.common import make_academic_table, make_glossary_box

def build_chapter1(S):
    story = []

    # =========================================================================
    # CAPÍTULO 1: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E PIPELINE
    # =========================================================================
    story.append(Paragraph("1.0. CAPÍTULO 1: ARQUITETURA DE SOFTWARE, CONCORRÊNCIA E PIPELINE DE DADOS", S["h1"]))
    story.append(Paragraph(
        "A versão 4.5.0 do Crinômetro consolida uma reestruturação profunda de engenharia de software, "
        "migrando de uma arquitetura acoplada centrada na janela principal para um padrão Model-View-Controller (MVC) "
        "desacoplado, governado pelo repositório reativo <code>SessionContext</code> e operando em concorrência assíncrona "
        "segura via <code>GenericWorker</code> e <code>WorkerRegistry</code>.",
        S["body"]
    ))

    # 1.1
    story.append(Paragraph("1.1. Topologia de Fluxo de Dados (Dataflow) e Pipeline Reativo", S["h2"]))
    story.append(Paragraph(
        "O pipeline segue um fluxo estritamente determinístico, imutável e unidirecional, desde a leitura de amostras brutas "
        "PCM do formato WAV (taxas de amostragem de 11.025 Hz a 384.000 Hz, quantizações de 16, 24 e 32 bits) "
        "até a persistência atômica e renderização gráfica acelerada por motores LoD:",
        S["body"]
    ))

    dataflow_ascii = (
        "  [ARQUIVO WAV] (11.025 a 384.000 Hz) --> Leitura e Validação (scipy.io.wavfile)\n"
        "        |\n"
        "        v\n"
        "  [CONDICIONAMENTO] --> Seleção RMS Estéreo (Evita Comb Filtering) + Remoção DC\n"
        "        |\n"
        "        v\n"
        "  [FILTRAGEM SOS] --> Passa-Altas 50 Hz (Vento) + Passa-Faixa Butterworth 4ª Ordem\n"
        "        |              (Filtro Bidirecional Zero-Phase: sosfiltfilt)\n"
        "        +-----------------------------------+\n"
        "        |                                   |\n"
        "        v                                   v\n"
        "  [DOMÍNIO DA FREQUÊNCIA]             [DOMÍNIO DO TEMPO]\n"
        "  • STFT Hann (N=1024, Hop=256)       • Transformada de Hilbert (FFT 5-suave)\n"
        "  • Refinamento Parabólico Sub-Bin    • Envoltória Suavizada e Normalizada P99.85\n"
        "  • Densidade Welch (PSD 50 ms)       • Limiar Adaptativo P25 x 2.5\n"
        "  • Frequência Portadora Modal fc     • Métricas de Pulso (-3 dB, -6 dB, IPI, PRR)\n"
        "        |                                   |\n"
        "        +-----------------+-----------------+\n"
        "                          |\n"
        "                          v\n"
        "  [AGRUPAMENTO SINTÁTICO & ML HÍBRIDO] --> 5 Camadas + Coerência O(N) + GMM / HistGradient\n"
        "                          |\n"
        "                          v\n"
        "  [SESSIONCONTEXT (SSOT)] --> batch_update() Atômico --> state_changed(category)\n"
        "        |                          |                          |\n"
        "        v                          v                          v\n"
        "  [PLOTRENDERERS]            [NAVIGATION]               [EXPORTCONTROLLER]\n"
        "  LoD Min-Max Blitting       Sync Eixos & Hover O(log M) Relatórios PDF & CSV"
    )
    story.append(Preformatted(dataflow_ascii, S["code"]))

    # 1.2
    story.append(Paragraph("1.2. Refatoração Arquitetural: Transição Monolito -> MVC Desacoplado", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A análise bioacústica profissional demanda o processamento de gravações contínuas de campo com durações de "
        "minutos a horas (frequentemente de 10 a 50 milhões de amostras de áudio). Em arquiteturas acopladas (onde a lógica "
        "de DSP reside na classe da janela principal), qualquer interação do usuário (como redimensionamento de janela ou "
        "ajuste de controles deslizantes) bloqueia o processamento numérico ou induz condições de corrida na leitura de buffers. "
        "O desacoplamento arquitetural isola a representação física do sinal acústico do ciclo de vida efêmero dos widgets gráficos.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O padrão Single Source of Truth (SSOT) estabelece que o estado compartilhado da aplicação reside unicamente na classe "
        "<code>SessionContext</code>. O grafo de dependências entre controladores é modelado como um Grafo Acíclico Direcionado (DAG). "
        "Para evitar disparos intermediários e inconsistências de renderização durante modificações coordenadas de múltiplos parâmetros, "
        "o sistema define uma transação em lote atômica. Se um conjunto de alterações gera um conjunto de sinais pendentes "
        "ΔS = {s_1, s_2, ..., s_k}, a notificação aos ouvintes é diferida até a saída do bloco transacional:",
        S["body"]
    ))
    story.append(Paragraph(
        "ΔS<sub>pending</sub> = união<sub>i</sub> S<sub>i</sub>, "
        "&nbsp;&nbsp;&nbsp;&nbsp; Emitir(S) &lt;=&gt; depth<sub>batch</sub> = 0",
        S["formula"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_12 = (
        "# core/session_context.py (SessionContext & batch_update)\n"
        "from contextlib import contextmanager\n"
        "from PyQt6.QtCore import QObject, pyqtSignal\n\n"
        "class SessionContext(QObject):\n"
        "    state_changed = pyqtSignal(str)\n\n"
        "    def __init__(self, parent=None):\n"
        "        super().__init__(parent)\n"
        "        self._batch_depth = 0\n"
        "        self._pending_state_changes = set()\n"
        "        self._active_heavy_data = {}\n"
        "        self._analysis_cache = {}\n\n"
        "    def emit_state_changed(self, category: str):\n"
        "        if getattr(self, '_batch_depth', 0) > 0:\n"
        "            self._pending_state_changes.add(category)\n"
        "            return\n"
        "        self.state_changed.emit(category)\n\n"
        "    @contextmanager\n"
        "    def batch_update(self):\n"
        "        self._batch_depth = getattr(self, '_batch_depth', 0) + 1\n"
        "        try:\n"
        "            yield self\n"
        "        except Exception:\n"
        "            if self._batch_depth == 1:\n"
        "                self._pending_state_changes.clear()\n"
        "            raise\n"
        "        finally:\n"
        "            self._batch_depth -= 1\n"
        "            if self._batch_depth == 0 and self._pending_state_changes:\n"
        "                pending = sorted(self._pending_state_changes)\n"
        "                self._pending_state_changes.clear()\n"
        "                for cat in pending:\n"
        "                    self.state_changed.emit(cat)"
    )
    story.append(Preformatted(code_12, S["code"]))
    story.append(Spacer(1, 4))

    mvc_headers = ["Dimensão de Engenharia", "Arquitetura v4.3.2 (Legada)", "Arquitetura v4.5.0 (Produção Desacoplada)"]
    mvc_rows = [
        ["Gerenciamento de Estado", "Disperso em variáveis de MainWindow", "Centralizado no SessionContext (core/session_context.py)"],
        ["Sincronização de Threads", "Threads soltas sem barramento comum", "Pool monitorado por WorkerRegistry com cancelamento cooperativo"],
        ["Comunicação de Módulos", "Invocação direta de métodos de UI", "Sinais fracos PyQt6: state_changed(category)"],
        ["Atomicidade de Atualizações", "Atribuições sequenciais parciais", "Context Manager transacional batch_update() com bloqueio de sinais"],
        ["Gravação de Preferências", "open('w') direto sem flush", "Write-Ahead Tempfile + Fsync + Atomic Replace (persistence.py)"],
        ["Serialização de Modelos ML", "Pickle binário inseguro (.pkl)", "Formato seguro .skops com auditoria estática de AST"],
        ["Estimativa Térmica", "Fórmula empírica de Dolbear acoplada", "TOTALMENTE EXPURGADA (Metrologia Pura de Novas Espécies)"]
    ]
    story.append(make_academic_table(mvc_headers, mvc_rows, S, col_widths=[3.5*cm, 6.5*cm, 7.0*cm]))
    story.append(Spacer(1, 6))

    # 1.3
    story.append(Paragraph("1.3. Concorrência Assíncrona: GenericWorker e WorkerRegistry Monotônico", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "A extração de atributos espectrais e temporais (como a Transformada de Hilbert e o cálculo da matriz STFT) "
        "envolve trilhões de operações de ponto flutuante. A execução síncrona na thread principal do Qt congelaria a "
        "interface por vários segundos, impedindo a visualização responsiva e interrompendo a interação de campo. "
        "A versão 4.5.0 delega todo o processamento computacionalmente denso para instâncias assíncronas de <code>QThread</code>.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O cancelamento de operações adota uma barreira atômica de memória (<code>threading.Event()</code>) consultada a cada etapa "
        "do pipeline. No encerramento da aplicação, para evitar a falha crítica de ponteiro solto (<i>dangling pointer</i>) do Qt "
        "<code>QThread: Destroyed while thread is still running</code>, o <code>WorkerRegistry</code> calcula um <i>deadline</i> monotônico "
        "baseado no relógio de hardware do sistema (imune a saltos NTP do sistema operacional):",
        S["body"]
    ))
    story.append(Paragraph(
        "t<sub>deadline</sub> = t<sub>monotonic</sub> + (T<sub>max</sub> / 1000), "
        "&nbsp;&nbsp;&nbsp;&nbsp; Δt<sub>rem</sub>(w<sub>i</sub>) = max(50 ms, floor((t<sub>deadline</sub> - t<sub>monotonic</sub>) × 1000))",
        S["formula"]
    ))
    story.append(Paragraph(
        "Onde T<sub>max</sub> = 3000 ms representa o tempo limite global concedido a todas as threads ativas combinadas.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_13 = (
        "# core/worker.py (GenericWorker & WorkerRegistry)\n"
        "class GenericWorker(QThread):\n"
        "    finished_signal = pyqtSignal(object)\n"
        "    cancelled_signal = pyqtSignal()\n"
        "    error_signal = pyqtSignal(str)\n\n"
        "    def __init__(self, target_fn, *args, **kwargs):\n"
        "        super().__init__()\n"
        "        self.target_fn = target_fn\n"
        "        self.args = args\n"
        "        self.kwargs = kwargs\n"
        "        self._abort_event = threading.Event()\n\n"
        "    def abort(self):\n"
        "        self._abort_event.set()\n\n"
        "    def run(self):\n"
        "        try:\n"
        "            res = self.target_fn(*self.args, **self.kwargs)\n"
        "            if not self._abort_event.is_set():\n"
        "                self.finished_signal.emit(res)\n"
        "            else:\n"
        "                self.cancelled_signal.emit()\n"
        "        except Exception as exc:\n"
        "            if not self._abort_event.is_set():\n"
        "                self.error_signal.emit(str(exc))\n"
        "            else:\n"
        "                self.cancelled_signal.emit()\n\n"
        "class WorkerRegistry:\n"
        "    def wait_all(self, timeout_ms=3000):\n"
        "        deadline = time.monotonic() + (timeout_ms / 1000.0)\n"
        "        with self._lock:\n"
        "            snapshot = list(self._workers)\n"
        "        for w in snapshot:\n"
        "            if w.isRunning():\n"
        "                rem_ms = max(50, int((deadline - time.monotonic()) * 1000))\n"
        "                w.wait(rem_ms)"
    )
    story.append(Preformatted(code_13, S["code"]))
    story.append(Spacer(1, 4))

    # 1.4
    story.append(Paragraph("1.4. Persistência Transacional Atômica: Write-Ahead e Fsync", S["h2"]))
    story.append(Paragraph("[BLOCO A: FUNDAMENTOS FÍSICOS E BIOACÚSTICOS]", S["h3"]))
    story.append(Paragraph(
        "Expedições biológicas frequentemente utilizam computadores portáteis sujeitos a esgotamento repentino de bateria "
        "ou desconexões acidentais. Uma operação de salvamento de parâmetros taxonômicos interrompida no meio da escrita "
        "em disco corromperia permanentemente o arquivo de configuração e os modelos treinados. "
        "O Crinômetro implementa gravação transacional com integridade garantida em hardware.",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO B: FORMULAÇÃO MATEMÁTICA E ESTATÍSTICA]", S["h3"]))
    story.append(Paragraph(
        "O protocolo segue rigorosamente a semântica ACID para sistemas de arquivos: "
        "<i>(1)</i> Cópia de segurança imediata para <code>filepath.bak</code>; "
        "<i>(2)</i> Criação de arquivo temporário oculto via <code>tempfile.mkstemp</code> estritamente no mesmo diretório/volume "
        "(garantindo que o descritor de arquivo pertença ao mesmo inode/MFT); "
        "<i>(3)</i> Descarga forçada de todos os buffers do kernel para os pratos magnéticos ou células NAND flash via <code>os.fsync(fd)</code>; "
        "<i>(4)</i> Troca atômica de ponteiro de diretório no nível do sistema operacional via <code>os.replace</code> (operação atômica POSIX e Win32).",
        S["body"]
    ))

    story.append(Paragraph("[BLOCO C: ARQUITETURA E IMPLEMENTAÇÃO DE CÓDIGO (v4.5.0)]", S["h3"]))
    code_14 = (
        "# utils/persistence.py (atomic_write & quarantine_corrupted)\n"
        "def atomic_write(filepath: str, content: bytes):\n"
        "    bak_path = filepath + '.bak'\n"
        "    if os.path.exists(filepath):\n"
        "        try:\n"
        "            shutil.copy2(filepath, bak_path)\n"
        "        except Exception as e:\n"
        "            logger.warning(f'Falha ao criar backup de {filepath}: {e}')\n"
        "    dir_name = os.path.dirname(filepath)\n"
        "    os.makedirs(dir_name, exist_ok=True)\n"
        "    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix='.' + os.path.basename(filepath), suffix='.tmp')\n"
        "    try:\n"
        "        with os.fdopen(fd, 'wb') as f:\n"
        "            f.write(content)\n"
        "            f.flush()\n"
        "            os.fsync(f.fileno())  # Descarga compulsória de hardware\n"
        "        os.replace(temp_path, filepath)  # Transação atômica de SO\n"
        "    except Exception as e:\n"
        "        logger.error(f'Erro na escrita atômica para {filepath}: {e}')\n"
        "        if os.path.exists(temp_path):\n"
        "            os.remove(temp_path)\n"
        "        raise"
    )
    story.append(Preformatted(code_14, S["code"]))
    story.append(Spacer(1, 4))

    # Glossário Seção 1
    g1_items = [
        ("G-01", "Single Source of Truth (SSOT)", "Repositório centralizado (SessionContext) que detém a verdade exclusiva do estado da aplicação, eliminando divergências entre controladores."),
        ("G-02", "Transação Atômica em Batch", "Mecanismo que acumula alterações de estado e atrasa a emissão de sinais gráficos até a conclusão total do bloco de modificações."),
        ("G-03", "Cancelamento Cooperativo", "Protocolo seguro onde a thread consulta periodicamente uma flag atômica (abort_event) e finaliza sua execução sem corrupção de ponteiros."),
        ("G-04", "Deadline Monotônico", "Temporizador absoluto baseado no clock de hardware do sistema (time.monotonic), imune a ajustes e desvios de relógio do sistema operacional."),
        ("G-05", "Substituição Atômica (os.replace)", "Operação atômica em nível de sistema de arquivos POSIX/NTFS que troca o descritor de arquivo garantindo que arquivos incompletos nunca sejam lidos.")
    ]
    story.append(make_glossary_box("§1.0 - §1.4", g1_items, S))
    story.append(PageBreak())

    return story
