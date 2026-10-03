import unittest
import os
import weakref
import gc
import numpy as np
import tempfile
from pathlib import Path
from ui.figure_factory import unique_path, png_set_suffix, export_figures_png, export_figures_pdf, ExportConfig, _new_fig

class MockContext:
    active_heavy_data = {"rate": 44100}
    algo_params = {"b1_min": 3200, "b1_max": 6000}
    active_filename = "test.wav"

class TestFigureFactory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        
    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_unique_path(self):
        f = self.tmp_path / "test.pdf"
        self.assertEqual(unique_path(str(f)), str(f))
        f.touch()
        self.assertEqual(unique_path(str(f)), str(self.tmp_path / "test (1).pdf"))

    def test_png_set_suffix(self):
        base = str(self.tmp_path / "x")
        panels = ["waveform", "psd"]
        self.assertEqual(png_set_suffix(base, panels), "")
        (self.tmp_path / "x_psd.png").touch()
        self.assertEqual(png_set_suffix(base, panels), " (1)")

    def test_export_config_defaults(self):
        cfg = ExportConfig()
        self.assertEqual(cfg.xlabel_wave, "Tempo (s)")
        self.assertEqual(cfg.ylabel_wave, "Amplitude")
        self.assertEqual(cfg.xlabel_spec, "Tempo (s)")
        self.assertIsNone(cfg.ylabel_spec)
        self.assertIsNone(cfg.xlabel_psd)
        self.assertIsNone(cfg.ylabel_psd)

    def test_decimation_preserves_peak(self):
        from ui.figure_factory import draw_waveform
        cfg = ExportConfig()
        fig, ax = _new_fig(cfg)
        data = np.zeros(250000)
        data[150000] = 5.0
        time_sec = np.linspace(0, 5, 250000)
        draw_waveform(ax, data, 44100, cfg=cfg, interactive=False)
        line = ax.lines[0]
        ydata = line.get_ydata()
        self.assertIn(5.0, ydata)
        fig.clf()

    def test_spectrogram_colorbar_auto(self):
        from ui.figure_factory import draw_spectrogram
        cfg = ExportConfig(spec_xmin=0, spec_xmax=1)
        fig, ax = _new_fig(cfg)
        t_spec = np.linspace(0, 1, 10)
        f_spec = np.linspace(0, 10000, 10)
        Sxx = np.zeros((10, 10))
        draw_spectrogram(ax, Sxx, t_spec, f_spec, cfg=cfg, interactive=False)
        self.assertTrue(len(fig.axes) > 1)
        fig.clf()

    def test_cancel_removes_files(self):
        ctx = MockContext()
        ctx.active_heavy_data = {
            "rate": 44100,
            "data": np.zeros(100),
            "time_sec": np.linspace(0, 1, 100)
        }
        cfg = ExportConfig(panels=["waveform"])
        base = str(self.tmp_path / "cancel")
        
        def should_cancel(): return True
        written = export_figures_png(ctx, base, cfg, should_cancel=should_cancel)
        self.assertEqual(written, [])
        self.assertFalse(os.path.exists(base + "_waveform.png"))

    def test_leak_weakref(self):
        cfg = ExportConfig()
        fig, ax = _new_fig(cfg)
        ref = weakref.ref(fig)
        fig.clf()
        del fig
        del ax
        gc.collect()
        self.assertIsNone(ref())

    def test_all_panels_export(self):
        ctx = MockContext()
        ctx.active_heavy_data = {
            "rate": 44100,
            "data": np.zeros(100),
            "time_sec": np.linspace(0, 1, 100),
            "f_psd": np.linspace(0, 10000, 10),
            "Pxx_db": np.ones(10),
            "t_spec": np.linspace(0, 1, 10),
            "f_spec": np.linspace(0, 10000, 10),
            "Sxx_db": np.zeros((10, 10))
        }
        ctx.active_heavy_data["chirps"] = [1, 2, 3]
        ctx.active_heavy_data["chirp_peaks_list"] = [[10], [20, 25], [30, 35, 40]]
        
        cfg = ExportConfig(panels=["waveform", "histogram", "psd", "spectrogram"])
        base = str(self.tmp_path / "all")
        
        pngs = export_figures_png(ctx, base, cfg)
        self.assertEqual(len(pngs), 4)
        
        pdf = export_figures_pdf(ctx, base + ".pdf", cfg)
        self.assertTrue(os.path.exists(pdf))

if __name__ == '__main__':
    unittest.main()
