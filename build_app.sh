#!/bin/bash

# Exit on error
set -e

echo "Starting build process..."

# Create and activate virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Building the app..."
python setup.py py2app

# Verify the app was created
if [ ! -d "dist/ustwo IT Tools.app" ]; then
    echo "Error: App was not created successfully"
    exit 1
fi

# Print app location
echo "App built successfully! You can find it at:"
echo "dist/ustwo IT Tools.app"

# Print debugging information
echo -e "\nDebugging Information:"
echo "App bundle contents:"
ls -la "dist/ustwo IT Tools.app/Contents/MacOS/"
echo -e "\nPython version used:"
python --version
echo -e "\nInstalled packages:"
pip list

# Deactivate virtual environment
deactivate

echo -e "\nBuild complete! To run the app:"
echo "1. Double-click the app in the dist/ directory"
echo "2. Or drag it to your Applications folder"
echo "3. If you get a security warning, right-click and select 'Open'" 