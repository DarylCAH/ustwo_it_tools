from setuptools import setup

APP = ['ustwo_tools.py']
DATA_FILES = [
    ('assets', ['assets/brandingimage.icns']),
    ('config', ['config/.gitkeep'])
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['PyQt5'],
    'includes': ['config'],
    'iconfile': 'assets/brandingimage.icns',
    'plist': {
        'CFBundleName': 'ustwo IT Tools',
        'CFBundleDisplayName': 'ustwo IT Tools',
        'CFBundleIdentifier': 'com.ustwo.it-tools',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2024 ustwo'
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 