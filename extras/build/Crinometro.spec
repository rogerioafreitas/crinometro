# -*- mode: python ; coding: utf-8 -*-


import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(SPECPATH, '../..')))
from utils.constants import APP_VERSION

app_dist_name = f'Crinometro_v{APP_VERSION}'

a = Analysis(
    ['../../crinometro__laucher.py'],
    pathex=['../..'],
    binaries=[],
    datas=[('M:/Documentos/Faculdade/Biologia/grilinho.ico', '.')],
    hiddenimports=[
        'reportlab', 'reportlab.platypus', 'reportlab.lib', 'reportlab.pdfgen',
        'scipy.special', 'scipy.integrate', 'scipy.signal', 'sklearn', 'matplotlib'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_dist_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['M:/Documentos/Faculdade/Biologia/grilinho.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_dist_name,
)
