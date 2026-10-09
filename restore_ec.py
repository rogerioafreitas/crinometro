filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix save_corrections_state
target_save = """    def save_corrections_state(self) -> bool:
        \"\"\"Persiste correções de arquivos no arquivo JSON de configurações de forma atômica.\"\"\"
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
            
            if temp_path:
                os.replace(temp_path, self.config_file)
            return True
        except Exception:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False"""

replacement_save = """    def save_corrections_state(self) -> bool:
        try:
            from utils.constants import CONFIG_LOCK
            CONFIG_LOCK.acquire()
            \"\"\"Persiste correções de arquivos no arquivo JSON de configurações de forma atômica.\"\"\"
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
                        return False
                config["corrections_by_file"] = ctx.corrections_by_file

                cfg_dir = os.path.dirname(os.path.abspath(self.config_file)) or "."
                os.makedirs(cfg_dir, exist_ok=True)

                import tempfile
                with tempfile.NamedTemporaryFile("w", dir=cfg_dir, delete=False, encoding="utf-8") as tf:
                    temp_path = tf.name
                    json.dump(config, tf, indent=4, ensure_ascii=False)
                    tf.flush()
                
                if temp_path:
                    os.replace(temp_path, self.config_file)
                return True
            except Exception:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                return False
        finally:
            CONFIG_LOCK.release()"""

content = content.replace(target_save, replacement_save)

# 2. Add _retained_workers
target_init = """        self.pulse_learner = None
        self._learning_in_progress = False"""

replacement_init = """        self.pulse_learner = None
        self._learning_in_progress = False
        self._retained_workers = set()"""

content = content.replace(target_init, replacement_init)

target_thread = """            self.learning_failed.emit(str(e))

        worker.result_ready_signal.connect(_on_success)
        worker.error_signal.connect(_on_error)
        
        worker.start()"""

replacement_thread = """            self.learning_failed.emit(str(e))

        worker.result_ready_signal.connect(_on_success)
        worker.error_signal.connect(_on_error)
        
        self._retained_workers.add(worker)
        worker.finished.connect(lambda w=worker: self._retained_workers.discard(w))
        worker.start()"""

content = content.replace(target_thread, replacement_thread)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
