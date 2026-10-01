import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QGroupBox, QFormLayout, QFileDialog, QTabWidget, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from utils.report_generator import ReportConfig, ReportSectionFlags

class ExportReportDialog(QDialog):
    """
    Diálogo para configurar a exportação do Relatório PDF Modular (Fase 9).
    Coleta metadados científicos e as seções desejadas no documento.
    """
    def __init__(self, session_context, parent=None):
        super().__init__(parent)
        self.session_context = session_context
        self.setWindowTitle("Exportar Relatório Científico (PDF)")
        self.resize(500, 450)
        self.config = None

        self._build_ui()
        self._load_defaults()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        
        # Aba 1: Metadados
        self.tab_meta = QWidget()
        meta_layout = QFormLayout(self.tab_meta)
        self.txt_species = QLineEdit()
        self.txt_specimen = QLineEdit()
        self.txt_location = QLineEdit()
        self.txt_temp = QLineEdit()
        self.txt_equip = QLineEdit()
        self.txt_researcher = QLineEdit()
        self.txt_inst = QLineEdit()

        meta_layout.addRow("Espécie:", self.txt_species)
        meta_layout.addRow("Cód. Espécime:", self.txt_specimen)
        meta_layout.addRow("Localidade:", self.txt_location)
        meta_layout.addRow("Temperatura (°C):", self.txt_temp)
        meta_layout.addRow("Equipamento:", self.txt_equip)
        meta_layout.addRow("Pesquisador:", self.txt_researcher)
        meta_layout.addRow("Instituição:", self.txt_inst)
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
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        layout.addLayout(btn_layout)

        # Conexões
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_export.clicked.connect(self._on_export)

    def _load_defaults(self):
        # Carregar metadados pré-existentes se houver
        rp = self.session_context.report_params if hasattr(self.session_context, 'report_params') else {}
        self.txt_inst.setText(rp.get('institution', ''))
        self.txt_researcher.setText(rp.get('researcher_name', ''))
        # Assumindo checkboxes padrão
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

        meta = {
            "species": self.txt_species.text().strip(),
            "specimen": self.txt_specimen.text().strip(),
            "location": self.txt_location.text().strip(),
            "temperature": self.txt_temp.text().strip(),
            "equipment": self.txt_equip.text().strip(),
            "researcher_name": self.txt_researcher.text().strip(),
            "institution": self.txt_inst.text().strip()
        }

        # Atualiza o contexto legado para manter a compatibilidade temporária
        if hasattr(self.session_context, 'report_params'):
            self.session_context.report_params['institution'] = meta['institution']
            self.session_context.report_params['researcher_name'] = meta['researcher_name']

        self.config = ReportConfig(
            metadata=meta,
            section_flags=flags,
            output_path=path
        )
        self.accept()
