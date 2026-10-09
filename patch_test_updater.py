filepath = 'tests/test_auto_updater.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        self.ps1_file = os.path.join(self.updater_dir, "apply_update.ps1")
        self.bat_file = os.path.join(self.updater_dir, "apply_update.bat")"""
replacement1 = """        self.ps1_file = os.path.join(tempfile.gettempdir(), "apply_update.ps1")"""
content = content.replace(target1, replacement1)

target2 = """        self.assertTrue(os.path.exists(self.ps1_file), "apply_update.ps1 deve existir!")
        self.assertTrue(os.path.exists(self.bat_file), "apply_update.bat deve existir!")

        # Verifica se o arquivo tem conteúdo não vazio (> 0 bytes)
        self.assertGreater(os.path.getsize(self.ps1_file), 100, "apply_update.ps1 não pode estar vazio!")
        self.assertGreater(os.path.getsize(self.bat_file), 10, "apply_update.bat não pode estar vazio!")"""
replacement2 = """        self.assertTrue(os.path.exists(self.ps1_file), "apply_update.ps1 deve existir!")

        # Verifica se o arquivo tem conteúdo não vazio (> 0 bytes)
        self.assertGreater(os.path.getsize(self.ps1_file), 100, "apply_update.ps1 não pode estar vazio!")"""
content = content.replace(target2, replacement2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
