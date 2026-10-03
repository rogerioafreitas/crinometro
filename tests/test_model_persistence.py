import unittest
import os
import tempfile
import numpy as np

try:
    from core.learner import PulseLearner
except ImportError:
    PulseLearner = None

class TestModelPersistence(unittest.TestCase):
    @unittest.skipIf(PulseLearner is None, "scikit-learn not available")
    def test_persistence_skops(self):
        # Configurar ambiente
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "config.json")
            export_path = os.path.join(tmp_dir, "export.skops")
            
            # Instanciar e forjar treinamento (HistGradientBoosting)
            learner = PulseLearner(config_path)
            X = np.random.rand(50, len(learner.feature_names))
            y = np.random.randint(0, 2, 50)
            learner.fit(X, y)
            
            # Testar serialize
            payload = learner.serialize()
            self.assertIsNotNone(payload)
            self.assertIn("model_pickle_b64", payload)
            
            # Testar save_to_config e load_from_config
            self.assertTrue(learner.save_to_config())
            learner2 = PulseLearner(config_path)
            self.assertTrue(learner2.load_from_config())
            self.assertIsNotNone(learner2.model)
            
            # Testar export / import file
            self.assertTrue(learner.export_model_file(export_path))
            self.assertTrue(os.path.exists(export_path))
            
            learner3 = PulseLearner(config_path)
            self.assertTrue(learner3.import_model_file(export_path))
            self.assertIsNotNone(learner3.model)
            self.assertTrue(os.path.exists(learner3.persistence_path))
            self.assertTrue(learner3.persistence_path.endswith('.skops'))

if __name__ == "__main__":
    unittest.main()
