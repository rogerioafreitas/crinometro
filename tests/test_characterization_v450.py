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
from matplotlib.backend_bases import MouseEvent

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
        self.window.show()

    def tearDown(self):
        self.patch_crit.stop()
        self.patch_warn.stop()
        self.patch_info.stop()
        if hasattr(self, 'window'):
            self.window.pipeline.abort_current_analysis()
            self.window.close()
        QApplication.processEvents()

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
        self.window.active_filename = fname
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
        """Verifica o algoritmo real de pan e zoom do Crinômetro (on_press, on_release, zoom_graph)."""
        ax = self.window.panel_wave.ax
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(-1.0, 1.0)
        self.window.active_heavy_data = {"rate": 44100, "duration": 1.0}

        # 1. Teste de Pan via on_press (botão direito = 3)
        event_press = MouseEvent(
            'button_press_event', self.window.panel_wave.canvas,
            x=100, y=100, button=3, dblclick=False, guiEvent=None
        )
        event_press.inaxes = ax
        self.window.on_press(event_press)
        self.assertTrue(self.window.panning)
        self.assertEqual(self.window.active_ax, ax)
        self.assertEqual(self.window.start_xlim, (0.0, 1.0))

        # 2. Teste de término de Pan via on_release
        event_release = MouseEvent(
            'button_release_event', self.window.panel_wave.canvas,
            x=100, y=100, button=3, dblclick=False, guiEvent=None
        )
        self.window.on_release(event_release)
        self.assertFalse(self.window.panning)
        self.assertIsNone(self.window.active_ax)

        # 3. Teste de Zoom real via zoom_graph (scroll 'up' dá zoom in)
        event_zoom = MouseEvent(
            'scroll_event', self.window.panel_wave.canvas,
            x=100, y=100, button='up', step=1, dblclick=False, guiEvent=None
        )
        event_zoom.inaxes = ax
        event_zoom.xdata = 0.5
        event_zoom.ydata = 0.0

        orig_width = ax.get_xlim()[1] - ax.get_xlim()[0]
        self.window.zoom_graph(event_zoom)
        new_width = ax.get_xlim()[1] - ax.get_xlim()[0]

        self.assertLess(new_width, orig_width, "Zoom 'up' deve aproximar reduzindo a largura da janela de tempo")

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
        """Verifica interceptação de CricketAnalyzer.analyze comprovando o gate de ML."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})

        # Cenário 1: IA desativada (Modo DSP) -> CricketAnalyzer.analyze recebe pulse_learner=None
        self.window.use_machine_learning = False
        with patch.object(CricketAnalyzer, 'analyze', wraps=CricketAnalyzer.analyze) as mock_analyze:
            self.window.run_analysis(fname, params, render=False)
            mock_analyze.assert_called_once()
            self.assertIsNone(mock_analyze.call_args.kwargs.get('pulse_learner'))

        # Cenário 2: IA ativada -> CricketAnalyzer.analyze recebe self.window.pulse_learner
        self.window.use_machine_learning = True
        with patch.object(CricketAnalyzer, 'analyze', wraps=CricketAnalyzer.analyze) as mock_analyze:
            self.window.run_analysis(fname, params, render=False)
            mock_analyze.assert_called_once()
            self.assertIs(mock_analyze.call_args.kwargs.get('pulse_learner'), self.window.pulse_learner)

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
        """Verifica reavaliação de tolerância espectral em tempo real, sincronização e preservação de zoom."""
        fname = "sample_chirp.wav"
        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})
        res = CricketAnalyzer.analyze(self.sample_wav, params)
        self.window._apply_analysis_results(fname, res, params=params, render=False)

        # Ativa os dados para simular o estado em exibição
        self.window.active_filename = fname
        self.window.active_heavy_data = self.window.analysis_cache[fname]
        self.window.panel_wave.ax.set_xlim(0.05, 0.35)
        cur_xlim = self.window.panel_wave.ax.get_xlim()

        signals_emitted = []
        self.window.pipeline.realtime_tolerance_updated.connect(lambda s: signals_emitted.append(s))

        # Aplica tolerância de 500 Hz
        self.window.apply_realtime_freq_tolerance(500.0)
        self.window._execute_realtime_freq_tolerance()

        # 1. Verifica emissão do sinal realtime_tolerance_updated
        self.assertIn(fname, signals_emitted)
        # 2. Verifica dados atualizados
        self.assertIn("carrier_freq", self.window.active_heavy_data)
        self.assertEqual(self.window.active_heavy_data["params"]["freq_tolerance_hz"], 500.0)
        # 3. Verifica sincronização de tolerância visual no espectrograma
        if hasattr(self.window.panel_spec, "slider_carrier_tol"):
            self.assertEqual(self.window.panel_spec.slider_carrier_tol.value(), 500)
        # 4. Verifica preservação do zoom X
        self.assertEqual(self.window.panel_wave.ax.get_xlim(), cur_xlim)

    def test_10_force_reanalyze_lifecycle(self):
        """Testa o ciclo de vida completo de force_reanalyze:
        - Inicia worker e exibe botão Abortar
        - Conclui análise em thread secundária
        - active_heavy_data no SessionContext é atualizado com novo resultado
        - Cache aponta para o mesmo resultado
        - Botão Abortar desaparece
        """
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.active_filename = fname

        # Inicializa com um dado antigo
        old_data = {"rate": 22050, "peaks": [1, 2], "carrier_freq": 1000.0, "params": {}}
        self.window.ctx.active_heavy_data = old_data
        self.window.ctx.analysis_cache[fname] = old_data

        # Botão Abortar inicialmente oculto
        self.assertFalse(self.window.btn_abort_analysis.isVisible())

        # Dispara reanálise
        self.window.force_reanalyze()

        # Botão Abortar deve estar visível durante execução
        self.assertTrue(self.window.btn_abort_analysis.isVisible())

        # Aguarda thread secundária terminar
        worker = self.window.pipeline._reanalyze_worker
        self.assertIsNotNone(worker)
        worker.wait(3000)

        for _ in range(10):
            QApplication.processEvents()
            time.sleep(0.02)

        # 1. active_heavy_data deve ser o NOVO resultado, não o antigo!
        new_active = self.window.ctx.active_heavy_data
        self.assertIsNot(new_active, old_data)
        self.assertEqual(new_active["rate"], 44100)
        self.assertIn("f_psd", new_active)

        # 2. Cache deve apontar para o mesmo resultado
        self.assertIs(self.window.ctx.analysis_cache[fname], new_active)

        # 3. Botão Abortar deve ter desaparecido!
        self.assertFalse(self.window.btn_abort_analysis.isVisible())

    def test_11_batch_analysis_and_progress(self):
        """Testa análise em lote e emissão dos sinais de lote de ponta a ponta sem corrida."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        
        progress_events = []
        item_events = []
        completed_events = []
        self.window.pipeline.batch_progress.connect(lambda cur, tot: progress_events.append((cur, tot)))
        self.window.pipeline.batch_item_completed.connect(lambda f: item_events.append(f))
        self.window.pipeline.batch_completed.connect(lambda count, errs: completed_events.append((count, errs)))

        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})

        started = self.window.pipeline.run_batch_analysis([fname], params)
        self.assertTrue(started)

        worker = self.window.pipeline._batch_worker
        self.assertIsNotNone(worker)
        worker.wait(3000)
        for _ in range(10):
            QApplication.processEvents()
            time.sleep(0.02)

        # Verifica se o progresso (1, 1), item e finalização foram emitidos
        self.assertIn((1, 1), progress_events)
        self.assertIn(fname, item_events)
        self.assertEqual(len(completed_events), 1)
        self.assertEqual(completed_events[0][0], 1)
        self.assertIn(fname, self.window.ctx.analysis_cache)

    def test_12_batch_preserves_active_file_state(self):
        """Teste de regressão: análise em lote com múltiplos arquivos preserva estritamente o arquivo ativo."""
        file_a = "file_a.wav"
        file_b = "file_b.wav"
        file_c = "file_c.wav"
        self.window.loaded_files[file_a] = self.sample_wav
        self.window.loaded_files[file_b] = self.sample_wav
        self.window.loaded_files[file_c] = self.sample_wav

        params = DEFAULT_ALGO_PARAMS.copy()
        params.update({"dur_min": 5.0, "dur_max": 40.0, "min_p": 2})

        # 1. Usuário seleciona e analisa inicialmente o file_a (tornando-o ativo)
        self.window.run_analysis(file_a, params, render=True)
        self.assertEqual(self.window.ctx.active_filename, file_a)
        initial_active_heavy = self.window.ctx.active_heavy_data
        self.assertIsNotNone(initial_active_heavy)

        # 2. Executa lote com file_a, file_b e file_c (file_b e file_c processados em background)
        completed_events = []
        self.window.pipeline.batch_completed.connect(lambda count, errs: completed_events.append((count, errs)))

        started = self.window.pipeline.run_batch_analysis([file_a, file_b, file_c], params)
        self.assertTrue(started)

        worker = self.window.pipeline._batch_worker
        self.assertIsNotNone(worker)
        worker.wait(6000)
        for _ in range(15):
            QApplication.processEvents()
            time.sleep(0.02)

        # 3. Todos os arquivos devem estar presentes no cache da sessão
        self.assertEqual(len(completed_events), 1)
        self.assertIn(file_a, self.window.ctx.analysis_cache)
        self.assertIn(file_b, self.window.ctx.analysis_cache)
        self.assertIn(file_c, self.window.ctx.analysis_cache)

        # 4. CRÍTICO: O arquivo ativo e o active_heavy_data no SessionContext DEVEM ser estritamente de file_a!
        self.assertEqual(self.window.ctx.active_filename, file_a)
        self.assertIs(self.window.ctx.active_heavy_data, self.window.ctx.analysis_cache[file_a])
        self.assertIsNot(self.window.ctx.active_heavy_data, self.window.ctx.analysis_cache[file_b])
        self.assertIsNot(self.window.ctx.active_heavy_data, self.window.ctx.analysis_cache[file_c])
        self.assertEqual(self.window.ctx.peaks_detected, self.window.ctx.analysis_cache[file_a]["peaks_detected"])

if __name__ == '__main__':
    unittest.main()
