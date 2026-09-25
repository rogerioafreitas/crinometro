"""
Crinômetro - Pipeline Orchestrator Controller (v4.5.0).
Gerencia a execução e orquestração do pipeline bioacústico:
- Análise individual e em lote em thread secundária (GenericWorker).
- Cancelamento cooperativo de tarefas em andamento.
- Aplicação de resultados analíticos com integridade ao SessionContext.
- Reavaliação rápida de tolerância de frequência em tempo real.
- Adaptação dinâmica de parâmetros heurísticos via estatísticas de correções.
"""

import os
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from core.analyzer import CricketAnalyzer
from core.worker import GenericWorker
from core.learner import PulseLearner

class PipelineOrchestrator(QObject):
    analysis_started = pyqtSignal(str, bool)     # (filename, is_first_time)
    analysis_progress = pyqtSignal(int, int)      # (current, total)
    analysis_completed = pyqtSignal(str)         # (filename)
    analysis_failed = pyqtSignal(str, str)       # (filename, error_msg)
    analysis_cancelled = pyqtSignal(str)         # (filename)
    realtime_tolerance_updated = pyqtSignal(str) # (filename)

    # Sinais formais de alto nível para análise em lote (Roadmap FASE 2)
    batch_started = pyqtSignal(int)              # (total_files)
    batch_item_completed = pyqtSignal(str)       # (filename)
    batch_progress = pyqtSignal(int, int)        # (current, total)
    batch_completed = pyqtSignal(int, list)      # (success_count, errors)
    batch_failed = pyqtSignal(str)               # (error_message)
    batch_cancelled = pyqtSignal()               # ()

    def __init__(self, session_context, parent=None):
        super().__init__(parent)
        self.ctx = session_context
        self._reanalyze_worker = None
        self._batch_worker = None

        # Debounce de 25 ms para reavaliação contínua da tolerância
        self._pending_carrier_tol = None
        self._carrier_tol_timer = QTimer(self)
        self._carrier_tol_timer.setSingleShot(True)
        self._carrier_tol_timer.timeout.connect(self._execute_realtime_freq_tolerance)

    # ------------------------------------------------------------------ #
    # 1. Heurísticas Adaptativas (_adapt_advanced_params)                #
    # ------------------------------------------------------------------ #
    def _adapt_advanced_params(self):
        """Atualiza sobreposições adaptativas com estatísticas das correções atuais.

        Preserva os valores exatos de fisiologia: prominence (0.002 a 0.08),
        noise_floor (0.85 a 1.05) e width_min_ms limitado estritamente a 25.0 ms.
        """
        if not self.ctx.active_heavy_data or not self.ctx.peaks_user_verified:
            return
        env = self.ctx.active_heavy_data.get("env")
        if env is None:
            return
        rate = float(self.ctx.active_heavy_data.get("rate", 1.0))
        features = np.asarray([
            PulseLearner.extract_features_for_peak(p, rate, env)
            for p in self.ctx.peaks_user_verified
        ])
        if features.size == 0 or features.shape[1] < 14:
            return

        adaptation = float(self.ctx.algo_params.get("adaptation_rate", 0.10))
        adaptation = min(0.15, max(0.0, adaptation))

        # Ajuste seguro e fisiológico de proeminência relativa
        target_prom = float(np.percentile(features[:, 6], 20)) * 0.08
        current_prominence = float(self.ctx._adaptive_overrides.get(
            "prominence", self.ctx.algo_params.get("prominence", 0.01)
        ))
        new_prom = (1.0 - adaptation) * current_prominence + adaptation * target_prom
        
        overrides = dict(self.ctx._adaptive_overrides)
        overrides["prominence"] = float(np.clip(new_prom, 0.002, 0.08))

        # Manutenção de noise_floor em faixa segura (0.85 a 1.05)
        current_noise = float(overrides.get(
            "noise_floor", self.ctx.algo_params.get("noise_floor", 0.90)
        ))
        overrides["noise_floor"] = float(np.clip(current_noise, 0.85, 1.05))

        target_width_ms = float(np.median(features[:, 1]) * 1000.0)
        if target_width_ms > 0:
            current_width = float(overrides.get(
                "width_min_ms", self.ctx.algo_params.get("width_min_ms", 0.0)
            ))
            new_width = (1.0 - adaptation) * current_width + adaptation * (target_width_ms * 0.40)
            overrides["width_min_ms"] = float(np.clip(new_width, 0.0, 25.0))

        self.ctx._adaptive_overrides = overrides

    # ------------------------------------------------------------------ #
    # 2. Tolerância Espectral em Tempo Real                             #
    # ------------------------------------------------------------------ #
    def apply_realtime_freq_tolerance(self, new_tol, source_panel=None):
        """Dispara timer de debounce (25 ms) para deslizamento contínuo sem sobrecarga."""
        d = self.ctx.active_heavy_data
        if not d:
            return
        self._pending_carrier_tol = new_tol
        self._carrier_tol_timer.start(25)

    def _execute_realtime_freq_tolerance(self):
        """Executa a reavaliação instantânea de tolerância espectral sobre o sinal ativo."""
        d = self.ctx.active_heavy_data
        if not d:
            return
        new_tol = getattr(self, "_pending_carrier_tol", float(self.ctx.algo_params.get("freq_tolerance_hz", 700.0)))
        if new_tol is None:
            new_tol = float(self.ctx.algo_params.get("freq_tolerance_hz", 700.0))

        valid_peaks_stage2 = d.get("valid_peaks_stage2", d.get("peaks_detected", []))
        carrier_freq = float(d.get("carrier_freq", 5000.0))
        rate = float(d.get("rate", 44100))
        t_spec = d.get("t_spec", np.array([]))
        dom_freqs = d.get("dom_freqs", np.array([]))
        env = d.get("env1_smooth", d.get("env", np.array([])))
        data_b1 = d.get("data_b1", None)
        effective_params = {**self.ctx.algo_params, **self.ctx._adaptive_overrides, "freq_tolerance_hz": new_tol}

        # Gate estrito de ML via SessionContext
        use_ml = self.ctx.use_machine_learning
        learner = self.ctx.pulse_learner if use_ml else None

        peaks, chirps, chirp_peaks_list, media, moda, all_distant, discarded_reasons = (
            CricketAnalyzer.reevaluate_carrier_tolerance(
                valid_peaks_stage2, carrier_freq, new_tol,
                rate, t_spec, dom_freqs, env, effective_params,
                data_b1=data_b1, pulse_learner=learner,
                base_discarded_reasons=d.get("discarded_peaks_reasons", {})
            )
        )

        d["peaks"] = list(peaks)
        d["chirps"] = chirps
        d["chirp_peaks_list"] = chirp_peaks_list
        d["media"] = media
        d["moda"] = moda
        d["distant_peaks"] = list(all_distant)
        d["discarded_peaks_reasons"] = discarded_reasons
        if "params" in d:
            d["params"]["freq_tolerance_hz"] = new_tol

        # Emite notificação de que os cálculos de tolerância foram concluídos
        self.realtime_tolerance_updated.emit(self.ctx.active_filename or "")

    # ------------------------------------------------------------------ #
    # 3. Aplicação Integral de Resultados (_apply_analysis_results)      #
    # ------------------------------------------------------------------ #
    def _apply_analysis_results(self, filename, results, params=None):
        """Aplica os 21 elementos gerados por CricketAnalyzer ao SessionContext.

        Preserva todos os 25 campos de heavy_data, conversão para float32,
        reagrupamento de correções e atualização do cache analítico.
        Garante que, se o arquivo analisado for o ativo, active_heavy_data é
        atualizado diretamente no SessionContext.
        """
        if params is None:
            params = self.ctx.algo_params.copy()

        rate, data, data_b1, env, peaks, chirps, chirp_peaks_list, media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration = results[:14]
        distant_peaks = results[14] if len(results) > 14 else []
        carrier_freq = float(results[15]) if len(results) > 15 else 0.0
        discarded_peaks_reasons = results[16] if len(results) > 16 else {}
        valid_peaks_stage2 = results[17] if len(results) > 17 else list(peaks)
        peak_dur_dict = results[18] if len(results) > 18 else {}
        f_psd = results[19] if len(results) > 19 else np.array([])
        Pxx_db = results[20] if len(results) > 20 else np.array([])

        # Converte dados volumosos de ponto flutuante para float32 (reduz 50% de RAM)
        if isinstance(data, np.ndarray) and data.dtype != np.float32:
            data = data.astype(np.float32)
        if isinstance(data_b1, np.ndarray) and data_b1.dtype != np.float32:
            data_b1 = data_b1.astype(np.float32)
        if isinstance(env, np.ndarray) and env.dtype != np.float32:
            env = env.astype(np.float32)
        if isinstance(Sxx_db, np.ndarray) and Sxx_db.dtype != np.float32:
            Sxx_db = Sxx_db.astype(np.float32)

        file_peaks_detected = [int(p) for p in np.asarray(peaks, dtype=int)]
        stored_corrections = self.ctx.corrections_by_file.get(filename)
        effective_params = {**params, **self.ctx._adaptive_overrides}

        file_pulse_metadata = {}

        if stored_corrections is not None:
            extracted_peaks = []
            for item in stored_corrections:
                if isinstance(item, dict):
                    extracted_peaks.append(item["idx"])
                    file_pulse_metadata[item["idx"]] = item
                else:
                    extracted_peaks.append(int(item))
            file_peaks_user_verified = extracted_peaks
            peaks_added = sorted(set(extracted_peaks) - set(file_peaks_detected))
            peaks_removed = sorted(set(file_peaks_detected) - set(extracted_peaks))

            if peaks_removed:
                distant_peaks = sorted(list(set(distant_peaks) | set(peaks_removed)))
                for pk in peaks_removed:
                    discarded_peaks_reasons[int(pk)] = "Removido manualmente pelo usuário"

            if peaks_added or peaks_removed:
                effective_peaks = np.asarray(
                    sorted(set(file_peaks_detected) | set(peaks_added) - set(peaks_removed)),
                    dtype=int
                )
                if len(effective_peaks) >= 2:
                    try:
                        chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
                            effective_peaks, effective_params, rate, env, raw_signal=data_b1
                        )
                    except Exception:
                        pass
        else:
            file_peaks_user_verified = list(file_peaks_detected)

        heavy_data = {
            "rate": rate, "data": data, "data_b1": data_b1, "env": env, "peaks": list(file_peaks_detected), "chirps": chirps,
            "chirp_peaks_list": chirp_peaks_list, "chirp_peaks": list(chirp_peaks_list), "media": media, "moda": moda,
            "f_spec": f_spec, "t_spec": t_spec, "Sxx_db": Sxx_db, "dom_freqs": dom_freqs,
            "duration": audio_duration, "params": params.copy(),
            "peaks_detected": list(file_peaks_detected),
            "peaks_user_verified": list(file_peaks_user_verified),
            "distant_peaks": list(distant_peaks),
            "carrier_freq": carrier_freq,
            "discarded_peaks_reasons": discarded_peaks_reasons,
            "valid_peaks_stage2": list(valid_peaks_stage2),
            "peak_dur_dict": peak_dur_dict,
            "f_psd": f_psd,
            "Pxx_db": Pxx_db,
            "pulse_metadata": dict(file_pulse_metadata),
        }


        # 1. Atualiza sempre o cache da sessão para o arquivo analisado
        new_cache = dict(self.ctx.analysis_cache)
        new_cache[filename] = heavy_data
        self.ctx.analysis_cache = new_cache

        # 2. Atualiza os estados ativos do SessionContext ESTRITAMENTE se este arquivo for o arquivo ativo
        if self.ctx.active_filename == filename:
            self.ctx.peaks_detected = list(file_peaks_detected)
            self.ctx.peaks_user_verified = list(file_peaks_user_verified)
            self.ctx.pulse_metadata = file_pulse_metadata
            self.ctx.active_heavy_data = heavy_data

        return heavy_data

    # ------------------------------------------------------------------ #
    # 4. Execução Síncrona / Contrato v4.5.0 (run_analysis)               #
    # ------------------------------------------------------------------ #
    def run_analysis(self, filename, params, render=True, validate_all=False):
        """Executa a análise mantendo a assinatura exata do contrato ROADMAP v4.5.0."""
        file_path = self.ctx.loaded_files.get(filename)
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {filename}")

        effective_params = {**params, **self.ctx._adaptive_overrides}
        use_ml = self.ctx.use_machine_learning
        learner = self.ctx.pulse_learner if use_ml else None

        res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner)
        heavy_data = self._apply_analysis_results(filename, res, params=params)

        if render:
            self.ctx.activate_cached_file(filename)
            self.analysis_completed.emit(filename)

        return heavy_data


    # ------------------------------------------------------------------ #
    # 5. Execução em Lote Assíncrona (run_batch_analysis)                #
    # ------------------------------------------------------------------ #
    def run_batch_analysis(self, checked_files, params):
        """Gerencia worker de análise em lote e emite sinais de alto nível de ponta a ponta.
        
        O ciclo de vida do GenericWorker é de propriedade exclusiva do PipelineOrchestrator.
        Nenhum sinal do worker é exposto diretamente à MainWindow, eliminando qualquer
        janela de corrida na conexão de sinais e prevenindo renderizações duplicadas.
        """
        if not checked_files:
            return False

        if self._batch_worker and self._batch_worker.isRunning():
            return False

        effective_params = {**params, **self.ctx._adaptive_overrides}
        use_ml = self.ctx.use_machine_learning
        learner = self.ctx.pulse_learner if use_ml else None

        self.batch_started.emit(len(checked_files))

        def _task():
            success_count = 0
            errors = []
            worker = self._batch_worker
            for i, fname in enumerate(checked_files):
                if worker and worker.abort_requested:
                    break
                if fname not in self.ctx.loaded_files or not os.path.exists(self.ctx.loaded_files[fname]):
                    continue
                try:
                    fpath = self.ctx.loaded_files[fname]
                    res = CricketAnalyzer.analyze(fpath, effective_params, pulse_learner=learner)
                    if worker and not worker.abort_requested:
                        worker.result_ready_signal.emit(fname, res)
                        success_count += 1
                except Exception as exc:
                    errors.append(f"{fname}: {exc}")

                if worker and not worker.abort_requested:
                    worker.progress_signal.emit(i + 1, len(checked_files))

            return success_count, errors

        worker = GenericWorker(_task)
        self._batch_worker = worker

        def _on_single_result(fname, res):
            is_active = (self.ctx.active_filename == fname)
            self._apply_analysis_results(fname, res, params=params)
            self.batch_item_completed.emit(fname)
            # Centraliza a autoridade visual: emite analysis_completed apenas se for o arquivo ativo
            if is_active:
                self.analysis_completed.emit(fname)

        def _on_progress(current, total):
            self.analysis_progress.emit(current, total)
            self.batch_progress.emit(current, total)

        def _on_finished(result):
            success_count, errors = result
            self.batch_completed.emit(success_count, errors)

        def _on_error(err_msg):
            self.batch_failed.emit(err_msg)

        worker.result_ready_signal.connect(_on_single_result)
        worker.progress_signal.connect(_on_progress)
        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)

        worker.start()
        return True

    # ------------------------------------------------------------------ #
    # 6. Reanálise em Background (force_reanalyze)                       #
    # ------------------------------------------------------------------ #
    def force_reanalyze(self, filename):
        """Inicia análise em thread secundária GenericWorker."""
        if not filename or filename not in self.ctx.loaded_files or not os.path.exists(self.ctx.loaded_files[filename]):
            self.analysis_failed.emit(filename or "", "Arquivo não carregado ou não encontrado.")
            return

        self.ctx.active_filename = filename
        is_first_time = (filename not in self.ctx.analysis_cache)
        self.analysis_started.emit(filename, is_first_time)

        def _task():
            # 1. Se o usuário fez correções, atualiza o modelo ML
            use_ml = self.ctx.use_machine_learning
            if (self.ctx.active_heavy_data and self.ctx.active_filename == filename and
                filename in self.ctx.corrections_by_file and self.ctx.peaks_user_verified and use_ml):
                rate = float(self.ctx.active_heavy_data.get("rate", 1.0))
                env = self.ctx.active_heavy_data.get("env")
                data_b1 = self.ctx.active_heavy_data.get("data_b1")
                if env is not None:
                    try:
                        self.ctx.pulse_learner.update_from_corrections(
                            self.ctx.peaks_detected, self.ctx.peaks_user_verified, rate, env, raw_signal=data_b1
                        )
                        self._adapt_advanced_params()
                        self.ctx.pulse_learner.save_to_config()
                    except Exception:
                        pass

            effective_params = {**self.ctx.algo_params, **self.ctx._adaptive_overrides}
            file_path = self.ctx.loaded_files[filename]
            learner = self.ctx.pulse_learner if use_ml else None

            cached_spec = None
            if self.ctx.active_heavy_data and self.ctx.active_filename == filename:
                if all(self.ctx.active_heavy_data.get(k) is not None for k in ("f_spec", "t_spec", "Sxx_db", "dom_freqs")):
                    cached_spec = {
                        "f_spec": self.ctx.active_heavy_data.get("f_spec"),
                        "t_spec": self.ctx.active_heavy_data.get("t_spec"),
                        "Sxx_db": self.ctx.active_heavy_data.get("Sxx_db"),
                        "dom_freqs": self.ctx.active_heavy_data.get("dom_freqs"),
                    }

            res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner, cached_spec=cached_spec)
            return res

        worker = GenericWorker(_task)
        self._reanalyze_worker = worker

        def _on_finished(results):
            # _apply_analysis_results atualiza active_heavy_data e cache
            self._apply_analysis_results(filename, results)
            self.analysis_completed.emit(filename)

        def _on_error(err_msg):
            self.analysis_failed.emit(filename, err_msg)

        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)
        worker.start()

    # ------------------------------------------------------------------ #
    # 7. Cancelamento Cooperativo (abort_current_analysis)               #
    # ------------------------------------------------------------------ #
    def abort_current_analysis(self):
        """Cancela cooperativamente qualquer worker em execução (individual ou lote)."""
        aborted = False
        if self._reanalyze_worker and self._reanalyze_worker.isRunning():
            self._reanalyze_worker.abort()
            aborted = True
        if self._batch_worker and self._batch_worker.isRunning():
            self._batch_worker.abort()
            aborted = True
            self.batch_cancelled.emit()

        if aborted:
            active_name = self.ctx.active_filename or ""
            self.analysis_cancelled.emit(active_name)
        return aborted
