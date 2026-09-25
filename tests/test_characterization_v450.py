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
from ui.controllers.navigation_controller import NavigationController
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

        # 7. render_file com arquivo inexistente no cache preserva estado sem renderização inconsistente
        old_active = pr.session_context.active_filename
        pr.render_file("arquivo_inexistente_no_cache.wav")
        self.assertEqual(pr.session_context.active_filename, old_active)

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

        # 2. Renderiza Arquivo B (deve alternar todo o estado atômico e emitir state_changed)
        emitted_signals = []
        self.window.ctx.state_changed.connect(emitted_signals.append)

        pr.render_file(fname_b)
        self.assertEqual(self.window.ctx.active_filename, fname_b)
        self.assertIs(self.window.ctx.active_heavy_data, data_b)
        self.assertEqual(self.window.ctx.peaks_detected, [500, 700])
        self.assertEqual(self.window.ctx.peaks_user_verified, [700])
        self.assertEqual(self.window.ctx.pulse_metadata, {700: {"idx": 700, "freq": 6000.0}})

        # Comprova emissão estrita dos sinais de mudança de estado da sessão
        for expected_category in ["active_filename", "active_heavy_data", "peaks_detected", "peaks_user_verified", "pulse_metadata"]:
            self.assertIn(expected_category, emitted_signals, f"Sinal state_changed('{expected_category}') não foi emitido na ativação.")

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

    def test_17_run_analysis_render_switches_complete_active_state(self):
        """FASE 3: Comprova que run_analysis(render=True) utiliza atomicamente

        activate_cached_file(), sincronizando todo o estado ativo mesmo quando
        outro arquivo já estava ativo anteriormente, com resultados deliberadamente distintos."""
        fname_a = "file_A.wav"
        fname_b = "file_B.wav"
        self.window.loaded_files[fname_a] = self.sample_wav
        self.window.loaded_files[fname_b] = self.sample_wav
        self.window.ctx.loaded_files[fname_a] = self.sample_wav
        self.window.ctx.loaded_files[fname_b] = self.sample_wav

        params = DEFAULT_ALGO_PARAMS.copy()

        # Obtém uma tupla real completa do CricketAnalyzer para servir de base estrutural
        real_tuple = CricketAnalyzer.analyze(self.sample_wav, params)

        # Configura resultado analítico deliberadamente distinto para o Arquivo A
        list_a = list(real_tuple)
        list_a[4] = [100, 200]    # peaks
        list_a[15] = 4500.0       # carrier_freq
        res_a = tuple(list_a)

        # Configura resultado analítico deliberadamente distinto para o Arquivo B
        list_b = list(real_tuple)
        list_b[4] = [500, 700]    # peaks
        list_b[15] = 6200.0       # carrier_freq
        res_b = tuple(list_b)

        # Mocka CricketAnalyzer.analyze retornando res_a no 1º run_analysis e res_b no 2º
        with patch.object(CricketAnalyzer, "analyze", side_effect=[res_a, res_b]):
            # 1. Analisa e ativa o Arquivo A
            self.window.pipeline.run_analysis(fname_a, params, render=True)
            self.assertEqual(self.window.ctx.active_filename, fname_a)
            self.assertEqual(self.window.ctx.peaks_detected, [100, 200])
            self.assertEqual(self.window.ctx.peaks_user_verified, [100, 200])
            self.assertAlmostEqual(self.window.ctx.active_heavy_data["carrier_freq"], 4500.0)

            # 2. Analisa o Arquivo B com render=True (deve comutar atomicamente TODO o estado)
            self.window.pipeline.run_analysis(fname_b, params, render=True)

            # Validações estritas comprovando que todo o estado ativo pertence a B e NADA a A
            self.assertEqual(self.window.ctx.active_filename, fname_b)
            self.assertIs(self.window.ctx.active_heavy_data, self.window.ctx.analysis_cache[fname_b])

            self.assertEqual(self.window.ctx.peaks_detected, [500, 700])
            self.assertNotEqual(self.window.ctx.peaks_detected, [100, 200])

            self.assertEqual(self.window.ctx.peaks_user_verified, [500, 700])
            self.assertNotEqual(self.window.ctx.peaks_user_verified, [100, 200])

            self.assertAlmostEqual(self.window.ctx.active_heavy_data["carrier_freq"], 6200.0)
            self.assertNotAlmostEqual(self.window.ctx.active_heavy_data["carrier_freq"], 4500.0)

    def test_18_navigation_controller_extracted_and_single_ownership(self):
        """FASE 4: Comprova instanciação do NavigationController, sinais semânticos
        e eliminação total de dual ownership através de aliases bidirecionais."""
        self.assertIsNotNone(self.window.nav_controller)
        self.assertIsInstance(self.window.nav_controller, NavigationController)

        # Conexão entre PlotRenderers e NavigationController
        self.assertIs(self.window.plot_renderers.nav_controller, self.window.nav_controller)

        # Validação de ownership único e compartilhamento de referências de estado
        nc = self.window.nav_controller
        self.assertIs(self.window.cursor_lines, nc.cursor_lines)
        self.assertIs(self.window.backgrounds, nc.backgrounds)
        self.assertEqual(self.window.bg_cache_valid, nc.bg_cache_valid)
        self.assertEqual(self.window.panning, nc.panning)
        self.assertIs(self.window.pulse_hover_data, nc.pulse_hover_data)
        self.assertIs(self.window._click_alignment_lines, nc._click_alignment_lines)
        self.assertEqual(self.window.start_xlim, nc.start_xlim)
        self.assertEqual(self.window.start_ylim, nc.start_ylim)

        # Mutação através de setters na MainWindow reflete no NavigationController
        self.window.cursor_lines = ["dummy_line"]
        self.assertEqual(nc.cursor_lines, ["dummy_line"])
        self.window.cursor_lines = []

        self.window.panning = True
        self.assertTrue(nc.panning)
        self.window.panning = False
        self.assertFalse(nc.panning)

        # Verificação da existência dos sinais do contrato §4.3
        self.assertTrue(hasattr(nc, "viewport_changed"))
        self.assertTrue(hasattr(nc, "hover_changed"))
        self.assertTrue(hasattr(nc, "pan_started"))
        self.assertTrue(hasattr(nc, "pan_finished"))

    def test_19_navigation_controller_pan_lifecycle_and_signals(self):
        """FASE 4: Comprova o ciclo completo de pan (início, movimento com clamping, término)
        e a emissão correspondente de pan_started, pan_finished e viewport_changed."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        self.window.pipeline.run_analysis(fname, DEFAULT_ALGO_PARAMS.copy(), render=True)

        nc = self.window.nav_controller
        ax = self.window.panel_wave.ax

        pan_started_spy = MagicMock()
        pan_finished_spy = MagicMock()
        viewport_spy = MagicMock()

        nc.pan_started.connect(pan_started_spy)
        nc.pan_finished.connect(pan_finished_spy)
        nc.viewport_changed.connect(viewport_spy)

        # 1. Inicia Pan com botão direito (button == 3)
        ev_press = MouseEvent('button_press_event', self.window.panel_wave.canvas, x=200, y=150, button=3)
        ev_press.inaxes = ax
        self.window.on_press(ev_press)

        pan_started_spy.assert_called_once()
        self.assertTrue(nc.panning)
        self.assertIs(nc.active_ax, ax)

        # 2. Movimento do mouse durante pan
        nc._last_pan_time = 0.0  # Reseta throttle para garantir execução
        ev_motion = MouseEvent('motion_notify_event', self.window.panel_wave.canvas, x=250, y=170, button=3)
        ev_motion.inaxes = ax
        self.window.on_motion(ev_motion)

        viewport_spy.assert_called()
        call_xmin, call_xmax = viewport_spy.call_args[0]
        self.assertLess(call_xmin, call_xmax)

        # 3. Finalização do Pan
        ev_release = MouseEvent('button_release_event', self.window.panel_wave.canvas, x=250, y=170, button=3)
        ev_release.inaxes = ax
        self.window.on_release(ev_release)

        pan_finished_spy.assert_called_once()
        self.assertFalse(nc.panning)
        self.assertIsNone(nc.active_ax)

    def test_20_navigation_controller_zoom_and_bounds_clamping(self):
        """FASE 4: Comprova zoom centrado no cursor, restrição por _clamp_bounds
        e sincronização entre eixos temporal wave e spec via NavigationController."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        self.window.pipeline.run_analysis(fname, DEFAULT_ALGO_PARAMS.copy(), render=True)

        nc = self.window.nav_controller
        ax_wave = self.window.panel_wave.ax
        ax_spec = self.window.panel_spec.ax

        initial_xlim = ax_wave.get_xlim()
        initial_width = initial_xlim[1] - initial_xlim[0]

        viewport_spy = MagicMock()
        nc.viewport_changed.connect(viewport_spy)

        # 1. Zoom in (scroll 'up' centrado em x=0.25)
        ev_zoom_in = MouseEvent('scroll_event', self.window.panel_wave.canvas, x=150, y=150, button='up', step=1)
        ev_zoom_in.inaxes = ax_wave
        ev_zoom_in.xdata = 0.25
        ev_zoom_in.ydata = 0.0
        self.window.zoom_graph(ev_zoom_in)

        new_xlim = ax_wave.get_xlim()
        new_width = new_xlim[1] - new_xlim[0]
        self.assertLess(new_width, initial_width)
        viewport_spy.assert_called()

        # 2. Zoom out sincronizado com botão de sincronização ativo
        self.window.btn_sync.setChecked(True)
        ev_zoom_out = MouseEvent('scroll_event', self.window.panel_wave.canvas, x=150, y=150, button='down', step=-1)
        ev_zoom_out.inaxes = ax_wave
        ev_zoom_out.xdata = 0.25
        ev_zoom_out.ydata = 0.0
        self.window.zoom_graph(ev_zoom_out)

        # Ambos os eixos de tempo (wave e spec) devem ter recebido o mesmo xlim
        self.assertAlmostEqual(ax_wave.get_xlim()[0], ax_spec.get_xlim()[0], places=5)
        self.assertAlmostEqual(ax_wave.get_xlim()[1], ax_spec.get_xlim()[1], places=5)

        # 3. Teste explícito de _clamp_bounds
        dur = float(self.window.ctx.active_heavy_data["duration"])
        clamped = nc._clamp_bounds(ax_wave, -0.5, dur + 1.0, -2.0, 2.0)
        self.assertEqual(clamped[0], 0.0)
        self.assertEqual(clamped[1], dur)
        self.assertEqual(clamped[2], -1.05)
        self.assertEqual(clamped[3], 1.05)

    def test_21_navigation_controller_hover_metadata_and_signals(self):
        """FASE 4: Comprova detecção de hover sobre marcadores de pulsos, formatação
        de coordenadas e emissão semântica de hover_changed."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        self.window.pipeline.run_analysis(fname, DEFAULT_ALGO_PARAMS.copy(), render=True)

        nc = self.window.nav_controller
        self.assertGreater(len(nc.pulse_hover_data), 0)

        first_pulse = nc.pulse_hover_data[0]
        t_pulse = first_pulse["time"]

        hover_spy = MagicMock()
        nc.hover_changed.connect(hover_spy)

        ax = self.window.panel_wave.ax
        # Transforma coordenada de dados em coordenada de display (pixels)
        pt_disp = ax.transData.transform((t_pulse, first_pulse["env_y"]))

        # 1. Movimento diretamente sobre o marcador do pulso
        ev_hover = MouseEvent('motion_notify_event', self.window.panel_wave.canvas, x=pt_disp[0], y=pt_disp[1])
        ev_hover.inaxes = ax
        ev_hover.xdata = t_pulse
        ev_hover.ydata = first_pulse["env_y"]
        self.window.on_motion(ev_hover)

        # Valida emissão do sinal com o dicionário de metadados do pulso
        hover_spy.assert_called()
        emitted_payload = hover_spy.call_args[0][0]
        self.assertIsNotNone(emitted_payload)
        self.assertEqual(emitted_payload["time"], t_pulse)

        # 2. Movimento para área vazia (fora do raio de tolerância de pixels)
        hover_spy.reset_mock()
        ev_away = MouseEvent('motion_notify_event', self.window.panel_wave.canvas, x=0, y=0)
        ev_away.inaxes = ax
        ev_away.xdata = t_pulse + 5.0
        ev_away.ydata = 0.9
        self.window.on_motion(ev_away)

        hover_spy.assert_called()
        self.assertIsNone(hover_spy.call_args[0][0])

        # 3. Saída do eixo oculta coord_label
        self.window.panel_wave.coord_label.setVisible(True)
        ev_leave = MouseEvent('axes_leave_event', self.window.panel_wave.canvas, x=0, y=0)
        ev_leave.inaxes = ax
        self.window.on_axes_leave(ev_leave)
        self.assertFalse(self.window.panel_wave.coord_label.isVisible())

    def test_22_navigation_controller_background_blitting_and_cursor(self):
        """FASE 4: Comprova captura de backgrounds para blitting ultra-rápido,
        atualização do cursor de reprodução e preservação do cache de background."""
        fname = "sample_chirp.wav"
        self.window.loaded_files[fname] = self.sample_wav
        self.window.ctx.loaded_files[fname] = self.sample_wav
        self.window.pipeline.run_analysis(fname, DEFAULT_ALGO_PARAMS.copy(), render=True)

        nc = self.window.nav_controller
        self.assertEqual(len(nc.cursor_lines), 2)  # wave e spec

        # 1. Captura de backgrounds
        nc.capture_backgrounds()
        self.assertTrue(nc.bg_cache_valid)
        self.assertEqual(len(nc.backgrounds), 2)

        # 2. Atualização de posição do cursor com blitting
        target_pos = 0.25
        nc.update_playback_cursor(target_pos)

        # Verifica que as linhas de cursor foram atualizadas para a posição solicitada
        for line in nc.cursor_lines:
            self.assertEqual(list(line.get_xdata()), [target_pos, target_pos])

        # O cache de background deve permanecer íntegro após o blitting
        self.assertTrue(nc.bg_cache_valid)

    def test_23_navigation_controller_robustness_and_edge_cases(self):
        """FASE 4: Comprova robustez do NavigationController contra casos degenerados
        (limites invertidos, divisão por zero em zoom, heavy_data com campos nulos e invalidação de cache)."""
        nc = self.window.nav_controller
        ax = self.window.panel_wave.ax

        # 1. Limites invertidos em _clamp_bounds são reordenados canonicamente
        xmin, xmax, ymin, ymax = nc._clamp_bounds(ax, 0.8, 0.2, 1.0, -1.0)
        self.assertLessEqual(xmin, xmax)
        self.assertLessEqual(ymin, ymax)

        # 2. Zoom com eixo degenerado (delta zero) não gera ZeroDivisionError
        with patch.object(ax, 'get_xlim', return_value=(0.5, 0.5)), \
             patch.object(ax, 'get_ylim', return_value=(0.0, 0.0)):
            ev_zero_delta = MouseEvent('scroll_event', self.window.panel_wave.canvas, x=100, y=100, button='up', step=1)
            ev_zero_delta.inaxes = ax
            ev_zero_delta.xdata = 0.5
            ev_zero_delta.ydata = 0.0
            # Não deve lançar ZeroDivisionError
            nc.zoom_graph(ev_zero_delta)

        # 3. update_hover_data com chaves None no dicionário
        sparse_heavy = {
            "rate": 44100,
            "duration": 1.0,
            "env1_smooth": None,
            "env": None,
            "chirp_peaks_list": None,
            "distant_peaks": None,
            "discarded_peaks_reasons": None,
            "params": None,
        }
        nc.update_hover_data(sparse_heavy)
        self.assertEqual(nc.pulse_hover_data, [])

        # 4. setup_cursor_lines invalida o cache de background
        nc.bg_cache_valid = True
        nc.backgrounds = ["dummy_cached_bg"]
        nc.setup_cursor_lines()
        self.assertFalse(nc.bg_cache_valid)
        self.assertEqual(nc.backgrounds, [])

if __name__ == '__main__':
    unittest.main()






