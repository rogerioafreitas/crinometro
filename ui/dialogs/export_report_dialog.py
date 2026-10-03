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
        self.setWindowTitle("Exportar Relatório Bioacústico")
        self.resize(620, 700)
        
        self.config = None
        self.export_csv = False
        self.csv_path = None
        self.export_txt = False
        self.txt_path = None

        self._build_ui()
        self._load_defaults()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        
        # ── Aba 1: Metadados ─────────────────────────────────────────────────
        self.tab_meta = QWidget()
        meta_layout = QVBoxLayout(self.tab_meta)

        group_global = QGroupBox("Metadados Globais (Gravação / Contexto)")
        global_layout = QFormLayout(group_global)
        global_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.txt_location   = QLineEdit()
        self.txt_temp       = QLineEdit()
        self.txt_equip      = QLineEdit()
        self.txt_researcher = QLineEdit()
        self.txt_inst       = QLineEdit()

        global_layout.addRow("Localidade:", self.txt_location)
        global_layout.addRow("Temperatura (°C):", self.txt_temp)
        global_layout.addRow("Equipamento:", self.txt_equip)
        global_layout.addRow("Pesquisador:", self.txt_researcher)
        global_layout.addRow("Instituição:", self.txt_inst)
        
        meta_layout.addWidget(group_global)

        # Campos por Arquivo
        group_files = QGroupBox("Metadados por Áudio (Espécie / Cód. Espécime)")
        files_layout = QVBoxLayout(group_files)
        
        self.table_files = QTableWidget(len(self.checked_files), 3)
        self.table_files.setHorizontalHeaderLabels(["Arquivo", "Espécie", "Cód. Espécime"])
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
        
        btn_apply_all = QPushButton("Espécie = Todos")
        btn_apply_all.setToolTip("Copia a espécie da 1 linha para todas")
        btn_apply_all.clicked.connect(self._apply_species_to_all)
        
        btn_apply_sel_sp = QPushButton("Agrupar Espécie")
        btn_apply_sel_sp.setToolTip("Copia a espécie da primeira linha selecionada para as demais selecionadas")
        btn_apply_sel_sp.clicked.connect(self._apply_species_to_selected)
        
        btn_apply_sel_id = QPushButton("Agrupar Espécime")
        btn_apply_sel_id.setToolTip("Copia o espécime da primeira linha selecionada para as demais selecionadas")
        btn_apply_sel_id.clicked.connect(self._apply_specimen_to_selected)
        
        btn_layout_table.addWidget(btn_apply_all)
        btn_layout_table.addWidget(btn_apply_sel_sp)
        btn_layout_table.addWidget(btn_apply_sel_id)
        files_layout.addLayout(btn_layout_table)

        meta_layout.addWidget(group_files)
        self.tabs.addTab(self.tab_meta, "Metadados")

        # ── Aba 2: Conteúdo / Módulos ────────────────────────────────────────
        self.tab_modules = QWidget()
        mod_layout = QVBoxLayout(self.tab_modules)
        
        group_mod = QGroupBox("Seções Inclusas no PDF")
        vmod = QVBoxLayout(group_mod)
        self.chk_resumo   = QCheckBox("Resumo Executivo e Tabela de Arquivos")
        self.chk_metricas = QCheckBox("Métricas Temporais Consolidadas (inclui Variância de Pulsos)")
        self.chk_cadencia = QCheckBox("Diagnóstico de Cadência Rítmica")
        self.chk_dolbear  = QCheckBox("Estimativa de Temperatura (Lei de Dolbear)")
        self.chk_graficos = QCheckBox("Gráficos selecionados (Em breve)")
        self.chk_pulsos   = QCheckBox("Listagem exaustiva de chilreios e pulsos")
        
        self.chk_graficos.setEnabled(False)
        
        for chk in (self.chk_resumo, self.chk_metricas, self.chk_cadencia,
                    self.chk_dolbear, self.chk_graficos, self.chk_pulsos):
            vmod.addWidget(chk)
        mod_layout.addWidget(group_mod)

        # ── Formatos de exportação ─────────────────────────────────────────────
        group_fmt = QGroupBox("Formatos de Exportação (Selecione um ou mais)")
        fmt_layout = QVBoxLayout(group_fmt)

        self.chk_fmt_pdf = QCheckBox("Exportar em PDF (Relatório completo formatado)")
        self.chk_fmt_csv = QCheckBox("Exportar em CSV (Planilha com métricas de cada chilreio)")
        
        
        self.csv_options_widget = QWidget()
        csv_opt_layout = QVBoxLayout(self.csv_options_widget)
        csv_opt_layout.setContentsMargins(30, 0, 0, 0)
        
        self.rdo_csv_br = QRadioButton("Padrão Brasileiro (Excel pt-BR: delimitador ';', decimal ',')")
        self.rdo_csv_univ = QRadioButton("Padrão Universal (Python/R: delimitador ',', decimal '.')")
        self.rdo_csv_br.setChecked(True)
        
        self.csv_group = QButtonGroup(self)
        self.csv_group.addButton(self.rdo_csv_br)
        self.csv_group.addButton(self.rdo_csv_univ)
        
        csv_opt_layout.addWidget(self.rdo_csv_br)
        csv_opt_layout.addWidget(self.rdo_csv_univ)
        
        self.chk_fmt_csv.toggled.connect(self.csv_options_widget.setVisible)
        self.csv_options_widget.setVisible(False)

        self.chk_fmt_txt = QCheckBox("Exportar em TXT (Relatório em texto simples)")

        self.chk_fmt_pdf.setChecked(True)

        fmt_layout.addWidget(self.chk_fmt_pdf)
        fmt_layout.addWidget(self.chk_fmt_csv)
        fmt_layout.addWidget(self.csv_options_widget)
        fmt_layout.addWidget(self.chk_fmt_txt)
        mod_layout.addWidget(group_fmt)

        mod_layout.addStretch()
        self.tabs.addTab(self.tab_modules, "Conteúdo")

        layout.addWidget(self.tabs)

        # ── Botões ───────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_export = QPushButton("Gerar Relatório")
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
        self.chk_dolbear.setChecked(True)
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
            "location":        self.txt_location.text().strip(),
            "temperature":     self.txt_temp.text().strip(),
            "equipment":       self.txt_equip.text().strip(),
            "researcher_name": self.txt_researcher.text().strip(),
            "institution":     self.txt_inst.text().strip(),
            "file_meta":       file_meta
        }

        # Persiste na sessão
        if hasattr(self.session_context, 'report_params'):
            self.session_context.report_params['institution']     = meta['institution']
            self.session_context.report_params['researcher_name'] = meta['researcher_name']
            if self.table_files.rowCount() > 0:
                self.session_context.report_params['species'] = self.table_files.item(0, 1).text().strip()

        return meta

    def _on_export(self):
        want_pdf = self.chk_fmt_pdf.isChecked()
        want_csv = self.chk_fmt_csv.isChecked()
        want_txt = self.chk_fmt_txt.isChecked()

        if not (want_pdf or want_csv or want_txt):
            QMessageBox.warning(self, "Aviso", "Por favor, selecione pelo menos um formato para exportação.")
            return

        pdf_path = None
        csv_path = None
        txt_path = None

        if want_pdf:
            pdf_path, _ = QFileDialog.getSaveFileName(
                self, "Salvar Relatório PDF", _default_filename("pdf"), "PDF Files (*.pdf)"
            )
            if not pdf_path: return

        if want_csv:
            csv_path, _ = QFileDialog.getSaveFileName(
                self, "Salvar Relatório CSV", _default_filename("csv"), "CSV Files (*.csv)"
            )
            if not csv_path: return

        if want_txt:
            txt_path, _ = QFileDialog.getSaveFileName(
                self, "Salvar Relatório TXT", _default_filename("txt"), "Text Files (*.txt)"
            )
            if not txt_path: return

        flags = ReportSectionFlags(
            resumo      = self.chk_resumo.isChecked(),
            metricas    = self.chk_metricas.isChecked(),
            cadencia    = self.chk_cadencia.isChecked(),
            dolbear     = self.chk_dolbear.isChecked(),
            graficos    = self.chk_graficos.isChecked(),
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
