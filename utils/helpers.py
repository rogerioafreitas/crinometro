"""
Crinômetro - Utilitários de Diagnóstico, Exceções e Controle de Versão.
"""
import os
import sys
import traceback
import logging
import re
from PyQt6.QtWidgets import QApplication, QMessageBox

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("crinometro").error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    if os.environ.get("CRINOMETRO_TESTING") == "1":
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    from PyQt6.QtCore import QThread
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
        msg.setText("Ocorreu um erro inesperado.")
        msg.setInformativeText(str(exc_value))
        msg.setWindowTitle("Erro Crítico")
        msg.setDetailedText("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        msg.exec()
    finally:
        handle_exception._busy = False

def setup_global_exception_handler():
    sys.excepthook = handle_exception

def setup_logging():
    from logging.handlers import RotatingFileHandler
    from utils.constants import CONFIG_FILE
    log_dir = os.path.dirname(CONFIG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "crinometro.log")
    
    logger = logging.getLogger("crinometro")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

_VER_RE = re.compile(r"^\s*v?(\d+)\.(\d+)(?:\.(\d+))?")
def parse_version_tuple(ver_str):
    m = _VER_RE.match(str(ver_str))
    if not m:
        return (0, 0, 0)
    return tuple(int(g) if g is not None else 0 for g in m.groups())

def is_version_newer(latest, current):
    return parse_version_tuple(latest) > parse_version_tuple(current)
