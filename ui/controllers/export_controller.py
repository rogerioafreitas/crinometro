from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QMenu
import os
import datetime
import time

from utils.i18n import I18N
from core.worker import GenericWorker

class ExportController(QObject):
    """
    Controlador responsável pelos fluxos de exportação da aplicação (Gráficos, TXT Legado, PDF Modular).
    A MainWindow delega a execução das ações de exportação para esta classe.
    """
    export_started = pyqtSignal()
    export_finished = pyqtSignal()
    export_error = pyqtSignal(str)

    def __init__(self, ctx, pipeline, main_window):
        super().__init__(main_window)
        self.ctx = ctx
        self.pipeline = pipeline
        self.main_window = main_window
        self.lang = main_window.lang
        
        self._pending_export_action = None
        self._batch_spinner = None
        self._report_worker = None
        
        # Conectar sinal do batch analysis para destravar a exportação se estiver aguardando
        self.pipeline.batch_completed.connect(self._on_batch_completed)
        self.pipeline.batch_failed.connect(self._on_batch_failed)
        self.pipeline.batch_cancelled.connect(self._on_batch_cancelled)

    def _get_checked_files(self):
        return self.main_window.get_checked_files()

    def _start_batch_for_export(self, unprocessed, action_type, action_args):
        for fname in unprocessed:
            w = self.main_window._get_item_widget_by_name(fname)
            if w and hasattr(w, "set_loading"):
                w.set_loading(True)
        
        if hasattr(self.main_window, "btn_analyze_selected"):
            self.main_window.btn_analyze_selected.setEnabled(False)
            
        from ui.widgets import ButtonSpinner
        self._batch_spinner = ButtonSpinner(self.main_window.btn_export_main, "Analisando pendentes...")
        self._batch_spinner.start()
        
        self._pending_export_action = (action_type, action_args)
        self.pipeline.run_batch_analysis(unprocessed, self.ctx.algo_params)

    def _on_batch_completed(self, success_count, errors):
        pending = self._pending_export_action
        if self._batch_spinner is not None:
            self._batch_spinner.stop()
            self._batch_spinner = None
            
        if pending is not None:
            self._pending_export_action = None
            if not errors:
                action, args = pending
                if action == 'txt':
                    self._generate_txt_report(self._get_checked_files())
                elif action == 'pdf_modular':
                    cfg, wcsv, cpath, wtxt, tpath, cmode = args
                    self._generate_pdf_report_modular(self._get_checked_files(), cfg, want_csv=wcsv, csv_path=cpath, want_txt=wtxt, txt_path=tpath, csv_mode=cmode)
            else:
                QMessageBox.warning(self.main_window, "Falha na Análise", "Não foi possível gerar a exportação pois alguns arquivos falharam na análise.")

    def _on_batch_failed(self, error_message):
        if self._pending_export_action is not None:
            if self._batch_spinner is not None:
                self._batch_spinner.stop()
                self._batch_spinner = None
            self._pending_export_action = None
            QMessageBox.critical(self.main_window, "Erro", f"A análise falhou antes da exportação: {error_message}")

    def _on_batch_cancelled(self):
        if self._pending_export_action is not None:
            if self._batch_spinner is not None:
                self._batch_spinner.stop()
                self._batch_spinner = None
            self._pending_export_action = None

    # ---------- TXT Export ----------
    def request_txt_export(self):
        checked_files = self._get_checked_files()
        if not checked_files:
            QMessageBox.warning(
                self.main_window,
                "Nenhum áudio selecionado",
                "Marque a caixinha de pelo menos um arquivo de áudio na lista para gerar o relatório."
            )
            return

        unprocessed = [f for f in checked_files if f not in self.ctx.analysis_cache and f in self.ctx.loaded_files]
        if unprocessed:
            self._start_batch_for_export(unprocessed, 'txt', None)
            return

        self._generate_txt_report(checked_files)

    def _generate_txt_report(self, checked_files):
        selected_cache = {
            fname: self.ctx.analysis_cache[fname]
            for fname in checked_files
            if fname in self.ctx.analysis_cache
        }

        if not selected_cache:
            QMessageBox.warning(
                self.main_window,
                "Sem dados",
                "Nenhum dos áudios selecionados possui dados de análise válidos para o relatório."
            )
            return

        now = datetime.datetime.now()
        default_name = f"Relatorio_Crinometro_{now.strftime('%Y%m%d_%H%M')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(self.main_window, I18N[self.lang]["export"], default_name, "Text Files (*.txt)")
        if not file_path:
            return

        with open(file_path, 'w', encoding='utf-8') as f:
            inst = self.ctx.report_params.get('institution', '').strip()
            name = self.ctx.report_params.get('researcher_name', '').strip()
            role = self.ctx.report_params.get('role', '').strip()
            level = self.ctx.report_params.get('level', '').strip()
            header_lines = []
            if inst: header_lines.append(f"Instituição: {inst.upper()}")
            if name: header_lines.append(f"Pesquisador(a): {name}")
            if role: header_lines.append(f"Função: {role}")
            if level: header_lines.append(f"Grau Acadêmico: {level}")
            header_text = "\n".join(header_lines) + "\n\n" if header_lines else ""
            params_list = [d['params'] for d in selected_cache.values()]
            all_same_params = all(p == params_list[0] for p in params_list) if params_list else True
            texto = (
                f"RELATÓRIO MULTIPLEXADO DE ANÁLISE BIOACÚSTICA - CRINÓMETRO\n"
                f"{'='*58}\n"
                f"{header_text}"
            )
            f.write(texto)
            # Simplificando a geracao original do txt para caber ou chamar de util
            from utils.report_generator import generate_txt_report
            generate_txt_report(file_path, selected_cache, self.ctx.report_params)

        QMessageBox.information(self.main_window, I18N[self.lang]["success"], f"Relatório gerado com sucesso para {len(selected_cache)} áudio(s) selecionado(s).")


    # ---------- Modular PDF Export ----------
    def request_modular_report(self):
        checked_files = self._get_checked_files()
        if not checked_files:
            QMessageBox.warning(self.main_window, "Nenhum áudio", "Marque pelo menos um arquivo na lista para gerar o relatório.")
            return

        from ui.dialogs.export_report_dialog import ExportReportDialog
        dlg = ExportReportDialog(self.ctx, checked_files=checked_files, parent=self.main_window)
        if dlg.exec():
            config    = dlg.config
            want_csv  = dlg.export_csv
            csv_path  = dlg.csv_path
            want_txt  = dlg.export_txt
            txt_path  = dlg.txt_path
            csv_mode  = getattr(dlg, 'csv_mode', 'brazilian')
            unprocessed = [f for f in checked_files if f not in self.ctx.analysis_cache and f in self.ctx.loaded_files]
            if unprocessed:
                self._start_batch_for_export(unprocessed, 'pdf_modular', (config, want_csv, csv_path, want_txt, txt_path, csv_mode))
                return
            self._generate_pdf_report_modular(checked_files, config, want_csv=want_csv, csv_path=csv_path, want_txt=want_txt, txt_path=txt_path, csv_mode=csv_mode)

    def _generate_pdf_report_modular(self, checked_files, config, want_csv=False, csv_path=None, want_txt=False, txt_path=None, csv_mode="brazilian"):
        selected_cache = {fname: self.ctx.analysis_cache[fname] for fname in checked_files if fname in self.ctx.analysis_cache}
        if not selected_cache:
            QMessageBox.warning(self.main_window, "Sem dados", "Nenhum dos áudios selecionados possui dados válidos.")
            return

        def _task():
            results = []
            if config.output_path:
                from utils.report_generator import generate_pdf_report
                generate_pdf_report(config.output_path, config, selected_cache, self.ctx.algo_params)
                results.append(config.output_path)
            if want_csv and csv_path:
                from utils.report_generator import generate_csv_report
                generate_csv_report(csv_path, selected_cache, config.metadata, csv_mode=csv_mode)
                results.append(csv_path)
            if want_txt and txt_path:
                from utils.report_generator import generate_txt_report
                generate_txt_report(txt_path, selected_cache, config.metadata)
                results.append(txt_path)
            return results

        def _on_finished(paths):
            paths_str = "\n".join(paths) if paths else ""
            QMessageBox.information(self.main_window, I18N[self.lang]["success"],
                                    f"Relatório gerado com sucesso!\n\nSalvo em:\n{paths_str}")
            if self._batch_spinner is not None:
                self._batch_spinner.stop()
                self._batch_spinner = None

        def _on_error(err_msg):
            QMessageBox.critical(self.main_window, I18N[self.lang]["error"], f"Falha ao gerar relatório:\n{err_msg}")
            if self._batch_spinner is not None:
                self._batch_spinner.stop()
                self._batch_spinner = None

        worker = GenericWorker(_task)
        self._report_worker = worker
        worker.finished_signal.connect(_on_finished)
        worker.error_signal.connect(_on_error)

        if hasattr(self.main_window, "btn_export_main"):
            from ui.widgets import ButtonSpinner
            if not getattr(self, "_batch_spinner", None):
                spinner = ButtonSpinner(self.main_window.btn_export_main, "Gerando relatório...")
                spinner.start()
                self._batch_spinner = spinner

        worker.start()

    # ---------- Graph Export ----------
    def request_graph_export(self):
        from ui.dialogs.export_graph_dialog import ExportGraphDialog
        live_view = {}
        if hasattr(self.main_window, 'plot_renderers') and hasattr(self.main_window.plot_renderers, 'panel_spec') and self.main_window.plot_renderers.panel_spec and self.main_window.plot_renderers.panel_spec.ax:
            try:
                ax = self.main_window.plot_renderers.panel_spec.ax
                live_view['xlim'] = ax.get_xlim()
                live_view['ylim'] = ax.get_ylim()
                live_view['spec_unit'] = getattr(self.main_window.plot_renderers.panel_spec, 'spec_unit', 'kHz')
            except Exception:
                pass # Ignoring spec unit warning to avoid disruption

        dlg = ExportGraphDialog(self.ctx, live_view=live_view, parent=self.main_window)
        dlg.exec()
