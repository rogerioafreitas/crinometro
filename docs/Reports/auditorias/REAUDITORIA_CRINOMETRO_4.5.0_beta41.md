# Re-auditoria — Crinômetro 4.5.0 beta41 (contra o beta39)

## Método

- Extraí o beta41 e fiz `diff` arquivo a arquivo contra o beta39 (ignorando fim de linha: `export_controller.py` e outros mudaram de LF para CRLF, o que polui o diff cru).
- Para cada achado do relatório anterior, verifiquei no código se foi corrigido.
- **[EXEC]** = rodei de verdade (analisador com sinais sintéticos; resolução de imports e atributos por AST sobre o repositório; o `quality_gate.py` do projeto). **[LEITURA]** = deduzido do código.
- Limite igual ao da rodada anterior: PyQt6 e skops não instalam no meu ambiente. Não executei a GUI nem a suíte de testes. Os efeitos de runtime Qt abaixo são deduzidos do código, e as regressões de import e atributo são certas porque são estáticas.

---

## 1. Veredito

| Item | beta39 | beta41 |
|---|---|---|
| Nota técnica | 60/100 | **40/100** |
| Risco para release | Alto | **CRÍTICO — bloqueante** |

**O beta41 não inicia.** `main.py` e `crinometro.py` importam `setup_global_exception_handler`, que foi apagada de `utils/helpers.py`. Mesmo que se corrija isso, a exportação de relatório quebra por mais dois erros (`dolbear` e `_retain`). O `quality_gate.py` do projeto continua dizendo **PASS** nesse estado.

Dos 33 achados do beta39: **8 corrigidos, 7 corrigidos parcialmente (3 deles com defeito novo) e 18 ainda abertos.** As correções que entraram são, em geral, as que sugeri no relatório anterior, aplicadas quase literalmente. Faltou ligar as pontas: criar o método usado, conectar o sinal novo, chamar a função nova.

`docs/FASE8_REPORT.md` agora afirma "99/99 testes", "mitigação completa de race conditions" e "não restam mutações perigosas". A suíte tem **95** testes (eram 105), e os achados abertos abaixo contradizem as outras duas frases.

---

## 2. Regressões novas (bloqueiam o release)

### R1 (C) O app não inicia: `ImportError` [EXEC]
- **Local:** `utils/helpers.py` (reescrito) × `main.py:14,21` e `crinometro.py:16`.
- **Causa:** o novo `helpers.py` só define `handle_exception`, `parse_version_tuple`, `is_version_newer` e `_VER_RE`. `setup_global_exception_handler` sumiu, e `main.py` e `crinometro.py` não foram atualizados. `crinometro__laucher.py` faz `import crinometro` em `CoreLoaderThread`, então o launcher também falha.
- **Efeito colateral:** o `sys.excepthook` agora é instalado no import, e o desvio `CRINOMETRO_TESTING=1` foi removido. Numa exceção não tratada dentro de teste, abre-se um `QMessageBox.exec()` modal, e a suíte trava em vez de falhar.
- **Correção** (`utils/helpers.py`):

```python
import os, sys, logging, traceback

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("crinometro").error(
        "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    if os.environ.get("CRINOMETRO_TESTING") == "1":
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    from PyQt6.QtCore import QThread
    from PyQt6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance()
    if app is None or QThread.currentThread() is not app.thread():
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    if getattr(handle_exception, "_busy", False):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    handle_exception._busy = True
    try:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Erro Inesperado - Crinômetro")
        msg.setText(f"Ocorreu um erro inesperado:\n\n{exc_type.__name__}: {exc_value}")
        msg.setDetailedText("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        msg.exec()
    finally:
        handle_exception._busy = False

def setup_global_exception_handler():
    sys.excepthook = handle_exception
```

Remova a linha solta `sys.excepthook = handle_exception` do import. Hoje não existe nenhuma configuração de `logging` no projeto, então `logging.error(...)` só escreve num stderr que um `.exe` sem console descarta. Adicione em `main()` um `RotatingFileHandler` no diretório de configuração do usuário:

```python
import logging, logging.handlers, os
from utils.constants import CONFIG_FILE

def setup_logging():
    log = logging.getLogger("crinometro")
    if log.handlers:
        return
    h = logging.handlers.RotatingFileHandler(
        os.path.join(os.path.dirname(CONFIG_FILE), "crinometro.log"),
        maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)
```

