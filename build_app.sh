#!/bin/bash
#
# Simple wrapper for the main build script
#

# Make the build script executable
chmod +x ./build_scripts/build_macos_app.sh

# Run the build script in non-interactive mode
./build_scripts/build_macos_app.sh

# Check the result
if [ $? -eq 0 ]; then
    echo "Build completed successfully"
    open ./dist
else
    echo "Build failed"
    exit 1
fi 