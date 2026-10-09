import re
import os

# 1 & 5. core/learner.py: Remove pickle fallback, add atomic save
filepath = 'core/learner.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Atomic save
old_save = """            config["pulse_learner"] = self.serialize()
            config["pruning_rules"] = getattr(self, "pruning_rules", [])
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True"""
new_save = """            config["pulse_learner"] = self.serialize()
            config["pruning_rules"] = getattr(self, "pruning_rules", [])
            
            cfg_dir = os.path.dirname(os.path.abspath(self.config_path)) or "."
            import tempfile
            with tempfile.NamedTemporaryFile("w", dir=cfg_dir, delete=False, encoding="utf-8") as tf:
                temp_path = tf.name
                json.dump(config, tf, indent=4, ensure_ascii=False)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(temp_path, self.config_path)
            return True"""
if old_save in content:
    content = content.replace(old_save, new_save)

# Remove pickle load_from_config
old_load_cfg_1 = """                try:
                    self.model = skio.loads(model_bytes, trusted=[HistGradientBoostingClassifier, RandomForestClassifier, "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "sklearn.tree._tree.Tree"])
                except Exception:
                    self.model = pickle.loads(model_bytes)
                return True
            except Exception as exc:"""
new_load_cfg_1 = """                try:
                    self.model = skio.loads(model_bytes, trusted=[HistGradientBoostingClassifier, RandomForestClassifier, "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "sklearn.tree._tree.Tree"])
                    return True
                except Exception as exc:
                    self.model = None
                    return False
            except Exception as exc:"""
content = content.replace(old_load_cfg_1, new_load_cfg_1)

old_load_cfg_2 = """                model_bytes = base64.b64decode(payload["model_pickle_b64"])
                self.model = pickle.loads(model_bytes)
                return True
            except Exception as exc:"""
new_load_cfg_2 = """                model_bytes = base64.b64decode(payload["model_pickle_b64"])
                self.model = skio.loads(model_bytes, trusted=[HistGradientBoostingClassifier, RandomForestClassifier, "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "sklearn.tree._tree.Tree"])
                return True
            except Exception as exc:"""
content = content.replace(old_load_cfg_2, new_load_cfg_2)

# Remove pickle load_persisted_training
old_load_pt = """        try:
            try:
                with open(self.persistence_path, "rb") as f:
                    payload = skio.load(f, trusted=[HistGradientBoostingClassifier, RandomForestClassifier, np.ndarray, np.dtype, "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "sklearn.tree._tree.Tree"])
            except Exception:
                with open(self.persistence_path, "rb") as f:
                    payload = pickle.load(f)
                # Força a migração do formato antigo para o novo (skops)
                if self.persistence_path.endswith(".pkl"):
                    self.persistence_path = self.persistence_path.replace(".pkl", ".skops")
        except Exception:"""
new_load_pt = """        try:
            with open(self.persistence_path, "rb") as f:
                payload = skio.load(f, trusted=[HistGradientBoostingClassifier, RandomForestClassifier, np.ndarray, np.dtype, "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor", "sklearn.tree._tree.Tree"])
        except Exception:"""
content = content.replace(old_load_pt, new_load_pt)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)


# 2. ui/controllers/pipeline_orchestrator.py: Fix race conditions with snapshots
filepath = 'ui/controllers/pipeline_orchestrator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_task = """        def _task():
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
                        pass"""

new_task = """        def _task():
            # 1. Se o usuário fez correções, atualiza o modelo ML
            use_ml = self.ctx.use_machine_learning
            if (self.ctx.active_heavy_data and self.ctx.active_filename == filename and
                filename in self.ctx.corrections_by_file and self.ctx.peaks_user_verified and use_ml):
                
                # Snapshot imediato e isolado
                import numpy as np
                rate = float(self.ctx.active_heavy_data.get("rate", 1.0))
                env_orig = self.ctx.active_heavy_data.get("env", np.array([]))
                env = np.copy(env_orig) if env_orig is not None else np.array([])
                
                data_b1_orig = self.ctx.active_heavy_data.get("data_b1", np.array([]))
                data_b1 = np.copy(data_b1_orig) if data_b1_orig is not None else np.array([])
                
                peaks_det = list(self.ctx.peaks_detected)
                peaks_verif = list(self.ctx.peaks_user_verified)
                
                if env.size > 0:
                    try:
                        self.ctx.pulse_learner.update_from_corrections(
                            peaks_det, peaks_verif, rate, env, raw_signal=data_b1
                        )
                        self._adapt_advanced_params()
                        self.ctx.pulse_learner.save_to_config()
                    except Exception:
                        pass"""
if old_task in content:
    content = content.replace(old_task, new_task)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)


# 3. ui/main_window.py: closeEvent
filepath = 'ui/main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

close_event_code = """
    def closeEvent(self, event):
        \"\"\"Finaliza threads em background de forma graciosa antes de fechar.\"\"\"
        if hasattr(self, 'pipeline_orchestrator') and getattr(self.pipeline_orchestrator, 'is_processing', False):
            self.pipeline_orchestrator.abort_current_analysis()
            
        if hasattr(self, '_checker_thread') and self._checker_thread.isRunning():
            self._checker_thread.quit()
            self._checker_thread.wait(1000)
            
        event.accept()

    def _setup_connections(self):"""

if 'def closeEvent(self' not in content:
    content = content.replace("    def _setup_connections(self):", close_event_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)


# 4. core/analyzer.py: 1024 samples minimum
filepath = 'core/analyzer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_analyzer_check = """        if max_abs == 0:
            raise ValueError("O arquivo de áudio está mudo.")"""
new_analyzer_check = """        if max_abs == 0:
            raise ValueError("O arquivo de áudio está mudo.")
        
        if len(data) < 1024:
            raise ValueError("O arquivo de áudio é curto demais para o janelamento espectral (mínimo de 1024 frames).")"""
if new_analyzer_check not in content:
    content = content.replace(old_analyzer_check, new_analyzer_check)

old_analyzer_check_fallback = """        if max_abs == 0:
            raise ValueError("O arquivo de udio est mudo.")"""
new_analyzer_check_fallback = """        if max_abs == 0:
            raise ValueError("O arquivo de áudio está mudo.")
        
        if len(data) < 1024:
            raise ValueError("O arquivo de áudio é curto demais para o janelamento espectral (mínimo de 1024 frames).")"""
if new_analyzer_check_fallback in content and new_analyzer_check not in content:
    content = content.replace(old_analyzer_check_fallback, new_analyzer_check_fallback)

# Some encodings might corrupt the string
content = content.replace('raise ValueError("O arquivo de udio est mudo.")', 'raise ValueError("O arquivo de udio est mudo.")\n        if len(data) < 1024:\n            raise ValueError("O arquivo de udio  curto demais para o janelamento espectral (mnimo de 1024 frames).")')


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