Troque os `logging.error(...)` do `learner.py` por `logging.getLogger("crinometro")`, para o log cair nesse arquivo.

### R2 (C) Exportar relatório modular → `TypeError` [EXEC]
- **Local:** `ui/dialogs/export_report_dialog.py:289-294` × `utils/report_generator.py` (`ReportSectionFlags`).
- **Causa:** a Lei de Dolbear foi removida de propósito (consta no FASE8_REPORT), e o campo `dolbear` saiu do dataclass. Mas o diálogo ainda monta `ReportSectionFlags(..., dolbear=self.chk_dolbear.isChecked(), ...)`. Ao confirmar o diálogo, dá `TypeError: unexpected keyword argument 'dolbear'`.
- **Correção:** apague a linha `dolbear = self.chk_dolbear.isChecked(),` do `ReportSectionFlags(...)`. Apague também o `QCheckBox` oculto (`chk_dolbear`, linhas ~125 e 131), a chave `chk_dolbear_est` do i18n e a menção "Estimativa de Temperatura (Dolbear)" no ROADMAP, que ainda tem `[x]`.

### R3 (C) Gerar o PDF/CSV → `AttributeError: _retain` [EXEC]
- **Local:** `ui/controllers/export_controller.py:203` chama `self._retain(worker)`. A classe `ExportController` não define `_retain`. `restore_ec.py` (um script de patch na raiz) existe para adicionar esse método, mas nunca foi aplicado.
- **Efeito:** mesmo corrigindo R2, toda exportação de PDF/CSV/TXT modular falha antes de iniciar o worker.
- **Correção:**

```python
# ExportController.__init__
self._retained_workers = set()

def _retain(self, worker):
    self._retained_workers.add(worker)
    worker.finished.connect(lambda w=worker: self._retained_workers.discard(w))

def shutdown(self, timeout_ms=8000):
    pending = list(self._retained_workers)
    for w in pending:
        w.abort()
    for w in pending:
        w.wait(timeout_ms)
```

Evite copiar o mesmo método em cada controller: coloque `retain/shutdown` num `WorkerRegistry` em `core/worker.py` e use composição.

### R4 (A) Abortar um lote deixa a UI travada para sempre [LEITURA]
- **Local:** `pipeline_orchestrator.py` / `core/worker.py` / `main_window.py`.
- **Causa:** o relatório anterior sugeria emitir `batch_cancelled` só quando a thread terminasse de fato. No beta41 o `emit` imediato foi removido de `abort_current_analysis`, e `GenericWorker.cancelled_signal` foi criado, mas **nada o conecta a `batch_cancelled`**. `grep cancelled_signal` só acha as emissões. Além disso, `run()` emite `cancelled_signal` uma segunda vez depois do `emit` manual em `_task`.
- **Cenário:** o usuário clica em "✕ Abortar" durante um lote. `_on_batch_cancelled` (reabilitar "Analisar selecionados", parar o spinner) e o `_on_batch_cancelled` do `ExportController` (limpar a exportação pendente) **nunca executam**, porque `finished_signal` também não sai em abort. O botão fica desabilitado até reiniciar. Isso é pior que o beta39, onde o botão ao menos era reabilitado.
- **Correção:**

```python
# run_batch_analysis, logo após criar o worker
worker = GenericWorker(_task)
self._batch_worker = worker
self._retain(worker)
worker.cancelled_signal.connect(self.batch_cancelled)      # <- faltava

# _task: remover o emit manual
except AnalysisAborted:
    break                                                  # run() emite cancelled_signal uma vez

# main_window / ExportController: já tratam batch_cancelled corretamente
```

Complete três pontos:
1. **Reanálise:** passe `should_abort=lambda: worker.abort_requested` também em `force_reanalyze._task`. Hoje só o lote o recebe, e a reanálise individual ainda é incancelável.
2. **Mais checkpoints:** o `analyze()` tem só 2 chamadas a `_chk()`. Adicione-as após `hilbert`, antes de `find_peaks` e antes do ML.
3. **Silêncio no `False`:** `run_batch_analysis` e `force_reanalyze` devolvem `False` em silêncio, e os callers (`analyze_selected_audios`, `_start_batch_for_export`, as quatro chamadas de `force_reanalyze` em `main_window`) ignoram o retorno. O usuário muda um parâmetro, a reanálise é descartada e a tela mostra o resultado velho. Tratar o retorno (aviso na barra de status ou fila) fecha o item A3 do relatório anterior.

