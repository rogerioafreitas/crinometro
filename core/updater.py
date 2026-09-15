"""
Crinômetro - Módulo de Atualização Automática (Auto-Updater).
Verifica lançamentos via API do GitHub, realiza download com progresso
e orquestra a substituição limpa em ambiente executável ou redirecionamento no fonte.
"""
import os
import sys
import json
import tempfile
import subprocess
import urllib.request
from PyQt6.QtCore import QThread, pyqtSignal

from utils.constants import APP_VERSION
from utils.helpers import parse_version_tuple

GITHUB_REPO = "rogerioafreitas/crinometro"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"


def is_remote_version_newer(remote_ver: str, current_ver: str = APP_VERSION) -> bool:
    """Compara versões SemVer (X, Y, Z). Retorna True se a versão remota for superior."""
    try:
        r_tuple = parse_version_tuple(remote_ver)
        c_tuple = parse_version_tuple(current_ver)
        return r_tuple > c_tuple
    except Exception:
        return False


class UpdateCheckerThread(QThread):
    """
    Consulta assíncrona da API do GitHub para checar a versão mais recente.
    Emite update_available(dict) se houver nova versão,
    ou no_update(dict) se já estiver na versão mais recente.
    Emite error(str) em caso de falha de conexão.
    """
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "User-Agent": f"Crinometro-Updater/{APP_VERSION}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status != 200:
                    self.error.emit(f"Servidor retornou status HTTP {resp.status}")
                    return
                raw_data = resp.read().decode("utf-8")
                release_info = json.loads(raw_data)

            tag = release_info.get("tag_name", "").strip().lstrip("v")
            title = release_info.get("name", f"Versão {tag}")
            changelog = release_info.get("body", "Sem notas de lançamento disponíveis.")
            html_url = release_info.get("html_url", GITHUB_RELEASES_PAGE)
            assets = release_info.get("assets", [])

            # Procura preferencialmente por instalador Inno Setup (.exe com 'setup' ou 'installer')
            download_url = ""
            asset_name = ""
            
            # 1. Prioridade máxima: instalador .exe do Inno Setup
            for a in assets:
                name = a.get("name", "").lower()
                url = a.get("browser_download_url", "")
                if name.endswith(".exe") and any(kw in name for kw in ("setup", "installer", "install")):
                    download_url = url
                    asset_name = a.get("name")
                    break

            # 2. Segunda prioridade: qualquer executável do crinômetro
            if not download_url:
                for a in assets:
                    name = a.get("name", "").lower()
                    url = a.get("browser_download_url", "")
                    if name.endswith(".exe") and "crinometro" in name:
                        download_url = url
                        asset_name = a.get("name")
                        break

            # 3. Terceira prioridade: pacote .zip do Crinômetro
            if not download_url:
                for a in assets:
                    name = a.get("name", "").lower()
                    url = a.get("browser_download_url", "")
                    if name.endswith(".zip") and ("crinometro" in name or "onedir" in name):
                        download_url = url
                        asset_name = a.get("name")
                        break


            info_payload = {
                "tag": tag,
                "title": title,
                "changelog": changelog,
                "html_url": html_url,
                "download_url": download_url,
                "asset_name": asset_name,
                "assets": assets,
                "is_frozen": getattr(sys, "frozen", False)
            }

            if tag and is_remote_version_newer(tag, APP_VERSION):
                self.update_available.emit(info_payload)
            else:
                self.no_update.emit(info_payload)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Nenhuma release publicada ainda
                self.no_update.emit({
                    "tag": APP_VERSION,
                    "title": "Versão Atual",
                    "changelog": "Você já está executando a versão mais recente.",
                    "html_url": GITHUB_RELEASES_PAGE,
                    "download_url": "",
                    "is_frozen": getattr(sys, "frozen", False)
                })
            else:
                self.error.emit(f"Falha de comunicação com o GitHub (HTTP {e.code}): {e.reason}")
        except Exception as e:
            self.error.emit(f"Erro ao verificar atualizações: {str(e)}")


