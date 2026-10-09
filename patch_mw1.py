import re

filepath = 'ui/main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

bad_pattern = """        if hasattr(self, "btn_analyze_selected"):

        sp = getattr(self, "_batch_spinner", None)
        if sp is not None:
            sp.stop(restore_text=I18N[self.lang]["analyze_selected"])
            self._batch_spinner = None

        self.btn_analyze_selected.setEnabled(True)"""

good_pattern = """        if hasattr(self, "btn_analyze_selected"):
            sp = getattr(self, "_batch_spinner", None)
            if sp is not None:
                sp.stop(restore_text=I18N[self.lang]["analyze_selected"])
                self._batch_spinner = None
            self.btn_analyze_selected.setEnabled(True)"""

content = content.replace(bad_pattern, good_pattern)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
