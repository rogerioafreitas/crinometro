"""
Crinômetro - Ponto de Entrada da Aplicação (Entry Point).
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from utils.helpers import setup_global_exception_handler
from utils.icons import get_app_icon
from ui.main_window import MainWindow
from ui.widgets import LoadingScreen


def main():
    setup_global_exception_handler()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--launcher-managed", action="store_true")
    parser.add_argument("--ready-file", default="")
    parser.add_argument("--release-file", default="")
    parser.add_argument("--shown-file", default="")
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Define o ícone global da aplicação
    icon_file = LoadingScreen._asset_path("grilinho.ico")
    if os.path.isfile(icon_file):
        app.setWindowIcon(QIcon(icon_file))
    else:
        app.setWindowIcon(get_app_icon())

    window = MainWindow()

    def write_signal(path, content):
        if not path:
            return
        try:
            path = os.path.abspath(path)
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    if not args.launcher_managed:
        window.show()
        window.raise_()
        window.activateWindow()
    else:
        # Sinaliza que MainWindow terminou de ser construída, aguardando liberação do launcher
        write_signal(args.ready_file, "ready")

        release_timer = QTimer()
        release_timer.setInterval(25)
        wait_ticks = [0]

        def release_when_requested():
            wait_ticks[0] += 1
            if not args.release_file:
                return
            if os.path.exists(args.release_file):
                release_timer.stop()
                try:
                    window.show()
                    window.raise_()
                    window.activateWindow()
                    write_signal(args.shown_file, "shown")
                except Exception as e:
                    print(f"Erro ao exibir janela principal: {e}")
            elif wait_ticks[0] > 4800:  # 120s de timeout
                release_timer.stop()
                sys.exit(0)

        release_timer.timeout.connect(release_when_requested)
        release_timer.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
