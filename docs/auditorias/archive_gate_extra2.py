#!/usr/bin/env python3
"""Verificações adicionais (rodar na raiz do repo, junto de gate_extra.py):
 (d) hasattr/getattr(self, 'nome') com 'nome' que nunca é atribuído em lugar nenhum do projeto
     (o guard esconde o AttributeError: ex. self.export_ctrl vs self.export_controller);
 (e) '.connect(' dentro de shutdown/closeEvent/cleanup/stop (conexão de sinais em método de encerramento);
 (f) testes vazios: corpo só 'pass' ou sem nenhuma asserção."""
import ast, glob, os, sys

ROOTS = ("core", "ui", "utils")
# guards legados já existentes desde a beta41 (opcionais/mortos); remova da lista ao limpá-los
LEGACY_GHOSTS = {"action_export_pdf_full", "action_export_pdf_simple", "btn_reset_layout", "stack_layout", "_sidebar_collapsed"}

def _parse(p):
    with open(p, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=p)

def _files(dirs, extra=()):
    fs = [p for d in dirs for p in glob.glob(f"{d}/**/*.py", recursive=True)]
    return fs + [e for e in extra if os.path.exists(e)]

def check_ghost_attrs(files):
    assigned = set()
    trees = {f: _parse(f) for f in files}
    for t in trees.values():
        for n in ast.walk(t):
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                assigned.add(n.attr)
            elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                assigned.add(n.name)
            elif isinstance(n, ast.Assign):
                for tg in n.targets:
                    if isinstance(tg, ast.Name):
                        assigned.add(tg.id)
    errs = []
    for f, t in trees.items():
        for n in ast.walk(t):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("hasattr", "getattr")
                    and len(n.args) >= 2 and isinstance(n.args[0], ast.Name) and n.args[0].id == "self"
                    and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str)):
                nm = n.args[1].value
                if nm not in assigned and nm not in LEGACY_GHOSTS and not nm.startswith("__"):
                    errs.append(f"{f}:{n.lineno}: {n.func.id}(self, '{nm}') — atributo nunca atribuído no projeto")
    return errs

def check_connect_in_teardown(files):
    errs = []
    for f in files:
        for c in ast.walk(_parse(f)):
            if isinstance(c, ast.FunctionDef) and c.name in ("shutdown", "closeEvent", "cleanup", "stop", "_retain"):
                for n in ast.walk(c):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "connect":
                        # permitido em _retain (finished -> discard); proibido nos demais
                        if c.name != "_retain":
                            errs.append(f"{f}:{n.lineno}: .connect() dentro de {c.name}()")
    return errs

def check_vacuous_tests(files):
    errs = []
    for f in files:
        for c in ast.walk(_parse(f)):
            if isinstance(c, ast.ClassDef):
                for m in c.body:
                    if isinstance(m, ast.FunctionDef) and m.name.startswith("test"):
                        body = [s for s in m.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
                        if all(isinstance(s, ast.Pass) for s in body):
                            errs.append(f"{f}:{m.lineno}: teste vazio '{m.name}' (só pass)")
                            continue
                        ok = any(isinstance(n, ast.Assert) or isinstance(n, ast.With)
                                 or (isinstance(n, ast.Call) and getattr(n.func, "attr", "").startswith(("assert", "fail")))
                                 for s in m.body for n in ast.walk(s))
                        if not ok:
                            errs.append(f"{f}:{m.lineno}: teste sem asserção '{m.name}'")
    return errs

if __name__ == "__main__":
    src = _files(ROOTS, ("main.py", "crinometro.py", "crinometro__laucher.py"))
    errs = check_ghost_attrs(src) + check_connect_in_teardown(src) + check_vacuous_tests(glob.glob("tests/test_*.py"))
    if errs:
        print("FALHOU:"); [print("  -", e) for e in errs]; sys.exit(1)
    print("OK")
