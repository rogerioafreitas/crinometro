import os
import datetime
from PyQt6.QtWidgets import QRadioButton, QButtonGroup
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QGroupBox, QFormLayout, QFileDialog, QTabWidget, QWidget,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from ui.dialogs.theme import get_dialog_theme
from utils.i18n import I18N
from utils.report_generator import ReportConfig, ReportSectionFlags, extract_specimen_id


def _default_filename(ext: str) -> str:
    """Gera nome de arquivo único baseado em data e hora: Relatorio_Bioacustico_YYYYMMDD_HHmm.ext"""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    return f"Relatorio_Bioacustico_{ts}.{ext}"


class ExportReportDialog(QDialog):
    """
    Diálogo para configurar a exportação do Relatório Bioacústico Modular.
    Suporta exportação em PDF, CSV e TXT simultaneamente.
    """
    def __init__(self, session_context, checked_files=None, parent=None):
        super().__init__(parent)
        self.session_context = session_context
        self.checked_files = checked_files or []
        self.lang = getattr(parent, "lang", None) or getattr(session_context, "report_params", {}).get("lang", "pt")
        t = I18N.get(self.lang, I18N["pt"])
        self.setWindowTitle(t["export_report_title"])
        self.resize(620, 700)
        
        self.config = None
        self.export_csv = False
        self.csv_path = None
        self.export_txt = False
        self.txt_path = None

        self._build_ui()
        self._load_defaults()

    def _build_ui(self):
        t = I18N.get(getattr(self, "lang", "pt"), I18N["pt"])
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        
        # ── Aba 1: Metadados ─────────────────────────────────────────────────
        self.tab_meta = QWidget()
        meta_layout = QVBoxLayout(self.tab_meta)

        group_global = QGroupBox(t["meta_global_group"])
        global_layout = QFormLayout(group_global)
        global_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.txt_temp       = QLineEdit()
        self.txt_equip      = QLineEdit()
        self.txt_researcher = QLineEdit()
        self.txt_inst       = QLineEdit()

        global_layout.addRow(t["temp_lbl"], self.txt_temp)
        global_layout.addRow(t["equip_lbl"], self.txt_equip)
        global_layout.addRow(t["researcher_lbl"], self.txt_researcher)
        global_layout.addRow(t["inst_lbl"], self.txt_inst)
        
        meta_layout.addWidget(group_global)

        # Campos por Arquivo
        group_files = QGroupBox(t["meta_files_group"])
        files_layout = QVBoxLayout(group_files)
        
        self.table_files = QTableWidget(len(self.checked_files), 3)
        self.table_files.setHorizontalHeaderLabels([t["th_file"], t["th_species"], t["th_specimen"]])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_files.setAlternatingRowColors(True)
        self.table_files.verticalHeader().setVisible(False)
        from PyQt6.QtWidgets import QAbstractItemView
        self.table_files.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        for i, fname in enumerate(self.checked_files):
            item_file = QTableWidgetItem(fname)
            item_file.setFlags(item_file.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_files.setItem(i, 0, item_file)
            self.table_files.setItem(i, 1, QTableWidgetItem(""))
            specimen_inferred = extract_specimen_id(fname)
            self.table_files.setItem(i, 2, QTableWidgetItem(specimen_inferred))

        files_layout.addWidget(self.table_files)

        btn_layout_table = QHBoxLayout()
        
        btn_apply_all = QPushButton(t["btn_species_all"])
        btn_apply_all.setToolTip(t["btn_species_all_tt"])
        btn_apply_all.clicked.connect(self._apply_species_to_all)
        
        btn_apply_sel_sp = QPushButton(t["btn_group_species"])
        btn_apply_sel_sp.setToolTip(t["btn_group_species_tt"])
        btn_apply_sel_sp.clicked.connect(self._apply_species_to_selected)
        
        btn_apply_sel_id = QPushButton(t["btn_group_specimen"])
        btn_apply_sel_id.setToolTip(t["btn_group_specimen_tt"])
        btn_apply_sel_id.clicked.connect(self._apply_specimen_to_selected)
        
        btn_layout_table.addWidget(btn_apply_all)
        btn_layout_table.addWidget(btn_apply_sel_sp)
        btn_layout_table.addWidget(btn_apply_sel_id)
        files_layout.addLayout(btn_layout_table)

        meta_layout.addWidget(group_files)
        self.tabs.addTab(self.tab_meta, t["tab_metadata"])

        # ── Aba 2: Conteúdo / Módulos ────────────────────────────────────────
        self.tab_modules = QWidget()
        mod_layout = QVBoxLayout(self.tab_modules)
        
        group_mod = QGroupBox(t["sec_included_group"])
        vmod = QVBoxLayout(group_mod)
        self.chk_resumo   = QCheckBox(t["chk_exec_summary"])
        self.chk_metricas = QCheckBox(t["chk_consolidated_metrics"])
        self.chk_cadencia = QCheckBox(t["chk_cadence_diag"])
        self.chk_pulsos   = QCheckBox(t["chk_pulse_listing"])
        
        for chk in (self.chk_resumo, self.chk_metricas, self.chk_cadencia,
                    self.chk_pulsos):
            vmod.addWidget(chk)
        mod_layout.addWidget(group_mod)

        # ── Formatos de exportação ─────────────────────────────────────────────
        group_fmt = QGroupBox(t["export_formats_group"])
        fmt_layout = QVBoxLayout(group_fmt)

        self.chk_fmt_pdf = QCheckBox(t["chk_export_pdf"])
        self.chk_fmt_csv = QCheckBox(t["chk_export_csv"])
        
        
        self.csv_options_widget = QWidget()
        csv_opt_layout = QVBoxLayout(self.csv_options_widget)
        csv_opt_layout.setContentsMargins(30, 0, 0, 0)
        
        self.rdo_csv_br = QRadioButton(t["rdo_csv_br"])
        self.rdo_csv_univ = QRadioButton(t["rdo_csv_univ"])
        self.rdo_csv_br.setChecked(True)
        
        self.csv_group = QButtonGroup(self)
        self.csv_group.addButton(self.rdo_csv_br)
        self.csv_group.addButton(self.rdo_csv_univ)
        
        csv_opt_layout.addWidget(self.rdo_csv_br)
        csv_opt_layout.addWidget(self.rdo_csv_univ)
        
        self.chk_fmt_csv.toggled.connect(self.csv_options_widget.setVisible)
        self.csv_options_widget.setVisible(False)

        self.chk_fmt_txt = QCheckBox(t["chk_export_txt"])

        self.chk_fmt_pdf.setChecked(True)

        fmt_layout.addWidget(self.chk_fmt_pdf)
        fmt_layout.addWidget(self.chk_fmt_csv)
        fmt_layout.addWidget(self.csv_options_widget)
        fmt_layout.addWidget(self.chk_fmt_txt)
        mod_layout.addWidget(group_fmt)

        mod_layout.addStretch()
        self.tabs.addTab(self.tab_modules, t["tab_content"])

        layout.addWidget(self.tabs)

        # ── Botões ───────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(t["cancel"])
        self.btn_export = QPushButton(t["btn_generate_report"])
        self.btn_export.setDefault(True)
        self.btn_export.setObjectName("primaryButton")
        btn_layout.setContentsMargins(0, 16, 0, 0)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_export.clicked.connect(self._on_export)
        is_dark = True
        if hasattr(self.parent(), "theme_mode"):
            is_dark = self.parent().theme_mode == "dark"
        self.setStyleSheet(get_dialog_theme(is_dark))

    def _apply_species_to_all(self):
        if self.table_files.rowCount() > 0:
            first_species = self.table_files.item(0, 1).text()
            for i in range(1, self.table_files.rowCount()):
                self.table_files.item(i, 1).setText(first_species)

    def _apply_species_to_selected(self):
        selected = self.table_files.selectedItems()
        if not selected: return
        rows = sorted(list(set([item.row() for item in selected])))
        ref_text = self.table_files.item(rows[0], 1).text()
        for r in rows:
            self.table_files.item(r, 1).setText(ref_text)

    def _apply_specimen_to_selected(self):
        selected = self.table_files.selectedItems()
        if not selected: return
        rows = sorted(list(set([item.row() for item in selected])))
        ref_text = self.table_files.item(rows[0], 2).text()
        for r in rows:
            self.table_files.item(r, 2).setText(ref_text)

    def _load_defaults(self):
        rp = self.session_context.report_params if hasattr(self.session_context, 'report_params') else {}
        self.txt_inst.setText(rp.get('institution', ''))
        self.txt_researcher.setText(rp.get('researcher_name', ''))
        
        legacy_species = rp.get('species', '')
        if legacy_species and self.table_files.rowCount() > 0:
            self.table_files.item(0, 1).setText(legacy_species)
            self._apply_species_to_all()

        self.chk_resumo.setChecked(True)
        self.chk_metricas.setChecked(True)
        self.chk_cadencia.setChecked(True)
        self.chk_pulsos.setChecked(False)

    def _build_meta(self):
        """Coleta metadados do formulário."""
        file_meta = {}
        for i in range(self.table_files.rowCount()):
            fname   = self.table_files.item(i, 0).text()
            species = self.table_files.item(i, 1).text().strip()
            specimen = self.table_files.item(i, 2).text().strip()
            file_meta[fname] = {"species": species, "specimen": specimen}

        meta = {
            "temperature":     self.txt_temp.text().strip(),
            "equipment":       self.txt_equip.text().strip(),
            "researcher_name": self.txt_researcher.text().strip(),
            "institution":     self.txt_inst.text().strip(),
            "file_meta":       file_meta
        }

        # Persiste na sessão acionando o setter de report_params
        if hasattr(self.session_context, 'report_params') and isinstance(self.session_context.report_params, dict):
            updated_params = dict(self.session_context.report_params)
            updated_params['institution']     = meta['institution']
            updated_params['researcher_name'] = meta['researcher_name']
            if self.table_files.rowCount() > 0:
                updated_params['species'] = self.table_files.item(0, 1).text().strip()
            self.session_context.report_params = updated_params

        return meta

    def _on_export(self):
        t = I18N.get(getattr(self, "lang", "pt"), I18N["pt"])
        want_pdf = self.chk_fmt_pdf.isChecked()
        want_csv = self.chk_fmt_csv.isChecked()
        want_txt = self.chk_fmt_txt.isChecked()

        if not (want_pdf or want_csv or want_txt):
            QMessageBox.warning(self, t["warning"], t["select_one_format_warn"])
            return

        pdf_path = None
        csv_path = None
        txt_path = None

        if want_pdf:
            pdf_path, _ = QFileDialog.getSaveFileName(
                self, t["save_pdf_title"], _default_filename("pdf"), "PDF Files (*.pdf)"
            )
            if not pdf_path: return

        if want_csv:
            csv_path, _ = QFileDialog.getSaveFileName(
                self, t["save_csv_title"], _default_filename("csv"), "CSV Files (*.csv)"
            )
            if not csv_path: return

        if want_txt:
            txt_path, _ = QFileDialog.getSaveFileName(
                self, t["save_txt_title"], _default_filename("txt"), "Text Files (*.txt)"
            )
            if not txt_path: return

        flags = ReportSectionFlags(
            resumo      = self.chk_resumo.isChecked(),
            metricas    = self.chk_metricas.isChecked(),
            cadencia    = self.chk_cadencia.isChecked(),
            lista_pulsos= self.chk_pulsos.isChecked()
        )

        meta = self._build_meta()

        self.config = ReportConfig(
            metadata=meta,
            section_flags=flags,
            output_path=pdf_path or ""
        )
        self.export_csv = want_csv
        self.csv_path   = csv_path
        self.csv_mode   = "brazilian" if getattr(self, 'rdo_csv_br', None) and self.rdo_csv_br.isChecked() else "universal"
        self.export_txt = want_txt
        self.txt_path   = txt_path
        self.accept()
