# Re-auditoria — Crinômetro 4.5.0 beta43 (contra a beta42)

## Método e limites

- `diff` arquivo a arquivo contra a beta42 (ignorando CRLF/LF), com cada achado N1–N15 reverificado.
- **[EXEC]** = rodei. **[ESTÁTICO]** = AST ou assinatura de função conferida no código. **[LEITURA]** = deduzido.
- Rodei: `compileall` com `SyntaxWarning` como erro, `gate_extra2.py`, o analisador com 11 entradas sintéticas/patológicas, os 2 testes `test_characterization_dsp` (com PyQt6 e skops substituídos por stubs), o teste de contenção do lock do learner e as chamadas exatas que os testes novos fazem.
- **Limite que continua:** PyQt6 e skops não instalam aqui. Não executei a GUI nem a suíte completa (112 testes).

---

## 1. Veredito

| | beta41 | beta42 | **beta43** |
|---|---|---|---|
| Nota técnica | 40 | 66 | **70 / 100** |
| Risco | Crítico | Alto | **Médio-Alto** |

**Resolvidos desde a beta42:** N1 (sinais de volta ao `__init__`), N2 (LRU removido; era a opção segura), N3 (`closeEvent` com os nomes certos, salva config e chama `shutdown` dos três controllers), N4 (treino fora do lock, medido: leitor bloqueado 1,70 s → 0,00 s [EXEC]), N7 (README), N11 (`AllowEmptyString`), N13 (retenção só em `finished`), N14 (gate não reescreve mais o `.min_test_count`), N10 em parte (`install.ps1` saiu) e o "Versão" do CHANGELOG.

**Mas a beta43 introduz regressões novas e deixa a suíte vermelha.** Resumo:

1. **N16 (A):** quatro dos testes "consertados" **erram** ao executar (chamam API que não existe). A suíte não passa.
2. **N17 (M):** o B3 foi desfeito: o espectrograma e o PSD voltam a ser calculados sobre o sinal recortado.
3. **N18 (M):** `filter_peaks` perdeu a rede de segurança "se todos os picos foram podados, mantenha os 25% de maior prior". Mudança de comportamento fora do escopo de qualquer achado.
4. **N19 (M):** `requirements.txt` está corrompido (barras `\n` literais numa linha só).
5. **N20 (M):** o `gate_extra.py` foi **removido do repositório e do gate**, e 10 scripts `fix_*.py` entraram na raiz sem que o gate reclame.
6. **N21 (B):** o updater passou a renomear qualquer pasta cujo nome começa com "crin".

Continuam abertos: **N6** (`save_corrections_state` ainda pode apagar a configuração inteira) e **N8** (14 versões do histórico ainda faltam).

---

## 2. Defeitos novos

### N16 (A) Testes novos que quebram [EXEC]
Executei as chamadas exatas de cada teste:

| Teste | Resultado |
|---|---|
| `test_50_regroup_chirps_less_than_two_peaks` | `AttributeError`: `CricketAnalyzer._regroup_chirps` não existe (o método é `regroup_chirps(peaks, params, rate, env, raw_signal=None)`). |
| `test_54_learner_security_pickle` | `TypeError`: `PulseLearner(None)` faz `os.path.abspath(None)`; além disso `load_persisted_training` não recebe argumento. |
| `test_55_learner_security_other` | Idem. |
| `test_launch_windows_updater_require_hash` | `TypeError`: `launch_windows_updater` não tem o parâmetro `require_hash`. `assertRaises(ValueError)` não captura `TypeError`. |
| `test_launch_windows_updater_sha256_verification` | **Passa** (levanta `ValueError`, como esperado). |
| `test_51_low_sample_rate_filter` | Roda, mas **não testa nada**: analisa o `sample_chirp.wav` com parâmetros padrão e confere `assertIsNotNone`. Devia ser `assertRaises(ValueError)` com um WAV de 6 kHz. |
| `test_52`, `test_53` | Continuam fracos (ver beta42). |

Além disso, `test_export_controller_generate_pdf` (novo) chama `ctrl._report_worker.run()` **depois** de `_generate_pdf_report_modular` já ter dado `worker.start()`: o corpo roda duas vezes (uma na thread, outra na principal), e a segunda dispara `_on_finished`, que abre um `QMessageBox.information(self.main_window, ...)` com uma `QObject` falsa como pai. Pode travar ou abortar o runner [LEITURA]; só rodando com PyQt6 para confirmar. Troque por `QSignalSpy`/`QEventLoop` aguardando `finished_signal` e faça patch de `QMessageBox`.

O que passa com esforço mínimo (`test_connects_pipeline_signals` é bom e pega o N1):

