import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

from reportlab.platypus import Paragraph, SimpleDocTemplate

from utils.constants import CHANGELOG_FULL

RESTORED = ["4.1.1", "3.5.1", "3.4.5", "3.4.4", "3.4.3", "3.4.2", "3.4.1",
            "3.3.0", "3.2.3", "3.2.2", "3.2.1", "3.2.0", "3.1.0", "3.0.0"]
EXISTING = ["4.5.0", "4.4.1", "4.4.0", "4.3.2", "4.3.0", "4.2.2", "4.2.0",
            "4.1.2", "4.1.0", "4.0.0", "3.5.0", "3.4.0"]


class TestN8ChangelogFull(unittest.TestCase):
    def test_has_26_expected_versions_with_entries(self):
        self.assertEqual(set(CHANGELOG_FULL), set(RESTORED + EXISTING))
        self.assertEqual(len(CHANGELOG_FULL), 26)
        for ver, items in CHANGELOG_FULL.items():
            self.assertTrue(items and all(isinstance(i, str) and i.strip() for i in items), ver)

    def test_restored_entries_keep_accents(self):
        self.assertIn("Correção definitiva da seleção individual", CHANGELOG_FULL["3.4.2"][0])
        self.assertIn("Nova interface visual modernizada com temas Claro e Escuro.", CHANGELOG_FULL["3.0.0"])
        for ver in RESTORED:
            for item in CHANGELOG_FULL[ver]:
                self.assertNotIn("\ufffd", item)

    def test_pdf_generator_includes_all_versions(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
        self.addCleanup(sys.path.pop, 0)
        gen = importlib.import_module("generate_changelog_pdf")
        captured = {}

        def fake_build(self_doc, story, **kw):
            captured["story"] = story

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(gen, "PDF_OUTPUT_PATH", os.path.join(tmp, "CHANGELOG.pdf")), \
                mock.patch.object(SimpleDocTemplate, "build", fake_build):
            gen.generate_changelog_pdf()

        def texts(flowables):
            for f in flowables:
                if isinstance(f, Paragraph):
                    yield f.text
                for sub in getattr(f, "_content", []) or []:
                    if isinstance(sub, Paragraph):
                        yield sub.text

        joined = "\n".join(texts(captured["story"]))
        for ver in RESTORED + EXISTING:
            self.assertIn(f"Versão {ver}", joined)


if __name__ == "__main__":
    unittest.main()
