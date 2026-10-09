import os
import unittest
from unittest.mock import patch, MagicMock

# Define a varivel *antes* dos imports
os.environ["CRINOMETRO_TESTING"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

class TestImports(unittest.TestCase):
    def test_import_main_and_crinometro(self):
        try:
            import main
            import crinometro
            import crinometro__laucher
        except Exception as e:
            self.fail(f"Import failed with CRINOMETRO_TESTING=1: {e}")

    @patch("utils.helpers.QMessageBox")
    def test_handle_exception_testing_bypass(self, mock_qmsgbox):
        from utils.helpers import handle_exception
        # ensure env var is set
        self.assertEqual(os.environ.get("CRINOMETRO_TESTING"), "1")
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            import sys
            handle_exception(type(e), e, e.__traceback__)
        
        mock_qmsgbox.assert_not_called()
        mock_qmsgbox.return_value.exec.assert_not_called()

if __name__ == '__main__':
    unittest.main()
