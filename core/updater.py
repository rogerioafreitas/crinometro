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
import hashlib
import re
from PyQt6.QtCore import QThread, pyqtSignal

from utils.constants import APP_VERSION
from utils.helpers import parse_version_tuple

GITHUB_REPO = "rogerioafreitas/crinometro"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"


def extract_expected_hash(release_info: dict, asset_name: str = "") -> str:
    """Extrai hash SHA-256 esperado das notas de lançamento (body) ou de assets de checksum."""
    body = release_info.get("body", "") or ""
    if asset_name and body:
        esc_name = re.escape(asset_name)
        # Formatos: "asset.exe: <hash>", "asset.exe - <hash>", "<hash> *asset.exe", "<hash>  asset.exe"
        m = re.search(rf"(?i){esc_name}\s*[:=\-]\s*([a-f0-9]{{64}})", body)
        if not m:
            m = re.search(rf"(?i)\b([a-f0-9]{{64}})\s+\*?{esc_name}", body)
        if m:
            return m.group(1).lower()

    # Formatos explícitos nas notas: "SHA256: <hash>", "SHA-256: <hash>", "sha256 = <hash>"
    m = re.search(r"(?i)\bsha-?256\s*[:=]\s*([a-f0-9]{64})\b", body)
    if m:
        return m.group(1).lower()

    # Procura por asset de checksum (.sha256 ou SHA256SUMS)
    assets = release_info.get("assets", [])
    for a in assets:
        a_name = a.get("name", "").lower()
        is_single_asset_chk = asset_name and a_name in (
            f"{asset_name.lower()}.sha256",
            f"{asset_name.lower()}.sha256sum",
        )
        is_multi_chk = a_name in ("sha256sums.txt", "sha256sums", "checksums.txt", "hashes.txt")
        if is_single_asset_chk or is_multi_chk:
            chk_url = a.get("browser_download_url")
            if chk_url:
                try:
                    req = urllib.request.Request(
                        chk_url,
                        headers={"User-Agent": f"Crinometro-Updater/{APP_VERSION}"}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        chk_text = resp.read().decode("utf-8", errors="ignore")
                        if is_single_asset_chk:
                            # Arquivo dedicado exclusivamente ao asset
                            m2 = re.search(r"(?i)\b([a-f0-9]{64})\b", chk_text)
                            if m2:
                                return m2.group(1).lower()
                        elif asset_name:
                            # Arquivo com múltiplos checksums (ex: SHA256SUMS):
                            # Mapeia estritamente a linha correspondente ao asset_name
                            esc = re.escape(asset_name)
                            for line in chk_text.splitlines():
                                if re.search(rf"(?i){esc}", line):
                                    m2 = re.search(r"(?i)\b([a-f0-9]{64})\b", line)
                                    if m2:
                                        return m2.group(1).lower()
                except Exception:
                    pass
            if is_single_asset_chk:
                break

    return ""


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


            expected_hash = extract_expected_hash(release_info, asset_name)
            info_payload = {
                "tag": tag,
                "title": title,
                "changelog": changelog,
                "html_url": html_url,
                "download_url": download_url,
                "asset_name": asset_name,
                "expected_hash": expected_hash,
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
    Download assíncrono do arquivo de atualização com notificação de progresso (0-100%)
    e verificação estrita de integridade via hash SHA-256.
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url: str, dest_filename: str = "", expected_hash: str = "", require_hash: bool = True, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.dest_filename = dest_filename
        self.expected_hash = (expected_hash or "").strip().lower()
        self.require_hash = require_hash
        self.computed_hash = ""
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if not self.download_url:
                self.error.emit("URL de download inválida ou não especificada.")
                return

            if self.require_hash and not self.expected_hash:
                self.error.emit("A atualização exige validação de integridade criptográfica, mas nenhum hash SHA-256 foi publicado no release.")
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
                hasher = hashlib.sha256()

                with open(dest_path, "wb") as f_out:
                    while True:
                        if self._is_cancelled:
                            if os.path.exists(dest_path):
                                try: os.remove(dest_path)
                                except Exception: pass
                            self.error.emit("Download cancelado pelo usuário.")
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(min(100, percent))

                if total_size > 0 and downloaded < total_size:
                    if os.path.exists(dest_path):
                        try: os.remove(dest_path)
                        except Exception: pass
                    self.error.emit(f"Download truncado ou incompleto ({downloaded}/{total_size} bytes).")
                    return
                if downloaded == 0:
                    if os.path.exists(dest_path):
                        try: os.remove(dest_path)
                        except Exception: pass
                    self.error.emit("O download foi concluído com 0 bytes.")
                    return

                self.computed_hash = hasher.hexdigest().lower()
                if self.expected_hash and self.computed_hash != self.expected_hash:
                    if os.path.exists(dest_path):
                        try: os.remove(dest_path)
                        except Exception: pass
                    self.error.emit(
                        f"Falha na verificação de integridade (SHA-256):\n"
                        f"Esperado: {self.expected_hash}\n"
                        f"Obtido: {self.computed_hash}"
                    )
                    return

            self.progress.emit(100)
            self.finished.emit(dest_path)

        except Exception as e:
            self.error.emit(f"Erro durante o download da atualização: {str(e)}")


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


            expected_hash = extract_expected_hash(release_info, asset_name)
            info_payload = {
                "tag": tag,
                "title": title,
                "changelog": changelog,
                "html_url": html_url,
                "download_url": download_url,
                "asset_name": asset_name,
                "expected_hash": expected_hash,
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
    Download assíncrono do arquivo de atualização com notificação de progresso (0-100%)
    e verificação estrita de integridade via hash SHA-256.
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url: str, dest_filename: str = "", expected_hash: str = "", require_hash: bool = True, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.dest_filename = dest_filename
        self.expected_hash = (expected_hash or "").strip().lower()
        self.require_hash = require_hash
        self.computed_hash = ""
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if not self.download_url:
                self.error.emit("URL de download inválida ou não especificada.")
                return

            if self.require_hash and not self.expected_hash:
                self.error.emit("A atualização exige validação de integridade criptográfica, mas nenhum hash SHA-256 foi publicado no release.")
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
                hasher = hashlib.sha256()

                with open(dest_path, "wb") as f_out:
                    while True:
                        if self._is_cancelled:
                            if os.path.exists(dest_path):
                                try: os.remove(dest_path)
                                except Exception: pass
                            self.error.emit("Download cancelado pelo usuário.")
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(min(100, percent))

                if total_size > 0 and downloaded < total_size:
                    if os.path.exists(dest_path):
                        try: os.remove(dest_path)
                        except Exception: pass
                    self.error.emit(f"Download truncado ou incompleto ({downloaded}/{total_size} bytes).")
                    return
                if downloaded == 0:
                    if os.path.exists(dest_path):
                        try: os.remove(dest_path)
                        except Exception: pass
                    self.error.emit("O download foi concluído com 0 bytes.")
                    return

                self.computed_hash = hasher.hexdigest().lower()
                if self.expected_hash and self.computed_hash != self.expected_hash:
                    if os.path.exists(dest_path):
                        try: os.remove(dest_path)
                        except Exception: pass
                    self.error.emit(
                        f"Falha na verificação de integridade (SHA-256):\n"
                        f"Esperado: {self.expected_hash}\n"
                        f"Obtido: {self.computed_hash}"
                    )
                    return

            self.progress.emit(100)
            self.finished.emit(dest_path)

        except Exception as e:
            self.error.emit(f"Erro durante o download da atualização: {str(e)}")


def launch_windows_updater(downloaded_file: str, target_dir: str = "", expected_hash: str = "", require_hash: bool = True, execute: bool = True):
    """
    Orquestra a substituição limpa e atualização do Crinômetro no Windows de forma assíncrona.
    Utiliza script PowerShell (.ps1) codificado em UTF-8 com BOM para suporte total e nativo
    a caracteres especiais (como acentos em 'Crinômetro'), normaliza diretórios legados,
    verifica integridade SHA-256, aguarda a liberação das travas de arquivo do processo pai e executa o instalador.
    """
    expected_hash = (expected_hash or "").strip().lower()
    downloaded_file = os.path.abspath(downloaded_file)

    if require_hash and not expected_hash:
        raise ValueError("Validação de integridade obrigatória falhou: nenhum hash SHA-256 foi fornecido.")

    # Verificação de integridade preliminar em Python
    if expected_hash and os.path.exists(downloaded_file):
        hasher = hashlib.sha256()
        with open(downloaded_file, "rb") as f_in:
            while chunk := f_in.read(65536):
                hasher.update(chunk)
        file_hash = hasher.hexdigest().lower()
        if file_hash != expected_hash:
            raise ValueError(
                f"Falha na verificação de integridade (SHA-256) do instalador:\n"
                f"Esperado: {expected_hash}\n"
                f"Obtido: {file_hash}"
            )

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
    if base_name in ("Crinômetro", "Crin\ufffdmetro", "Crin?metro") or base_name.lower() in ("crinometro", "crinômetro"):
        target_dir = os.path.join(parent_dir, "Crinometro")

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
if (Test-Path "$extractDir") {{ Remove-Item -Path "$extractDir" -Recurse -Force }}
Expand-Archive -LiteralPath '{downloaded_file}' -DestinationPath $extractDir -Force
Copy-Item -Path "$extractDir\*" -Destination '{target_dir}' -Recurse -Force
Remove-Item -Path "$extractDir" -Recurse -Force
"""
    else:
        update_cmd_ps1 = f"""
# Substituicao direta de executavel
Copy-Item -LiteralPath '{downloaded_file}' -Destination '{exe_target}' -Force
"""

    ps1_content = f"""# Crinometro Auto-Updater PowerShell Script
# ErrorActionPreference removed

$TargetDir = '{target_dir}'
$DownloadedFile = '{downloaded_file}'
$ExeTarget = '{exe_target}'
$ProcessPid = {pid}
$ExpectedHash = '{expected_hash}'

# 0. Verificacao de integridade criptografica (SHA-256) antes de executar operacoes
if ($ExpectedHash -and (Test-LiteralPath $DownloadedFile)) {{
    $actualHash = (Get-FileHash -LiteralPath $DownloadedFile -Algorithm SHA256 -ErrorAction Stop).Hash.ToLower()
    if ($actualHash -ne $ExpectedHash.ToLower()) {{
        Write-Error "Integrity check failed: Expected $ExpectedHash but got $actualHash"
        exit 1
    }}
}}

# 1. Aguarda o encerramento do processo Crinometro atual para liberacao das travas de arquivo
$parentProc = Get-Process -Id $ProcessPid
if ($parentProc) {{
    $parentProc.WaitForExit(10000)
}}
Stop-Process -Id $ProcessPid -Force
Start-Sleep -Milliseconds 600

# 2. Executa a atualizacao
{update_cmd_ps1}

# 3. Migra configuracoes e limpa pastas legadas com acento ou corrompidas
$parentDir = Split-LiteralPath $TargetDir -Parent
$legacyDirs = @(
    (Join-Path "$parentDir" "Crinômetro"),
    (Join-Path "$parentDir" ("Crin" + [char]0xFFFD + "metro"))
)
foreach ($ld in $legacyDirs) {{
    if ((Test-Path "$ld") -and ("$ld" -ne "$TargetDir")) {{
        # Preserva arquivos de configuracao e modelos do usuario caso existam na pasta antiga
        Get-ChildItem -Path "$ld" -Include "*.json","*.skops","*.pkl" -File -Recurse | ForEach-Object {{
            $destFile = Join-LiteralPath $TargetDir $_.Name
            if (!(Test-Path "$destFile")) {{
                Copy-Item -Path $_.FullName -Destination "$destFile" -Force
            }}
        }}
        Remove-Item -Path "$ld" -Recurse -Force
    }}
}}

# 4. Localiza o executavel mais recente gerado pelo instalador
$latestExe = Get-ChildItem -LiteralPath $TargetDir -Filter "Crinometro*.exe" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latestExe) {{
    # Remove executaveis legados duplicados para manter apenas o executavel atual
    Get-ChildItem -LiteralPath $TargetDir -Filter "Crinometro*.exe" -File |
        Where-Object {{ $_.FullName -ne $latestExe.FullName }} |
        Remove-Item -Force

    Start-Process -FilePath $latestExe.FullName
}} elseif (Test-Path "$ExeTarget") {{
    Start-Process -FilePath "$ExeTarget"
}}

# 5. Limpeza de arquivos temporarios
Start-Sleep -Seconds 2
Remove-Item -LiteralPath $DownloadedFile -Force
$batFile = Join-Path (Split-Path $PSCommandPath) "apply_update.bat"
if (Test-LiteralPath $batFile) {{ Remove-Item -LiteralPath $batFile -Force }}
Remove-Item -Path $PSCommandPath -Force
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



