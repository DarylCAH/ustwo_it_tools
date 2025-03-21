#!/usr/bin/env python3
"""
Direct app bundle builder for ustwo IT Tools
This creates a macOS app bundle manually without PyInstaller or py2app
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("Building ustwo IT Tools app bundle directly...")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Create the app bundle structure
    app_name = "ustwo IT Tools.app"
    app_path = Path("dist") / app_name
    contents_path = app_path / "Contents"
    macos_path = contents_path / "MacOS"
    resources_path = contents_path / "Resources"
    
    # Create directories
    macos_path.mkdir(parents=True, exist_ok=True)
    resources_path.mkdir(parents=True, exist_ok=True)
    
    # Create launcher script
    launcher_path = macos_path / "ustwo_it_tools"
    with open(launcher_path, "w") as f:
        f.write("""#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH="$PYTHONPATH:$DIR/../Resources"
cd "$DIR/../Resources"
/usr/bin/env python3 "$DIR/../Resources/ustwo_tools.py"
""")
    
    # Make launcher executable
    os.chmod(launcher_path, 0o755)
    
    # Create Info.plist
    plist_path = contents_path / "Info.plist"
    with open(plist_path, "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleDisplayName</key>
    <string>ustwo IT Tools</string>
    <key>CFBundleExecutable</key>
    <string>ustwo_it_tools</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.ustwo.it-tools</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>ustwo IT Tools</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSAppleScriptEnabled</key>
    <false/>
</dict>
</plist>
""")
    
    # Create PkgInfo
    with open(contents_path / "PkgInfo", "w") as f:
        f.write("APPL????")
    
    # Copy the Python files
    shutil.copy("ustwo_tools.py", resources_path)
    shutil.copy("Create_Group.py", resources_path)
    shutil.copy("Shared_Drive.py", resources_path)
    shutil.copy("Offboarding.py", resources_path)
    shutil.copy("config.py", resources_path)
    
    # Create config directory in Resources
    config_resources_path = resources_path / "config"
    config_resources_path.mkdir(exist_ok=True)
    
    # Copy or create config.json
    if os.path.exists("config/config.json"):
        shutil.copy("config/config.json", config_resources_path)
    else:
        with open(config_resources_path / "config.json", "w") as f:
            f.write("""{
  "version": "1.0.0",
  "app_name": "ustwo IT Tools",
  "debug": false
}""")
    
    # Copy assets
    assets_resources_path = resources_path / "assets"
    assets_resources_path.mkdir(exist_ok=True)
    
    if os.path.exists("assets"):
        for item in os.listdir("assets"):
            src_path = os.path.join("assets", item)
            dst_path = os.path.join(assets_resources_path, item)
            if os.path.isfile(src_path):
                shutil.copy(src_path, dst_path)
    
    # Copy icon
    if os.path.exists("assets/brandingimage.icns"):
        shutil.copy("assets/brandingimage.icns", resources_path / "icon.icns")
    
    # Set proper permissions
    subprocess.run(["chmod", "-R", "755", str(app_path)])
    
    print(f"\nApp bundle created successfully at: {app_path}")
    print("To run the app:")
    print("1. Double-click the app in the dist/ directory")
    print("2. Or drag it to your Applications folder")
    print("3. If you get a security warning, right-click and select 'Open'")

if __name__ == "__main__":
    main() 