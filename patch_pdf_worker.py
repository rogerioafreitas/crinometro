filepath = 'ui/controllers/export_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target_cache = """        selected_cache = {fname: self.ctx.analysis_cache[fname] for fname in checked_files if fname in self.ctx.analysis_cache}"""
replacement_cache = """        # Copia o cache e params para isolar a thread de background de mutações concorrentes na UI
        import copy
        selected_cache = {fname: dict(self.ctx.analysis_cache[fname]) for fname in checked_files if fname in self.ctx.analysis_cache}
        params_copy = copy.deepcopy(self.ctx.algo_params)"""
content = content.replace(target_cache, replacement_cache)

target_task = """                generate_pdf_report(config.output_path, config, selected_cache, self.ctx.algo_params)"""
replacement_task = """                generate_pdf_report(config.output_path, config, selected_cache, params_copy)"""
content = content.replace(target_task, replacement_task)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