```python
def test_50_regroup_chirps_less_than_two_peaks(self):
    from core.analyzer import CricketAnalyzer
    env = np.ones(16000)
    out = CricketAnalyzer.regroup_chirps(np.array([100]), DEFAULT_ALGO_PARAMS.copy(), 16000, env)
    self.assertEqual(out[0], [])                      # sem chilreios
    self.assertEqual(out[3], 0)                       # moda zerada

def test_51_low_sample_rate_filter(self):
    path = self._make_wav(sr=6000, f=2800)            # helper: WAV sintético em arquivo temporário
    with self.assertRaisesRegex(ValueError, "Nyquist"):
        CricketAnalyzer.analyze(path, DEFAULT_ALGO_PARAMS.copy())

def test_54_learner_rejects_untrusted_skops(self):
    # grave um .skops que contenha um tipo fora da lista de confiança e verifique que NÃO carrega
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "cfg.json")
        L = PulseLearner(config_path=cfg)
        skio.dump({"model": object(), "feature_names": L.feature_names}, L.persistence_path)  # tipo não confiável
        self.assertFalse(L.load_persisted_training())
        self.assertTrue(L.degraded)

def test_55_learner_rejects_legacy_pickle(self):
    with tempfile.TemporaryDirectory() as td:
        L = PulseLearner(config_path=os.path.join(td, "cfg.json"))
        with open(L.persistence_path.replace(".skops", ".pkl"), "wb") as f:
            pickle.dump({"model": object()}, f)        # não pode ser executado/carregado
        self.assertFalse(L.load_persisted_training())
```
Para o `require_hash`, o comportamento real está em `UpdateDownloaderThread` (`require_hash=True` recusa sem hash, linha 224), então o teste certo é sobre ela (`downloader.run()` com `expected_hash=""` emite `error`), não sobre `launch_windows_updater`.

### N17 (M) B3 desfeito: espectro de novo sobre sinal recortado [EXEC]
- **Local:** `core/analyzer.py:107-108, 125, 303`. Para economizar a cópia `data_norm` (N15), o código voltou a `np.clip(data, -1, 1, out=data)` **antes** do espectrograma e do PSD.
- **Medido:** num sinal com um estalo alto, o `Sxx_db` com e sem clip difere em até **57 dB**. A contagem de pulsos/chilreios não muda, mas o espectro publicado e o `dom_freqs` sim.
- **Correção sem custo de memória:** `data` só é usado no espectrograma (l. 125) e no PSD (l. 303). Basta mover o clip para depois do PSD:

```python
data = data / raw_scale                      # sem clip
...
f_spec, t_spec, Sxx = spectrogram(data, rate, nperseg=1024, noverlap=768)   # sem clip
...
f_psd, Pxx_db = CricketAnalyzer.compute_psd(data, rate)                     # sem clip
np.clip(data, -1.0, 1.0, out=data)           # só agora, para o oscilograma
return (rate, data.astype(np.float32), ...)
```

### N18 (M) Rede de segurança removida de `filter_peaks` [ESTÁTICO]
- **Local:** `learner.py`, ramo sem modelo (≈ l. 720). O `fix_c2c3.py` apagou:

```python
if not np.any(kept_mask) and len(priors) > 0:
    kept_mask = (priors >= np.percentile(priors, 75))
```
  (o script o chama de "blind acceptance", mas é o contrário: **evita** descartar tudo). Com ele fora, uma gravação em que o gate GMM + piso de amplitude poda todos os picos devolve **zero chilreios** sem aviso.
- **Correção:** restaure o bloco. Se a intenção era sinalizar o caso, mantenha o resgate **e** registre `logging` e `degraded=True`.
- **Também:** `predict()` perdeu o `try/except` e o `astype(int)`: qualquer exceção do sklearn agora sobe até a GUI/worker. Prefira capturar, logar, marcar `degraded` e devolver um sinal claro (por exemplo, levantar uma exceção própria `ModelUnavailable` que `filter_peaks` já trata), em vez de nada.
- **Para ficar claro o que melhorou:** a remoção do pad/truncate de features (C3) é correta e estava no escopo.

### N19 (M) `requirements.txt` corrompido [ESTÁTICO]
O arquivo tem **uma única linha** com barras e "n" literais (`PyQt6\nnumpy\nscipy...`; confirmado com `od -c`). `pip install -r requirements.txt` falha. Escreva uma dependência por linha e fixe versões (`PyQt6==6.x`, `numpy==...`, etc., as que a build empacotada usa).

### N20 (M) Gate enfraquecido e artefatos de patch de volta [ESTÁTICO]
- `gate_extra.py` saiu do repositório e **do `quality_gate.py`** (o bloco de import/execução foi apagado). Os defeitos que ele pegava (imports locais, `self._x()`, kwargs de dataclass) voltam a passar despercebidos. O `gate_extra2.py` que eu enviei passa (OK), mas só cobre outra classe de erro.
- A lista de arquivos proibidos continua `patch_*.py`, `restore_*.py`, `remove_prints_*.py`. Entraram **10 scripts novos** (`fix_c2c3.py`, `fix_ed3.py`, `fix_elif.py`, `fix_n12.py`, `fix_n15.py`, `fix_qg.py`, `fix_qg2.py`, `fix_t3.py`, `fix_up.py`, `fix_up2.py`), que o gate não vê. Também ficou `r2r3.txt`.
- **Correção:** recoloque `gate_extra.py` (e `gate_extra2.py`) e chame os dois no `quality_gate.py`; troque os padrões proibidos por `fix_*.py`, `patch_*.py`, `restore_*.py`, `remove_prints_*.py`, `*.txt` de rascunho na raiz.

### N21 (B) Updater renomeia qualquer pasta que comece com "crin" [ESTÁTICO]
`if base_name.lower().startswith("crin"): target_dir = os.path.join(parent_dir, "Crinometro")`. Uma instalação em `C:\Apps\crinometro-beta` ou `D:\Crin Lab` passa a ser atualizada em `C:\Apps\Crinometro` (outra pasta), e a instalação em uso fica intacta. O objetivo era normalizar nomes corrompidos (`Crin�metro`); restrinja a: o nome ser exatamente `Crinômetro`, `Crin?metro` ou conter `\ufffd`, e **não** renomeie se o diretório não existir.

### Observações menores
- `constants.py`: o texto do CHANGELOG 4.4.1 agora tem um caractere U+FFFD real (antes mostrava a sequência `\ufffd` literal). Cosmético.
- `update_dialog.py` ainda chama `downloader.wait()` na GUI thread em `reject()` (N12).
- `fix_elif.py` apagou o `elif` morto (N15, OK), mas a economia de memória que justificou N17 se resolve como mostrado acima.

---

## 3. Status dos itens abertos na beta42

| ID | beta43 |
|---|---|
| N1 | **Corrigido** (e há teste que pega: `receivers > 0`). |
| N2 | **Corrigido** por reversão do LRU (B5 volta a ficar aberto: o cache segue sem limite). |
| N3 | **Corrigido.** `EditorController.shutdown()` espera o worker sem timeout; aceitável, mas um treino longo atrasa o fechamento. |
| N4 | **Corrigido** [EXEC]. `fit()` (usado em outro caminho) ainda treina dentro do lock. |
| N5 | **Parcial e pior** (N16: quatro testes erram, um continua vazio). O `test_r3` agora usa o `ExportController`, o que é um avanço. |
| N6 | **Aberto.** `save_corrections_state` sem lock, `config = {}` em falha de leitura, sobrescreve tudo. |
| N7 | **Corrigido.** |
| N8 | **Aberto** (14 versões do CHANGELOG faltam; "Versão" corrigido). |
| N9 | Parcial (corrigiram "Versão"; ainda há "incompatveis", "parmetros" etc.). |
| N10 | Parcial (`install.ps1` saiu; `r2r3.txt` e os `fix_*.py` ficam). |
| N11 | **Corrigido.** |
| N12 | Aberto. |
| N13 | **Corrigido.** |
| N14 | **Corrigido** (sem escrita automática). Mas o gate ainda aceita testes `pass` e agora não roda o `gate_extra`. |
| N15 | Parcial (`elif` morto removido; B3 desfeito, ver N17). |
| B3 | **Aberto de novo** (N17). |
| C3 | **Corrigido** (sem pad/truncate; dimensão divergente agora levanta erro no `vstack`/sklearn, o que é o comportamento certo, desde que o carregamento rejeite modelos de outra dimensão, o que `_features_compatible` já faz). |
| DSP | Sem mudança numérica nas 11 entradas [EXEC]; os 2 testes de caracterização passam. |

---

## 4. Ordem de correção sugerida

1. **N16**: conserte os 4 testes que erram (código acima) e confirme `Ran N tests … OK` num ambiente com PyQt6 e skops. Sem isso nenhum outro item é verificável.
2. **N20 e N19**: restaurar `gate_extra.py` no gate, proibir `fix_*.py`, corrigir `requirements.txt`; remover os 10 scripts e `r2r3.txt`.
3. **N18** (restaurar o resgate dos 25%) e **N17** (mover o clip).
4. **N6** (`save_corrections_state`, código do relatório da beta41).
5. **N8** (mesclar as duas versões do CHANGELOG), **N21**, **N9**.
6. B5 (cache limitado, desta vez com reidratação), B4 configurável, N12.

**Regra que teria evitado a maior parte disso:** nenhum commit pode apresentar um teste sem antes ter executado ele; o `Ran N tests … OK` da suíte completa, colado no commit, é o único comprovante aceito.
