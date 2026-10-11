import glob
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sequências conhecidas de acentos perdidos (palavra sem os caracteres acentuados).
LOST_ACCENT_PATTERNS = [
    r"incompatveis", r"parmetros", r"avanados", r"\baps\b", r"\bVerso\b",
    r"Migrao", r"\bConfiguraes\b", r"\bAtualizao\b", r"\bExportao\b",
]


def _py_files():
    out = []
    for d in ("core", "ui", "utils"):
        out += glob.glob(os.path.join(ROOT, d, "**", "*.py"), recursive=True)
    out += [os.path.join(ROOT, n) for n in ("main.py", "crinometro.py", "crinometro__laucher.py")]
    return [f for f in out if os.path.exists(f)]


class TestEncoding(unittest.TestCase):
    def test_no_known_lost_accent_sequences(self):
        found = []
        for f in _py_files():
            with io.open(f, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    for pat in LOST_ACCENT_PATTERNS:
                        if re.search(pat, line):
                            found.append(f"{os.path.relpath(f, ROOT)}:{n}: {pat}")
        self.assertEqual(found, [])

    def test_no_replacement_char_in_literals(self):
        found = []
        for f in _py_files():
            with io.open(f, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    if "\ufffd" in line:
                        found.append(f"{os.path.relpath(f, ROOT)}:{n}")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
