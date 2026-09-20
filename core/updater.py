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


def launch_windows_updater(downloaded_file: str, target_dir: str = "", execute: bool = True):
    """
    Orquestra a substituição limpa e atualização do Crinômetro no Windows de forma assíncrona.
    Utiliza script PowerShell (.ps1) codificado em UTF-8 com BOM para suporte total e nativo
    a caracteres especiais (como acentos em 'Crinômetro'), normaliza diretórios legados,
    aguarda a liberação das travas de arquivo do processo pai e executa o instalador.
    """
    if not target_dir:
        if getattr(sys, "frozen", False):
            target_dir = os.path.dirname(sys.executable)
        else:
            default_pf = os.environ.get("ProgramFiles", r"C:\Program Files")
            target_dir = os.path.join(default_pf, "Crinometro")

    # Normalização rigorosa: padroniza a pasta de instalação como 'Crinometro' (sem acento)
    # eliminando de vez incompatibilidades históricas de codepages e caminhos no Windows
    target_dir = os.path.abspath(target_dir)
    parent_dir = os.path.dirname(target_dir)
    base_name = os.path.basename(target_dir)
    if base_name in ("Crinômetro", "Crin\ufffdmetro", "Crin?metro") or base_name.lower().startswith("crin"):
        target_dir = os.path.join(parent_dir, "Crinometro")

    downloaded_file = os.path.abspath(downloaded_file)
    pid = os.getpid()

    updater_dir = os.path.join(tempfile.gettempdir(), "crinometro_updater")
    os.makedirs(updater_dir, exist_ok=True)
    ps1_file = os.path.join(updater_dir, "apply_update.ps1")
    bat_file = os.path.join(updater_dir, "apply_update.bat")

    is_zip = downloaded_file.lower().endswith(".zip")
    is_installer = downloaded_file.lower().endswith(".exe") and any(
        kw in os.path.basename(downloaded_file).lower() for kw in ("setup", "install")
    )
    exe_name = os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "Crinometro.exe"
    exe_name = exe_name.replace("ô", "o").replace("\ufffd", "o").replace("?", "o")
    exe_target = os.path.join(target_dir, exe_name)

    if not os.path.exists(exe_target) and os.path.isdir(target_dir):
        try:
            cands = [f for f in os.listdir(target_dir) if f.lower().startswith("crinometro") and f.lower().endswith(".exe")]
            if cands:
                exe_target = os.path.join(target_dir, cands[0])
        except Exception:
            pass

    if is_installer:
        update_cmd_ps1 = f"""
# Executa instalador Inno Setup silenciosamente e aguarda conclusao
$installArgs = "/SP- /VERYSILENT /SUPPRESSMSGBOXES /DIR=`"{target_dir}`""
Start-Process -FilePath "{downloaded_file}" -ArgumentList $installArgs -Wait
"""
    elif is_zip:
        update_cmd_ps1 = f"""
# Extrai arquivo zip e copia recursivamente para a pasta de destino
$extractDir = Join-Path (Split-Path "{downloaded_file}") "extracted"
if (Test-Path "$extractDir") {{ Remove-Item -Path "$extractDir" -Recurse -Force -ErrorAction SilentlyContinue }}
Expand-Archive -Path "{downloaded_file}" -DestinationPath "$extractDir" -Force
Copy-Item -Path "$extractDir\\*" -Destination "{target_dir}" -Recurse -Force
Remove-Item -Path "$extractDir" -Recurse -Force -ErrorAction SilentlyContinue
"""
    else:
        update_cmd_ps1 = f"""
# Substituicao direta de executavel
Copy-Item -Path "{downloaded_file}" -Destination "{exe_target}" -Force
"""

    ps1_content = f"""# Crinometro Auto-Updater PowerShell Script
$ErrorActionPreference = 'SilentlyContinue'

$TargetDir = "{target_dir}"
$DownloadedFile = "{downloaded_file}"
$ExeTarget = "{exe_target}"
$ProcessPid = {pid}

# 1. Aguarda o encerramento do processo Crinometro atual para liberacao das travas de arquivo
$parentProc = Get-Process -Id $ProcessPid -ErrorAction SilentlyContinue
if ($parentProc) {{
    $parentProc.WaitForExit(10000)
}}
Stop-Process -Id $ProcessPid -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 600

# 2. Executa a atualizacao
{update_cmd_ps1}

# 3. Migra configuracoes e limpa pastas legadas com acento ou corrompidas
$parentDir = Split-Path "$TargetDir" -Parent
$legacyDirs = @(
    (Join-Path "$parentDir" "Crinômetro"),
    (Join-Path "$parentDir" ("Crin" + [char]0xFFFD + "metro"))
)
foreach ($ld in $legacyDirs) {{
    if (Test-Path "$ld") {{
        # Preserva crinometro_config.json caso exista na pasta antiga
        $oldCfg = Join-Path "$ld" "crinometro_config.json"
        $newCfg = Join-Path "$TargetDir" "crinometro_config.json"
        if ((Test-Path "$oldCfg") -and !(Test-Path "$newCfg")) {{
            Copy-Item -Path "$oldCfg" -Destination "$newCfg" -Force -ErrorAction SilentlyContinue
        }}
        Remove-Item -Path "$ld" -Recurse -Force -ErrorAction SilentlyContinue
    }}
}}

# 4. Localiza o executavel mais recente gerado pelo instalador
$latestExe = Get-ChildItem -Path "$TargetDir" -Filter "Crinometro*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latestExe) {{
    # Remove executaveis legados duplicados para manter apenas o executavel atual
    Get-ChildItem -Path "$TargetDir" -Filter "Crinometro*.exe" -File -ErrorAction SilentlyContinue |
        Where-Object {{ $_.FullName -ne $latestExe.FullName }} |
        Remove-Item -Force -ErrorAction SilentlyContinue

    Start-Process -FilePath $latestExe.FullName
}} elseif (Test-Path "$ExeTarget") {{
    Start-Process -FilePath "$ExeTarget"
}}

# 5. Limpeza de arquivos temporarios
Start-Sleep -Seconds 2
Remove-Item -Path "$DownloadedFile" -Force -ErrorAction SilentlyContinue
$batFile = Join-Path (Split-Path $PSCommandPath) "apply_update.bat"
if (Test-Path "$batFile") {{ Remove-Item -Path "$batFile" -Force -ErrorAction SilentlyContinue }}
Remove-Item -Path $PSCommandPath -Force -ErrorAction SilentlyContinue
"""

    # Gravacao do script em UTF-8 com BOM (essencial para Windows PowerShell 5.1 interpretar acentos)
    with open(ps1_file, "w", encoding="utf-8-sig") as f:
        f.write(ps1_content)

    # Wrapper .bat para compatibilidade e fallback
    bat_content = f"""@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps1_file}"
"""
    with open(bat_file, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # Disparo em processo totalmente desacoplado da arvore do aplicativo
    if execute:
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creation_flags |= subprocess.DETACHED_PROCESS

        ps_cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden",
            "-File", ps1_file
        ]

        subprocess.Popen(
            ps_cmd,
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )



