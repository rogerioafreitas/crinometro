# Linha de base beta43 (Fase 0)

Ambiente: `.venv2` (Python 3.12.15); `import PyQt6, skops, sklearn, numpy, scipy, matplotlib, reportlab, PIL` OK.

- `compileall` (com `-W error::SyntaxWarning`): exit 0.
- `import main`: OK.
- `unittest discover tests -v`: **o processo morre** em `test_r3_export.TestExportControllerR3.test_export_controller_generate_pdf`
  (exit code -1073740791 / 0xC0000409, sem "Ran N tests"). Os testes depois dele não executam. Ver `unittest.txt`.
- Teste com ERROR observado antes do crash: `test_characterization_v450...test_50_regroup_chirps_less_than_two_peaks`.
  Os demais esperados (54, 55, updater require_hash) não chegaram a rodar por causa do crash (Fase 2).
- `scripts/quality_gate.py`: **quebrado** - `NameError: name 'subprocess' is not defined` (ver `quality_gate.txt`).
- `gate_extra.py` ausente da raiz; `gate_extra2.py` nunca existiu no repositório.
- `requirements.txt` contém a string literal `PyQt6\nnumpy\n...` em uma só linha.
