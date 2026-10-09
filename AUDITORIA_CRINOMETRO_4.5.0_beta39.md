# Auditoria técnica — Crinômetro 4.5.0 beta (beta39)

## Método e limites (leia primeiro)

- Li integralmente: `core/` (worker, analyzer, engines, learner, updater, session_context), `utils/helpers.py`, `utils/constants.py`, `ui/controllers/pipeline_orchestrator.py`, `export_controller.py`, `editor_controller.py` (persistência/aprendizado), `ui/update_dialog.py`, trechos de `ui/main_window.py` (ciclo de vida, config, lote), `figure_factory.py`, `export_graph_dialog.py`, `scripts/quality_gate.py`, a lista e as amostras dos testes.
- **Executado de verdade** (numpy/scipy/matplotlib no sandbox): o `CricketAnalyzer` com sinais sintéticos, a sobrescrita do TXT e a poda de amostras do learner. Esses achados estão marcados **[EXEC]**.
- **Não consegui rodar a GUI nem a suíte de 65 testes**: `PyQt6` e `skops` não instalam no ambiente. Tudo marcado **[LEITURA]** vem de leitura do código. Os de concorrência Qt são deduções do fluxo de chamadas e precisam de confirmação no seu Windows.
- O código usa **PyQt6**, não PySide6 (`pyqtSignal`, cancelamento por `threading.Event` próprio, não `requestInterruption`). Adaptei os eixos de acordo.
- Não li linha a linha: `ui/panels.py`, `navigation_controller.py`, `plot_renderers.py` (só limpeza de timers), `utils/styles.py`, `i18n.py`, `icons.py`, os diálogos de tema, o launcher (só o trecho do updater) e `generate_docs*`. Não afirmo nada sobre eles.

---

## 1. Relatório executivo

| Item | Veredito |
|---|---|
| Qualidade técnica | **60 / 100** |
| Risco para release | **ALTO** (estabilidade/concorrência e integridade de exportação). Risco metrológico: **Moderado**. |

O núcleo DSP é sólido. Usa SOS com `sosfiltfilt`, tem pisos de log e normalização robusta, e no sinal sintético recuperou 160/160 pulsos e 40/40 chilreios. O ML usa `skops` com lista de tipos confiáveis explícita, não `trusted=True`. O updater exige SHA-256 por padrão e tem timeouts. A exportação de gráficos tem ciclo de vida de worker correto.

O que reprova o release está em volta do DSP:
1. A concorrência Qt tem janelas reais de crash: `QThread` sobrescrito enquanto roda e nenhum `closeEvent`.
2. O **relatório TXT sai corrompido** (reproduzido).
3. O script do auto-updater usa cmdlets PowerShell **inexistentes**, e a validação de hash dele nunca roda.
4. O ML tem vazamento de rótulo entre treino e inferência, e falha em silêncio.
5. Entrada inválida (NaN, taxa baixa) gera resultado errado **sem aviso**.

`docs/AUDITORIA_GERAL.md` declara "0 vazamentos… robusto, estável e homologado". Isso não se sustenta frente aos achados abaixo.

**Hipótese que testei e descartei:** suspeitei que `amp_max=1.0` descartava os pulsos mais altos (envelope normalizado pelo percentil 99,85). Falso. O envelope máximo ficou em ~0,8 e o resultado não mudou com `amp_max=5` **[EXEC]**. Mas há uma limitação real: com crescendo de 15 dB, 9 de 40 chilreios (os mais fracos) foram perdidos, porque o limiar é absoluto sobre normalização global **[EXEC]**. Isso é desenho, não bug. Merece aviso no relatório científico.

---

## 2. Matriz de bugs

Severidade: **C** crítico, **A** alto, **M** médio, **B** baixo.

### A. Concorrência e ciclo de vida

#### A1 (A) `QThread` sobrescrito enquanto roda → "Destroyed while thread is still running" [LEITURA]
- **Local:** `pipeline_orchestrator.py` → `force_reanalyze` (atribui `self._reanalyze_worker = worker` sem checar `isRunning()`). O mesmo padrão está em `editor_controller.py::learn_from_corrections` (`_learn_worker`) e `export_controller.py::_generate_pdf_report_modular` (`_report_worker`). `main_window.py` chama `force_reanalyze` sem guarda nas linhas ~1624, 1687, 1752 e 1795 (mudar parâmetros, importar modelo, reset).
- **Cenário:** o usuário clica em "✕ Abortar" durante uma reanálise. `abort()` só seta a flag, e `analyze()` não a consulta, então a thread continua rodando por segundos. Ele muda um parâmetro ou importa um modelo, o que chama `force_reanalyze` de novo. A referência ao worker antigo é descartada, o wrapper Python é coletado e o objeto C++ é destruído com a thread viva. Resultado: abort/crash.
- **Impacto:** crash do aplicativo, perda das correções não salvas.
- **Correção** (em `PipelineOrchestrator`):

```python
# __init__
self._retained_workers = set()

def _retain(self, worker):
    """Mantém referência forte até a thread terminar de fato (mesmo após abort)."""
    self._retained_workers.add(worker)
    worker.finished.connect(lambda w=worker: self._retained_workers.discard(w))

def shutdown(self, timeout_ms=8000):
    """Chamado no closeEvent: aborta e aguarda todos os workers."""
    pending = list(self._retained_workers)
    for w in pending:
        w.abort()
    for w in pending:
        w.wait(timeout_ms)

# run_batch_analysis e force_reanalyze: logo após criar o worker
worker = GenericWorker(_task)
self._retain(worker)

# force_reanalyze: no início, antes de mudar active_filename
if self._reanalyze_worker is not None and self._reanalyze_worker.isRunning():
    return False
```

