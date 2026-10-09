filepath = 'ui/controllers/pipeline_orchestrator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target_task = """        def _task():
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
            return res"""

replacement_task = """        # Captura o contexto de forma síncrona
        import numpy as np
        use_ml = self.ctx.use_machine_learning
        has_corrections = (self.ctx.active_heavy_data and self.ctx.active_filename == filename and
                           filename in self.ctx.corrections_by_file and self.ctx.peaks_user_verified and use_ml)
        
        env = np.array([])
        data_b1 = np.array([])
        rate = 1.0
        peaks_det = []
        peaks_verif = []
        
        if has_corrections:
            rate = float(self.ctx.active_heavy_data.get("rate", 1.0))
            env_orig = self.ctx.active_heavy_data.get("env", np.array([]))
            env = np.copy(env_orig) if env_orig is not None else np.array([])
            data_b1_orig = self.ctx.active_heavy_data.get("data_b1", np.array([]))
            data_b1 = np.copy(data_b1_orig) if data_b1_orig is not None else np.array([])
            peaks_det = list(self.ctx.peaks_detected)
            peaks_verif = list(self.ctx.peaks_user_verified)
            
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

        def _task():
            if has_corrections and env.size > 0:
                try:
                    learner.update_from_corrections(
                        peaks_det, peaks_verif, rate, env, raw_signal=data_b1
                    )
                    learner.save_to_config()
                except Exception:
                    pass
            res = CricketAnalyzer.analyze(file_path, effective_params, pulse_learner=learner, cached_spec=cached_spec)
            return res"""
content = content.replace(target_task, replacement_task)

target_finished = """        def _on_finished(res):
            self._apply_analysis_results(filename, res, params=self.ctx.algo_params)"""

replacement_finished = """        def _on_finished(res):
            if has_corrections and env.size > 0:
                try:
                    self._adapt_advanced_params()
                except Exception:
                    pass
            self._apply_analysis_results(filename, res, params=self.ctx.algo_params)"""
content = content.replace(target_finished, replacement_finished)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
