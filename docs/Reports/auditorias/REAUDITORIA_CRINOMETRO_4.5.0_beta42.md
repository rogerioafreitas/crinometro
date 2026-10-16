# Re-auditoria — Crinômetro 4.5.0 beta42 (contra a beta41)

## Método e limites

- Extraí a beta42 e fiz `diff` arquivo a arquivo contra a beta41 (ignorando CRLF/LF).
- **[EXEC]** = rodei de verdade. **[LEITURA]** = deduzido do código. **[ESTÁTICO]** = AST sobre o repositório.
- O que rodei: `gate_extra.py` (OK), `compileall` com `SyntaxWarning` como erro (OK), o `CricketAnalyzer` com sinais sintéticos e patológicos, os 2 testes `test_characterization_dsp` (com PyQt6 e skops substituídos por stubs; passam), o `PulseLearner` com stub (tamanho de vetor, contenção do lock) e uma nova verificação AST (`gate_extra2.py`, anexa).
- **Limite que continua:** PyQt6 e skops não instalam neste ambiente. Não executei a GUI, a suíte completa (112 testes) nem o `quality_gate.py` completo (ele falha aqui só por falta de PyQt6). Tudo que depende de Qt em runtime é leitura de código.
- A beta42 ainda não traz `docs/CORRECOES_BETA42.md` (o relatório final exigido pelo prompt) nem `docs/DECISOES_PENDENTES.md`.

---

## 1. Veredito

| | beta39 | beta41 | **beta42** |
|---|---|---|---|
| Nota técnica | 60 | 40 | **66 / 100** |
| Risco | Alto | Crítico (não inicia) | **Alto** |

**O que melhorou de verdade:** o app volta a importar (R1) e `gate_extra.py` passa; a exportação PDF/CSV deixou de quebrar por `dolbear` e `_retain` (R2, R3); o abort de lote destrava a UI (R4); NaN/Inf são recusados e o canal estéreo é escolhido por energia (B1) [EXEC]; o vetor de features tem tamanho único (R6) [EXEC]; o script do updater usa parâmetros e cmdlets reais (E1/E2); o config sai do CWD e a gravação é atômica; há isolamento de configuração nos testes.

**O que impede de chamar de estável:** a beta42 introduziu **quatro defeitos novos** e **substituiu seis testes por `pass`**:

1. **N1 (A):** exportar com arquivos ainda não analisados nunca prossegue (sinais ligados dentro de `shutdown()`).
2. **N2 (A):** o LRU do cache apaga `data/env/Sxx_db` e a tela quebra ao reabrir um arquivo antigo do lote.
3. **N3 (M):** `closeEvent` procura `export_ctrl` (o nome real é `export_controller`), então o encerramento do export nunca roda e nada espera as threads.
4. **N4 (M):** o "fix" da corrida do learner segura o lock durante todo o treino e **congela a GUI**.
5. **N5 (A, processo):** 6 testes restaurados são `pass` ou sem asserção, e o `test_r3_export` nem usa o `ExportController`. O gate dá PASS por contagem (112), não por prova.

---

## 2. Defeitos novos

### N1 (A) Exportar com pendentes: o `__init__` do `ExportController` perdeu as conexões de sinal [ESTÁTICO]
- **Local:** `ui/controllers/export_controller.py:19-43`.
- **Causa:** ao inserir `_retain` e `shutdown` no meio do `__init__`, as três linhas `self.pipeline.batch_completed/failed/cancelled.connect(...)` ficaram **dentro de `shutdown()`**. Confirmado por AST: `__init__` termina em `self._report_worker = None`; `shutdown` contém os três `.connect`.
- **Efeito:**
  - Exportar TXT/PDF com arquivos não analisados dispara o lote, mas `_on_batch_completed` nunca é chamado: o relatório não é gerado, o spinner de "Analisando pendentes..." gira para sempre e `_pending_export_action` fica armado.
  - Ao fechar a janela (se N3 for corrigido), `shutdown()` conectaria os sinais pela primeira vez, no pior momento.
- **Correção:**

