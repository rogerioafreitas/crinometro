#!/usr/bin/env python3
"""Verificações extras para scripts/quality_gate.py:
 (a) 'from core|ui|utils.X import nome' precisa resolver;
 (b) 'self._privado(...)' precisa existir na classe ou numa base do repositório;
 (c) kwargs de dataclasses locais precisam existir (ex.: ReportSectionFlags(dolbear=...))."""
import ast, glob, os, sys

ROOTS = ("core", "ui", "utils")
# métodos privados herdados de bibliotecas externas (reportlab, Qt...)
EXTERNAL_PRIVATE = {"_startPage"}

def _parse(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)

def _top_names(tree):
    s = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            s.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            s.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                s.add((a.asname or a.name).split(".")[0])
    return s

def check_imports(files):
    errs = []
    cache = {}
    for f in files:
        for n in ast.walk(_parse(f)):
            if isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in ROOTS:
                p = n.module.replace(".", "/")
                path = next((c for c in (p + ".py", p + "/__init__.py") if os.path.exists(c)), None)
                if path is None:
                    errs.append(f"{f}:{n.lineno}: módulo local inexistente '{n.module}'")
                    continue
                names = cache.setdefault(path, _top_names(_parse(path)))
                for a in n.names:
                    if a.name != "*" and a.name not in names and not os.path.exists(f"{p}/{a.name}.py"):
                        errs.append(f"{f}:{n.lineno}: '{a.name}' não existe em {n.module}")
    return errs

def check_private_self_calls(files):
    classes = {}
    for f in files:
        for c in [n for n in ast.walk(_parse(f)) if isinstance(n, ast.ClassDef)]:
            attrs = {m.name for m in c.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for n in ast.walk(c):
                if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store) \
                        and isinstance(n.value, ast.Name) and n.value.id == "self":
                    attrs.add(n.attr)
            for m in c.body:
                if isinstance(m, ast.Assign):
                    attrs |= {t.id for t in m.targets if isinstance(t, ast.Name)}
            classes[c.name] = (f, c, attrs)
    errs = []
    for name, (f, c, attrs) in classes.items():
        known = set(attrs)
        stack = [b.id for b in c.bases if isinstance(b, ast.Name)]
        while stack:
            b = stack.pop()
            if b in classes:
                known |= classes[b][2]
                stack += [x.id for x in classes[b][1].bases if isinstance(x, ast.Name)]
        for n in ast.walk(c):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "self" \
                    and n.func.attr.startswith("_") and not n.func.attr.startswith("__") \
                    and n.func.attr not in known and n.func.attr not in EXTERNAL_PRIVATE:
                errs.append(f"{f}:{n.lineno}: {name}.{n.func.attr}() não está definido")
    return errs

def check_dataclass_kwargs(files):
    dcs = {}
    for f in files:
        for c in [n for n in ast.walk(_parse(f)) if isinstance(n, ast.ClassDef)]:
            if any((isinstance(d, ast.Name) and d.id == "dataclass") or
                   (isinstance(d, ast.Call) and getattr(d.func, "id", "") == "dataclass") for d in c.decorator_list):
                dcs[c.name] = {s.target.id for s in c.body if isinstance(s, ast.AnnAssign)}
    errs = []
    for f in files:
        for n in ast.walk(_parse(f)):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) in dcs:
                for kw in n.keywords:
                    if kw.arg and kw.arg not in dcs[n.func.id]:
                        errs.append(f"{f}:{n.lineno}: {n.func.id}() não aceita '{kw.arg}'")
    return errs

if __name__ == "__main__":
    files = [p for d in ROOTS for p in glob.glob(f"{d}/**/*.py", recursive=True)]
    files += ["main.py", "crinometro.py", "crinometro__laucher.py"]
    files = [f for f in files if os.path.exists(f)]
    errs = check_imports(files) + check_private_self_calls(files) + check_dataclass_kwargs(files)
    print("\n".join(errs) or "OK")
    sys.exit(1 if errs else 0)
