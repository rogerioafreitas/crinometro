filepath = 'tests/test_auto_updater.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        self.ps1_file = os.path.join(tempfile.gettempdir(), "apply_update.ps1")"""
replacement1 = """        self.ps1_file = os.path.join(self.updater_dir, "apply_update.ps1")
        # Mock tempfile.gettempdir para apontar para updater_dir durante os testes
        self.original_gettempdir = tempfile.gettempdir
        tempfile.gettempdir = lambda: self.updater_dir"""
content = content.replace(target1, replacement1)

target2 = """    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)"""
replacement2 = """    def tearDown(self):
        tempfile.gettempdir = self.original_gettempdir
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.updater_dir, ignore_errors=True)"""
content = content.replace(target2, replacement2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
