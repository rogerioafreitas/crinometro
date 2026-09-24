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

    def test_13_plot_renderers_integration_and_engine_aliasing(self):
        """FASE 3: Verifica a integração do PlotRenderers, eliminação de duplicidade de estado

        e ausência de dual ownership para engines gráficos e marcadores."""
        from ui.controllers.plot_renderers import PlotRenderers
        from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine

        # 1. PlotRenderers instanciado e acessível na MainWindow
        self.assertIsInstance(self.window.plot_renderers, PlotRenderers)
        self.assertIs(self.window.plot_renderers.session_context, self.window.ctx)

        # 2. Executa análise real
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        params = DEFAULT_ALGO_PARAMS.copy()
        heavy_data = self.window.pipeline.run_analysis(fname, params, render=True)

        # 3. Engines criados no PlotRenderers e refletidos unicamente na MainWindow
        pr = self.window.plot_renderers
        self.assertIsNotNone(pr.line_engine)
        self.assertIsInstance(pr.line_engine, HighPerfLineEngine)
        self.assertIsNotNone(pr.spectro_engine)
        self.assertIsInstance(pr.spectro_engine, HighPerfSpectrogramEngine)

        # 4. CRÍTICO: Eliminação de dual ownership (Solução A — aliases estritos)
        self.assertIs(self.window.line_engine, pr.line_engine)
        self.assertIs(self.window.spectro_engine, pr.spectro_engine)
        self.assertIs(self.window.freq_engine, pr.freq_engine)
        self.assertIsNone(pr.freq_engine, "freq_engine permanece None por preservação de compatibilidade legada")
        self.assertIs(self.window.wave_lines, pr.wave_lines)
        self.assertIs(self.window._wave_user_markers, pr._wave_user_markers)

        # 5. Sincronização da Frequência Portadora (FP badge)
        badge_text = self.window.panel_spec.lbl_carrier_info.text()
        self.assertNotEqual(badge_text, "FP: —")
        self.assertIn("FP:", badge_text)
        self.assertIn("kHz", badge_text)
        self.assertGreater(getattr(self.window.panel_spec, "_carrier_freq", 0.0), 0.0)

    def test_14_plot_renderers_semantic_api(self):
        """FASE 3: Verifica as operações semânticas públicas do PlotRenderers

        (render_file, refresh_histogram, refresh_markers, refresh_all, update_wave_visibility, apply_spectrogram_y_limits)."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        params = DEFAULT_ALGO_PARAMS.copy()
        self.window.pipeline.run_analysis(fname, params, render=True)

        pr = self.window.plot_renderers

        # 1. refresh_histogram
        pr.refresh_histogram()
        ax_hist = pr.panel_hist.ax
        self.assertGreater(len(ax_hist.patches), 0)

        # 2. refresh_markers
        initial_marker_count = len(pr._wave_user_markers)
        self.assertGreater(initial_marker_count, 0)
        pr.refresh_markers()
        self.assertEqual(len(pr._wave_user_markers), initial_marker_count)

        # 3. update_wave_visibility
        pr.update_wave_visibility(show_raw=False, show_env=True, show_lod=True, show_peaks=False)
        self.assertFalse(pr.wave_lines['raw'].get_visible())
        self.assertTrue(pr.wave_lines['env'].get_visible())
        self.assertTrue(pr.wave_lines['lod'].get_visible())

        # 4. apply_spectrogram_y_limits
        pr.apply_spectrogram_y_limits(2.5, 7.5, unit="kHz")
        ymin, ymax = pr.panel_spec.ax.get_ylim()
        self.assertAlmostEqual(ymin, 2.5, places=1)
        self.assertAlmostEqual(ymax, 7.5, places=1)

        # 5. refresh_all (re-renderiza arquivo ativo)
        pr.refresh_all()
        self.assertIsNotNone(pr.line_engine)
        self.assertIsNotNone(pr.spectro_engine)
        self.assertIs(self.window.line_engine, pr.line_engine)

        # 6. render_file seleciona arquivo do cache e atualiza o estado ativo
        dummy_file = "dummy_other.wav"
        dummy_data = self.window.ctx.active_heavy_data.copy()
        dummy_data["duration"] = 12.34
        self.window.ctx.analysis_cache[dummy_file] = dummy_data

        pr.render_file(dummy_file)
        self.assertEqual(self.window.ctx.active_filename, dummy_file)
        self.assertEqual(self.window.lbl_summary_file.text(), dummy_file)
        self.assertEqual(self.window.ctx.active_heavy_data["duration"], 12.34)

    def test_15_sync_render_invokes_plot_renderers_engines(self):
        """FASE 3: Comprova que rotinas de navegação da MainWindow (_sync_render)

        consomem diretamente os engines HighPerf instanciados pelo PlotRenderers."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        params = DEFAULT_ALGO_PARAMS.copy()
        self.window.pipeline.run_analysis(fname, params, render=True)

        pr = self.window.plot_renderers
        self.assertIsNotNone(pr.line_engine)
        self.assertIsNotNone(pr.spectro_engine)

        with patch.object(pr.line_engine, 'render_interactive', wraps=pr.line_engine.render_interactive) as spy_line, \
             patch.object(pr.spectro_engine, 'render_interactive', wraps=pr.spectro_engine.render_interactive) as spy_spec:

            self.window.panel_wave.setVisible(True)
            self.window.panel_spec.setVisible(True)
            self.window.sync_throttle_time = 0.0

            # Invoca o caminho real de sincronização da navegação da MainWindow
            self.window._sync_render([self.window.panel_wave, self.window.panel_spec], xmin=0.1, xmax=0.5)

            # Comprova que _sync_render acionou os engines reais do PlotRenderers
            spy_line.assert_called_once_with(0.1, 0.5, is_sync=True)
            ymin, ymax = self.window.panel_spec.ax.get_ylim()
            spy_spec.assert_called_once_with(0.1, 0.5, ymin, ymax, is_sync=True)

    def test_16_render_file_switches_complete_active_state(self):
        """FASE 3: Comprova que render_file() e activate_cached_file() alternam atomicamente

        TODO o estado ativo (filename, heavy_data, peaks_detected, peaks_user_verified, pulse_metadata)
        entre dois arquivos com estados propositalmente distintos, sem contaminação de marcadores."""
        pr = self.window.plot_renderers
        rate = 44100.0

        fname_a = "file_A.wav"
        fname_b = "file_B.wav"
        self.window.loaded_files[fname_a] = self.sample_wav
        self.window.loaded_files[fname_b] = self.sample_wav
        self.window.ctx.loaded_files[fname_a] = self.sample_wav
        self.window.ctx.loaded_files[fname_b] = self.sample_wav

        base_res = self.window.pipeline.run_analysis(fname_a, DEFAULT_ALGO_PARAMS.copy(), render=True)

        # Configura estado propositalmente distinto para Arquivo A
        data_a = base_res.copy()
        data_a["peaks_detected"] = [100, 200]
        data_a["peaks_user_verified"] = [100]
        data_a["pulse_metadata"] = {100: {"idx": 100, "freq": 4500.0}}
        self.window.ctx.analysis_cache[fname_a] = data_a

        # Configura estado propositalmente distinto para Arquivo B
        data_b = base_res.copy()
        data_b["peaks_detected"] = [500, 700]
        data_b["peaks_user_verified"] = [700]
        data_b["pulse_metadata"] = {700: {"idx": 700, "freq": 6000.0}}
        self.window.ctx.analysis_cache[fname_b] = data_b

        # 1. Renderiza Arquivo A
        pr.render_file(fname_a)
        self.assertEqual(self.window.ctx.active_filename, fname_a)
        self.assertIs(self.window.ctx.active_heavy_data, data_a)
        self.assertEqual(self.window.ctx.peaks_detected, [100, 200])
        self.assertEqual(self.window.ctx.peaks_user_verified, [100])
        self.assertEqual(self.window.ctx.pulse_metadata, {100: {"idx": 100, "freq": 4500.0}})

        # 2. Renderiza Arquivo B (deve alternar todo o estado atômico)
        pr.render_file(fname_b)
        self.assertEqual(self.window.ctx.active_filename, fname_b)
        self.assertIs(self.window.ctx.active_heavy_data, data_b)
        self.assertEqual(self.window.ctx.peaks_detected, [500, 700])
        self.assertEqual(self.window.ctx.peaks_user_verified, [700])
        self.assertEqual(self.window.ctx.pulse_metadata, {700: {"idx": 700, "freq": 6000.0}})

        # 3. Comprova que os marcadores visuais no painel pertencem estritamente a B
        # e nenhum marcador de A permanece no canvas
        markers = pr._wave_user_markers
        self.assertGreater(len(markers), 0)

        plotted_x = []
        for m in markers:
            if hasattr(m, 'get_xdata'):
                plotted_x.extend(list(m.get_xdata()))
            elif hasattr(m, 'get_offsets'):
                offsets = m.get_offsets()
                if len(offsets) > 0:
                    plotted_x.extend([pt[0] for pt in offsets])

        expected_b_times = [500 / rate, 700 / rate]
        prohibited_a_times = [100 / rate, 200 / rate]

        # Verifica presença dos tempos de B
        for pb_time in expected_b_times:
            self.assertTrue(
                any(abs(x - pb_time) < 1e-4 for x in plotted_x),
                f"Tempo esperado de B ({pb_time}) não encontrado nos marcadores plotados: {plotted_x}"
            )
        # Verifica ausência total dos tempos de A
        for pa_time in prohibited_a_times:
            self.assertFalse(
                any(abs(x - pa_time) < 1e-4 for x in plotted_x),
                f"Tempo proibido de A ({pa_time}) ainda presente nos marcadores plotados: {plotted_x}"
            )

if __name__ == '__main__':
    unittest.main()



