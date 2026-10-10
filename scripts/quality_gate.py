#!/usr/bin/env python3
"""
Portão de Qualidade Arquitetural (Quality Gate) - Crinômetro v4.5.0
Valida:
1. Codificacao (UTF-8 sem BOM, sem corrupcao de acentos)
2. Análise estática por AST e Symtable (detecção real de NameError / variáveis indefinidas)
3. Preservação de integridade estrutural
"""

import os
import sys
import ast
import symtable
import builtins
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

    # Verificação de tabela de símbolos (symtable) para detectar referências a variáveis indefinidas
    try:
        st = symtable.symtable(code, filepath, "exec")
        module_globals = (
            set(st.get_identifiers())
            | set(dir(builtins))
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
    import glob
    files_to_check = []
    for d in ["core", "ui", "utils", "scripts", "tests"]:
        files_to_check.extend(glob.glob(f"{d}/**/*.py", recursive=True))



    all_errors = []
    for fp in files_to_check:
        if "quality_gate.py" in fp: continue
        if os.path.exists(fp):
            all_errors.extend(check_file_encoding(fp))
            if fp.endswith(".py"):
                all_errors.extend(check_ast_syntax_and_symbols(fp))


    # Import e execucao do gate_extra.py
    import subprocess
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    try:
        import gate_extra
        files = [p for d in gate_extra.ROOTS for p in __import__('glob').glob(f"{d}/**/*.py", recursive=True)]
        files += ["main.py", "crinometro.py", "crinometro__laucher.py"]
        files = [f for f in files if os.path.exists(f)]
        extra_errors = gate_extra.check_imports(files) + gate_extra.check_private_self_calls(files) + gate_extra.check_dataclass_kwargs(files)
        all_errors.extend(extra_errors)
    except Exception as e:
        all_errors.append(f"Erro ao executar gate_extra: {e}")
    
    # check patch_*.py, restore_*.py, remove_prints_*.py na raiz
    import glob
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    forbidden = []
    for pat in ['patch_*.py', 'restore_*.py', 'remove_prints_*.py']:
        forbidden.extend(glob.glob(os.path.join(root_dir, pat)))
    if forbidden:
        all_errors.append(f"Arquivos proibidos na raiz: {forbidden}")
        
    # compileall
    res_compile = subprocess.run([sys.executable, "-W", "error::SyntaxWarning", "-m", "compileall", "core", "ui", "utils", "main.py", "crinometro__laucher.py"], cwd=root_dir, capture_output=True)
    if res_compile.returncode != 0:
        all_errors.append(f"Erro no compileall: {res_compile.stderr.decode('utf-8', errors='ignore')}")

    # testes
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['CRINOMETRO_TESTING'] = '1'
    env['CRINOMETRO_CONFIG_DIR'] = __import__('tempfile').mkdtemp()
    
    res_tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=root_dir, env=env, capture_output=True, text=True)
    out_test = res_tests.stderr
    # parse ran X tests
    import re
    match = re.search(r'Ran (\d+) tests', out_test)
    ran_tests = int(match.group(1)) if match else 0
    
    min_test_count = 0
    try:
        with open(os.path.join(root_dir, 'tests', '.min_test_count'), 'r') as f:
            min_test_count = int(f.read().strip())
    except Exception:
        pass
        
    if ran_tests < min_test_count:
        all_errors.append(f"Regressao no numero de testes: rodaram {ran_tests}, esperado >= {min_test_count}")
    else:
        with open(os.path.join(root_dir, 'tests', '.min_test_count'), 'w') as f:
            f.write(str(ran_tests))
            
    if res_tests.returncode != 0:
        all_errors.append(f"Erro nos testes: {out_test[-1000:]}")
        
    if all_errors:
        print("FAIL: Quality Gate encontrou problemas:")
        for err in all_errors:
            print("  -", err)
        return 1

    print("PASS: Quality Gate completo passou com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(run_gate())
