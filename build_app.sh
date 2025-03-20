#!/bin/bash

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Clean previous builds
rm -rf build dist

# Build the app
python setup.py py2app

# Deactivate virtual environment
deactivate

echo "App built successfully! You can find it in the dist/ directory." 