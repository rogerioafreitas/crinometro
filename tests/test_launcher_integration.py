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


from unittest.mock import patch


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

        # Simula sucesso na instalação com mock
        with patch("crinometro__laucher.launch_windows_updater") as mock_updater:
            splash._step_install_files("dummy_file_path.exe")
            mock_updater.assert_called_once_with("dummy_file_path.exe")
            self.assertEqual(splash.update_status_text, "Instalando arquivos...")

        # Simula exceção na chamada para validar resiliência do try/except
        with patch("crinometro__laucher.launch_windows_updater", side_effect=RuntimeError("Falha de teste")):
            splash._step_install_files("dummy_file_path.exe")
            self.assertEqual(splash.update_status_text, "Erro na instalação. Iniciando versão atual...")

        splash.close()


if __name__ == "__main__":
    unittest.main()
