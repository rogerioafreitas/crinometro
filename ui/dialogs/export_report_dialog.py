import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QGroupBox, QFormLayout, QFileDialog, QTabWidget, QWidget, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from ui.dialogs.theme import MODERN_DIALOG_THEME
from utils.report_generator import ReportConfig, ReportSectionFlags, extract_specimen_id

class ExportReportDialog(QDialog):
    """
    Diálogo para configurar a exportação do Relatório PDF Modular (Fase 9).
    Coleta metadados científicos e as seções desejadas no documento.
    """
    def __init__(self, session_context, checked_files=None, parent=None):
        super().__init__(parent)
        self.session_context = session_context
        self.checked_files = checked_files or []
        self.setWindowTitle("Exportar Relatório Científico (PDF)")
        self.resize(600, 680)
        self.config = None

        self._build_ui()
        self._load_defaults()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        
        # Aba 1: Metadados
        self.tab_meta = QWidget()
        meta_layout = QVBoxLayout(self.tab_meta)

        # Campos Globais
        group_global = QGroupBox("Metadados Globais (Gravação / Contexto)")
        global_layout = QFormLayout(group_global)
        global_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.txt_location = QLineEdit()
        self.txt_temp = QLineEdit()
        self.txt_equip = QLineEdit()
        self.txt_researcher = QLineEdit()
        self.txt_inst = QLineEdit()

        global_layout.addRow("Localidade:", self.txt_location)
        global_layout.addRow("Temperatura (°C):", self.txt_temp)
        global_layout.addRow("Equipamento:", self.txt_equip)
        global_layout.addRow("Pesquisador:", self.txt_researcher)
        global_layout.addRow("Instituição:", self.txt_inst)
        
        meta_layout.addWidget(group_global)

        # Campos por Arquivo
        group_files = QGroupBox("Metadados por Áudio (Espécie / Espécime)")
        files_layout = QVBoxLayout(group_files)
        
        self.table_files = QTableWidget(len(self.checked_files), 3)
        self.table_files.setHorizontalHeaderLabels(["Arquivo", "Espécie", "Cód. Espécime"])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_files.setAlternatingRowColors(True)
        self.table_files.verticalHeader().setVisible(False)

        for i, fname in enumerate(self.checked_files):
            item_file = QTableWidgetItem(fname)
            item_file.setFlags(item_file.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_files.setItem(i, 0, item_file)
            
            # Espécie default
            self.table_files.setItem(i, 1, QTableWidgetItem(""))
            
            # Espécime extraído do nome
            specimen_inferred = extract_specimen_id(fname)
            self.table_files.setItem(i, 2, QTableWidgetItem(specimen_inferred))

        files_layout.addWidget(self.table_files)

        btn_apply_all = QPushButton("Aplicar Espécie do 1º áudio aos demais")
        btn_apply_all.setToolTip("Copia a espécie da primeira linha para as demais")
        btn_apply_all.clicked.connect(self._apply_species_to_all)
        files_layout.addWidget(btn_apply_all)

        meta_layout.addWidget(group_files)

        self.tabs.addTab(self.tab_meta, "Metadados")

        # Aba 2: Módulos do Relatório
        self.tab_modules = QWidget()
        mod_layout = QVBoxLayout(self.tab_modules)
        
        group_mod = QGroupBox("Seções Inclusas no PDF")
        vmod = QVBoxLayout(group_mod)
        self.chk_resumo = QCheckBox("Resumo Executivo e Tabela de Arquivos")
        self.chk_metricas = QCheckBox("Métricas Temporais Consolidadas")
        self.chk_cadencia = QCheckBox("Diagnóstico de Cadência Rítmica")
        self.chk_dolbear = QCheckBox("Estimativa de Temperatura (Lei de Dolbear)")
        self.chk_graficos = QCheckBox("Gráficos selecionados (Em breve)")
        self.chk_pulsos = QCheckBox("Listagem exaustiva de chilreios e pulsos")
        
        self.chk_graficos.setEnabled(False) # Serão ativados quando gráficos forem integrados
        
        vmod.addWidget(self.chk_resumo)
        vmod.addWidget(self.chk_metricas)
        vmod.addWidget(self.chk_cadencia)
        vmod.addWidget(self.chk_dolbear)
        vmod.addWidget(self.chk_graficos)
        vmod.addWidget(self.chk_pulsos)
        mod_layout.addWidget(group_mod)
        mod_layout.addStretch()
        self.tabs.addTab(self.tab_modules, "Conteúdo")

        layout.addWidget(self.tabs)

        # Botões
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

        # Conexões
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_export.clicked.connect(self._on_export)
        self.setStyleSheet(MODERN_DIALOG_THEME)

    def _apply_species_to_all(self):
        if self.table_files.rowCount() > 0:
            first_species = self.table_files.item(0, 1).text()
            for i in range(1, self.table_files.rowCount()):
                self.table_files.setItem(i, 1, QTableWidgetItem(first_species))

    def _load_defaults(self):
        rp = self.session_context.report_params if hasattr(self.session_context, 'report_params') else {}
        self.txt_inst.setText(rp.get('institution', ''))
        self.txt_researcher.setText(rp.get('researcher_name', ''))
        
        # Carrega espécie global legado, se houver, no 1º item da tabela e replica
        legacy_species = rp.get('species', '')
        if legacy_species and self.table_files.rowCount() > 0:
            self.table_files.item(0, 1).setText(legacy_species)
            self._apply_species_to_all()

        self.chk_resumo.setChecked(True)
        self.chk_metricas.setChecked(True)
        self.chk_cadencia.setChecked(True)
        self.chk_dolbear.setChecked(True)
        self.chk_pulsos.setChecked(False)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório Modular", "Relatorio_Modular.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return

        flags = ReportSectionFlags(
            resumo=self.chk_resumo.isChecked(),
            metricas=self.chk_metricas.isChecked(),
            cadencia=self.chk_cadencia.isChecked(),
            dolbear=self.chk_dolbear.isChecked(),
            graficos=self.chk_graficos.isChecked(),
            lista_pulsos=self.chk_pulsos.isChecked()
        )

        file_meta = {}
        for i in range(self.table_files.rowCount()):
            fname = self.table_files.item(i, 0).text()
            species = self.table_files.item(i, 1).text().strip()
            specimen = self.table_files.item(i, 2).text().strip()
            file_meta[fname] = {
                "species": species,
                "specimen": specimen
            }

        meta = {
            "location": self.txt_location.text().strip(),
            "temperature": self.txt_temp.text().strip(),
            "equipment": self.txt_equip.text().strip(),
            "researcher_name": self.txt_researcher.text().strip(),
            "institution": self.txt_inst.text().strip(),
            "file_meta": file_meta
        }

        if hasattr(self.session_context, 'report_params'):
            self.session_context.report_params['institution'] = meta['institution']
            self.session_context.report_params['researcher_name'] = meta['researcher_name']
            if self.table_files.rowCount() > 0:
                self.session_context.report_params['species'] = self.table_files.item(0, 1).text().strip()

        self.config = ReportConfig(
            metadata=meta,
            section_flags=flags,
            output_path=path
        )
        self.accept()