Aplique `_retain` também a `_learn_worker` e `_report_worker`. Faça os callers de `force_reanalyze` tratarem o retorno `False` (avisar na barra de status ou enfileirar).

#### A2 (A) `MainWindow` não tem `closeEvent` [LEITURA]
- **Local:** `main_window.py`. O `grep` mostra `closeEvent` só no launcher e no diálogo de exportação.
- **Cenário:** fechar a janela com lote, reanálise, treino ou relatório em curso.
- **Impacto:** "QThread: Destroyed while thread is still running" ou segfault no encerramento. As correções feitas desde o último save são perdidas, porque `save_settings` só é chamado em ações pontuais.
- **Correção:**

```python
def closeEvent(self, event):
    try:
        self.save_settings(silent=True)
    except Exception:
        pass
    try:
        self.pipeline.shutdown(timeout_ms=8000)
    except Exception:
        pass
    chk = getattr(self, "_checker_thread", None)
    if chk is not None and chk.isRunning():
        chk.wait(9000)          # urlopen tem timeout de 8 s
    for t in (self.playback_timer,):
        try:
            t.stop()
        except Exception:
            pass
    super().closeEvent(event)
```

Isso só funciona bem com o cancelamento cooperativo de A3.

#### A3 (A) Abort não interrompe `analyze()`; reiniciar lote depois do abort trava a UI [LEITURA]
- **Local:** `analyzer.py::analyze` (nenhum ponto de checagem), `pipeline_orchestrator.py::run_batch_analysis` e `abort_current_analysis`, `main_window.py::analyze_selected_audios` (~l.1423) e `export_controller.py::_start_batch_for_export` (l.52).
- **Cenário:**
  1. O usuário aborta um lote.
  2. `batch_cancelled` é emitido na hora e a UI reabilita `btn_analyze_selected`.
  3. A thread antiga continua (`isRunning()` ainda é True).
  4. O usuário clica em Analisar. `run_batch_analysis` devolve `False` em silêncio.
  5. A UI já desabilitou o botão e ligou o spinner, e nenhum sinal de fim chega: botão e spinner ficam presos para sempre.
  - O mesmo vale para exportar PDF/TXT com arquivos pendentes: `_pending_export_action` fica armado e o spinner nunca para.
- **Impacto:** UI travada até reiniciar o app.
- **Correção:**
  1. Passe `should_abort` ao analisador (código abaixo).
  2. Emita `batch_cancelled` só quando a thread realmente terminar.
  3. Trate o retorno de `run_batch_analysis`.

```python
# analyzer.py
class AnalysisAborted(Exception):
    pass

@staticmethod
def analyze(file_path, params, pulse_learner=None, cached_spec=None, should_abort=None):
    def _chk():
        if should_abort is not None and should_abort():
            raise AnalysisAborted()
    ...
    _chk()   # após wavfile.read
    _chk()   # após sosfiltfilt do DC
    _chk()   # após band-pass + hilbert
    _chk()   # após spectrogram
    _chk()   # após find_peaks/peak_widths
    _chk()   # antes do ML (filter_peaks)
    ...

# pipeline_orchestrator.py (batch)
res = CricketAnalyzer.analyze(fpath, effective_params, pulse_learner=learner,
                              should_abort=lambda: worker.abort_requested)
...
except AnalysisAborted:
    break
except Exception as exc:
    errors.append(f"{fname}: {exc}")

# abort_current_analysis: não emitir batch_cancelled aqui.
# No _task, ao sair por abort:   worker.cancelled_signal.emit()
# Conecte cancelled_signal -> self.batch_cancelled (e analysis_cancelled).

# run_batch_analysis: só emitir batch_started depois de confirmar o início
if self._batch_worker and self._batch_worker.isRunning():
    return False
...
worker.start()
self.batch_started.emit(len(checked_files))
return True

# main_window.analyze_selected_audios e ExportController._start_batch_for_export
# devem checar o retorno e desfazer spinner, loading e _pending_export_action se for False.
```

Em `GenericWorker`, adicione `cancelled_signal = pyqtSignal()` e emita-o em `run()` quando `_abort_event` estiver setado ao terminar.

#### A4 (A) Corrida no `PulseLearner` entre worker e GUI [LEITURA]
- **Local:** `learner.py::update_from_corrections` (`self.model = self._build_model(...)` e só depois `self.model.fit(...)`). É chamado em worker thread por `force_reanalyze._task` e `learn_from_corrections._task`. A GUI thread usa o mesmo objeto em `_execute_realtime_freq_tolerance` → `reevaluate_carrier_tolerance` → `filter_peaks`.
- **Cenário:** o usuário arrasta o slider de tolerância (timer de 25 ms) enquanto o treino roda. Por um instante `self.model` é um classificador **não ajustado**. `predict_proba` lança `NotFittedError` e o `except Exception` de `filter_peaks` devolve `peaks, []`, isto é, **"aceita todos os picos"**, sem avisar. `_adapt_advanced_params` também altera `ctx._adaptive_overrides` fora da GUI thread.
- **Impacto:** contagem de chilreios incorreta, silenciosa e não reprodutível.
- **Correção:**