class UpdateDownloaderThread(QThread):
    """
    Download assíncrono do arquivo de atualização com notificação de progresso (0-100%).
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url: str, dest_filename: str = "", parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.dest_filename = dest_filename
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if not self.download_url:
                self.error.emit("URL de download inválida ou não especificada.")
                return

            temp_dir = os.path.join(tempfile.gettempdir(), "crinometro_updater")
            os.makedirs(temp_dir, exist_ok=True)

            filename = self.dest_filename or os.path.basename(self.download_url) or "crinometro_update.zip"
            dest_path = os.path.join(temp_dir, filename)

            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": f"Crinometro-Updater/{APP_VERSION}"}
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = resp.getheader("Content-Length")
                total_size = int(total_size) if total_size else 0

                downloaded = 0
                chunk_size = 1024 * 64  # 64 KB por bloco

                with open(dest_path, "wb") as f_out:
                    while True:
                        if self._is_cancelled:
                            self.error.emit("Download cancelado pelo usuário.")
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(min(100, percent))

            self.progress.emit(100)
            self.finished.emit(dest_path)

        except Exception as e:
            self.error.emit(f"Erro durante o download da atualização: {str(e)}")


def launch_windows_updater(downloaded_file: str, target_dir: str = ""):
    """
    Gera um script batch desacoplado (.bat) que:
    1. Aguarda o término do processo Crinômetro atual;
    2. Se for instalador Inno Setup (.exe), executa-o com parâmetros silenciosos para atualizar a instalação;
    3. Se for .zip ou binário, extrai e substitui diretamente;
    4. Reinicia o executável do Crinômetro atualizado e limpa temporários.
    """
    if not target_dir:
        target_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))

    target_dir = os.path.abspath(target_dir)
    downloaded_file = os.path.abspath(downloaded_file)
    pid = os.getpid()

    bat_dir = os.path.join(tempfile.gettempdir(), "crinometro_updater")
    os.makedirs(bat_dir, exist_ok=True)
    bat_file = os.path.join(bat_dir, "apply_update.bat")

    is_zip = downloaded_file.lower().endswith(".zip")
    is_installer = downloaded_file.lower().endswith(".exe") and any(
        kw in os.path.basename(downloaded_file).lower() for kw in ("setup", "install")
    )
    exe_name = os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "Crinometro.exe"
    exe_target = os.path.join(target_dir, exe_name)
    if not os.path.exists(exe_target):
        cands = [f for f in os.listdir(target_dir) if f.lower().startswith("crinometro") and f.lower().endswith(".exe")]
        if cands:
            exe_target = os.path.join(target_dir, cands[0])

    if is_installer:
        # Execução do instalador Inno Setup silencioso /SP- /SILENT /SUPPRESSMSGBOXES
        update_commands = f"""
echo Executando instalador Inno Setup da nova versão...
"{downloaded_file}" /SP- /SILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS /DIR="{target_dir}"
"""
    elif is_zip:
        # Extração via PowerShell e cópia recursiva
        update_commands = f"""
powershell -Command "Expand-Archive -Path '{downloaded_file}' -DestinationPath '{bat_dir}\\extracted' -Force"
xcopy /E /Y /Q "{bat_dir}\\extracted\\*" "{target_dir}\\"
"""
    else:
        update_commands = f"""
copy /Y "{downloaded_file}" "{exe_target}"
"""

    bat_content = f"""@echo off
chcp 65001 > nul
echo Aguardando encerramento do Crinômetro (PID {pid})...
:WAIT_PID
tasklist /FI "PID eq {pid}" 2>NUL | find /I /N "{pid}">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak > nul
    goto WAIT_PID
)

echo Aplicando atualização...
{update_commands}

echo Reiniciando Crinômetro...
start "" "{exe_target}"

rem Limpeza de arquivos temporários
timeout /t 2 /nobreak > nul
del /f /q "{downloaded_file}" 2>nul
(goto) 2>nul & del "%~f0"
"""

    with open(bat_file, "w", encoding="latin-1") as f:
        f.write(bat_content)

    # Executa o batch em processo totalmente desacoplado
    subprocess.Popen(["cmd.exe", "/c", bat_file], shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

