#!/bin/bash
echo "=== Starting build process for ustwo IT Tools with debug support ==="
echo "Cleaning up previous builds..."; rm -rf build dist
echo "Building app with py2app..."; python3 setup_py2app.py py2app
echo "=== Build process complete ==="
