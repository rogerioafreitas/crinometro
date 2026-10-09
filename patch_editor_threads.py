filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target_task = """        def _task():
            learner.update_from_corrections(
                detected, verified, rate, env, raw_signal=data_b1
            )
            self._adapt_advanced_params()
            learner.save_to_config()
            return len(detected_set ^ verified_set)"""

replacement_task = """        def _task():
            learner.update_from_corrections(
                detected, verified, rate, env, raw_signal=data_b1
            )
            learner.save_to_config()
            return len(detected_set ^ verified_set)"""

content = content.replace(target_task, replacement_task)

target_blocking = """        if blocking:
            try:
                num_corrections = _task()
                self.learning_completed.emit(num_corrections, active_fn)
                return True, num_corrections"""

replacement_blocking = """        if blocking:
            try:
                num_corrections = _task()
                self._adapt_advanced_params()
                self.learning_completed.emit(num_corrections, active_fn)
                return True, num_corrections"""

content = content.replace(target_blocking, replacement_blocking)

target_onfinished = """        def _on_finished(num_corrections):
            self.learning_completed.emit(num_corrections, active_fn)"""

replacement_onfinished = """        def _on_finished(num_corrections):
            self._adapt_advanced_params()
            self.learning_completed.emit(num_corrections, active_fn)"""

content = content.replace(target_onfinished, replacement_onfinished)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
