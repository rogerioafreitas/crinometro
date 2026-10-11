#!/usr/bin/env python3
"""Verificações extras (parte 2) para scripts/quality_gate.py.

 (a) check_vacuous_tests: nenhum teste vazio (corpo ``pass``/docstring, sem asserção,
     ou cuja única verificação é ``assertIsNotNone``);
 (b) check_generic_assert_raises: proibido ``assertRaises(Exception)`` genérico;
 (c) check_forbidden_root_files: arquivos de patch/lixo proibidos na raiz.
"""
import ast
import fnmatch
import glob
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

FORBIDDEN_ROOT_PATTERNS = (
    "fix_*.py", "patch_*.py", "restore_*.py", "apply_*.py", "remove_prints_*.py",
    "*.skops", "crinometro_config.json", "temp*.txt", "r2r3.txt", "install.ps1",
)


def _parse(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _assert_calls(func):
    """Nomes (atributo) das chamadas de asserção dentro do teste; 'raise'/'fail' contam."""
    names = []
    for n in ast.walk(func):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name.startswith("assert") or name in ("fail", "skipTest"):
                names.append(name)
        elif isinstance(n, ast.Assert):
            names.append("assert")
        elif isinstance(n, ast.Raise):
            names.append("raise")
    return names


def check_vacuous_tests(files):
    errs = []
    for f in files:
        for cls in [n for n in ast.walk(_parse(f)) if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        or not fn.name.startswith("test"):
                    continue
                body = [s for s in fn.body
                        if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                                and isinstance(s.value.value, str))]
                where = f"{f}:{fn.lineno}: {cls.name}.{fn.name}"
                if not body or all(isinstance(s, ast.Pass) for s in body):
                    errs.append(f"{where}: teste vazio (corpo 'pass')")
                    continue
                calls = _assert_calls(fn)
                if not calls:
                    errs.append(f"{where}: teste sem nenhuma asserção")
                elif all(c == "assertIsNotNone" for c in calls):
                    errs.append(f"{where}: única verificação é assertIsNotNone")
    return errs


def check_generic_assert_raises(files):
    errs = []
    for f in files:
        for n in ast.walk(_parse(f)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and n.func.attr in ("assertRaises", "assertRaisesRegex") and n.args \
                    and isinstance(n.args[0], ast.Name) and n.args[0].id in ("Exception", "BaseException"):
                errs.append(f"{f}:{n.lineno}: {n.func.attr}({n.args[0].id}) genérico")
    return errs


def check_forbidden_root_files(root=ROOT):
    errs = []
    for name in os.listdir(root):
        if os.path.isfile(os.path.join(root, name)) and \
                any(fnmatch.fnmatch(name, p) for p in FORBIDDEN_ROOT_PATTERNS):
            errs.append(f"arquivo proibido na raiz: {name}")
    return errs


def run(root=ROOT):
    files = glob.glob(os.path.join(root, "tests", "**", "test*.py"), recursive=True)
    return (check_vacuous_tests(files) + check_generic_assert_raises(files)
            + check_forbidden_root_files(root))


if __name__ == "__main__":
    errs = run()
    print("\n".join(errs) or "OK")
    sys.exit(1 if errs else 0)
