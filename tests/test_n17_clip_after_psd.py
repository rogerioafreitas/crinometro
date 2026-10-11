import os
import tempfile
import unittest
import warnings

import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import butter, sosfiltfilt, spectrogram

from core.analyzer import CricketAnalyzer
from utils.constants import DEFAULT_ALGO_PARAMS

SR = 16000
CLICK_AT = 3.5


def _make_click_wav(path):
    """3 chilreios de 4 pulsos (5 kHz, amplitude 0.3) + 1 estalo de 1 amostra (amplitude 1.0)."""
    n = int(SR * 6.0)
    sig = np.zeros(n)
    for i in range(3):
        for j in range(4):
            start = int((i * 1.5 + 0.2 + j * 0.04) * SR)
            length = int(0.015 * SR)
            tt = np.arange(length) / SR
            sig[start:start + length] = 0.3 * np.sin(2 * np.pi * 5000 * tt) * np.hanning(length)
    sig[int(CLICK_AT * SR)] = 1.0
    wav.write(path, SR, (sig * 32767).astype(np.int16))


class TestN17ClipAfterSpectrogram(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        _make_click_wav(self.path)
        self.addCleanup(lambda: os.path.exists(self.path) and os.remove(self.path))

    def _expected_unclipped_sxx_db(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rate, raw = wav.read(self.path)
        data = raw.astype(np.float64)
        data = data - np.mean(data)
        sos = butter(2, 50.0 / (0.5 * rate), btype="high", output="sos")
        data = sosfiltfilt(sos, data)
        scale = max(float(np.percentile(np.abs(data), 99.9)), 1e-9)
        data = data / scale
        self.assertGreater(np.max(np.abs(data)), 1.0, "o estalo deve exceder 1.0 antes do clip")
        _, _, sxx = spectrogram(data, rate, nperseg=1024, noverlap=768)
        return (10 * np.log10(sxx + 1e-10)).astype(np.float32)

    def test_spectrogram_computed_without_clip(self):
        res = CricketAnalyzer.analyze(self.path, DEFAULT_ALGO_PARAMS.copy())
        sxx_db = res[11]
        np.testing.assert_allclose(sxx_db, self._expected_unclipped_sxx_db(), atol=1e-3)

    def test_returned_signal_is_clipped_and_counts_unchanged(self):
        res = CricketAnalyzer.analyze(self.path, DEFAULT_ALGO_PARAMS.copy())
        self.assertLessEqual(float(np.max(np.abs(res[1]))), 1.0)
        self.assertEqual((len(res[4]), len(res[5])), (EXPECTED_PULSES, EXPECTED_CHIRPS))


EXPECTED_PULSES = 12
EXPECTED_CHIRPS = 3

if __name__ == "__main__":
    unittest.main()
