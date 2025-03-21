# Building ustwo IT Tools for macOS

This document explains how to build the ustwo IT Tools application for macOS.

## Direct Build Method

The simplest and most reliable method is to use the direct build approach which manually creates a macOS app bundle:

```bash
# Build the app
python3 build_direct.py

# Create a DMG installer (optional)
python3 create_dmg.py
```

This will create:
- The application at `dist/ustwo IT Tools.app`
- A DMG installer at `dist/ustwo_IT_Tools.dmg` (if you run the second script)

### How It Works

The direct build approach:
1. Creates a standard macOS app bundle structure
2. Copies all Python files and assets into the Resources directory
3. Creates a launcher script to run the main Python file
4. Sets up the correct permissions and metadata

This approach is simpler and more reliable than using PyInstaller or py2app, which can have issues with certain modules and dependencies.

## Alternative Methods

If the direct build doesn't work for your needs, you can try these alternative approaches:

### Using PyInstaller

```bash
python3 build_app_pyinstaller.py
```

### Using fbs (Python Frozen Binary)

```bash
python3 build_app_fbs.py
```

## Troubleshooting

If you encounter issues:

1. **Missing Dependencies**: Make sure PyQt5 is installed (`pip install PyQt5`)
2. **Path Issues**: Ensure all files are in their expected locations
3. **Permission Errors**: Make sure build scripts are executable (`chmod +x script.py`)
4. **Security Warnings**: When opening the app, right-click and select "Open" to bypass Gatekeeper

## Distribution

For distribution:
1. Use the generated DMG file
2. Users can drag the app to their Applications folder
3. For first launch, users should right-click and select "Open" 