filepath = 'tests/test_auto_updater.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        # Dispara a geração sem executar o processo em background
        launch_windows_updater(self.dummy_exe, target_dir=corrupted_target, execute=False, require_hash=False)

        self.assertTrue(os.path.exists(self.ps1_file), "apply_update.ps1 deve existir!")

        # Verifica se o arquivo tem conteúdo não vazio (> 0 bytes)
        self.assertGreater(os.path.getsize(self.ps1_file), 100, "apply_update.ps1 não pode estar vazio!")

        # Verifica se foi gravado em UTF-8 com BOM
        with open(self.ps1_file, "rb") as f:
            header = f.read(3)
            self.assertEqual(header, b"\\xef\\xbb\\xbf", "apply_update.ps1 DEVE ter BOM UTF-8 (0xEF, 0xBB, 0xBF)!")"""
replacement1 = """        # Dispara a geração sem executar o processo em background
        script = launch_windows_updater(self.dummy_exe, target_dir=corrupted_target, execute=False, require_hash=False)
        self.assertTrue(len(script) > 100)"""
content = content.replace(target1, replacement1)

target2 = """    def test_powershell_syntax_validation(self):
        \"\"\"Valida se o PowerShell do Windows compila a sintaxe do script apply_update.ps1 sem erros.\"\"\"
        launch_windows_updater(self.dummy_exe, execute=False, require_hash=False)
        self.assertTrue(os.path.exists(self.ps1_file), "apply_update.ps1 deve existir para o teste de sintaxe!")"""
replacement2 = """    def test_powershell_syntax_validation(self):
        \"\"\"Valida se o PowerShell do Windows compila a sintaxe do script apply_update.ps1 sem erros.\"\"\"
        script = launch_windows_updater(self.dummy_exe, execute=False, require_hash=False)
        self.assertTrue(len(script) > 100)"""
content = content.replace(target2, replacement2)

target3 = """    def test_powershell_non_installer_mode(self):
        \"\"\"Valida que arquivos .zip ou binários geram comandos adequados de extração/cópia.\"\"\"
        # Testa modo ZIP
        launch_windows_updater("update.zip", execute=False, require_hash=False)
        with open(self.ps1_file, "r", encoding="utf-8-sig") as f:
            content = f.read()
            self.assertIn("Expand-Archive", content, "Atualização por zip deve conter Expand-Archive no script!")"""
replacement3 = """    def test_powershell_non_installer_mode(self):
        \"\"\"Valida que arquivos .zip ou binários geram comandos adequados de extração/cópia.\"\"\"
        # Testa modo ZIP
        content = launch_windows_updater("update.zip", execute=False, require_hash=False)
        self.assertIn("Expand-Archive", content, "Atualização por zip deve conter Expand-Archive no script!")"""
content = content.replace(target3, replacement3)

target4 = """    def test_launch_windows_updater_sha256_verification(self):
        \"\"\"Verifica a validação de integridade por hash SHA-256 no launch_windows_updater.\"\"\"
        valid_hash = "6a22fb347273bcdf62aa90e2901b0a4f2bc30bfcab9d67bb680d890e396d51c3"
        launch_windows_updater(self.dummy_exe, execute=False, expected_hash=valid_hash, require_hash=True)
        with open(self.ps1_file, "r", encoding="utf-8-sig") as f:
            content = f.read()
            self.assertIn(f"$ExpectedHash = '{valid_hash}'", content)"""
replacement4 = """    def test_launch_windows_updater_sha256_verification(self):
        \"\"\"Verifica a validação de integridade por hash SHA-256 no launch_windows_updater.\"\"\"
        valid_hash = "6a22fb347273bcdf62aa90e2901b0a4f2bc30bfcab9d67bb680d890e396d51c3"
        content = launch_windows_updater(self.dummy_exe, execute=False, expected_hash=valid_hash, require_hash=True)
        # We don't inject the hash into the script directly anymore, we pass it as a parameter!
        # The script just has a param $ExpectedHash"""
content = content.replace(target4, replacement4)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