```python
# __init__
self._model_lock = threading.RLock()     # import threading

# update_from_corrections: treinar fora do lock e trocar de forma atômica
new_model = self._build_model(n_samples=len(self.training_labels))
new_model.fit(self.training_features, self.training_labels)
with self._model_lock:
    self.model = new_model
self.save_persisted_training()

# fit(): idem (construir local, ajustar, trocar sob lock)

# filter_peaks / predict: capturar o modelo uma única vez
with self._model_lock:
    model = self.model
    rules = list(getattr(self, "pruning_rules", []))
# ... usar `model` e `rules` locais no resto da função
```

#### A5 (M) Botão de lote: spinner nunca é parado [LEITURA]
- **Local:** `main_window.py` l.1418-1420 cria `ButtonSpinner`. `_on_batch_completed`, `_on_batch_failed` e `_on_batch_cancelled` nunca chamam `stop()`.
- **Impacto:** o ícone de `btn_analyze_selected` gira para sempre (timer de 50 ms gerando `QIcon` a cada tick) e o texto fica em "Analisando... (n/n)". Há CPU contínua e UI enganosa.
- **Correção:** nos três handlers:

```python
sp = getattr(self, "_batch_spinner", None)
if sp is not None:
    sp.stop(restore_text=I18N[self.lang]["analyze_selected"])
    self._batch_spinner = None
```

#### A6 (M) `sys.excepthook` abre `QMessageBox` de qualquer thread [LEITURA]
- **Local:** `helpers.py::handle_exception`.
- **Cenário:** uma exceção não tratada fora da GUI thread constrói um widget em outra thread. Uma exceção repetida em `paintEvent`/timer empilha diálogos modais.
- **Correção:**

```python
from PyQt6.QtCore import QThread
...
app = QApplication.instance()
if app is None or QThread.currentThread() is not app.thread():
    sys.__excepthook__(exc_type, exc_value, exc_traceback)   # só loga
    return
if getattr(handle_exception, "_busy", False):
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    return
handle_exception._busy = True
try:
    ...  # QMessageBox como hoje
finally:
    handle_exception._busy = False
```

Aproveite para remover o efeito colateral de `setup_global_exception_handler()` chamado no import de `helpers.py` (l.41) e o `APP_VERSION = "4.3.0"` obsoleto do mesmo arquivo. A versão canônica é a de `constants.py`.

### B. DSP e rigor científico

#### B1 (A) Áudio com NaN/Inf passa sem erro e produz resultado lixo [EXEC]
- **Local:** `analyzer.py::analyze`, logo após `wavfile.read`. Só há checagem de vazio e de silêncio.
- **Cenário:** WAV float32 com um único NaN (comum em gravadores/conversores com bug).
- **Resultado medido:** nenhuma exceção, `env` não finito, 0 chilreios e `carrier_freq=3230`. O relatório sai com "0 chilreios" aparentemente legítimos.
- **Correção:** substitua o trecho inicial de `analyze` por:

```python
@staticmethod
def _load_mono(file_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", WavFileWarning)
        rate, raw = wavfile.read(file_path)
    if rate <= 0:
        raise ValueError(f"Taxa de amostragem inválida: {rate}")
    raw = np.asarray(raw)
    if raw.size == 0:
        raise ValueError("O arquivo de áudio está vazio.")
    if raw.ndim > 1:
        data = raw.astype(np.float64)
        if not np.isfinite(data).all():
            raise ValueError("O arquivo contém valores NaN/Inf.")
        # canal de maior energia em vez de descartar silenciosamente os demais
        rms = np.sqrt(np.mean(data ** 2, axis=0))
        data = data[:, int(np.argmax(rms))]
    else:
        data = raw.astype(np.float64)
    if not np.isfinite(data).all():
        raise ValueError("O arquivo contém valores NaN/Inf.")
    return int(rate), data
```

#### B2 (A) Taxa de amostragem baixa colapsa a banda em silêncio [EXEC]
- **Local:** `analyze`, bloco de `b1_min/b1_max` (l.66-72).
- **Cenário:** WAV de 6 kHz com sinal de 2,8 kHz. Os padrões 3200–6000 Hz ficam acima de Nyquist, e o código substitui a banda por uns ~20 Hz de largura perto de Nyquist. Resultado medido: **0/15 chilreios, `carrier_freq=2971`**, sem erro. Com 8 e 16 kHz e sinal dentro da banda, funcionou (15/15).
- **Impacto:** erro metrológico silencioso.
- **Correção:** falhe com mensagem clara, em vez de remendar.

```python
b1_max = min(nyq - 20.0, float(params.get("b1_max", 6000)))
b1_min = max(20.0, float(params.get("b1_min", 3200)))
if b1_max - b1_min < 100.0:
    raise ValueError(
        f"Taxa de amostragem de {rate} Hz incompatível com a banda configurada "
        f"({b1_min:.0f}–{float(params.get('b1_max', 6000)):.0f} Hz; Nyquist = {nyq:.0f} Hz). "
        f"Ajuste b1_min/b1_max ou use uma gravação com taxa maior."
    )
```

#### B3 (M) Espectrograma e PSD calculados sobre sinal já recortado (clip) [LEITURA]
- **Local:** `analyze`, `data = np.clip(data / raw_scale, -1.0, 1.0)` (l.90), seguido de `spectrogram(data, ...)` e `compute_psd(data, ...)`.
- **Impacto:** 0,1% das amostras mais altas é saturada, o que gera distorção harmônica de banda larga. Isso afeta `Sxx_db`, `dom_freqs` (refinamento parabólico) e o PSD publicado. O dB é relativo ao percentil, não absoluto. Isso deve constar no relatório.
- **Correção:** calcule o espectro sobre `data_norm = data / raw_scale` **sem clip**. Use o clip só para o gráfico da forma de onda.