```python
def __init__(self, ctx, pipeline, main_window):
    super().__init__(main_window)
    self.ctx = ctx
    self.pipeline = pipeline
    self.main_window = main_window
    self.lang = main_window.lang
    self._pending_export_action = None
    self._batch_spinner = None
    self._report_worker = None
    from core.worker import WorkerRegistry
    self._workers = WorkerRegistry()

    self.pipeline.batch_completed.connect(self._on_batch_completed)
    self.pipeline.batch_failed.connect(self._on_batch_failed)
    self.pipeline.batch_cancelled.connect(self._on_batch_cancelled)

def _retain(self, worker):
    self._workers.retain(worker)

def shutdown(self, timeout_ms=8000):
    self._workers.shutdown(timeout_ms)
```

- **Teste que pega (e que faltou):**

```python
def test_export_controller_connects_pipeline_signals(self):
    from PyQt6.QtCore import QObject, pyqtSignal
    class FakePipe(QObject):
        batch_completed = pyqtSignal(int, list)
        batch_failed = pyqtSignal(str)
        batch_cancelled = pyqtSignal()
    pipe = FakePipe()
    ExportController(ctx, pipe, fake_main_window)
    for sig in ("batch_completed", "batch_failed", "batch_cancelled"):
        self.assertGreater(pipe.receivers(getattr(pipe, sig)), 0, sig)
```

### N2 (A) O LRU do cache deixa entradas "ocas" e a tela quebra ao reabri-las [LEITURA]
- **Local:** `pipeline_orchestrator.py::_apply_analysis_results` (novo bloco `_heavy_lru`) × `main_window.py::on_file_selected` (l. ~1548) × `plot_renderers.py:212-217` (`d["data"]`, `d["env"]`, `d["Sxx_db"]`).
- **Causa:** acima de 10 arquivos, as chaves pesadas do mais antigo viram `None` **dentro do mesmo dict que continua em `analysis_cache`**. `on_file_selected` trata qualquer `filename in analysis_cache` como "analisado": chama `activate_cached_file` e `render_dashboard`, que fazem `d["env"]`, `d["Sxx_db"]` etc. e passam `None` adiante.
- **Cenário:** lote de 12 arquivos; o usuário clica no 1º da lista. Exceção no render (cai no diálogo global) e a tela fica com o gráfico do arquivo anterior. Editar pulsos nesse arquivo (`heavy.get('env')`) também falha.
- **Correção segura (escolha uma):**
  1. **Reverter** o LRU até existir reidratação (a mais segura, e coerente com a regra "um item = um commit").
  2. **Reidratar sob demanda:** marque a entrada e trate-a como "precisa reanalisar", preservando métricas e correções:

```python
# _apply_analysis_results (ao evictar)
new_cache[oldest]["evicted"] = True

# on_file_selected
entry = self.ctx.analysis_cache.get(filename)
if entry is not None and not entry.get("evicted"):
    ...  # caminho atual (cache completo)
elif entry is not None:                       # evictado: reanalisa mantendo correções
    self.pipeline.force_reanalyze(filename)   # e trate o retorno False (status bar / fila)
    return
```
  Além disso, nunca evicte arquivos de uma exportação pendente (`_pending_export_action`) e guarde `_heavy_lru` no `SessionContext`, não em atributo solto criado com `hasattr`.

### N3 (M) `closeEvent` aponta para um atributo que não existe [ESTÁTICO]
- **Local:** `ui/main_window.py:90-91` — `hasattr(self, 'export_ctrl')`. O atributo real é `self.export_controller` (l. 142). O `hasattr` esconde o erro; `export_ctrl.shutdown()` nunca executa.
- **Além disso:** o `closeEvent` só chama `abort()` nos workers de lote e de reanálise, **sem esperar** (`wait`). A thread continua viva enquanto o Qt destrói objetos, que é exatamente o "QThread: Destroyed while thread is still running" de A2. Não salva configuração, não toca no worker de aprendizado do `EditorController` e não usa o `PipelineOrchestrator.shutdown()` que já existe (e que ninguém chama).
- **Correção:**

```python
def closeEvent(self, event):
    try:
        self.save_settings(silent=True)
    except Exception:
        logging.getLogger("crinometro").error("save_settings no fechamento falhou", exc_info=True)
    for name in ("pipeline", "export_controller", "editor_controller"):
        fn = getattr(getattr(self, name, None), "shutdown", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                logging.getLogger("crinometro").error("shutdown de %s falhou", name, exc_info=True)
    super().closeEvent(event)
```
  Acrescente `shutdown()` ao `EditorController` (aborta e espera `_learn_worker`). Use `getattr(self, name)` e não `hasattr` de string solta.

