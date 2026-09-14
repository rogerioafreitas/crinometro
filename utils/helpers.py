"""
Crinômetro - Utilitários de Diagnóstico, Exceções e Controle de Versão.
"""
import os
import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox

def setup_global_exception_handler():
    """Captura qualquer exceção não tratada na aplicação e exibe um pop-up de erro detalhado para o usuário."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)
        print("CRASH / UNHANDLED EXCEPTION:\n", tb_text, file=sys.stderr)

        if os.environ.get("CRINOMETRO_TESTING") == "1":
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        app = QApplication.instance()
        if app:
            try:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Erro Inesperado - Crinômetro")
                msg_box.setText(f"Ocorreu um erro inesperado no aplicativo:\n\n{exc_type.__name__}: {exc_value}")
                msg_box.setDetailedText(tb_text)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
            except Exception:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
        else:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception

setup_global_exception_handler()

# ==============================================================================
# VERSÃO DO APLICATIVO (Altere aqui para atualizar a versão em todo o sistema)
# Regras de versionamento (SemVer de 3 casas: X.Y.Z):
#   - Z (+1): Correção de erros, bugs visuais e pequenos ajustes (ex: 3.0.0 -> 3.0.1)
#   - Y (+1): Nova complexidade algorítmica ou alterações visuais (ex: 3.0.1 -> 3.1.0)
#   - X (+1): Apenas sob comando explícito ou manualmente pelo usuário
# ==============================================================================
APP_VERSION = "4.1.2"
# ==============================================================================

def parse_version_tuple(ver_str):
    """Converte string de versão 'X.Y.Z' para tupla de inteiros (X, Y, Z)."""
    try:
        parts = str(ver_str).strip().lstrip("v").split(".")
        return tuple(int(p) for p in parts[:3])
    except Exception:
        return (0, 0, 0)

def is_version_newer(file_ver_str, app_ver_str):
    """Retorna True se a versão do arquivo for mais nova nas casas X ou Y do que a do aplicativo."""
    f_parts = parse_version_tuple(file_ver_str)
    a_parts = parse_version_tuple(app_ver_str)
    f_major = f_parts[0] if len(f_parts) > 0 else 0
    f_minor = f_parts[1] if len(f_parts) > 1 else 0
    a_major = a_parts[0] if len(a_parts) > 0 else 0
    a_minor = a_parts[1] if len(a_parts) > 1 else 0
    if f_major > a_major:
        return True
    if f_major == a_major and f_minor > a_minor:
        return True
    return False


