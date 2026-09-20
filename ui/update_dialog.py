"""
Crinômetro - Interface Visual de Notificação e Download de Atualizações.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

from utils.constants import APP_VERSION
from core.updater import UpdateDownloaderThread, launch_windows_updater


class UpdateDialog(QDialog):
    """
    Janela modal para notificar nova versão, exibir changelog
    e realizar o download com barra de progresso.
    """
    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.downloader = None
        self.new_version = update_info.get("tag", "Desconhecida")
        self.download_url = update_info.get("download_url", "")
        self.html_url = update_info.get("html_url", "")
        self.is_frozen = update_info.get("is_frozen", False)

        self.setWindowTitle("Nova Versão Disponível - Crinômetro")
        self.setMinimumSize(540, 420)
        self.apply_styles()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Cabeçalho com destaque
        header_frame = QFrame()
        header_l = QVBoxLayout(header_frame)
        header_l.setContentsMargins(0, 0, 0, 0)
        header_l.setSpacing(4)

        lbl_title = QLabel("🚀 Nova Versão Disponível!")
        lbl_title.setObjectName("lbl_update_title")
        lbl_title.setStyleSheet("font-size: 19px; font-weight: bold; color: #3B82F6;")

        lbl_sub = QLabel(f"Versão atual: <b>v{APP_VERSION}</b>  ➜  Nova versão: <b style='color:#10B981;'>v{self.new_version}</b>")
        lbl_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")

        header_l.addWidget(lbl_title)
        header_l.addWidget(lbl_sub)
        layout.addWidget(header_frame)

        # Changelog / Notas da Versão
        lbl_notes = QLabel("Notas da Atualização:")
        lbl_notes.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(lbl_notes)

        self.txt_notes = QTextBrowser()
        self.txt_notes.setOpenExternalLinks(True)
        body_text = self.update_info.get("changelog", "")
        if not body_text.strip():
            body_text = "Esta atualização inclui melhorias de desempenho, correções e novas funcionalidades."
        # Formata quebras de linha básicas para HTML legível
        html_body = body_text.replace("\r\n", "<br>").replace("\n", "<br>")
        self.txt_notes.setHtml(f"<div style='font-family: Segoe UI, sans-serif; font-size: 12px; line-height: 1.5;'>{html_body}</div>")
        layout.addWidget(self.txt_notes)

        # Barra de Progresso (oculta inicialmente)
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(True)
        self.prog_bar.setFixedHeight(18)
        self.prog_bar.setVisible(False)
        layout.addWidget(self.prog_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #64748B;")
        self.lbl_status.setVisible(False)
        layout.addWidget(self.lbl_status)

        # Botões de Ação
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_web = QPushButton("🌐 Abrir no GitHub")
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.clicked.connect(self._open_web)

        btn_layout.addWidget(self.btn_web)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Lembrar Mais Tarde")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_update = QPushButton("⚡ Atualizar Agora")
        self.btn_update.setObjectName("btn_primary")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self._start_update)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

    def _open_web(self):
        url = self.html_url or "https://github.com/rogerioafreitas/crinometro/releases"
        QDesktopServices.openUrl(QUrl(url))

    def _start_update(self):
        if not self.download_url:
            # Se não houver asset executável direto cadastrado na release do GitHub, redireciona para a página de download
            QMessageBox.information(
                self,
                "Download Manual",
                f"A nova versão v{self.new_version} foi lançada!\n\n"
                "Você será direcionado à página oficial de lançamentos para efetuar o download."
            )
            self._open_web()
            self.accept()
            return

        # Inicia download assíncrono
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText("Baixando nova versão...")

        self.downloader = UpdateDownloaderThread(self.download_url, parent=self)
        self.downloader.progress.connect(self._on_download_progress)
        self.downloader.finished.connect(self._on_download_finished)
        self.downloader.error.connect(self._on_download_error)
        self.downloader.start()

    def _on_download_progress(self, val: int):
        self.prog_bar.setValue(val)
        self.lbl_status.setText(f"Baixando pacote da atualização... {val}%")

    def _on_download_finished(self, file_path: str):
        self.lbl_status.setText("Download concluído! Preparando instalação...")
        reply = QMessageBox.question(
            self,
            "Reiniciar e Atualizar",
            f"O download da versão v{self.new_version} foi concluído com sucesso.\n\n"
            "O Crinômetro precisa ser reiniciado para aplicar a atualização.\n"
            "Deseja atualizar e reiniciar agora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                launch_windows_updater(file_path)
                import os
                app = QApplication.instance()
                if app:
                    app.quit()
                os._exit(0)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Falha ao Atualizar",
                    f"Ocorreu um erro ao iniciar o instalador automático:\n\n{str(e)}"
                )
        else:
            self.accept()

    def _on_download_error(self, err_msg: str):
        self.btn_update.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.lbl_status.setText("Erro no download.")
        QMessageBox.warning(
            self,
            "Falha na Atualização",
            f"Não foi possível concluir o download automático:\n\n{err_msg}\n\n"
            "Você pode baixar a versão diretamente na página do GitHub."
        )

    def apply_styles(self):
        dark = True
        if self.parent() and hasattr(self.parent(), "theme_mode"):
            dark = (self.parent().theme_mode == "dark")

        if dark:
            self.setStyleSheet("""
                QDialog { background-color: #171A1E; color: #E7E9EC; font-family: 'Segoe UI'; }
                QLabel { background: transparent; color: #E7E9EC; }
                QTextBrowser {
                    background-color: #0E1013; color: #CBD5E1; border: 1px solid #2D333B;
                    border-radius: 6px; padding: 8px;
                }
                QProgressBar {
                    background-color: #262A30; border: 1px solid #3F444D; border-radius: 4px;
                    text-align: center; color: white; font-weight: bold; font-size: 10px;
                }
                QProgressBar::chunk { background-color: #10B981; border-radius: 3px; }
                QPushButton { background-color: #2D333B; color: #E2E8F0; padding: 7px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #444C56; }
                QPushButton:hover { background-color: #373E47; }
                QPushButton#btn_primary { background-color: #2563EB; color: white; border: none; }
                QPushButton#btn_primary:hover { background-color: #1D4ED8; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #FFFFFF; color: #1E293B; font-family: 'Segoe UI'; }
                QLabel { background: transparent; color: #334155; }
                QTextBrowser {
                    background-color: #F8FAFC; color: #334155; border: 1px solid #E2E8F0;
                    border-radius: 6px; padding: 8px;
                }
                QProgressBar {
                    background-color: #E2E8F0; border: 1px solid #CBD5E1; border-radius: 4px;
                    text-align: center; color: #1E293B; font-weight: bold; font-size: 10px;
                }
                QProgressBar::chunk { background-color: #10B981; border-radius: 3px; }
                QPushButton { background-color: #F1F5F9; color: #334155; padding: 7px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #CBD5E1; }
                QPushButton:hover { background-color: #E2E8F0; }
                QPushButton#btn_primary { background-color: #2563EB; color: white; border: none; }
                QPushButton#btn_primary:hover { background-color: #1D4ED8; }
            """)