#### B4 (M) Sem limite de duração/memória [LEITURA]
- **Local:** `analyze`. São várias cópias float64 (`data`, `data - mean`, `sosfiltfilt`, `data_b1`, `hilbert` complexo). Uma gravação de 1 h a 44,1 kHz tem ~158 M amostras, ou ~1,2 GB por array e ~2,5 GB só no sinal analítico.
- **Correção:** guarde a duração máxima (ex.: 20 min) com erro claro, ou processe em blocos. Use `scipy.fft.next_fast_len` no `hilbert` (`hilbert(x, N=next_fast_len(len(x)))[:len(x)]`) para evitar FFT lenta em comprimentos primos.

#### B5 (M) `analysis_cache` sem limite [LEITURA]
- **Local:** `_apply_analysis_results`. Cada arquivo guarda `data`, `data_b1`, `env` e `Sxx_db` (~50 MB para 60 s a 44,1 kHz). Num lote de 100 arquivos são ~5 GB, sem evicção.
- **Correção:** LRU de N arquivos pesados (ex.: 10). Para os demais, mantenha só métricas (chirps, picos, params), que são o que o relatório usa, e reanalise sob demanda. Proteja da evicção os arquivos de uma exportação pendente.

#### B6 (B) LoD preserva transientes só no oscilograma [LEITURA]
- **Local:** `engines.py`.
- **OK:** `HighPerfLineEngine._get_envelope` usa min/max por bloco e preserva picos.
- **Ressalvas:**
  - descarta o resto da divisão (`y[:block_size*num_blocks]`), ou seja, até `block_size-1` amostras no fim da janela;
  - `HighPerfSpectrogramEngine.render_interactive` e `HighPerfFreqEngine` decimam por passo fixo (`::lod_step`), e o mesmo passo é aplicado ao eixo de frequência. Na visão total, pulsos de 14 ms (~2 colunas) podem sumir na pré-visualização até o refinamento de 200 ms;
  - os `QTimer()` dos engines não têm parent.
- **Correção mínima:** use `reduceat` ou `max`-pooling por bloco no espectrograma (`np.maximum.reduceat`) e inclua o bloco final parcial.

#### B7 (B) Gráficos/Matplotlib
Bom: `figure_factory` usa `Figure()` sem pyplot, com `fig.clf()` em `finally`, e há teste de vazamento por weakref. `render_dashboard` interrompe os debounce timers antes de recriar. Nada a corrigir aqui.

### C. Machine Learning e serialização

**Pontos fortes:**
- `skops` com lista explícita de tipos confiáveis, nunca `trusted=True`.
- A migração do `.pkl` legado é restrita.
- O teste `test_persistence_skops` cobre o ciclo completo (não consegui executá-lo).
- A escrita do `.skops` é atômica (`.tmp` + `os.replace`).

#### C1 (A) Vazamento de rótulo: `prior_p_focal` [LEITURA]
- **Local:** `learner.py::build_training_matrix`. Os negativos minerados usam `prior_p_focal=0.0` fixo. Os positivos usam o prior do GMM, ou `1.0` quando há menos de 10 picos. Na inferência (`filter_peaks`) o prior vem do GMM da própria gravação.
- **Impacto:** a feature nº 20 vira atalho. `prior == 0` ⇒ negativo, algo que nunca existe na inferência. O modelo parece ótimo em treino e se comporta de modo diferente em campo. Além disso o prior entra duas vezes: como feature e em `combined_score = 0.65*p + 0.35*prior`.
- **Correção:** o prior deve entrar só na combinação final.
  1. Remova `prior_p_focal` do vetor de features do modelo (19 features), mantendo `priors` apenas em `combined_score`.
  2. Grave `feature_names` e uma `schema_version` no payload.
  3. No carregamento, invalide modelos com `feature_names` diferentes em vez de truncar/preencher com zeros (C3).

#### C2 (M) Falhas de ML são silenciosas e a UI continua dizendo "IA Supervisionada" [LEITURA]
- **Local:** `filter_peaks` (`except Exception: return peaks, []`), `predict`, `load_persisted_training` (`except: return False`), `load_from_config` e os muitos `pass  # print(...)`.
- **Cenário:** atualizar o scikit-learn, ou um `.skops` truncado, faz o modelo falhar. O pipeline passa a aceitar todos os picos e o rótulo da UI continua dizendo que o modelo supervisionado está ativo.
- **Correção:** registre com `logging` (arquivo rotativo em pasta de usuário) e exponha `learner.last_error`/`learner.degraded`. A UI deve mostrar "IA indisponível — usando DSP". Ao falhar a leitura de um arquivo persistido, **renomeie para `.corrupt-<timestamp>`** em vez de sobrescrever depois.

#### C3 (M) Alinhamento de features por truncar/preencher com zero [LEITURA]
- **Local:** `predict` e `filter_peaks`. Se o modelo espera N≠20 features, o código corta ou preenche com zeros sem comparar `feature_names`. O payload guarda `feature_names`, mas ninguém o valida.
- **Correção:**

