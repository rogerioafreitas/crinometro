filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Clear config in setUpClass after reading
target_setupclass = """        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cls._original_config_text = f.read()"""

replacement_setupclass = """        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cls._original_config_text = f.read()
        # Ensure tests start with a clean slate
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("{}")"""

content = content.replace(target_setupclass, replacement_setupclass)

# 2. Fix test_33 text assertion
target_test33 = """self.assertEqual(self.window.lbl_metric_sub.text(), f"{_t['mean']}: -   |   {_t['variance']}: -")"""
replacement_test33 = """self.assertEqual(self.window.lbl_metric_sub.text(), f"{_t['mean']}: -   |   {_t['variance']}: -")"""

# Wait, the error was: AssertionError: 'Moda: -   |   Média: -' != 'Média: -   |   Variância: -'
# It means self.window.lbl_metric_sub.text() returned 'Moda: -   |   Média: -'
# And the test expected 'Média: -   |   Variância: -' (which uses _t['mean'] and _t['variance']).
# Let's fix EditorController to use Média and Variância when less than 2 peaks.

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
