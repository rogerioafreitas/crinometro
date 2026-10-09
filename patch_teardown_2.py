filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target_teardown = """        if hasattr(self.__class__, '_original_config_text') and self._original_config_text is not None:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(self._original_config_text)"""

replacement_teardown = """        # Ensure next test gets a clean slate
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("{}")"""

content = content.replace(target_teardown, replacement_teardown)

target_setupclass = """    @classmethod
    def setUpClass(cls):"""

replacement_setupclass = """    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_original_config_text') and cls._original_config_text is not None:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(cls._original_config_text)

    @classmethod
    def setUpClass(cls):"""

content = content.replace(target_setupclass, replacement_setupclass)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
