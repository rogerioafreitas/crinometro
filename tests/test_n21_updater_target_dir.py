import os
import tempfile
import unittest

from core import updater


class TestN21NormalizeTargetDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.abspath(self.tmp.name)

    def test_exact_name_with_accent_is_renamed(self):
        target = os.path.join(self.root, "Crin\u00f4metro")
        os.mkdir(target)
        self.assertEqual(updater.normalize_target_dir(target), os.path.join(self.root, "Crinometro"))

    def test_replacement_char_is_renamed(self):
        target = os.path.join(self.root, "Crin\ufffdmetro")
        self.assertEqual(updater.normalize_target_dir(target), os.path.join(self.root, "Crinometro"))

    def test_question_mark_is_renamed_when_parent_writable(self):
        target = os.path.join(self.root, "Crin?metro")
        self.assertEqual(updater.normalize_target_dir(target), os.path.join(self.root, "Crinometro"))

    def test_already_ascii_unchanged(self):
        target = os.path.join(self.root, "Crinometro")
        self.assertEqual(updater.normalize_target_dir(target), target)

    def test_prefix_match_is_not_renamed(self):
        target = os.path.join(self.root, "crinometro-beta")
        self.assertEqual(updater.normalize_target_dir(target), target)

    def test_unrelated_folder_with_space_unchanged(self):
        target = "D:\\Crin Lab"
        self.assertEqual(updater.normalize_target_dir(target), os.path.abspath(target))

    def test_not_renamed_when_dir_missing_and_parent_not_writable(self):
        target = os.path.join(self.root, "inexistente", "Crin\u00f4metro")
        self.assertEqual(updater.normalize_target_dir(target), target)


if __name__ == "__main__":
    unittest.main()
