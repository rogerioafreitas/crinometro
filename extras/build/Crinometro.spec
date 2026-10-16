# -*- mode: python ; coding: utf-8 -*-


import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(SPECPATH, '../..')))
from utils.constants import APP_VERSION
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

app_dist_name = f'Crinometro_v{APP_VERSION}'

skops_hidden = collect_submodules('skops')
skops_data = collect_data_files('skops')

a = Analysis(
    ['../../crinometro__laucher.py'],
    pathex=['../..'],
    binaries=[],
    datas=[
        ('M:/Documentos/Faculdade/Biologia/grilinho.ico', '.'),
        ('M:/Documentos/Faculdade/Biologia/assets', 'assets')
    ] + skops_data,
    hiddenimports=[
        'reportlab', 'reportlab.platypus', 'reportlab.lib', 'reportlab.pdfgen',
        'scipy.special', 'scipy.integrate', 'scipy.signal', 'scipy.stats', 'scipy.optimize',
        'sklearn', 'sklearn.ensemble', 'sklearn.ensemble._hist_gradient_boosting',
        'sklearn.ensemble._hist_gradient_boosting.gradient_boosting',
        'sklearn.mixture', 'sklearn.tree',
        'matplotlib', 'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_agg',
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'
    ] + skops_hidden,
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
