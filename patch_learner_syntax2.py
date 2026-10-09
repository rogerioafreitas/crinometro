import re

filepath = 'core/learner.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

bad_block = """self.model = None
        self.degraded = False
        self.last_error = None
        import threading
        self._model_lock = threading.RLock()"""

content = content.replace(bad_block, "self.model = None")

# Add it ONLY to __init__
init_pattern = r"(def __init__\(self, config_path=CONFIG_FILE\):\n\s+self\.config_path = config_path\n\s+config_dir = os\.path\.dirname\(os\.path\.abspath\(config_path\)\)\n\s+self\.persistence_path = os\.path\.join\(config_dir, \"modelo_treinado\.skops\"\)\n\s+self\.model = None)"

new_init = r"\1\n        self.degraded = False\n        self.last_error = None\n        import threading\n        self._model_lock = threading.RLock()"
content = re.sub(init_pattern, new_init, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
