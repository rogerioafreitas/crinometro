"""
Teste de integração da transição de estados de atualização do Launcher com timer de segurança.
"""
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import crinometro__laucher


class TestLauncherUpdateTransitions(unittest.TestCase):

    def setUp(self):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)

    def test_launcher_status_transitions_and_error_handling(self):
        """Valida que o launcher atualiza seus textos de status e não trava caso ocorra erro."""
        splash = crinometro__laucher.LauncherLoadingScreen()
        splash.show()

        # Simula download a 100%
        splash._on_download_progress(100)
        self.assertEqual(splash.update_progress, 100)
        self.assertIn("100%", splash.update_status_text)

        # Simula download concluído
        splash._on_download_finished("dummy_file_path.exe")
        self.assertEqual(splash.update_status_text, "Verificando arquivos...")

        # Simula chamada a _step_install_files com arquivo inexistente para testar try/except
        splash._step_install_files("caminho_inexistente_que_vai_dar_erro.bin")
        # Se launch_windows_updater conseguir gerar script, status vai para 'Instalando arquivos...'
        # E o timer de reinicialização é agendado sem travar
        self.assertIn(splash.update_status_text, ["Instalando arquivos...", "Erro na instalação. Iniciando versão atual..."])

        splash.close()


if __name__ == "__main__":
    unittest.main()