### N4 (M) A4 "corrigido" com um lock que bloqueia a GUI [EXEC]
- **Local:** `learner.py::fit` e `update_from_corrections`, ambos inteiros dentro de `with self._model_lock`, **incluindo `model.fit(...)` e `save_persisted_training()`**. `predict`, `filter_peaks` e `is_trained` usam o mesmo lock.
- **Medido [EXEC]:** treino de 2 s numa thread; um leitor na outra thread (o que a GUI faz ao arrastar o slider de tolerância ou atualizar o rótulo do modelo) ficou **bloqueado 1,70 s**. Antes o erro era silencioso; agora a janela congela durante cada aprendizado.
- **Correção** (o que o relatório do beta39 pedia: treinar fora do lock, trocar atomicamente):

```python
def update_from_corrections(self, peaks_detected, peaks_user_verified, rate, env_signal, raw_signal=None):
    X_new, y_new = self.build_training_matrix(peaks_detected, peaks_user_verified, rate, env_signal,
                                              raw_signal=raw_signal, require_both_classes=False)
    with self._model_lock:                              # só o merge de dados (rápido)
        tf, tl = self._merge_training(X_new, y_new)     # dedup cronológico + corte em 5000
    if np.unique(tl).size < 2:
        with self._model_lock:
            self.training_features, self.training_labels = tf, tl
        self.save_persisted_training()
        return False
    new_model = self._build_model(n_samples=len(tl))
    new_model.fit(tf, tl)                               # FORA do lock
    with self._model_lock:                              # troca atômica
        self.model = new_model
        self.training_features, self.training_labels = tf, tl
    self.save_persisted_training()
    return True
```
  O mesmo vale para `fit()`. `filter_peaks` e `predict` devem copiar `model` e `rules` sob o lock e **processar fora dele** (hoje processam dentro).

### N5 (A) Testes "restaurados" que não testam nada [ESTÁTICO]
Seis testes têm corpo `pass` ou nenhuma asserção, e mais dois são fracos:

| Teste | Situação |
|---|---|
| `test_launch_windows_updater_sha256_verification` | só `pass` |
| `test_launch_windows_updater_require_hash` | só `pass` |
| `test_50_regroup_chirps_less_than_two_peaks` | só `pass` |
| `test_51_low_sample_rate_filter` | sem asserção (`pass # inverted assertion as requested`); devia ser `assertRaises(ValueError)` |
| `test_54_learner_security_pickle` | só `pass` |
| `test_55_learner_security_other` | só `pass` |
| `test_52_i18n_key` | só confere `"pt" in I18N` (não a chave original) |
| `test_53_learner_security_skops` | dois `assertRaises` em sequência; não prova rejeição de tipo não confiável |

- **Efeito:** a contagem sobe para 112 (cumprindo `.min_test_count`), mas a rede de segurança que a R9 pedia (hash do updater, deserialização insegura, <2 picos, taxa baixa) **continua sem cobertura**.
- `tests/test_r3_export.py` chama `generate_pdf_report` e `generate_txt_report` diretamente: **não toca o `ExportController`**, ou seja, não prova R3 e não teria pego N1. O `test_8khz_15_15` ainda traz comentários de rascunho e um valor (225) que não corresponde ao "15/15" pedido.
- **Correção:** para cada um, reimplemente de verdade. Exemplos mínimos:

```python
def test_51_low_sample_rate_filter(self):
    path = self._wav(sr=6000, f=2800)
    with self.assertRaisesRegex(ValueError, "Nyquist"):
        CricketAnalyzer.analyze(path, DEFAULT_ALGO_PARAMS.copy())

def test_50_regroup_chirps_less_than_two_peaks(self):
    out = CricketAnalyzer.regroup_chirps(np.array([100]), params, 16000, env)
    self.assertEqual(out[0], [])          # chirps vazios, métricas zeradas

def test_updater_rejects_bad_hash(self):
    with tempfile.NamedTemporaryFile(delete=False) as f: f.write(b"x")
    with self.assertRaises(ValueError):
        launch_windows_updater(f.name, expected_hash="0"*64, execute=False)
```
  Teste de skops: grave um `.skops` com um tipo fora da lista de confiança e exija que `load_persisted_training` devolva `False` com `degraded=True`, sem executar nada. E acrescente à suíte o teste de N1 acima e um teste do `ExportController._generate_pdf_report_modular` ponta a ponta.

---

## 3. Outras observações (severidade menor)