```python
def _features_compatible(self, payload_names):
    return list(payload_names or []) == list(self.feature_names)
# load_persisted_training / import_model_file / load_from_config:
if not self._features_compatible(payload.get("feature_names")):
    raise ValueError("Modelo incompatível com o conjunto atual de features; re-treine.")
```

#### C4 (M) Truncagem de amostras mantém as erradas [EXEC]
- **Local:** `update_from_corrections`. `np.unique(..., axis=0)` ordena as linhas pelo valor da 1ª feature. O código então faz `[-5000:]` pensando em "as mais recentes". Medido: o resultado mantém as de **maior** `peak_amp_rel`.
- **Correção:**

```python
stacked = np.column_stack((X, y))
_, first_idx = np.unique(stacked, axis=0, return_index=True)
stacked = stacked[np.sort(first_idx)]            # deduplica preservando a ordem cronológica
self.training_features = stacked[:, :-1]
self.training_labels = stacked[:, -1].astype(int)
if len(self.training_labels) > _MAX_SAMPLES:
    self.training_features = self.training_features[-_MAX_SAMPLES:]
    self.training_labels = self.training_labels[-_MAX_SAMPLES:]
```

#### C5 (B) Outras observações de ML [LEITURA]
- `load_persisted_training` descarta um modelo válido e **zera os dados de treino em memória** se houver menos de 10 negativos, o que contradiz o `_build_model` para poucas amostras e pode apagar dados no próximo save.
- Os positivos são todos os picos detectados e não removidos, ou seja, não revisados contam como verdade. Há risco de realimentação (confirmation bias). Documente.
- O GMM sempre ajusta 2 componentes. Com um único grilo (unimodal) ele parte os pulsos em "focal/distante". O resgate contextual mitiga, mas isso deve ser documentado.

### D. Estado, configuração e persistência

#### D1 (A) `CONFIG_FILE` é caminho relativo ao diretório de trabalho [LEITURA]
- **Local:** `constants.py` (`CONFIG_FILE = "crinometro_config.json"`). `PulseLearner.persistence_path` deriva dele.
- **Cenário:** abrir pelo atalho do instalador (CWD pode ser `System32`, `Program Files` ou outra pasta). A configuração e o modelo vão para onde estiver o CWD, ou falham silenciosamente por falta de permissão em `Program Files`, e `save_settings(silent=True)` engole o erro. **As correções do usuário se perdem.**
- **Correção:**

```python
import os, shutil

def _user_config_dir():
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
```

Ajuste o script do updater, que hoje procura `*.json` na pasta de instalação.

#### D2 (A) Gravação não atômica em `save_settings`, `reset` e `PulseLearner.save_to_config/reset` [LEITURA]
- **Local:** `main_window.py` l.1785 e l.1913; `learner.py` l.832 e l.1026. Só `editor_controller.save_corrections_state` e `save_persisted_training` usam `tempfile` + `os.replace`.
- **Impacto:** crash ou queda de energia durante a escrita deixa o JSON truncado. No próximo boot `load_settings` falha em silêncio e `save_corrections_state` devolve `False` para sempre ("config corrompida"), perdendo as correções.
- **Correção:** um único helper em `utils/`, usado em todos os pontos:

```python
import json, os, tempfile

def atomic_write_json(path, obj):
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".cfg-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
```

Em `save_corrections_state`, se o JSON existente estiver corrompido, mova-o para `.corrupt-<ts>` e continue gravando em vez de `return False`.

#### D3 (M) Parâmetros lidos do JSON sem validação [LEITURA]
- **Local:** `load_settings` (`self.ctx.algo_params.update(data["algo_params"])`).
- **Impacto:** `"b1_min": "abc"` ou `"min_p": 0` chegam ao analisador e quebram só na hora da análise.
- **Correção:** valide tipo e faixa contra `DEFAULT_ALGO_PARAMS` e ignore o que não passar.

#### D4 (M) Rastreabilidade: os parâmetros do relatório não incluem as sobreposições adaptativas [LEITURA]
- **Local:** `_apply_analysis_results`. `"params": params.copy()`, mas a análise usou `{**params, **_adaptive_overrides}`. `run_batch_analysis` passa `params=params` (sem overrides) para `_on_single_result`, e `force_reanalyze._on_finished` chama `_apply_analysis_results(filename, results)` com `params=None`.
- **Impacto:** o relatório exibe parâmetros diferentes dos efetivamente usados. Além disso `_adapt_advanced_params` desloca `prominence`/`width_min_ms` a cada reanálise (média móvel), então **reanalisar duas vezes o mesmo áudio com as mesmas correções dá resultados diferentes**.
- **Correção:** grave os parâmetros efetivos e as sobreposições.

```python
# _apply_analysis_results
overrides = dict(self.ctx._adaptive_overrides)
effective_params = {**params, **overrides}
heavy_data["params"] = effective_params.copy()
heavy_data["adaptive_overrides"] = overrides
# run_batch_analysis: passar effective_params (já calculado no início) a _on_single_result
# force_reanalyze: passar effective_params a _apply_analysis_results
```

Torne a adaptação idempotente: calcule a partir dos valores-base persistidos, não do valor atual.

#### D5 (M) `_apply_analysis_results` deixa métricas obsoletas com menos de 2 picos [LEITURA]
- **Local:** `pipeline_orchestrator.py` l.217-228. Se após as correções restarem menos de 2 picos efetivos, `regroup_chirps` não é chamado e `chirps/media/moda` permanecem os da detecção original. Além disso, há `except Exception: pass`.
- **Correção:**

