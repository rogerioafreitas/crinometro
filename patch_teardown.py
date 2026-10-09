filepath = 'tests/test_characterization_v450.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target_setupclass = """        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cls._original_config_text = f.read()
        # Ensure tests start with a clean slate
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("{}")"""

replacement_setupclass = """        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cls._original_config_text = f.read()
        else:
            cls._original_config_text = "{}"
        
        # Ensure tests start with a clean slate
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("{}")"""

content = content.replace(target_setupclass, replacement_setupclass)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