---

## 3. Regressões e defeitos novos de severidade menor

### R5 (M) Migração do learner apaga o histórico de treino [LEITURA]
- **Local:** `learner.py::load_persisted_training` e `import_model_file`.
- **Causa:** ao tirar `prior_p_focal`, o modelo passou a 19 features. Quem tem um `modelo_treinado.skops` de 20 features recebe `return False` ("incompatível"). O learner fica vazio. No primeiro `update_from_corrections`, `save_persisted_training` **sobrescreve** o arquivo antigo. Todo o histórico de treino acumulado é perdido. A única coluna a descartar é a última.
- **Correção:**

```python
_LEGACY_NAMES = None   # definido no __init__: self.feature_names + ["prior_p_focal"]

def load_persisted_training(self):
    ...
    names = list(payload.get("feature_names") or [])
    legacy = names == self.feature_names + ["prior_p_focal"]
    if not legacy and names != self.feature_names:
        self.degraded, self.last_error = True, "Modelo salvo com features incompatíveis."
        return False
    features = np.asarray(payload.get("training_features", []), dtype=float)
    labels = np.asarray(payload.get("training_labels", []), dtype=int)
    if legacy and features.ndim == 2:
        features = features[:, :len(self.feature_names)]      # descarta a coluna do prior
    ...
    if legacy:
        self.model = None                                     # modelo antigo depende do prior vazado
        if np.unique(labels).size >= 2:
            m = self._build_model(n_samples=len(labels))
            m.fit(features, labels)
            with self._model_lock:
                self.model = m
```

Faça o mesmo em `import_model_file` e antes de sobrescrever qualquer arquivo incompatível: copie-o para `.legacy-<ts>`.

### R6 (M) Vetor de features com tamanho inconsistente [EXEC]
- **Local:** `learner.py::extract_features_for_peak`, linhas 119/121/130 (`n_features = 20`).
- **Causa:** os dois retornos antecipados (pico fora do envelope, segmento vazio) devolvem `np.zeros(20)`. O vetor normal agora tem 19 elementos (medido: 19 vs 20). `np.asarray([...], dtype=float)` sobre uma mistura dá `ValueError: inhomogeneous shape`.
- **Correção:** defina `N_FEATURES = 19` (ou `len(feature_names)`) como constante do módulo e use-a nos dois retornos antecipados.

### R7 (M) `save_corrections_state` perdeu o lock e pode apagar a configuração [LEITURA]
- **Local:** `editor_controller.py`.
- **Causa:** `CONFIG_LOCK` foi removido, mas `main_window.save_settings` e `learner.save_to_config` ainda o usam. Agora há leitura-modificação-escrita concorrente sem exclusão mútua. Pior: uma falha de leitura (JSON inválido, `PermissionError` por antivírus) vira `config = {}`, e a gravação seguinte **substitui o arquivo inteiro**: parâmetros, tema, modelo serializado e correções de outros arquivos somem.
- **Correção:**

```python
def save_corrections_state(self) -> bool:
    ctx = self.session_context
    with CONFIG_LOCK:
        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                config = loaded if isinstance(loaded, dict) else {}
            except (OSError, ValueError):
                backup = f"{self.config_file}.corrupt-{int(time.time())}"
                try:
                    os.replace(self.config_file, backup)    # preserva o original antes de recriar
                except OSError:
                    return False                            # não sobrescreve sem preservar
        config["corrections_by_file"] = ctx.corrections_by_file
        atomic_write_json(self.config_file, config)         # helper do relatório anterior (D2)
        return True
```

### R8 (M) `updater.py` com as duas classes de thread duplicadas [EXEC]
`UpdateCheckerThread` e `UpdateDownloaderThread` aparecem nas linhas 92/197 **e** 299/404, idênticas. A segunda sobrescreve a primeira, inofensiva por ora, mas qualquer correção futura numa cópia é ignorada em silêncio. Apague as linhas 299-505. Também há `SyntaxWarning: invalid escape sequence '\*'` na linha 586 (`"$extractDir\*"` num f-string não raw); em versões futuras do Python vira erro.

### R9 (M) Testes enfraquecidos e agora tocam a configuração real do usuário [LEITURA]
- **Removidos 10 testes** (105 → 95):
  - `test_extract_expected_hash` e `..._multi_file_checksum`;
  - `test_launch_windows_updater_sha256_verification` e `..._require_hash`;
  - `test_50_regroup_chirps_less_than_two_peaks`;
  - `test_51_low_sample_rate_filter`;
  - `test_52` (chave i18n);
  - os três de segurança do learner: `test_53`, `test_54`, `test_55`.