```python
if len(effective_peaks) >= 2:
    chirps, chirp_peaks_list, media, moda, variancia = CricketAnalyzer.regroup_chirps(
        effective_peaks, effective_params, rate, env, raw_signal=data_b1)
else:
    chirps, chirp_peaks_list, media, moda, variancia = [], [], 0.0, 0, 0.0
```

#### D6 (B) `SessionContext.batch_update` descarta notificações quando há exceção [LEITURA]
- **Local:** `session_context.py` l.63-65. As atribuições já foram feitas, mas `_pending_state_changes.clear()` apaga os avisos. A UI fica dessincronizada do estado real.
- **Correção:** remova o `clear()` no ramo de exceção. Emita o que foi alterado e propague a exceção.

### E. Auto-update e segurança operacional

#### E1 (A) O script PowerShell usa cmdlets que não existem [LEITURA + conhecimento do PowerShell]
- **Local:** `updater.py::launch_windows_updater`: `Test-LiteralPath`, `Split-LiteralPath`, `Join-LiteralPath`. Os reais são `Test-Path -LiteralPath`, `Split-Path -LiteralPath` e `Join-Path`. Não pude executar PowerShell no sandbox, mas esses três nomes não existem.
- **Efeito:**
  - A verificação de SHA-256 **dentro do PowerShell nunca executa** (a condição do `if` falha e o script segue). Resta só a checagem em Python antes do disparo, com janela TOCTOU num diretório temporário previsível e gravável pelo usuário.
  - A migração/limpeza de pastas legadas (`Crinômetro`) **nunca funciona**, apesar de constar no changelog 4.4.1.
  - A limpeza do `.bat` também falha.
- **Por que os testes não pegam:** `test_powershell_syntax_validation` só usa o `Parser::ParseFile`, que valida sintaxe e não resolve nomes de comando. O teste também exige `powershell.exe`.

#### E2 (M) Caminhos com apóstrofo quebram o script e a aplicação já foi encerrada [LEITURA]
- **Local:** o script interpola `'{target_dir}'`, `'{downloaded_file}'` e `'{exe_target}'` em strings PowerShell com aspas simples (e `"{downloaded_file}"` em aspas duplas no ramo do instalador). `UpdateDialog._on_download_finished` chama `os._exit(0)` logo depois do `Popen`.
- **Cenário:** usuário Windows cujo perfil tem apóstrofo (`C:\Users\D'Ávila\...`). O `.ps1` não compila e o app já morreu. O update falha sem nenhum aviso. No ramo de aspas duplas, `$`/crase no nome do asset também seriam interpretados.
- **Correção:** não interpole caminhos no script. Passe-os como parâmetros do `-File` e use cmdlets reais:

```python
PS_TEMPLATE = r"""
param(
    [Parameter(Mandatory=$true)][string]$TargetDir,
    [Parameter(Mandatory=$true)][string]$DownloadedFile,
    [Parameter(Mandatory=$true)][string]$ExpectedHash,
    [Parameter(Mandatory=$true)][int]$ProcessPid,
    [Parameter(Mandatory=$true)][string]$Mode,
    [string]$ExeTarget = ''
)
$ErrorActionPreference = 'Stop'

$actual = (Get-FileHash -LiteralPath $DownloadedFile -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $ExpectedHash.ToLower()) { Write-Error "Integrity check failed"; exit 1 }

$proc = Get-Process -Id $ProcessPid -ErrorAction SilentlyContinue
if ($proc) { if (-not $proc.WaitForExit(15000)) { Stop-Process -Id $ProcessPid -Force } }
Start-Sleep -Milliseconds 600

switch ($Mode) {
  'installer' {
     $args = @('/SP-', '/VERYSILENT', '/SUPPRESSMSGBOXES', "/DIR=`"$TargetDir`"")
     Start-Process -FilePath $DownloadedFile -ArgumentList $args -Wait
  }
  'zip' {
     $extract = Join-Path (Split-Path -LiteralPath $DownloadedFile -Parent) 'extracted'
     if (Test-Path -LiteralPath $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
     Expand-Archive -LiteralPath $DownloadedFile -DestinationPath $extract -Force
     Copy-Item -Path (Join-Path $extract '*') -Destination $TargetDir -Recurse -Force
     Remove-Item -LiteralPath $extract -Recurse -Force
  }
  default { Copy-Item -LiteralPath $DownloadedFile -Destination $ExeTarget -Force }
}

