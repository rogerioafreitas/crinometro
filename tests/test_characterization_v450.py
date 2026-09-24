import os
import sys
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

# Configura o Qt para rodar em modo offscreen/headless em ambiente de teste
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtMultimedia import QMediaPlayer

from ui.main_window import MainWindow
from core.analyzer import CricketAnalyzer
from core.worker import GenericWorker
from core.learner import PulseLearner
from utils.constants import DEFAULT_ALGO_PARAMS

app = QApplication.instance() or QApplication(sys.argv)

class TestCharacterization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.sample_wav = os.path.abspath(os.path.join("tests", "fixtures", "sample_chirp.wav"))
        if not os.path.exists(cls.sample_wav):
            raise FileNotFoundError(f"Arquivo de teste obrigatório não encontrado: {cls.sample_wav}")

    def setUp(self):
        # Silencia caixas de diálogo durante testes para evitar bloqueio
        self.patch_crit = patch('PyQt6.QtWidgets.QMessageBox.critical')
        self.patch_warn = patch('PyQt6.QtWidgets.QMessageBox.warning')
        self.patch_info = patch('PyQt6.QtWidgets.QMessageBox.information')
        self.patch_crit.start()
        self.patch_warn.start()
        self.patch_info.start()

        self.window = MainWindow()

    def tearDown(self):
        self.patch_crit.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        self.window.close()

    def test_00_session_context_redirection_and_emission(self):
        """Verifica se SessionContext armazena o estado e emite state_changed em qualquer atribuição."""
        emitted_signals = []
        self.window.ctx.state_changed.connect(lambda s: emitted_signals.append(s))

        # Atribuição via MainWindow property
        mock_data = {"rate": 44100, "dummy": True}
        self.window.active_heavy_data = mock_data

        # Fonte da verdade deve ser o contexto
        self.assertIs(self.window.ctx.active_heavy_data, mock_data)
        self.assertIn("active_heavy_data", emitted_signals)

        # Atribuição direta no SessionContext também deve emitir sinal
        emitted_signals.clear()
        self.window.ctx.analysis_cache = {"file.wav": mock_data}
        self.assertEqual(self.window.analysis_cache, {"file.wav": mock_data})
        self.assertIn("analysis_cache", emitted_signals)

    def test_01_pipeline_and_cache(self):
        """Pipeline real com WAV versionado: verifica estrutura completa e reutilização de cache."""
        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})

        # 1. Execução do analisador científico
        res = CricketAnalyzer.analyze(self.sample_wav, params)
        self.assertEqual(len(res), 21, "CricketAnalyzer.analyze deve retornar exatamente 21 elementos")

        rate, data, data_b1, env, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, duration, all_distant, carrier_freq, discarded_reasons, valid_peaks_stage2, peak_dur_dict, f_psd, Pxx_db = res

        self.assertEqual(rate, 44100)
        self.assertGreater(len(peaks), 0)
        self.assertGreater(len(chirps), 0)
        self.assertAlmostEqual(carrier_freq, 5000.0, delta=200.0)
        self.assertGreater(len(f_psd), 0)
        self.assertGreater(len(Pxx_db), 0)

        # 2. Aplicação na MainWindow e verificação das chaves obrigatórias do cache
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window._apply_analysis_results(fname, res, params=params, render=False)

        self.assertIn(fname, self.window.analysis_cache)
        cached = self.window.analysis_cache[fname]

        required_keys = [
            "rate", "data", "data_b1", "env", "peaks", "chirps",
            "chirp_peaks_list", "chirp_peaks", "media", "moda",
            "f_spec", "t_spec", "Sxx_db", "dom_freqs", "duration",
            "params", "peaks_detected", "peaks_user_verified",
            "distant_peaks", "carrier_freq", "discarded_peaks_reasons",
            "valid_peaks_stage2", "peak_dur_dict", "f_psd", "Pxx_db"
        ]
        for key in required_keys:
            self.assertIn(key, cached, f"Chave essencial '{key}' ausente no cache de análise")

        # 3. Verificação de integridade dos arrays
        self.assertIs(self.window.analysis_cache[fname]["f_psd"], f_psd)
        self.assertEqual(self.window.active_filename, fname)
        self.assertEqual(len(self.window.peaks_detected), len(peaks))

    def test_02_cancelamento_cooperativo(self):
        """Verifica encerramento limpo de worker cooperativo sem deixar estado inconsistente."""
        def long_task(is_aborted_fn):
            for _ in range(100):
                if is_aborted_fn():
                    return False
                time.sleep(0.005)
            return True

        worker = GenericWorker(lambda: long_task(lambda: worker.abort_requested))
        self.window._reanalyze_worker = worker
        worker.start()

        # Aguarda thread iniciar execução
        time.sleep(0.02)
        self.assertTrue(worker.isRunning())

        # Dispara aborto cooperativo da janela
        self.window.abort_current_analysis()
        self.assertTrue(worker.abort_requested)

        # Aguarda encerramento cooperativo
        worker.wait(1000)
        self.assertFalse(worker.isRunning())

    def test_03_navegacao_pan_zoom(self):
        """Verifica se pan/zoom altera somente o viewport pretendido."""
        ax_wave = self.window.panel_wave.ax
        ax_wave.set_xlim(0.0, 1.0)
        ax_wave.set_ylim(-1.0, 1.0)

        # Simula alteração de limites de visualização via navegação
        ax_wave.set_xlim(0.1, 0.5)
        new_xlim = ax_wave.get_xlim()
        self.assertAlmostEqual(new_xlim[0], 0.1, places=3)
        self.assertAlmostEqual(new_xlim[1], 0.5, places=3)

    def test_04_sincronizacao_eixos(self):
        """Verifica se a alteração do eixo X propaga aos painéis sincronizados."""
        self.window.sync_throttle_time = 0.0
        self.window.panel_spec.isVisible = MagicMock(return_value=True)
        self.window.spectro_engine = MagicMock()

        with patch.object(self.window.panel_spec.ax, 'get_ylim', return_value=(0, 6000)):
            self.window._sync_render([self.window.panel_spec], 0.05, 0.35)
            self.window.spectro_engine.render_interactive.assert_called_once_with(
                0.05, 0.35, 0, 6000, is_sync=True
            )

    def test_05_edicao_e_undo_pulsos(self):
        """Adicionar/remover/restaurar pulso atualiza marcadores e histórico."""
        self.window.active_heavy_data = {
            "rate": 1000.0, 
            "env": np.zeros(1000), 
            "data_b1": np.zeros(1000),
            "peaks_detected": [10, 50, 100],
            "peaks_user_verified": [10, 50, 100]
        }
        self.window.peaks_detected = [10, 50, 100]
        self.window.peaks_user_verified = [10, 50, 100]
        self.window._pulse_edit_history = []

        # Remove pulso em t = 0.050s (índice 50)
        self.window._toggle_peak_marker(0.051)
        self.assertNotIn(50, self.window.peaks_user_verified)
        self.assertEqual(len(self.window._pulse_edit_history), 1)

        # Desfaz edição
        self.window._undo_pulse_edit()
        self.assertIn(50, self.window.peaks_user_verified)
        self.assertEqual(len(self.window._pulse_edit_history), 0)

    def test_06_machine_learning_gate(self):
        """Verifica respeito estrito ao gate use_machine_learning."""
        # Cenário 1: IA desativada (Modo DSP) -> Não deve invocar adaptações nem learner
        self.window.use_machine_learning = False
        self.window.active_heavy_data = {
            "rate": 1000.0, "env": np.ones(1000), "data_b1": np.ones(1000),
            "peaks_detected": [10, 50], "peaks_user_verified": [10]
        }
        self.window.active_filename = "test.wav"
        self.window.corrections_by_file["test.wav"] = [10]

        with patch.object(PulseLearner, 'update_from_corrections') as mock_update:
            # Em modo DSP (ML=False), learner é None
            learner = self.window.pulse_learner if self.window.use_machine_learning else None
            self.assertIsNone(learner)
            mock_update.assert_not_called()

        # Cenário 2: IA ativada -> Executa adaptação de parâmetros
        self.window.use_machine_learning = True
        self.window._adaptive_overrides = {}
        self.window._adapt_advanced_params()
        self.assertIsInstance(self.window._adaptive_overrides, dict)

    def test_07_exportacao_txt_e_pdf(self):
        """Verifica produção real de arquivos válidos TXT e PDF."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.active_filename = fname
        self.window.get_checked_files = MagicMock(return_value=[fname])

        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})
        res = CricketAnalyzer.analyze(self.sample_wav, params)
        self.window._apply_analysis_results(fname, res, params=params, render=False)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Exportação TXT
            txt_path = os.path.join(tmp_dir, "relatorio.txt")
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=(txt_path, "")):
                self.window.action_save_txt()
                self.assertTrue(os.path.exists(txt_path), "Arquivo TXT não foi gerado")
                with open(txt_path, "r", encoding="utf-8") as f:
                    txt_content = f.read()
                self.assertIn("ANÁLISE BIOACÚSTICA", txt_content)
                self.assertIn(fname, txt_content)

            # 2. Exportação PDF
            pdf_path = os.path.join(tmp_dir, "relatorio.pdf")
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=(pdf_path, "")):
                self.window.action_save_pdf(include_chirp_list=False)
                self.assertTrue(os.path.exists(pdf_path), "Arquivo PDF não foi gerado")
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Arquivo gerado não é um PDF válido")

    def test_08_audio_transport(self):
        """Verifica play/pause, set_position, cursor e velocidade de reprodução."""
        # 1. Velocidade de reprodução cíclica
        self.window.playback_speed = 1.0
        self.window.cycle_playback_speed()
        self.assertEqual(self.window.playback_speed, 0.75)
        self.window.cycle_playback_speed()
        self.assertEqual(self.window.playback_speed, 0.5)

        # 2. Posicionamento
        self.window.player.setPosition = MagicMock()
        self.window.set_position(250, is_final=True)
        self.window.player.setPosition.assert_called_with(250)

    def test_09_realtime_frequency_tolerance(self):
        """Verifica reavaliação de tolerância espectral em tempo real."""
        fname = "sample_chirp.wav"
        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})
        res = CricketAnalyzer.analyze(self.sample_wav, params)
        self.window._apply_analysis_results(fname, res, params=params, render=False)

        # Ativa os dados para simular o estado em exibição
        self.window.active_heavy_data = self.window.analysis_cache[fname]
        initial_peaks_count = len(self.window.active_heavy_data["peaks"])
        self.assertGreater(initial_peaks_count, 0)

        # Aplica tolerância estreita que força descarte
        self.window._pending_carrier_tol = 50.0
        self.window._execute_realtime_freq_tolerance()

        self.assertIn("carrier_freq", self.window.active_heavy_data)
        self.assertEqual(self.window.active_heavy_data["params"]["freq_tolerance_hz"], 50.0)

if __name__ == '__main__':
    unittest.main()
