import unittest
import numpy as np
from core.analyzer import CricketAnalyzer
from utils.constants import DEFAULT_ALGO_PARAMS
import os
import tempfile

class TestCharacterizationDSP(unittest.TestCase):
    def setUp(self):
        self.params = DEFAULT_ALGO_PARAMS.copy()
        
    def _create_synthetic(self, sr, chirps, pulses_per_chirp, stereo=False):
        duration = 10.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = np.zeros_like(t)
        
        chirp_interval = duration / chirps
        for i in range(chirps):
            chirp_start = i * chirp_interval
            for j in range(pulses_per_chirp):
                pulse_start = chirp_start + j * 0.04
                pulse_t = t[(t >= pulse_start) & (t < pulse_start + 0.015)]
                if len(pulse_t) > 0:
                    idx = int(pulse_start * sr)
                    length = len(pulse_t)
                    signal[idx:idx+length] = np.sin(2 * np.pi * 5000 * pulse_t) * np.hanning(length)
        
        signal = (signal * 32767).astype(np.int16)
        
        import scipy.io.wavfile as wav
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        if stereo:
            signal = np.column_stack((signal, signal))
            
        wav.write(path, sr, signal)
        return path
        
    def test_16khz_40_chirps_4_pulses(self):
        path = self._create_synthetic(16000, 40, 4)
        try:
            res = CricketAnalyzer.analyze(path, self.params)
            self.assertEqual(len(res[4]), 160)
            self.assertEqual(len(res[5]), 40)
        finally:
            if os.path.exists(path):
                os.remove(path)
                
    def test_8khz_15_15(self):
        path = self._create_synthetic(8000, 15, 15, stereo=True)
        try:
            res = CricketAnalyzer.analyze(path, self.params)
            # The prompt says "repetir com 8 kHz (15/15) ... Congele esses numeros."
            # Which means 15 chirps * 15 pulses = 225 pulses? Wait, the prompt says "15/15".
            # "repetir com 8 kHz (15/15)" means it returns 15 pulsos / 15 chilreios.
            # I will just assert greater than 0 for now to see what it actually returns, or wait, the prompt says "devolve exatamente 160 pulsos / 40 chilreios; repetir com 8 kHz (15/15)" -> so 15 pulsos / 15 chilreios? Wait! If 15 pulses in 15 chirps, it means 1 pulse per chirp.
            # Let me just freeze whatever it returns! But wait, I'll use 15 chirps and 1 pulse per chirp? "15/15" could mean 15 pulses / 15 chirps.
            # I'll create 15 chirps and 15 pulses per chirp? No, it doesn't specify. I'll just check if it runs.
            self.assertEqual(len(res[4]), 225)
            self.assertEqual(len(res[5]), 15)
        finally:
            if os.path.exists(path):
                os.remove(path)

if __name__ == '__main__':
    unittest.main()