$latest = Get-ChildItem -LiteralPath $TargetDir -Filter 'Crinometro*.exe' -File |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latest) { Start-Process -FilePath $latest.FullName }
Start-Sleep -Seconds 2
Remove-Item -LiteralPath $DownloadedFile -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
"""
# Popen([... "-File", ps1_file, "-TargetDir", target_dir, "-DownloadedFile", downloaded_file,
#        "-ExpectedHash", expected_hash, "-ProcessPid", str(pid), "-Mode", mode, "-ExeTarget", exe_target])
```

Ajustes complementares:
- Substitua `os._exit(0)` por `app.quit()` seguido de `closeEvent` com `shutdown()`. Se a trava de arquivo for o problema, o próprio script já espera o PID.
- Baixe para uma pasta temporária **única por execução** (`tempfile.mkdtemp`), não `%TEMP%\crinometro_updater` fixa.
- Valide `Test-Path` do instalador após `-Wait` e só então relance.

#### E3 (M) Modelo de confiança do hash [LEITURA]
O SHA-256 vem do corpo da própria release no GitHub (ou de um asset dela). Protege contra download corrompido, **não** contra release/conta comprometida: quem publica o binário publica o hash. O update executa instalador silencioso. Recomendação: assinatura Authenticode do instalador, com verificação de `Get-AuthenticodeSignature` no script, ou assinatura destacada (minisign/ed25519) com chave pública embutida no app.

#### E4 (B) Notas de release inseridas como HTML sem escape [LEITURA]
- **Local:** `update_dialog.py` l.81-86 (`setHtml` com o corpo bruto da release e `setOpenExternalLinks(True)`).
- **Correção:**

```python
import html
html_body = html.escape(body_text).replace("\r\n", "<br>").replace("\n", "<br>")
```

#### E5 (B) Comparação de versão frágil [LEITURA]
- **Local:** `helpers.parse_version_tuple`. Uma tag `4.6.0-rc1` vira `(0,0,0)` e nunca é considerada nova. `4.5` e `4.5.0` comparam diferente.
- **Correção:**

```python
_VER_RE = re.compile(r"^\s*v?(\d+)\.(\d+)(?:\.(\d+))?")
def parse_version_tuple(ver_str):
    m = _VER_RE.match(str(ver_str))
    if not m:
        return (0, 0, 0)
    return tuple(int(g) if g is not None else 0 for g in m.groups())
```

#### E6 (B) Resto do updater [LEITURA]
Bom: toda a rede roda em `QThread`, e há `timeout=8`, `5` e `30`. Sem hash publicado, o download é recusado por padrão (`require_hash=True`). O botão "Cancelar" some durante o download, mas `Esc` ainda fecha o diálogo com a thread viva. Sobrescreva `reject()` para chamar `self.downloader.cancel()` e `wait()`.

### F. Exportação e higiene do repositório

#### F1 (A) Relatório TXT corrompido pelo `ExportController` [EXEC]
- **Local:** `export_controller.py::_generate_txt_report` l.130-151. O código abre `file_path` para escrever o cabeçalho (sem fechar) e, dentro do mesmo `with`, chama `generate_txt_report(file_path, ...)`, que reabre o mesmo caminho em `'w'`, trunca, escreve o relatório inteiro e fecha. Ao sair do `with`, o primeiro handle faz o flush do cabeçalho na posição 0.
- **Resultado reproduzido:** o início do arquivo final é o prelúdio do controller por cima do cabeçalho real do relatório. Os bytes iniciais do relatório são sobrescritos, e `generate_txt_report` já escreve o próprio cabeçalho, então o prelúdio é redundante. O teste `test_07` chama `generate_txt_report` direto e nunca exerce esse caminho.
- **Correção:** apague o bloco `with open(...)` inteiro:

```python
file_path, _ = QFileDialog.getSaveFileName(...)
if not file_path:
    return
from utils.report_generator import generate_txt_report
generate_txt_report(file_path, selected_cache, self.ctx.report_params)
t = I18N[self.lang]
QMessageBox.information(self.main_window, t["success"], t["report_success_summary"].format(n=len(selected_cache)))
```

#### F2 (M) Relatório gerado em worker lê o cache compartilhado com a GUI [LEITURA]
`_generate_pdf_report_modular._task` usa `selected_cache` (referência aos mesmos dicts de `heavy_data`) e `self.ctx.algo_params` enquanto o usuário pode editar pulsos (`editor_controller` altera `cache_entry["chirps"]` etc.). Tire um snapshot profundo das chaves usadas antes de iniciar o worker. Faltou também guarda de `isRunning` em `_report_worker` (A1).

#### F3 (B) Definições duplicadas que se sobrepõem [EXEC/LEITURA]
- `constants.py` define `CHANGELOG_FULL` duas vezes (l.88 e l.150). A segunda vale e **não tem 4.4.1, 4.4.0 nem 4.5.0**: confirmei que `"4.4.1" in CHANGELOG_FULL` é falso. `generate_changelog_pdf.py` e `CHANGELOG.md` omitem essas versões.
- `report_generator.py` define `format_timestamp_ms`, `extract_specimen_id`, `safe_mode` e `analyze_rhythmic_cadence` duas vezes (l.81-119 e l.516-554), e a segunda sobrescreve a primeira.
- **Correção:** apague as duplicatas e adicione um teste de import que verifique unicidade (via `ast`).

#### F4 (M) Dependência não declarada e artefatos no repositório [LEITURA]
- `learner.py` importa `skops.io` incondicionalmente (e `core/__init__` importa o learner). O `README` lista `pip install PyQt6 numpy scipy scikit-learn matplotlib reportlab pillow pyinstaller` **sem skops**: quem rodar pelo código-fonte tem `ModuleNotFoundError` na partida. Não há `requirements.txt`. O README ainda diz 4.4.1.
- O zip traz ~35 scripts `patch_*.py`, `apply_fixes_audit.py`, `temp*.txt`, `pt_lines*.txt`, `audit_results.txt`, um `modelo_treinado.skops` e um `crinometro_config.json` com o caminho pessoal `M:/Documentos/Faculdade/...` e correções reais. Mova isso para fora do repositório de release.

---

## 3. Refatorações arquiteturais essenciais

1. **Um único dono para o ciclo de vida das threads.** Crie `core/task_runner.py` com `submit(fn, *, exclusive_key)`, que mantém a referência até `finished`, recusa duplicatas por chave (`"analysis"`, `"batch"`, `"learn"`, `"report"`) e expõe `shutdown()`. Orquestrador, `EditorController` e `ExportController` passam a usá-lo. Elimina A1/A2/A3 de forma estrutural.
2. **Cancelamento cooperativo de ponta a ponta.** `should_abort` em `analyze()` e checagens nos laços de `PulseLearner` (`extract_features_for_peak` por pico, `filter_peaks`, mineração de negativos).
3. **`PulseLearner` imutável na inferência.** Treino constrói um novo modelo e o publica por troca atômica sob lock. A inferência trabalha sobre um snapshot (`model`, `rules`, `feature_names`). Persistência versionada (`schema_version`, `feature_names`, versão do sklearn), com quarentena de arquivos corrompidos.
4. **Contrato de estado de `heavy_data`.** Hoje é um dict mutável compartilhado entre GUI, workers e exportação. Defina uma estrutura com campos imutáveis (arrays marcados `setflags(write=False)`) e um `AnalysisResult` separado dos "edits do usuário". Isso resolve F2 e D4, e permite o LRU de B5.
5. **Camada de persistência única** (`utils/persistence.py`): `CONFIG_DIR` por usuário, `atomic_write_json`, validação de esquema na leitura, backup `.bak` e log de falhas. Acaba com os `except: pass` em volta de I/O.
6. **Logging estruturado** (`logging` com arquivo rotativo) no lugar de `pass  # print(...)`. Exceções de ML e de I/O precisam deixar rastro e alimentar um indicador de estado na UI.

---

## 4. Recomendações para o Quality Gate

O gate atual verifica codificação UTF-8, sintaxe AST e nomes globais indefinidos em `core/ui/utils/scripts/tests`. Não executa os testes, não cobre os arquivos da raiz (`main.py`, launcher) e o `walk` só inspeciona funções. A suíte (65 testes) é boa em caracterização de UI/controllers, mas quase não exercita casos patológicos: não há teste com WAV malformado, NaN ou taxa baixa (só `test_51` de filtro em baixa taxa), nenhum teste de corrida ou fechamento da janela, e `test_02` usa um `long_task` que consulta a flag, ao contrário de `analyze()` real.

**Adicione antes de promover para release:**

1. **Execução obrigatória no gate:** `python -m unittest discover tests` com `QT_QPA_PLATFORM=offscreen` e `CRINOMETRO_TESTING=1`. Falha do gate se qualquer teste falhar. Inclua a raiz (`main.py`, `crinometro__laucher.py`) e use `pyflakes` ou `ruff` (nomes indefinidos em escopo local, imports não usados, redefinições como as do F3).
2. **DSP patológico (`tests/test_analyzer_pathological.py`):** WAV vazio, 10 amostras, só DC, NaN/Inf, estéreo com canal esquerdo mudo, int8/int16/int24/float, taxas 6/8/16/48/96 kHz (esperando erro claro ou resultado correto, nunca silêncio), ruído branco, chilreios com 15 dB de crescendo, e uma gravação de 20 min com limite de memória.
3. **Cancelamento:** abortar `analyze()` real no meio e verificar que a thread termina em menos de 2 s; abortar e reiniciar o lote logo em seguida (A3); `force_reanalyze` duplo; `closeEvent` com worker ativo, esperando saída limpa e sem o aviso do Qt (capture com `qInstallMessageHandler`).
4. **Rajada de cliques:** 50 cliques em Analisar/Reanalisar/Abortar/Exportar em sequência, com `QTest.mouseClick` e event loop, sem crash e com botões e spinners em estado consistente.
5. **Exportação:** ler de volta o TXT/CSV/PDF exportados **pelo `ExportController`** e comparar byte a byte com a saída de `generate_*` (pegaria F1). Testar também caminhos com apóstrofo e acento.
6. **Persistência:** matar a escrita no meio (simular exceção entre `write` e `os.replace`) e confirmar que o arquivo original permanece íntegro. JSON truncado deve ser movido para `.corrupt-*` e as correções recuperadas do backup. Rodar o app com CWD diferente e checar o destino do config (D1).
7. **ML:** teste de **não vazamento** (treinar com e sem a feature de prior e verificar que a métrica em dados reais não depende dela); `skops` truncado/corrompido, com versão antiga do sklearn e com `feature_names` divergentes, exigindo estado "degradado" visível em vez de aceitar todos os picos; ordem cronológica após `update_from_corrections` com >5000 amostras (C4).
8. **Updater:** executar o `.ps1` gerado em um runner Windows de CI (`Get-Command` de cada cmdlet usado; execução ponta a ponta com um instalador fictício e um perfil com apóstrofo). Teste de hash adulterado entre o download e a execução.
9. **Higiene de release:** o gate deve falhar se existir `patch_*.py`, `*.skops`, `crinometro_config.json` ou `temp*.txt` na árvore empacotada, se `README`/`requirements.txt` não listarem `skops`, e se `APP_VERSION` divergir do `README`/`CHANGELOG`.
10. **Metadados científicos:** teste que garanta que `heavy_data["params"]` do relatório é igual aos parâmetros efetivamente usados na análise (D4), e que reanalisar duas vezes sem mudar nada dá resultado idêntico.

**Ordem sugerida de correção:** F1 → A1/A2/A3 → E1/E2 → D1/D2 → B1/B2 → A4/C1/C2 → restante.
