filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def learn_from_corrections(self, filename: str = None, blocking: bool = False):
        \"\"\"Coordena o retreinamento do classificador PulseLearner com base nas correções do usuário.\"\"\"
        ctx = self.session_context"""

replacement = """    def learn_from_corrections(self, filename: str = None, blocking: bool = False):
        \"\"\"Coordena o retreinamento do classificador PulseLearner com base nas correções do usuário.\"\"\"
        if getattr(self, "_learn_worker", None) is not None and self._learn_worker.isRunning():
            return False, "Treinamento já em andamento."
        ctx = self.session_context"""

content = content.replace(target, replacement)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
