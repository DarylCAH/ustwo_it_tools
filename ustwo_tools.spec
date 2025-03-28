# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['build_scripts/app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('ustwo_tools', 'ustwo_tools')],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'ustwo_tools',
        'json',
        'os',
        'sys',
        'logging',
        'datetime',
        'pathlib',
        'base64',
        'io',
        'time',
        'uuid',
        'urllib',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'http',
        'http.client',
        'ssl'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ustwo IT Tools',
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
    icon='assets/brandingimage.icns'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ustwo IT Tools',
)

app = BUNDLE(
    coll,
    name='ustwo IT Tools.app',
    icon='assets/brandingimage.icns',
    bundle_identifier='com.ustwo.it-tools',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDisplayName': 'ustwo IT Tools',
        'CFBundleName': 'ustwo IT Tools',
        'CFBundleExecutable': 'ustwo IT Tools',
        'LSEnvironment': {
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            'QT_MAC_WANTS_LAYER': '1',
        },
        'LSMinimumSystemVersion': '10.13.0',
    },
)
