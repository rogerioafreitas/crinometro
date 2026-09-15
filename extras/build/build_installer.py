"""
Script de automação para compilação completa do Crinômetro:
1. Executa PyInstaller com o spec (extras/build/Crinometro.spec) gerando a pasta onedir em extras/dist/Crinometro_vX.Y.Z
2. Copia o arquivo crinometro_config.json padrão se não existir na pasta de distribuição
3. Executa o Inno Setup Compiler (ISCC.exe) para empacotar a distribuição em instalador executável (.exe)
   salvo em extras/dist/Download Versions/Crinometro_setup__vX.Y.Z.exe
"""
import os
import sys
import shutil
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from utils.constants import APP_VERSION

ISCC_CANDIDATES = [
    r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    r'C:\Program Files\Inno Setup 6\ISCC.exe',
    r'C:\Program Files (x86)\Inno Setup 5\ISCC.exe',
    r'C:\Program Files\Inno Setup 5\ISCC.exe',
]


def find_iscc():
    for p in ISCC_CANDIDATES:
        if os.path.isfile(p):
            return p
    iscc_path = shutil.which('ISCC.exe') or shutil.which('ISCC')
    if iscc_path:
        return iscc_path
    return None


def remove_readonly(func, path, exc_info):
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def clean_target_dist():
    target = os.path.join(PROJECT_ROOT, 'extras', 'dist', f'Crinometro_v{APP_VERSION}')
    if os.path.exists(target):
        print(f"Limpando pasta anterior com tratamento de permissões: {target}...")
        try:
            subprocess.run(['attrib', '-r', '-s', f'{target}\\*', '/s', '/d'], capture_output=True)
            subprocess.run(['attrib', '-r', '-s', target, '/d'], capture_output=True)
            shutil.rmtree(target, onexc=remove_readonly)
        except Exception as e:
            print(f"Aviso ao limpar pasta: {e}")


def run_pyinstaller():
    print('=' * 60)
    print(f'[*] 1/3 Compilando Crinômetro v{APP_VERSION} via PyInstaller...')
    print('=' * 60)

    clean_target_dist()

    spec_path = os.path.join(PROJECT_ROOT, 'extras', 'build', 'Crinometro.spec')
    if not os.path.isfile(spec_path):
        raise FileNotFoundError(f'Arquivo spec não encontrado: {spec_path}')

    py_exec = sys.executable
    cmd = [
        py_exec, '-m', 'PyInstaller',
        spec_path,
        '--distpath', os.path.join(PROJECT_ROOT, 'extras', 'dist'),
        '--workpath', os.path.join(PROJECT_ROOT, 'extras', 'build', 'pyinstaller_temp'),
        '--noconfirm'
    ]
    cmd_str = " ".join(cmd)
    print(f"Executando: {cmd_str}")
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)
    print("[+] PyInstaller concluído com sucesso!\n")


def prepare_dist_assets():
    print('=' * 60)
    print('[*] 2/3 Preparando arquivos complementares na pasta de distribuição...')
    print('=' * 60)

    dist_dir = os.path.join(PROJECT_ROOT, 'extras', 'dist', f'Crinometro_v{APP_VERSION}')
    if not os.path.isdir(dist_dir):
        parent_dist = os.path.join(PROJECT_ROOT, 'extras', 'dist')
        cands = [os.path.join(parent_dist, d) for d in os.listdir(parent_dist) if d.startswith('Crinometro_v') and os.path.isdir(os.path.join(parent_dist, d))]
        if cands:
            dist_dir = cands[0]

    config_source = os.path.join(PROJECT_ROOT, 'crinometro_config.json')
    config_dest = os.path.join(dist_dir, 'crinometro_config.json')
    if os.path.isfile(config_source) and not os.path.isfile(config_dest):
        print(f'Copiando {config_source} para {config_dest}...')
        shutil.copy2(config_source, config_dest)

    # Garantir estritamente apenas 1 executável na pasta onedir
    expected_exe = f'Crinometro_v{APP_VERSION}.exe'
    for item in os.listdir(dist_dir):
        if item.endswith('.exe') and item != expected_exe:
            redundant_file = os.path.join(dist_dir, item)
            print(f'Removendo executável duplicado: {redundant_file}...')
            try:
                os.remove(redundant_file)
            except Exception as e:
                print(f'Aviso ao remover {redundant_file}: {e}')

    print('[+] Preparação concluída!\n')
    return dist_dir


def run_inno_setup():
    print('=' * 60)
    print(f'[*] 3/3 Gerando Instalador Inno Setup (.exe) para v{APP_VERSION}...')
    print('=' * 60)

    iscc_path = find_iscc()
    if not iscc_path:
        print('[!] AVISO: Compilador do Inno Setup (ISCC.exe) não encontrado no sistema.')
        print('    Instale o Inno Setup 6 para gerar o instalador executável automaticamente.')
        return

    iss_path = os.path.join(PROJECT_ROOT, 'extras', 'dist', 'Setup_script.iss')
    if not os.path.isfile(iss_path):
        raise FileNotFoundError(f'Script Inno Setup não encontrado: {iss_path}')

    cmd = [
        iscc_path,
        f'/DMyAppVersion={APP_VERSION}',
        f'/DMyAppExeName=Crinometro_v{APP_VERSION}.exe',
        f'/DOutputBaseFilename=Crinometro_setup__v{APP_VERSION}',
        iss_path
    ]
    cmd_str = " ".join(cmd)
    print(f"Executando ISCC: {cmd_str}")
    subprocess.check_call(cmd, cwd=os.path.dirname(iss_path))
    dest_exe = os.path.join(PROJECT_ROOT, "extras", "dist", "Download Versions", f"Crinometro_setup__v{APP_VERSION}.exe")
    print(f"\n[+] Instalador gerado com sucesso!")
    print(f"    Destino: {dest_exe}\n")


def main():
    try:
        run_pyinstaller()
        prepare_dist_assets()
        run_inno_setup()
        print('=' * 60)
        print(f'[OK] BUILD COMPLETO CONCLUÍDO COM SUCESSO! (Versão {APP_VERSION})')
        print('=' * 60)
    except subprocess.CalledProcessError as e:
        print(f'[!] Erro ao executar etapa de compilação: código {e.returncode}', file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f'[!] Falha durante a compilação: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
