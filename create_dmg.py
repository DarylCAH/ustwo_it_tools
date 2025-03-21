#!/usr/bin/env python3
"""
DMG Creator for ustwo IT Tools
This script creates a macOS DMG installer for the app bundle
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Run a shell command and return its output"""
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print(f"Error running command: {command}")
        print(f"Error: {process.stderr}")
        return False
    return True

def main():
    print("Creating DMG for ustwo IT Tools...")
    
    # Check if the app exists
    app_path = Path("dist/ustwo IT Tools.app")
    if not app_path.exists():
        print("Error: App bundle not found. Please run build_direct.py first.")
        return
    
    # Check if create-dmg is installed
    result = subprocess.run("which create-dmg", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("create-dmg not found. Installing...")
        if not run_command("brew install create-dmg"):
            print("Failed to install create-dmg. Please install it manually with 'brew install create-dmg'")
            return
    
    # Create a DMG
    dmg_path = Path("dist/ustwo_IT_Tools.dmg")
    if dmg_path.exists():
        os.remove(dmg_path)
    
    print("Creating DMG...")
    dmg_command = f"""
    create-dmg \\
      --volname "ustwo IT Tools Installer" \\
      --background "assets/dmg_background.png" \\
      --window-pos 200 120 \\
      --window-size 800 400 \\
      --icon-size 100 \\
      --icon "ustwo IT Tools.app" 200 190 \\
      --app-drop-link 600 185 \\
      --skip-jenkins \\
      "dist/ustwo_IT_Tools.dmg" \\
      "dist/ustwo IT Tools.app"
    """
    
    # If background image doesn't exist, use a simpler command
    if not Path("assets/dmg_background.png").exists():
        dmg_command = f"""
        create-dmg \\
          --volname "ustwo IT Tools Installer" \\
          --window-pos 200 120 \\
          --window-size 800 400 \\
          --icon-size 100 \\
          --icon "ustwo IT Tools.app" 200 190 \\
          --app-drop-link 600 190 \\
          --skip-jenkins \\
          "dist/ustwo_IT_Tools.dmg" \\
          "dist/ustwo IT Tools.app"
        """
    
    if run_command(dmg_command):
        print(f"\nDMG created successfully at: dist/ustwo_IT_Tools.dmg")
        print("You can distribute this DMG file to users for easy installation.")
    else:
        print("Failed to create DMG. Please check the error messages above.")

if __name__ == "__main__":
    main() 