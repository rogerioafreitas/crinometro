# -*- mode: python ; coding: utf-8 -*-


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
    name='Crinometro_v4.2.2',
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
    name='Crinometro_v4.2.2',
)
