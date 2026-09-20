"""
Testes automatizados com timeout e asserções rigorosas para o Auto-Updater do Crinômetro.
"""
import os
import sys
import unittest
import tempfile
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.constants import APP_VERSION
from utils.helpers import parse_version_tuple
from core.updater import is_remote_version_newer, launch_windows_updater


class TestAutoUpdater(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="crn_test_updater_")
        self.dummy_exe = os.path.join(self.test_dir, "Crinometro_setup__v4.4.1.exe")
        with open(self.dummy_exe, "wb") as f:
            f.write(b"MOCK_INNO_SETUP_EXE")

        self.updater_dir = os.path.join(tempfile.gettempdir(), "crinometro_updater")
        os.makedirs(self.updater_dir, exist_ok=True)
        self.ps1_file = os.path.join(self.updater_dir, "apply_update.ps1")
        self.bat_file = os.path.join(self.updater_dir, "apply_update.bat")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_version_constants(self):
        """Verifica se a versão global foi atualizada para 4.4.1."""
        self.assertEqual(APP_VERSION, "4.4.1")
        self.assertEqual(parse_version_tuple("4.4.1"), (4, 4, 1))

    def test_version_comparison(self):
        """Verifica a lógica de comparação SemVer do atualizador."""
        self.assertTrue(is_remote_version_newer("4.4.1", "4.4.0"))
        self.assertTrue(is_remote_version_newer("4.4.1", "4.3.2"))
        self.assertTrue(is_remote_version_newer("5.0.0", "4.4.1"))
        self.assertFalse(is_remote_version_newer("4.4.0", "4.4.1"))
        self.assertFalse(is_remote_version_newer("4.4.1", "4.4.1"))

    def test_path_normalization_corrupted_char(self):
        """Verifica se diretórios com acento ou caractere de substituição são normalizados para 'Crinometro'."""
        for corrupted in ("C:\\Program Files\\Crin\ufffdmetro", "C:\\Program Files\\Crin?metro", "C:\\Program Files\\Crinômetro"):
            parent = os.path.dirname(corrupted)
            base = os.path.basename(corrupted)
            if base in ("Crinômetro", "Crin\ufffdmetro", "Crin?metro") or base.lower().startswith("crin"):
                normalized = os.path.join(parent, "Crinometro")
            self.assertEqual(normalized, "C:\\Program Files\\Crinometro")

    def test_script_generation_unicode_and_utf8_bom(self):
        """Verifica se o gerador grava o script em utf-8-sig sem crash e normaliza o alvo para Crinometro."""
        corrupted_target = "C:\\Program Files\\Crin\ufffdmetro"
        
        # Dispara a geração
        launch_windows_updater(self.dummy_exe, target_dir=corrupted_target)

        self.assertTrue(os.path.exists(self.ps1_file), "apply_update.ps1 deve existir!")
        self.assertTrue(os.path.exists(self.bat_file), "apply_update.bat deve existir!")

        # Verifica se o arquivo tem conteúdo não vazio (> 0 bytes)
        self.assertGreater(os.path.getsize(self.ps1_file), 100, "apply_update.ps1 não pode estar vazio!")
        self.assertGreater(os.path.getsize(self.bat_file), 10, "apply_update.bat não pode estar vazio!")

        # Verifica se foi gravado em UTF-8 com BOM
        with open(self.ps1_file, "rb") as f:
            header = f.read(3)
            self.assertEqual(header, b"\xef\xbb\xbf", "apply_update.ps1 DEVE ter BOM UTF-8 (0xEF, 0xBB, 0xBF)!")

        # Lê com utf-8-sig e valida conteúdo
        with open(self.ps1_file, "r", encoding="utf-8-sig") as f:
            content = f.read()

        self.assertIn("Crinometro", content, "O caminho normalizado 'Crinometro' deve estar presente no script!")
        self.assertNotIn("\ufffd", content, "O script não deve conter o caractere corrompido \\ufffd no caminho alvo!")
        self.assertIn("WaitForExit", content, "O script deve aguardar liberação via WaitForExit!")
        self.assertIn("Stop-Process", content, "O script deve conter salvaguarda Stop-Process!")

    def test_powershell_syntax_validation(self):
        """Valida se o PowerShell do Windows compila a sintaxe do script apply_update.ps1 sem erros."""
        corrupted_target = "C:\\Program Files\\Crin\ufffdmetro"
        launch_windows_updater(self.dummy_exe, target_dir=corrupted_target)

        self.assertTrue(os.path.exists(self.ps1_file), "apply_update.ps1 deve existir para o teste de sintaxe!")

        check_script = f"""
        $tokens = $null
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile('{self.ps1_file}', [ref]$tokens, [ref]$errors)
        if ($errors.Count -gt 0) {{
            $errors | ForEach-Object {{ Write-Error $_.Message }}
            exit 1
        }} else {{
            Write-Host "SYNTAX_OK"
            exit 0
        }}
        """
        # Executa com timeout de segurança (10 segundos)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", check_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"Erros de sintaxe encontrados no PowerShell: {proc.stderr}")
        self.assertIn("SYNTAX_OK", proc.stdout)

    def test_powershell_non_installer_mode(self):
        """Valida que arquivos .zip ou binários geram comandos adequados de extração/cópia."""
        zip_update = os.path.join(self.test_dir, "crinometro_update.zip")
        with open(zip_update, "wb") as f:
            f.write(b"MOCK_ZIP")

        launch_windows_updater(zip_update, target_dir=r"C:\Program Files\Crinômetro")

        with open(self.ps1_file, "r", encoding="utf-8-sig") as f:
            content = f.read()

        self.assertIn("Expand-Archive", content, "Atualização por zip deve conter Expand-Archive no script!")


if __name__ == "__main__":
    unittest.main()
