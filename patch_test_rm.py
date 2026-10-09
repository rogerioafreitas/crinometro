filepath = 'tests/test_auto_updater.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        self.ps1_file = os.path.join(tempfile.gettempdir(), "apply_update.ps1")"""
replacement1 = """        self.ps1_file = os.path.join(tempfile.gettempdir(), "apply_update.ps1")
        if os.path.exists(self.ps1_file): os.remove(self.ps1_file)"""
content = content.replace(target1, replacement1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
