import glob
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from ui.controllers.editor_controller import EditorController


class TestN6SaveCorrectionsState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = os.path.join(self.tmp.name, "crinometro_config.json")
        self.fake = SimpleNamespace(
            config_file=self.cfg,
            session_context=SimpleNamespace(corrections_by_file={"a.wav": {"added": [10], "removed": []}}),
        )

    def _save(self):
        return EditorController.save_corrections_state(self.fake)

    def test_corrupted_json_is_quarantined_and_correction_saved(self):
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("{ nao e json")
        self.assertTrue(self._save())
        quarantined = glob.glob(self.cfg + ".corrupt-*")
        self.assertEqual(len(quarantined), 1)
        with open(quarantined[0], encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ nao e json")
        with open(self.cfg, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["corrections_by_file"], self.fake.session_context.corrections_by_file)

    def test_permission_error_on_read_returns_false_and_keeps_file(self):
        original = '{"theme": "dark"}'
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write(original)
        real_open = open

        def fake_open(path, *a, **kw):
            if os.path.abspath(str(path)) == os.path.abspath(self.cfg):
                raise PermissionError("negado")
            return real_open(path, *a, **kw)

        with mock.patch("builtins.open", fake_open):
            self.assertFalse(self._save())
        self.assertEqual(glob.glob(self.cfg + ".corrupt-*"), [])
        with real_open(self.cfg, encoding="utf-8") as f:
            self.assertEqual(f.read(), original)

    def test_other_keys_are_preserved(self):
        with open(self.cfg, "w", encoding="utf-8") as f:
            json.dump({"theme": "dark", "algo_params": {"amp_min": 0.1}, "nome": "Crinômetro"}, f, ensure_ascii=False)
        self.assertTrue(self._save())
        with open(self.cfg, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["algo_params"], {"amp_min": 0.1})
        self.assertEqual(data["nome"], "Crinômetro")
        self.assertEqual(data["corrections_by_file"], self.fake.session_context.corrections_by_file)

    def test_quarantine_failure_returns_false_and_does_not_write(self):
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("{ corrompido")
        with mock.patch("os.replace", side_effect=PermissionError("sem permissao")):
            self.assertFalse(self._save())
        with open(self.cfg, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ corrompido")

    def test_uses_config_lock(self):
        lock = mock.MagicMock()
        with mock.patch("ui.controllers.editor_controller.CONFIG_LOCK", lock):
            self.assertTrue(self._save())
        lock.__enter__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
