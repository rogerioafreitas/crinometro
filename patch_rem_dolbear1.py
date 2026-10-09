filepath = 'ui/dialogs/export_report_dialog.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        self.chk_cadencia = QCheckBox(t["chk_cadence_diag"])
        self.chk_dolbear  = QCheckBox(t["chk_dolbear_est"])
        self.chk_pulsos   = QCheckBox(t["chk_pulse_listing"])

        for chk in (self.chk_resumo, self.chk_metricas, self.chk_cadencia,
                    self.chk_pulsos):
            vmod.addWidget(chk)
        self.chk_dolbear.setVisible(False)"""
replacement1 = """        self.chk_cadencia = QCheckBox(t["chk_cadence_diag"])
        self.chk_pulsos   = QCheckBox(t["chk_pulse_listing"])

        for chk in (self.chk_resumo, self.chk_metricas, self.chk_cadencia, self.chk_pulsos):
            vmod.addWidget(chk)"""
content = content.replace(target1, replacement1)

target2 = """        self.chk_cadencia.setChecked(True)
        self.chk_dolbear.setChecked(True)
        self.chk_pulsos.setChecked(False)"""
replacement2 = """        self.chk_cadencia.setChecked(True)
        self.chk_pulsos.setChecked(False)"""
content = content.replace(target2, replacement2)

target3 = """            metadata=ExportMetadata(
                resumo      = self.chk_resumo.isChecked(),
                metricas    = self.chk_metricas.isChecked(),
                cadencia    = self.chk_cadencia.isChecked(),
                dolbear     = self.chk_dolbear.isChecked(),
                lista_pulsos= self.chk_pulsos.isChecked()
            )"""
replacement3 = """            metadata=ExportMetadata(
                resumo      = self.chk_resumo.isChecked(),
                metricas    = self.chk_metricas.isChecked(),
                cadencia    = self.chk_cadencia.isChecked(),
                lista_pulsos= self.chk_pulsos.isChecked()
            )"""
content = content.replace(target3, replacement3)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
