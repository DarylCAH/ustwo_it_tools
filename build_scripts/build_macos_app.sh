#!/bin/bash
#
# Build script for ustwo IT Tools macOS application
#
# This script handles the entire process of building the macOS app:
# 1. Cleans up previous builds
# 2. Creates the app bundle using py2app
# 3. Signs the app with a developer certificate (if available)
# 4. Creates a DMG installer (optional)
# 5. Verifies the app bundle
#

# Exit on any error
set -e

# Get the absolute path of the app directory
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "======================================================="
echo "Building ustwo IT Tools macOS App"
echo "======================================================="
echo "App directory: $APP_DIR"

# Check for dependencies
echo "Checking for required dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

if ! python3 -c "import PyQt5" &> /dev/null; then
    echo "Error: PyQt5 is not installed. Run: pip3 install -r requirements.txt"
    exit 1
fi

if ! python3 -c "import py2app" &> /dev/null; then
    echo "Error: py2app is not installed. Run: pip3 install -r requirements.txt"
    exit 1
fi

# Clean up previous builds
echo "Cleaning up previous builds..."
rm -rf build dist

# Make our launcher script executable
chmod +x build_scripts/app_launcher.py

# Build the app with py2app
echo "Building application with py2app..."
python3 build_scripts/setup_py2app.py py2app

# Check if build was successful
if [ -d "dist/ustwo IT Tools.app" ]; then
    echo "Build successful!"
    APP_PATH="dist/ustwo IT Tools.app"
else
    echo "Build failed! App bundle not found."
    exit 1
fi

# Code signing (optional)
SIGN_IDENTITY=""  # Set your Developer ID here if you have one
if [ -n "$SIGN_IDENTITY" ]; then
    echo "Signing application with identity: $SIGN_IDENTITY"
    codesign --force --deep --sign "$SIGN_IDENTITY" "$APP_PATH"
    echo "Verifying signature..."
    codesign --verify --verbose "$APP_PATH"
else
    echo "Skipping code signing - no identity provided"
    echo "Note: Unsigned apps may trigger Gatekeeper warnings on macOS"
fi

# Create DMG (optional)
CREATE_DMG=false  # Set to true if you want to create a DMG
if [ "$CREATE_DMG" = true ]; then
    echo "Creating DMG installer..."
    if ! command -v create-dmg &> /dev/null; then
        echo "create-dmg not found. Install with: brew install create-dmg"
        echo "Skipping DMG creation."
    else
        create-dmg \
            --volname "ustwo IT Tools" \
            --volicon "assets/brandingimage.icns" \
            --window-pos 200 120 \
            --window-size 800 400 \
            --icon-size 100 \
            --icon "ustwo IT Tools.app" 200 190 \
            --hide-extension "ustwo IT Tools.app" \
            --app-drop-link 600 185 \
            "dist/ustwo IT Tools.dmg" \
            "dist/ustwo IT Tools.app"
        echo "DMG created: dist/ustwo IT Tools.dmg"
    fi
fi

echo "======================================================="
echo "Build completed successfully!"
echo "Application bundle created at: $APP_PATH"
echo "======================================================="
echo "To run the application:"
echo "  open \"$APP_PATH\""
echo "Or copy it to your Applications folder"
echo "" 