- **Motivo provável:** o `test_51` passaria a falhar com o novo `ValueError` de taxa baixa. O certo era invertê-lo, não apagá-lo. Os de segurança do skops/pickle são justamente os que protegem contra a deserialização insegura.
- **Teste adulterado para casar com um bug:** `test_33` agora espera `"Moda: —   |   Média: —"`, texto fixo em português e com rótulos trocados (a outra ramificação mostra Média e Variância). A versão correta usa `I18N[lang]['mean']` e `['variance']`.
- **Risco novo:** `CONFIG_FILE` agora é `%APPDATA%\Crinometro\crinometro_config.json`, a configuração **real** do usuário. `setUp`/`tearDown` de `test_characterization_v450.py` gravam `"{}"` nesse arquivo a cada teste. Se a suíte for interrompida (crash, Ctrl-C), a configuração real fica zerada.
- **Correção:** em `constants.py`, aceite um override de ambiente e use-o nos testes:

```python
def _user_config_dir():
    override = os.environ.get("CRINOMETRO_CONFIG_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "Crinometro")
    os.makedirs(d, exist_ok=True)
    return d
# tests: os.environ["CRINOMETRO_CONFIG_DIR"] = tempfile.mkdtemp()  ANTES de importar utils.constants
```

Restaure os 10 testes (inverta o `test_51` para `assertRaises(ValueError)`) e acrescente um teste que importe `main` e `crinometro`, o que teria pego R1.

### R10 (B) Outros pontos da migração para `%APPDATA%` [LEITURA]
- Só o JSON é copiado do legado. O `modelo_treinado.skops` (os dados de treino) não é migrado.
- `os.makedirs` roda no import de `constants.py`. Se `%APPDATA%` não for gravável, o app inteiro falha ao importar.
- A cópia do JSON usa o CWD no momento do import.
- Ponto positivo: como a configuração saiu da pasta de instalação, ela agora sobrevive a atualizações.

### R11 (B) `load_persisted_training` renomeia arquivo para `.corrupt-*` em **qualquer** exceção [LEITURA]
Inclui falhas transitórias (`PermissionError`, tipo não confiável após atualizar o skops). O arquivo bom vai embora sem aviso. Restrinja o rename a erros de parse (`skops.io` / `ValueError` / `EOFError`), e exponha `learner.degraded` e `learner.last_error` na UI. Hoje **nada** lê esses campos.

---

## 4. Status dos achados do beta39