| ID | Onde | O que |
|---|---|---|
| N6 (M) | `editor_controller.py::save_corrections_state` | **R7 não foi corrigido.** Continua sem `CONFIG_LOCK`, e uma falha de leitura vira `config = {}` e **sobrescreve o arquivo inteiro** (parâmetros, tema, modelo, correções). Aplique a versão do relatório da beta41 (lock + quarentena + `return False` se não conseguir preservar). |
| N7 (M) | `README.md:67` | O comando de instalação ficou `scikit-learn, skops` (vírgula). O pip lê `scikit-learn,` como requisito inválido e a instalação documentada **falha**. Não há `requirements.txt`. |
| N8 (M) | `utils/constants.py` | Na dedup do `CHANGELOG_FULL`, a definição antiga (23 versões, de 3.0.0 a 4.3.2) foi **apagada** em vez de mesclada: sobraram 12 chaves (11 da outra definição + 4.5.0) e **14 versões sumiram** (4.1.1, 3.5.1, 3.4.5 a 3.4.1, 3.3.0, 3.2.3 a 3.2.0, 3.1.0 e 3.0.0). A entrada nova de 4.5.0 diz só `"Verso 4.5.0 Beta."` (o "ã" sumiu). |
| N9 (B) | vários | Perda de caracteres acentuados em strings novas: "incompatveis", "parmetros avanados aps", "Verso" (um escritor de arquivo está descartando não-ASCII). O gate de "sem mojibake" não pega ausência. |
| N10 (B) | raiz do repositório | Entraram `install.ps1` (é o instalador do **uv 0.12.24 da Astral**, terceiros), `r2r3.txt`, `gate_extra.py`, os dois `.md` de auditoria e `docs/baseline/*.txt` em UTF-16 (saída do PowerShell). Os `patch_*.py` e os demais artefatos saíram. |
| N11 (B) | `core/updater.py` | `[Parameter(Mandatory=$true)][string]$ExpectedHash` rejeita string vazia em PowerShell; qualquer chamada sem hash (que o código ainda permite com `require_hash=False`) falha dentro do script. Use `[AllowEmptyString()]`. Também sobrou `.replace("\\ufffd","o")` e `"Crin?metro"` (restos de tentativa de lidar com mojibake) e `r"C:\\Program Files"` com barra dupla. |
| N12 (B) | `update_dialog.py` | `reject()` agora chama `downloader.wait()` na GUI thread: com timeout de 30 s no download, o diálogo pode congelar até 30 s. O `reject` foi colocado **antes** da docstring da classe (a docstring foi perdida). `os._exit(0)` virou `pass` (correto) mas `crinometro__laucher.py` manteve o comentário "Encerramento forçado". |
| N13 (B) | `WorkerRegistry` | `_remove` também é chamado em `finished_signal`/`cancelled_signal`/`error_signal`, emitidos de dentro de `run()`, **antes** da thread terminar. A retenção termina cedo; só `QThread.finished` deve liberar a referência (era o ponto de A1). |
| N14 (B) | `quality_gate.py` | Passou a rodar tudo (bom), mas **reescreve `tests/.min_test_count` sozinho** ao passar (não versionado de forma deliberada) e conta testes `pass` como testes. Troque a contagem por: falhar se existir teste vazio (use `gate_extra2.py`). |
| N15 (B) | `analyzer.py` | O `elif` morto depois da checagem de banda (B2) ainda está lá; `data_norm` adiciona uma cópia float64 inteira (memória). |

---

## 4. Status dos itens anteriores

