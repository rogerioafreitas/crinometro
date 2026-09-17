"""
Crinômetro - Internacionalização (Português / Inglês).
"""
from utils.constants import APP_VERSION

I18N = {
    "pt": {
        "app_title": f"Crinômetro - {APP_VERSION}",
        "file": "Arquivo",
        "load": "Carregar .wav",
        "export": "Exportar Relatório (.txt)",
        "settings": "Configurações",
        "algo_settings": "Parâmetros do Algoritmo...",
        "gen_settings": "Preferências Gerais...",
        "save_settings": "Salvar Configurações Atuais",
        "help": "Ajuda",
        "about": "Sobre...",
        "check_updates": "Verificar Atualizações...",
        "files": "🎧 Arquivos",
        "reanalyze": "🔄 Reanalisar",
        "remove": "🗑️",
        "sync": "🔗 Sincronizar (X)",
        "learn_corrections": "Salvar Correções",
        "wave": "Onda Acústica",
        "hist": "Histograma de Pulsos",
        "freq": "Freq. Dominante vs Tempo",
        "spec": "Espectrograma",
        "welcome": "Vá em Arquivo > Carregar .wav ou arraste um arquivo para iniciar.",
        "success": "Sucesso",
        "config_saved": "Configurações salvas para a próxima inicialização.",
        "error": "Erro",
        "inst": "Instituição:",
        "researcher": "Pesquisador:",
        "role": "Função:",
        "level": "Grau Acadêmico:",
        "lang": "Idioma:",
        "toggle_panel": "Ocultar/Mostrar Painel de Arquivos",
        "reset_settings": "Resetar para Padrões (Desaprender)...",
        "reset_confirm_title": "Resetar Configurações?",
        "reset_confirm_msg": (
            "Esta ação irá:\n\n"
            "• Restaurar todos os parâmetros do algoritmo para os valores padrão\n"
            "• Apagar o modelo de aprendizado ativo\n"
            "• Remover todas as correções manuais salvas\n\n"
            "Esta operação não pode ser desfeita. Deseja continuar?"
        ),
        "reset_done": "Configurações resetadas. O app agora usa os parâmetros padrão originais.",
        "export_training": "Exportar Treinamento (.pkl)...",
        "import_training": "Carregar Treinamento (.pkl)...",
    },
    "en": {
        "app_title": f"Crinometer - {APP_VERSION}",
        "file": "File",
        "load": "Load .wav",
        "export": "Export Report (.txt)",
        "settings": "Settings",
        "algo_settings": "Algorithm Parameters...",
        "gen_settings": "General Preferences...",
        "save_settings": "Save Current Settings",
        "help": "Help",
        "about": "About...",
        "check_updates": "Check for Updates...",
        "files": "🎧 Files",
        "reanalyze": "🔄 Reanalyze",
        "remove": "🗑️",
        "sync": "🔗 Sync Time (X)",
        "learn_corrections": "Save Corrections",
        "wave": "Acoustic Wave",
        "hist": "Pulse Histogram",
        "freq": "Dominant Freq. vs Time",
        "spec": "Spectrogram",
        "welcome": "Go to File > Load .wav or drag a file here to start.",
        "success": "Success",
        "config_saved": "Settings saved for next startup.",
        "error": "Error",
        "inst": "Institution:",
        "researcher": "Researcher:",
        "role": "Role:",
        "level": "Academic Level:",
        "lang": "Language:",
        "toggle_panel": "Toggle File Panel",
        "reset_settings": "Reset to Defaults (Forget Learning)...",
        "reset_confirm_title": "Reset Settings?",
        "reset_confirm_msg": (
            "This will:\n\n"
            "• Restore all algorithm parameters to factory defaults\n"
            "• Erase the active learning model\n"
            "• Remove all manually saved corrections\n\n"
            "This cannot be undone. Continue?"
        ),
        "reset_done": "Settings reset. The app now uses the original default parameters.",
        "export_training": "Export Training Model (.pkl)...",
        "import_training": "Load Training Model (.pkl)...",
    }
}

