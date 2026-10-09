filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'self.assertEqual(self.window.ctx.corrections_by_file[fname], list(self.window.ctx.peaks_user_verified))'
replacement = '''saved = self.window.ctx.corrections_by_file[fname]
        saved_ints = [item["idx"] if isinstance(item, dict) else int(item) for item in saved]
        self.assertEqual(saved_ints, list(self.window.ctx.peaks_user_verified))'''

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
