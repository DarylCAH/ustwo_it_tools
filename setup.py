from setuptools import setup

APP = ['ustwo_tools.py']
DATA_FILES = [
    ('assets', ['assets/brandingimage.icns']),
    ('config', ['config/.gitkeep'])
]
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        'config',
        'json',
        'os',
        'sys',
        'subprocess',
        'logging'
    ],
    'includes': [
        'config',
        'json',
        'os',
        'subprocess',
        'sys',
        'logging'
    ],
    'excludes': ['tkinter'],
    'iconfile': 'assets/brandingimage.icns',
    'plist': {
        'CFBundleName': 'ustwo IT Tools',
        'CFBundleDisplayName': 'ustwo IT Tools',
        'CFBundleIdentifier': 'com.ustwo.it-tools',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2024 ustwo',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSAppleEventsUsageDescription': 'This app needs to run GAM commands',
        'NSAppleScriptEnabled': True,
        'LSEnvironment': {
            'PYTHONPATH': '@executable_path/../Resources/lib/python3.11/site-packages/',
            'DYLD_LIBRARY_PATH': '@executable_path/../Frameworks/'
        },
        'PyRuntimeLocations': [
            '@executable_path/../Frameworks/Python.framework/Versions/3.11/Python'
        ]
    },
    'frameworks': ['Python.framework'],
    'resources': ['assets', 'config'],
    'site_packages': True,
    'strip': False,
    'debug_modulegraph': True,
    'optimize': 0
}

setup(
    name='ustwo_it_tools',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 