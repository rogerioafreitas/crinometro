import logging
import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from core import learner as learner_mod
from core.learner import PulseLearner

RATE = 16000
PEAKS = np.array([300, 500, 700, 900, 1100])
FAKE_PRIORS = np.array([0.10, 0.15, 0.20, 0.25, 0.12])


def _env():
    rs = np.random.RandomState(0)
    return np.abs(rs.randn(2000)) * 0.5 + 0.2


def _fake_priors(peaks, rate, env_signal, raw_signal=None):
    return FAKE_PRIORS[:len(peaks)].copy()


class _RaisingModel:
    classes_ = [0, 1]

    def predict_proba(self, X):
        raise RuntimeError("boom-proba")

    def predict(self, X):
        raise RuntimeError("boom-predict")


class TestN18LearnerFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.learner = PulseLearner(config_path=os.path.join(self.tmp.name, "cfg.json"))
        p = mock.patch.object(PulseLearner, "compute_unsupervised_focal_priors",
                              staticmethod(_fake_priors))
        p.start()
        self.addCleanup(p.stop)

    def test_no_model_rescue_keeps_top_quartile_and_warns(self):
        with self.assertLogs("crinometro", level="WARNING") as cm:
            kept, dropped = self.learner.filter_peaks(PEAKS, RATE, _env())
        self.assertEqual(kept.tolist(), [700, 900])
        self.assertEqual(dropped.tolist(), [300, 500, 1100])
        self.assertTrue(any("resgate" in m.lower() for m in cm.output), cm.output)

    def test_model_predict_failure_degrades_and_falls_back_to_no_model(self):
        self.learner.model = _RaisingModel()
        with self.assertLogs("crinometro", level="ERROR"):
            kept, dropped = self.learner.filter_peaks(PEAKS, RATE, _env())
        self.assertTrue(self.learner.degraded)
        self.assertIn("boom", self.learner.last_error)
        self.assertEqual(kept.tolist(), [700, 900])
        self.assertEqual(dropped.tolist(), [300, 500, 1100])

    def test_predict_raises_model_unavailable(self):
        self.learner.model = _RaisingModel()
        with self.assertLogs("crinometro", level="ERROR"):
            with self.assertRaisesRegex(learner_mod.ModelUnavailable, "boom-predict"):
                self.learner.predict(np.zeros((2, len(self.learner.feature_names))))
        self.assertTrue(self.learner.degraded)
        self.assertIn("boom-predict", self.learner.last_error)


if __name__ == "__main__":
    unittest.main()