| ID | Achado | Status no beta41 |
|---|---|---|
| A1 | `QThread` sobrescrito | **Parcial.** Guardas e `_retain` entraram no orquestrador e no `learn_from_corrections`. O `ExportController` quebra (R3). |
| A2 | Sem `closeEvent` | **Aberto.** `shutdown()` foi criado e **nunca é chamado**. `MainWindow` continua sem `closeEvent`. |
| A3 | Abort / lote reiniciado | **Parcial, com regressão (R4).** |
| A4 | Corrida no `PulseLearner` | **Aberto.** `_model_lock` é criado e **nunca usado**. `_adapt_advanced_params` saiu da thread só no `editor_controller`. Em `force_reanalyze._task` ainda roda no worker. |
| A5 | Spinner do lote | **Corrigido** nos 3 handlers (mas `_on_batch_cancelled` nunca dispara, R4). |
| A6 | `excepthook` | **Parcial.** Lógica boa, mas apagou a função usada (R1). |
| B1 | NaN/Inf | **Aberto** [EXEC]: segue sem exceção, 0 chilreios, `env` não finito. |
| B2 | Taxa baixa | **Corrigido** [EXEC]: 6 kHz agora levanta `ValueError` claro. 8 kHz segue ok (15/15). O `elif` seguinte virou código morto. |
| B3 | Clip antes do espectro | Aberto |
| B4 | Sem limite de memória | Aberto |
| B5 | `analysis_cache` sem LRU | Aberto |
| B6 | LoD do espectrograma | Aberto |
| C1 | Vazamento do prior | **Corrigido** (feature removida), com R5 e R6. |
| C2 | Falhas de ML silenciosas | **Parcial.** `degraded`/`last_error` só no `except` do load. `filter_peaks` ainda devolve "aceitar tudo" sem registrar, e nenhuma UI lê o estado. |
| C3 | Alinhamento de features | **Parcial.** Validado no load/import. `predict` e `filter_peaks` ainda cortam/preenchem com zeros. |
| C4 | `np.unique` | **Corrigido.** Mantém a ordem cronológica. |
| C5 | Guarda de modelo degenerado, GMM | Aberto |
| D1 | `CONFIG_FILE` relativo | **Corrigido** (`%APPDATA%`), com R10. |
| D2 | Gravação não atômica | **Aberto.** `save_settings`, reset e `save_to_config` seguem com `open(..., 'w')`. |
| D3 | Config sem validação | Aberto |
| D4 | Parâmetros do relatório sem overrides | Aberto |
| D5 | Métricas obsoletas com < 2 picos | Aberto |
| D6 | `batch_update` descarta notificações | Aberto |
| E1 | Cmdlets PowerShell inexistentes | **Aberto.** `launch_windows_updater` não mudou. |
| E2 | Apóstrofo, `os._exit` | Aberto |
| E3 | Confiança do hash | Aberto |
| E4 | HTML sem escape | Aberto |
| E5 | Parse de versão | **Corrigido.** Atenção: `is_version_newer` agora compara o patch também. Um `.skops` exportado por 4.5.1 passa a ser recusado no 4.5.0. |
| E6 | `Esc` fecha o diálogo | Aberto |
| F1 | TXT corrompido | **Corrigido.** Bloco removido. |
| F2 | Relatório lê cache compartilhado | **Parcial.** Cópia rasa + `deepcopy` dos parâmetros. Útil, mas o retain falha (R3). |
| F3 | Definições duplicadas | **Parcial.** `report_generator` limpo. `CHANGELOG_FULL` continua duplicado (linhas 104 e 166), e a segunda definição não tem 4.4.x nem 4.5.0. |
| F4 | Dependências e higiene | **Parcial.** Saíram `crinometro_config.json`, `modelo_treinado.skops`, `temp*.txt` e `audit_results.txt`. Seguem os `patch_*.py`, e entraram `remove_prints_ec.py` e `restore_ec.py`. README e `requirements.txt` ainda sem `skops`. |

**Contagem:** corrigidos 8 (A5, B2, C1, C4, D1, E5, F1 e o item de `CHANGELOG`/duplicatas do `report_generator`), parciais 7, abertos 18.

---

## 5. Quality gate: por que não pegou nada

O `scripts/quality_gate.py` rodou e deu **PASS** no beta41, que não inicia. Ele valida codificação, sintaxe e globais indefinidas dentro de funções, mas não resolve imports locais nem atributos de `self`.

Escrevi uma verificação complementar (`gate_extra.py`, anexa). Ela checa:
1. `from core|ui|utils.X import nome` resolve;
2. `self._privado()` existe na classe ou numa base;
3. kwargs de dataclasses locais existem.

Rodei contra os dois zips:
- **beta41:** falha com exatamente os quatro problemas bloqueantes (R1 ×2, R3, R2).
- **beta39:** passa limpa (controle).

Ligue-a no `quality_gate.py` (`from gate_extra import ...` ou chame como subprocesso) e acrescente:
- `python -W error::SyntaxWarning -m compileall core ui utils main.py crinometro.py` (pega o `\*` do updater);
- `python -m unittest discover tests` com `QT_QPA_PLATFORM=offscreen` e `CRINOMETRO_TESTING=1`, falhando o gate se o número de testes cair em relação ao anterior (um limiar em arquivo versionado) — isso pegaria a remoção silenciosa dos 10 testes;
- falha se existir `patch_*.py`, `restore_*.py` ou `remove_prints_*.py` na raiz.

---

## 6. Ordem sugerida

1. **R1, R2, R3** (o app volta a iniciar e a exportar). Depois rode `gate_extra.py` até dar `OK`.
2. **R4** (conectar `cancelled_signal`) + `closeEvent` chamando `pipeline.shutdown()` e `export_controller.shutdown()` (A2) + usar `_model_lock` de fato (A4).
3. **R5, R6, R7** (perda de dados de treino e de configuração).
4. Restaurar os 10 testes e isolar a configuração dos testes (R9).
5. B1 (NaN/Inf) e D2 (escrita atômica), cujas correções estão no relatório anterior.
6. E1/E2 (updater PowerShell), cujo script corrigido também está no relatório anterior.
7. Resto da tabela.
