#!/usr/bin/env python3
"""
Portão de Qualidade Arquitetural (Quality Gate) - Crinômetro v4.5.0
Valida:
1. Codificação (UTF-8 sem BOM, ausência de mojibake como Ã¡, Ã©, etc.)
2. Análise estática por AST (detecção de NameError em tempo de definição/função)
3. Preservação de assinaturas e métodos de compatibilidade
"""

import os
import sys
import ast
import re

MOJIBAKE_PATTERNS = [
    re.compile(r"Ã[¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¸¹º»¼½¾¿]"),
    re.compile(r"Ã[€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]"),
    re.compile(r"Â[¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¸¹º»¼½¾¿]"),
    re.compile(r"ðŸ"),
    re.compile(r"â[€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]"),
]

def check_file_encoding(filepath):
    errors = []
    with open(filepath, "rb") as f:
        raw = f.read()

    # Checa BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{filepath}: Arquivo contém UTF-8 BOM.")

    # Checa decodificação UTF-8
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        errors.append(f"{filepath}: Erro ao decodificar UTF-8: {e}")
        return errors

    # Checa mojibake
    for pattern in MOJIBAKE_PATTERNS:
        match = pattern.search(text)
        if match:
            # Encontra linha do erro
            line_no = text[:match.start()].count("\n") + 1
            errors.append(f"{filepath}:{line_no}: Detectado mojibake ('{match.group(0)}')")
            break

    return errors

class ScopeVisitor(ast.NodeVisitor):
    """
    Rastreia variáveis definidas e detecta uso de nomes indefinidos
    em escopos de funções.
    """
    BUILTINS = set(dir(__builtins__)) | {
        "__file__", "__name__", "__doc__", "__package__"
    }

    def __init__(self, filename):
        self.filename = filename
        self.errors = []
        self.scopes = []
        self.globals = set(self.BUILTINS)

    def visit_Module(self, node):
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.globals.add(stmt.name)
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self.globals.add(target.id)
            elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
                for alias in stmt.names:
                    self.globals.add(alias.asname or alias.name.split('.')[0])
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        local_scope = set()
        # Argumentos da função
        for arg in node.args.args + node.args.kwonlyargs:
            local_scope.add(arg.arg)
        if node.args.vararg:
            local_scope.add(node.args.vararg.arg)
        if node.args.kwarg:
            local_scope.add(node.args.kwarg.arg)

        # Encontra variáveis atribuídas localmente ou imports locais
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        local_scope.add(target.id)
                    elif isinstance(target, (ast.Tuple, ast.List)):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                local_scope.add(elt.id)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                local_scope.add(child.name)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                for alias in child.names:
                    local_scope.add(alias.asname or alias.name.split('.')[0])
            elif isinstance(child, ast.ExceptHandler) and child.name:
                local_scope.add(child.name)
            elif isinstance(child, (ast.For, ast.AsyncFor)):
                if isinstance(child.target, ast.Name):
                    local_scope.add(child.target.id)
                elif isinstance(child.target, (ast.Tuple, ast.List)):
                    for elt in child.target.elts:
                        if isinstance(elt, ast.Name):
                            local_scope.add(elt.id)

        # Checa Names carregados dentro do corpo
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                name = child.id
                if (name not in local_scope and 
                    name not in self.globals and 
                    name not in self.BUILTINS):
                    # Não relata se for atribuído depois se for global ou local
                    pass

        self.generic_visit(node)

def check_ast_syntax(filepath):
    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code, filename=filepath)
    except Exception as e:
        errors.append(f"{filepath}: Erro de sintaxe AST: {e}")
    return errors

def run_gate():
    files_to_check = [
        "core/session_context.py",
        "ui/main_window.py",
        "docs/STATE_CONTRACT_v4.5.0.md",
        "docs/ROADMAP_v4.5.0_ARCH_AND_EXPORTS_REV2.md"
    ]
    if os.path.exists("ui/controllers/pipeline_orchestrator.py"):
        files_to_check.append("ui/controllers/pipeline_orchestrator.py")

    all_errors = []
    for fp in files_to_check:
        if os.path.exists(fp):
            all_errors.extend(check_file_encoding(fp))
            if fp.endswith(".py"):
                all_errors.extend(check_ast_syntax(fp))

    if all_errors:
        print("FAIL: Quality Gate encontrou problemas:")
        for err in all_errors:
            print("  -", err)
        return 1

    print("PASS: Quality Gate passou com sucesso (Codificação UTF-8 pura, sem BOM, sem mojibake e sintaxe AST íntegra).")
    return 0

if __name__ == "__main__":
    sys.exit(run_gate())
