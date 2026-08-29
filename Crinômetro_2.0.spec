# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['crinometro_laucher.py'],
    pathex=['M:\\Documentos\\Faculdade\\Biologia'],
    binaries=[],
    datas=[
        ('loading.mp4', '.'),
        ('loaded.mp4', '.'),
        ('grilinho.ico', '.'),
        ('grilinho.png', '.'),
        ('crinometro_config.json', '.'),
        ('crinometro.py', '.'),
    ],
    hiddenimports=[
        'crinometro',
        'scipy',
        'scipy.io',
        'scipy.io.wavfile',
        'scipy.signal',
        'matplotlib',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.figure',
        'matplotlib.patches',
        'numpy',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Crinômetro_2.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='grilinho.ico',
)
