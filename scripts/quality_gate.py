#!/usr/bin/env python3
"""
Portão de Qualidade Arquitetural (Quality Gate) - Crinômetro v4.5.0
Valida:
1. Codificação (UTF-8 sem BOM, ausência de mojibake como Ã¡, Ã©, etc.)
2. Análise estática por AST e Symtable (detecção real de NameError / variáveis indefinidas)
3. Preservação de integridade estrutural
"""

import os
import sys
import ast
import symtable
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
            line_no = text[:match.start()].count("\n") + 1
            errors.append(f"{filepath}:{line_no}: Detectado mojibake ('{match.group(0)}')")
            break

    return errors

def check_ast_syntax_and_symbols(filepath):
    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code, filename=filepath)
    except Exception as e:
        errors.append(f"{filepath}: Erro de sintaxe AST: {e}")
        return errors

    # Verificação de tabela de símbolos (symtable) para detectar NameError em escopos locais
    try:
        st = symtable.symtable(code, filepath, "exec")
        module_globals = (
            set(st.get_identifiers())
            | set(dir(__builtins__))
            | {"__file__", "__name__", "__doc__", "__package__"}
        )

        def walk(table, path):
            for child in table.get_children():
                child_path = f"{path}.{child.get_name()}"
                if child.get_type() == "function":
                    for sym in child.get_symbols():
                        if sym.is_global() and sym.get_name() not in module_globals:
                            errors.append(f"{filepath} em {child_path}: Nome global indefinido '{sym.get_name()}'")
                walk(child, child_path)

        walk(st, os.path.basename(filepath))
    except Exception as e:
        errors.append(f"{filepath}: Erro na análise de tabela de símbolos: {e}")

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
                all_errors.extend(check_ast_syntax_and_symbols(fp))

    if all_errors:
        print("FAIL: Quality Gate encontrou problemas:")
        for err in all_errors:
            print("  -", err)
        return 1

    print("PASS: Quality Gate passou com sucesso (Codificação UTF-8 pura, sem BOM, sem mojibake, sintaxe AST íntegra e zero NameError).")
    return 0

if __name__ == "__main__":
    sys.exit(run_gate())
