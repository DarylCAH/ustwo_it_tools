#!/usr/bin/env python3
"""
py2app setup script for ustwo IT Tools

This script is used to build a macOS app bundle using py2app.
Run with: python3 build_scripts/setup_py2app.py py2app
"""

from setuptools import setup

APP = ['build_scripts/app_launcher.py']  # Use our launcher as the entry point
DATA_FILES = [
    'ustwo_tools.py',
    'Create_Group.py',
    'Shared_Drive.py',
    'Offboarding.py',
    'config.py',
    'assets'
]

OPTIONS = {
    'argv_emulation': False,  # This can cause issues on macOS
    'packages': ['PyQt5', 'json'],
    'includes': [
        'config', 
        'Create_Group', 
        'Shared_Drive', 
        'Offboarding',
        'datetime',
        'pathlib',
        'logging',
        'json'
    ],
    'excludes': ['tkinter', 'matplotlib', 'numpy'],  # Exclude unnecessary large packages
    'plist': {
        'CFBundleName': 'ustwo IT Tools',
        'CFBundleDisplayName': 'ustwo IT Tools',
        'CFBundleIdentifier': 'com.ustwo.ittools',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2023 ustwo ltd',
        'NSHighResolutionCapable': True,
        'LSEnvironment': {'QT_MAC_WANTS_LAYER': '1'},  # Fix for modern macOS
    },
    'iconfile': 'assets/brandingimage.icns'
}

setup(
    name='ustwo IT Tools',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 