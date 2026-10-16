"""
Crinômetro - Interface Visual de Notificação e Download de Atualizações.
"""
from PyQt6.QtWidgets import (
    QApplication,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

from utils.constants import APP_VERSION, APP_VERSION_LABEL
from utils.i18n import I18N
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
        self.expected_hash = update_info.get("expected_hash", "")

        self.lang = getattr(parent, "lang", "pt")
        t = I18N[self.lang]
        self.setWindowTitle(t["update_dialog_title"])
        self.setMinimumSize(540, 420)
        self.apply_styles()
        self._setup_ui()

    def _setup_ui(self):
        t = I18N[self.lang]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Cabeçalho com destaque
        header_frame = QFrame()
        header_l = QVBoxLayout(header_frame)
        header_l.setContentsMargins(0, 0, 0, 0)
        header_l.setSpacing(4)

        lbl_title = QLabel(t["update_header_title"])
        lbl_title.setObjectName("lbl_update_title")
        lbl_title.setStyleSheet("font-size: 19px; font-weight: bold; color: #3B82F6;")

        lbl_sub = QLabel(f"{t['update_cur_ver']} <b>v{APP_VERSION_LABEL}</b>  ➜  {t['update_new_ver']} <b style='color:#10B981;'>v{self.new_version}</b>")
        lbl_sub.setStyleSheet("font-size: 13px; color: #94A3B8;")

        header_l.addWidget(lbl_title)
        header_l.addWidget(lbl_sub)

        if self.expected_hash:
            lbl_hash = QLabel(f"🔒 SHA-256: <span style='font-family: Consolas, monospace; color: #10B981;'>{self.expected_hash[:8]}...{self.expected_hash[-8:]}</span>")
            lbl_hash.setToolTip(f"Checksum SHA-256 verificado: {self.expected_hash}")
            lbl_hash.setStyleSheet("font-size: 11px; color: #94A3B8;")
            header_l.addWidget(lbl_hash)
        else:
            lbl_hash = QLabel(f"⚠️ <span style='color: #F59E0B;'>{t['update_no_hash_warn']}</span>")
            lbl_hash.setToolTip(t["update_no_hash_tooltip"])
            lbl_hash.setStyleSheet("font-size: 11px; color: #D97706;")
            header_l.addWidget(lbl_hash)

        layout.addWidget(header_frame)

        # Changelog / Notas da Versão
        lbl_notes = QLabel(t["update_notes_lbl"])
        lbl_notes.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(lbl_notes)

        self.txt_notes = QTextBrowser()
        self.txt_notes.setOpenExternalLinks(True)
        body_text = self.update_info.get("changelog", "")
        if not body_text.strip():
            body_text = t["update_default_notes"]
        # Formata quebras de linha básicas para HTML legível
        import html
        html_body = html.escape(body_text).replace("\r\n", "<br>").replace("\n", "<br>")
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

        self.btn_web = QPushButton(t["btn_open_github"])
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.clicked.connect(self._open_web)

        btn_layout.addWidget(self.btn_web)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t["btn_remind_later"])
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_update = QPushButton(t["btn_update_now"])
        self.btn_update.setObjectName("btn_primary")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self._start_update)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

    def _open_web(self):
        url = self.html_url or "https://github.com/rogerioafreitas/crinometro/releases"
        QDesktopServices.openUrl(QUrl(url))

    def _start_update(self):
        t = I18N[self.lang]
        if not self.download_url:
            # Se não houver asset executável direto cadastrado na release do GitHub, redireciona para a página de download
            QMessageBox.information(
                self,
                t["download_manual_title"],
                t["download_manual_msg"].format(ver=self.new_version)
            )
            self._open_web()
            self.accept()
            return

        # Inicia download assíncrono
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText(t["status_downloading"])

        self.downloader = UpdateDownloaderThread(
            self.download_url,
            expected_hash=self.expected_hash,
            require_hash=bool(self.expected_hash),
            parent=self
        )
        self.downloader.progress.connect(self._on_download_progress)
        self.downloader.finished.connect(self._on_download_finished)
        self.downloader.error.connect(self._on_download_error)
        self.downloader.start()

    def _on_download_progress(self, val: int):
        t = I18N[self.lang]
        self.prog_bar.setValue(val)
        self.lbl_status.setText(t["status_downloading_pct"].format(val=val))

    def _on_download_finished(self, file_path: str):
        t = I18N[self.lang]
        self.lbl_status.setText(t["status_download_done"])
        if self.expected_hash:
            prompt_msg = t.get(
                "restart_update_prompt_verified",
                t["restart_update_prompt"]
            ).format(ver=self.new_version, hash=f"{self.expected_hash[:8]}...{self.expected_hash[-8:]}")
        else:
            prompt_msg = t.get(
                "restart_update_prompt_unverified",
                t["restart_update_prompt"]
            ).format(ver=self.new_version)

        reply = QMessageBox.question(
            self,
            t["restart_update_title"],
            prompt_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.expected_hash:
                    launch_windows_updater(file_path, expected_hash=self.expected_hash)
                else:
                    launch_windows_updater(file_path)
                import os
                app = QApplication.instance()
                if app:
                    app.quit()
                pass
            except Exception as e:
                QMessageBox.critical(
                    self,
                    t["update_failed_title"],
                    t["update_failed_msg"].format(err=str(e))
                )
        else:
            self.accept()

    def _on_download_error(self, err_msg: str):
        t = I18N[self.lang]
        self.btn_update.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.lbl_status.setText(t["status_download_err"])
        QMessageBox.warning(
            self,
            t["update_failed_title"],
            t["update_failed_download_msg"].format(err=err_msg)
        )

    def _cleanup_downloader(self):
        downloader = getattr(self, "downloader", None)
        if downloader is not None and downloader.isRunning():
            downloader.cancel()
            try:
                downloader.progress.disconnect()
            except Exception:
                pass
            try:
                downloader.finished.disconnect()
            except Exception:
                pass
            try:
                downloader.error.disconnect()
            except Exception:
                pass
            downloader.wait(1500)

    def reject(self):
        self._cleanup_downloader()
        super().reject()

    def closeEvent(self, event):
        self._cleanup_downloader()
        super().closeEvent(event)

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