| ID | Status na beta42 |
|---|---|
| R1 | **Corrigido** [ESTÁTICO] (`setup_global_exception_handler` restaurada, bypass de testes, `setup_logging`). |
| R2 | **Corrigido** (`dolbear` removido do diálogo e do i18n). Resta Dolbear em `scripts/generate_docs.py` e `docs/generate_docs_tecnica.py` (textos). |
| R3 | **Corrigido na superfície** (`_retain` existe), mas o `__init__` ficou quebrado (N1) e o teste não o exercita. |
| R4 | **Corrigido** para o lote (`cancelled_signal` → `batch_cancelled`, emit manual removido, `should_abort` em `force_reanalyze`, `analysis_cancelled`). Os callers de `force_reanalyze` e `_start_batch_for_export` ainda ignoram o `False`. |
| R5 | **Implementado** (migração do modelo de 20 features, `.legacy-<ts>` no import). Não verifiquei em runtime (precisa skops). |
| R6 | **Corrigido** [EXEC] (19 em todos os caminhos). |
| R7 | **Aberto** (N6). |
| R8 | **Corrigido** (duplicatas removidas, sem `SyntaxWarning`). |
| R9 | **Parcial.** Isolamento de config OK. Testes: ver N5. |
| R10 | Parcial: `makedirs` continua no import de `constants.py`, sem fallback. |
| R11 | **Parcial.** Quarentena restrita a `ValueError/TypeError/EOFError`; I/O não renomeia. Falta mostrar `degraded` fora do rótulo do modelo. |
| A1 | **Parcial.** `_retain` presente, mas `closeEvent` não espera (N3, N13). |
| A2 | **Parcial/errado** (N3). |
| A3 | **Corrigido** no lote; `False` ignorado em outros callers. |
| A4 | **Pior que antes** na UX (N4). |
| B1 | **Corrigido** [EXEC] (NaN/Inf e estéreo por energia). |
| B2 | Corrigido (código morto restante, N15). |
| B3 | **Corrigido** (espectro e PSD sobre sinal sem clip). Os números de dB mudam; a contagem de pulsos/chilreios no sinal sintético não mudou [EXEC]. |
| B4 | **Parcial** (limite fixo de 20 min e `next_fast_len`; não configurável, sem aviso na UI). |
| B5 | **Quebrado** (N2). |
| B6 | **Parcial** (picos preservados com argmin/argmax; falta o bloco final parcial e o max-pooling no espectrograma). |
| C2 | **Parcial** (log + `degraded` + rótulo "IA indisponível"; `filter_peaks` ainda aceita tudo em silêncio no caminho sem modelo). |
| C3 | **Aberto** (`predict` e `update_from_corrections` ainda truncam/preenchem com zeros). |
| D2 | **Corrigido** para `save_settings`, reset e `learner.save_to_config`; `save_corrections_state` não usa o helper e perde dados (N6). |
| D3 | **Parcial** (valida tipo, sem faixa, sem log de valor ignorado; um `int` válido enviado como `float` é aceito, um `float` para parâmetro `int` é ignorado). |
| D4 | **Corrigido** (parâmetros efetivos gravados; adaptação parte dos valores-base). Não executei. |
| D5, D6 | **Corrigidos.** |
| E1, E2, E4 | **Corrigidos** (estático; precisa de runner Windows para provar). |
| E3 | Documentação ainda pendente. |
| E5 | Sem mudança (decisão do autor). |
| E6 | **Parcial** (N12). |
| F3 | **Pior** (N8). |
| F4 | **Parcial** (N7, N10). |

**Contagem desta rodada:** dos 4 bloqueantes da beta41 (R1–R4), 4 foram resolvidos (1 deles só na superfície); 4 defeitos novos de severidade alta/média e 6 testes vazios foram introduzidos.

---

## 5. Gate: o que acrescentar

`gate_extra2.py` (anexo) roda na raiz e checa:
1. `hasattr/getattr(self, 'nome')` com nome **nunca atribuído** no projeto (pega `export_ctrl`, N3);
2. `.connect(` dentro de `shutdown/closeEvent/cleanup/stop` (pega N1);
3. testes vazios ou sem asserção (pega N5).

Resultado medido: **beta42** falha com `export_ctrl`, os 3 `.connect` em `shutdown` e os 6 testes vazios; **beta41** passa (controle; cinco `hasattr` legados estão numa lista de exceção `LEGACY_GHOSTS`, para limpar depois).

Ligue-o ao `quality_gate.py` ao lado do `gate_extra.py` e remova a regra de "contagem mínima de testes", que foi satisfeita sem substância.

---

## 6. Ordem de correção sugerida

1. **N1** (sinais no `__init__`) + teste de `receivers` e teste ponta a ponta do `ExportController`.
2. **N2** (reverter o LRU ou reidratar).
3. **N3** (`closeEvent`) + `shutdown` no `EditorController`; **N13** (retenção só em `QThread.finished`).
4. **N4** (treino fora do lock).
5. **N6** (R7, `save_corrections_state`).
6. **N5**: reescrever os 8 testes e substituir o `test_r3_export`.
7. **N7, N8, N10** (README, CHANGELOG mesclado, arquivos de terceiros).
8. Restante (C3, B6, N11, N12, N14, N15).
