"""
ui/controllers/editor_controller.py
-----------------------------------
FASE 5 — Edição de pulsos, histórico de alterações e integração com PulseLearner.

Responsabilidade: Isolar a manipulação interativa de marcações de pulsos
(adição, remoção, alternância), hit-box snapping em pixels e tempo, pilha de
desfeita (undo history), recálculo imediato de chilreios e métricas
(via CricketAnalyzer.regroup_chirps), persistência de correções no arquivo
de configuração e coordenação do retreinamento supervisionado do PulseLearner.

Comunicação semântica via sinais Qt:
  - pulse_added(int)
  - pulse_removed(int)
  - pulses_changed(list)
  - undo_availability_changed(bool)
  - metrics_recalculated(dict)
  - learning_started()
  - learning_completed(int, str)  # (num_corrections, filename)
  - learning_failed(str)

Consome SessionContext como fonte de verdade de dados e PlotRenderers /
NavigationController para orquestração visual sem acoplamento reverso.
"""

import json
import os
import tempfile
import weakref
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from utils.constants import CONFIG_FILE
from core.analyzer import CricketAnalyzer
from core.worker import GenericWorker


class EditorController(QObject):
    """Controlador de edição de pulsos e aprendizado supervisionado do Crinômetro."""

    # Sinais semânticos (contrato FASE 5 §5.3)
    pulse_added = pyqtSignal(int)
    pulse_removed = pyqtSignal(int)
    pulses_changed = pyqtSignal(list)
    undo_availability_changed = pyqtSignal(bool)
    metrics_recalculated = pyqtSignal(dict)
    learning_started = pyqtSignal()
    learning_completed = pyqtSignal(int, str)
    learning_failed = pyqtSignal(str)

    def __init__(
        self,
        session_context,
        plot_renderers=None,
        navigation_controller=None,
        pipeline_orchestrator=None,
        main_window=None,
        config_file: str = CONFIG_FILE,
        parent=None,
    ):
        super().__init__(parent)
        self.session_context = session_context
        self._plot_renderers = weakref.ref(plot_renderers) if plot_renderers is not None else lambda: None
        self._nav_controller = weakref.ref(navigation_controller) if navigation_controller is not None else lambda: None
        self._pipeline = weakref.ref(pipeline_orchestrator) if pipeline_orchestrator is not None else lambda: None
        self._main_window = weakref.ref(main_window) if main_window is not None else lambda: None
        self.config_file = config_file

        # Estado autoritativo de histórico de edição (propriedade única de EditorController)
        self._pulse_edit_history: list = []
        self._learn_worker = None

    # ------------------------------------------------------------------
    # Propriedades de acesso a componentes externos via weakref
    # ------------------------------------------------------------------

    @property
    def main_window(self):
        return self._main_window()

    @property
    def plot_renderers(self):
        return self._plot_renderers()

    def set_plot_renderers(self, plot_renderers):
        self._plot_renderers = weakref.ref(plot_renderers) if plot_renderers is not None else lambda: None

    @property
    def nav_controller(self):
        return self._nav_controller()

    def set_navigation_controller(self, nav_controller):
        self._nav_controller = weakref.ref(nav_controller) if nav_controller is not None else lambda: None

    @property
    def pipeline(self):
        return self._pipeline()

    def set_pipeline_orchestrator(self, pipeline):
        self._pipeline = weakref.ref(pipeline) if pipeline is not None else lambda: None

    @property
    def all_panels(self):
        win = self.main_window
        if win is not None and hasattr(win, "all_panels"):
            return win.all_panels
        pr = self.plot_renderers
        if pr is not None and hasattr(pr, "all_panels"):
            return pr.all_panels
        nav = self.nav_controller
        if nav is not None and hasattr(nav, "all_panels"):
            return nav.all_panels
        return []

    # ------------------------------------------------------------------
    # Gestão de Histórico de Edição (Undo Stack)
    # ------------------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        """Informa se existem estados anteriores disponíveis para desfeita."""
        return bool(self._pulse_edit_history)

    def reset_history(self) -> None:
        """Limpa a pilha de desfeita e atualiza controles visuais vinculados."""
        self._pulse_edit_history = []
        self.sync_panel_undo_buttons()
        self.undo_availability_changed.emit(False)

    def sync_panel_undo_buttons(self) -> None:
        """Atualiza a propriedade isEnabled dos botões de desfazer nos painéis gráficos."""
        enabled = self.can_undo
        for panel in self.all_panels:
            if hasattr(panel, "btn_pulse_undo"):
                panel.btn_pulse_undo.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Localização e Hit-Box Snapping de Picos
    # ------------------------------------------------------------------

    def find_nearest_user_peak(self, time_sec: float, tolerance_sec: float = 0.005) -> int | None:
        """Encontra o pico verificado mais próximo ao instante fornecido, com tolerância precisa."""
        ctx = self.session_context
        peaks_verified = ctx.peaks_user_verified
        heavy = ctx.active_heavy_data
        if not peaks_verified or not heavy:
            return None
        rate = float(heavy.get('rate', 1.0) or 1.0)
        tolerance_samples = max(2, int(round(tolerance_sec * rate)))
        peak_samples = np.asarray(peaks_verified, dtype=int)
        target = int(round(float(time_sec) * rate))
        diffs = np.abs(peak_samples - target)
        if diffs.size == 0:
            return None
        nearest_idx = int(np.argmin(diffs))
        if diffs[nearest_idx] <= tolerance_samples:
            return int(peak_samples[nearest_idx])
        return None

    # ------------------------------------------------------------------
    # Edição Interativa de Pulsos (Alternar / Adicionar / Remover)
    # ------------------------------------------------------------------

    def toggle_peak_marker(
        self,
        time_sec: float,
        panel=None,
        event=None,
        f_click: float = None,
        amp_click: float = None,
    ) -> int | None:
        """Alterna a classificação do pico mais próximo com snapping inteligente em pixels ou adiciona um novo pico."""
        ctx = self.session_context
        heavy = ctx.active_heavy_data
        if not heavy:
            return None

        rate = float(heavy.get('rate', 1.0) or 1.0)
        target = int(round(float(time_sec) * rate))
        detected = ctx.peaks_detected or []
        verified = ctx.peaks_user_verified or []
        candidates = sorted(set(int(p) for p in detected) | set(int(p) for p in verified))
        nearest = None

        if candidates:
            # Hit-box snapping adaptativo em pixels de tela (tolerância suave de ~15px)
            ax = panel.ax if (panel and hasattr(panel, 'ax')) else (event.inaxes if event else None)
            if ax is not None and event is not None and getattr(event, 'x', None) is not None:
                xlim = ax.get_xlim()
                pad = max(0.1, (xlim[1] - xlim[0]) * 0.1)
                vis_cands = [p for p in candidates if (xlim[0] - pad) <= (p / rate) <= (xlim[1] + pad)]
                if not vis_cands:
                    vis_cands = candidates
                cand_times = np.asarray(vis_cands, dtype=float) / rate
                pts_disp = ax.transData.transform(np.column_stack([cand_times, np.zeros_like(cand_times)]))
                pixel_dists = np.abs(pts_disp[:, 0] - event.x)
                min_idx = int(np.argmin(pixel_dists))
                if pixel_dists[min_idx] <= 15.0 and abs(cand_times[min_idx] - float(time_sec)) <= 0.020:
                    nearest = vis_cands[min_idx]
            else:
                # Fallback adaptativo à janela temporal visível ou 5 ms
                if ax is not None:
                    xlim = ax.get_xlim()
                    vis_span = max(0.01, xlim[1] - xlim[0])
                    time_tol_sec = min(0.020, max(0.003, vis_span * 0.015))
                else:
                    time_tol_sec = 0.005
                distances = np.abs(np.asarray(candidates, dtype=int) - target)
                min_dist_idx = int(np.argmin(distances))
                if distances[min_dist_idx] <= int(round(time_tol_sec * rate)):
                    nearest = candidates[min_dist_idx]

        # Salva o estado atual na pilha de desfeita (picos e metadados)
        meta = dict(ctx.pulse_metadata or {})
        meta_snapshot = {k: dict(v) if isinstance(v, dict) else v for k, v in meta.items()}
        self._pulse_edit_history.append({
            "peaks": list(verified),
            "metadata": meta_snapshot,
        })
        if len(self._pulse_edit_history) > 50:
            self._pulse_edit_history = self._pulse_edit_history[-50:]

        modified_sample = None
        action = None

        if nearest is not None and nearest in verified:
            # Remoção do pulso verificado existente e limpeza de metadados associados
            new_verified = [int(p) for p in verified if int(p) != nearest]
            meta.pop(nearest, None)
            modified_sample = nearest
            action = "removed"
        elif nearest is not None:
            # Reativação de pico previamente detectado mas não verificado
            new_verified = sorted(set(verified + [nearest]))
            modified_sample = nearest
            action = "added"
            if f_click is not None or amp_click is not None:
                meta[nearest] = {"idx": nearest}
                if f_click is not None:
                    meta[nearest]["freq"] = f_click
                if amp_click is not None:
                    meta[nearest]["amp"] = amp_click
        else:
            # Inserção de um pulso totalmente novo no instante do clique
            new_verified = sorted(set(verified + [target]))
            modified_sample = target
            action = "added"
            if f_click is not None or amp_click is not None:
                meta[target] = {"idx": target}
                if f_click is not None:
                    meta[target]["freq"] = f_click
                if amp_click is not None:
                    meta[target]["amp"] = amp_click

        # Atualiza o estado da sessão de forma transacional e atômica
        heavy['peaks_user_verified'] = list(new_verified)
        heavy['pulse_metadata'] = dict(meta)

        if hasattr(ctx, "update_verified_and_metadata"):
            ctx.update_verified_and_metadata(new_verified, meta)
        else:
            ctx.pulse_metadata = meta
            ctx.peaks_user_verified = new_verified

        active_fn = ctx.active_filename
        if active_fn:
            combined = []
            for p in new_verified:
                if p in meta:
                    combined.append(meta[p])
                else:
                    combined.append(int(p))
            corrections = dict(ctx.corrections_by_file or {})
            corrections[active_fn] = combined
            ctx.corrections_by_file = corrections
            self.save_corrections_state()

        self.sync_panel_undo_buttons()
        self.recalculate_metrics()

        # Atualiza marcadores e visualizações nos outros subsistemas
        pr = self.plot_renderers
        if pr is not None:
            pr.refresh_histogram()
            pr.refresh_markers()

        nav = self.nav_controller
        if nav is not None and hasattr(nav, "update_hover_data"):
            nav.update_hover_data()

        if action == "removed":
            self.pulse_removed.emit(modified_sample)
        else:
            self.pulse_added.emit(modified_sample)

        self.pulses_changed.emit(new_verified)
        self.undo_availability_changed.emit(self.can_undo)
        return modified_sample

    def undo(self) -> bool:
        """Desfaz a última alteração na lista de pulsos verificados e restaura metadados de forma transacional."""
        if not self._pulse_edit_history:
            return False

        ctx = self.session_context
        heavy = ctx.active_heavy_data
        entry = self._pulse_edit_history.pop()

        if isinstance(entry, dict) and "peaks" in entry:
            restored_peaks = list(entry["peaks"])
            restored_meta = {
                k: dict(v) if isinstance(v, dict) else v
                for k, v in entry.get("metadata", {}).items()
            }
        elif isinstance(entry, (list, tuple)):
            restored_peaks = list(entry)
            restored_meta = {
                k: v for k, v in (ctx.pulse_metadata or {}).items()
                if k in restored_peaks
            }
        else:
            restored_peaks = []
            restored_meta = {}

        if heavy:
            heavy['peaks_user_verified'] = list(restored_peaks)
            heavy['pulse_metadata'] = dict(restored_meta)

        if hasattr(ctx, "update_verified_and_metadata"):
            ctx.update_verified_and_metadata(restored_peaks, restored_meta)
        else:
            ctx.peaks_user_verified = list(restored_peaks)
            ctx.pulse_metadata = dict(restored_meta)

        active_fn = ctx.active_filename
        if active_fn:
            combined = []
            for p in restored_peaks:
                if p in restored_meta:
                    combined.append(restored_meta[p])
                else:
                    combined.append(int(p))
            corrections = dict(ctx.corrections_by_file or {})
            corrections[active_fn] = combined
            ctx.corrections_by_file = corrections
            self.save_corrections_state()

        self.sync_panel_undo_buttons()
        self.recalculate_metrics()

        pr = self.plot_renderers
        if pr is not None:
            pr.refresh_histogram()
            pr.refresh_markers()

        nav = self.nav_controller
        if nav is not None and hasattr(nav, "update_hover_data"):
            nav.update_hover_data()

        self.pulses_changed.emit(restored_peaks)
        self.undo_availability_changed.emit(self.can_undo)
        return True

    # ------------------------------------------------------------------
    # Recálculo Imediato de Chilreios e Métricas
    # ------------------------------------------------------------------

    def recalculate_metrics(self) -> dict | None:
        """Recalcula chilreios e métricas instantaneamente após edição pelo usuário."""
        ctx = self.session_context
        heavy = ctx.active_heavy_data
        verified = ctx.peaks_user_verified or []
        win = self.main_window

        if len(verified) < 2:
            # Estado sem chilreios calculáveis (< 2 pulsos verificados)
            # Limpa explicitamente estruturas e métricas para evitar manter valores obsoletos
            heavy['chirps'] = []
            heavy['chirp_peaks_list'] = []
            heavy['media'] = 0.0
            heavy['moda'] = 0.0

            active_fn = ctx.active_filename
            if active_fn and active_fn in ctx.analysis_cache:
                cache_entry = ctx.analysis_cache[active_fn]
                cache_entry["chirps"] = []
                cache_entry["chirp_peaks_list"] = []
                cache_entry["media"] = 0.0
                cache_entry["moda"] = 0.0

            if win is not None:
                if hasattr(win, 'lbl_total'):
                    win.lbl_total.setText("0")
                if hasattr(win, 'lbl_metric_sub'):
                    win.lbl_metric_sub.setText("Moda: —   |   Média: —")
                if hasattr(win, 'timeline') and 'duration' in heavy:
                    win.timeline.set_data(heavy.get('duration', 0.0), [])

            metrics_payload = {
                "total_chirps": 0,
                "media": 0.0,
                "moda": 0.0,
                "chirps": [],
                "chirp_peaks_list": [],
            }
            self.metrics_recalculated.emit(metrics_payload)
            return metrics_payload

        try:
            rate = float(heavy.get('rate', 1.0) or 1.0)
            effective_params = {**(ctx.algo_params or {}), **(ctx._adaptive_overrides or {})}
            env = heavy.get('env')
            data_b1 = heavy.get('data_b1')

            chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
                verified,
                effective_params,
                rate,
                env,
                raw_signal=data_b1,
            )

            heavy['chirps'] = chirps
            heavy['chirp_peaks_list'] = chirp_peaks_list
            heavy['media'] = media
            heavy['moda'] = moda

            active_fn = ctx.active_filename
            if active_fn and active_fn in ctx.analysis_cache:
                cache_entry = ctx.analysis_cache[active_fn]
                cache_entry["chirps"] = chirps
                cache_entry["chirp_peaks_list"] = chirp_peaks_list
                cache_entry["media"] = media
                cache_entry["moda"] = moda

            win = self.main_window
            if win is not None:
                if hasattr(win, 'lbl_total'):
                    win.lbl_total.setText(str(len(chirps)))
                if hasattr(win, 'lbl_metric_sub'):
                    win.lbl_metric_sub.setText(f"Moda: {moda}   |   Média: {media:.2f}")

            metrics_payload = {
                "total_chirps": len(chirps),
                "media": float(media),
                "moda": float(moda),
                "chirps": chirps,
                "chirp_peaks_list": chirp_peaks_list,
            }
            self.metrics_recalculated.emit(metrics_payload)
            return metrics_payload
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Persistência de Correções
    # ------------------------------------------------------------------

    def save_corrections_state(self) -> bool:
        """Persiste correções de arquivos no arquivo JSON de configurações de forma atômica."""
        ctx = self.session_context
        temp_path = None
        try:
            config = {}
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        config = loaded
                except Exception:
                    config = {}
            config["corrections_by_file"] = ctx.corrections_by_file

            cfg_dir = os.path.dirname(os.path.abspath(self.config_file)) or "."
            os.makedirs(cfg_dir, exist_ok=True)

            with tempfile.NamedTemporaryFile("w", dir=cfg_dir, delete=False, encoding="utf-8") as tf:
                temp_path = tf.name
                json.dump(config, tf, indent=4, ensure_ascii=False)
                tf.flush()
                os.fsync(tf.fileno())

            os.replace(temp_path, self.config_file)
            temp_path = None
            return True
        except (OSError, ValueError, TypeError) as exc:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            print(f"Erro ao persistir correções: {exc}")
            return False

    # ------------------------------------------------------------------
    # Integração com PulseLearner (Treinamento Supervisionado)
    # ------------------------------------------------------------------

    def _adapt_advanced_params(self) -> None:
        """Encaminha adaptação de parâmetros ao PipelineOrchestrator ou MainWindow."""
        pipe = self.pipeline
        if pipe is not None and hasattr(pipe, "_adapt_advanced_params"):
            pipe._adapt_advanced_params()
            return
        win = self.main_window
        if win is not None and hasattr(win, "_adapt_advanced_params"):
            win._adapt_advanced_params()

    def learn_from_corrections(self, filename: str = None, blocking: bool = False):
        """Coordena o retreinamento do classificador PulseLearner com base nas correções do usuário."""
        ctx = self.session_context

        # Sincroniza coerência entre o argumento filename e o arquivo ativo no SessionContext
        if filename and filename != ctx.active_filename:
            if filename in ctx.analysis_cache:
                ctx.activate_cached_file(filename)
            else:
                err_msg = f"Arquivo '{filename}' não corresponde ao arquivo ativo e não possui análise em cache."
                self.learning_failed.emit(err_msg)
                return False, err_msg

        active_fn = ctx.active_filename
        if not active_fn:
            err_msg = "Nenhum arquivo ativo selecionado para treinamento."
            self.learning_failed.emit(err_msg)
            return False, err_msg

        heavy = ctx.active_heavy_data
        if not heavy:
            err_msg = "Nenhum dado analítico ativo disponível para treinamento."
            self.learning_failed.emit(err_msg)
            return False, err_msg

        detected = list(ctx.peaks_detected or [])
        verified = list(ctx.peaks_user_verified or [])
        detected_set = set(int(p) for p in detected)
        verified_set = set(int(p) for p in verified)

        if not detected_set or not verified_set:
            err_msg = "Dados insuficientes: é necessário ter pulsos detectados e verificados."
            self.learning_failed.emit(err_msg)
            return False, err_msg

        learner = ctx.pulse_learner
        if learner is None:
            err_msg = "Módulo de aprendizado supervisionado (PulseLearner) não inicializado."
            self.learning_failed.emit(err_msg)
            return False, err_msg

        # Preserva metadados dos pulsos (dicionários com freq/amp) nas correções salvas
        meta = ctx.pulse_metadata or {}
        combined = []
        for p in verified:
            if p in meta:
                combined.append(meta[p])
            else:
                combined.append(int(p))
        corrections = dict(ctx.corrections_by_file or {})
        corrections[active_fn] = combined
        ctx.corrections_by_file = corrections
        self.save_corrections_state()

        rate = float(heavy.get('rate', 1.0) or 1.0)
        env = heavy.get('env')
        data_b1 = heavy.get('data_b1')

        def _task():
            learner.update_from_corrections(
                detected, verified, rate, env, raw_signal=data_b1
            )
            self._adapt_advanced_params()
            learner.save_to_config()
            return len(detected_set ^ verified_set)

        self.learning_started.emit()

        if blocking:
            try:
                num_corrections = _task()
                self.learning_completed.emit(num_corrections, active_fn)
                return True, num_corrections
            except Exception as e:
                err_str = str(e)
                self.learning_failed.emit(err_str)
                return False, err_str

        worker = GenericWorker(_task)
        self._learn_worker = worker

        def _on_finished(num_corrections):
            self.learning_completed.emit(num_corrections, active_fn)

        def _on_error(err_msg):
            self.learning_failed.emit(str(err_msg))

        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)
        worker.start()
        return worker

    # ------------------------------------------------------------------
    # Coordenação dos Modos de Edição dos Painéis
    # ------------------------------------------------------------------

    def update_pulse_edit_buttons(self, activated_panel) -> None:
        """Quando um painel é ativado para edição de pulsos, desativa os outros."""
        for panel in self.all_panels:
            if panel != activated_panel:
                panel.pulse_edit_mode = False
                if hasattr(panel, 'btn_pulse_edit'):
                    panel.btn_pulse_edit.blockSignals(True)
                    panel.btn_pulse_edit.setChecked(False)
                    panel.btn_pulse_edit.setStyleSheet("")
                    panel.btn_pulse_edit.setToolTip("Ativar modo de edição de pulsos (clique para adicionar/remover)")
                    panel.btn_pulse_edit.blockSignals(False)
