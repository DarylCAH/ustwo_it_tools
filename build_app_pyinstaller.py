#!/usr/bin/env python3
"""
PyInstaller build script for ustwo IT Tools
This creates a macOS app with proper configuration
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def run_command(command):
    """Run a command and print output"""
    print(f"Running: {command}")
    subprocess.run(command, shell=True, check=True)

def main():
    print("Setting up PyInstaller for ustwo IT Tools...")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Install PyInstaller if needed
    run_command("pip install 'PyInstaller<5.0'")
    
    # Create a spec file with proper configuration
    spec_file = "ustwo_tools.spec"
    with open(spec_file, "w") as f:
        f.write("""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['ustwo_tools.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('config', 'config')
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'Create_Group',
        'Shared_Drive',
        'Offboarding',
        'config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pkg_resources.py2_warn', 'pkg_resources.tests'],
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
    name='ustwo_tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/brandingimage.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ustwo_tools',
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
        'CFBundleExecutable': 'ustwo_tools',
        'LSEnvironment': {
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
        },
        'LSMinimumSystemVersion': '10.13.0',
    },
)
""")
    
    # Call PyInstaller with the spec file and extra options for Apple Silicon Macs
    print("Building the app with PyInstaller...")
    
    # Use environment variables to avoid problematic modules
    env_vars = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONOPTIMIZE": "1",
    }
    
    # Create environment with necessary variables
    build_env = os.environ.copy()
    build_env.update(env_vars)
    
    # Run PyInstaller with the spec file
    subprocess.run(
        ["python3", "-m", "PyInstaller", "--clean", "--noconfirm", spec_file],
        env=build_env,
        check=True
    )
    
    print("\nBuild complete! You can find the app at:")
    print(f"{os.path.abspath('dist/ustwo IT Tools.app')}")
    print("\nTo create a DMG installer, you can use the create-dmg tool:")
    print("brew install create-dmg")
    print('create-dmg --volname "ustwo IT Tools" --window-pos 200 120 --window-size 800 400 ' + 
          '--icon "ustwo IT Tools.app" 200 190 --app-drop-link 600 185 ' + 
          '"ustwo IT Tools.dmg" "dist/ustwo IT Tools.app"')

if __name__ == "__main__":
    main() 